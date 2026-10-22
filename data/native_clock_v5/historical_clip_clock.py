"""Source-pinned historical clip base sampling clock, NOT final mixed output.

Implements only normal/parallel time branches established by static source review.
Stateful hold edges and sequential/group remapping are explicit blockers.
No audio identity, track participation, output transforms, or latency is inferred.
"""
import bisect, math
from native_clip_reader import SOURCE_SHA256, get_clip, iter_native_events

def capability(c):
    hold = c.get('hold_mode','none')
    sequential = c.get('fade_group_sequence_mode','parallel') != 'parallel'
    if hold not in ('none','last_frame'):
        support = 'unsupported_hold_mode'
    elif c.get('run_mode','normal') != 'normal':
        support = 'unsupported_run_mode'
    elif sequential:
        support = 'sequential_requires_full_branch_context'
    elif hold != 'none':
        support = 'base_clock_safe_interior_only'
    else:
        support = 'base_clock_full_authored_interval'
    duration = float(c['duration'])
    return {'base_clock_support':support,'clip_id':c['id'],'start_time':c['start_time'],
            'duration':duration,'playback_rate':c.get('playback_rate',1.0),
            'source_duration':c.get('source_duration',0),'run_mode':c.get('run_mode','normal'),
            'hold_mode':hold,'sequence_mode':c.get('fade_group_sequence_mode','parallel'),
            'resize_cycle':c.get('resize_cycle',True),
            'safe_local_interval':[0.0,duration*.75 if hold!='none' else duration] if not sequential else None,
            'safe_interval_end_exclusive':True,
            'hold_edge_requirements':['observed timer interval','hold boundary latch','consumed and covered channel masks'] if hold!='none' else [],
            'final_output_or_audio_pair_certified':False}

def base_source_clock(document, program_id, clip_id, timeline_seconds):
    if document.get('source_sha256') != SOURCE_SHA256:
        raise ValueError('Historical source version mismatch')
    _,_,c = get_clip(document,program_id,clip_id)
    support = capability(c)
    now = float(timeline_seconds)
    if not math.isfinite(now): raise ValueError('Finite timeline time required')
    start, duration = float(c['start_time']),float(c['duration'])
    if not start <= now < start+duration:
        raise ValueError('Outside half-open authored clip interval; no extrapolation or hold assumption')
    if support['base_clock_support'].startswith(('unsupported','sequential')):
        raise ValueError(support['base_clock_support'])
    local = now-start
    if c.get('hold_mode','none')!='none' and local >= .75*duration:
        raise ValueError('Stateful hold edge requires observed runtime state')
    rate = max(.001,float(c.get('playback_rate',1.0) or 1.0))
    declared_source = max(0.0,float(c.get('source_duration',0.0) or 0.0))
    source_duration = declared_source if declared_source>0 else max(0.0,duration*rate)
    end = max(0.0,source_duration-1e-4)
    source = max(0.0,local*rate)
    ts = c['frames_blob']['ts']
    if not ts: raise ValueError('Missing recorded timestamp span')
    low,high = min(ts),max(ts)
    period = high-low
    extended = duration*rate > (declared_source+1e-6 if declared_source>0 else high+.05)
    cycled = bool(c.get('resize_cycle',True)) and extended and period>1e-6 and source>high
    if cycled:
        source = low+((source-low)%period)
    else:
        source = min(source,end)
    source = min(source,end)
    return {'source_sha256':SOURCE_SHA256,'clip_id':clip_id,'timeline_seconds':now,
            'local_seconds':local,'base_source_seconds':source,'authored_rate':rate,
            'authored_resize_cycle_applied':cycled,
            'scope':'base_source_sampling_before_track_selection_and_per_device_output_transforms',
            'final_output_or_audio_pair_certified':False}

def select_native_base_event(document, program_id, clip_id, universe, timeline_seconds):
    clock = base_source_clock(document,program_id,clip_id,timeline_seconds)
    events = [e for e in iter_native_events(document,program_id,clip_id) if e['universe']==universe]
    if not events: raise ValueError('Universe has no native events')
    events.sort(key=lambda e:e['source_recording_time_seconds'])
    times = [e['source_recording_time_seconds'] for e in events]
    if len(times)!=len(set(times)):
        raise ValueError('Duplicate native universe timestamps require producer ordering proof')
    source = clock['base_source_seconds']; i = bisect.bisect_left(times,source)
    if i<=0: idx=0
    elif i>=len(times): idx=len(times)-1
    else: idx=i-1 if source-times[i-1] < times[i]-source else i
    return {**clock,'native_event':events[idx],
            'selection_rule':'producer nearest native timestamp; exact midpoint selects later sample; no interpolated bytes'}
