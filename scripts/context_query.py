"""Retrieve exact normalized context fields without asserting historical ownership."""
import argparse,gzip,hashlib,json,io
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def load_context(song,base=BASE):
 base=Path(base).resolve()
 inventory=json.loads((base/'catalog/components.json').read_text())
 if inventory.get('status')!='frozen':raise ValueError('Unfrozen inventory')
 files={r['path']:r for r in inventory['files']}
 def checked(rel):
  p=(base/rel).resolve()
  if rel not in files or not p.is_relative_to(base):raise ValueError('Unlisted/outside component')
  b=p.read_bytes();m=files[rel]
  if len(b)!=m['size'] or hashlib.sha256(b).hexdigest()!=m['sha256']:raise ValueError('Context component hash mismatch')
  return b
 rows=[json.loads(x) for x in checked('data/registry/canonical_registry_v3.jsonl').decode().splitlines() if x.strip()]
 matches=[r for r in rows if r['source_song_id']==song]
 if len(matches)!=1:raise ValueError('Unknown/ambiguous source ID')
 evidence=matches[0].get('context_evidence') or {};sha=evidence.get('member_sha256')
 if not sha:raise ValueError('Source context absent; do not substitute alias context')
 rel='data/registry/normalized_contexts/'+sha+'.json.gz'
 context=json.loads(gzip.decompress(checked(rel)))
 if context['source_sha256']!=sha:raise ValueError('Context source hash mismatch')
 return context,sha,rel
def read_component(base,rel):
 base=Path(base).resolve();inventory=json.loads((base/'catalog/components.json').read_text())
 if inventory.get('status')!='frozen':raise ValueError('Unfrozen inventory')
 bypath={r['path']:r for r in inventory['files']}
 if rel not in bypath:raise ValueError('Unlisted component')
 p=(base/rel).resolve()
 if not p.is_relative_to(base):raise ValueError('Component outside bundle')
 b=p.read_bytes();entry=bypath[rel]
 if len(b)!=entry['size'] or hashlib.sha256(b).hexdigest()!=entry['sha256']:raise ValueError('Component hash mismatch')
 return b

def owned_context(context,base=BASE):
 rel='data/device_semantics_v2/context_xml_bindings.jsonl.gz'
 inventory=json.loads((Path(base)/'catalog/components.json').read_text())
 if rel not in {r['path'] for r in inventory['files']}:return None
 matches=[]
 with gzip.GzipFile(fileobj=io.BytesIO(read_component(base,rel))) as source:
  for line in source:
   row=json.loads(line)
   if row['context_source_sha256']==context['source_sha256']:matches.append(row)
 if len(matches)!=1:raise ValueError('Missing/ambiguous context XML binding')
 binding=matches[0]
 if not binding['binding_status'].startswith('all_fixture_'):return {'binding':binding,'owned':None}
 owned=json.loads(gzip.decompress(read_component(base,'data/device_semantics_v2/fixture_owned_modes.json.gz')))
 if owned['source_xml_sha256']!=binding['xml_source_sha256']:raise ValueError('XML source identity mismatch')
 return {'binding':binding,'owned':owned}

