# SPDX-License-Identifier: GPL-3.0-only
"""Compile the union of expanded convex pieces to a compact native BSP tree."""
import hashlib
from itertools import product
import os
from pathlib import Path
import pickle
import struct
import subprocess
import tempfile
import numpy as np
from scipy.spatial import ConvexHull
from player_hull import MINS,MAXS,lumps


class StandingHullInexact(ValueError):
    """The compiled standing hull is not the union of its pieces (standing_check failed): .check holds the
    measurement. A ValueError, so every caller's compile fallback takes it (CHIM-COMPILED-HULL-SHORT-36)."""

    def __init__(self,check):
        self.check=check
        super().__init__('compiled standing hull inexact: short %(short)s, over %(over)s units'%check)


def compile_standing(pieces,qbsp,cache,grid=64,check_box=None,patch=True,strict=False):
    """The compiled standing hull (nodes, root) of the pieces (compile_standing_checked). strict: raise
    StandingHullInexact when the hull still is not the union of the pieces (the caller falls back to another
    hull); otherwise return it as it is."""
    result,check=compile_standing_checked(pieces,qbsp,cache,grid,check_box,patch)
    if strict and (check['short']>0 or check['over']>0):raise StandingHullInexact(check)
    return result


MERGE_COPLANAR='Qt C-0.01'     # qhull: merge facets whose centrums lie within 0.01 units (one plane per flat side)


def compile_standing_checked(pieces,qbsp,cache,grid=64,check_box=None,patch=True):
    """compile_standing_checked_once; when qbsp refuses the brushes with a non-convex face (near-coplanar facets of a
    piece's hull written as separate planes make sliver faces: Ashurnibibi's ruins, CHIM-COLLISION-UNION-FALLBACK-41),
    once more with those facets merged (MERGE_COPLANAR). Hulls that compile today are unchanged: same brushes, same
    cache key. The retry's result passes the same standing check."""
    try:
        return compile_standing_checked_once(pieces,qbsp,cache,grid,check_box,patch)
    except ValueError as error:
        if 'non-convex face' not in str(error):raise
        try:
            return compile_standing_checked_once(pieces,qbsp,cache,grid,check_box,patch,merge_coplanar=True)
        except ValueError as again:
            raise ValueError('%s | retried with coplanar facets merged: %s'%(str(error)[:300],str(again)[:300])) from again


