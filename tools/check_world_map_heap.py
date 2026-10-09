#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Conservatively estimate one Quake BSP29 world's target Hunk loading peak.

The target ABI profile is compiled by the configured Amiga SDK on every run.
The report separates modeled loader residency, temporary input, an explicit
pre-map engine reserve, and independent safety headroom. Passing is a source
allocation estimate, not a target or gameplay memory validation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BSP_VERSION = 29
HEADER_SIZE = 4 + 15 * 8
HEAP_RESERVE_BYTES = 11 * 1024 * 1024
BASELINE_RESERVE_BYTES = 3 * 1024 * 1024
SAFETY_HEADROOM_BYTES = 2 * 1024 * 1024

# name, disk record size probe name, decoded target allocation probe name
RECORDS = {
    'entities': (0, None, None),
    'planes': (1, 'dplane', 'mplane'),
    'textures': (2, None, None),
    'vertexes': (3, 'dvertex', 'mvertex'),
    'visibility': (4, None, None),
    'nodes': (5, 'dnode', 'mnode'),
    'texinfo': (6, 'texinfo', 'mtexinfo'),
    'faces': (7, 'dface', 'msurface'),
    'lighting': (8, None, None),
    'clipnodes': (9, 'dclipnode', 'clipnode'),
    'leafs': (10, 'dleaf', 'mleaf'),
    'marksurfaces': (11, 'short', None),
    'edges': (12, 'dedge', 'medge'),
    'surfedges': (13, 'int', None),
    'models': (14, 'dmodel', 'dmodel'),
}
LOAD_ORDER = ('vertexes', 'edges', 'surfedges', 'textures', 'lighting', 'planes',
              'texinfo', 'faces', 'marksurfaces', 'visibility', 'leafs', 'models',
              'nodes', 'clipnodes', 'entities')
DIRECT_BYTE_LUMPS = {'entities', 'visibility', 'lighting'}
DIRECT_IN_PLACE_LUMPS = {'clipnodes'}
# Every other lump is decoded from one bounded Hunk_TempAlloc slice straight into
# its final allocations (model.c AW_LoadBrushSection / AW_RecordsNext): a window
# of min(lump, 16 KiB) plus, for a lump larger than one window, a prefix: 64
# bytes for a split record or, for the texture lump, its directory (at most
# 4+4*512 bytes).
BSP_SLICE_BYTES = 16384
BSP_RECORD_PREFIX_BYTES = 64
BSP_DIRECTORY_BYTES = 4 + 4 * 512
PROBE_TYPES = ('pointer', 'short', 'int', 'hunk', 'dvertex', 'dedge', 'dplane', 'dnode',
               'dclipnode', 'clipnode', 'dleaf', 'texinfo', 'dface', 'dmodel', 'mvertex',
               'medge', 'mplane', 'mtexinfo', 'msurface', 'mnode', 'mleaf',
               'clipnode', 'texture', 'hull', 'float', 'entity', 'efrag', 'efrag_page',
               'msprite', 'mspriteframe', 'mspritegroup', 'mspriteframedesc',
               'scenery', 'client', 'qsocket', 'signon_capacity', 'reliable_capacity', 'network_capacity',
               'aliashdr', 'maliasframedesc', 'mdl', 'stvert', 'mtriangle',
               'maliasskindesc', 'trivertx', 'cache_system',
               'harvest_proxy_static', 'harvest_catalogue_extension',
               'harvest_plant_capacity', 'harvest_model_capacity',
               'harvest_storage_mode', 'harvest_runtime_static',
               'harvest_model_record', 'harvest_node_record', 'harvest_edge_record',
               'harvest_plant_record', 'harvest_node_capacity', 'harvest_edge_capacity',
               'harvest_text_capacity', 'interior_section_static', 'edge_cache_static', 'model')

