"""Bounded, ordered process work and dependency-aware build scheduling."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from build_jobs import resolve_jobs
import build_profile
from build_scratch import stage_environment

# One numerical-library thread per worker prevents N workers each starting N
# BLAS/OpenMP threads. Native make and map tools use their explicit job budget.
THREAD_LIMITS = {name: '1' for name in (
    'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
    'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}


# Scheduler allowance: a running stage's Python pools follow the share the
# scheduler writes to this file (BUILD-SCHEDULER-JOBSHARE-32).
ALLOWANCE_ENV = 'AMIWIND_BUILD_JOBS_FILE'
BUDGET_ENV = 'AMIWIND_BUILD_BUDGET'


@contextmanager
def worker_environment():
    previous = {key: os.environ.get(key) for key in THREAD_LIMITS}
    os.environ.update(THREAD_LIMITS)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _pool_worker_init():
    """A pool worker is one of its stage's workers, not the stage: pools a worker
    opens must not follow the stage's allowance (BUILD-NESTED-POOL-ALLOWANCE-33).
    Without the allowance a nested ordered_map(f, items, 1) stays serial and an
    explicit share stays that share, so outer x inner keeps to the budget."""
    os.environ.pop(ALLOWANCE_ENV, None)
    os.environ.pop(BUDGET_ENV, None)
    # A spawned worker inherits the caller's sys.path; when tools/ comes before src/ there,
    # `import mwad` finds the tools/mwad.py launcher instead of the mwad package and the
    # worker dies unpickling its task (TEST-WORKER-SYSPATH-32). The package always wins.
    src = Path(__file__).resolve().parents[1] / 'src'

    def same(entry):
        try:
            return Path(entry or '.').resolve() == src
        except OSError:
            return False
    sys.path[:] = [str(src)] + [entry for entry in sys.path if not same(entry)]


def process_pool(count):
    """The one worker-pool factory of the builder (tests record its size).

    Spawn avoids inherited archive handles and numerical-library thread state.
    """
    return ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context('spawn'),
                               initializer=_pool_worker_init)


# Pool modes of a stage (BUILD-CHIM-STAGE-SERIAL-TAIL-36): 'stage' (default) keeps ONE worker pool for the whole
# stage (stage_pool), so every ordered_map / completed_map of the stage submits to the same warm workers;
# 'batch' (the method before v0.0.42) starts a pool for every map and stops it at the map's end.
POOL_MODES = ('stage', 'batch')
_STAGE = None


class StagePool:
    """The worker pool of one stage, kept from the stage's start to its end (stage_pool).

    One process_pool of `size` workers (the stage's budget under the scheduler) serves every map of the stage;
    each map still keeps to its own in-flight limit (its jobs, or the stage's live allowance). The pool starts
    again only when it must: a map needs more workers than it has, a worker died (broken pool), or the
    environment changed since it started (workers are spawned with the environment of that moment, e.g. a
    variable the CHIM hull fallback sets between two world builds); each restart is printed with its reason."""

    def __init__(self, size, label):
        self.size, self.label = size, label
        self.pid = os.getpid()
        self.executor = self.env = None
        self.capacity = 0
        self.starts, self.maps, self.tasks = 0, 0, 0
        self.restarts = []

    def executor_for(self, size):
        env = dict(os.environ)
        if self.executor is not None:
            reason = None
            if size > self.capacity:
                reason = 'a map needs %d workers, the pool has %d' % (size, self.capacity)
            elif getattr(self.executor, '_broken', False):
                reason = 'a worker died (broken pool)'
            elif env != self.env:
                changed = sorted(k for k in set(env) | set(self.env) if env.get(k) != self.env.get(k))
                reason = 'environment changed: %s' % ', '.join(changed[:5])
            if reason:
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.executor = None
                self.restarts.append(reason)
                print('[pool] %s: worker pool started again (%s)' % (self.label, reason), flush=True)
        if self.executor is None:
            self.capacity = max(size, self.size)
            self.executor = process_pool(self.capacity)
            self.env = env
            self.starts += 1
        self.maps += 1
        return self.executor

    def recycle(self, reason):
        """Stop the workers at a phase boundary (the next map starts fresh ones), e.g. after a phase whose
        workers grew large: one restart, printed with its reason, instead of one per map."""
        if self.executor is not None:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.executor = None
            self.restarts.append(reason)
            print('[pool] %s: workers stopped (%s); the next map starts fresh ones' % (self.label, reason), flush=True)

    def summary(self):
        return {'mode': 'stage', 'workers': self.capacity or self.size, 'pool_starts': self.starts,
                'maps': self.maps, 'tasks': self.tasks, 'restarts': list(self.restarts)}

    def close(self):
        if self.executor is not None:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.executor = None


def active_stage_pool():
    """The stage pool of this process (stage_pool), or None: in a pool worker, in a forked child of the stage
    and outside a stage_pool block it is None, and maps start their own pool as before."""
    stage = _STAGE
    return stage if stage is not None and stage.pid == os.getpid() else None


@contextmanager
def stage_pool(jobs=None, label='stage', mode='stage'):
    """One worker pool for every map of the block (mode 'stage', the default), or none (mode 'batch': each map
    starts and stops its own pool, the method before v0.0.42). Sized as a map of `jobs` workers is: the
    stage's budget under the scheduler (the pool follows its live allowance), else `jobs`. A block inside
    another uses the outer pool. Yields the StagePool or None; at the end prints one line with how often the
    pool started and how many maps and tasks it served."""
    global _STAGE
    if mode not in POOL_MODES:
        raise ValueError('Unknown pool mode %r (choose %s)' % (mode, ' or '.join(POOL_MODES)))
    if mode == 'batch' or active_stage_pool() is not None:
        yield active_stage_pool()
        return
    count = resolve_jobs(jobs)
    size = _throttle(count)[0]
    if size <= 1:
        yield None
        return
    pool = StagePool(size, label)
    _STAGE = pool
    try:
        with worker_environment():
            yield pool
    finally:
        _STAGE = None
        pool.close()
        s = pool.summary()
        print('[pool] %s: one worker pool of %d workers for the whole step: started %d time(s), %d maps, %d tasks%s'
              % (label, s['workers'], s['pool_starts'], s['maps'], s['tasks'],
                 ' (started again: %s)' % '; '.join(s['restarts']) if s['restarts'] else ''), flush=True)


@contextmanager
def _map_pool(size):
    """The executor of one map: the stage pool when one is active (kept running after the map), else a pool of
    `size` workers of its own, stopped at the map's end (the batch method)."""
    stage = active_stage_pool()
    if stage is not None:
        yield stage.executor_for(size)
        return
    with process_pool(size) as pool:
        yield pool


def _count_task():
    stage = active_stage_pool()
    if stage is not None:
        stage.tasks += 1


class Background:
    """One call run beside the caller in a spawned worker (process_pool(1)); result() waits for it.

    For work a stage needs only at its end and that reads nothing the stage writes, such as
    the door catalogue of the game's master file (prepare_doors.door_sources). With one job
    the call runs in the caller when result() first asks for it, as before."""

    def __init__(self, function, *args, jobs=None):
        self._call = (function, args)
        self._pool = self._future = None
        if resolve_jobs(jobs) > 1:
            with worker_environment():
                self._pool = process_pool(1)
                self._future = self._pool.submit(function, *args)

    def result(self):
        try:
            if self._future is None:
                return self._call[0](*self._call[1])
            return self._future.result()
        finally:
            if self._pool is not None:
                self._pool.shutdown(wait=True)
                self._pool = None


def sha256_file(path):
    """Worker: SHA-256 hex digest of one file."""
    import hashlib
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 22), b''):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files(paths, jobs=None):
    """SHA-256 of every path, in input order, hashed by up to `jobs` workers.

    Threads of this process (tools/parallel_hash.py: size batches, largest first; reading and hashing
    release the interpreter lock), the default since BUILD-IMAGE-HASH-UNDERUSED-36. The earlier method,
    one spawned-process task per file, stays selectable: AMIWIND_HASH_METHOD=process. Same digests."""
    paths = list(paths)
    if os.environ.get('AMIWIND_HASH_METHOD') == 'process':
        return list(ordered_map(sha256_file, paths, max(1, min(resolve_jobs(jobs), len(paths) or 1))))
    import parallel_hash
    return parallel_hash.hash_files(paths, live_jobs(resolve_jobs(jobs)))


