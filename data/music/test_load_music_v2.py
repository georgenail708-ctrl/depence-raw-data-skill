"""Tests operate only on disposable copies, never mutate sealed evidence."""
import json, shutil, tempfile
from pathlib import Path
from load_music_v2 import MusicLoader, MusicIntegrityError, BASE
checks=[]
def rejects(label, function):
    try:
        function()
    except MusicIntegrityError:
        checks.append(label)
    else:
        raise AssertionError(label + ' did not fail closed')
loader=MusicLoader()
actual=loader.load_song_music('pengquan124_blk0_0s')
assert actual['reference_events']['notes'] and actual['transcription_events']['notes']
checks.append('actual_source_and_derivative_query')
assert len(loader.load_song_music('glimmers_end')['source_record_music_without_packaged_midi']['music']['notes']) == 1590
checks.append('record_only_notes_query')
assert loader.load_data('deterministic_note_facts.jsonl.gz')
checks.append('facts_query')
d=actual['catalog']['transcribed_midi']
with tempfile.TemporaryDirectory(prefix='music_v2_test_', dir='/tmp') as directory:
    root=Path(directory)
    for name in ['music_manifest.json', d['raw_file'], d['events_file'], 'glimmers_end_record_music.json.gz', 'deterministic_note_facts.jsonl.gz']:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(BASE/name,target)
    test=MusicLoader(root)
    assert test.load_source(d)['source']['sha256']==d['source_sha256']
    checks.append('copied_valid_source_and_events')
    event=root/d['events_file'];original=event.read_bytes();event.write_bytes(original[:-1]+bytes([original[-1]^1]))
    rejects('event_tamper_with_unchanged_raw',lambda:test.load_source(d));event.write_bytes(original)
    note=root/'glimmers_end_record_music.json.gz';b=note.read_bytes();note.write_bytes(b+b'x')
    rejects('record_only_notes_tamper',lambda:test.load_data('glimmers_end_record_music.json.gz'));note.write_bytes(b)
    fact=root/'deterministic_note_facts.jsonl.gz';b=fact.read_bytes();fact.write_bytes(b[:-1])
    rejects('facts_tamper',lambda:test.load_data('deterministic_note_facts.jsonl.gz'))
    event.unlink();rejects('missing_events',lambda:test.load_source(d));event.write_bytes(original)
    rejects('traversal',lambda:test.read_verified('../music_manifest.json'))
    rejects('absolute_path',lambda:test.read_verified(str(BASE/'midi_sources.jsonl')))
    rejects('unsupported_sealed_script',lambda:test.read_verified('smf_reader.py'))
    event.unlink();event.symlink_to(BASE/d['events_file'])
    rejects('symlink_escape',lambda:test.load_source(d));event.unlink();event.write_bytes(original)
    bad=dict(d);bad['events_file']='events/'+'0'*64+'.json.gz'
    rejects('descriptor_source_mismatch',lambda:test.load_source(bad))
    manifest=root/'music_manifest.json';manifest.write_bytes(manifest.read_bytes()+b' ')
    rejects('manifest_tamper',lambda:MusicLoader(root))
print(json.dumps({'status':'passed','checks':checks},indent=2))
