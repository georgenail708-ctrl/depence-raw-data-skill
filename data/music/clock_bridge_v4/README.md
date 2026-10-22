# Authored audio timeline repair, v4

## Functional change

The supplier exporter takes the first overlapping audio block, computes its start minus the DMX block start, then applies that offset globally. Independently, it selects reference MIDI by duration/name scoring and finds transcription audio by filename/fallback matching. Those operations do not establish a common media identity.

For 水仙十字_blk2_240s the source show proves four authored intervals, relative to DMX start240s:
- [0,4.8): tail of audio object d6dea3d9-4a99-447f-b8be-800f3cb298d0.
- [4.8,4.833333333333): no authored audio block.
- [4.833333333333,199.3): audio object32514b1d-4aaf-4491-867c-0b29bdfdbf15.
- [199.3,199.4): no authored audio block.

The old−116.933 offset describes the first object's tail, not the entire capture and not the independently selected MP3/MIDI. This is an explained exporter binding error, not a sign-flip or lag-fit repair.

## Use

Use timeline_reader.load(expected_sha256), then map_local_time(timeline, source_song_id, decimal_seconds). Supply the authored_timeline.json SHA from the component manifest. Results preserve all simultaneously authored audio objects and gaps. Inputs are decimal strings; interval ends are exclusive. map_frame_nominal is deliberately labeled nominal and never certifies a ready pair. No interpolation, timing stretch, origin shift or duration-fit resampling is applied.

Only four source IDs have exact record provenance matches for stream filename, show, start and length. The remaining two show blocks retain their GUIDs and ordinal/name claims but are not certified source-ID joins. Nonzero OffsetTime and unsupported Solo semantics fail closed. Source audio positions are unit-rate candidates, not certified decoder/sample-clock coordinates. Mute and parent-track mute are respected. The reader does not synthesize a media or MIDI binding.

## Independent readiness gates

pair_status_by_source_id.jsonl covers every517 original source IDs; unlinked_audio_assets.jsonl preserves all192 verified audio assets. These are retrieval pointers, not synchronization assertions. Legacy links are quarantined only from synchronized/ready-paired use, never deleted. Extra audio can remain unlinked. Zero ready-paired links are established by this repair.

The complete source package has2.show files,1project.xml and26OSS source files. Selected original full records/context and the second show were inspected beyond the normalized summaries. No six-GUID resource definition was found in those sources; the main show holds references, and exhaustive project.xml attribute lookup returned no exact target GUID matches. This is scoped missing binding evidence, not a claim that every package byte was semantically decoded. No filename/order/duration fallback is allowed.

The actual source OSS header has byte9=60 and byte10=10. Six saved show lengths correlate strongly with60Hz, but their recorded sample counts exceed length×60 by0–2samples. EditorResolution30 is an editor setting, not a proven capture rate. Prior26 source receipts retain header hashes but not all header bytes; this repair recovered one200-byte header and matched its prior full-member hash. Native origin, rate interpretation, endpoint policy, trim/playrate and measured playback latency are not established merely by these facts.

## Remaining evidence needed

Provide the source project's audio resource table or original project/archive resources resolving each AudioObjectGUID to exact media bytes, plus authoritative native OSS timing/offset semantics or a qualified source capture-time relation. Existing audio and MIDI analyses may describe an unbound asset, but cannot reconstruct these private missing bindings. Reference MIDI is a source artifact, AI transcription an estimate, and legacy chord/tempo summaries are not musical ground truth.

All original v1/v2/v3 seals remain unchanged. This component adds factual queries and gates rather than silently overwriting old alignment claims. Build scripts require their named audited source inputs; operational retrieval uses only the sealed timeline JSON and reader.
