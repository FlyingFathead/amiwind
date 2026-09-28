# SPDX-License-Identifier: GPL-3.0-only
"""Host-only original head morph sampling and compact speech envelopes."""
import struct
import wave
import numpy as np

class ActorSkeleton:
    """Shared base animation, with the original female locomotion override.

    The female file has no ordinary idle. Disjoint host-only sample times
    select its walk group without confusing the base animation's time range.
    """
    def __init__(self, base, override=None):
        self.base=base;self.override=override;self.N=base.N;self.events=dict(base.events)
        if override:
            for name in ('walkforward: loop start','walkforward: loop stop'):
                self.events[name]=override.events[name]+10000
    def idle_times(self,count):return self.base.idle_times(count)
    def pose(self,time):
        return self.override.pose(time-10000) if self.override and time>=10000 else self.base.pose(time)


def sample_morph(node, data, N, amount=0., blink=False):
    """Use authored Talk/Blink text keys; relative targets are vertex deltas."""
    base=np.array([v.as_list() for v in node.data.vertices],dtype=float)
    controller=node.controller
    while controller and not isinstance(controller,N.NiGeomMorpherController):
        controller=controller.next_controller
    if controller is None:return base
    morph=controller.data
    if not morph or len(morph.morphs)<2:return base
    events={}
    for block in data.get_global_iterator():
        if isinstance(block,N.NiTextKeyExtraData):
            for key in block.text_keys:
                for line in key.value.decode('cp1252').splitlines():events[line.strip().casefold()]=key.time
    group='blink' if blink else 'talk'
    if group+': start' not in events or group+': stop' not in events:
        raise ValueError('Morph lacks authored '+group+' range')
    lo,hi=events[group+': start'],events[group+': stop']
    if blink:
        peaks=[(key.value,key.time) for target in morph.morphs[1:] for key in target.keys if lo<=key.time<=hi]
        if not peaks:raise ValueError('Blink range has no authored keys')
        time=max(peaks)[1]
    else:time=lo+np.clip(amount,0,1)*(hi-lo)
    reference=np.array([v.as_list() for v in morph.morphs[0].vectors],dtype=float)
    if reference.shape!=base.shape:raise ValueError('Morph vertex count mismatch')
    result=reference.copy()
    for target in morph.morphs[1:]:
        if not len(target.keys):continue
        times=[k.time for k in target.keys];values=[k.value for k in target.keys]
        weight=float(np.interp(time,times,values))
        points=np.array([v.as_list() for v in target.vectors],dtype=float)
        if points.shape!=base.shape:raise ValueError('Morph target vertex count mismatch')
        result+=weight*(points if morph.relative_targets else points-reference)
    if not np.isfinite(result).all():raise ValueError('Non-finite head morph')
    return result


def actor_samples(skeleton):
    """ABI: idle 0..7, talk 8..11, blink 12, walk 13..20."""
    idle,step=skeleton.idle_times(8)
    start=skeleton.events['walkforward: loop start'];stop=skeleton.events['walkforward: loop stop']
    if stop<=start:raise ValueError('Invalid walk range')
    times=np.concatenate((idle,np.repeat(idle[0],5),np.linspace(start,stop,8,endpoint=False)))
    faces=[None]*8+[(v/3,False) for v in range(4)]+[(0,True)]+[None]*8
    return times,faces,step,(stop-start)/8


def envelope(path):
    """Four mouth levels at 25Hz; silence closes the mouth. PCM duration exact."""
    with wave.open(str(path)) as wav:
        rate=wav.getframerate();count=wav.getnframes()
        if wav.getnchannels()!=1 or wav.getsampwidth()!=1 or rate!=11025 or not 0<count<=rate*120:
            raise ValueError('Speech must be mono unsigned 8-bit 11025Hz, <=120s')
        samples=np.frombuffer(wav.readframes(count),np.uint8).astype(float)-128
    bins=(count*25+rate-1)//rate
    rms=np.array([np.sqrt(np.mean(samples[i*rate//25:min(count,(i+1)*rate//25)]**2)) for i in range(bins)])
    peak=max(4,float(np.percentile(rms,95)));levels=np.clip(np.ceil(rms/peak*3),0,3).astype(np.uint8)
    levels[rms<max(1.5,peak*.08)]=0
    return struct.pack('<4sHHI',b'AWL1',25,bins,count)+levels.tobytes()
