#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Source-derived bounded inventory metadata and selected original ground assets.

All converted outputs are private game data. The catalogue contains identities,
names, categories, weights, values and supported actions; missing conversions
disable those actions rather than substitute an unrelated model/icon.
"""
import argparse, hashlib, io, json, math, re, struct, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mwad.esm import records, subrecords, text, first, is_deleted
from mwad.paths import resolve_data_files, child_ci

KINDS={'WEAP':1,'ARMO':2,'CLOT':3,'ALCH':4,'INGR':5,'BOOK':6,'MISC':7,
       'LIGH':7,'APPA':7,'LOCK':7,'PROB':7,'REPA':7}
CLOTHING_SLOTS={0:9,1:7,2:8,3:15,4:11,5:6,6:5,7:10,8:12,9:14}
ROW=512

def safe_text(value,size):
    value=str(value).replace('\\','/').strip()
    if any(ord(c)<32 for c in value):raise ValueError('Control byte in item metadata')
    raw=value.encode('cp1252')
    if len(raw)>=size:raise ValueError('Item metadata exceeds field limit')
    return raw+b'\0'*(size-len(raw))

def script_inert_after_registration(source):
    # A narrow proof, not a script interpreter: initial declarations followed by
    # an unconditional early return when registration has finished.
    source=re.sub(r';[^\n]*','',source).lower()
    source=re.sub(r'^\s*begin\s+[^\n]+','',source)
    source=re.sub(r'^\s*(?:(?:short|long|float)\s+\w+\s*)*','',source)
    return bool(re.match(r'\s*if\s*\(?\s*chargenstate\s*==\s*-1\s*\)?\s*return\s*endif',source))

def effect_cost(effect,mgef,cost_mult):
    # OpenMW 0.51 mwmechanics/spellutil.cpp calcEffectCost, EffectCostMethod::GameEnchantment
    # (no magnitude clamp, no duration offset, no minimum area), then getTotalCost's x1.5 on target.
    ident,_,_,rng,area,duration,low,high=effect
    base,flags=mgef.get(ident,(None,None))
    if base is None:raise ValueError('Enchantment names an unknown magic effect %d'%ident)
    if flags&8:low=high=1                    # NoMagnitude
    if flags&4:duration=1                    # NoDuration
    if not flags&0x1000:duration=max(1,duration)   # not AppliedOnce
    x=.5*(low+high)*.1*base*duration+.05*max(0,area)*base
    x=max(0.,x*cost_mult)
    return x*1.5 if rng==2 else x

def max_charge(enchant,effects,mgef,settings):
    # OpenMW 0.51 spellutil.cpp getEnchantmentCharge: autocalc charge = round(total cost) times
    # iMagicItemCharge{Once,Strike,Use,Const}; otherwise the ENDT charge as authored.
    kind,_,charge,flags=enchant
    if not flags&1:return float(charge)
    total=sum(effect_cost(e,mgef,settings['feffectcostmult']) for e in effects)
    multiplier=settings[('imagicitemchargeonce','imagicitemchargestrike','imagicitemchargeuse','imagicitemchargeconst')[kind]]
    return float(math.floor(total+.5)*multiplier)

def source_items(data):
    result={};enchantments={};scripts={};settings={};initial=[]
    effects={};mgef={};charges={}
    for kind,flags,raw in records(child_ci(data,'Morrowind.esm').read_bytes()):
        if kind not in KINDS and kind not in ('ENCH','SCPT','GMST','NPC_','MGEF'):continue
        fields=list(subrecords(raw))
        if is_deleted(flags,fields):continue
        if kind=='NPC_':
            if text(fields,'NAME').casefold()=='player':
                for tag,entry in fields:
                    if tag=='NPCO':
                        if len(entry)!=36:raise ValueError('Malformed original player inventory')
                        count=struct.unpack_from('<i',entry)[0];identifier=entry[4:].split(b'\0')[0].decode('cp1252').casefold()
                        if count<1:raise ValueError('Unsupported original player restocking inventory')
                        initial.append((identifier,count))
            continue
        if kind=='GMST':
            key=text(fields,'NAME').casefold();value=first(fields,'FLTV') or first(fields,'INTV')
            if len(value)==4:settings[key]=struct.unpack('<f' if first(fields,'FLTV') else '<i',value)[0]
            continue
        if kind=='SCPT':
            header=first(fields,'SCHD');name=header[:32].split(b'\0')[0].decode('cp1252').casefold()
            scripts[name]=text(fields,'SCTX');continue
        if kind=='MGEF':
            index=first(fields,'INDX');medt=first(fields,'MEDT')
            if len(index)==4 and len(medt)>=12:
                _,base,mflags=struct.unpack_from('<ifi',medt);mgef[struct.unpack('<i',index)[0]]=(base,mflags)
            continue
        identifier=text(fields,'NAME').casefold()
        if kind=='ENCH':
            raw=first(fields,'ENDT')
            if len(raw)==16:
                enchantments[identifier]=struct.unpack('<4i',raw)
                effects[identifier]=[struct.unpack('<hbbiiiii',e) for t,e in fields if t=='ENAM' and len(e)==24]
            continue
        name=text(fields,'FNAM') or identifier;subtype=-1;weight=value=None
        tag={'WEAP':'WPDT','ARMO':'AODT','CLOT':'CTDT','ALCH':'ALDT','INGR':'IRDT',
             'BOOK':'BKDT','MISC':'MCDT','LIGH':'LHDT','APPA':'AADT','LOCK':'LKDT','PROB':'PBDT','REPA':'RIDT'}[kind]
        raw=first(fields,tag)
        if kind=='CLOT' and len(raw)==12:subtype,weight,value,_=struct.unpack('<ifHH',raw)
        elif kind=='ARMO' and len(raw)>=24:subtype,weight,value=struct.unpack_from('<ifi',raw)
        elif kind=='WEAP' and len(raw)==32:weight,value,subtype=struct.unpack_from('<fih',raw)
        elif kind in ('BOOK','MISC','INGR','ALCH') and len(raw)>=8:weight,value=struct.unpack_from('<fi',raw)
        elif kind in ('APPA','LOCK','PROB','REPA') and len(raw)>=12:
            # These records have different layouts; preserve their identity but
            # leave unsupported metadata absent until explicitly decoded.
            continue
        else:continue
        if not math.isfinite(weight) or weight<0 or value<0:raise ValueError('Invalid item weight/value '+identifier)
        result[identifier]=dict(id=identifier,name=name,category=KINDS[kind],kind=kind,
            subtype=subtype,weight=weight,value=value,source_model=text(fields,'MODL'),
            source_icon=text(fields,'ITEX'),script=text(fields,'SCRI').casefold(),
            raw=raw,enchantment=text(fields,'ENAM').casefold() if kind in ('CLOT','ARMO','WEAP','BOOK') else '',parts=any(k=='INDX' for k,_ in fields))
    for identifier,enchant in enchantments.items():
        if not 0<=enchant[0]<=3:continue
        try:charges[identifier]=max_charge(enchant,effects[identifier],mgef,settings)
        except (KeyError,ValueError):pass
    return result,enchantments,scripts,settings,initial,charges

def prepare(data_files,id1,selected=(),palette=None,models=True):
    data=resolve_data_files(Path(data_files));id1=Path(id1)
    items,enchantments,scripts,settings,initial,charges=source_items(data);selected=set(s.casefold() for s in selected)
    if not selected:
        # Existing earned opening items plus original player starting clothes.
        # This stages resources only; it does not invent inventory ownership.
        selected={'gold_001','ring_keley','chargen statssheet','bk_a1_1_caiuspackage',
                  'bk_a1_1_directionscaiuscosades','common_shirt_01','common_pants_01','common_shoes_01','steel longsword','steel_shield'}
    palette=bytes(palette if palette is not None else (id1/'gfx/palette.lmp').read_bytes())
    if len(palette)!=768:raise ValueError('Expected installed 256-colour game palette')
    assets=None;report={'rows':len(items),'selected':sorted(selected),'models':{},'icons':{},'held':{}}
    if models:
        import numpy as np
        from PIL import Image
        from npc_geometry import Assets
        from mwad.audit import BSA
        from npc_items import item_model
        from prepare_scenery import nif_reader
        nif=nif_reader()
        assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
    rows=[]
    for identifier,item in sorted(items.items()):
        model=icon='';slots=flags=0
        inert=not item['script'] or script_inert_after_registration(scripts.get(item['script'],''))
        if item['kind']=='CLOT' and item['subtype'] in CLOTHING_SLOTS:
            slot=CLOTHING_SLOTS[item['subtype']]
            slots=(1<<12)|(1<<13) if item['subtype']==8 else 1<<slot
            flags|=1
            # First implemented equipment: accessories with no visible body-part
            # replacement and no constant/cast-on-equip effect. CastWhenUsed is
            # never applied merely by wearing the item.
            enchant=enchantments.get(item['enchantment']) if item['enchantment'] else None
            if item['subtype'] in (8,9) and not item['parts'] and inert and (not item['enchantment'] or (enchant and enchant[0]==2)):flags|=4
        combat=[0,26,*([0]*6),0.,0.,0.,0.,0,0]
        if item['kind']=='WEAP' and item['subtype'] in (0,1,2,3,4,5,6,7,8):
            from prepare_combat import WEAPON_SKILL
            raw=item['raw'];health=struct.unpack_from('<h',raw,10)[0]
            combat=[1+item['subtype'],WEAPON_SKILL[item['subtype']],*raw[22:28],
                    struct.unpack_from('<f',raw,16)[0],struct.unpack_from('<f',raw,12)[0],float(health),0.,0,0]
            slots=1<<16;flags|=1
        elif item['kind']=='ARMO' and item['subtype']==8:
            raw=item['raw'];health,base=struct.unpack_from('<i',raw,12)[0],struct.unpack_from('<i',raw,20)[0]
            limit=settings['ishieldweight']
            cls=0 if item['weight']<=limit*settings['flightmaxmod']+.0005 else 1 if item['weight']<=limit*settings['fmedmaxmod']+.0005 else 2
            combat=[0,26,*([0]*6),0.,0.,float(health),float(base),cls,int(settings['ibasearmorskill'])]
            slots=1<<17;flags|=1
        if item['script']:flags|=8
        if item['enchantment'] and enchantments.get(item['enchantment'],[None])[0]==3:flags|=16
        if models and identifier in selected:
            stem=hashlib.sha256(identifier.encode()).hexdigest()[:16]
            if item['source_model']:
                try:
                    raw=item_model(assets,{'slot':25,'id':identifier,'mesh':item['source_model'],'attach':'','filter':''},palette,nif)
                    model='progs/inv/i'+stem+'.mdl';out=id1/model;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
                    report['models'][identifier]={'path':model,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
                    if inert:flags|=2
                    if inert and not item['enchantment'] and (item['kind']=='WEAP' and item['subtype'] in (0,1,2,3,4,5,6,7,8) or item['kind']=='ARMO' and item['subtype']==8):flags|=4

                except (ValueError,KeyError,OSError) as error:report['held'].setdefault(identifier,{})['model']=str(error)
            if item['source_icon']:
                try:
                    from PIL import Image
                    icon_source='icons/'+item['source_icon'].replace('\\','/')
                    candidates=[str(Path(icon_source).with_suffix('.dds')),icon_source]
                    failures=[]
                    for candidate in candidates:
                        try:
                            image=Image.open(io.BytesIO(assets.read(candidate))).convert('RGBA');break
                        except (KeyError,OSError,ValueError) as error:failures.append(candidate+': '+str(error))
                    else:raise ValueError('; '.join(failures))
                    image=image.resize((32,32),Image.Resampling.NEAREST)
                    palette_image=Image.new('P',(1,1));palette_image.putpalette(list(palette))
                    rgb=Image.new('RGB',(32,32),(0,0,0));rgb.paste(image,mask=image.getchannel('A'))
                    indices=rgb.quantize(palette=palette_image,dither=Image.Dither.NONE).tobytes()
                    icon='gfx/inv/i'+stem+'.awi';out=id1/icon;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b'AWIC'+indices)
                    report['icons'][identifier]={'path':icon,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
                except (ValueError,KeyError,OSError) as error:report['held'].setdefault(identifier,{})['icon']=str(error)
        row=safe_text(identifier,64)+safe_text(item['name'],96)+struct.pack('<iiifII',item['category'],item['subtype'],item['value'],item['weight'],slots,flags)
        row+=safe_text(model,64)+safe_text(icon,64)+safe_text(item['enchantment'],64)+safe_text(item['script'],64)
        # Bytes 496..511 (zero in older catalogues): the enchantment's kind (0 none, else ENDT
        # type + 1: cast once, when strikes, when used, constant) and its maximum charge, so
        # the HUD can show the original charge bar (docs/HUD.md "Weapon and magic boxes").
        enchant=enchantments.get(item['enchantment']) if item['enchantment'] else None
        kind=enchant[0]+1 if enchant and 0<=enchant[0]<=3 and item['enchantment'] in charges else 0
        charge=charges[item['enchantment']] if kind else 0.
        if not (math.isfinite(charge) and 0<=charge<=1000000):raise ValueError('Invalid enchantment charge '+identifier)
        row+=struct.pack('<ii6iffffii',*combat)+struct.pack('<B3xf8x',kind,charge)
        assert len(row)==ROW;rows.append(row)
    out=id1/'inventory/items.awi';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(b'AWI2'+struct.pack('<I',len(rows))+b''.join(rows))
    initial_rows=[]
    for identifier,count in initial:
        item=items.get(identifier)
        if not item:raise ValueError('Original starting item metadata unavailable '+identifier)
        slot=CLOTHING_SLOTS.get(item['subtype'],-1) if item['kind']=='CLOT' else -1
        initial_rows.append(safe_text(identifier,64)+struct.pack('<ii',count,slot))
    (id1/'inventory/initial.awi').write_bytes(b'AWST'+struct.pack('<I',len(initial_rows))+b''.join(initial_rows))
    report['initial_items']=[{'id':identifier,'count':count} for identifier,count in initial]
    report['catalogue_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
    if models:
        # One icon lookup table for the HUD boxes and the inventory (tools/prepare_icons.py):
        # the same referenced closure as the staged inventory resources.
        from prepare_icons import prepare as prepare_icons, hud_settings, ini_colours
        closure={i:{'source_icon':items[i]['source_icon'],'enchanted':bool(items[i]['enchantment'])}
                 for i in sorted(selected) if i in items}
        colours,report['hud_colours']=ini_colours(data)
        report['icon_table']=prepare_icons(assets,id1,closure,palette,colours)
        text_out,report['hud_settings']=hud_settings(settings)
        (id1/'gfx/hud-settings.txt').write_text(text_out,encoding='ascii',newline='\n')
    report['enchanted_items']={i:{'enchantment':items[i]['enchantment'],'kind':enchantments[items[i]['enchantment']][0],
        'max_charge':charges.get(items[i]['enchantment'])} for i in sorted(selected)
        if i in items and items[i]['enchantment'] in enchantments}
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',required=True,type=Path)
    p.add_argument('--id1',required=True,type=Path);p.add_argument('--palette',type=Path)
    p.add_argument('--item',action='append',default=[]);p.add_argument('--report',type=Path)
    a=p.parse_args();report=prepare(a.data_files,a.id1,a.item,a.palette.read_bytes() if a.palette else None)
    text=json.dumps(report,indent=2)+'\n'
    if a.report:a.report.write_text(text,encoding='utf-8',newline='\n')
    else:print(text)
if __name__=='__main__':main()
