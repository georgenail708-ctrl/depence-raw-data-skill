# Native timing evidence and historical clip recovery, v5

This component adds real native data. It does not relabel current projected data as recovered.

## Recovered data

- All 26 OSS headers (200 bytes each) plus first record headers were fetched through bounded source prefixes. Every header matches its prior full-source SHA receipt. Total network read: 1,300,674 bytes.
- Every source has raw byte9=60 and byte10=10. Seven begin with marker3 and nineteen with marker5. All stored record indices start at0, are contiguous, and end at the trailer's last index.
- Generic 60fps rendering documentation and six approximately60Hz spans do not prove native OSS field semantics. Their endpoint residuals differ. Native OSS absolute origin, rate field meaning and endpoint policy remain uncertified; no duration-fit correction was made.
- The separately pinned historical Water DMXT contains73clips and54,732 native(universe,time,512-byte-body) events. Their exact stored timestamp arrays and all original clip fields are preserved in historical_water_native_clips.json.gz.
- Old source aecb016d… and current handoff source94b1782b… are different versions. All73 retained clip metadata records and integer-binned projections match uniquely, but the projection is non-injective. Changing an actual timestamp0.075 to0.076 preserves the current-style array while changing the native sequence. Therefore this supplement never claims restoration of missing current-version subsecond information.
- Applying the known exporter to the historical source performs54,732 event writes into2,048 distinct(clip,universe,integer-second) bins, causing52,684 overwrite operations. This is a demonstrated property of the historical source, not a counted loss in the unknown current original.

## Use

Read native_supplement_receipt.json, then native_clip_reader.load(path, expected_file_sha256, expected_source_sha256). Query by full program and clip IDs; iter_native_events returns original events without interpolation or generated timestamps. A current-source hash request fails.

historical_clip_clock.base_source_clock maps authored timeline time to the producer's base source-sampling clock for supported historical clips. It uses stored playback rate and explicit resize-cycle semantics, never a duration-fit or lag fit. The73-row capability map covers41 full authored intervals,31 hold clips with a provably state-independent interior(local<75% of duration), and1 sequential clip requiring full branch context. Stateful hold edges and sequential requests fail closed. Selection uses the producer's nearest native sample rule; exact midpoints choose the later sample. No bytes are interpolated.

This is the pre-output-transform sampling clock defined by the separately pinned restored playback source, conditional on clip participation, not a claim about an observed historical runtime or its full mixed output. Track mute/solo participation, per-device motor/transition transforms, hold state, decoded audio identity and physical latency are separate. No historical audio-frame pair is certified.

## Verification

test_native_clip_reader.py has9 passing tests verifying73 complete original clip dictionaries, all54,732 event digests, version/hash rejection and the actual non-injectivity counterexample. test_historical_clip_clock.py has11 passing tests covering all72 compatible interiors, nonunit rates, authored cycles, half-open boundaries, both hold-latch states across timer intervals, exact75% hold-edge rejection, unsupported hold cycles, sequential rejection, endpoint cap and nearest-sample choice. Source code is reviewed as text only; no historical application is run.

native_clock_proof_neutral.json records timing facts, source file hashes, line numbers and excerpt hashes without embedding supplied implementation excerpts. Its official documentation links explicitly distinguish what they support from what they do not establish. Final deliverable files are sealed in component_manifest.json; one-off collection/build scripts are excluded. Existing v2 artifacts are untouched.
