# SPDX-License-Identifier: GPL-3.0-only
"""Bake the base humanoid standing hull with unmodified external qbsp.

NIF base_anim collision half extents (29.28,28.48,66.5), at world scale .25.
Compile enlarged geometry, then inverse-transform only the standing hull.
Visible geometry, point traces and visibility data remain unchanged.

Collision hulls the engine uses (BUILD-SEYDA-HULL2-32). SV_HullForEntity
(engine/aga/src/world.c) picks the hull from the moving box's x size: < 3 is
hull 0 (point traces), <= 32 is hull 1, wider is hull 2. Every box in
engine/aga/qc/world.qc and every engine SV_Move call is either a point or the
14.64-unit standing humanoid, so only hulls 0 and 1 are ever selected;
model.c gives hull 1 this module's MINS/MAXS. Hull 2 (and hull 3) are loaded
but never traced. tests/test_engine_hulls.py keeps that contract checked.

The scaled standing-collision map is an intermediate: only its hull 1 is
grafted. It is compiled as BSP2, whose 32-bit indices cannot overflow, so its
unused hull 2 can never stop a build. The engine's real limits apply to the
grafted hull in the BSP29 result (check_engine_hulls).
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
# Keep the offline floor diagnostic aligned with quakedef.h's AW_WALKABLE_Z.
WALKABLE_Z=0.69
# The engine's step height (sv_move.c and sv_phys.c STEPSIZE): the largest
# rise the player steps up without jumping.
STEP_HEIGHT=8.5

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

# model.c AW_DecodeClipnodes: at most 65520 clipnodes; children are unsigned
# 16-bit, 65521..65535 being contents -15..-1 (world.c AW_ClipChild).
ENGINE_CLIPNODE_LIMIT=65520
# bspfile.h MAX_MAP_NODES: hull 0 render/point nodes use signed short children.
ENGINE_NODE_LIMIT=32767
# Hulls traced by the engine (see the module docstring); others are not limited.
ENGINE_HULLS=(0,1)
# Option for the scaled intermediate compile: 32-bit indices, no 16-bit limits.
INTERMEDIATE_FORMAT='-bsp2'

def clip_child(value):
    """Decode a BSP29 clipnode child as the engine does (AW_ClipChild)."""
    return value+65536 if value<-15 else value

def intermediate_hull(raw):
    """Planes, clipnodes and world hull-1 root of a BSP29 or BSP2 qbsp output."""
    if raw[:4]==b'BSP2':
        if len(raw)<124:raise ValueError('BSP lump bounds')
        parts=[]
        for i in range(15):
            o,n=struct.unpack_from('<ii',raw,4+i*8)
            if o<124 or n<0 or o+n>len(raw):raise ValueError('BSP lump bounds')
            parts.append(raw[o:o+n])
        nodes=list(struct.iter_unpack('<iii',parts[9]))
    else:
        parts=lumps(raw)
        nodes=[(p,clip_child(l),clip_child(r)) for p,l,r in struct.iter_unpack('<ihh',parts[9])]
    if len(parts[14])<64:raise ValueError('BSP has no world model')
    planes=list(struct.iter_unpack('<4fi',parts[1]))
    return planes,nodes,struct.unpack_from('<i',parts[14],40)[0]

def graft_hull(target, collision):
    a=lumps(target);planes,nodes,root=intermediate_hull(collision)
    seen=set();ordered=[];stack=[root]
    # Pre-order (node, left subtree, right subtree), the order of the BSP29 graft.
    while stack:
        n=stack.pop()
        if n<0 or n in seen:continue
        if n>=len(nodes):raise ValueError('Clipnode index')
        seen.add(n);ordered.append(n);_,left,right=nodes[n];stack.extend((right,left))
    start=len(a[9])//8;remap={n:start+i for i,n in enumerate(ordered)};pmap={}
    if start+len(ordered)>ENGINE_CLIPNODE_LIMIT:
        raise ValueError(f'Standing hull exceeds the engine clipnode limit ({start+len(ordered)} > {ENGINE_CLIPNODE_LIMIT})')
    for old in ordered:
        pi,left,right=nodes[old]
        if pi not in pmap:
            normal=[planes[pi][i]*FACTORS[i] for i in range(3)];length=math.sqrt(sum(v*v for v in normal));normal=[v/length for v in normal]
            distance=planes[pi][3]/length+normal[2]*(-MINS[2]-24/FACTORS[2])
            pmap[pi]=len(a[1])//20;a[1]+=struct.pack('<4fi',*normal,distance,3)
        a[9]+=struct.pack('<iHH',pmap[pi],*((remap[c] if c>=0 else c)&65535 for c in (left,right)))
    struct.pack_into('<i',a[14],40,remap[root] if root>=0 else root)
    # A format marker documents the standing hull needed by this checkpoint.
    a[0]=a[0].replace(b'"classname" "worldspawn"',b'"classname" "worldspawn"\n"aw_hull" "'+PROFILE.encode()+b'"',1)
    return pack_lumps(a)

def check_engine_hulls(raw):
    """Fail if a hull the engine traces exceeds an engine limit; report the rest.

    Hull 0 is the node tree (signed 16-bit children), hull 1 the clipnode tree
    (unsigned 16-bit children). Unused hulls are counted, never limited.
    """
    data=lumps(raw)
    nodes=[(p,l,r) for p,l,r,*_ in struct.iter_unpack('<i2h6h2H',data[5])]
    clips=[(p,clip_child(l),clip_child(r)) for p,l,r in struct.iter_unpack('<ihh',data[9])]
    models=[struct.unpack_from('<4i',data[14],k*64+36) for k in range(len(data[14])//64)]
    if len(nodes)>ENGINE_NODE_LIMIT:raise ValueError(f'Hull 0 node count exceeds the engine limit ({len(nodes)} > {ENGINE_NODE_LIMIT})')
    if len(clips)>ENGINE_CLIPNODE_LIMIT:raise ValueError(f'Clipnode count exceeds the engine limit ({len(clips)} > {ENGINE_CLIPNODE_LIMIT})')
    report={'nodes':len(nodes),'clipnodes':len(clips),'hulls':{}}
    for hull in range(4):
        tree=nodes if hull==0 else clips;seen=set()
        for model in models:
            stack=[model[hull]]
            while stack:
                n=stack.pop()
                if n<0 or n in seen:continue
                if n>=len(tree):
                    if hull in ENGINE_HULLS:raise ValueError(f'Hull {hull} child {n} outside {len(tree)} records')
                    continue
                seen.add(n);stack.extend(tree[n][1:3])
        report['hulls'][str(hull)]={'reachable':len(seen),'engine_traced':hull in ENGINE_HULLS}
    return report

def compile_standing_hull(map_path, qbsp, log=None):
    """Compile the scaled standing map; return the intermediate (BSP2) bytes."""
    collision=map_path.parent/'standing-collision.map';collision.write_text(scaled_map(map_path.read_text()))
    output={} if log is None else {'stdout':log,'stderr':subprocess.STDOUT}
    subprocess.run([str(Path(qbsp).resolve()),'-nopercent',INTERMEDIATE_FORMAT,collision.name],
                   cwd=collision.parent,check=True,**output)
    return collision.with_suffix('.bsp').read_bytes()

def rebuild_world_hull(base, map_path, qbsp, discard_stock_hulls=False, records=None, log=None):
    """The one standing-hull path for every converted map.

    records optionally filters the entity list kept when stock hulls are
    discarded; log receives the compiler output (default: inherited).
    """
    collision=compile_standing_hull(map_path,qbsp,log)
    raw=base.read_bytes()
    if discard_stock_hulls:
        # Towns use the source-sized standing player, like streamed world maps.
        # Remove superseded/default Quake actor hulls before grafting that hull.
        from compact_bsp import compact, entities
        data=lumps(raw)
        for offset in (40,44,48):struct.pack_into('<i',data[14],offset,-1)
        raw,_=compact(pack_lumps(data),records=None if records is None else records(entities(data[0])))
    grafted=graft_hull(raw,collision)
    check_engine_hulls(grafted)
    base.write_bytes(grafted)
