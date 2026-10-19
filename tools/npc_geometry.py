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
from pathlib import Path, PurePosixPath
import numpy as np
from PIL import Image
from mwad.audit import normpath
from prepare_scenery import bsa_read, nif_reader
from nif_common import ROOT_RULES, root_local, check_root_rule
import os

# NPC root-node rule (DON'T DELETE ANY METHOD): 'morrowind' = the game's rule shared with
# scenery (root rotation dropped, translation + scale kept); 'legacy' = full root transform.
# Set from --npc-root-rule; also exported so worker processes inherit it.
# DEFAULT = legacy: measured 2026-10-10: the scenery rule breaks 35 rigid NPC body-part meshes
# (necks, upper legs, knees, ankles, groin, pants): e.g. a dark elf upper leg shrinks from 9.6 to 3.2 units tall.
NPC_DEFAULT_ROOT_RULE='legacy'
ROOT_RULE_ENV='AMIWIND_NPC_ROOT_RULE'
_root_rule=check_root_rule(os.environ.get(ROOT_RULE_ENV,NPC_DEFAULT_ROOT_RULE))

def set_root_rule(rule):
    global _root_rule
    _root_rule=check_root_rule(rule);os.environ[ROOT_RULE_ENV]=_root_rule
    return _root_rule

def get_root_rule():
    return _root_rule

def add_root_rule_arg(parser):
    parser.add_argument('--npc-root-rule',choices=ROOT_RULES,default=NPC_DEFAULT_ROOT_RULE,help='NIF root node rule for NPC parts: legacy (default; full root transform, verified correct for rigid body parts) or morrowind (root rotation ignored like scenery; breaks 35 rigid part meshes, see docs)')

def apply_root_rule(args):
    return set_root_rule(getattr(args,'npc_root_rule',None) or NPC_DEFAULT_ROOT_RULE)

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
        for candidate in (str(PurePosixPath(name).with_suffix('.dds')),name):
            try:
                image=np.array(Image.open(io.BytesIO(self.read(candidate))).convert('RGBA'))
                if image.nbytes<=16*1024*1024:
                    while self.textures and self.texture_bytes+image.nbytes>16*1024*1024:
                        _,old=self.textures.popitem(last=False);self.texture_bytes-=old.nbytes
                    image.setflags(write=False);self.textures[name]=image;self.texture_bytes+=image.nbytes
                return image
            except KeyError:pass
        raise ValueError('Missing texture '+name)

def blend_keys(times, values, time, quaternion=False, interpolation=1, tangents=None):
    """Clamp linear keys; spherical interpolation for unit quaternions (wxyz).

    As the original engine's reference (OpenMW nifosg/controller.hpp interpolate):
    quaternion keys of the quadratic and TBC types are slerped like linear ones;
    quadratic vector/scale keys with their tangents (in, out per key) use the cubic
    Hermite spline value*b1 + next*b2 + out*b3 + next_in*b4. The Weapon Bone carries
    TBC rotation and quadratic position/scale keys (base_anim.nif).
    """
    if not len(times):raise ValueError('Empty key channel')
    hi=bisect.bisect_right(times,time)
    if hi==0:return values[0].copy()
    if hi==len(times):return values[-1].copy()
    lo=hi-1;u=(time-times[lo])/(times[hi]-times[lo]);a=values[lo];b=values[hi]
    if quaternion and interpolation in (2,3):interpolation=1
    if interpolation==2 and tangents is not None:
        t2=u*u;t3=t2*u
        return a*(2*t3-3*t2+1)+b*(-2*t3+3*t2)+tangents[lo][1]*(t3-2*t2+u)+tangents[hi][0]*(t3-t2)
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
        # events: last time of each text-key line; keys: every (time, line) in file order
        # (repeated keys such as 'soundgen: left' need the full list; npc_anim.py).
        self.nodes={};self.parents={};self.channels={};self.events={};self.keys=[]
        def visit(node,parent):
            if not isinstance(node,self.N.NiNode):return
            name=node.name.decode('cp1252').casefold()
            if name in self.nodes:raise ValueError('Duplicate skeleton node '+name)
            self.nodes[name]=node;self.parents[name]=parent
            e=node.extra_data
            while e:
                if isinstance(e,self.N.NiTextKeyExtraData):
                    for key in e.text_keys:
                        for line in key.value.decode('cp1252').splitlines():
                            self.events[line.strip().casefold()]=key.time;self.keys.append((float(key.time),line.strip().casefold()))
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
                            vec=(lambda v:np.array(v.as_list())) if field=='position' else (lambda v:np.array(float(v)))
                            channels[field]=([k.time for k in group.keys],np.array([vec(k.value) for k in group.keys]))
                            channels[field+'_interpolation']=int(group.interpolation)
                            if int(group.interpolation)==2:
                                channels[field+'_tangents']=[(vec(k.backward),vec(k.forward)) for k in group.keys]
                c=c.next_controller
            self.channels[name]=channels
        channels=self.channels[name]
        if 'rotation' in channels:m[:3,:3]=quat_matrix(blend_keys(*channels['rotation'],time,True,channels['rotation_interpolation']))*node.scale
        if 'position' in channels:m[3,:3]=blend_keys(*channels['position'],time,interpolation=channels['position_interpolation'],tangents=channels.get('position_tangents'))
        if 'scale' in channels:m[:3,:3]*=float(blend_keys(*channels['scale'],time,interpolation=channels['scale_interpolation'],tangents=channels.get('scale_tangents')))/node.scale
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

