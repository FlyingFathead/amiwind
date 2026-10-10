# SPDX-License-Identifier: GPL-3.0-only
"""Lava as a Quake liquid: the one implementation every converter uses (docs/LAVA.md).

Morrowind's molten lava is a pool mesh (a flat stack of molten and crust layers) on an
activator whose script hurts an actor standing on it. Quake's own lava is a liquid brush
whose texture name starts with "*lava": the BSP compiler gives it CONTENTS_LAVA and
turbulent faces, the renderer draws those faces with the warp span drawer, fully bright and
without the surface cache. This module maps the first onto the second:

- molten_objects(master bytes): the objects whose script hurts a standing actor (the lava
  contract: damage per second and loop sound), decided from the game's records only;
- pool_points / footprint: the pool's upward molten faces, placed (rotation, scale, position)
  and reduced to a convex plan polygon and a surface height;
- pool_brushes: the liquid brush ("*lava", LIQUID_DEPTH deep) over a solid bed brush, as
  BSP-compiler map text, so the player stands with the feet in lava (waterlevel 1, no swimming);
- pool_entity: the "aw_lava" entity the engine reads for the rising embers (aw_lava.c);
- glow_lights: light records over the pool for the converters' light bake (AmiWind addition:
  the original lights lava caves with placed lights only);
- lava_texture: the 64 x 64 warp texture made from your own pool textures, crust laid over
  molten by its alpha; never stored in this repository.

The mode is the builder setting `lava` (config/build-defaults.json, --lava quake|static),
exported as AMIWIND_LAVA for every converter worker: quake (default) converts the pools to
liquid; static keeps the earlier behaviour (interior rooms leave the activator out, exterior
frames place the pool mesh as a solid model).
"""
import math
import os
import re
import struct

MODES = ('quake', 'static')
DEFAULT_MODE = 'quake'
VARIABLE = 'AMIWIND_LAVA'
TEXTURE = '*lava'
BED_TEXTURE = 'lavabed'
LIQUID_DEPTH = 8.0       # Quake units of lava above the bed: feet in lava, origin above it (waterlevel 1)
BED_THICKNESS = 16.0     # Quake units of solid under the liquid
GLOW_SPACING = 512.0     # Morrowind units between glow lights over a large pool
GLOW_HEIGHT = 48.0       # Morrowind units above the surface
GLOW_COLOUR = (255, 72, 24)
UP_NZ = 0.7

HURT = re.compile(r'^\s*hurtstandingactor\s*,?\s*([0-9.]+)', re.I | re.M)
LOOP_SOUND = re.compile(r'playloopsound3dvp\s*,?\s*"([^"]+)"', re.I)


def lava_mode():
    """The lava mode every converter reads (AMIWIND_LAVA, default quake)."""
    mode = os.environ.get(VARIABLE, DEFAULT_MODE).strip() or DEFAULT_MODE
    if mode not in MODES:
        raise ValueError(VARIABLE + ' must be quake or static')
    return mode


def export_lava(mode):
    """Export the resolved lava mode for every converter worker."""
    if mode not in MODES:
        raise ValueError('lava must be quake or static')
    os.environ[VARIABLE] = mode


def is_lava_texture(name):
    """True for a lava texture file name (tx_lava_molten.tga, textures/tx_ma_lava05.dds, ...).
    A name alone does not make lava molten: see molten_objects."""
    stem = (name or '').replace('\\', '/').rsplit('/', 1)[-1].casefold()
    return 'lava' in stem


def script_contract(text):
    """(damage per second while an actor stands on the object, loop sound) of a script's
    source; (0.0, '') when it does neither. Comments (after ';') are ignored."""
    code = '\n'.join(line.split(';', 1)[0] for line in text.splitlines())
    hurt = HURT.search(code)
    sound = LOOP_SOUND.search(code)
    return (float(hurt.group(1)) if hurt else 0.0), (sound.group(1) if sound else '')


def _cstr(raw):
    return raw.split(b'\0')[0].decode('cp1252', 'replace')


