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
node tree as the point hull (dclipnode + mnode per node), and the standing
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


def image_bytes(lumps, sizes):
    """One zone block for a brush image (a chunk's terrain or a placed model): the allocation header,
    the model header and the arena AW_BrushBound gives for it (texture references, not miptex)."""
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
        nodes * sizes['dclipnode'], nodes * sizes['mnode']))
    return sizes['hunk'] + _a16(sizes['model'] + arena)


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
    model_tex = []
    for i, m in enumerate(models):
        lumps = F.read_brush_image(m['image'])
        model_size[i] = image_bytes(lumps, sizes)
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
        uses_s = np.zeros((n, len(snames)), np.int32)
        lo = np.zeros((n, 2))
        for k, c in enumerate(chunks):
            lumps = F.read_brush_image(c['image'])
            records = c['owned'] + c['reach']
            own[k] = (image_bytes(lumps, sizes) + sizes['hunk']
                      + _a16(len(records) * (entry + sizes['pointer'])) + extra.get(c['index'], 0))
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
            'peak_models': peak_models,
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

HEAP_AUDIT_VERSION = 2      # bump when the per-frame audit's arithmetic changes (cache keys)
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
    model_size, model_tex = {}, {}

    def model(i):
        if i not in model_size:
            lumps = F.read_brush_image(models[i]['image'])
            model_size[i] = image_bytes(lumps, sizes)
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
                'model_tex': mtex,
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
        cache.mkdir(parents=True, exist_ok=True)
        for i, k in enumerate(keys):
            f = cache / (k + '.json')
            if f.is_file():
                results[i] = json.loads(f.read_text(encoding='utf-8'))
    todo = [i for i, r in enumerate(results) if r is None]
    if jobs and jobs > 1 and len(todo) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=min(jobs, len(todo))) as pool:
            for i, r in zip(todo, pool.map(_frame_ring, [tasks[i] for i in todo])):
                results[i] = r
    else:
        for i in todo:
            results[i] = _frame_ring(tasks[i])
    if cache:
        for i in todo:
            (cache / (keys[i] + '.json')).write_text(json.dumps(results[i], sort_keys=True), encoding='utf-8',
                                                    newline='\n')
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


def _frame_ring(task):
    """One frame's ring report (ring_peak), on the frame's own model and texture numbering."""
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
    uses_model = np.zeros((n, len(used)), np.int32)
    uses_tex = np.zeros((n, len(tex_ids)), np.int32)
    uses_s = np.zeros((n, len(snames)), np.int32)
    lo = np.zeros((n, 2))
    for k, c in enumerate(chunks):
        lumps = F.read_brush_image(c['image'])
        records = c['owned'] + c['reach']
        own[k] = (image_bytes(lumps, sizes) + sizes['hunk']
                  + _a16(len(records) * (entry + sizes['pointer'])) + extra.get(c['index'], 0))
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
    model_uses_tex = np.zeros((len(used), len(tex_ids)), np.int32)
    for i, ts in enumerate(task['model_tex']):
        model_uses_tex[i, [tlocal[t] for t in ts]] = 1
    xs = np.arange(lx + sample / 2, lx + frame['nx'] * g, sample)
    ys = np.arange(ly + sample / 2, ly + frame['ny'] * g, sample)
    P = np.array([(x, y) for y in ys for x in xs])

    def rings(p, r=radius):
        dx = np.maximum(np.maximum(lo[None, :, 0] - p[:, None, 0], p[:, None, 0] - hi[None, :, 0]), 0)
        dy = np.maximum(np.maximum(lo[None, :, 1] - p[:, None, 1], p[:, None, 1] - hi[None, :, 1]), 0)
        active = (dx * dx + dy * dy <= r * r).astype(np.int32)
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
                    [int(used[i]) for i in np.nonzero(need_m[k])[0]])
        ltotal, lactive, lneed_m, _ = rings(p, load_radius)
        load_totals.append(ltotal)
        k = int(np.argmax(ltotal))
        if load_best is None or ltotal[k] > load_best[0]:
            load_best = (float(ltotal[k]), p[k])
        if lneed_m.any():
            largest = max(largest, float((lneed_m * model_size[None, :]).max()))
    largest = max(largest, float(own.max()) if len(own) else 0.0)
    total, where, nchunks, nmodels, ntex, peak_models = best
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
            'peak_models': peak_models,
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


