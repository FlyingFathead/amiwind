#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert the owned torch, first-person grip and source flame for image assembly."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA, normpath, records, subrecords
from mwad.npc import load_master, text
from mwad.paths import child_ci, ensure_external
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl, rigid_attachment
from prepare_hands import nord_parts
from prepare_hand_sprites import decode_mdl, render_frame, pack_frame

FRAMES = 8
VIEW_OFFSET = np.array([4.0, 0.0, 0.0])

def camera_space(points, camera):
    # The Quake viewmodel clips at five camera units. Move the entire authored
    # assembly forward together, retaining the grip and all emitter transforms.
    return (np.asarray(points)-camera)[...,[1,0,2]]*np.array([1,-1,1])+VIEW_OFFSET

class TorchSkeleton(Skeleton):
    """Layer the authored torch motion on the left arm over unarmed idle."""
    def pose(self, time):
        start=self.events['torch: start'];stop=self.events['torch: stop']
        idle_start=self.events['idlehh: start'];idle_stop=self.events['idlehh: stop']
        if stop<=start or idle_stop<=idle_start:raise ValueError('Invalid torch/idle animation range')
        idle_time=idle_start+(time-start)/(stop-start)*(idle_stop-idle_start)
        if 'bip01 l clavicle' not in self.nodes:raise ValueError('Missing torch arm root')
        matrices={};left={}
        def world(name):
            name=name.casefold()
            if name not in matrices:
                parent=self.parents[name];base=world(parent) if parent else np.eye(4)
                left[name]=name=='bip01 l clavicle' or bool(parent and left[parent])
                matrices[name]=self.local(name,time if left[name] else idle_time)@base
            return matrices[name]
        return world

def source_nodes(data, N):
    nodes={}
    def walk(node,parent):
        if not isinstance(node,N.NiAVObject):return
        matrix=np.array(node.get_transform().as_list())@parent
        name=node.name.decode('cp1252').casefold()
        if name in ('boneoffset','fire emitter','smoke emitter','attachlight'):
            if name in nodes:raise ValueError('Duplicate torch attachment '+name)
            nodes[name]=(node,matrix)
        for child in getattr(node,'children',[]):
            if child:walk(child,matrix)
    for root in data.roots:walk(root,np.eye(4))
    for name in ('boneoffset','fire emitter','attachlight'):
        if name not in nodes:raise ValueError('Missing torch attachment '+name)
    return nodes

def flame_texture(data, N, assets, palette):
    matches=[]
    def walk(node):
        if isinstance(node,N.NiRotatingParticles):
            c=node.controller
            while c:
                if (isinstance(c,N.NiParticleSystemController) and c.emitter and
                        c.emitter.name.lower()==b'fire emitter'):
                    for prop in node.properties:
                        if isinstance(prop,N.NiTexturingProperty) and prop.has_base_texture and prop.base_texture.source:
                            matches.append(prop.base_texture.source.file_name.decode('cp1252'))
                c=c.next_controller
        for child in getattr(node,'children',[]):
            if child:walk(child)
    for root in data.roots:walk(root)
    if len(matches)!=1:raise ValueError('Expected one source fire texture')
    rgba=Image.fromarray(assets.texture(matches[0])).resize((16,16),Image.Resampling.LANCZOS)
    pixels=np.array(rgba);rgb=pixels[:,:,:3].astype(float)
    # Preserve the source alpha silhouette; a warm palette ramp keeps this tiny
    # additive-effect approximation visible without framebuffer alpha blending.
    strength=rgb.max(axis=2)/max(1,float(rgb.max()))
    warm=np.stack((255*strength,235*strength**1.6,100*strength**3),axis=2)
    pal=np.frombuffer(palette,np.uint8).reshape(256,3)[:255].astype(float)
    indices=((warm[:,:,None,:]-pal[None,None,:,:])**2).sum(3).argmin(2).astype(np.uint8)
    alpha=(pixels[:,:,3].astype(float)*strength).astype(np.uint8)
    return matches[0],np.stack((indices,alpha),axis=2).tobytes()

