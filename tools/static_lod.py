# SPDX-License-Identifier: GPL-3.0-only
"""Optional host-side static LOD, preserving material/component membership.

UVs are projected from the nearest same-material source triangle. This is an
approximation for a selected large prop, not a replacement for original source
geometry or collision. Keep the original geometry for collider generation.
"""
import numpy as np


def rock_profile(name, triangles):
    """Bound terrain-rock visual cost; collision retains the source geometry."""
    stem=name.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    if not stem.startswith('terrain_rock_'):
        return {}
    return {'ratio': min(1., 64/max(1, triangles)), 'texture_size': 64,
            'visual_triangle_target': 64}
from mesh_geometry import connected_components


# Boundary-locked reduction: no face may turn more than acos(0.5) = 60 degrees
# from its source orientation (MESH-LOD-OPEN-SEAMS-33).
LOCKED_MAX_TURN = 0.5


def boundary_vertices(triangles):
    """Vertex indices on an edge that is not shared by exactly two triangles:
    the rim of an open part and any non-manifold edge."""
    from collections import Counter
    edges = Counter(tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))) for t in triangles for i in range(3))
    return {x for edge, count in edges.items() if count != 2 for x in edge}


def profile_reduction(profile):
    """reduce_mesh keyword options a visual profile asks for. One reading for
    the converter and the size estimates (asset census, world estimate)."""
    return {'preserve_shared_seams': bool(profile.get('preserve_shared_seams', False)),
            'lock_boundaries': bool(profile.get('lock_boundaries', False))}


def reduce_for_profile(vertices, faces, profile, materials=None, name='mesh'):
    """Visual reduction a profile asks for: (vertices, faces, details).

    One implementation for the converter (prepare_mesh_bsp._prepare_model) and
    the size estimates (asset census, world estimate): ratio, the source shapes
    kept unreduced (preserve_shape_prefixes, matched on the NIF shape names of
    materials) and the reducer options (profile_reduction)."""
    ratio = profile.get('ratio')
    if not ratio:
        return vertices, faces, {}
    keep = set()
    prefixes = profile.get('preserve_shape_prefixes', [])
    if prefixes:
        if materials is None:
            raise ValueError('Shape-preserving profile needs the material list: ' + name)
        for prefix in prefixes:
            matched = {i for i, mat in enumerate(materials)
                       if mat.get('source_shape', '').casefold().startswith(prefix.casefold())}
            if not matched:
                raise ValueError('Missing preserved structural shape in ' + name)
            keep |= matched
    return reduce_mesh(vertices, faces, ratio, keep, **profile_reduction(profile))


