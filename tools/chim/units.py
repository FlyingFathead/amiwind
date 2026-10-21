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
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT_FORMAT = 1           # bump when a unit's pickled result changes shape

# The tool sources of each unit kind as whole files: the key form before code keys ('files' form, kept as the
# previous form every key also computes, so units stored under it are reused: UnitKey.previous). Its data files
# (config/...) stay part of the code-key form too (unit_code_key).
_GEOMETRY = ['tools/prepare_mesh_bsp.py', 'tools/mesh_geometry.py', 'tools/static_lod.py', 'tools/scenery_reduce.py',
             'tools/routed_hull.py', 'tools/visual_primitives.py',
             'tools/surface_flatten.py', 'tools/exterior_visibility.py', 'tools/player_hull.py', 'src/mwad/scene.py',
             'config/surface-flattening.json']
TOOLS = {
    'mesh': _GEOMETRY,
    'mesh-stair': _GEOMETRY + ['tools/stair_mesh.py', 'tools/chim/build.py'],
    'variant': _GEOMETRY + ['tools/surface_grid.py', 'tools/collision_bsp.py', 'tools/prepare_scenery.py', 'tools/nif_common.py',
                            'tools/visual_offsets.py', 'config/visual-offsets.json', 'tools/chim/models.py',
                            'tools/chim/format.py', 'tools/chim/occluders.py'],
    'tiles': _GEOMETRY + ['tools/surface_grid.py', 'tools/prepare_scenery.py', 'tools/nif_common.py', 'tools/visual_offsets.py',
                          'config/visual-offsets.json', 'tools/chim/models.py', 'tools/chim/format.py',
                          'tools/chim/occluders.py', 'tools/chim/cut.py', 'tools/routed_hull.py'],
    'cut': _GEOMETRY + ['tools/surface_grid.py', 'tools/prepare_scenery.py', 'tools/nif_common.py', 'tools/visual_offsets.py',
                        'config/visual-offsets.json', 'tools/chim/models.py', 'tools/chim/format.py',
                        'tools/chim/occluders.py', 'tools/chim/cut.py', 'tools/routed_hull.py'],
    'texture': ['tools/chim/models.py', 'tools/prepare_quake.py', 'tools/prepare_mesh_bsp.py', 'src/mwad/scene.py'],
    'terrain': ['tools/chim/terrain.py', 'tools/chim/models.py', 'tools/mesh_geometry.py', 'tools/surface_grid.py',
                'tools/collision_bsp.py',
                'tools/prepare_mesh_bsp.py', 'tools/chim/format.py', 'tools/player_hull.py'],
    'ocean': ['tools/chim/ocean.py', 'tools/chim/terrain.py', 'tools/chim/models.py', 'tools/mesh_geometry.py',
              'tools/surface_grid.py', 'tools/prepare_mesh_bsp.py', 'tools/chim/format.py', 'tools/player_hull.py',
              'tools/sky_palette_overlay.py'],
    # the collision surface gate (chim.build.hull_surface_gate, CHIM-VIVEC-DOCK-WALKWAY-43)
    'hull-surface': ['tools/mesh_geometry.py', 'tools/player_hull.py', 'src/mwad/scene.py'],
    'pvs': ['tools/chim/visibility.py', 'tools/asset_census.py', 'tools/chim/occluders.py', 'tools/chim/ground.py'],
}
# EXPERIMENTAL edge bevels (chim.bevels, build setting model_bevels tol:N): the default kinds plus that module
TOOLS['variant-bevels'] = TOOLS['variant'] + ['tools/chim/bevels.py']
TOOLS['tiles-bevels'] = TOOLS['tiles'] + ['tools/chim/bevels.py']
# EXPERIMENTAL world format 0.8 (chim.placed, build setting placement_format 0.8): the default kinds plus that module
TOOLS['variant-placed'] = TOOLS['variant'] + ['tools/chim/placed.py']
TOOLS['tiles-placed'] = TOOLS['tiles'] + ['tools/chim/placed.py']
# Build switches read from the environment by the converter functions (the stair rule:
# mesh_geometry.collision_pieces, COLLISION-STAIR-SLOPE-32).
# The standing-hull form (--model-hull, mesh_geometry_env.model_hull_mode) changes every big model's hull:
# a cached unit of one form must never be reused for another (BUILD-CHIM-UNIT-HULL-KEY-33).
SWITCHES = ('AMIWIND_NO_EMISSIVE', 'AMIWIND_NO_FLAMES', 'AMIWIND_SCENERY_REDUCE', 'AMIWIND_SCENERY_REDUCE_TEXELS',
            'AMIWIND_TEXINFO_SNAP', 'AMIWIND_STAIR_MITIGATION', 'AMIWIND_MODEL_HULL', 'AMIWIND_LAVA')
