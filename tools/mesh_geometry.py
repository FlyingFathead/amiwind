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

HOLE_AREA=32.  # uncovered square units that make a flat collision piece authored plates (STAIRS-EBONHEART-CHIM-36)

UNDERSIDE_DEPTH=1.  # a convex piece reaching more than this below an authored downward surface of its own closes space
UNDERSIDE_NZ=-.69    # downward-facing: a surface a player can stand under (the walkable normal, mirrored)
UNDERSIDE_ABOVE=.25  # and solid just above it: the surface is the underside of something (not a top wound downward)

def collision_parts(v,f,tolerance=2,plates=None,fill_plates=False,underside=None,underside_split=False):
 """Convex proxies of a collision mesh: each connected component, split at its median while the convex hull
 closes source surface deeper than tolerance. plates: a list to collect the positions of authored plates that
 replace a piece (they need exact standing bevels); with it, a flat component whose hull covers more than
 HOLE_AREA square units its triangles do not (a wall plate around an arch or a door: the hull fills the opening,
 STAIRS-EBONHEART-CHIM-36) becomes the authored plates of its triangles, and with fill_plates (meshes with stairs)
 a piece that still closes more than tolerance when it cannot be split further does too (three triangles over a
 flight whose hull invents a 67-degree face, VIVEC-TEMPLE-STAIRS-33). With underside (a depth, UNDERSIDE_DEPTH: the
 CHIM model builder) a piece whose hull passes through an authored downward-facing surface of the mesh and reaches
 more than that depth below it (the underside of a slab a walkway runs under, whichever piece the slab is in)
 becomes the authored plates of its triangles: the convex proxy closed the space under it (CHIM-VOS-TEMPLE-WALKWAY-41; the general rule that replaces the name list
 of town_regions.UNDERPASS_NAMES); with underside_split such a piece is split further first and only a piece that
 cannot be split becomes plates. Without plates: the convex proxies only."""
 results=[];tris=v[f[:,:3],:3]*.25
 ceilings=_ceiling_samples(tris) if underside and plates is not None else None
 def as_plates(ids):
  for piece in shell_collision_parts(v,f[np.array(ids,int)]):
   plates.append(len(results));results.append(piece)
 def split(ids,depth):
  p=np.unique(np.round(tris[ids].reshape(-1,3)*16)/16,axis=0);offset=p.mean(axis=0)
  if len(p)<3:return
  _,sig,axes=np.linalg.svd(p-offset,full_matrices=False)
  flat=sig[-1]<.15
  if flat:
   normal=axes[-1];p=np.vstack((p-normal*.2,p+normal*.2))
  dirs=np.array([(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]+[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)])
  choice=np.unique(np.argmax(p@dirs.T,axis=0));candidate=p[choice]
  if len(candidate)>=4 and np.linalg.matrix_rank(candidate-candidate[0])==3:p=candidate
  hull=ConvexHull(p)
  if plates is not None and flat:
   t=tris[ids];area=float(np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1).sum())/2
   if hull.volume/.4-area>HOLE_AREA:
    as_plates(ids);return
  # Interior source surface samples reveal concave recesses closed by this hull.
  samples=tris[ids].mean(axis=1)
  inside=-(samples@hull.equations[:,:3].T+hull.equations[:,3]).max(axis=1)
  error=float(inside.max())
  if error>tolerance and len(ids)>4 and depth<8:
   axis=np.argmax(np.ptp(samples,axis=0));order=np.argsort(samples[:,axis]);mid=len(order)//2
   split(np.array(ids)[order[:mid]],depth+1);split(np.array(ids)[order[mid:]],depth+1);return
  if error>tolerance and fill_plates and plates is not None and len(ids)<=4 and _invents_steep_face(hull,tris[ids]):
   as_plates(ids);return
  if ceilings is not None and len(ceilings) and _closes_under_ceiling(hull,ceilings,underside):
   # underside_split: split first, as for any closed space (smaller convex pieces cost less memory than plates:
   # on every exterior mesh plates at once add 15 % standing clipnodes, split first 3.6 %); the authored plates
   # only for a piece that cannot be split further
   if underside_split and len(ids)>4 and depth<8:
    axis=np.argmax(np.ptp(samples,axis=0));order=np.argsort(samples[:,axis]);mid=len(order)//2
    split(np.array(ids)[order[:mid]],depth+1);split(np.array(ids)[order[mid:]],depth+1);return
   as_plates(ids);return
  results.append((p,hull,ids,error))
 for ids in connected_components(v,f):split(ids,0)
 return results

