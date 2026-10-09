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

def collision_pieces(v,f,profile,stairs=None):
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
 mode=stair_mitigation_mode() if stairs is None else stairs
 if profile.get('hollow_collision'):
  # Authored surface plates of a mesh with stairs need exact standing bevels:
  # a thin plate's approximate (axial) standing hull grows into the space
  # above a turned or sloped neighbour, and a spiral stairwell closes
  # (COLLISION-STAIR-SLOPE-32). Other meshes keep their profile's bevels
  # (exact everywhere would exceed the clip-node budget of large rooms).
  if exact or mode=='off' or not len(stair_treads(v,f)):
   return shell_collision_parts(v,f),exact,None
  return shell_collision_parts(v,f),True,'stairs: exact bevels on the authored plates of a mesh with stairs'
 pieces=collision_parts(v,f,2)
 limit=profile.get('surface_collision_beyond')
 if limit is not None:
  fill=max((error for _,_,_,error in pieces),default=0.)
  if fill>limit:
   return shell_collision_parts(v,f),True,('authored collision surfaces: convex approximation closes '
                                           f'{fill:.2f} units > {limit} step height')
 if mode!='off':
  pieces,plates,stats=mitigate_stairs(v,f,pieces,mode)
  if stats:
   note='stairs: '+'; '.join(f"{s['action']} (proxy {s['proxy_angle']:.1f} deg, {s['buried_depth']:.1f} over a tread)" for s in stats)
   return pieces,True if exact else plates,note
 return pieces,exact,None

# Stair mitigation (COLLISION-STAIR-SLOPE-32). Reference behaviour: Morrowind,
# as reimplemented by OpenMW 0.51, collides against the authored triangles
# (or the NIF RootCollisionNode), never a convex hull; its stepper climbs
# risers up to sStepSizeUp 34 units (8.5 here) and stands on slopes up to
# sMaxSlope 46 degrees (components/misc/constants.hpp). Quake stands on a
# plane with normal z >= 0.7 (this engine: AW_WALKABLE_Z 0.69, about 46.4
# degrees) and steps up STEPSIZE 8.5. A convex proxy over a staircase becomes
# a ramp through the nosings plus whatever else the piece holds; when that
# ramp is steeper than the walkable limit the steps cannot be climbed.
STAIR_MODES=('on','ramps','off')
TREAD_NZ=.985          # tread: an upward face within 10 degrees of level
RISER_NZ=.15           # riser: a face within 9 degrees of vertical
STAIR_PLATE_BUDGET=96  # 'on' keeps authored plates up to this many per piece

def stair_mitigation_mode():
 """The stair rule's mode for this build: 'on' (default), 'ramps' or 'off'.
 tools/build.py exports it from follow_original_stair_rules
 (config/build-defaults.json, --[no-]follow-original-stair-rules) as
 AMIWIND_STAIR_MITIGATION (mesh_geometry_env), so every converter worker
 and the image step see the same choice."""
 from mesh_geometry_env import stair_mode
 return stair_mode()

def _top_face(equations,point):
 """The convex hull face directly above an XY point: (z, normal z) or None."""
 up=equations[equations[:,2]>1e-9]
 if not len(up):return None
 z=-(up[:,3]+up[:,0]*point[0]+up[:,1]*point[1])/up[:,2]
 i=int(np.argmin(z));return float(z[i]),float(up[i,2])

def stair_profile(tris,ids,step=None):
 """Tread levels, riser heights and tread centroids of the triangles ids, or
 None when they are not a staircase climbable step by step: at least two
 tread levels, a riser, and no gap between levels above the step height
 (a ledge taller than a step stays a wall)."""
 from player_hull import STEP_HEIGHT
 step=STEP_HEIGHT if step is None else step
 t=tris[ids];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);a=np.linalg.norm(n,axis=1)
 ok=a>1e-6;nz=np.zeros(len(ids));nz[ok]=n[ok,2]/a[ok]
 tread=np.array(ids)[ok&(nz>TREAD_NZ)];riser=np.array(ids)[ok&(np.abs(nz)<RISER_NZ)]
 if len(tread)<2 or not len(riser):return None
 heights=np.sort(tris[tread][:,:,2].mean(axis=1))
 levels=[heights[0]]
 for h in heights[1:]:
  if h-levels[-1]>.25:levels.append(h)
 if len(levels)<2:return None
 gaps=np.diff(levels)
 if gaps.max()>step+1e-3:return None
 return dict(tread=tread,riser=riser,levels=levels,max_riser=float(gaps.max()),
             centroids=tris[tread].mean(axis=1))

