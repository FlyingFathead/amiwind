# SPDX-License-Identifier: GPL-3.0-only
"""Ordered TES3 NPC/outfit inspection for the bounded actor conversion study."""
import random
import struct
from .audit import records, subrecords, string, cell_data

PART_NAMES = ('Head','Hair','Neck','Chest','Groin','Groin','Right Hand','Left Hand',
              'Right Wrist','Left Wrist','Shield Bone','Right Forearm','Left Forearm',
              'Right Upper Arm','Left Upper Arm','Right Foot','Left Foot','Right Ankle',
              'Left Ankle','Right Knee','Left Knee','Right Upper Leg','Left Upper Leg',
              'Right Clavicle','Left Clavicle','Weapon Bone','Tail')
BODY_SLOTS = {2:(2,),3:(3,),4:(4,),5:(6,7),6:(8,9),7:(11,12),8:(13,14),9:(15,16),
              10:(17,18),11:(19,20),12:(21,22),13:(23,24),14:(26,)}

def first(fields, tag, default=b''):
    return next((v for k,v in fields if k==tag),default)

def text(fields, tag):
    return string(first(fields,tag))

def load_master(path):
    kinds={k:{} for k in ('NPC_','RACE','BODY','CLOT','ARMO','LEVI','WEAP','GMST')}
    cells=[];topics={};topic=None
    for tag,flags,raw in records(path.read_bytes()):
        if tag in kinds:
            fields=list(subrecords(raw));identifier=text(fields,'NAME').casefold()
            if flags & 0x20 or first(fields,'DELE'):continue
            kinds[tag][identifier]=fields
        elif tag=='CELL':
            cell=cell_data(list(subrecords(raw)))
            if not cell['flags']&1:cells.append(cell)
        elif tag=='DIAL':
            topic=text(list(subrecords(raw)),'NAME').casefold();topics.setdefault(topic,[])
        elif tag=='INFO' and topic is not None:
            topics[topic].append(list(subrecords(raw)))
    return kinds,cells,topics

def behavior_record(fields, scale=0.25):
    """Preserve ordered authored packages; decode wandering for future routes.

    AIDT has a uint16 Hello, three byte ratings, three padding bytes and
    uint32 services. AI_W has two int16s followed by ten bytes. No engine
    implementation is copied; this is an independent format reader.
    """
    raw=first(fields,'AIDT')
    if len(raw)!=12:raise ValueError('Malformed NPC AIDT')
    hello,fight,flee,alarm,services=struct.unpack('<HBBB3xI',raw)
    packages=[]
    for tag,raw in fields:
        if tag not in ('AI_W','AI_T','AI_F','AI_E','AI_A','CNDT'):continue
        item={'tag':tag,'raw_hex':raw.hex()}
        if tag=='AI_W':
            if len(raw)!=14:raise ValueError('Malformed NPC AI_W')
            distance,duration,hour,*tail=struct.unpack('<hh10B',raw)
            item.update(distance=distance,scaled_distance=distance*scale,
                        duration_hours=duration,time_of_day=hour,
                        idle_weights=tail[:8],repeat=bool(tail[8]))
        packages.append(item)
    return {'hello':hello,'fight':fight,'flee':flee,'alarm':alarm,
            'services':services,'packages':packages,'runtime_wandering':False}

def greeting_settings(kinds, behavior, scale=0.25):
    def value(name, tag, fmt):
        raw=first(kinds['GMST'][name.casefold()],tag)
        if len(raw)!=4:raise ValueError('Malformed greeting setting '+name)
        return struct.unpack(fmt,raw)[0]
    radius=behavior['hello']*value('iGreetDistanceMultiplier','INTV','<i')*scale
    reset=value('fGreetDistanceReset','FLTV','<f')*scale
    duration=value('iGreetDuration','INTV','<i')
    if not 0<=radius<=4096 or not radius<reset<=8192 or not 0<duration<=30:
        raise ValueError('Unsupported greeting settings')
    return {'distance':radius,'reset_distance':reset,'duration':duration,
            'poll_seconds':0.25,'sustained_polls':2,'global_cooldown_seconds':8}