def _ceiling_samples(t):
 """Sample points of every downward-facing triangle of a mesh (normal z at most UNDERSIDE_NZ): its centre and the
 points halfway to each corner."""
 n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);a=np.linalg.norm(n,axis=1);ok=a>1e-9
 nz=np.zeros(len(t));nz[ok]=n[ok,2]/a[ok]
 down=t[ok&(nz<=UNDERSIDE_NZ)]
 if not len(down):return np.zeros((0,3))
 c=down.mean(axis=1)
 return np.concatenate([c]+[(c+down[:,k])/2 for k in range(3)])

def _closes_under_ceiling(hull,samples,depth=UNDERSIDE_DEPTH):
 """True when the convex hull passes through an authored downward-facing surface (SAMPLES, _ceiling_samples of the
 whole mesh): a sample point UNDERSIDE_ABOVE up (inside the solid the surface is the underside of) and DEPTH down
 (the space under it) both lie inside the hull. The piece then fills more than DEPTH of the space the visible mesh
 leaves open under that surface (CHIM-VOS-TEMPLE-WALKWAY-41). A piece that only touches a ceiling from below (a
 column under a slab) or a top face wound the wrong way (open air above it) is not caught."""
 lo,hi=hull.min_bound,hull.max_bound
 near=samples[(samples[:,0]>lo[0])&(samples[:,0]<hi[0])&(samples[:,1]>lo[1])&(samples[:,1]<hi[1])
              &(samples[:,2]-depth>lo[2])&(samples[:,2]+UNDERSIDE_ABOVE<hi[2])]
 if not len(near):return False
 def inside(q):
  return ((q@hull.equations[:,:3].T+hull.equations[:,3])<-1e-6).all(axis=1)
 return bool((inside(near-np.array([0.,0.,depth]))&inside(near+np.array([0.,0.,UNDERSIDE_ABOVE]))).any())

def _invents_steep_face(hull,t):
 """True when the hull has an upward face too steep to stand on (but not a wall) that no source triangle lies
 in: a slope the convex proxy made up, where a standing box stepping up comes down (the palace steps' 67-degree
 faces). Authored slopes the hull only repeats are left to the convex proxy."""
 from player_hull import WALKABLE_Z
 n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);a=np.linalg.norm(n,axis=1);ok=a>1e-9
 n=n[ok]/a[ok][:,None];c=t[ok].mean(axis=1)
 for e in np.unique(np.round(hull.equations,6),axis=0):
  if not (RISER_NZ<=e[2]<WALKABLE_Z):continue
  if not np.any((np.abs(n@e[:3])>.999)&(np.abs(c@e[:3]+e[3])<.3)):return True
 return False

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

def collision_pieces(v,f,profile,stairs=None,visible=None):
 """Collision proxies of one mesh under its profile: (pieces, exact_bevels, note).

 One implementation for the converter and the size estimates. The convex
 approximation (collision_parts) may close authored space. A profile with
 surface_collision_beyond (exterior architecture of converted towns,
 town_regions.visual_profile) keeps each authored collision surface instead
 when the deepest closed space exceeds that height, the engine's step height:
 the player cannot step over such invented solid and residents standing in it
 are buried (VIVEC-ARENA-ACTORS-32).

 visible: (v, f) of the mesh as drawn (its collision mesh may be a separate RootCollisionNode); with the stair-plate
 rules and a profile with visible_treads (the CHIM model builder), collision that stands more than a step over a
 visible stair tread (or walkway, for architecture) with standing room is changed (clear_visible_treads,
 CHIM-STAIR-STEPS-SOLID-43).
 """
 if not profile.get('stair_plates'):
  # the stair-plate rules (plate_toes, plates for open flat pieces, fill plates) are opted into by the converters
  # whose walkers need them: CHIM models (chim.build) and rooms (prepare_interior); legacy open-world maps keep
  # the classic proxies and their clip-node budget (BUILD-FLORA-STAIR-PLATES-BUDGET-36)
  return collision_pieces_classic(v,f,profile,stairs)
 pieces,exact,note=_collision_pieces_stairs(v,f,profile,stairs)
 mode=stair_mitigation_mode() if stairs is None else stairs
 if visible is None or not profile.get('visible_treads') or mode=='off' or not pieces or profile.get('collision_none'):
  return pieces,exact,note
 # the visible flights of every mesh; a family with visible_walkways (town_regions.visual_profile: the walkways the
 # Hlaalu flights lead onto) also its walkable faces, for slopes its convex proxy invented over them
 pieces,exact,stats=clear_visible_treads(v,f,pieces,exact,visible[0],visible[1],
                                         walkways=bool(profile.get('visible_walkways')))
 if stats:
  # exact standing bevels for the whole mesh: its new plates need them, and the CHIM model variants take the
  # mesh-wide flag only (chim.build: collision_bevels), not the positions
  exact=True
  extra=('visible treads: %d collision pieces stood over the flight (%d split, %d made authored plates, %d ramp '
         'plates and %d pieces at the flight replaced by %d visible plates, %d kept)'
         %(stats['pieces'],stats['split'],stats['authored'],stats['replaced'],stats.get('flight_sides',0),
           stats['visible_plates'],stats['kept']))
  note=extra if not note else note+'; '+extra
 return pieces,exact,note

