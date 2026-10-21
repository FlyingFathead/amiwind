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
# Re-pinned 2026-10-10 for ENGINE-FILEBASE-UNBOUNDED-35 (model.c): loadname is sized by
# COM_FILEBASE_SIZE (32, as before); edge-cache allocation is unchanged.
# Re-pinned 2026-10-10 for CHIM bad brush data (model.c, model.h; CHIM-BRUSH-BAD-DATA-35): arena decodes
# catch decoder errors and return a failed load; legacy loads and edge-cache allocation unchanged.
# Re-pinned 2026-10-09 for near/far NPC models (model.c, model.h): Mod_ReleaseAlias frees an optional
# alias model's Cache data and marks its slot unreferenced (aw_npc_lod.c); edge-cache allocation is unchanged.
# Re-pinned 2026-10-10 for crash paths (model.c; ENGINE-MODEL-NAME-SYSERROR-35, ENGINE-LEAF-LIMIT-UNCHECKED-35,
# ENGINE-ENTITY-TEXT-UNBOUNDED-35): name length checks, a leaf-count check, a bounded frame name; edge-cache
# allocation is unchanged.
# Re-pinned 2026-10-15 for CHIM-MODEL-ARENA-RESERVE-41: only placed-model
# arena bounds change; all edge-cache code and legacy loaders are byte-identical.
# Re-pinned 2026-10-20 for shared actor skins (IMAGE-ACTOR-SKIN-REPEATS-46): the alias file loader rebuilds a
# shared-skin model in its own malloc block before decoding; edge-cache code and brush loaders are byte-identical.
# Re-pinned 2026-10-20 for CHIM-PLANE-TYPE-ALL-SLANTED-46: Mod_LoadPlanes sets the type of exact +X/+Y/+Z planes;
# no allocation changes.
# Re-pinned 2026-10-20 for ENGINE-STRICT-WARNINGS-36 (model.c): only Sys_Error format conversions (%ld -> %d for
# int values) and a format attribute on AW_BrushError's declaration; no allocation or loader code changed.
# Re-pinned 2026-10-21 for GHOSTFENCE-NO-ANIMATION-46 (r_draw.c): one static table of CYCLE ints (stillturbtable,
# dbg ghostfence off); no edge-cache allocation changes.
SOURCE_HASHES={
    'model.c':'7865e39df3b8ea89ef5ad38a1cab239cd35eb5b7df19f222ac35a3e4fdaeb517',
    'model.h':'6ca2bae523261a81ad9613620e84af3dfb355551ee4fc64fb9644fe435e28f3c',
    'r_draw.c':'08464e4c3bbb98ed197f7c42c5b013818d2ef4fffd1a5727ed9a6a4c3385cce4',
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

def prefix(lumps,method=None):
    """The world edge-cache prefix: edges of every face the world model, a node or a leaf mark can draw.
    method: 'vector' (default; numpy spans) or 'python' (the earlier per-face loop, kept selectable;
    env AMIWIND_HEAP_AUDIT_METHOD). Both give the same result (tests/test_edge_cache_heap.py and every
    map of the dev5 full build); the loop was a fifth of the world map heap audit's remaining time
    (BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36). For a broken map both raise; when it has several faults the
    one named first may differ."""
    from sprite_heap import efrag_method
    if efrag_method(method)=='python':
        return prefix_python(lumps)
    return prefix_vector(lumps)

def prefix_vector(lumps):
    import numpy as np
    # struct.iter_unpack checks each lump's length up front (the same struct.error as the loop)
    struct.iter_unpack('<HhihH4Bi',lumps['faces']);struct.iter_unpack('<i2h6h2H',lumps['nodes'])
    struct.iter_unpack('<i',lumps['surfedges']);struct.iter_unpack('<H',lumps['marksurfaces'])
    models=list(struct.iter_unpack('<9f7i',lumps['models']))
    face_rows=np.frombuffer(lumps['faces'],dtype=np.dtype([('plane','<u2'),('side','<i2'),('first','<i4'),
                                                           ('count','<i2'),('tex','<u2'),('styles','u1',(4,)),
                                                           ('light','<i4')]))
    node_rows=np.frombuffer(lumps['nodes'],dtype=np.dtype([('plane','<i4'),('children','<i2',(2,)),
                                                           ('box','<i2',(6,)),('first','<u2'),('count','<u2')]))
    sequence=np.frombuffer(lumps['surfedges'],dtype='<i4').astype(np.int64)
    marks=np.frombuffer(lumps['marksurfaces'],dtype='<u2').astype(np.int64)
    edges=len(lumps['edges'])//4
    if not models:raise ValueError('Missing edge-cache world model')
    face_count=len(face_rows)
    first=np.concatenate(([models[0][14]],node_rows['first'].astype(np.int64),marks))
    count=np.concatenate(([models[0][15]],node_rows['count'].astype(np.int64),np.ones(len(marks),dtype=np.int64)))
    if ((first<0)|(count<0)|(first+count>face_count)).any():raise ValueError('Invalid edge-cache face span')
    protected=_spans(np,first,count,face_count)
    limit=1 if edges else 0
    faces=np.flatnonzero(protected)
    span_first=face_rows['first'][faces].astype(np.int64);span_count=face_rows['count'][faces].astype(np.int64)
    if ((span_first<0)|(span_count<0)|(span_first+span_count>len(sequence))).any():
        raise ValueError('Invalid edge-cache edge span')
    used=np.abs(sequence[_spans(np,span_first,span_count,len(sequence))])
    if used.size:
        if (used>=edges).any():raise ValueError('Invalid edge-cache edge index')
        limit=max(limit,int(used.max())+1)
    return dict(prefix_edges=limit,protected_faces=int(faces.size),all_edges=edges)

def _spans(np,first,count,length):
    """Boolean mask of [first, first+count) over 0..length-1 (spans already checked to fit)."""
    keep=count>0
    change=np.zeros(length+1,dtype=np.int64)
    np.add.at(change,first[keep],1);np.add.at(change,first[keep]+count[keep],-1)
    return np.cumsum(change[:length])>0

def prefix_python(lumps):
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
