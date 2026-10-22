"""Own synthetic boundary/fail-closed and actual authored interval controls."""
import copy,hashlib,json
from pathlib import Path
from timeline_reader import load,map_local_time,map_frame_nominal,map_show_time
p=Path(__file__).resolve().parent;t=load(hashlib.sha256((p/'authored_timeline.json').read_bytes()).hexdigest());sid='水仙十字_blk2_240s';checks=[]
def check(name,ok):assert ok,name;checks.append(name)
check('first4.8seconds_previous_audio',map_local_time(t,sid,0)['audio_objects'][0]['audio_object_guid']=='d6dea3d9-4a99-447f-b8be-800f3cb298d0')
check('gap_at_previous_audio_end',map_local_time(t,sid,'4.8')['audio_objects']==[])
check('new_audio_exact_start',map_local_time(t,sid,'4.833333333333')['audio_objects'][0]['unit_rate_source_position_candidate_s']=='0E-12')
check('last_gap',map_local_time(t,sid,'199.3')['audio_objects']==[])
check('dmx_end_exclusive',map_local_time(t,sid,'199.4')['status']=='outside_authored_dmx_block')
check('extra_saved_frame_not_stretched',map_frame_nominal(t,sid,11965)['status']=='outside_authored_dmx_block')
check('no_certified_pair_from_nominal_frame',map_frame_nominal(t,sid,300)['ready_paired'] is False)
check('negative_time_outside',map_local_time(t,sid,-1)['status']=='outside_authored_dmx_block')
for name,fn in [('nan_rejected',lambda:map_show_time(t,'NaN')),('out_of_array_rejected',lambda:map_frame_nominal(t,sid,11966)),('wrong_hash_rejected',lambda:load('0'*64))]:
 try:fn()
 except ValueError:checks.append(name)
 else:raise AssertionError(name)
s=copy.deepcopy(t);s['audio_blocks'][2]['OffsetTime']='1'
try:map_show_time(s,300)
except ValueError:checks.append('nonzero_unproven_offset_fails_closed')
else:raise AssertionError('offset')

s=copy.deepcopy(t);s['tracks'][0]['Solo']='True'
try:map_show_time(s,300)
except ValueError:checks.append('solo_semantics_fail_closed')
else:raise AssertionError('solo')
s=copy.deepcopy(t);s['audio_blocks'][2]['StartTimeInAudioStream']='12.5'
check('saved_trim_preserved_without_certifying_rate',map_show_time(s,'244.833333333333')['audio_objects'][0]['unit_rate_source_position_candidate_s']=='12.500000000000')
s=copy.deepcopy(t);s['audio_blocks'].append(copy.deepcopy(s['audio_blocks'][2]));s['audio_blocks'][-1]['GUID']='synthetic-overlap'
check('overlap_returns_all_not_first',len(map_show_time(s,300)['audio_objects'])==2)
check('unbound_ordinal_source_ID_rejected',all(r['source_song_id'] is None for r in t['piecewise_intervals'][4:]))

(p/'reader_test_receipt.json').write_text(json.dumps({'passed':len(checks),'controls':checks,'scope':'boundary/integrity and nominal-rate controls, not measured playback validation'},indent=2));print(len(checks),'passed')
