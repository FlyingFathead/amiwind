#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The open world's seams and edges: no wall or blocker the original does not have (SOL-SEA-INVISIBLE-BLOCKER-68,
ACTOR-CLIP-ABOVE-DRAWN-BODY-69). Kept beside tools/seam_audit.py, which checks the seams INSIDE a reduced mesh; this one
checks the seams BETWEEN the places of the open world and what collides there.

In the original the exterior is one grid of cells with open sea between and around the islands: nothing stops a
swimmer, a water walker or a levitating player anywhere inside the map's box (OpenMW 0.53 apps/openmw/mwworld/
worldmodel.cpp 55-62 makes every recordless cell open water; the map spans the box of every exterior CELL record,
mwrender/globalmap.cpp 291-308). AmiWind keeps one rule of its own: the sea current at the box's outer edge
(tools/world_bounds.py, docs/WORLD_BOUNDS.md), the maintainer's ruling of 2026-11-24 (SOL-SEA-CROSSING-68: walls only
at the extreme outer edge of the map, where the map ends). The checks, all from a build's own outputs:

- bounds: the engine's table of world cells (engine/aga/src/aw_bounds_rules.c: the cell of each open-world map's core
  centre, from the image's world/regions.awr, regions-sl.awr and regions-mh.awr, as aw_world.c reads them). It must
  fit the engine's grid (AW_BOUNDS_GRID cells a side), have no hole inside the map's box, and open sides (where the
  current stands) only on the box's perimeter;
- stores: every cell of the map's box is a frame of exactly one exterior store (the base world, Solstheim's, its open
  sea, ...): a cell with none is a wall in the middle of the sea, a cell in two stores is two collisions in one place.
  Every store edge (neighbouring frames of different stores: a level change, CHIM-STORE-ONE-AT-A-TIME-64) is listed;
- actors: every creature of the image's actor table (maps/chim-actors.cca) against what is drawn: the engine's
  collision top (aw_actor_clip.c: the drawn idle pose's top, never above the person box) and, for each reference in
  the water, whether anything of it collides above the surface where nothing of it is drawn. The person box alone
  (aw_actor_clip 0, the method before v0.0.69) is counted beside it;
- collision only: every open-world model of the collision census (collision-census.json) with collision and no drawn
  face; a flora model drawn by its card ('#collision_only', the trees drawn as a sprite, tools/prepare_world_flora.py)
  is drawn elsewhere and is listed apart from the others;
- barriers: the original's own invisible walls (id1/world-barriers.txt, tools/world_barriers.py: collision markers of
  the game files), listed as theirs, never as a finding;
