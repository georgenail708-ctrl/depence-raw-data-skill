"""Retrieve matched fixture-owned XML features and declared profiles without invented units."""
import argparse,gzip,json,xml.etree.ElementTree as ET
from decimal import Decimal,InvalidOperation
from pathlib import Path
from context_query import load_context,owned_context,read_component
BASE=Path(__file__).resolve().parents[1]
def sample_profile(profile_xml,x):
 root=ET.fromstring(profile_xml);points=[dict(e.attrib) for e in root.findall('./KeyPoints/X')];raw_x=str(x)
 try:
  value=Decimal(raw_x);pairs=[(Decimal(p['x']),Decimal(p['y'])) for p in points]
 except (InvalidOperation,KeyError):raise ValueError('Profile numeric fields invalid')
 if not value.is_finite() or any(not a.is_finite() or not b.is_finite() for a,b in pairs):raise ValueError('Nonfinite profile point')
 result={'source_profile_attrs':dict(root.attrib),'source_points':points,'input_x':raw_x,'physical_units':'not inferred','rendering_engine_equivalence':'unverified'}
 exact=[{'source_point_index':i,'x':points[i]['x'],'y':points[i]['y']} for i,(a,b) in enumerate(pairs) if a==value]
 if exact:return {**result,'status':'exact_source_knot' if len({p['y'] for p in exact})==1 else 'multiple_source_values_at_same_x','matches':exact}
 if root.get('IsSpline')!='False':return {**result,'status':'spline_or_unspecified_interpolation_unavailable','value':None}
 if len(pairs)<2 or any(pairs[i][0]>=pairs[i+1][0] for i in range(len(pairs)-1)):return {**result,'status':'non_strict_or_insufficient_knots_interpolation_unavailable','value':None}
 for i,((a,b),(c,d)) in enumerate(zip(pairs,pairs[1:])):
  if a<value<c:return {**result,'status':'derived_piecewise_linear_between_declared_nonspline_knots','value':str(b+(d-b)*(value-a)/(c-a)),'source_segment_indices':[i,i+1]}
 return {**result,'status':'outside_declared_domain_no_extrapolation','value':None}
def fixture(song,guid,base=BASE):
 context,sha,rel=load_context(song,base);bridge=owned_context(context,base)
 if not bridge or bridge['owned'] is None:raise ValueError('No all-base-fixture-field-matched source XML; do not borrow another project definition')
 owned=bridge['owned']['fixtures'].get(guid)
 if owned is None:raise ValueError('Exact fixture not present in matched XML')
 projection=json.loads(gzip.decompress(read_component(base,'data/device_semantics_v2/complete_semantic_projection.json.gz')))
 if projection['source_sha256']!=bridge['binding']['xml_source_sha256']:raise ValueError('Source XML hash mismatch')
 attrs=projection['attribute_definitions'];objects={};profiles={}
 for obj in projection['fixture_and_physical_objects']:objects.setdefault(obj['attrs'].get('GUID'),[]).append(obj)
 for index,profile in enumerate(projection['profiles']):profiles.setdefault(profile['owner_guid'],[]).append({'source_profile_index':index,**profile})
 sources=[]
 for entry in owned['owned_sources']:
  i=entry['source_occurrence_index'];occ=projection['source_occurrences'][i]
  if occ['owner_guid']!=guid:raise ValueError('Fixture-owned source mismatch')
  features=[]
  for feature in occ['features']:
   links=[x.get('LinkedGUID') for x in feature['linked_objects']]
   features.append({'raw_attrs':projection['feature_definitions'][feature['definition']],'linked_object_references':feature['linked_objects'],'conditions':feature['conditions'],'linked_object_matches':{key:objects.get(key,[]) for key in links},'linked_profiles':{key:profiles.get(key,[]) for key in links},'unresolved_linked_GUIDs':[key for key in links if key not in objects]})
  sources.append({**entry,'features':features,'control_attrs':attrs.get(occ.get('control_definition'),{}),'source_xml_path':occ['path']})
 return {'classification':'exact_fixture_owned_authored_source_semantics_NOT_verified_recorded_physical_action','source_song_id':song,'context_source_sha256':sha,'source_xml_sha256':projection['source_sha256'],'fixture_guid':guid,'raw_fixture_attrs':owned['fixture_attrs'],'normalized_fixture':context['fixtures'][guid],'coordinate_pairing':{'normalized':['pos_x_cm','pos_y_cm','pos_z_cm'],'raw_XML':['PosX','PosZ','PosY'],'status':'all_fixture_base_fields_exact_match','units':'normalized exporter labels cm; independent physical calibration not established'},'sources':sources,'mode_status':owned['mode_status'],'source_definition_precedence':'fixture-owned XML source occurrence supersedes global mode-GUID dictionary for this matched context only','limits':['Stored Slot2 and SlotType are preserved; active bit width/coarse-fine order not inferred.','Raw min/max,Invert,LogicalMin/Max,Value_Type and conditions are declarations; no undocumented engine formula is applied.','Physical object settings are authored parameters, not observed pressures/heights/angles or proven dynamics.','Historical render patch and precise audio/capture synchronization remain separate unresolved bindings.']}
def profile(song,guid,profile_index,x,base=BASE):
 f=fixture(song,guid,base);matches=[]
 for source in f['sources']:
  for feature in source['features']:
   for profiles in feature['linked_profiles'].values():
    matches.extend(p for p in profiles if p['source_profile_index']==profile_index)
 if not matches:raise ValueError('Profile is not linked by the selected fixture-owned feature')
 unique={p['xml'] for p in matches}
 if len(unique)!=1:raise ValueError('Conflicting profile content for occurrence index')
 return {'source_xml_sha256':f['source_xml_sha256'],'source_song_id':song,'fixture_guid':guid,'source_profile_index':profile_index,'profile_sample':sample_profile(next(iter(unique)),x)}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--song',required=True);p.add_argument('--fixture',required=True);p.add_argument('--base',default=str(BASE));p.add_argument('--out');p.add_argument('--profile-index',type=int);p.add_argument('--x');a=p.parse_args()
 if (a.profile_index is None)!=(a.x is None):raise SystemExit('Supply both --profile-index and --x')
 result=json.dumps(fixture(a.song,a.fixture,a.base) if a.profile_index is None else profile(a.song,a.fixture,a.profile_index,a.x,a.base),ensure_ascii=False)
 if a.out:
  with open(a.out,'x',encoding='utf-8') as f:f.write(result+'\n')
 else:print(result)
