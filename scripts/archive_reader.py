"""Read allowed ZIP members from local split parts; Python standard library only."""
import argparse, bisect, hashlib, json, os, struct, tempfile, zlib
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
CHUNK = 1024 * 1024

class Parts:
    def __init__(self, directory, manifest):
        self.root = Path(directory)
        self.manifest = manifest
        self.parts = manifest['parts']
        self.starts = [p['offset'] for p in self.parts]
        self.size = sum(p['size'] for p in self.parts)
    def read(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError('Read outside archive')
        chunks = []
        while length:
            i = bisect.bisect_right(self.starts, offset) - 1
            p = self.parts[i]
            path = self.root / p['filename']
            if Path(p['filename']).name != p['filename']:
                raise ValueError('Unsafe part filename')
            if path.stat().st_size != p['size']:
                raise ValueError('Wrong part size: ' + p['filename'])
            n = min(length, p['size'] - (offset - p['offset']))
            with path.open('rb') as f:
                f.seek(offset - p['offset']); data = f.read(n)
            if len(data) != n:
                raise ValueError('Short part read')
            chunks.append(data); offset += n; length -= n
        return b''.join(chunks)
    def verify(self):
        whole = hashlib.sha256()
        for p in self.parts:
            h = hashlib.sha256(); n = 0
            with (self.root / p['filename']).open('rb') as f:
                for b in iter(lambda: f.read(CHUNK), b''):
                    h.update(b); whole.update(b); n += len(b)
            if n != p['size'] or h.hexdigest() != p['sha256']:
                raise ValueError('Part integrity failure: ' + p['filename'])
        if whole.hexdigest() != self.manifest['archive_sha256']:
            raise ValueError('Whole archive SHA-256 mismatch')
        return {'parts': len(self.parts), 'bytes': self.size, 'archive_sha256': whole.hexdigest(), 'status': 'verified_now'}

def extract(entry, parts, target, max_bytes=1024**3):
    """Write only after complete length/CRC/SHA checks. Never execute archive code."""
    size = entry['uncompressed_size']; csize = entry['compressed_size']
    if size > max_bytes or size < 0 or csize < 0:
        raise ValueError('Member exceeds explicit output budget')
    h = parts.read(entry['local_header_offset'], 30)
    sig, ver, flags, method, tm, dt, crc, cs, us, nl, xl = struct.unpack('<4s5H3L2H', h)
    if sig != b'PK\x03\x04' or flags != entry['flags'] or method != entry['method']:
        raise ValueError('Local header disagrees with catalog')
    if flags & 1 or method not in (0, 8):
        raise ValueError('Encrypted/unsupported member')
    fields = parts.read(entry['local_header_offset'] + 30, nl + xl)
    name = fields[:nl].decode('utf-8' if flags & 2048 else 'cp437')
    if name != entry['name']:
        raise ValueError('Member name mismatch')
    if not flags & 8:
        # ZIP64 uses 0xffffffff sentinels; central catalog supplies actual sizes.
        if crc != int(entry['crc32'], 16) or cs not in (csize, 0xffffffff) or us not in (size, 0xffffffff):
            raise ValueError('Local length/CRC mismatch')
    target = Path(target)
    if target.exists():
        raise FileExistsError('Refusing to overwrite: ' + str(target))
    if not target.parent.is_dir():
        raise FileNotFoundError('Output parent must already exist')
    fd, temp = tempfile.mkstemp(prefix='.member-', dir=target.parent)
    count = checksum = 0; sha = hashlib.sha256()
    dec = zlib.decompressobj(-15) if method == 8 else None
    def write(data, out):
        nonlocal count, checksum
        count += len(data)
        if count > size or count > max_bytes:
            raise ValueError('Expanded output exceeds catalog/budget')
        checksum = zlib.crc32(data, checksum); sha.update(data); out.write(data)
    try:
        with os.fdopen(fd, 'wb') as out:
            off = entry['local_header_offset'] + 30 + nl + xl
            remaining = csize
            while remaining:
                n = min(CHUNK, remaining); data = parts.read(off, n)
                off += n; remaining -= n
                if dec:
                    while data:
                        block = dec.decompress(data, min(CHUNK, size - count + 1))
                        data = dec.unconsumed_tail; write(block, out)
                        if dec.unused_data:
                            raise ValueError('Trailing compressed payload')
                else:
                    write(data, out)
            if dec and (not dec.eof or dec.unused_data or dec.unconsumed_tail):
                raise ValueError('Incomplete deflate stream')
            if count != size or checksum != int(entry['crc32'], 16):
                raise ValueError('Member length/CRC failure')
            digest = sha.hexdigest()
            if entry.get('sha256') and digest != entry['sha256']:
                raise ValueError('Member SHA-256 failure')
        # Hardlink publishes atomically without overwriting an existing target.
        os.link(temp, target)
        return {'name': name, 'bytes': count, 'crc32': f'{checksum:08x}', 'sha256': digest,
                'expected_member_sha256_checked': bool(entry.get('sha256')),
                'archive_verification': 'historical_receipt_only; run verify for local parts',
                'classification': 'raw_source_bytes; contents not certified as accurate'}
    finally:
        os.unlink(temp)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--parts-dir', required=True)
    sp = ap.add_subparsers(dest='command', required=True)
    sp.add_parser('verify')
    ex = sp.add_parser('extract'); ex.add_argument('--member', required=True); ex.add_argument('--out', required=True)
    ex.add_argument('--max-bytes', type=int, default=1024**3)
    args = ap.parse_args()
    parts = Parts(args.parts_dir, json.loads((BASE/'catalog/archive_parts.json').read_text()))
    if args.command == 'verify': result = parts.verify()
    else:
        matches = [e for e in json.loads((BASE/'catalog/archive_entries.json').read_text())['entries'] if e['name'] == args.member]
        if len(matches) != 1: raise ValueError('Member is missing, excluded, or ambiguous')
        result = extract(matches[0], parts, args.out, args.max_bytes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
