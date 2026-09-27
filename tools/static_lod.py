# SPDX-License-Identifier: GPL-3.0-only
"""Optional host-side static LOD, preserving material/component membership.

UVs are projected from the nearest same-material source triangle. This is an
approximation for a selected large prop, not a replacement for original source
geometry or collision. Keep the original geometry for collider generation.
"""
import numpy as np
from mesh_geometry import connected_components


def reduce_mesh(vertices, faces, ratio, preserve_materials=()):
    import fast_simplification
    if not 0 < ratio <= 1:
        raise ValueError('Invalid static LOD ratio')
    preserve_materials=set(preserve_materials)
    if not preserve_materials.issubset(set(faces[:,3])):
        raise ValueError('Preserved material is absent from mesh')
    out_v, out_f = [], []
    groups=0
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
    return np.array(out_v),np.array(out_f),{'source_triangles':len(faces),
        'lod_triangles':len(out_f),'material_components':groups,'ratio':ratio,
        'preserved_materials':sorted(int(x) for x in preserve_materials),
        'uv_mapping':'original UVs on preserved materials; nearest source triangle on reduced materials',
        'collision':'original full-detail source retained'}
