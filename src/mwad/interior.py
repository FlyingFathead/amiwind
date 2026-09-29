"""Bounded base-master interior audit. No script execution or asset redistribution."""
from pathlib import Path
import hashlib, math, struct
from .audit import records, subrecords, cell_data, string, require


def read_interior(path, name):
    raw=Path(path).read_bytes();cells=[];objects={};entrances=[]
    kinds={'STAT','DOOR','CONT','LIGH','ACTI','NPC_','MISC','BOOK','INGR','WEAP','ARMO','CLOT','ALCH','APPA','REPA','LOCK','PROB','LEVC','LEVI','CREA'}
    for tag,flags,payload in records(raw):
        if tag not in kinds and tag!='CELL':continue
        subs=list(subrecords(payload));s=dict(subs)
        if tag=='CELL':
            header={}
            for t,b in subs:
                if t=='FRMR':break
                header[t]=b
            if not struct.unpack_from('<I',header['DATA'])[0]&1:
                if any(t=='DNAM' and string(b).casefold()==name.casefold() for t,b in subs):
                    outside=cell_data(subs)
                    entrances.extend(r for r in outside['refs'] if r.get('destination_cell','').casefold()==name.casefold())
                continue
            if string(header.get('NAME',b'')).casefold()!=name.casefold():continue
            cell=cell_data(subs)
            if not cell['flags']&1:continue
            cell['water_height']=None
            if cell['flags']&2:
                # Original master uses integer INTV; later files may use WHGT.
                water=0.
                for tag,data in header.items():
                    if tag in ('INTV','WHGT'):
                        require(len(data)==4,'Invalid interior water height')
                        water=struct.unpack('<i' if tag=='INTV' else '<f',data)[0]
                require(math.isfinite(water),'Nonfinite interior water height')
                cell['water_height']=water
            ambient=header.get('AMBI')
            require(ambient is not None and len(ambient)==16,'Interior AMBI missing/invalid')
            cell['lighting']={'ambient':list(ambient[:3]),'sunlight':list(ambient[4:7]),
                              'fog':list(ambient[8:11]),'fog_density':struct.unpack_from('<f',ambient,12)[0]}
            cells.append(cell)
        elif 'NAME' in s and 'DELE' not in s:
            obj={'type':tag,'model':string(s.get('MODL',b'')),'display_name':string(s.get('FNAM',b''))}
            if tag=='LIGH':
                require(len(s.get('LHDT',b''))==24,'Invalid light record')
                weight,value,duration,radius=struct.unpack_from('<fiiI',s['LHDT'])
                obj['light']={'radius':radius,'color':list(s['LHDT'][16:19]),'flags':struct.unpack_from('<I',s['LHDT'],20)[0]}
            objects[string(s['NAME']).casefold()]=obj
    require(len(cells)==1,'Interior must resolve uniquely: '+name)
    cell=cells[0]
    for ref in cell['refs']:
        require(ref['id'].casefold() in objects,'Missing interior base record: '+ref['id'])
        ref.update(objects[ref['id'].casefold()])
    cell['entrances']=entrances
    cell['master_sha256']=hashlib.sha256(raw).hexdigest()
    return cell


def select_geometry(cell):
    selected=[];omitted=[]
    for ref in cell['refs']:
        model=ref.get('model','').replace('\\','/').lower()
        reason=None
        if ref.get('deleted'):reason='deleted reference'
        elif not model:reason='no static model'
        elif 'marker' in model:reason='editor marker'
        elif ref['type'] not in ('STAT','DOOR','CONT','LIGH','ACTI'):reason='small item or actor deferred'
        elif ref['type']=='ACTI' and 'active_de_bed' not in model and not (
                ref['id'].casefold()=='chargen stuff room' and
                model=='i/in_c_plain_room_side.nif'):reason='unsupported activator'
        elif any(x in model for x in ('furn_bone','furn_de_rope','shack_hook','shack_basket')):reason='fine dressing deferred'
        if reason:omitted.append({'reference':ref['number'],'id':ref['id'],'reason':reason})
        else:selected.append(ref)
    return selected,omitted
