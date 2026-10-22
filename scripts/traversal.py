"""Resumable exhaustive source coverage ledger. Hash/read/review are different states."""
import argparse,datetime,hashlib,json,zlib
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def jsonl(p):
 with Path(p).open(encoding='utf8') as f:return [json.loads(l) for l in f if l.strip()]
def save(x,p):
 with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def initialize(data_dir,entries):
 d=Path(data_dir);registry=jsonl(d/'registry/canonical_registry_v3.jsonl')
 overlay={x['source_song_id']:x for x in jsonl(d/'registry/registry_policy_overlay_v4.jsonl')}
 music={x['source_song_id']:x for x in jsonl(d/'music/song_music_catalog.jsonl')}
 by={e['name']:e for e in entries};sources=[];ids=set()
 dp=d/'dmx/dmx_manifest_v1.jsonl';dmx={r['song_id']:r for r in jsonl(dp)}
 for r in registry:
  sid=r['source_song_id']
  if sid in ids:raise ValueError('Duplicate source ID')
  ids.add(sid);m=music.get(sid,{})
  names={v['member'] for v in r.get('assets',{}).values() if v.get('member')}
  # Exact metadata joins, not statistics or approximate title joins.
  for key in ['record_reference_midi','reference_midi','transcribed_midi']:
   if m.get(key) and m[key].get('member'):names.add(m[key]['member'])
  audio=m.get('audio_member')
  if isinstance(audio,str):names.add(audio)
  elif isinstance(audio,dict) and audio.get('member',audio.get('name')):names.add(audio.get('member',audio.get('name')))
  # Include filename candidates even when musical identity remains unverified.
  names.update(e['name'] for e in entries if e['name'].startswith('07_音频_全部匹配/'+sid+'.'))
  assets=[]
  for name in sorted(names):
   e=by.get(name)
   if e is None:raise ValueError('Referenced asset missing from safe locator: '+name)
   assets.append({'member':name,'bytes':e['uncompressed_size'],'expected_sha256':e.get('sha256'),'crc32':e['crc32'],'bytes_verified':None,'raw_read':[],'semantic_reviewed':[]})
  derived=[];rec=dmx.get(sid,{}).get('recommended_npz')
  if rec and rec.get('path'):
   parts=Path(rec['path']).parts
   for folder in ('corrected','opaque_restored'):
    if folder in parts:
     rel='/'.join(parts[parts.index(folder):]);path=d/'dmx'/rel
     derived.append({'member':'component:data/dmx/'+rel,'bytes':path.stat().st_size,'expected_sha256':rec['sha256'],'crc32':None,'provenance_kind':'derived_or_restored_component_not_original_archive_member','bytes_verified':None,'raw_read':[],'semantic_reviewed':[]})
     break
  sources.append({'derived_assets':derived,'source_song_id':sid,'group_id':r['group_id'],'selection_status':r.get('selection_status'),'claimed_duplicate_of':r.get('duplicate_of_source_song_id'),'identity':'retain_original_group_not_deduplicated','scene_disposition':overlay.get(sid,{}).get('scene_frame_scope'),'audio_correspondence':'unverified_even_if_member_present','assets':assets})
 linked={a['member'] for s in sources for a in s['assets']}
 supplemental=[{'member':e['name'],'bytes':e['uncompressed_size'],'expected_sha256':e.get('sha256'),'crc32':e['crc32'],'bytes_verified':None,'raw_read':[],'semantic_reviewed':[]} for e in entries if e['name'] not in linked]
 return {'supplemental_assets':supplemental,'schema':'depence.coverage-ledger.v1','source_group_count':len(sources),'status':'initialized_not_read_or_reviewed','coverage_semantics':'Available source byte spans only. Reported reads/reviews are auditable declarations, not proof of comprehension or original source authenticity. Missing frames remain explicit source limitations.','sources':sources}
def covered(spans,size):
 if size==0:return bool(spans)
 end=0
 for x in sorted(spans,key=lambda x:x['start']):
  if x['start']>end:return False
  end=max(end,x['end'])
 return end>=size

def summary(ledger):
 a=[a for s in ledger['sources'] for a in s['assets']+s.get('derived_assets',[])]+ledger.get('supplemental_assets',[])
 unique={}
 for x in a:unique.setdefault(x['member'],[]).append(x)
 return {'unique_members_bytes_verified':sum(any(y['bytes_verified'] is not None for y in v) for v in unique.values()),'unique_members_raw_read_full_reported':sum(any(covered(y['raw_read'],y['bytes']) for y in v) for v in unique.values()),'unique_members_semantic_review_full_reported':sum(any(covered(y['semantic_reviewed'],y['bytes']) for y in v) for v in unique.values()),'unique_original_archive_members':sum(not k.startswith('component:') for k in unique),'unique_derived_components':sum(k.startswith('component:') for k in unique),'source_groups':len(ledger['sources']),'asset_references':len(a),'unique_members':len({x['member'] for x in a}),'bytes_verified':sum(x['bytes_verified'] is not None for x in a),'raw_read_full_reported':sum(covered(x['raw_read'],x['bytes']) for x in a),'semantic_review_full_reported':sum(covered(x['semantic_reviewed'],x['bytes']) for x in a),'accepted_missing_scene_frames':sum(s.get('scene_disposition',{}).get('status')=='accepted_terminal_missing_this_round' for s in ledger['sources'] if s.get('scene_disposition')),'all_available_assets_review_reported':bool(a) and all(covered(x['semantic_reviewed'],x['bytes']) for x in a),'full_project_authenticity_or_audio_alignment':'not_established_by_coverage_ledger'}
