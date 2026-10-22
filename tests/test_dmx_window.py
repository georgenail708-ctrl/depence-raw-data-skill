import hashlib,json,pathlib,sys,tempfile,unittest,zipfile,struct
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from dmx_window import window
from test_dmx_value import npy
class WindowTests(unittest.TestCase):
 def test_complete_channel_window_unknown_zero_eof(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);np=p/'x.npz';frames=bytearray(2*512);frames[513]=17
   with zipfile.ZipFile(np,'w',compression=8) as z:
    z.writestr('frames.npy',npy('|u1',(2,1,512),frames));z.writestr('first_write_ids.npy',npy('<i8',(2,),struct.pack('<2q',0,1)));z.writestr('first_write_frame.npy',npy('<i8',(2,),struct.pack('<2q',1,0)))
   sha=hashlib.sha256(np.read_bytes()).hexdigest();r=window(np,sha,0,2,p/'out.jsonl');x=[json.loads(l) for l in (p/'out.jsonl').read_text().splitlines()]
   self.assertEqual(r['values_written'],1024);self.assertTrue(r['eof']);self.assertIsNone(r['next_frame']);self.assertEqual(len(x[1]['values']),512);self.assertIsNone(x[1]['values'][0]);self.assertEqual(x[2]['values'][0],0);self.assertEqual(x[2]['values'][1],17);self.assertIsNone(x[2]['values'][2])
   with self.assertRaises(FileExistsError):window(np,sha,0,2,p/'out.jsonl')
   with self.assertRaises(ValueError):window(np,'0'*64,0,2,p/'bad')
if __name__=='__main__':unittest.main()
