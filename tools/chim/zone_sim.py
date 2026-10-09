# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM zone walk gate: the engine's own zone allocator (engine/aga/src/chim/chim_zone.c,
compiled for the host) driven by the engine's ring rules over walks through a CHIM world.

Why (CHIM-CHUNK-LOAD-FAIL-33): the heap gate (chim/heap.py) adds up what the active ring needs
at one position. The engine's zone never moves a block, so a ring that fits by the sum can
still fail when locked blocks split the free room into pieces smaller than a large model; and
chunks stay active out to the load radius, past the active ring the heap gate counts. Only the
allocator itself, fed the real block sizes in the order a walk asks for them, shows that.

What is simulated (chim_chunks.c ChimChunks_Tick and chim_models.c, per player step):
- a chunk is loaded (catalogue, terrain, then each model with its textures) when within the
  load radius, nearest first; past the active radius only into free room (PrefetchRoom: twice
  the bytes plus 64 KiB must fit the largest free block);
- within the active radius it is activated: catalogue, terrain and its models locked;
- an active chunk past the load radius is deactivated (locks dropped, blocks cached);
- a model keeps one lock on each texture it uses while it is resident (ResolveTexture);
- the zone is the engine's: chim_zone_kib from the Hunk, the loading buffer, the world and
  frame indices, the frame-world pool (twice chim_pool_kib), locked for the map;
- the full-zone methods of the engine: chim_zone_ends, chim_release, chim_partial (same
  meaning as the cvars, defaults read from the engine source; 0 is the first method of each).

