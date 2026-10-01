# SPDX-License-Identifier: GPL-3.0-only
"""Host-only TES3 humanoid assembly and original animation sampling.

PyFFI is an external NIF reader. No game data or OpenMW implementation is embedded.
Matrices use row vectors, matching the NIF reader; skin offsets are inverse binds.
"""
import bisect
import io
import math
import struct
from collections import OrderedDict
from pathlib import Path
import numpy as np
from PIL import Image
from mwad.audit import normpath
from prepare_scenery import bsa_read, nif_reader

class Assets:
    def __init__(self, data_files, bsa):
        self.bsa=bsa
        self.loose={normpath(p.relative_to(data_files).as_posix()):p for p in data_files.rglob('*') if p.is_file()}
        self.models=OrderedDict();self.textures=OrderedDict();self.texture_bytes=0
    def read(self, name):
        name=normpath(name)
        if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe asset path')
        if name in self.loose:return self.loose[name].read_bytes()
        return bsa_read(self.bsa,name)
    def texture(self, name):
        name=normpath(name)
        if not name.startswith('textures/'):name='textures/'+name
        if name in self.textures:
            self.textures.move_to_end(name);return self.textures[name]
        for candidate in (str(Path(name).with_suffix('.dds')),name):
            try:
                image=np.array(Image.open(io.BytesIO(self.read(candidate))).convert('RGBA'))
                if image.nbytes<=16*1024*1024:
                    while self.textures and self.texture_bytes+image.nbytes>16*1024*1024:
                        _,old=self.textures.popitem(last=False);self.texture_bytes-=old.nbytes
                    image.setflags(write=False);self.textures[name]=image;self.texture_bytes+=image.nbytes
                return image
            except KeyError:pass
        raise ValueError('Missing texture '+name)

def blend_keys(times, values, time, quaternion=False, interpolation=1):
    """Clamp linear keys; spherical interpolation for unit quaternions (wxyz)."""
    if not len(times):raise ValueError('Empty key channel')
    hi=bisect.bisect_right(times,time)
    if hi==0:return values[0].copy()
    if hi==len(times):return values[-1].copy()
    lo=hi-1;u=(time-times[lo])/(times[hi]-times[lo]);a=values[lo];b=values[hi]
    if interpolation!=1:
        # A static inspection pose may use an exact authored key or a constant
        # interval without approximating unsupported TBC/quadratic curves.
        if abs(time-times[lo])<=1e-5:return a.copy()
        if abs(time-times[hi])<=1e-5:return b.copy()
        if np.allclose(a,b,rtol=0,atol=1e-7) or (quaternion and np.allclose(a,-b,rtol=0,atol=1e-7)):return a.copy()
        raise ValueError('Nonlinear key interval needs its authored interpolation')
    if quaternion:
        a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);dot=float(a@b)
        if dot<0:b=-b;dot=-dot
        if dot<.9995:
            theta=math.acos(np.clip(dot,-1,1));v=(math.sin((1-u)*theta)*a+math.sin(u*theta)*b)/math.sin(theta)
        else:v=(1-u)*a+u*b
        return v/np.linalg.norm(v)
    return (1-u)*a+u*b

def quat_matrix(q):
    from scipy.spatial.transform import Rotation
    return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix().T

