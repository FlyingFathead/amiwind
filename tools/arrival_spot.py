#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Town arrivals checked against converted collision (VIVEC-ARENA-TP-ARRIVAL-32).

`standing_spot` is the engine's arrival search (aw_scene.c standing_spot) on a
converted BSP: from the requested point, eight 16-unit neighbours, then lower
by 8 units at a time down to 64, the first spot with a walkable floor, a clear
standing hull and dry feet. The town importer stores that spot as the town's
arrival, so the engine's first candidate is valid; `check` verifies every
town directory of a finished payload: the arrival is a standing spot (hull
clear, walkable ground within the step height, dry feet) and a return point
resolves to one.

Usage: arrival_spot.py ID1_DIR [--out report.json]
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_walkability import Scene, dot  # noqa: E402
from player_hull import MINS, WALKABLE_Z, STEP_HEIGHT  # noqa: E402

OFFSETS = ((0, 0), (16, 0), (-16, 0), (0, 16), (0, -16), (16, 16), (-16, 16), (16, -16), (-16, -16))
CONTENTS_EMPTY = -1


class Collision:
    """Standing hull (engine hull 1, world and func_wall) plus world contents."""

    def __init__(self, raw):
        self.hull = Scene(raw, hull=1)
        self.point = Scene(raw, hull=0)

    def solid(self, p):
        hit = self.hull.trace(p, (p[0], p[1], p[2] - 1e-3))
        return bool(hit and hit['fraction'] == 0)

    def contents(self, p):
        """World point contents (SV_PointContents): -1 empty, -2 solid, -3 water."""
        node = self.point.brushes[0][0]
        while node >= 0:
            plane, front, back = self.point.nodes[node]
            normal_dist = self.point.planes[plane]
            node = front if dot(p, normal_dist[:3]) - normal_dist[3] >= 0 else back
        return node

    def dry(self, p):
        return self.contents((p[0], p[1], p[2] + MINS[2] + 1)) == CONTENTS_EMPTY

    def ground(self, p, depth):
        """Height of walkable ground within depth below the standing origin, or None."""
        hit = self.hull.trace(p, (p[0], p[1], p[2] - depth))
        if not hit or hit['fraction'] == 0 or hit['normal'][2] < WALKABLE_Z:
            return None
        return p[2] - depth * hit['fraction']


def standing_spot(collision, preferred):
    """The engine's arrival search: the first valid spot, or None."""
    for drop in range(0, 65, 8):
        for dx, dy in OFFSETS:
            top = (preferred[0] + dx, preferred[1] + dy, preferred[2] + 8 - drop)
            floor = collision.ground(top, 32)
            if floor is None:
                continue
            point = (top[0], top[1], floor + .25)
            if collision.solid(point) or not collision.dry(point):
                continue
            return point
    return None


def standing(collision, point):
    """A stored arrival must itself be a spot: hull clear, ground within a step, dry."""
    floor = collision.ground(point, STEP_HEIGHT + .25)
    return not collision.solid(point) and floor is not None and collision.dry(point)


def owner(directory, point):
    for row in directory['regions']:
        x0, y0, x1, y1 = row['core']
        if x0 <= point[0] < x1 and y0 <= point[1] < y1:
            return row['name']
    for row in directory['regions']:
        x0, y0, x1, y1 = row['core']
        if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
            return row['name']
    raise ValueError('No region owns the point %r' % (point,))


def read_directory(path):
    """AWBR1 region directory (aw_region.c read_regions)."""
    lines = Path(path).read_text().splitlines()
    head = lines[0].split()
    if head[0] != 'AWBR1':
        raise ValueError('Not a region directory: %s' % path)
    values = list(map(float, head[4:12]))
    regions = [dict(name=v[0], core=list(map(float, v[1:5]))) for v in (line.split() for line in lines[1:])]
    return dict(arrival=tuple(values[0:3]), yaw=values[3], return_point=tuple(values[4:7]), regions=regions)


def check(id1, towns=None):
    """Every runtime town directory present in id1: arrival and return point."""
    from town_config import runtime_towns
    id1 = Path(id1)
    rows, errors, cache = [], [], {}
    towns = towns or runtime_towns()
    directories = {t['name']: id1 / t['regions'] for t in towns if (id1 / t['regions']).is_file()}

    def collision(name):
        if name not in cache:
            cache[name] = Collision((id1 / 'maps' / (name + '.bsp')).read_bytes())
        return cache[name]
    for town in towns:
        name = town['name']
        if name not in directories:
            continue
        directory = read_directory(directories[name])
        targets = [('arrival', name, directory['arrival'])]
        travel = town.get('travel_target') or ''
        # A return point is used only by towns whose travel returns (aw_scene.c travel_return).
        if town.get('travel_return') and travel in directories:
            targets.append(('return', travel, directory['return_point']))
        for kind, area, point in targets:
            region = owner(read_directory(directories[area]), point)
            c = collision(region)
            spot = standing_spot(c, point)
            row = dict(town=name, kind=kind, area=area, region=region, point=list(point),
                       spot=list(spot) if spot else None,
                       standing=standing(c, point) if kind == 'arrival' else None)
            if spot is None or (kind == 'arrival' and not row['standing']):
                errors.append(dict(row, error='Arrival is not a valid standing spot' if spot else
                                   'No standing spot reachable by the engine arrival search'))
            rows.append(row)
    return dict(format=1, status='failed' if errors else 'passed', rows=rows, errors=errors,
                rule='engine arrival search (aw_scene.c standing_spot): hull 1 clear, walkable floor, dry feet; '
                     'stored arrivals are themselves standing spots (ground within STEPSIZE %.1f)' % STEP_HEIGHT)


def require(id1, output=None, towns=None):
    report = check(id1, towns)
    if output:
        Path(output).write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    if report['status'] != 'passed':
        raise ValueError('Town arrival check failed: ' + '; '.join(
            '%s %s %s at %s' % (e['town'], e['kind'], e['error'], e['point']) for e in report['errors']))
    return report


def resolve(scenes, entries, arrival, owner_of):
    """The importer's rule for every town: the original arrival pose resolved by
    the engine's arrival search on the converted collision of the region that
    owns it. scenes(name) returns that region's BSP bytes. Fails closed."""
    point = tuple(arrival)
    for _ in range(3):
        name = entries[owner_of(point, entries)]['name']
        spot = standing_spot(Collision(scenes(name)), point)
        if spot is None:
            raise ValueError('Town arrival %r has no standing spot in %s' % (tuple(arrival), name))
        if entries[owner_of(spot, entries)]['name'] == name:
            return list(spot)
        point = spot
    raise ValueError('Town arrival does not settle in one region: %r' % (tuple(arrival),))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('id1', type=Path)
    parser.add_argument('--out', type=Path)
    a = parser.parse_args()
    try:
        report = require(a.id1, a.out)
    except ValueError as exc:
        parser.exit(1, 'Error: %s\n' % exc)
    for row in report['rows']:
        print(row['town'], row['kind'], row['region'], row['point'], '->', row['spot'])


if __name__ == '__main__':
    main()