def reduce_mesh(vertices, faces, ratio, preserve_materials=(), preserve_shared_seams=False,
                lock_boundaries=False):
    """Reduce each material component to about ratio of its triangles.

    Default reducer: fast_simplification, which also collapses rim edges, so
    an open part shrinks away from the neighbouring part it met at the rim
    (MESH-LOD-OPEN-SEAMS-33: the Silt Strider's shell plates part and show
    the sky). lock_boundaries=True uses the boundary-locked quadric reducer
    instead: rim vertices and vertices shared with another component keep
    their exact position, only interior edges collapse, so parts stay joined
    where the source joins them. The default stays selectable per profile
    (DON'T DELETE ANY METHOD)."""
    import fast_simplification
    if not 0 < ratio <= 1:
        raise ValueError('Invalid static LOD ratio')
    preserve_materials=set(preserve_materials)
    if not preserve_materials.issubset(set(faces[:,3])):
        raise ValueError('Preserved material is absent from mesh')
    if preserve_shared_seams:
        # Independently simplified materials cannot maintain a shared rim.
        # Keep both adjoining sections, including source UVs, until a boundary-
        # constrained reducer is available. Position identity ignores UV splits.
        owners = {}
        for material in set(faces[:, 3]):
            points = vertices[faces[faces[:, 3] == material, :3], :3].reshape(-1, 3)
            for point in points:
                owners.setdefault(tuple(point), set()).add(int(material))
        preserve_materials.update(m for group in owners.values() if len(group) > 1 for m in group)
    out_v, out_f = [], []
    groups=0
    shared_points=set();locked_total=0
    if lock_boundaries:
        # Positions used by more than one material component (rounded like
        # connected_components): seams between parts that are not rims.
        owners={}
        for material in sorted(set(faces[:,3])):
            mf=faces[faces[:,3]==material]
            for k,ids in enumerate(connected_components(vertices,mf)):
                for point in np.round(vertices[mf[ids][:,:3],:3].reshape(-1,3),2):
                    owners.setdefault(tuple(point),set()).add((int(material),k))
        shared_points={point for point,group in owners.items() if len(group)>1}
    for material in sorted(set(faces[:,3])):
        mf=faces[faces[:,3]==material]
        for ids in connected_components(vertices,mf):
            original=mf[ids];groups+=1
            if len(original)<=12 or ratio==1 or material in preserve_materials:
                for face in original:
                    n=len(out_v);out_v.extend(vertices[face[:3]].tolist())
                    out_f.append([n,n+1,n+2,int(material)])
                continue
            points,inverse=np.unique(vertices[original[:,:3],:3].reshape(-1,3),
                                     axis=0,return_inverse=True)
            triangles=inverse.reshape(-1,3)
            target=max(4,round(len(triangles)*ratio))
            if lock_boundaries:
                from mold_shell import quadric_simplify
                locked=boundary_vertices(triangles)|{i for i,point in enumerate(np.round(points,2))
                                                      if tuple(point) in shared_points}
                locked_total+=len(locked)
                rim=points[sorted(locked)]
                points,triangles=quadric_simplify(points,triangles,[target],max_turn=LOCKED_MAX_TURN,locked=locked,anchored=True)[target]
                kept={tuple(point) for point in points[np.unique(triangles)]}
                if any(tuple(point) not in kept for point in rim):
                    # Gate: a moved rim is exactly the open seam this mode exists to prevent.
                    raise ValueError('Boundary-locked reduction moved a rim vertex')
            else:
                points,triangles=fast_simplification.simplify(
                    points,triangles.astype(np.int32),target_count=target)
            if not len(triangles):
                raise ValueError('Static LOD removed a component')
            old=vertices[original[:,:3]]
            centres=old[:,:,:3].mean(axis=1)
            normals=np.cross(old[:,1,:3]-old[:,0,:3],old[:,2,:3]-old[:,0,:3])
            normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
            for face in triangles:
                tri=points[face];normal=np.cross(tri[1]-tri[0],tri[2]-tri[0])
                norm=np.linalg.norm(normal)
                if norm<1e-8:continue
                normal/=norm
                score=((centres-tri.mean(axis=0))**2).sum(axis=1)
                # Avoid projecting a deck triangle from its close underside.
                score=np.where(normals@normal>.25,score,np.inf)
                if not np.isfinite(score).any():
                    score=((centres-tri.mean(axis=0))**2).sum(axis=1)
                src=old[int(np.argmin(score))]
                basis=np.column_stack((src[1,:3]-src[0,:3],src[2,:3]-src[0,:3]))
                coords=(tri-src[0,:3])@np.linalg.pinv(basis).T
                uv=src[0,3:5]+coords[:,0,None]*(src[1,3:5]-src[0,3:5])+coords[:,1,None]*(src[2,3:5]-src[0,3:5])
                n=len(out_v)
                for xyz,st in zip(tri,uv):out_v.append([*xyz,*st,*src[:,5:].mean(axis=0)])
                out_f.append([n,n+1,n+2,int(material)])
    details={}
    if lock_boundaries:
        details={'reducer':'boundary-locked quadric (rims and shared seams kept)','locked_vertices':locked_total}
    return np.array(out_v),np.array(out_f),{**details,'source_triangles':len(faces),
        'lod_triangles':len(out_f),'material_components':groups,'ratio':ratio,
        'preserved_materials':sorted(int(x) for x in preserve_materials),
        'uv_mapping':'original UVs on preserved materials; nearest source triangle on reduced materials',
        'collision':'original full-detail source retained'}
