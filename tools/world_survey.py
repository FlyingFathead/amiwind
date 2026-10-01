# SPDX-License-Identifier: GPL-3.0-only
"""Offline world-space measurements; no native engine or gameplay mutations."""
import math
from pathlib import Path
import json
import numpy as np

CELL_SIZE = 8192
SUBTILES = 4


def cell_of(point):
    if len(point) < 2 or not all(math.isfinite(v) for v in point[:2]):
        raise ValueError('Expected finite world XY')
    return [math.floor(v / CELL_SIZE) for v in point[:2]]


def local_to_world(point, area):
    if len(point) != 3 or not all(math.isfinite(v) for v in point) or not math.isfinite(area['scale']) or area['scale'] <= 0:
        raise ValueError('Expected finite local XYZ')
    return [point[i] / area['scale'] + (area['centre'][i] if i < 2 else 0) for i in range(3)]


def world_to_local(point, area):
    local_to_world(point, area)  # Shared finite-coordinate/positive-scale validation.
    return [(point[i] - (area['centre'][i] if i < 2 else 0)) * area['scale'] for i in range(3)]


def area_catalogue(root):
    from balmora_regions import regions as balmora_regions
    from prepare_seyda_regions import regions as seyda_regions
    out = []
    for name, file, builder in [('Balmora', 'balmora.json', balmora_regions),
                                ('Seyda Neen', 'seyda_area.json', lambda _: seyda_regions())]:
        config = json.loads((Path(root) / 'config' / file).read_text())
        rows = builder(config)
        area = dict(name=name, centre=config['centre'], scale=config['scale'], regions=[])
        for row in rows:
            r = dict(name=row['name'])
            for key in ('core', 'coverage'):
                r[key] = [local_to_world([*point, 0], area)[:2] for point in row[key]]
            area['regions'].append(r)
        out.append(area)
    return out


def triangle_bins(centres, reference, size=CELL_SIZE // SUBTILES):
    from prepare_scenery import reference_rotation
    points = np.asarray(centres, dtype=np.float64) @ reference_rotation(reference).T
    points = points * reference['scale'] + reference['position']
    bins, counts = np.unique(np.floor(points[:, :2] / size).astype(np.int64), axis=0, return_counts=True)
    return [(tuple(map(int, key)), int(count)) for key, count in zip(bins, counts)]


def candidate_boxes(cell, divisions, overlap):
    if divisions not in (1, 2, 4, 8) or not math.isfinite(overlap) or overlap < 0:
        raise ValueError('Invalid bounded subdivision')
    side = CELL_SIZE / divisions
    for y in range(divisions):
        for x in range(divisions):
            lo = [(cell[0] * CELL_SIZE + x * side), (cell[1] * CELL_SIZE + y * side)]
            yield [[v - overlap for v in lo], [v + side + overlap for v in lo]]


class SpatialIndex:
    """Whole placed AABBs, indexed across every source cell they intersect."""
    def __init__(self, rows):
        self.rows = rows
        self.bounds = np.asarray([r['bounds'] for r in rows], dtype=float).reshape(-1, 2, 3)
        self.triangles = np.asarray([r['triangles'] for r in rows], dtype=np.int64)
        if not np.isfinite(self.bounds).all() or np.any(self.bounds[:, 0] > self.bounds[:, 1]) or np.any(self.triangles < 0):
            raise ValueError('Invalid placed geometry bounds or counts')
        self.bins = {}
        for i, box in enumerate(self.bounds):
            a, b = np.floor(box[:, :2] / CELL_SIZE).astype(int)
            if np.prod(b - a + 1) > 4096:
                raise ValueError('Excessive placed bounds require investigation')
            for y in range(a[1], b[1] + 1):
                for x in range(a[0], b[0] + 1):
                    self.bins.setdefault((x, y), []).append(i)

    def select(self, box):
        box = np.asarray(box, dtype=float)
        if box.shape != (2, 2) or not np.isfinite(box).all() or np.any(box[0] > box[1]):
            raise ValueError('Invalid query bounds')
        a, b = np.floor(np.asarray(box) / CELL_SIZE).astype(int)
        ids = set()
        for y in range(a[1], b[1] + 1):
            for x in range(a[0], b[0] + 1):
                ids.update(self.bins.get((x, y), []))
        ids = np.array(sorted(ids), dtype=int)
        if not len(ids):
            return ids
        bounds = self.bounds[ids, :, :2]
        keep = np.all(bounds[:, 1] >= box[0], axis=1) & np.all(bounds[:, 0] <= box[1], axis=1)
        return ids[keep]

    def measure(self, box):
        ids = self.select(box)
        return dict(placed_source_triangles=int(self.triangles[ids].sum()), references=len(ids))


def evaluate_cell(cell, index, limit, overlap):
    """Screen options against reference geometry, never certify a runtime budget."""
    if not math.isfinite(limit) or limit <= 0:
        raise ValueError('Expected positive screening limit')
    options = []
    for divisions in (1, 2, 4, 8):
        costs = [index.measure(box) for box in candidate_boxes(cell, divisions, overlap)]
        peak = max(c['placed_source_triangles'] for c in costs)
        options.append(dict(divisions=divisions, regions=divisions ** 2,
                            peak_source_triangles=peak,
                            duplicated_source_triangles=sum(c['placed_source_triangles'] for c in costs),
                            peak_references=max(c['references'] for c in costs)))
        if peak <= limit:
            return dict(candidate=divisions, status='geometry-screen-only', options=options)
    return dict(candidate=None, status='overlap-floor-or-conversion-review', options=options)