class Skeleton:
    def __init__(self, assets, source='meshes/base_anim.nif'):
        self.N=nif_reader();data=self.N.Data();data.read(io.BytesIO(assets.read(source)))
        self.nodes={};self.parents={};self.channels={};self.events={}
        def visit(node,parent):
            if not isinstance(node,self.N.NiNode):return
            name=node.name.decode('cp1252').casefold()
            if name in self.nodes:raise ValueError('Duplicate skeleton node '+name)
            self.nodes[name]=node;self.parents[name]=parent
            e=node.extra_data
            while e:
                if isinstance(e,self.N.NiTextKeyExtraData):
                    for key in e.text_keys:
                        for line in key.value.decode('cp1252').splitlines():self.events[line.strip().casefold()]=key.time
                e=getattr(e,'next_extra_data',None)
            for child in node.children:
                if child:visit(child,name)
        for root in data.roots:visit(root,None)
    def local(self,name,time):
        node=self.nodes[name];m=np.array(node.get_transform().as_list())
        if name not in self.channels:
            channels={};c=node.controller
            while c:
                if isinstance(c,self.N.NiKeyframeController) and c.data:
                    d=c.data
                    if d.num_rotation_keys:
                        if d.rotation_type not in (1,2,3):raise ValueError('Unsupported rotation keys on required bone '+name)
                        channels['rotation']=([k.time for k in d.quaternion_keys],np.array([[k.value.w,k.value.x,k.value.y,k.value.z] for k in d.quaternion_keys]))
                        channels['rotation_interpolation']=int(d.rotation_type)
                    for field,group in [('position',d.translations),('scale',d.scales)]:
                        if len(group.keys):
                            channels[field]=([k.time for k in group.keys],np.array([k.value.as_list() if field=='position' else k.value for k in group.keys]))
                            channels[field+'_interpolation']=int(group.interpolation)
                c=c.next_controller
            self.channels[name]=channels
        channels=self.channels[name]
        if 'rotation' in channels:m[:3,:3]=quat_matrix(blend_keys(*channels['rotation'],time,True,channels['rotation_interpolation']))*node.scale
        if 'position' in channels:m[3,:3]=blend_keys(*channels['position'],time,interpolation=channels['position_interpolation'])
        if 'scale' in channels:m[:3,:3]*=float(blend_keys(*channels['scale'],time,interpolation=channels['scale_interpolation']))/node.scale
        return m
    def pose(self,time):
        matrices={}
        def world(name):
            name=name.casefold()
            if name not in matrices:
                parent=self.parents[name];matrices[name]=self.local(name,time)@(world(parent) if parent else np.eye(4))
            return matrices[name]
        return world
    def idle_times(self,count):
        a=self.events['idle: start'];b=self.events['idle: stop']
        if b<=a:raise ValueError('Invalid idle range')
        return np.linspace(a,b,count,endpoint=False),(b-a)/count

def assemble(assets, appearance, skeleton, times, face_samples=None):
    N=skeleton.N;shapes=[];materials=[];textures={};cache=assets.models
    poses=[skeleton.pose(float(t)) for t in times]
    for part in appearance['parts']:
        mesh=normpath('meshes/'+part['mesh'])
        if mesh not in cache:
            raw=assets.read(mesh)
            if not raw.startswith(b'NetImmerse File Format, Version 4.0.0.2\n'):raise ValueError('Unsupported NIF version')
            d=N.Data();d.read(io.BytesIO(raw));cache[mesh]=d
            while len(cache)>32:cache.popitem(last=False)
        cache.move_to_end(mesh)
        data=cache[mesh];nodes=[]
        def walk(node,parent,hidden=False):
            if not isinstance(node,N.NiAVObject):return
            transform=np.array(node.get_transform().as_list())@parent
            hidden=hidden or bool(node.flags&1)
            nodes.append((node,transform,hidden))
            for child in getattr(node,'children',[]):
                if child:walk(child,transform,hidden)
        for root in data.roots:walk(root,np.eye(4))
        rig=any(isinstance(n,N.NiTriShape) and n.skin_instance for n,_,_ in nodes)
        offset=next((np.array(n.translation.as_list()) for n,_,_ in nodes if n.name.lower()==b'boneoffset'),np.zeros(3))
        found=0
        for node,transform,hidden in nodes:
            if hidden or not isinstance(node,N.NiTriShape) or not node.data:continue
            name=node.name.decode('cp1252');filt=name.casefold().removeprefix('tri ')
            if rig and (not node.skin_instance or not filt.startswith(part['filter'].casefold())):continue
            g=node.data
            if not g.num_triangles:continue
            vertices=np.array([v.as_list() for v in g.vertices]);hom=np.column_stack((vertices,np.ones(len(vertices))))
            mirrored=False
            if node.skin_instance:
                sk=node.skin_instance;positions=np.zeros((len(times),len(vertices),3));weights=np.zeros(len(vertices))
                for bone,info in zip(sk.bones,sk.data.bone_list):
                    ids=np.array([w.index for w in info.vertex_weights],int);ww=np.array([w.weight for w in info.vertex_weights])
                    if not len(ids) or not np.any(ww):continue
                    weights[ids]+=ww;inverse_bind=np.array(info.get_transform().as_list())
                    for fi,pose in enumerate(poses):
                        positions[fi,ids]+=((hom[ids]@inverse_bind@pose(bone.name.decode('cp1252')))[:,:3])*ww[:,None]
                if np.any(np.abs(weights-1)>.02):raise ValueError('Invalid skin weights '+name)
                positions/=weights[None,:,None]
            else:
                attach=part['attach'];mirror=np.eye(4);mirrored=attach.startswith('Left')
                if mirrored:mirror[0,0]=-1
                mirror[3,:3]=offset
                if part['slot']==0 and face_samples is not None:
                    from npc_faces import sample_morph
                    if len(face_samples)!=len(poses):raise ValueError('Facial sample count mismatch')
                    head=[]
                    for pose,sample in zip(poses,face_samples):
                        v=vertices if sample is None else sample_morph(node,data,N,*sample)
                        head.append((np.column_stack((v,np.ones(len(v))))@transform@mirror@pose(attach))[:,:3])
                    positions=np.array(head)
                else:positions=np.array([(hom@transform@mirror@pose(attach))[:,:3] for pose in poses])
            uv=np.array([[u.u,u.v] for u in g.uv_sets[0]]) if g.num_uv_sets else np.zeros((len(vertices),2))
            colours=np.array([[c.r,c.g,c.b,c.a] for c in g.vertex_colors]) if g.has_vertex_colors else np.ones((len(vertices),4))
            diffuse=[1.,1.,1.];alpha=1.;source=None
            for prop in node.properties:
                if isinstance(prop,N.NiMaterialProperty):diffuse=[prop.diffuse_color.r,prop.diffuse_color.g,prop.diffuse_color.b];alpha=prop.alpha
                if isinstance(prop,N.NiTexturingProperty) and prop.has_base_texture and prop.base_texture.source:source=prop.base_texture.source.file_name.decode('cp1252')
            ti=None
            if source:
                ti=normpath(source)
                if ti not in textures:textures[ti]=assets.texture(source)
            mi=len(materials);materials.append({'texture_index':ti,'diffuse':diffuse,'alpha':alpha})
            faces=np.array(g.get_triangles(),int)
            if mirrored:faces=faces[:,[0,2,1]]
            if face_samples is not None:
                # Locomotion is advanced by collision-aware game movement. Bake
                # the authored cycle in place; retain its vertical body motion.
                root=np.array([pose('bip01')[3,:2] for pose in poses])
                positions[13:,:,:2]-=(root[13:]-root[0])[:,None,:]
            positions*=np.array([appearance['weight'],appearance['weight'],appearance['height']])*.25
            shapes.append({'name':name,'part':part['slot'],'positions':positions,'faces':faces,'uv':uv,'colours':colours,'material':mi})
            found+=1
        if not found:raise ValueError('No attached geometry: '+str(part))
    return shapes,materials,textures