def _collision_pieces_stairs(v,f,profile,stairs=None):
 """collision_pieces with the stair-plate rules, before the visible-tread rule."""
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
  shell,toes=plate_toes(v,f,shell_collision_parts(v,f),mode)
  cut=f'{toes} steep toes cut to vertical steps' if toes else None
  if exact or mode=='off' or not len(stair_treads(v,f)):
   if toes and not exact:
    return shell,frozenset(_plate_positions(shell)),'stairs: '+cut
   return shell,exact,('stairs: '+cut) if cut else None
  return shell,True,'stairs: exact bevels on the authored plates of a mesh with stairs'+('; '+cut if cut else '')
 whole=profile.get('underside_whole')
 if whole:
  # the underside rule for the whole mesh (AMIWIND_COLLISION_UNDERSIDE whole): when any plain convex piece passes
  # through an authored downward-facing surface and fills more than WHOLE units under it, the mesh keeps all its
  # authored collision surfaces with exact bevels, as the name list did for the Velothi temples
  samples=_ceiling_samples(v[f[:,:3],:3]*.25)
  if len(samples) and any(_closes_under_ceiling(hull,samples,whole) for _,hull,_,_ in
                          collision_parts(v,f,profile.get('collision_tolerance',2))):
   shell,toes=plate_toes(v,f,shell_collision_parts(v,f),mode)
   return shell,True,('authored collision surfaces: a convex piece fills more than %g units under an authored '
                      'ceiling' % whole)+(f'; {toes} steep toes cut to vertical steps' if toes else '')
 limit=profile.get('surface_collision_beyond')
 if limit is not None:
  # measured on the plain convex proxies: the plates below would hide the deep fill this test is for (the Vivec
  # palace stairs, ex_vivec_ps_01, close 9.05 units and keep all their authored surfaces)
  fill=max((error for _,_,_,error in collision_parts(v,f,profile.get('collision_tolerance',2))),default=0.)
  if fill>limit:
   shell,toes=plate_toes(v,f,shell_collision_parts(v,f),mode)
   return shell,True,('authored collision surfaces: convex approximation closes '
                      f'{fill:.2f} units > {limit} step height'+(f'; {toes} steep toes cut to vertical steps' if toes else ''))
 plates=[]
 # the fill test of the stair rule only on meshes with stairs (mode on): every other mesh keeps its convex proxies
 treads=mode!='off' and bool(len(stair_treads(v,f)))
 pieces=collision_parts(v,f,profile.get('collision_tolerance',2),plates=plates,fill_plates=treads,
                        underside=profile.get('underside_plates'),underside_split=bool(profile.get('underside_split')))
 own=[pieces[k] for k in plates]
 notes=[f'authored plates where the convex proxy filled open space ({len(own)} plates)'] if own else []
 stair_plates=frozenset()
 if mode!='off':
  pieces,stair_plates,stats=mitigate_stairs(v,f,pieces,mode)
  if stats:
   notes.insert(0,'stairs: '+'; '.join(f"{s['action']} (proxy {s['proxy_angle']:.1f} deg, {s['buried_depth']:.1f} over a tread)" for s in stats))
 if exact:
  return pieces,True,'; '.join(notes) or None
 # by the ids list each plate carries: the stair rule rebuilds every piece's tuple (vertical_risers), not its ids
 marked=frozenset(stair_plates)|frozenset(k for k,piece in enumerate(pieces) if any(piece[2] is q[2] for q in own))
 return pieces,(marked or False),'; '.join(notes) or None

def _plate_positions(pieces):
 """Positions of the plates plate_toes made (marked by their ids being the TOE marker)."""
 return [k for k,piece in enumerate(pieces) if getattr(piece[2],'toe',False)]

class _Toe(list):
 """ids of a toe plate cut to vertical (plate_toes): a list that says so, for the exact-bevel positions."""
 toe=True

