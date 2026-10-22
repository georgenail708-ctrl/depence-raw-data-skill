"""Read all selected group members over contiguous frames using explicit current-patch candidates."""
import argparse,hashlib,json,math,os,tempfile,zipfile
from pathlib import Path
from context_query import query,read_component
from dmx_value import header,integers
BASE=Path(__file__).resolve().parents[1]
def trace(song,group,npz,sha256,start,count,out,base=BASE):
 if start<0 or not 1<=count<=120:raise ValueError('Use start>=0 and count1..120')
 evidence=[json.loads(x) for x in read_component(base,'data/dmx/dmx_manifest_v1.jsonl').decode().splitlines() if x.strip()]
 selected=[r for r in evidence if r['song_id']==song]
 if len(selected)!=1 or not selected[0].get('recommended_npz') or selected[0]['recommended_npz'].get('sha256')!=sha256:raise ValueError('NPZ is not the exact recommended source-song artifact; no cross-song substitution')
 source_evidence=selected[0]
 members=[];cursor=0
 while True:
  page=query(song,group=group,cursor=cursor,limit=1000,base=base)
  if 'dmxt' in page.get('context_schema','').lower():raise ValueError('DMXT universe labels have no verified flat capture mapping; use context and dmxt_channel queries, not an invented universe base.')
  members.extend(page['items'])
  if page['eof']:break
  cursor=page['next_cursor']
 descriptors=[];addresses=[]
 for member in members:
  row={**member,'trace_slots':[]}
  # Every membership occurrence survives, even if saved order or GUID repeats.
  for slot in member.get('mode_slots') or []:
   candidates=[]
   for candidate in member['current_slot_start_candidates_including_collisions']:
    if any(c[0]==member['fixture_guid'] and str(c[1])==str(slot.get('slot1')) for c in candidate['all_current_claims']):
     address=int(candidate['flat_address_key']);candidates.append({'flat_address':address,'all_claims':candidate['all_current_claims']});addresses.append(address)
   row['trace_slots'].append({'source_slot':slot,'candidates':candidates,'mapping_status':'virtual_no_physical_slot' if slot.get('virtual') else 'current_patch_candidate' if candidates else 'unmapped'})
  row['member_status']='mapped_current_context' if row['trace_slots'] else 'missing_fixture_or_mode_or_empty_mode';descriptors.append(row)
 addresses=sorted(set(addresses));columns={c:i for i,c in enumerate(addresses)}
 for row in descriptors:
  for slot in row['trace_slots']:
   for c in slot['candidates']:c['value_column']=columns[c['flat_address']]
 digest=hashlib.sha256()
 with open(npz,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):digest.update(b)
 if digest.hexdigest()!=sha256:raise ValueError('NPZ SHA mismatch')
 out=Path(out)
 if out.exists():raise FileExistsError('Refusing overwrite')
 with zipfile.ZipFile(npz) as z:
  if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate NPZ member')
  with z.open('frames.npy') as f:
   h=header(f);shape=h['shape'];offset=f.tell()
   if h['descr']!='|u1' or len(shape)!=3 or shape[2]!=512:raise ValueError('Not dense uint8[T,U,512]')
   if not 0<=start<shape[0]:raise ValueError('Frame start outside capture')
   if z.getinfo('frames.npy').file_size!=offset+math.prod(shape):raise ValueError('Invalid frame payload length')
   channels=shape[1]*512;ids=integers(z,'first_write_ids');first=integers(z,'first_write_frame')
   if len(ids)!=len(first) or len(ids)!=len(set(ids)):raise ValueError('Invalid first write mapping')
   fw=dict(zip(ids,first))
   if any(not 0<=c<channels or not 0<=t<shape[0] for c,t in fw.items()):raise ValueError('First write outside capture')
   end=min(start+count,shape[0]);f.seek(offset+start*channels)
   metadata={'classification':'raw_array_values_joined_to_current_patch_candidates_NOT_historical_device_actions','song':song,'frame_acceptance':source_evidence.get('acceptance'),'source_authenticity':source_evidence.get('source_authenticity'),'group':group,'members':descriptors,'columns_flat_address':addresses,'source_context_sha256':page['source_sha256'],'npz_sha256':sha256,'capture_shape':shape,'start_frame':start,'end_frame_exclusive':end,'historical_patch_verified':False,'value_semantics':'0 and1 remain exact values; null status distinguishes never_written,before_first_write,out_of_capture','visibility':'A parameter changing is not proof of visible water/light. Physical response and concurrent control dependencies require explicit source evidence.'}
   fd,temp=tempfile.mkstemp(dir=out.parent,prefix='.grouptrace-');output_hash=hashlib.sha256()
   try:
    with os.fdopen(fd,'wb') as target:
     def emit(row):
      data=(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode();target.write(data);output_hash.update(data)
     emit({'metadata':metadata})
     for frame in range(start,end):
      raw=f.read(channels)
      if len(raw)!=channels:raise ValueError('Truncated frame')
      values=[];status=[]
      for c in addresses:
       reason='out_of_capture' if not 0<=c<channels else 'never_written' if c not in fw else 'before_first_write' if frame<fw[c] else 'known'
       status.append(reason);values.append(raw[c] if reason=='known' else None)
      emit({'frame_index':frame,'values':values,'status':status})
    os.link(temp,out)
   finally:os.unlink(temp)
 return {'source_song_id':song,'member_occurrences':len(members),'value_columns':len(addresses),'frames':end-start,'index_range':[start,end],'next_frame':None if end==shape[0] else end,'eof':end==shape[0],'output_sha256':output_hash.hexdigest(),'coverage':'Only this frame window and this exact group; EOF alone does not establish earlier-window coverage.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['song','group','npz','sha256','out']:p.add_argument('--'+name,required=True)
 p.add_argument('--base',default=str(BASE));p.add_argument('--start',type=int,required=True);p.add_argument('--count',type=int,default=1);a=p.parse_args()
 print(json.dumps(trace(a.song,a.group,a.npz,a.sha256,a.start,a.count,a.out,a.base),ensure_ascii=False))
