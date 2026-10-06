# SPDX-License-Identifier: GPL-3.0-only
"""Conservative endpoint-collapse prototype for sampled first-person meshes.

Keep every authored boundary vertex, UV seam and material split fixed. A
collapse reuses an existing endpoint's complete pose/UV/tint trajectory, never
nearest-face animation transfer. Unsafe candidates are skipped. A requested
triangle count is a goal, not permission to delete faces or cap source openings.
"""
from collections import Counter
import numpy as np


def edge_counts(faces):
    return Counter(tuple(sorted((int(a),int(b)))) for f in faces
                   for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])))


def boundary_edges(faces):
    return {edge for edge,count in edge_counts(faces).items() if count==1}


def projection_locks(shape, near=5., offset=(0.,0.,0.)):
    """Lock sampled silhouettes, near-plane intersections and scale extremes.

    Coordinates must be in view space; the caller supplies the same viewmodel
    offset as its coverage oracle. This supplements, never replaces, boundary
    and complete-pose coverage checks.
    """
    points=np.asarray(shape['positions'],dtype=float)+np.asarray(offset)
    faces=np.asarray(shape['faces'],dtype=int)
    triangles=points[:,faces]
    normals=np.cross(triangles[:,:,1]-triangles[:,:,0],triangles[:,:,2]-triangles[:,:,0])
    front=np.einsum('fij,fij->fi',normals,triangles[:,:,0])<0
    adjacent={}
    for i,face in enumerate(faces):
        for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
            adjacent.setdefault(tuple(sorted((int(a),int(b)))),[]).append(i)
    locked=set()
    for edge,indices in adjacent.items():
        if len(indices)!=2 or np.any(front[:,indices[0]]!=front[:,indices[1]]):locked.update(edge)
    clipped=(triangles[:,:,:,0].min(2)<near)&(triangles[:,:,:,0].max(2)>=near)
    locked.update(int(v) for v in faces[np.any(clipped,axis=0)].ravel())
    # Preserve the MDL quantization envelope as well as geometric boundaries.
    flat=points.reshape(-1,3);count=points.shape[1]
    locked.update(int(i%count) for i in np.r_[flat.argmin(0),flat.argmax(0)])
    return locked


def reduce_shape(shape, target, max_displacement=.25, max_uv_change=1/64, extra_locked=()):
    positions=np.asarray(shape['positions'],dtype=float)
    faces=np.asarray(shape['faces'],dtype=np.int64).copy()
    uv=np.asarray(shape['uv'],dtype=float);colours=np.asarray(shape['colours'],dtype=float)
    if positions.ndim!=3 or positions.shape[2]!=3 or not np.isfinite(positions).all():
        raise ValueError('Invalid sampled geometry')
    if faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or faces.min()<0 or faces.max()>=positions.shape[1]:
        raise ValueError('Invalid sampled topology')
    if uv.shape!=(positions.shape[1],2) or colours.shape!=(positions.shape[1],4) or not np.isfinite(uv).all() or not np.isfinite(colours).all():
        raise ValueError('Invalid sampled attributes')
    if not isinstance(target,int) or target<1 or max_displacement<0 or max_uv_change<0:
        raise ValueError('Invalid reduction limits')
    original_faces=len(faces);original_boundary=boundary_edges(faces)
    original_edges=edge_counts(faces)
    # Index boundaries include material/UV splits, whether or not an adjacent
    # shape overlaps them. Non-manifold edges are also immutable.
    locked={v for edge,count in original_edges.items() if count!=2 for v in edge}
    if any(type(v) is not int or not 0<=v<positions.shape[1] for v in extra_locked):
        raise ValueError('Invalid projection lock')
    locked.update(extra_locked)
    members={i:{i} for i in range(positions.shape[1])};accepted=[]
    while len(faces)>target:
        edges=edge_counts(faces);neighbours={i:set() for i in np.unique(faces)}
        for a,b in edges:neighbours[a].add(b);neighbours[b].add(a)
        candidates=[]
        for (a,b),count in edges.items():
            if count!=2 or a in locked or b in locked:continue
            # Link condition prevents pinches and merges of separate shells.
            adjacent=faces[np.any(faces==a,axis=1)&np.any(faces==b,axis=1)]
            opposite=set(adjacent.ravel())-{a,b}
            if neighbours[a]&neighbours[b]!=opposite:continue
            for keep,remove in ((a,b),(b,a)):
                group=sorted(members[keep]|members[remove])
                error=float(np.linalg.norm(positions[:,group]-positions[:,keep,None],axis=2).max())
                if error>max_displacement:continue
                if np.abs(uv[group]-uv[keep]).max()>max_uv_change:continue
                if np.abs(colours[group]-colours[keep]).max()>1e-6:continue
                candidates.append((error,keep,remove))
        changed=False
        for error,keep,remove in sorted(candidates):
            trial=faces.copy();trial[trial==remove]=keep
            surviving=(trial[:,0]!=trial[:,1])&(trial[:,1]!=trial[:,2])&(trial[:,2]!=trial[:,0])
            if int((~surviving).sum())!=2 or len(faces)-2<target:continue
            newfaces=trial[surviving]
            if len(np.unique(np.sort(newfaces,axis=1),axis=0))!=len(newfaces):continue
            if boundary_edges(newfaces)!=original_boundary:continue
            if any(count>2 and original_edges.get(edge)!=count for edge,count in edge_counts(newfaces).items()):continue
            affected=np.any(faces[surviving]==remove,axis=1)
            old=positions[:,faces[surviving][affected]];new=positions[:,newfaces[affected]]
            oldn=np.cross(old[:,:,1]-old[:,:,0],old[:,:,2]-old[:,:,0])
            newn=np.cross(new[:,:,1]-new[:,:,0],new[:,:,2]-new[:,:,0])
            oldarea=np.linalg.norm(oldn,axis=2);newarea=np.linalg.norm(newn,axis=2)
            if np.any(oldarea<1e-10) or np.any(newarea<oldarea*.25):continue
            if np.any(np.einsum('fij,fij->fi',oldn,newn)<.9*oldarea*newarea):continue
            # Positive UV orientation at every surviving face; no mirrored
            # sampling patch even if geometric orientation was unchanged.
            olduv=uv[faces[surviving][affected]];newuv=uv[newfaces[affected]]
            def area2(p):
                a=p[:,1]-p[:,0];b=p[:,2]-p[:,0]
                return a[:,0]*b[:,1]-a[:,1]*b[:,0]
            olda=area2(olduv);newa=area2(newuv)
            if np.any(olda*newa<=0):continue
            faces=newfaces;members[keep]|=members.pop(remove)
            accepted.append((keep,remove,error));changed=True;break
        if not changed:break
    used=np.unique(faces);mapping=np.full(positions.shape[1],-1,int);mapping[used]=np.arange(len(used))
    # Verify exact locked-edge endpoints and every authored pose before return.
    assert boundary_edges(faces)==original_boundary
    assert locked.issubset(set(used))
    result=dict(shape,positions=positions[:,used].copy(),faces=mapping[faces],uv=uv[used].copy(),colours=colours[used].copy())
    report={'source_triangles':original_faces,'triangles':len(faces),'target':target,
            'target_reached':len(faces)<=target,'locked_vertices':len(locked),
            'authored_boundary_edges':len(original_boundary),'new_boundary_edges':0,
            'accepted_collapses':len(accepted),'max_displacement':max((x[2] for x in accepted),default=0),
            'source_vertex_indices':used.tolist(),'all_sampled_poses':positions.shape[0]}
    return result,report
