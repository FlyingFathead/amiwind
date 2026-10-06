# SPDX-License-Identifier: GPL-3.0-only
"""Preserve authored first-person topology in a bounded repeated-texture atlas."""
import numpy as np
from PIL import Image


def audit_source_topology(shapes, frames, faces):
    """Compare full animated surfaces, independent of texture vertex copies.

    Weld only vertices whose complete sampled trajectories are identical.
    Authored open ends are counted, never capped. An added/deleted face, changed
    winding or separated seam fails even when its rest pose still looks right.
    """
    from collections import Counter
    vertex_ids={}
    def ids(points):
        points=np.asarray(points,dtype=np.float64)
        if points.ndim!=3 or points.shape[0]!=len(frames) or points.shape[2]!=3:
            raise ValueError('Topology oracle frame contract mismatch')
        if not np.isfinite(points).all():raise ValueError('Nonfinite topology oracle input')
        points=points.copy();points[points==0]=0 # normalize negative zero
        return [vertex_ids.setdefault(points[:,i].tobytes(),len(vertex_ids)) for i in range(points.shape[1])]
    def triangles(vertices, triangles):
        result=[]
        for a,b,c in triangles:
            t=(vertices[int(a)],vertices[int(b)],vertices[int(c)])
            result.append(min(t,t[1:]+t[:1],t[2:]+t[:2]))
        return result
    source=[];material_boundary=0
    def edges(tris):
        return Counter(tuple(sorted((a,b))) for a,b,c in tris for a,b in ((a,b),(b,c),(c,a)))
    for shape in shapes:
        source.extend(triangles(ids(shape['positions']),np.asarray(shape['faces'])[:,[0,2,1]]))
        material_boundary+=sum(n==1 for n in edges(shape['faces']).values())
    actual=triangles(ids(frames),faces)
    if Counter(source)!=Counter(actual):
        raise ValueError('Source surface changed: missing/reversed faces or opened animation seam')
    boundaries=sum(n==1 for n in edges(source).values())
    return dict(source_triangles=len(source),output_triangles=len(actual),
                sampled_frames=len(frames),authored_open_boundary_edges=boundaries,
                shape_boundary_edges=material_boundary,new_boundary_edges=0,
                geometry='identical complete sampled trajectories and oriented surfaces')


def _bake_vertex_tints(shapes, materials, textures):
    """Bake varying RGB into small face tiles without moving any geometry.

    MDL has no vertex colour channel. Only gradient-tinted source faces need
    UV-local copies; copied edge endpoints keep identical complete trajectories
    and are quantized together, so texture seams cannot become geometric gaps.
    """
    result=[];materials=list(materials);textures=dict(textures)
    for shape_index,shape in enumerate(shapes):
        colours=np.asarray(shape['colours'])
        count=np.asarray(shape['positions']).shape[1]
        if colours.shape!=(count,4) or not np.isfinite(colours).all() or np.any(colours<0) or np.any(colours>1):
            raise ValueError('Invalid hand vertex colour')
        if not np.allclose(colours[:,3],1,rtol=0,atol=1e-6):
            raise ValueError('Translucent hand faces need a separate renderer')
        if np.allclose(colours,colours[:1],rtol=0,atol=1e-6):
            result.append(shape);continue
        material=materials[shape['material']];texture=textures.get(material['texture_index'])
        yy,xx=np.mgrid[0:16,0:16]
        weights=np.column_stack((np.maximum(0,1-(xx.ravel()+yy.ravel())/15),xx.ravel()/15,yy.ravel()/15))
        weights/=weights.sum(1)[:,None]
        for face_index,face in enumerate(shape['faces']):
            uv=weights@shape['uv'][face]
            if texture is None:pixels=np.full((256,3),220.)
            else:
                x=np.floor(uv[:,0]*texture.shape[1]).astype(int)%texture.shape[1]
                y=np.floor(uv[:,1]*texture.shape[0]).astype(int)%texture.shape[0]
                pixels=texture[y,x,:3].astype(float)
            pixels*=weights@colours[face,:3]*np.asarray(material['diffuse'])
            key=('hand-vertex-tint',shape_index,face_index)
            textures[key]=np.clip(pixels,0,255).astype(np.uint8).reshape(16,16,3)
            material_index=len(materials)
            materials.append(dict(material,texture_index=key,diffuse=[1,1,1]))
            result.append(dict(shape,positions=shape['positions'][:,face,:].copy(),
                               faces=np.array([[0,1,2]]),uv=np.array([[0,0],[15/16,0],[0,15/16]]),
                               colours=np.ones((3,4)),material=material_index))
    return result,materials,textures


