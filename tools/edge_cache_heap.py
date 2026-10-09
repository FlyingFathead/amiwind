# SPDX-License-Identifier: GPL-3.0-only
"""Exact world-edge cache prefix and conservative generic BSP cost."""
import hashlib
from pathlib import Path
import struct

# Re-pinned 2026-10-07 for the warning cleanup: model.c (line split, name buffer
# 10->16, Mod_PointInLeaf signature matches model.h) and r_draw.c (tedge static).
# Edge-cache allocation is unchanged.
# Re-pinned 2026-10-08 for unsigned texinfo/marksurface/leaf-mark reads and the
# double-precision CalcSurfaceExtents rule (model.c); edge-cache allocation is
# unchanged.
# Re-pinned 2026-10-08 for Q_sscanf in model.c (engine text parsing,
# ENGINE-FPSP-MISSING-31) and the renderer edge counters in r_draw.c
# (dbg rcount); edge-cache allocation is unchanged.
# Re-pinned 2026-10-08 for BSP sections decoded from bounded slices
# (LOADER-STAGING-PEAK-32): AW_InitEdgeCache and every resident allocation are
# unchanged; the decoded Hunk of all shipped maps is byte-identical to the
# staged loader's. Only the temporary input changed (check_world_map_heap).
# Re-pinned 2026-10-08 for CHIM brush loading (model.c, model.h): the decoders
# allocate through AW_BrushAlloc, which is Hunk_AllocName unless a CHIM arena
# is set, and Mod_LoadBrushModel runs the same sections in the same order. Legacy
# loads, AW_InitEdgeCache and every Hunk allocation are unchanged (decoded Hunk
# byte-identical on the slice-load fixtures); CHIM models get no edge cache.
# Re-pinned 2026-10-08 for the merge of v0.0.32-dev (Q_sscanf, renderer edge
# counters) into the CHIM engine branch; edge-cache allocation is unchanged.
# Re-pinned 2026-10-08 for CHIM placed models (model.c, model.h): an arena flag
# decodes a model's chained point hull into hull 0 clipnodes only (no render
# nodes, no Mod_SetParent). Legacy loads and edge-cache allocation unchanged.
# Re-pinned 2026-10-09 for the in-memory diagnostic logs (BOOT-VOLUME-NOT-VALIDATED-33):
# model.c writes bsp-load-profile.txt through aw_log.c; edge-cache allocation is unchanged.
# Re-pinned 2026-10-09 for CHIM streamed statics (model.c): the sprite loader allocates through
# AW_SpriteAlloc, which is Hunk_AllocName unless Mod_LoadSpriteInto sets a zone allocator; edge-cache
# allocation is unchanged.
SOURCE_HASHES={
    'model.c':'2b6084440550513f87a741b543a47fd8ff2abe8287f64f5c3b5d5113c6120fb2',
    'model.h':'594e162fd26856ce2721319abd0a8e319a17f975b3796de39f25b2a83439da35',
    'r_draw.c':'1e26849d022fa219adfd399f8863118b72e34daab4b6e2b588e22ed8c53c8232',
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
    faces=list(struct.iter_unpack('<HhihH4Bi',lumps['faces']))
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
