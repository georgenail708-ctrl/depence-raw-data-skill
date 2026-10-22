"""Independent read-only regression oracles. No source scripts executed or files modified."""
import sys,pathlib,gzip,json,copy,unittest,collections
S=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(S/'scripts'),str(S/'data/music/clock_bridge_v4')]
from dmxt_channel import classify_definition
from device_semantics import sample_profile
from timeline_reader import map_local_time,map_frame_nominal
class Oracles(unittest.TestCase):
 def test_real_dmxt_boundaries(self):
  c=json.load(gzip.open(S/'data/registry/normalized_contexts/41755b84ce2a6597ab89ef54dcd8c92b0dd41e1a8954cad9315f69ac3c376c3f.json.gz','rt'))
  f=next(x for x in c['fixture_defs'] if x['id']=='1bb18106-8300-41d2-9485-7531c35f2570');i=f['channels'].index('valve')
  for v,label in [(0,'Valve Close'),(254,'Valve Close'),(255,'Valve Open')]:
   r=classify_definition(f,i,v);self.assertEqual(r['source_interval_matches'][0]['source_interval']['name'],label);self.assertEqual(r['status'],'source_interval_match')
  self.assertEqual(classify_definition(f,i,None)['status'],'UNKNOWN_input')
  for v in [-1,256,True,1.5]:
   with self.assertRaises(ValueError):classify_definition(f,i,v)
  q=copy.deepcopy(f);q['channel_modes']['valve'][0]['dmx_max']=255
  self.assertEqual(classify_definition(q,i,255)['status'],'overlapping_source_intervals')
  q['channel_modes']['valve'][0]['dmx_max']=200
  self.assertEqual(classify_definition(q,i,254)['status'],'uncovered_source_value')
 def test_fixture_instance_and_inactive_secondary(self):
  p=json.load(gzip.open(S/'data/device_semantics_v2/fixture_owned_modes.json.gz','rt'))
  f=p['fixtures']['b4d7a937-ff25-4f8f-852b-49fbfff8e9ee'];a={s['source_attrs']['Name']:s for s in f['owned_sources']}
  self.assertNotIn('Rotation',a);self.assertNotIn('Turn',a)
  self.assertEqual((a['Motor']['primary_address'],a['Motor']['stored_secondary_slot']),(8,'8'))
  self.assertEqual((a['Reset']['primary_address'],a['Reset']['stored_secondary_slot']),(9,'9'))
  self.assertIn('unverified',a['Motor']['secondary_slot_active_and_byte_order'])
  self.assertTrue(all(len(v)==1 for v in p['current_primary_address_claims'].values()))
  mode=f['patched_mode_guid'];variants={tuple((s['source_attrs']['Name'],s['source_attrs']['Slot1']) for s in x['owned_sources']) for x in p['fixtures'].values() if x['patched_mode_guid']==mode}
  self.assertGreater(len(variants),1)
 def test_profile_no_invented_extrapolation_or_spline(self):
  p='<PressureProfile IsSpline="False"><KeyPoints><X x="0" y="2"/><X x="1" y="4"/></KeyPoints></PressureProfile>'
  self.assertEqual(sample_profile(p,'0')['status'],'exact_source_knot')
  self.assertEqual(sample_profile(p,'.5')['value'],'3.0')
  self.assertEqual(sample_profile(p,'2')['status'],'outside_declared_domain_no_extrapolation')
  self.assertEqual(sample_profile(p.replace('False','True'),'.5')['status'],'spline_or_unspecified_interpolation_unavailable')
 def test_actual_authored_not_captured_clock(self):
  t=json.loads((S/'data/music/clock_bridge_v4/authored_timeline.json').read_text());song='水仙十字_blk2_240s'
  self.assertEqual(map_local_time(t,song,'4.8')['status'],'no_authored_audio_block')
  r=map_local_time(t,song,'4.833333333333');self.assertEqual(r['audio_objects'][0]['audio_object_guid'],'32514b1d-4aaf-4491-867c-0b29bdfdbf15');self.assertFalse(r['ready_paired'])
  self.assertEqual(map_frame_nominal(t,song,11965)['status'],'outside_authored_dmx_block')
if __name__=='__main__':unittest.main()