def molten_objects(raw):
    """{object id (casefolded): {'script', 'dps', 'sound'}} of one master: every object whose
    script hurts a standing actor. Scripts and objects are read in one pass."""
    from mwad.audit import records, subrecords
    contracts, scripted = {}, {}
    for tag, _flags, payload in records(raw):
        if tag == 'SCPT':
            s = dict(subrecords(payload))
            name = _cstr(s.get('SCHD', b'')[:32])
            dps, sound = script_contract(s.get('SCTX', b'').decode('cp1252', 'replace'))
            if name and dps > 0:
                contracts[name.casefold()] = {'dps': dps, 'sound': sound}
        elif tag in ('ACTI', 'STAT', 'DOOR', 'CONT', 'LIGH', 'MISC'):
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' in s and 'SCRI' in s and 'DELE' not in s:
                scripted[_cstr(s['NAME']).casefold()] = _cstr(s['SCRI'])
    return {obj: dict(script=script, **contracts[script.casefold()])
            for obj, script in sorted(scripted.items()) if script.casefold() in contracts}


_MOLTEN = {}


def molten_objects_of(path):
    """molten_objects of a master file, read once per process."""
    from pathlib import Path
    key = str(Path(path).resolve())
    if key not in _MOLTEN:
        _MOLTEN[key] = molten_objects(Path(path).read_bytes())
    return _MOLTEN[key]


# ---------------------------------------------------------------- geometry

def pool_points(vertices, faces, materials):
    """Mesh-local vertices of the pool's upward lava faces (rows x, y, z); empty when none."""
    import numpy as np
    lava = [i for i, m in enumerate(materials) if is_lava_texture(m.get('texture_source'))]
    P = np.asarray(vertices, dtype=float)[:, :3]
    F = np.asarray(faces, dtype=int)
    F = F[np.isin(F[:, 3], lava)] if lava else F[:0]
    if not len(F):
        return P[:0]
    n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    length = np.linalg.norm(n, axis=1)
    up = (length > 0) & (n[:, 2] >= UP_NZ * length)
    return P[np.unique(F[up][:, :3])] if up.any() else P[:0]


def convex_hull_2d(points):
    """Counter-clockwise convex hull of 2D points (monotone chain), without collinear points."""
    pts = sorted({(round(float(x), 4), round(float(y), 4)) for x, y in points})
    if len(pts) < 3:
        return [list(p) for p in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1] + upper[:-1]]


def footprint(points, rotation, scale, position):
    """(plan hull [[x, y], ...] counter-clockwise, surface z) of a placed pool in world units:
    world = local @ rotation.T * scale + position (prepare_scenery.world_bounds)."""
    import numpy as np
    w = np.asarray(points, dtype=float) @ np.asarray(rotation, dtype=float).T * float(scale)
    w = w + np.asarray(position, dtype=float)
    return convex_hull_2d(w[:, :2]), float(w[:, 2].max())


def to_quake(hull, top, centre, scale):
    """A footprint in world units -> Quake units: (point - centre) * scale."""
    cx, cy, cz = centre
    return [[(x - cx) * scale, (y - cy) * scale] for x, y in hull], (top - cz) * scale


def prism_brush(hull, zlo, zhi, texture):
    """Map text of the convex prism over a counter-clockwise plan hull from zlo to zhi."""
    from prepare_quake import brush
    n = len(hull)
    if n < 3 or not zhi > zlo:
        raise ValueError('A lava prism needs a polygon of 3 or more corners and a height')
    points = [[x, y, zlo] for x, y in hull] + [[x, y, zhi] for x, y in hull]
    faces = [(0, 1, 2), (n, n + 1, n + 2)] + [(k, (k + 1) % n, n + (k + 1) % n) for k in range(n)]
    return brush(points, faces, texture)


def pool_brushes(hull, top, depth=LIQUID_DEPTH, bed=BED_THICKNESS):
    """The pool as two brushes (Quake units): the liquid from top - depth to top ("*lava")
    and the solid bed under it, so a player stands in lava up to the shins."""
    return [prism_brush(hull, top - depth, top, TEXTURE),
            prism_brush(hull, top - depth - bed, top - depth, BED_TEXTURE)]