Block sizes are the target ABI's (heap.image_bytes and texture_bytes, the strict heap gate's
probe); the zone's own block header is the host's (larger than the Amiga's 32 bytes), so the
simulation is slightly pessimistic.

Results per walk: chunk loads that failed for room within the active radius, chunks within the
collision margin left without ground at the end of a step (holes), chunks released for nearer
ones, partial activations, peak locked bytes, evictions and loads (thrash).
"""
import ctypes
import math
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'engine/aga/src'
KIND = {'index': 1, 'buffer': 2, 'model': 3, 'chunk': 4, 'terrain': 5, 'texture': 6, 'world': 7}
SHIM = r'''
#include <stdarg.h>
#include "quakedef.h"
#include "chim/chim_zone.h"
void Sys_Error (char *fmt, ...)
{
	va_list a;
	va_start (a, fmt); vfprintf (stderr, fmt, a); va_end (a); fputc ('\n', stderr);
	abort ();
}
'''


class Stats(ctypes.Structure):
    _fields_ = [('banks', ctypes.c_int), ('blocks', ctypes.c_int), ('locked', ctypes.c_int),
                ('used_bytes', ctypes.c_int), ('free_bytes', ctypes.c_int), ('largest_free', ctypes.c_int),
                ('kind_blocks', ctypes.c_int * 8), ('kind_bytes', ctypes.c_int * 8),
                ('locked_bytes', ctypes.c_long), ('locked_peak', ctypes.c_long),
                ('allocations', ctypes.c_ulong), ('evictions', ctypes.c_ulong), ('failures', ctypes.c_ulong),
                ('trims', ctypes.c_ulong)]


def build_library(out_dir, source=SRC, compiler=None):
    """Compile chim_zone.c and a Sys_Error shim into a shared library; returns its path."""
    cc = compiler or os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
    if not cc:
        raise RuntimeError('no C compiler for the zone walk gate')
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shim = out_dir / 'zone_shim.c'
    shim.write_text(SHIM, encoding='utf-8', newline='\n')
    from project_version import generate_native
    generate_native(ROOT / 'VERSION', out_dir)
    lib = out_dir / 'libchimzone.so'
    cmd = [cc, '-std=gnu89', '-O2', '-shared', '-fPIC', '-I' + str(out_dir), '-I' + str(source),
           str(Path(source) / 'chim/chim_zone.c'), str(shim), '-o', str(lib)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('zone library: ' + result.stdout + result.stderr)
    return lib


class Zone:
    """The engine's zone through ctypes: one bank of the map's size."""

    EVICT = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint)

    def __init__(self, lib_path, zone_bytes, ends):
        self.lib = ctypes.CDLL(str(lib_path))
        L = self.lib
        L.ChimZone_Alloc.restype = ctypes.c_void_p
        L.ChimZone_Alloc.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        for name in ('ChimZone_Lock', 'ChimZone_Unlock', 'ChimZone_FreeData', 'ChimZone_Touch'):
            getattr(L, name).argtypes = [ctypes.c_void_p]
        L.ChimZone_AddBank.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        L.ChimZone_LargestUnlocked.restype = ctypes.c_int
        L.ChimZone_Reset()
        self.memory = ctypes.create_string_buffer(zone_bytes + 64)
        if L.ChimZone_AddBank(ctypes.addressof(self.memory), zone_bytes, 0) < 0:
            raise RuntimeError('zone bank refused')
        L.ChimZone_SetEnds(int(ends))       # chim_zone_ends in bytes (0: first fit, the first method)
        self.callbacks = {}

    def on_evict(self, kind, fn):
        cb = self.EVICT(lambda data, ident: fn(data, ident))
        self.callbacks[kind] = cb
        self.lib.ChimZone_SetEvict(KIND[kind], cb)

    def alloc(self, size, kind, ident):
        return self.lib.ChimZone_Alloc(None, int(size), KIND[kind], ident) or None

    def lock(self, p):
        self.lib.ChimZone_Lock(p)

    def unlock(self, p):
        self.lib.ChimZone_Unlock(p)

    def touch(self, p):
        self.lib.ChimZone_Touch(p)

    def stats(self):
        s = Stats()
        self.lib.ChimZone_Stats(ctypes.byref(s))
        return s

    def failures(self):
        return self.lib.ChimZone_Failures(None)


def block_sizes(world, sizes):
    """Zone request sizes (bytes, without the zone's header) for every model, texture, chunk
    catalogue and chunk terrain of the world (chim.validate.load_world layout)."""
    from chim import format as F
    from chim import heap as H
    hunk = sizes['hunk']
    model_bytes, model_tex = [], []
    for m in world['models']:
        lumps = F.read_brush_image(m['image'])
        model_bytes.append(H.image_bytes(lumps, sizes) - hunk + 64)       # + chim_model_t's arena record
        model_tex.append(F.read_texture_refs(lumps[2]))
    tex_bytes = [H.texture_bytes(t['width'], t['height'], sizes) - hunk for t in world['textures']]
    entry = sizes.get('scenery', sizes['entity'])
    frames = []
    for path, frame, chunks in world['frames']:
        out = []
        for c in chunks:
            lumps = F.read_brush_image(c['image'])
            records = c['owned'] + c['reach']
            out.append({
                'catalogue': 64 + len(records) * (entry + 48 + sizes['pointer'] + 8) + len(c.get('pvs', b'')) +
                len(c.get('pvl', b'')),
                'terrain': H.image_bytes(lumps, sizes) - hunk + 64,
                'terrain_textures': F.read_texture_refs(lumps[2]),
                'models': sorted({r['model'] for r in records}),
                'box': (frame['low'][0] + c['cx'] * frame['grain'], frame['low'][1] + c['cy'] * frame['grain'],
                        frame['grain'])})
        frames.append((path, frame, out))
    return model_bytes, model_tex, tex_bytes, frames


class Walker:
    """The engine's ring scheduler over one frame, on a fresh zone."""

    def __init__(self, lib_path, memory, settings, frame, chunks, model_bytes, model_tex, tex_bytes,
                 ends=None, release=1, partial=1, world_index=24 * 1024, draw_distance=None):
        self.zone = Zone(lib_path, memory['zone_kib'] * 1024,
                         memory.get('ends_kib', 0) * 1024 if ends is None else ends)
        self.release, self.partial = release, partial
        self.chunks, self.model_bytes, self.model_tex, self.tex_bytes = chunks, model_bytes, model_tex, tex_bytes
        self.active_r = (draw_distance or settings['draw_distance']) + settings['hysteresis']
        self.load_r = self.active_r + settings['prefetch_margin']
        self.urgent_r = settings['collision_margin']
        n = len(chunks)
        self.state = [0] * n          # 0 absent, 1 loaded, 2 active
        self.part = [False] * n
        self.cat = [None] * n
        self.ter = [None] * n
        self.locked_models = [[] for _ in range(n)]
        self.failed_until = [0] * n
        self.released_until = [0] * n
        self.model = {}               # id -> pointer
        self.texture = {}             # id -> pointer
        self.model_tex_ptr = {}       # model pointer -> texture pointers locked for it
        self.by_ptr = {}
        self.tick = 0
        self.m = dict(zone_fail=0, data_fail=0, holes=0, hole_steps=0, released_band=0, released_ring=0,
                      partial=0, model_loads=0, chunk_loads=0, locked_peak=0, steps=0, failed_chunks=set(),
                      min_largest_unlocked=None, fail_need={}, hole_need={})
        z = self.zone
        z.on_evict('chunk', self._chunk_evicted)
        z.on_evict('terrain', self._terrain_evicted)
        z.on_evict('model', self._model_evicted)
        z.on_evict('texture', self._texture_evicted)
        # MapBegin's order: loading buffer, world index, frame index, frame-world pool.
        for kind, size in (('buffer', 32 * 1024), ('index', world_index),
                           ('index', n * 112 + n * 2 + 2 * ((frame['owned_total'] + 7) // 8)),
                           ('world', 2 * memory['pool_kib'] * 1024)):
            p = z.alloc(size, kind, 0)
            if not p:
                raise RuntimeError('zone too small for the map blocks')
            z.lock(p)

    # eviction callbacks (the engine's ChunkEvicted / ModelEvicted / TextureEvicted)
    def _chunk_evicted(self, data, ident):
        i = self.by_ptr.pop(data, None)
        if i is not None and i[0] == 'cat':
            assert self.state[i[1]] != 2
            self.state[i[1]] = 0
            self.cat[i[1]] = None

    def _terrain_evicted(self, data, ident):
        i = self.by_ptr.pop(data, None)
        if i is not None:
            self.ter[i[1]] = None

    def _model_evicted(self, data, ident):
        i = self.by_ptr.pop(data, None)
        if i is not None:
            self.model.pop(i[1], None)
        for t in self.model_tex_ptr.pop(data, []):
            self.zone.unlock(t)

    def _texture_evicted(self, data, ident):
        i = self.by_ptr.pop(data, None)
        if i is not None:
            self.texture.pop(i[1], None)

    def _dist2(self, i, x, y):
        bx, by, g = self.chunks[i]['box']
        dx = max(bx - x, x - (bx + g), 0)
        dy = max(by - y, y - (by + g), 0)
        return dx * dx + dy * dy

    def _alloc(self, size, kind, ident, key):
        before = self.zone.failures()
        p = self.zone.alloc(size, kind, ident)
        if p:
            self.by_ptr[p] = key
        return p, self.zone.failures() != before

    def _load_model(self, mid):
        if mid in self.model:
            return 1
        p, _ = self._alloc(self.model_bytes[mid], 'model', mid, ('model', mid))
        if not p:
            return -1
        self.zone.lock(p)               # locked while decoding
        locks = []
        for t in self.model_tex[mid]:
            tp = self.texture.get(t)
            if not tp:
                tp, _ = self._alloc(self.tex_bytes[t], 'texture', t, ('tex', t))
                if tp:
                    self.texture[t] = tp
            if tp:                      # else drawn untextured, as the engine does
                self.zone.touch(tp)
                self.zone.lock(tp)
                locks.append(tp)
        self.zone.unlock(p)
        self.model[mid] = p
        self.model_tex_ptr[p] = locks
        self.m['model_loads'] += 1
        return 1

    def _need(self, i, active2):
        if self.state[i] == 2:
            if not self.part[i]:
                return 0, None
            for mid in self.chunks[i]['models']:
                if mid not in self.model:
                    return 3, mid
            return 5, None
        if self.state[i] == 0 or not self.cat[i]:
            return 1, None
        if not self.ter[i]:
            return 2, None
        for mid in self.chunks[i]['models']:
            if mid not in self.model:
                return 3, mid
        return (4, None) if self.dist[i] <= active2 else (0, None)

    def _activate(self, i, partial=False):
        if not self.ter[i]:
            return False
        if not partial and any(mid not in self.model for mid in self.chunks[i]['models']):
            return False
        z = self.zone
        z.lock(self.cat[i])
        z.lock(self.ter[i])
        got = [self.model[mid] for mid in self.chunks[i]['models'] if mid in self.model]
        for p in got:
            z.lock(p)
        self.locked_models[i] = got
        self.part[i] = len(got) != len(self.chunks[i]['models'])
        if self.part[i]:
            self.m['partial'] += 1
        self.state[i] = 2
        return True

    def _complete(self, i):
        have = set(self.locked_models[i])
        for mid in self.chunks[i]['models']:
            p = self.model.get(mid)
            if p and p not in have:
                self.zone.lock(p)
                self.locked_models[i].append(p)
                have.add(p)
        self.part[i] = len(have) != len(self.chunks[i]['models'])

    def _deactivate(self, i):
        z = self.zone
        for p in self.locked_models[i]:
            z.unlock(p)
        self.locked_models[i] = []
        z.unlock(self.ter[i])
        z.unlock(self.cat[i])
        self.state[i] = 1
        self.part[i] = False

    def _release(self, i, active2, urgent2):
        d = self.dist[i]
        far = None
        for j, s in enumerate(self.state):
            if s == 2 and self.dist[j] > d and self.dist[j] > urgent2 and (far is None or self.dist[j] > self.dist[far]):
                far = j
        if far is None:
            return False
        self.m['released_band' if self.dist[far] > active2 else 'released_ring'] += 1
        self._deactivate(far)
        self.failed_until = [0] * len(self.chunks)
        self.released_until[far] = self.tick + 50
        return True

    def step(self, x, y):
        active2, load2, urgent2 = self.active_r ** 2, self.load_r ** 2, self.urgent_r ** 2
        self.dist = [self._dist2(i, x, y) for i in range(len(self.chunks))]
        gone = False
        for i, s in enumerate(self.state):
            if s == 2 and self.dist[i] > load2:
                self._deactivate(i)
                gone = True
        if gone:
            self.failed_until = [0] * len(self.chunks)
        cand = sorted((i for i in range(len(self.chunks)) if self.dist[i] <= load2 and
                       (self.state[i] != 2 or self.part[i])), key=lambda i: self.dist[i])
        for _guard in range(4 * 4096):        # chim_chunks.c: 4*CHIM_MAX_CHUNKS steps a tick
            best = None
            for i in cand:
                if self.tick < self.failed_until[i] or (self.state[i] != 2 and self.tick < self.released_until[i] and
                                                        self.dist[i] > urgent2):
                    continue
                need, mid = self._need(i, active2)
                if not need:
                    continue
                if self.dist[i] > active2 and need in (1, 2, 3):
                    want = (16384 if need == 1 else self.chunks[i]['terrain'] if need == 2 else self.model_bytes[mid])
                    if self.zone.stats().largest_free < 2 * want + 65536:
                        continue
                best = (i, need, mid)
                break
            if best is None:
                break
            i, need, mid = best
            result, zone_failed = 0, False
            # chim_release: a chunk the player can see keeps what it has while it loads (Pin).
            pins = []
            if self.release and self.dist[i] <= active2 and need in (2, 3):
                pins = [p for p in [self.cat[i], self.ter[i]] + [self.model.get(m) for m in self.chunks[i]['models']]
                        if p][:256]
                for p in pins:
                    self.zone.lock(p)
            if need == 1:
                p, zone_failed = self._alloc(self.chunks[i]['catalogue'], 'chunk', i, ('cat', i))
                if p:
                    self.cat[i] = p
                    self.state[i] = 1
                    self.m['chunk_loads'] += 1
                result = 1 if p else -1
            elif need == 2:
                p, zone_failed = self._alloc(self.chunks[i]['terrain'], 'terrain', i, ('ter', i))
                if p:
                    self.ter[i] = p
                result = 1 if p else -1
            elif need == 3:
                before = self.zone.failures()
                result = self._load_model(mid)
                zone_failed = self.zone.failures() != before
            elif need == 4:
                self._activate(i)
            elif need == 5:
                self._complete(i)
            for p in pins:
                self.zone.unlock(p)
            if result < 0:
                if zone_failed and self.release and self.dist[i] <= active2 and self._release(i, active2, urgent2):
                    continue
                self.failed_until[i] = self.tick + (1 if self.release and self.dist[i] <= urgent2 and self.state[i] != 2 else 50)
                if self.dist[i] <= active2:
                    self.m['zone_fail' if zone_failed else 'data_fail'] += 1
                    self.m['failed_chunks'].add(i)
                    self.m['fail_need'][need] = self.m['fail_need'].get(need, 0) + 1
                if need == 3 and self.partial and self.state[i] == 1 and self.dist[i] <= active2:
                    self._activate(i, partial=True)
        holes = 0
        for i, s in enumerate(self.state):
            if self.dist[i] <= urgent2 and s != 2:
                holes += 1
                k = '%d/%d%s' % (s, self._need(i, active2)[0], '/held' if self.tick < self.failed_until[i] else
                                 '/released' if self.tick < self.released_until[i] else '')
                self.m['hole_need'][k] = self.m['hole_need'].get(k, 0) + 1
        if holes:
            self.m['holes'] += holes
            self.m['hole_steps'] += 1
        s = self.zone.stats()
        self.m['locked_peak'] = max(self.m['locked_peak'], s.locked_bytes)
        lu = self.zone.lib.ChimZone_LargestUnlocked()
        if self.m['min_largest_unlocked'] is None or lu < self.m['min_largest_unlocked']:
            self.m['min_largest_unlocked'] = lu
        self.m['evictions'] = s.evictions
        self.m['steps'] += 1
        self.tick += 1

    def result(self):
        out = dict(self.m)
        out['failed_chunks'] = sorted(out['failed_chunks'])
        return out


def line(points, step):
    """Positions every step units along a polyline."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(points[-1])
    return out


def lawnmower(frame, spacing=256.0, step=16.0, margin=128.0):
    """A walk over the whole frame: rows `spacing` apart, back and forth."""
    lx, ly = frame['low']
    hx, hy = lx + frame['nx'] * frame['grain'], ly + frame['ny'] * frame['grain']
    pts, y, flip = [], ly + margin, False
    while y <= hy - margin:
        row = [(lx + margin, y), (hx - margin, y)]
        pts += row[::-1] if flip else row
        flip = not flip
        y += spacing
    return line(pts, step)


def walk(lib_path, memory, world, sizes_tuple, routes, ends=None, release=1, partial=1, draw_distance=None):
    """Run each route on a fresh zone; returns {route name: result}."""
    model_bytes, model_tex, tex_bytes, frames = sizes_tuple
    settings = world['settings']
    results = {}
    for name, frame_index, positions in routes:
        _path, frame, chunks = frames[frame_index]
        w = Walker(lib_path, memory, settings, frame, chunks, model_bytes, model_tex, tex_bytes,
                   ends=ends, release=release, partial=partial, draw_distance=draw_distance)
        for x, y in positions:
            w.step(x, y)
        results[name] = w.result()
    return results


def require_zone_walk(out, sdk=None, sizes=None, report_path=None, memory=None, spacing=256.0, step=24.0):
    """The build's CHIM zone walk gate: OUT/chim-zone-walk.json, and a ValueError when a walk over any
    frame leaves the player without ground (a chunk within the collision margin not active at the end
    of a step) or a chunk fails for bad data. Loads that found no room, chunks released for nearer
    ones and partial activations are reported (the engine's full-zone methods at their defaults); the
    budget itself is the heap gate's (chim.heap) and CHIM-ZONE-BUDGET-33's. Without sizes or an SDK the
    gate is recorded as not run."""
    import json
    from build_scratch import scratch_dir
    from chim.validate import Failures, load_world
    from chim import heap as H
    report_path = Path(report_path or Path(out) / 'chim-zone-walk.json')
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]
        fails = Failures()
        settings, files, disk, textures, models, frames = load_world(out, fails)
        if fails:
            raise ValueError('CHIM zone walk gate: the world does not read back (%s)' % fails[0])
        world = {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}
        memory = memory or H.engine_memory()
        blocks = block_sizes(world, sizes)
        # The host library is built and loaded from the build's own scratch folder (build_scratch: the
        # run's scratch, else OUT/work): /tmp is often mounted noexec (Docker --tmpfs, hardened hosts),
        # where loading a shared object fails (CHIM-ZONE-TMP-NOEXEC-33, BUILD-TMP-SCRATCH-33).
        work = Path(out) / 'work'
        work.mkdir(parents=True, exist_ok=True)
        with scratch_dir('amiwind-zone-', near=work) as tmp:
            lib = build_library(tmp)
            routes = [('%s lawnmower' % path, k, lawnmower(frame, spacing, step))
                      for k, (path, frame, chunks) in enumerate(frames)]
            results = walk(lib, memory, world, blocks, routes, release=1, partial=1)
        walks = []
        for name, r in results.items():
            r = dict(r, hole_need={str(k): v for k, v in r['hole_need'].items()},
                     fail_need={str(k): v for k, v in r['fail_need'].items()})
            r['name'] = name
            r['ok'] = r['holes'] == 0 and r['data_fail'] == 0
            walks.append(r)
        report = {'zone_kib': memory['zone_kib'], 'pool_kib': memory['pool_kib'], 'spacing': spacing, 'step': step,
                  'ends_kib': memory.get('ends_kib', 0),
                  'method': 'engine zone allocator (chim_zone.c, host build) driven by the ring rules of chim_chunks.c '
                            'with chim_release 1, chim_partial 1 and chim_zone_ends at its default; block sizes of the '
                            'target ABI',
                  'walks': walks, 'ok': all(w['ok'] for w in walks)}
        report['status'] = 'passed' if report['ok'] else 'failed'
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    bad = [w for w in report.get('walks', []) if not w['ok']]
    if bad:
        w = bad[0]
        raise ValueError('CHIM zone walk gate failed: %s left the player without ground in %d of %d steps '
                         '(%d failed for bad data); see %s' % (w['name'], w['hole_steps'], w['steps'], w['data_fail'],
                                                               report_path))
    return report