def bake_source_hands(shapes,materials,textures,palette,texture_size=128):
    """No simplification or animation transfer; retain shared source vertices.

    UV bounds may extend beyond a source texture. Bake that repeated rectangle
    into the atlas instead of wrapping individual vertices across a triangle.
    Varying authored vertex tint is baked without changing face trajectories.
    """
    if texture_size not in (64,128):raise ValueError('Unsupported hand texture profile')
    if len(palette)!=768 or not shapes:raise ValueError('Invalid hand source')
    source_shapes=shapes
    shapes,materials,textures=_bake_vertex_tints(shapes,materials,textures)
    groups={};keys=[];frames=[];faces=[];uvs=[];offset=0;frame_count=None
    for s in shapes:
        p=np.asarray(s['positions']);uv=np.asarray(s['uv']);f=np.asarray(s['faces']);c=np.asarray(s['colours'])
        if p.ndim!=3 or p.shape[2]!=3 or not np.isfinite(p).all() or uv.shape!=(p.shape[1],2) or not np.isfinite(uv).all():raise ValueError('Invalid authored hand vertices')
        if frame_count is None:frame_count=p.shape[0]
        if p.shape[0]!=frame_count or f.ndim!=2 or f.shape[1]!=3 or f.min()<0 or f.max()>=p.shape[1]:raise ValueError('Invalid authored hand topology')
        if c.shape!=(p.shape[1],4) or not np.isfinite(c).all() or not np.allclose(c,c[:1],rtol=0,atol=1e-6):raise ValueError('Nonuniform hand vertex tint needs a separate bake')
        m=materials[s['material']];tint=np.asarray(m['diffuse'])*c[0,:3]
        if not np.isfinite(tint).all() or np.any(tint<0) or np.any(tint>1):raise ValueError('Invalid hand material tint')
        key=(m['texture_index'],tuple(tint));keys.append(key)
        group=groups.setdefault(key,{'low':uv.min(0),'high':uv.max(0)})
        group['low']=np.minimum(group['low'],uv.min(0));group['high']=np.maximum(group['high'],uv.max(0))
        frames.append(p);faces.append(f[:,[0,2,1]]+offset);uvs.append(uv);offset+=p.shape[1]
    if offset>1999 or sum(len(f) for f in faces)>2048:raise ValueError('Authored hand model exceeds bounded profile')
    canvas=Image.new('RGB',(512,480));x=y=row_height=0
    for key,g in groups.items():
        tex=textures.get(key[0])
        if tex is None:tex=np.full((1,1,3),220,np.uint8)
        image=Image.fromarray(np.asarray(tex)[:,:,:3].astype(np.uint8))
        scale=min(1,texture_size/max(image.size));size=tuple(max(1,round(v*scale)) for v in image.size)
        image=image.resize(size,Image.Resampling.LANCZOS);pixels=np.asarray(image)
        lo=np.floor(g['low']*size).astype(int)-1;hi=np.ceil(g['high']*size).astype(int)+1
        width,height=(hi-lo+1).tolist()
        if width>512 or height>480:raise ValueError('Hand UV repeat exceeds atlas bounds')
        if x+width>512:x=0;y+=row_height;row_height=0
        if y+height>480:raise ValueError('Hand texture atlas exceeds480rows')
        xx=np.arange(lo[0],hi[0]+1)%size[0];yy=np.arange(lo[1],hi[1]+1)%size[1]
        tile=np.clip(pixels[yy[:,None],xx[None,:]]*np.asarray(key[1]),0,255).astype(np.uint8)
        canvas.paste(Image.fromarray(tile),(x,y));g.update(origin=np.array([x,y])-lo,size=np.array(size))
        x+=width;row_height=max(row_height,height)
    uvs=[uv*groups[key]['size']+groups[key]['origin'] for uv,key in zip(uvs,keys)]
    canvas=canvas.crop((0,0,512,y+row_height))
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    frames=np.concatenate(frames,axis=1);faces=np.concatenate(faces)
    audit_source_topology(source_shapes,frames,faces)
    return frames,faces,np.concatenate(uvs),canvas.quantize(palette=pal,dither=Image.Dither.NONE)
