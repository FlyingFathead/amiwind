#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Face validator for BSP29 maps: every face of every model, as the engine reads it.

Checks, per face (docs/FACE_VALIDATION.md):

  structure  plane, texinfo, edge-span, surfedge, edge-vertex and miptex index
             ranges as `engine/aga/src/model.c` reads them; the edge loop must
             close; edge 0 must not be used (the extent code and the renderer
             read it in opposite directions); plane normals unit length and
             axial plane types pointing along +axis.
  geometry   planarity (largest vertex distance from the stored plane), plane
             tilt (stored normal against the polygon's own Newell normal),
             side (winding against the plane side flag: Quake faces are
             clockwise seen from the front, r_draw.c leading/trailing edges),
             degenerate faces (fewer than three distinct vertices, zero area,
             slivers, zero-length edges) and convexity (the edge-sorted span
             renderer draws one span per surface and scan line).
  extents    the engine's CalcSurfaceExtents rule (`tools/surface_grid.py`)
             against the 256-texel limit; the single-precision and extended
             rules are reported where they exceed it or change the grid.
  texcoords  texture minima and extents stored in the engine's 16-bit fields.
  lightmaps  offset and size by the engine rule inside the lighting lump and
             not into the next face's samples.

The report is JSON: per-check counts, worst cases and a per-model breakdown.
Checks are `fail`, `warn` or `off`; metric checks have a warn and a fail
threshold. The exit code is 1 when any `fail` check has failing faces and 2
when a map cannot be read. Read-only; never edits a map.
"""
import argparse
from dataclasses import dataclass, field, replace
import heapq
import json
from pathlib import Path
import re
import struct
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from surface_grid import MAX_EXTENT  # noqa: E402  (the engine's 256-texel limit)

LUMP_COUNT = 15
ENTITIES, PLANES, TEXTURES, VERTEXES, VISIBILITY, NODES, TEXINFO, FACES, LIGHTING, \
    CLIPNODES, LEAFS, MARKSURFACES, EDGES, SURFEDGES, MODELS = range(LUMP_COUNT)

FACE_DT = np.dtype([('plane', '<u2'), ('side', '<i2'), ('firstedge', '<i4'), ('numedges', '<i2'),
                    ('texinfo', '<u2'), ('styles', 'u1', 4), ('lightofs', '<i4')])
PLANE_DT = np.dtype([('normal', '<f4', 3), ('dist', '<f4'), ('type', '<i4')])
TEXINFO_DT = np.dtype([('vecs', '<f4', (2, 4)), ('miptex', '<i4'), ('flags', '<i4')])
MODEL_DT = np.dtype([('mins', '<f4', 3), ('maxs', '<f4', 3), ('origin', '<f4', 3),
                     ('headnode', '<i4', 4), ('visleafs', '<i4'), ('firstface', '<i4'),
                     ('numfaces', '<i4')])
NODE_DT = np.dtype([('plane', '<i4'), ('children', '<i2', 2), ('mins', '<i2', 3),
                    ('maxs', '<i2', 3), ('firstface', '<u2'), ('numfaces', '<u2')])
LEAF_DT = np.dtype([('contents', '<i4'), ('visofs', '<i4'), ('mins', '<i2', 3), ('maxs', '<i2', 3),
                    ('firstmark', '<u2'), ('nummarks', '<u2'), ('ambient', 'u1', 4)])

TEX_SPECIAL = 1        # texinfo flag: sky/water, no lightmap, no extent limit (model.c)
SHORT_MIN, SHORT_MAX = -32768, 32767  # msurface_t texturemins/extents are shorts (model.h)

# --- thresholds -----------------------------------------------------------
# Stored vertices are binary32. Map coordinates stay within +-32768 units, where
# one float32 step is at most 2**-8 (0.004) units, so storage alone moves a
# vertex off an exact plane by under 0.004 units (the plane is stored the
# same way). WARN at 0.02 is five storage steps; it also catches the known
# 0.05-unit bend of rounded coplanar grouping (CONVERT-MERGE-NONPLANAR-32).
PLANARITY_WARN = 0.02
# FAIL at 0.25 units: the renderer's 1/z gradients and backface test come
# from the stored plane, so a vertex a quarter unit off already shifts depth
# sorting and perspective texture mapping visibly at close range; qbsp-class
# compilers keep faces within 0.1 (ON_EPSILON) of their plane.
PLANARITY_FAIL = 0.25
# Tilt of the stored normal against the polygon's own Newell normal, degrees.
# Rounding normals to 4 decimals (the converter's grouping key) tilts them by
# under 0.01 degree; 0.5 degree is fifty times that. 5 degrees is a visibly
# wrong plane (the measured Khuul faces are 29 degrees off).
TILT_WARN_DEG = 0.5
TILT_FAIL_DEG = 5.0
# Faces below this area (square units) have no stable normal: orientation and
# convexity are not judged, the face is reported as degenerate instead.
MIN_FACE_AREA = 1e-3
# Width (2 * area / longest chord) below which a face is a sliver: thinner
# than a hundredth of a unit, it never covers a pixel centre at any distance
# the player can reach and its normal is dominated by float32 noise.
SLIVER_WIDTH = 0.01
# Edges shorter than this (units) count as zero length: a repeated vertex.
ZERO_EDGE_LENGTH = 1e-3
# Reflex depth (units a vertex lies inside the chord of its neighbours). The
# span renderer assumes one leading and one trailing edge per scan line;
# 0.01 is float noise level for merged polygons with collinear runs, 0.5 units
# is several pixels at close range.
CONVEX_WARN = 0.01
CONVEX_FAIL = 0.5
# Plane normal length error. Stored binary32 unit vectors are within 1e-6.
NORMAL_LENGTH_WARN = 1e-4
NORMAL_LENGTH_FAIL = 1e-2
# Axial plane types (0-2) make the engine use dist and the coordinate directly
# (BOX_ON_PLANE_SIDE, R_RecursiveWorldNode); the normal must be +axis.
AXIAL_TOLERANCE = 1e-6
# Texture coordinates: the 16-bit fields hold texturemins and extents; warn
# within 1/16 of the edge (2048 texels: room for a 256-texel surface and
# mipmap shifts), fail outside.
TEXCOORD_WARN = SHORT_MAX - 2048

WORST_CASES = 10


@dataclass(frozen=True)
class Check:
    group: str
    kind: str            # 'metric' (value vs thresholds) or 'flag'
    severity: str        # 'fail', 'warn' or 'off'
    unit: str
    description: str
    warn: float = 0.0
    fail: float = 0.0


CHECKS = {
    # (g) index ranges and structure
    'face_plane_index': Check('structure', 'flag', 'fail', 'index', 'face plane index outside plane lump'),
    'face_texinfo_index': Check('structure', 'flag', 'fail', 'index', 'face texinfo index outside texinfo lump'),
    'face_edge_range': Check('structure', 'flag', 'fail', 'index', 'face firstedge/numedges outside surfedge lump'),
    'surfedge_index': Check('structure', 'flag', 'fail', 'index', 'face surfedge outside edge lump'),
    'edge_vertex_index': Check('structure', 'flag', 'fail', 'index', 'face edge vertex outside vertex lump'),
    'texinfo_miptex_index': Check('structure', 'flag', 'fail', 'index', 'face texinfo miptex outside texture table'),
    'edge_zero_used': Check('structure', 'flag', 'fail', 'count',
                            'face uses edge 0 (extents read it forward, the renderer backward)'),
    'edge_loop_open': Check('structure', 'flag', 'fail', 'count', 'consecutive face edges do not share a vertex'),
    'face_unowned': Check('structure', 'flag', 'warn', 'count', 'face belongs to no model'),
    'face_multiple_models': Check('structure', 'flag', 'warn', 'count',
                                  'face in partly overlapping model face ranges (identical ranges are instances)'),
    'model_face_range': Check('structure', 'flag', 'fail', 'model', 'model face range outside face lump'),
    'node_face_range': Check('structure', 'flag', 'fail', 'node', 'node face range outside face lump'),
    'marksurface_index': Check('structure', 'flag', 'fail', 'mark', 'marksurface outside face lump'),
    'leaf_mark_range': Check('structure', 'flag', 'fail', 'leaf', 'leaf marksurface range outside lump'),
    'plane_normal': Check('structure', 'metric', 'fail', 'length error', 'plane normal not unit length',
                          NORMAL_LENGTH_WARN, NORMAL_LENGTH_FAIL),
    'plane_type': Check('structure', 'flag', 'fail', 'plane',
                        'plane type invalid, or axial type whose normal is not +axis'),
    # (a)-(c) geometry
    'planarity': Check('geometry', 'metric', 'fail', 'units', 'largest vertex distance from the stored plane',
                       PLANARITY_WARN, PLANARITY_FAIL),
    'plane_tilt': Check('geometry', 'metric', 'fail', 'degrees',
                        'angle between stored plane normal and polygon Newell normal', TILT_WARN_DEG, TILT_FAIL_DEG),
    'plane_side': Check('geometry', 'flag', 'fail', 'count',
                        'winding faces the other way than the plane side flag says'),
    'degenerate_vertices': Check('geometry', 'flag', 'fail', 'vertices', 'fewer than 3 distinct vertices'),
    'degenerate_area': Check('geometry', 'flag', 'warn', 'square units', 'zero area (collinear or coincident)'),
    'degenerate_sliver': Check('geometry', 'flag', 'warn', 'units', 'sliver thinner than SLIVER_WIDTH'),
    'zero_length_edge': Check('geometry', 'flag', 'warn', 'edges', 'repeated consecutive vertex'),
    'nonconvex': Check('geometry', 'metric', 'fail', 'units', 'reflex vertex depth', CONVEX_WARN, CONVEX_FAIL),
    # (d) extents
    'extents_engine': Check('extents', 'flag', 'fail', 'texels', 'engine-rule extent above 256 texels'),
    'extents_target': Check('extents', 'flag', 'warn', 'texels',
                            'single-precision or extended rule extent above 256 texels'),
    'extents_rule_disagreement': Check('extents', 'flag', 'warn', 'count',
                                       'FPU rules give different texture minima or extents'),
    # (e) texture coordinates
    'texcoord_range': Check('texcoords', 'flag', 'fail', 'texels', 'texturemins or extents outside 16 bits'),
    'texcoord_margin': Check('texcoords', 'flag', 'warn', 'texels',
                             'texture coordinate within 2048 texels of the 16-bit edge'),
    # (f) lightmaps
    'lightmap_offset': Check('lightmaps', 'flag', 'fail', 'bytes', 'negative light offset other than -1'),
    'lightmap_outside_lump': Check('lightmaps', 'flag', 'fail', 'bytes',
                                   'engine-rule lightmap runs past the lighting lump'),
    'lightmap_overlap': Check('lightmaps', 'flag', 'fail', 'bytes',
                              "engine-rule lightmap runs into the next face's samples"),
    'lightmap_span_mismatch': Check('lightmaps', 'flag', 'warn', 'bytes',
                                    'stored block longer than the engine reads (bake grid differs)'),
    'lightmap_shared_size': Check('lightmaps', 'flag', 'warn', 'bytes',
                                  'faces sharing one light offset need different sizes'),
}
SEVERITIES = ('fail', 'warn', 'off')
# Arithmetic rules for texture coordinates: 'engine' is CalcSurfaceExtents now
# (double precision after every step); 'binary32' is single precision after
# every step, as engines before that rule compiled for the 68040 computed it;
# 'extended' keeps 68040 extended intermediates.
EXTENT_RULES = ('engine', 'binary32', 'extended')
# Checks whose worst cases are the smallest values.
LOW_IS_WORSE = {'degenerate_area', 'degenerate_sliver'}


def rank(check):
    return (lambda r: -r['value']) if check in LOW_IS_WORSE else (lambda r: r['value'])
FACE_LEVEL = {name for name, c in CHECKS.items()
              if name not in ('model_face_range', 'node_face_range', 'marksurface_index',
                              'leaf_mark_range', 'plane_normal', 'plane_type')}


@dataclass
class Config:
    checks: dict = field(default_factory=lambda: dict(CHECKS))
    worst: int = WORST_CASES
    extent_rule: str = 'engine'

    def set_severity(self, name, severity):
        if name not in self.checks:
            raise ValueError(f'Unknown check: {name}')
        if severity not in SEVERITIES:
            raise ValueError(f'Unknown severity: {severity}')
        self.checks[name] = replace(self.checks[name], severity=severity)

    def set_threshold(self, name, level, value):
        if name not in self.checks or self.checks[name].kind != 'metric':
            raise ValueError(f'Not a metric check: {name}')
        if level not in ('warn', 'fail'):
            raise ValueError(f'Threshold level must be warn or fail: {level}')
        self.checks[name] = replace(self.checks[name], **{level: float(value)})


class MapError(ValueError):
    """The map cannot be read as BSP29 at all."""


def split_lumps(raw):
    if len(raw) < 4+8*LUMP_COUNT:
        raise MapError('Truncated BSP header')
    if struct.unpack_from('<i', raw)[0] != 29:
        raise MapError('Expected BSP29')
    lumps = []
    for index in range(LUMP_COUNT):
        offset, size = struct.unpack_from('<ii', raw, 4+8*index)
        if offset < 0 or size < 0 or offset+size > len(raw):
            raise MapError(f'Lump {index} outside file')
        lumps.append(bytes(raw[offset:offset+size]))
    return lumps


def records(lump, dtype, index):
    if len(lump) % dtype.itemsize:
        raise MapError(f'Lump {index} length {len(lump)} not a multiple of {dtype.itemsize}')
    return np.frombuffer(lump, dtype=dtype)


def texture_names(lump):
    if len(lump) < 4:
        return []
    count = struct.unpack_from('<i', lump)[0]
    if count < 0 or 4+4*count > len(lump):
        return []
    names = []
    for i in range(count):
        start = struct.unpack_from('<i', lump, 4+4*i)[0]
        if start < 0 or start+16 > len(lump):
            names.append(None)
        else:
            names.append(lump[start:start+16].split(b'\0', 1)[0].decode('latin-1'))
    return names


def model_classnames(lump):
    """{model index: classname} from the entity text ("model" "*N")."""
    text = lump.split(b'\0', 1)[0].decode('latin-1', 'replace')
    result = {0: 'worldspawn'}
    for block in re.findall(r'\{([^{}]*)\}', text):
        keys = dict(re.findall(r'"([^"]*)"\s*"([^"]*)"', block))
        model = keys.get('model', '')
        if model.startswith('*') and model[1:].isdigit():
            result[int(model[1:])] = keys.get('classname', '?')
    return result


def face_vertex_layout(faces_ok, firstedge, numedges):
    """Flattened per-vertex indices for the selected faces."""
    counts = numedges[faces_ok].astype(np.int64)
    starts = np.zeros(len(counts), dtype=np.int64)
    if len(counts):
        starts[1:] = np.cumsum(counts)[:-1]
    total = int(counts.sum())
    owner = np.repeat(np.arange(len(counts)), counts)
    local = np.arange(total) - starts[owner] if total else np.zeros(0, dtype=np.int64)
    surf_index = firstedge[faces_ok].astype(np.int64)[owner] + local
    nxt = np.arange(total) + 1
    prv = np.arange(total) - 1
    if len(counts):
        ends = starts + counts - 1
        nonempty = counts > 0
        nxt[ends[nonempty]] = starts[nonempty]
        prv[starts[nonempty]] = ends[nonempty]
    return counts, starts, owner, surf_index, nxt, prv


def reduce_max(values, starts, counts, empty=0.0):
    out = np.full(len(counts), empty, dtype=np.result_type(values.dtype, np.float64))
    nonempty = counts > 0
    if values.size and nonempty.any():
        out[nonempty] = np.maximum.reduceat(values, starts[nonempty])
    return out


def reduce_min(values, starts, counts, empty=0.0):
    out = np.full(len(counts), empty, dtype=np.result_type(values.dtype, np.float64))
    nonempty = counts > 0
    if values.size and nonempty.any():
        out[nonempty] = np.minimum.reduceat(values, starts[nonempty])
    return out


def reduce_sum(values, starts, counts):
    shape = (len(counts),) + values.shape[1:]
    out = np.zeros(shape, dtype=np.float64)
    nonempty = counts > 0
    if values.size and nonempty.any():
        out[nonempty] = np.add.reduceat(values, starts[nonempty], axis=0)
    return out


def rule_uv(points32, vecs32, rule):
    """Per-vertex (s, t) under one arithmetic rule; inputs as stored (float32)."""
    if rule == 'binary32':
        p, v = points32, vecs32
        return [(((p[:, 0]*v[:, j, 0]) + (p[:, 1]*v[:, j, 1])) + (p[:, 2]*v[:, j, 2])) + v[:, j, 3]
                for j in range(2)]
    dtype = np.longdouble if rule == 'extended' else np.float64
    p, v = points32.astype(dtype), vecs32.astype(dtype)
    return [((p[:, 0]*v[:, j, 0] + p[:, 1]*v[:, j, 1]) + p[:, 2]*v[:, j, 2]) + v[:, j, 3] for j in range(2)]


def rule_grid(uv, starts, counts):
    """(texturemins (n,2), extents (n,2)) as CalcSurfaceExtents computes them."""
    mins = np.zeros((len(counts), 2), dtype=np.int64)
    extents = np.zeros((len(counts), 2), dtype=np.int64)
    for j in range(2):
        # Round in the coordinates' own precision (extended stays extended).
        low = np.floor(np.minimum(999999., reduce_min(uv[j], starts, counts, 999999.))/16)
        high = np.ceil(np.maximum(-99999., reduce_max(uv[j], starts, counts, -99999.))/16)
        mins[:, j] = low.astype(np.int64)*16
        extents[:, j] = np.maximum(16, (high-low).astype(np.int64)*16)
    return mins, extents


class Collector:
    """Per-check counts, worst cases and per-model counts for one map."""

    def __init__(self, config, name, models_of_face, classnames, textures_of_face, numedges):
        self.config, self.name = config, name
        self.models_of_face, self.classnames = models_of_face, classnames
        self.textures_of_face, self.numedges = textures_of_face, numedges
        self.results = {}
        self.per_model = {}

    def add(self, check, faces, values=None, failing=None, extra=None):
        """Record flagged faces (indices into the face lump)."""
        spec = self.config.checks[check]
        faces = np.asarray(faces, dtype=np.int64)
        values = np.zeros(len(faces)) if values is None else np.asarray(values, dtype=np.float64)
        if failing is None:
            failing = np.ones(len(faces), dtype=bool)
        result = self.results.setdefault(check, {'flagged': 0, 'failing': 0, 'worst': []})
        result['flagged'] += int(len(faces))
        result['failing'] += int(np.count_nonzero(failing))
        if spec.kind == 'metric' or values.any():
            order = np.argsort(values if check in LOW_IS_WORSE else -values, kind='stable')[:self.config.worst]
        else:
            order = np.arange(min(len(faces), self.config.worst))
        for i in order:
            face = int(faces[i])
            row = {'map': self.name, 'face': face, 'value': float(values[i])}
            if check in FACE_LEVEL:
                model = int(self.models_of_face[face]) if 0 <= face < len(self.models_of_face) else -1
                row.update(model=model, classname=self.classnames.get(model),
                           texture=self.textures_of_face(face),
                           vertices=int(self.numedges[face]) if 0 <= face < len(self.numedges) else None)
            if extra is not None:
                row.update({k: (v[i].tolist() if hasattr(v[i], 'tolist') else v[i]) for k, v in extra.items()})
            result['worst'].append(row)
        result['worst'] = heapq.nlargest(self.config.worst, result['worst'], key=rank(check)) \
            if spec.kind == 'metric' or values.any() else result['worst'][:self.config.worst]
        if check in FACE_LEVEL and len(faces):
            models = self.models_of_face[faces]
            for model, count in zip(*np.unique(models, return_counts=True)):
                entry = self.per_model.setdefault(int(model), {})
                entry[check] = entry.get(check, 0) + int(count)


def check_bsp(raw, name='map', config=None):
    """Validate every face of a BSP29 map; returns the per-map report."""
    config = config or Config()
    lumps = split_lumps(raw)
    planes = records(lumps[PLANES], PLANE_DT, PLANES)
    vertices = records(lumps[VERTEXES], np.dtype(('<f4', 3)), VERTEXES)
    texinfo = records(lumps[TEXINFO], TEXINFO_DT, TEXINFO)
    faces = records(lumps[FACES], FACE_DT, FACES)
    edges = records(lumps[EDGES], np.dtype(('<u2', 2)), EDGES)
    surfedges = records(lumps[SURFEDGES], np.dtype('<i4'), SURFEDGES)
    models = records(lumps[MODELS], MODEL_DT, MODELS)
    nodes = records(lumps[NODES], NODE_DT, NODES)
    leafs = records(lumps[LEAFS], LEAF_DT, LEAFS)
    marks = records(lumps[MARKSURFACES], np.dtype('<u2'), MARKSURFACES)
    names = texture_names(lumps[TEXTURES])
    classnames = model_classnames(lumps[ENTITIES])
    nfaces = len(faces)

    # Model ownership (model.c: dmodel firstface/numfaces).
    owner_count = np.zeros(nfaces, dtype=np.int64)
    models_of_face = np.full(nfaces, -1, dtype=np.int64)
    bad_models = []
    seen_ranges = set()
    instanced = 0
    for index, model in enumerate(models):
        first, count = int(model['firstface']), int(model['numfaces'])
        if first < 0 or count < 0 or first+count > nfaces:
            bad_models.append(index)
            continue
        # Models with an identical face range are instances of one geometry
        # (shared on purpose); only partly overlapping ranges are suspect.
        if (first, count) in seen_ranges:
            instanced += 1
            continue
        seen_ranges.add((first, count))
        part = slice(first, first+count)
        unset = models_of_face[part] < 0
        models_of_face[part][unset] = index
        owner_count[part] += 1

    def texture_of_face(face):
        info = int(faces['texinfo'][face])
        if info >= len(texinfo):
            return None
        miptex = int(texinfo['miptex'][info])
        return names[miptex] if 0 <= miptex < len(names) else None

    out = Collector(config, name, models_of_face, classnames, texture_of_face, faces['numedges'])
    if bad_models:
        out.add('model_face_range', bad_models)

    # Map-level structure.
    if len(nodes):
        bad = np.flatnonzero(nodes['firstface'].astype(np.int64)+nodes['numfaces'] > nfaces)
        if len(bad):
            out.add('node_face_range', bad)
    bad = np.flatnonzero(marks >= nfaces)
    if len(bad):
        out.add('marksurface_index', bad)
    if len(leafs):
        bad = np.flatnonzero(leafs['firstmark'].astype(np.int64)+leafs['nummarks'] > len(marks))
        if len(bad):
            out.add('leaf_mark_range', bad)
    normals = planes['normal'].astype(np.float64)
    length_error = np.abs(np.linalg.norm(normals, axis=1)-1) if len(planes) else np.zeros(0)
    spec = config.checks['plane_normal']
    bad = np.flatnonzero(length_error > spec.warn)
    if len(bad):
        out.add('plane_normal', bad, length_error[bad], length_error[bad] > spec.fail)
    ptype = planes['type']
    axial = ptype < 3
    safe_type = np.clip(ptype, 0, 2)
    along = normals[np.arange(len(planes)), safe_type] if len(planes) else np.zeros(0)
    off_axis = np.abs(normals).sum(axis=1)-np.abs(along) if len(planes) else np.zeros(0)
    bad_type = (ptype < 0) | (ptype > 5) | (axial & ((along < 1-AXIAL_TOLERANCE) | (off_axis > AXIAL_TOLERANCE)))
    bad = np.flatnonzero(bad_type)
    if len(bad):
        out.add('plane_type', bad, extra={'type': ptype[bad], 'normal': normals[bad]})

    if not len(faces):
        return finish(out, name, nfaces, models, 0, 0, instanced)

    # Face index ranges (model.c Mod_LoadFaces/Mod_LoadTexinfo/Mod_LoadSurfedges).
    face_ids = np.arange(nfaces)
    ok_plane = faces['plane'] < len(planes)
    ok_texinfo = faces['texinfo'] < len(texinfo)
    firstedge = faces['firstedge'].astype(np.int64)
    numedges = faces['numedges'].astype(np.int64)
    ok_range = (firstedge >= 0) & (numedges >= 0) & (firstedge+numedges <= len(surfedges))
    for check, ok in (('face_plane_index', ok_plane), ('face_texinfo_index', ok_texinfo),
                      ('face_edge_range', ok_range)):
        if not ok.all():
            out.add(check, face_ids[~ok])
    # Mod_LoadTexinfo: miptex >= numtextures stops the load when the map has
    # a texture lump; without one every face gets the checkerboard.
    miptex_ok = np.ones(nfaces, dtype=bool)
    if lumps[TEXTURES]:
        miptex = texinfo['miptex'][faces['texinfo'][ok_texinfo]]
        miptex_ok[ok_texinfo] = (miptex >= 0) & (miptex < len(names))
    bad = face_ids[ok_texinfo & ~miptex_ok]
    if len(bad):
        out.add('texinfo_miptex_index', bad)

    counts, starts, owner, surf_index, nxt, prv = face_vertex_layout(ok_range, firstedge, numedges)
    ranged = face_ids[ok_range]
    se = surfedges[surf_index].astype(np.int64)
    ae = np.abs(se)
    ok_se_v = ae < len(edges)
    ok_se = reduce_min(ok_se_v.astype(np.float64), starts, counts, 1.0) > 0
    if not ok_se.all():
        out.add('surfedge_index', ranged[~ok_se])
    ae_safe = np.where(ok_se_v, ae, 0)
    edge_rows = edges[ae_safe].astype(np.int64) if len(edges) else np.zeros((len(ae), 2), dtype=np.int64)
    neg = se < 0
    # CalcSurfaceExtents: e >= 0 takes v[0]; the loop's next vertex is the other end.
    start_v = np.where(neg, edge_rows[:, 1], edge_rows[:, 0])
    end_v = np.where(neg, edge_rows[:, 0], edge_rows[:, 1])
    ok_vert_v = (start_v < len(vertices)) & (end_v < len(vertices)) & ok_se_v
    ok_vert = reduce_min(ok_vert_v.astype(np.float64), starts, counts, 1.0) > 0
    bad_vert = ok_se & ~ok_vert
    if bad_vert.any():
        out.add('edge_vertex_index', ranged[bad_vert])

    valid_r = ok_se & ok_vert & ok_plane[ranged] & ok_texinfo[ranged]
    zero_used = reduce_max((se == 0).astype(np.float64), starts, counts) > 0
    if (zero_used & valid_r).any():
        out.add('edge_zero_used', ranged[zero_used & valid_r])
    loop_open_v = (end_v != start_v[nxt]) if len(start_v) else np.zeros(0, dtype=bool)
    loop_open = reduce_max(loop_open_v.astype(np.float64), starts, counts) > 0
    if (loop_open & valid_r).any():
        out.add('edge_loop_open', ranged[loop_open & valid_r],
                reduce_sum(loop_open_v.astype(np.float64), starts, counts)[loop_open & valid_r])
    unowned = face_ids[owner_count == 0]
    if len(unowned):
        out.add('face_unowned', unowned)
    shared = face_ids[owner_count > 1]
    if len(shared):
        out.add('face_multiple_models', shared, owner_count[shared])

    # Geometry on structurally valid faces only.
    vsel = valid_r[owner]
    safe_start = np.where(vsel, start_v, 0)
    p32 = vertices[safe_start] if len(vertices) else np.zeros((len(safe_start), 3), dtype=np.float32)
    p = p32.astype(np.float64)
    fplane = faces['plane'][ranged]
    fplane_safe = np.where(ok_plane[ranged], fplane, 0)
    n = normals[fplane_safe] if len(planes) else np.zeros((len(ranged), 3))
    dist = planes['dist'][fplane_safe].astype(np.float64) if len(planes) else np.zeros(len(ranged))
    flipped = faces['side'][ranged] != 0

    # (a) planarity against the stored plane, as the engine uses it.
    distance = np.abs((p*n[owner]).sum(axis=1)-dist[owner])
    planarity = reduce_max(distance, starts, counts)

    # (b)/(c) Newell normal, area, chords.
    first = np.repeat(starts, counts)
    rel = p - p[first]
    newell = reduce_sum(np.cross(rel, rel[nxt]), starts, counts)
    area2 = np.linalg.norm(newell, axis=1)
    area = area2/2
    unit_newell = newell/np.where(area2 > 0, area2, 1)[:, None]
    edge_vec = p[nxt]-p
    edge_len = np.linalg.norm(edge_vec, axis=1)
    zero_edges = reduce_sum((edge_len < ZERO_EDGE_LENGTH).astype(np.float64), starts, counts)
    chord = reduce_max(np.linalg.norm(rel, axis=1), starts, counts)
    width = np.where(chord > 0, area2/np.where(chord > 0, chord, 1), 0)

    # Distinct vertex indices per face.
    if len(start_v):
        pairs = np.unique(owner*(len(vertices)+1)+np.where(vsel, start_v, len(vertices)))
        distinct = np.bincount(pairs//(len(vertices)+1), minlength=len(ranged))
    else:
        distinct = np.zeros(len(ranged), dtype=np.int64)
    positions = counts - zero_edges
    # An open edge loop is not a polygon: no geometry metrics for it.
    geom = valid_r & ~loop_open
    few = geom & ((counts < 3) | (distinct < 3) | (positions < 3))
    if few.any():
        out.add('degenerate_vertices', ranged[few], np.minimum(distinct, positions)[few])
    flat = geom & ~few & (area < MIN_FACE_AREA)
    if flat.any():
        out.add('degenerate_area', ranged[flat], area[flat])
    sliver = geom & ~few & ~flat & (width < SLIVER_WIDTH)
    if sliver.any():
        out.add('degenerate_sliver', ranged[sliver], width[sliver])
    repeated = geom & ~few & (zero_edges > 0)
    if repeated.any():
        out.add('zero_length_edge', ranged[repeated], zero_edges[repeated])

    spec = config.checks['planarity']
    hit = geom & ~few & (planarity > spec.warn)
    if hit.any():
        out.add('planarity', ranged[hit], planarity[hit], planarity[hit] > spec.fail,
                extra={'area': area[hit]})

    oriented = geom & ~few & (area >= MIN_FACE_AREA)
    n_len = np.linalg.norm(n, axis=1)
    cos_tilt = np.abs((unit_newell*n).sum(axis=1))/np.where(n_len > 0, n_len, 1)
    tilt = np.degrees(np.arccos(np.clip(cos_tilt, 0, 1)))
    spec = config.checks['plane_tilt']
    hit = oriented & (tilt > spec.warn)
    if hit.any():
        out.add('plane_tilt', ranged[hit], tilt[hit], tilt[hit] > spec.fail, extra={'area': area[hit]})
    # Quake winding: clockwise seen from the front, so the right-handed Newell
    # normal points away from the facing normal (plane normal, negated by side).
    facing = n*np.where(flipped, -1., 1.)[:, None]
    winding_dot = (unit_newell*facing).sum(axis=1)
    wrong_side = oriented & (winding_dot > 0)
    if wrong_side.any():
        out.add('plane_side', ranged[wrong_side], winding_dot[wrong_side],
                extra={'side': faces['side'][ranged][wrong_side], 'tilt': tilt[wrong_side]})

    # Convexity relative to the polygon's own winding.
    e_prev = p - p[prv]
    turn = (np.cross(e_prev, edge_vec)*unit_newell[owner]).sum(axis=1)
    span = np.linalg.norm(p[nxt]-p[prv], axis=1)
    reflex = np.where(span > ZERO_EDGE_LENGTH, -turn/np.where(span > 0, span, 1), 0)
    reflex_depth = reduce_max(reflex, starts, counts)
    spec = config.checks['nonconvex']
    hit = oriented & (reflex_depth > spec.warn)
    if hit.any():
        out.add('nonconvex', ranged[hit], reflex_depth[hit], reflex_depth[hit] > spec.fail)

    # (d) extents under the engine rule and the other FPU rules.
    tex_r = np.where(ok_texinfo[ranged], faces['texinfo'][ranged], 0)
    vecs32 = texinfo['vecs'][tex_r] if len(texinfo) else np.zeros((len(ranged), 2, 4), dtype=np.float32)
    special = (texinfo['flags'][tex_r] & TEX_SPECIAL) != 0 if len(texinfo) else np.zeros(len(ranged), bool)
    vv = vecs32[owner]
    grids = {rule: rule_grid(rule_uv(p32, vv, rule), starts, counts)
             for rule in ('engine', 'binary32', 'extended')}
    if config.extent_rule not in EXTENT_RULES:
        raise ValueError(f'Unknown extent rule: {config.extent_rule}')
    mins, extents = grids[config.extent_rule]
    has_edges = counts > 0
    worst_extent = np.max([g[1].max(axis=1) for g in grids.values()], axis=0)
    engine_extent = extents.max(axis=1)
    hit = valid_r & has_edges & ~special & (engine_extent > MAX_EXTENT)
    if hit.any():
        out.add('extents_engine', ranged[hit], engine_extent[hit], extra={'extents': extents[hit]})
    hit = valid_r & has_edges & ~special & (engine_extent <= MAX_EXTENT) & (worst_extent > MAX_EXTENT)
    if hit.any():
        out.add('extents_target', ranged[hit], worst_extent[hit], extra={'engine_extents': extents[hit]})
    differs = np.zeros(len(ranged), dtype=bool)
    for rule in EXTENT_RULES:
        differs |= (grids[rule][0] != mins).any(axis=1) | (grids[rule][1] != extents).any(axis=1)
    hit = valid_r & has_edges & ~special & differs
    if hit.any():
        out.add('extents_rule_disagreement', ranged[hit], engine_extent[hit],
                extra={'engine_extents': grids['engine'][1][hit], 'binary32_extents': grids['binary32'][1][hit],
                       'extended_extents': grids['extended'][1][hit]})

    # (e) 16-bit texture fields.
    uv = rule_uv(p32, vv, config.extent_rule)
    coord_abs = np.maximum(reduce_max(np.abs(uv[0]), starts, counts), reduce_max(np.abs(uv[1]), starts, counts))
    top = mins+extents
    out_of_range = ((mins < SHORT_MIN) | (top > SHORT_MAX) | (extents > SHORT_MAX)).any(axis=1)
    hit = valid_r & has_edges & out_of_range
    if hit.any():
        out.add('texcoord_range', ranged[hit], coord_abs[hit], extra={'texturemins': mins[hit]})
    hit = valid_r & has_edges & ~out_of_range & (coord_abs > TEXCOORD_WARN)
    if hit.any():
        out.add('texcoord_margin', ranged[hit], coord_abs[hit])

    # (f) lightmaps by the engine rule.
    lightofs = faces['lightofs'][ranged].astype(np.int64)
    styles = faces['styles'][ranged]
    nstyles = np.argmax(np.concatenate([styles, np.full((len(styles), 1), 255, np.uint8)], axis=1) == 255,
                        axis=1)
    size = ((extents[:, 0] >> 4)+1)*((extents[:, 1] >> 4)+1)*nstyles
    light_len = len(lumps[LIGHTING])
    hit = valid_r & (lightofs < -1)
    if hit.any():
        out.add('lightmap_offset', ranged[hit], lightofs[hit])
    lit = valid_r & has_edges & (lightofs >= 0)
    reads = lit & ~special & (nstyles > 0)
    past = reads & (lightofs+size > light_len)
    if past.any():
        out.add('lightmap_outside_lump', ranged[past], (lightofs+size-light_len)[past],
                extra={'offset': lightofs[past], 'size': size[past]})
    if lit.any():
        offsets = np.unique(lightofs[lit])
        following = np.append(offsets[1:], max(light_len, int(offsets[-1])))
        next_offset = following[np.searchsorted(offsets, np.where(lit, lightofs, offsets[0]))]
        avail = next_offset - lightofs
        over = reads & ~past & (size > avail)
        if over.any():
            out.add('lightmap_overlap', ranged[over], (size-avail)[over],
                    extra={'offset': lightofs[over], 'size': size[over], 'available': avail[over]})
        slack = reads & ~past & (size < avail)
        if slack.any():
            out.add('lightmap_span_mismatch', ranged[slack], (avail-size)[slack],
                    extra={'offset': lightofs[slack], 'size': size[slack], 'available': avail[slack]})
        sel = np.flatnonzero(reads)
        if len(sel):
            order = np.lexsort((size[sel], lightofs[sel]))
            ofs_sorted, size_sorted = lightofs[sel][order], size[sel][order]
            group_start = np.r_[True, ofs_sorted[1:] != ofs_sorted[:-1]]
            gid = np.cumsum(group_start)-1
            gmin = np.minimum.reduceat(size_sorted, np.flatnonzero(group_start))
            gmax = np.maximum.reduceat(size_sorted, np.flatnonzero(group_start))
            mixed = (gmax != gmin)[gid] & (size_sorted != gmin[gid])
            if mixed.any():
                faces_mixed = sel[order][mixed]
                out.add('lightmap_shared_size', ranged[faces_mixed], (size_sorted-gmin[gid])[mixed])

    return finish(out, name, nfaces, models, int(np.count_nonzero(valid_r)), int(np.count_nonzero(reads)), instanced)


def finish(out, name, nfaces, models, valid, lit, instanced=0):
    checks = {}
    for check, spec in out.config.checks.items():
        if spec.severity == 'off':
            continue
        result = out.results.get(check, {'flagged': 0, 'failing': 0, 'worst': []})
        failing = result['failing'] if spec.kind == 'metric' else result['flagged']
        checks[check] = {'group': spec.group, 'severity': spec.severity, 'unit': spec.unit,
                         'flagged': result['flagged'], 'failing': failing,
                         'fatal': spec.severity == 'fail' and failing > 0, 'worst': result['worst']}
        if spec.kind == 'metric':
            checks[check].update(warn_above=spec.warn, fail_above=spec.fail)
    per_model = {}
    for model, entry in sorted(out.per_model.items()):
        entry = {k: v for k, v in entry.items() if out.config.checks[k].severity != 'off'}
        if entry:
            mf = models[model] if 0 <= model < len(models) else None
            per_model[str(model)] = {'classname': out.classnames.get(model),
                                     'faces': int(mf['numfaces']) if mf is not None else None,
                                     'flagged': entry}
    return {'map': name, 'extent_rule': out.config.extent_rule,
            'faces': int(nfaces), 'faces_checked': valid, 'faces_lit': lit, 'models': int(len(models)),
            'instanced_models': instanced,
            'fatal': any(c['fatal'] for c in checks.values()), 'checks': checks, 'per_model': per_model}


def merge(reports, config=None, errors=()):
    """Combine per-map reports: totals, global worst cases, maps with findings."""
    config = config or Config()
    total = {'maps': len(reports), 'faces': 0, 'faces_checked': 0, 'faces_lit': 0, 'unreadable': list(errors),
             'checks': {}, 'maps_with_findings': {}}
    for report in reports:
        total['faces'] += report['faces']
        total['faces_checked'] += report['faces_checked']
        total['faces_lit'] += report['faces_lit']
        for check, result in report['checks'].items():
            entry = total['checks'].setdefault(check, {
                k: v for k, v in result.items() if k not in ('flagged', 'failing', 'fatal', 'worst')})
            entry['flagged'] = entry.get('flagged', 0)+result['flagged']
            entry['failing'] = entry.get('failing', 0)+result['failing']
            entry['maps'] = entry.get('maps', 0)+(1 if result['flagged'] else 0)
            metric = config.checks[check].kind == 'metric' or any(r['value'] for r in result['worst'])
            pool = entry.get('worst', [])+result['worst']
            entry['worst'] = heapq.nlargest(config.worst, pool, key=rank(check)) if metric \
                else pool[:config.worst]
            if result['flagged']:
                total['maps_with_findings'].setdefault(report['map'], {})[check] = result['flagged']
    for entry in total['checks'].values():
        entry['fatal'] = entry['severity'] == 'fail' and entry['failing'] > 0
    total['fatal'] = any(e['fatal'] for e in total['checks'].values()) or bool(errors)
    return total


def bsp_paths(paths):
    for path in paths:
        path = Path(path)
        if path.is_dir():
            yield from sorted(p for p in path.rglob('*') if p.suffix.lower() == '.bsp')
        else:
            yield path


def parse_assignments(values, what):
    result = []
    for value in values or ():
        if '=' not in value:
            raise ValueError(f'{what} must be NAME=VALUE: {value}')
        result.append(value.split('=', 1))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('paths', nargs='+', help='BSP29 files or directories (searched for *.bsp)')
    parser.add_argument('--report', type=Path, help='write the JSON report here')
    parser.add_argument('--severity', action='append', metavar='CHECK=fail|warn|off')
    parser.add_argument('--threshold', action='append', metavar='CHECK.warn|fail=VALUE')
    parser.add_argument('--worst', type=int, default=WORST_CASES, help='worst cases kept per check')
    parser.add_argument('--extent-rule', choices=EXTENT_RULES, default='engine',
                        help='texture-coordinate arithmetic for extents, 16-bit and lightmap checks')
    parser.add_argument('--maps', action='store_true', help='include every per-map report')
    parser.add_argument('--list-checks', action='store_true', help='print the checks and exit')
    args = parser.parse_args(argv)
    config = Config(worst=args.worst, extent_rule=args.extent_rule)
    try:
        for name, value in parse_assignments(args.severity, '--severity'):
            config.set_severity(name, value)
        for name, value in parse_assignments(args.threshold, '--threshold'):
            check, _, level = name.partition('.')
            config.set_threshold(check, level, value)
    except ValueError as exc:
        parser.error(str(exc))
    if args.list_checks:
        for name, spec in config.checks.items():
            limits = f' warn>{spec.warn:g} fail>{spec.fail:g}' if spec.kind == 'metric' else ''
            print(f'{name:28} {spec.group:10} {spec.severity:5}{limits}  {spec.description}')
        return 0
    reports, errors = [], []
    for path in bsp_paths(args.paths):
        try:
            reports.append(check_bsp(path.read_bytes(), str(path), config))
        except (OSError, MapError) as exc:
            errors.append({'map': str(path), 'error': str(exc)})
    total = merge(reports, config, errors)
    if args.maps:
        total['map_reports'] = reports
    text = json.dumps(total, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))+'\n'
    if args.report:
        args.report.write_text(text, encoding='utf-8', newline='\n')
    for check, entry in total['checks'].items():
        if entry['flagged']:
            mark = 'FAIL' if entry['fatal'] else entry['severity']
            print(f'{mark:5} {check}: {entry["flagged"]} flagged, {entry["failing"]} failing '
                  f'in {entry["maps"]} maps')
    print(f'{total["maps"]} maps, {total["faces"]} faces, {total["faces_checked"]} checked, '
          f'{len(errors)} unreadable')
    if errors:
        return 2
    return 1 if total['fatal'] else 0


if __name__ == '__main__':
    sys.exit(main())
