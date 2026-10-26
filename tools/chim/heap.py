# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM heap gate: the active ring of every player position fits the engine's CHIM zone.

A CHIM map takes one zone bank from the Hunk at map start (engine chim_world.c:
chim_zone_kib) and reserves the frame-world pool in it (one block of twice
chim_pool_kib). Both defaults are read from the engine source
(tools/engine_limits.chim_memory), the one source for the builder and the engine. The rest of the bank holds what the
active ring needs at once. The engine's rule is in chim_chunks.c: a chunk is
active when the player's position lies within the active radius of its box
(ChimChunks_ActiveRadius: the view distance plus the world's hysteresis;
Distance is the distance to the box). The ring then needs:

- the active chunks' terrain blocks;
- the models their owned and reach records place;
- those models' textures;
- each active chunk's catalogue (one entry per placement).

Every terrain or model block is one zone allocation: the model header plus
the decoded arena. AW_BrushBound (model.c) gives the arena size from the
image's lump sizes: each lump rounded to 16 bytes, placed models keep their
node tree as the point hull (dclipnode only per node; terrain also keeps mnode), and the standing
hull's clipnodes stay as stored. The target ABI sizes are the strict
world-map heap gate's own, probed with the Amiga compiler from the engine
headers (check_world_map_heap.compile_target_sizes). A texture is one block:
texture_t and its four mip levels.

