"""Compare explicit independent MIDI-local windows without choosing a musical ground truth."""
import argparse,json,math
from pathlib import Path
from music_query import load,CLOCK_DOMAINS
BASE=Path(__file__).resolve().parents[1]
def compare(song,reference_start,reference_end,transcription_start,transcription_end,reference_cursor=0,transcription_cursor=0,limit=100,base=BASE):
 if not 1<=limit<=1000:raise ValueError('Limit outside1..1000')
 full=load(song,base);result={'source_song_id':song,'classification':'independent_source_local_note_windows_NOT_synchronized_audio','clock_domains':CLOCK_DOMAINS,'truth_selection':'Neither source is automatically true; no union, time shift, nearest-note matching or replacement performed.','sources':{}}
 signatures={}
 for name,start,end,cursor in [('reference',reference_start,reference_end,reference_cursor),('transcription',transcription_start,transcription_end,transcription_cursor)]:
  if not all(math.isfinite(v) for v in [start,end]) or not 0<=start<end or cursor<0:raise ValueError('Invalid half-open window/cursor')
  data=full[name+'_events'];catalog=full['catalog'];identity=(catalog.get('record_reference_midi') or catalog.get('reference_midi')) if name=='reference' else catalog.get('transcribed_midi')
  if data is None:result['sources'][name]={'status':'source_absent','requested_window':[start,end]};signatures[name]=set();continue
  notes=data['notes'];selected=[];unknown=[]
  for index,note in enumerate(notes):
   a=note.get('start_s',note.get('time_s'));b=note.get('end_s')
   if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or not math.isfinite(a) or not math.isfinite(b):unknown.append({'absolute_record_index':index,'record':note});continue
   # Sustained notes crossing either boundary are retained. A zero-length event belongs by onset.
   if a<end and (b>start or (a==b and start<=a<end)):selected.append({'absolute_record_index':index,'record':note,'crosses_left_boundary':a<start,'crosses_right_boundary':b>end})
  if cursor>len(selected):raise ValueError('Cursor past filtered window')
  stop=min(cursor+limit,len(selected));result['sources'][name]={'status':'available','requested_source_identity':identity,'canonical_event_byte_source':data.get('source'),'window_half_open':[start,end],'selection':'key-release overlap, including crossing notes; not pedal acoustic duration','source_total_notes':len(notes),'window_total_notes':len(selected),'cursor':cursor,'next_cursor':None if stop==len(selected) else stop,'eof':stop==len(selected),'items':selected[cursor:stop],'indeterminate_note_indices':[x['absolute_record_index'] for x in unknown],'unmatched_start_count':len(data.get('unmatched_starts',[])),'unmatched_release_count':len(data.get('unmatched_releases',[])),'unmatched_event_route':'Use music_query --all to preserve unmatched raw events; this window does not assign them invented durations.'}
  signatures[name]={(x['record'].get('pitch'),x['record'].get('start_s'),x['record'].get('end_s'),x['record'].get('velocity')) for x in selected}
 a=signatures['reference'];b=signatures['transcription']
 result['exact_tuple_discrepancies']={'tuple_fields':['pitch','start_s','end_s','velocity'],'reference_not_in_transcription':sorted(a-b,key=repr),'transcription_not_in_reference':sorted(b-a,key=repr),'semantics':'Exact source tuple difference over both full selected windows; not a correctness verdict or alignment test.','bounded_display':False}
 # Preserve bounded output: discrepancies also paginate, independently of source pages.
 result['exact_tuple_discrepancies']['reference_not_in_transcription_total']=len(a-b);result['exact_tuple_discrepancies']['transcription_not_in_reference_total']=len(b-a)
 result['exact_tuple_discrepancies']['reference_not_in_transcription']=sorted(a-b,key=repr)[reference_cursor:reference_cursor+limit];result['exact_tuple_discrepancies']['transcription_not_in_reference']=sorted(b-a,key=repr)[transcription_cursor:transcription_cursor+limit];result['exact_tuple_discrepancies']['bounded_display']=True
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--song',required=True);p.add_argument('--base',default=str(BASE));p.add_argument('--limit',type=int,default=100)
 for source in ['reference','transcription']:
  for bound in ['start','end']:p.add_argument('--'+source+'-'+bound,type=float,required=True)
  p.add_argument('--'+source+'-cursor',type=int,default=0)
 a=p.parse_args();print(json.dumps(compare(a.song,a.reference_start,a.reference_end,a.transcription_start,a.transcription_end,a.reference_cursor,a.transcription_cursor,a.limit,a.base),ensure_ascii=False))
