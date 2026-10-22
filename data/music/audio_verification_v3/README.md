# Original audio byte and container evidence, v3

This separate component supplements, and does not modify, the sealed music v1 and integrity-loader v2 components.

`audio_catalog.jsonl` contains one row per original archive audio member. Acceptance requires exact ZIP local-header/name agreement, complete decompressed size and CRC agreement, and a SHA-256 computed across every original audio byte. No audio file is retained here. Source bytes remain addressable by archive member and offset in the independently sealed original archive.

Audio is streamed one member at a time into a bounded anonymous memory file. `ffprobe` auto-detects only WAV, MP3 or FLAC using the file protocol. Header/container duration, sample rate, channels and codec are observations from that probe, not a complete decode, listening result or independently measured playback duration. A failed probe does not erase successfully verified byte evidence.

`audio_record_associations.jsonl` preserves record IDs, source path and offset claims, and numerical duration comparisons. Name, path or ID agreement does not certify correct recording identity. Native clock origin, saved offset basis, drift and audio-to-MIDI/DMX correspondence remain unverified. Do not accept a saved timeline formula merely because it is present, and do not optimize an offset against evaluation material and call that independent validation.

`exact_sha_duplicate_groups.json` groups identical complete audio files, not identical choreography. Different choreographies may reuse audio. `record_audio_hash_claims.json` records the search for explicit source audio hash claims in all available compact original-record projections; missing claims are not fabricated.

`audio_summary.json` is the actual traversal outcome. `audio_manifest_v3.json` pins component files by byte size and SHA-256; its own digest is supplied separately to the assembler. `source_pin_validation.json` records post-read Drive metadata pin checks without storing ephemeral credentials or download URLs.

No musical style, genre, emotion, artistic rule, transcription accuracy or semantic song-recognition conclusion is inferred by this component. Existing AI transcription and legacy analyses retain their original confidence and provenance.
