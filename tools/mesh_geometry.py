# SPDX-License-Identifier: GPL-3.0-only
"""Convex surface merging, bounded UV patches and separate collision proxies.

Visible polygons preserve recesses. Collision is an approximation and must be
measured separately; its 14-direction support samples can miss small details.
"""
import collections
import numpy as np
from scipy.spatial import ConvexHull
from surface_grid import GRID_GUARD

def mapping_deviation(points,axes,offset,ref_axes,ref_offset):
 """Largest texture-coordinate difference at points between two affine
 mappings, in the mappings' units, ignoring whole-texture (wrap) shifts.

 The difference of two affine mappings is affine, so over a convex polygon
 its largest value is reached at a vertex: measuring the vertices is exact.
 Accepts one reference mapping or a stack (c,3,2)/(c,2); returns a float or
 an array of c values.
 """
 ref_axes=np.asarray(ref_axes,float);ref_offset=np.asarray(ref_offset,float)
 d=np.einsum('pi,...ij->...pj',points,ref_axes-axes)+(ref_offset-offset)[...,None,:]
 # Textures repeat: a whole-texture shift samples the same texels.
 k=np.round(d.mean(axis=-2,keepdims=True))
 return np.abs(d-k).max(axis=(-2,-1))

def merge_convex(patches,normal):
 """Greedy union of coplanar polygons that share two vertices into convex
 polygons; a union is kept only if its convex hull adds no area."""
 from scipy.spatial import ConvexHull
 drop=int(np.argmax(abs(np.asarray(normal))));dims=[k for k in range(3) if k!=drop]
 def area(q):
  x=q[:,dims[0]];y=q[:,dims[1]]
  return abs(float(np.dot(x,np.roll(y,-1))-np.dot(np.roll(x,-1),y)))/2
 def keys(q):return {tuple(k) for k in np.round(q,3).tolist()}
 alive={i:np.asarray(p) for i,p in enumerate(patches)};areas={i:area(p) for i,p in alive.items()}
 vkeys={i:keys(p) for i,p in alive.items()};owners=collections.defaultdict(set)
 for i,ks in vkeys.items():
  for k in ks:owners[k].add(i)
 queue=collections.deque(sorted(alive))
 while queue:
  i=queue.popleft()
  if i not in alive:continue
  counts=collections.Counter(j for k in vkeys[i] for j in owners[k] if j!=i)
  for j in sorted(counts):
   if counts[j]<2:continue
   pts=np.unique(np.round(np.concatenate((alive[i],alive[j])),5),axis=0)
   try:hull=ConvexHull(pts[:,dims])
   except Exception:continue
   poly=pts[hull.vertices];a=area(poly)
   if abs(a-areas[i]-areas[j])>.01:continue
   for k in vkeys[i]:owners[k].discard(i)
   for k in vkeys[j]:owners[k].discard(j)
   del alive[j],areas[j],vkeys[j]
   alive[i]=poly;areas[i]=a;vkeys[i]=keys(poly)
   for k in vkeys[i]:owners[k].add(i)
   queue.append(i);break
 return [alive[i] for i in sorted(alive)]

def fit_mapping(points,uv):
 """Least-squares 3D affine texture mapping uv ~ points @ axes + offset.

 Directions in which the points hardly spread (a flat set has no normal
 extent) get no axis component, so coplanar sets keep in-plane axes."""
 c=points.mean(axis=0);u=uv.mean(axis=0)
 axes=np.linalg.lstsq(points-c,uv-u,rcond=1e-3)[0]
 return axes,u-c@axes