def _segment_distance(p0,p1,q0,q1):
 """Distances in plan between segment p0-p1 and each segment q0[i]-q1[i]."""
 def point_seg(p,a,b):
  ab=b-a;l=np.maximum((ab*ab).sum(axis=-1),1e-12)
  t=np.clip(((p-a)*ab).sum(axis=-1)/l,0,1)
  return np.linalg.norm(a+ab*t[...,None]-p,axis=-1)
 d=np.minimum.reduce([point_seg(p0,q0,q1),point_seg(p1,q0,q1),
                      point_seg(q0,p0[None],p1[None]),point_seg(q1,p0[None],p1[None])])
 # crossing segments
 def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
 r=p1-p0;s=q1-q0;den=cross(r[None],s)
 with np.errstate(all='ignore'):
  tt=cross(q0-p0,s)/den;uu=cross(q0-p0,r[None])/den
 hit=(np.abs(den)>1e-12)&(tt>=0)&(tt<=1)&(uu>=0)&(uu<=1)
 return np.where(hit,0.,d)

def stair_treads(v,f,step=None):
 """Indices of the stair treads of a mesh: level upward triangles (at least
 2 square units) that a riser joins to another level triangle: the riser is
 a group of near-vertical triangles at least 4 units wide, touching (within
 0.75 in plan) a level triangle at its top and another 1..step lower. Rock ledges, leaves and trinkets without such steps have none."""
 from player_hull import STEP_HEIGHT
 step=STEP_HEIGHT if step is None else step
 tris=v[f[:,:3],:3]*.25
 n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);a=np.linalg.norm(n,axis=1)
 nz=np.zeros(len(f));ok=a>1e-6;nz[ok]=n[ok,2]/a[ok]
 riser=np.flatnonzero(ok&(np.abs(nz)<RISER_NZ))
 level=np.flatnonzero(ok&(nz>TREAD_NZ)&(a/2>=2.))
 if not len(riser) or len(level)<2:return np.array([],int)
 lz=tris[level][:,:,2].mean(axis=1)
 le0=tris[level][:,:,:2];le1=np.roll(le0,-1,axis=1)
 # Group riser triangles that share a vertex position and lie in one plane.
 key=np.round(tris[riser]*16).astype(np.int64)
 parent=list(range(len(riser)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 seen={}
 for i in range(len(riser)):
  for j in range(3):
   k=tuple(key[i,j])
   if k in seen and abs(np.dot(n[riser[i]],n[riser[seen[k]]]))>.98*a[riser[i]]*a[riser[seen[k]]]:
    parent[root(i)]=root(seen[k])
   else:seen.setdefault(k,i)
 groups={}
 for i in range(len(riser)):groups.setdefault(root(i),[]).append(riser[i])
 out=set()
 for members in groups.values():
  pts=tris[members].reshape(-1,3);lo,hi=pts[:,2].min(),pts[:,2].max()
  if hi-lo<1.:continue
  xy=pts[:,:2];c=xy.mean(axis=0);_,_,vt=np.linalg.svd(xy-c);u=vt[0]
  proj=(xy-c)@u;p0=c+u*proj.min();p1=c+u*proj.max()
  if proj.max()-proj.min()<4:continue
  def touching(cand):
   if not len(cand):return cand
   d=_segment_distance(p0,p1,le0[cand].reshape(-1,2),le1[cand].reshape(-1,2)).reshape(-1,3).min(axis=1)
   return cand[d<.75]
  # The upper tread at the riser top; the lower one 1..step below it (a
  # stepped block's riser may reach below the lower tread).
  top=touching(np.flatnonzero(np.abs(lz-hi)<.15))
  if not len(top):continue
  low=touching(np.flatnonzero((lz>=max(lo-.15,hi-step-1e-3))&(lz<=hi-1.)))
  if len(low):out.update(level[np.concatenate((top,low))].tolist())
 return np.array(sorted(out),int)

def mitigate_stairs(v,f,pieces,mode='on',walkable=None,step=None):
 """The one stair rule for every converter (towns, world, interiors, CHIM).

 v, f: the collision mesh as collision_parts takes it (source units, x0.25
 inside); pieces: its convex proxy (collision_parts, [(points, hull, ids,
 error)]). The stair treads of the mesh are found (stair_treads: level
 triangles next to risers of at most a step). A piece is changed only when
 it buries one of them: the proxy face directly above the tread stands more
 than 0.5 above it and is too steep to stand on (normal z below walkable),
 or stands more than a step above it (a block or a chord wall over the
 flight). Mode 'on': the piece becomes the authored surface plates
 (shell_collision_parts of its triangles, exact standing bevels), as
 Morrowind collides; when that piece holds a staircase and its plates exceed
 STAIR_PLATE_BUDGET, a walkable clip ramp replaces them. Mode 'ramps': a clip
 ramp (the convex hull of the piece's treads and risers, through the
 nosings, as Quake mappers clip stairs) wherever it is walkable, plates
 otherwise. Mode 'off': unchanged. Treads under a proxy that is walkable
 and within a step (a ramp through the nosings) are left alone.
 Slanted risers (STAIRS-SEYDA-LIGHTHOUSE-32): in modes 'on' and 'ramps', a
 collision face steeper than walkable but not vertical whose top edge is a
 tread's front edge is cut back to the vertical plane through that edge
 (vertical_risers), so a box stepping up onto the tread never rests on it.
 Returns (pieces, exact_positions, stats): the positions of the new plates
 (they need exact standing bevels) and one stats row per changed piece.
 Interface used by both builders (legacy and CHIM); keep it stable."""
 from player_hull import WALKABLE_Z, STEP_HEIGHT
 walkable=WALKABLE_Z if walkable is None else walkable
 lift=STEP_HEIGHT if step is None else step
 if mode not in STAIR_MODES:raise ValueError('Unknown stair mitigation mode')
 if mode=='off' or not pieces:return pieces,frozenset(),[]
 treads=stair_treads(v,f,step)
 if not len(treads):return pieces,frozenset(),[]
 tris=v[f[:,:3],:3]*.25
 centres=tris[treads].mean(axis=1)
 out=[];plates=set();stats=[]
 for piece in pieces:
  points,hull,ids,error=piece
  lo=points.min(axis=0)-.5;hi=points.max(axis=0)+.5
  near=np.all((centres[:,:2]>=lo[:2])&(centres[:,:2]<=hi[:2]),axis=1)&(centres[:,2]<=hi[2])
  steep=None;depth=0.
  for c in centres[near]:
   top=_top_face(hull.equations,c)
   if not top or top[0]-c[2]<=.5:continue
   # the column above the tread must lie inside this piece
   if (hull.equations[:,:3]@np.array([c[0],c[1],c[2]+.25])+hull.equations[:,3]).max()>.01:continue
   if top[1]<walkable or top[0]-c[2]>lift+.5:
    if steep is None or top[1]<steep:steep=top[1]
    depth=max(depth,top[0]-c[2])
  if steep is None:out.append(piece);continue
  angle=float(np.degrees(np.arccos(max(-1.,min(1.,steep)))))
  sub=f[np.array(ids,int)]
  shell=shell_collision_parts(v,sub)
  profile=stair_profile(tris,ids,step) if len(ids)>2 else None
  ramp=None
  if profile is not None and (mode=='ramps' or len(shell)>STAIR_PLATE_BUDGET):
   stair=np.concatenate((profile['tread'],profile['riser']))
   p=np.unique(np.round(tris[stair].reshape(-1,3)*16)/16,axis=0)
   if len(p)>=4 and np.linalg.matrix_rank(p-p[0])==3:
    h=ConvexHull(p)
    tops=[_top_face(h.equations,c) for c in profile['centroids']]
    if all(x is not None and x[1]>=walkable for x in tops):
     used=set(stair.tolist());rest=[i for i in ids if i not in used]
     ramp=[(p,h,list(stair),0.)]+(shell_collision_parts(v,f[np.array(rest,int)]) if rest else [])
  if ramp is not None:
   plates.update(range(len(out)+1,len(out)+len(ramp)));out.extend(ramp);action='clip ramp'
  else:
   plates.update(range(len(out),len(out)+len(shell)));out.extend(shell);action='authored plates'
  stats.append(dict(action=action,proxy_angle=angle,buried_depth=round(depth,2),
                    max_riser=profile['max_riser'] if profile else None,triangles=len(ids)))
 out,cut=vertical_risers(out,tris[treads],walkable)
 if cut:
  stats.append(dict(action='vertical risers',proxy_angle=0.,buried_depth=0.,max_riser=None,
                    triangles=int(cut)))
 return out,frozenset(plates),stats

def vertical_risers(pieces,treads,walkable,tolerance=.25,touch=.75):
 """Cut slanted risers back to vertical (STAIRS-SEYDA-LIGHTHOUSE-32).

 A stair step's front face may be authored sloping (a block whose front leans
 back, 70-80 degrees). A standing box stepping up onto the tread above it can
 come down on that slope, which is too steep to stand on, so the step is
 refused, although the original's stepper climbs it. Every collision face
 steeper than walkable (but not within RISER_NZ of vertical) whose top edge
 lies at a tread's level (within tolerance) and touches that tread in plan
 (within touch) is replaced by the vertical plane through its top edge: the
 piece is clipped to the side behind it. Treads stay; the step's riser becomes
 vertical at the tread's front edge, as a mapper's stair would be. Returns
 (pieces, faces cut)."""
 from scipy.spatial import HalfspaceIntersection
 if not len(treads) or not pieces:return pieces,0
 tz=treads[:,:,2].mean(axis=1)
 e0=treads[:,:,:2];e1=np.roll(e0,-1,axis=1)
 out=[];cut=0
 for points,hull,ids,error in pieces:
  eqs=hull.equations;changed=False
  for n in np.unique(np.round(eqs,6),axis=0):     # ConvexHull repeats a plane per facet
   nz=n[2]
   if not (RISER_NZ<=nz<walkable):continue
   face=points[np.abs(points@n[:3]+n[3])<1e-4]
   if len(face)<2:continue
   top=face[:,2].max();edge=face[face[:,2]>top-.05]
   near=np.flatnonzero(np.abs(tz-top)<tolerance)
   if not len(near):continue
   nv=np.array([n[0],n[1],0.]);nv/=np.linalg.norm(nv)
   h=np.array([-nv[1],nv[0]])
   # the top edge in plan (a single corner for a triangle leaning back from one point)
   ta,tb=edge[np.argmin(edge[:,:2]@h)][:2],edge[np.argmax(edge[:,:2]@h)][:2]
   d=_segment_distance(ta,tb,e0[near].reshape(-1,2),e1[near].reshape(-1,2)).reshape(-1,3).min(axis=1)
   if not (d<touch).any():continue
   dv=float((edge@nv).max())
   # the face's whole width along the riser, at the vertical plane
   a,b=face[np.argmin(face[:,:2]@h)][:2],face[np.argmax(face[:,:2]@h)][:2]
   behind=points[points@nv<=dv+1e-6]
   if len(behind)<4 or np.linalg.matrix_rank(behind-behind[0])<3:
    # the whole piece is the slanted riser (an authored plate): a vertical plate at the edge instead
    lo=float(face[:,2].min());a3=np.array([*a,0.]);b3=np.array([*b,0.])
    a3+=nv*(dv-a3@nv);b3+=nv*(dv-b3@nv)
    if np.linalg.norm(b3-a3)<1e-3 or top-lo<1e-3:continue
    newp=np.array([q+nv*o+np.array([0.,0.,z]) for q in (a3,b3) for o in (-.2,.2) for z in (lo,top)])
    points,hull=newp,ConvexHull(newp);eqs=hull.equations;changed=True;cut+=1
    break
   halfspaces=np.vstack((eqs,np.append(nv,-dv)))
   try:
    inner=behind.mean(axis=0)-nv*1e-3
    if (halfspaces[:,:3]@inner+halfspaces[:,3]).max()>=0:continue
    hs=HalfspaceIntersection(halfspaces,inner)
    newp=np.unique(np.round(hs.intersections,6),axis=0)
    if len(newp)<4 or np.linalg.matrix_rank(newp-newp[0])<3:continue
    points,hull=newp,ConvexHull(newp);eqs=hull.equations;changed=True;cut+=1
   except Exception:  # degenerate after clipping: keep the piece as authored
    continue
  out.append((points,hull,ids,error))
 return out,cut

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