def rigid_attachment(part, offset):
    """Equipment uses its attachment convention before the animated bone.

    Carried TES3 lights rotate -90 degrees about X on Shield Bone; BoneOffset
    is a translation AFTER that rotation (row-vector convention).
    """
    matrix=np.eye(4)
    if part.get('carried_light'):
        matrix[:3,:3]=((1,0,0),(0,0,-1),(0,1,0))
    elif part['attach'].startswith('Left'):
        matrix[0,0]=-1
    matrix[3,:3]=offset
    return matrix

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
        def walk(node,parent,hidden=False,root=False,rule='morrowind'):
            if not isinstance(node,N.NiAVObject):return
            # Collision geometry is never drawn (weapons and shields carry it).
            if isinstance(node,N.NiNode) and node.name.lower()==b'rootcollisionnode':return
            local=np.array(node.get_transform().as_list())
            if root:local=root_local(local,rule)
            transform=local@parent
            hidden=hidden or bool(node.flags&1)
            nodes.append((node,transform,hidden))
            for child in getattr(node,'children',[]):
                if child:walk(child,transform,hidden)
        rule=check_root_rule(appearance.get('root_rule') or _root_rule)
        for root in data.roots:walk(root,np.eye(4),root=True,rule=rule)
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
                attach=part['attach'];mirror=rigid_attachment(part,offset)
                mirrored=attach.startswith('Left') and not part.get('carried_light')
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


def simplify_head_locked(points, faces, quota):
    """Head or hair reduction that opens no new hole (NPC-HEAD-DECIMATION-33, npc_head_reducer locked): the
    boundary-locked quadric reducer of the static meshes (mold_shell.quadric_simplify, static_lod's
    lock_boundaries rule): every rim vertex keeps its place, a rim edge never collapses, no face turns by
    more than acos(LOCKED_MAX_TURN) from its original normal. points/faces: the welded shape. A shape whose rim
    leaves fewer collapses than its quota keeps the smallest valid mesh (a few faces over the quota; the
    alias face limit is checked by the bake as before)."""
    from mold_shell import quadric_simplify
    from static_lod import LOCKED_MAX_TURN, boundary_vertices
    faces = np.asarray(faces, dtype=np.int64)
    if quota >= len(faces):
        return points, faces
    v, f = quadric_simplify(points, faces, [int(quota)], max_turn=LOCKED_MAX_TURN,
                            locked=boundary_vertices(faces), anchored=True)[int(quota)]
    return np.asarray(v, float), np.asarray(f, dtype=np.int32)


def simplify_shell_components(points, faces, quota):
    """Retain every disconnected panel under the existing shell tests.

    Only the overflow retry uses this path. A whole-shape QEM reduction may
    discard an entire disconnected robe panel before the shell check notices.
    Give every original component a share, then require both its own shell and
    the combined shell to retain the same area/extent fractions as before.
    """
    from mesh_geometry import connected_components
    groups = connected_components(points, np.column_stack((faces, np.zeros(len(faces), dtype=int))))
    if len(groups) < 2:
        return None
    def area(p, f):
        return np.linalg.norm(np.cross(p[f[:, 1]]-p[f[:, 0]], p[f[:, 2]]-p[f[:, 0]]), axis=1).sum()
    def valid(p, f, original, original_faces):
        return len(f) and np.isfinite(p).all() and area(p, f) >= .8*area(original, original_faces) and \
            np.all(np.ptp(p, axis=0) >= .7*np.ptp(original, axis=0))
    vertices, triangles = [], []
    for ids in groups:
        used, remap = np.unique(faces[np.asarray(ids)], return_inverse=True)
        original = points[used]; original_faces = remap.reshape(-1, 3)
        share = max(4, int(round(quota*len(original_faces)/len(faces))))
        p, f = simplify_shape(original, original_faces.astype(np.int32), share, True) \
            if len(original_faces) > share else (original, original_faces)
        if not valid(p, f, original, original_faces):
            raise ValueError('Disconnected shell component lost its authored area or extent')
        triangles.extend((f+len(vertices)).tolist()); vertices.extend(p.tolist())
    p, f = np.asarray(vertices), np.asarray(triangles, dtype=int)
    if not valid(p, f, points, faces):
        raise ValueError('Combined shell lost its authored area or extent')
    return p, f


def player_leg_section_ok(reference, reference_faces, candidate, candidate_faces, minimum=.75,
                          reference_parts=None, candidate_parts=None):
    """Check the rest-pose visible leg union against the earlier body mesh.

    Both models are complete, equivalently posed alias surfaces. When per-face
    body-part labels are supplied, only lower/upper leg parts participate. A
    Khajiit tail must not inflate the reference leg width if it later decimates.
    This still checks the union of overlapping trouser/limb fragments.
    It is a numeric candidate gate, not visual acceptance.
    """
    if (reference_parts is None) != (candidate_parts is None):
        raise ValueError('Player leg section labels must cover both models')
    if reference_parts is not None:
        if len(reference_parts)!=len(reference_faces) or len(candidate_parts)!=len(candidate_faces):
            raise ValueError('Player leg section labels must cover every face')
        leg_parts=np.arange(17,23)
        reference_faces=reference_faces[np.isin(reference_parts,leg_parts)]
        candidate_faces=candidate_faces[np.isin(candidate_parts,leg_parts)]
        if not len(reference_faces) or not len(candidate_faces):
            return False
    lo, hi = float(reference[:, 2].min()), float(reference[:, 2].max())
    mid = float(reference[:, 0].min() + reference[:, 0].max()) / 2
    def widths(points, faces, height, side):
        edges = ((0, 1), (1, 2), (2, 0))
        cuts = []
        tri = points[faces]
        tri = tri[(tri[:, :, 0].mean(axis=1) < mid) if side < 0 else
                  (tri[:, :, 0].mean(axis=1) >= mid)]
        for a, b in edges:
            za, zb = tri[:, a, 2], tri[:, b, 2]
            crossing = ((za <= height) & (zb >= height) | (zb <= height) & (za >= height))
            crossing &= np.abs(zb - za) > 1e-6
            if np.any(crossing):
                t = ((height - za[crossing]) / (zb[crossing] - za[crossing]))[:, None]
                cuts.append(tri[crossing, a, :2] + t * (tri[crossing, b, :2] - tri[crossing, a, :2]))
        if not cuts:
            return None
        xy = np.concatenate(cuts)
        return np.ptp(xy, axis=0) if len(xy) >= 2 else None
    if hi - lo < 1e-4:
        return True
    for side in (-1, 1):
        valid = 0
        for share in (.25, .35, .45):
            height = lo + (hi - lo) * share
            original = widths(reference, reference_faces, height, side)
            if original is None or max(original) < .02 * (hi - lo):
                continue
            valid += 1
            after_widths = widths(candidate, candidate_faces, height, side)
            if after_widths is None:
                return False
            for before, after in zip(original, after_widths):
                if before >= .02 * (hi - lo) and after < minimum * before:
                    return False
        if valid < 2:
            return False
    return True

