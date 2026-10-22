import hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_bundle import verify
class BundleTests(unittest.TestCase):
 def test_freeze_hash_and_path_gates(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'catalog').mkdir();(p/'data').mkdir();f=p/'data/file';f.write_bytes(b'raw')
   m={'version':'test','status':'frozen','files':[{'path':'data/file','size':3,'sha256':hashlib.sha256(b'raw').hexdigest()}]}
   def save():(p/'catalog/components.json').write_text(json.dumps(m))
   save();self.assertEqual(verify(p)['component_files'],1)
   f.write_bytes(b'bad')
   with self.assertRaises(ValueError):verify(p)
   m['files'][0]['path']='../outside';save()
   with self.assertRaises(ValueError):verify(p)
   m['status']='candidate';save()
   with self.assertRaises(ValueError):verify(p)
if __name__=='__main__':unittest.main()