_TOOL_HASH = {}
# Code keys (tools/code_key.py; BUILD-CACHE-CLOSURE-WIDE-33, BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46): the code
# part of a unit's key is what its worker can reach, not the whole files of TOOLS: a collision-hull fix in
# tools/mesh_geometry.py no longer rekeys the terrain units, which run none of it. The entries are the worker and the
# modules whose classes' methods run on objects the worker is handed ('<top>': the reach cannot follow a method of an
# argument);
# run_units records what really ran and stores no unit of a process that ran code outside the key (key_gap).
CODE_ENTRIES = {
    'mesh': [('tools/chim/build.py', 'mesh_unit')],
    # stair collision method 1 builds only (CHIM-STAIR-COLLISION-MESH-47): the default mesh worker run with method 1's
    # collision; its code stays out of the default 'mesh' key
    'mesh-stair': [('tools/stair_mesh.py', 'mesh_unit_stair')],
    'hull-surface': [('tools/chim/build.py', 'hull_surface_unit')],
    'variant': [('tools/chim/models.py', 'variant_unit')],
    'texture': [('tools/chim/models.py', 'texture_unit')],
    'terrain': [('tools/chim/terrain.py', 'terrain_unit')],
    'tiles': [('tools/chim/cut.py', 'tile_unit')],
    # EXPERIMENTAL edge bevels (build setting model_bevels tol:N, chim.bevels): own kinds, so the default kinds' keys
    # never reach that module
    'variant-bevels': [('tools/chim/bevels.py', 'variant_unit_bevels')],
    'tiles-bevels': [('tools/chim/bevels.py', 'tile_unit_bevels')],
    # EXPERIMENTAL world format 0.8 (build setting placement_format 0.8, chim.placed): own kinds, so the default kinds'
    # keys never reach that module
    'variant-placed': [('tools/chim/placed.py', 'variant_unit_placed')],
    'tiles-placed': [('tools/chim/placed.py', 'tile_unit_placed')],
    'cut': [('tools/chim/cut.py', 'cut_unit')],
    'ocean': [('tools/chim/ocean.py', 'build_ocean')],
    # Ground and Occluders (chim/visibility.py, reached as the workers' module) and TriangleGround (chim/ground.py)
    # are handed to the workers as objects
    'pvs': [('tools/chim/visibility.py', 'pvs_unit'), ('tools/chim/visibility.py', 'pvl_unit'),
            ('tools/chim/ground.py', '<top>')],
}
# Off: keys of the 'files' form only (A/B, and what every build used before code keys).
CODE_KEYS_VARIABLE = 'AMIWIND_UNIT_CODE_KEYS'


def code_keys_on():
    return os.environ.get(CODE_KEYS_VARIABLE, 'on') != 'off'


def tool_fingerprint(kind, files=None):
    """Hash of the code and switches of one unit kind: its code key (CODE_ENTRIES, tools/code_key.py) and the data
    files of TOOLS; with FILES, or for a kind without entries, or with AMIWIND_UNIT_CODE_KEYS=off, the whole files
    (files_fingerprint, the form before)."""
    if files or kind not in CODE_ENTRIES or not code_keys_on():
        return files_fingerprint(kind, files)
    switches = tuple(os.environ.get(name, '') for name in SWITCHES)
    key = ('code', kind, switches)
    if key not in _TOOL_HASH:
        h = hashlib.sha256(('chim-unit-%d|%s|code|' % (UNIT_FORMAT, kind)).encode())
        h.update(unit_code_key(kind)['digest'].encode() + b'\0')
        for name, value in zip(SWITCHES, switches):
            h.update(('%s=%s\0' % (name, value)).encode())
        _TOOL_HASH[key] = h.hexdigest()
    return _TOOL_HASH[key]