# Heads keep their original geometry (project decision 2026-10-09, NPC-HEAD-DECIMATION-33).
# The whole-model bake used to fit a humanoid into 480 triangles; the head got at
# most 120 of them and was decimated with the rest, which left faces
# unrecognisable (Fargoth). Like Dagoth Ur's mask profile
# (config/gallery_model_quality.json: exact minimum_faces), the head part and the
# head-attached hair/helmet part (body part slots 0 and 1) now keep every original
# triangle; the reduction comes out of clothing and body, and the budget is raised
# only as far as that needs, within the alias face limits (666/777/1024).
# --npc-head-detail budget (AMIWIND_NPC_HEAD_DETAIL=budget) keeps the previous
# bake, byte for byte (DON'T DELETE ANY METHOD).
HEAD_SLOTS=(0,1)
ALIAS_FACE_LIMITS=(666,777,1024)
# The plan of this process's last whole-model bake (receipts: which shapes stayed
# exact, whether the hair/helmet was reduced or torso shells were given up).
LAST_PLAN={}

class AliasOverflow(ValueError):
    """The bake produced more faces than its alias face limit (over: by how many)."""
    def __init__(self,message,over=0):
        super().__init__(message);self.over=int(over)

def _budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames):
    """The previous whole-model split (--npc-head-detail budget), unchanged."""
    if face_limit not in ALIAS_FACE_LIMITS:raise ValueError('Unsupported alias face limit')
    ceiling=face_limit if minimum_faces else 480
    if not 64<=budget<=ceiling:raise ValueError('Triangle budget outside allowed profile')
    minimum_faces=minimum_faces or {}
    # Companion poses retain the original model's head topology/face quota.
    if reference_frames is not None and (not isinstance(reference_frames,int) or
            reference_frames<1 or any(reference_frames>len(s['positions']) for s in shapes)):
        raise ValueError('Invalid reference frame count')
    if set(minimum_faces)-{s.get('name','') for s in shapes}:raise ValueError('Missing protected model shape')
    for s in shapes:
        required=minimum_faces.get(s.get('name',''),0)
        if not isinstance(required,int) or not 0<=required<=len(s['faces']):raise ValueError('Invalid protected shape budget')
    weights=np.array([len(s['faces'])*(1.7 if s['part']==0 else 1) for s in shapes],dtype=float);weights/=weights.sum()
    quotas=np.array([max(minimum_faces.get(s.get('name',''),0),min(120,len(s['faces'])) if s['part']==0 and (reference_frames if reference_frames is not None else len(s['positions']))>8 else 4) for s in shapes],int);remaining=budget-int(quotas.sum())
    if remaining<0:raise ValueError('Too many separate shapes for budget')
    quotas+=np.floor(weights*remaining).astype(int)
    return quotas

# Body classes of the original-head bake, in the order they give up triangles
# when the face limit is tight (maintainer, 9 October 2026): hair/helmet first, then
# small details, then the torso, last the limbs, each never below its floor (its
# silhouette count, simplify_shape, capped at its budget-bake share).
LIMB_SLOTS=frozenset(range(6,23))|{26}
CUT_ORDER=('hair','detail','torso','limb')
DETAIL_EXTENT=.1            # a body shape smaller than this share of the actor's height

def body_classes(shapes,actor_height):
    """head / hair / detail / torso / limb for each shape (original-head bake)."""
    out=[]
    for s in shapes:
        if s['part']==0:out.append('head')
        elif s['part']==1:out.append('hair')
        elif float(np.ptp(s['positions'][0],axis=0).max())<DETAIL_EXTENT*actor_height:out.append('detail')
        elif s['part'] in LIMB_SLOTS:out.append('limb')
        else:out.append('torso')
    return out

def silhouette_floors(shapes,classes):
    """Per shape: the fewest triangles its shell-preserving reduction keeps
    (area and extent, simplify_shape); 4 for details, all faces for a head. bake
    caps a body shape's floor at its budget-bake share."""
    out=[]
    for s,c in zip(shapes,classes):
        n=len(s['faces'])
        if c=='head':out.append(n);continue
        if c=='detail' or n<=4:out.append(min(n,4));continue
        points,ix=np.unique(np.round(s['positions'][0],5),axis=0,return_inverse=True)
        out.append(min(n,len(simplify_shape(points,ix[s['faces']].astype(np.int32),4,True)[1])))
    return out