def combined(shapes,frame=0):
    vertices=[];faces=[]
    for shape in shapes:
        base=len(vertices);vertices.extend(np.column_stack((shape['positions'][frame],shape['uv'],shape['colours']*255)).tolist())
        faces.extend([[*(f+base),shape['material']] for f in shape['faces']])
    return np.array(vertices),np.array(faces,int)

def simplify_shape(points, faces, quota, preserve_shell=False):
    """Bound reduction without allowing a large torso panel to collapse away.

    Thin/open armour does not have the volume protection of a closed body.
    Retry with more faces when its surface area or extent collapses. The final
    alias budget is still enforced by bake; no triangles are silently dropped.
    """
    import fast_simplification
    # Some authored armour panels duplicate every triangle with reversed
    # winding. Decimating that non-manifold pair as one mesh erodes the panel.
    # Simplify one surface, then restore both visible sides explicitly.
    canonical=np.sort(faces,axis=1)
    _,first,inverse,counts=np.unique(canonical,axis=0,return_index=True,return_inverse=True,return_counts=True)
    if len(first)*2==len(faces) and np.all(counts==2):
        normals=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
        paired=all(np.dot(*normals[np.flatnonzero(inverse==i)])<=0 for i in range(len(first)))
        if paired:
            p,f=simplify_shape(points,faces[first],max(2,quota//2),preserve_shell)
            return p,np.concatenate((f,f[:,[0,2,1]]))
    def area(p, f):
        return np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],
                                       p[f[:,2]]-p[f[:,0]]), axis=1).sum()
    original_area = area(points, faces)
    span = np.ptp(points, axis=0)
    failed=0
    def reduced(target):
        p,f=fast_simplification.simplify(points,faces,target_count=target)
        if len(f)>target+2:p,f=fast_simplification.simplify(points,faces,target_count=target,agg=10.)
        valid=len(f) and (not preserve_shell or
                (area(p,f)>=.8*original_area and np.all(np.ptp(p,axis=0)>=.7*span)))
        return p,f,valid
    while quota < len(faces):
        candidate,triangles,valid=reduced(quota)
        if valid:
            # Doubling can overshoot the smallest safe open-panel mesh. Refine
            # between the failed and passing budgets, retaining the same area
            # and silhouette checks for every accepted candidate.
            if preserve_shell and failed:
                low,high=failed+1,quota-1
                while low<=high:
                    mid=(low+high)//2;p,f,ok=reduced(mid)
                    if ok:
                        if len(f)<len(triangles):candidate,triangles=p,f
                        high=mid-1
                    else:low=mid+1
            return candidate, triangles
        failed=quota;quota=max(quota+1,quota*2)
    return points, faces

