"""Bounded base-master interior audit. No script execution or asset redistribution."""
from pathlib import Path
import hashlib, math, struct
from .audit import records, subrecords, cell_data, string, require


def original_doors(raw):
    """Return only authored directed DOOR/DODT links, never inferred reverses."""
    objects={};cells=[]
    for tag,flags,payload in records(raw):
        if tag not in ('DOOR','CELL') or flags&0x20:continue
        subs=list(subrecords(payload));fields=dict(subs)
        if tag=='DOOR' and 'NAME' in fields and 'DELE' not in fields:
            objects[string(fields['NAME']).casefold()]={
                'model':string(fields.get('MODL',b'')),
                'script':string(fields.get('SCRI',b'')),
                'open_sound':string(fields.get('SNAM',b'')),
                'close_sound':string(fields.get('ANAM',b''))}
        elif tag=='CELL':
            cell=cell_data(subs);fields={};current=None;markers=[]
            for subtag,data in subs:
                # NAM0 starts the cell's temporary-reference section; it is not
                # ownership/lock state of the previous reference (ESM3 CellRef).
                if subtag=='NAM0':
                    require(len(data)==4,'Invalid temporary reference section marker')
                    markers.append({'tag':subtag,'hex':data.hex(),'after_reference':current})
                elif subtag=='FRMR':current=struct.unpack('<I',data)[0];fields[current]=[]
                elif current is not None:
                    fields[current].append({'tag':subtag,'hex':data.hex()})
            for ref in cell['refs']:ref['original_subrecords']=fields[ref['number']]
            cell['reference_section_markers']=markers;cells.append(cell)
    names={}
    for cell in cells:
        if cell['flags']&1:
            key=cell['name'].casefold()
            require(key not in names,'Ambiguous original interior name')
            names[key]=cell['name']
    out=[]
    for cell in cells:
        interior=bool(cell['flags']&1)
        for ref in cell['refs']:
            base=objects.get(ref.get('id','').casefold())
            if not base or ref.get('deleted') or 'destination' not in ref:continue
            target=ref.get('destination_cell','')
            if target:
                require(target.casefold() in names,'Missing original door destination: '+target)
                target=names[target.casefold()]
            out.append({**ref,**base,'source_cell':cell['name'],
                'source_interior':interior,'source_grid':[cell['x'],cell['y']],
                'destination_cell':target,'destination_interior':bool(target),
                'cell_reference_section_markers':cell['reference_section_markers']})
    return out


def read_interior(path, name, *, include_interior_entrances=False):
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
    if include_interior_entrances:
        entrances=[r for r in original_doors(raw)
                   if r['destination_cell'].casefold()==cell['name'].casefold()]
    cell['entrances']=entrances
    cell['master_sha256']=hashlib.sha256(raw).hexdigest()
    return cell


def select_geometry(cell, *, harvest_references=(), harvest_master_sha256=None):
    """Opt-in exact source-bound CONT exclusion; all other policy is unchanged."""
    exclusions={}
    if harvest_references:
        require(harvest_master_sha256==cell.get('master_sha256') and
                isinstance(harvest_master_sha256,str) and len(harvest_master_sha256)==64,
                'Harvest exclusion requires the exact room master')
        original={r['number']:r for r in cell['refs']}
        require(len(original)==len(cell['refs']),'Duplicate room reference number')
        for ref in harvest_references:
            number=ref['number'];source=original.get(number)
            require(number not in exclusions and source is not None,'Unknown/duplicate harvest exclusion')
            require(ref.get('cell')==cell['name'] and ref.get('type')=='CONT' and
                    source.get('type')=='CONT' and not source.get('deleted'),
                    'Harvest exclusion is not a live CONT in this exact room')
            for field in ('id','model'):
                norm=lambda value:value.replace('\\','/').casefold()
                require(norm(ref[field])==norm(source[field]),'Harvest exclusion source differs: '+field)
            for field in ('position','rotation_radians'):
                require(ref[field]==source[field],'Harvest exclusion pose differs: '+field)
            require(ref.get('scale',1.)==source.get('scale',1.),'Harvest exclusion scale differs')
            exclusions[number]=ref
    selected=[];omitted=[]
    for ref in cell['refs']:
        model=ref.get('model','').replace('\\','/').lower()
        reason=None
        if ref.get('deleted'):reason='deleted reference'
        elif ref['number'] in exclusions:reason='external harvest reference'
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