def _sha256_existing(path):
    return sha256_file(path) if os.path.isfile(path) else None


def hash_existing(paths, jobs=None):
    """Like hash_files, with None for a path that is not a regular file (same methods)."""
    paths = [str(p) for p in paths]
    if os.environ.get('AMIWIND_HASH_METHOD') == 'process':
        return list(ordered_map(_sha256_existing, paths, max(1, min(resolve_jobs(jobs), len(paths) or 1))))
    import parallel_hash
    return parallel_hash.hash_existing(paths, live_jobs(resolve_jobs(jobs)))


def keep_original(path, backup, raw):
    """Keep a staged file's current bytes at `backup` before it is replaced.

    A hard link when possible (same file system): the pass then replaces the
    staged file by renaming its candidate over it, so the linked inode keeps
    the original bytes without writing them again. Callers must replace, never
    rewrite in place, a file they backed up this way. Otherwise a copy of `raw`.
    """
    try:
        os.link(path, backup)
    except OSError:
        Path(backup).write_bytes(raw)


def captured(function, *args):
    """Run function(*args) with this process's stdout and stderr (file descriptors 1
    and 2, so tool subprocesses too) going to a temporary file.

    Returns (result, output text). A pool worker uses it so the caller can print
    each item's output in item order, keeping a stage log readable and in the
    serial order. On an error the output is written to stderr before re-raising.
    """
    import sys
    from build_scratch import scratch_file
    for stream in (sys.stdout, sys.stderr):
        stream.flush()
    with scratch_file() as sink:
        saved = [os.dup(1), os.dup(2)]
        failed = True
        try:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            result = function(*args)
            failed = False
        finally:
            for stream in (sys.stdout, sys.stderr):
                stream.flush()
            os.dup2(saved[0], 1)
            os.dup2(saved[1], 2)
            for fd in saved:
                os.close(fd)
            sink.seek(0)
            text = sink.read().decode('utf-8', errors='replace')
            if failed and text:
                sys.stderr.write(text)
                sys.stderr.flush()
    return result, text


def _copy(task):
    import shutil
    shutil.copyfile(*task)