def snapped_polygons(v,f,tolerance,stats=None):
 """surface_polygons with texture-mapping snapping (--texinfo-snap).

 Edge-connected triangles of one material grow a mapping cluster while one
 3D affine mapping (a Quake texinfo, which may span several planes)
 reproduces every member vertex's texture coordinates within `tolerance`
 (texture units: texels / texture size), modulo whole-texture repeats.
 Coplanar members of a cluster then merge into convex polygons; all
 polygons of a cluster carry its mapping, so placed copies share one texinfo.
 """
 tris=[]
 for face in f:
  p=v[face[:3],:3]*.25;uv=v[face[:3],3:5];n=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(n)
  if area<.05:continue
  n/=area
  # The triangle's own exact in-plane mapping (as surface_polygons).
  A=np.vstack((p[1]-p[0],p[2]-p[0],n));b=np.vstack((uv[1]-uv[0],uv[2]-uv[0],[0,0]));axes=np.linalg.solve(A,b)
  tris.append((p,uv,int(face[3]),(int(face[3]),*np.round(n,4),round(float(n@p[0]),2)),axes,uv[0]-p[0]@axes))
 keys=[[tuple(k) for k in np.round(t[0],3).tolist()] for t in tris]
 edges=collections.defaultdict(list)
 for i,ks in enumerate(keys):
  for a,b in ((0,1),(1,2),(2,0)):edges[frozenset((ks[a],ks[b]))].append(i)
 neighbours=[set() for _ in tris]
 for owners in edges.values():
  for i in owners:
   for j in owners:
    if i!=j and tris[i][2]==tris[j][2]:neighbours[i].add(j)
 cluster_of=[-1]*len(tris);clusters=[];worst=0.
 for seed in range(len(tris)):
  if cluster_of[seed]>=0:continue
  cid=len(clusters);members=[seed];cluster_of[seed]=cid
  P=tris[seed][0].copy();U=tris[seed][1].copy()
  axes,off=tris[seed][4],tris[seed][5]
  # Shared mappings stay near the members' own texel density: no long axes
  # fitted to near-degenerate point sets (precision, mip choice).
  limit=1.5*np.linalg.norm(axes,axis=0)+1e-9
  todo=collections.deque(sorted(neighbours[seed]))
  while todo:
   t=todo.popleft()
   if cluster_of[t]>=0:continue
   p,uv=tris[t][0],tris[t][1]
   # A whole-texture shift samples the same texels (textures repeat).
   uv=uv-np.round((uv-(p@axes+off)).mean(axis=0))
   P2=np.vstack((P,p));U2=np.vstack((U,uv))
   ax2,off2=fit_mapping(P2,U2)
   if np.abs(P2@ax2+off2-U2).max()>tolerance:continue
   if np.any(np.linalg.norm(ax2,axis=0)>np.maximum(limit,1.5*np.linalg.norm(tris[t][4],axis=0))):continue
   P,U,axes,off=P2,U2,ax2,off2;members.append(t);cluster_of[t]=cid
   todo.extend(sorted(j for j in neighbours[t] if cluster_of[j]<0))
  worst=max(worst,float(np.abs(P@axes+off-U).max()))
  clusters.append((members,axes,off))
 result=[]
 for members,axes,off in clusters:
  planes=collections.defaultdict(list)
  for i in members:planes[tris[i][3]].append(i)
  for key,ids in planes.items():
   normal=np.array(key[1:4])
   for poly in merge_convex([tris[i][0] for i in ids],normal):
    result.append((poly,int(key[0]),axes,off,normal))
 if stats is not None:
  stats['triangles']=stats.get('triangles',0)+len(tris)
  stats['mapping_clusters']=stats.get('mapping_clusters',0)+len(clusters)
  stats['polygons']=stats.get('polygons',0)+len(result)
  stats['max_deviation']=max(stats.get('max_deviation',0.),worst)
 return result

def surface_polygons(v,f,geometry_only=False,snap=None,stats=None):
 if snap is not None and not geometry_only:return snapped_polygons(v,f,snap,stats)
 groups=collections.defaultdict(list)
 for face in f:
  p=v[face[:3],:3]*.25; uv=v[face[:3],3:5]; n=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(n)
  if area<.05:continue
  n/=area
  # Texture affine derivatives on the surface, with zero normal component.
  A=np.vstack((p[1]-p[0],p[2]-p[0],n));b=np.vstack((uv[1]-uv[0],uv[2]-uv[0],[0,0]));axes=np.linalg.solve(A,b);off=uv[0]-p[0]@axes
  key=(0 if geometry_only else int(face[3]),*np.round(n,4),round(float(n@p[0]),2))
  if not geometry_only:key+=(*np.round(axes.flatten(),5),*np.round(off,3))
  groups[key].append((p,axes,off))
 result=[]
 for key,tris in groups.items():
  # Merge only complete convex unions; disconnected regions stay separate.
  patches=[]
  for p,ax,off in tris:
   patches.append(p)
  changed=True
  while changed:
   changed=False
   for i in range(len(patches)):
    if changed:break
    for j in range(i+1,len(patches)):
     a,b=patches[i],patches[j]
     common=sum(any(np.linalg.norm(x-y)<.005 for y in b) for x in a)
     if common<2:continue
     n=np.array(key[1:4]);drop=np.argmax(abs(n));dims=[k for k in range(3) if k!=drop]
     pts=np.unique(np.round(np.concatenate((a,b)),5),axis=0)
     hull=ConvexHull(pts[:,dims]); poly=pts[hull.vertices]
     area=lambda q:abs(sum(q[k,dims[0]]*q[(k+1)%len(q),dims[1]]-q[(k+1)%len(q),dims[0]]*q[k,dims[1]] for k in range(len(q))))/2
     if abs(area(poly)-area(a)-area(b))>.01:continue
     patches[i]=poly;patches.pop(j);changed=True;break
  for poly in patches:result.append((poly,int(key[0]),tris[0][1],tris[0][2],np.array(key[1:4])))
 return result

