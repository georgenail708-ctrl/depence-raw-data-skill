"""Read one known dense channel cell without NumPy, never invent unwritten zeroes."""
import argparse,ast,hashlib,json,math,struct,zipfile

def header(f):
 if f.read(6)!=b'\x93NUMPY':raise ValueError('Not NPY')
 v=f.read(2)
 if v==b'\x01\x00':n=struct.unpack('<H',f.read(2))[0]
 elif v in (b'\x02\x00',b'\x03\x00'):n=struct.unpack('<I',f.read(4))[0]
 else:raise ValueError('Unsupported NPY version')
 if n>65536:raise ValueError('Oversized NPY header')
 h=ast.literal_eval(f.read(n).decode('utf8' if v[0]==3 else 'latin1'))
 if h.get('fortran_order'):raise ValueError('Fortran layout not supported')
 if not isinstance(h['shape'],tuple) or any(type(x)!=int or x<0 for x in h['shape']):raise ValueError('Invalid shape')
 return h

def integers(z,name):
 with z.open(name+'.npy') as f:
  h=header(f);fmt={'<i8':'<q','<i4':'<i','|u1':'B','<u8':'<Q','<u4':'<I'}.get(h['descr'])
  if fmt is None or len(h['shape'])!=1 or h['shape'][0]>1000000:raise ValueError('Unsupported integer vector')
  n=h['shape'][0]*struct.calcsize(fmt);b=f.read(n+1)
  if len(b)!=n:raise ValueError('Vector length mismatch')
  return [v[0] for v in struct.iter_unpack(fmt,b)]

def value(path,expected_sha,frame,channel):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 if h.hexdigest()!=expected_sha:raise ValueError('NPZ does not match selected audit evidence')
 with zipfile.ZipFile(path) as z:
  if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate NPZ members')
  if 'frames.npy' not in z.namelist():raise ValueError('No dense frames; opaque/Scene data cannot be interpreted as DMX')
  with z.open('frames.npy') as f:
   a=header(f);shape=a['shape']
   if a['descr']!='|u1' or len(shape)!=3 or shape[2]!=512:raise ValueError('Not uint8[T,U,512] dense frames')
   if not 0<=frame<shape[0] or not 0<=channel<shape[1]*512:raise ValueError('Frame/channel outside array')
   if z.getinfo('frames.npy').file_size!=f.tell()+math.prod(shape):raise ValueError('Frame payload length mismatch')
   ids=integers(z,'first_write_ids');first=integers(z,'first_write_frame')
   if len(ids)!=len(first) or len(set(ids))!=len(ids):raise ValueError('Invalid first-write mapping')
   fw=dict(zip(ids,first))
   if any(not 0<=i<shape[1]*512 or not 0<=t<shape[0] for i,t in fw.items()):raise ValueError('Invalid first-write range')
   out={'classification':'derived_dense_value','frame_index':frame,'flat_channel_id':channel,'npz_sha256':expected_sha,'fixture_ownership':'unknown_without_validated_mapping','time_seconds':'unknown_without_validated_clock','source_authenticity':'not_established_by_this_query'}
   if channel not in fw or frame<fw[channel]:out.update(status='UNKNOWN',value=None,reason='channel not written by this frame')
   else:
    f.seek(f.tell()+frame*shape[1]*512+channel);v=f.read(1)
    if len(v)!=1:raise ValueError('Truncated frame cell')
    out.update(status='known_in_selected_array',value=v[0],first_write_frame=fw[channel])
   return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--npz',required=True);p.add_argument('--sha256',required=True);p.add_argument('--frame',required=True,type=int);p.add_argument('--channel',required=True,type=int);a=p.parse_args();print(json.dumps(value(a.npz,a.sha256,a.frame,a.channel),indent=2))
if __name__=='__main__':main()
