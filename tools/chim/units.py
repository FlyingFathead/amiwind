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
            'AMIWIND_TEXINFO_SNAP', 'AMIWIND_STAIR_MITIGATION', 'AMIWIND_MODEL_HULL', 'AMIWIND_LAVA')
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
        try:
            if not path.is_file():
                return None
            stored_fp, value = pickle.loads(path.read_bytes())
        except Exception:  # noqa: BLE001 - a damaged entry is rebuilt and counted
            self.stats.setdefault(kind, {}).setdefault('damaged', 0)
            self.stats[kind]['damaged'] += 1
            return None
        return value if stored_fp == fp else None

    def put(self, kind, fp, value):
        """Store a built unit. A cache that cannot be written never fails the stage: the unit was built
        locally, the refusal is counted ('write_refused') and reported once per kind
        (BUILD-CACHE-OWNER-FAILS-STAGE-34: entries owned by another user stopped a release build)."""
        if self.folder is None:
            return
        path = self._path(kind, fp)
        tmp = path.with_name(f'{path.stem}.{os.getpid()}.tmp')
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(pickle.dumps((fp, value), protocol=4))
            tmp.replace(path)
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            s = self.stats.setdefault(kind, {})
            if not s.get('write_refused'):
                print(f'[warning] cache write refused: {path.parent} ({exc.strerror or exc}); the unit was built '
                      f'locally and the build continues (fix: make {self.folder} writable by this user)', flush=True)
            s['write_refused'] = s.get('write_refused', 0) + 1

    def count(self, kind, built, reused):
        s = self.stats.setdefault(kind, {})
        s['built'] = s.get('built', 0) + built
        s['reused'] = s.get('reused', 0) + reused


# Unit keys in the shared storage pool: POOL/keys/chim-unit/<kind>/FP[:2]/FP.json names the SHA-256 of the
# pickled unit, stored once in POOL/objects (tools/storage_pool.py, tools/file_cache.py key layout, so the one
# garbage collector, tools/build_gc.py, sees every unit an index names).
POOL_NAMESPACE = 'chim-unit'


class PooledUnitCache(UnitCache):
    """A unit cache backed by the shared, content-addressed storage pool (CHIMPORT-NO-SHARED-POOL-35).

    get: a unit missing from this run's folder is looked up by its fingerprint in the pool and placed into the
    folder (a read-only hard link with link=True, else a verified copy), so a unit any earlier run or workspace
    built is never built again. put: the built unit is written as before, then stored once in the pool (by a hard
    link: no second copy) and its key recorded; a unit whose key already names an intact object links to it.
    A pool problem never fails the stage: the unit stays in the run folder and the problem is counted."""

    def __init__(self, folder, pool, link=True, store=True):
        """LINK: units found in the pool are hard-linked into FOLDER (else copied); STORE: built units go to the pool."""
        super().__init__(folder)
        from file_cache import FileCache
        self.pool = Path(pool)
        self.link = link
        self.store = store
        self._keys = {}
        self._FileCache = FileCache
        self.pool_stats = {'reused_units': 0, 'reused_bytes': 0, 'stored_units': 0, 'stored_bytes': 0,
                           'linked_units': 0, 'linked_bytes': 0, 'errors': 0}

    def _index(self, kind):
        if kind not in self._keys:
            self._keys[kind] = self._FileCache(self.pool, '%s/%s' % (POOL_NAMESPACE, kind), None, fallback=False)
        return self._keys[kind]

    def _pool_count(self, kind, name, size):
        self.pool_stats[name + '_units'] += 1
        self.pool_stats[name + '_bytes'] += size
        s = self.stats.setdefault(kind, {})
        s['pool_' + name] = s.get('pool_' + name, 0) + 1

    def get(self, kind, fp):
        if self.folder is not None and not self._path(kind, fp).is_file():
            meta = self._index(kind).lookup(fp)
            if meta is not None:
                import storage_pool
                try:
                    if storage_pool.place(self.pool, meta['sha256'], self._path(kind, fp), link=self.link):
                        self._pool_count(kind, 'reused', int(meta.get('bytes') or 0))
                except OSError:
                    self.pool_stats['errors'] += 1
        return super().get(kind, fp)

    def put(self, kind, fp, value):
        UnitCache.put(self, kind, fp, value)
        if self.folder is None or not self.store:
            return
        import storage_pool
        path = self._path(kind, fp)
        try:
            digest = storage_pool.sha256_file(path)
            size = path.stat().st_size
            index = self._index(kind)
            known = index.lookup(fp)
            if known is not None and known['sha256'] != digest and self.link and \
                    storage_pool.place(self.pool, known['sha256'], path, link=True):
                # Same key, other pickle bytes (an equal value): keep the pooled object, drop this copy.
                self._pool_count(kind, 'linked', size)
                return
            existed = storage_pool.object_path(self.pool, digest).is_file()
            # Stored by a hard link (the run's file becomes the pooled inode); across mounts the pool gets one
            # verified copy. As root or on Windows nothing is written to the shared pool (read-only use: shared
            # caches are written only by the build user), as for the builder's own pooling.
            if storage_pool.put(self.pool, path, digest)[0] == 'skipped':
                return
            if known is None or known['sha256'] != digest:
                index.point(fp, digest, size, {'kind': kind})
            self._pool_count(kind, 'linked' if existed else 'stored', size)
        except OSError as exc:
            if not self.pool_stats['errors']:
                print('[warning] storage pool not used for a %s unit (%s); the unit stays in the run folder and '
                      'the build continues' % (kind, exc), flush=True)
            self.pool_stats['errors'] += 1


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
