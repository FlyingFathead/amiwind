# SPDX-License-Identifier: GPL-3.0-only
"""The engine loader policy the heap audits read from engine/aga/src/model.c (BUILD-CHIM-HEAP-KEY-LOADER-63).

The CHIM world stages reach the heap audits (tools/check_world_map_heap.py compile_target_sizes, tools/alias_stream_heap.py,
tools/edge_cache_heap.py, tools/sprite_heap.py). They read model.c only for its loader policy: the sprite streaming
profile, the BSP slice sizes, the alias stream limits, and the packed-edge pin over the brush and edge-cache loaders.
Keyed as the whole file, every model.c edit (an alias reader change, a log line) re-keyed the whole CHIM world. A stage
key now counts model.c by policy(): the extracted values, each policy's refusal text when it does not recognise the
loader (the stage then runs and its audit refuses, as before), and brush_edge_digest() of the loaders the packed-edge
pin covers. tools/engine_facts.py narrow() uses it; tests/test_engine_loader_policy.py keeps it honest.

Instrumentation for keys plus the edge pin's reading of model.c: it decides what a key counts and what the edge pin
compares, never what the audit computes."""
import hashlib
import json
from pathlib import Path

MODEL_C = 'engine/aga/src/model.c'
# Version 2 (2026-11-09): body-less items count only when the loaders reach them (brush_edge_items).
VERSION = 2
PREFIX = 'policy%d:' % VERSION
# The brush and edge-cache loaders of model.c (BSP lumps, sections, records, the edge cache, the brush stream): the code
# the packed-edge allocation policy depends on. Every #define and every declaration that is not a function body counts
# too when these loaders reach it, directly or through other such items (limits, tables, static buffers, types).
BRUSH_EDGE_FUNCTIONS = frozenset((
    'AW_RecordSection AW_TryStreamBrush AW_BrushError AW_BrushCaught AW_BrushAlloc AW_BrushMark AW_BrushFreeToMark '
    'AW_LumpBytes AW_RecordsBegin AW_SliceWindow AW_RecordsNext AW_WindowBytes AW_LoadTextureRefs Mod_LoadTextures '
    'Mod_LoadLighting Mod_LoadVisibility Mod_LoadEntities Mod_LoadVertexes Mod_LoadSubmodels Mod_LoadEdges '
    'Mod_LoadTexinfo AW_DoubleRound CalcSurfaceExtents Mod_LoadFaces Mod_SetParent AW_PredictRenderPrefix '
    'AW_DecodeNodes Mod_LoadNodes Mod_LoadLeafs AW_DecodeClipnodes Mod_LoadClipnodes Mod_MakeHull0 '
    'Mod_LoadMarksurfaces Mod_LoadSurfedges Mod_LoadPlanes RadiusFromBounds AW_LoadBrushSection AW_EdgeCacheService '
    'AW_EdgeCacheFace AW_InitEdgeCache AW_BrushSection AW_BrushFinish Mod_LoadBrushModel AW_BrushHeader AW_BrushBound '
    'AW_BrushImage AW_BrushStreamBegin AW_BrushStreamStep').split())


def brush_edge_items(text):
    """The items of model.c TEXT the packed-edge pin covers (engine_facts.parse_header items)."""
    import engine_facts
    items = engine_facts.parse_header(text, 2)
    loaders = [item for item in items if item.get('body') and item['defines'] & BRUSH_EDGE_FUNCTIONS]
    # A body-less item (a #define, a declaration, a static table, a struct type) counts only when the loaders reach it:
    # their identifiers, then the identifiers of every item reached so far, until nothing new is added. 'uses' holds
    # the words of an item's #if/#ifdef conditions too, so a macro guarding reached code is reached as well. An item
    # that defines nothing nameable (an #error, a bare directive) cannot be told apart and always counts.
    bodyless = [item for item in items if not item.get('body')]
    reached, wanted = set(), set()
    for item in loaders:
        wanted |= item['uses'] | item['defines']
    pending = True
    while pending:
        pending = False
        for index, item in enumerate(bodyless):
            if index not in reached and item['defines'] & wanted:
                reached.add(index)
                wanted |= item['uses'] | item['defines']
                pending = True
    keep = {id(item) for index, item in enumerate(bodyless) if index in reached or not item['defines']}
    keep |= {id(item) for item in loaders}
    return [item for item in items if id(item) in keep]


def brush_edge_digest(text):
    """SHA-256 of the brush and edge-cache loaders of model.c TEXT (comments and spacing do not count)."""
    rows = [[[list(level) for level in item['stack']], item['text']] for item in brush_edge_items(text)]
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode('utf-8')).hexdigest()


def policy(source):
    """{policy: value or 'refused: text'} of the engine source folder SOURCE (engine/aga/src)."""
    import alias_stream_heap
    import check_world_map_heap
    import edge_cache_heap
    import sprite_heap
    source = Path(source)
    text = (source / 'model.c').read_text(encoding='utf-8')
    out = {'brush_edge_loaders': brush_edge_digest(text)}
    for name, call in (('sprite', lambda: sprite_heap.sprite_loader_profile(text)),
                       ('bsp_slice', lambda: check_world_map_heap.bsp_slice_policy(text)),
                       ('alias', lambda: alias_stream_heap.runtime_policy(source)),
                       ('edge_cache', lambda: edge_cache_heap.runtime_policy(source))):
        try:
            out[name] = call()
        except (OSError, ValueError) as error:
            out[name] = 'refused: %s' % error
    return out


def key_value(root):
    """The stage key value of model.c in the checkout ROOT."""
    found = policy(Path(root) / 'engine/aga/src')
    return PREFIX + hashlib.sha256(json.dumps(found, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