def unit_code_key(kind):
    """tools/code_key.py code_key of a unit kind: its CODE_ENTRIES' reach and the data files of TOOLS."""
    import code_key
    data = [rel for rel in TOOLS.get(kind, ()) if not rel.endswith('.py')]
    return code_key.code_key(CODE_ENTRIES[kind], data, ROOT)


def files_fingerprint(kind, files=None):
    """Hash of the tool sources (whole files: FILES or TOOLS[kind]) and switches of one unit kind."""
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


class UnitKey(str):
    """A unit fingerprint (str). previous: the same unit's key in the 'files' form (files_fingerprint, with every
    key among its parts in that form too), or None. A unit not found under its key is looked up under previous
    (run_units), so the change of key form costs no unit a rebuild."""
    previous = None

    def __reduce__(self):
        return (_unit_key, (str(self), self.previous))


def _unit_key(value, previous):
    key = UnitKey(value)
    key.previous = previous
    return key


def _previous_parts(value):
    """VALUE with every UnitKey among it replaced by its previous form (LookupError when one has none)."""
    if isinstance(value, UnitKey):
        if value.previous is None:
            raise LookupError(value)
        return value.previous
    if isinstance(value, dict):
        return {k: _previous_parts(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_previous_parts(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_previous_parts(v) for v in value)
    return value


def fingerprint(kind, *parts):
    """Fingerprint of one unit: its kind's tool hash and its own inputs (a UnitKey that also holds its key in the
    'files' form)."""
    blob = json.dumps([tool_fingerprint(kind), _canonical(list(parts))], sort_keys=True, separators=(',', ':'))
    import cache_provenance
    cache_provenance.remember_unit(kind, blob)
    key = UnitKey(hashlib.sha256(blob.encode()).hexdigest())
    if kind in CODE_ENTRIES and code_keys_on():
        try:
            old = _canonical(_previous_parts(list(parts)))
        except LookupError:
            old = None
        if old is not None:
            key.previous = hashlib.sha256(json.dumps([files_fingerprint(kind), old], sort_keys=True,
                                                     separators=(',', ':')).encode()).hexdigest()
    return key


def content_key(*parts):
    """A key of input content alone (no code); with result_key, what a unit's result is keyed by downstream."""
    return hashlib.sha256(json.dumps(_canonical(list(parts)), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def output_digest(value):
    """SHA-256 of a unit's result by content (typed: a tuple is not a list; arrays by dtype, shape and bytes); None
    when it holds a value without a stable form (then nothing after it is cut off)."""
    import numpy as np

    def form(v):
        if isinstance(v, np.ndarray):
            if v.dtype == object:
                raise TypeError('object array')
            return ['A', str(v.dtype), list(v.shape), hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()]
        if isinstance(v, (bytes, bytearray)):
            return ['B', hashlib.sha256(bytes(v)).hexdigest()]
        if isinstance(v, dict):
            return ['D', [[form(k), form(x)] for k, x in v.items()]]
        if isinstance(v, list):
            return ['L', [form(x) for x in v]]
        if isinstance(v, tuple):
            return ['T', [form(x) for x in v]]
        if isinstance(v, (set, frozenset)):
            return ['S', sorted((form(x) for x in v), key=lambda f: json.dumps(f, sort_keys=True))]
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (float, np.floating)):
            return ['F', type(v).__name__, float(v).hex()]
        if isinstance(v, (int, np.integer)):
            return ['I', type(v).__name__, int(v)]
        if isinstance(v, str):
            return ['s', v]
        raise TypeError(type(v).__name__)
    try:
        return hashlib.sha256(json.dumps(form(value), separators=(',', ':')).encode()).hexdigest()
    except (TypeError, ValueError):
        return None


_RESULT_DIGESTS = {}


def result_key(kind, content, value, fallback):
    """The key a unit's result has for the units it feeds (early cutoff, BUILD-CACHE-NO-CUTOFF-33 in the unit
    layer): its input CONTENT (content_key: no code) and the SHA-256 of the result itself, so a unit rebuilt for a
    code change with a byte-identical result keeps the keys of every unit after it. FALLBACK (the unit's own key)
    when the result has no stable form or code keys are off; previous = FALLBACK's previous form."""
    if not code_keys_on():
        return fallback
    # one unit's result is hashed once per process (a mesh is prepared once and placed in many frames)
    memo = str(fallback)
    if memo in _RESULT_DIGESTS:
        digest = _RESULT_DIGESTS[memo]
    else:
        if len(_RESULT_DIGESTS) > 200000:
            _RESULT_DIGESTS.clear()
        digest = _RESULT_DIGESTS[memo] = output_digest(value)
    if digest is None:
        return fallback
    key = UnitKey(hashlib.sha256(('chim-result|%s|%s|%s' % (kind, content, digest)).encode()).hexdigest())
    key.previous = getattr(fallback, 'previous', None)
    return key


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
            import cache_provenance
            cache_provenance.verify_file(path)
        except Exception:  # noqa: BLE001 - a damaged entry is rebuilt and counted
            self.stats.setdefault(kind, {}).setdefault('damaged', 0)
            self.stats[kind]['damaged'] += 1
            return None
        import cache_provenance
        cache_provenance.reused(self.folder, kind, fp, stored_fp == fp)
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
            tmp.write_bytes(pickle.dumps((str(fp), value), protocol=4))
            tmp.replace(path)
            import cache_provenance
            cache_provenance.sidecar_unit(path, kind, fp)
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


# Unit kinds whose built units this process no longer stores: a worker ran code outside the kind's code key
# ({kind: [(path, function)]}; run_units).
KEY_GAPS = {}


def _traced(worker, task):
    """A pool worker's call, with the repository code it ran first in its process (code_key.Tracer)."""
    import code_key
    tracer = code_key.tracer()
    tracer.begin()
    try:
        value = worker(task)
    finally:
        tracer.end()
    return value, tracer.take()


def run_units(kind, items, worker, jobs, cache):
    """items: [(fingerprint, task)]; returns results in order. Misses run through the pool.

    A unit not in the cache under its key is looked up under the key's previous form (UnitKey.previous). For a kind
    with a code key (CODE_ENTRIES) every built unit's worker is traced, and this call's units are stored only when
    no worker ran a repository function outside the key's reach (code_key.uncovered). Otherwise none of them is
    stored, nor any later unit of the kind in this process (KEY_GAPS), and the gap is printed and counted (key_gap):
    a gap costs reuse, never a unit reused for code its key does not hold. (A function reports once per process, in
    the call where it first ran there; so a process's earlier units never ran a function its later call reports.)"""
    from functools import partial
    from build_parallel import ordered_map
    cache = cache or UnitCache()
    results = [None] * len(items)
    todo = []
    previous_hits = 0
    for i, (fp, task) in enumerate(items):
        hit = cache.get(kind, fp)
        if hit is None and getattr(fp, 'previous', None):
            hit = cache.get(kind, fp.previous)
            previous_hits += hit is not None
        if hit is not None:
            results[i] = hit
        else:
            todo.append(i)
    traced = kind in CODE_ENTRIES and code_keys_on()
    if todo:
        call = partial(_traced, worker) if traced else worker
        ran, untraced = set(), False
        for i, value in zip(todo, ordered_map(call, [items[i][1] for i in todo], max(1, min(jobs, len(todo))))):
            if traced:
                value, executed = value
                if executed is None:
                    untraced = True
                else:
                    ran.update(executed)
            results[i] = value
        store = kind not in KEY_GAPS
        if traced and store:
            import code_key
            if untraced:
                gaps = [('no trace', 'Python %d.%d has no sys.monitoring' % sys.version_info[:2])]
            else:
                gaps = code_key.uncovered(ran, unit_code_key(kind), ROOT)
            if gaps:
                KEY_GAPS[kind] = gaps
                store = False
                print('[warning] CHIM %s units: a worker ran code outside the unit key (%s); no %s unit is stored in '
                      'the unit cache from here on (fix: its entry in chim.units.CODE_ENTRIES)' % (
                          kind, ', '.join('%s %s' % g for g in gaps[:5]) + (' ...' if len(gaps) > 5 else ''), kind),
                      flush=True)
        if store:
            for i in todo:
                cache.put(kind, items[i][0], results[i])
        else:
            s = cache.stats.setdefault(kind, {})
            s['key_gap'] = s.get('key_gap', 0) + len(todo)
    cache.count(kind, len(todo), len(items) - len(todo))
    if previous_hits:
        s = cache.stats.setdefault(kind, {})
        s['reused_previous_key'] = s.get('reused_previous_key', 0) + previous_hits
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
