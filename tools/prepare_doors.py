#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Map original entrances; expose names even before destinations are converted."""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import records, subrecords, cell_data, string, BSA
from mwad.paths import child_ci, ensure_external, resolve_data_files
from prepare_scenery import bsa_read, model_geometry, nif_reader, world_bounds
from prepare_quake import CENTRE


def catalogue(master):
    raw=Path(master).read_bytes(); bases={};cells=[]
    for tag,flags,payload in records(raw):
        if tag not in ('DOOR','CELL'):continue
        subs=list(subrecords(payload)); s=dict(subs)
        if tag=='DOOR' and 'DELE' not in s:
            bases[string(s['NAME']).casefold()]={
                'model':string(s.get('MODL',b'')), 'name':string(s.get('FNAM',b'')),
                'script':string(s.get('SCRI',b'')),
                'open_sound':string(s.get('SNAM',b'')), 'close_sound':string(s.get('ANAM',b''))}
        elif tag=='CELL':cells.append(cell_data(subs))
    out=[]
    for c in cells:
        interior=bool(c['flags']&1)
        for r in c['refs']:
            base=bases.get(r.get('id','').casefold())
            if not base or r.get('deleted') or 'destination' not in r:continue
            target=r.get('destination_cell','')
            # Includes links between town interiors and the ship, in both directions.
            if not any('seyda neen' in x.casefold() or x.casefold()=='imperial prison ship' for x in (c['name'],target)):continue
            out.append({**r,**base,'source_cell':c['name'],'source_interior':interior,
                        'source_grid':[c['x'],c['y']], 'destination_interior':bool(target)})
    return {'format':'AmiWind original door catalogue 1','master_sha256':hashlib.sha256(raw).hexdigest(),'doors':out}


def runtime_position(position, interior):
    return [(position[0]-(0 if interior else CENTRE[0]))*.25,
            (position[1]-(0 if interior else CENTRE[1]))*.25,position[2]*.25]


def interior_reference(master,report,scene):
    """Private source layouts, with separate placed references for every door."""
    from mwad.interior import read_interior
    names=sorted({r['destination_cell'] for r in report['doors'] if r.get('destination_cell')})
    cells=[read_interior(master,name) for name in names]
    (scene/'interior-reference.json').write_text(json.dumps({'master_sha256':report['master_sha256'],
        'units':'original source units; each interior has its own local coordinates',
        'cells':cells},indent=2)+'\n')
    rows=['# Private Seyda Neen interior reference','',
          'Original CELL layouts and door destinations; not a claim that the interiors are playable.',
          'The companion JSON preserves each room\'s objects, transforms, lights, actors and entrances.',
          'Never infer a reciprocal door from a shared destination name. Use the placed reference and DODT.',
          '', '| Interior | Exterior entrance references | Placed objects | Actors | Lights |',
          '| --- | --- | ---: | ---: | ---: |']
    for c in cells:
        refs=[r for r in c['refs'] if not r.get('deleted')]
        rows.append('| '+c['name']+' | '+', '.join(str(r['number']) for r in c['entrances'])+
            f" | {len(refs)} | {sum(r['type'] in ('NPC_','CREA') for r in refs)} | {sum(r['type']=='LIGH' for r in refs)} |")
    rows+=['','## Door links','', '| Source cell | Reference | Destination | Source XYZ | Destination XYZ |',
           '| --- | ---: | --- | --- | --- |']
    for r in report['doors']:
        rows.append('| '+' | '.join([r['source_cell'],str(r['number']),r.get('destination_cell') or 'Exterior world',
            ', '.join(f'{v:.2f}' for v in r['position']),', '.join(f'{v:.2f}' for v in r['destination']['position'])])+' |')
    (scene/'interior-reference.md').write_text('\n'.join(rows)+'\n')


def prepare(data_files, scene):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'door conversion')
    report=catalogue(child_ci(data_files,'Morrowind.esm'))
    bsa=BSA(child_ci(data_files,'Morrowind.bsa'));N=nif_reader();cache={};links=[]
    for r in report['doors']:
        # A visible source entrance remains inspectable before its interior exists.
        names={'imperial prison ship':'prison','seyda neen, census and excise office':'census'}
        source=names.get(r['source_cell'].casefold()) if r['source_interior'] else 'seyda'
        target=names.get(r.get('destination_cell','').casefold()) if r['destination_interior'] else 'seyda'
        if not source or not (scene/'id1/maps'/f'{source}.bsp').is_file():
            r['runtime_status']='source scene not converted';continue
        available=bool(target and (scene/'id1/maps'/f'{target}.bsp').is_file())
        model='meshes/'+r['model']
        if model not in cache:
            raw=bsa_read(bsa,model);_,_,bounds,_=model_geometry(raw,N);cache[model]=bounds
        bounds=world_bounds(cache[model],r)
        # Padding absorbs converter quantization; do not expand to the whole room.
        low=[v-.5 for v in runtime_position(bounds[0],r['source_interior'])]
        high=[v+.5 for v in runtime_position(bounds[1],r['source_interior'])]
        arrival=runtime_position(r['destination']['position'],r['destination_interior']);arrival[2]+=16.875
        yaw=round((90-math.degrees(r['destination']['rotation_radians'][2]))%360,5)%360
        label=r.get('destination_cell') or 'Seyda Neen'
        if label.startswith('Seyda Neen, '):label=label[len('Seyda Neen, '):]
        if any(ord(c)<32 for c in label) or len(label.encode('cp1252'))>95:
            raise ValueError('Invalid doorway label')
        link={'source':source,'target':target if available else '-', 'label':label,
              'mins':low,'maxs':high,'arrival':arrival,'yaw':yaw,'reference':r['number']}
        links.append(link);r['runtime_status']='mapped' if available else 'entrance mapped; interior unavailable';r['runtime']=link
    if len(links)>64:raise ValueError('Runtime doorway limit exceeded')
    lines=['AWD3']
    for r in links:
        lines.append(r['source']+' '+r['target']+' '+str(r['reference'])+' '+' '.join(f'{v:.5f}' for v in (*r['mins'],*r['maxs'],*r['arrival'],r['yaw']))+'\t'+r['label'])
    (scene/'id1/scene-doors.txt').write_text('\n'.join(lines)+'\n',encoding='cp1252')
    (scene/'door-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    interior_reference(child_ci(data_files,'Morrowind.esm'),report,scene)
    return {'catalogued':len(report['doors']),'mapped':len(links),
            'available':sum(r['target']!='-' for r in links),'links':links}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.scene),indent=2))
