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
# Armour type (AODT) -> the engine's slot (aw_inventory.h AW_SLOT_*): helmet, cuirass, left and right pauldron,
# greaves, boots, left and right gauntlet, shield (the left hand), left and right bracer (the gauntlet slots).
ARMOUR_SLOTS={0:0,1:1,2:3,3:4,4:2,5:7,6:5,7:6,8:17,9:5,10:6}
ROW=512
# The weapons the player can hold in the right hand: the melee types 0..8 and, since v0.0.61 (FIRST-PERSON-WEAPONS-56),
# bow 9, crossbow 10 and thrown 11 (held, drawn and shown in both views; their shot waits for ranged combat, the engine
# strikes nothing with them). Arrows and bolts (12, 13) stay carried until the ammunition slot exists. A ranged
# weapon's combat skill is Marksman (the ESM skill index 23), its damage row the record's own (chop = its damage).
HELD_WEAPONS=(0,1,2,3,4,5,6,7,8,9,10,11)
MARKSMAN=23
# The debug torch (test only; the maintainer's preview-stage request, 17 October 2026): one
# catalogue row made from the original torch (LIGH "torch": model, icon, weight, value, light
# radius and colour) whose burn time is LIGHT_INFINITE, the value OpenMW 0.51
# (apps/openmw/mwmechanics/actors.cpp) treats as a light that never runs out. The engine gives it
# once at the census exit while aw_debug_torch is 1 (config/game.cfg). Its slot is the left hand.
DEBUG_TORCH_ID='aw_debug_torch'
DEBUG_TORCH_NAME='Debug torch (test only)'
DEBUG_TORCH_SOURCE='torch'
LIGHT_INFINITE=-1
FLAG_LIGHT=32
FLAG_BEAST_HEAD=128   # EQUIP-ACTION-REGRESSION-62: a Head part: a beast race cannot wear it (sNotifyMessage13)
FLAG_BEAST_FEET=256   # a foot part: a beast race cannot wear it (sNotifyMessage14 armour, 15 clothing)
FLAG_ALCHEMY=64  # ALCHEMY-61: bytes 440..495 hold the alchemy block (tools/prepare_alchemy.py)
SLOT_LEFT=17

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

# EQUIP-ACTION-REGRESSION-62: in the original any carried item with a script can be worn, wielded and dropped; the
# script matters to equipping only when it reads OnPCEquip or sets PCSkipEquip, and to dropping only when it reads
# OnPCDrop (OpenMW 0.51 mwgui/inventorywindow.cpp useItem, mwworld/actionequip.cpp; mwscript/miscextensions.cpp).
# The engine does not run those yet, so only such scripts keep their item from being equipped or dropped. Before
# this, every script that was not the narrow "registration done" form refused both: the census office's dagger
# (chargen dagger, an OnActivate-only script) showed no action at all.
# Only PCSkipEquip refuses: such a script replaces the equipping itself (Sunder and Keening without Wraithguard, the
# Wraithguard of a wrong race). A script that only reads OnPCEquip (the census dagger's tutorial message, the faction
# armour's checks) reacts after the item is worn; the item is worn and that reaction is listed in the stage report
# (equip_reaction_not_run) until carried items' scripts run (MWSCRIPT tracker).
EQUIP_SCRIPT_WORDS=re.compile(r'\bpcskipequip\b')
EQUIP_REACTION_WORDS=re.compile(r'\bonpcequip\b')
DROP_SCRIPT_WORDS=re.compile(r'\bonpcdrop\b')
def equip_refusal(item,source,model,enchantments,may_equip):
    """Why a wearable or wieldable record gets no Equip action, or None when no rule refuses it (then it is a bug)."""
    if not may_equip:return 'its script sets PCSkipEquip, which the engine does not run yet'
    if item['enchantment']:
        enchant=enchantments.get(item['enchantment'])
        if not enchant:return 'its enchantment is not in the masters'
        held=item['kind']=='WEAP' or (item['kind']=='ARMO' and item['subtype']==8)
        if enchant[0] not in ((1,2,3) if held else (2,3)):return 'its enchantment kind %d is not applied when worn'%enchant[0]
    if item['kind']=='ARMO' and item['subtype']!=8 and struct.unpack_from('<i',item['raw'],12)[0]<=0:return 'its armour health is 0'
    if (item['kind']=='WEAP' or (item['kind']=='ARMO' and item['subtype']==8)) and not model:return 'no world model to hold'
    return None