def plate_toes(v,f,pieces,mode='on',tolerance=.25,touch=.75):
 """Steep toes of authored ramps cut to vertical steps (STAIRS-VIVEC-ROOMS-JOINT-36). An authored plate (a
 thin piece of shell_collision_parts) steeper than walkable but not vertical, at most a step tall, whose top
 edge lies on a walkable authored surface (a ramp or a tread: within tolerance of its plane and inside it or
 within touch of it in plan) is the lip at the foot of that surface: the Velothi stair pieces end each ramp with
 a 50-degree lip 2.9 units tall, and a standing box stepping up onto the joint of two pieces came down on it.
 Such a plate is replaced by a vertical plate through its top edge (as vertical_risers' plate branch), so the
 box steps over it as over any riser. Returns (pieces, plates cut). Mode 'off': unchanged."""
 from player_hull import WALKABLE_Z, STEP_HEIGHT
 if mode=='off' or not pieces:return pieces,0
 tris=v[f[:,:3],:3]*.25
 n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);a=np.linalg.norm(n,axis=1)
 ok=a>1e-6;nz=np.zeros(len(f));nz[ok]=n[ok,2]/a[ok]
 walk=np.flatnonzero(ok&(nz>=WALKABLE_Z))
 if not len(walk):return pieces,0
 wt=tris[walk];wn=n[walk]/a[walk][:,None]
 def on_walkable(p):
  d=np.abs(((p-wt[:,0])*wn).sum(axis=1))
  for k in np.flatnonzero(d<tolerance):
   t=wt[k][:,:2]
   if _segment_distance(p[:2],p[:2],t,np.roll(t,-1,axis=0)).min()<touch:return True
   c=[(t[(i+1)%3][0]-t[i][0])*(p[1]-t[i][1])-(t[(i+1)%3][1]-t[i][1])*(p[0]-t[i][0]) for i in range(3)]
   if min(c)>=0 or max(c)<=0:return True
  return False
 out=[];cut=0
 for points,hull,ids,error in pieces:
  eqs=hull.equations;new=None
  planes=np.unique(np.round(eqs,6),axis=0)
  for e in planes:
   if not (RISER_NZ<=e[2]<WALKABLE_Z):continue
   if np.ptp(points@e[:3])>.5:continue          # a thin plate along this face only
   face=points[np.abs(points@e[:3]+e[3])<1e-4]
   if len(face)<3:continue
   top=face[:,2].max();lo=face[:,2].min()
   if top-lo>STEP_HEIGHT+1e-3 or top-lo<.5:continue
   edge=face[face[:,2]>top-.05]
   if not on_walkable(edge.mean(axis=0)):continue
   nv=np.array([e[0],e[1],0.]);nv/=np.linalg.norm(nv);h=np.array([-nv[1],nv[0]])
   a2,b2=face[np.argmin(face[:,:2]@h)][:2],face[np.argmax(face[:,:2]@h)][:2]
   dv=float((edge@nv).max())
   a3=np.array([*a2,0.]);b3=np.array([*b2,0.]);a3+=nv*(dv-a3@nv);b3+=nv*(dv-b3@nv)
   if np.linalg.norm(b3-a3)<1e-3:continue
   newp=np.array([q+nv*o+np.array([0.,0.,z]) for q in (a3,b3) for o in (-.2,.2) for z in (lo,top)])
   new=(newp,ConvexHull(newp),_Toe(ids),error);break
  if new is None:out.append((points,hull,ids,error))
  else:out.append(new);cut+=1
 return out,cut

