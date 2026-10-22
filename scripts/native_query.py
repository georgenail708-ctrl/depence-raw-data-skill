"""Version-explicit historical native events and conditional base clock; never current pairing."""
import argparse,importlib.util,json,sys
from pathlib import Path
from context_query import read_component
BASE=Path(__file__).resolve().parents[1]
PREFIX='data/native_clock_v5/'
def module(base,name):
 path=PREFIX+name+'.py';read_component(base,path)
 spec=importlib.util.spec_from_file_location(name,Path(base)/path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def query(source_sha,command,program=None,clip=None,start=0,limit=100,seconds=None,universe=None,base=BASE):
 base=Path(base);reader=module(base,'native_clip_reader')
 if source_sha!=reader.SOURCE_SHA256:raise ValueError('Explicit source version does not match this historical component; never substitute for current source')
 payload=read_component(base,PREFIX+'historical_water_native_clips.json.gz')
 import hashlib
 d=reader.load(base/PREFIX/'historical_water_native_clips.json.gz',hashlib.sha256(payload).hexdigest(),source_sha)
 if type(start)is not int or start<0 or type(limit)is not int or not 1<=limit<=200:raise ValueError('Nonnegative cursor and limit1..200 required')
 out={'source_sha256':source_sha,'classification':'separate_historical_version_not_current_source','current_source_restored':False,'audio_pair_certified':False}
 if command=='clips':
  rows=[{'program_id':p['id'],'track_id':t.get('id'),'clip':{k:v for k,v in c.items() if k!='frames_blob'},'native_event_count':c['frames_blob'].get('n')} for p in d['programs'] for t in p['tracks'] for c in t['clips']]
 elif command=='events':
  import itertools
  _,_,c=reader.get_clip(d,program,clip);total=c['frames_blob']['n']
  if start>total:raise ValueError('Cursor beyond EOF')
  end=min(total,start+limit)
  rows=[{**r,'data':list(r['data'])} for r in itertools.islice(reader.iter_native_events(d,program,clip),start,end)]
  if len(rows)!=end-start:raise ValueError('Native sequence shorter than declared')
  out.update({'items':rows,'index_range':[start,end],'next_index':end,'total_items':total,'eof':end==total,'coverage':'Only returned original event range; no interpolation or implied prior review.'});return out
 elif command=='clock':
  clock=module(base,'historical_clip_clock')
  if seconds is None:raise ValueError('Timeline seconds required')
  if universe is None:out['mapping']=clock.base_source_clock(d,program,clip,seconds)
  else:
   r=clock.select_native_base_event(d,program,clip,universe,seconds);r['native_event']['data']=list(r['native_event']['data']);out['mapping']=r
  return out
 else:raise ValueError('Unknown native query')
 if start>len(rows):raise ValueError('Cursor beyond EOF')
 end=min(len(rows),start+limit);out.update({'items':rows[start:end],'index_range':[start,end],'next_index':end,'total_items':len(rows),'eof':end==len(rows),'coverage':'Only returned ordered range; EOF does not prove prior ranges read.'});return out
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['clips','events','clock']);p.add_argument('--source-sha',required=True);p.add_argument('--program');p.add_argument('--clip');p.add_argument('--start',type=int,default=0);p.add_argument('--limit',type=int,default=100);p.add_argument('--seconds',type=float);p.add_argument('--universe',type=int);p.add_argument('--base',default=str(BASE));p.add_argument('--out');a=p.parse_args();r=query(a.source_sha,a.command,a.program,a.clip,a.start,a.limit,a.seconds,a.universe,Path(a.base));s=json.dumps(r,ensure_ascii=False,indent=2)
 if a.out:
  with open(a.out,'x',encoding='utf8') as f:f.write(s+'\n')
 else:print(s)
if __name__=='__main__':main()
