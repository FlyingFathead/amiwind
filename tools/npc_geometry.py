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
import sys

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
        fm=shape.get('face_material')
        faces.extend([[*(f+base),int(fm[k]) if fm is not None else shape['material']]
                      for k,f in enumerate(shape['faces'])])
    return np.array(vertices),np.array(faces,int)

SKIN_PREFIXES=('b_n_','b_v_','tri b_n_','tri b_v_','tri chest','tri right hand','tri left hand')

def is_skin(shape):
    """A bare body part (the race's own mesh) rather than worn armour or clothing."""
    return shape.get('name','').lower().startswith(SKIN_PREFIXES)

def merge_worn_pieces(shapes):
    """MESH-SEAM-METHOD-62, armoured outfits: the worn pieces of one limb slot (a pauldron's three parts, a greave's
    parts, a bracer's two) become ONE shape before reducing, so the slot is reduced as one piece with one width floor
    instead of each part falling to 4 faces (the Hlaalu guard: 69 shapes in 568 faces, bracers kept 0.01 of their
    width). Positions coincide where the parts meet, so the reducer's weld closes those seams. Each face keeps its own
    material (face_material). Shapes outside the limb slots, bare body parts, heads and hair are unchanged; a slot with
    one worn piece is unchanged. Returns (shapes, {merged shape name: [source names]})."""
    groups={}
    for i,s in enumerate(shapes):
        if s['part'] in LIMB_SLOTS and s['part'] not in HEAD_SLOTS and not is_skin(s):
            groups.setdefault(s['part'],[]).append(i)
    merged={};out=[];done=set()
    for i,s in enumerate(shapes):
        if i in done:continue
        idx=groups.get(s['part']) if s['part'] in groups and i in groups[s['part']] else None
        if not idx or len(idx)<2 or len({shapes[j]['positions'].shape[0] for j in idx})!=1:
            out.append(s);continue
        parts=[shapes[j] for j in idx];done.update(idx)
        off=np.cumsum([0]+[p['positions'].shape[1] for p in parts])
        name=parts[0].get('name','')+' (merged %d)'%len(parts)
        out.append({'name':name,'part':s['part'],
                    'positions':np.concatenate([p['positions'] for p in parts],axis=1),
                    'faces':np.concatenate([np.asarray(p['faces'])[:,:3]+off[k] for k,p in enumerate(parts)]),
                    'uv':np.concatenate([p['uv'] for p in parts]),
                    'colours':np.concatenate([p['colours'] for p in parts]),
                    'material':parts[0]['material'],
                    'face_material':np.concatenate([np.full(len(p['faces']),
                        p['material'],int) if p.get('face_material') is None else np.asarray(p['face_material'])
                        for p in parts])})
        merged[name]=[p.get('name','') for p in parts]
    return out,merged

def worn_merge():
    """AMIWIND_NPC_WORN_MERGE: merge (default from v0.0.62: merge_worn_pieces before the bake) or pieces (each worn
    piece reduced alone, the step before). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_WORN_MERGE','').strip() or 'merge'
    if value not in ('merge','pieces'):raise ValueError('AMIWIND_NPC_WORN_MERGE must be merge or pieces')
    return value=='merge'

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

HAIR_SHARES=('whole','head','plain')
HAIR_WHOLE_MARGIN=8         # faces kept free under the alias face limit: the locked reducer may leave a head a few over

def hair_share():
    """The hair or helmet's share of a budget-head bake (NPC-HAIR-BACK-MISSING-53): 'whole' (the default from
    v0.0.54: body part slot 1 keeps every original triangle when the model still fits its alias face limit, else
    'head'), 'head' (slot 1 takes the head's weight and floor) or 'plain' (the v0.0.53 split, byte for byte: slot 1
    gets 4 faces and a plain share). AMIWIND_NPC_HAIR_SHARE selects it; read here only, so only the stages that
    reach the NPC bake are keyed on it."""
    import os
    value=os.environ.get('AMIWIND_NPC_HAIR_SHARE','').strip() or 'whole'
    if value not in HAIR_SHARES:raise ValueError('AMIWIND_NPC_HAIR_SHARE must be whole, head or plain')
    return value

BODY_SHARES=('body','budget')

def body_share():
    """The body's share of an original-head bake (NPC-BODY-REGRESSION-62): 'body' (the default from v0.0.62: the
    budget split among the body shapes alone, the head and hair kept whole beside it, no more triangles than the
    previous plan) or 'budget' (v0.0.54 to v0.0.61, byte for byte: the body took what a split that also weighed the
    head and hair left it, down to 4 faces a limb). AMIWIND_NPC_BODY_SHARE selects it; read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_BODY_SHARE','').strip() or 'body'
    if value not in BODY_SHARES:raise ValueError('AMIWIND_NPC_BODY_SHARE must be body or budget')
    return value

def body_quotas(shapes,budget,classes):
    """Per shape: the budget split among the body shapes (every class but head and hair) by their triangles, at
    least 4 each; 0 for the head and hair (kept whole by the original-head plan)."""
    body=[i for i,c in enumerate(classes) if c not in ('head','hair')]
    out=np.zeros(len(shapes),int)
    if not body:return out
    n=np.array([len(shapes[i]['faces']) for i in body],float)
    base=np.minimum(4,n).astype(int);rest=max(0,int(budget)-int(base.sum()))
    out[body]=base+np.floor(n/n.sum()*rest).astype(int)
    return out

# The body check of a whole-model bake (NPC-BODY-REGRESSION-62, NPC-JOINT-GAPS-33, PLAYER-BODY-LEG-SHAPE-39): every
# limb slot (LIMB_SLOTS) keeps its width across the source's cross-section (limb_widths: Jiub's v0.0.61 upper legs and
# wrists 0.12, the repaired bake at least 0.60), and the neck (slot 2) is sampled against the baked model as
# lost_surface does, at BODY_CHECK_RATIO of the actor's largest extent (the guards' 4-face necks lost 3.5 to 4.6 %, the
# repaired ones at most 0.7 %).
BODY_CHECK_RATIO=0.02
BODY_LIMB_WIDTH=0.5         # under it: the bake retries with more faces for that part, then reports it
BODY_NECK_LOST=0.03
BODY_LIMB_FAIL=0.2          # a limb kept under a fifth of its width (Jiub's v0.0.61 legs: 0.12) stops the bake
BODY_NECK_FAIL=0.2          # a neck that lost a fifth of its surface stops the bake

def limb_widths(shapes,frame,faces,face_parts,face_shapes=None):
    """{slot: (width ratio, first shape index)} of every limb slot (LIMB_SLOTS): the baked faces of the slot against
    the slot's source shapes, across the source's two narrow principal axes (the limb's cross-section): the smaller
    of the two ratios of baked to source extent (5th to 95th percentile of face samples). 1.0 keeps the width."""
    faces=np.asarray(faces)[:,:3];face_parts=np.asarray(face_parts)
    out={}
    def ratio(src,baked):
        centre=src.mean(0);_,_,axes=np.linalg.svd(src-centre,full_matrices=False)
        r=[]
        for axis in axes[1:]:
            a=np.percentile((src-centre)@axis,[5,95]);b=np.percentile((baked-centre)@axis,[5,95])
            r.append(float((b[1]-b[0])/max(a[1]-a[0],1e-6)))
        return min(r)
    for slot in sorted({s['part'] for s in shapes} & LIMB_SLOTS):
        idx=[i for i,s in enumerate(shapes) if s['part']==slot]
        src=np.concatenate([face_samples(shapes[i]['positions'][0],shapes[i]['faces']) for i in idx])
        mine=faces[face_parts==slot] if len(face_parts)==len(faces) else faces[:0]
        if len(src)<8:continue
        if not len(mine):out[slot]=(0.0,idx[0]);continue
        best=(round(ratio(src,face_samples(frame,mine)),3),idx[0])
        if face_shapes is not None and len(face_shapes)==len(faces) and worn_widths():
            # MESH-SEAM-METHOD-62: every worn piece of the slot on its own (a bracer, a pauldron, a greave): the slot
            # as a whole kept 0.50 on a Hlaalu guard whose bracers kept 0.01 to 0.27 of their width ("pencil arms")
            fsh=np.asarray(face_shapes)
            for i in idx:
                if len(shapes[i]['faces'])<WORN_MIN_FACES:continue
                own=faces[fsh==i]
                s_i=face_samples(shapes[i]['positions'][0],shapes[i]['faces'])
                w=0.0 if not len(own) else ratio(s_i,face_samples(frame,own))
                if w<best[0]:best=(round(w,3),i)
        out[slot]=best
    return out

WORN_MIN_FACES=24               # a limb-slot piece this small is a detail (a buckle, a strap): not judged alone

