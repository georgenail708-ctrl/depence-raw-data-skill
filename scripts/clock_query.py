"""Query authored piecewise time facts without manufacturing a synchronized media pair."""
import argparse,importlib.util,json
from pathlib import Path
from context_query import read_component
BASE=Path(__file__).resolve().parents[1]
def query(song,local_seconds=None,nominal_frame=None,base=BASE):
 base=Path(base).resolve()
 if (local_seconds is None)==(nominal_frame is None):raise ValueError('Supply exactly one authored-local time or nominal frame')
 rel='data/music/clock_bridge_v4/timeline_reader.py';read_component(base,rel)
 spec=importlib.util.spec_from_file_location('_verified_clock_reader',base/rel);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 timeline=json.loads(read_component(base,'data/music/clock_bridge_v4/authored_timeline.json'))
 rows=[json.loads(line) for line in read_component(base,'data/music/clock_bridge_v4/pair_status_by_source_id.jsonl').decode().splitlines() if line.strip()]
 gates=[row for row in rows if row['source_song_id']==song]
 if len(gates)!=1:raise ValueError('Source readiness missing/ambiguous')
 mapped=module.map_local_time(timeline,song,local_seconds) if local_seconds is not None else module.map_frame_nominal(timeline,song,nominal_frame)
 return {'classification':'authored_timeline_query_NOT_measured_playback_or_verified_audio_pair','pair_readiness':gates[0],'mapping':mapped,'synchronized_use_allowed':gates[0]['pair_readiness']=='ready' and mapped.get('ready_paired') is True}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--song',required=True);p.add_argument('--base',default=str(BASE));g=p.add_mutually_exclusive_group(required=True);g.add_argument('--local-seconds');g.add_argument('--nominal-frame',type=int);a=p.parse_args();print(json.dumps(query(a.song,a.local_seconds,a.nominal_frame,a.base),ensure_ascii=False))
