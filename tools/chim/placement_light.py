# SPDX-License-Identifier: GPL-3.0-only
"""Placement light levels of a CHIM exterior world: the light the original's light sources give each placed model.

Part 2 of the hybrid lighting type (docs/chim/LIGHTING.md, "Decision: the hybrid lighting type"): one light level
per placement, stored in the placed record's flags (world format 0.12, the byte the CHIM rooms already use;
docs/chim/WORLD_FORMAT.md "Placement light, stores and room records (0.12)"). Outdoors the engine adds the level to
the daylight-dimmed ambient and never dims it (r_surf.c R_BuildLightMap, as the lamp styles 32 and up), so a model
next to a lamp, a fire or a light without a mesh is lit by it day and night; r_lamps 0 turns it off for A/B.

The value is the rooms' rule (tools/chim/interior.py: interior_lighting.point_light at the placement's drawn-box
centre) without the cell ambient: the sum over every exterior light source that adds light of its colour's luma
times the original attenuation (interior_lighting.original_weight: min(1, r / 3d), faded out between r and 2r).
Every class that adds light counts, the lights without a mesh among them (CHIM-MESHLESS-LIGHTS-33): plain lights,
glowing plants, fires, lamps, torches and candles (tools/light_sources.py LIGHT_CLASS_CODES). Darkeners and lights
that are off by default give none (a level only adds). Levels are rounded to LEVEL_STEP so placements of one model
share their cached surfaces; a sum under MIN_LEVEL is none.

Build setting (EXPERIMENTAL, off by default until its in-game frame cost is measured): tools/build.py
--chim-placement-light sources -> tools/chim_build.py --placement-light sources (hybrid lighting type only), which
exports MODE_VARIABLE and MASTER_VARIABLE (the master the sources are read from); chim.world.build_frames stores the
levels when the world has placed records (format 0.8 and later) and writes the world as format 0.12. Off: every byte
as before.

Cost to measure before it goes on: the renderer keeps one cached surface per model surface and mip level
(d_surf.c D_CacheSurface), so placements of one model at different levels drawn in the same frame rebuild it in turn;
tools/chim/flames.py measure counts those models per frame.
"""
import os
import struct
from pathlib import Path

from chim import format as F

MODE_VARIABLE = 'AMIWIND_CHIM_PLACEMENT_LIGHT'
MASTER_VARIABLE = 'AMIWIND_CHIM_LIGHT_MASTER'
# 'fires': only the light records whose mesh burns (a fire mesh with flame emitters, the frame maps' aw_flame
# sources: campfires, fire pits, braziers, torches, lanterns, candles); 'sources': every light that adds light
MODES = ('off', 'fires', 'sources')
FORMAT_VERSION = (0, 12)          # the first world format whose placed record flags carry a light level
# Importing this module lets chim.format read world format 0.12 (as chim.interior does for the rooms); kept out of
# chim.placed so the placed units' code keys stay as they were. Readers of an exterior 0.12 world import it.
if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)
FLAGS_AT = 46                     # the flags' offset in a placed record (chim.format.PLACEMENT)
LEVEL_STEP = 8
MIN_LEVEL = 4
SCALE = 0.25                      # Morrowind units to frame-local units (chim.world.frame_box: centre + 4 x local)
LUMA = (.299, .587, .114)


def mode():
    """The placement light mode from the environment ('off' without it: a world built outside the CHIM stage)."""
    value = os.environ.get(MODE_VARIABLE, 'off').strip() or 'off'
    if value not in MODES:
        raise ValueError('%s must be one of %s' % (MODE_VARIABLE, ', '.join(MODES)))
    return value


def mode_for_lighting(lighting_type):
    """The placement light mode a CHIM lighting type allows (chim.light_types): hybrid -> sources, else off."""
    return 'sources' if lighting_type == 'hybrid' else 'off'


def model_stem(model):
    """A mesh path as a CHIM model is named ('l\\\\Light_Fire.NIF' -> 'l/light_fire'; '@' and '#' suffixes of a
    model name dropped)."""
    stem = str(model).replace('\\', '/').casefold().split('@', 1)[0].split('#', 1)[0]
    stem = stem[len('meshes/'):] if stem.startswith('meshes/') else stem
    return stem[:-4] if stem.endswith('.nif') else stem


def fire_sources(found, fire_stems):
    """The sources (sources()) whose mesh is one of FIRE_STEMS (model_stem names of the meshes that carry flames)."""
    stems = set(fire_stems)
    return [s for s in found if s.get('model') and model_stem(s['model']) in stems]


def model_fire_stems(models):
    """model_stem names of the models (CHIM index entries or variants: 'name' with 'image' bytes or 'lumps') whose
    entity lump holds a fire emitter (chim.flames: aw_flame on a fire mesh)."""
    from chim import format as F
    from chim.flames import FLAME_CLASS, fire_mesh
    out = set()
    for m in models:
        if m is None:
            continue
        lump = m['lumps'][0] if 'lumps' in m else F.read_brush_image(m['image'])[0]
        if ('"%s"' % FLAME_CLASS).encode() in bytes(lump) and fire_mesh(m['name']):
            out.add(model_stem(m['name']))
    return out


