# SPDX-License-Identifier: GPL-3.0-only
"""Convex surface merging, bounded UV patches and separate collision proxies.

Visible polygons preserve recesses. Collision is an approximation and must be
measured separately; its 14-direction support samples can miss small details.
"""
import collections
import numpy as np
from scipy.spatial import ConvexHull

def surface_polygons(v,f):
 groups=collections.defaultdict(list)
 for face in f:
  p=v[face[:3],:3]*.25; uv=v[face[:3],3:5]; n=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(n)
  if area<.05:continue
  n/=area
  # Texture affine derivatives on the surface, with zero normal component.
  A=np.vstack((p[1]-p[0],p[2]-p[0],n));b=np.vstack((uv[1]-uv[0],uv[2]-uv[0],[0,0]));axes=np.linalg.solve(A,b);off=uv[0]-p[0]@axes
  key=(int(face[3]),*np.round(n,4),round(float(n@p[0]),2),*np.round(axes.flatten(),5),*np.round(off,3))
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
  lo=np.floor(uv[:,a].min()/16)*16;hi=np.ceil(uv[:,a].max()/16)*16
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

def shell_collision_parts(v,f,thickness=.2):
 """Thin convex prisms preserve a hollow authored interior collision shell.

 Enclosing an entire connected room with one convex volume fills its free space.
 Merge only actual planar surfaces, then give each a small two-sided thickness.
 """
 out=[]
 for poly,material,axes,offset,normal in surface_polygons(v,f):
  points=np.vstack((poly-normal*thickness,poly+normal*thickness))
  out.append((points,ConvexHull(points),[],0.))
 return out