def outfit(kinds, actor_id, seed=0):
    """One deterministic humanoid appearance, no inventory simulation.

    Female equipment uses CNAM when supplied, otherwise its male BNAM. Skin
    parts prefer the actor's sex, with male parts as the source-data fallback.
    """
    npc=kinds['NPC_'][actor_id.casefold()];female=bool(struct.unpack('<I',first(npc,'FLAG'))[0]&1)
    race=text(npc,'RNAM').casefold();race_data=first(kinds['RACE'][race],'RADT')
    height,fheight,weight,fweight,flags=struct.unpack_from('<4fI',race_data,len(race_data)-20)
    if female:height,weight=fheight,fweight
    if flags&2:raise ValueError('Beast skeletons are outside this checkpoint')
    if not .5<=height<=2 or not .5<=weight<=2:raise ValueError('Unsupported race proportions')
    selected={};priority={};equipment=[];rng=random.Random(seed)
    for identifier,body in kinds['BODY'].items():
        bydt=first(body,'BYDT')
        if len(bydt)!=4:raise ValueError('Malformed body descriptor')
        part,vampire,bflags,kind=bydt
        if kind or vampire or (bflags&1 and not female) or identifier.endswith('.1st') or text(body,'FNAM').casefold()!=race:continue
        skin_rank=1 if bool(bflags&1)==female else .5
        for slot in BODY_SLOTS.get(part,()):
            if skin_rank>=priority.get(slot,0):selected[slot]=identifier;priority[slot]=skin_rank
    for slot,tag in ((0,'BNAM'),(1,'KNAM')):
        identifier=text(npc,tag).casefold()
        if identifier:selected[slot]=identifier;priority[slot]=1
    level=struct.unpack_from('<h',first(npc,'NPDT'))[0]
    def resolve(identifier,stack=()):
        key=identifier.casefold()
        if key not in kinds['LEVI']:return key
        if key in stack or len(stack)>8:raise ValueError('Recursive leveled equipment list')
        fields=kinds['LEVI'][key];chance=first(fields,'NNAM',b'\0')[0]
        if rng.randrange(100)<chance:return None
        entries=[];pending=None
        for tag,data in fields:
            if tag=='INAM':pending=string(data).casefold()
            elif tag=='INTV' and pending is not None:
                lev=struct.unpack('<H',data)[0]
                if lev<=level:entries.append((lev,pending))
                pending=None
        if not entries:return None
        if not struct.unpack('<I',first(fields,'DATA'))[0]&1:
            highest=max(n for n,_ in entries);entries=[e for e in entries if e[0]==highest]
        chosen=rng.choice(entries)[1];equipment.append({'list':key,'chosen':chosen})
        return resolve(chosen,(*stack,key))
    worn=[]
    for tag,data in npc:
        if tag!='NPCO':continue
        if len(data)!=36:raise ValueError('Malformed NPC inventory entry')
        if struct.unpack_from('<i',data)[0]==0:continue
        identifier=resolve(string(data[4:]))
        if not identifier:continue
        kind=next((k for k in ('CLOT','ARMO') if identifier in kinds[k]),None)
        if kind:
            fields=kinds[kind][identifier];typ=struct.unpack_from('<i',first(fields,'CTDT' if kind=='CLOT' else 'AODT'))[0]
            # Shields/weapons are not drawn in this unarmed idle study.
            if kind=='ARMO' and typ==8:continue
            rank=(24 if typ==4 else 8 if typ==7 else 2) if kind=='CLOT' else 3
            worn.append((rank,identifier,kind,typ,fields))
    for rank,identifier,kind,typ,fields in sorted(worn):
        slot=None;groups={}
        for tag,data in fields:
            if tag=='INDX':
                if len(data)!=1 or data[0]>=len(PART_NAMES):raise ValueError('Bad equipment part')
                slot=data[0];groups[slot]=None
            elif tag=='BNAM' and slot is not None:groups[slot]=string(data).casefold() or None
            elif tag=='CNAM' and slot is not None and female and string(data):groups[slot]=string(data).casefold()
        if kind=='ARMO' and typ==0:groups.setdefault(1,None)
        if kind=='CLOT' and typ==4:
            for slot in (3,4,5,11,12,13,14,19,20,21,22):groups.setdefault(slot,None)
        if kind=='CLOT' and typ==7:
            for slot in (4,21,22):groups.setdefault(slot,None)
        for slot,body in groups.items():
            if rank>priority.get(slot,0):selected[slot]=body;priority[slot]=rank
        equipment.append({'item':identifier,'kind':kind,'priority':rank})
    parts=[]
    for slot,identifier in sorted(selected.items()):
        if identifier:
            if identifier not in kinds['BODY']:raise ValueError('Missing body part '+identifier)
            parts.append({'slot':slot,'attach':'Head' if slot==1 else PART_NAMES[slot],
                          'filter':PART_NAMES[slot],'id':identifier,
                          'mesh':text(kinds['BODY'][identifier],'MODL')})
    return {'id':actor_id,'name':text(npc,'FNAM'),'race':race,'female':female,
            'class':text(npc,'CNAM'),'faction':text(npc,'ANAM'),'height':height,'weight':weight,
            'parts':parts,'equipment':equipment,'seed':seed,'level':level}

def greeting_fixture(topics, appearance, disposition=50):
    """Pick a generic voice audition, not a full original dialogue evaluator.

    Reject scripts, quest/context tests, faction/rank and location constraints.
    Prefer the highest eligible disposition threshold; keep original file order
    for ties. All production dialogue condition handling remains separate work.
    """
    choices=[]
    allowed={'INAM','PNAM','NNAM','DATA','RNAM','ONAM','CNAM','SNAM','NAME'}
    for fields in topics.get('hello',[]):
        if any(k not in allowed for k,_ in fields):continue
        raw=first(fields,'DATA')
        if len(raw)!=12 or not text(fields,'SNAM'):continue
        typ,disp,rank,gender,pcrank,_=struct.unpack('<iibbbb',raw)
        if typ!=1 or disp>disposition or rank!=-1 or pcrank!=-1:continue
        if gender not in (-1,int(appearance['female'])):continue
        if any(text(fields,k) and text(fields,k).casefold()!=str(appearance[key]).casefold()
               for k,key in [('RNAM','race'),('ONAM','id'),('CNAM','class')]):continue
        choices.append((disp,fields))
    if not choices:raise ValueError('No supported generic greeting for '+appearance['id'])
    best=max(d for d,_ in choices);fields=next(f for d,f in choices if d==best)
    return {'info':text(fields,'INAM'),'voice':text(fields,'SNAM'),
            'text':text(fields,'NAME'),'disposition_fixture':disposition,
            'matched_threshold':best,'mode':'bounded generic voice audition; not full dialogue filtering'}