def worn_widths():
    """AMIWIND_NPC_WORN_WIDTHS: each (default from v0.0.62: every piece of a limb slot judged on its own width, worn
    armour and clothing included) or slot (the slot as a whole, the step before). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_WORN_WIDTHS','').strip() or 'each'
    if value not in ('each','slot'):raise ValueError('AMIWIND_NPC_WORN_WIDTHS must be each or slot')
    return value=='each'

def body_check(shapes,frame,faces,face_parts=None,ratio=BODY_CHECK_RATIO,face_shapes=None):
    """[(shape index, part, name, measure, kind)] of the thin limbs (limb_widths under BODY_LIMB_WIDTH, with the
    baked face slots FACE_PARTS) and the neck gaps (a neck that lost more than BODY_NECK_LOST of its surface) of the
    baked FRAME/FACES; empty: the body is whole."""
    from scipy.spatial import cKDTree
    src=np.concatenate([s['positions'][0] for s in shapes])
    size=float((src.max(0)-src.min(0)).max()) or 1.0
    tree=None;out=[]
    for index,s in enumerate(shapes):
        if s['part']!=2:continue
        if tree is None:tree=cKDTree(face_samples(frame,np.asarray(faces)[:,:3]))
        samples=face_samples(s['positions'][0],s['faces'])
        if not len(samples):continue
        lost=float((tree.query(samples)[0]>ratio*size).mean())
        if lost>BODY_NECK_LOST:out.append((index,2,s.get('name',''),round(lost,3),'neck gap'))
    if face_parts is not None:
        for slot,(width,index) in limb_widths(shapes,frame,faces,face_parts,face_shapes).items():
            if width<BODY_LIMB_WIDTH:out.append((index,slot,shapes[index].get('name',''),width,'thin limb'))
    return out

JOINT_OPEN_SHARE=0.05       # design step 2 (3.5): at most this share of the joint length open
JOINT_MAX_GAP=0.5           # and no opening past 0.5 units (4 alias steps of a resident)
SPIKE_DISTANCE=1.0          # a reduced vertex farther than this from the source surface (NPC-GALLERY-SPIKE-33)
JOINT_FAIL_GAP=1.0          # an opening this wide left after the retries stops the bake (the v0.0.61 guards: 0.83)
AUDIT_MODES=('gate','check')
BODY_REDUCERS=('default','seams')

def body_reducer():
    """AMIWIND_NPC_BODY_REDUCER: seams (the default from v0.0.62, design step 3: the seam points locked on both
    sides, tools/npc_seams.py; an actor whose seams do not fit its total takes faces from the hair and head first and
    falls back to the free reducer only after that, recorded in its receipt) or default (each body shape reduced
    alone, rims free, as up to v0.0.62-dev1). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_BODY_REDUCER','').strip() or 'seams'
    if value not in BODY_REDUCERS:raise ValueError('AMIWIND_NPC_BODY_REDUCER must be default or seams')
    return value

def body_audit_mode():
    """AMIWIND_NPC_BODY_AUDIT: gate (default from v0.0.62: body_audit, the joints and spikes beside the widths and
    the neck, with the per-actor receipt) or check (body_check only, the step before). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_BODY_AUDIT','').strip() or 'gate'
    if value not in AUDIT_MODES:raise ValueError('AMIWIND_NPC_BODY_AUDIT must be gate or check')
    return value

def body_audit(shapes,frame,faces,face_parts=None,face_shapes=None,source_shapes=None,covered_tris=None):
    """The per-actor receipt of a whole-model bake (design step 2): faces, vertices, the joints (npc_seam_audit.measure:
    open share and largest gap), the least limb width, the neck's lost surface, the shapes that lost surface, the
    farthest reduced vertex from the source; and its failures [(shape index, part, name, measure, kind)]."""
    import npc_seam_audit as seams
    faces=np.asarray(faces)[:,:3];frame=np.asarray(frame,float)
    src=[{'name':s.get('name',''),'points':np.asarray(s['positions'][0],float),'faces':np.asarray(s['faces'])}
         for s in shapes]
    reduced=frame[faces]
    joints=seams.measure(src,reduced)
    widths=limb_widths(shapes,frame,faces,face_parts,face_shapes) if face_parts is not None else {}
    lost=lost_shapes(shapes,frame,faces)
    source_tris=np.concatenate([s['points'][s['faces']] for s in src if len(s['faces'])])
    spike=float(seams.point_triangle_distance(frame,source_tris,SPIKE_DISTANCE).max()) if len(frame) else 0.0
    receipt={'faces':int(len(faces)),'vertices':int(len(frame)),'joint_length':joints['joint_length'],
             'open_share':joints['open_share'],'max_gap':joints['max_gap'],
             'least_width':round(min((w for w,_ in widths.values()),default=1.0),3),
             'lost_shapes':{k:list(v) for k,v in lost.items()},'farthest_vertex':round(spike,3)}
    failures=list(body_check(shapes,frame,faces,face_parts,face_shapes=face_shapes))
    if joints['open_share']>JOINT_OPEN_SHARE or joints['max_gap']>JOINT_MAX_GAP:
        names={s.get('name',''):i for i,s in enumerate(shapes)}
        for pair,row in sorted(joints['pairs'].items(),key=lambda kv:-kv[1]['open_length']):
            a=pair.split(' / ')[0]
            if a in names:
                i=names[a];failures.append((i,shapes[i]['part'],a,row['max_gap'],'open joint'))
    if spike>SPIKE_DISTANCE:failures.append((-1,-1,'',round(spike,3),'spike'))
    if face_shapes is not None and len(face_shapes)==len(faces):
        # open edges the source does not have (mesh_seam_check): covered only on a head patch the bake removed under
        # the hair or helmet and away from every join; the pass rule is 0 uncovered (MESH-REDUCTION-SEAMS-62)
        import mesh_seam_check
        source=source_shapes if source_shapes is not None else shapes
        covered,uncovered=mesh_seam_check.classify(source,frame,faces,face_shapes,covered_tris)
        receipt.update(new_openings=len(covered)+len(uncovered),covered_openings=len(covered),
                       uncovered_openings=len(uncovered),uncovered_at=[[n,list(p)] for _,n,p in uncovered[:20]])
        # the join map (every seam of the source: which parts meet, its length, what stayed open) and each limb's
        # thickness at 25 / 50 / 75 % of its length (MESH-SEAM-METHOD-62)
        groups={str(slot):[i for i,s in enumerate(shapes) if s['part']==slot]
                for slot in sorted({s['part'] for s in shapes} & LIMB_SLOTS)}
        thick=mesh_seam_check.limb_thickness(shapes,frame,faces,face_shapes,groups)
        receipt.update(joins=mesh_seam_check.join_map(source,frame,faces),limb_thickness=thick,
                       least_thickness=round(mesh_seam_check.least_thickness(thick),3))
        per={}
        for i,n,p in uncovered:per.setdefault(i,[]).append(p)
        for i,ps in per.items():
            failures.append((i,source[i]['part'],source[i].get('name',''),len(ps),'open edge'))
    return receipt,failures

def _cleared(items):
    """ITEMS emptied for the next bake attempt (None stays None)."""
    if items is not None:
        items.clear()
    return items

def _reduced_total(shapes,materials,textures,palette,minimum_faces,quotas,shell_height,protected,shell_set,preserve,
                   head_reducer=None):
    """The triangles a plan's reduction keeps, without the texture work: _bake reduces every shape first and refuses
    a total over its face limit with the overshoot, so a face limit of 0 returns the total."""
    try:
        _bake(shapes,materials,textures,palette,0,minimum_faces,quotas,shell_height,protected,False,shell_set,
              preserve=preserve,head_reducer=head_reducer)
    except AliasOverflow as overflow:
        if str(overflow)=='Alias vertex budget exceeded':return int(overflow.over)
        raise
    raise ValueError('reduction total not measured')

def body_check_mode():
    """AMIWIND_NPC_BODY_CHECK: fail (default: a bake whose body check finds a gap or a thin limb stops) or warn."""
    import os
    value=os.environ.get('AMIWIND_NPC_BODY_CHECK','').strip() or 'fail'
    if value not in ('fail','warn'):raise ValueError('AMIWIND_NPC_BODY_CHECK must be fail or warn')
    return value

SEAM_FREE_MAX=6                 # shapes whose seam locks may be let go one by one before the free reducer takes all

def _seam_shape_to_free(shapes,locks,freed):
    """The next shape whose seam locks are let go when the locks do not fit (MESH-SEAM-METHOD-62, the dressed
    actors): clothing and armour first (a shape not named like a skin part, B_N_/B_V_/Tri Chest/hands), the most
    locked points first; a head or hair never; None after SEAM_FREE_MAX or when nothing is left (the whole free
    reducer then, as before)."""
    if len(freed)>=SEAM_FREE_MAX:return None
    def skin(s):
        n=s.get('name','').lower()
        return n.startswith(('b_n_','b_v_','tri b_n_','tri b_v_','tri chest','tri right hand','tri left hand'))
    cands=[i for i,s in enumerate(shapes) if s['part'] not in HEAD_SLOTS and i not in freed and len(locks[i])]
    if not cands:return None
    return max(cands,key=lambda i:(not skin(shapes[i]),len(locks[i])))

def head_rims_locked():
    """AMIWIND_NPC_HEAD_RIMS: locked (default from v0.0.62: the head's and hair's rim vertices keep their reduced
    place through keep_head_inside_cover / keep_outside_surface) or pushed (the step before). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_HEAD_RIMS','').strip() or 'locked'
    if value not in ('locked','pushed'):raise ValueError('AMIWIND_NPC_HEAD_RIMS must be locked or pushed')
    return value=='locked'

class BakeStop(RuntimeError):
    """The seam stop (MESH-SEAM-METHOD-62): a reduced model with an uncovered new opening or a limb under
    SEAM_STOP_WIDTH of its width, and no entry in config/model-face-overrides.json. A RuntimeError, so the budget
    ladders that catch ValueError (a rung that does not fit) never take it for a smaller rung."""

SEAM_STOP_WIDTH=0.5             # a limb kept under half its width stops the bake (engine_chim_design.md MESH REDUCTION)

SEAM_STOP_MODES=('ratchet','fail','warn')
WIDTH_SLACK=0.005               # a baselined limb this much thinner is the same measurement, not worse

