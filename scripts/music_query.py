"""Load music evidence only after checking catalog, raw MIDI and event-file hashes."""
import argparse,gzip,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
CLOCK_DOMAINS={'midi':'Each MIDI retains its own tick/tempo-derived time origin; reference and transcription are distinct timelines.','dmx':'Frame index belongs to the supplied block, not automatically a project/global audio origin.','saved_offsets':'Saved offsets and any catalog formula are source/derivation claims, not verified transforms. Local-block vs project origin and sign/basis remain unverified.','joining_rule':'Do not apply offsets or frame/FPS arithmetic as established correspondence. Verify clock origins, sign, rate, duration coverage and source identity first; report mismatches without extrapolation.'}
def load(song,base=BASE):
 base=Path(base).resolve();manifest=json.loads((base/'catalog/components.json').read_text())
 if manifest.get('status')!='frozen':raise ValueError('Unfrozen component inventory')
 bypath={r['path']:r for r in manifest['files']}
 def checked(rel):
  p=(base/rel).resolve()
  if not p.is_relative_to(base) or rel not in bypath:raise ValueError('Unlisted/outside component')
  b=p.read_bytes();m=bypath[rel]
  if len(b)!=m['size'] or hashlib.sha256(b).hexdigest()!=m['sha256']:raise ValueError('Music component hash mismatch: '+rel)
  return b
 rows=[json.loads(x) for x in checked('data/music/song_music_catalog.jsonl').decode().splitlines() if x.strip()]
 found=[r for r in rows if r['source_song_id']==song]
 if len(found)!=1:raise ValueError('Music source ID missing or ambiguous')
 row=found[0]
 def source(d):
  if not d:return None
  raw=checked('data/music/'+d['raw_file'])
  if hashlib.sha256(raw).hexdigest()!=d['source_sha256']:raise ValueError('Source MIDI hash mismatch')
  return json.loads(gzip.decompress(checked('data/music/'+d['events_file'])))
 out={'clock_domains':CLOCK_DOMAINS,'classification':'raw_MIDI_events_and_derived_music; audio_identity_and_alignment_unverified','catalog':row,'reference_events':source(row.get('record_reference_midi') or row.get('reference_midi')),'transcription_events':source(row.get('transcribed_midi'))}
 if song=='glimmers_end':out['source_record_music_without_packaged_midi']=json.loads(gzip.decompress(checked('data/music/glimmers_end_record_music.json.gz')))
 return out
def page(song,source='reference',kind='events',cursor=0,limit=50,base=BASE):
 if cursor<0 or not 1<=limit<=1000:raise ValueError('Cursor/limit outside bounds')
 full=load(song,base)
 key={'reference':'reference_events','transcription':'transcription_events','record-only':'source_record_music_without_packaged_midi'}[source]
 data=full.get(key)
 if data is None:raise ValueError('Requested source is absent; do not substitute another MIDI')
 if source=='record-only':data=data['music']
 array_key={'events':'all_track_events','notes':'notes'}[kind]
 if array_key not in data:raise ValueError('Requested ordered event/notes collection not present')
 items=data[array_key]
 if not isinstance(items,list) or cursor>len(items):raise ValueError('Invalid collection/cursor')
 end=min(len(items),cursor+limit)
 catalog=full['catalog']
 requested=(catalog.get('record_reference_midi') or catalog.get('reference_midi')) if source=='reference' else catalog.get('transcribed_midi') if source=='transcription' else {'source_song_id':song,'kind':'source_record_music_without_packaged_midi'}
 return {'classification':'verified_source_derived_ordered_records_not_semantic_review','source_song_id':song,'source':source,'collection':array_key,'order':'stored source order; preserve track/order/offset fields, no statistical reduction','cursor':cursor,'end_cursor':end,'total_records':len(items),'next_cursor':None if end==len(items) else end,'eof':end==len(items),'items':[{'absolute_record_index':i,'record':items[i]} for i in range(cursor,end)],'requested_source_identity':requested,'canonical_event_byte_source':full[key].get('source_record') if source=='record-only' else data.get('source'),'provenance_rule':'Shared SHA event storage may name a different original member; requested_source_identity preserves this request. Byte equality is not whole-song identity.','audio_alignment':'unverified','clock_domains':CLOCK_DOMAINS}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default=str(BASE),help='Released bundle root containing catalog/ and data/');p.add_argument('--song',required=True);p.add_argument('--source',choices=['reference','transcription','record-only'],default='reference');p.add_argument('--kind',choices=['events','notes'],default='events');p.add_argument('--cursor',type=int,default=0);p.add_argument('--limit',type=int,default=50);p.add_argument('--all',action='store_true',help='Full programmatic tree; redirect to a file, not a truncated terminal')
 a=p.parse_args()
 try:print(json.dumps(load(a.song,a.base) if a.all else page(a.song,a.source,a.kind,a.cursor,a.limit,a.base),ensure_ascii=False))
 except FileNotFoundError as e:raise SystemExit('Missing music component: '+str(e.filename)+'. Restore data/music and catalog/components.json from the released bundle.') from None
