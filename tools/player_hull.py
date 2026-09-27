# SPDX-License-Identifier: GPL-3.0-only
"""Bake the base humanoid standing hull with unmodified external qbsp.

NIF base_anim collision half extents (29.28,28.48,66.5), at world scale .25.
Compile enlarged geometry, then inverse-transform only the standing hull.
Visible geometry, point traces and visibility data remain unchanged.
"""
import math
import re
import struct
import subprocess
from pathlib import Path

MINS=(-7.32,-7.12,-16.625)
MAXS=(7.32,7.12,16.625)
FACTORS=(16/7.32,16/7.12,56/33.25)
PROFILE='tes3-humanoid-v1'

def scaled_map(text):
    pattern=r'\(\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*\)'
    def point(m):return '( '+' '.join(format(float(m[i+1])*FACTORS[i],'.8f') for i in range(3))+' )'
    return re.sub(pattern,point,text)

def lumps(raw):
    if len(raw)<124 or struct.unpack_from('<i',raw)[0]!=29:raise ValueError('Expected BSP29')
    out=[]
    for i in range(15):
        o,n=struct.unpack_from('<ii',raw,4+i*8)
        if o<124 or n<0 or o+n>len(raw):raise ValueError('BSP lump bounds')
        out.append(bytearray(raw[o:o+n]))
    return out

def pack_lumps(data):
    head=bytearray(struct.pack('<i',29)+bytes(120));body=bytearray()
    for i,raw in enumerate(data):
        body+=bytes(-len(body)%4);struct.pack_into('<ii',head,4+i*8,124+len(body),len(raw));body+=raw
    return bytes(head+body)

def graft_hull(target, collision):
    a=lumps(target);b=lumps(collision)
    planes=list(struct.iter_unpack('<4fi',b[1]));nodes=list(struct.iter_unpack('<ihh',b[9]))
    root=struct.unpack_from('<i',b[14],40)[0];seen=set();ordered=[]
    def walk(n):
        if n<0 or n in seen:return
        if n>=len(nodes):raise ValueError('Clipnode index')
        seen.add(n);ordered.append(n);_,left,right=nodes[n];walk(left);walk(right)
    walk(root)
    start=len(a[9])//8;remap={n:start+i for i,n in enumerate(ordered)};pmap={}
    if start+len(ordered)>32767:raise ValueError('Standing hull exceeds clipnode budget')
    for old in ordered:
        pi,left,right=nodes[old]
        if pi not in pmap:
            normal=[planes[pi][i]*FACTORS[i] for i in range(3)];length=math.sqrt(sum(v*v for v in normal));normal=[v/length for v in normal]
            distance=planes[pi][3]/length+normal[2]*(-MINS[2]-24/FACTORS[2])
            pmap[pi]=len(a[1])//20;a[1]+=struct.pack('<4fi',*normal,distance,3)
        a[9]+=struct.pack('<ihh',pmap[pi],remap[left] if left>=0 else left,remap[right] if right>=0 else right)
    struct.pack_into('<i',a[14],40,remap[root])
    # A format marker documents the standing hull needed by this checkpoint.
    a[0]=a[0].replace(b'"classname" "worldspawn"',b'"classname" "worldspawn"\n"aw_hull" "'+PROFILE.encode()+b'"',1)
    return pack_lumps(a)

def rebuild_world_hull(base, map_path, qbsp):
    collision=map_path.parent/'standing-collision.map';collision.write_text(scaled_map(map_path.read_text()))
    subprocess.run([str(Path(qbsp).resolve()),'-nopercent',collision.name],cwd=collision.parent,check=True)
    base.write_bytes(graft_hull(base.read_bytes(),collision.with_suffix('.bsp').read_bytes()))
