#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Measure Morrowind path grids (PGRD) and actor behaviour packages, island-wide.

Reads the owner's own master files read-only and prints aggregate numbers
only: grids, nodes and edges, nodes per grid, interiors against exteriors,
cells with placed actors but no grid, behaviour package use and the bytes a compact
node graph would take. No record is copied out; the per-grid list (cell
name, node count) is written only with --details, for private use.

Record layouts (TES3):
  PGRD DATA  i32 grid x, i32 grid y, u16 granularity, u16 point count
  PGRD PGRP  16 bytes per point: i32 x, y, z, u8 auto-generated, u8 links, u16 pad
  PGRD PGRC  i32 per link, the points' links in point order
  NPC_/CREA AI_W  u16 distance, u16 duration, u8 hour, u8 idle[8], u8 reset
Exterior point coordinates are local to the cell (8192 units square).

Usage: path_grid_stats.py MASTER.esm [MASTER.esm ...] [--out FILE] [--details]
Later masters replace earlier records with the same identity, as the game does.
"""
import argparse
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import records, subrecords, string  # noqa: E402

CELL_UNITS = 8192
ACTOR_TAGS = ('NPC_', 'CREA')
SPAWN_TAG = 'LEVC'  # levelled creature lists: placed spawn points, no behaviour package of their own
AI_TAGS = {'AI_W': 'wander', 'AI_T': 'travel', 'AI_F': 'follow', 'AI_E': 'escort', 'AI_A': 'activate'}
BUCKETS = (1, 8, 16, 32, 64, 128, 256, 512, 1024)
# Areas measured by name: (exterior cell centre, radius in cells, interior name prefix).
AREAS = {
    'seyda_neen': ((-2, -9), 1, 'Seyda Neen'),
    'balmora': ((-3, -2), 1, 'Balmora'),
    'vivec_arena': ((4, -11), 1, 'Vivec, Arena'),
}
BORDER = 256  # a node this close to a cell edge counts as a border node
PATCH_RADII = (512, 1024, 2048)  # Morrowind units (128, 256, 512 AmiWind units)


def parse_pgrd(fields):
    """One PGRD record as (name, (x, y), granularity, points, links)."""
    name = ''; grid = (0, 0); gran = 0; count = 0; points = []; links = []
    for tag, data in fields:
        if tag == 'NAME':
            name = string(data)
        elif tag == 'DATA':
            if len(data) != 12:
                raise ValueError('PGRD DATA must be 12 bytes')
            x, y, gran, count = struct.unpack('<iiHH', data)
            grid = (x, y)
        elif tag == 'PGRP':
            if len(data) % 16:
                raise ValueError('PGRD PGRP must hold 16-byte points')
            points = [struct.unpack_from('<iiiBBH', data, i) for i in range(0, len(data), 16)]
        elif tag == 'PGRC':
            if len(data) % 4:
                raise ValueError('PGRD PGRC must hold 32-bit links')
            links = list(struct.unpack('<%di' % (len(data) // 4), data))
    if count and len(points) != count:
        raise ValueError('PGRD %r: %d points stored, %d declared' % (name, len(points), count))
    return name, grid, gran, points, links


def cell_header(fields):
    """(name, flags, x, y, region) of a CELL record, and its placed base ids."""
    name = ''; flags = x = y = 0; region = ''; ids = []; in_refs = False
    for tag, data in fields:
        if tag == 'FRMR':
            in_refs = True
        elif not in_refs and tag == 'NAME':
            name = string(data)
        elif not in_refs and tag == 'DATA' and len(data) == 12:
            flags, x, y = struct.unpack('<Iii', data)
        elif not in_refs and tag == 'RGNN':
            region = string(data)
        elif in_refs and tag == 'NAME':
            ids.append(string(data).casefold())
    return name, flags, x, y, region, ids


def load(paths):
    """Merged cells, grids and actor bases over the masters, later masters winning."""
    cells = {}; grids = {}; actors = {}; per_master = []
    for path in paths:
        raw = Path(path).read_bytes()
        n_grids = n_cells = 0; pending = []
        for tag, flags, payload in records(raw):
            if tag not in ('CELL', 'PGRD', SPAWN_TAG, *ACTOR_TAGS):
                continue
            fields = list(subrecords(payload))
            if tag == 'CELL':
                name, cflags, x, y, region, ids = cell_header(fields)
                interior = bool(cflags & 1)
                key = ('i', name.casefold()) if interior else ('e', x, y)
                old = cells.get(key)
                # A later master's CELL adds or changes references; keep every base id seen.
                merged = (old['ids'] if old else []) + ids
                cells[key] = {'name': name, 'interior': interior, 'x': x, 'y': y,
                              'region': region, 'ids': merged}
                n_cells += 1
            elif tag == 'PGRD':
                pending.append(parse_pgrd(fields)); n_grids += 1
            elif tag == SPAWN_TAG:
                ident = next((string(d).casefold() for k, d in fields if k == 'NAME'), '')
                actors[ident] = {'kind': tag, 'ai': []}
            else:
                ident = ''; ai = []
                for k, data in fields:
                    if k == 'NAME' and not ident:
                        ident = string(data).casefold()
                    elif k in AI_TAGS:
                        ai.append((AI_TAGS[k], struct.unpack_from('<HH', data) if k == 'AI_W' else None))
                actors[ident] = {'kind': tag, 'ai': ai}
        interiors = {k[1] for k in cells if k[0] == 'i'}
        for name, grid, gran, points, links in pending:
            interior = grid == (0, 0) and name.casefold() in interiors
            key = ('i', name.casefold()) if interior else ('e',) + grid
            grids[key] = {'name': name, 'interior': interior, 'grid': grid,
                          'granularity': gran, 'points': points, 'links': links}
        per_master.append({'master': Path(path).name, 'cell_records': n_cells, 'pgrd_records': n_grids})
    return cells, grids, actors, per_master


def graph(g):
    """Directed links, undirected edges, components and edge lengths of one grid."""
    pts = g['points']; links = g['links']; n = len(pts)
    directed = []; pos = 0
    for i, p in enumerate(pts):
        for j in links[pos:pos + p[4]]:
            if 0 <= j < n:
                directed.append((i, j))
        pos += p[4]
    edges = {(min(a, b), max(a, b)) for a, b in directed if a != b}
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for a, b in edges:
        parent[find(a)] = find(b)
    comps = len({find(i) for i in range(n)}) if n else 0
    lengths = [((pts[a][0] - pts[b][0]) ** 2 + (pts[a][1] - pts[b][1]) ** 2 + (pts[a][2] - pts[b][2]) ** 2) ** .5
               for a, b in edges]
    seen = set(directed)
    one_way = len({(a, b) for a, b in directed if a != b and (b, a) not in seen})
    # A local patch: the nodes within R of a node (what a search around one actor may touch).
    patch = {r: [sum(1 for q in pts if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 <= r * r) for p in pts]
             for r in PATCH_RADII}
    return {'nodes': n, 'directed': len(directed), 'edges': len(edges), 'components': comps,
            'lengths': lengths, 'one_way': one_way, 'patch': patch, 'stored_links': len(links),
            'auto': sum(1 for p in pts if p[3])}


def quantiles(values):
    if not values:
        return {}
    v = sorted(values)
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + .5))]  # noqa: E731
    return {'min': v[0], 'p25': pick(.25), 'median': pick(.5), 'p75': pick(.75),
            'p90': pick(.9), 'p99': pick(.99), 'max': v[-1], 'mean': round(sum(v) / len(v), 1)}


def histogram(values):
    out = Counter()
    for n in values:
        low = 0
        for b in BUCKETS:
            if n <= b:
                out['%d-%d' % (low + 1, b) if b > 1 else '1'] += 1; break
            low = b
        else:
            out['>%d' % BUCKETS[-1]] += 1
    return dict(out)


def compact_bytes(nodes, edges):
    """Bytes of a compact graph: i16 x,y,z + u8 link count per node, u8 (u16 over 255 nodes) per directed link."""
    index = 1 if nodes <= 256 else 2
    return nodes * 7 + 2 * edges * index


def summarise(group):
    nodes = [s['nodes'] for s in group]
    return {'grids': len(group), 'nodes': sum(nodes), 'edges': sum(s['edges'] for s in group),
            'directed_links': sum(s['directed'] for s in group),
            'one_way_links': sum(s['one_way'] for s in group),
            'auto_generated_nodes': sum(s['auto'] for s in group),
            'grids_split_in_parts': sum(1 for s in group if s['components'] > 1),
            'nodes_per_grid': quantiles(nodes), 'histogram': histogram(nodes),
            'edge_length': quantiles([round(x) for s in group for x in s['lengths']]),
            'patch_nodes': {str(r): quantiles([n for s in group for n in s['patch'][r]]) for r in PATCH_RADII},
            'edges_longer_than_1024': sum(1 for s in group for x in s['lengths'] if x > 1024),
            'esm_bytes': sum(16 * s['nodes'] + 4 * s['stored_links'] for s in group),
            'compact_bytes': sum(compact_bytes(s['nodes'], s['edges']) for s in group)}


def border_stats(grids, stats):
    """Exterior nodes near a cell edge, and how many face a neighbour cell that has a grid."""
    near = 0; facing = 0
    for key, g in grids.items():
        if g['interior']:
            continue
        x, y = g['grid']
        for p in g['points']:
            lx, ly = p[0], p[1]  # exterior points are cell-local (see coordinate_frame)
            sides = []
            if lx < BORDER: sides.append((x - 1, y))
            if lx > CELL_UNITS - BORDER: sides.append((x + 1, y))
            if ly < BORDER: sides.append((x, y - 1))
            if ly > CELL_UNITS - BORDER: sides.append((x, y + 1))
            if sides:
                near += 1
                facing += any(('e',) + s in grids for s in sides)
    return {'border_nodes': near, 'border_nodes_facing_a_gridded_cell': facing, 'border_units': BORDER}


def coordinate_frame(grids):
    """Whether exterior points are stored cell-local (0..8192) or in world units."""
    local = world = 0
    for g in grids.values():
        if g['interior'] or not g['points']:
            continue
        x, y = g['grid']
        p = g['points'][0]
        if -64 <= p[0] <= CELL_UNITS + 64 and -64 <= p[1] <= CELL_UNITS + 64 and (x, y) != (0, 0):
            local += 1
        else:
            world += 1
    return {'exterior_grids_cell_local': local, 'exterior_grids_world_units': world}


def actor_stats(cells, grids, actors):
    placed = Counter(); placed_cells = Counter(); no_grid = Counter(); actors_no_grid = Counter()
    packages = Counter(); wander_dist = []; no_package = 0
    spawns = Counter(); spawns_no_grid = Counter()
    for key, c in cells.items():
        kind = 'interior' if c['interior'] else 'exterior'
        here = sum(1 for i in c['ids'] if i in actors and actors[i]['kind'] == SPAWN_TAG)
        spawns[kind] += here
        if key not in grids:
            spawns_no_grid[kind] += here
        acts = [actors[i] for i in c['ids'] if i in actors and actors[i]['kind'] != SPAWN_TAG]
        if not acts:
            continue
        placed[kind] += len(acts); placed_cells[kind] += 1
        if key not in grids:
            no_grid[kind] += 1; actors_no_grid[kind] += len(acts)
        for a in acts:
            if not a['ai']:
                no_package += 1
            for name, extra in a['ai']:
                packages[name] += 1
                if name == 'wander':
                    wander_dist.append(extra[0])
    return {'placed_actors': dict(placed), 'placed_levelled_spawns': dict(spawns),
            'levelled_spawns_in_cells_without_grid': dict(spawns_no_grid), 'cells_with_actors': dict(placed_cells),
            'cells_with_actors_but_no_grid': dict(no_grid),
            'actors_in_cells_without_grid': dict(actors_no_grid),
            'placed_ai_packages': dict(packages), 'placed_actors_without_package': no_package,
            'placed_wander_distance': quantiles(wander_dist),
            'placed_wander_distance_zero': sum(1 for d in wander_dist if d == 0)}


def area_stats(cells, grids, stats):
    out = {}
    for area, ((cx, cy), r, prefix) in AREAS.items():
        ext = [('e', x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)]
        ints = [k for k in cells if k[0] == 'i' and cells[k]['name'].casefold().startswith(prefix.casefold())]
        group = lambda keys: [stats[k] for k in keys if k in stats]  # noqa: E731
        ge = group(ext); gi = group(ints)
        out[area] = {'exterior_cells': len(ext), 'exterior_cells_with_grid': len(ge),
                     'exterior_nodes': sum(s['nodes'] for s in ge), 'exterior_edges': sum(s['edges'] for s in ge),
                     'exterior_max_nodes': max((s['nodes'] for s in ge), default=0),
                     'interiors': len(ints), 'interiors_with_grid': len(gi),
                     'interior_nodes': sum(s['nodes'] for s in gi), 'interior_edges': sum(s['edges'] for s in gi),
                     'interior_max_nodes': max((s['nodes'] for s in gi), default=0)}
    return out


def measure(paths, details=False):
    cells, grids, actors, per_master = load(paths)
    stats = {k: graph(g) for k, g in grids.items()}
    inter = [stats[k] for k in stats if grids[k]['interior']]
    exter = [stats[k] for k in stats if not grids[k]['interior']]
    n_int = sum(1 for k in cells if k[0] == 'i'); n_ext = sum(1 for k in cells if k[0] == 'e')
    report = {
        'masters': per_master,
        'cells': {'interior': n_int, 'exterior': n_ext},
        'cells_with_grid': {'interior': len(inter), 'exterior': len(exter)},
        'grids_without_cell': sum(1 for k in grids if k not in cells),
        'granularity': dict(Counter(g['granularity'] for g in grids.values())),
        'all': summarise(list(stats.values())),
        'interior': summarise(inter),
        'exterior': summarise(exter),
        'exterior_borders': border_stats(grids, stats),
        'coordinates': coordinate_frame(grids),
        'actors': actor_stats(cells, grids, actors),
        'areas': area_stats(cells, grids, stats),
    }
    if details:
        report['grids'] = sorted(({'cell': g['name'] or '%d,%d' % g['grid'], 'interior': g['interior'],
                                   'nodes': stats[k]['nodes'], 'edges': stats[k]['edges'],
                                   'components': stats[k]['components']}
                                  for k, g in grids.items()), key=lambda r: -r['nodes'])
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('masters', nargs='+', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--details', action='store_true', help='also list every grid (private use only)')
    args = ap.parse_args(argv)
    text = json.dumps(measure(args.masters, args.details), indent=1, sort_keys=True) + '\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8', newline='\n')
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