def head_plan(shapes,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,head_detail=None,
              floors=None,classes=None,extra_cut=0):
    """The whole-model bake plan: quotas, the shapes kept exactly and the alias face limit.

    budget mode: the previous split. original mode (default): every shape of body part
    slot 0 (head) keeps its exact original triangles; slot 1 (hair or helmet) too,
    while it fits. Every other shape wants what the budget split gave it, but never
    less than its floor (floors: silhouette_floors; without them 4 faces, or its
    protected minimum). The limit is the caller's face_limit, raised to the smallest
    of 666/777/1024 that holds the plan (a raised-limit model mixes 16- and 8-texel
    face tiles in its 480-row skin: mixed_tile_skin). When even 1,024 is too tight,
    triangles come off in CUT_ORDER: hair/helmet, details, torso, limbs, each down to
    its floor; extra_cut takes that many more (a bake's measured overshoot). If the
    head and every floor do not fit, the plan is 'lod_only': no original-head model
    for this appearance (the budget bake is used and recorded), never stick limbs.
    """
    from mesh_geometry_env import npc_head_detail
    quotas=_budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames)
    mode=npc_head_detail(head_detail)
    plan={'mode':mode,'quotas':quotas,'protected':frozenset(),'face_limit':face_limit,
          'head_faces':0,'hair_reduced':False,'lod_only':False,'cuts':{}}
    if mode=='budget' or not any(s['part'] in HEAD_SLOTS for s in shapes):return plan
    minimum_faces=minimum_faces or {}
    if classes is None:classes=['head' if s['part']==0 else 'hair' if s['part']==1 else 'torso' for s in shapes]
    n=[len(s['faces']) for s in shapes]
    floor=[]
    for i,(s,c) in enumerate(zip(shapes,classes)):
        if c=='head':floor.append(n[i]);continue
        f=max(4,minimum_faces.get(s.get('name',''),0),floors[i] if floors is not None else 0)
        floor.append(min(n[i],f))
    want=[n[i] if c in ('head','hair') else max(floor[i],min(int(quotas[i]),n[i])) for i,c in enumerate(classes)]
    if sum(floor)>ALIAS_FACE_LIMITS[-1]:
        plan.update(mode='budget',lod_only=True);return plan
    target=sum(want)
    limit=next((l for l in ALIAS_FACE_LIMITS if l>=face_limit and l>=target),ALIAS_FACE_LIMITS[-1])
    over=max(0,target-limit)+int(extra_cut)
    cuts={}
    for cls in CUT_ORDER:
        idx=[i for i,c in enumerate(classes) if c==cls and want[i]>floor[i]]
        room=sum(want[i]-floor[i] for i in idx)
        if over<=0 or not room:continue
        cut=min(over,room);taken=0
        for i in idx:
            t=(want[i]-floor[i])*cut//room;want[i]-=t;taken+=t
        for i in sorted(idx,key=lambda i:floor[i]-want[i]):
            if taken>=cut:break
            if want[i]>floor[i]:want[i]-=1;taken+=1
        over-=cut;cuts[cls]=cut
    if over>0:
        plan.update(mode='budget',lod_only=True);return plan
    protected=frozenset(i for i,c in enumerate(classes) if c in ('head','hair') and want[i]==n[i])
    plan.update(quotas=np.array(want,int),protected=protected,face_limit=limit,cuts=cuts,
                head_faces=sum(n[i] for i in protected),
                hair_reduced=any(c=='hair' and want[i]<n[i] for i,c in enumerate(classes)))
    return plan

def bake_quotas(shapes,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,head_detail=None):
    """Per-shape triangle quotas of one complete appearance (the whole-model bake).

    A shape's quota depends on every other shape in the outfit (MODULAR_NPCS.md):
    the same body part gets a different quota in a different outfit. Heads keep
    their original triangles unless head_detail is 'budget' (head_plan).
    """
    return head_plan(shapes,budget,face_limit,minimum_faces,reference_frames,head_detail)['quotas']

def _retry_head_reducer(run, reducer):
    """run(reducer); when the boundary-locked head reducer leaves an appearance over the alias vertex budget
    (it keeps every rim vertex, so a head can stay a few faces over its quota), that appearance alone is baked
    again with the previous reducer and the fallback is logged (v0.0.43-dev4 build: the npcs stage stopped
    on 'Alias vertex budget exceeded'; NPC-HEAD-DECIMATION-33)."""
    try:
        return run(reducer)
    except AliasOverflow as overflow:
        if reducer != 'locked' or str(overflow) != 'Alias vertex budget exceeded':
            raise
        HEAD_REDUCER_FALLBACKS.append(overflow.over)
        print('npc bake: locked head reducer over the alias vertex budget by %s; this appearance uses the '
              'previous head reducer' % overflow.over, flush=True)
        return run(None)


HEAD_REDUCER_FALLBACKS = []


