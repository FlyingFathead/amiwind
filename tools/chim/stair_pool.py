# SPDX-License-Identifier: GPL-3.0-only
"""How many stair walk workers fit, and the worker that keeps to its memory share (CHIM-STAIR-GATE-POOL-BROKEN-42).

Kept apart from chim.collision: the walker's code (chim.collision.STAIR_WALK_CODE) keys every stored frame walk, and
how many workers walk at once, or which frames a worker keeps built, never changes a walk's rows.
"""
from pathlib import Path

# A walk worker's memory (CHIM-STAIR-GATE-POOL-BROKEN-42): measured high-water marks of one worker that read a frame
# (scenes and polygons) and counted its cores, against the frame's placed bytes (its chunks' images plus the model
# image of every placement it owns), v0.0.41 world and the v0.0.42 Vivec frame: 11 MiB placed -> 259 MiB, 18 -> 393,
# 28 -> 548, 150 (whole-city Vivec, 7,643 placements) -> 2,643 MiB. About 100 MiB + 17 x placed; taken with a margin.
WORKER_BASE_MIB = 128
WORKER_MIB_PER_PLACED_MIB = 18
MEMORY_HEADROOM = 0.8           # of the memory left in the container: the rest for the gate's own process and slack


def frame_walk_mib(frame_row, models):
    """Estimated peak memory (MiB) of a walk worker reading FRAME_ROW: WORKER_BASE_MIB + WORKER_MIB_PER_PLACED_MIB x
    its placed bytes (chunk images and the model image of each owned placement; models None: the chunks only)."""
    placed = 0
    for c in frame_row[2]:
        image = c.get('image')
        placed += len(image) if isinstance(image, (bytes, bytearray)) else 0
        for r in c.get('owned') or ():
            m = r.get('model')
            try:
                image = models[m]['image'] if models is not None else None
            except (KeyError, IndexError, TypeError):
                image = None
            placed += len(image) if isinstance(image, (bytes, bytearray)) else 0
    return WORKER_BASE_MIB + WORKER_MIB_PER_PLACED_MIB * placed / float(1 << 20)


def _read_int(path):
    try:
        text = Path(path).read_text().strip()
    except OSError:
        return None
    return None if text in ('', 'max') else int(text)


def _inactive_file(path):
    try:
        for line in Path(path).read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in ('inactive_file', 'total_inactive_file'):
                return int(parts[1])
    except (OSError, ValueError):
        pass
    return 0


def memory_room():
    """(bytes a stage may still use, note): the container's own memory limit minus what it uses now (cgroup v2
    memory.max and memory.current, else cgroup v1), else the host's MemAvailable. The workers of the stair gate are
    sized by it, never by the host's total (other containers run beside a build)."""
    for limit_path, used_path, stat_path, name in (
            ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory.stat', 'cgroup v2'),
            ('/sys/fs/cgroup/memory/memory.limit_in_bytes', '/sys/fs/cgroup/memory/memory.usage_in_bytes',
             '/sys/fs/cgroup/memory/memory.stat', 'cgroup v1')):
        limit, used = _read_int(limit_path), _read_int(used_path)
        if limit is not None and used is not None and limit < (1 << 50):
            # the reclaimable file cache is not in use (BUILD-CHIM-SERIAL-SECTIONS-44: counted as used it shrank the
            # stair gate's pool); the same reading as the scheduler's memory guard (resource_plan.cgroup_memory)
            cache = _inactive_file(stat_path)
            used = max(0, used - cache)
            return max(0, limit - used), '%s limit %.1f GiB, in use %.1f GiB besides %.1f GiB file cache' % (
                name, limit / 2.0 ** 30, used / 2.0 ** 30, cache / 2.0 ** 30)
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                free = int(line.split()[1]) * 1024
                return free, 'no container limit; host MemAvailable %.1f GiB' % (free / 2.0 ** 30)
    except (OSError, ValueError):
        pass
    return None, 'memory unknown'


def memory_workers(workers, per_worker_mib, room=None):
    """(workers, note): at most WORKERS, and no more than MEMORY_HEADROOM of the memory room holds at
    PER_WORKER_MIB each (at least one)."""
    free, note = memory_room() if room is None else room
    if free is None:
        return workers, 'memory unknown: %d workers by cores' % workers
    fit = max(1, int(free * MEMORY_HEADROOM / (per_worker_mib * float(1 << 20))))
    if fit >= workers:
        return workers, '%d workers by cores (memory fits %d at about %.0f MiB each; %s)' % (
            workers, fit, per_worker_mib, note)
    return fit, '%d workers by memory (cores allow %d; about %.0f MiB each; %s)' % (fit, workers, per_worker_mib, note)


def _hwm_mib():
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmHWM:'):
                return int(line.split()[1]) / 1024.0
    except (OSError, ValueError):
        pass
    return None


_CACHE_MIB = {}


def stair_unit_sized(task):
    """Worker: stair_unit on (unit task, frame MiB, worker MiB): the frames this worker keeps built (_STAIR_CACHE) are
    let go, oldest first, until the unit's frame fits beside them in the worker's memory share (worker MiB), so a
    worker never holds more than the largest frame it walks. Returns (unit id, rows, the worker's peak MiB)."""
    from chim.collision import _STAIR_CACHE, stair_unit
    unit, mib, cap = task
    key = (str(unit[0]), unit[1])
    if key not in _STAIR_CACHE:
        while _STAIR_CACHE and sum(_CACHE_MIB.get(k, 0.) for k in _STAIR_CACHE) + mib > cap:
            gone = next(iter(_STAIR_CACHE))
            _STAIR_CACHE.pop(gone)
            _CACHE_MIB.pop(gone, None)
        import gc
        gc.collect()
    _CACHE_MIB[key] = mib
    uid, rows = stair_unit(unit)
    return uid, rows, _hwm_mib()


def memory_killed():
    """The container's out-of-memory kills so far (cgroup v2 memory.events oom_kill), or None."""
    try:
        for line in Path('/sys/fs/cgroup/memory.events').read_text().splitlines():
            if line.startswith('oom_kill '):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None
