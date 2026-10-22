"""Emit contiguous dense frame windows with every channel and explicit UNKNOWNs."""
import argparse,hashlib,json,math,os,tempfile,zipfile
from pathlib import Path
from dmx_value import header,integers

def window(npz,sha256,start,count,out):
 if start<0 or not 1<=count<=120:raise ValueError('Use start>=0 and count1..120; resume with next_frame')
 digest=hashlib.sha256()
 with open(npz,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):digest.update(b)
 if digest.hexdigest()!=sha256:raise ValueError('NPZ SHA mismatch')
 out=Path(out)
 if out.exists():raise FileExistsError('Refusing to overwrite output')
 with zipfile.ZipFile(npz) as z:
  if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate NPZ members')
  if 'frames.npy' not in z.namelist():raise ValueError('No dense frames; opaque/Scene/clip is not this format')
  with z.open('frames.npy') as f:
   h=header(f);shape=h['shape']
   if h['descr']!='|u1' or len(shape)!=3 or shape[2]!=512:raise ValueError('Expected uint8[T,U,512]')
   if start>=shape[0]:raise ValueError('Start outside frames')
   offset=f.tell();channels=shape[1]*512
   if z.getinfo('frames.npy').file_size!=offset+math.prod(shape):raise ValueError('Frame payload size mismatch')
   ids=integers(z,'first_write_ids');first=integers(z,'first_write_frame')
   if len(ids)!=len(first) or len(ids)!=len(set(ids)):raise ValueError('Invalid first-write mapping')
   fw=dict(zip(ids,first))
   if any(not 0<=c<channels or not 0<=t<shape[0] for c,t in fw.items()):raise ValueError('First-write range invalid')
   end=min(start+count,shape[0]);f.seek(offset+start*channels)
   meta={'classification':'derived_dense_ordered_window','npz_sha256':sha256,'shape':shape,'start_frame':start,'end_frame_exclusive':end,'channel_ids':'every flat ID0..'+str(channels-1),'unknown':'null if never written or before first write','time_and_fixture_ownership':'not established by array row/channel index'}
   fd,temp=tempfile.mkstemp(prefix='.window-',dir=out.parent);oh=hashlib.sha256()
   try:
    with os.fdopen(fd,'wb') as target:
     def emit(x):
      b=(json.dumps(x,separators=(',',':'))+'\n').encode();target.write(b);oh.update(b)
     emit({'metadata':meta})
     for frame in range(start,end):
      raw=f.read(channels)
      if len(raw)!=channels:raise ValueError('Short frame')
      emit({'frame_index':frame,'values':[raw[c] if c in fw and frame>=fw[c] else None for c in range(channels)]})
    os.link(temp,out)
   finally:os.unlink(temp)
 return {**meta,'output':str(out),'output_sha256':oh.hexdigest(),'frames_written':end-start,'values_written':(end-start)*channels,'next_frame':None if end==shape[0] else end,'eof':end==shape[0],'coverage':'this window only; EOF alone does not prove prior windows were read'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--npz',required=True);p.add_argument('--sha256',required=True);p.add_argument('--start',type=int,required=True);p.add_argument('--count',type=int,default=1);p.add_argument('--out',required=True);a=p.parse_args()
 try:print(json.dumps(window(a.npz,a.sha256,a.start,a.count,a.out),indent=2))
 except FileNotFoundError as e:raise SystemExit('Missing input/output directory: '+str(e.filename)+'. Restore the selected corrected NPZ and create output directory first.') from None
