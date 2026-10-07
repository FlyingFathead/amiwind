# SPDX-License-Identifier: GPL-3.0-only
"""Exact world-edge cache prefix and conservative generic BSP cost."""
import hashlib
from pathlib import Path
import struct

# Re-pinned 2026-10-07 for the warning cleanup: model.c (line split, name buffer
# 10->16, Mod_PointInLeaf signature matches model.h) and r_draw.c (tedge static).
# Edge-cache allocation is unchanged.
SOURCE_HASHES={
    'model.c':'8731bbbc42c05ae3e2e67b955a992772dd521cf07be0488db9fe9435436aec8d',
    'model.h':'c49d4a759229aaaab738aac9857ea5dc8feedf300d1c0dca5193e7d80eafb9d2',
    'r_draw.c':'d56257781f2617d09f54d9fdc596f3f3dd31f1b3b94629acc1a870284d98965b',
    'asm_draw.h':'15dafafe33898852972379fc48524346c287a342ba95f17c01becdc75926eba1',
}

def runtime_policy(source):
    source=Path(source)
    text=(source/'model.h').read_text()
    if '#define AW_EDGE_CACHE_SPLIT 1' not in text:
        return dict(mode='embedded',edge_cache_split=0,model_slot_static_delta=0)
    if not SOURCE_HASHES or any(hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha for name,sha in SOURCE_HASHES.items()):
        raise ValueError('Unrecognized packed-edge allocation policy')
    return dict(mode='world_prefix',edge_cache_split=1,source_sha256=SOURCE_HASHES,
        model_slot_capacity=256,immutable_edge_bytes=4,
        note='Allocation/source policy. Renderer output, target ABI and native acceptance are separate gates.')

def prefix(lumps):
    faces=list(struct.iter_unpack('<Hhihh4Bi',lumps['faces']))
    nodes=list(struct.iter_unpack('<i2h6h2H',lumps['nodes']))
    models=list(struct.iter_unpack('<9f7i',lumps['models']))
    sequence=[v[0] for v in struct.iter_unpack('<i',lumps['surfedges'])]
    edges=len(lumps['edges'])//4
    if not models:raise ValueError('Missing edge-cache world model')
    protected=set()
    def add(first,count):
        if first<0 or count<0 or first+count>len(faces):raise ValueError('Invalid edge-cache face span')
        protected.update(range(first,first+count))
    add(*models[0][14:16])
    for node in nodes:add(*node[9:11])
    for mark, in struct.iter_unpack('<H',lumps['marksurfaces']):add(mark,1)
    limit=1 if edges else 0
    for index in protected:
        first,count=faces[index][2:4]
        if first<0 or count<0 or first+count>len(sequence):raise ValueError('Invalid edge-cache edge span')
        for value in sequence[first:first+count]:
            edge=abs(value)
            if edge>=edges:raise ValueError('Invalid edge-cache edge index')
            limit=max(limit,edge+1)
    return dict(prefix_edges=limit,protected_faces=len(protected),all_edges=edges)