def collision_pieces_classic(v,f,profile,stairs=None):
 """The collision proxies before the stair-plate rules (collision_pieces without the profile's stair_plates:
 every legacy open-world map, whose clip-node budget they would raise: vf0779 went from 32,614 to
 33,172 aggregate clipnodes, over 32,767, BUILD-FLORA-STAIR-PLATES-BUDGET-36). Unchanged method.

 (pieces, exact_bevels, note).

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
 pieces=collision_parts(v,f,profile.get('collision_tolerance',2))
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

def stair_treads(v,f,step=None,pairs=None):
 """Indices of the stair treads of a mesh: level upward triangles (at least
 2 square units) that a riser joins to another level triangle: the riser is
 a group of near-vertical triangles at least 4 units wide, touching (within
 0.75 in plan) a level triangle at its top and another 1..step lower. Rock ledges, leaves and trinkets without such steps have none.
 pairs: a list to collect (riser width, upper tread triangles, lower tread triangles) per riser (flight_treads)."""
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
  if len(low):
   out.update(level[np.concatenate((top,low))].tolist())
   if pairs is not None:pairs.append((float(proj.max()-proj.min()),level[top].tolist(),level[low].tolist()))
 return np.array(sorted(out),int)

FLIGHT_WIDTH=16.  # a riser the standing box (14.6 wide) can climb (the stair gate's MIN_OVERLAP)
FLIGHT_LEVELS=3   # tread levels joined by risers that make a flight (the stair gate: 3+ steps in a row)

def flight_treads(v,f,step=None):
 """The stair treads of a mesh that belong to a flight: treads joined by risers at least FLIGHT_WIDTH wide
 (stair_treads), level triangles of one tread joined where they share a corner, and at least FLIGHT_LEVELS tread
 levels more than a unit apart in one such staircase. Decorative ledges (a carved door, a bed's frame) are not flights."""
 pairs=[]
 treads=stair_treads(v,f,step,pairs=pairs)
 if not len(treads):return treads
 tris=v[f[:,:3],:3]*.25
 parent={int(t):int(t) for t in treads}
 def root(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 used=set()
 for width,top,low in pairs:
  if width<FLIGHT_WIDTH:continue
  ids=[int(t) for t in top+low];used.update(ids)
  for t in ids[1:]:parent[root(t)]=root(ids[0])
 if not used:return np.array([],int)
 # one tread's triangles: level, sharing a corner
 ids=sorted(used);z=tris[ids][:,:,2].mean(axis=1);corner={}
 for t,h in zip(ids,z):
  for k in np.round(tris[t]*16).astype(np.int64).tolist():
   other=corner.setdefault(tuple(k),[])
   for o,oh in other:
    if abs(oh-h)<.25:parent[root(t)]=root(o)
   other.append((t,h))
 levels={}
 for t,h in zip(ids,z):levels.setdefault(root(t),[]).append(h)
 def count(hs):
  hs=sorted(hs);n=1
  last=hs[0]
  for b in hs[1:]:
   if b-last>1.:n+=1;last=b        # risers under a unit are trim, not steps (the stair gate's RISE_MIN)
  return n
 keep=[t for t in ids if count(levels[root(t)])>=FLIGHT_LEVELS]
 return np.array(sorted(keep),int)

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

# The visible-tread rule (CHIM-STAIR-STEPS-SOLID-43). Morrowind collides with the authored collision mesh (a
# RootCollisionNode) where a mesh has one; that mesh may run a ramp over a staircase well above its visible nosings
# (ex_redoran_steps_02: a 45-degree ramp 7 to 14 units over the treads, one plate of four triangles), and a convex
# proxy of a curved authored deck closes the space over it (ex_ropebridge_2048_01: one piece of 260 triangles, solid
# 22.8 units over the sagging deck). The player then cannot stand on the visible steps the stair gate and the eye
# see. The rule: over every visible stair tread with standing room, sampled across its area, a collision piece in the
# open column more than VISIBLE_TREAD_MARGIN over the tread must be within a step of it and walkable on top (the
# stair rule's own test, mitigate_stairs, which only reads tread centres of the collision mesh): a ramp through the
# nosings, Quake's clip ramp, or an authored deck a little over the visible planks stays as it is. A piece over that
# is split while
# it has more than four authored triangles (as collision_parts splits), then made the authored plates of its
# triangles; a plate that still stands there, is not a wall and lies over the flight (the authored surface itself is
# a ramp over the steps) is replaced by the visible flight under it as plates, and then every other authored piece
# that lies mostly in the flight (the standing box's width around its treads) by the visible faces where it stood (the
# flight's cheeks and rails); a wall, a roof or a floor elsewhere stays. A family with visible_walkways also has its
# walkable faces checked, for a slope its convex proxy invented more than a step over them (the walkway a flight leads
# onto).
# Visible geometry is never changed.
VISIBLE_TREAD_MARGIN=.5
VISIBLE_TREAD_INSET=.1   # samples keep this barycentric distance from a tread triangle's edges (risers stand .2 off)
VISIBLE_TREAD_GRID=7     # samples per tread triangle edge
VISIBLE_RAMP_COVER=.75   # an authored ramp plate with this share of its plan area at the flight under it ran over the flight

def _proxy_piece(tris,ids):
 """The convex proxy of triangles ids (their hull, a flat set thickened 0.2 each side), as collision_parts builds
 it: (points, hull, ids, error) or None."""
 p=np.unique(np.round(tris[ids].reshape(-1,3)*16)/16,axis=0)
 if len(p)<3:return None
 offset=p.mean(axis=0);_,sig,axes=np.linalg.svd(p-offset,full_matrices=False)
 if sig[-1]<.15:
  normal=axes[-1];p=np.vstack((p-normal*.2,p+normal*.2))
 if len(p)<4 or np.linalg.matrix_rank(p-p[0])<3:return None
 hull=ConvexHull(p)
 samples=tris[ids].mean(axis=1)
 error=float((-(samples@hull.equations[:,:3].T+hull.equations[:,3]).max(axis=1)).max())
 return (p,hull,list(ids),error)

def walkway_faces(v,f):
 """Visible walkable faces of at least 2 square units (normal z at least WALKABLE_Z)."""
 from player_hull import WALKABLE_Z
 tris=v[f[:,:3],:3]*.25
 n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);a=np.linalg.norm(n,axis=1)
 nz=np.zeros(len(f));ok=a>1e-6;nz[ok]=n[ok,2]/a[ok]
 return np.flatnonzero(ok&(nz>=WALKABLE_Z)&(a/2>=2.))

def visible_tread_samples(v,f,step=None,faces=None):
 """Sample points over visible faces of a mesh (FACES; by default its flight treads, flight_treads) and, per point,
 the lowest height collision may start over it (a step over the face) and the top of its open column (the standing
 height: points with a visible surface over them lower than that are left out): (points, floor, top), or None when
 there are no such points."""
 from player_hull import STEP_HEIGHT, MINS, MAXS
 step=STEP_HEIGHT if step is None else step
 tris=v[f[:,:3],:3]*.25
 faces=flight_treads(v,f,step) if faces is None else faces
 if not len(faces):return None
 g=np.linspace(VISIBLE_TREAD_INSET,1-2*VISIBLE_TREAD_INSET,VISIBLE_TREAD_GRID)
 bary=np.array([(a,b) for a in g for b in g if a+b<=1-VISIBLE_TREAD_INSET+1e-9])
 T=tris[faces]
 pts=(T[:,None,0]+bary[None,:,0,None]*(T[:,None,1]-T[:,None,0])+bary[None,:,1,None]*(T[:,None,2]-T[:,None,0])).reshape(-1,3)
 z=pts[:,2]
 # collision within a step over the tread can be stepped onto (a ramp through the nosings, an authored deck a little
 # over the visible planks); higher it closes the tread
 floor=z+step
 # the open column: up to the next visible surface over the point
 height=MAXS[2]-MINS[2];top=z+height
 a,b,c=tris[:,0],tris[:,1],tris[:,2]
 m00=b[:,0]-a[:,0];m01=c[:,0]-a[:,0];m10=b[:,1]-a[:,1];m11=c[:,1]-a[:,1];det=m00*m11-m01*m10
 good=np.abs(det)>1e-9;lo=tris.min(axis=1);hi=tris.max(axis=1)
 for k,p in enumerate(pts):
  near=good&(lo[:,0]<=p[0])&(hi[:,0]>=p[0])&(lo[:,1]<=p[1])&(hi[:,1]>=p[1])&(hi[:,2]>p[2]+.3)
  if not near.any():continue
  i=np.flatnonzero(near);d=det[i]
  u=((p[0]-a[i,0])*m11[i]-(p[1]-a[i,1])*m01[i])/d;w=((p[1]-a[i,1])*m00[i]-(p[0]-a[i,0])*m10[i])/d
  ok=(u>=-1e-6)&(w>=-1e-6)&(u+w<=1+1e-6)
  if not ok.any():continue
  hz=(a[i,2]+u*(b[i,2]-a[i,2])+w*(c[i,2]-a[i,2]))[ok]
  hz=hz[hz>p[2]+.3]
  if len(hz):top[k]=min(top[k],float(hz.min()))
 # only where the visible mesh leaves the player's whole height free over the tread: space under a table top, a
 # bed or a landing keeps the collision its authors gave it
 keep=top>=z+height-1e-6
 if not keep.any():return None
 return pts[keep],floor[keep],top[keep]

def _stands_over(piece,samples,steep=True):
 """True when the piece is solid in the open column over a visible tread sample above the tread (more than
 VISIBLE_TREAD_MARGIN) and either higher than a step there or (steep) under a top face too steep to stand on: the
 stair rule's own test (mitigate_stairs), over the visible faces and their whole area."""
 from player_hull import WALKABLE_Z
 pts,floor,top=samples[:3]
 points,hull=piece[0],piece[1]
 lo=points.min(axis=0);hi=points.max(axis=0)
 sel=(pts[:,0]>=lo[0]-1e-3)&(pts[:,0]<=hi[0]+1e-3)&(pts[:,1]>=lo[1]-1e-3)&(pts[:,1]<=hi[1]+1e-3)&(top>lo[2])&(pts[:,2]+VISIBLE_TREAD_MARGIN<hi[2])
 if not sel.any():return False
 p=pts[sel];eq=hull.equations
 r=-(p[:,:2]@eq[:,:2].T+eq[:,3])            # c*z <= r per plane
 c=eq[:,2]
 with np.errstate(divide='ignore',invalid='ignore'):
  ups=np.where(c[None,:]>1e-9,r/c[None,:],np.inf)
  down=np.where(c[None,:]<-1e-9,r/c[None,:],-np.inf).max(axis=1)
 k=np.argmin(ups,axis=1);up=ups[np.arange(len(p)),k];upn=c[k]
 flat=np.where(np.abs(c)[None,:]<=1e-9,r,np.inf).min(axis=1)>=-1e-6
 s0=np.maximum(down,p[:,2]+VISIBLE_TREAD_MARGIN);s1=np.minimum(up,top[sel]-VISIBLE_TREAD_MARGIN)
 solid=flat&(s1-s0>.05)
 return bool((solid&((s1>floor[sel]+.05)|((upn<WALKABLE_Z) if steep else False))).any())

def _ramp_plate(piece):
 """A thin piece (an authored plate) that is not a wall: its plane leans more than RISER_NZ from vertical (a floor,
 a ramp, a slope over a flight)."""
 p=piece[0]
 if len(p)<3:return False
 _,sig,axes=np.linalg.svd(p-p.mean(axis=0),full_matrices=False)
 return bool(sig[-1]<.5*max(sig[0],1e-9) and np.ptp(p@axes[-1])<=.5 and abs(axes[-1][2])>=RISER_NZ)

def clear_visible_treads(v,f,pieces,exact,vis_v,vis_f,step=None,walkways=False):
 """The visible-tread rule (see VISIBLE_TREAD_MARGIN): v, f the collision mesh, pieces its proxies, exact their
 bevel marker (True, False or the positions that need exact bevels); vis_v, vis_f the mesh as drawn. Returns
 (pieces, exact, stats); stats is None when nothing changed. Every new plate is marked for exact bevels."""
 flight=flight_treads(vis_v,vis_f,step)
 samples=visible_tread_samples(vis_v,vis_f,step,flight) if len(flight) else None
 walk=None
 if walkways:
  faces=np.setdiff1d(walkway_faces(vis_v,vis_f),flight)
  walk=visible_tread_samples(vis_v,vis_f,step,faces) if len(faces) else None
 if samples is None and walk is None:return pieces,exact,None
 tris=v[f[:,:3],:3]*.25;vtris=vis_v[vis_f[:,:3],:3]*.25
 def over(piece):
  if samples is not None and _stands_over(piece,samples):return True
  # a walkway: only a slope the convex proxy invented (no authored triangle in it) more than a step over it
  ids=list(piece[2]) if piece[2] is not None else []
  return bool(walk is not None and len(ids)>2 and _stands_over(piece,walk,steep=False) and
              _invents_steep_face(piece[1],tris[np.array(ids,int)]))
 flagged=[k for k,piece in enumerate(pieces) if over(piece)]
 if not flagged:return pieces,exact,None
 stats=dict(pieces=len(flagged),split=0,authored=0,replaced=0,kept=0,visible_plates=0)
 out=[];marks=[];hidden=set();covered=set()
 ft=vtris[flight]
 def under(plate):
  """The visible faces an authored ramp plate ran over, when the plate lies at the flight (VISIBLE_RAMP_COVER of
  its plan area within the standing box's width of the flight treads under it; a deck or a floor that only reaches
  over a flight stays): the faces in its plan outline (grown .5) under its surface, from a standing
  height under the lowest flight tread there (the first riser) up to the highest (treads, risers, the stringers'
  inner faces); True when replaced."""
  from scipy.spatial import Delaunay
  pts=plate[0];xy=pts[:,:2]
  try:
   outline=Delaunay(np.vstack((xy,xy+np.sign(xy-xy.mean(axis=0))*.5)))
  except Exception:
   return False
  from player_hull import MINS, MAXS
  if np.linalg.matrix_rank(xy-xy[0])<2:return False
  inside=outline.find_simplex(ft.mean(axis=1)[:,:2])>=0
  if not inside.any():return False
  # the flight under the plate: its treads' outline grown by the standing box; the plate must lie there
  fxy=ft[inside][:,:,:2].reshape(-1,2)
  try:
   ring=fxy[ConvexHull(fxy).vertices];m=ring-ring.mean(axis=0)
   region=Delaunay(ring+m/np.maximum(np.linalg.norm(m,axis=1,keepdims=True),1e-9)*(max(MAXS[0],MAXS[1])+VISIBLE_TREAD_MARGIN))
  except Exception:
   return False
  lo2,hi2=xy.min(axis=0),xy.max(axis=0)
  grid=np.stack(np.meshgrid(np.linspace(lo2[0],hi2[0],24),np.linspace(lo2[1],hi2[1],24)),axis=-1).reshape(-1,2)
  grid=grid[Delaunay(xy[ConvexHull(xy).vertices]).find_simplex(grid)>=0]
  if not len(grid) or (region.find_simplex(grid)>=0).mean()<VISIBLE_RAMP_COVER:return False
  lo=ft[inside][:,:,2].min()-(MAXS[2]-MINS[2]);hi=ft[inside][:,:,2].max()+.5
  # the plate's plane: faces under it only
  _,_,axes=np.linalg.svd(pts-pts.mean(axis=0),full_matrices=False);n=axes[-1]*np.sign(axes[-1][2]);d=float(n@pts.mean(axis=0))
  c=vtris.mean(axis=1)
  sel=(outline.find_simplex(c[:,:2])>=0)&(c[:,2]>=lo)&(c[:,2]<=hi)&((d-c[:,:2]@n[:2])/n[2]+.5>=c[:,2])
  hidden.update(int(i) for i in np.flatnonzero(sel))
  covered.update(int(i) for i in np.flatnonzero(inside))
  return True
 def settle(piece,depth,ex):
  ids=list(piece[2]) if piece[2] is not None else []
  if not over(piece):
   out.append(piece);marks.append(ex);return
  if len(ids)>4 and depth<8:
   stats['split']+=1
   centres=tris[ids].mean(axis=1);axis=int(np.argmax(np.ptp(centres,axis=0)));order=np.argsort(centres[:,axis],kind='stable')
   mid=len(order)//2
   for half in (np.array(ids)[order[:mid]],np.array(ids)[order[mid:]]):
    q=_proxy_piece(tris,half)
    if q is None:
     for plate in shell_collision_parts(v,f[half]):settle(plate,8,True)
    else:settle(q,depth+1,ex)
   return
  if ids:
   stats['authored']+=1
   for plate in shell_collision_parts(v,f[np.array(ids,int)]):
    if over(plate):last(plate,True)
    else:
     out.append(plate);marks.append(True)
   return
  last(piece,ex)
 def last(plate,ex):
  # an authored surface over the flight that is not a wall and lies over the flight is a ramp the authors ran over
  # the steps (the visible flight under it takes its place); a wall, a roof or a floor elsewhere stays
  if _ramp_plate(plate) and under(plate):
   stats['replaced']+=1
  else:
   stats['kept']+=1;out.append(plate);marks.append(ex)
 for k,piece in enumerate(pieces):
  ex=exact is True or (bool(exact) and exact is not True and k in exact)
  if k in flagged:
   settle(piece,0,ex)
  else:
   out.append(piece);marks.append(ex)
 if stats['replaced'] and covered:
  # the flight's collision now comes from the visible flight (the treads the replaced ramps ran over): every other
  # authored piece that lies mostly in the flight (its plan outline grown by the standing box, between a standing
  # height under its lowest tread and over its highest) goes too, and the visible faces there take its place: the
  # sides of the flight are its visible cheeks and rails, not authored walls inset into the visible treads
  from scipy.spatial import Delaunay
  from player_hull import MINS, MAXS
  height=MAXS[2]-MINS[2];grow=max(MAXS[0],MAXS[1])+VISIBLE_TREAD_MARGIN
  cov=ft[np.array(sorted(covered),int)]       # the treads the replaced ramps ran over
  fxy=cov[:,:,:2].reshape(-1,2)
  zlo=cov[:,:,2].min()-height;zhi=cov[:,:,2].max()+height
  try:
   hull=ConvexHull(fxy);ring=fxy[hull.vertices];centre=ring.mean(axis=0)
   d=ring-centre;ring=ring+d/np.maximum(np.linalg.norm(d,axis=1,keepdims=True),1e-9)*grow
   region=Delaunay(ring)
  except Exception:
   region=None
  if region is not None:
   c=vtris.mean(axis=1)
   keep_out,keep_marks=[],[]
   for piece,mark in zip(out,marks):
    pts=piece[0]
    if pts[:,2].max()>=zlo and pts[:,2].min()<=zhi and (region.find_simplex(pts[:,:2])>=0).mean()>=.5:
     # a piece mostly at the flight (a hull, a deck elsewhere stays)
     stats['flight_sides']=stats.get('flight_sides',0)+1
     lo=pts.min(axis=0)-.5;hi=pts.max(axis=0)+.5
     sel=(np.all((c[:,:2]>=lo[:2])&(c[:,:2]<=hi[:2]),axis=1)&(c[:,2]>=max(lo[2],zlo))&(c[:,2]<=min(hi[2],zhi))
          &(region.find_simplex(c[:,:2])>=0))
     hidden.update(int(i) for i in np.flatnonzero(sel))
    else:
     keep_out.append(piece);keep_marks.append(mark)
   out,marks=keep_out,keep_marks
 if hidden:
  plates=shell_collision_parts(vis_v,vis_f[np.array(sorted(hidden),int)])
  stats['visible_plates']=len(plates)
  out.extend(plates);marks.extend([True]*len(plates))
 if exact is True:return out,True,stats
 return out,frozenset(k for k,m in enumerate(marks) if m),stats

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