def polygon_centroid(hull):
    """Area centroid of a counter-clockwise polygon (its mean for a degenerate one)."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(hull, hull[1:] + hull[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        return [sum(p[0] for p in hull) / len(hull), sum(p[1] for p in hull) / len(hull)]
    return [cx / (3 * a), cy / (3 * a)]


def pool_entity(hull, top):
    """The "aw_lava" entity of one pool (Quake units): origin on the surface at the centroid,
    radius to the farthest corner. The engine reads it for the rising embers."""
    c = polygon_centroid(hull)
    radius = max(math.hypot(x - c[0], y - c[1]) for x, y in hull)
    return '{\n"classname" "aw_lava"\n"origin" "%.2f %.2f %.2f"\n"_aw_lava_radius" "%.2f"\n}' % (c[0], c[1], top, radius)


def glow_lights(hull, top, colour=GLOW_COLOUR, spacing=GLOW_SPACING, height=GLOW_HEIGHT):
    """Light records over a pool (world units, the interior light format of
    interior_lighting.cell_lighting: position, radius, color, flags): one per `spacing` grid
    cell whose centre lies in the pool (at least one, at the centroid)."""
    xs = [p[0] for p in hull]
    ys = [p[1] for p in hull]

    def inside(x, y):
        return all((bx - ax) * (y - ay) - (by - ay) * (x - ax) >= 0
                   for (ax, ay), (bx, by) in zip(hull, hull[1:] + hull[:1]))
    points = []
    y = min(ys) + spacing / 2
    while y < max(ys):
        x = min(xs) + spacing / 2
        while x < max(xs):
            if inside(x, y):
                points.append([x, y])
            x += spacing
        y += spacing
    if not points:
        points = [polygon_centroid(hull)]
    radius = int(round(spacing * 0.9))
    return [{'position': [round(x, 2), round(y, 2), round(top + height, 2)], 'radius': radius,
             'color': list(colour), 'flags': 0} for x, y in points]


def lava_texture(layers, size=64):
    """The warp texture (RGB PIL image, size x size) of a pool: layers = RGBA arrays of the
    pool's lava layers from bottom to top; each is laid over the result by its alpha (the
    crust over the molten flow). The first layer is opaque."""
    import numpy as np
    from PIL import Image
    if not layers:
        raise ValueError('A lava texture needs at least one layer')
    images = [np.asarray(Image.fromarray(np.asarray(l, dtype=np.uint8)).convert('RGBA')
                         .resize((size, size), Image.Resampling.LANCZOS), dtype=float) for l in layers]
    out = images[0][:, :, :3]
    for im in images[1:]:
        a = im[:, :, 3:4] / 255.0
        out = out * (1 - a) + im[:, :, :3] * a
    return Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8), 'RGB')


def pool_layers(vertices, faces, materials):
    """Texture sources of the pool's lava layers, bottom to top (by the height of their faces)."""
    import numpy as np
    P = np.asarray(vertices, dtype=float)
    F = np.asarray(faces, dtype=int)
    rows = []
    for i, m in enumerate(materials):
        if not is_lava_texture(m.get('texture_source')):
            continue
        f = F[F[:, 3] == i]
        if len(f):
            rows.append((float(P[f[:, :3].ravel(), 2].mean()), i, m['texture_source']))
    return [t for _, _, t in sorted(rows)]


# ---------------------------------------------------------------- converters

def pools_of(data_files, refs, molten, source=None):
    """The molten pools among placed references (dicts with id, model, position,
    rotation_radians, scale): [{reference, id, model, hull, top, layers, dps, sound}] in world
    units, in reference order. molten: molten_objects_of(master). Meshes are read with the
    converter's own NIF reader from your Morrowind files (loose files first, then archives)."""
    from prepare_scenery import model_geometry, nif_reader, reference_rotation
    from mwad.scene import unpack_geometry
    shapes, out = {}, []
    for ref in refs:
        if ref.get('deleted') or ref.get('id', '').casefold() not in molten:
            continue
        if source is None:      # only rooms and frames with lava read meshes
            from world_estimate_data import MeshSource
            source = MeshSource(data_files)
        model = ref['model'].replace('\\', '/').casefold()
        model = model if model.startswith('meshes/') else 'meshes/' + model
        if model not in shapes:
            raw, _ = source.read(model)
            geometry, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
            vv, ff, _ = unpack_geometry(geometry)
            shapes[model] = (pool_points(vv, ff, materials), pool_layers(vv, ff, materials))
        points, layers = shapes[model]
        if not len(points):
            raise ValueError('Lava pool without upward lava faces: ' + model)
        hull, top = footprint(points, reference_rotation(ref), ref.get('scale', 1.0), ref['position'])
        contract = molten[ref['id'].casefold()]
        out.append({'reference': ref.get('number'), 'id': ref['id'], 'model': model, 'hull': hull, 'top': top,
                    'layers': layers, 'dps': contract['dps'], 'sound': contract['sound']})
    return out


