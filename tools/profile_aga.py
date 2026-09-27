#!/usr/bin/env python3
"""Summarize AGA counters and compare only explicitly matched benchmark runs."""
import argparse,csv,json,math,sys
from pathlib import Path

MATCH_FIELDS=('emulator_sha256','rom_sha256','effective_machine','host_class','route','source_assets_sha256','view_settings','storage_mode')

def counters(path):
    result={}
    for line in path.read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep:result[key]=value if key=='track_history' else int(value)
    return result

def summarize(directory,context):
    for key in MATCH_FIELDS:
        if key not in context or not context[key]:raise ValueError('Missing benchmark context: '+key)
    f=counters(directory/'frame-profile.txt');m=counters(directory/'music-profile.txt')
    samples=sorted(int(row['frame_us']) for row in csv.DictReader((directory/'walk-profile.csv').open()))
    if not samples or f['frames']<=0 or f['elapsed_ms']<=0:raise ValueError('Empty or invalid native profile')
    history=[int(v) for v in m.get('track_history','').split(',') if v]
    return {'context':context,'frame':f,'music':m,'average_fps':f['frames']*1000/f['elapsed_ms'],
            'sample_count':len(samples),'sampled_p95_frame_us':samples[math.ceil(.95*len(samples))-1],
            'adjacent_track_repeats':sum(a==b for a,b in zip(history,history[1:])),
            'note':'CSV samples every tenth frame; sampled p95 is not the percentile of every frame. Quake caps ordinary runs at 72 fps. JIT/max-speed measurements are host-dependent.'}

def compare(baseline,candidate,tolerance=.10):
    for key in MATCH_FIELDS:
        if baseline['context'][key]!=candidate['context'][key]:raise ValueError('Unmatched benchmark: '+key)
    regressions=[]
    for label,old,new in [('sampled_p95_frame_us',baseline['sampled_p95_frame_us'],candidate['sampled_p95_frame_us']),
                          ('worst_frame_us',baseline['frame']['worst_frame_us'],candidate['frame']['worst_frame_us']),
                          ('heap_used_bytes',baseline['frame']['heap_used_bytes'],candidate['frame']['heap_used_bytes'])]:
        if new>old*(1+tolerance):regressions.append(label)
    for group,key in [('music','read_errors'),('frame','audio_late_updates'),('frame','missed_audio_frames')]:
        if candidate[group][key]>baseline[group][key]:regressions.append(key)
    for key in ('surface_overflow_frames','edge_overflow_frames'):
        if candidate['frame'].get(key,0)>0:regressions.append(key)
    if candidate['adjacent_track_repeats']:regressions.append('adjacent_track_repeats')
    return {'passed':not regressions,'regressions':regressions,'tolerance':tolerance,
            'baseline_fps':baseline['average_fps'],'candidate_fps':candidate['average_fps'],
            'note':'A single matched run is a screening gate. Repeat a failing case before selecting or rejecting an optimization.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    r=s.add_parser('report');r.add_argument('directory',type=Path);r.add_argument('--context',type=Path,required=True)
    c=s.add_parser('compare');c.add_argument('baseline',type=Path);c.add_argument('candidate',type=Path);c.add_argument('--tolerance',type=float,default=.10)
    a=p.parse_args()
    try:
        if a.command=='report':result=summarize(a.directory,json.loads(a.context.read_text()))
        else:
            if a.tolerance<0:raise ValueError('Tolerance must be nonnegative')
            result=compare(json.loads(a.baseline.read_text()),json.loads(a.candidate.read_text()),a.tolerance)
        print(json.dumps(result,indent=2));return 1 if result.get('passed') is False else 0
    except (OSError,ValueError,KeyError) as exc:p.exit(2,str(exc)+'\n')
if __name__=='__main__':sys.exit(main())