def copy_files(pairs, jobs=None):
    """Copy (source, destination) pairs with up to `jobs` workers (independent files)."""
    pairs = [(str(a), str(b)) for a, b in pairs]
    for _ in ordered_map(_copy, pairs, max(1, min(resolve_jobs(jobs), len(pairs) or 1))):
        pass


def live_jobs(jobs):
    """The workers this stage holds now: under the scheduler its allowance file
    (the share grows when other stages finish), otherwise `jobs` unchanged.

    For choices taken when a pass starts rather than per pool task: map tool
    threads and whether a pass runs serially at all. Pool workers do not see the
    allowance (BUILD-NESTED-POOL-ALLOWANCE-33), so inside them this is `jobs`.
    """
    path = os.environ.get(ALLOWANCE_ENV)
    if not path:
        return jobs
    try:
        return max(1, int(Path(path).read_text().strip()))
    except (OSError, ValueError):
        return jobs


def stage_ceiling(jobs):
    """The most workers a pool of this stage may grow to: under the scheduler the build budget (its live allowance
    file decides how many it holds at each task, _throttle), never less than JOBS; outside it JOBS (resolve_jobs).
    For a stage's own sizing that is taken once (how many walk units to cut, how many workers memory admits): the
    launch --jobs is only the scheduler's share at the moment the stage started (BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42:
    the v0.0.42 final's stair gate stayed on the 2 workers of its launch while its allowance was 12)."""
    count = resolve_jobs(jobs)
    if not os.environ.get(ALLOWANCE_ENV):
        return count
    try:
        return max(count, int(os.environ.get(BUDGET_ENV, count)))
    except ValueError:
        return count


def _throttle(count):
    """(pool size, in-flight limit function or None) for a pool of `count` workers.

    Outside the scheduler, or when the caller capped `count` below the stage's
    assigned workers (fewer items), the limit is that count. Under the
    scheduler the limit follows the stage's allowance file, so a stage shrinks
    when another stage starts and grows (up to the build budget) when workers
    free up; the pool is sized for the budget and starts workers on demand.
    """
    path = os.environ.get(ALLOWANCE_ENV)
    if not path:
        return count, None
    try:
        assigned = int(os.environ.get('AMIWIND_BUILD_JOBS', count))
        ceiling = max(count, int(os.environ.get(BUDGET_ENV, count)))
    except ValueError:
        return count, None
    capped = count < assigned
    cache = {'at': 0.0, 'value': assigned}

    def limit():
        now = time.monotonic()
        if now - cache['at'] >= .5:
            cache['at'] = now
            try:
                cache['value'] = max(1, int(Path(path).read_text().strip()))
            except (OSError, ValueError):
                pass
        return min(cache['value'], count) if capped else min(cache['value'], ceiling)
    return (count if capped else ceiling), limit


def _running(futures):
    return sum(not future.done() for future in futures)


def _grow_seconds():
    """How long a pool under the scheduler waits for a finished unit before it reads its allowance again: a raised
    allowance (another stage finished) starts more units within this time, never only at the next finish
    (BUILD-CHIM-SERIAL-SECTIONS-44). A function, not a module constant: scheduling only, it is one of the build
    cache's SCHEDULING_UNITS and keys no stage."""
    return 1.0

# Results an ordered map may hold ahead of the one it hands back next, per worker:
# with only two, one slow item at the head left the others idle (world terrain
# ran at 14 of 24 cores; simulated on its 2,532 region times: 994 s with two,
# 921 s with four, 919 s ideal; BUILD-ORDERED-WINDOW-33).
WINDOW = 4


def _timed_call(function, item):
    """Worker: (seconds, result) of one item."""
    started = time.monotonic()
    result = function(item)
    return time.monotonic() - started, result


def ordered_map(function, items, jobs=None, cost=None, timings=None, history=None, key=None):
    """Yield in input order; at most the current limit running.

    Up to WINDOW times the limit are submitted and not yet handed back, so a slow
    item at the head does not idle the other workers. `cost` (item -> number):
    every item is submitted largest first (ties in input order) so the long ones
    do not finish last on a few workers; results still come back in input order,
    held until their turn. `timings` (a list): the seconds each item took in its
    worker are appended in input order (item cost history, build_costs.py).
    `history` (a pool name) with `key` (item -> stable name): largest first by the
    seconds recorded for the items in earlier builds, by default whenever such a
    history exists, and this run's times recorded for the next one
    (build_costs.costed_map; BUILD-CHIM-REGION-FRAMES-TAIL-43).
    Workers return data; the caller alone writes shared archives and indices.
    Spawn avoids inherited archive handles and numerical-library thread state.
    The running map's queued and running units go to the scheduler's supervisor
    (tools/pool_status.py; status only, never the order of results).
    """
    from functools import partial
    if history is not None and cost is None:
        from build_costs import costed_map
        items = list(items)
        yield from costed_map(history, function, items, [(key or str)(item) for item in items], jobs)
        return
    import pool_status
    count = resolve_jobs(jobs)
    size, limit = _throttle(count)
    call = function if timings is None else partial(_timed_call, function)

    def deliver(result):
        if timings is None:
            return result
        seconds, value = result
        timings.append(round(seconds, 3))
        return value
    if size == 1:
        for item in items:
            yield deliver(call(item))
        return
    if cost is not None:
        items = list(items)
        order = iter(sorted(range(len(items)), key=lambda i: -cost(items[i])))
        source = ((index, items[index]) for index in order)
    else:
        source = enumerate(items)
    status = pool_status.watch(getattr(function, '__name__', 'map'), items)
    with worker_environment(), _map_pool(size) as pool:
        pending = {}
        following = 0          # next input index to hand back
        submitted = 0
        exhausted = False
        try:
            while True:
                cap = count if limit is None else limit()
                while (not exhausted and _running(pending.values()) < cap
                       and (cost is not None or submitted - following < WINDOW * cap)):
                    try:
                        index, item = next(source)
                    except StopIteration:
                        exhausted = True
                        if status:
                            status.end_of_input()
                        break
                    pending[index] = pool.submit(call, item)
                    submitted += 1
                    _count_task()
                    if status:
                        status.submit(index, item)
                        pending[index].add_done_callback(lambda _f, i=index: status.finish(i))
                if following in pending and pending[following].done():
                    yield deliver(pending.pop(following).result())
                    following += 1
                    continue
                if not pending:
                    return
                if following in pending and (exhausted or cost is None and submitted - following >= WINDOW * cap):
                    # Nothing more may be submitted: wait for the head itself.
                    yield deliver(pending.pop(following).result())
                    following += 1
                    continue
                wait([f for f in pending.values() if not f.done()], timeout=1, return_when=FIRST_COMPLETED)
        finally:
            for future in pending.values():
                future.cancel()
            if status:
                status.close()


