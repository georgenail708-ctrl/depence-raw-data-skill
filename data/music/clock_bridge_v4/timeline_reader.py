"""Read exact authored show intervals, never infer a recording/MIDI binding."""
import json,hashlib
from pathlib import Path
from decimal import Decimal,InvalidOperation
P=Path(__file__).resolve().parent

def number(value):
 try:d=Decimal(str(value))
 except InvalidOperation:raise ValueError('Invalid time') from None
 if not d.is_finite():raise ValueError('Time must be finite')
 return d

def load(expected_sha256):
 raw=(P/'authored_timeline.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Timeline integrity mismatch')
 return json.loads(raw)

def map_show_time(timeline,show_s):
 t=number(show_s)
 if any(x.get('Solo')!='False' for x in timeline['tracks']):raise ValueError('Unsupported solo-track semantics')
 tracks={x['GUID']:x for x in timeline['tracks']};active=[]
 for b in timeline['audio_blocks']:
  start=number(b['StartTime']);end=start+number(b['LengthTime'])
  if not start<=t<end:continue
  track=tracks.get(b['ParentTrack'])
  if not track:raise ValueError('Missing parent track evidence')
  if b.get('Mute')!='False' or track.get('Muted')!='False':continue
  if number(b.get('OffsetTime','0'))!=0:raise ValueError('Unsupported nonzero OffsetTime')
  active.append({'audio_block_guid':b['GUID'],'audio_object_guid':b['AudioObjectGUID'],'authored_audio_elapsed_s':str(t-start),'saved_source_start_s':b['StartTimeInAudioStream'],'unit_rate_source_position_candidate_s':str(t-start+number(b['StartTimeInAudioStream'])),'source_audio_position_semantics':'unit-rate candidate using authored elapsed plus saved source start; explicit playback-rate/native decoder sample clock not certified','stream_file_binding':'consult exact GUID binding overlay; never substitute legacy duration/name match'})
 return {'show_time_s':str(t),'audio_objects':active,'status':'authored_audio_interval' if active else 'no_authored_audio_block','ready_paired':False,'precision_scope':'authored decimal interval arithmetic only; not independently verified rendering/audio sampling synchronization'}

def map_local_time(timeline,song_id,local_s):
 row=next((r for r in timeline['piecewise_intervals'] if r['source_song_id']==song_id),None)
 if row is None:raise KeyError('Unsupported source song ID')
 block=next(b for b in timeline['dmx_blocks'] if b['GUID']==row['dmx_block_guid']);t=number(local_s)
 if t<0 or t>=number(block['LengthTime']):return {'status':'outside_authored_dmx_block','ready_paired':False,'source_song_id':song_id,'dmx_local_time_s':str(t)}
 out=map_show_time(timeline,number(block['StartTime'])+t);out.update(source_song_id=song_id,dmx_local_time_s=str(t),dmx_block_guid=block['GUID']);return out

def map_frame_nominal(timeline,song_id,frame):
 if isinstance(frame,bool) or not isinstance(frame,int):raise ValueError('Integer frame index required')
 rec=next((r for r in timeline['record_claims'] if r['source_song_id']==song_id),None)
 if not rec or not rec['frames_shape'] or rec['fps_claim'] is None:raise ValueError('No saved nominal frame-rate claim')
 if not 0<=frame<rec['frames_shape'][0]:raise ValueError('Frame outside complete captured array')
 out=map_local_time(timeline,song_id,Decimal(frame)/number(rec['fps_claim']));out.update(frame_index=frame,frame_clock_status='nominal exporter FPS only; source sampling origin/rate and endpoint correspondence uncalibrated',fps_claim=rec['fps_claim']);return out

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--timeline-sha256',required=True);a.add_argument('--song',required=True);g=a.add_mutually_exclusive_group(required=True);g.add_argument('--local-seconds');g.add_argument('--nominal-frame',type=int);x=a.parse_args();t=load(x.timeline_sha256)
 print(json.dumps(map_local_time(t,x.song,x.local_seconds) if x.local_seconds is not None else map_frame_nominal(t,x.song,x.nominal_frame),ensure_ascii=False,indent=2))