def connected_components(v,f):
 pts,ix=np.unique(np.round(v[:,:3],2),axis=0,return_inverse=True);parent=list(range(len(pts)))
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for a,b,c,_ in f:
  parent[find(ix[b])]=find(ix[a]);parent[find(ix[c])]=find(ix[a])
 out=collections.defaultdict(list)
 for i,face in enumerate(f):out[find(ix[face[0]])].append(i)
 return list(out.values())

def collision_parts(v,f,tolerance=2):
 results=[];tris=v[f[:,:3],:3]*.25
 def split(ids,depth):
  p=np.unique(np.round(tris[ids].reshape(-1,3)*16)/16,axis=0);offset=p.mean(axis=0)
  if len(p)<3:return
  _,sig,axes=np.linalg.svd(p-offset,full_matrices=False)
  if sig[-1]<.15:
   normal=axes[-1];p=np.vstack((p-normal*.2,p+normal*.2))
  dirs=np.array([(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]+[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)])
  choice=np.unique(np.argmax(p@dirs.T,axis=0));candidate=p[choice]
  if len(candidate)>=4 and np.linalg.matrix_rank(candidate-candidate[0])==3:p=candidate
  hull=ConvexHull(p)
  # Interior source surface samples reveal concave recesses closed by this hull.
  samples=tris[ids].mean(axis=1)
  inside=-(samples@hull.equations[:,:3].T+hull.equations[:,3]).max(axis=1)
  error=float(inside.max())
  if error>tolerance and len(ids)>4 and depth<8:
   axis=np.argmax(np.ptp(samples,axis=0));order=np.argsort(samples[:,axis]);mid=len(order)//2
   split(np.array(ids)[order[:mid]],depth+1);split(np.array(ids)[order[mid:]],depth+1);return
  results.append((p,hull,ids,error))
 for ids in connected_components(v,f):split(ids,0)
 return results

def split_surface(poly,ax):
 uv=poly@ax[:,:3].T+ax[:,3]
 for a in range(2):
  # Widen by GRID_GUARD before rounding: placement and single-precision
  # storage move a span that ends exactly on 16-texel lines by a few
  # millionths of a texel, and the engine then rounds each end one block
  # outward (240 -> 272 > 256, MESH-EXTENT-GRID-31). With the guard such a
  # span is split; anything kept stays within 240 texels on any FPU.
  lo=np.floor((uv[:,a].min()-GRID_GUARD)/16)*16;hi=np.ceil((uv[:,a].max()+GRID_GUARD)/16)*16
  if hi-lo<=240:continue
  cut=lo+224;dist=uv[:,a]-cut;front=[];back=[]
  for i,p in enumerate(poly):
   j=(i+1)%len(poly);d,e=dist[i],dist[j]
   if d<=1e-6:back.append(p)
   if d>=-1e-6:front.append(p)
   if (d>1e-6 and e< -1e-6) or (d< -1e-6 and e>1e-6):
    q=p+(poly[j]-p)*d/(d-e);front.append(q);back.append(q)
  assert len(back)>=3 and len(front)>=3
  return split_surface(np.array(back),ax)+split_surface(np.array(front),ax)
 return [poly]

def collision_pieces(v,f,profile):
 """Collision proxies of one mesh under its profile: (pieces, exact_bevels, note).

 One implementation for the converter and the size estimates. The convex
 approximation (collision_parts) may close authored space. A profile with
 surface_collision_beyond (exterior architecture of converted towns,
 town_regions.visual_profile) keeps each authored collision surface instead
 when the deepest closed space exceeds that height, the engine's step height:
 the player cannot step over such invented solid and residents standing in it
 are buried (VIVEC-ARENA-ACTORS-32).
 """
 if profile.get('collision_none'):
  return [],False,'explicit nonsolid source/category policy'
 exact=bool(profile.get('exact_collision_bevels'))
 if profile.get('hollow_collision'):
  return shell_collision_parts(v,f),exact,None
 pieces=collision_parts(v,f,2)
 limit=profile.get('surface_collision_beyond')
 if limit is not None:
  fill=max((error for _,_,_,error in pieces),default=0.)
  if fill>limit:
   return shell_collision_parts(v,f),True,('authored collision surfaces: convex approximation closes '
                                           f'{fill:.2f} units > {limit} step height')
 return pieces,exact,None

def shell_collision_parts(v,f,thickness=.2):
 """Thin convex prisms preserve a hollow authored interior collision shell.

 Enclosing an entire connected room with one convex volume fills its free space.
 Merge only actual planar surfaces, then give each a small two-sided thickness.
 """
 out=[]
 for poly,material,axes,offset,normal in surface_polygons(v,f,geometry_only=True):
  points=np.vstack((poly-normal*thickness,poly+normal*thickness))
  out.append((points,ConvexHull(points),[],0.))
 return out