def wad_entries(assets_texture, layers, palette_image, size=64):
    """[(name, lump type, miptex)] of the warp texture and the bed texture, quantized to the
    game palette. assets_texture(name) -> RGBA array (npc_geometry.Assets.texture)."""
    from PIL import Image
    from prepare_quake import miptex
    liquid = lava_texture([assets_texture(t) for t in layers], size)
    bed = Image.new('RGB', (16, 16), (52, 30, 24))
    return [(TEXTURE, 68, miptex(TEXTURE, liquid.quantize(palette=palette_image, dither=Image.Dither.NONE))),
            (BED_TEXTURE, 68, miptex(BED_TEXTURE, bed.quantize(palette=palette_image, dither=Image.Dither.NONE)))]


def map_parts(pools, centre, scale):
    """(world brush texts, entity texts, records) of pools for a BSP-compiler map in Quake
    units: point_q = (point - centre) * scale."""
    brushes, entities, records = [], [], []
    for p in pools:
        hull, top = to_quake(p['hull'], p['top'], centre, scale)
        brushes += pool_brushes(hull, top)
        entities.append(pool_entity(hull, top))
        records.append({'reference': p['reference'], 'id': p['id'], 'model': p['model'],
                        'top': round(top, 2), 'corners': len(hull), 'dps': p['dps'], 'sound': p['sound']})
    return brushes, entities, records


def quake_bounds(pools, centre, scale):
    """(low, high) Quake-unit box of the pools' brushes, bed included; None without pools."""
    if not pools:
        return None
    xs, ys, zs = [], [], []
    for p in pools:
        hull, top = to_quake(p['hull'], p['top'], centre, scale)
        xs += [h[0] for h in hull]
        ys += [h[1] for h in hull]
        zs += [top, top - LIQUID_DEPTH - BED_THICKNESS]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]


# ---------------------------------------------------------------- sound

LOOP_LIMIT = 4           # looping lava emitters per map: Quake mixes every static sound each frame
LOOP_ATTENUATION = 2     # aw_loop attenuation (as the ship's hull loop, prepare_intro.ship_ambience)
SOUND_FOLDER = 'env'


def sound_record(raw, name):
    """(sound file, volume 0..1) of the master's SOUN record `name` (casefolded match); None when absent."""
    from mwad.audit import records, subrecords
    for tag, _flags, payload in records(raw):
        if tag != 'SOUN':
            continue
        s = dict(subrecords(payload))
        if _cstr(s.get('NAME', b'')).casefold() == name.casefold() and 'FNAM' in s:
            data = s.get('DATA', b'\xff')
            return _cstr(s['FNAM']), data[0] / 255.0
    return None


def sound_stem(name):
    """The game-side file name of a lava loop: env/<name, letters and digits only>.wav."""
    return SOUND_FOLDER + '/' + (re.sub(r'[^a-z0-9]+', '_', name.casefold()).strip('_') or 'lava') + '.wav'


def loop_points(pools, limit=LOOP_LIMIT):
    """Up to `limit` emitter points (world units, on the surface) spread over the pools: the largest pool's
    centroid first, then each time the pool centroid farthest from every chosen one (farthest-point order)."""
    if not pools:
        return []

    def area(hull):
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(hull, hull[1:] + hull[:1]))) / 2
    points = [(polygon_centroid(p['hull']), p['top'], area(p['hull']), p) for p in pools]
    chosen = [max(points, key=lambda q: (q[2], -q[0][0], -q[0][1]))]
    while len(chosen) < min(limit, len(points)):
        def gap(q):
            return min(math.hypot(q[0][0] - c[0][0], q[0][1] - c[0][1]) for c in chosen)
        best = max((q for q in points if q not in chosen), key=lambda q: (gap(q), q[2]))
        if gap(best) <= 0:
            break
        chosen.append(best)
    return [{'origin': [c[0][0], c[0][1], c[1]], 'sound': c[3]['sound']} for c in chosen]


def loop_entities(pools, centre, scale, volumes, limit=LOOP_LIMIT):
    """aw_loop entity texts (Quake units) of a map's lava pools; volumes: {sound name: volume 0..1}."""
    out = []
    for p in loop_points([p for p in pools if p.get('sound') in volumes], limit):
        x, y, z = [(p['origin'][i] - centre[i]) * scale for i in range(3)]
        out.append('{\n"classname" "aw_loop"\n"aw_voice" "%s"\n"origin" "%.2f %.2f %.2f"\n"aw_volume" "%.3f"\n'
                   '"aw_attenuation" "%d"\n}' % (sound_stem(p['sound']), x, y, z, volumes[p['sound']],
                                                 LOOP_ATTENUATION))
    return out


