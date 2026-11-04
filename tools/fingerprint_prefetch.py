"""Stage source selections in worker processes (BUILD-REUSE-CHECK-ONE-CORE-59; tools/build_cache.py fingerprint_steps).

The build's reuse check spent 4-5 minutes on one of 24 cores, almost all of it working out each stage script's source
selection (build_cache.SourceIndex.selection and previous_selections), one stage after another. prefetch_selections
works them out in forked worker processes and keeps them in the index, so stage_components reads them; every result
is the same function of the same files as the serial path (tests/test_build_cache_prefetch.py compares both).

OPT-IN (AMIWIND_FINGERPRINT_JOBS=N): measured 2026-11-04 on the v0.0.59 release run at --cpus 4 (busy host), the
serial path 143.0 s, 4 workers 153.6 s, 16 workers 208.5 s: each worker parses the shared modules again, and that
parsing is most of the work. The default stays serial until the shared parse is done once before the fork.
"""
import os
from pathlib import Path
import time

PREFETCH_ENV = 'AMIWIND_FINGERPRINT_JOBS'   # worker processes for the stage source selections (unset or 1 = serial)
_INDEX = None


def _one(script):
    index = _INDEX
    selected = index.selection(script)
    previous = index.previous_selections(script) if not selected[1] and index.top_format != 1 else None
    return str(script), selected, previous


def _share(scripts):
    # one worker keeps its parsed modules and closures across its share of the scripts
    return [_one(script) for script in scripts]


def usable_cores():
    """Cores this process may use: the CPU affinity, capped by a cgroup v2 CPU quota (docker --cpus)."""
    cores = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    try:
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()[:2]
        if quota != 'max':
            cores = min(cores, max(1, int(int(quota) / int(period))))
    except (OSError, ValueError):
        pass
    return cores


def prefetch_selections(index, scripts, workers=None, log=None):
    """Work out SCRIPTS' selections in WORKERS forked processes (default: AMIWIND_FINGERPRINT_JOBS, else serial) and
    keep them in INDEX (index._prefetched, read by SourceIndex.selection / previous_selections, forgotten by
    refresh). Returns the number of scripts done (0 = nothing done here, the serial path computes them)."""
    global _INDEX
    scripts = sorted({str(Path(s).resolve()) for s in scripts})
    if workers is None:
        try:
            workers = int(os.environ.get(PREFETCH_ENV) or 1)
        except ValueError:
            workers = 1
    workers = min(workers, len(scripts))
    if workers < 2:
        return 0
    import multiprocessing
    try:
        context = multiprocessing.get_context('fork')
    except ValueError:   # no fork (Windows): the serial path
        return 0
    began = time.monotonic()
    _INDEX = index
    memo = index.__dict__.setdefault('_prefetched', {})
    try:
        shares = [scripts[i::workers] for i in range(workers)]   # interleaved: similar mixes per worker
        with context.Pool(workers) as pool:
            for done in pool.imap_unordered(_share, shares):
                for script, selected, previous in done:
                    memo[('selection', script, index.top_format)] = selected
                    if previous is not None:
                        memo[('previous', script, index.top_format)] = previous
    finally:
        _INDEX = None
    (log or print)('Stage fingerprints: source selections of %d stage scripts in %d worker processes, %.1f s'
                   % (len(scripts), workers, time.monotonic() - began))
    return len(scripts)
