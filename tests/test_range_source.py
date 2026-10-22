import io,pathlib,sys,time,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from range_source import RangeParts,EphemeralHTTP
class Response(io.BytesIO):
 def __init__(self,body,status=206,cr='bytes 1-2/4'):
  super().__init__(body);self.status=status;self.headers={'Content-Range':cr,'Content-Length':str(len(body))}
class Opener:
 def __init__(self,response):self.response=response;self.calls=0
 def open(self,*a,**kw):self.calls+=1;return self.response
class RangeTests(unittest.TestCase):
 def test_cross_parts_exact_bounds(self):
  calls=[];data=[b'abc',b'defg'];m={'parts':[{'offset':0,'size':3},{'offset':3,'size':4}]}
  def fetch(i,s,n,t):calls.append((i,s,n,t));return data[i][s:s+n]
  r=RangeParts(m,fetch);self.assertEqual(r.read(2,4),b'cdef');self.assertEqual(calls,[(0,2,1,3),(1,0,3,4)])
  with self.assertRaises(ValueError):r.read(6,2)
 def test_http_contract_and_expiry(self):
  grant=lambda p:{'url':'https://example.invalid/ephemeral','expires_at_epoch':time.time()+300}
  self.assertEqual(EphemeralHTTP(grant,Opener(Response(b'bc')))(0,1,2,4),b'bc')
  for response in [Response(b'abcd',200),Response(b'bc',206,'bytes 0-1/4'),Response(b'bcd')]:
   o=Opener(response);h=EphemeralHTTP(grant,o)
   with self.assertRaises(RuntimeError):h(0,1,2,4)
   with self.assertRaises(RuntimeError):h(0,1,2,4)
   self.assertEqual(o.calls,1)
  o=Opener(Response(b'bc'));h=EphemeralHTTP(lambda p:{'url':'https://example.invalid','expires_at_epoch':0},o)
  with self.assertRaises(RuntimeError):h(0,1,2,4)
  self.assertEqual(o.calls,0)
if __name__=='__main__':unittest.main()
