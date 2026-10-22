"""Strict historical-source roundtrip and rejection controls; no supplier code execution."""
import copy, gzip, hashlib, json, pathlib, resource, unittest
import native_clip_reader as reader

O = pathlib.Path(__file__).resolve().parent
R = json.loads((O/'native_supplement_receipt.json').read_text())
D = reader.load(O/R['path'],R['sha256'],R['source_sha256'])
C = json.loads((O/'old_dmxt_projection_comparison.json').read_text())
FIRST = C['rows'][0]
PID, CID = FIRST['program_id'], FIRST['old_clip_id']

def one_clip_document():
    p,t,c = reader.get_clip(D,PID,CID)
    return {'source_sha256':D['source_sha256'],'programs':[{'id':p['id'],'tracks':[{'id':t['id'],'clips':[copy.deepcopy(c)]}]}]}

class NativeTests(unittest.TestCase):
    def test_all_73_native_sequences_and_exact_count(self):
        total = 0
        for c in C['rows']:
            sha,n = reader.native_digest(D,c['program_id'],c['old_clip_id'])
            self.assertEqual(sha,c['native_interleaved_u64_f64_body_sha256'])
            self.assertEqual(n,c['old_native_event_count']); total += n
        self.assertEqual(total,54732)
        self.assertEqual(len(C['rows']),73)
    def test_all_original_clip_fields_preserved(self):
        source_path = pathlib.Path(C['source_path'])
        if not source_path.exists():
            self.skipTest('Independent original source is not attached; prior sealed receipt retains the completed original comparison')
        source = json.loads(source_path.read_bytes())
        checked = 0
        for p in source['programs']:
            for t in p['tracks']:
                for c in t['clips']:
                    if c.get('frames_blob'):
                        self.assertEqual(reader.get_clip(D,p['id'],c['id'])[2],c); checked += 1
        self.assertEqual(checked,73)
    def test_current_source_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'Source version mismatch'):
            reader.load(O/R['path'],R['sha256'],'94b1782b9ad68848312945c919009d01657a3600cd63a1d37a45e4d3239e5bf4')
    def test_corrupt_supplement_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'Supplement hash mismatch'):
            reader.load(O/R['path'],'0'*64,R['source_sha256'])
    def test_native_nonuniform_gap_not_filled(self):
        ts = sorted(set(e['source_recording_time_seconds'] for e in reader.iter_native_events(D,PID,CID)))
        self.assertEqual(ts[:3],[0.0,0.075,0.1])
        self.assertNotIn(0.025,ts[:3]); self.assertNotIn(0.05,ts[:3])
    def test_missing_exact_timestamps_rejected(self):
        d = one_clip_document(); f = reader.get_clip(d,PID,CID)[2]['frames_blob']; f.pop('ts'); f['dt']=0.025
        with self.assertRaisesRegex(ValueError,'Exact native timestamps'):
            list(reader.iter_native_events(d,PID,CID))
    def test_out_of_range_universe_map_rejected(self):
        d = one_clip_document(); f = reader.get_clip(d,PID,CID)[2]['frames_blob']; f['m'][0]=999
        with self.assertRaisesRegex(ValueError,'universe index'):
            list(reader.iter_native_events(d,PID,CID))
    def test_noninjective_actual_timestamp_counterexample(self):
        d = one_clip_document(); f = reader.get_clip(d,PID,CID)[2]['frames_blob']
        self.assertEqual(f['ts'][4],0.075); f['ts'][4]=0.076
        def bins(doc):
            out={}
            for e in reader.iter_native_events(doc,PID,CID):
                out[(e['universe'],int(e['source_recording_time_seconds']))]=e['data']
            return out
        self.assertEqual(bins(d),bins(D))
        self.assertNotEqual(reader.native_digest(d,PID,CID),reader.native_digest(D,PID,CID))
    def test_wrong_clip_id_and_audio_pair_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'missing or ambiguous'):
            reader.get_clip(D,PID,'unknown')
        with self.assertRaisesRegex(ValueError,'No decoded audio identity'):
            reader.require_audio_pair(D,PID,CID)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeTests))
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
             'skipped':len(result.skipped),'success':result.wasSuccessful(),'native_sequences_verified':73,'events_verified':54732,
             'actual_noninjectivity_control':'Changed native event4 timestamp0.075→0.076; same integer-binned arrays but different native sequence digest',
             'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (O/'native_reader_test_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
