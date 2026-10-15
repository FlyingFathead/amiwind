# SPDX-License-Identifier: GPL-3.0-only
"""Original-master terrain/material adapter used only by explicit ocean frames.

The regular base-master path is unchanged. LAND samples use the shared TES3
height/material decoders; LTEX indices are local to the LAND record's master.
Ground pixels use the existing original-archive resolver and normal palette bake.
"""
import hashlib
import io
import struct
from pathlib import Path, PurePosixPath

from mwad.audit import decode_heights, decode_materials, normpath
from mwad.esm import GAME_MASTERS, subrecords, string, is_deleted
from mwad.paths import child_ci


def resolve_grids(data_files, wanted):
    """Selected original LAND, last present master wins, with stable master-local materials.

    Returns (grids, extra materials, receipt). Base IDs are untouched. Expansion
    namespaces cannot collide with a base LTEX of the same numeric index.
    Deleted LAND is refused here rather than resurrecting an earlier record.
    """
    wanted=set(map(tuple,wanted)); grids={}; materials={}; masters=[]; dependencies=[]; heightless=[]
    for master_index,name in enumerate(GAME_MASTERS):
        path=child_ci(Path(data_files),name,required=False)
        if path is None or not path.is_file():
            if master_index==0:raise ValueError('Ocean terrain needs Morrowind.esm')
            continue
        sha=hashlib.sha256(); local={}; lands={}
        with path.open('rb') as stream:
            while True:
                h=stream.read(16)
                if not h:break
                if len(h)!=16:raise ValueError('Truncated terrain master header')
                tag,size,_,flags=struct.unpack('<4sIII',h);raw=stream.read(size)
                if len(raw)!=size:raise ValueError('Truncated terrain master record')
                sha.update(h);sha.update(raw)
                if tag not in (b'LAND',b'LTEX'):continue
                s=dict(subrecords(raw))
                if tag==b'LTEX':
                    if is_deleted(flags,s):continue
                    if len(s.get('INTV',b''))!=4:raise ValueError('Invalid original LTEX index')
                    ident=struct.unpack('<I',s['INTV'])[0]+1
                    if not 0<ident<65536:raise ValueError('Original LTEX index exceeds material namespace')
                    local[ident]={'texture':string(s.get('DATA',b''),'LTEX DATA'),'record_sha256':hashlib.sha256(raw).hexdigest()}
                else:
                    if len(s.get('INTV',b''))!=8:raise ValueError('Invalid original LAND coordinates')
                    xy=struct.unpack('<ii',s['INTV'])
                    if xy not in wanted:continue
                    if is_deleted(flags,s):raise ValueError('Deleted apron LAND needs content-loader resolution: %s'% (xy,))
                    if 'VHGT' not in s:
                        # Match mwad.audit.load_esm/far.land_heights for base map-only LAND.
                        # Expansion records requiring inherited data stay outside this adapter.
                        if master_index:
                            raise ValueError('Expansion apron LAND lacks heights: %s' % (xy,))
                        heightless.append({'cell':list(xy),'master':name,
                                           'land_sha256':hashlib.sha256(raw).hexdigest(),
                                           'status':'no VHGT; established base default-height policy'})
                        continue
                    lands[xy]=(s,hashlib.sha256(raw).hexdigest())
        masters.append({'name':name,'sha256':sha.hexdigest(),'bytes':path.stat().st_size})
        for xy,(s,digest) in lands.items():
            source_ids=decode_materials(s['VTEX']) if 'VTEX' in s else [[0]*16 for _ in range(16)]
            used=set(v for row in source_ids for v in row)
            if any(v and v not in local for v in used):raise ValueError('Apron LAND uses an unresolved master-local LTEX in '+name)
            if master_index:
                for value in used-{0}:
                    key=master_index*65536+value
                    materials[key]=dict(local[value],master=name,source_index=value)
            mapped=[[master_index*65536+v if master_index and v else v for v in row] for row in source_ids]
            grids[xy]={'cell':list(xy),'heights':decode_heights(s['VHGT']),'materials':mapped}
            dependencies.append({'cell':list(xy),'master':name,'land_sha256':digest,
                                 'materials':[{'source_index':v,**local[v]} for v in sorted(used-{0})]})
    # Records superseded by a later master are dependencies too: changes in either cannot be hidden.
    used_final = {v for g in grids.values() for row in g['materials'] for v in row}
    materials = {k:v for k,v in materials.items() if k in used_final}
    return grids,materials,{'masters':masters,'land_records':dependencies,'heightless_base_records':heightless,'material_namespace_stride':65536}


def ground_textures(data_files, materials, palette, source=None):
    """Bake only expansion terrain textures with the same BOX/palette path as ground_assets.

    Archive search is reused from MeshSource; its loose lookup covers Meshes only,
    so this does not broaden the existing ground path to loose texture overrides.
    """
    from PIL import Image
    from prepare_quake import miptex
    from world_estimate_data import MeshSource
    source=source or MeshSource(data_files);pal=Image.new('P',(1,1));pal.putpalette(palette)
    textures={};dependencies=[]
    for key,record in sorted(materials.items()):
        name=normpath('textures/'+record['texture']); raw=None;archive=None;candidate=None
        for candidate in dict.fromkeys([str(PurePosixPath(name).with_suffix('.dds')),name]):
            try:raw,archive=source.read(candidate);break
            except (FileNotFoundError,KeyError):pass
        if raw is None:raise ValueError('Missing original ocean apron texture '+name)
        im=Image.open(io.BytesIO(raw)).convert('RGB').resize((32,32),Image.Resampling.BOX)
        im=im.quantize(palette=pal,dither=Image.Dither.NONE);label='g%d'%key
        textures[label]=miptex(label,im)
        dependencies.append({'material':key,'master':record['master'],'source_index':record['source_index'],
                             'asset':candidate,'archive':archive,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                             'ltex_sha256':record['record_sha256'],'miptex_sha256':hashlib.sha256(textures[label]).hexdigest()})
    return textures,dependencies