def frame_map_heap(world_dir, id1, sizes, heap_mb=None, zone_kib=None, pool_kib=None, streamed=None):
    """The whole-map CHIM heap of each frame map in id1/maps (*-chim.bsp): the zone the engine can take
    (engine_limits.whole_map_zone: the Hunk minus the start-up Hunk, the frame map's BSP, its stated
    "_chim_hunk_rest" and the reserve; never more than chim_zone_kib) and the frame's rings with the
    streamed statics' models in their chunks. Returns {map name: ring_peak frame report}."""
    from pathlib import Path
    from engine_limits import MEASURED_HUNK, chim_memory, whole_map_zone
    from chim.frame_map import FRAME_KEY, HUNK_KEY, entities
    from chim.validate import Failures, load_world
    memory = chim_memory(heap_mb=heap_mb)
    fails = Failures()
    settings, files, disk, textures, models, frames = load_world(world_dir, fails)
    if fails:
        raise ValueError('CHIM heap gate: the world does not read back (%s)' % fails[0])
    world = {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}
    out = {}
    for path in sorted(Path(id1, 'maps').glob('*-chim.bsp')):
        data = path.read_bytes()
        rows = entities(data)
        cell = tuple(int(v) for v in rows[0][FRAME_KEY].split())
        before = MEASURED_HUNK['before_map_bytes'] + _a16(len(data) + sizes['hunk'])
        after = int(rows[0].get(HUNK_KEY, MEASURED_HUNK['client_per_map_bytes']))
        zone = whole_map_zone(before, after, memory)
        one = dict(world, frames=[f for f in frames if tuple(f[1]['cell']) == cell])
        policy = streamed or STREAMED_MODELS
        if policy not in ('chunk', 'shared'):
            raise ValueError('Unknown streamed-model policy: %s' % policy)
        per = ({'chunk_extra': {cell: streamed_chunk_bytes(rows, id1, sizes)}} if policy == 'chunk' else
               {'chunk_models': {cell: streamed_chunk_models(rows, id1, sizes)}})
        report = ring_peak(one, sizes, zone_kib if zone_kib is not None else memory['zone_kib'],
                           pool_kib if pool_kib is not None else memory['pool_kib'], zone_bytes={cell: zone}, **per)
        frame = report['frames'][0]
        frame.update(map=path.name, heap_mb=memory['heap_mb'], before_zone_bytes=before, after_zone_bytes=after,
                     whole_map_zone_bytes=zone, streamed_models=policy,
                     actor_cache=actor_cache(id1, rows, sizes, memory['gap_bytes']))
        out[path.stem] = frame
    return out


def require_frame_map_heap(world_dir, id1, sdk=None, sizes=None, heap_mb=None, report_path=None):
    """The image step's CHIM heap gate per frame map (frame_map_heap): report_path (JSON), and a
    ValueError naming the first frame map whose gated ring does not fit its whole-map zone."""
    import json
    from pathlib import Path
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]
        maps = frame_map_heap(world_dir, id1, sizes, heap_mb)
        report = {'maps': maps, 'ok': all(m['ok'] for m in maps.values()),
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


def require_heap(out, sdk=None, sizes=None, report_path=None, zone_kib=None, pool_kib=None, jobs=1, cache_dir=None):
    """The build's CHIM heap gate: OUT/chim-heap.json, and a ValueError naming the frame whose largest
    ring does not fit. sizes: the target ABI sizes (default: probed with the SDK's compiler, as the
    strict world-map heap gate does). Without either the gate is recorded as not run. jobs and
    cache_dir: ring_peak's (frames in parallel, each frame's result kept by its content key)."""
    import json
    from pathlib import Path
    from chim.validate import Failures, load_world
    report_path = Path(report_path or Path(out) / 'chim-heap.json')
    if sizes is None and sdk is None:
        report = {'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}
    else:
        if sizes is None:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(sdk)[0]       # (sizes, probe receipt)
        fails = Failures()
        settings, files, disk, textures, models, frames = load_world(out, fails)
        if fails:
            raise ValueError('CHIM heap gate: the world does not read back (%s)' % fails[0])
        report = ring_peak({'settings': settings, 'textures': textures, 'models': models, 'frames': frames},
                           sizes, zone_kib, pool_kib, jobs=jobs, cache_dir=cache_dir)
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
        f = bad[0]
        zone_kib, pool_kib = report['zone_kib'], report['pool_kib']
        raise ValueError('CHIM heap gate failed: %s needs %d bytes at %s, the zone holds %d (%d KiB zone '
                         'minus %d x %d KiB frame-world slots); see %s'
                         % (f['frame'], f['peak_bytes'], f['peak_position'], f['budget_bytes'], zone_kib, POOL_SLOTS,
                            pool_kib, report_path))
    return report