def seam_stop_mode():
    """AMIWIND_MESH_SEAM_STOP: ratchet (default from v0.0.62: a model that fails stops the bake unless it is in
    config/mesh-seam-baseline.json and no worse than its baseline line), fail (every failing model stops) or warn
    (printed only). Read here only."""
    import os
    value=os.environ.get('AMIWIND_MESH_SEAM_STOP','').strip() or 'ratchet'
    if value not in SEAM_STOP_MODES:raise ValueError('AMIWIND_MESH_SEAM_STOP must be ratchet, fail or warn')
    return value

def seam_stop(model,uncovered,least_width,has_entry,kind='npc',baseline=None):
    """The bake stop (MESH-SEAM-METHOD-62). Returns the model's status: 'passing' (0 uncovered openings, every limb
    at SEAM_STOP_WIDTH or more), 'entry' (fails, but has an entry in config/model-face-overrides.json: printed),
    'baselined' (fails, listed in config/mesh-seam-baseline.json and no worse: printed), 'new' or 'worse' (printed in
    warn mode; BakeStop in ratchet and fail mode; fail mode stops a baselined model too). A passing model that is
    still in the baseline is printed as leaving it (tools/mesh_seam_baseline.py write drops it, so it cannot fail
    again unnoticed). BASELINE: {key: line} (default: model_face_overrides.load_seam_baseline())."""
    bad=[]
    if uncovered:bad.append('%d uncovered new opening%s'%(uncovered,'' if uncovered==1 else 's'))
    if least_width is not None and least_width<SEAM_STOP_WIDTH:bad.append('a limb at %.2f of its width'%least_width)
    if baseline is None:
        from model_face_overrides import load_seam_baseline
        baseline=load_seam_baseline()
    key='%s:%s'%(kind,str(model or '').strip().lower())
    line=baseline.get(key)
    if not bad:
        if line is not None:
            print('seam: %s %s passes now and leaves the baseline (tools/mesh_seam_baseline.py write)'%(kind,model),
                  flush=True)
        return 'passing'
    text='%s %s: %s'%(kind,model or '(unnamed)','; '.join(bad))
    if has_entry:
        print('seam stop: %s (passed by its entry in config/model-face-overrides.json)'%text,flush=True)
        return 'entry'
    mode=seam_stop_mode()
    status='new'
    if line is not None:
        worse=(uncovered or 0)>int(line.get('uncovered',0)) or (
            least_width is not None and least_width<float(line.get('least_width',1.0))-WIDTH_SLACK)
        status='worse' if worse else 'baselined'
        if status=='baselined':
            text+=' (baseline %s: %d uncovered, least width %.2f)'%(line.get('date',''),int(line.get('uncovered',0)),
                                                                  float(line.get('least_width',1.0)))
            if mode!='fail':
                print('seam: baselined: '+text,flush=True)
                return status
    if mode=='warn':
        print('seam stop (warn, %s): %s'%(status,text),flush=True)
        return status
    raise BakeStop('seam stop (%s): %s; the smallest fix first (lock the seam), else an entry in '
                   'config/model-face-overrides.json'%(status,text))

COVER_TILTS=(0.0,40.0,70.0)     # degrees from a head face's normal: the rays that must all meet the cover
COVER_AROUND=6
COVER_SAMPLES=((1/3,1/3,1/3),(.7,.15,.15),(.15,.7,.15),(.15,.15,.7))

def _ray_hits(origins,dirs,a,e1,e2,normal,facing_only=True):
    """Distance along each ray (origins[i] + t dirs[i]) to its nearest triangle (a, e1, e2); inf for none.
    facing_only: only triangles whose normal points along the ray (their outside seen from inside)."""
    out=np.full(len(origins),np.inf)
    for i,(o,d) in enumerate(zip(origins,dirs)):
        good=(normal@d>0) if facing_only else np.ones(len(a),bool)
        p=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,p);good&=np.abs(det)>1e-12
        inv=np.where(good,1/np.where(good,det,1),0);s=o-a
        u=np.einsum('ij,ij->i',s,p)*inv;q=np.cross(s,e1);v=(q@d)*inv;t=np.einsum('ij,ij->i',e2,q)*inv
        hit=good&(u>=0)&(v>=0)&(u+v<=1)&(t>0)
        if hit.any():out[i]=t[hit].min()
    return out

def _cover(shapes):
    """The hair or helmet (slot 1) at frame 0 as one triangle soup: (a, e1, e2, normal) or None."""
    cover=[s for s in shapes if s['part']==1]
    if not cover:return None
    tri=np.concatenate([np.asarray(s['positions'][0])[np.asarray(s['faces'])] for s in cover])
    a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a
    return a,e1,e2,np.cross(e1,e2)

def hidden_head_faces(head_points,head_faces,cover):
    """Per head (slot 0) face: True when the hair or helmet hides it from every side (rays from points on it,
    along its normal and up to 70 degrees around it, all meet the cover from inside): it is never seen, so the bake
    leaves it out instead of reducing it (the maintainer, 27 October 2026: a reduced head poked out through the
    hair as pale specks on the crown and temples)."""
    a,e1,e2,normal=cover
    hp=np.asarray(head_points)[np.asarray(head_faces)]
    hn=np.cross(hp[:,1]-hp[:,0],hp[:,2]-hp[:,0])
    out=np.zeros(len(hp),bool)
    for i in range(len(hp)):
        nn=np.linalg.norm(hn[i])
        if nn<1e-12:continue
        n=hn[i]/nn;ref=np.array([1.,0,0]) if abs(n[0])<.9 else np.array([0,1.,0])
        u=np.cross(n,ref);u/=np.linalg.norm(u);w=np.cross(n,u)
        dirs=[n]+[np.cos(np.radians(t))*n+np.sin(np.radians(t))*(np.cos(2*np.pi*k/COVER_AROUND)*u+
                  np.sin(2*np.pi*k/COVER_AROUND)*w) for t in COVER_TILTS[1:] for k in range(COVER_AROUND)]
        origins=[np.asarray(s)@hp[i]+n*1e-3 for s in COVER_SAMPLES]
        o=np.repeat(origins,len(dirs),axis=0);d=np.tile(dirs,(len(origins),1))
        out[i]=bool(np.all(np.isfinite(_ray_hits(o,d,a,e1,e2,normal))))
    return out

JOIN_KEEP=0.5                   # a head face with a corner this close to another part's surface stays (two seam TOLs)

def _faces_at_joins(shape,others):
    """Mask of SHAPE's faces with a corner within JOIN_KEEP of any of OTHERS' surfaces (frame 0)."""
    from npc_seam_audit import point_triangle_distance
    p=np.asarray(shape['positions'][0],float);f=np.asarray(shape['faces'])[:,:3]
    tris=[np.asarray(o['positions'][0],float)[np.asarray(o['faces'])[:,:3]] for o in others if len(o['faces'])]
    if not tris or not len(f):return np.zeros(len(f),bool)
    near=point_triangle_distance(p,np.concatenate(tris),JOIN_KEEP)<=JOIN_KEEP
    return near[f].any(axis=1)

def cull_hidden_head(shapes,minimum_faces=None):
    """'whole' hair: the head faces the hair or helmet hides are left out before the split (they also free faces
    for the hair). A head shape every face of which is hidden keeps one face (the shape list stays the same)."""
    cover=_cover(shapes)
    if cover is None:return shapes,0
    out=[];total=0
    for s in shapes:
        if s['part']!=0 or (minimum_faces or {}).get(s.get('name','')):out.append(s);continue
        hide=hidden_head_faces(s['positions'][0],s['faces'],cover)
        if hide.any() and head_rims_locked():
            # MESH-SEAM-METHOD-62: the head keeps every face that touches another part (the nape against the neck):
            # removing it opens an edge at a join, which no hair excuses (mesh_seam_check.classify)
            hide&=~_faces_at_joins(s,[o for o in shapes if o is not s and o['part']!=1])
        if hide.all():hide[0]=False
        total+=int(hide.sum());out.append({**s,'faces':np.asarray(s['faces'])[~hide]})
    return out,total

def keep_head_inside_cover(points,cover,centre,margin=.02):
    """'whole' hair: no reduced head vertex outside the hair or helmet shell. A vertex whose ray from the head's
    centre meets the cover nearer than the vertex is moved in, along that ray, to just inside the cover."""
    a,e1,e2,normal=cover
    points=np.array(points,float);d=points-centre;dist=np.linalg.norm(d,axis=1)
    ok=dist>1e-9;dirs=np.where(ok[:,None],d/np.where(ok,dist,1)[:,None],0)
    t=_ray_hits(np.repeat(centre[None],len(points),axis=0),dirs,a,e1,e2,normal,facing_only=False)
    move=ok&np.isfinite(t)&(t<dist)
    points[move]=centre+dirs[move]*(t[move]*(1-margin))[:,None]
    return points,int(move.sum())

def keep_outside_surface(points,surface,centre,margin=.02):
    """A reduced hair or helmet vertex inside the head (its ray from the head's centre leaves the head beyond the
    vertex) moves out along that ray to just outside the head."""
    a,e1,e2,normal=surface
    points=np.array(points,float);d=points-centre;dist=np.linalg.norm(d,axis=1)
    ok=dist>1e-9;dirs=np.where(ok[:,None],d/np.where(ok,dist,1)[:,None],0)
    t=_ray_hits(np.repeat(centre[None],len(points),axis=0),dirs,a,e1,e2,normal,facing_only=False)
    move=ok&np.isfinite(t)&(t>dist)
    points[move]=centre+dirs[move]*(t[move]*(1+margin))[:,None]
    return points,int(move.sum())

