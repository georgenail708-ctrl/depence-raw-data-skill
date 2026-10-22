import hashlib,io,pathlib,struct,sys,tempfile,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from dmx_value import value

def npy(dtype,shape,data):
 h=repr({'descr':dtype,'fortran_order':False,'shape':shape}).encode();h+=b' '*((64-(10+len(h)+1)%64)%64)+b'\n'
 return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(h))+h+data
class ValueTests(unittest.TestCase):
 def test_known_zero_and_unknown(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'test.npz';frames=bytearray(2*512);frames[512]=0;frames[513]=21
   with zipfile.ZipFile(p,'w',compression=8) as z:
    z.writestr('frames.npy',npy('|u1',(2,1,512),bytes(frames)))
    z.writestr('first_write_ids.npy',npy('<i8',(2,),struct.pack('<2q',0,1)))
    z.writestr('first_write_frame.npy',npy('<i8',(2,),struct.pack('<2q',1,0)))
   sha=hashlib.sha256(p.read_bytes()).hexdigest()
   self.assertIsNone(value(p,sha,0,0)['value']);self.assertIsNone(value(p,sha,1,2)['value'])
   self.assertEqual(value(p,sha,1,0)['value'],0);self.assertEqual(value(p,sha,1,1)['value'],21)
   with self.assertRaises(ValueError):value(p,'0'*64,1,1)
   with self.assertRaises(ValueError):value(p,sha,2,1)
if __name__=='__main__':unittest.main()
