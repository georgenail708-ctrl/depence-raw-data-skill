"""Catalog queries; labels prevent source observations becoming validation claims."""
import argparse,json,gzip
from music_query import CLOCK_DOMAINS
from context_query import read_component
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def rows(path):
 with Path(path).open(encoding='utf-8') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 a=s.add_parser('coverage');a.add_argument('--song',required=True);a.add_argument('--data-dir',default=str(BASE/'data'))
 a=s.add_parser('pair-status');a.add_argument('--song',required=True);a.add_argument('--data-dir',default=str(BASE/'data'))
 a=s.add_parser('assets');a.add_argument('--song',required=True)
 a=s.add_parser('row');a.add_argument('--file',required=True);a.add_argument('--song',required=True)
 a=s.add_parser('search');a.add_argument('--text',required=True)
 a=s.add_parser('song');a.add_argument('--song',required=True);a.add_argument('--data-dir',default=str(BASE/'data'))
 x=p.parse_args()
 if x.command in ('coverage','pair-status'):
  d=Path(x.data_dir)
  if x.command=='coverage':
   found=[json.loads(line) for line in gzip.decompress(read_component(d.parent,'data/coverage_matrix_v2.jsonl.gz')).decode().splitlines() if line.strip()]
  else:found=[json.loads(line) for line in read_component(d.parent,'data/music/clock_bridge_v4/pair_status_by_source_id.jsonl').decode().splitlines() if line.strip()]
  selected=[r for r in found if r['source_song_id']==x.song]
  if len(selected)!=1:raise ValueError('Source ID missing or ambiguous')
  result={'classification':'explicit_source_coverage_or_pair_gate_not_global_completion','evidence':selected[0]}
 elif x.command=='song':
  d=Path(x.data_dir);found={}
  for label,file in [('registry_base','registry/canonical_registry_v3.jsonl'),('current_scope','registry/registry_policy_overlay_v4.jsonl'),('current_dmx','dmx/dmx_manifest_v1.jsonl'),('music','music/song_music_catalog.jsonl')]:
   matches=[r for r in rows(d/file) if r.get('source_song_id',r.get('song_id'))==x.song]
   if len(matches)>1:raise ValueError('Ambiguous source ID in '+file)
   found[label]=matches[0] if matches else None
  if found['registry_base'] is None:raise ValueError('Unknown source ID')
  audio_path=d/'music/audio_verification_v3/audio_catalog.jsonl'
  found['audio_byte_header_verification']=[r for r in rows(audio_path) if r.get('source_song_id')==x.song] if audio_path.exists() else {'status':'audio_v3_component_unavailable'}
  association_path=d/'music/audio_verification_v3/audio_record_associations.jsonl'
  found['audio_record_associations']=[r for r in rows(association_path) if r.get('source_song_id')==x.song] if association_path.exists() else {'status':'audio_v3_component_unavailable'}
  gate=[r for r in map(json.loads,read_component(d.parent,'data/music/clock_bridge_v4/pair_status_by_source_id.jsonl').decode().splitlines()) if r['source_song_id']==x.song]
  if len(gate)!=1:raise ValueError('Source pair-readiness row missing or ambiguous')
  found['effective_pair_readiness']=gate[0]
  result={'synchronized_use_allowed':gate[0]['pair_readiness']=='ready','legacy_links':'retrieval candidates only; never a synchronized program/audio pair unless all independent gates pass','clock_domains':CLOCK_DOMAINS,'classification':'joined_evidence_not_global_acceptance','precedence':'current_scope controls accepted Scene absence; current_dmx supersedes registry historical frame evidence; music alignment remains unverified','source_song_id':x.song,'evidence':found}
 elif x.command=='row':
  found=[r for r in rows(x.file) if r.get('source_song_id',r.get('song_id'))==x.song]
  if len(found)!=1:raise ValueError('Source ID missing or ambiguous; do not silently choose')
  result={'classification':'source_audit_record; retain individual evidence statuses','row':found[0]}
 else:
  entries=json.loads((BASE/'catalog/archive_entries.json').read_text())['entries']
  if x.command=='assets':
   # Exact source-ID prefix, not a substring which can join different songs.
   found=[e for e in entries if e['name'].startswith('01_数据集_songs/'+x.song+'.') or e['name']=='01_数据集_songs/qa/'+x.song+'.qa.json']
  else:found=[e for e in entries if x.text.casefold() in e['name'].casefold()]
  result={'classification':'raw_archive_locator; filename match is not content identity','count':len(found),'entries':found}
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except FileNotFoundError as e:raise SystemExit('Missing component/input: '+str(e.filename)+'. Restore data/ from the released bundle or provide its location; catalog locators remain usable without embedded components.') from None