def _by_cost(items, cost):
    """ITEMS largest first by COST (ties in input order) as [(index, item)], or enumerate(items) without a cost."""
    if cost is None:
        return enumerate(items)
    items = list(items)
    return iter([(index, items[index]) for index in sorted(range(len(items)), key=lambda i: -cost(items[i]))])


def completed_map(function, items, jobs=None, cost=None):
    """Yield independent work as it finishes, with a bounded submission window.

    Refill freed slots before handing results to the caller. A slow early task
    must not prevent later tasks from being submitted or reported. Callers must
    restore stable key order before exporting catalogues or shared receipts.
    Existing order-dependent conversion stages continue to use ordered_map.
    `cost` (item -> number): submitted largest first (BUILD-CHIM-REGION-FRAMES-TAIL-43).
    """
    import pool_status
    count = resolve_jobs(jobs)
    size, limit = _throttle(count)
    if size == 1:
        yield from map(function, (item for _, item in _by_cost(items, cost)))
        return
    status = pool_status.watch(getattr(function, '__name__', 'map'), items)
    items = _by_cost(items, cost)
    # In a pool of its own (exactly `size` workers) two tasks per worker are kept in flight, so a worker never
    # waits for its next task. In the stage's shared pool, which may hold more workers than this map asked for,
    # every submitted task runs at once: there the map keeps to `count` tasks in flight, as it asked
    # (CHIM-STAIR-GATE-POOL-BROKEN-42: 11 walk workers asked, 22 frame walks ran at once in a 24-worker pool
    # and the container ran out of memory).
    stage = active_stage_pool()
    with worker_environment(), _map_pool(size) as pool:
        pending = set()
        window = count if stage is not None and stage.capacity > size else 2 * count

        def refill():
            while len(pending) < (window if limit is None else limit()):
                try:
                    index, item = next(items)
                except StopIteration:
                    if status:
                        status.end_of_input()
                    return
                pending.add(_submit(pool, function, index, item, status))

        try:
            refill()
            while pending:
                # under the scheduler a short wait, so a raised allowance starts more units at once, not only when a
                # unit finishes (maintainer 2026-10-19: pools follow the live allowance continuously)
                done, pending = wait(pending, timeout=None if limit is None else _grow_seconds(),
                                     return_when=FIRST_COMPLETED)
                results = [future.result() for future in done]
                refill()
                yield from results
        finally:
            for future in pending:
                future.cancel()
            if status:
                status.close()


def _submit(pool, function, index, item, status):
    """One task of a completed or governed map, counted for the stage pool and shown to the supervisor."""
    future = pool.submit(function, item)
    _count_task()
    if status:
        status.submit(index, item)
        future.add_done_callback(lambda _f: status.finish(index))
    return future