WHOLE_FACE_LIMIT=960        # a caller whose reader takes extended models (whole_limit): 960 faces of 16-texel tiles
                            # fill the renderer's 480 skin rows (MAX_LBM_HEIGHT); 2,880 vertices

def _whole_hair(shapes,quotas,face_limit):
    """'whole': the original hair or helmet (slot 1) is a closed, authored shell; any reduction of it pulled the cap
    into the head (the crown and temples showed scalp) and broke its outline into shards (the maintainer, 27 October
    2026: the hair must close up and read as one consistent shell). Every slot 1 shape keeps all its faces when the
    whole model still fits face_limit less HAIR_WHOLE_MARGIN; the head and the rest keep their quotas. Otherwise the
    quotas are returned unchanged (the 'head' split)."""
    hair=[i for i,s in enumerate(shapes) if s['part']==1]
    if not hair:return quotas
    whole=quotas.copy()
    for i in hair:whole[i]=len(shapes[i]['faces'])
    return whole if int(whole.sum())<=face_limit-HAIR_WHOLE_MARGIN else quotas

# CREATURE-RACER-MESH-SPIKE-58: the reduction can keep a thin chain's vertices but collapse its faces to lines (the
# cliff racer's tail lost its lower curve, so the tail tip floated free below the body). The check samples every
# source face (centre, edge points) and looks for a baked face sample near it; a sample farther than LOSS_RATIO of the
# model's largest extent is surface the bake lost.
LOSS_RATIO=0.05
LOSS_SAMPLES=4


def face_samples(v,f):
    """Points on every face (n, 3) x faces (m, 3): the centre and three points along each edge."""
    t=np.asarray(v,float)[np.asarray(f,int)]
    pts=[t.mean(1)]
    for a in (.25,.5,.75):
        pts+=[t[:,i]*a+t[:,(i+1)%3]*(1-a) for i in range(3)]
    return np.concatenate(pts)


def lost_surface(source,source_faces,baked,baked_faces,size,ratio=LOSS_RATIO):
    """(count, worst): the samples of one source shape's faces with no baked face sample within RATIO * SIZE."""
    s=face_samples(source,source_faces)
    b=face_samples(baked,baked_faces)
    if not len(s):
        return 0,0.0
    near=np.empty(len(s))
    for i in range(0,len(s),256):
        near[i:i+256]=np.sqrt(((s[i:i+256,None,:]-b[None,:,:])**2).sum(-1)).min(1)
    return int((near>ratio*size).sum()),float(near.max())


def lost_shapes(shapes,frame,faces,ratio=LOSS_RATIO,least=LOSS_SAMPLES):
    """{shape name: (count, worst)} of the shapes (bake input, first frame) whose surface the baked FRAME/FACES lost."""
    src=np.concatenate([s['positions'][0] for s in shapes])
    size=float((src.max(0)-src.min(0)).max()) or 1.0
    out={}
    for s in shapes:
        count,worst=lost_surface(s['positions'][0],s['faces'],frame,np.asarray(faces)[:,:3],size,ratio)
        if count>=least:
            out[s.get('name','')]=(count,round(worst,2))
    return out


def _budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames,whole_limit=None,body=None):
    """The whole-model split of a budget-head bake (--npc-head-detail budget); the hair or helmet takes the head's
    rule unless hair_share() is 'plain' (the previous split). whole_limit: the face limit a whole hair may take the
    model to (a caller whose reader takes extended models: skeletal residents, SKEL-VERTEX-LIMIT-52); default
    face_limit."""
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
    # The head's rule (weight 1.7; a floor of up to 120 faces past 8 frames) covers the hair or helmet too
    # (hair_share 'head', NPC-HAIR-BACK-MISSING-53): a hair cap reduced far below the head under it sank under the
    # scalp, and the back of the head showed skin.
    share=hair_share()
    def split(group,heads,head_floor=False):
        weights=np.array([len(s['faces'])*(1.7 if s['part'] in heads else 1) for s in group],dtype=float);weights/=weights.sum()
        quotas=np.array([max(minimum_faces.get(s.get('name',''),0),min(120,len(s['faces'])) if s['part'] in heads and (head_floor or (reference_frames if reference_frames is not None else len(s['positions']))>8) else 4) for s in group],int);remaining=budget-int(quotas.sum())
        if remaining<0:raise ValueError('Too many separate shapes for budget')
        quotas+=np.floor(weights*remaining).astype(int)
        return quotas
    quotas=_hair_split(shapes,budget,face_limit,minimum_faces,whole_limit,share,split)
    if share=='plain' or (body or body_share())=='budget':return quotas
    return _keep_body(shapes,quotas,split(shapes,(0,)),minimum_faces)


def _keep_body(shapes,quotas,plain,minimum_faces):
    """NPC-BODY-REGRESSION-62: every body shape (not head or hair) keeps at least its share of the v0.0.53 split
    (PLAIN: the hair took 4 faces and a plain share). With the head's weight and floor on the hair (v0.0.54) a whole
    or heavy hair left the body 4 faces a part: Jiub's legs became sticks, a 4-face neck left a gap under the guards'
    helmets. The total stays the same (the triangle cap): the faces come off the hair first, then the head, never
    below 4 faces, the head's floor of up to 120, or a protected minimum."""
    quotas=np.array(quotas,int);plain=np.asarray(plain,int)
    body=[i for i,s in enumerate(shapes) if s['part'] not in HEAD_SLOTS]
    need=sum(max(0,int(plain[i])-int(quotas[i])) for i in body)
    if not need:return quotas
    minimum_faces=minimum_faces or {}
    def least(i):
        s=shapes[i];n=len(s['faces'])
        return min(n,max(4,minimum_faces.get(s.get('name',''),0),min(120,n) if s['part']==0 else 4))
    give=0
    for slot in (1,0):
        idx=[i for i,s in enumerate(shapes) if s['part']==slot and quotas[i]>least(i)]
        room=sum(int(quotas[i])-least(i) for i in idx)
        take=min(need-give,room)
        if take<=0 or not room:continue
        taken=0
        for i in idx:
            t=(int(quotas[i])-least(i))*take//room;quotas[i]-=t;taken+=t
        for i in idx:
            if taken>=take:break
            if quotas[i]>least(i):quotas[i]-=1;taken+=1
        give+=taken
    # what the head and hair gave goes to the body, short shapes first, up to their v0.0.53 share
    for i in sorted(body,key=lambda i:int(quotas[i])-int(plain[i])):
        if give<=0:break
        t=min(give,max(0,int(plain[i])-int(quotas[i])));quotas[i]+=t;give-=t
    return quotas


def _hair_split(shapes,budget,face_limit,minimum_faces,whole_limit,share,split):
    """The head and hair part of _budget_quotas (hair_share)."""
    # only the full model (the 480 budget, or any budget of a caller's ladder that takes extended models: a skeletal
    # resident whose outfit overflowed at 480 retries at 384 and lower); the lower levels and parts keep the 'head' split
    if share=='whole' and (budget>=480 or whole_limit):
        # the whole hair sits outside the budget: the budget is split among the head and the rest alone, so the head
        # keeps the share the 'head' split gave the hair (the universal check: Dark Elf women's faces fell to 28-52
        # triangles beside a whole 261-376 triangle hair)
        # The head keeps its floor (up to 120 faces) also in the 8-frame retry of an outfit of many shapes, where it
        # used to fall to 4 faces plus a share (Dark Elf women in robes: a 32-triangle face)
        rest=[i for i,s in enumerate(shapes) if s['part']!=1]
        if rest and len(rest)<len(shapes):
            whole=np.array([len(s['faces']) for s in shapes],int)
            try:
                whole[rest]=split([shapes[i] for i in rest],(0,),head_floor=True)
            except ValueError:
                whole[rest]=split([shapes[i] for i in rest],(0,))
            if int(whole.sum())<=max(face_limit,min(int(whole_limit or 0),WHOLE_FACE_LIMIT))-HAIR_WHOLE_MARGIN:
                return whole
        return _whole_hair(shapes,split(shapes,(0,1)),max(face_limit,min(int(whole_limit or 0),WHOLE_FACE_LIMIT)))
    return split(shapes,(0,1) if share in ('head','whole') else (0,))

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

# NPC-BODY-REGRESSION-62, the body reduction design step 1 (docs/MODEL_REDUCTION.md):
# classes by body part slot. Every skin slot of a limb (neck, hands, wrists, forearms, arms, feet, ankles, knees, legs,
# tail) is a limb whatever its size; 'detail' (a 4-face floor) only for the small shapes of the torso, groin and
# clavicle slots (belts, spikes). The size rule above filed every hand, wrist, forearm and neck as a detail.
LIMB_CLASS_SLOTS=frozenset({2,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,26})
DETAIL_CLASS_SLOTS=frozenset({3,4,5,23,24,25})
GIRTH_LADDER=(4,6,8,10,12,14,16,20,24,28,32,40,48,64)
GIRTH_KEEP=0.8              # a limb part keeps at least this share of its source cross-section (n=6 ring: 0.866)
FLOOR_METHODS=('parts','silhouette')

def floor_method():
    """AMIWIND_NPC_BODY_FLOORS: parts (default from v0.0.62: slot classes, girth and loss floors) or silhouette (the
    size classes and silhouette floors up to v0.0.62-dev1, byte for byte). Read here only."""
    import os
    value=os.environ.get('AMIWIND_NPC_BODY_FLOORS','').strip() or 'parts'
    if value not in FLOOR_METHODS:raise ValueError('AMIWIND_NPC_BODY_FLOORS must be parts or silhouette')
    return value

