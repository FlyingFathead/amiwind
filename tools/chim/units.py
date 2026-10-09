# SPDX-License-Identifier: GPL-3.0-only
"""Build units of the CHIM builder: fingerprints, the unit cache, the parallel runner, timers.

Every independent piece of work (a mesh, a model variant, a texture, a chunk's
terrain, a block of visibility rows) is a unit with a fingerprint: the hashes
of its inputs, of the tool sources that make it and of the switches that
change it. A unit whose fingerprint is in the cache is reused, and the
receipt counts every reuse; anything else is built, in parallel through
build_parallel.ordered_map with exactly --jobs workers, and stored. Results
never depend on the worker count or on reuse (tests compare the bytes).
"""
import hashlib
import json
import os
import pickle
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT_FORMAT = 1           # bump when a unit's pickled result changes shape

# Tool sources whose bytes are part of each unit's fingerprint.
_GEOMETRY = ['tools/prepare_mesh_bsp.py', 'tools/mesh_geometry.py', 'tools/static_lod.py', 'tools/scenery_reduce.py',
             'tools/routed_hull.py',
             'tools/surface_flatten.py', 'tools/exterior_visibility.py', 'tools/player_hull.py', 'src/mwad/scene.py',
             'config/surface-flattening.json']
TOOLS = {
    'mesh': _GEOMETRY,
    'variant': _GEOMETRY + ['tools/surface_grid.py', 'tools/collision_bsp.py', 'tools/prepare_scenery.py',
                            'tools/visual_offsets.py', 'config/visual-offsets.json', 'tools/chim/models.py',
                            'tools/chim/format.py', 'tools/chim/occluders.py'],
    'tiles': _GEOMETRY + ['tools/surface_grid.py', 'tools/prepare_scenery.py', 'tools/visual_offsets.py',
                          'config/visual-offsets.json', 'tools/chim/models.py', 'tools/chim/format.py',
                          'tools/chim/occluders.py', 'tools/chim/cut.py', 'tools/routed_hull.py'],
    'cut': _GEOMETRY + ['tools/surface_grid.py', 'tools/prepare_scenery.py', 'tools/visual_offsets.py',
                        'config/visual-offsets.json', 'tools/chim/models.py', 'tools/chim/format.py',
                        'tools/chim/occluders.py', 'tools/chim/cut.py', 'tools/routed_hull.py'],
    'texture': ['tools/chim/models.py', 'tools/prepare_quake.py', 'tools/prepare_mesh_bsp.py', 'src/mwad/scene.py'],
    'terrain': ['tools/chim/terrain.py', 'tools/chim/models.py', 'tools/mesh_geometry.py', 'tools/surface_grid.py',
                'tools/collision_bsp.py',
                'tools/prepare_mesh_bsp.py', 'tools/chim/format.py', 'tools/player_hull.py'],
    'pvs': ['tools/chim/visibility.py', 'tools/asset_census.py', 'tools/chim/occluders.py', 'tools/chim/ground.py'],
}
# Build switches read from the environment by the converter functions (the stair rule:
# mesh_geometry.collision_pieces, COLLISION-STAIR-SLOPE-32).
# The standing-hull form (--model-hull, mesh_geometry_env.model_hull_mode) changes every big model's hull:
# a cached unit of one form must never be reused for another (BUILD-CHIM-UNIT-HULL-KEY-33).
SWITCHES = ('AMIWIND_NO_EMISSIVE', 'AMIWIND_NO_FLAMES', 'AMIWIND_SCENERY_REDUCE', 'AMIWIND_SCENERY_REDUCE_TEXELS',
            'AMIWIND_TEXINFO_SNAP', 'AMIWIND_STAIR_MITIGATION', 'AMIWIND_MODEL_HULL')
_TOOL_HASH = {}


