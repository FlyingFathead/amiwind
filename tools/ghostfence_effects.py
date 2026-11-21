#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The Ghostfence's glow and curtain, and the blight cloud's plume (GHOSTFENCE-PARTICLES-NOT-DRAWN-68,
GHOSTFENCE-NO-ANIMATION-46, v0.0.68).

THE GLOW. In the original each Ghostfence pylon carries two invisible emitters (x/ex_gg_particles_01.nif, 132
placements in 34 exterior cells): a particle system that throws faint mist puffs (tx_waterfall_mist_01, drawn
additively) sideways out of the pylon's arm, where its wind force bends them down. The blight cloud over Dagoth Ur
(f/active_blight_large.nif, one placement in cell 2,8) has one more: dark puffs rising and paling out. AmiWind draws
each emitter as a plain sprite (the project's decision for the meshes' emitters, MESH-PARTICLE-EMITTERS: a simple
sprite, no particle simulation in the game): the builder runs the emitter's own particle system from the model
(birth rate, life, speed, cone, wind, grow and fade, colour keys, texture, blend: rules from OpenMW
components/nifosg/particle.cpp and nifloader.cpp, read, not copied) and bakes what it shows, seen from the side, into
GLOW_FRAMES frames of id1/world/glow.spr. id1/world/glow.awg holds one row per emitter placement (GLOW_ROW: the
plume's centre and size in the original's units, its frames, and the placement's reference, so a script's Disable
hides it: GhostfenceScript disables every pylon emitter once the Heart is destroyed, EndGame the blight cloud). The
engine (aw_atmos.c) reads the rows of the 3 x 3 cells around the view and draws the nearest in front.

THE CURTAIN. Each curtain mesh (x/ex_gg_fence_s_01 .. _04, _s_h_01) is three layers, each with an NiUVController that
slides its texture: two layers of Tx_GG_fence_01 at two speeds and one of Tx_GG_fence_02, each swaying sideways.
id1/world/curtain.awc gives the engine (aw_curtain.c) the layers' texture intensities, their motion as tables, a
colour ramp with the pulse, and the checksums of the curtain textures as the CHIM stores hold them; with aw_curtain 1
the engine composes the three layers into the curtain's texture once a frame and draws it straight, instead of
Quake's warp. No CHIM unit is touched: the tables are written at image assembly from the stores as built.

Kept in a module of its own: only the image step reads it (tools/build_aga.py write_ghostfence), so a change here
re-keys the engine and image stages alone (as tools/world_barriers.py).

    python3 tools/ghostfence_effects.py measure --data-files DIR [--store WORLD_CWI ...] [--palette LMP] [--json OUT]