def bake(shapes,materials,textures,palette,budget=480,face_limit=666,minimum_faces=None):
    """One topology shared by every frame, per-face tiny UV atlas patches."""
    from scipy.spatial import cKDTree
    if face_limit not in (666,777,1024):raise ValueError('Unsupported alias face limit')
    ceiling=face_limit if minimum_faces else 480
    if not 64<=budget<=ceiling:raise ValueError('Triangle budget outside allowed profile')
    minimum_faces=minimum_faces or {}
    if set(minimum_faces)-{s.get('name','') for s in shapes}:raise ValueError('Missing protected model shape')
    for s in shapes:
        required=minimum_faces.get(s.get('name',''),0)
        if not isinstance(required,int) or not 0<=required<=len(s['faces']):raise ValueError('Invalid protected shape budget')
    weights=np.array([len(s['faces'])*(1.7 if s['part']==0 else 1) for s in shapes],dtype=float);weights/=weights.sum()
    quotas=np.array([max(minimum_faces.get(s.get('name',''),0),min(120,len(s['faces'])) if s['part']==0 and len(s['positions'])>8 else 4) for s in shapes],int);remaining=budget-int(quotas.sum())
    if remaining<0:raise ValueError('Too many separate shapes for budget')
    quotas+=np.floor(weights*remaining).astype(int)
    actor_height = max(s['positions'][0,:,2].max() for s in shapes)-min(s['positions'][0,:,2].min() for s in shapes)
    skin=Image.new('RGB',(512,256));allframes=[];outfaces=[];outuv=[];fi=0
    for shape,quota in zip(shapes,quotas):
        orig=shape['positions'];faces=shape['faces'];p=orig[0]
        exact=minimum_faces.get(shape.get('name',''),0)==len(faces)
        points,ix=np.unique(np.round(p,5),axis=0,return_inverse=True);ff=ix[faces]
        if exact:points=p;ff=faces
        if len(ff)>quota:
            preserve_shell = shape['part']==3 and np.ptp(p[:,2]) >= .2*actor_height
            points,ff=simplify_shape(points,ff.astype(np.int32),int(quota),preserve_shell)
        old_tri=p[faces];centres=old_tri.mean(axis=1);tree=cKDTree(centres)
        mat=materials[shape['material']];tex=textures.get(mat['texture_index'])
        for source_face,face in enumerate(ff):
            triangle=points[face];oi=int(tree.query(triangle.mean(axis=0))[1]);old=old_tri[oi]
            basis=np.column_stack((old[1]-old[0],old[2]-old[0]));coords=(triangle-old[0])@np.linalg.pinv(basis).T
            bary=np.column_stack((1-coords.sum(axis=1),coords));uv=bary@shape['uv'][faces[oi]]
            # Transfer each decimated vertex via the nearest original triangle;
            # retain the rest-pose residual instead of snapping away the silhouette.
            animated=[]
            for point in triangle:
                ti=int(tree.query(point)[1]);t=old_tri[ti];xy=np.linalg.pinv(np.column_stack((t[1]-t[0],t[2]-t[0])))@(point-t[0])
                w=np.array([1-xy.sum(),*xy]);w=np.clip(w,0,1);w/=w.sum()
                animated.append(np.einsum('v,fvc->fc',w,orig[:,faces[ti]])+(point-w@t))
            allframes.append(np.stack(animated,axis=1))
            if exact:allframes[-1]=orig[:,face,:].copy()
            tile=np.zeros((16,16,3),np.uint8)
            # Sample the closest original surface per texel. Projecting an
            # entire decimated face onto one tiny source triangle crosses UV
            # seams and produces stripes, particularly on armour and faces.
            yy,xx=np.mgrid[0:16,0:16];w=np.column_stack((np.maximum(0,1-(xx.ravel()+yy.ravel())/15),xx.ravel()/15,yy.ravel()/15));w/=w.sum(1)[:,None]
            samples=w@triangle
            choices=tree.query(samples,k=min(12,len(old_tri)))[1]
            if choices.ndim==1:choices=choices[:,None]
            best=np.full(len(samples),np.inf);sampleuv=np.zeros((len(samples),2));samplecolour=np.ones((len(samples),3))
            for ci in range(choices.shape[1]):
                triids=choices[:,ci];tri=old_tri[triids]
                bases=np.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=2)
                xy=np.einsum('nij,nj->ni',np.linalg.pinv(bases),samples-tri[:,0])
                bw=np.column_stack((1-xy.sum(1),xy));bw=np.maximum(bw,0);bw/=bw.sum(1)[:,None]
                projected=np.einsum('nv,nvc->nc',bw,tri);dist=((projected-samples)**2).sum(1);take=dist<best
                sampleuv[take]=np.einsum('nv,nvc->nc',bw,shape['uv'][faces[triids]])[take]
                samplecolour[take]=np.einsum('nv,nvc->nc',bw,shape['colours'][faces[triids],:3])[take];best[take]=dist[take]
            if exact:
                # Protected shapes retain authored triangles and UV seams.
                # Nearby folds must not lend their texture to the original face.
                sampleuv=w@shape['uv'][faces[source_face]]
                samplecolour=w@shape['colours'][faces[source_face],:3]
            if tex is None:colours=np.full((len(samples),3),220.)
            else:
                px=np.floor(sampleuv[:,0]*tex.shape[1]).astype(int)%tex.shape[1];py=np.floor(sampleuv[:,1]*tex.shape[0]).astype(int)%tex.shape[0]
                colours=tex[py,px,:3].astype(float)
            colours*=samplecolour*np.array(mat['diffuse']);tile=np.clip(colours,0,255).astype(np.uint8).reshape(16,16,3)
            if fi>=face_limit:raise ValueError('Alias vertex budget exceeded')
            ty_required=((fi//32)+1)*16
            if ty_required>skin.height:
                # Gallery compacts these tiles before MDL encoding, retaining
                # the renderer's 480-row skin bound even for extended models.
                larger=Image.new('RGB',(512,((face_limit+31)//32)*16));larger.paste(skin,(0,0));skin=larger
            tx=fi%32*16;ty=fi//32*16;skin.paste(Image.fromarray(tile),(tx,ty));outuv.extend([(tx,ty),(tx+15,ty),(tx,ty+15)])
            outfaces.append([fi*3,fi*3+2,fi*3+1]);fi+=1
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    return np.concatenate(allframes,axis=1),np.array(outfaces),np.array(outuv),skin.quantize(palette=pal,dither=Image.Dither.NONE)

def animated_mdl(frames,faces,uv,skin,vertex_limit=1999):
    if frames.ndim!=3 or frames.shape[2]!=3 or not np.isfinite(frames).all():raise ValueError('Invalid alias frames')
    nf,nv,_=frames.shape
    if vertex_limit not in (1999,2331,3072):raise ValueError('Unsupported alias vertex limit')
    if not 1<=nf<=32 or nv>vertex_limit or not len(faces):raise ValueError('Alias budget exceeded')
    if faces.min()<0 or faces.max()>=nv:raise ValueError('Alias face index')
    lo=frames.min(axis=(0,1));hi=frames.max(axis=(0,1));scale=np.maximum((hi-lo)/255,.0001)
    xyz=np.clip(np.rint((frames-lo)/scale),0,255).astype(np.uint8);w,h=skin.size
    if skin.mode!='P' or w%4 or h>480:raise ValueError('Unsupported alias skin')
    if uv.shape!=(nv,2) or not np.isfinite(uv).all() or np.any(uv<0) or np.any(uv>=np.array([w,h])):raise ValueError('Alias UV bounds')
    data=bytearray(struct.pack('<4si3f3ff3f8if',b'IDPO',6,*scale,*lo,float(np.linalg.norm(frames,axis=2).max()),0,0,0,1,w,h,nv,len(faces),nf,0,0,1.))
    data.extend(struct.pack('<i',0));data.extend(skin.tobytes())
    for u,v in uv:data.extend(struct.pack('<iii',0,int(u),int(v)))
    for a,b,c in faces:data.extend(struct.pack('<4i',1,int(a),int(b),int(c)))
    for i,points in enumerate(xyz):
        data.extend(struct.pack('<i4B4B16s',0,*points.min(0),0,*points.max(0),0,('idle%02d'%i).encode()))
        data.extend(np.column_stack((points,np.zeros(nv,np.uint8))).astype(np.uint8).tobytes())
    return bytes(data)