def bake(shapes,materials,textures,palette,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,
         quotas=None,shell_height=None,head_detail=None,lod_only='budget',preserve=None,body_skin_rows=None,
         body_leg_contour=False,face_parts=None,full_frame_budget=None):
    """One topology shared by every frame, per-face tiny UV atlas patches.

    Default: quotas from head_plan (the whole-appearance bake). Heads (body part
    slots 0 and 1) keep their original geometry, like Dagoth Ur's mask profile,
    because decimated faces were unrecognisable (Fargoth, NPC-HEAD-DECIMATION-33);
    head_detail='budget' (or AMIWIND_NPC_HEAD_DETAIL=budget) is the previous bake.
    Body, clothing and a reduced hair/helmet keep their silhouette (shell-preserving
    reduction, silhouette_floors). If the reduced model overshoots the face limit,
    the overshoot comes off in CUT_ORDER and the reduction runs again; the head
    never does. An appearance whose head and floors cannot fit bakes the budget
    model and is recorded lod_only (LAST_PLAN) instead of getting stick limbs;
    lod_only='raise' raises ValueError instead (a near level is then not made).
    quotas/shell_height: a modular part bake (MODULAR_NPCS.md) with explicit
    per-shape quotas and the reference actor height for shell preservation;
    preserve: explicit per-shape shell flags (the flag the whole-appearance bake
    would compute for that shape in its outfit), overriding shell_height.
    """
    from mesh_geometry_env import npc_head_detail, npc_head_reducer
    if full_frame_budget is not None and (type(full_frame_budget) is not int or full_frame_budget <= 0):
        raise ValueError('Invalid full-frame byte budget')
    if quotas is not None:
        if face_limit not in ALIAS_FACE_LIMITS:raise ValueError('Unsupported alias face limit')
        quotas=np.array(quotas,int)
        if len(quotas)!=len(shapes) or np.any(quotas<1) or int(quotas.sum())>face_limit:
            raise ValueError('Invalid explicit part quotas')
        protected=frozenset() if npc_head_detail(head_detail)=='budget' else frozenset(
            i for i,s in enumerate(shapes) if s['part'] in HEAD_SLOTS and quotas[i]>=len(s['faces']))
        if face_parts is not None:face_parts.clear()
        return _retry_head_reducer(lambda reducer:_bake(shapes,materials,textures,palette,face_limit,minimum_faces,
                     quotas,shell_height,protected,False,
                     preserve=preserve,body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,
                     face_parts=face_parts,head_reducer=reducer),
                     npc_head_reducer() if npc_head_detail(head_detail)=='budget' else None)
    mode=npc_head_detail(head_detail)
    floors=classes=None;shell_set=None
    if mode=='original' and any(s['part'] in HEAD_SLOTS for s in shapes):
        height=float(shell_height) if shell_height else (max(s['positions'][0,:,2].max() for s in shapes)-
                                                          min(s['positions'][0,:,2].min() for s in shapes))
        classes=body_classes(shapes,height);silhouette=silhouette_floors(shapes,classes)
        # A body shape's floor: its silhouette count, but never more than the budget
        # bake gave it (that body is never thinner than the budget model's).
        share=_budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames)
        floors=[f if c in ('head','hair','detail') else min(f,max(4,int(q))) for f,c,q in zip(silhouette,classes,share)]
    extra=0
    for _ in range(16):
        plan=head_plan(shapes,budget,face_limit,minimum_faces,reference_frames,head_detail,floors,classes,extra)
        if classes is not None:
            # Shapes whose quota holds their silhouette keep it in the reduction.
            shell_set=frozenset(i for i,c in enumerate(classes) if c in ('hair','torso','limb')
                                and plan['quotas'][i]>=silhouette[i])
        if plan['lod_only'] and lod_only=='raise':
            raise ValueError('Original head does not fit the alias face limit (lod_only)')
        try:
            if face_parts is not None:face_parts.clear()
            # head and hair of the budget bake: the boundary-locked reducer by default (npc_head_reducer)
            head_reducer=npc_head_reducer() if plan['mode']=='budget' else None
            result=_bake(shapes,materials,textures,palette,plan['face_limit'],minimum_faces,plan['quotas'],
                         shell_height,plan['protected'],plan['face_limit']!=face_limit,
                         None if plan['mode']=='budget' else shell_set,preserve=preserve,
                         body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,face_parts=face_parts,
                         head_reducer=head_reducer)
        except AliasOverflow as overflow:
            if str(overflow).startswith('Player leg'):raise
            if plan['mode']=='budget':
                # NPC-BAKE-VERTEX-32: preserve every disconnected visible panel;
                # successful normal bakes and all animation samples are unchanged.
                if str(overflow) != 'Alias vertex budget exceeded':raise
                retry=lambda reducer:_bake(shapes,materials,textures,palette,plan['face_limit'],minimum_faces,
                             plan['quotas'],shell_height,plan['protected'],False,None,preserve=preserve,
                             body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,
                             face_parts=face_parts,shell_components=True,full_frame_budget=full_frame_budget,
                             head_reducer=reducer)
                result=_retry_head_reducer(retry,head_reducer)
            else:
                extra+=overflow.over+2;continue
        LAST_PLAN.clear()
        LAST_PLAN.update(mode=plan['mode'],face_limit=plan['face_limit'],head_faces=plan['head_faces'],
                         protected_shapes=len(plan['protected']),hair_reduced=plan['hair_reduced'],
                         lod_only=plan['lod_only'],cuts=dict(plan['cuts']),extra_cut=extra)
        return result
    raise ValueError('Original head does not fit the alias face limit')