def slot_classes(shapes,actor_height):
    """head / hair / detail / torso / limb for each shape by its body part slot (LIMB_CLASS_SLOTS)."""
    out=[]
    for s in shapes:
        part=s['part']
        if part==0:out.append('head')
        elif part==1:out.append('hair')
        elif part in LIMB_CLASS_SLOTS:out.append('limb')
        elif part in DETAIL_CLASS_SLOTS and float(np.ptp(s['positions'][0],axis=0).max())<DETAIL_EXTENT*actor_height:
            out.append('detail')
        else:out.append('torso')
    return out

def girth_ratio(source_points,source_faces,points,faces):
    """The share of a shape's source cross-section its reduction keeps: the smaller ratio of reduced to source
    extent (5th to 95th percentile of face samples) along the source's two narrow principal axes."""
    src=face_samples(source_points,source_faces)
    if len(src)<8 or not len(faces):return 0.0 if len(src)>=8 else 1.0
    red=face_samples(points,faces)
    centre=src.mean(0);_,_,axes=np.linalg.svd(src-centre,full_matrices=False)
    ratios=[]
    for axis in axes[1:]:
        a=np.percentile((src-centre)@axis,[5,95]);b=np.percentile((red-centre)@axis,[5,95])
        ratios.append(float((b[1]-b[0])/max(a[1]-a[0],1e-6)))
    return min(ratios)

def part_floors(shapes,classes,model_size=None):
    """Per shape: the fewest faces on GIRTH_LADDER at which today's reduction keeps the shape whole (design 3.3):
    girth (limbs and torso: GIRTH_KEEP of the cross-section at that rung and the next, the reducer is not monotone)
    and loss (every body shape: fewer than LOSS_SAMPLES samples farther than LOSS_RATIO of the model's size). The
    head keeps all its faces, details 4; never more than the source."""
    if model_size is None:
        src=np.concatenate([s['positions'][0] for s in shapes])
        model_size=float((src.max(0)-src.min(0)).max()) or 1.0
    out=[]
    for s,c in zip(shapes,classes):
        n=len(s['faces'])
        if c=='head':out.append(n);continue
        if c=='detail' or n<=4:out.append(min(n,4));continue
        points,ix=np.unique(np.round(s['positions'][0],5),axis=0,return_inverse=True);ff=ix[s['faces']].astype(np.int32)
        rungs=[r for r in GIRTH_LADDER if r<n]+[n]
        results={}
        def reduced(r):
            if r not in results:
                results[r]=(points,ff) if r>=n else simplify_shape(points,ff,r,c in ('torso','limb','hair'))
            return results[r]
        def whole(r):
            p,f=reduced(r)
            if c in ('limb','torso') and girth_ratio(points,ff,p,f)<GIRTH_KEEP:return False
            count,_=lost_surface(points,ff,p,f,model_size)
            return count<LOSS_SAMPLES
        floor=n
        for k,r in enumerate(rungs):
            if whole(r) and (k+1>=len(rungs) or whole(rungs[k+1])):floor=r;break
        out.append(min(n,max(4,floor)))
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

# The head's floor when the trims of the budget-head bake take faces from it (the hair gives first, then the head
# down to this). 120 is the shipped default; the override-or-floor measurement (NPC-BODY-REGRESSION-62) tries lower.
HEAD_TRIM_FLOOR=120