def script_allows(source,words):
    if not source:return True
    if script_inert_after_registration(source):return True
    return not words.search(re.sub(r';[^\n]*','',source).lower())

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
            elif key in ('sskillhandtohand','sweight','svalue','stake'):settings[key]=text(fields,'STRV')
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
        if kind=='LIGH':pass
        elif kind=='CLOT' and len(raw)==12:subtype,weight,value,_=struct.unpack('<ifHH',raw)
        elif kind=='ARMO' and len(raw)>=24:subtype,weight,value=struct.unpack_from('<ifi',raw)
        elif kind=='WEAP' and len(raw)==32:weight,value,subtype=struct.unpack_from('<fih',raw)
        elif kind in ('BOOK','MISC','INGR','ALCH') and len(raw)>=8:weight,value=struct.unpack_from('<fi',raw)
        if kind=='LIGH' and identifier==DEBUG_TORCH_SOURCE and len(raw)==24:
            # LHDT: weight, value, time, radius, colour RGBA, flags. The debug torch is made from the original
            # torch; the torch itself is catalogued below as any carried light.
            weight,value,time,radius=struct.unpack_from('<fiii',raw)
            if not (math.isfinite(weight) and weight>=0 and value>=0 and 1<=radius<=65535):
                raise ValueError('Invalid original torch light record')
            result[DEBUG_TORCH_ID]=dict(id=DEBUG_TORCH_ID,name=DEBUG_TORCH_NAME,category=KINDS[kind],kind=kind,
                subtype=radius,weight=weight,value=value,source_model=text(fields,'MODL'),
                source_icon=text(fields,'ITEX'),script='',raw=raw,enchantment='',parts=False,
                light=dict(source=identifier,time=LIGHT_INFINITE,source_time=time,radius=radius,colour=list(raw[16:19]),
                           flags=struct.unpack_from('<I',raw,20)[0]))
        if kind=='LIGH':
            if len(raw)!=24:continue
            # A carried light (LHDT flag 2, "can carry"): weight, value, burn time, radius, colour, as the torch
            # above. A burn time below 1 is a light that never runs out (OpenMW: time -1). Fixed lights stay scenery.
            weight,value,time,radius=struct.unpack_from('<fiii',raw)
            if not struct.unpack_from('<I',raw,20)[0]&2:continue
            light=dict(source=identifier,time=LIGHT_INFINITE if time<1 else min(time,1000000),source_time=time,
                       radius=max(1,min(65535,radius)),colour=list(raw[16:19]),flags=struct.unpack_from('<I',raw,20)[0])
            if not (math.isfinite(weight) and weight>=0 and value>=0):raise ValueError('Invalid item weight/value '+identifier)
            result[identifier]=dict(id=identifier,name=name,category=KINDS[kind],kind=kind,subtype=light['radius'],
                weight=weight,value=value,source_model=text(fields,'MODL'),source_icon=text(fields,'ITEX'),
                script=text(fields,'SCRI').casefold(),raw=raw,enchantment='',parts=False,light=light)
            continue
        if kind in ('APPA','LOCK','PROB','REPA') and len(raw)==16:
            # Tools (OpenMW esm3 loadappa/loadlock/loadprob/loadrepa): AADT type, quality, weight, value;
            # LKDT and PBDT weight, value, quality, uses; RIDT weight, value, uses, quality. The subtype is the
            # apparatus type (0 mortar, 1 alembic, 2 calcinator, 3 retort), -1 for the others.
            if kind=='APPA':subtype,_,weight,value=struct.unpack('<iffi',raw)
            else:weight,value=struct.unpack_from('<fi',raw)
        if weight is None:continue          # a record whose data this does not decode
        if not math.isfinite(weight) or weight<0 or value<0:raise ValueError('Invalid item weight/value '+identifier)
        # ALCHEMY-61: an ingredient's four effects, a potion's effects, an apparatus' quality (tools/prepare_alchemy.py
        # block_for), written into the row's bytes 440..495 with catalogue flag 64
        from prepare_alchemy import block_for
        result[identifier]=dict(id=identifier,name=name,category=KINDS[kind],kind=kind,
            subtype=subtype,weight=weight,value=value,source_model=text(fields,'MODL'),
            source_icon=text(fields,'TEXT' if kind=='ALCH' else 'ITEX'),script=text(fields,'SCRI').casefold(),
            raw=raw,enchantment=text(fields,'ENAM').casefold() if kind in ('CLOT','ARMO','WEAP','BOOK') else '',parts=any(k=='INDX' for k,_ in fields),
            part_ids={v[0] for k,v in fields if k=='INDX' and len(v)==1},
            capacity=enchant_capacity(kind,raw),alchemy=block_for(kind,fields))
    for identifier,enchant in enchantments.items():
        if not 0<=enchant[0]<=3:continue
        try:charges[identifier]=max_charge(enchant,effects[identifier],mgef,settings)
        except (KeyError,ValueError):pass
    return result,enchantments,scripts,settings,initial,charges