- frame edges: every frame map (id1/maps/*.chim) whose worldspawn closes its frame edge with walls (a town frame that
  joins no open world, tools/chim/frame_map.py closed_edge). A finding when a player can reach the walls; listed as
  handed off when the town's handoff line (the engine's town table: its core + 32, aw_world.c AW_WorldDestination)
  lies inside them on every side, so he goes on into the open world first; Mournhold's districts listed apart.

Usage (in the shell container; reads a build run only):
  world_seams.py audit --run RUN_DIR --out REPORT.json [--box X0,Y0,X1,Y1]
  world_seams.py check --report REPORT.json            exit 1 on any finding
"""
import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

FORMAT = 'aw-world-seams-1'
CELL = 2048.0                    # map units per exterior cell (engine AW_BOUNDS_CELL)
GRID = 128                       # cells a side the engine's bounds table holds (AW_BOUNDS_GRID)
PERSON_TOP = 33.25               # the person box's top (world.qc aw_npc_floor)
ACTOR_CLIP_MIN = 1.0             # aw_actor_clip.h AW_ACTOR_CLIP_MIN
WATER_LEVEL = 0.0                # the exterior water surface (map units, tools/chim/region_actors.py WATER_LEVEL)
LOCAL = 0.25                     # map units per Morrowind unit
SIDES = ((1, 0, 'east'), (0, 1, 'north'), (-1, 0, 'west'), (0, -1, 'south'))
# the exterior stores of a build run: (store, the stage folder holding its chim/ world)
STORES = (('chim', 'chim-world'), ('chimsol', 'bloodmoon-solstheim'), ('chimsea', 'bloodmoon-solstheim-sea'),
          ('chimmh', 'tribunal-mournhold'))
DIRECTORIES = ('world/regions.awr', 'world/regions-sl.awr', 'world/regions-mh.awr')


# ---------------------------------------------------------------- the engine's bounds table

def directory_rows(raw):
    """[(name, origin (x, y, z), core (x0, y0, x1, y1))] of an open-world directory: AWR2 (world/regions.awr, a 64-byte
    header) or AWS1 (a layer's rows file, an 8-byte header), 52 bytes a row (aw_world.c read_row)."""
    if raw[:4] == b'AWR2':
        head = 64
    elif raw[:4] == b'AWS1':
        head = 8
    else:
        raise ValueError('not an open-world directory (AWR2 or AWS1)')
    count = struct.unpack_from('<I', raw, 4)[0]
    if len(raw) != head + 52 * count:
        raise ValueError('open-world directory length does not match its %d rows' % count)
    out = []
    for i in range(count):
        at = head + 52 * i
        name = raw[at:at + 8].split(b'\0')[0].decode('ascii', 'replace')
        out.append((name, struct.unpack_from('<3f', raw, at + 8), struct.unpack_from('<4f', raw, at + 20)))
    return out


def bounds_cells(rows):
    """{cell: [map names]}: the engine's world cells (aw_world.c AW_WorldRegionCentres, aw_bounds_rules.c
    AW_BoundsBuild): the cell of each row's core centre."""
    out = {}
    for name, origin, core in rows:
        x = origin[0] + (core[0] + core[2]) * .5
        y = origin[1] + (core[1] + core[3]) * .5
        out.setdefault((math.floor(x / CELL), math.floor(y / CELL)), []).append(name)
    return out


def box_of(cells):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs), max(ys)


def inside(cell, box):
    return box[0] <= cell[0] <= box[2] and box[1] <= cell[1] <= box[3]


def components(cells):
    """[set of cells]: the 4-connected groups of CELLS, largest first."""
    left, out = set(cells), []
    while left:
        start = left.pop()
        group, todo = {start}, [start]
        while todo:
            c = todo.pop()
            for dx, dy, _ in SIDES:
                n = (c[0] + dx, c[1] + dy)
                if n in left:
                    left.discard(n)
                    group.add(n)
                    todo.append(n)
        out.append(group)
    return sorted(out, key=lambda g: (-len(g), min(g)))


def bounds_check(cells, box):
    """The engine's table against the map's BOX: {'cells', 'fits_grid', 'span', 'holes' (cells of the box not held),
    'inner_sides' ([cell, side] open sides whose neighbour lies inside the box: a current in the middle of the sea),
    'perimeter_sides', 'outside' (held cells outside the box), 'groups' (sizes of the 4-connected groups)}."""
    cells = set(cells)
    span = box_of(cells) if cells else box
    holes = sorted(c for c in ((x, y) for x in range(box[0], box[2] + 1) for y in range(box[1], box[3] + 1))
                   if c not in cells)
    inner, perimeter = [], 0
    for c in sorted(cells):
        for dx, dy, name in SIDES:
            n = (c[0] + dx, c[1] + dy)
            if n in cells:
                continue
            if inside(c, box) and inside(n, box):
                inner.append([list(c), name])
            elif inside(c, box):
                perimeter += 1
    return {'cells': len(cells), 'span': list(span),
            'fits_grid': span[2] - span[0] + 3 <= GRID and span[3] - span[1] + 3 <= GRID,
            'holes': [list(c) for c in holes], 'inner_sides': inner, 'perimeter_sides': perimeter,
            'outside': [list(c) for c in sorted(c for c in cells if not inside(c, box))],
            'groups': [len(g) for g in components(cells)]}


# ---------------------------------------------------------------- the stores

OVERLAP = 896.0                  # a frame's chunk grid reaches this far past its core (tools/world_bounds.py OVERLAP)


def frame_cells(frame):
    """The cells a frame's core covers: its chunk grid (centre, low, nx x ny chunks of grain map units) less the
    overlap on each side. A region frame's core is its own cell; a town's frame covers several (Seyda Neen's 42 x 39
    chunks), part of some."""
    if frame.get('cells'):
        return [tuple(c) for c in frame['cells']]
    out = []
    span = []
    for k, n in ((0, frame['nx']), (1, frame['ny'])):
        lo = frame['centre'][k] * LOCAL + frame['low'][k] + OVERLAP
        hi = frame['centre'][k] * LOCAL + frame['low'][k] + n * frame['grain'] - OVERLAP
        span.append(range(math.floor(lo / CELL), math.ceil(hi / CELL)))
    for x in span[0]:
        for y in span[1]:
            out.append((x, y))
    return out or [tuple(frame['cell'])]


def store_frames(world_dir):
    """{cell: frame path} of a CHIM world's frame files (chim/world.cwi): every cell a frame's core covers."""
    from chim import format as F
    from chim import placed, placement_light, reach, room_records, terc, thgt  # noqa: F401 (world formats 0.8 to 0.11)
    root = Path(world_dir) / 'chim'
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    out = {}
    for f in files:
        if f['kind'] == b'FRAM':
            for cell in frame_cells(F.read_frame((root / f['path']).read_bytes())[0]):
                out.setdefault(cell, f['path'])
    return out


def stores_check(frames_by_store, box):
    """Every cell of BOX in exactly one store: {'stores': {store: frames}, 'gaps': cells with no frame, 'doubles':
    [cell, stores] in more than one, 'edges': {"a|b": count} of store edges, 'edge_list'}."""
    owner = {}
    doubles = []
    for store, frames in sorted(frames_by_store.items()):
        for cell in frames:
            if cell in owner:
                doubles.append([list(cell), [owner[cell], store]])
            else:
                owner[cell] = store
    gaps = sorted(c for c in ((x, y) for x in range(box[0], box[2] + 1) for y in range(box[1], box[3] + 1))
                  if c not in owner)
    edges, listed = {}, []
    for cell, store in sorted(owner.items()):
        for dx, dy, _ in SIDES[:2]:
            n = (cell[0] + dx, cell[1] + dy)
            if n in owner and owner[n] != store:
                key = '|'.join(sorted((store, owner[n])))
                edges[key] = edges.get(key, 0) + 1
                listed.append([list(cell), list(n), store, owner[n]])
    return {'stores': {s: len(f) for s, f in sorted(frames_by_store.items())}, 'gaps': [list(c) for c in gaps],
            'doubles': doubles, 'edges': edges, 'edge_list': listed}


# ---------------------------------------------------------------- the actors

def clip_top(drawn, scale=1.0, box_top=PERSON_TOP):
    """aw_actor_clip.c AW_ActorClipTopRule: the top a creature collides up to."""
    if not drawn > 0 or not scale > 0 or not box_top > 0:
        return box_top
    return min(max(drawn * scale, ACTOR_CLIP_MIN), box_top)


def model_top(id1, model):
    """The drawn idle pose's top above the origin (map units) of an actor model (tools/check_actor_ground.py
    model_frames: a skeletal actor's rest frame, every frame of another), shared skins and shapes expanded; None when
    the model cannot be read."""
    import payload_share as P
    from check_actor_ground import model_frames
    path = Path(id1) / model
    if not path.is_file():
        return None
    raw = path.read_bytes()
    read = lambda name: (Path(id1) / name).read_bytes()
    try:
        if P.is_shared(raw):
            raw = P.expand_shared_skin(raw, read)
        if P.is_shape_shared(raw):
            raw = P.expand_shared_shape(raw, read)
        frames = model_frames(raw)
    except (ValueError, struct.error, OSError):
        return None
    return max(p[2] for f in frames for p in f)


def creature_rows(table_path, id1):
    """[(record dict, base text fields, cell)] of every actor-table record that resolves to a creature model (its own
    base, or the creatures a levelled list can give), with the models' drawn tops: (rows, {model: top})."""
    from chim import actors as A
    data = Path(table_path).read_bytes()
    _, cells, records, bases, _ = A.read_table(data)
    lists = A.read_lists(data) or []
    scales = A.read_scales(data)

    def fields(text):
        import re
        return dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', text))

    def creatures_of(base_index, depth=0):
        base = bases[base_index]
        if base['kind'] == 1 and base['text']:
            return [fields(base['text'])]
        if base['kind'] == 2 and depth < 4 and base.get('list') is not None and base['list'] < len(lists):
            out = []
            for _, target in lists[base['list']][2]:
                if target & A.NESTED:
                    continue
                out.extend(creatures_of(target, depth + 1))
            return out
        return []
    tops, rows = {}, []
    for cell, first, n in cells:
        for k in range(first, first + n):
            r = records[k]
            for f in creatures_of(r['base']):
                model = f.get('model', '')
                if not model.startswith('progs/c_'):
                    continue
                if model not in tops:
                    tops[model] = model_top(id1, model)
                rows.append((r, f, cell, scales.get(k, 1.0)))
    return rows, tops


def actors_check(rows, tops):
    """{'creatures' (record x creature pairs), 'models', 'unreadable' models, 'lowered' (pairs whose collision top is
    below the person box), 'water': pairs in the water, 'water_blockers_person_box' (the method before v0.0.69: the box
    above the surface while the drawn body is wholly under it), 'water_blockers' (the same under aw_actor_clip 1: must be
    none), 'examples'}."""
    out = {'creatures': len(rows), 'models': len(tops), 'unreadable': sorted(m for m, t in tops.items() if t is None),
           'lowered': 0, 'water': 0, 'water_blockers_person_box': 0, 'water_blockers': 0, 'examples': []}
    for r, f, cell, scale in rows:
        drawn = tops.get(f.get('model'))
        top = clip_top(drawn or 0, scale)
        if top < PERSON_TOP:
            out['lowered'] += 1
        z = r['origin'][2]              # the record's height in its cell's local map units (tools/chim/actors.py)
        if z >= WATER_LEVEL:
            continue
        out['water'] += 1
        below = drawn is not None and z + drawn * scale <= WATER_LEVEL
        if below and z + PERSON_TOP > WATER_LEVEL:
            out['water_blockers_person_box'] += 1
            by = out.setdefault('person_box_by_creature', {})
            by[f.get('aw_source_id', '?')] = by.get(f.get('aw_source_id', '?'), 0) + 1
            out.setdefault('person_box_references', set()).add(r['key'])
            if len(out['examples']) < 12:
                out['examples'].append({'key': r['key'], 'cell': list(cell), 'creature': f.get('aw_source_id'),
                                        'model': f.get('model'), 'z': round(z, 2),
                                        'drawn_top': round(z + drawn * scale, 2),
                                        'person_box_top': round(z + PERSON_TOP, 2), 'collision_top': round(z + top, 2)})
        if below and z + top > WATER_LEVEL:
            out['water_blockers'] += 1
    out['person_box_references'] = len(out.get('person_box_references', ()))
    return out


# ---------------------------------------------------------------- collision without a drawn face

def model_stem(name):
    """'x/flora_ashtree_04@s2#2' or 'f/flora_tree_01.nif#collision_only@s1' -> 'x/flora_ashtree_04' (lower case)."""
    stem = name.replace('\\', '/').casefold()
    for mark in ('#', '@'):
        stem = stem.split(mark, 1)[0]
    return stem[:-4] if stem.endswith('.nif') else stem


def card_models(tree_sprites):
    """{model stem} of every placement the world flora draws as a card (world-flora/tree-sprites.json rows of kind
    'tree', tools/prepare_world_flora.py): their collision is a model with no drawn face, by design."""
    out = set()
    for value in (tree_sprites or {}).values():
        if isinstance(value, list):
            for r in value:
                if isinstance(r, dict) and r.get('kind') == 'tree' and r.get('model'):
                    out.add(model_stem(r['model']))
    return out


def collision_only_check(census, cards=()):
    """{'models': open-world models with collision and no drawn face, 'cards': those drawn by their flora card (a
    '#collision_only' model, or one whose model the world flora draws as a card: CARDS), 'others': [name, file]}."""
    rows = [r for r in census.get('models') or [] if r.get('store') == 'open world' and not r.get('faces') and
            (r.get('clipnodes') or r.get('pieces'))]
    cards = set(cards)
    card = lambda r: '#collision_only' in r.get('name', '') or model_stem(r.get('name', '')) in cards
    return {'models': len(rows), 'cards': sum(1 for r in rows if card(r)),
            'others': sorted([r.get('name'), r.get('file')] for r in rows if not card(r))}


def barriers_list(text):
    """[key] of the original's own solid boxes in id1/world-barriers.txt (tools/world_barriers.py)."""
    return [int(line.split()[1]) for line in text.splitlines() if line.startswith('box ')]


EDGE_KEY = '_chim_edge'          # tools/chim/frame_map.py: a frame map closed by walls at its frame edge
TOWN_TABLE = ROOT / 'engine/aga/src/aw_town_table.h'
HANDOFF_MARGIN = 32.0            # aw_world.c AW_WorldDestination: a point this far past its own town's core moves on
TOWN_ROW = re.compile(r'\{"([^"]+)","[^"]*","[^"]*","[^"]*","[^"]*","[^"]*",(-?\d+),(-?\d+),(-?\d+),[^,]+,(\d+),(\d+),'
                      r'\{([^}]*)\},\{([^}]*)\}\}')


def town_rows(text):
    """{town map name: {'world_slot', 'handoff', 'origin', 'core'}} of the engine's town table (aw_town_table.h
    AW_TOWN_ROWS, tools/town_table.py)."""
    out = {}
    for name, _cap, _draw, slot, _back, handoff, origin, core in TOWN_ROW.findall(text):
        out[name] = {'world_slot': int(slot), 'handoff': int(handoff),
                     'origin': [float(v) for v in origin.split(',')], 'core': [float(v) for v in core.split(',')]}
    return out


def map_bounds(raw):
    """(mins, maxs) of a BSP29 / .chim frame map's world model (lump 14, model 0): where frame_walls stand."""
    ofs = struct.unpack_from('<i', raw, 4 + 14 * 8)[0]
    v = struct.unpack_from('<6f', raw, ofs)
    return list(v[:3]), list(v[3:])


def handoff_before_walls(town, bounds):
    """The units between the handoff line (the town's core + HANDOFF_MARGIN) and the walls on its nearest side, when the
    town hands off to the open world (aw_world.c world_town: a directory slot, or a table frame: handoff 1) and the line
    lies inside the walls on every side; None otherwise (the walls are reached first, or nothing hands off)."""
    if not town or not (town['world_slot'] >= 0 or town['handoff']) or not bounds:
        return None
    (x0, y0, _), (x1, y1, _) = bounds
    c = town['core']
    gaps = [(c[0] - HANDOFF_MARGIN) - x0, (c[1] - HANDOFF_MARGIN) - y0, x1 - (c[2] + HANDOFF_MARGIN),
            y1 - (c[3] + HANDOFF_MARGIN)]
    return min(gaps) if min(gaps) > 0 else None


def closed_edges(maps, towns=None, bounds=None):
    """{'closed': [[map, message]] of the frame maps (id1/maps/*.chim) whose worldspawn closes their edge with walls
    (tools/chim/frame_map.py closed_edge, frame_walls: a town that joins no open world) and whose walls a player can
    reach, 'handed_off': [[map, message, units]] those whose town hands off to the open world before its walls (the
    engine's town table, TOWNS: town_rows; BOUNDS: {map: map_bounds}): the walls stand behind the handoff line, UNITS
    inside it on the nearest side, 'mournhold': Mournhold's districts (mhNNNN: interior cells in the original, bounded
    by the city), listed apart}. MAPS: {map name: entity rows}."""
    closed, handed, districts = [], [], []
    for name, rows in sorted(maps.items()):
        world = rows[0] if rows else {}
        if not world.get(EDGE_KEY):
            continue
        if name.startswith('mh'):
            districts.append([name, world.get('message', '')])
            continue
        gap = handoff_before_walls((towns or {}).get(name[:-5] if name.endswith('-chim') else name),
                                   (bounds or {}).get(name))
        if gap is None:
            closed.append([name, world.get('message', '')])
        else:
            handed.append([name, world.get('message', ''), round(gap, 1)])
    return {'closed': closed, 'handed_off': handed, 'mournhold': districts}


# ---------------------------------------------------------------- the audit

def audit(run, box=None):
    run = Path(run)
    id1 = run / 'image' / 'boot' / 'id1'
    rows = []
    for rel in DIRECTORIES:
        if (id1 / rel).is_file():
            rows.extend(directory_rows((id1 / rel).read_bytes()))
    world = bounds_cells(rows)
    frames = {s: store_frames(run / stage) for s, stage in STORES
              if (run / stage / 'chim' / 'world.cwi').is_file()}
    exterior = {s: f for s, f in frames.items() if s != 'chimmh'}   # Mournhold's districts are presented elsewhere
    if box is None:
        box = box_of({c for f in exterior.values() for c in f})
    report = {'format': FORMAT, 'run': run.name, 'box': list(box),
              'bounds': bounds_check(world, box), 'stores': stores_check(exterior, box),
              'mournhold_frames': len(frames.get('chimmh', {}))}
    table = id1 / 'maps' / 'chim-actors.cca'
    if table.is_file():
        report['actors'] = actors_check(*creature_rows(table, id1))
    if (run / 'collision-census.json').is_file():
        trees = run / 'world-flora' / 'tree-sprites.json'
        cards = card_models(json.loads(trees.read_text())) if trees.is_file() else set()
        report['collision_only'] = collision_only_check(json.loads((run / 'collision-census.json').read_text()), cards)
    if (id1 / 'world-barriers.txt').is_file():
        report['original_barriers'] = barriers_list((id1 / 'world-barriers.txt').read_text(encoding='ascii'))
    if (id1 / 'maps').is_dir():
        from chim.actors import map_entities
        maps, bounds = {}, {}
        for path in sorted((id1 / 'maps').glob('*.chim')):
            try:
                maps[path.stem] = map_entities(path)[:1]
                if maps[path.stem] and maps[path.stem][0].get(EDGE_KEY):
                    bounds[path.stem] = map_bounds(path.read_bytes())
            except (OSError, struct.error):
                maps[path.stem] = []
        towns = town_rows(TOWN_TABLE.read_text(encoding='utf-8')) if TOWN_TABLE.is_file() else {}
        report['frame_edges'] = closed_edges(maps, towns, bounds)
    return report


def check(report):
    """[finding]: everything that would stop or hold a player inside the map's box that the original does not."""
    out = []
    b = report['bounds']
    if not b['fits_grid']:
        out.append('the bounds table spans %s, over the engine grid of %d cells' % (b['span'], GRID))
    if b['holes']:
        out.append('%d cells of the box are not in the bounds table (the edge current stands round them): %s'
                   % (len(b['holes']), b['holes'][:8]))
    if b['inner_sides']:
        out.append('%d open sides inside the box: %s' % (len(b['inner_sides']), b['inner_sides'][:8]))
    s = report['stores']
    if s['gaps']:
        out.append('%d cells of the box have no exterior frame: %s' % (len(s['gaps']), s['gaps'][:8]))
    if s['doubles']:
        out.append('%d cells have a frame in two stores: %s' % (len(s['doubles']), s['doubles'][:8]))
    a = report.get('actors')
    if a and a['water_blockers']:
        out.append('%d creatures in the water collide above the surface with nothing of them drawn there'
                   % a['water_blockers'])
    if a and a['unreadable']:
        out.append('%d creature models could not be read for their drawn height: %s' % (len(a['unreadable']),
                                                                                   a['unreadable'][:6]))
    c = report.get('collision_only')
    if c and c['others']:
        out.append('%d open-world models collide without a drawn face and are no flora card: %s'
                   % (len(c['others']), c['others'][:6]))
    e = report.get('frame_edges')
    if e and e['closed']:
        out.append('%d frame maps are closed by walls at their frame edge that a player reaches before any handoff '
                   '(VIVEC-CITY-FRAME-EDGE-WALLS-69): %s' % (len(e['closed']), e['closed'][:6]))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('audit')
    a.add_argument('--run', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--box', help='X0,Y0,X1,Y1: the map\'s box (default: the box of every exterior frame)')
    c = sub.add_parser('check')
    c.add_argument('--report', type=Path, required=True)
    args = p.parse_args(argv)
    if args.cmd == 'audit':
        box = tuple(int(v) for v in args.box.split(',')) if args.box else None
        print('=== PHASE 1/2: reading the bounds table, the stores, the actor table and the census ===', flush=True)
        report = audit(args.run, box)
        args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    else:
        report = json.loads(args.report.read_text(encoding='utf-8'))
    print('=== PHASE 2/2: the findings ===', flush=True)
    b, s = report['bounds'], report['stores']
    print('World seams (%s): box %s; bounds table %d cells (groups %s), %d holes, %d inner open sides, %d perimeter '
          'sides; stores %s, %d gaps, %d doubles, store edges %s' % (
              report['run'], report['box'], b['cells'], b['groups'][:4], len(b['holes']), len(b['inner_sides']),
              b['perimeter_sides'], s['stores'], len(s['gaps']), len(s['doubles']), s['edges']))
    if report.get('actors'):
        a = report['actors']
        print('Creatures: %d record x creature pairs, %d models (%d unreadable), %d lowered to their drawn top; %d in '
              'the water: %d stood above the surface undrawn in the person box (%d references: %s), %d under '
              'aw_actor_clip 1' % (
                  a['creatures'], a['models'], len(a['unreadable']), a['lowered'], a['water'],
                  a['water_blockers_person_box'], a.get('person_box_references', 0),
                  a.get('person_box_by_creature', {}), a['water_blockers']))
    if report.get('collision_only'):
        c = report['collision_only']
        print('Collision without a drawn face: %d open-world models, %d flora cards, %d others'
              % (c['models'], c['cards'], len(c['others'])))
    if 'original_barriers' in report:
        print('The original\'s own invisible walls (world-barriers.txt): %d' % len(report['original_barriers']))
    if report.get('frame_edges'):
        e = report['frame_edges']
        print('Frame maps closed at their edge: %s; handed off to the open world before their walls (units): %s; '
              'Mournhold\'s districts: %s' % (e['closed'], e.get('handed_off', []), e['mournhold']))
    findings = check(report)
    for f in findings:
        print('SEAM: ' + f)
    print('World seams check: %d finding(s)' % len(findings))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