def tool_fingerprint(kind, files=None):
    """Hash of the tool sources and switches of one unit kind."""
    switches = tuple(os.environ.get(name, '') for name in SWITCHES)
    key = (kind, tuple(files) if files else None, switches)
    if key not in _TOOL_HASH:
        h = hashlib.sha256(('chim-unit-%d|%s|' % (UNIT_FORMAT, kind)).encode())
        for rel in files or TOOLS[kind]:
            path = ROOT / rel
            h.update(rel.encode() + b'\0')
            h.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b'missing')
        for name, value in zip(SWITCHES, switches):
            h.update(('%s=%s\0' % (name, value)).encode())
        _TOOL_HASH[key] = h.hexdigest()
    return _TOOL_HASH[key]


def _canonical(value):
    """A stable byte form of nested inputs (dicts sorted, floats exact, arrays by content)."""
    import numpy as np
    if isinstance(value, np.ndarray):
        return ['ndarray', str(value.dtype), list(value.shape), hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()]
    if isinstance(value, (bytes, bytearray)):
        return ['bytes', hashlib.sha256(bytes(value)).hexdigest()]
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, float):
        return ['f', value.hex()]
    if isinstance(value, (np.floating,)):
        return ['f', float(value).hex()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return ['repr', repr(value)]


def fingerprint(kind, *parts):
    """Fingerprint of one unit: its kind's tool hash and its own inputs."""
    blob = json.dumps([tool_fingerprint(kind), _canonical(list(parts))], sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode()).hexdigest()


class UnitCache:
    """Pickled unit results by fingerprint under one folder; counts reuse and builds per kind."""

    def __init__(self, folder=None):
        self.folder = Path(folder) if folder else None
        self.stats = {}

    def _path(self, kind, fp):
        return self.folder / kind / (fp[:2]) / (fp + '.pickle')

    def get(self, kind, fp):
        if self.folder is None:
            return None
        path = self._path(kind, fp)
        if not path.is_file():
            return None
        try:
            stored_fp, value = pickle.loads(path.read_bytes())
        except Exception:  # noqa: BLE001 - a damaged entry is rebuilt and counted
            self.stats.setdefault(kind, {}).setdefault('damaged', 0)
            self.stats[kind]['damaged'] += 1
            return None
        return value if stored_fp == fp else None

    def put(self, kind, fp, value):
        if self.folder is None:
            return
        path = self._path(kind, fp)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_bytes(pickle.dumps((fp, value), protocol=4))
        tmp.replace(path)

    def count(self, kind, built, reused):
        s = self.stats.setdefault(kind, {})
        s['built'] = s.get('built', 0) + built
        s['reused'] = s.get('reused', 0) + reused


def run_units(kind, items, worker, jobs, cache):
    """items: [(fingerprint, task)]; returns results in order. Misses run through the pool."""
    from build_parallel import ordered_map
    cache = cache or UnitCache()
    results = [None] * len(items)
    todo = []
    for i, (fp, task) in enumerate(items):
        hit = cache.get(kind, fp)
        if hit is not None:
            results[i] = hit
        else:
            todo.append(i)
    if todo:
        for i, value in zip(todo, ordered_map(worker, [items[i][1] for i in todo], max(1, min(jobs, len(todo))))):
            results[i] = value
            cache.put(kind, items[i][0], value)
    cache.count(kind, len(todo), len(items) - len(todo))
    return results


class Timer:
    """section('name') records wall seconds and CPU seconds (this process and its finished workers)."""

    def __init__(self):
        self.sections = []

    @contextmanager
    def section(self, name):
        t0, c0 = time.perf_counter(), os.times()
        try:
            yield
        finally:
            t1, c1 = time.perf_counter(), os.times()
            cpu = sum(getattr(c1, k) - getattr(c0, k) for k in ('user', 'system', 'children_user', 'children_system'))
            self.sections.append({'section': name, 'seconds': round(t1 - t0, 3), 'cpu_seconds': round(cpu, 3)})

    def report(self):
        return {'sections': self.sections, 'seconds': round(sum(s['seconds'] for s in self.sections), 3),
                'cpu_seconds': round(sum(s['cpu_seconds'] for s in self.sections), 3)}
