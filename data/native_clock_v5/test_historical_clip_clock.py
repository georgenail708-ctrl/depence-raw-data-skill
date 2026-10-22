import copy,gzip,json,pathlib,resource,unittest
from native_clip_reader import load,get_clip
from historical_clip_clock import base_source_clock,capability,select_native_base_event
O=pathlib.Path(__file__).resolve().parent
R=json.loads((O/'native_supplement_receipt.json').read_text())
D=load(O/R['path'],R['sha256'],R['source_sha256'])
CLIPS=[(p['id'],c) for p in D['programs'] for t in p['tracks'] for c in t['clips']]

class ClockTests(unittest.TestCase):
    def test_all_73_capabilities(self):
        types=[capability(c)['base_clock_support'] for p,c in CLIPS]
        self.assertEqual(types.count('base_clock_full_authored_interval'),41)
        self.assertEqual(types.count('base_clock_safe_interior_only'),31)
        self.assertEqual(types.count('sequential_requires_full_branch_context'),1)
    def test_72_real_clip_midinteriors(self):
        n=0
        for p,c in CLIPS:
            if c['fade_group_sequence_mode']!='parallel':continue
            t=c['start_time']+min(c['duration']*.1,.1)
            r=base_source_clock(D,p,c['id'],t)
            self.assertAlmostEqual(r['base_source_seconds'],(t-c['start_time'])*c['playback_rate'],places=12);n+=1
        self.assertEqual(n,72)
    def test_actual_nonunit_rate(self):
        for p,c in CLIPS:
            if c['playback_rate'] == 1:continue
            t=c['start_time']+1
            r=base_source_clock(D,p,c['id'],t)
            self.assertAlmostEqual(r['base_source_seconds'],c['playback_rate'],places=12)
    def test_before_start_and_exclusive_end_rejected(self):
        for p,c in CLIPS:
            for t in (c['start_time']-1e-6,c['start_time']+c['duration']):
                with self.assertRaisesRegex(ValueError,'Outside half-open'):base_source_clock(D,p,c['id'],t)
    def test_hold_interior_preserved_edge_rejected(self):
        for p,c in CLIPS:
            if c['hold_mode']=='none':continue
            base_source_clock(D,p,c['id'],c['start_time']+.5*c['duration'])
            with self.assertRaisesRegex(ValueError,'Stateful hold edge'):
                base_source_clock(D,p,c['id'],c['start_time']+.9*c['duration'])
    def test_hold_interior_independent_of_timer_and_prelatched_state(self):
        for duration in (.05,1.0,4.0,100.0):
            for timer in (0.0,1e-6,.001,.025,.1,1.0,10.0,1e6):
                for latched in (False,True):
                    enter=min(duration*.25,max(1e-4,timer*1.35))
                    leave=min(duration*.25,max(1e-4,timer*1.75))
                    for local in (0.0,.1*duration,.5*duration,.749999*duration):
                        extension=(local>=duration-(leave if latched else enter)
                                   or (latched and local>=duration-leave))
                        self.assertFalse(extension)
        p,c=CLIPS[0];synthetic=copy.deepcopy(c)
        synthetic.update(start_time=0.0,duration=4.0,hold_mode='last_frame',source_duration=4.0)
        doc={'source_sha256':D['source_sha256'],'programs':[{'id':p,'tracks':[{'clips':[synthetic]}]}]}
        base_source_clock(doc,p,c['id'],3.0-1e-6)
        with self.assertRaisesRegex(ValueError,'Stateful hold edge'):
            base_source_clock(doc,p,c['id'],3.0)
    def test_unsupported_hold_cycle_rejected(self):
        p,c=CLIPS[0];synthetic=copy.deepcopy(c);synthetic['hold_mode']='last_cycle'
        doc={'source_sha256':D['source_sha256'],'programs':[{'id':p,'tracks':[{'clips':[synthetic]}]}]}
        with self.assertRaisesRegex(ValueError,'unsupported_hold_mode'):
            base_source_clock(doc,p,c['id'],c['start_time']+.1)
    def test_real_sequential_rejected(self):
        p,c=next((p,c) for p,c in CLIPS if c['fade_group_sequence_mode']=='sequential')
        with self.assertRaisesRegex(ValueError,'sequential_requires'):
            base_source_clock(D,p,c['id'],c['start_time']+1)
    def test_real_authored_resize_cycle_not_duration_fit(self):
        p,c=next((p,c) for p,c in CLIPS if c['id']=='e8f8386a-eb9a-470f-b2bb-059f24c7ea64')
        t=c['start_time']+6;r=base_source_clock(D,p,c['id'],t)
        self.assertTrue(r['authored_resize_cycle_applied'])
        self.assertAlmostEqual(r['base_source_seconds'],6%5.275,places=12)
    def test_nearest_native_timestamp_tie_later_no_interpolation(self):
        p,c=CLIPS[0];r=select_native_base_event(D,p,c['id'],5,c['start_time']+.05)
        self.assertEqual(r['native_event']['source_recording_time_seconds'],.075)
        self.assertEqual(len(r['native_event']['data']),512)
        synthetic=copy.deepcopy(c);synthetic['start_time']=0.0
        doc={'source_sha256':D['source_sha256'],'programs':[{'id':p,'tracks':[{'clips':[synthetic]}]}]}
        tie=select_native_base_event(doc,p,c['id'],5,.0375)
        self.assertEqual(tie['native_event']['source_recording_time_seconds'],.075)
    def test_near_end_cap_for_no_hold(self):
        p,c=next((p,c) for p,c in CLIPS if c['id']=='00567a33-659e-4dac-a1a4-4223f8f2c62e')
        r=base_source_clock(D,p,c['id'],c['start_time']+c['duration']-1e-6)
        self.assertAlmostEqual(r['base_source_seconds'],c['source_duration']-1e-4,places=12)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ClockTests))
    caps=[{'program_id':p,**capability(c)} for p,c in CLIPS]
    (O/'historical_clock_capabilities.json').write_text(json.dumps({'schema':'depence.historical_base_clock_capabilities.v5','rows':caps},ensure_ascii=False,indent=2)+'\n')
    (O/'historical_clock_test_receipt.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'success':result.wasSuccessful(),'actual_clips_with_safe_interior_tested':72,'full_authored_interval_base_clock':41,'hold_safe_interior':31,'sequential_blocked':1,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