def transfer_vertex(point, triangles):
    """Carry a simplified vertex's residual with its animated source triangle.

    Clipped barycentric weights keep the surface anchor bounded. A proper
    best-fit rotation and RMS triangle scale carry the residual, without the
    large extrapolation coefficients of a nearly collinear triangle basis.
    Rigid transforms and positive uniform scales are exact. General skinned
    deformation is approximate; no three points determine off-surface skinning.
    This is conversion only; the runtime still selects ordinary alias frames.
    """
    rest = triangles[0]
    edges = (rest[1:] - rest[:1]).T
    xy = np.linalg.pinv(edges) @ (point - rest[0])
    weights = np.clip(np.array([1 - xy.sum(), *xy]), 0, 1)
    weights /= weights.sum()
    anchor = np.einsum('v,fvc->fc', weights, triangles)
    residual = point - weights @ rest
    centered = triangles - triangles.mean(axis=1, keepdims=True)
    energy = np.einsum('fvc,fvc->f', centered, centered)
    cross_length = np.linalg.norm(np.cross(edges[:, 0], edges[:, 1]))
    edge_product = np.linalg.norm(edges[:, 0]) * np.linalg.norm(edges[:, 1])
    if cross_length <= 1e-10 * edge_product:
        # A collinear/point reference has no recoverable surface orientation.
        result = anchor + residual
    else:
        covariance = np.einsum('vi,fvj->fij', centered[0], centered)
        left, _, right = np.linalg.svd(covariance)
        rotation = left @ right
        # Reject reflection: the residual belongs to the same side of the limb.
        left[:, :, -1] *= np.where(np.linalg.det(rotation) < 0, -1., 1.)[:, None]
        rotation = left @ right
        scale = np.sqrt(energy / energy[0])
        result = anchor + np.einsum('i,fij->fj', residual, rotation) * scale[:, None]
    result[0] = point  # preserve the simplifier's exact floating-point rest pose
    return result