The gate is strict: there is no exception list. It samples player positions
on a 64-unit grid over every frame and fails when the largest ring does not
fit the bank minus the slots. Per frame it reports the peak, where it happens
and the headroom.
"""

POOL_SLOTS = 2         # the frame-world pool: one block of twice chim_pool_kib (engine_limits.chim_memory)


def engine_memory(heap_mb=None):
    """The engine's CHIM memory defaults, read from its source (tools/engine_limits.chim_memory: the
    chim_zone_kib and chim_pool_kib cvar defaults): the one source, never a copy of the numbers.
    heap_mb: the build's own heap (engine-build.json heap_mb, from --heap-mb); default the source's."""
    from engine_limits import chim_memory
    return chim_memory(heap_mb=heap_mb)
SAMPLE = 64.0          # player positions sampled every 64 units


def efrag_report(links, budget_links):
    """CHIM-EFRAG-UNCAPPED-35: the active ring's placements, one efrag each at least, against the CHIM
    efrag budget (engine_limits.chim_efrag_budget, the engine's own defines). Past it the engine makes
    the farthest placements wait unlinked; a ring whose placements alone pass it fails the gate."""
    return {'ring_placements_peak': int(links), 'budget_links': budget_links,
            'ok': budget_links is None or links <= budget_links,
            'method': 'placements owned by the active chunks (one efrag each at least; the engine counts '
                      'the leaves of each when the limit is near)'}


def _a16(n):
    return (int(n) + 15) & ~15


def image_bytes(lumps, sizes, point_hull_only=False):
    """One zone block for a brush image (a chunk's terrain or a placed model): the allocation header,
    the model header and the arena AW_BrushBound gives for it (texture references, not miptex).
    Placed models use the unconditional direct hull-0 path; terrain retains renderer nodes."""
    def count(k, probe):
        return len(lumps[k]) // sizes[probe]
    nodes = count(5, 'dnode')
    arena = sum(_a16(x) for x in (
        count(3, 'dvertex') * sizes['mvertex'],
        (count(12, 'dedge') + 1) * sizes['medge'],
        count(13, 'int') * sizes['int'],
        (len(lumps[2]) // 4) * sizes['pointer'] if len(lumps[2]) else 0,
        len(lumps[8]), len(lumps[4]), len(lumps[0]), len(lumps[9]),
        count(1, 'dplane') * sizes['mplane'],
        count(6, 'texinfo') * sizes['mtexinfo'],
        count(7, 'dface') * sizes['msurface'],
        count(11, 'short') * sizes['pointer'],
        count(10, 'dleaf') * sizes['mleaf'],
        count(14, 'dmodel') * sizes['dmodel'],
        nodes * sizes['dclipnode'], 0 if point_hull_only else nodes * sizes['mnode']))
    return sizes['hunk'] + _a16(sizes['model'] + arena)


def collision_bytes(lumps, sizes):
    """The part of image_bytes a brush image's collision takes: its clipnodes (the standing hull) and the hull-0
    clipnodes the loader builds from its nodes (Mod_MakeHull0). The rest of the block is what is drawn."""
    return _a16(len(lumps[9])) + (len(lumps[5]) // sizes['dnode']) * sizes['dclipnode']


def texture_bytes(width, height, sizes):
    return sizes['hunk'] + _a16(sizes['texture'] + width * height // 64 * 85)


def ring_peak_whole(world, sizes, zone_kib=None, pool_kib=None, sample=SAMPLE, points=(), zone_bytes=None,
                    chunk_extra=None, chunk_models=None):
    """The whole-world form of ring_peak (the reference; CHIM-WORLD-AUDIT-SCALING-33): every frame indexes
    the whole world's models and textures, so its cost grows with the world, not with the frame.
    Per frame: the largest active ring (bytes) over player positions on a grid, against the zone
    bank minus the frame-world slots. world: chim.validate's world (settings, models, textures, frames).
    points: [(name, x, y)] frame-local positions also reported (the benchmark cameras), in the frame
    that holds them. zone_bytes: {frame cell: zone bytes} where the whole-map rule makes the zone
    smaller than zone_kib (engine_limits.whole_map_zone); chunk_extra: {frame cell: {chunk index:
    bytes}} more blocks a chunk brings into the zone when it loads (its own copies of its streamed
    statics' models); chunk_models: {frame cell: {chunk index: {model: bytes}}} blocks the ring shares
    (one copy while any chunk in the ring uses it)."""
    import numpy as np
    from chim import format as F
    memory = engine_memory() if zone_kib is None or pool_kib is None else {}
    zone_kib = memory['zone_kib'] if zone_kib is None else zone_kib
    pool_kib = memory['pool_kib'] if pool_kib is None else pool_kib
    s = world['settings']
    radius = float(s['draw_distance'] + s['hysteresis'])
    # A chunk stays locked until the player is past the load radius (CHIM-CHUNK-LOAD-FAIL-33): a moving
    # player can hold everything within it locked. Reported always; gated when the engine states that
    # policy (engine_limits.chim_memory 'locked_ring' == 'load').
    load_radius = radius + float(s.get('prefetch_margin', 0))
    gate_ring = memory.get('locked_ring', 'active')
    from engine_limits import chim_efrag_budget
    efrag_budget = chim_efrag_budget()
    models = world['models']
    model_size = np.zeros(len(models))
    model_coll = np.zeros(len(models))
    model_tex = []
    for i, m in enumerate(models):
        lumps = F.read_brush_image(m['image'])
        model_size[i] = image_bytes(lumps, sizes, point_hull_only=True)
        model_coll[i] = collision_bytes(lumps, sizes)
        model_tex.append(F.read_texture_refs(lumps[2]))
    tex_size = np.array([texture_bytes(t['width'], t['height'], sizes) for t in world['textures']], float)
    entry = sizes.get('scenery', sizes['entity'])
    frames = []
    for path, frame, chunks in world['frames']:
        cell = tuple(frame['cell'])
        zone = min(zone_kib * 1024, (zone_bytes or {}).get(cell, zone_kib * 1024))
        budget = zone - POOL_SLOTS * pool_kib * 1024
        extra = (chunk_extra or {}).get(cell, {})
        shared = (chunk_models or {}).get(cell, {})
        snames = sorted({m for v in shared.values() for m in v})
        sindex = {m: i for i, m in enumerate(snames)}
        ssize = np.zeros(len(snames))
        g, (lx, ly) = frame['grain'], frame['low']
        n = len(chunks)
        own = np.zeros(n)
        placed = np.zeros(n)
        uses_model = np.zeros((n, len(models)), np.int32)
        uses_tex = np.zeros((n, len(tex_size)), np.int32)
        uses_s = np.zeros((n, len(snames)), np.float32)
        lo = np.zeros((n, 2))
        parts = np.zeros((n, 4))    # terrain drawn, terrain collision, placement records, streamed extra
        for k, c in enumerate(chunks):
            lumps = F.read_brush_image(c['image'])
            records = c['owned'] + c['reach']
            terrain, coll = image_bytes(lumps, sizes), collision_bytes(lumps, sizes)
            parts[k] = (terrain - coll, coll, sizes['hunk'] + _a16(len(records) * (entry + sizes['pointer'])),
                        extra.get(c['index'], 0))
            own[k] = parts[k].sum()
            placed[k] = len(c['owned'])
            for t in F.read_texture_refs(lumps[2]):
                uses_tex[k, t] = 1
            for r in records:
                uses_model[k, r['model']] = 1
            for m, b in shared.get(c['index'], {}).items():
                uses_s[k, sindex[m]] = 1
                ssize[sindex[m]] = b
            lo[k] = (lx + c['cx'] * g, ly + c['cy'] * g)
        hi = lo + g
        model_uses_tex = np.zeros((len(models), len(tex_size)), np.int32)
        for i, ts in enumerate(model_tex):
            model_uses_tex[i, ts] = 1
        xs = np.arange(lx + sample / 2, lx + frame['nx'] * g, sample)
        ys = np.arange(ly + sample / 2, ly + frame['ny'] * g, sample)
        P = np.array([(x, y) for y in ys for x in xs])

        def rings(p, r=radius):
            dx = np.maximum(np.maximum(lo[None, :, 0] - p[:, None, 0], p[:, None, 0] - hi[None, :, 0]), 0)
            dy = np.maximum(np.maximum(lo[None, :, 1] - p[:, None, 1], p[:, None, 1] - hi[None, :, 1]), 0)
            active = (dx * dx + dy * dy <= r * r).astype(np.int32)     # (positions, chunks)
            need_m = (active @ uses_model) > 0
            need_t = ((active @ uses_tex) > 0) | ((need_m.astype(np.int32) @ model_uses_tex) > 0)
            total = active @ own + need_m @ model_size + need_t @ tex_size + ((active @ uses_s) > 0) @ ssize
            return total, active, need_m, need_t
        best, totals, load_best, load_totals, largest = None, [], None, [], 0.0
        links = 0
        for start in range(0, len(P), 512):
            p = P[start:start + 512]
            total, active, need_m, need_t = rings(p)
            if n:
                links = max(links, int((active @ placed).max()))
            totals.append(total)
            k = int(np.argmax(total))
            if best is None or total[k] > best[0]:
                best = (float(total[k]), p[k], int(active[k].sum()), int(need_m[k].sum()), int(need_t[k].sum()),
                        [int(i) for i in np.nonzero(need_m[k])[0]])
            ltotal, lactive, lneed_m, _ = rings(p, load_radius)
            load_totals.append(ltotal)
            k = int(np.argmax(ltotal))
            if load_best is None or ltotal[k] > load_best[0]:
                load_best = (float(ltotal[k]), p[k])
            # the largest single block any ring needs (a model or a chunk's terrain): it needs one free run
            if lneed_m.any():
                largest = max(largest, float((lneed_m * model_size[None, :]).max()))
        largest = max(largest, float(own.max()) if len(own) else 0.0)
        total, where, nchunks, nmodels, ntex, peak_models = best
        _, act, nm, nt = rings(np.array([where]))
        breakdown = {'terrain_drawn': int(act[0] @ parts[:, 0]), 'terrain_collision': int(act[0] @ parts[:, 1]),
                     'placement_records': int(act[0] @ parts[:, 2]), 'streamed': int(act[0] @ parts[:, 3]),
                     'models_drawn': int(nm[0] @ (model_size - model_coll)), 'models_collision': int(nm[0] @ model_coll),
                     'textures': int(nt[0] @ tex_size), 'shared': int(((act @ uses_s) > 0)[0] @ ssize)}
        totals = np.concatenate(totals)
        load_totals = np.concatenate(load_totals)
        inside = [(nm, x, y) for nm, x, y in points
                  if lx <= x < lx + frame['nx'] * g and ly <= y < ly + frame['ny'] * g]
        at = []
        if inside:
            t = rings(np.array([(x, y) for _, x, y in inside], float))[0]
            at = [{'name': nm, 'position': [x, y], 'bytes': int(v), 'ok': v <= budget}
                  for (nm, x, y), v in zip(inside, t)]
        load = {'radius': load_radius, 'peak_bytes': int(load_best[0]),
                'peak_position': [round(float(v), 1) for v in load_best[1]],
                'positions_over_budget': int((load_totals > budget).sum()), 'headroom_bytes': budget - int(load_best[0])}
        gated = total if gate_ring == 'active' else load_best[0]
        efrags = efrag_report(links, efrag_budget)
        frames.append({'frame': path, 'points': at, 'efrags': efrags, 'median_bytes': int(np.median(totals)),
                       'positions_over_budget': int((totals > budget).sum()), 'peak_bytes': int(total),
                       'peak_position': [round(float(v), 1) for v in where],
                       'ring_chunks': nchunks, 'ring_models': nmodels, 'ring_textures': ntex,
                       'peak_models': peak_models, 'peak_breakdown': breakdown,
                       'budget_bytes': budget, 'headroom_bytes': budget - int(total),
                       'load_ring': load, 'largest_block_bytes': int(largest),
                       'gated_ring': gate_ring, 'ok': gated <= budget and efrags['ok'], 'positions': int(len(P)),
                       'zone_bytes': int(zone), 'streamed_bytes': int(sum(extra.values()) + ssize.sum())})
    return {'zone_kib': zone_kib, 'pool_kib': pool_kib, 'pool_slots': POOL_SLOTS, 'sample_units': sample,
            'active_radius': radius, 'load_radius': load_radius, 'gated_ring': gate_ring,
            'method': 'engine active ring (chunk boxes within view distance + hysteresis of the player) at '
                      'positions every %g units; blocks sized as AW_BrushBound with the target ABI' % sample,
            'frames': frames, 'ok': all(f['ok'] for f in frames)}


# ---------------------------------------------------------------- per-frame audit (CHIM-WORLD-AUDIT-SCALING-33)
#
# The engine holds one ring, and a ring never leaves its frame (chim_chunks.c: the active and load rings are
# chunk boxes of the current frame). So a frame's audit needs only that frame's chunks and the models and
# textures they use. ring_peak indexes each frame by what it uses (its own model and texture numbering),
# audits the frames in parallel (jobs) and keeps each frame's result in a cache by its content key (cache_dir),
# with the same result as ring_peak_whole (tests/test_chim_heap.py proves it on small worlds). The whole-world
# form cost ~ frames x world models x world textures: 3.6 s at 171 frames, 473 s at 331, over 2 h at 844.

HEAP_AUDIT_VERSION = 3      # bump when the per-frame audit's arithmetic changes (cache keys); 3: peak_breakdown
# 2: the ring's placements against the CHIM efrag budget (CHIM-EFRAG-UNCAPPED-35)


def ring_peak(world, sizes, zone_kib=None, pool_kib=None, sample=SAMPLE, points=(), zone_bytes=None,
              chunk_extra=None, chunk_models=None, jobs=1, cache_dir=None):
    """Per frame: the largest active ring (bytes) over player positions on a grid, against the zone bank
    minus the frame-world slots; the same report as ring_peak_whole (its docstring has the arguments),
    computed frame by frame on what each frame uses. jobs: frames audited in parallel (processes);
    cache_dir: a folder keeping each frame's result by its content key (the frame's chunks, the sizes of
    the models and textures it uses, the target sizes and the gate's settings)."""
    import json
    from pathlib import Path
    from chim import format as F
    memory = engine_memory() if zone_kib is None or pool_kib is None else {}
    zone_kib = memory['zone_kib'] if zone_kib is None else zone_kib
    pool_kib = memory['pool_kib'] if pool_kib is None else pool_kib
    s = world['settings']
    radius = float(s['draw_distance'] + s['hysteresis'])
    load_radius = radius + float(s.get('prefetch_margin', 0))
    gate_ring = memory.get('locked_ring', 'active')
    from engine_limits import chim_efrag_budget
    efrag_budget = chim_efrag_budget()
    models, textures = world['models'], world['textures']
    model_size, model_tex, model_coll = {}, {}, {}

    def model(i):
        if i not in model_size:
            lumps = F.read_brush_image(models[i]['image'])
            model_size[i] = image_bytes(lumps, sizes, point_hull_only=True)
            model_coll[i] = collision_bytes(lumps, sizes)
            model_tex[i] = sorted(set(F.read_texture_refs(lumps[2])))
        return model_size[i], model_tex[i]
    tasks = []
    for path, frame, chunks in world['frames']:
        cell = tuple(frame['cell'])
        used_m = sorted({r['model'] for c in chunks for r in c['owned'] + c['reach']})
        msizes = [model(i)[0] for i in used_m]
        mtex = [model(i)[1] for i in used_m]
        g, (lx, ly) = frame['grain'], frame['low']
        task = {'path': path, 'frame': frame, 'chunks': chunks, 'used_models': used_m, 'model_sizes': msizes,
                'model_tex': mtex, 'model_collision': [model_coll[i] for i in used_m],
                'sizes': sizes, 'zone': min(zone_kib * 1024, (zone_bytes or {}).get(cell, zone_kib * 1024)),
                'pool_bytes': POOL_SLOTS * pool_kib * 1024, 'extra': (chunk_extra or {}).get(cell, {}),
                'shared': (chunk_models or {}).get(cell, {}), 'radius': radius, 'load_radius': load_radius,
                'gate_ring': gate_ring, 'sample': sample, 'efrag_budget': efrag_budget,
                'points': [(nm, x, y) for nm, x, y in points
                           if lx <= x < lx + frame['nx'] * g and ly <= y < ly + frame['ny'] * g]}
        task['textures'] = {t: (textures[t]['width'], textures[t]['height']) for t in _frame_textures(task)}
        tasks.append(task)
    cache = Path(cache_dir) if cache_dir else None
    keys = [_frame_key(t) if cache else None for t in tasks]
    results = [None] * len(tasks)
    if cache:
        try:
            cache.mkdir(parents=True, exist_ok=True)
        except OSError as exc:      # a cache problem never fails the gate (BUILD-CACHE-OWNER-FAILS-STAGE-34)
            print('[warning] heap gate cache not writable (%s); frames are computed, not stored' % exc, flush=True)
        for i, k in enumerate(keys):
            f = cache / (k + '.json')
            if f.is_file():
                results[i] = json.loads(f.read_text(encoding='utf-8'))
    todo = [i for i, r in enumerate(results) if r is None]
    # A big frame (all of Vivec: 28,224 positions over 1,764 chunks, 5 minutes on one core) splits its positions over
    # the whole pool (_frame_ring jobs, in this process); the other frames share the pool one frame per worker,
    # largest first. Same report either way (tests/test_chim_heap.py: positions split or whole, byte for byte).
    jobs = jobs or 1
    big = [i for i in todo if jobs > 1 and _frame_positions(tasks[i]) >= BIG_FRAME_POSITIONS]
    small = [i for i in todo if i not in big]
    import build_parallel
    if jobs > 1 and build_parallel.active_stage_pool() is not None and len(big) + len(small) > 1:
        # ONE map over the slices of every big frame and every small frame, largest first, on the stage's pool
        # (BUILD-CHIM-STAGE-SERIAL-TAIL-36): no big frame waits for the one before, no small frame for the big ones;
        # one progress line per frame
        import progress_line
        steps = {i: _frame_ring_steps(tasks[i], jobs) for i in big}
        units = [('slice', i, k, w) for i in big for k, w in enumerate(next(steps[i]))]
        units += [('frame', i, 0, tasks[i]) for i in small]
        slices_of = {i: sum(1 for u in units if u[0] == 'slice' and u[1] == i) for i in big}
        got = {i: {} for i in big}

        def cost(u):
            if u[0] == 'slice':
                return (u[3][2] - u[3][1]) * max(1, len(u[3][0]['own']))
            return _frame_positions(u[3]) * max(1, len(u[3]['chunks']))
        done = 0
        units.sort(key=lambda u: -cost(u))           # largest first (stable: ties in frame order)
        for (kind, i, k), r in build_parallel.completed_map(_heap_unit, units, min(jobs, len(units))):
            if kind == 'slice':
                got[i][k] = r
                if len(got[i]) < slices_of[i]:
                    continue
                try:
                    steps[i].send([got[i][n] for n in range(slices_of[i])])
                except StopIteration as finished:
                    results[i] = finished.value
            else:
                results[i] = r
            done += 1
            progress_line.emit('CHIM heap gate', tasks[i]['path'], 'active ring peak %d of %d bytes'
                               % (results[i]['peak_bytes'], results[i]['budget_bytes']),
                               (done, len(todo), 'frames'))
    else:
        for i in big:
            results[i] = _frame_ring(tasks[i], jobs=jobs)
        if jobs > 1 and len(small) > 1:
            # the shared worker pool: largest frames first, and the pool follows the stage's live allowance
            # (a fixed pool of the stage's start share left cores idle; BUILD-CHIM-STAGE-SERIAL-TAIL-36)
            from build_parallel import ordered_map
            for i, r in zip(small, ordered_map(_frame_ring, [tasks[i] for i in small], min(jobs, len(small)),
                                               cost=lambda t: len(t['chunks']) * (1 + len(t['used_models'])))):
                results[i] = r
        else:
            for i in small:
                results[i] = _frame_ring(tasks[i], jobs=jobs)
    if cache:
        for i in todo:
            try:
                (cache / (keys[i] + '.json')).write_text(json.dumps(results[i], sort_keys=True), encoding='utf-8',
                                                        newline='\n')
            except OSError as exc:  # a cache problem never fails the gate (BUILD-CACHE-OWNER-FAILS-STAGE-34)
                print('[warning] heap gate cache write refused (%s); the frame was computed, the gate goes on' % exc,
                      flush=True)
    frames = [dict(r, frame=t['path']) for r, t in zip(results, tasks)]
    return {'zone_kib': zone_kib, 'pool_kib': pool_kib, 'pool_slots': POOL_SLOTS, 'sample_units': sample,
            'active_radius': radius, 'load_radius': load_radius, 'gated_ring': gate_ring,
            'method': 'engine active ring (chunk boxes within view distance + hysteresis of the player) at '
                      'positions every %g units; blocks sized as AW_BrushBound with the target ABI' % sample,
            'frames': frames, 'ok': all(f['ok'] for f in frames)}


def _frame_textures(task):
    """The textures a frame's ring can need: its chunks' own and its models'."""
    from chim import format as F
    out = set()
    for c in task['chunks']:
        out.update(F.read_texture_refs(F.read_brush_image(c['image'])[2]))
    for ts in task['model_tex']:
        out.update(ts)
    return sorted(out)


def _frame_key(task):
    """A frame's content key: everything its audit reads (cache by content, CHIM-WORLD-AUDIT-SCALING-33)."""
    import hashlib
    import json
    h = hashlib.sha256()
    tlocal = {t: i for i, t in enumerate(sorted(task['textures']))}
    meta = {'v': HEAP_AUDIT_VERSION, 'frame': {k: v for k, v in task['frame'].items()},
            'sizes': task['sizes'], 'zone': task['zone'], 'pool': task['pool_bytes'],
            'extra': sorted((str(k), v) for k, v in task['extra'].items()),
            'shared': sorted((str(k), sorted(v.items())) for k, v in task['shared'].items()),
            'radius': task['radius'], 'load': task['load_radius'], 'gate': task['gate_ring'],
            'sample': task['sample'], 'points': task['points'], 'model_sizes': task['model_sizes'],
            'efrag_budget': task.get('efrag_budget'),
            # textures by the frame's own numbering (which models share one) with their sizes; the chunk
            # images below carry the world's texture numbers
            'model_tex': [[tlocal[t] for t in ts] for ts in task['model_tex']],
            'textures': [task['textures'][t] for t in sorted(task['textures'])]}
    h.update(json.dumps(meta, sort_keys=True, default=str).encode())
    local = {m: i for i, m in enumerate(task['used_models'])}
    for c in task['chunks']:
        h.update(json.dumps([c['index'], c['cx'], c['cy'],
                             [local[r['model']] for r in c['owned'] + c['reach']]], default=str).encode())
        h.update(hashlib.sha256(c['image']).digest())
    return h.hexdigest()


BIG_FRAME_POSITIONS = 4 * 1024     # a frame with this many sample positions or more scans them over the whole pool
SCAN_BATCH = 256               # positions per ring evaluation (one matrix product)


def _frame_positions(task):
    frame, sample = task['frame'], task['sample']
    g = frame['grain']
    return len(range(0, int(frame['nx'] * g / sample + 0.999))) * len(range(0, int(frame['ny'] * g / sample + 0.999)))


def _rings(arrays, p, r):
    """The ring bytes of positions p (rows) at radius r: (total, active, need_m, need_t)."""
    import numpy as np
    a = arrays
    lo, hi = a['lo'], a['hi']
    dx = np.maximum(np.maximum(lo[None, :, 0] - p[:, None, 0], p[:, None, 0] - hi[None, :, 0]), 0)
    dy = np.maximum(np.maximum(lo[None, :, 1] - p[:, None, 1], p[:, None, 1] - hi[None, :, 1]), 0)
    # 0/1 incidence as float32: the products are small whole counts (exact in float32) and run through BLAS;
    # int32 products take numpy's plain loop, ~10x slower (CHIM-HEAP-INT-MATMUL-36). Same report.
    active = (dx * dx + dy * dy <= r * r).astype(np.float32)
    need_m = (active @ a['uses_model']) > 0
    need_t = ((active @ a['uses_tex']) > 0) | ((need_m.astype(np.float32) @ a['model_uses_tex']) > 0)
    total = (active.astype(np.float64) @ a['own'] + need_m @ a['model_size'] + need_t @ a['tex_size']
             + ((active @ a['uses_s']) > 0) @ a['ssize'])
    return total, active, need_m, need_t


def _scan(work):
    """Worker (or in-process): the ring scan of positions P[start:end] in SCAN_BATCH rows: (totals, load totals,
    best, load best, efrag links, largest block). Slices merged in order give the whole scan's result."""
    import numpy as np
    arrays, start, end = work
    a = arrays
    P, used, n = a['P'], a['used'], len(a['own'])
    best, totals, load_best, load_totals, largest, links = None, [], None, [], 0.0, 0
    for at in range(start, end, SCAN_BATCH):
        p = P[at:min(at + SCAN_BATCH, end)]
        total, active, need_m, need_t = _rings(a, p, a['radius'])
        if n:
            links = max(links, int((active @ a['placed']).max()))
        totals.append(total)
        k = int(np.argmax(total))
        if best is None or total[k] > best[0]:
            best = (float(total[k]), p[k], int(active[k].sum()), int(need_m[k].sum()), int(need_t[k].sum()),
                    [int(used[i]) for i in np.nonzero(need_m[k])[0]])
        ltotal, lactive, lneed_m, _ = _rings(a, p, a['load_radius'])
        load_totals.append(ltotal)
        k = int(np.argmax(ltotal))
        if load_best is None or ltotal[k] > load_best[0]:
            load_best = (float(ltotal[k]), p[k])
        if lneed_m.any():
            largest = max(largest, float((lneed_m * a['model_size'][None, :]).max()))
    return (np.concatenate(totals) if totals else np.zeros(0), np.concatenate(load_totals) if load_totals
            else np.zeros(0), best, load_best, links, largest)


def _heap_unit(unit):
    """Worker of ring_peak's one map: a slice of a big frame's position scan, or a whole small frame."""
    kind, i, k, work = unit
    return (kind, i, k), (_scan(work) if kind == 'slice' else _frame_ring(work))


def _frame_ring(task, jobs=1):
    """One frame's ring report (ring_peak), on the frame's own model and texture numbering. jobs > 1: the
    positions are scanned in slices over the shared worker pool (same report)."""
    steps = _frame_ring_steps(task, jobs)
    work = next(steps)
    if len(work) > 1:
        from build_parallel import ordered_map
        parts_out = list(ordered_map(_scan, work, min(jobs, len(work))))
    else:
        parts_out = [_scan(w) for w in work]
    try:
        steps.send(parts_out)
    except StopIteration as done:
        return done.value
    raise RuntimeError('heap frame steps did not finish')


def _frame_ring_steps(task, jobs=1):
    """_frame_ring in two steps (a generator): it yields the frame's scan work (slices of positions, _scan's
    input), takes back their results in the same order and returns the report. ring_peak scans the slices
    of every big frame and the small frames in ONE map, largest first, so no frame waits for another frame's
    slices (BUILD-CHIM-STAGE-SERIAL-TAIL-36)."""
    import numpy as np
    from chim import format as F
    sizes = task['sizes']
    frame, chunks = task['frame'], task['chunks']
    used = task['used_models']
    mlocal = {m: i for i, m in enumerate(used)}
    tex_ids = sorted(task['textures'])
    tlocal = {t: i for i, t in enumerate(tex_ids)}
    model_size = np.array(task['model_sizes'], float)
    tex_size = np.array([texture_bytes(*task['textures'][t], sizes) for t in tex_ids], float)
    entry = sizes.get('scenery', sizes['entity'])
    budget = task['zone'] - task['pool_bytes']
    extra, shared = task['extra'], task['shared']
    radius, load_radius, gate_ring, sample = task['radius'], task['load_radius'], task['gate_ring'], task['sample']
    snames = sorted({m for v in shared.values() for m in v})
    sindex = {m: i for i, m in enumerate(snames)}
    ssize = np.zeros(len(snames))
    g, (lx, ly) = frame['grain'], frame['low']
    n = len(chunks)
    own = np.zeros(n)
    placed = np.zeros(n)        # placements a chunk owns: each links at least one efrag when active
    uses_model = np.zeros((n, len(used)), np.float32)
    uses_tex = np.zeros((n, len(tex_ids)), np.float32)
    uses_s = np.zeros((n, len(snames)), np.float32)
    lo = np.zeros((n, 2))
    parts = np.zeros((n, 4))    # terrain drawn, terrain collision, placement records, streamed extra
    for k, c in enumerate(chunks):
        lumps = F.read_brush_image(c['image'])
        records = c['owned'] + c['reach']
        terrain, coll = image_bytes(lumps, sizes), collision_bytes(lumps, sizes)
        parts[k] = (terrain - coll, coll, sizes['hunk'] + _a16(len(records) * (entry + sizes['pointer'])),
                    extra.get(c['index'], 0))
        own[k] = parts[k].sum()
        placed[k] = len(c['owned'])
        for t in F.read_texture_refs(lumps[2]):
            uses_tex[k, tlocal[t]] = 1
        for r in records:
            uses_model[k, mlocal[r['model']]] = 1
        for m, b in shared.get(c['index'], {}).items():
            uses_s[k, sindex[m]] = 1
            ssize[sindex[m]] = b
        lo[k] = (lx + c['cx'] * g, ly + c['cy'] * g)
    hi = lo + g
    model_uses_tex = np.zeros((len(used), len(tex_ids)), np.float32)
    for i, ts in enumerate(task['model_tex']):
        model_uses_tex[i, [tlocal[t] for t in ts]] = 1
    xs = np.arange(lx + sample / 2, lx + frame['nx'] * g, sample)
    ys = np.arange(ly + sample / 2, ly + frame['ny'] * g, sample)
    P = np.array([(x, y) for y in ys for x in xs])
    arrays = {'lo': lo, 'hi': hi, 'own': own, 'placed': placed, 'uses_model': uses_model, 'uses_tex': uses_tex,
              'uses_s': uses_s, 'model_uses_tex': model_uses_tex, 'model_size': model_size, 'tex_size': tex_size,
              'ssize': ssize, 'P': P, 'used': list(used), 'radius': radius, 'load_radius': load_radius}

    def rings(p, r=radius):
        return _rings(arrays, p, r)
    # the position scan: whole, or in slices of whole batches over the pool, merged in order
    slices = 1 if jobs <= 1 or len(P) < BIG_FRAME_POSITIONS else min(jobs * 4, -(-len(P) // SCAN_BATCH))
    step = -(-(-(-len(P) // SCAN_BATCH)) // slices) * SCAN_BATCH
    work = [(arrays, start, min(start + step, len(P))) for start in range(0, len(P), step)] if len(P) else \
        [(arrays, 0, 0)]
    parts_out = yield work
    best, load_best, largest, links = None, None, 0.0, 0
    for _, _, b, lb, li, la in parts_out:
        if b is not None and (best is None or b[0] > best[0]):
            best = b
        if lb is not None and (load_best is None or lb[0] > load_best[0]):
            load_best = lb
        links, largest = max(links, li), max(largest, la)
    totals = [t for t, _, _, _, _, _ in parts_out]
    load_totals = [t for _, t, _, _, _, _ in parts_out]
    largest = max(largest, float(own.max()) if len(own) else 0.0)
    total, where, nchunks, nmodels, ntex, peak_models = best
    # What fills the worst position, by kind (the maintainer's question "is any terrain resident twice?": each chunk's
    # terrain is one zone block here; its copy in the frame world lives in the frame-world slots, outside this
    # budget)
    _, act, nm, nt = rings(np.array([where]))
    mcoll = np.array(task.get('model_collision', [0] * len(used)), float)
    breakdown = {'terrain_drawn': int(act[0] @ parts[:, 0]), 'terrain_collision': int(act[0] @ parts[:, 1]),
                 'placement_records': int(act[0] @ parts[:, 2]), 'streamed': int(act[0] @ parts[:, 3]),
                 'models_drawn': int(nm[0] @ (model_size - mcoll)), 'models_collision': int(nm[0] @ mcoll),
                 'textures': int(nt[0] @ tex_size), 'shared': int(((act @ uses_s) > 0)[0] @ ssize)}
    totals = np.concatenate(totals)
    load_totals = np.concatenate(load_totals)
    at = []
    if task['points']:
        t = rings(np.array([(x, y) for _, x, y in task['points']], float))[0]
        at = [{'name': nm, 'position': [x, y], 'bytes': int(v), 'ok': bool(v <= budget)}
              for (nm, x, y), v in zip(task['points'], t)]
    load = {'radius': load_radius, 'peak_bytes': int(load_best[0]),
            'peak_position': [round(float(v), 1) for v in load_best[1]],
            'positions_over_budget': int((load_totals > budget).sum()), 'headroom_bytes': budget - int(load_best[0])}
    gated = total if gate_ring == 'active' else load_best[0]
    efrags = efrag_report(links, task.get('efrag_budget'))
    return {'points': at, 'efrags': efrags, 'median_bytes': int(np.median(totals)),
            'positions_over_budget': int((totals > budget).sum()), 'peak_bytes': int(total),
            'peak_position': [round(float(v), 1) for v in where],
            'ring_chunks': nchunks, 'ring_models': nmodels, 'ring_textures': ntex,
            'peak_models': peak_models, 'peak_breakdown': breakdown,
            'budget_bytes': budget, 'headroom_bytes': budget - int(total),
            'load_ring': load, 'largest_block_bytes': int(largest),
            'gated_ring': gate_ring, 'ok': bool(gated <= budget) and efrags['ok'], 'positions': int(len(P)),
            'zone_bytes': int(task['zone']), 'streamed_bytes': int(sum(extra.values()) + ssize.sum())}


def streamed_chunk_models(rows, id1, sizes):
    """{chunk index: {model: bytes}} of the frame map's streamed statics (chim.frame_map CHUNK_KEY):
    each chunk's distinct models, a 16-byte-aligned block each with its block header."""
    from pathlib import Path
    from chim.frame_map import CHUNK_KEY
    per = {}
    for e in rows:
        if CHUNK_KEY in e:
            per.setdefault(int(e[CHUNK_KEY]), set()).add(e['model'])
    size = {}
    out = {}
    for k, models in per.items():
        for m in models:
            if m not in size:
                size[m] = (Path(id1) / m).stat().st_size
        out[k] = {m: _a16(size[m] + sizes['hunk']) for m in models}
    return out


# How the engine holds a streamed static's model: 'shared' (the engine: decoded once into the zone,
# keyed by name, referenced by the active chunks that place it, like ring models) or 'chunk' (each
# chunk its own copy; the larger figure, kept selectable for engines that decode per chunk).
STREAMED_MODELS = 'shared'


def streamed_chunk_bytes(rows, id1, sizes):
    """{chunk index: bytes} the streamed statics bring into the zone with their chunk ('chunk' policy)."""
    return {k: sum(v.values()) for k, v in streamed_chunk_models(rows, id1, sizes).items()}


MOVERS_AT_ONCE = 2     # the companion and one opponent wear their mover models at the same time


def actor_cache(id1, rows, sizes, gap_bytes, movers=MOVERS_AT_ONCE):
    """The actors' alias models in Quake's Cache (they never enter the CHIM zone: Mod_LoadAliasModel puts
    them in the Cache, which lives in the Hunk gap the zone leaves, chim_reserve_kib). Measured in FS-UAE on
    the Balmora MiniWind: the zone and the Hunk are byte-identical with idle-only, react or react+full
    actors; the Cache peak at load grows (docs/ANIMATION.md "Memory"). Reports the distinct standing models
    every placed actor precaches, the largest mover models (animation kit: <model>_m.mdl, loaded only while
    an actor moves) and whether they fit the gap; LRU eviction makes an overflow slower, not fatal, so this
    is recorded, not a failure."""
    from pathlib import Path
    from chim.frame_map import ACTOR_CLASSES
    models = sorted({e['model'] for e in rows if e.get('classname') in ACTOR_CLASSES and e.get('model')
                     and (Path(id1) / e['model']).is_file()})
    block = lambda path: _a16(path.stat().st_size + sizes['hunk'])
    standing = sum(block(Path(id1) / m) for m in models)
    mover_sizes = sorted((block(Path(id1) / (m[:-4] + '_m.mdl')) for m in models
                          if (Path(id1) / (m[:-4] + '_m.mdl')).is_file()), reverse=True)
    peak = standing + sum(mover_sizes[:movers])
    return {'actor_models': len(models), 'standing_bytes': standing, 'movers': len(mover_sizes),
            'mover_bytes_at_once': sum(mover_sizes[:movers]), 'movers_at_once': movers, 'peak_bytes': peak,
            'gap_bytes': gap_bytes, 'fits_gap': peak <= gap_bytes,
            'note': 'Cache, not the CHIM zone: an overflow evicts least recently used models (recorded, not fatal)'}


def skeletal_table(raw):
    """The animation table path a skeletal actor model names (its "AWSB" block: magic, two u16, the 32-byte path;
    tools/skeletal_actor.py), without a view suffix ("|f": the same file), or None for an ordinary model."""
    from actor_frames import SKEL_BLOCK_HEAD, SKEL_BLOCK_MAGIC, SKEL_VERT_BYTES, skeletal_frames
    try:
        if skeletal_frames(raw) is None:
            return None
    except ValueError:
        return None
    import struct
    at = len(raw) - SKEL_BLOCK_HEAD - struct.unpack_from('<i', raw, 60)[0] * SKEL_VERT_BYTES
    name = raw[at + 8:at + 40].split(b'\0', 1)[0].decode('ascii', 'replace')
    return name.split('|', 1)[0] or None


def actor_fast_ram(id1, rows, source=None):
    """The Fast RAM a room's actors take after the room has taken its bank (CHIM-ROOM-HEART-CHAMBER-LOAD-50): the
    animation tables their skeletal models name (aw_skel_load.c, each once, a malloc of the file) and the large pose
    cache (r_alias.c AW_POSE_CACHE_LARGE slots of MAXALIASVERTS vertices), each with the checked allocator's spare
    (aw_tryalloc.h). They load after the room's models (the "after-actors" step), from what the room's bank leaves:
    CHIM_ROOM_KEEP at the least (chim_zone.c ChimZone_RoomStep). Their alias models live in Quake's Cache (actor_cache)."""
    from pathlib import Path
    import engine_limits as EL
    from chim.frame_map import ACTOR_CLASSES
    src = source or EL.SOURCE
    tables = {}
    for m in sorted({e['model'] for e in rows if e.get('classname') in ACTOR_CLASSES and e.get('model')}):
        path = Path(id1) / m
        if not path.is_file():
            continue
        name = skeletal_table(path.read_bytes())
        if name and (Path(id1) / name).is_file():
            tables[name] = (Path(id1) / name).stat().st_size
    import re
    spare = int(re.search(r'#define\s+AW_TRYALLOC_SPARE\s+(\d+)', (Path(src) / 'aw_tryalloc.h').read_text()).group(1))
    pose = need = 0
    if tables:
        # aw_posed_t: two pointers, the frame, the clock, the 6-byte box (24 bytes with padding), the vertices
        pose = EL.define('r_alias.c', 'AW_POSE_CACHE_LARGE', src) * (24 + 4 * EL.define('r_local.h', 'MAXALIASVERTS', src))
        need = sum(t + 4 for t in tables.values()) + pose + spare      # malloc's 4-byte head each; the spare once
    keep = EL._mib_define('chim/chim_zone.h', 'CHIM_ROOM_KEEP', src) * EL.MIB
    return {'tables': tables, 'table_bytes': sum(tables.values()), 'pose_cache_bytes': pose, 'need_bytes': need,
            'keep_bytes': keep, 'fits_keep': need <= keep}


def frame_map_heap(world_dir, id1, sizes, heap_mb=None, zone_kib=None, pool_kib=None, streamed=None, extra_maps=(),
                   jobs=1, cache_dir=None, world=None):
    """The whole-map CHIM heap of each frame map in id1/maps (found by its "_chim_frame" key, .chim or .bsp:
    tools/map_files.py): the zone the engine can take
    (engine_limits.whole_map_zone: the Hunk minus the start-up Hunk, the frame map's BSP, its stated
    "_chim_hunk_rest" and the reserve; never more than chim_zone_kib) and the frame's rings with the
    streamed statics' models in their chunks; extra_maps: further frame map file names in id1/maps (the CHIM region
    frames, which keep their open-world map names). Returns {map name: ring_peak frame report}.
    All frames go through ONE ring_peak (jobs: the shared worker pool, a big frame's positions split over it;
    cache_dir: each frame's result kept by the SHA-256 content key of everything it reads), the same reports as
    frame by frame (tests/test_chim_heap.py). world: the CHIM world the image step already read and checked
    (chim.frame_map.load, read only here); without it the world is read again (BUILD-IMAGE-REGION-MAPS-SERIAL-43)."""
    from pathlib import Path
    from engine_limits import MEASURED_HUNK, chim_memory, whole_map_zone
    from chim.frame_map import FRAME_KEY, HUNK_KEY, entities
    from chim.validate import Failures, load_world
    memory = chim_memory(heap_mb=heap_mb)
    if world is not None:
        settings, textures, models, frames = world['settings'], world['textures'], world['models'], world['frames']
    else:
        fails = Failures()
        settings, files, disk, textures, models, frames = load_world(world_dir, fails)
        if fails:
            raise ValueError('CHIM heap gate: the world does not read back (%s)' % fails[0])
    policy = streamed or STREAMED_MODELS
    if policy not in ('chunk', 'shared'):
        raise ValueError('Unknown streamed-model policy: %s' % policy)
    from map_files import frame_maps
    paths = set(frame_maps(Path(id1, 'maps'))) | {Path(id1, 'maps', name) for name in extra_maps}
    # one entry per frame map; maps that share a frame (Seyda Neen's special maps) go in later batches, so every
    # batch holds each frame once with that map's own zone and streamed statics
    batches = []
    for path in sorted(paths):
        data = path.read_bytes()
        rows = entities(data)
        cell = tuple(int(v) for v in rows[0][FRAME_KEY].split())
        before = MEASURED_HUNK['before_map_bytes'] + _a16(len(data) + sizes['hunk'])
        after = int(rows[0].get(HUNK_KEY, MEASURED_HUNK['client_per_map_bytes']))
        entry = {'path': path, 'cell': cell, 'before': before, 'after': after,
                 'zone': whole_map_zone(before, after, memory),
                 'streamed': (streamed_chunk_bytes(rows, id1, sizes) if policy == 'chunk'
                              else streamed_chunk_models(rows, id1, sizes)),
                 'actor_cache': actor_cache(id1, rows, sizes, memory['gap_bytes'])}
        batch = next((b for b in batches if cell not in b), None)
        if batch is None:
            batch = {}
            batches.append(batch)
        batch[cell] = entry
    out = {}
    for batch in batches:
        world = {'settings': settings, 'textures': textures, 'models': models,
                 'frames': [f for f in frames if tuple(f[1]['cell']) in batch]}
        by_cell = {tuple(f[1]['cell']): f[0] for f in world['frames']}
        streamed_per = {cell: e['streamed'] for cell, e in batch.items()}
        per = {'chunk_extra': streamed_per} if policy == 'chunk' else {'chunk_models': streamed_per}
        report = ring_peak(world, sizes, zone_kib if zone_kib is not None else memory['zone_kib'],
                           pool_kib if pool_kib is not None else memory['pool_kib'],
                           zone_bytes={cell: e['zone'] for cell, e in batch.items()}, jobs=jobs, cache_dir=cache_dir,
                           **per)
        by_path = {f['frame']: f for f in report['frames']}
        for cell, e in batch.items():
            frame = dict(by_path[by_cell[cell]])
            frame.update(map=e['path'].name, heap_mb=memory['heap_mb'], before_zone_bytes=e['before'],
                         after_zone_bytes=e['after'], whole_map_zone_bytes=e['zone'], streamed_models=policy,
                         actor_cache=e['actor_cache'])
            out[e['path'].stem] = frame
    return dict(sorted(out.items()))


def require_frame_map_heap(world_dir, id1, sdk=None, sizes=None, heap_mb=None, report_path=None, extra_maps=(),
                           jobs=1, cache_dir=None, world=None):
    """The image step's CHIM heap gate per frame map (frame_map_heap): report_path (JSON), and a
    ValueError naming the first frame map whose gated ring does not fit its whole-map zone. world: the CHIM
    world already read (frame_map_heap)."""
    import json
    from pathlib import Path
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]
        maps = frame_map_heap(world_dir, id1, sizes, heap_mb, extra_maps=extra_maps, jobs=jobs, cache_dir=cache_dir,
                              world=world)
        # A frame map over the 16 MB budget that fits the 32 MB minimum is marked as the CHIM stage marks such frames
        # (CHIM-FRAME-16MB-REFUSAL-48: 32 MB is the default, the player is kept out on less), not refused: the CHIM
        # stage's estimate can pass a frame that this exact check finds over (BUILD-CHIM-HEAP-GATE-LATE-36: vf0147,
        # 9,536 bytes over in the v0.0.52-dev1 build). Only a frame that fits neither stops the build.
        late = []
        for name, m in maps.items():
            if not m['ok'] and m.get('efrags', {'ok': True})['ok'] and frame_fast_ram(m) == SAFE_FAST_MB:
                if mark_frame_maps(id1, frame_cells([m['frame']]), maps=[m['map']]):
                    m.update(ok=True, fast_mb=SAFE_FAST_MB, marked_by_image_gate=True)
                    late.append(name)
        report = {'maps': maps, 'ok': all(m['ok'] for m in maps.values()), 'marked_32mb_late': late,
                  'method': 'frame map: zone = engine_limits.whole_map_zone(start-up Hunk + frame-map BSP, '
                            '_chim_hunk_rest); rings as the CHIM heap gate with each chunk\'s streamed statics'}
        report['status'] = 'passed' if report['ok'] else 'failed'
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                     newline='\n')
    bad = [m for m in report.get('maps', {}).values() if not m['ok']]
    if bad:
        m = bad[0]
        ring = m['peak_bytes'] if m['gated_ring'] == 'active' else m['load_ring']['peak_bytes']
        raise ValueError('CHIM frame-map heap gate failed: %s needs %d bytes (%s ring), its whole-map zone leaves '
                         '%d for chunks (zone %d bytes on a %d MiB heap)'
                         % (m['map'], ring, m['gated_ring'], m['budget_bytes'], m['zone_bytes'], m['heap_mb']))
    return report


def room_zone_limits(before, after, heap_mb=None, source=None):
    """What a CHIM room map with before/after Hunk bytes around its zone gets (tools/door_graph.py room_limits uses
    the same with the measured start-up Hunk and client allocations). A room map holds nothing but its room
    (ROOM-AKULAKHAN-HEAP-52): it has no frame world (chim_world.c), and a room its zone and the cache banks do not hold
    grows (chim_world.c Chim_RoomGrow): a bank of the free Fast RAM, then the Hunk's rest past the zone
    (engine_limits.room_step, room_hunk_rest). Returns:
    - 'zone_bytes' at the built heap (the 16 MB baseline; Extra RAM off counts as it), 'hunk_rest_bytes' what the
      room can take there past it, and 'zone_room_bytes' the two less the loading buffer (no cache bank, no free Fast
      RAM on 16 MB);
    - on the minimum Fast RAM (32 MB, engine_limits.fast_ram_memory): 'zone_32mb_zone_bytes' (that heap's zone),
      'bank_bytes' (the automatic cache bank, which models and textures prefer, chim_zone.c AllocIn),
      'room_bank_bytes' (the room's bank of free Fast RAM, from the measured largest free block),
      'hunk_rest_32mb_bytes', and 'min_fast_room_bytes' all of them less the buffer (CHIM-ROOM-ESTIMATE-48);
    - 'block_bytes_min_fast': the largest one model can be there (one block: the largest of those banks)."""
    import engine_limits as EL
    src = source or EL.SOURCE
    memory = EL.chim_memory(src, heap_mb=heap_mb)
    safe = EL.fast_ram_memory(EL.MIN_FAST_RAM_MIB, src)
    safe_memory = EL.chim_memory(src, heap_mb=safe['heap_mb'])
    # Chim_RoomGrow step 2 keeps the larger of CHIM_ROOM_REST_KIB and the map's statement for what loads after the zone
    rest = max(int(after), EL.define('chim/chim_zone.h', 'CHIM_ROOM_REST_KIB', src) * 1024)
    zone = min(memory['zone_kib'] * 1024, EL.whole_map_zone(before, after, memory))
    safe_zone = min(safe_memory['zone_kib'] * 1024, EL.whole_map_zone(before, after, safe_memory))
    hunk16 = EL.room_hunk_rest(before, rest, memory, src)
    hunk32 = EL.room_hunk_rest(before, rest, safe_memory, src)
    buffer = safe['buffer_bytes']
    return {'heap_mb': memory['heap_mb'], 'zone_bytes': zone, 'hunk_rest_bytes': hunk16,
            'zone_room_bytes': zone + hunk16 - buffer, 'buffer_bytes': buffer,
            'min_fast_ram_mib': EL.MIN_FAST_RAM_MIB, 'heap_32mb_mb': safe['heap_mb'], 'zone_32mb_zone_bytes': safe_zone,
            'bank_bytes': safe['bank_bytes'], 'room_bank_bytes': safe['room_bank_bytes'],
            'room_largest_free_bytes': safe['room_largest_bytes'], 'hunk_rest_32mb_bytes': hunk32,
            'min_fast_room_bytes': safe_zone - buffer + safe['bank_bytes'] + safe['room_bank_bytes'] + hunk32,
            'block_bytes_min_fast': max(safe_zone - buffer, safe['bank_bytes'], safe['room_bank_bytes'], hunk32)}


# The engine's own blocks of a CHIM room map on the target (m68k, 4-byte pointers; ROOM-AKULAKHAN-HEAP-52), kept against
# the engine source by tests/test_chim_room_heap.py:
# - chim_zone.c CHIM_HEADER, every block's header: sizeof(chim_block_t) (int, two bytes, short, unsigned, five
#   pointers: 32 bytes) rounded to 16;
# - chim_local.h chim_place_t, one per placement in the record block: entity_t and 56 bytes (mins, maxs, s, c, pid,
#   model, owner, linked, flags, leaves); the block also holds the file, 9 floats a placement and a pointer a model
#   (chim_room.c RoomLoad);
# - the store index (chim_world.c ReadIndex): a chim_file_row_t per file (26 bytes on the target, counted 28) and a
#   chim_asset_t (20 bytes) with its slot pointer per model and texture;
# - chim_prefetch.c: SLOTS (1 << 12) slot_t of 8 bytes, the prefetch table locked in the cache bank from the first
#   exterior frame on;
# - chim_local.h chim_model_t past its model_t: the arena record and five words, counted 64 (as chim/zone_sim.py).
ROOM_BLOCK_HEADER = 32
ROOM_PLACE_EXTRA = 56
ROOM_INDEX_ROW = 28
ROOM_INDEX_ASSET = 24
ROOM_PREFETCH_TABLE = (1 << 12) * 8
ROOM_MODEL_EXTRA = 64


def room_block(request):
    """The zone bytes one request takes on the target: the block header and the data rounded to 16."""
    return ROOM_BLOCK_HEADER + _a16(request)


def room_blocks(id1, room, sizes, index=None, buffer_bytes=None):
    """The zone requests (bytes without the block header) of one CHIM room (chim.interior.installed_room or its
    record read with 'store' and 'room'): 'record', 'models' [(id, bytes, texture ids)] in the record's order,
    'textures' {id: bytes}, 'index' (the store index), 'buffer' (the loading buffer) and 'prefetch_table'. INDEX:
    the store's chim.format.read_index (read when not given)."""
    from pathlib import Path
    from chim import format as F
    from chim.interior import store_model_images
    root = Path(id1) / room['store']
    index = index or F.read_index((root / 'world.cwi').read_bytes())
    files, directory, textures = index[1], index[2], index[3]
    images = store_model_images(id1, room['store'], room['models'])
    models = []
    for i in room['models']:
        lumps = F.read_brush_image(images[i])
        models.append((i, image_bytes(lumps, sizes, point_hull_only=True) - sizes['hunk'] + ROOM_MODEL_EXTRA,
                       F.read_texture_refs(lumps[2])))
    used = sorted({t for _, _, refs in models for t in refs})
    record_file = (root / 'rooms' / (room['room'] + '.crm')).stat().st_size
    n = len(room['placements'])
    if buffer_bytes is None:
        from engine_limits import cvar_default
        buffer_bytes = cvar_default('chim/chim_world.c', 'chim_buffer_kib') * 1024
    return {'record': ((record_file + 3) & ~3) + n * (sizes['entity'] + ROOM_PLACE_EXTRA) + 36 * n + 4 * len(models),
            'record_file_bytes': record_file, 'models': models,
            'textures': {t: texture_bytes(textures[t]['width'], textures[t]['height'], sizes) - sizes['hunk']
                         for t in used},
            'index': len(files) * ROOM_INDEX_ROW + (len(directory) + len(textures)) * ROOM_INDEX_ASSET,
            'buffer': max(int(buffer_bytes), int(sizes.get('bsp_slice_bytes', 0))),
            'prefetch_table': ROOM_PREFETCH_TABLE}


def room_heap(blocks, limits, walk=True, lib=None):
    """One room's report from its blocks (room_blocks) and limits (room_zone_limits): the sums and, with WALK, the
    load through the engine's allocator (chim.room_zone.walk) on the 16 MB baseline and on the 32 MB minimum.
    need_bytes: what the room holds at 32 MB besides the loading buffer (its record, models and textures, the store
    index and the prefetch table, each a block); need_16mb_bytes the same without the prefetch table (no cache bank).
    The walk runs where packing can decide: a fresh bank holds every block its sum holds (no block is freed during a
    room's first try: large blocks fill it from the low end, small ones from the high end, chim_zone.c TryHigh), so a
    room within one bank (the zone at 16 MB, the cache bank at 32 MB) fits by its sum; a room past it spreads over
    banks and grows (Chim_RoomGrow), where the tail of each bank can stay empty: that room is walked ('walk_16mb',
    'walk_32mb', or 'one bank: the sum decides')."""
    from engine_limits import cvar_default
    models = sum(room_block(b) for _, b, _ in blocks['models'])
    textures = sum(room_block(b) for b in blocks['textures'].values())
    own = room_block(blocks['record']) + models + textures + room_block(blocks['index'])
    # the buffer's own block header: the limits take its data off the zone
    need16 = own + ROOM_BLOCK_HEADER
    need = need16 + room_block(blocks['prefetch_table'])
    largest = max([room_block(b) for _, b, _ in blocks['models']] or [0])
    out = dict(limits, **{
        'models': len(blocks['models']), 'textures': len(blocks['textures']), 'model_bytes': models,
        'texture_bytes': textures, 'record_bytes': blocks['record_file_bytes'],
        'record_block_bytes': room_block(blocks['record']), 'index_block_bytes': room_block(blocks['index']),
        'need_bytes': need, 'need_16mb_bytes': need16, 'largest_model_bytes': largest,
        'fits_zone': need16 <= limits['zone_room_bytes'],
        'ok': need <= limits['min_fast_room_bytes'] and largest <= limits['block_bytes_min_fast']})
    out['headroom_32mb_bytes'] = limits['min_fast_room_bytes'] - need
    if walk:
        from chim.room_zone import walk as room_walk
        ends = cvar_default('chim/chim_world.c', 'chim_zone_ends') * 1024
        one = 'one bank: the sum decides'
        out['walk_16mb'] = out['walk_32mb'] = one
        # 16 MB: one bank (the zone) unless the room needs the Hunk's rest, and only a room the sum lets in
        if out['fits_zone'] and need16 > limits['zone_bytes'] - limits['buffer_bytes']:
            w16 = room_walk(blocks, 0, limits['zone_bytes'],
                            [('free Fast RAM', 0), ('Hunk rest', limits['hunk_rest_bytes'])], ends, lib)
            out['walk_16mb'] = w16
            out['fits_zone'] = w16['ok'] and not w16['untextured']
        # 32 MB: the models and textures prefer the cache bank (chim_zone.c AllocIn); past it the room spreads
        if out['ok'] and need > limits['bank_bytes']:
            w32 = room_walk(blocks, limits['bank_bytes'], limits['zone_32mb_zone_bytes'],
                            [('free Fast RAM', limits['room_bank_bytes']),
                             ('Hunk rest', limits['hunk_rest_32mb_bytes'])], ends, lib)
            out['walk_32mb'] = w32
            out['ok'] = w32['ok'] and not w32['untextured']
    return out


def room_map_heap(id1, sizes, heap_mb=None, stems=None, walk=True):
    """The zone each CHIM room map needs (IMAGE-ROOM-MAPS-LATE-PASSES-48: the BSP heap estimate of a room map counts
    only its shell world and entities, while the room loads every model of its record, with their textures, into the
    map's zone: chim/chim_room.c). Per room map: what the engine gives the room (room_zone_limits: the zone by the
    whole-map rule, engine_limits.whole_map_zone: the start-up Hunk and the room map before it, "_chim_hunk_rest" or
    the measured client allocations after it, never more than chim_zone_kib; the cache bank; the room's growth) against
    the engine's own blocks of the room (room_blocks: the record with its placements, every listed model and texture
    once, the store index, the prefetch table), added up and, with WALK, loaded through the engine's allocator
    (room_heap). 'actors': the room's actor models in Quake's Cache against the Hunk gap (actor_cache, recorded).
    STEMS: only these room maps (default every one). Returns {room map stem: report}."""
    from pathlib import Path
    from chim import format as F
    from chim.frame_map import HUNK_KEY, entities
    from chim.interior import installed_room
    from engine_limits import MEASURED_HUNK, chim_memory
    from map_files import map_stem, room_maps
    out, indexes = {}, {}
    gap = chim_memory(heap_mb=heap_mb)['gap_bytes']
    for path in room_maps(Path(id1) / 'maps'):
        if stems is not None and map_stem(path.name) not in stems:
            continue
        data = path.read_bytes()
        rows = entities(data)
        room = installed_room(path)
        if room['store'] not in indexes:
            indexes[room['store']] = F.read_index((Path(id1) / room['store'] / 'world.cwi').read_bytes())
        before = MEASURED_HUNK['before_map_bytes'] + _a16(len(data) + sizes['hunk'])
        after = int(rows[0].get(HUNK_KEY, MEASURED_HUNK['client_per_map_bytes']))
        limits = room_zone_limits(before, after, heap_mb)
        report = room_heap(room_blocks(id1, room, sizes, indexes[room['store']]), limits, walk)
        report.update({'map': path.name, 'room': room['room'], 'placements': len(room['placements']),
                       'before_zone_bytes': before, 'after_zone_bytes': after,
                       'actors': actor_cache(id1, rows, sizes, gap)})
        # a room past the 16 MB zone may take the free Fast RAM down to CHIM_ROOM_KEEP; its actors' tables and posed
        # frames load from what is left (CHIM-ROOM-HEART-CHAMBER-LOAD-50)
        report['actor_fast'] = actor_fast_ram(id1, rows)
        if not report.get('fits_zone') and not report['actor_fast']['fits_keep']:
            report['ok'] = False
        out[map_stem(path.name)] = report
    return out


_STORE_INDEX = {}


def _store_room_task(task):
    """One room of room_store_heap on a pool worker: (room, report)."""
    from pathlib import Path
    from chim import format as F
    from chim.interior import STORE, read_room_record
    out, name, sizes, limits, walk = task
    root = Path(out) / STORE
    if _STORE_INDEX.get('root') != str(root):
        _STORE_INDEX.update(root=str(root), index=F.read_index((root / 'world.cwi').read_bytes()))
    room = dict(read_room_record((root / 'rooms' / (name + '.crm')).read_bytes()), store=STORE, room=name)
    report = room_heap(room_blocks(out, room, sizes, _STORE_INDEX['index']), limits, walk)
    report.update({'room': name, 'placements': len(room['placements'])})
    return name, report


def room_store_heap(out, sizes, rooms=None, walk=True, jobs=1):
    """The early room heap check (ROOM-AKULAKHAN-HEAP-52, the chim-interiors stage, tools/chim/interior.py): every room
    record of the interior store the stage wrote in OUT (OUT/<store>/rooms/<room>.crm), before any room map exists,
    with the room map at its smallest (the start-up Hunk and the map's Hunk block, no map bytes) and the measured
    client allocations after it: the most the image's room heap gate (room_map_heap) can give the room, so a room that
    fails here fails there; never the other way round. ROOMS: only these room names. Rooms side by side on JOBS
    workers, largest record first. Returns {room: report}."""
    from pathlib import Path
    from build_parallel import ordered_map
    from chim.interior import STORE
    from engine_limits import MEASURED_HUNK
    root = Path(out) / STORE
    before = MEASURED_HUNK['before_map_bytes'] + _a16(sizes['hunk'])
    after = MEASURED_HUNK['client_per_map_bytes']
    limits = dict(room_zone_limits(before, after), before_zone_bytes=before, after_zone_bytes=after)
    names = [p.stem for p in sorted((root / 'rooms').glob('*.crm')) if rooms is None or p.stem in rooms]
    tasks = [(str(out), n, sizes, limits, walk) for n in names]
    return dict(ordered_map(_store_room_task, tasks, max(1, int(jobs or 1)),
                            cost=lambda t: (Path(t[0]) / STORE / 'rooms' / (t[1] + '.crm')).stat().st_size))


def require_room_store_heap(out, sdk=None, sizes=None, report_path=None, jobs=1):
    """The chim-interiors stage's early room heap check (room_store_heap): report_path (JSON); a ValueError names the
    first room the 32 MB minimum cannot hold even with its room map at its smallest, seconds after the store is
    written instead of in the image step (the image's gate, require_room_map_heap, stays the check of record)."""
    import json
    from pathlib import Path
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]
        rooms = room_store_heap(out, sizes, jobs=jobs)
        report = {'rooms': rooms, 'ok': all(r['ok'] for r in rooms.values()),
                  'failed': sorted(n for n, r in rooms.items() if not r['ok']),
                  'method': 'room_store_heap: the room heap gate of the image step (room_heap) with each room map at '
                            'its smallest: what fails here fails there'}
        report['status'] = 'passed' if report['ok'] else 'failed'
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                     newline='\n')
    if report.get('failed'):
        raise ValueError(room_failure_text('CHIM room heap check (early, before the image)', report['rooms'][report['failed'][0]]))
    return report


def room_failure_text(what, r):
    """One line naming a room that does not fit the 32 MB minimum, with what it needs and what it has."""
    walk = r.get('walk_32mb')
    walk = walk if isinstance(walk, dict) else {}
    af = r.get('actor_fast') or {}
    zone_ok = r.get('need_bytes', 0) <= r.get('min_fast_room_bytes', 0) and walk.get('ok', True)
    if af and not af.get('fits_keep') and not r.get('fits_zone') and zone_ok:
        return ('%s failed: %s: its actors\' animation tables and posed frames need %d bytes of Fast RAM (tables %s, '
                'pose cache %d) after the room takes its bank, which leaves %d (CHIM_ROOM_KEEP)'
                % (what, r.get('map') or r.get('room'), af['need_bytes'], af['tables'], af['pose_cache_bytes'],
                   af['keep_bytes']))
    return ('%s failed: %s needs %d bytes for its models, textures, record and index; its zone holds %d (%d MiB heap) '
            'and the 32 MB minimum %d (zone %d, cache bank %d, free Fast RAM %d, Hunk rest %d, less the buffer); its '
            'largest model %d bytes, one block %d%s'
            % (what, r.get('map') or r.get('room'), r['need_bytes'], r.get('zone_bytes', 0), r.get('heap_mb', 0),
               r.get('min_fast_room_bytes', 0), r.get('zone_32mb_zone_bytes', 0), r.get('bank_bytes', 0),
               r.get('room_bank_bytes', 0), r.get('hunk_rest_32mb_bytes', 0), r.get('largest_model_bytes', 0),
               r.get('block_bytes_min_fast', 0),
               '; the load through the engine\'s allocator: %s did not fit after %s' % (
                   walk.get('failed'), ', '.join(walk.get('grown') or ['no growth']))
               if walk and not walk.get('ok') else ''))


# What the 32 MB minimum gives a CHIM room (RAM-REQUIREMENT-32MB-48, CHIM-ROOM-16MB-REFUSAL-48, ROOM-AKULAKHAN-HEAP-52):
# the measured model of room_zone_limits (engine_limits.fast_ram_memory, measured in FS-UAE: the 13 MiB heap, one
# automatic 7 MiB CHIM cache bank, which models and textures prefer, chim_zone.c AllocIn, and in a room map after a
# town 5,512 KiB of free Fast RAM in one block, of which a room that needs it takes 3,456 KiB (the largest block less
# 2 MiB in 64 KiB steps; engine_limits.MEASURED_ROOM), then the Hunk's rest). The 16 MB baseline
# (or Extra RAM off) has the built heap and no bank: the zone and the Hunk's rest, less the loading buffer.
SAFE_FAST_MB = 32
ROOM_FAST_KEY = '_chim_room_fast_mb'    # the room map's worldspawn mark the engine reads at the door (aw_scene.c)


def require_room_map_heap(id1, sdk=None, sizes=None, heap_mb=None, report_path=None):
    """The image step's zone gate per CHIM room map (room_map_heap): report_path (JSON). A room that fits the 16 MB
    baseline ('fits_zone': the zone and the Hunk rest less the loading buffer, room_zone_limits) is 'fast_mb' 16; one
    that fits only what the 32 MB minimum gives a room (its zone, the automatic cache bank, the room's bank of free
    Fast RAM and the Hunk rest, 'min_fast_room_bytes', with its largest model within one block and, past one bank, its
    load through the engine's allocator; CHIM-ROOM-ESTIMATE-48, ROOM-AKULAKHAN-HEAP-52) is 'fast_mb' 32, and its
    room map is marked (ROOM_FAST_KEY) so the engine refuses it at the door on less (CHIM-ROOM-16MB-REFUSAL-48); a
    ValueError names the first room that fits neither. 'over_16mb_zone' lists the rooms over the 16 MB zone alone,
    the same set as 'marked_32mb' when every room fits."""
    import json
    from pathlib import Path
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]
        rooms = room_map_heap(id1, sizes, heap_mb)
        for r in rooms.values():
            r['fits_16mb'] = r['fits_zone']
            r['zone_32mb_bytes'] = r['min_fast_room_bytes']
            r['fast_mb'] = 16 if r['fits_16mb'] else SAFE_FAST_MB
        marked = mark_room_fast_ram(id1, sorted(n for n, r in rooms.items() if r['ok'] and not r['fits_16mb']))
        # the mark makes each marked map a few bytes longer, and the map sits before the zone in the Hunk: the marked
        # rooms are measured again as they ship (CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48)
        for n, r in (room_map_heap(id1, sizes, heap_mb, stems=set(marked)) if marked else {}).items():
            r.update(fits_16mb=False, zone_32mb_bytes=r['min_fast_room_bytes'], fast_mb=SAFE_FAST_MB, marked=True)
            rooms[n] = r
        report = {'rooms': rooms, 'ok': all(r['ok'] for r in rooms.values()), 'marked_32mb': marked,
                  'over_16mb_zone': sorted(n for n, r in rooms.items() if not r['fits_zone']),
                  'method': 'room map: zone = engine_limits.whole_map_zone(start-up Hunk + room map, '
                            '_chim_hunk_rest), never more than chim_zone_kib; need = the engine\'s blocks of the room '
                            '(room_blocks: the record with its placements, every model of the record and every texture '
                            'they use once, the store index, the prefetch table at 32 MB; block headers); 16 MB = need '
                            'within the zone and the Hunk rest a room can take (engine_limits.room_hunk_rest) less the '
                            'loading buffer; ok = need within what the minimum Fast RAM gives a room (that heap\'s '
                            'zone, the automatic cache bank, the room\'s bank of the measured free Fast RAM, the Hunk '
                            'rest: engine_limits.fast_ram_memory, chim_world.c Chim_RoomGrow) and the largest model '
                            'within one block, and, for a room past one bank, its load through the engine\'s '
                            'allocator (chim/room_zone.py); a room over the 16 MB zone that is ok carries "%s" "%d"'
                            % (ROOM_FAST_KEY, SAFE_FAST_MB)}
        report['status'] = 'passed' if report['ok'] else 'failed'
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                     newline='\n')
    bad = [r for r in report.get('rooms', {}).values() if not r['ok']]
    if bad:
        raise ValueError(room_failure_text('CHIM room heap gate', bad[0]))
    return report


def mark_room_fast_ram(id1, stems, fast_mb=SAFE_FAST_MB):
    """Write ROOM_FAST_KEY into the worldspawn of each named CHIM room map (id1/maps/<stem>.chim). Returns the stems
    marked. The rest of the map is unchanged (its lumps are written again in the same order)."""
    from pathlib import Path
    from chim import format as F
    from chim.frame_map import entities, entity_text
    from map_files import frame_map_path
    out = []
    for stem in stems:
        path = frame_map_path(Path(id1), stem, 'chim')
        data = path.read_bytes()
        rows = entities(data)
        if not rows or rows[0].get('classname') != 'worldspawn':
            raise ValueError('CHIM room map %s has no worldspawn first' % path.name)
        rows[0][ROOM_FAST_KEY] = str(int(fast_mb))
        lumps = F.read_brush_image(data)
        lumps[0] = entity_text(rows)
        path.write_bytes(F.brush_image(lumps)[0])
        out.append(stem)
    return out


# A CHIM frame whose gated ring is over the 16 MB baseline's zone, or within FRAME_NEAR_BYTES of it, is built as it is
# and marked as needing 32 MB of Fast RAM (the maintainer's rule for v0.0.48: "if there's places that go over the
# budget, you just mark them up as 'needs 32MB of RAM to run'"; CHIM-FRAME-16MB-REFUSAL-48), the way the rooms are
# (ROOM_FAST_KEY): FRAME_FAST_KEY in its frame map's worldspawn, read by the engine at the crossing into the frame
# (aw_scene.c AW_SceneFrameRefuse). Near: 64 KiB, about 1 % of the 6,242,304-byte budget; measured on the v0.0.48-dev2
# builds (1,351 frames), 5 frames lie under it (368 to 35,968 bytes of headroom) and the next has 179,136.
FRAME_NEAR_BYTES = 64 * 1024
FRAME_FAST_KEY = '_chim_frame_fast_mb'
BANKED = ('models_drawn', 'models_collision', 'textures', 'shared')   # peak_breakdown parts the cache bank can hold


def frame_fast_ram(frame, near=FRAME_NEAR_BYTES, memory=None):
    """The Fast RAM (MB) one frame of a heap report needs: 16 when its gated ring fits the 16 MB baseline's budget
    with at least NEAR bytes to spare; SAFE_FAST_MB (32) when it does not but fits what the 32 MB minimum gives a
    frame (engine_limits.fast_ram_memory: the same zone, and the automatic CHIM cache bank, which models and
    textures prefer, chim_zone.c AllocIn: the ring less its banked parts, at most the bank, within the budget, and
    its largest block within the larger of the two); 0 when it fits neither. Efrag links are not Fast RAM: a frame
    over them fails as before (require_heap)."""
    from engine_limits import MIN_FAST_RAM_MIB, fast_ram_memory
    gated = frame['peak_bytes'] if frame.get('gated_ring', 'active') == 'active' else frame['load_ring']['peak_bytes']
    budget = frame['budget_bytes']
    if budget - gated >= near:
        return 16
    bank = (memory or fast_ram_memory(MIN_FAST_RAM_MIB))['bank_bytes']
    banked = sum(int((frame.get('peak_breakdown') or {}).get(k, 0)) for k in BANKED)
    zone_need = gated - min(bank, banked)
    if zone_need <= budget and frame['largest_block_bytes'] <= max(budget, bank):
        return SAFE_FAST_MB
    return 0


def mark_frames(report, near=FRAME_NEAR_BYTES):
    """Each frame of a heap report gets 'fast_mb' (frame_fast_ram); a frame over the 16 MB budget that fits the 32 MB
    minimum is ok (built as is, marked); the report gets 'marked_32mb' (frame record paths), 'near_bytes' and
    'fast_ram_32mb' (the counts for the receipt). Returns the marked frames."""
    from engine_limits import MIN_FAST_RAM_MIB, fast_ram_memory
    memory = fast_ram_memory(MIN_FAST_RAM_MIB)
    marked = []
    for f in report.get('frames', []):
        f['fast_mb'] = frame_fast_ram(f, near, memory)
        if f['fast_mb'] == SAFE_FAST_MB:
            marked.append(f['frame'])
            if f.get('efrags', {'ok': True})['ok']:
                f['ok'] = True
    report['marked_32mb'] = marked
    report['near_bytes'] = near
    report['fast_ram_32mb'] = {'frames': len(marked), 'frame_records': marked,
                               'over_16mb': sum(1 for f in report.get('frames', [])
                                                if f['fast_mb'] == SAFE_FAST_MB and f['headroom_bytes'] < 0),
                               'near_bytes': near, 'bank_bytes': memory['bank_bytes'],
                               'rule': 'gated ring over the 16 MB budget or within near_bytes of it, and within the '
                                       '32 MB minimum (the same zone and the automatic cache bank): marked %s %d'
                                       % (FRAME_FAST_KEY, SAFE_FAST_MB)}
    report['ok'] = all(f['ok'] for f in report.get('frames', []))
    return marked


def frame_cells(paths):
    """{(x, y)} of frame record paths 'frames/x-07/y-04/frame.ccf' (the CHIM world's frame cells)."""
    out = set()
    for p in paths:
        parts = str(p).replace(chr(92), '/').split('/')
        xs = [s for s in parts if s[:1] == 'x' and s[1:2] in '+-']
        ys = [s for s in parts if s[:1] == 'y' and s[1:2] in '+-']
        if xs and ys:
            out.add((int(xs[-1][1:]), int(ys[-1][1:])))
    return out


def mark_frame_maps(id1, cells, fast_mb=SAFE_FAST_MB, maps=None):
    """Write FRAME_FAST_KEY into the worldspawn of each CHIM frame map in id1/maps (found by its "_chim_frame" key,
    tools/map_files.py; maps: file names to look at, default all) whose frame cell is in CELLS; the rest of the map is
    unchanged.
    Returns the map names (stems) marked, sorted."""
    from pathlib import Path
    from chim import format as F
    from chim.frame_map import FRAME_KEY, entities, entity_text
    from map_files import frame_maps
    cells = {tuple(c) for c in cells}
    out = []
    paths = frame_maps(Path(id1, 'maps')) if maps is None else [Path(id1, 'maps', m) for m in maps]
    for path in sorted(paths):
        data = path.read_bytes()
        rows = entities(data)
        if not rows or rows[0].get('classname') != 'worldspawn' or FRAME_KEY not in rows[0]:
            continue
        if tuple(int(v) for v in rows[0][FRAME_KEY].split()) not in cells:
            continue
        if rows[0].get(FRAME_FAST_KEY) != str(int(fast_mb)):
            # right after the classname: the engine reads only the first KiB of the entity text (aw_scene.c
            # map_fast_mb), and a frame map's worldspawn carries the hand fields after it
            rest = {k: x for k, x in rows[0].items() if k not in ('classname', FRAME_FAST_KEY)}
            rows[0] = dict({'classname': 'worldspawn', FRAME_FAST_KEY: str(int(fast_mb))}, **rest)
            lumps = F.read_brush_image(data)
            lumps[0] = entity_text(rows)
            path.write_bytes(F.brush_image(lumps)[0])
        out.append(path.stem)
    return sorted(out)


def require_heap(out, sdk=None, sizes=None, report_path=None, zone_kib=None, pool_kib=None, jobs=1, cache_dir=None,
                 world=None):
    """The build's CHIM heap gate: OUT/chim-heap.json, and a ValueError naming the frame whose largest
    ring does not fit. sizes: the target ABI sizes (default: probed with the SDK's compiler, as the
    strict world-map heap gate does). Without either the gate is recorded as not run. jobs and
    cache_dir: ring_peak's (frames in parallel, each frame's result kept by its content key). world: the world
    the step's validation read (chim.validate.loaded_world), else the files are read again."""
    import json
    from pathlib import Path
    from chim.validate import loaded_world
    report_path = Path(report_path or Path(out) / 'chim-heap.json')
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]       # (sizes, probe receipt)
        try:
            # the frame files read on the worker pool when the world is not given (BUILD-CHIM-SERIAL-SECTIONS-44)
            settings, files, disk, textures, models, frames = loaded_world(out, world, jobs)
        except ValueError as exc:
            raise ValueError('CHIM heap gate: the world does not read back (%s)' % exc)
        report = ring_peak({'settings': settings, 'textures': textures, 'models': models, 'frames': frames},
                           sizes, zone_kib, pool_kib, jobs=jobs, cache_dir=cache_dir)
        # over or near the 16 MB budget and within the 32 MB minimum: built as is, marked (CHIM-FRAME-16MB-REFUSAL-48)
        mark_frames(report)
        report['status'] = 'passed' if report['ok'] else 'failed'
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    bad = [f for f in report.get('frames', []) if not f['ok']]
    links = [f for f in bad if not f.get('efrags', {'ok': True})['ok']]
    if links:
        f = links[0]
        raise ValueError('CHIM heap gate failed: %s places %d placements in one active ring, more than the %d '
                         'efrag links CHIM may use (client.h AW_EFRAG_LIMIT less CHIM_EFRAG_RESERVE); see %s'
                         % (f['frame'], f['efrags']['ring_placements_peak'], f['efrags']['budget_links'],
                            report_path))
    if bad:
        # every frame over the budget, worst first, each with how much it is over (maintainer 2026-10-16: "whenever
        # something is over budget, I'd know how much over budget")
        bad = sorted(bad, key=lambda f: f['budget_bytes'] - f['peak_bytes'])
        zone_kib, pool_kib = report['zone_kib'], report['pool_kib']
        raise ValueError('CHIM heap gate failed: %d frame(s) over the zone of %d bytes (%d KiB zone minus %d x %d KiB '
                         'frame-world slots): %s; see %s'
                         % (len(bad), bad[0]['budget_bytes'], zone_kib, POOL_SLOTS, pool_kib,
                            '; '.join(over_budget_text(f) for f in bad), report_path))
    return report


def over_budget_text(f):
    """'frames/x/y needs N bytes at [x, y], over by M bytes (K KiB, P %)' for one frame of the heap report."""
    over = f['peak_bytes'] - f['budget_bytes']
    return '%s needs %d bytes at %s, over by %d bytes (%.0f KiB, %.1f %%)' % (
        f['frame'], f['peak_bytes'], f['peak_position'], over, over / 1024, 100.0 * over / f['budget_bytes'])