PROBE_SOURCE = r'''#include "quakedef.h"
#include "model.h"
#include "aw_harvest.h"
#include "aw_section.h"
const unsigned int aw_size_interior_section_static=sizeof(aw_section_directory_t)+2*sizeof(int)+40;
typedef struct { int sentinel; int size; char name[8]; } aw_hunk_probe_t;
const unsigned int aw_size_pointer = sizeof(void *);
const unsigned int aw_size_short = sizeof(short);
const unsigned int aw_size_int = sizeof(int);
const unsigned int aw_size_hunk = sizeof(aw_hunk_probe_t);
const unsigned int aw_size_dvertex = sizeof(dvertex_t);
const unsigned int aw_size_dedge = sizeof(dedge_t);
const unsigned int aw_size_dplane = sizeof(dplane_t);
const unsigned int aw_size_dnode = sizeof(dnode_t);
const unsigned int aw_size_dclipnode = sizeof(dclipnode_t);
const unsigned int aw_size_clipnode = sizeof(dclipnode_t);
const unsigned int aw_size_dleaf = sizeof(dleaf_t);
const unsigned int aw_size_texinfo = sizeof(texinfo_t);
const unsigned int aw_size_dface = sizeof(dface_t);
const unsigned int aw_size_dmodel = sizeof(dmodel_t);
const unsigned int aw_size_mvertex = sizeof(mvertex_t);
const unsigned int aw_size_medge = sizeof(medge_t);
const unsigned int aw_size_model = sizeof(model_t);
#ifdef AW_EDGE_CACHE_SPLIT
const unsigned int aw_size_edge_cache_static = (sizeof(((model_t *)0)->edgecache)+sizeof(((model_t *)0)->edgecache_count))*AW_EDGE_CACHE_MODEL_LIMIT;
#else
const unsigned int aw_size_edge_cache_static = 0;
#endif
const unsigned int aw_size_mplane = sizeof(mplane_t);
const unsigned int aw_size_mtexinfo = sizeof(mtexinfo_t);
const unsigned int aw_size_msurface = sizeof(msurface_t);
const unsigned int aw_size_mnode = sizeof(mnode_t);
const unsigned int aw_size_mleaf = sizeof(mleaf_t);
const unsigned int aw_size_texture = sizeof(texture_t);
const unsigned int aw_size_hull = sizeof(hull_t);
const unsigned int aw_size_float = sizeof(float);
const unsigned int aw_size_entity = sizeof(entity_t);
/* Same fields/order as aw_scenery_t; target compiler supplies alignment. */
typedef struct { entity_t render; vec3_t mins,maxs; int modelindex; } aw_scenery_probe_t;
const unsigned int aw_size_scenery = sizeof(aw_scenery_probe_t);
const unsigned int aw_size_efrag = sizeof(efrag_t);
/* Same fields/order as the map-lifetime overflow page in r_efrag.c. */
typedef struct { void *next; efrag_t links[AW_EFRAG_PAGE_LINKS]; } aw_efrag_page_probe_t;
const unsigned int aw_size_efrag_page = sizeof(aw_efrag_page_probe_t);
const unsigned int aw_size_msprite = sizeof(msprite_t);
const unsigned int aw_size_mspriteframe = sizeof(mspriteframe_t);
const unsigned int aw_size_mspritegroup = sizeof(mspritegroup_t);
const unsigned int aw_size_mspriteframedesc = sizeof(mspriteframedesc_t);
const unsigned int aw_size_client = sizeof(client_t);
const unsigned int aw_size_qsocket = sizeof(qsocket_t);
const unsigned int aw_size_signon_capacity = sizeof(((server_t *)0)->signon_buf);
const unsigned int aw_size_reliable_capacity = MAX_MSGLEN;
const unsigned int aw_size_network_capacity = NET_MAXMESSAGE;
const unsigned int aw_size_aliashdr = sizeof(aliashdr_t);
const unsigned int aw_size_maliasframedesc = sizeof(maliasframedesc_t);
const unsigned int aw_size_mdl = sizeof(mdl_t);
const unsigned int aw_size_stvert = sizeof(stvert_t);
const unsigned int aw_size_mtriangle = sizeof(mtriangle_t);
const unsigned int aw_size_maliasskindesc = sizeof(maliasskindesc_t);
const unsigned int aw_size_trivertx = sizeof(trivertx_t);
/* Same field order as private cache_system_t in zone.c. */
typedef struct aw_cache_probe_s {
    int size; cache_user_t *user; char name[16];
    struct aw_cache_probe_s *prev,*next,*lru_prev,*lru_next;
} aw_cache_probe_t;
const unsigned int aw_size_cache_system = sizeof(aw_cache_probe_t);
/* Match the dedicated proxy arrays/pointers and AWH4 catalogue extension.
 * These are static Fast RAM, not Hunk allocations. Report them separately,
 * then conservatively debit the map admission allowance by the same amount. */
#ifdef AW_HARVEST_MODELS
#ifdef AW_HARVEST_TEXT_BYTES
typedef struct {
    entity_t *proxies; unsigned short *indices; unsigned char *submitted;
    model_t *models[AW_HARVEST_MODELS]; const aw_harvest_t *catalogue;
    aw_state_t *state; int capacity_warning,proxy_count; unsigned allocated_bytes;
} aw_harvest_proxy_probe_t;
const unsigned int aw_size_harvest_proxy_static=sizeof(aw_harvest_proxy_probe_t);
const unsigned int aw_size_harvest_catalogue_extension=0;
const unsigned int aw_size_harvest_storage_mode=1;
const unsigned int aw_size_harvest_runtime_static=sizeof(aw_harvest_t)+sizeof(edict_t **)+sizeof(unsigned char *)+sizeof(cvar_t)+sizeof(int);
const unsigned int aw_size_harvest_text_capacity=AW_HARVEST_TEXT_BYTES;
#else
typedef struct {
    entity_t proxies[AW_HARVEST_PLANTS];
    model_t *models[AW_HARVEST_MODELS];
    unsigned char submitted[AW_HARVEST_PLANTS];
    const aw_harvest_t *catalogue; aw_state_t *state; int capacity_warning;
} aw_harvest_proxy_probe_t;
const unsigned int aw_size_harvest_proxy_static = sizeof(aw_harvest_proxy_probe_t);
const unsigned int aw_size_harvest_catalogue_extension =
    sizeof(((aw_harvest_t *)0)->representation) + sizeof(((aw_harvest_t *)0)->models) +
    sizeof(((aw_harvest_t *)0)->model) +
    AW_HARVEST_PLANTS * sizeof(((aw_harvest_plant_t *)0)->scale);
const unsigned int aw_size_harvest_storage_mode=0;
const unsigned int aw_size_harvest_runtime_static=sizeof(aw_harvest_t)+AW_HARVEST_PLANTS*(sizeof(edict_t *)+sizeof(unsigned char))+sizeof(cvar_t)+sizeof(int);
const unsigned int aw_size_harvest_text_capacity=0;
#endif
const unsigned int aw_size_harvest_model_record=sizeof(aw_harvest_model_t);
const unsigned int aw_size_harvest_node_record=sizeof(aw_harvest_node_t);
const unsigned int aw_size_harvest_edge_record=sizeof(aw_harvest_edge_t);
const unsigned int aw_size_harvest_plant_record=sizeof(aw_harvest_plant_t);
const unsigned int aw_size_harvest_node_capacity=AW_HARVEST_NODES;
const unsigned int aw_size_harvest_edge_capacity=AW_HARVEST_EDGES;
const unsigned int aw_size_harvest_plant_capacity = AW_HARVEST_PLANTS;
const unsigned int aw_size_harvest_model_capacity = AW_HARVEST_MODELS;
#else
const unsigned int aw_size_harvest_proxy_static = 0;
const unsigned int aw_size_harvest_catalogue_extension = 0;
const unsigned int aw_size_harvest_plant_capacity = 0;
const unsigned int aw_size_harvest_model_capacity = 0;
const unsigned int aw_size_harvest_storage_mode=0;
const unsigned int aw_size_harvest_runtime_static=0;
const unsigned int aw_size_harvest_model_record=0;
const unsigned int aw_size_harvest_node_record=0;
const unsigned int aw_size_harvest_edge_record=0;
const unsigned int aw_size_harvest_plant_record=0;
const unsigned int aw_size_harvest_node_capacity=0;
const unsigned int aw_size_harvest_edge_capacity=0;
const unsigned int aw_size_harvest_text_capacity=0;
#endif
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def align16(value):
    return (value + 15) & ~15


def hunk_alloc_bytes(payload, hunk_header):
    if payload < 0:
        raise ValueError('Negative Hunk allocation')
    return hunk_header + align16(payload)


def hunk_temp_bytes(payload, hunk_header):
    # Hunk_TempAlloc aligns payload, then Hunk_HighAllocName adds its header.
    return hunk_header + align16(payload)


def slice_prefix_bytes(name, lump_bytes, record_prefix=BSP_RECORD_PREFIX_BYTES,
                       directory_bytes=BSP_DIRECTORY_BYTES):
    """Slice prefix of model.c AW_LoadBrushSection for one lump."""
    if lump_bytes <= BSP_SLICE_BYTES:
        return 0
    if name != 'textures':
        return record_prefix
    return align16(min(lump_bytes, directory_bytes))


def slice_temp_bytes(lump_bytes, hunk_header, slice_bytes=BSP_SLICE_BYTES,
                     prefix_bytes=BSP_RECORD_PREFIX_BYTES):
    """Temporary input while one sliced lump decodes: prefix + min(lump, slice), none if empty."""
    if lump_bytes < 0 or slice_bytes <= 0 or prefix_bytes < 0:
        raise ValueError('Invalid slice accounting')
    return hunk_temp_bytes(prefix_bytes + min(lump_bytes, slice_bytes), hunk_header) if lump_bytes else 0


def bsp_slice_policy(model_c):
    """Bind the modelled temporary input to the loader source (no staged lumps)."""
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', model_c, flags=re.S)
    match = re.search(r'^#define\s+AW_BSP_SLICE_BYTES\s+(\d+)\s*$', clean, re.M)
    prefix = re.search(r'^#define\s+AW_BSP_RECORD_PREFIX\s+(\d+)\s*$', clean, re.M)
    if (not match or not prefix or 'Hunk_TempAlloc(l->filelen' in clean or
            not re.search(r'^#define\s+AW_BSP_DIRECTORY_BYTES\s+\(4\+4\*MAX_MAP_TEXTURES\)\s*$', clean, re.M) or
            'aw_bsp_slice=Hunk_TempAlloc(aw_bsp_slice_bytes)' not in clean or
            'l->filelen<AW_BSP_SLICE_BYTES?l->filelen:AW_BSP_SLICE_BYTES' not in clean or
            'aw_bsp_slice_prefix=l->filelen<=AW_BSP_SLICE_BYTES?0:decode!=Mod_LoadTextures?AW_BSP_RECORD_PREFIX:' not in clean or
            '((l->filelen<AW_BSP_DIRECTORY_BYTES?l->filelen:AW_BSP_DIRECTORY_BYTES)+15)&~15;' not in clean or
            'if(aw_bsp_slice_bytes)aw_bsp_slice_bytes+=aw_bsp_slice_prefix;' not in clean):
        raise ValueError('Unrecognized BSP section loader; refusing to estimate')
    return {'mode': 'bounded_slices', 'slice_bytes': int(match.group(1)),
            'record_prefix_bytes': int(prefix.group(1)), 'directory_bytes': BSP_DIRECTORY_BYTES}


def compile_target_sizes(sdk):
    sdk = Path(sdk).resolve()
    suffix = '.exe' if os.name == 'nt' else ''
    compiler = sdk / 'bin' / ('m68k-amigaos-gcc' + suffix)
    if not compiler.is_file():
        raise ValueError('The selected SDK must provide m68k-amigaos-gcc')
    includes = [ROOT / 'engine/aga', ROOT / 'engine/aga/src', ROOT / 'engine/aga/CDPlayerSDK',
                ROOT / 'engine/aga/build/version', sdk / 'm68k-amigaos/ndk-include']
    with tempfile.TemporaryDirectory(prefix='amiwind-target-bsp-abi-') as temp:
        temp = Path(temp)
        source, assembly = temp / 'sizes.c', temp / 'sizes.s'
        source.write_text(PROBE_SOURCE, encoding='ascii', newline='\n')
        command = [str(compiler), '-std=gnu89', '-m68040', '-m68881', '-O1',
                   '-fno-strict-aliasing', '-DAMIGA', '-DFALSE=0', '-DTRUE=1',
                   '-DUSE_ASM_SPANS=0', '-DUSE_FAST_RECIPROCAL=1',
                   *[part for include in includes for part in ('-I', str(include))],
                   '-S', str(source), '-o', str(assembly)]
        compiled = subprocess.run(command, text=True, capture_output=True)
        if compiled.returncode:
            raise ValueError('Target ABI probe compile failed: ' + compiled.stderr.strip())
        sizes = {}
        current = None
        for line in assembly.read_text(encoding='ascii').splitlines():
            label = re.match(r'^_?aw_size_(\w+):\s*$', line.strip())
            if label:
                current = label.group(1)
                continue
            value = re.match(r'^\s*\.long\s+([0-9]+)\s*$', line)
            if current and re.match(r'^\s*\.(?:skip|space|zero)\s+4\s*$', line):
                sizes[current] = 0
                current = None
            if current and value:
                sizes[current] = int(value.group(1))
                current = None
    missing = sorted(set(PROBE_TYPES) - set(sizes))
    if missing or any(size <= 0 for key, size in sizes.items() if not key.startswith(('harvest_','edge_cache_'))):
        raise ValueError('Target ABI probe did not provide valid sizes: ' + ', '.join(missing))
    if (sizes.get('pointer'), sizes.get('short'), sizes.get('int'), sizes.get('hunk')) != (4, 2, 4, 16):
        raise ValueError('Unexpected Amiga ABI core sizes; refusing to estimate')
    from sprite_heap import sprite_loader_profile, efrag_pool_profile
    sprite_policy = sprite_loader_profile((ROOT / 'engine/aga/src/model.c').read_text(encoding='utf-8'))
    efrag_policy = efrag_pool_profile((ROOT / 'engine/aga/src/client.h').read_text(encoding='utf-8'))
    sizes['sprite_streaming'] = sprite_policy['sprite_streaming']
    slice_policy = bsp_slice_policy((ROOT / 'engine/aga/src/model.c').read_text(encoding='utf-8'))
    sizes['bsp_slice_bytes'] = slice_policy['slice_bytes']
    sizes['bsp_record_prefix_bytes'] = slice_policy['record_prefix_bytes']
    if not re.search(r'^#define\s+MAX_MAP_TEXTURES\s+512\b', (ROOT / 'engine/aga/src/bspfile.h').read_text(encoding='utf-8'), re.M):
        raise ValueError('Texture directory bound differs from the heap model')
    from alias_stream_heap import runtime_policy as alias_runtime_policy
    alias_policy=alias_runtime_policy(ROOT/'engine/aga/src')
    sizes['alias_streaming']=alias_policy['alias_streaming']
    from edge_cache_heap import runtime_policy as edge_runtime_policy
    edge_policy=edge_runtime_policy(ROOT/'engine/aga/src')
    sizes['edge_cache_split']=edge_policy['edge_cache_split']
    if sizes['medge']!=(4 if sizes['edge_cache_split'] else 8):raise ValueError('Packed-edge ABI differs from source policy')
    from compact_harvest_heap import runtime_policy,allocator_policy
    harvest_policy=runtime_policy(ROOT/'engine/aga')
    if (harvest_policy['mode']=='compact_offsets') != bool(sizes['harvest_storage_mode']):
        raise ValueError('Compiled harvest storage mode differs from recognized source policy')
    sizes['harvest_storage_policy_verified']=1
    allocator=allocator_policy(compiler) if sizes['harvest_storage_mode'] else {'mode':'not_required'}
    sizes['harvest_allocator_mode']=int(allocator['mode']=='newlib_memmap_1')
    compiler_version = subprocess.run([str(compiler), '--version'], text=True,
                                      capture_output=True, check=True).stdout.splitlines()[0]
    return sizes, {'compiler': str(compiler), 'compiler_version': compiler_version,
                   'flags': command[1:command.index('-S')], 'target': 'm68k-amigaos, 68040/FPU, GNU89',
                   'probe_sha256': hashlib.sha256(PROBE_SOURCE.encode('ascii')).hexdigest(),
                   'runtime_render_h_sha256': digest(ROOT / 'engine/aga/src/render.h'),
                   'runtime_model_h_sha256': digest(ROOT / 'engine/aga/src/model.h'),
                   'runtime_modelgen_h_sha256': digest(ROOT / 'engine/aga/src/modelgen.h'),
                   'runtime_quakedef_h_sha256': digest(ROOT / 'engine/aga/src/quakedef.h'),
                   'runtime_bspfile_h_sha256': digest(ROOT / 'engine/aga/src/bspfile.h'),
                   'runtime_model_c_sha256': digest(ROOT / 'engine/aga/src/model.c'),
                   'sprite_loader_policy': sprite_policy,
                   'bsp_section_policy': slice_policy,
                   'alias_loader_policy': alias_policy,
                   'edge_cache_policy': edge_policy,
                   'efrag_pool_policy': efrag_policy,
                   'harvest_storage_policy': harvest_policy,
                   'harvest_allocator_policy': allocator,
                   'runtime_client_h_sha256': digest(ROOT / 'engine/aga/src/client.h'),
                   'runtime_r_efrag_c_sha256': digest(ROOT / 'engine/aga/src/r_efrag.c'),
                   'runtime_cl_main_c_sha256': digest(ROOT / 'engine/aga/src/cl_main.c'),
                   'runtime_host_c_sha256': digest(ROOT / 'engine/aga/src/host.c'),
                   'runtime_zone_c_sha256': digest(ROOT / 'engine/aga/src/zone.c'),
                   'runtime_aw_section_h_sha256': digest(ROOT / 'engine/aga/src/aw_section.h'),
                   'runtime_aw_section_c_sha256': digest(ROOT / 'engine/aga/src/aw_section.c'),
                   'runtime_aw_harvest_h_sha256': digest(ROOT / 'engine/aga/src/aw_harvest.h'),
                   'runtime_aw_harvest_proxy_c_sha256': digest(ROOT / 'engine/aga/src/aw_harvest_proxy.c')
                       if (ROOT / 'engine/aga/src/aw_harvest_proxy.c').is_file() else None}


def lump_table(raw, path):
    if len(raw) < HEADER_SIZE:
        raise ValueError(f'{path}: truncated BSP29 header')
    version = struct.unpack_from('<i', raw, 0)[0]
    if version != BSP_VERSION:
        raise ValueError(f'{path}: BSP version {version}, expected {BSP_VERSION}')
    result = {}
    for name, (index, _, _) in RECORDS.items():
        offset, length = struct.unpack_from('<ii', raw, 4 + index * 8)
        if offset < HEADER_SIZE or length < 0 or offset > len(raw) or length > len(raw) - offset:
            if length == 0 and offset == 0:
                result[name] = b''
                continue
            raise ValueError(f'{path}: invalid {name} lump bounds')
        result[name] = raw[offset:offset + length]
    return result


def record_count(data, label, disk_size, path):
    if disk_size <= 0 or len(data) % disk_size:
        raise ValueError(f'{path}: {label} lump length is not a target disk-record multiple')
    return len(data) // disk_size


def texture_allocations(data, sizes, path):
    if not data:
        return 0, 0, 0
    if len(data) < 4:
        raise ValueError(f'{path}: truncated texture directory')
    count = struct.unpack_from('<i', data, 0)[0]
    if count < 0 or count > 512 or 4 + count * 4 > len(data):
        raise ValueError(f'{path}: invalid texture directory count')
    allocations = [hunk_alloc_bytes(count * sizes['pointer'], sizes['hunk'])]
    present = 0
    for i in range(count):
        offset = struct.unpack_from('<i', data, 4 + i * 4)[0]
        if offset == -1:
            continue
        if offset < 4 + count * 4 or offset + 40 > len(data):
            raise ValueError(f'{path}: invalid miptex offset {i}')
        width, height = struct.unpack_from('<II', data, offset + 16)
        if not width or not height or width & 15 or height & 15:
            raise ValueError(f'{path}: invalid miptex dimensions {i}')
        pixel_bytes = width * height // 64 * 85
        if offset + 40 + pixel_bytes > len(data):
            raise ValueError(f'{path}: truncated miptex payload {i}')
        allocations.append(hunk_alloc_bytes(sizes['texture'] + pixel_bytes, sizes['hunk']))
        present += 1
    return sum(allocations), len(allocations), present


def runtime_node_policy(lumps):
    """Mirror AW_RenderNodePrefix's strict forward-order fast path.

    This memory estimate is not a geometry validator. Malformed or unsupported
    records receive the full generic estimate, never optimistic node savings.
    The native loader separately rejects invalid ranges before making pointers.
    """
    nodes = list(struct.iter_unpack('<i2h6h2H', lumps['nodes']))
    models = list(struct.iter_unpack('<9f7i', lumps['models']))
    count = len(nodes)
    result = {'disk_nodes': count, 'render_nodes': count, 'direct_hull0': False,
              'external_scratch_bytes': 0, 'reason': 'generic node representation'}
    if not 0 < count <= 32767 or len(models) < 2 or models[0][9] != 0:
        return result
    leaf_count = len(lumps['leafs'])//28
    plane_count = len(lumps['planes'])//20
    face_count = len(lumps['faces'])//20
    for node in nodes:
        if not 0 <= node[0] < plane_count or node[9]+node[10] > face_count:
            result['reason'] = 'invalid node fields; no optimization credit'
            return result
        if any(child >= count or child < -leaf_count for child in node[1:3]):
            result['reason'] = 'invalid node child; no optimization credit'
            return result
    if any(model[9] >= count or model[9] < -leaf_count for model in models):
        result['reason'] = 'invalid model root; no optimization credit'
        return result
    result['external_scratch_bytes'] = (count+7)//8
    seen = {0}
    index = last = 0
    while index <= last:
        if index not in seen:
            return result
        for child in nodes[index][1:3]:
            if child < 0:
                continue
            if child <= index or child in seen:
                return result
            seen.add(child)
            last = max(last, child)
        index += 1
    world = last+1
    if world == count:
        return result
    seen = set()
    for model in models[1:]:
        root = model[9]
        if root < 0:
            continue
        if root < world:
            return result
        seen.add(root)
    for index in range(world, count):
        if index not in seen or nodes[index][10]:
            return result
        for child in nodes[index][1:3]:
            if child < 0:
                continue
            if child <= index:
                return result
            seen.add(child)
    result.update(render_nodes=world, direct_hull0=True,
                  reason='certified world prefix plus inline collision-only tail')
    return result


def predicted_render_prefix(lumps):
    """Mirror AW_PredictRenderPrefix: the world prefix the streamed node loader
    tries before certification, or 0. The lowest inline point root ends a
    valid prefix; when certification then fails, the attempt (all hull0 nodes
    plus the predicted prefix) was resident before the legacy arrays."""
    count = len(lumps['nodes']) // 24
    models = list(struct.iter_unpack('<9f7i', lumps['models']))
    if len(models) < 2 or models[0][9] != 0:
        return 0
    roots = [model[9] for model in models[1:] if model[9] >= 0]
    world = min(roots + [count])
    return world if 0 < world < count else 0


def estimate_bsp(path, sizes):
    path = Path(path)
    raw = path.read_bytes()
    lumps = lump_table(raw, path)
    counts = {}
    for name, (_, disk_type, _) in RECORDS.items():
        if disk_type:
            counts[name] = record_count(lumps[name], name, sizes[disk_type], path)
    node_policy = runtime_node_policy(lumps)
    direct_hull0 = node_policy['direct_hull0']
    pointer = sizes['pointer']
    hunk = sizes['hunk']
    slice_bytes = sizes.get('bsp_slice_bytes', BSP_SLICE_BYTES)
    record_prefix = sizes.get('bsp_record_prefix_bytes', BSP_RECORD_PREFIX_BYTES)
    attempt = predicted_render_prefix(lumps) if not direct_hull0 else 0
    node_policy['failed_prefix_attempt_nodes'] = attempt
    resident = 0
    resident_breakdown = []
    peak_total = 0
    peak_lump = None
    resident_at_peak = 0
    temp_at_peak = 0
    temp_peak = 0
    temp_lump = None
    fallback_resident = 0
    fallback_peak = 0

    def add(label, payload):
        nonlocal resident
        amount = hunk_alloc_bytes(payload, hunk)
        resident += amount
        resident_breakdown.append({'allocation': label, 'payload_bytes': payload,
                                   'hunk_bytes': amount, 'resident_after_bytes': resident})

    for name in LOAD_ORDER:
        before = resident
        lump = lumps[name]
        temp = 0 if name in DIRECT_BYTE_LUMPS | DIRECT_IN_PLACE_LUMPS else slice_temp_bytes(len(lump), hunk, slice_bytes,
                                                       slice_prefix_bytes(name, len(lump), record_prefix))
        if temp > temp_peak:
            temp_peak, temp_lump = temp, name
        if name == 'vertexes':
            add(name, counts[name] * sizes['mvertex'])
        elif name == 'edges':
            add(name, (counts[name] + 1) * sizes['medge'])
        elif name == 'surfedges':
            add(name, counts[name] * 4)
        elif name == 'textures':
            if lump:
                amount, nalloc, present = texture_allocations(lump, sizes, path)
                resident += amount
                resident_breakdown.append({'allocation': 'textures (pointer array and pixels)',
                    'hunk_bytes': amount, 'allocations': nalloc, 'present_textures': present,
                    'resident_after_bytes': resident})
        elif name in ('lighting', 'visibility', 'entities'):
            if lump: add(name + ' (direct byte load)', len(lump))
        elif name == 'nodes' and direct_hull0:
            # Both allocations coexist with the node lump's decode slice.
            add('hull0 clipnodes (direct disk)', counts[name] * sizes['clipnode'])
            add('nodes (world render prefix)', node_policy['render_nodes'] * sizes['mnode'])
        elif name in ('planes', 'texinfo', 'faces', 'leafs', 'nodes', 'clipnodes', 'models'):
            add(name, counts[name] * sizes[RECORDS[name][2]])
        elif name == 'marksurfaces':
            add(name, counts[name] * pointer)
        # Optional classifier calloc failure keeps the full legacy node array.
        # Track that bound separately; it is not the selected normal load path.
        fallback_resident += (hunk_alloc_bytes(counts['nodes'] * sizes['mnode'], hunk)
                              if name == 'nodes' and direct_hull0 else resident-before)
        fallback_peak = max(fallback_peak, fallback_resident + temp)
        section_peak = resident + temp
        if name == 'nodes' and attempt:
            # A failed prefix certification is released before the legacy arrays.
            section_peak = max(section_peak, before + temp +
                               hunk_alloc_bytes(counts[name] * sizes['clipnode'], hunk) +
                               hunk_alloc_bytes(attempt * sizes['mnode'], hunk))
        if section_peak > peak_total:
            peak_total, peak_lump = section_peak, name
            resident_at_peak, temp_at_peak = resident, temp

    # Edge cache is allocated after every section, before generic hull0.
    edge_policy=None
    if sizes.get('edge_cache_split'):
        from edge_cache_heap import prefix
        edge_policy=prefix(lumps)
        if edge_policy['prefix_edges']:
            amount=hunk_alloc_bytes(edge_policy['prefix_edges']*sizes['int'],hunk)
            add('world edge cache prefix',edge_policy['prefix_edges']*sizes['int'])
            fallback_resident+=amount;fallback_peak=max(fallback_peak,fallback_resident)
    # Generic fallback still makes hull0 after all sections. The certified
    # prefix path already made ALL original-index hull0 nodes during node load.
    hull0_payload = counts.get('nodes', 0) * sizes['clipnode']
    hull0_bytes = hunk_alloc_bytes(hull0_payload, hunk)
    fallback_resident += hull0_bytes
    fallback_peak = max(fallback_peak, fallback_resident)
    if not direct_hull0:
        resident += hull0_bytes
        resident_breakdown.append({'allocation': 'hull0 clipnodes', 'payload_bytes': hull0_payload,
                                   'hunk_bytes': hull0_bytes, 'resident_after_bytes': resident})
    if resident > peak_total:
        peak_total, peak_lump = resident, 'post-load hull0'
        resident_at_peak, temp_at_peak = resident, 0
    # One streamed lump is high-resident at a time; every earlier low allocation remains resident.
    if peak_total < resident:
        peak_total = resident
    return {
        'map': path.name, 'path': str(path), 'file_bytes': len(raw),
        'loader_policy': 'validated renderer-prefix/direct-hull0, direct in-place clipnodes, '
                         'other sections decoded from bounded slices',
        'bsp_slice_bytes': slice_bytes, 'bsp_record_prefix_bytes': record_prefix,
        'direct_in_place_sections': sorted(DIRECT_IN_PLACE_LUMPS),
        'node_residency': node_policy,
        'edge_cache_residency': edge_policy,
        'external_classifier_scratch_bytes': node_policy['external_scratch_bytes'],
        'classifier_allocation_failure_fallback_peak_bytes': fallback_peak,
        'file_sha256': hashlib.sha256(raw).hexdigest(), 'counts': counts,
        'resident_loader_bytes': resident, 'peak_loader_bytes': peak_total,
        'resident_bytes_at_peak': resident_at_peak,
        'temporary_input_bytes_at_peak': temp_at_peak,
        'temporary_input_peak_bytes': temp_peak, 'temporary_input_peak_lump': temp_lump,
        'peak_section': peak_lump, 'resident_allocations': resident_breakdown,
    }


def heap_capacity(heap_mb=None):
    """The heap the maps must fit: the build's own size (the engine receipt's heap_mb, from --heap-mb)
    when given, else the engine source's AMIWIND_HEAP_MB."""
    source = ROOT / 'engine/aga/src/sys_amiga.c'
    text = source.read_text(encoding='utf-8')
    match = re.search(r'^#define\s+AMIWIND_HEAP_MB\s+(\d+)\s*$', text, re.M)
    if not match:
        raise ValueError('Could not find literal AMIWIND_HEAP_MB in sys_amiga.c')
    megabytes = int(match.group(1)) if heap_mb is None else int(heap_mb)
    return megabytes * 1024 * 1024, {'source': str(source), 'source_sha256': digest(source),
                                     'heap_megabytes': megabytes,
                                     'selected_by': 'engine source' if heap_mb is None else 'engine build receipt'}


def _map_reports(task):
    """Worker: complete heap rows for a chunk of maps (independent per map)."""
    paths, sizes, guards, harvest, efrag_policy, baseline_reserve_bytes, safety_headroom_bytes, budget = task
    from guard_torch_heap import map_cost as guard_cost, apply as apply_guard_cost
    from harvest_heap import apply as apply_harvest_cost
    from sprite_heap import inspect_sprites, inspect_efrags
    from scenery_admission import catalogue_count
    reports = []
    for path in map(Path, paths):
        report = estimate_bsp(path, sizes)
        raw = path.read_bytes()
        table = lump_table(raw, path)
        entity_bytes = table['entities']
        sprites = inspect_sprites(entity_bytes, path.parent.parent, sizes)
        captured = catalogue_count(path.stem, entity_bytes)
        catalogue_bytes = hunk_alloc_bytes(captured * sizes['scenery'], sizes['hunk']) if captured else 0
        report['scenery_catalogue'] = {'placements':captured,'hunk_bytes':catalogue_bytes,
                                      'target_record_bytes':sizes.get('scenery'),
                                      'live_edicts_released':captured,
                                      'acceptance':'source allocation model; not measured live count'}
        # Conservative overlap bound: retain catalogue through every map/model
        # loading peak, including sprite input. Never subtract BSP allocations.
        report['resident_loader_bytes'] += catalogue_bytes
        report['peak_loader_bytes'] += catalogue_bytes
        report['resident_bytes_at_peak'] += catalogue_bytes
        report['classifier_allocation_failure_fallback_peak_bytes'] += catalogue_bytes
        report['sprites'] = sprites
        report['bsp_peak_loader_bytes'] = report['peak_loader_bytes']
        if sprites['unique_sprite_models']:
            sprite_peak = report['resident_loader_bytes'] + sprites['resident_hunk_bytes'] + sprites['temporary_input_peak_bytes']
            report['resident_loader_bytes'] += sprites['resident_hunk_bytes']
            if sprite_peak > report['peak_loader_bytes']:
                report['peak_loader_bytes'] = sprite_peak
                report['peak_section'] = 'sprite model load'
                report['resident_bytes_at_peak'] = report['resident_loader_bytes']
                report['temporary_input_bytes_at_peak'] = sprites['temporary_input_peak_bytes']
            report['classifier_allocation_failure_fallback_peak_bytes'] = max(
                report['classifier_allocation_failure_fallback_peak_bytes'], sprite_peak)
        efrags=inspect_efrags(table,sprites,sizes,efrag_policy)
        report['efrags']=efrags
        report['resident_loader_bytes']+=efrags['resident_hunk_bytes']
        if report['resident_loader_bytes']>report['peak_loader_bytes']:
            report['peak_loader_bytes']=report['resident_loader_bytes']
            report['peak_section']='static entity leaf links'
            report['resident_bytes_at_peak']=report['resident_loader_bytes']
            report['temporary_input_bytes_at_peak']=0
        report['classifier_allocation_failure_fallback_peak_bytes']=max(
            report['classifier_allocation_failure_fallback_peak_bytes']+efrags['resident_hunk_bytes'],
            report['resident_loader_bytes'])
        apply_guard_cost(report,guard_cost(entity_bytes,guards))
        apply_harvest_cost(report,harvest)
        # The section directory lives in static Fast RAM for every map.
        # Debit it even when this particular map has no section catalogue.
        section_static=sizes.get("interior_section_static",0)
        report["interior_section_static_allowance_bytes"]=section_static
        report["additional_static_allowance_bytes"]+=section_static
        edge_static=sizes.get('edge_cache_static',0)
        report['edge_cache_static_allowance_bytes']=edge_static
        report['additional_static_allowance_bytes']+=edge_static
        required = (report['peak_loader_bytes'] + baseline_reserve_bytes + safety_headroom_bytes +
                    report['additional_static_allowance_bytes']+
                    report['additional_external_allocation_allowance_bytes'])
        report.update(baseline_reserve_bytes=baseline_reserve_bytes,
                      safety_headroom_bytes=safety_headroom_bytes,
                      estimated_total_bytes=required,
                      estimated_clearance_bytes=budget - required,
                      gate='pass' if required <= budget else 'fail')
        reports.append(report)
    return reports


def inspect_maps(maps, sizes, baseline_reserve_bytes=BASELINE_RESERVE_BYTES,
                 safety_headroom_bytes=SAFETY_HEADROOM_BYTES, jobs=1, only=None, heap_mb=None):
    # only: map names (no .bsp) to estimate, e.g. harvest admission candidates.
    if baseline_reserve_bytes <= 0:
        raise ValueError('Baseline reserve must be positive')
    if safety_headroom_bytes <= 0:
        raise ValueError('Safety headroom must be positive')
    maps = Path(maps)
    candidates = sorted(p for p in maps.glob('*.bsp') if p.is_file() and (only is None or p.stem in only))
    if not candidates:
        raise ValueError(f'No BSP maps found in {maps}')
    budget, budget_source = heap_capacity(heap_mb)
    from guard_torch_heap import profile as guard_profile
    guards=guard_profile(maps.parent,sizes)
    from harvest_heap import profile as harvest_profile
    harvest=harvest_profile(maps.parent,sizes)
    from sprite_heap import efrag_pool_profile
    efrag_policy=efrag_pool_profile((ROOT/'engine/aga/src/client.h').read_text(encoding='utf-8'))
    # Every map's estimate is independent: chunks run in up to `jobs` workers
    # (shared pool, tools/build_parallel.py); rows keep sorted map order.
    from build_parallel import ordered_map
    size = max(1, -(-len(candidates) // (4 * max(1, jobs))))
    chunks = [[str(p) for p in candidates[i:i + size]] for i in range(0, len(candidates), size)]
    reports = [row for rows in ordered_map(_map_reports, [
        (chunk, sizes, guards, harvest, efrag_policy, baseline_reserve_bytes, safety_headroom_bytes, budget)
        for chunk in chunks], max(1, min(jobs, len(chunks)))) for row in rows]
    worst = max(reports, key=lambda row: row['estimated_total_bytes'])
    return {'format': 'AmiWind target BSP heap estimate 1',
            'acceptance': 'estimate-only; not target or gameplay validation',
            'heap_budget_bytes': budget, 'heap_budget_source': budget_source,
            'baseline_reserve_bytes': baseline_reserve_bytes,
            'safety_headroom_bytes': safety_headroom_bytes,
            'map_count': len(reports), 'passing_maps': sum(r['gate'] == 'pass' for r in reports),
            'failing_maps': [r['map'] for r in reports if r['gate'] == 'fail'],
            'worst_map': worst['map'], 'worst_estimated_total_bytes': worst['estimated_total_bytes'],
            'minimum_estimated_clearance_bytes': min(r['estimated_clearance_bytes'] for r in reports),
            'target_struct_sizes_bytes': sizes, 'guard_torch_profile': guards,
            'harvest_external_profile': harvest, 'maps': reports}


def audit_world_maps(maps, sdk, out, baseline_reserve_bytes=BASELINE_RESERVE_BYTES,
                     safety_headroom_bytes=SAFETY_HEADROOM_BYTES, jobs=1, heap_mb=None):
    sizes, abi = compile_target_sizes(sdk)
    report = inspect_maps(maps, sizes, baseline_reserve_bytes, safety_headroom_bytes, jobs=jobs, heap_mb=heap_mb)
    report['target_abi_probe'] = abi
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maps', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline-reserve-bytes', type=int, default=BASELINE_RESERVE_BYTES)
    parser.add_argument('--safety-headroom-bytes', type=int, default=SAFETY_HEADROOM_BYTES)
    parser.add_argument('--heap-mb', type=int, help="The build's heap in MiB (default: the engine source's)")
    args = parser.parse_args()
    report = audit_world_maps(args.maps, args.sdk, args.out,
                              args.baseline_reserve_bytes, args.safety_headroom_bytes, heap_mb=args.heap_mb)
    print(f"BSP heap estimate: {report['passing_maps']}/{report['map_count']} maps clear "
          f"{report['heap_budget_source']['heap_megabytes']} MiB with {args.baseline_reserve_bytes} baseline + {args.safety_headroom_bytes} safety bytes; "
          f"worst={report['worst_map']} estimated={report['worst_estimated_total_bytes']}; "
          f"report={args.out}", flush=True)
    if report['failing_maps']:
        raise SystemExit('World map heap clearance gate failed: ' + ', '.join(report['failing_maps']))


if __name__ == '__main__':
    main()
