# SPDX-License-Identifier: GPL-3.0-only
"""Share identical BSP29 lightmaps and visibility rows without runtime decoding.

Geometry, textures, collision, leaf membership and decoded samples stay intact.
Offsets point to shared immutable bytes using the existing BSP29 format.
"""
import struct
import numpy as np
from player_hull import lumps, pack_lumps


def light_ranges(data):
    faces=list(struct.iter_unpack('<Hhihh4Bi',data[7]))
    vertices=np.frombuffer(data[3],dtype='<f4').reshape(-1,3).astype(np.float64)
    edges=np.frombuffer(data[12],dtype='<u2').reshape(-1,2)
    surfedges=np.frombuffer(data[13],dtype='<i4')
    texinfo=np.frombuffer(data[6],dtype=np.dtype([('vec','<f4',(2,4)),('tail','<i4',(2,))]))['vec']
    counts=np.array([f[3] for f in faces])
    if np.any(counts<1):raise ValueError('Empty BSP face')
    starts=np.r_[0,np.cumsum(counts)[:-1]]
    indices=np.concatenate([np.arange(f[2],f[2]+f[3]) for f in faces])
    selected=surfedges[indices]
    points=vertices[edges[np.abs(selected),(selected<0).astype(int)]]
    vectors=np.repeat(texinfo[[f[4] for f in faces]].astype(np.float64),counts,axis=0)
    # CalcSurfaceExtents stores the projected value in a float before rounding.
    uv=((points[:,None,:]*vectors[:,:,:3]).sum(2)+vectors[:,:,3]).astype(np.float32)
    low=np.floor(np.minimum.reduceat(uv,starts,axis=0)/16)
    high=np.ceil(np.maximum.reduceat(uv,starts,axis=0)/16)
    dims=np.maximum(1,high-low).astype(int)+1
    result=[]
    for i,face in enumerate(faces):
        if face[-1]<0:continue
        styles=sum(s!=255 for s in face[5:9])
        size=int(dims[i,0]*dims[i,1])*styles
        offset=face[-1]
        if not styles or size<1 or offset+size>len(data[8]):
            raise ValueError('Lightmap sample bounds')
        result.append((i,offset,size))
    return result


def visibility_row(data, offset, width):
    start=offset;expanded=0
    while expanded<width:
        if offset>=len(data):raise ValueError('Truncated PVS')
        value=data[offset];offset+=1
        if value:expanded+=1
        else:
            if offset>=len(data) or not data[offset]:raise ValueError('Invalid PVS run')
            expanded+=data[offset];offset+=1
    if expanded!=width:raise ValueError('PVS row overrun')
    return bytes(data[start:offset])


def deduplicate(raw):
    data=lumps(raw);before=[len(b) for b in data]
    light=bytearray();seen={}
    ranges=light_ranges(data)
    for index,offset,size in ranges:
        samples=bytes(data[8][offset:offset+size])
        if samples not in seen:
            seen[samples]=len(light);light+=samples
        struct.pack_into('<i',data[7],index*20+16,seen[samples])
    # Independently compare every old referenced byte range before discarding it.
    for index,offset,size in ranges:
        new=struct.unpack_from('<i',data[7],index*20+16)[0]
        if light[new:new+size]!=data[8][offset:offset+size]:raise ValueError('Lightmap changed')
    data[8]=light
    width=(struct.unpack_from('<i',data[14],52)[0]+7)//8
    vis=bytearray();seen={}
    for index in range(len(data[10])//28):
        offset=struct.unpack_from('<i',data[10],index*28+4)[0]
        if offset<0:continue
        row=visibility_row(data[4],offset,width)
        if row not in seen:
            seen[row]=len(vis);vis+=row
        struct.pack_into('<i',data[10],index*28+4,seen[row])
    data[4]=vis
    result=pack_lumps(data)
    return result,dict(bytes_before=len(raw),bytes_after=len(result),
                       lighting_before=before[8],lighting_after=len(light),
                       visibility_before=before[4],visibility_after=len(vis),
                       lightmap_samples='byte-identical',visibility_rows='byte-identical',
                       geometry_and_collision='unchanged')