def _bake(shapes,materials,textures,palette,face_limit,minimum_faces,quotas,shell_height,protected,raised,
          shell_set=None,preserve=None,body_skin_rows=None,body_leg_contour=False,face_parts=None,shell_components=False,full_frame_budget=None,
          head_reducer=None):
    """shell_set None: the previous rule (large torso panels keep their shell); else the
    shape indices whose reduction keeps its silhouette (original-head bake). head_reducer 'locked': head and
    hair shapes (HEAD_SLOTS) are reduced with simplify_head_locked; None/'default': the previous reducer."""
    from scipy.spatial import cKDTree
    minimum_faces=minimum_faces or {}
    actor_height = max(s['positions'][0,:,2].max() for s in shapes)-min(s['positions'][0,:,2].min() for s in shapes)
    if shell_height is not None:
        if not shell_height>0:raise ValueError('Invalid shell reference height')
        actor_height=float(shell_height)
    if preserve is not None and len(preserve)!=len(shapes):raise ValueError('Invalid explicit shell flags')
    skin=Image.new('RGB',(512,256));allframes=[];outfaces=[];outuv=[];fi=0;tiles=[]
    # Reduce every shape first: an outfit past the face limit is refused before
    # the per-face texture work (the retry with a smaller body share is cheap).
    reduced=[]
    for index,(shape,quota) in enumerate(zip(shapes,quotas)):
        faces=shape['faces'];p=shape['positions'][0]
        exact=index in protected or minimum_faces.get(shape.get('name',''),0)==len(faces)
        points,ix=np.unique(np.round(p,5),axis=0,return_inverse=True);ff=ix[faces]
        if exact:points=p;ff=faces
        if len(ff)>quota:
            # preserve: explicit shell flags per shape (tools/npc_parts.py, --npc-models parts).
            preserve_shell = bool(preserve[index]) if preserve is not None else \
                (shape['part']==3 and np.ptp(p[:,2]) >= .2*actor_height) if shell_set is None \
                else index in shell_set
            source_points=points; source_faces=ff
            if head_reducer=='locked' and shape['part'] in HEAD_SLOTS:
                points,ff=simplify_head_locked(points,ff,int(quota))
            else:
                points,ff=simplify_shape(points,ff.astype(np.int32),int(quota),preserve_shell)
            if shell_components and preserve_shell:
                candidate=simplify_shell_components(source_points,source_faces,int(quota))
                if candidate is not None and len(candidate[1]) < len(ff):
                    points,ff=candidate
            if body_leg_contour and (shape['part'] in (19,20) or
                                     (body_leg_contour==2 and shape['part'] in (21,22))):
                # Player-body fallback only: a tiny knee quota can keep the
                # triangle count yet pull the visible trouser contour inward.
                # Restore 90% of each knee's authored side-to-side extent;
                # the later fallback also restores the upper thigh's extent.
                # The complete assembled leg must still pass its 75% section
                # guard before the model is accepted. No NPC bake opts in.
                source_lo,source_hi=np.min(source_points[:,0]),np.max(source_points[:,0])
                reduced_lo,reduced_hi=np.min(points[:,0]),np.max(points[:,0])
                required=(1.0 if body_leg_contour==2 and shape['part'] in (21,22) else .9)*(source_hi-source_lo)
                width=reduced_hi-reduced_lo
                if 1e-6<width<required:
                    points=points.copy()
                    pivot=np.mean(source_points[:,0])
                    points[:,0]=(points[:,0]-pivot)*(required/width)+pivot
        reduced.append((exact,points,ff))
    total=sum(len(ff) for _,_,ff in reduced)
    if total>face_limit:raise AliasOverflow('Alias vertex budget exceeded',total-face_limit)
    if full_frame_budget is not None:
        # Overflow-only NPC retry: choose smaller geometry before atlas work,
        # preserving the entire source sample list under the existing byte cap.
        from npc_anim import alias_bytes
        rows = 256 if total <= 512 else ((face_limit+31)//32)*16
        if alias_bytes(len(shapes[0]['positions']),total*3,total,512,rows) > full_frame_budget:
            raise AliasOverflow('Alias byte budget exceeded with full samples')
    for shape,(exact,points,ff) in zip(shapes,reduced):
        orig=shape['positions'];faces=shape['faces'];p=orig[0]
        old_tri=p[faces];centres=old_tri.mean(axis=1);tree=cKDTree(centres)
        # Every pseudo-inverse below is of one original triangle's edge matrix:
        # computed once per shape. Batched results are bitwise equal to the
        # per-matrix calls (tests/test_npc_parts.py), so output bytes are unchanged.
        inverse=np.linalg.pinv(np.stack((old_tri[:,1]-old_tri[:,0],old_tri[:,2]-old_tri[:,0]),axis=2))
        mat=materials[shape['material']];tex=textures.get(mat['texture_index'])
        for source_face,face in enumerate(ff):
            triangle=points[face]
            if exact:
                # Protected shapes keep their authored vertices in every frame
                # (no transfer search: the result would be replaced anyway).
                allframes.append(orig[:,face,:].copy())
            else:
                # Transfer each decimated vertex via the nearest original triangle;
                # carry its rest-pose offset with that surface as the limb moves.
                animated=[]
                for point in triangle:
                    ti=int(tree.query(point)[1])
                    animated.append(transfer_vertex(point,orig[:,faces[ti]]))
                allframes.append(np.stack(animated,axis=1))
            tile=np.zeros((16,16,3),np.uint8)
            yy,xx=np.mgrid[0:16,0:16];w=np.column_stack((np.maximum(0,1-(xx.ravel()+yy.ravel())/15),xx.ravel()/15,yy.ravel()/15));w/=w.sum(1)[:,None]
            samples=w@triangle
            if exact:
                # Protected shapes retain authored triangles and UV seams.
                # Nearby folds must not lend their texture to the original face.
                sampleuv=w@shape['uv'][faces[source_face]]
                samplecolour=w@shape['colours'][faces[source_face],:3]
            else:
                # Sample the closest original surface per texel. Projecting an
                # entire decimated face onto one tiny source triangle crosses UV
                # seams and produces stripes, particularly on armour and faces.
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
            if tex is None:colours=np.full((len(samples),3),220.)
            else:
                px=np.floor(sampleuv[:,0]*tex.shape[1]).astype(int)%tex.shape[1];py=np.floor(sampleuv[:,1]*tex.shape[0]).astype(int)%tex.shape[0]
                colours=tex[py,px,:3].astype(float)
            colours*=samplecolour*np.array(mat['diffuse']);tile=np.clip(colours,0,255).astype(np.uint8).reshape(16,16,3)
            if fi>=face_limit:raise AliasOverflow('Alias vertex budget exceeded',1)
            ty_required=((fi//32)+1)*16
            if ty_required>skin.height:
                # Gallery compacts these tiles before MDL encoding, retaining
                # the renderer's 480-row skin bound even for extended models.
                larger=Image.new('RGB',(512,((face_limit+31)//32)*16));larger.paste(skin,(0,0));skin=larger
            tx=fi%32*16;ty=fi//32*16;skin.paste(Image.fromarray(tile),(tx,ty));outuv.extend([(tx,ty),(tx+15,ty),(tx,ty+15)])
            if raised or body_skin_rows:tiles.append((tile,shape['part']))
            outfaces.append([fi*3,fi*3+2,fi*3+1]);fi+=1
            if face_parts is not None:face_parts.append(shape['part'])
    outuv=np.array(outuv)
    if raised:skin,outuv=mixed_tile_skin(tiles)
    elif body_skin_rows:skin,outuv=mixed_tile_skin(tiles,rows=body_skin_rows)
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    return np.concatenate(allframes,axis=1),np.array(outfaces),outuv,skin.quantize(palette=pal,dither=Image.Dither.NONE)

SHARED_SKIN=(512,480)        # the renderer's skin bound (MAX_LBM_HEIGHT 480 rows)
MIXED_SKIN_ROWS=480          # skin rows of a raised-limit (original-head) model
# 16-texel tiles go to the faces seen most first: the face (slot 0), then the
# torso, neck and hands, then the rest of the body, last the hair or helmet.
TILE_PRIORITY={0:0,2:1,3:1,6:1,7:1,1:3}

def mixed_tile_rows(n16,n8):
    return 16*-(-n16//32)+8*-(-n8//64)

def mixed_tile_skin(tiles,rows=MIXED_SKIN_ROWS):
    """One skin with 16-texel tiles where they fit and 8-texel tiles for the rest.

    A raised-limit (original-head) model has more faces than 16-texel tiles can hold
    in the renderer's 480-row skin. Halving every tile left its body a quarter of the
    texels of the budget model (blurrier up close than far away: NPC-NEAR-SKIN-TEXELS-33).
    Here the faces seen most keep 16 texels (TILE_PRIORITY: face, torso and hands,
    body, hair) as far as the rows allow; the rest get 8-texel tiles below them.
    tiles: [(16 x 16 x 3 array, body part slot)] in face order. Returns (RGB skin, uv).
    """
    n=len(tiles)
    order=sorted(range(n),key=lambda i:(TILE_PRIORITY.get(tiles[i][1],2),i))
    big=n
    while big and mixed_tile_rows(big,n-big)>rows:big-=1
    if mixed_tile_rows(big,n-big)>rows:raise ValueError('Alias skin rows exceeded')
    chosen=set(order[:big]);top=16*-(-big//32)
    skin=Image.new('RGB',(512,max(1,mixed_tile_rows(big,n-big))));uv=[];a=b=0
    for i,(tile,_) in enumerate(tiles):
        if i in chosen:
            tx,ty=a%32*16,a//32*16;a+=1;skin.paste(Image.fromarray(tile),(tx,ty));size=15
        else:
            tx,ty=b%64*8,top+b//64*8;b+=1;skin.paste(Image.fromarray(np.ascontiguousarray(tile[1::2,1::2])),(tx,ty));size=7
        uv.extend([(tx,ty),(tx+size,ty),(tx,ty+size)])
    return skin,np.array(uv)

def shared_vertex_mdl(shapes,materials,textures,palette):
    """A whole model with every original triangle on its original vertices.

    The face-tile bake gives each triangle its own texture tile and three vertices,
    so it stops at 1,024 triangles (3,072 vertices: the renderer's extended path).
    This encoding keeps the source vertices and their texture coordinates and packs
    the model's original textures into one skin atlas (shelf packing, halved until
    it fits 512 x 480), so a model of up to 1,999 vertices takes the renderer's
    original alias path, which has no triangle cap (Dagoth Ur: 2,254 triangles on
    1,741 vertices; NPC-DAGOTH-BODY-DECIMATION-33). Texture coordinates are clamped
    to their texture (no wrap across the atlas). Shapes must have plain vertex
    colours and diffuse (no per-vertex tint in this encoding).
    """
    keys=[]
    for s in shapes:
        m=materials[s['material']]
        if not (np.allclose(s['colours'][:,:3],1) and np.allclose(m['diffuse'],1)):
            raise ValueError('Shared-vertex encoding needs plain vertex colours and diffuse: '+s.get('name',''))
        keys.append(m['texture_index'])
    images={k:(textures[k] if k is not None and textures.get(k) is not None else np.full((4,4,4),220,np.uint8))
            for k in dict.fromkeys(keys)}
    for scale in (1,2,4,8):
        place={};x=y=row=width=0
        for k in sorted(images,key=lambda k:(-images[k].shape[0],str(k))):
            h,w=max(1,images[k].shape[0]//scale),max(1,images[k].shape[1]//scale)
            if x+w>SHARED_SKIN[0]:y+=row;x=row=0
            place[k]=(x,y,w,h);x+=w;row=max(row,h);width=max(width,x)
        height=y+row
        if height<=SHARED_SKIN[1] and width<=SHARED_SKIN[0]:break
    else:raise ValueError('Shared-vertex textures do not fit the skin')
    skin=Image.new('RGB',((width+3)//4*4,height))
    for k,(x0,y0,w,h) in place.items():
        tile=Image.fromarray(np.ascontiguousarray(images[k][:,:,:3]))
        if tile.size!=(w,h):tile=tile.resize((w,h),Image.Resampling.BOX)
        skin.paste(tile,(x0,y0))
    frames=[];faces=[];st=[];base=0
    for s,k in zip(shapes,keys):
        x0,y0,w,h=place[k];uv=np.clip(s['uv'],0,1)
        st.append(np.column_stack((x0+np.minimum(w-1,np.floor(uv[:,0]*w)),y0+np.minimum(h-1,np.floor(uv[:,1]*h)))))
        frames.append(s['positions']);faces.append(s['faces'][:,[0,2,1]]+base);base+=s['positions'].shape[1]
    frames=np.concatenate(frames,axis=1);faces=np.concatenate(faces);st=np.concatenate(st).astype(int)
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    return frames,faces,st,skin.quantize(palette=pal,dither=Image.Dither.NONE)

# Alias frame budget in bytes, not frames (TOOL-ALIAS-FRAMES-33): every frame costs a 28-byte
# header plus 4 bytes per vertex. The default is the previous worst case (64 named frames of a
# 1,999-vertex model), so a light model may carry more frames and a heavy one fewer; 256 frames
# at most (the engine's pose table).
ALIAS_FRAME_HEADER = 28
ALIAS_FRAME_BYTES = 64 * (ALIAS_FRAME_HEADER + 4 * 1999)
ALIAS_MAX_FRAMES = 256


def alias_frame_bytes(frames, vertices):
    return frames * (ALIAS_FRAME_HEADER + 4 * vertices)


def animated_mdl(frames,faces,uv,skin,vertex_limit=None,names=None,frame_bytes=ALIAS_FRAME_BYTES):
    """vertex_limit None: the smallest of 1999/2331/3072 that holds the model (an
    original-head bake past 666 faces; the image step lists such models in
    model-budgets.txt, which the engine needs for more than 2,000 vertices).
    names: one frame name per frame (at most 15 characters; default idleNN).
    frame_bytes: the model's budget for its vertex frames (alias_frame_bytes)."""
    if frames.ndim!=3 or frames.shape[2]!=3 or not np.isfinite(frames).all():raise ValueError('Invalid alias frames')
    nf,nv,_=frames.shape
    if vertex_limit is None:vertex_limit=next((l for l in (1999,2331,3072) if nv<=l),3072)
    if vertex_limit not in (1999,2331,3072):raise ValueError('Unsupported alias vertex limit')
    if not 1<=nf<=ALIAS_MAX_FRAMES or alias_frame_bytes(nf,nv)>frame_bytes or nv>vertex_limit or not len(faces):
        raise ValueError('Alias budget exceeded')
    if names is not None and (len(names)!=nf or any(not n or len(n.encode('ascii'))>15 for n in names)):raise ValueError('Alias frame names')
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
        data.extend(struct.pack('<i4B4B16s',0,*points.min(0),0,*points.max(0),0,(names[i] if names is not None else 'idle%02d'%i if i<100 else 'idle%03d'%i).encode()))
        data.extend(np.column_stack((points,np.zeros(nv,np.uint8))).astype(np.uint8).tobytes())
    return bytes(data)
