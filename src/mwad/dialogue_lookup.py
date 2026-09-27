# SPDX-License-Identifier: GPL-3.0-only
"""Lossless ordered voice-response index; no runtime dialogue evaluator.

Actor indices apply static identity filters only. A candidate is not permission
for playback: disposition, faction rank, player/cell state, SCVR predicates and
result scripts still need evaluation. Preserve unsupported bytes for auditing.
"""
import struct
from .npc import first, text
from .audit import string, normpath

IDENTITY = {'ONAM':'id', 'RNAM':'race', 'CNAM':'class', 'FNAM':'faction'}
VOICE_TOPICS = ('hello','idle','intruder','thief','hit','attack','flee','alarm')

def response(fields, topic, order):
    data = first(fields, 'DATA')
    if len(data) != 12:
        raise ValueError('Malformed INFO DATA')
    kind, disposition, rank, sex, pc_rank, padding = struct.unpack('<iibbbb', data)
    conditions = []
    for tag, raw in fields:
        if tag == 'SCVR':
            conditions.append({'expression':string(raw), 'raw_hex':raw.hex(), 'operand':None})
        elif tag in ('INTV','FLTV'):
            if len(raw)!=4 or not conditions or conditions[-1]['operand'] is not None:
                raise ValueError('Unpaired INFO condition operand')
            value = struct.unpack('<i' if tag=='INTV' else '<f',raw)[0]
            conditions[-1]['operand'] = {'type':tag,'value':value,'raw_hex':raw.hex()}
    if any(c['operand'] is None for c in conditions):
        raise ValueError('INFO condition missing operand')
    script = text(fields,'BNAM')
    executable = any(line.split(';',1)[0].strip() for line in script.splitlines())
    return {'id':text(fields,'INAM'), 'topic':topic, 'file_order':order,
            'previous':text(fields,'PNAM'), 'next':text(fields,'NNAM'),
            'type':kind, 'disposition_min':disposition, 'npc_rank_min':rank,
            'sex':sex, 'player_rank_min':pc_rank,
            'identity':{key:text(fields,tag) for tag,key in IDENTITY.items()},
            'cell':text(fields,'ANAM'), 'player_faction':text(fields,'DNAM'),
            'sound':normpath(text(fields,'SNAM')), 'text':text(fields,'NAME'),
            'conditions':conditions, 'result_script':script,
            'has_executable_result':executable, 'deleted':any(k=='DELE' for k,_ in fields),
            'raw_subrecords':[[tag,raw.hex()] for tag,raw in fields]}

def static_candidate(item, actor):
    if item['deleted']:return False
    if item['sex'] not in (-1,int(actor['female'])):return False
    for key,wanted in item['identity'].items():
        actual = str(actor.get(key,''))
        if key=='faction' and wanted.casefold()=='ffff':
            if actual:return False
        elif wanted and wanted.casefold()!=actual.casefold():return False
    return True

def build_lookup(topics, actors):
    entries=[];by_topic={};seen=set()
    for topic in VOICE_TOPICS:
        ids=[]
        for order, fields in enumerate(topics.get(topic,())):
            item=response(fields,topic,order)
            key=(topic,item['id'])
            if key in seen:raise ValueError('Duplicate INFO identifier')
            seen.add(key);ids.append(len(entries));entries.append(item)
        by_topic[topic]=ids
    index={}
    for actor in actors:
        index[actor['id']]={'identity':{k:actor.get(k,'') for k in ('id','race','class','faction','female')},
            'topics':{topic:[i for i in indices if static_candidate(entries[i],actor)] for topic,indices in by_topic.items()}}
    return {'format':'AmiWind dialogue lookup study','version':1,
            'scope':'base master file order; static candidates only, not eligible playback; no mod merge',
            'responses':entries, 'topics':by_topic, 'actors':index}