def compile_standing_checked_once(pieces,qbsp,cache,grid=64,check_box=None,patch=True,merge_coplanar=False):
    """grid: the expanded corners are merged on a 1/grid unit lattice (64, as for the models; a finer
    lattice leaves qbsp slivers, seam holes in the CHIM terrain hull: CHIM-SEYDA-MEMORY-33).
    The compiled hull is checked against the exact union of the pieces (standing_check over check_box, default
    the pieces' plan): where the compiler lost pieces under a walkable top, patch (default) adds those pieces
    exactly (patch_holes). Returns (result, check); the check is cached with the result
    (CHIM-COMPILED-HULL-SHORT-36)."""
    corners=np.array(list(product(*zip(MINS,MAXS))))
    brushes=[]
    for points,hull,ids,error in pieces:
        expanded=(points[:,None,:]-corners[None,:,:]).reshape(-1,3)
        expanded=np.unique(np.round(expanded*grid)/grid,axis=0)
        convex=(ConvexHull(expanded,qhull_options=MERGE_COPLANAR) if merge_coplanar else ConvexHull(expanded))
        seen=set();lines=['{']
        for equation in convex.equations:
            n=equation[:3];d=-equation[3]
            key=(*np.round(n,4),round(d,3))
            if key in seen:continue
            seen.add(key)
            axis=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,axis);u/=np.linalg.norm(u);v=np.cross(n,u)
            centre=n*d
            points=(centre+u*256,centre,centre+v*256)
            lines.append(' '.join('( '+' '.join(f'{x:.8f}' for x in point)+' )' for point in points)+' stone 0 0 0 1 1')
        brushes.append('\n'.join(lines+['}']))
    source='{\n"classname" "worldspawn"\n'+'\n'.join(brushes)+'\n}\n'
    # Compiler identity and format are part of the cache key.
    compiler=Path(qbsp).resolve();key=hashlib.sha256(source.encode()+compiler.read_bytes()).hexdigest()
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    box=None if check_box is None else tuple(round(float(v),6) for v in check_box)
    # the cached entry holds the result and its check (CHECK_VERSION, box, patch): older entries are not read
    path=cache/('%s.%s.pickle'%(key,hashlib.sha256(repr((CHECK_VERSION,box,bool(patch))).encode()).hexdigest()[:16]))
    if path.is_file():
        result,check=pickle.loads(path.read_bytes());_sweep(key,pieces,check)
        return result,check
    with tempfile.TemporaryDirectory(prefix='aw-collision-') as tmp:
        tmp=Path(tmp);(tmp/'collision.map').write_text(source)
        result=subprocess.run([str(compiler),'-noclip','-nofill','-nopercent','collision.map'],cwd=tmp,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if result.returncode:
            # the exit code and qbsp's own error lines first: its tail is often warning noise (CHIM-COLLISION-UNION-FALLBACK-41)
            text=result.stdout.decode(errors='replace')
            errors=[l.strip() for l in text.splitlines() if 'error' in l.lower() and 'warning' not in l.lower()]
            raise ValueError('Collision compiler failed (exit %d%s): %s | output tail: %s'%(result.returncode,
                ', signal %d'%-result.returncode if result.returncode<0 else '','; '.join(errors[-3:]) or 'no error line',text[-600:]))
        data=lumps((tmp/'collision.bsp').read_bytes())
    planes=list(struct.iter_unpack('<4fi',data[1]));nodes=list(struct.iter_unpack('<ihh6h2H',data[5]));leaves=list(struct.iter_unpack('<ii6h2H4B',data[10]))
    root=struct.unpack_from('<i',data[14],36)[0];found=set();order=[];stack=[root]
    while stack:
        n=stack.pop()
        if n<0 or n in found:continue
        found.add(n);order.append(n);stack.extend(nodes[n][1:3])
    remap={old:i for i,old in enumerate(order)}
    def child(n):
        if n>=0:return remap[n]
        contents=leaves[-n-1][0]
        if contents not in (-1,-2):raise ValueError('Unexpected collision contents')
        return contents
    packed=[(planes[nodes[n][0]][:4],child(nodes[n][1]),child(nodes[n][2])) for n in order]
    result=(packed,remap[root] if root>=0 else child(root))
    implicated=set();check=standing_check(result,pieces,box,implicated=implicated)
    patched=0
    # Holes (pieces the compiler lost under a walkable top) are patched with the exact pieces themselves, a few
    # rounds at most; a hull that still fails, or one that floats above the union, is refused.
    while patch and check['short']>0 and check['over']==0 and implicated and patched<PATCH_ROUNDS:
        patched+=1
        result=patch_holes(result,pieces,implicated)
        more=set();check=standing_check(result,pieces,box,implicated=more)
        implicated=more
    if patched:check=dict(check,patched_rounds=patched,patched_nodes=len(result[0])-len(packed))
    # Atomic: maps compiled side by side share this content-addressed cache.
    partial=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');partial.write_bytes(pickle.dumps((result,check),protocol=4))
    os.replace(partial,path);_sweep(key,pieces,check)
    return result,check


def _sweep(key,pieces,check):
    """AMIWIND_HULL_SWEEP=<file>: append this compiled hull's standing_check (JSON line, keyed by the SHA-256 of
    its compiler source) for an island-wide sweep (CHIM-COMPILED-HULL-SHORT-36). Off by default."""
    target=os.environ.get('AMIWIND_HULL_SWEEP')
    if not target:return
    import json
    pts=np.vstack([p[0] for p in pieces])
    row=dict(check,sha256=key,pieces=len(pieces),
             extent=[round(float(v),1) for v in (*pts.min(axis=0),*pts.max(axis=0))],
             label=os.environ.get('AMIWIND_HULL_SWEEP_LABEL',''))
    with open(target,'a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
    if row['short']>0 and os.environ.get('AMIWIND_HULL_SWEEP_PIECES'):
        # the pieces of a short hull, for inspection (sweep only)
        np.savez_compressed(Path(os.environ['AMIWIND_HULL_SWEEP_PIECES'])/(key[:16]+'.npz'),*[p[0] for p in pieces])


# The exactness check of a compiled standing hull (CHIM-COMPILED-HULL-SHORT-36): one implementation for every
# caller (chunk terrain, CHIM models, legacy maps). qbsp snaps and merges planes, so on small or thin pieces the
# compiled union can lie units inside or outside the exact one.
CHECK_VERSION=2         # the cached verdicts of an older check are not reused
PATCH_ROUNDS=3          # rounds of hole patching before a compiled hull is refused
CHECK_TOLERANCE=0.25    # a box must be held this close below the exact surface and be free this close above it
CHECK_SIDE=0.05         # samples this close to a piece's side are not judged (either answer is right there)
CHECK_SAMPLES=4096      # at most this many lattice columns per hull (finer lattice on small hulls)
WALKABLE=0.7            # a face a box stands on: normal z at least this (Quake's onground rule)


def check_samples(pieces,box=None,step=8.0):
    """(x, y) columns of the check: a lattice over box (x0, y0, x1, y1; default the pieces' expanded plan)
    every `step` units (coarser on a large hull: at most CHECK_SAMPLES), the seam samples 0.25, 2 and 5 units
    inside every edge of box, and the plan centre of every piece inside it."""
    if box is None:
        pts=np.vstack([p[0] for p in pieces])
        box=(pts[:,0].min()-MAXS[0],pts[:,1].min()-MAXS[1],pts[:,0].max()-MINS[0],pts[:,1].max()-MINS[1])
    x0,y0,x1,y1=box
    step=max(step,((x1-x0)*(y1-y0)/CHECK_SAMPLES)**.5)
    n=max(1,int(round((x1-x0)/step)));m=max(1,int(round((y1-y0)/step)))
    out=[(x0+(x1-x0)*(i+.5)/n,y0+(y1-y0)*(j+.5)/m) for i in range(n) for j in range(m)]
    for d in (0.25,2.0,5.0):
        for k in range(n+1):
            t=min(max(k/n,.01),.99)
            out+=[(x0+d,y0+t*(y1-y0)),(x1-d,y0+t*(y1-y0))]
        for k in range(m+1):
            t=min(max(k/m,.01),.99)
            out+=[(x0+t*(x1-x0),y0+d),(x0+t*(x1-x0),y1-d)]
    for points,_,_,_ in pieces:
        c=points[:,:2].mean(axis=0)
        if x0<c[0]<x1 and y0<c[1]<y1:out.append((float(c[0]),float(c[1])))
    return np.array(out,dtype=float)


def _intervals(pieces,xy,grow):
    """Per piece and column, the z interval a standing box's origin is solid in (the piece expanded by the box
    exactly, without the compile lattice), every face moved outward by `grow` units (negative: inward), and the
    normal z of the face that makes the interval's top: (lo, hi, top_nz) arrays of shape (pieces, columns);
    empty where lo > hi."""
    corners=np.array(list(product(*zip(MINS,MAXS))))
    los,his,nzs=[],[],[]
    for points,_,_,_ in pieces:
        eq=ConvexHull((points[:,None,:]-corners[None,:,:]).reshape(-1,3)).equations
        a,b,c,e=eq[:,0],eq[:,1],eq[:,2],eq[:,3]-grow
        lin=xy[:,0:1]*a+xy[:,1:2]*b+e
        flat=np.abs(c)<1e-9
        ok=np.all(lin[:,flat]<=0,axis=1) if flat.any() else np.ones(len(xy),bool)
        up,down=c>1e-9,c<-1e-9
        if up.any():
            tops=-lin[:,up]/c[up];k=np.argmin(tops,axis=1)
            hi=tops[np.arange(len(xy)),k];nz=c[up][k]
        else:
            hi=np.full(len(xy),np.inf);nz=np.zeros(len(xy))
        lo=np.max(-lin[:,down]/c[down],axis=1) if down.any() else np.full(len(xy),-np.inf)
        bad=~ok|(lo>hi)
        los.append(np.where(bad,np.inf,lo));his.append(np.where(bad,-np.inf,hi));nzs.append(nz)
    return np.array(los),np.array(his),np.array(nzs)


def _merged(lo,hi,nz):
    """Union of intervals on one column, sorted: [[lo, hi, normal z of the face at hi, the pieces in it]]."""
    out=[]
    for a,b,n,i in sorted((a,b,n,i) for i,(a,b,n) in enumerate(zip(lo,hi,nz)) if a<=b):
        if out and a<=out[-1][1]+1e-9:
            out[-1][3].append(i)
            if b>out[-1][1]:out[-1][1]=b;out[-1][2]=n
        else:out.append([a,b,n,[i]])
    return out


def standing_check(compiled,pieces,box=None,step=8.0,implicated=None):
    """Compare a compiled standing hull ((nodes, root) of compile_standing) with the exact union of its pieces on
    the columns of check_samples, where a box can stand: at every top of the union whose face is walkable
    (normal z >= WALKABLE, Quake's floor rule) a box must be held CHECK_TOLERANCE below the exact height and be
    free CHECK_TOLERANCE above it. (A steep face's height is not judged: a lattice step on it is a large
    vertical difference that changes nothing for a box.) Returns {'short': units the hull lies below an exact
    walkable top (a box sinks), 'over': above it (a box floats), 'columns': judged, 'worst_at': [x, y, z] of the
    worst short top}; short and over 0 for an exact hull. implicated: a set that receives the indices of the
    pieces under every short top (patch_holes)."""
    nodes,root=compiled
    def contents(x,y,z):
        n=root
        while n>=0:
            (nx,ny,nz,d),front,back=nodes[n]
            n=front if nx*x+ny*y+nz*z-d>=0 else back
        return n
    xy=check_samples(pieces,box,step)
    ilo,ihi,inz=_intervals(pieces,xy,-CHECK_SIDE)
    olo,ohi,onz=_intervals(pieces,xy,CHECK_SIDE)
    worst={'short':0.,'over':0.};judged=0;where={}
    t=CHECK_TOLERANCE
    for k,(x,y) in enumerate(xy):
        inner=_merged(ilo[:,k],ihi[:,k],inz[:,k]);outer=_merged(olo[:,k],ohi[:,k],onz[:,k])
        if not outer:continue
        judged+=1
        for a,b,n,ids in inner:
            if not (np.isfinite(b) and n>=WALKABLE and b-a>2*t) or contents(x,y,b-t)==-2:continue
            if implicated is not None:implicated.update(i for i in ids if ihi[i,k]>=b-t)
            z0,z1=b-max(64.,b-a),b-t
            if contents(x,y,z0)==-2:
                for _ in range(24):
                    zm=(z0+z1)/2;z0,z1=(zm,z1) if contents(x,y,zm)==-2 else (z0,zm)
                gap=b-z0
            else:gap=b-a
            if gap>worst['short']:worst['short']=gap;where['short']=[round(float(x),2),round(float(y),2),round(float(b),2)]
        for a,b,n,_ in outer:
            if np.isfinite(b) and n>=WALKABLE and not any(a2<=b+t<=b2 for a2,b2,_,_ in outer) and contents(x,y,b+t)!=-1:
                worst['over']=max(worst['over'],t)
    return dict({k:round(float(v),3) for k,v in worst.items()},columns=judged,**({'worst_at':where['short']} if where else {}))


def patch_holes(compiled,pieces,indices):
    """The compiled hull with the given pieces added where it is empty: every empty leaf of the compiled tree
    leads to one shared chain of those pieces, each expanded by the standing box exactly (its convex hull, edge
    bevels included), as the routed and chained hulls hold them. A point inside the result is inside the compiled
    hull or one of the pieces: the union does not grow past the pieces (CHIM-COMPILED-HULL-SHORT-36)."""
    nodes,root=compiled
    nodes=list(nodes);corners=np.array(list(product(*zip(MINS,MAXS))))
    chain=[]
    for i in sorted(indices):
        eq=ConvexHull((pieces[i][0][:,None,:]-corners[None,:,:]).reshape(-1,3)).equations
        chain.append([(tuple(float(v) for v in e[:3])+(float(-e[3]),)) for e in eq])
    if not chain:return compiled
    first=len(nodes);out=[]
    for k,planes in enumerate(chain):
        start=first+len(out);after=start+len(planes)
        nxt=after if k<len(chain)-1 else -1          # outside this piece: the next piece, or empty
        for j,plane in enumerate(planes):
            out.append((plane,nxt,start+j+1 if j<len(planes)-1 else -2))
    head=first
    def lead(c):return head if c==-1 else c
    nodes=[(plane,lead(f),lead(b)) for plane,f,b in nodes]+out
    return nodes,(head if root==-1 else root)