def convert_sounds(data_files, pools, sound_root, ffmpeg='ffmpeg'):
    """Convert the pools' loop sounds from the user's own files into sound_root/env/*.wav (11,025 Hz 8-bit mono,
    looping from the start, prepare_intro.ship_hull_convert); returns {sound name: volume} and the receipts."""
    from pathlib import Path
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets
    from prepare_intro import ship_hull_convert
    names = sorted({p['sound'] for p in pools if p.get('sound')})
    if not names:
        return {}, []
    raw = child_ci(Path(data_files), 'Morrowind.esm').read_bytes()
    assets = Assets(Path(data_files), BSA(child_ci(Path(data_files), 'Morrowind.bsa')))
    volumes, receipts = {}, []
    for name in names:
        rec = sound_record(raw, name)
        if rec is None:
            raise ValueError('Lava loop sound has no sound record: ' + name)
        target = Path(sound_root) / sound_stem(name)
        if not target.is_file():
            # rooms convert in parallel workers: write beside the target, then replace it atomically
            import os
            part = target.with_name('%s.%d.part.wav' % (target.stem, os.getpid()))
            receipts.append(dict(ship_hull_convert(assets, rec[0], part, ffmpeg), name=name))
            os.replace(part, target)
        volumes[name] = rec[1]
    return volumes, receipts


# ---------------------------------------------------------------- CHIM glow (the night lamp table)

LAMP_CLASS = 8           # lamps.awl class of a lava glow row (light_sources.LAVA_GLOW_CLASS; 1-7 are lights)
GLOW_GRID = 512.0        # Morrowind units: pools whose centres share a square of this size share one glow row


def exterior_pools(data_files):
    """Every molten pool of the exterior cells of Morrowind.esm, in world units (pools_of rows plus 'cell')."""
    from pathlib import Path
    from mwad.audit import cell_data, records, subrecords
    from mwad.paths import child_ci
    raw = child_ci(Path(data_files), 'Morrowind.esm').read_bytes()
    molten = molten_objects(raw)
    models, refs = {}, []
    for tag, _flags, payload in records(raw):
        if tag in ('ACTI', 'STAT', 'DOOR', 'CONT', 'LIGH', 'MISC'):
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' in s and 'MODL' in s and _cstr(s['NAME']).casefold() in molten:
                models[_cstr(s['NAME']).casefold()] = _cstr(s['MODL'])
        elif tag == 'CELL':
            subs = list(subrecords(payload))
            data = next((v for k, v in subs if k == 'DATA'), b'')
            if len(data) < 12 or struct.unpack_from('<I', data)[0] & 1:
                continue
            cell = cell_data(subs)
            for r in cell['refs']:
                if not r.get('deleted') and r.get('id', '').casefold() in molten and 'position' in r:
                    refs.append(dict(r, cell=[cell['x'], cell['y']]))
    for r in refs:
        r['model'] = models.get(r['id'].casefold(), '')
    refs = [r for r in refs if r['model']]
    pools = pools_of(data_files, refs, molten)
    if len(pools) != len(refs):
        raise ValueError('Every exterior lava reference must give one pool')
    for p, r in zip(pools, refs):      # pools_of keeps the order of its molten references, one pool each
        p['cell'] = r['cell']
    return pools


def glow_rows(pools, grid=GLOW_GRID):
    """lamps.awl rows (light_sources.LAMP_ROW: cell x, cell y, x, y, z, radius, class, colour) for the CHIM glow:
    one row per occupied grid square at the mean of its pool centres, just above the highest surface. The engine
    lights the nearest of them at night like the lamps (aw_lamps.c: a torch's worth of light each)."""
    squares = {}
    for p in pools:
        c = polygon_centroid(p['hull'])
        squares.setdefault((math.floor(c[0] / grid), math.floor(c[1] / grid)), []).append((c, p['top']))
    rows = []
    for _, items in sorted(squares.items()):
        x = sum(c[0] for c, _ in items) / len(items)
        y = sum(c[1] for c, _ in items) / len(items)
        z = max(t for _, t in items) + GLOW_HEIGHT
        rows.append((math.floor(x / 8192), math.floor(y / 8192), x, y, z, int(GLOW_SPACING), LAMP_CLASS, 1))
    return rows
