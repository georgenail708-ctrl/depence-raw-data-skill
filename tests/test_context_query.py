import gzip,hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from context_query import query
class ContextTests(unittest.TestCase):
 def test_exact_order_collisions_unknown_and_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'catalog').mkdir();sha='a'*64
   context={'source_sha256':sha,'groups':{'exact ':[['2','b'],['1','a']]},'fixtures':{'a':{'pos_x_cm':'1','rot':['0','0','0'],'mode_guid':'m'},'b':{'mode_guid':'m'}},'modes':{'m':[{'slot1':'3'}]},'current_patch_address_claims':{'2':[['a',3,'x'],['b',3,'x']]},'render_time_patch_verified':False}
   rel='data/registry/normalized_contexts/'+sha+'.json.gz'
   payload={'data/registry/canonical_registry_v3.jsonl':json.dumps({'source_song_id':'s','context_evidence':{'member_sha256':sha}}).encode(),rel:gzip.compress(json.dumps(context).encode())};files=[]
   for name,b in payload.items():
    target=p/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);files.append({'path':name,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()})
   (p/'catalog/components.json').write_text(json.dumps({'status':'frozen','files':files}))
   first=query('s',group='exact ',limit=1,base=p);last=query('s',group='exact ',cursor=1,base=p)
   self.assertEqual(first['items'][0]['fixture_guid'],'b');self.assertFalse(first['eof']);self.assertTrue(last['eof']);self.assertEqual(len(first['items'][0]['current_slot_start_candidates_including_collisions'][0]['all_current_claims']),2);self.assertFalse(first['source_conventions']['render_time_patch_verified'])
   with self.assertRaises(ValueError):query('s',group='exact',base=p)
   (p/rel).write_bytes(b'changed')
   with self.assertRaises(ValueError):query('s',base=p)
if __name__=='__main__':unittest.main()
