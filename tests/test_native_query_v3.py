import pathlib,sys,json,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_query import query
SOURCE='aecb016d9b2bdea71f793a0a7a65a81b74a0677006cad39ef777907d2d92e407'
class NativeQueryTests(unittest.TestCase):
 def test_source_version_must_be_explicit_and_exact(self):
  for sha in ['', '94b1782b9ad68848312945c919009d01657a3600cd63a1d37a45e4d3239e5bf4']:
   with self.assertRaises(ValueError):query(sha,'clips',base=ROOT)
 def test_all_clips_and_bounded_events(self):
  r=query(SOURCE,'clips',limit=200,base=ROOT);self.assertEqual(r['total_items'],73);self.assertTrue(r['eof']);self.assertFalse(r['current_source_restored'])
  c=r['items'][0];a=query(SOURCE,'events',c['program_id'],c['clip']['id'],limit=2,base=ROOT)
  self.assertEqual(a['index_range'],[0,2]);self.assertEqual([x['event_index'] for x in a['items']],[0,1]);self.assertTrue(all(len(x['data'])==512 for x in a['items']))
  n=c['native_event_count'];z=query(SOURCE,'events',c['program_id'],c['clip']['id'],start=n-1,limit=2,base=ROOT);self.assertTrue(z['eof']);self.assertEqual(z['items'][0]['event_index'],n-1)
 def test_conditional_historical_clock_not_audio_pair(self):
  cap=json.loads((ROOT/'data/native_clock_v5/historical_clock_capabilities.json').read_text());c=next(r for r in cap['rows'] if r['base_clock_support']=='base_clock_full_authored_interval')
  r=query(SOURCE,'clock',c['program_id'],c['clip_id'],seconds=c['start_time'],base=ROOT);self.assertFalse(r['audio_pair_certified']);self.assertFalse(r['mapping']['final_output_or_audio_pair_certified'])
if __name__=='__main__':unittest.main()