"""
import argparse
import io
import json
import math
from pathlib import Path
import random
import struct
import sys

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / 'src'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from editor_markers import EditorMarkers, read_masters  # noqa: E402
from mwad.esm import GAME_MASTERS  # noqa: E402
from world_barriers import master_lists, placement_axes, reference_key  # noqa: E402

GLOW_TABLE = 'world/glow.awg'
GLOW_SPRITE = 'world/glow.spr'
CURTAIN_TABLE = 'world/curtain.awc'
RECEIPT = 'ghostfence-effects.json'

# id1/world/glow.awg (engine aw_atmos.c GLOW_*): "AWG1" <I> rows; rows sorted by cell (x, then y), GLOW_ROW each:
# <hh> exterior cell of the plume's centre, <3f> the centre (original units), <HH> the sprite's width and height
# (original units), <B> kind (GLOW_KINDS), <B> first frame in glow.spr, <B> frames, <B> phase (0..255, the frame
# cycle's start), <I> the placement's reference (the world change list's key: tools/world_barriers.py reference_key).
GLOW_MAGIC = b'AWG1'
GLOW_ROW = struct.Struct('<hh3fHHBBBBI')
GLOW_ROWS_MAX = 1024
GLOW_MODELS = (('x/ex_gg_particles_01.nif', 'ghostfence'), ('f/active_blight_large.nif', 'blight'))
GLOW_KINDS = {'ghostfence': 1, 'blight': 2}
GLOW_FRAMES = 4                  # frames a plume cycles through (aw_atmos.c GLOW_FPS a second)
GLOW_SPRITE_SIZE = 64            # texels along a plume sprite's longer side
GLOW_SNAPSHOTS = 3               # steady-state snapshots averaged into one frame
GLOW_SATURATE = 70               # an additive plume is full where its light passes this percentile of its lit texels
GRAVITY_GAIN = 1.6               # OpenMW GravityAffector::operate: velocity += direction * force * dt * 1.6
NO_AUTO_ADJUST = 1               # NiParticleSystemController emit flag: the birth rate as written (OpenMW noAutoAdjust)
CELL = 8192.0
# a 4 x 4 ordered dither: a plume texel shows where its coverage passes the threshold (no blending in the 8-bit view)
BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

# id1/world/curtain.awc (engine aw_curtain_rules.c): header CURTAIN_HEAD ("AWC1", version, size, sources, layers,
# levels, pulses, textures, steps, period ms, pulse ms); textures x (<I> FNV-1a 32 of the 64 x 64 block the engine
# draws a curtain texture from, <H> the texture's own size in a CHIM store, 32 or 64, <H> 0); sources x size*size
# intensity levels (0..15); layers x (<B> source, <B> 0, steps x <b> U offset in texels, steps x <B> V offset in texels
# mod size); 16 x <B> pulse step; pulses x levels <B> palette index (never a sky bank index: the file is not overlaid).
CURTAIN_MAGIC = b'AWC1'
CURTAIN_HEAD = struct.Struct('<4s8HII')
CURTAIN_PREFIX = 'x/ex_gg_fence_s'
CURTAIN_MODELS = ('x/ex_gg_fence_s_01.nif', 'x/ex_gg_fence_s_02.nif', 'x/ex_gg_fence_s_03.nif', 'x/ex_gg_fence_s_04.nif',
                  'x/ex_gg_fence_s_h_01.nif')
CURTAIN_SIZE = 32                # the curtain textures as built (chim.models: 32 x 32, tiled to 64 x 64 at load)
DRAWN = 64                       # the turbulent drawing's texture (d_scan.c Turbulent8: 64 x 64)
CURTAIN_STEPS = 64               # motion table steps over the loop
CURTAIN_LEVEL_MAX = 15
CURTAIN_PULSES = 8
CURTAIN_PULSE_MS = 2000          # one slow breath of the glow
CURTAIN_PULSE_DEPTH = 0.12       # +- this share of the brightness
CURTAIN_GLOW = 1.25              # brighter than the texture: the maintainer asked for more glow
CURTAIN_FLOOR = 0.22             # the brightness where every layer is thin
CURTAIN_SAT = 0.7                # the share of the summed levels at which the colour is full
FNV_OFFSET, FNV_PRIME = 0x811C9DC5, 0x01000193


def fnv1a(data):
    h = FNV_OFFSET
    for b in data:
        h = ((h ^ b) * FNV_PRIME) & 0xFFFFFFFF
    return h


# ---------------------------------------------------------------- the models' particle systems

def _vec(v):
    return (float(v.x), float(v.y), float(v.z))


def _texture_and_blend(node):
    """(texture stem, additive) of a particles node: its NiTexturingProperty's base texture and whether its
    NiAlphaProperty blends one onto the destination (source alpha, one: flags 13) or over it."""
    stem, additive = '', False
    for prop in getattr(node, 'properties', None) or []:
        if prop is None:
            continue
        kind = type(prop).__name__
        if kind == 'NiTexturingProperty' and getattr(prop, 'has_base_texture', False):
            source = getattr(prop.base_texture, 'source', None)
            name = source.file_name.decode('cp1252', 'replace') if source is not None and source.file_name else ''
            stem = name.replace('\\', '/').rsplit('/', 1)[-1].rsplit('.', 1)[0].casefold()
        if kind == 'NiAlphaProperty':
            flags = int(prop.flags)
            additive = bool(flags & 1) and (flags >> 5) & 15 == 0     # destination factor ONE
    return stem, additive


def particle_systems(raw, N):
    """[{...}] of every NiParticleSystemController of a NIF: its numbers, its emitter's and its particles' model-frame
    matrices (row vectors, the scenery root rule of tools/particle_emitters.py emitter_points), its modifiers."""
    import numpy as np
    from nif_common import first_record, scenery_root_local
    data = N.Data()
    data.read(io.BytesIO(raw))
    worlds = {}

    def collect(node, parent, root=False):
        if not isinstance(node, N.NiAVObject):
            return
        local = np.array(node.get_transform().as_list())
        if root:
            local = scenery_root_local(local, node, N, first_record(data, node))
        world = local @ parent
        worlds[id(node)] = world
        for child in getattr(node, 'children', []) or []:
            if child is not None:
                collect(child, world)
    for root in data.roots:
        collect(root, np.eye(4), root=True)
    out = []
    for block in data.blocks:
        if type(block).__name__ != 'NiParticleSystemController':
            continue
        emitter, target = block.emitter, block.target
        if emitter is None or target is None or id(emitter) not in worlds or id(target) not in worlds:
            continue
        winds, points, grow, fade, colours = [], 0, 0.0, 0.0, None
        modifier = block.particle_extra
        while modifier is not None:
            kind = type(modifier).__name__
            if kind == 'NiGravity':
                if int(modifier.type) == 0:
                    winds.append((float(modifier.force), _vec(modifier.direction)))
                else:
                    points += 1
            elif kind == 'NiParticleGrowFade':
                grow, fade = float(modifier.grow), float(modifier.fade)
            elif kind == 'NiParticleColorModifier' and modifier.color_data is not None:
                colours = [(float(k.time), (float(k.value.r), float(k.value.g), float(k.value.b), float(k.value.a)))
                           for k in modifier.color_data.data.keys]
            modifier = modifier.next_modifier
        texture, additive = _texture_and_blend(target)
        life, life_random = float(block.lifetime), float(block.lifetime_random)
        rate = (float(block.emit_rate) if int(block.emit_flags) & NO_AUTO_ADJUST else
                len(block.particles) / max(1e-6, life + life_random / 2))
        out.append({'speed': float(block.speed), 'speed_random': float(block.speed_random),
                    'vertical': (float(block.vertical_direction), float(block.vertical_angle)),
                    'horizontal': (float(block.horizontal_direction), float(block.horizontal_angle)),
                    'size': float(block.size), 'rate': rate, 'lifetime': life, 'lifetime_random': life_random,
                    'box': _vec(block.start_random), 'emitter': worlds[id(emitter)], 'particles': worlds[id(target)],
                    'winds': winds, 'point_forces': points, 'grow': grow, 'fade': fade, 'colours': colours,
                    'texture': texture, 'additive': additive})
    return out


def colour_at(keys, x):
    """The colour keys (time 0..1, rgba) at X, linear between keys (the system's own colour modifier); white without."""
    if not keys:
        return (1.0, 1.0, 1.0, 1.0)
    if x <= keys[0][0]:
        return keys[0][1]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if x <= t1:
            f = 0.0 if t1 <= t0 else (x - t0) / (t1 - t0)
            return tuple(a + (b - a) * f for a, b in zip(c0, c1))
    return keys[-1][1]


def snapshot(system, rng):
    """One steady-state moment of the system in the model frame: [(position, radius, (r, g, b, a))] for every live
    particle (as many as birth rate x mean life), each at a random age of its life."""
    import numpy as np
    count = max(1, int(round(system['rate'] * (system['lifetime'] + system['lifetime_random'] / 2))))
    emitter, particles = system['emitter'], system['particles']
    origin = emitter[3, :3]
    acc = np.zeros(3)
    for force, direction in system['winds']:
        d = np.array(direction) @ particles[:3, :3]
        n = float(np.linalg.norm(d))
        if n > 0:
            acc += d / n * force * GRAVITY_GAIN
    vdir, vang = system['vertical']
    hdir, hang = system['horizontal']
    low, high = system['speed'] - system['speed_random'] / 2, system['speed'] + system['speed_random'] / 2
    out = []
    for _ in range(count):
        life = max(1e-3, system['lifetime'] + system['lifetime_random'] * rng.random())
        age = rng.random() * life
        h = hdir + hang * (2 * rng.random() - 1)
        v = vdir + vang * (2 * rng.random() - 1)
        direction = np.array((math.sin(v) * math.cos(h), math.sin(v) * math.sin(h), math.cos(v))) @ emitter[:3, :3]
        speed = low + (high - low) * rng.random()
        box = np.array([(rng.random() - 0.5) * d for d in system['box']]) @ emitter[:3, :3]
        position = origin + box + direction * speed * age + 0.5 * acc * age * age
        size = system['size']
        if system['grow'] > 0 and age < system['grow']:
            size *= age / system['grow']
        if system['fade'] > 0 and life - age < system['fade']:
            size *= (life - age) / system['fade']
        if size > 0:
            out.append((position, size, colour_at(system['colours'], age / life)))
    return out


def _texture_rgba(files, stem):
    """The particle texture (RGBA floats 0..1) from the archives or loose files, None when it cannot be read."""
    import numpy as np
    from PIL import Image
    from particle_emitters import _read
    for ext in ('.dds', '.tga', '.bmp'):
        source = files.get('textures/' + stem + ext)
        if source is None:
            continue
        try:
            return np.asarray(Image.open(io.BytesIO(_read(source))).convert('RGBA'), dtype=float) / 255.0
        except Exception:
            continue
    return None


def _nearest(palette, rgb, exclude=(255,)):
    """Palette indices nearest each RGB row (N x 3, 0..255), never one of EXCLUDE."""
    import numpy as np
    pal = np.frombuffer(bytes(palette[:768]), np.uint8).reshape(256, 3).astype(float)
    d = ((rgb[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
    d[:, list(exclude)] = np.inf
    return d.argmin(axis=1).astype(np.uint8)


def bake(system, texture, palette, kind_seed):
    """The plume of one system as sprite frames: {'frames': [(width, height, pixels)], 'centre': model-frame point,
    'width', 'height' (original units), 'visible': texels drawn per frame}. Seen along its narrowest horizontal axis."""
    import numpy as np
    from PIL import Image
    snaps = [[snapshot(system, random.Random(kind_seed * 1000 + f * 10 + s)) for s in range(GLOW_SNAPSHOTS)]
             for f in range(GLOW_FRAMES)]
    allp = np.array([p for frame in snaps for snap in frame for p, _, _ in snap])
    radius = max(r for frame in snaps for snap in frame for _, r, _ in snap)
    # the horizontal axis the plume spreads along most, and the vertical
    flat = allp[:, :2] - allp[:, :2].mean(axis=0)
    _, _, vt = np.linalg.svd(flat, full_matrices=False)
    u_axis = np.array([vt[0][0], vt[0][1], 0.0])
    w_axis = np.array([-u_axis[1], u_axis[0], 0.0])
    us, zs = allp @ u_axis, allp[:, 2]
    u0, u1, z0, z1 = us.min() - radius, us.max() + radius, zs.min() - radius, zs.max() + radius
    width, height = float(u1 - u0), float(z1 - z0)
    if width >= height:
        tw, th = GLOW_SPRITE_SIZE, max(8, int(round(GLOW_SPRITE_SIZE * height / width)))
    else:
        tw, th = max(8, int(round(GLOW_SPRITE_SIZE * width / height))), GLOW_SPRITE_SIZE
    sw, sh = tw * 2, th * 2                       # drawn at twice the size, then averaged down
    scale_u, scale_z = sw / width, sh / height
    tex = texture if texture is not None else np.ones((8, 8, 4))
    timg = Image.fromarray((np.clip(tex, 0, 1) * 255).astype(np.uint8), 'RGBA')
    cache = {}
    frames, visible = [], []
    for frame in snaps:
        rgb = np.zeros((sh, sw, 3))
        cover_log = np.zeros((sh, sw))
        weight = np.zeros((sh, sw))
        for snap in frame:
            for p, r, c in snap:
                k = max(1, int(round(2 * r * scale_u)))
                if k not in cache:
                    cache[k] = np.asarray(timg.resize((k, k), Image.Resampling.BILINEAR), dtype=float) / 255.0
                t = cache[k]
                cx, cy = (p @ u_axis - u0) * scale_u, (z1 - p[2]) * scale_z
                x0, y0 = int(round(cx - k / 2)), int(round(cy - k / 2))
                xa, ya, xb, yb = max(0, x0), max(0, y0), min(sw, x0 + k), min(sh, y0 + k)
                if xa >= xb or ya >= yb:
                    continue
                patch = t[ya - y0:yb - y0, xa - x0:xb - x0]
                a = patch[:, :, 3] * c[3] / GLOW_SNAPSHOTS
                col = patch[:, :, :3] * np.array(c[:3])
                if system['additive']:
                    rgb[ya:yb, xa:xb] += col * a[:, :, None]
                else:
                    cover_log[ya:yb, xa:xb] += np.log(np.clip(1 - a, 1e-6, 1))
                    rgb[ya:yb, xa:xb] += col * a[:, :, None]
                    weight[ya:yb, xa:xb] += a
        rgb = rgb.reshape(th, 2, tw, 2, 3).mean(axis=(1, 3))
        if system['additive']:
            lum = rgb @ np.array([0.3, 0.59, 0.11])
            lit = lum[lum > 0.01 * max(1e-9, lum.max())]
            sat = float(np.percentile(lit, GLOW_SATURATE)) if lit.size else 1.0
            cover = np.clip(lum / max(1e-9, sat), 0, 1)
            chroma = rgb / np.maximum(1e-9, rgb.max(axis=2, keepdims=True))
            colour = chroma * 255 * (0.7 + 0.3 * cover[:, :, None])
        else:
            weight = weight.reshape(th, 2, tw, 2).mean(axis=(1, 3))
            cover = 1 - np.exp(cover_log.reshape(th, 2, tw, 2).mean(axis=(1, 3)))
            colour = rgb / np.maximum(1e-9, weight[:, :, None]) * 255
        threshold = np.array([[(BAYER4[y % 4][x % 4] + 0.5) / 16 for x in range(tw)] for y in range(th)])
        show = cover > threshold
        index = _nearest(palette, np.clip(colour.reshape(-1, 3), 0, 255)).reshape(th, tw)
        frames.append(np.where(show, index, 255).astype(np.uint8))
        visible.append(int(show.sum()))
    # every frame cut to the texels any frame shows (the engine visits every texel of a sprite's square on screen)
    shown = np.argwhere(np.any(np.stack(frames) != 255, axis=0))
    (ya, xa), (yb, xb) = (shown.min(axis=0), shown.max(axis=0) + 1) if len(shown) else ((0, 0), (th, tw))
    du, dz = width / tw, height / th
    depth = float((allp @ w_axis).mean())
    mid_u = u0 + du * (xa + xb) / 2
    mid_z = z1 - dz * (ya + yb) / 2
    centre = u_axis * mid_u + w_axis * depth + np.array([0.0, 0.0, mid_z])
    cut = [(int(xb - xa), int(yb - ya), f[ya:yb, xa:xb].tobytes()) for f in frames]
    return {'frames': cut, 'centre': [float(v) for v in centre], 'width': float(du * (xb - xa)),
            'height': float(dz * (yb - ya)), 'visible': visible, 'particles': len(snaps[0][0]),
            'radius': float(radius), 'box': [width, height]}


def sprite_bytes(frames):
    """A Quake sprite (IDSP version 1, facing the view, as tools/particle_emitters.py smoke_sprite) of FRAMES
    [(width, height, pixels)], each centred on its origin; palette index 255 is transparent."""
    w, h = max(f[0] for f in frames), max(f[1] for f in frames)
    raw = struct.pack('<4siifiiifi', b'IDSP', 1, 2, math.hypot(w, h) / 2, w, h, len(frames), 0.0, 0)
    for fw, fh, pixels in frames:
        raw += struct.pack('<5i', 0, -(fw // 2), fh // 2, fw, fh) + pixels
    return raw


def glow(data_files, palette):
    """(rows, sprite bytes, report): every exterior placement of a GLOW_MODELS model, one row per particle system,
    and the sprite with each model's baked plumes."""
    import numpy as np
    from particle_emitters import _sources
    from prepare_scenery import nif_reader
    N = nif_reader()
    markers = EditorMarkers(data_files, masters=GAME_MASTERS)
    _, files = _sources(data_files)
    _, objects, _, _, cells = read_masters(data_files, with_cells=True)
    lists = master_lists(data_files)
    bakes, frames, report = {}, [], {'models': {}, 'rows': 0, 'by_kind': {}, 'skipped': []}
    for model, kind in GLOW_MODELS:
        raw = markers.raw(model)
        systems = particle_systems(raw, N) if raw else []
        bakes[model] = []
        for s, system in enumerate(systems):
            texture = _texture_rgba(files, system['texture'])
            b = bake(system, texture, palette, GLOW_KINDS[kind] * 10 + s)
            b['frame0'] = len(frames)
            frames += b['frames']
            bakes[model].append(b)
        report['models'][model] = [{'kind': kind, 'texture': sy['texture'], 'additive': sy['additive'],
                                    'rate': round(sy['rate'], 3), 'lifetime': sy['lifetime'], 'size': sy['size'],
                                    'point_forces': sy['point_forces'], 'particles': b['particles'],
                                    'plume': [round(b['width'], 1), round(b['height'], 1)],
                                    'centre': [round(v, 1) for v in b['centre']], 'visible_texels': b['visible']}
                                   for sy, b in zip(systems, bakes[model])]
    wanted = {m.casefold(): (m, k) for m, k in GLOW_MODELS}
    rows, seen = [], set()
    for master, cell in cells:
        if cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            if ref.get('deleted'):
                continue
            obj = objects.get(ref.get('id', '').casefold())
            model = (obj or {}).get('model', '').replace('\\', '/').casefold()
            if model not in wanted:
                continue
            name, kind = wanted[model]
            key = reference_key(master, ref['number'], lists)
            if key is None:
                report['skipped'].append({'id': ref['id'], 'master': master, 'number': ref['number'],
                                          'why': 'no reference key'})
                continue
            if key in seen:
                continue
            seen.add(key)
            scale = float(ref.get('scale', 1) or 1)
            axes = placement_axes(ref['rotation_radians'])
            for s, b in enumerate(bakes[name]):
                at = np.array(ref['position'], dtype=float) + axes @ (np.array(b['centre']) * scale)
                cx, cy = int(math.floor(at[0] / CELL)), int(math.floor(at[1] / CELL))
                rows.append((cx, cy, float(at[0]), float(at[1]), float(at[2]),
                             min(65535, int(round(b['width'] * scale))), min(65535, int(round(b['height'] * scale))),
                             GLOW_KINDS[kind], b['frame0'], len(b['frames']), (key * 37 + s * 101) & 255, key))
                report['by_kind'][kind] = report['by_kind'].get(kind, 0) + 1
    if len(rows) > GLOW_ROWS_MAX:
        raise ValueError('glow table exceeds the engine\'s bounds: %d rows' % len(rows))
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[11]))
    report['rows'] = len(rows)
    report['cells'] = len({(r[0], r[1]) for r in rows})
    report['sprite_frames'] = len(frames)
    return rows, sprite_bytes(frames) if frames else None, report


def glow_table(rows):
    return GLOW_MAGIC + struct.pack('<I', len(rows)) + b''.join(GLOW_ROW.pack(*r) for r in rows)


PAIR_REACH = 1000.0              # original units: the two plumes of one pylon's arms (measured 385 to 505 apart)


def pylon_pairs(rows, kind=GLOW_KINDS['ghostfence']):
    """The KIND rows' mutual-nearest pairs [(i, j)] (by plume centre, within PAIR_REACH) and the rows left alone: every
    Ghostfence pylon carries two emitters, one on each arm."""
    import numpy as np
    idx = [i for i, r in enumerate(rows) if r[7] == kind]
    if len(idx) < 2:
        return [], idx
    p = np.array([rows[i][2:5] for i in idx], dtype=float)
    d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    near = d.argmin(axis=1)
    pairs = sorted({(min(a, int(b)), max(a, int(b))) for a, b in enumerate(near)
                    if int(near[int(b)]) == a and d[a, int(b)] <= PAIR_REACH})
    paired = {k for pair in pairs for k in pair}
    return [(idx[a], idx[b]) for a, b in pairs], [idx[k] for k in range(len(idx)) if k not in paired]


def check_glow(rows):
    """The build's keeper of the glow table: every row names its placement's reference (its hide row), no reference
    twice, every Ghostfence row in a pylon's pair. Returns the problems ([] when none)."""
    problems = []
    refs = [r[11] for r in rows]
    if any(not ref for ref in refs):
        problems.append('%d glow rows without a reference' % sum(1 for ref in refs if not ref))
    if len(set(refs)) != len(refs):
        problems.append('a reference on two glow rows')
    pairs, alone = pylon_pairs(rows)
    if alone:
        problems.append('%d Ghostfence plumes without the other of their pylon: %s' % (
            len(alone), ', '.join('%d' % rows[i][11] for i in alone[:8])))
    return problems


def read_glow_table(raw):
    """Rows of an AWG1 table as dicts (tests, measurements)."""
    if raw[:4] != GLOW_MAGIC:
        raise ValueError('Not a glow table')
    count = struct.unpack_from('<I', raw, 4)[0]
    if len(raw) != 8 + count * GLOW_ROW.size:
        raise ValueError('Glow table has the wrong shape')
    names = ('cx', 'cy', 'x', 'y', 'z', 'width', 'height', 'kind', 'frame0', 'frames', 'phase', 'reference')
    return [dict(zip(names, GLOW_ROW.unpack_from(raw, 8 + i * GLOW_ROW.size))) for i in range(count)]


# ---------------------------------------------------------------- the curtain

def key_value(keys, t):
    """The value of NiUVData keys [(time, value, forward, backward)] at T: OpenMW's cubic Hermite between keys for
    quadratic keys (components/nifosg/controller.hpp interpolate: a.mValue, b.mValue, a's out tangent = the second
    tangent read, b's in tangent = the first), held at the ends."""
    if not keys:
        return 0.0
    if t <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            x = 0.0 if b[0] <= a[0] else (t - a[0]) / (b[0] - a[0])
            x2, x3 = x * x, x * x * x
            return (a[1] * (2 * x3 - 3 * x2 + 1) + b[1] * (-2 * x3 + 3 * x2) + a[3] * (x3 - 2 * x2 + x) +
                    b[2] * (x3 - x2))
    return keys[-1][1]


def curtain_layers(raw, N):
    """[{'texture', 'u', 'v' (keys), 'start', 'stop'}] of a curtain NIF's shapes with an NiUVController, in file
    order."""
    data = N.Data()
    data.read(io.BytesIO(raw))
    out = []
    for block in data.blocks:
        if type(block).__name__ != 'NiTriShape':
            continue
        ctrl = block.controller
        while ctrl is not None and type(ctrl).__name__ != 'NiUVController':
            ctrl = ctrl.next_controller
        if ctrl is None or ctrl.data is None:
            continue
        texture, _ = _texture_and_blend(block)
        groups = ctrl.data.uv_groups

        def keys(g):
            return [(float(k.time), float(k.value), float(getattr(k, 'forward', 0.0)),
                     float(getattr(k, 'backward', 0.0))) for k in g.keys]
        out.append({'texture': texture, 'u': keys(groups[0]), 'v': keys(groups[1]),
                    'start': float(ctrl.start_time), 'stop': float(ctrl.stop_time)})
    return out


def drawn_block(pixels, size):
    """The 64 x 64 mip-0 block the engine's turbulent drawing reads of a SIZE x SIZE texture: a smaller one tiled as
    the CHIM loader tiles it (chim_format.c ChimFormat_TileTurbulent), a 64 one as it is."""
    if size == DRAWN:
        return bytes(pixels[:DRAWN * DRAWN])
    return bytes(pixels[(y % size) * size + x % size] for y in range(DRAWN) for x in range(DRAWN))


def _curtain_stores(stores):
    """{fnv: (size, store, texture id, name)} of the curtain textures in the CHIM stores (world.cwi paths): every
    turbulent texture ('*' name) a model named CURTAIN_PREFIX* draws (32 x 32 in the open world; a store could hold a
    64 x 64 one), hashed over the 64 x 64 block the engine draws from (drawn_block). A curtain drawn still (the room
    store's curtain piece: an emissive texture) is not composed and not listed."""
    from chim import format as F
    from chim import placed, reach, terc, thgt  # noqa: F401 (world formats 0.8-0.11, as tools/chim/flames.py)
    from chim import room_records  # noqa: F401 (the room store's world format 0.13)
    out, counts = {}, {}
    for cwi in stores:
        cwi = Path(cwi)
        _, files, models, textures = F.read_index(cwi.read_bytes())

        def record(entry):
            with (cwi.parent / files[entry['file']]['path']).open('rb') as f:
                f.seek(entry['offset'])
                return f.read(entry['bytes'])
        used = set()
        n = turbulent = 0
        for m in models:
            if not m['name'].casefold().startswith(CURTAIN_PREFIX):
                continue
            n += 1
            used.update(F.read_texture_refs(F.read_brush_image(record(m))[2]))
        for tid in sorted(used):
            raw = record(textures[tid])
            name, w, h, o0 = struct.unpack_from('<16sIII', raw, 0)
            if not name.startswith(b'*'):
                continue            # drawn still (a room's emissive curtain): not a turbulent texture, nothing to compose
            if o0 != 40 or w != h or w not in (CURTAIN_SIZE, DRAWN):
                raise ValueError('%s: curtain texture %d is %dx%d at %d, not %d or %d square at 40' % (
                    cwi, tid, w, h, o0, CURTAIN_SIZE, DRAWN))
            out.setdefault(fnv1a(drawn_block(raw[o0:o0 + w * h], w)), (w, str(cwi), tid, textures[tid]['name']))
            turbulent += 1
        counts[str(cwi)] = {'models': n, 'textures': len(used), 'turbulent': turbulent}
    return out, counts


def curtain_table(data_files, stores, palette):
    """(AWC1 bytes, report): the curtain's three layers from x/ex_gg_fence_s_01.nif (every curtain model must carry the
    same layers), their texture intensities, motion tables and the colour ramp; the checksums of the curtain textures
    of STORES. None when no store holds a curtain model."""
    import numpy as np
    from PIL import Image
    from particle_emitters import _sources
    from prepare_scenery import nif_reader
    from sky_palette_overlay import BANK
    N = nif_reader()
    markers = EditorMarkers(data_files, masters=GAME_MASTERS)
    layers = None
    for model in CURTAIN_MODELS:
        raw = markers.raw(model)
        if not raw:
            continue
        these = curtain_layers(raw, N)
        if layers is None:
            layers, first = these, model
        elif [(a['texture'], a['u'], a['v']) for a in these] != [(a['texture'], a['u'], a['v']) for a in layers]:
            raise ValueError('%s: its layers differ from %s' % (model, first))
    if not layers:
        return None, {'note': 'no curtain model in the game data'}
    hashes, counts = _curtain_stores(stores)
    if not hashes:
        return None, {'note': 'no CHIM store holds a curtain model', 'stores': counts}
    _, files = _sources(data_files)
    sources = sorted({a['texture'] for a in layers}, key=[a['texture'] for a in layers].index)
    levels, colours = [], []
    for stem in sources:
        rgba = _texture_rgba(files, stem)
        if rgba is None:
            raise ValueError('curtain texture %s not found' % stem)
        img = Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').resize((CURTAIN_SIZE, CURTAIN_SIZE),
                                                                           Image.Resampling.BOX)
        a = np.asarray(img, dtype=float) / 255.0
        intensity = (a[:, :, :3] @ np.array([0.3, 0.59, 0.11])) * a[:, :, 3]
        levels.append(np.clip(np.round(CURTAIN_LEVEL_MAX * intensity / max(1e-9, intensity.max())), 0,
                              CURTAIN_LEVEL_MAX).astype(np.uint8))
        w = rgba[:, :, 3:4]
        colours.append((rgba[:, :, :3] * w).sum(axis=(0, 1)) / max(1e-9, w.sum()))
    period = max(a['stop'] - a['start'] for a in layers)
    motion = motion_tables(layers, sources, period)
    nlevels = CURTAIN_LEVEL_MAX * len(layers) + 1
    ramp = ramp_indices(np.mean(colours, axis=0), nlevels, palette, tuple(BANK))
    raw = curtain_bytes({h: v[0] for h, v in hashes.items()}, [lv.tobytes() for lv in levels], motion, nlevels,
                        int(round(period * 1000)), pulse_steps(), ramp)
    report = {'sources': sources, 'period_s': period, 'levels': nlevels, 'pulses': CURTAIN_PULSES,
              'layers': [{'texture': sources[m[0]], 'u': m[1][::8], 'v': m[2][::8]} for m in motion],
              'textures': [{'fnv': '%08x' % h, 'size': size, 'store': Path(s).parent.name, 'id': tid, 'key': name}
                           for h, (size, s, tid, name) in sorted(hashes.items())],
              'stores': counts, 'bytes': len(raw)}
    return raw, report


def motion_tables(layers, sources, period):
    """[(source index, U offsets, V offsets)] of LAYERS (curtain_layers): each layer's keys at CURTAIN_STEPS steps of
    the loop, in texels of the CURTAIN_SIZE texture (U rounded, V down, mod the size)."""
    out = []
    for a in layers:
        us, vs = [], []
        for k in range(CURTAIN_STEPS):
            t = a['start'] + period * k / CURTAIN_STEPS
            us.append(int(round(key_value(a['u'], t) * CURTAIN_SIZE)))
            vs.append(int(math.floor(key_value(a['v'], t) * CURTAIN_SIZE + 1e-6)) % CURTAIN_SIZE)
        if any(not -128 <= u <= 127 for u in us):
            raise ValueError('curtain sway past a byte')
        out.append((sources.index(a['texture']), us, vs))
    return out


def pulse_steps():
    """The pulse's 16 steps over CURTAIN_PULSE_MS: which of the CURTAIN_PULSES ramps, a slow sine."""
    return bytes(int(round((CURTAIN_PULSES - 1) * (0.5 + 0.5 * math.sin(2 * math.pi * k / 16)))) for k in range(16))


def ramp_indices(colour, nlevels, palette, exclude):
    """CURTAIN_PULSES x NLEVELS palette indices: the curtain's own hue (COLOUR, its textures' mean) from CURTAIN_FLOOR
    to full at CURTAIN_SAT of the summed levels, CURTAIN_GLOW brighter than the texture and whitening past white,
    times the pulse's gain; never an index of EXCLUDE (255 and the sky bank)."""
    import numpy as np
    hue = np.asarray(colour, dtype=float)
    hue = hue / max(1e-9, float(hue.max()))
    ramp = []
    for p in range(CURTAIN_PULSES):
        gain = 1 + CURTAIN_PULSE_DEPTH * (2 * p / (CURTAIN_PULSES - 1) - 1)
        for s in range(nlevels):
            b = CURTAIN_FLOOR + (1 - CURTAIN_FLOOR) * min(1.0, s / (CURTAIN_SAT * (nlevels - 1)))
            rgb = hue * 255 * b * CURTAIN_GLOW * gain
            over = max(0.0, float(rgb.max()) - 255)
            ramp.append(np.clip(rgb + over * 0.6, 0, 255))
    return _nearest(palette, np.array(ramp), exclude=(255,) + tuple(exclude)).tobytes()


def curtain_bytes(hashes, levels, motion, nlevels, period_ms, pulse, ramp):
    """The AWC1 table: HASHES {fnv: texture size}, LEVELS [size*size bytes] a source, MOTION (motion_tables), the
    PULSE steps and the RAMP (CURTAIN_PULSES x NLEVELS)."""
    head = CURTAIN_HEAD.pack(CURTAIN_MAGIC, 1, CURTAIN_SIZE, len(levels), len(motion), nlevels, CURTAIN_PULSES,
                             len(hashes), CURTAIN_STEPS, period_ms, CURTAIN_PULSE_MS)
    rows = b''.join(struct.pack('<BB', s, 0) + struct.pack('<%db' % CURTAIN_STEPS, *us) + bytes(vs)
                    for s, us, vs in motion)
    if len(ramp) != CURTAIN_PULSES * nlevels or len(pulse) != 16:
        raise ValueError('curtain ramp or pulse of the wrong size')
    return (head + b''.join(struct.pack('<IHH', h, hashes[h], 0) for h in sorted(hashes)) + b''.join(levels) + rows +
            bytes(pulse) + bytes(ramp))


def read_curtain_table(raw):
    """The parts of an AWC1 table (tests, the compose's Python twin)."""
    (magic, version, size, nsources, nlayers, levels, pulses, ntextures, steps, period_ms,
     pulse_ms) = CURTAIN_HEAD.unpack_from(raw, 0)
    if magic != CURTAIN_MAGIC or version != 1:
        raise ValueError('Not a curtain table')
    at = CURTAIN_HEAD.size
    hashes = [struct.unpack_from('<IHH', raw, at + 8 * i)[:2] for i in range(ntextures)]
    at += 8 * ntextures
    sources = [raw[at + i * size * size:at + (i + 1) * size * size] for i in range(nsources)]
    at += nsources * size * size
    layers = []
    for _ in range(nlayers):
        source = raw[at]
        us = list(struct.unpack_from('<%db' % steps, raw, at + 2))
        vs = list(raw[at + 2 + steps:at + 2 + 2 * steps])
        layers.append({'source': source, 'u': us, 'v': vs})
        at += 2 + 2 * steps
    pulse = list(raw[at:at + 16])
    at += 16
    ramp = raw[at:at + pulses * levels]
    if at + pulses * levels != len(raw):
        raise ValueError('Curtain table has the wrong shape')
    return {'size': size, 'levels': levels, 'pulses': pulses, 'steps': steps, 'period_ms': period_ms,
            'pulse_ms': pulse_ms, 'hashes': hashes, 'sources': sources, 'layers': layers, 'pulse': pulse, 'ramp': ramp}


def curtain_compose(table, t_ms):
    """The composed curtain texture (size x size palette indices) at T_MS: the engine's AW_CurtainCompose
    (aw_curtain_rules.c), the same integer steps."""
    size, mask = table['size'], table['size'] - 1
    t = t_ms % table['period_ms']
    step = t * table['steps'] // table['period_ms']
    p = table['pulse'][(t_ms % table['pulse_ms']) * 16 // table['pulse_ms']]
    ramp = table['ramp'][p * table['levels']:(p + 1) * table['levels']]
    offsets = [(l['u'][step] & mask, l['v'][step] & mask, table['sources'][l['source']]) for l in table['layers']]
    out = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            s = 0
            for du, dv, src in offsets:
                s += src[((y + dv) & mask) * size + ((x + du) & mask)]
            out[y * size + x] = ramp[s]
    return bytes(out)


# ---------------------------------------------------------------- the image step

GLOW_CONFIG_LINES = (b'// The Ghostfence (GHOSTFENCE-PARTICLES-NOT-DRAWN-68): the pylons\' glow and the blight cloud\'s plume\n'
                     b'// (dbg glow on|off; off until its frame cost is measured), how many and how far (dbg glow draw,\n'
                     b'// dbg glow range), and the curtain (dbg curtain 0 rippling, 1 the original\'s scrolling layers).\n'
                     b'aw_glow 0\naw_glow_draw 8\naw_glow_range 2048\naw_curtain 0\n')


def chim_stores(args, id1):
    """The world.cwi of the CHIM stores this image is made from: the base world (--chim-world) and the rooms
    (--chim-interiors), those that exist."""
    out = []
    for folder, sub in ((getattr(args, 'chim_world', None), 'chim'), (getattr(args, 'chim_interiors', None), 'chimi')):
        if folder and (Path(folder) / sub / 'world.cwi').is_file():
            out.append(Path(folder) / sub / 'world.cwi')
    return out


def write(args, id1, out):
    """The image step's part (tools/build_aga.py write_ghostfence): id1/world/glow.awg, glow.spr and curtain.awc, the
    receipt out/ghostfence-effects.json and the settings' lines in id1/default-game.cfg. Returns the receipt."""
    id1, out = Path(id1), Path(out)
    data = getattr(args, 'data_files', None)
    receipt = {'format': 'AmiWind Ghostfence effects 1'}
    if data:
        palette = (id1 / 'gfx/palette.lmp').read_bytes()
        rows, sprite, report = glow(data, palette)
        problems = check_glow(rows)
        if problems:
            raise SystemExit('Ghostfence glow: ' + '; '.join(problems))
        report['pylon_pairs'] = len(pylon_pairs(rows)[0])
        (id1 / 'world').mkdir(parents=True, exist_ok=True)
        (id1 / GLOW_TABLE).write_bytes(glow_table(rows))
        if sprite is not None:
            (id1 / GLOW_SPRITE).write_bytes(sprite)
        receipt['glow'] = report
        curtain, creport = curtain_table(data, chim_stores(args, id1), palette)
        if curtain is not None:
            (id1 / CURTAIN_TABLE).write_bytes(curtain)
        receipt['curtain'] = creport
    path = id1 / 'default-game.cfg'
    if path.is_file():
        raw = path.read_bytes()
        path.write_bytes(raw + (b'' if raw.endswith(b'\n') else b'\n') + GLOW_CONFIG_LINES)
    receipt['config'] = ['aw_glow 0', 'aw_glow_draw 8', 'aw_glow_range 2048', 'aw_curtain 0']
    (out / RECEIPT).write_text(json.dumps(receipt, indent=1, default=str) + '\n', encoding='utf-8', newline='\n')
    g = receipt.get('glow') or {}
    print('Ghostfence: %s glow rows in %s cells (%s), %s sprite frames; curtain table %s' % (
        g.get('rows', 0), g.get('cells', 0), g.get('by_kind', {}), g.get('sprite_frames', 0),
        '%d bytes' % receipt['curtain']['bytes'] if receipt.get('curtain', {}).get('bytes') else 'not written'),
        flush=True)
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    m = sub.add_parser('measure', help='the glow rows and plumes and the curtain table, printed (read only)')
    m.add_argument('--data-files', type=Path, required=True)
    m.add_argument('--store', type=Path, action='append', default=[], help='a CHIM store\'s world.cwi')
    m.add_argument('--palette', type=Path, help='gfx/palette.lmp (default: a grey ramp)')
    m.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    palette = a.palette.read_bytes() if a.palette else bytes(v for i in range(256) for v in (i, i, i))
    rows, sprite, report = glow(a.data_files, palette)
    curtain, creport = curtain_table(a.data_files, a.store, palette)
    pairs, alone = pylon_pairs(rows)
    result = {'glow': report, 'glow_sprite_bytes': len(sprite or b''), 'glow_table_bytes': len(glow_table(rows)),
              'glow_problems': check_glow(rows), 'pylon_pairs': len(pairs), 'unpaired': len(alone),
              'pair_distance': sorted(round(math.dist(rows[i][2:5], rows[j][2:5])) for i, j in pairs)[::11],
              'curtain': creport}
    if curtain is not None:
        table = read_curtain_table(curtain)
        result['curtain_compose_fnv'] = {t: '%08x' % fnv1a(curtain_compose(table, t)) for t in (0, 1000, 4125, 7999)}
    text = json.dumps(result, indent=1, default=str)
    if a.json:
        a.json.write_text(text + '\n', encoding='utf-8', newline='\n')
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