def prepare(data_files,id1):
    data_files=ensure_external(data_files,'owned data');id1=ensure_external(id1,'torch output')
    master=child_ci(data_files,'Morrowind.esm');archive=child_ci(data_files,'Morrowind.bsa')
    kinds,_,_=load_master(master);record=None
    for kind,flags,payload in records(master.read_bytes()):
        if kind!='LIGH':continue
        fields=list(subrecords(payload))
        if text(fields,'NAME').casefold()=='torch':
            record=None if any(tag=='DELE' for tag,_ in fields) else fields
    if record is None:raise ValueError('Original torch light record missing')
    mesh=text(record,'MODL');assets=Assets(data_files,BSA(archive))
    skeleton=TorchSkeleton(assets,'meshes/base_anim.1st.nif')
    start=skeleton.events['torch: start'];stop=skeleton.events['torch: stop']
    if not np.isfinite([start,stop]).all() or not 0<stop-start<60:raise ValueError('Invalid torch animation')
    times=np.linspace(start,stop,FRAMES,endpoint=False)
    parts=nord_parts(kinds)
    # Carried lights use the original left-hand Shield Bone attachment. Unlike
    # mirrored left body parts this rigid equipment mesh must not be mirrored.
    torch_part={'slot':10,'attach':'Shield Bone','filter':'','id':'torch','mesh':mesh,'carried_light':True}
    parts.append(torch_part)
    shapes,materials,textures=assemble(assets,{'parts':parts,'weight':1,'height':1},skeleton,times)
    shapes=[s for s in shapes if 'shadowbox' not in s['name'].casefold()]
    torch_shapes=[s for s in shapes if s['part']==10]
    if not torch_shapes:raise ValueError('No visible source torch geometry')
    camera=skeleton.pose(float(times[0]))('Camera')[3,:3]*.25
    for s in shapes:s['positions']=camera_space(s['positions'],camera)
    palette=(id1/'gfx/palette.lmp').read_bytes()
    protected={s['name']:len(s['faces']) for s in torch_shapes}
    frames,faces,uv,skin=bake(shapes,materials,textures,palette,budget=620,minimum_faces=protected)
    raw=animated_mdl(frames,faces,uv,skin)
    # Resolve emitter through exactly the rigid transform used by assemble.
    model=assets.models[normpath('meshes/'+mesh)];nodes=source_nodes(model,skeleton.N)
    offset=rigid_attachment(torch_part,nodes['boneoffset'][0].translation.as_list())
    anchors=[]
    for t in times:
        attachment=offset@skeleton.pose(float(t))('Shield Bone')
        anchors.append([camera_space((nodes[n][1]@attachment)[3,:3]*.25,camera).tolist()
                        for n in ('fire emitter','attachlight')])
    texname,texture=flame_texture(model,skeleton.N,assets,palette)
    # Big-endian signed 16.16 points and millisecond duration: no native float
    # layout assumptions. Bounds are validated again by the runtime loader.
    anchors=np.asarray(anchors)
    if not np.isfinite(anchors).all() or np.max(abs(anchors))>128:raise ValueError('Torch emitter outside viewmodel bounds')
    meta=struct.pack('>4sHHI',b'AWT1',FRAMES,16,round((stop-start)*1000))
    meta+=np.rint(anchors*65536).astype('>i4').tobytes()+texture
    for folder in ('progs','gfx'):(id1/folder).mkdir(exist_ok=True)
    (id1/'progs/v_torch.mdl').write_bytes(raw);(id1/'gfx/torch.awt').write_bytes(meta)
    decoded,faces,uv,skin=decode_mdl(raw)
    rendered=[render_frame(p,faces,uv,skin) for p in decoded]
    if any(not np.any(p!=255) for p in rendered):raise ValueError('Empty torch holding frame')
    payload=[pack_frame(p) for p in rendered];offsets=[12+4*(FRAMES+1)]
    for p in payload:offsets.append(offsets[-1]+len(p))
    sprites=struct.pack('>4s4H',b'AWS1',160,100,FRAMES,0)+struct.pack('>9I',*offsets)+b''.join(payload)
    (id1/'gfx/torch.aws').write_bytes(sprites)
    report={'format':'AmiWind carried source torch 1','source_id':'torch','source_mesh':mesh,
            'animation_layer':'authored torch left arm over authored unarmed idle','attachment':'Shield Bone','carried_light_rotation_x_degrees':-90,'view_offset':VIEW_OFFSET.tolist(),'source_flame_texture':texname,'source_torch_triangles':sum(protected.values()),
            'frames':FRAMES,'duration_seconds':float(stop-start),'triangles':len(faces),'vertices':len(decoded[0]),
            'opaque_pixels':[int((p!=255).sum()) for p in rendered],
            'files':{n:hashlib.sha256((id1/n).read_bytes()).hexdigest() for n in ('progs/v_torch.mdl','gfx/torch.awt','gfx/torch.aws')},
            'scope':'Original mesh/grip and emitter; bounded flame approximation, no smoke or inventory simulation'}
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',type=Path,required=True);p.add_argument('--id1',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.id1),indent=2))
