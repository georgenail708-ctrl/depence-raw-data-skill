"""Own strict SMF 0/1 PPQN parser. Inputs read only; no network/process activity.
Preserves every event payload, original ordering, ticks and byte offsets.
FIFO same-key overlap is bookkeeping, not physical voice identification.
"""
import struct,hashlib,collections,bisect
from pathlib import Path
class MidiParseError(ValueError):pass

def vlq(b,p):
 v=0
 for i in range(4):
  if p>=len(b):raise MidiParseError('truncated VLQ')
  x=b[p];p+=1;v=(v<<7)|(x&127)
  if x<128:return v,p
 raise MidiParseError('VLQ exceeds 4 bytes')

def _parse_track(b,ti,base=0):
 p=tick=order=0;run=None;out=[];name='track '+str(ti);ended=False
 while p<len(b):
  start=p;dt,p=vlq(b,p);tick+=dt
  if p>=len(b):raise MidiParseError('missing event')
  s=b[p]
  if s<128:
   if run is None:raise MidiParseError('running status without channel status')
   s=run
  else:
   p+=1
   if s<240:run=s
  e={'track':ti,'tick':tick,'order':order,'source_byte_offset':base+start,'offset_in_track':start,'status':s};order+=1
  if s==255:
   if p>=len(b):raise MidiParseError('missing meta type')
   mt=b[p];p+=1;n,p=vlq(b,p)
   if p+n>len(b):raise MidiParseError('meta overrun')
   payload=b[p:p+n];p+=n;e.update(kind='meta',meta_type=mt,payload_hex=payload.hex())
   if mt==3:name=payload.decode('utf-8','replace')
   if mt==81:
    if n!=3 or not int.from_bytes(payload,'big'):raise MidiParseError('invalid tempo')
    e.update(kind='tempo',us_per_quarter=int.from_bytes(payload,'big'))
   if mt==88 and n!=4:raise MidiParseError('invalid meter payload')
   if mt==47:
    if n or p!=len(b):raise MidiParseError('invalid EndOfTrack or trailing track bytes')
    e['kind']='end_of_track';ended=True
  elif s in (240,247):
   run=None;n,p=vlq(b,p)
   if p+n>len(b):raise MidiParseError('sysex overrun')
   e.update(kind='sysex',payload_hex=b[p:p+n].hex(),payload_length=n);p+=n
  elif s<240:
   n=1 if s>>4 in (12,13) else 2
   if p+n>len(b):raise MidiParseError('channel overrun')
   d=list(b[p:p+n]);p+=n
   if any(x>127 for x in d):raise MidiParseError('invalid channel data')
   e.update(kind='other',channel=s&15,data=d)
   if s>>4==9 and d[1]:e.update(kind='note_on',pitch=d[0],velocity=d[1])
   if s>>4==8 or (s>>4==9 and d[1]==0):e.update(kind='note_off',pitch=d[0],release_velocity=d[1],release_form='note_on_zero' if s>>4==9 else 'note_off')
  else:raise MidiParseError('unsupported system event')
  out.append(e)
  if ended:break
 if not ended:raise MidiParseError('missing EndOfTrack')
 return out,name

def parse(path):
 b=Path(path).read_bytes()
 if len(b)<14 or b[:4]!=b'MThd':raise MidiParseError('missing header')
 hl=int.from_bytes(b[4:8],'big');fmt,nt,div=struct.unpack('>HHH',b[8:14])
 if hl<6 or 8+hl>len(b) or fmt not in (0,1) or not nt or fmt==0 and nt!=1:raise MidiParseError('unsupported/invalid MIDI header')
 if not div or div&32768:raise MidiParseError('unsupported SMPTE/zero timing')
 p=8+hl;events=[];names=[];ends=[]
 for ti in range(nt):
  if p+8>len(b) or b[p:p+4]!=b'MTrk':raise MidiParseError('missing track chunk')
  n=int.from_bytes(b[p+4:p+8],'big')
  if p+8+n>len(b):raise MidiParseError('track overrun')
  ev,name=_parse_track(b[p+8:p+8+n],ti,p+8);p+=8+n;events+=ev;names.append(name);ends.append(ev[-1]['tick'])
 if p!=len(b):raise MidiParseError('trailing bytes after tracks')
 tempos=[e for e in events if e['kind']=='tempo'];at=collections.defaultdict(list)
 for e in tempos:at[e['tick']].append(e)
 tm=[]
 for tick,ev in sorted(at.items()):
  finals={}
  for e in ev:finals[e['track']]=e['us_per_quarter']
  if len(set(finals.values()))>1:raise MidiParseError('conflicting cross-track tempos')
  tm.append({'tick':tick,'us_per_quarter':next(iter(finals.values())),'all_original_events':ev})
 def sec(t):
  last=0;v=0.;us=500000
  for e in tm:
   if e['tick']>t:break
   v+=(e['tick']-last)*us/1e6/div;last=e['tick'];us=e['us_per_quarter']
  return v+(t-last)*us/1e6/div
 notes=[];opens=collections.defaultdict(collections.deque);unoff=[]
 for e in events:
  if e['kind']=='note_on':
   q=opens[(e['track'],e['channel'],e['pitch'])]
   if q:
    for a in q:a['overlap_fifo_ambiguous']=True
    e['overlap_fifo_ambiguous']=True
   q.append(e)
  elif e['kind']=='note_off':
   q=opens[(e['track'],e['channel'],e['pitch'])]
   if not q:unoff.append(e);continue
   a=q.popleft();notes.append({'track':a['track'],'channel':a['channel'],'pitch':a['pitch'],'velocity':a['velocity'],'release_velocity':e['release_velocity'],'release_form':e['release_form'],'start_tick':a['tick'],'end_tick':e['tick'],'start_s':sec(a['tick']),'end_s':sec(e['tick']),'time_s':sec(a['tick']),'onset_event':a,'release_event':e,'overlap_fifo_ambiguous':a.get('overlap_fifo_ambiguous',False)})
 unon=[a for q in opens.values() for a in q];notes.sort(key=lambda n:(n['start_tick'],n['track'],n['onset_event']['order']))
 return {'format':fmt,'division':div,'ppqn':div,'tempo_map':tm,'tempo_events_raw':tempos,'track_names':names,'track_end_ticks':ends,'tracks':[{'index':i,'name':v,'note_count':sum(n['track']==i for n in notes)} for i,v in enumerate(names)],'notes':notes,'unmatched_starts':unon,'unmatched_releases':unoff,'all_track_events':events,'other_channel_events':[e for e in events if e['kind']=='other'],'duration_s':max((n['end_s'] for n in notes),default=0),'end_of_file_s':sec(max(ends)),'diagnostics':{'unmatched_start_count':len(unon),'unmatched_release_count':len(unoff),'overlap_note_count':sum(n['overlap_fifo_ambiguous'] for n in notes),'tempo_conflicts':[]},'field_semantics':{'velocity':'note-on attack velocity, not artistic accent','release_velocity':'key-release velocity','end_s':'MIDI key-release time, not pedal-extended acoustic duration','overlap_fifo_ambiguous':'FIFO matching convention, voice identity uncertain','tempo':'MIDI time conversion, not verified performed tempo'}}
