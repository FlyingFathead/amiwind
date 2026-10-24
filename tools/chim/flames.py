#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Static flames of a CHIM frame: the aw_flame entities of its placements, for its frame map.

The engine draws a placed fire's flame from the aw_flame entities of the map it has loaded
(engine/aga/src/aw_guard_torch.c static_flames_load: cl.worldmodel's entity text, at most
STATIC_FLAME_MAX per map, the best STATIC_FLAME_DRAW on screen within 640 units animated each frame).
The room and town converters write one aw_flame per particle emitter of a placed mesh
(tools/prepare_mesh_bsp.py flame_entities). A CHIM model keeps the same emitters in its own entity lump,
in the model frame (chim.models.variant_flames; docs/chim/WORLD_FORMAT.md "Model records"), but nothing
read them: the frame maps of CHIM towns and regions carried no aw_flame, so every campfire, brazier, fire
pit and flame lamp outdoors on CHIM was drawn without its fire (CHIM-EXTERIOR-FLAMES-MISSING-48).

frame_rows turns the emitters of every placement a frame owns into frame-local aw_flame rows (the model
frame turned by the placement's angles, as the engine turns the model). The fire itself is the engine's
one flame animation (flame_particle with the hearth colour table, plus Quake ember particles): nothing per
fire is stored but its row, a few dozen bytes of entity text.

    python3 tools/chim/flames.py measure CHIM_WORLD [--master Morrowind.esm] [--lamps lamps.awl]
                                  [--regions chim-regions.json] [--jobs N] [--json OUT]
"""
import argparse
import collections
import json
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# engine/aga/src/aw_guard_torch.c: STATIC_FLAME_MAX flames read per map, the rest ignored (FLAMES-CAP-31)
STATIC_FLAME_MAX = 128
FLAME_CLASS = 'aw_flame'
# Shape particle size from which the engine draws a flame with the hearth colour table and embers
# (aw_guard_torch.c AW_StaticFlamesDraw: shape[0] >= 4)
HEARTH_SIZE = 4.0
_ENTITY = re.compile(r'\{([^{}]*)\}')
_FIELD = re.compile(r'"([^"]*)"\s+"([^"]*)"')
# Meshes whose particle emitters are not fire although the emitter's own name passed the converter's rule
# (prepare_scenery.FLAME_SKIP reads the emitter name only): the blight and mist clouds, lava sparks, steam and
# vents, the ash mire. Measured on the v0.0.47 CHIM world: 23 meshes carry emitters, 10 of them these. A flame
# on them would burn in a cloud of blight or over a steam vent, so the frame map leaves them out (counted).
NOT_FIRE_MESH = ('blight', 'mist', 'steam', 'spark', 'smoke', 'vent', 'ashmire', 'dust', 'fog', 'bubble')


def fire_mesh(name):
    """True when a CHIM model (its index name, e.g. 'l/light_fire' or 'x/terrain_lava_vent@t1') may carry flames."""
    stem = name.rsplit('/', 1)[-1].split('@', 1)[0].split('#', 1)[0].casefold()
    stem = stem.replace('nosmoke', '')          # light_fire_nosmoke is a fire without its smoke
    return not any(k in stem for k in NOT_FIRE_MESH)


def model_flames(image):
    """The aw_flame emitters in a CHIM model record's entity lump: [{'origin': (x, y, z) model frame,
    'size': text, 'shape': text or None}] in lump order; [] when it has none."""
    from chim import format as F
    raw = F.read_brush_image(image)[0]
    text = raw.split(b'\0', 1)[0].decode('latin-1')
    out = []
    for body in _ENTITY.findall(text):
        keys = dict(_FIELD.findall(body))
        if keys.get('classname') != FLAME_CLASS:
            continue
        origin = tuple(float(v) for v in keys['origin'].split())
        if len(origin) != 3 or not all(math.isfinite(v) for v in origin):
            raise ValueError('aw_flame emitter with a bad origin: %r' % keys.get('origin'))
        out.append({'origin': origin, 'size': keys.get('aw_flame_size', '1'), 'shape': keys.get('aw_flame_shape')})
    return out


def record_angles(record):
    """Quake angles (pitch, yaw, roll) a placement record turns its model by: the 0.8 record's three, or the
    yaw of an earlier record."""
    return tuple(record['angles']) if 'angles' in record else (0.0, record['yaw'], 0.0)


def placed_flames(record, flames):
    """Frame-local aw_flame rows of one placement record (its model's emitters, model_flames): world =
    origin + model_matrix(angles) @ emitter, as the engine places the model (chim.placed.model_matrix)."""
    import numpy as np
    from chim.placed import model_matrix
    if not flames:
        return []
    m = model_matrix(record_angles(record))
    origin = np.array(record['origin'], dtype=float)
    rows = []
    for f in flames:
        p = origin + m @ np.array(f['origin'], dtype=float)
        row = {'classname': FLAME_CLASS, 'origin': '%.2f %.2f %.2f' % tuple(float(v) for v in p),
               'aw_flame_size': f['size']}
        if f['shape'] is not None:
            row['aw_flame_shape'] = f['shape']
        rows.append(row)
    return rows


def _size_rank(row):
    """Drawn size of a flame row, the engine's flame_size: the shape's particle size or 1.5 x the size."""
    size = float(row['aw_flame_size'])
    shape = [float(v) for v in row.get('aw_flame_shape', '0 0 0').split()]
    return max(shape[0], size * 1.5)


# Fire light (CHIM-EXTERIOR-FLAMES-MISSING-48, the maintainer 2026-10-23: "set it on by default but add some dbg
# command like dbg campfires on|off"): the first flame row of each fire placement carries its light record's radius
# (frame-local units) and brightness, "aw_flame_light" "R L"; the engine lights the placed models around it from
# these (chim_chunks.c, the rooms' attenuation rule) and dbg campfires off hides it. Build setting --chim-fire-light
# (on by default): tools/build.py exports FIRE_LIGHT_VARIABLE and the master (placement_light.MASTER_VARIABLE).
FIRE_LIGHT_KEY = 'aw_flame_light'
FIRE_LIGHT_VARIABLE = 'AMIWIND_CHIM_FIRE_LIGHT'
FIRE_LIGHT_MATCH = 8.0           # frame-local units: a light record sits at its fire placement's origin
_FIRE_LIGHTS = {}


def export_fire_light(mode, data_files=None):
    """Export the build setting chim_fire_light ('on' or 'off') and, when on, the master it reads the fires' light
    records from (Morrowind.esm of the data files). Returns the mode."""
    import os
    from chim import placement_light as PL
    if mode not in ('on', 'off'):
        raise ValueError('chim_fire_light must be on or off')
    os.environ[FIRE_LIGHT_VARIABLE] = mode
    if mode == 'on' and data_files is not None and Path(data_files).is_dir():
        from mwad.paths import child_ci
        master = child_ci(Path(data_files), 'Morrowind.esm', required=False)
        if master is None:
            raise ValueError('chim_fire_light on needs Morrowind.esm in the data files')
        os.environ[PL.MASTER_VARIABLE] = str(master)
    return mode


def fire_light_sources():
    """{model stem: [light source (placement_light.sources)]} of the master named by placement_light.MASTER_VARIABLE
    when FIRE_LIGHT_VARIABLE is 'on' (read once per process), else None: off, or not set (a frame map made outside
    the build: no fire light, as before)."""
    import os
    from chim import placement_light as PL
    if os.environ.get(FIRE_LIGHT_VARIABLE, 'off') != 'on':
        return None
    master = os.environ.get(PL.MASTER_VARIABLE, '')
    if not master or not Path(master).is_file():
        raise ValueError('%s=on needs %s naming the master (got %r)' % (FIRE_LIGHT_VARIABLE, PL.MASTER_VARIABLE, master))
    if _FIRE_LIGHTS.get('master') != master:
        by_stem = collections.defaultdict(list)
        for s in PL.sources(Path(master).read_bytes()):
            if s['mesh']:
                by_stem[PL.model_stem(s['model'])].append(s)
        _FIRE_LIGHTS.clear()
        _FIRE_LIGHTS.update(master=master, by_stem=dict(by_stem))
    return _FIRE_LIGHTS['by_stem']


def _fire_light(record, name, frame, lights):
    """'R L' (radius in frame-local units, brightness 0..255) of the light record placed at a fire placement (same
    mesh, within FIRE_LIGHT_MATCH of its origin), or None."""
    from chim import placement_light as PL
    best, found = FIRE_LIGHT_MATCH, None
    cx, cy = frame['centre'][:2]
    for s in lights.get(PL.model_stem(name), ()):
        x, y, z = (s['position'][0] - cx) * PL.SCALE, (s['position'][1] - cy) * PL.SCALE, s['position'][2] * PL.SCALE
        d = math.dist((x, y, z), record['origin'])
        if d < best:
            best, found = d, s
    return None if found is None else '%.1f %.1f' % (found['radius'] * PL.SCALE, found['luma'])


def frame_rows(chunks, models, cap=STATIC_FLAME_MAX, frame=None, lights=None):
    """(rows, report): the aw_flame rows of every placement the frame's chunks own, largest flames first
    (hearths and campfires before candles), then by origin; at most CAP rows (the engine reads no more), every
    row past it counted in the report. chunks: the frame's chunks (frame_map.load / validate.load_frame:
    'owned' placement records); models[model id] -> its index entry with 'name' and 'image' (the model record
    bytes). A placement hidden by the opening story gets none (its fire would burn in the air); a mesh that is
    not fire (fire_mesh) gets none, counted; the same emitter reached twice (one origin rounded to 0.01) is
    written once. lights (fire_light_sources) and frame (its 'centre'): the first row of each fire placement whose
    light record is found carries FIRE_LIGHT_KEY."""
    from chim import format as F
    cache = getattr(models, 'flames', None)
    cache = {} if cache is None else cache
    rows, seen = [], set()
    placements = hidden = lit = unmatched = 0
    not_fire = collections.Counter()
    for c in chunks:
        for r in c.get('owned', ()):
            mid = r['model']
            if mid not in cache:
                cache[mid] = model_flames(models[mid]['image'])
            if not cache[mid]:
                continue
            if not fire_mesh(models[mid]['name']):
                not_fire[models[mid]['name'].split('@', 1)[0].split('#', 1)[0]] += len(cache[mid])
                continue
            if r.get('flags', 0) & F.FLAG_STORY_HIDDEN:
                hidden += 1
                continue
            placements += 1
            light = _fire_light(r, models[mid]['name'], frame, lights) if lights is not None else None
            if lights is not None:
                lit += light is not None
                unmatched += light is None
            for row in placed_flames(r, cache[mid]):
                if row['origin'] not in seen:
                    seen.add(row['origin'])
                    if light is not None:
                        row[FIRE_LIGHT_KEY], light = light, None      # once per fire placement
                    rows.append(row)
    rows.sort(key=lambda e: (-_size_rank(e), e['origin']))
    kept = rows[:cap] if cap is not None else rows
    report = {'placements': placements, 'emitters': len(rows), 'written': len(kept),
              'over_cap': len(rows) - len(kept), 'cap': cap, 'story_hidden_placements': hidden,
              **({'fire_lights': sum(1 for e in kept if FIRE_LIGHT_KEY in e), 'fire_placements_without_light': unmatched}
                 if lights is not None else {}),
              'not_fire_emitters': dict(sorted(not_fire.items())),
              'hearth_size': sum(1 for e in kept if _size_rank(e) >= HEARTH_SIZE),
              'entity_bytes': entity_bytes(kept)}
    return kept, report


def entity_bytes(rows):
    """Bytes the rows add to a frame map's entity text (frame_map.entity_text's layout)."""
    return sum(len('{\n' + ''.join('"%s" "%s"\n' % (k, v) for k, v in e.items()) + '}\n') for e in rows)


class _Models:
    """models[mid] for frame_rows over a loaded world's model list, each model's emitters read once per world
    (the image step makes about 1,350 region frame maps from one world: every frame used to parse the same
    lamp and fire models again)."""

    def __init__(self, models):
        self.models = models
        self.flames = {}

    def __getitem__(self, mid):
        return self.models[mid]


_WORLD_MODELS = {}


def frame_rows_of(world, cell, cap=STATIC_FLAME_MAX):
    """frame_rows of the frame at CELL in a loaded CHIM world (frame_map.load or frame_map.frame_subworld)."""
    from chim.frame_map import frames_at
    found = frames_at(world['frames'], cell)
    if not found:
        raise ValueError('The CHIM world has no frame at cell %s' % (tuple(cell),))
    _, (_, frame, chunks) = found[0]
    models = world['models']
    table = _WORLD_MODELS.get('table')
    if table is None or table.models is not models or _WORLD_MODELS.get('count') != len(models):
        # the list itself is held by the table, so its id is never reused for another world's list
        _WORLD_MODELS.clear()
        _WORLD_MODELS.update(count=len(models), table=_Models(models))
    return frame_rows(chunks, _WORLD_MODELS['table'], cap, frame=frame, lights=fire_light_sources())


def world_frame_rows(world, world_dir, cell, cap=STATIC_FLAME_MAX):
    """frame_rows_of for a frame map maker: WORLD (loaded) or, when None, the CHIM world in WORLD_DIR read here; a
    folder without a CHIM world (a frame map made from stand-in data, the tests) has no flames, said so."""
    if world is None:
        if not (Path(world_dir) / 'chim/world.cwi').is_file():
            return [], {'placements': 0, 'emitters': 0, 'written': 0, 'over_cap': 0, 'cap': cap,
                        'note': 'no CHIM world read: no flames'}
        from chim.frame_map import load
        world = load(world_dir)
    return frame_rows_of(world, cell, cap)


def store_models(store):
    """models[store id] -> {'name', 'image'} of a CHIM store folder (the interior store chimi/: world.cwi and its
    packs), each record read when first asked for."""
    from chim import format as F
    from chim import interior  # noqa: F401 (registers world format 0.12, the store's)
    root = Path(store)
    _, files, mdir, _ = F.read_index((root / 'world.cwi').read_bytes())

    class Lazy(dict):
        def __missing__(self, mid):
            e = mdir[mid]
            with (root / files[e['file']]['path']).open('rb') as f:
                f.seek(e['offset'])
                image = f.read(e['bytes'])
            self[mid] = {'name': e['name'], 'image': image}
            return self[mid]
    return Lazy()


# ---------------------------------------------------------------- measuring a built world (read only)

_MASTER_SOURCES = {}


def _measure_frame(task):
    """Pool worker: one frame of the world read from its own files (validate.load_frame), counted; with a master,
    the placement light levels it would get (chim.placement_light) too."""
    from chim.validate import load_frame
    out, index, master = task
    (_, frame, chunks), models = load_frame(out, index)
    lights = None
    if master:
        from chim import placement_light as PL
        if _MASTER_SOURCES.get('master') != master:
            all_sources = PL.sources(Path(master).read_bytes())
            by_stem = collections.defaultdict(list)
            for s in all_sources:
                if s['mesh']:
                    by_stem[PL.model_stem(s['model'])].append(s)
            _MASTER_SOURCES.update(master=master, sources=all_sources, by_stem=dict(by_stem))
        lights = _MASTER_SOURCES['by_stem']
    rows, report = frame_rows(chunks, models, cap=None, frame=frame, lights=lights)
    flame_models = sorted({models[r['model']]['name'].split('@', 1)[0].split('#', 1)[0]
                           for c in chunks for r in c['owned']
                           if fire_mesh(models[r['model']]['name']) and model_flames(models[r['model']]['image'])})
    light = None
    if master:
        owned = [r for c in chunks for r in c['owned']]
        placed = [{'_pid': r['pid'], '_box': r['box']} for r in owned]
        by_pid = {r['pid']: r for r in owned}

        def stats(levels):
            # models drawn at two or more levels in this frame (0 counts): one cached surface per mip level, so
            # placements of such a model at different levels rebuild it when drawn in turn (d_surf.c D_CacheSurface)
            per_model = collections.defaultdict(set)
            for r in owned:
                per_model[r['model']].add(levels.get(r['pid'], 0))
            mixed = [m for m, v in per_model.items() if len(v) > 1]
            from chim import format as F
            return {'lit': len(levels), 'levels': collections.Counter(levels.values()),
                    'models_mixed': len(mixed),
                    'faces_of_mixed_models': sum(len(F.read_brush_image(models[m]['image'])[7]) // 20 for m in mixed),
                    'placements_of_mixed_models': sum(1 for r in owned if len(per_model[r['model']]) > 1),
                    'model_levels': len({(by_pid[p]['model'], v) for p, v in levels.items()}),
                    'models_lit': len({by_pid[p]['model'] for p in levels})}
        # every light that adds light, stored in the world (--chim-placement-light sources)
        light = dict(stats(PL.frame_levels(frame, placed, _MASTER_SOURCES['sources'])),
                     already_set=sum(1 for r in owned if r['flags'] >> 8))
        # the fires' own light from the frame map's flame rows, as the engine computes it (chim_chunks.c)
        cx, cy = frame['centre'][:2]
        fires = []
        for e in rows:
            if FIRE_LIGHT_KEY in e:
                x, y, z = (float(v) for v in e['origin'].split())
                radius, luma = (float(v) for v in e[FIRE_LIGHT_KEY].split())
                fires.append({'position': (cx + x / PL.SCALE, cy + y / PL.SCALE, z / PL.SCALE),
                              'radius': radius / PL.SCALE, 'luma': luma})
        light['fires'] = dict(stats(PL.frame_levels(frame, placed, fires)), sources=len(fires))
    return {'cell': list(frame['cell']), 'centre': list(frame['centre']), 'low': list(frame['low']),
            'span': [frame['nx'] * frame['grain'], frame['ny'] * frame['grain']],
            'owned': sum(len(c['owned']) for c in chunks), 'flame_models': flame_models, 'light': light, **report}


def _cell_regions(raw):
    """{(x, y): region id} of every exterior cell of a master (CELL RGNN)."""
    from mwad.audit import records, subrecords, string
    out = {}
    for tag, _, payload in records(raw):
        if tag != 'CELL':
            continue
        subs = {}
        for key, value in subrecords(payload):
            if key == 'FRMR':
                break                       # the references' own DATA follow: the cell's come first
            subs.setdefault(key, value)
        data = subs.get('DATA', b'')
        if len(data) < 12:
            continue
        flags, x, y = struct.unpack_from('<Iii', data)
        if not flags & 1:
            out[(x, y)] = string(subs['RGNN']) if 'RGNN' in subs else '(none)'
    return out


def measure(world_dir, master=None, lamps=None, regions=None, jobs=1):
    """Flames and lights of a built CHIM world, per frame and per game region (read only)."""
    from chim import format as F
    from chim import placed, reach, terc, thgt  # noqa: F401 (world formats 0.8-0.11)
    from build_parallel import ordered_map
    root = Path(world_dir) / 'chim'
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    count = sum(1 for f in files if f['kind'] == b'FRAM')
    frames = list(ordered_map(_measure_frame, [(str(world_dir), i, master) for i in range(count)], jobs))
    names = {}
    if regions:
        data = json.loads(Path(regions).read_text())
        listed = data.get('frames') or []
        listed = [dict(f, id=k) for k, f in listed.items()] if isinstance(listed, dict) else listed
        for f in listed:
            if f.get('cell'):
                names[tuple(f['cell'])] = f.get('id', str(f['cell']))
    by_cell = {tuple(f['cell']): f for f in frames}
    region_of = _cell_regions(Path(master).read_bytes()) if master else {}
    lights = None
    if master:
        import light_sources as LS
        raw = Path(master).read_bytes()
        records = LS.light_records(raw)
        lights = collections.Counter()
        per_frame = collections.defaultdict(collections.Counter)
        towns = [f for f in frames if tuple(f['cell']) not in names] if names else []
        for key, ident, pos in LS.placements(raw, records):
            if key[0] != 'exterior':
                continue
            light = records[ident]
            kind = light['class'] + ('' if light['model'] else ' (no mesh)')
            lights[kind] += 1
            cell = (key[1], key[2])
            frame = by_cell.get(cell) if cell in names else None
            if frame is None:
                for f in towns:
                    x, y = (pos[0] - f['centre'][0]) * 0.25, (pos[1] - f['centre'][1]) * 0.25
                    if f['low'][0] <= x < f['low'][0] + f['span'][0] and f['low'][1] <= y < f['low'][1] + f['span'][1]:
                        frame = f
                        break
            target = tuple(frame['cell']) if frame is not None else None
            per_frame[target][kind] += 1
        for f in frames:
            f['lights'] = dict(per_frame.get(tuple(f['cell']), {}))
        lights = {'exterior_by_class': dict(lights), 'not_on_chim': dict(per_frame.get(None, {}))}
    lamp_table = None
    if lamps:
        import light_sources as LS
        raw = Path(lamps).read_bytes()
        n = struct.unpack_from('<I', raw, 4)[0]
        rows = [LS.LAMP_ROW.unpack_from(raw, 8 + k * LS.LAMP_ROW.size) for k in range(n)]
        codes = {v: k for k, v in LS.LIGHT_CLASS_CODES.items()}
        codes[LS.LAVA_GLOW_CLASS] = 'lava_glow'
        cells = collections.Counter((r[0], r[1]) for r in rows)
        window = max((sum(cells.get((x + dx, y + dy), 0) for dx in (-1, 0, 1) for dy in (-1, 0, 1)), (x, y))
                     for x, y in cells) if cells else (0, None)
        lamp_table = {'rows': n, 'by_class': dict(collections.Counter(codes.get(r[6], str(r[6])) for r in rows)),
                      'densest_3x3': {'rows': window[0], 'centre_cell': list(window[1]) if window[1] else None},
                      'engine_cache': 256}
    per_region = collections.defaultdict(lambda: collections.Counter())
    for f in frames:
        name = names.get(tuple(f['cell']))
        f['frame'] = name or 'town'
        region = region_of.get(tuple(f['cell']), '?') if name else 'town frame ' + str(tuple(f['cell']))
        g = per_region[region]
        g['frames'] += 1
        g['placements'] += f['owned']
        g['flame_placements'] += f['placements']
        g['flames'] += f['emitters']
        g['hearth_size'] += f['hearth_size']
        g['frames_over_cap'] += f['emitters'] > STATIC_FLAME_MAX
        g['entity_bytes'] += f['entity_bytes']
        for kind, n in (f.get('lights') or {}).items():
            g['lights: ' + kind] += n
        if f.get('light'):
            g['placements_lit'] += f['light']['lit']
    worst = sorted(frames, key=lambda f: -f['emitters'])[:10]
    placement_light = None
    if master:
        levels = sum((collections.Counter(f['light']['levels']) for f in frames), collections.Counter())
        lit = [f for f in frames if f['light']['lit']]
        placement_light = {'placements_lit': sum(f['light']['lit'] for f in frames),
                           'placements': sum(f['owned'] for f in frames), 'frames_with_lit': len(lit),
                           'max_lit_per_frame': max((f['light']['lit'] for f in frames), default=0),
                           'model_level_pairs_max_per_frame': max((f['light']['model_levels'] for f in frames),
                                                                  default=0),
                           'models_at_two_or_more_levels': sum(f['light']['models_mixed'] for f in frames),
                           'models_at_two_or_more_levels_max_per_frame': max(
                               (f['light']['models_mixed'] for f in frames), default=0),
                           'placements_of_those_models': sum(f['light']['placements_of_mixed_models']
                                                             for f in frames),
                           'records_with_a_level_today': sum(f['light']['already_set'] for f in frames),
                           'levels': {str(k): levels[k] for k in sorted(levels)}}
        fl = [f['light']['fires'] for f in frames]
        busiest = max(frames, key=lambda f: (f['light']['fires']['lit'], f['light']['fires']['sources']))
        fire_levels = sum((collections.Counter(x['levels']) for x in fl), collections.Counter())
        placement_light['fires_only'] = {
            'fire_light_sources': sum(x['sources'] for x in fl),
            'fire_placements_without_light': sum(f.get('fire_placements_without_light', 0) for f in frames),
            'placements_lit': sum(x['lit'] for x in fl), 'frames_with_lit': sum(1 for x in fl if x['lit']),
            'models_at_two_or_more_levels': sum(x['models_mixed'] for x in fl),
            'faces_of_those_models': sum(x['faces_of_mixed_models'] for x in fl),
            'levels': {str(k): fire_levels[k] for k in sorted(fire_levels)},
            'busiest_frame': {'cell': busiest['cell'], 'frame': names.get(tuple(busiest['cell']), 'town'),
                              'placements': busiest['owned'],
                              **{k: v for k, v in busiest['light']['fires'].items() if k != 'levels'}}}
        for f in frames:
            f['light'] = {k: (dict(v) if isinstance(v, collections.Counter) else
                              {a: (dict(b) if isinstance(b, collections.Counter) else b) for a, b in v.items()}
                              if isinstance(v, dict) else v) for k, v in f['light'].items()}
    return {'frames': len(frames), 'flame_placements': sum(f['placements'] for f in frames),
            'flames': sum(f['emitters'] for f in frames), 'frames_with_flames': sum(1 for f in frames if f['emitters']),
            'frames_over_cap': sum(1 for f in frames if f['emitters'] > STATIC_FLAME_MAX),
            'max_per_frame': max((f['emitters'] for f in frames), default=0),
            'entity_bytes': sum(f['entity_bytes'] for f in frames),
            'flame_models': sorted({m for f in frames for m in f['flame_models']}),
            'not_fire_emitters': dict(sum((collections.Counter(f['not_fire_emitters']) for f in frames),
                                          collections.Counter())),
            'worst_frames': [{k: f[k] for k in ('cell', 'frame', 'emitters', 'placements', 'hearth_size',
                                                'entity_bytes')} for f in worst],
            'per_region': {k: dict(v) for k, v in sorted(per_region.items())},
            'lights': lights, 'lamp_table': lamp_table, 'placement_light': placement_light,
            'per_frame': [{k: f[k] for k in ('cell', 'frame', 'owned', 'placements', 'emitters', 'hearth_size',
                                             'entity_bytes') if k in f}
                          | {'lights': f.get('lights', {}), 'light': f.get('light')}
                          for f in frames]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    m = sub.add_parser('measure', help='flames (and with --master, lights) per frame of a built CHIM world')
    m.add_argument('world')
    m.add_argument('--master')
    m.add_argument('--lamps')
    m.add_argument('--regions')
    m.add_argument('--jobs', type=int, default=1)
    m.add_argument('--json')
    args = ap.parse_args(argv)
    print('[chim flames] measuring %s on %d workers' % (args.world, args.jobs), flush=True)
    result = measure(args.world, args.master, args.lamps, args.regions, args.jobs)
    text = json.dumps(result, indent=1, sort_keys=True)
    if args.json:
        Path(args.json).write_text(text + '\n', encoding='utf-8', newline='\n')
    summary = {k: v for k, v in result.items() if k not in ('per_frame',)}
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
