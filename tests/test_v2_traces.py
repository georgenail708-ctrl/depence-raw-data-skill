import hashlib,json,pathlib,sys,tempfile,unittest,zipfile,struct
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from group_trace import trace
from music_compare import compare
from test_dmx_value import npy
class BridgeTests(unittest.TestCase):
 def test_group_members_collisions_zero_one_unknown_and_capture_bounds(self):
  fixture={'source_member_index':0,'source_group_order':'0','fixture_guid':'x','mode_slots':[{'slot1':str(i+1)} for i in range(4)],'current_slot_start_candidates_including_collisions':[{'flat_address_key':str(c),'all_current_claims':[['x',i+1,'p'],['collision',i+1,'p']]} for i,c in enumerate([0,1,2,513])]}
  page={'items':[fixture,{**fixture,'source_member_index':1}, {'source_member_index':2,'fixture_guid':'unmapped','mode_slots':None,'current_slot_start_candidates_including_collisions':[]}],'eof':True,'source_sha256':'s'}
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);np=p/'x.npz';raw=bytearray(1024);raw[512]=1
   with zipfile.ZipFile(np,'w') as z:
    z.writestr('frames.npy',npy('|u1',(2,1,512),raw));z.writestr('first_write_ids.npy',npy('<i8',(2,),struct.pack('<2q',0,1)));z.writestr('first_write_frame.npy',npy('<i8',(2,),struct.pack('<2q',0,1)))
   sha=hashlib.sha256(np.read_bytes()).hexdigest()
   with patch('group_trace.query',return_value=page),patch('group_trace.read_component',return_value=json.dumps({'song_id':'s','recommended_npz':{'sha256':sha}}).encode()):r=trace('s','g',np,sha,0,2,p/'out')
   rows=[json.loads(x) for x in (p/'out').read_text().splitlines()]
   self.assertEqual(r['member_occurrences'],3);self.assertEqual(rows[1]['values'],[0,None,None,None]);self.assertEqual(rows[2]['values'],[1,0,None,None]);self.assertEqual(rows[1]['status'],['known','before_first_write','never_written','out_of_capture']);self.assertEqual(len(rows[0]['metadata']['members']),3);self.assertEqual(len(rows[0]['metadata']['members'][0]['trace_slots'][0]['candidates'][0]['all_claims']),2)
 def test_independent_music_windows_crossing_notes_and_exact_discrepancy(self):
  full={'catalog':{'reference_midi':{'member':'a','source_sha256':'A'},'transcribed_midi':{'member':'b','source_sha256':'B'}},'reference_events':{'notes':[{'pitch':55,'start_s':0.,'end_s':3.,'velocity':100},{'pitch':60,'start_s':3.,'end_s':4.,'velocity':90}]},'transcription_events':{'notes':[{'pitch':55,'start_s':2.,'end_s':2.,'velocity':100}]}}
  with patch('music_compare.load',return_value=full):
   r=compare('s',1,2,2,3)
   self.assertTrue(r['sources']['reference']['items'][0]['crosses_left_boundary']);self.assertTrue(r['sources']['reference']['items'][0]['crosses_right_boundary']);self.assertEqual(r['sources']['reference']['items'][0]['absolute_record_index'],0);self.assertEqual(r['sources']['transcription']['items'][0]['record']['start_s'],2);self.assertEqual(r['exact_tuple_discrepancies']['reference_not_in_transcription_total'],1)
   with self.assertRaises(ValueError):compare('s',2,1,2,3)
if __name__=='__main__':unittest.main()
