"""Evaluate only explicit source-defined DMXT channel intervals, not physical response."""
import argparse,json,math
from pathlib import Path
from context_query import load_context
BASE=Path(__file__).resolve().parents[1]
def classify_definition(definition,channel_index,value):
 channels=definition.get('channels',[])
 if not 0<=channel_index<len(channels):raise ValueError('Channel index outside explicit channel list')
 if value is not None and (type(value)!=int or not 0<=value<=255):raise ValueError('Expected exact byte0..255 or UNKNOWN')
 channel=channels[channel_index];modes=definition.get('channel_modes',{}).get(channel,[]);matches=[];invalid=[]
 for index,mode in enumerate(modes):
  lo=mode.get('dmx_min');hi=mode.get('dmx_max')
  if not isinstance(lo,(int,float)) or not isinstance(hi,(int,float)) or not math.isfinite(lo) or not math.isfinite(hi) or lo>hi:invalid.append(index);continue
  if value is not None and lo<=value<=hi:matches.append({'source_interval_index':index,'source_interval':mode})
 status='UNKNOWN_input' if value is None else 'source_definition_invalid' if invalid else 'no_explicit_interval_table' if not modes else 'overlapping_source_intervals' if len(matches)>1 else 'source_interval_match' if matches else 'uncovered_source_value'
 return {'channel_index0':channel_index,'source_channel_name':channel,'input_byte':value,'input_origin':'caller supplied; not proof of an observed frame','status':status,'source_interval_matches':matches,'invalid_interval_indices':invalid,'all_source_intervals':modes,'function_name':definition.get('function_channel_names',{}).get(channel),'source_default':definition.get('function_channel_defaults',{}).get(channel),'declared_motor_range':definition.get('motor_ranges',{}).get(channel),'fine_name_label':channel.endswith('_fine') if isinstance(channel,str) else None,'byte_order':'not established by channel name alone','physical_action':'Source symbolic interval label only; no ignition, flow, position or visible response is executed or proven.'}
def evaluate(song,fixture_id,channel_index,value,base=BASE):
 context,sha,rel=load_context(song,base)
 if not isinstance(context.get('fixtures'),list):raise ValueError('Not a DMXT context; use XML semantic source query for this project')
 fixtures=[f for f in context['fixtures'] if f.get('id')==fixture_id]
 if len(fixtures)!=1:raise ValueError('Exact fixture ID missing/ambiguous')
 fixture=fixtures[0];defs=[d for d in context['fixture_defs'] if d.get('id')==fixture.get('def_id')]
 if len(defs)!=1:raise ValueError('Fixture definition missing/ambiguous')
 result=classify_definition(defs[0],channel_index,value)
 return {'classification':'deterministic_matching_of_explicit_source_ranges_NOT_hardware_action','source_song_id':song,'context_source_sha256':sha,'normalized_component':rel,'fixture':fixture,'fixture_definition':defs[0],'source_address':{'universe_label':fixture.get('universe'),'channel1':fixture['start_channel']+channel_index if type(fixture.get('start_channel'))==int else None,'global_flat_index':None},'historical_owner_verified':False,'evaluation':result}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--song',required=True);p.add_argument('--fixture',required=True);p.add_argument('--channel-index',type=int,required=True);p.add_argument('--value',type=int);p.add_argument('--base',default=str(BASE));a=p.parse_args();print(json.dumps(evaluate(a.song,a.fixture,a.channel_index,a.value,a.base),ensure_ascii=False))