def query(song,section="groups",group=None,cursor=0,limit=50,base=BASE):
 if cursor<0 or not 1<=limit<=1000:raise ValueError("Cursor/limit outside bounds")
 context,sha,rel=load_context(song,base)
 is_dmxt=isinstance(context.get("fixtures"),list)
 bridge=owned_context(context,base);owned=bridge.get("owned") if bridge else None
 if group is not None and is_dmxt:
  groups=[g for g in context['fixture_groups'] if group in [g.get('id'),g.get('name')]]
  if len(groups)!=1:raise ValueError('Exact DMXT group missing/ambiguous; use group ID')
  fixtures={f['id']:f for f in context['fixtures']};defs={d['id']:d for d in context['fixture_defs']};items=[]
  for index,guid in enumerate(groups[0].get('fixture_ids',[])):
   fixture=fixtures.get(guid);claims=[{'source_address_key':address,'all_current_claims':owners} for address,owners in context['current_patch_address_claims'].items() if any(owner[0]==guid for owner in owners)]
   items.append({'source_member_index':index,'source_group_order':None,'fixture_guid':guid,'fixture':fixture,'fixture_definition':defs.get(fixture.get('def_id')) if fixture else None,'current_source_address_candidates_including_collisions':claims,'array_address_mapping':'not established from source universe labels'})
 elif group is not None:
  if group not in context['groups']:raise ValueError('Exact group not found')
  items=[]
  for index,(order,guid) in enumerate(context['groups'][group]):
   fixture=context['fixtures'].get(guid)
   owned_fixture=owned['fixtures'].get(guid) if owned else None
   claims=[{'flat_address_key':address,'all_current_claims':owners} for address,owners in context['current_patch_address_claims'].items() if any(owner[0]==guid for owner in owners)]
   mode_slots=context['modes'].get(fixture.get('mode_guid')) if fixture else None
   legacy_mode_slots=mode_slots
   if owned_fixture is not None:
    mode_slots=[{'name':x['source_attrs'].get('Name'),'slot1':x['source_attrs'].get('Slot1'),'slot2':x['source_attrs'].get('Slot2'),'slot_type':x['source_attrs'].get('SlotType'),'virtual':x['source_attrs'].get('IsVirtualSource')=='True','parameter':x['source_attrs'].get('Parameter'),'source_occurrence_index':x['source_occurrence_index'],'source_attrs':x['source_attrs'],'secondary_slot_active_and_byte_order':x['secondary_slot_active_and_byte_order']} for x in owned_fixture['owned_sources']]
    claims=[{'flat_address_key':address,'all_current_claims':[[c['fixture_guid'],c['slot1'],c['source_name']] for c in owners]} for address,owners in owned['current_primary_address_claims'].items() if any(c['fixture_guid']==guid for c in owners)]
   items.append({'source_member_index':index,'source_group_order':order,'fixture_guid':guid,'fixture':fixture,'mode_slots':mode_slots,'legacy_global_mode_slots':legacy_mode_slots,'mode_evidence':'exact_fixture_owned_XML' if owned_fixture is not None else 'global_mode_GUID_only_instance_overrides_not_verified','current_slot_start_candidates_including_collisions':claims})
 else:
  actual_section={'groups':'fixture_groups','modes':'fixture_defs'}.get(section,section) if is_dmxt else section
  if section=='owned_modes':
   if owned is None:raise ValueError('No matched fixture-owned XML source for this context')
   value=owned['fixtures']
  elif section=='current_patch_address_claims' and owned is not None:value=owned['current_primary_address_claims']
  else:value=context[actual_section]
  items=[{'key':key,'value':value} for key,value in value.items()] if isinstance(value,dict) else [{'source_index':index,'value':item} for index,item in enumerate(value)]
 if cursor>len(items):raise ValueError('Cursor exceeds collection')
 end=min(len(items),cursor+limit)
 return {'classification':('legacy_global_mode_GUID_projection_not_effective_instance_semantics' if section=='modes' and group is None and not is_dmxt else 'source_context_fields_and_current_patch_candidates_not_historical_control_ownership'),'effective_mode_route':('Use section owned_modes or exact group for source-owned repaired definitions' if owned is not None else 'No matched instance XML; global mode GUID values are source claims, not proven instance semantics'),'xml_semantic_binding':({'status':bridge['binding']['binding_status'],'context_source_sha256':sha,'xml_source_sha256':bridge['binding'].get('xml_source_sha256'),'matched_fixture_count':len(bridge['binding'].get('matched_fixture_GUIDs',[])),'full_binding_component':'data/device_semantics_v2/context_xml_bindings.jsonl.gz'} if bridge else None),'context_schema':context.get('schema'),'source_song_id':song,'source_sha256':sha,'normalized_component':rel,'section':section,'exact_group':group,'cursor':cursor,'end_cursor':end,'next_cursor':None if end==len(items) else end,'eof':end==len(items),'total_records':len(items),'items':items[cursor:end],'effective_convention':{'array_channel_ids':('Source DMXT universe labels; global flat capture mapping is not established.' if is_dmxt else 'Flat captured byte indices; current patch candidates do not establish historical fixture ownership.'),'historical_owner_verified':False,'sequential_source_table_authoritative':False},'claim_conflict':{'source_channel_id_semantics':'Preserved supplier/historical claim, NOT accepted mapping of OSS/frame IDs. Current explicit physical slot candidates supersede sequential attribution, while historical owner remains unknown.'},'source_conventions':{k:context.get(k) for k in ['address_convention','rotation_units_and_axis_order','source_channel_id_semantics','render_time_patch_verified','address_domain','coordinate_units']},'limits':['Position fields retain source pos_*_cm labels and strings; do not infer audience left/right or calibrated world axes.','Slot starts are candidates, not proven widths/fine ownership or render-time patch. All colliding claims are retained.','Group order is saved membership order, not a derived spatial or artistic order.','Raw DMX 0,1 and UNKNOWN are distinct. No channel-to-height/angle/flow conversion is inferred.']}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default=str(BASE));p.add_argument('--song',required=True);p.add_argument('--section',choices=['groups','fixtures','modes','current_patch_address_claims','fixture_defs','fixture_groups','splines','owned_modes'],default='groups');p.add_argument('--group');p.add_argument('--cursor',type=int,default=0);p.add_argument('--limit',type=int,default=50);p.add_argument('--out');a=p.parse_args()
 try:
  result=query(a.song,a.section,a.group,a.cursor,a.limit,a.base);encoded=json.dumps(result,ensure_ascii=False)
  if a.out:
   with open(a.out,'x',encoding='utf-8') as f:f.write(encoded+'\n')
  else:print(encoded)
 except FileNotFoundError as e:raise SystemExit('Missing context component: '+str(e.filename)+'. Restore registry and catalog components from the released bundle.') from None