def governed_map(function, items, jobs=None, unit_mib=None, label='pool', cost=None, item_mib=None):
    """completed_map whose units in flight follow the container's memory and CPU quota while it runs
    (tools/resource_plan.py MemoryGovernor, fixlist A9): at most `jobs` (and the stage's allowance), and no more units
    of about UNIT_MIB each than the memory holds now, re-read every 30 s between tasks. A throttled map grows back
    when memory frees up (another container stopped, a raised lease) and stops handing out units when memory gets
    tight; a running unit is never stopped. Every change is printed with its reason. A new function of its own, so
    the stages that use completed_map keep their keys.

    ITEM_MIB (item -> MiB): each unit is admitted at its own size (BUILD-CHIM-SERIAL-SECTIONS-44): units start while
    the memory room holds them beside the units in flight, largest first; a larger unit at the head that does not fit
    yet keeps its room reserved, so smaller units fill only what is left over and the head starts when enough frees
    up. The count still follows the live allowance (grows when the scheduler raises it). Without ITEM_MIB every unit
    counts as UNIT_MIB (the method before v0.0.44)."""
    count = resolve_jobs(jobs)
    size, limit = _throttle(count)
    from resource_plan import governor_for
    # under the scheduler the pool is sized for the budget and follows the live allowance (_throttle): the memory
    # governor plans for that ceiling, not the launch count, or it never lets the pool grow past it
    # (BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42)
    governor = governor_for(size if limit is not None else count, unit_mib, label)
    if size == 1 or governor is None:
        yield from completed_map(function, items, jobs, **({'cost': cost} if cost is not None else {}))
        return
    import pool_status
    status = pool_status.watch(label, items)
    items = _by_cost(items, cost)
    stage = active_stage_pool()
    if item_mib is not None:
        yield from _sized_map(function, list(items), size, limit, governor, item_mib, status, stage, label)
        return
    with worker_environment(), _map_pool(size) as pool:
        pending = set()

        def refill():
            while True:
                cap = governor.limit(len(pending))
                if limit is not None:
                    cap = min(cap, limit())
                if len(pending) >= cap:
                    return
                try:
                    index, item = next(items)
                except StopIteration:
                    if status:
                        status.end_of_input()
                    return
                pending.add(_submit(pool, function, index, item, status))

        try:
            refill()
            while pending:
                # a short wait: a raised allowance or freed memory starts more units at once, not at the next finish
                done, pending = wait(pending, timeout=max(0.05, min(governor.interval, _grow_seconds())),
                                     return_when=FIRST_COMPLETED)
                results = [future.result() for future in done]
                refill()
                yield from results
        finally:
            for future in pending:
                future.cancel()
            if status:
                status.close()
    if stage is not None and governor.changes:
        print('[pool] %s: %d worker change(s) while it ran' % (label, len(governor.changes)), flush=True)


def _sized_map(function, queue, size, limit, governor, item_mib, status, stage, label):
    """governed_map with a size per unit (item_mib): QUEUE [(index, item)] largest first."""
    queue = [(index, item, float(item_mib(item))) for index, item in queue]
    if status and not queue:
        status.end_of_input()
    started = {'units': 0, 'peak': 0, 'held': 0}
    with worker_environment(), _map_pool(size) as pool:
        pending = {}

        def refill():
            while queue:
                cap = size if limit is None else min(size, limit())
                if len(pending) >= cap:
                    return
                flight = sum(pending.values())
                head = queue[0][2]
                pick = None
                for k, (_, _, mib) in enumerate(queue):
                    # the head first; a smaller unit only in the room left beside the head's reservation
                    if governor.admits(flight, mib, len(pending), 0.0 if k == 0 else head):
                        pick = k
                        break
                if pick is None:
                    started['held'] += 1
                    return
                index, item, mib = queue.pop(pick)
                pending[_submit(pool, function, index, item, status)] = mib
                started['units'] += 1
                started['peak'] = max(started['peak'], len(pending))
                if not queue and status:
                    status.end_of_input()

        try:
            refill()
            while pending:
                done, _ = wait(list(pending), timeout=max(0.05, min(governor.interval, _grow_seconds())),
                               return_when=FIRST_COMPLETED)
                results = []
                for future in done:
                    pending.pop(future)
                    results.append(future.result())
                refill()
                yield from results
        finally:
            for future in pending:
                future.cancel()
            if status:
                status.close()
    print('[pool] %s: %d units sized one by one, up to %d at once (of %d workers)%s' % (
        label, started['units'], started['peak'], size,
        '; a larger unit waited for memory %d time(s)' % started['held'] if started['held'] else ''), flush=True)


# Scene stages copy or mutate their predecessor's tree. Keep that chain ordered;
# only independent branches may overlap. Image assembly waits for every branch.
DEPENDENCIES = {
    'setup': (), 'terrain': ('setup',), 'scenery': ('terrain',),
    'scene': ('scenery',), 'bsp': ('scene',), 'npcs': ('bsp',),
    'hands': ('npcs',), 'interior': ('hands',),
    'dialogue-lookup': (), 'intro': ('interior',),
    'census': ('intro',), 'area': ('census',), 'balmora': ('area',),
    'balmora-interiors': ('balmora',), 'door-audio': ('balmora-interiors',), 'character': ('door-audio',),
    'reading': ('character',), 'opening-references': ('reading',),
    'world-survey': (), 'world-ui': ('opening-references', 'world-survey'),
    'npc-gallery': ('census',),
    'actor-contact': ('world-ui',), 'world-terrain': ('actor-contact', 'npc-gallery'),
    'world-scenery-assets': (),
    # Seam-tear gate over every mesh the static converters reduce (MESH-LOD-OPEN-SEAMS-33).
    'seam-audit': (),
    'world-scenery': ('world-terrain', 'world-scenery-assets'),
    # Census rewrites intro-scene/id1/gfx/palette.lmp (BUILD-PALETTE-RACE-32).
    'world-flora-assets': ('census',),
    'world-flora': ('world-terrain', 'world-scenery', 'world-flora-assets'),
    'hand-catalog': ('census',),
    'harvest': ('census',),
    # The CHIM world (--builder chim) reads the census palette too.
    'chim': ('census',),
    # The tracker data of the CHIM world (BUILD/toolkit), its own stage (BUILD-CHIM-KEY-UNDERDECLARED-35).
    'cell-progress': ('chim',),
    'media': (), 'music': (), 'engine': (),
    'image': ('world-terrain', 'world-scenery', 'npc-gallery', 'music', 'media', 'engine', 'dialogue-lookup'),
    'dry-run-image': ('engine',),
}