def enchant_capacity(kind,raw):
    # The record's enchantment points (what an Enchanting service can put on it; OpenMW getEnchantmentPoints): WPDT
    # bytes 20..21, AODT 16..19, CTDT 10..11, BKDT 16..19; 0 for the rest (they cannot be enchanted).
    if kind=='WEAP' and len(raw)>=22:return struct.unpack_from('<H',raw,20)[0]
    if kind=='ARMO' and len(raw)>=20:return max(0,min(0xFFFF,struct.unpack_from('<i',raw,16)[0]))
    if kind=='CLOT' and len(raw)>=12:return struct.unpack_from('<H',raw,10)[0]
    if kind=='BOOK' and len(raw)>=20:return max(0,min(0xFFFF,struct.unpack_from('<i',raw,16)[0]))
    return 0

def mesh_key(path):
    """The key of a world model in the item model table: the original mesh path, lower case, forward slashes
    (the same key for an inventory item now and for a placed object later)."""
    return str(path).replace('\\','/').strip().casefold()

def prepare(data_files,id1,selected=(),palette=None,models=True,jobs=None,model_table=None):
    """MODEL_TABLE: {mesh_key: payload .mdl path} of the item-models stage (prepare_item_models.py), installed
    before this runs; None converts only the selected items' models here (a tool run alone)."""
    data=resolve_data_files(Path(data_files));id1=Path(id1)
    items,enchantments,scripts,settings,initial,charges=source_items(data);selected=set(s.casefold() for s in selected)
    if not selected:
        # Existing earned opening items plus original player starting clothes.
        # This stages resources only; it does not invent inventory ownership.
        selected={'gold_001','ring_keley','chargen statssheet','bk_a1_1_caiuspackage',
                  'bk_a1_1_directionscaiuscosades','common_shirt_01','common_pants_01','common_shoes_01','steel longsword','steel_shield'}
    # The debug torch is given at the census exit: its ground model and icon are always staged.
    if DEBUG_TORCH_ID in items:selected.add(DEBUG_TORCH_ID)
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
    rows=[];inventory_icons={};row_flags={}
    from held_lights import catalogue_flags,held_light,sidecar_path,text as held_text
    # HELD-LIGHT-OWN-MODEL-61: beside each carried light's item model (not the torch's mesh: the torch keeps its own
    # hand, flame and light) its placing on the shield bone and its flames, one small file per model
    torch_mesh=mesh_key(items[DEBUG_TORCH_SOURCE]['source_model']) if DEBUG_TORCH_SOURCE in items else ''
    report['held_lights']={'files':0,'flames':0,'without_flame':0,'torch_mesh':0,'failed':{}}
    held_written=set()
    def held_inert(item):
        # EQUIP-SHARDAXE-REFUSED-61: a weapon or shield whose enchantment does nothing while it is merely held is
        # equipped as any other: none, Cast When Strikes (ENDT type 1) or Cast When Used (type 2). Only a worn item's
        # Constant Effect enchantment becomes an active effect (OpenMW mwmechanics/activespells.cpp); those stay
        # refused until constant effects are applied. 193 weapons (the iron shardaxe among them) were refused.
        # PLAYER-CASTING-59 (v0.0.61): a Constant Effect one (type 3) as well, its effects active while it is worn
        # (aw_cast.c worn_frame); only an enchantment the masters do not have stays refused.
        if not item['enchantment']:return True
        enchant=enchantments.get(item['enchantment'])
        return bool(enchant) and enchant[0] in (1,2,3)
    for identifier,item in sorted(items.items()):
        model=icon='';slots=flags=0
        source=scripts.get(item['script'],'') if item['script'] else ''
        inert=script_allows(source,EQUIP_SCRIPT_WORDS)          # may be equipped (EQUIP-ACTION-REGRESSION-62)
        droppable=script_allows(source,DROP_SCRIPT_WORDS)
        if item['kind']=='CLOT' and item['subtype'] in CLOTHING_SLOTS:
            slot=CLOTHING_SLOTS[item['subtype']]
            slots=(1<<12)|(1<<13) if item['subtype']==8 else 1<<slot
            flags|=1
            # First implemented equipment: accessories with no visible body-part
            # replacement and no constant/cast-on-equip effect. CastWhenUsed is
            # never applied merely by wearing the item.
            # v0.0.61 (PLAYER-CASTING-59): a Constant Effect enchantment too, active while worn (aw_cast.c).
            enchant=enchantments.get(item['enchantment']) if item['enchantment'] else None
            # Clothing with body parts (shirts, pants, shoes, robes, skirts, gloves): the player's assembled body
            # shows them (PLAYER-GEAR-VISUAL-59, tools/prepare_player_parts.py), so they are worn by the same rule
            # (nothing else happens when worn). EQUIP-ACTION-REGRESSION-62: a piece without body parts is worn as
            # well (the original wears it; nothing shows), so every clothing record follows one rule.
            if inert and (not item['enchantment'] or (enchant and enchant[0] in (2,3))):flags|=4
        combat=[0,26,*([0]*6),0.,0.,0.,0.,0,0]
        if item['kind']=='WEAP' and item['subtype'] in HELD_WEAPONS:
            from prepare_combat import WEAPON_SKILL
            raw=item['raw'];health=struct.unpack_from('<h',raw,10)[0]
            combat=[1+item['subtype'],WEAPON_SKILL.get(item['subtype'],MARKSMAN),*raw[22:28],
                    struct.unpack_from('<f',raw,16)[0],struct.unpack_from('<f',raw,12)[0],float(health),0.,0,0]
            slots=1<<16;flags|=1
        elif item['kind']=='ARMO' and item['subtype'] in ARMOUR_SLOTS:
            # Every armour piece in its own slot (OpenMW mwclass/armor.cpp getEquipmentSlots; bracers in the
            # gauntlet slots), its armour class by weight against its type's weight setting (getEquipmentSkill)
            # and its rating and health for the armour rating (npc.cpp getArmorRating). Bytes 488.. keep their
            # names from the shield-only catalogue: the class of any piece, the base armour skill.
            raw=item['raw'];health,base=struct.unpack_from('<i',raw,12)[0],struct.unpack_from('<i',raw,20)[0]
            from prepare_combat import ARMOR_TYPE_GMST
            limit=settings[ARMOR_TYPE_GMST[item['subtype']].casefold()]
            cls=0 if item['weight']<=limit*settings['flightmaxmod']+.0005 else 1 if item['weight']<=limit*settings['fmedmaxmod']+.0005 else 2
            combat=[0,26,*([0]*6),0.,0.,float(health),float(base),cls,int(settings['ibasearmorskill'])]
            slots=1<<ARMOUR_SLOTS[item['subtype']];flags|=1
            # Worn pieces count in combat (rating, hit sound) without a body picture yet (PLAYER-BODY-ALL-ANIMS):
            # equippable when the item does nothing else when worn (no script after registration); since v0.0.61 with
            # a Cast When Used or a Constant Effect enchantment too (PLAYER-CASTING-59, aw_cast.c).
            enchant=enchantments.get(item['enchantment']) if item['enchantment'] else None
            if item['subtype']!=8 and inert and (not item['enchantment'] or (enchant and enchant[0] in (2,3))) and health>0:flags|=4
        if item.get('light'):
            # Equipped like a torch: the left hand (its own slot rules; never a weapon or shield).
            slots=1<<SLOT_LEFT;flags|=1|4|FLAG_LIGHT
        # EQUIP-ACTION-REGRESSION-62: what a beast race cannot wear (OpenMW 0.51 mwclass/armor.cpp and clothing.cpp
        # canBeEquipped): a piece with a Head part (128) or a foot part, left or right (256)
        if item['kind'] in ('ARMO','CLOT') and slots:
            if 0 in item.get('part_ids',()):flags|=FLAG_BEAST_HEAD
            if item.get('part_ids',set())&{15,16}:flags|=FLAG_BEAST_FEET
        if item['script']:flags|=8
        if item['enchantment'] and enchantments.get(item['enchantment'],[None])[0]==3:flags|=16
        if model_table is not None and item['source_model']:
            # Every item's own world model from the item-models stage's table (one file per distinct mesh,
            # keyed by the mesh path): on disk only, loaded when the item lies on the ground (aw_inventory.c inv_model).
            model=model_table.get(mesh_key(item['source_model']),'')
            if model:
                if droppable:flags|=2
                if inert and held_inert(item) and (item['kind']=='WEAP' and item['subtype'] in HELD_WEAPONS or item['kind']=='ARMO' and item['subtype']==8):flags|=4
            else:report['held'].setdefault(identifier,{})['model']='not in the item model table'
            if model and item.get('light') and assets is not None and model not in held_written:
                # TORCH-HIDES-HELM-62: the torch's mesh gets its held file too, so a held torch (the debug torch
                # included) is a held light on the assembled body like every other light, on the carried-left slot;
                # before, it was skipped and the torch drew the old baked torch body without anything worn
                if mesh_key(item['source_model'])==torch_mesh:report['held_lights']['torch_mesh']+=1
                if True:
                    try:
                        from mwad.audit import normpath
                        key=normpath('meshes/'+item['source_model'])
                        held=held_light(assets.read(key),nif,key)
                        out=id1/sidecar_path(model);out.parent.mkdir(parents=True,exist_ok=True)
                        out.write_text(held_text(held),encoding='ascii',newline='\n')
                        held_written.add(model);report['held_lights']['files']+=1
                        report['held_lights']['flames']+=len(held['flames'])
                        report['held_lights']['without_flame']+=not held['flames']
                    except (ValueError,KeyError,OSError) as error:
                        report['held_lights']['failed'][identifier]=str(error)[:200]
        if models and identifier in selected:
            stem=hashlib.sha256(identifier.encode()).hexdigest()[:16]
            if model_table is None and item['source_model']:
                # Without the item-models stage (a tool run alone): the selected items' models, as before.
                try:
                    raw=item_model(assets,{'slot':25,'id':identifier,'mesh':item['source_model'],'attach':'','filter':''},palette,nif)
                    model='progs/inv/i'+stem+'.mdl';out=id1/model;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
                    report['models'][identifier]={'path':model,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
                    if droppable:flags|=2
                    if inert and held_inert(item) and (item['kind']=='WEAP' and item['subtype'] in HELD_WEAPONS or item['kind']=='ARMO' and item['subtype']==8):flags|=4
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
        # Every catalogue item can be owned (pickup, reward, grant): its inventory icon (UI-ICONS-INVENTORY-42).
        if item['source_icon']:inventory_icons[identifier]={'source_icon':item['source_icon'],
            'enchanted':bool(item['enchantment']),'equippable':bool(flags&1)}
        if item.get('alchemy'):flags|=FLAG_ALCHEMY
        row_flags[identifier]=flags
        # EQUIP-ACTION-REGRESSION-62: every wearable or wieldable record of the game is checked here: one that cannot
        # be equipped is listed with its named reason, and one refused without a known reason stops the stage.
        if flags&1 and not flags&4:
            reason=equip_refusal(item,source,model,enchantments,inert)
            report.setdefault('equip_refused',{})[identifier]=reason
            if reason is None:raise ValueError('EQUIP-ACTION-REGRESSION-62: %s (%s) refused Equip without a named reason'%(identifier,item['kind']))
        if flags&1 and flags&4:
            report['equip_allowed']=report.get('equip_allowed',0)+1
            if source and not script_inert_after_registration(source) and \
               not script_allows(source,EQUIP_REACTION_WORDS):
                report.setdefault('equip_reaction_not_run',[]).append(identifier)
        row=safe_text(identifier,64)+safe_text(item['name'],96)+struct.pack('<iiifII',item['category'],item['subtype'],item['value'],item['weight'],slots,flags)
        row+=safe_text(model,64)+safe_text(icon,64)+safe_text(item['enchantment'],64)+safe_text(item['script'],64)
        # Bytes 496..511 (zero in older catalogues): the enchantment's kind (0 none, else ENDT
        # type + 1: cast once, when strikes, when used, constant) and its maximum charge, so
        # the HUD can show the original charge bar (docs/HUD.md "Weapon and magic boxes").
        enchant=enchantments.get(item['enchantment']) if item['enchantment'] else None
        kind=enchant[0]+1 if enchant and 0<=enchant[0]<=3 and item['enchantment'] in charges else 0
        charge=charges[item['enchantment']] if kind else 0.
        if not (math.isfinite(charge) and 0<=charge<=1000000):raise ValueError('Invalid enchantment charge '+identifier)
        light=item.get('light')
        # bytes 504..511: a carried light's burn time and colour; else the enchantment points (u16 at 504, v0.0.58)
        # byte 506 of a weapon (v0.0.61, RESIST-NORMAL-WEAPONS-61): its WPDT flags, 1 magical and 2 silver (OpenMW
        # combat.cpp isNormalWeapon: a creature that resists normal weapons is hurt only by these or enchanted ones)
        flags_506=struct.unpack_from('<i',item['raw'],28)[0]&3 if item['kind']=='WEAP' and len(item['raw'])>=32 else 0
        # byte 511 of a carried light (v0.0.61, HELD-LIGHT-OWN-MODEL-61): 0x80 | 1 it flickers or pulses | 2 a fire
        # (held_lights.catalogue_flags; 0 in older catalogues)
        tail=struct.pack('<i3BB',light['time'],*light['colour'],catalogue_flags(light.get('flags',0))) if light else \
            struct.pack('<HB5x',item.get('capacity',0),flags_506)
        # ALCHEMY-61: an ingredient, potion or apparatus row carries the alchemy block where the weapon and armour
        # numbers sit (it has none), flag 64 (tools/prepare_alchemy.py)
        if item.get('alchemy'):
            if any(combat[2:]) or combat[0] or combat[1]!=26:raise ValueError('Alchemy row with combat numbers '+identifier)
            row+=item['alchemy']+struct.pack('<B3xf',kind,charge)+tail
        else:row+=struct.pack('<ii6iffffii',*combat)+struct.pack('<B3xf',kind,charge)+tail
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
    # The build receipt names it (docs/INVENTORY.md "Debug torch (test only)").
    report['debug_torch']=({'id':DEBUG_TORCH_ID,'name':DEBUG_TORCH_NAME,**items[DEBUG_TORCH_ID]['light']}
                           if DEBUG_TORCH_ID in items else None)
    report['catalogue_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
    # ALCHEMY-61: the alchemy settings, lines, sounds and bottle looks (alchemy/settings.txt), in the same step
    from prepare_alchemy import prepare as prepare_alchemy
    report['alchemy']=prepare_alchemy(data,id1,items)
    # dbg give weapons (DBG-GIVE-WEAPONS-59): one plain item of every weapon type and two shields, chosen from the
    # records by a rule (tools/prepare_weapon_kit.py), every one a row of the catalogue just written.
    from prepare_weapon_kit import write_kit
    report['weapon_kit']=write_kit(id1,items,settings,row_flags,child_ci(data,'Morrowind.esm').read_bytes())
    if models:
        # One icon lookup table for the HUD boxes and the inventory (tools/prepare_icons.py):
        # the same referenced closure as the staged inventory resources.
        from prepare_icons import prepare as prepare_icons, hud_settings, ini_colours
        # HUD-WEAPON-BOX-EMPTY-59: every weapon that can be equipped gets its HUD picture too (the box showed
        # nothing for a weapon outside the starting closure; the engine falls back to the inventory picture)
        hud_ids=set(selected)|{i for i,item in items.items() if item['kind']=='WEAP' and row_flags.get(i,0)&1}
        closure={i:{'source_icon':items[i]['source_icon'],'enchanted':bool(items[i]['enchantment'])}
                 for i in sorted(hud_ids) if i in items}
        colours,report['hud_colours']=ini_colours(data)
        import os
        report['icon_table']=prepare_icons(assets,id1,closure,palette,colours,inventory_icons,jobs or os.cpu_count() or 1)
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