def sources(raw):
    """Every exterior light source of a master that adds light: [{'position': Morrowind units, 'radius',
    'luma', 'class', 'mesh', 'model'}] in master order (light_sources.placements)."""
    import light_sources as LS
    records = LS.light_records(raw)
    adding = set(LS.LIGHT_CLASS_CODES)
    out = []
    for key, ident, position in LS.placements(raw, records):
        light = records[ident]
        if key[0] != 'exterior' or light['class'] not in adding or light['radius'] <= 0:
            continue
        luma = sum(c * w for c, w in zip(light['colour'], LUMA))
        if luma <= 0:
            continue
        out.append({'position': tuple(float(v) for v in position), 'radius': float(light['radius']),
                    'luma': float(luma), 'class': light['class'], 'mesh': bool(light['model']),
                    'model': light['model']})
    return out


_SOURCES = {}


def environment_sources():
    """(mode, sources or None): every source of MASTER_VARIABLE's master when the mode is not off, read once per
    process (the caller keeps the fires for 'fires': fire_sources). A mode without a readable master is refused
    (never a silent off)."""
    m = mode()
    if m == 'off':
        return m, None
    master = os.environ.get(MASTER_VARIABLE, '')
    if not master or not Path(master).is_file():
        raise ValueError('%s=%s needs %s naming the master (got %r)' % (MODE_VARIABLE, m, MASTER_VARIABLE, master))
    if _SOURCES.get('master') != master:
        raw = Path(master).read_bytes()
        _SOURCES.clear()
        import hashlib
        _SOURCES.update(master=master, sources=sources(raw), sha256=hashlib.sha256(raw).hexdigest())
    return m, _SOURCES['sources']


def source_sha256():
    """SHA-256 of the master the sources were read from (environment_sources), for the receipt."""
    return _SOURCES.get('sha256')


def level(value):
    """A summed source light (0..255 and up) as a stored level: 0 under MIN_LEVEL, else rounded to LEVEL_STEP
    (at least one step), at most 255."""
    if not value >= MIN_LEVEL:
        return 0
    # rounded half up, as the engine rounds the fires' light (chim_chunks.c ChimChunks_FireLevel)
    return max(LEVEL_STEP, min(255, int(value / LEVEL_STEP + 0.5) * LEVEL_STEP))


_ARRAYS = {}


def frame_levels(frame, placements, found):
    """{pid: level} of a frame's placements (dicts with '_pid' and '_box', the stored drawn box) lit by the sources
    FOUND (sources()); placements without light are left out. frame: its 'centre' (Morrowind units)."""
    import numpy as np
    if not placements or not found:
        return {}
    if _ARRAYS.get('found') is not found or _ARRAYS.get('count') != len(found):
        _ARRAYS.clear()
        _ARRAYS.update(found=found, count=len(found),        # the list itself is held: its id is never reused
                       position=np.array([s['position'] for s in found], dtype=float),
                       radius=np.array([s['radius'] for s in found], dtype=float))
    cx, cy = frame['centre'][:2]
    box = np.array([[*p['_box'][0], *p['_box'][1]] for p in placements], dtype=float)
    centres = (box[:, :3] + box[:, 3:]) / 2
    lo, hi = box[:, :3].min(axis=0), box[:, 3:].max(axis=0)
    local = (_ARRAYS['position'] - np.array([cx, cy, 0.0])) * SCALE
    reach = 2 * _ARRAYS['radius'] * SCALE
    # a source more than its reach (2 r) outside every placement box of the frame touches none
    inside = np.all((local >= lo - reach[:, None]) & (local <= hi + reach[:, None]), axis=1)
    values = np.zeros(len(placements))
    for k in np.nonzero(inside)[0]:
        s = found[k]
        r = s['radius'] * SCALE
        d = np.linalg.norm(centres - local[k], axis=1)
        near = d < 2 * r
        if not near.any():
            continue
        dn = d[near]
        weight = np.where(dn <= r / 3, 1.0, r / (3 * np.maximum(dn, 1e-9)))
        t = np.clip(dn / r - 1, 0.0, 1.0)
        t = 1 - t * t
        t = 1 - t * t
        values[near] += s['luma'] * weight * (1 - t)
    out = {}
    for p, v in zip(placements, values):
        lv = level(float(v))
        if lv:
            out[p['_pid']] = lv
    return out


def with_light(record, value):
    """A placed record with its light level in the flags' high byte (bits 0 and 1 kept); value 0: unchanged."""
    if not 0 <= value <= 255:
        raise ValueError('Light level %r outside 0..255' % value)
    if not value:
        return record
    flags = struct.unpack_from('>H', record, FLAGS_AT)[0]
    if flags & 0xFF00:
        raise ValueError('Placed record flags already use the high byte')
    out = bytearray(record)
    struct.pack_into('>H', out, FLAGS_AT, flags | (value << 8))
    return bytes(out)


def record_light(record):
    """The light level of a placed record's flags (0: none)."""
    return struct.unpack_from('>H', record, FLAGS_AT)[0] >> 8


def summary(levels, placements_total, found, mode_name):
    """The receipt's placement_light record."""
    import collections
    hist = collections.Counter(levels.values())
    return {'mode': mode_name, 'world_format': '%d.%d' % FORMAT_VERSION if levels else None,
            'sources': len(found or ()), 'sources_without_mesh': sum(1 for s in found or () if not s['mesh']),
            'sources_by_class': dict(sorted(collections.Counter(s['class'] for s in found or ()).items())),
            'placements': placements_total, 'placements_lit': len(levels),
            'levels': {str(k): hist[k] for k in sorted(hist)}, 'master_sha256': source_sha256(),
            'rule': 'sum of luma x original attenuation at the drawn-box centre, step %d, from %d' % (LEVEL_STEP,
                                                                                                    MIN_LEVEL)}