def plan_skipped(metadata):
    """Stages a quick test build leaves out on purpose (the build receipt's
    excluded_content.skipped_stages, written by tools/build.py from
    tools/build_exclusions.py). This module never imports that table: stage code
    stays free of it, so the stage fingerprints do not depend on it."""
    return set(((metadata or {}).get('excluded_content') or {}).get('skipped_stages') or ())


def stage_dependencies(steps, skipped=()):
    """{stage: (stages it waits for)}. skipped: stages the plan leaves out on purpose
    (plan_skipped); they are no one's dependency."""
    names = [name for name, _ in steps]
    commands = {name: [str(part) for part in command] for name, command in steps}
    if len(set(names)) != len(names):
        raise ValueError('Build stage names must be unique')
    result = {}
    # Extra town imports (town-<id>: shipped towns by default, --extra-town
    # towns on request) extend the ordered scene chain after Balmora's
    # interiors; the chain continues from the last of them.
    towns = [name for name in names if name.startswith('town-')]
    # An AmiWind "MiniWind" Playtester Build (its image step says --miniwind) leaves
    # stages out (tools/miniwind.py): Balmora follows the census and the image waits
    # only for the stages the plan has.
    miniwind = any(name == 'image' and '--miniwind' in map(str, command) for name, command in steps)

    def passed_on(dep):
        # A stage a MiniWind scope leaves out of the ordered scene chain (the exterior
        # scope: balmora-interiors, door-audio) passes its own predecessors on.
        if dep in names or dep not in DEPENDENCIES:
            return (dep,)
        return tuple(d for parent in DEPENDENCIES[dep] for d in passed_on(parent))
    skipped = set(skipped) - set(names)
    for index, name in enumerate(names):
        deps = DEPENDENCIES.get(name, tuple(names[index - 1:index]))
        # Quick test builds (--exclude): a stage the plan skips is no one's dependency.
        deps = tuple(d for d in deps if d not in skipped)
        if name.startswith('chim-town-'):
            # A CHIM town (tools/chim_town.py) reads the CHIM world and the census palette; Seyda Neen also reads
            # the scene chain's complete town, which the area and opening-references stages finish last.
            deps = ('chim', 'census', *(d for d in (('area', 'opening-references') if name == 'chim-town-seyda' else ())
                                        if d in names))
        # A CHIM town's legacy chain stage is not built (CHIM-LEGACY-CHAIN-33): the ordered
        # scene chain continues from its predecessor.
        deps = tuple(dict.fromkeys(d for dep in deps for d in
                                   (passed_on(dep) if dep == 'balmora' and dep not in names else (dep,))))
        if miniwind:
            # The plan's table only (pure data): stage code must not import tools/miniwind.py
            # (BUILD-MINIWIND-STAGE-CLOSURE-33).
            from miniwind_plan import DEPENDENCY_OVERRIDES, IMAGE_AFTER, omitted
            deps = DEPENDENCY_OVERRIDES.get(name, deps)
            if name == 'image':
                deps = (*(d for d in deps if not omitted(d)), *IMAGE_AFTER)
            else:
                deps = tuple(dict.fromkeys(d for dep in deps for d in passed_on(dep)))
        # An area build's reference closure (--exclude-unreferenced): its readers wait for it.
        if '--reference-closure' in commands[name] and 'reference-closure' in names:
            deps = (*deps, 'reference-closure')
        if name == 'door-audio' and towns:
            deps = (towns[-1],)
        # The sole optional branch requires an explicit builder opt-out.
        if "npc-gallery" not in names:
            deps = tuple(d for d in deps if d != "npc-gallery")
        if name == 'image' and 'world-flora' in names:
            deps = (*deps, 'world-flora')
        if name == 'image' and 'hand-catalog' in names:
            deps = (*deps, 'hand-catalog')
        if name == 'image' and 'harvest' in names:
            deps = (*deps, 'harvest')
        if name == 'image' and 'chim' in names:
            # the image installs every CHIM town's stage output and its rooms (BUILD-CHIM-ROOMS-IMAGE-RACE-36: the
            # image ran beside chim-rooms-vivec_city and read its record before it existed)
            deps = (*deps, 'chim', *(n for n in names if n.startswith(('chim-town-', 'chim-rooms-'))))
        # the CHIM world leaves out the harvest placements and adds the town flora (payload parity)
        if name == 'chim':
            deps = (*deps, *(d for d in ('harvest', 'world-flora-assets', 'world-survey') if d in names))
        if name == 'image' and 'seam-audit' in names:
            deps = (*deps, 'seam-audit')
        missing = set(deps) - set(names)
        if missing:
            raise ValueError(f'{name}: missing dependencies {sorted(missing)}')
        result[name] = deps
    return result


def budget_command(command, jobs):
    command = list(command)
    if '--jobs' in command:
        command[command.index('--jobs') + 1] = str(jobs)
    return command


def create_run(run, metadata):
    """Make the new run folder (refused when it exists: one run per name) and write the files the plan prepared
    for it before any stage (metadata '_run_files': {name: text}, e.g. world-manifest.json; never in a receipt)."""
    run.mkdir(parents=True, exist_ok=False)
    (run / 'logs').mkdir()
    for name, text in sorted(metadata.pop('_run_files', {}).items()):
        (run / name).write_text(text, encoding='utf-8', newline='\n')