def head_plan(shapes,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,head_detail=None,
              floors=None,classes=None,extra_cut=0,whole_limit=None,raised_limit=False,share=None,ceiling=None,
              boost=None,grow_to=None,trim=0,head_floor=None):
    """head_floor: this model's head trim floor from config/model-head-floors.json (None: HEAD_TRIM_FLOOR).

    The whole-model bake plan: quotas, the shapes kept exactly and the alias face limit.

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
    mode=npc_head_detail(head_detail)
    quotas=_budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames,
                          whole_limit if mode=='budget' else None)
    # a whole hair past face_limit (whole_limit): the largest alias face limit, so the locked reducer's overshoot on
    # the rest (its rims) still fits (the universal hair check: at 777 the outfits of 245 pairings overflowed and fell
    # down the resident ladder to a 384 budget)
    # raised_limit: the bake overflowed at face_limit with a whole hair (bake retries once at the largest limit)
    limit=face_limit if int(quotas.sum())<=face_limit and not raised_limit else ALIAS_FACE_LIMITS[-1]
    if boost and mode=='budget':
        # the body check's retry (bake): the named shapes take at least these faces, from the hair, then the head
        target=quotas.copy()
        for i,want in boost.items():target[i]=max(int(target[i]),min(int(want),len(shapes[i]['faces'])))
        quotas=_keep_body(shapes,quotas,target,minimum_faces)
        if trim:
            # the reduction kept more faces than its quotas: the overshoot comes off the hair, then the head, then
            # the body shapes above their targets, so the model stays at today's total (the triangle cap)
            quotas=quotas.copy();left=int(trim)
            groups=([i for i,s in enumerate(shapes) if s['part']==1],[i for i,s in enumerate(shapes) if s['part']==0],
                    [i for i in range(len(shapes)) if shapes[i]['part'] not in HEAD_SLOTS])
            for k,idx in enumerate(groups+(groups[2],)):
                # the last pass takes the body below its floors: without an override entry the total wins
                least=lambda i:min(head_floor or HEAD_TRIM_FLOOR,len(shapes[i]['faces'])) if shapes[i]['part']==0 else \
                    (int(target[i]) if shapes[i]['part'] not in HEAD_SLOTS and k<3 else 4)
                room=sum(max(0,int(quotas[i])-least(i)) for i in idx)
                if left<=0 or not room:continue
                take=min(left,room);taken=0
                for i in idx:
                    t=max(0,int(quotas[i])-least(i))*take//room;quotas[i]-=t;taken+=t
                for i in idx:
                    if taken>=take:break
                    if quotas[i]>least(i):quotas[i]-=1;taken+=1
                left-=taken
        if grow_to:
            # the last retry: what the hair and head could not give comes from the room left under the face limit
            room=int(grow_to)-int(quotas.sum())
            for i in sorted(boost,key=lambda i:int(quotas[i])-int(target[i])):
                if room<=0:break
                t=min(room,max(0,int(target[i])-int(quotas[i])));quotas[i]+=t;room-=t
    plan={'mode':mode,'quotas':quotas,'protected':frozenset(),'face_limit':limit,
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
    if (share or body_share())=='body':
        # NPC-BODY-REGRESSION-62: the head and hair are kept whole outside the budget, so the body takes the budget
        # split among the body shapes alone (body_quotas), never the leftovers of a split that also weighed the
        # whole head and hair (with the v0.0.54 hair share every limb of Jiub fell to 4 faces: stick legs, and a
        # 4-face neck left a gap under the guards' helmets). ceiling (bake: the triangles the previous split's model
        # draws) holds the total: the hair gives up faces first (CUT_ORDER), then details, the torso, the limbs.
        body=body_quotas(shapes,budget,classes)
        want=[n[i] if c in ('head','hair') else max(floor[i],min(int(body[i]),n[i])) for i,c in enumerate(classes)]
    target=sum(want)
    cap=target if ceiling is None else max(min(target,ceiling),sum(floor))
    limit=next((l for l in ALIAS_FACE_LIMITS if l>=face_limit and l>=cap),ALIAS_FACE_LIMITS[-1])
    over=max(0,target-min(limit,cap))+int(extra_cut)
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
    plan.update(quotas=np.array(want,int),protected=protected,face_limit=limit,cuts=cuts,ceiling=ceiling,
                head_faces=sum(n[i] for i in protected),
                hair_reduced=any(c=='hair' and want[i]<n[i] for i,c in enumerate(classes)))
    return plan

def bake_quotas(shapes,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,head_detail=None):
    """Per-shape triangle quotas of one complete appearance (the whole-model bake).

    A shape's quota depends on every other shape in the outfit (MODULAR_NPCS.md):
    the same body part gets a different quota in a different outfit. Heads keep
    their original triangles unless head_detail is 'budget' (head_plan).
    """
    # the parts library (tools/npc_parts.py) keeps the previous body share until its own repair (NPC-BODY-REGRESSION-62)
    return head_plan(shapes,budget,face_limit,minimum_faces,reference_frames,head_detail,share='budget')['quotas']

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


DEV1_BODY_RULES = {'AMIWIND_NPC_BODY_SHARE': 'budget', 'AMIWIND_NPC_BODY_FLOORS': 'silhouette',
                   'AMIWIND_NPC_BODY_REDUCER': 'default'}
_FALLBACK_ACTIVE = []


def bake(*args, head_detail=None, **kwargs):
    """The NPC bake. head_detail is named here because callers read it from the signature (npc_lod); it is passed on
    only when given (a module-level __wrapped__ link would make every importer reach the bake: test_stage_key_npc).
    The other parameters are _bake_once's. With AMIWIND_NPC_BAKE_FALLBACK=dev1 (off by default; set for the v0.0.62 release build by the
    maintainer's decision, 2026-11-08: high triangle counts or an imperfect character ship and are fixed later, the
    build never stops on one), a model the new seam and floor method cannot bake (AliasOverflow, or no split for its
    shapes) is baked once more with the v0.0.62-dev1 body rules, logged as BAKE-FALLBACK; only a failure of that too
    stops the build."""
    if head_detail is not None:
        kwargs['head_detail'] = head_detail
    if os.environ.get('AMIWIND_NPC_BAKE_FALLBACK', '').strip() != 'dev1' or _FALLBACK_ACTIVE:
        return _bake_once(*args, **kwargs)
    try:
        return _bake_once(*args, **kwargs)
    except (AliasOverflow, ValueError) as error:
        if not isinstance(error, AliasOverflow) and str(error) != 'Too many separate shapes for budget':
            raise
        saved = {k: os.environ.get(k) for k in DEV1_BODY_RULES}
        os.environ.update(DEV1_BODY_RULES)
        _FALLBACK_ACTIVE.append(1)
        try:
            print('BAKE-FALLBACK: %s: %s; baked with the v0.0.62-dev1 body rules'
                  % (kwargs.get('model') or '?', error), file=sys.stderr, flush=True)
            return _bake_once(*args, **kwargs)
        finally:
            _FALLBACK_ACTIVE.pop()
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _bake_once(shapes,materials,textures,palette,budget=480,face_limit=666,minimum_faces=None,reference_frames=None,
         quotas=None,shell_height=None,head_detail=None,lod_only='budget',preserve=None,body_skin_rows=None,
         body_leg_contour=False,face_parts=None,full_frame_budget=None,whole_limit=None,extra_faces=0,
         rim_locked=None,seams=None,face_shapes=None,model=None,body_key=None,keep_whole_retry=True):
    """One topology shared by every frame, per-face tiny UV atlas patches.

    model: the NPC record id of a builder bake: turns the seam stop on (seam_stop; MESH-SEAM-METHOD-62). Without it
    (far levels, the parts library, probes) the receipt is written and nothing stops.
    body_key: the body appearance ('head part id|hair part id', model_face_overrides.body_key) whose head trim floor
    config/model-head-floors.json may lower.

    seams: True = the seam locks (tools/npc_seams.py) whatever AMIWIND_NPC_BODY_REDUCER says (a creature's shapes);
    False = never (a caller whose face counts must follow its own quotas exactly: the far levels of npc_lod);
    None = AMIWIND_NPC_BODY_REDUCER.

    extra_faces: the faces this model may add over today's total, only from its entry in
    config/model-face-overrides.json (tools/model_face_overrides.extra_faces; NPC-BODY-REGRESSION-62).
    rim_locked: shape indices reduced with their rims locked (simplify_head_locked): an open panel that the free
    reduction folds away (the Alit's torso, CREATURE-MESH-HOLES-62).

    whole_limit: the face limit a whole hair may take a budget bake to (hair_share 'whole'; a caller whose reader
    takes extended models, e.g. skeletal residents: SKEL-VERTEX-LIMIT-52); such a model uses the raised-limit skin.

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
    worn_merged={}
    if model and quotas is None and worn_merge():
        # MESH-SEAM-METHOD-62: an armoured slot's pieces are reduced as one shape (merge_worn_pieces)
        shapes,worn_merged=merge_worn_pieces(shapes)
    _call=dict(locals())           # the arguments as given: the keep-whole retry bakes again with them
    _call.pop('worn_merged',None)
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
        explicit_locks=None
        if seams:
            from npc_seams import joint_locks
            explicit_locks=joint_locks(shapes)
        return _retry_head_reducer(lambda reducer:_bake(shapes,materials,textures,palette,face_limit,minimum_faces,
                     quotas,shell_height,protected,face_limit!=ALIAS_FACE_LIMITS[0] and int(quotas.sum())>ALIAS_FACE_LIMITS[0],
                     preserve=preserve,body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,
                     face_parts=face_parts,head_reducer=reducer,seam_locks=explicit_locks,
                     face_shapes=_cleared(face_shapes)),
                     npc_head_reducer() if npc_head_detail(head_detail)=='budget' else None)
    mode=npc_head_detail(head_detail)
    if face_parts is None:face_parts=[]     # the body check reads each baked face's body part slot
    # base_limit: the caller's alias face limit (a plan above it uses the raised-limit skin). A model with an override
    # entry may go up to the largest limit (1,024; the engine loads it through model-budgets.txt, written for every
    # model past 2,000 vertices by audit_gallery_budgets.world_allowances); its total stays today's plus the entry.
    base_limit=face_limit
    if extra_faces and face_limit<ALIAS_FACE_LIMITS[-1]:face_limit=ALIAS_FACE_LIMITS[-1]
    # the receipt's open-edge count compares the baked model with the source shapes as given (before any head cull)
    source_shapes=shapes;culled_tris=[]
    if face_shapes is None:face_shapes=[]
    if mode=='budget' and (budget>=480 or whole_limit) and hair_share()=='whole':
        # the head faces the hair or helmet hides are never drawn: out before the split (cull_hidden_head), but only
        # when the hair then stays whole; a reduced cap keeps the head under it (no hole through a sunk cap)
        culled,hidden=cull_hidden_head(shapes,minimum_faces)
        if hidden:
            q=_budget_quotas(culled,budget,face_limit,minimum_faces,reference_frames,whole_limit)
            if all(int(q[i])>=len(s['faces']) for i,s in enumerate(culled) if s['part']==1):
                # the removed head triangles: the only openings the receipt may count as covered (mesh_seam_check)
                for s,c in zip(shapes,culled):
                    if s['part']==0 and len(c['faces'])<len(s['faces']):
                        kept={tuple(f) for f in np.asarray(c['faces']).tolist()}
                        gone=[f for f in np.asarray(s['faces']).tolist() if tuple(f) not in kept]
                        if gone:culled_tris.append(np.asarray(s['positions'][0],float)[np.asarray(gone)])
                shapes=culled
    floors=classes=None;shell_set=None
    if mode=='original' and any(s['part'] in HEAD_SLOTS for s in shapes):
        height=float(shell_height) if shell_height else (max(s['positions'][0,:,2].max() for s in shapes)-
                                                          min(s['positions'][0,:,2].min() for s in shapes))
        if floor_method()=='parts':
            # design step 1: slot classes and each part's own girth and loss floor, never capped by a share
            classes=slot_classes(shapes,height);silhouette=part_floors(shapes,classes)
            floors=list(silhouette)
        else:
            classes=body_classes(shapes,height);silhouette=silhouette_floors(shapes,classes)
            # A body shape's floor: its silhouette count, but never more than the budget
            # bake gave it (that body is never thinner than the budget model's).
            share=_budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames) if body_share()=='budget' \
                else body_quotas(shapes,budget,classes)
            floors=[f if c in ('head','hair','detail') else min(f,max(4,int(q)))
                    for f,c,q in zip(silhouette,classes,share)]
    ceiling=None;regrow=0;boost={};best=None;use_best=False;plain_boost={}
    base_total=0;trim=0;trims=0
    seam_locks=None;seams_dropped=False;seams_trim=0
    if seams or (seams is None and body_reducer()=='seams' and floor_method()=='parts' and body_share()=='body' and
                 any(s['part']==0 for s in shapes)):
        from npc_seams import joint_locks
        seam_locks=joint_locks(shapes)
    if (mode=='budget' and body_share()=='body' and floor_method()=='parts' and
            any(s['part']==0 for s in shapes)):
        # design step 1 in the budget-head bake: every body part asks for its girth and loss floor; the hair, then
        # the head, give the faces (head_plan boost, _keep_body): the model's total stays today's
        height=float(shell_height) if shell_height else (max(s['positions'][0,:,2].max() for s in shapes)-
                                                          min(s['positions'][0,:,2].min() for s in shapes))
        part_classes=slot_classes(shapes,height)
        boost={i:f for i,(f,c) in enumerate(zip(part_floors(shapes,part_classes),part_classes))
               if c not in ('head','hair')}
        plain_boost=dict(boost)
        if seam_locks is not None:
            # a shape needs at least as many faces as it has seam vertices to fan the seam (design 3.3)
            for i in boost:
                boost[i]=min(len(shapes[i]['faces']),max(boost[i],len(seam_locks[i])))
        # today's total: the faces the previous split's reduction keeps (reduced without the texture work); the
        # reducer often keeps fewer than its quotas, so the quotas' sum would let the model grow
        try:
            old=_budget_quotas(shapes,budget,base_limit,minimum_faces,reference_frames,whole_limit,body='budget')
            base_total=min(base_limit,_reduced_total(shapes,materials,textures,palette,minimum_faces,old,shell_height,
                                                     frozenset(),None,preserve,head_reducer=npc_head_reducer()))
        except (ValueError,AliasOverflow):
            # the previous split does not bake at this budget: today's total is at most the caller's face limit
            base_total=base_limit
    if classes is not None and body_share()=='body':
        # NPC-BODY-REGRESSION-62, the triangle cap: the previous split's model is reduced (no texture work) and its
        # triangle count is this model's ceiling, so the repair moves triangles from the hair to the body, adds none
        try:
            old=_budget_quotas(shapes,budget,face_limit,minimum_faces,reference_frames)
            old_floors=[f if c in ('head','hair','detail') else min(f,max(4,int(q))) for f,c,q in zip(silhouette,classes,old)]
            old_plan=head_plan(shapes,budget,face_limit,minimum_faces,reference_frames,head_detail,old_floors,classes,
                               share='budget')
        except ValueError as error:
            # v0.0.62-dev2 build (the room batches, twice): an outfit of many pieces has no previous split at this
            # budget, so there is no previous model to cap it by: no ceiling, as before v0.0.62-dev2
            if str(error)!='Too many separate shapes for budget':raise
            old_plan={'lod_only':True}
        if not old_plan['lod_only']:
            old_shells=frozenset(i for i,c in enumerate(classes) if c in ('hair','torso','limb')
                                 and old_plan['quotas'][i]>=silhouette[i])
            ceiling=min(ALIAS_FACE_LIMITS[-1],_reduced_total(shapes,materials,textures,palette,minimum_faces,
                        old_plan['quotas'],shell_height,old_plan['protected'],old_shells,preserve))
    extra=0
    raised_limit=False
    # a lower head trim floor only per model, as data (config/model-head-floors.json; NPC-BODY-REGRESSION-62)
    from model_face_overrides import head_floor as _head_floor
    model_head_floor=_head_floor(body_key) if body_key else None
    seams_freed=[]           # shapes whose seam locks were let go one at a time before the whole fallback
    for _ in range(120):        # the cuts, the body-check retries, the total's trims and the seam fallback
        try:
            plan=head_plan(shapes,budget,face_limit,minimum_faces,reference_frames,head_detail,floors,classes,extra,
                           whole_limit,raised_limit,ceiling=ceiling,boost=boost,
                           # more faces than today's total only through an entry of config/model-face-overrides.json
                           grow_to=min(face_limit-HAIR_WHOLE_MARGIN,base_total+int(extra_faces))
                           if regrow>=3 and extra_faces and base_total else None,trim=trim,head_floor=model_head_floor)
        except ValueError as error:
            # v0.0.62-dev2 build (the room batches): the body floors and seam locks (NPC-BODY-REGRESSION-62) reserve
            # faces for every separate piece, so an outfit of many pieces fits no split at this budget; the last
            # fallback is the plain shares of v0.0.62-dev1 (no floors, no locks, no trim), logged, and the body check
            # reports what it costs; the caller's own budget ladder still runs when this too does not fit
            if str(error)!='Too many separate shapes for budget' or not (boost or seam_locks is not None or trim):
                raise
            print('npc bake: too many separate shapes with the body floors and seam locks: the plain shares instead',
                  flush=True)
            seam_locks=None;seams_dropped=True;boost={};plain_boost={};trim=0;trims=0
            continue
        if plan['mode']=='budget' and face_limit>base_limit:
            # an override entry's model: the smallest alias limit that holds today's total plus the entry
            want=max(int(plan['quotas'].sum()),(base_total or 0)+int(extra_faces))
            plan['face_limit']=next((l for l in ALIAS_FACE_LIMITS if l>=base_limit and l>=want),ALIAS_FACE_LIMITS[-1])
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
                         shell_height,plan['protected'],plan['face_limit']!=base_limit,
                         None if plan['mode']=='budget' else shell_set,preserve=preserve,
                         body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,face_parts=face_parts,
                         head_reducer=head_reducer,rim_locked=rim_locked,seam_locks=seam_locks,
                         face_shapes=_cleared(face_shapes))
        except AliasOverflow as overflow:
            if str(overflow).startswith('Player leg'):raise
            if seam_locks is not None and boost and trims<6 and str(overflow)=='Alias vertex budget exceeded':
                # the seam locks keep vertices the quotas did not count: the overshoot comes off the hair, the head,
                # then the body above its floors (trim), and the bake runs again
                trim+=int(overflow.over)+2;trims+=1;continue
            if seam_locks is not None and boost and str(overflow)=='Alias vertex budget exceeded':
                i=_seam_shape_to_free(shapes,seam_locks,seams_freed)
                if i is not None:
                    seams_freed.append(i);seam_locks[i]=set();trim=0;trims=0;continue
                print('npc bake: seam locks over the face limit after the trims: the free reducer instead',flush=True)
                seam_locks=None;seams_dropped=True;seams_trim=trim;trim=0;trims=0;boost=dict(plain_boost);continue
            if regrow and best is not None:
                # a body-check retry that no longer fits: the best bake so far stands (its problems reported below)
                result,plan=best[0],best[2];face_parts[:]=best[3];use_best=True
            elif plan['mode']=='budget':
                # NPC-BAKE-VERTEX-32: preserve every disconnected visible panel;
                # successful normal bakes and all animation samples are unchanged.
                if str(overflow) != 'Alias vertex budget exceeded':raise
                retry=lambda reducer:_bake(shapes,materials,textures,palette,plan['face_limit'],minimum_faces,
                             plan['quotas'],shell_height,plan['protected'],plan['face_limit']!=base_limit,None,
                             preserve=preserve,
                             body_skin_rows=body_skin_rows,body_leg_contour=body_leg_contour,
                             face_parts=face_parts,shell_components=True,full_frame_budget=full_frame_budget,
                             head_reducer=reducer,rim_locked=rim_locked,seam_locks=seam_locks,
                             face_shapes=_cleared(face_shapes))
                try:
                    result=_retry_head_reducer(retry,head_reducer)
                except AliasOverflow:
                    # the shell-components retry kept the seam locks: when it still overflows, the locks go and the
                    # free reducer bakes it, as the first fallback above does (v0.0.62-dev2 build: the imperial guard
                    # of the intro stopped the intro stage with 'Alias vertex budget exceeded', SEAM-STOP-MODE-FLAG-62)
                    if seam_locks is not None:
                        print('npc bake: seam locks over the face limit in the shell-components retry: the free '
                              'reducer instead',flush=True)
                        seam_locks=None;seams_dropped=True;seams_trim=trim;trim=0;trims=0
                        boost=dict(plain_boost) if plain_boost else boost;continue
                    # a whole hair that took the model past face_limit: once more at the largest alias face limit
                    whole=any(int(plan['quotas'][i])>=len(s['faces']) for i,s in enumerate(shapes) if s['part']==1)
                    if not (whole_limit and whole and hair_share()=='whole' and not raised_limit and
                            plan['face_limit']<ALIAS_FACE_LIMITS[-1]):
                        raise
                    raised_limit=True;continue
            else:
                extra+=overflow.over+2;continue
        # NPC-BODY-REGRESSION-62: the reducer can keep a few faces over its quotas; the body share draws no more
        # than the previous plan (the triangle cap), so the overshoot comes off as another cut
        if (not use_best and boost and base_total and len(result[1])>base_total+int(extra_faces)):
            # the budget-head bake with body floors: held to today's total (plus an override entry's faces)
            if trims<6:
                trim+=len(result[1])-base_total-int(extra_faces);trims+=1;continue
            if seam_locks is not None:
                i=_seam_shape_to_free(shapes,seam_locks,seams_freed)
                if i is not None:
                    seams_freed.append(i);seam_locks[i]=set();trim=0;trims=0;continue
                # the seam locks do not fit the total: this actor is baked with the free reducer (recorded)
                print('npc bake: seam locks over the total (%d faces, today %d + %d): the free reducer instead'
                      %(len(result[1]),base_total,int(extra_faces)),flush=True)
                seam_locks=None;seams_dropped=True;seams_trim=trim;trim=0;trims=0;boost=dict(plain_boost);continue
        if not use_best and ceiling and len(result[1])>max(ceiling,sum(floors)) and not plan['lod_only']:
            extra+=len(result[1])-max(ceiling,sum(floors));continue
        problems=[];receipt=None
        if body_share()=='body' and ((classes is not None and not plan['lod_only']) or
                                     (plan['mode']=='budget' and (budget>=480 or floor_method()=='parts') and
                                      any(s['part']==0 for s in shapes))):
            if use_best:
                problems,receipt=best[1],best[4]
            elif body_audit_mode()=='gate':
                # design step 2: the joints, spikes and lost surface beside the widths and the neck
                receipt,problems=body_audit(shapes,result[0][0],result[1],face_parts,face_shapes,source_shapes,
                                            np.concatenate(culled_tris) if culled_tris else None)
            else:
                problems=body_check(shapes,result[0][0],result[1],face_parts)
            if problems and (best is None or len(problems)<len(best[1])):
                best=(result,problems,plan,list(face_parts),receipt)
            # the retries raise thin limbs and necks; an open joint is closed by the seam locks (step 3), not by faces
            regrow_on=[x for x in problems if x[0]>=0 and x[4] in ('thin limb','neck gap')]
            if regrow_on and regrow<4 and not use_best:
                # a thin limb, a neck gap or an open joint: twice its faces (the hair and details, in a budget bake
                # the hair and the head, give them up; the total stays), twice more, then the whole source shape
                regrow+=1
                for i,*_ in regrow_on:
                    whole=len(shapes[i]['faces'])
                    if classes is not None:
                        floors[i]=whole if regrow>=3 else min(whole,max(2*floors[i],2*int(plan['quotas'][i])))
                    else:
                        boost[i]=whole if regrow>=3 else min(whole,2*max(int(plan['quotas'][i]),boost.get(i,0)))
                continue
            if problems:
                what={'neck gap':'surface lost','thin limb':'width kept','open joint':'gap','spike':'units off'}
                text='; '.join('%s part %d %s (%s %.2f)'%(k,p,n,what.get(k,''),l) for _,p,n,l,k in problems)
                hard=[x for x in problems if (x[4]=='neck gap' and x[3]>BODY_NECK_FAIL) or
                      (x[4]=='thin limb' and x[3]<BODY_LIMB_FAIL) or
                      (x[4]=='open joint' and x[3]>JOINT_FAIL_GAP and body_reducer()=='seams') or x[4]=='spike']
                if hard and body_check_mode()=='fail':raise ValueError('NPC body check: '+text)
                print('npc bake: body check: '+text,flush=True)
        LAST_PLAN.clear()
        LAST_PLAN.update(mode=plan['mode'],face_limit=plan['face_limit'],head_faces=plan['head_faces'],
                         protected_shapes=len(plan['protected']),hair_reduced=plan['hair_reduced'],
                         lod_only=plan['lod_only'],cuts=dict(plan['cuts']),extra_cut=extra,body_problems=problems,
                         receipt=dict(receipt or {},base_total=base_total,extra_faces=int(extra_faces),
                                      taken_from_hair_and_head=int(trim),
                                      head_floor=int(model_head_floor or HEAD_TRIM_FLOOR),
                                      seams_freed=[shapes[i].get('name','') for i in seams_freed],
                                      worn_merged=worn_merged,
                                      head_floor_entry=bool(model_head_floor),
                                      taken_before_the_fallback=int(seams_trim),
                                      reducer=('seams' if seam_locks is not None else
                                               'default (seams over the total)' if seams_dropped else 'default'),
                                      delta=(len(result[1])-base_total) if base_total else None))
        if model and receipt and receipt.get('uncovered_openings') and keep_whole_retry:
            # MESH-SEAM-METHOD-62: a head or hair whose reduction still opens an edge is kept whole (its source
            # triangles), the rest of the model as before; kept only when the model then passes inside today's total
            # plus its entry, else the first bake stands and the stop judges it
            names={n for n,_ in receipt.get('uncovered_at',[])}
            whole={s.get('name',''):len(s['faces']) for s in source_shapes
                   if s['part'] in HEAD_SLOTS and s.get('name','') in names}
            if whole:
                fp2,fs2=[],[];first=dict(LAST_PLAN)
                try:
                    again=bake(**dict(_call,minimum_faces=dict(_call.get('minimum_faces') or {},**whole),
                                      face_parts=fp2,face_shapes=fs2,model=None,keep_whole_retry=False))
                    r2=LAST_PLAN.get('receipt') or {}
                    ok=(r2.get('uncovered_openings')==0 and r2.get('least_width',1.0)>=SEAM_STOP_WIDTH and
                        (not base_total or len(again[1])<=base_total+int(extra_faces)))
                except (ValueError,AliasOverflow):
                    ok=False
                print('npc bake: %s: head/hair kept whole (%s): %s'%(model,', '.join(sorted(whole)),
                      'passes, kept' if ok else 'no pass inside the total, the first bake stands'),flush=True)
                if ok:
                    result=again
                    if face_parts is not None:face_parts[:]=fp2
                    if face_shapes is not None:face_shapes[:]=fs2
                    LAST_PLAN['receipt']['kept_whole']=sorted(whole)
                else:
                    LAST_PLAN.clear();LAST_PLAN.update(first)
                receipt=LAST_PLAN['receipt']
        if model and receipt and 'uncovered_openings' in receipt:
            # the seam stop (MESH-SEAM-METHOD-62): any uncovered new opening or a limb under half its width; only the
            # builder's named actor bakes (npc_library, prepare_area, prepare_intro), never a far level or a probe
            LAST_PLAN['receipt']['seam_model']=str(model)
            LAST_PLAN['receipt']['seam_status']=seam_stop(model,receipt['uncovered_openings'],
                                                          receipt.get('least_width'),bool(extra_faces))
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
          head_reducer=None,rim_locked=None,seam_locks=None,face_shapes=None):
    """face_shapes: a list that receives each baked face's shape index (the open-edge check, tools/mesh_seam_check.py).
    shell_set None: the previous rule (large torso panels keep their shell); else the
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
            if (head_reducer=='locked' and shape['part'] in HEAD_SLOTS) or (rim_locked and index in rim_locked):
                points,ff=simplify_head_locked(points,ff,int(quota))
            elif seam_locks is not None and shape['part'] not in HEAD_SLOTS and not exact:
                # design step 3 (AMIWIND_NPC_BODY_REDUCER=seams): the joint rims locked on both sides, the free rims
                # held by the boundary term (tools/npc_seams.py)
                from npc_seams import simplify_body
                points,ff=simplify_body(points,ff,int(quota),seam_locks[index])
            else:
                points,ff=simplify_shape(points,ff.astype(np.int32),int(quota),preserve_shell)
            if shape['part'] in HEAD_SLOTS and hair_share()=='whole':
                # the rims stay locked through the pushes below, as the reducer locked them (MESH-SEAM-METHOD-62): a
                # pushed rim slid off its source place and opened the edge the reduction had kept (the head's edge
                # round the patch the hair hides moved 0.6-1.0 units inward; a hair's edge slid over the scalp)
                from static_lod import boundary_vertices
                rim=np.asarray(sorted(boundary_vertices(np.asarray(ff,dtype=np.int64))),dtype=np.int64) \
                    if head_rims_locked() else np.zeros(0,np.int64)
                rim_at=np.asarray(points,float)[rim].copy() if len(rim) else None
                if shape['part']==0:
                    # the reduced head stays under the hair or helmet (no head vertex through the shell)
                    cover=_cover(shapes)
                    if cover is not None:
                        points,_=keep_head_inside_cover(points,cover,np.asarray(source_points).mean(axis=0))
                else:
                    # a reduced hair or helmet stays outside the head (its cap never sinks into the scalp)
                    head=_cover([{**s,'part':1} for s in shapes if s['part']==0])
                    if head is not None:
                        centre=np.concatenate([np.asarray(s['positions'][0]) for s in shapes
                                               if s['part']==0]).mean(axis=0)
                        points,_=keep_outside_surface(points,head,centre)
                if rim_at is not None:
                    points=np.array(points,float);points[rim]=rim_at
            seam_reduced=seam_locks is not None and shape['part'] not in HEAD_SLOTS
            if shell_components and preserve_shell and not seam_reduced:
                # (a seam-locked shape keeps its seam reduction: the shell components' free reducer would open it)
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
    # barycentric weights of the 16 x 16 texels of a face tile: the same for every face
    yy,xx=np.mgrid[0:16,0:16];tile_weights=np.column_stack((np.maximum(0,1-(xx.ravel()+yy.ravel())/15),xx.ravel()/15,yy.ravel()/15))
    tile_weights/=tile_weights.sum(1)[:,None]
    for shape_index,(shape,(exact,points,ff)) in enumerate(zip(shapes,reduced)):
        orig=shape['positions'];faces=shape['faces'];p=orig[0]
        old_tri=p[faces];centres=old_tri.mean(axis=1);tree=cKDTree(centres)
        # Every pseudo-inverse below is of one original triangle's edge matrix:
        # computed once per shape. Batched results are bitwise equal to the
        # per-matrix calls (tests/test_npc_parts.py), so output bytes are unchanged.
        inverse=np.linalg.pinv(np.stack((old_tri[:,1]-old_tri[:,0],old_tri[:,2]-old_tri[:,0]),axis=2))
        mat=materials[shape['material']];tex=textures.get(mat['texture_index'])
        fmat=shape.get('face_material')       # a merged worn slot (merge_worn_pieces): each face its own material
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
            samples=tile_weights@triangle
            if exact:
                # Protected shapes retain authored triangles and UV seams.
                # Nearby folds must not lend their texture to the original face.
                sampleuv=tile_weights@shape['uv'][faces[source_face]]
                samplecolour=tile_weights@shape['colours'][faces[source_face],:3]
                sampletri=np.full(len(samples),source_face)
            else:
                # Sample the closest original surface per texel. Projecting an
                # entire decimated face onto one tiny source triangle crosses UV
                # seams and produces stripes, particularly on armour and faces.
                choices=tree.query(samples,k=min(12,len(old_tri)))[1]
                if choices.ndim==1:choices=choices[:,None]
                best=np.full(len(samples),np.inf);sampleuv=np.zeros((len(samples),2));samplecolour=np.ones((len(samples),3))
                sampletri=np.zeros(len(samples),int)
                for ci in range(choices.shape[1]):
                    triids=choices[:,ci];tri=old_tri[triids]
                    # the pseudo-inverse of each original triangle's edge matrix, made once per shape above
                    # (`inverse`; the same matrices, so bitwise the same values): it was made again for every
                    # sample of every output face, 4.5 of 10 s of a body bake (BUILD-BODY-BAKE-SLOWER-44)
                    xy=np.einsum('nij,nj->ni',inverse[triids],samples-tri[:,0])
                    bw=np.column_stack((1-xy.sum(1),xy));bw=np.maximum(bw,0);bw/=bw.sum(1)[:,None]
                    projected=np.einsum('nv,nvc->nc',bw,tri);dist=((projected-samples)**2).sum(1);take=dist<best
                    sampleuv[take]=np.einsum('nv,nvc->nc',bw,shape['uv'][faces[triids]])[take]
                    samplecolour[take]=np.einsum('nv,nvc->nc',bw,shape['colours'][faces[triids],:3])[take];best[take]=dist[take]
                    sampletri[take]=triids[take]
            if fmat is not None:
                colours=np.zeros((len(samples),3))
                fm=np.asarray(fmat)[sampletri]
                for mi in np.unique(fm):
                    sel=fm==mi;m2=materials[int(mi)];t2=textures.get(m2['texture_index'])
                    if t2 is None:c=np.full((int(sel.sum()),3),220.)
                    else:
                        px=np.floor(sampleuv[sel,0]*t2.shape[1]).astype(int)%t2.shape[1];py=np.floor(sampleuv[sel,1]*t2.shape[0]).astype(int)%t2.shape[0]
                        c=t2[py,px,:3].astype(float)
                    colours[sel]=c*np.array(m2['diffuse'])
                colours*=samplecolour
            elif tex is None:colours=np.full((len(samples),3),220.)*samplecolour*np.array(mat['diffuse'])
            else:
                px=np.floor(sampleuv[:,0]*tex.shape[1]).astype(int)%tex.shape[1];py=np.floor(sampleuv[:,1]*tex.shape[0]).astype(int)%tex.shape[0]
                colours=tex[py,px,:3].astype(float)*samplecolour*np.array(mat['diffuse'])
            tile=np.clip(colours,0,255).astype(np.uint8).reshape(16,16,3)
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
            if face_shapes is not None:face_shapes.append(shape_index)
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
