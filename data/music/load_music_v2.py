"""Version 2: fail-closed, pinned-manifest music evidence retrieval.

The immutable v1 manifest supplies hashes for source and derivative data. v2 does
not change evidence files or the v1 seal. No network, models, or source writes.
"""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent
V1_MANIFEST_SHA256 = 'a3f437e3afbbfffa4df96fb70e6144ae90d5599e6b93023b1a6391fc39d6c122'
EXACT_DATA = {
    'song_music_catalog.jsonl', 'midi_sources.jsonl', 'cache_sources.jsonl',
    'note_cache_checks.jsonl', 'analysis_qa_sources.jsonl',
    'deterministic_note_facts.jsonl.gz', 'glimmers_end_record_music.json.gz',
    'music_gaps.jsonl', 'music_summary.json',
}

class MusicIntegrityError(ValueError):
    """Missing, unsupported, escaped, or altered evidence is never returned."""

class MusicLoader:
    def __init__(self, base=BASE):
        self.base = Path(base).resolve(strict=True)
        manifest_path = self._contained('music_manifest.json')
        blob = self._bounded_read(manifest_path, 2 * 1024 * 1024)
        if hashlib.sha256(blob).hexdigest() != V1_MANIFEST_SHA256:
            raise MusicIntegrityError('Pinned v1 manifest hash mismatch')
        manifest = json.loads(blob)
        self.files = {}
        for entry in manifest['files']:
            name = entry['path']
            self._contained(name)
            if name in self.files:
                raise MusicIntegrityError('Duplicate manifest member')
            self.files[name] = entry

    def _contained(self, name):
        if not isinstance(name, str) or not name or '\\' in name:
            raise MusicIntegrityError('Unsupported member path')
        logical = PurePosixPath(name)
        if logical.is_absolute() or '..' in logical.parts or str(logical) != name:
            raise MusicIntegrityError('Unsupported member path')
        path = (self.base / name).resolve()
        try:
            path.relative_to(self.base)
        except ValueError as exc:
            raise MusicIntegrityError('Member path escapes data directory') from exc
        return path

    @staticmethod
    def _bounded_read(path, limit):
        try:
            with path.open('rb') as stream:
                blob = stream.read(limit + 1)
        except (OSError, ValueError) as exc:
            raise MusicIntegrityError('Missing or unreadable evidence: ' + path.name) from exc
        if len(blob) > limit:
            raise MusicIntegrityError('Evidence exceeds expected size: ' + path.name)
        return blob

    @staticmethod
    def _supported(name):
        if name in EXACT_DATA:
            return True
        parts = PurePosixPath(name).parts
        if len(parts) != 2:
            return False
        folder, filename = parts
        permitted = {'raw_midi': ('.mid',), 'events': ('.json.gz',),
                     'legacy_facts': ('.json', '.md'), 'legacy_analysis_qa': ('.json',)}
        if folder not in permitted:
            return False
        for extension in permitted[folder]:
            if filename.endswith(extension):
                stem = filename[:-len(extension)]
                return len(stem) == 64 and all(c in '0123456789abcdef' for c in stem)
        return False

    def read_verified(self, name):
        path = self._contained(name)
        if not self._supported(name) or name not in self.files:
            raise MusicIntegrityError('Unsupported or unsealed data member: ' + name)
        entry = self.files[name]
        blob = self._bounded_read(path, entry['size'])
        if len(blob) != entry['size'] or hashlib.sha256(blob).hexdigest() != entry['sha256']:
            raise MusicIntegrityError('Evidence size/hash mismatch: ' + name)
        return blob

    def load_data(self, name):
        """Verify bytes before decoding requested event, note, fact, or legacy data."""
        blob = self.read_verified(name)
        if name.endswith('.gz'):
            blob = gzip.decompress(blob)
            name = name[:-3]
        if name.endswith('.jsonl'):
            return [json.loads(line) for line in blob.decode('utf-8-sig').splitlines() if line]
        if name.endswith('.json'):
            return json.loads(blob.decode('utf-8-sig'))
        if name.endswith('.md'):
            return blob.decode('utf-8-sig')
        return blob

    def catalog(self):
        return self.load_data('song_music_catalog.jsonl')

    def load_source(self, descriptor):
        if not descriptor:
            return None
        sha = descriptor.get('source_sha256')
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise MusicIntegrityError('Invalid source hash')
        if descriptor.get('raw_file') != 'raw_midi/' + sha + '.mid' or descriptor.get('events_file') != 'events/' + sha + '.json.gz':
            raise MusicIntegrityError('Source/derivative descriptor path mismatch')
        raw = self.read_verified(descriptor['raw_file'])
        if hashlib.sha256(raw).hexdigest() != sha:
            raise MusicIntegrityError('Source MIDI identity mismatch')
        events = self.load_data(descriptor['events_file'])
        if events.get('source', {}).get('sha256') != sha:
            raise MusicIntegrityError('Derivative source MIDI identity mismatch')
        return events

    def load_song_music(self, source_song_id):
        matches = [r for r in self.catalog() if r['source_song_id'] == source_song_id]
        if len(matches) != 1:
            raise MusicIntegrityError('Song ID missing or ambiguous')
        row = matches[0]
        result = {'catalog': row,
                  'reference_events': self.load_source(row.get('record_reference_midi') or row.get('reference_midi')),
                  'transcription_events': self.load_source(row.get('transcribed_midi'))}
        record_only = row.get('record_only_music_file')
        if record_only:
            result['source_record_music_without_packaged_midi'] = self.load_data(record_only)
        return result

# Preserve the simple v1 call shape without weakening v2 checks.
def load_song_music(source_song_id):
    return MusicLoader().load_song_music(source_song_id)
