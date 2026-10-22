"""Exact native events from a separately pinned historical DMXT version.

Never joins by title, duration, current exported array, or a claimed current hash.
Reads source timestamps as stored; does not generate a uniform time sequence.
"""
import base64, gzip, hashlib, json, math, pathlib, struct, zlib

SOURCE_SHA256 = 'aecb016d9b2bdea71f793a0a7a65a81b74a0677006cad39ef777907d2d92e407'
MAX_JSON_BYTES = 20 * 1024 * 1024
MAX_EVENTS_PER_CLIP = 200000

def load(path, expected_sha256, expected_source_sha256):
    p = pathlib.Path(path)
    if p.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Supplement exceeds compressed-size bound')
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != expected_sha256:
        raise ValueError('Supplement hash mismatch')
    if expected_source_sha256 != SOURCE_SHA256:
        raise ValueError('Source version mismatch: historical data cannot fill current gaps')
    with gzip.open(p, 'rb') as f:
        raw = f.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('Supplement exceeds JSON bound')
    d = json.loads(raw)
    if d.get('source_sha256') != expected_source_sha256:
        raise ValueError('Declared source hash mismatch')
    if d.get('schema') != 'depence.native_clip_supplement.v5':
        raise ValueError('Unsupported schema')
    return d

def get_clip(document, program_id, clip_id):
    found = [(p,t,c) for p in document['programs'] if p['id'] == program_id
             for t in p['tracks'] for c in t['clips'] if c['id'] == clip_id]
    if len(found) != 1:
        raise ValueError('Native clip ID missing or ambiguous')
    return found[0]

def iter_native_events(document, program_id, clip_id):
    _, _, c = get_clip(document, program_id, clip_id)
    f = c['frames_blob']
    n = f.get('n')
    if f.get('v') != 1 or type(n) is not int or not 0 < n <= MAX_EVENTS_PER_CLIP:
        raise ValueError('Invalid native frame count or version')
    if 'ts' not in f or len(f['ts']) != n or len(f.get('m', [])) != n:
        raise ValueError('Exact native timestamps and universe map are required')
    unis = f.get('unis')
    if not isinstance(unis, list) or not unis or len(set(unis)) != len(unis) or any(type(u) is not int for u in unis):
        raise ValueError('Invalid universe IDs')
    z = zlib.decompressobj()
    b = z.decompress(base64.b64decode(f['b'], validate=True), n * 512 + 1)
    if len(b) != n * 512 or not z.eof or z.unused_data or z.unconsumed_tail:
        raise ValueError('Native body length mismatch or trailing stream')
    for i, (m,t) in enumerate(zip(f['m'], f['ts'])):
        if type(m) is not int or not 0 <= m < len(unis):
            raise ValueError('Invalid native universe index')
        if type(t) not in (int,float) or not math.isfinite(t) or t < 0:
            raise ValueError('Invalid native timestamp')
        yield {'event_index':i, 'universe':unis[m], 'source_recording_time_seconds':t,
               'data':b[i*512:(i+1)*512], 'source_sha256':document['source_sha256']}

def native_digest(document, program_id, clip_id):
    h = hashlib.sha256(); count = 0
    for e in iter_native_events(document, program_id, clip_id):
        h.update(struct.pack('<qd',e['universe'],e['source_recording_time_seconds']))
        h.update(e['data']); count += 1
    return h.hexdigest(), count

def require_audio_pair(*args, **kwargs):
    raise ValueError('No decoded audio identity or source playback bridge is certified by native event recovery alone')