def asset(ledger,song,member):
 found=[a for s in ledger['sources'] if s['source_song_id']==song for a in s['assets']+s.get('derived_assets',[]) if a['member']==member]
 if song=='__archive_supplement__':found=[a for a in ledger.get('supplemental_assets',[]) if a['member']==member]
 if len(found)!=1:raise ValueError('Source/member missing or ambiguous')
 return found[0]
def record_window(a,stage,start,end,evidence,note):
 if stage not in ('raw_read','semantic_reviewed') or not (0<=start<end<=a['bytes'] or start==end==a['bytes']==0):raise ValueError('Invalid stage or byte range')
 if not evidence.strip() or not note.strip():raise ValueError('Evidence reference and exact scope note required')
 if a['bytes_verified'] is None:raise ValueError('Verify raw member bytes before recording a read/review')
 if stage=='semantic_reviewed' and not covered(a['raw_read'],end):raise ValueError('Read coverage must precede semantic review to this end offset')
 a[stage].append({'start':start,'end':end,'evidence':evidence,'scope_note':note,'reported_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
def verify_member(a,path):
 h=hashlib.sha256();crc=n=0
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);crc=zlib.crc32(b,crc);n+=len(b)
 if n!=a['bytes'] or (a['crc32'] is not None and f'{crc:08x}'!=a['crc32']) or (a['expected_sha256'] and h.hexdigest()!=a['expected_sha256']):raise ValueError('Raw member verification failed')
 a['bytes_verified']={'sha256':h.hexdigest(),'expected_sha_checked':bool(a['expected_sha256']),'crc32':f'{crc:08x}','bytes':n,'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
 q=s.add_parser('init');q.add_argument('--data-dir',default=str(BASE/'data'));q.add_argument('--out',required=True)
 for name in ['summary','next','record-window','verify-member']:
  q=s.add_parser(name);q.add_argument('--ledger',required=True)
  if name=='next':q.add_argument('--limit',type=int,default=10)
  if name in ['record-window','verify-member']:
   q.add_argument('--song',required=True);q.add_argument('--member',required=True);q.add_argument('--out',required=True)
  if name=='record-window':
   q.add_argument('--stage',choices=['raw_read','semantic_reviewed'],required=True);q.add_argument('--start',type=int,required=True);q.add_argument('--end',type=int,required=True);q.add_argument('--evidence',required=True);q.add_argument('--scope-note',required=True)
  if name=='verify-member':q.add_argument('--path',required=True)
 x=p.parse_args()
 if x.cmd=='init':
  l=initialize(x.data_dir,json.loads((BASE/'catalog/archive_entries.json').read_text())['entries']);save(l,x.out);result=summary(l)
 else:
  l=json.loads(Path(x.ledger).read_text())
  if x.cmd=='summary':result=summary(l)
  elif x.cmd=='next':
   pending=[{'source_song_id':r['source_song_id'],'member':a['member'],'bytes':a['bytes'],'raw_read_full_reported':covered(a['raw_read'],a['bytes']),'semantic_reviewed_windows':a['semantic_reviewed']} for r in l['sources'] for a in r['assets']+r.get('derived_assets',[]) if not covered(a['semantic_reviewed'],a['bytes'])]
   pending.extend({'source_song_id':'__archive_supplement__','member':a['member'],'bytes':a['bytes'],'raw_read_full_reported':covered(a['raw_read'],a['bytes']),'semantic_reviewed_windows':a['semantic_reviewed']} for a in l.get('supplemental_assets',[]) if not covered(a['semantic_reviewed'],a['bytes']))
   result={'remaining_asset_references':len(pending),'shown':pending[:max(0,x.limit)],'pagination_is_navigation_not_full_review':True}
  else:
   a=asset(l,x.song,x.member)
   if x.cmd=='verify-member':verify_member(a,x.path)
   else:record_window(a,x.stage,x.start,x.end,x.evidence,x.scope_note)
   l['status']='available_asset_review_reported_not_authenticity_proof' if summary(l)['all_available_assets_review_reported'] else 'in_progress_reported_coverage'
   save(l,x.out);result=summary(l)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except FileNotFoundError as e:raise SystemExit('Missing component/input: '+str(e.filename)+'. Restore data/ from the released bundle or provide --data-dir; archive-only originals require the listed source parts or authorized Range access.') from None