def execute_parallel(steps, run, metadata, root):
    dependencies = stage_dependencies(steps, plan_skipped(metadata))
    budget = int(metadata['compiler_jobs'])
    create_run(run, metadata)
    receipt = {**metadata, 'status': 'running', 'scheduler': 'bounded-dependencies-v1',
               'worker_budget': budget, 'steps': []}
    pending = list(enumerate(steps, 1))
    active = {}
    passed = set()
    start = time.monotonic()
    heartbeat = start

    def save():
        temporary = run / 'build-state.tmp'
        temporary.write_text(json.dumps(receipt, indent=2) + '\n')
        temporary.replace(run / 'build-state.json')

    def drain(state):
        # Separate logs stay authoritative; prefixes keep concurrent output legible.
        chunk = state['reader'].read(16384)
        if chunk:
            for line in chunk.splitlines():
                print(f"[{state['entry']['name']}] {line}", flush=True)

    def stop_children():
        for state in active.values():
            process = state['process']
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM) if os.name == 'posix' else process.terminate()
                except ProcessLookupError:
                    pass
        for state in active.values():
            process = state['process']
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL) if os.name == 'posix' else process.kill()
                except ProcessLookupError:
                    pass
                process.wait()
            state['entry'].update(status='cancelled', elapsed_seconds=round(time.monotonic() - state['start'], 3))
            profile.finished(state['entry']['name'], state['entry'])
            drain(state)
            state['reader'].close()
            state['writer'].close()

    print(f'Parallel build: {budget} total workers; shared scene writes remain ordered.', flush=True)
    save()
    allowances = run / 'jobs'
    allowances.mkdir()

    def held(state):
        return state['allowance'] if state['parallel'] else 1

    def rebalance(waiting, incoming=0):
        """Share the budget again: serial stages hold one worker, running pooled
        stages split the rest evenly, leaving one worker for each ready stage
        still waiting (BUILD-SCHEDULER-JOBSHARE-32). Pools inside a stage follow
        its allowance file at their next task; tool threads keep their start value.

        `incoming` pooled stages about to start are counted in the split: the
        running stages shrink first and the shares of the incoming ones are
        returned, so a stage starts with its fair share instead of the one
        worker left free at that moment (BUILD-STAGE-START-SHARE-33: its map
        tool threads and pool decisions are taken from that start value)."""
        pooled = [s for s in active.values() if s['parallel']]
        count = len(pooled) + incoming
        if not count:
            return []
        serial = len(active) - len(pooled)
        share = max(count, guard.effective_budget() - serial - waiting)
        base, extra = divmod(share, count)
        values = [base + (1 if index < extra else 0) for index in range(count)]
        ordered = sorted(pooled, key=lambda s: s['start'])
        if not incoming:
            # the free-core checker: a stage with nothing queued keeps what it runs, the rest goes to the stages
            # with queued units (stage_watch.lend_shares, BUILD-STAGE-ALLOWANCE-STUCK-43)
            lent = lend_shares({s['entry']['name']: v for v, s in zip(values, ordered)}, watch.demand)
            values = [lent[s['entry']['name']] for s in ordered]
        for value, state in zip(values, ordered):
            state['share'] = value
            value = guard.cap(state['entry']['name'], value)   # memory guard (SchedulerGuard)
            if value != state['allowance']:
                state['allowance'] = value
                temporary = state['allowance_file'].with_suffix('.tmp')
                temporary.write_text(f'{value}\n')
                temporary.replace(state['allowance_file'])
                state['entry']['workers_now'] = value
                state['entry'].setdefault('worker_changes', []).append(
                    [round(time.monotonic() - start, 3), value])
        return values[len(pooled):]
    profile = build_profile.start(run, steps, metadata, dependencies)
    from resource_plan import SchedulerGuard   # key-neutral module (build_cache.INSTRUMENTATION_MODULES)
    guard = SchedulerGuard(budget, metadata.get('resource_plan_units'), parents=metadata.get('resource_plan_parents'))
    # live supervisor (key-neutral modules): free cores to queued work, underuse named (BUILD-STAGE-ALLOWANCE-STUCK-43)
    from stage_watch import StageWatch, lend_shares
    import build_digest
    watch = StageWatch(run)

    def digest():
        try:
            build_digest.update(run, receipt, watch, now_seconds=time.monotonic() - start)
        except Exception as exc:          # the summary never fails a build
            print('[summary] not updated: %s' % exc, flush=True)
    try:
        while pending or active:
            ready = [item for item in pending if set(dependencies[item[1][0]]) <= passed]
            pooled_now = {n: s['allowance'] for n, s in active.items() if s['parallel']}
            if pooled_now:
                guard.tick(pooled_now, {n: s.get('share', s['allowance']) for n, s in active.items() if s['parallel']})
                if watch.due():
                    watch.sample({n: (s['allowance'], s.get('share', s['allowance']))
                                  for n, s in active.items() if s['parallel']})
            rebalance(len(ready))
            for item in ready:
                number, (name, original) = item
                # Reserve a slot for each other ready branch before handing the
                # remainder to a parallel stage. Never exceed the global budget.
                others = ready[ready.index(item) + 1:]
                serial = sum('--jobs' not in command for _, (_, command) in others)
                parallel = sum('--jobs' in command for _, (_, command) in others)
                if '--jobs' in original:
                    # A pooled stage takes its even share at once: running pooled
                    # stages shrink before it starts (BUILD-STAGE-START-SHARE-33).
                    running_serial = sum(not s['parallel'] for s in active.values())
                    running_pooled = len(active) - running_serial
                    # The other ready branches get a reserved worker only while the budget has room for
                    # them: with more ready branches than workers, stages start one per free worker
                    # instead of every branch waiting for room that never comes (BUILD-SCHEDULER-LOWBUDGET-33:
                    # first nothing started, then one stage at a time). Large budgets are unchanged.
                    if len(active) + 1 > budget:
                        break
                    room = budget - len(active) - 1
                    serial, parallel = min(serial, room), min(parallel, max(0, room - min(serial, room)))
                    if budget - running_serial - serial < running_pooled + 1 + parallel:
                        break
                    jobs = rebalance(serial, 1 + parallel)[0]
                else:
                    if budget - sum(held(s) for s in active.values()) < 1:
                        break
                    jobs = 1
                if '--jobs' in original:
                    # BUILD-SCHEDULER-MEMORY-STARVED-42: say before it starts when its workers will not fit
                    guard.start_check(name, jobs, running=list(active))
                command = budget_command(original, jobs)
                log = run / 'logs' / f'{number:02}-{name}.log'
                entry = {'name': name, 'command': command, 'status': 'running',
                         'log': str(log), 'jobs': jobs, 'dependencies': list(dependencies[name]),
                         'started_seconds': round(time.monotonic() - start, 3)}
                receipt['steps'].append(entry)
                pending.remove(item)
                writer = log.open('w')
                pooled_stage = '--jobs' in original
                allowance_file = allowances / f'{number:02}-{name}'
                allowance_file.write_text(f'{jobs}\n')
                limits = {ALLOWANCE_ENV: str(allowance_file), BUDGET_ENV: str(budget)} if pooled_stage else {}
                try:
                    process = subprocess.Popen(profile.command(number, name, command, jobs), cwd=root, stdout=writer, stderr=subprocess.STDOUT,
                        env=dict(os.environ, **THREAD_LIMITS, **limits, **stage_environment(run), PYTHONUNBUFFERED='1', AMIWIND_BUILD_JOBS=str(jobs)),
                        start_new_session=os.name == 'posix')
                except OSError as exc:
                    writer.close()
                    entry['status'] = 'failed'
                    raise RuntimeError(f'{name} failed to start. Read {log}.') from exc
                profile.started(name, process.pid)
                if pooled_stage:
                    guard.track(name, process.pid)
                    watch.started(name, process.pid, allowance_file, time.monotonic())
                active[name] = {'process': process, 'writer': writer, 'reader': log.open(errors='replace'),
                                'entry': entry, 'start': time.monotonic(), 'parallel': pooled_stage,
                                'allowance': jobs, 'allowance_file': allowance_file}
                title = name + " (pre-baking in-game character models...)" if name == "npc-gallery" else name
                print(f'Build [{number}/{len(steps)}]: {title}, {jobs} worker(s). Log: {log}', flush=True)
                save()
            for name, state in list(active.items()):
                drain(state)
                code = state['process'].poll()
                if code is None:
                    continue
                # Exhaust the log after exit, including bursts larger than one read.
                while state['reader'].tell() < Path(state['entry']['log']).stat().st_size:
                    drain(state)
                state['reader'].close()
                state['writer'].close()
                del active[name]
                state['entry'].update(status='passed' if code == 0 else 'failed',
                                      returncode=code, elapsed_seconds=round(time.monotonic() - state['start'], 3))
                guard.untrack(name)
                guard.at = None           # the memory a finished stage held is free now: look again at once
                watch.finished(name)
                seen = watch.summary(name)
                if seen:
                    state['entry']['cores'] = seen
                profile.finished(name, state['entry'])
                save()
                digest()
                if code:
                    raise RuntimeError(f"{name} failed. Earlier results are retained. Read {state['entry']['log']}; use a new --name after fixing the problem.")
                passed.add(name)
                print(f"Completed {name}: {state['entry']['elapsed_seconds']:.1f}s", flush=True)
            if not active and pending and not any(set(dependencies[n]) <= passed for _, (n, _) in pending):
                raise ValueError('Build dependency cycle')
            if time.monotonic() - heartbeat >= 15:
                # the live worker count of each stage (its allowance now), not its start share (fixlist B9)
                print('Building: ' + ', '.join(f"{n} ({held(s)} workers)" for n, s in active.items()), flush=True)
                heartbeat = time.monotonic()
            if active:
                time.sleep(.1)
    except BaseException as exc:
        stop_children()
        receipt['status'] = 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed'
        receipt['not_started'] = [name for _, (name, _) in pending]
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 3)
        if watch.occurrences:
            receipt['stage_underused'] = watch.occurrences
        save()
        digest()
        profile.close(receipt)
        raise
    if guard.changes:
        receipt['scheduler_guard_changes'] = guard.changes
    if guard.alarms:
        receipt['scheduler_alarms'] = guard.alarms
    if watch.occurrences:
        # warnings, never a failure (the maintainer, 18 October 2026); listed in the build summary
        receipt['stage_underused'] = watch.occurrences
    receipt.update(status='passed', elapsed_seconds=round(time.monotonic() - start, 3))
    save()
    digest()
    profile.close(receipt)
