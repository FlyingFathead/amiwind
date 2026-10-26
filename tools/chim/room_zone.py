# SPDX-License-Identifier: GPL-3.0-only
"""A CHIM room's load through the engine's own zone allocator (ROOM-AKULAKHAN-HEAP-52).

The room heap gate (chim/heap.py room_map_heap) adds up what a room map loads. The engine's zone never moves a
block, and a room's models are each one block in one bank: a room that fits by the sum can still fail when its large
models do not pack into the banks it has. This walk loads the room as the engine does, with the engine's allocator
(engine/aga/src/chim/chim_zone.c compiled for the host, chim/zone_sim.py):

- the banks in the engine's order: the automatic cache bank (persistent: models and textures prefer it,
  chim_zone.c AllocIn), then the map's zone (chim_world.c MapBeginWork);
- the prefetch table locked in the cache bank (chim_prefetch.c, taken on the first exterior frame and kept), the
  loading buffer and the store index (in the cache bank when there is one, chim_world.c ReadIndex);
- the room (chim_room.c RoomLoad): its record block, then every model of the record in its order, each followed by
  those of its textures not yet loaded (chim_models.c Begin and ResolveTexture), each locked;
- a try that finds the zone full lets go of what it loaded (its models evicted, their textures kept) and the room
  grows by the next step of chim_world.c Chim_RoomGrow (a bank of the free Fast RAM, then the Hunk's rest), then
  loads again (chim_room.c ChimRoom_Begin).

The host's block header is larger than the target's 32 bytes, so the walk is slightly pessimistic.
"""
from pathlib import Path

_LIB = {}


def library():
    """The engine's zone allocator for the host (compiled once per process, chim/zone_sim.py build_library), in the
    build's scratch folder (build_scratch: never /tmp, often mounted noexec, CHIM-ZONE-TMP-NOEXEC-33), removed when
    the process ends."""
    if 'path' not in _LIB:
        import atexit
        import shutil
        import tempfile
        from build_scratch import scratch_root
        from chim.zone_sim import build_library
        root = scratch_root()
        root.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix='amiwind-room-zone-', dir=str(root)))
        atexit.register(shutil.rmtree, str(folder), True)
        _LIB['path'] = build_library(folder)
    return _LIB['path']


def walk(blocks, bank_bytes, zone_bytes, steps, ends, lib=None):
    """Load one room (blocks: chim.heap.room_blocks, request sizes without the block header) into a cache bank of
    BANK_BYTES (0: none) and a zone of ZONE_BYTES, growing by STEPS ([(name, bytes)], in order; 0 bytes: the step takes
    nothing and the next is tried, as Chim_RoomGrow does) when a try finds the zone full; ENDS: chim_zone_ends in bytes.
    Returns {'ok', 'untextured' (textures that found no room after every step: drawn untextured), 'grown' (the steps
    taken), 'tries', 'failed' (what did not fit when not ok), 'free_bytes', 'largest_free_bytes'}."""
    from chim.zone_sim import Stats, Zone
    import ctypes
    z = Zone(lib or library(), None, ends)
    if bank_bytes and z.add_bank(bank_bytes, 1) < 0:
        raise RuntimeError('room walk: cache bank refused')
    if z.add_bank(zone_bytes, 0) < 0:
        raise RuntimeError('room walk: zone bank refused')
    models, textures, model_tex = {}, {}, {}

    def model_evicted(data, ident):
        models.pop(ident, None)
        for t in model_tex.pop(data, []):
            z.unlock(t)

    def texture_evicted(data, ident):
        textures.pop(ident, None)

    z.on_evict('model', model_evicted)
    z.on_evict('texture', texture_evicted)
    for kind in ('chunk', 'terrain', 'index', 'buffer'):     # an earlier walker's callbacks never run here
        z.on_evict(kind, lambda data, ident: None)
    # what the map holds before its room: the prefetch table (kept from the exterior), the buffer, the index
    if bank_bytes:
        p = z.alloc_persistent(blocks['prefetch_table'], 'index', 0x7f00)
        if not p:
            return {'ok': False, 'failed': 'the prefetch table', 'tries': 0, 'grown': [], 'untextured': 0}
        z.lock(p)
    for what, size, persistent in (('buffer', blocks['buffer'], False), ('index', blocks['index'], bool(bank_bytes))):
        p = (z.alloc_persistent(size, what, 0) if persistent else None) or z.alloc(size, what, 0)
        if not p:
            return {'ok': False, 'failed': 'the ' + ('loading buffer' if what == 'buffer' else 'store index'),
                    'tries': 0, 'grown': [], 'untextured': 0}
        z.lock(p)
    steps = list(steps)
    grown, tries, settle = [], 0, False
    while True:
        tries += 1
        before = z.failures()
        loaded, record, failed, untextured = [], None, None, 0
        record = z.alloc(blocks['record'], 'chunk', 0x7f10)
        if record:
            z.lock(record)
            for ident, size, refs in blocks['models']:
                p = models.get(ident)
                if p is None:
                    p = z.alloc(size, 'model', ident)
                    if not p:
                        failed = 'model %d (%d bytes)' % (ident, size)
                        break
                    z.lock(p)              # Begin: locked while it loads
                    models[ident] = p
                    for t in refs:
                        tp = textures.get(t)
                        if tp is None:
                            tp = z.alloc(blocks['textures'][t], 'texture', t)
                            if not tp:
                                untextured += 1        # ResolveTexture: drawn untextured
                                continue
                            textures[t] = tp
                        z.touch(tp)
                        z.lock(tp)
                        model_tex.setdefault(p, []).append(tp)
                    z.unlock(p)            # Finish
                z.lock(p)                  # the room keeps it locked
                loaded.append(p)
        else:
            failed = 'the room record (%d bytes)' % blocks['record']
        full = z.failures() != before
        ok = failed is None
        if ok and (not full or settle):
            s = Stats()
            z.lib.ChimZone_Stats(ctypes.byref(s))
            return {'ok': True, 'untextured': untextured, 'grown': grown, 'tries': tries, 'failed': None,
                    'free_bytes': int(s.free_bytes), 'largest_free_bytes': int(s.largest_free)}
        if not full or settle:
            break
        # ChimRoom_End, then the models of this try go (their textures stay cached)
        for p in loaded:
            z.unlock(p)
        if record:
            z.unlock(record)
            z.free(record)
        z.evict_kind('model')
        while steps:
            name, size = steps.pop(0)
            if size and z.add_bank(size, 0) >= 0:
                grown.append(name)
                break
        else:
            if not ok:
                break
            settle = True
    return {'ok': False, 'untextured': untextured, 'grown': grown, 'tries': tries,
            'failed': failed or '%d textures' % untextured, 'free_bytes': 0, 'largest_free_bytes': 0}
