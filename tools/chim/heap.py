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


def ring_peak(world, sizes, zone_kib=None, pool_kib=None, sample=SAMPLE, points=(), zone_bytes=None,
              chunk_extra=None, chunk_models=None):
    """Per frame: the largest active ring (bytes) over player positions on a grid, against the zone
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
        uses_model = np.zeros((n, len(models)), np.int32)
        uses_tex = np.zeros((n, len(tex_size)), np.int32)
        uses_s = np.zeros((n, len(snames)), np.int32)
        lo = np.zeros((n, 2))
        for k, c in enumerate(chunks):
            lumps = F.read_brush_image(c['image'])
            records = c['owned'] + c['reach']
            own[k] = (image_bytes(lumps, sizes) + sizes['hunk']
                      + _a16(len(records) * (entry + sizes['pointer'])) + extra.get(c['index'], 0))
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
        for start in range(0, len(P), 512):
            p = P[start:start + 512]
            total, active, need_m, need_t = rings(p)
            totals.append(total)
            k = int(np.argmax(total))
            if best is None or total[k] > best[0]:
                best = (float(total[k]), p[k], int(active[k].sum()), int(need_m[k].sum()), int(need_t[k].sum()))
            ltotal, lactive, lneed_m, _ = rings(p, load_radius)
            load_totals.append(ltotal)
            k = int(np.argmax(ltotal))
            if load_best is None or ltotal[k] > load_best[0]:
                load_best = (float(ltotal[k]), p[k])
            # the largest single block any ring needs (a model or a chunk's terrain): it needs one free run
            if lneed_m.any():
                largest = max(largest, float((lneed_m * model_size[None, :]).max()))
        largest = max(largest, float(own.max()) if len(own) else 0.0)
        total, where, nchunks, nmodels, ntex = best
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
        frames.append({'frame': path, 'points': at, 'median_bytes': int(np.median(totals)),
                       'positions_over_budget': int((totals > budget).sum()), 'peak_bytes': int(total),
                       'peak_position': [round(float(v), 1) for v in where],
                       'ring_chunks': nchunks, 'ring_models': nmodels, 'ring_textures': ntex,
                       'budget_bytes': budget, 'headroom_bytes': budget - int(total),
                       'load_ring': load, 'largest_block_bytes': int(largest),
                       'gated_ring': gate_ring, 'ok': gated <= budget, 'positions': int(len(P)),
                       'zone_bytes': int(zone), 'streamed_bytes': int(sum(extra.values()) + ssize.sum())})
    return {'zone_kib': zone_kib, 'pool_kib': pool_kib, 'pool_slots': POOL_SLOTS, 'sample_units': sample,
            'active_radius': radius, 'load_radius': load_radius, 'gated_ring': gate_ring,
            'method': 'engine active ring (chunk boxes within view distance + hysteresis of the player) at '
                      'positions every %g units; blocks sized as AW_BrushBound with the target ABI' % sample,
            'frames': frames, 'ok': all(f['ok'] for f in frames)}


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
                     whole_map_zone_bytes=zone, streamed_models=policy)
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


def require_heap(out, sdk=None, sizes=None, report_path=None, zone_kib=None, pool_kib=None):
    """The build's CHIM heap gate: OUT/chim-heap.json, and a ValueError naming the frame whose largest
    ring does not fit. sizes: the target ABI sizes (default: probed with the SDK's compiler, as the
    strict world-map heap gate does). Without either the gate is recorded as not run."""
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
                           sizes, zone_kib, pool_kib)
        report['status'] = 'passed' if report['ok'] else 'failed'
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    bad = [f for f in report.get('frames', []) if not f['ok']]
    if bad:
        f = bad[0]
        zone_kib, pool_kib = report['zone_kib'], report['pool_kib']
        raise ValueError('CHIM heap gate failed: %s needs %d bytes at %s, the zone holds %d (%d KiB zone '
                         'minus %d x %d KiB frame-world slots); see %s'
                         % (f['frame'], f['peak_bytes'], f['peak_position'], f['budget_bytes'], zone_kib, POOL_SLOTS,
                            pool_kib, report_path))
    return report
