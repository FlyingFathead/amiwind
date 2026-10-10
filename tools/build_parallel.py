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
    """SHA-256 of every path, in input order, hashed by up to `jobs` workers."""
    paths = list(paths)
    return list(ordered_map(sha256_file, paths, max(1, min(resolve_jobs(jobs), len(paths) or 1))))


def _sha256_existing(path):
    return sha256_file(path) if os.path.isfile(path) else None


def hash_existing(paths, jobs=None):
    """Like hash_files, with None for a path that is not a regular file."""
    paths = [str(p) for p in paths]
    return list(ordered_map(_sha256_existing, paths, max(1, min(resolve_jobs(jobs), len(paths) or 1))))


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


def ordered_map(function, items, jobs=None, cost=None, timings=None):
    """Yield in input order; at most the current limit running.

    Up to WINDOW times the limit are submitted and not yet handed back, so a slow
    item at the head does not idle the other workers. `cost` (item -> number):
    every item is submitted largest first (ties in input order) so the long ones
    do not finish last on a few workers; results still come back in input order,
    held until their turn. `timings` (a list): the seconds each item took in its
    worker are appended in input order (item cost history, build_costs.py).
    Workers return data; the caller alone writes shared archives and indices.
    Spawn avoids inherited archive handles and numerical-library thread state.
    """
    from functools import partial
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
    with worker_environment(), process_pool(size) as pool:
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
                        break
                    pending[index] = pool.submit(call, item)
                    submitted += 1
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


def completed_map(function, items, jobs=None):
    """Yield independent work as it finishes, with a bounded submission window.

    Refill freed slots before handing results to the caller. A slow early task
    must not prevent later tasks from being submitted or reported. Callers must
    restore stable key order before exporting catalogues or shared receipts.
    Existing order-dependent conversion stages continue to use ordered_map.
    """
    count = resolve_jobs(jobs)
    size, limit = _throttle(count)
    if size == 1:
        yield from map(function, items)
        return
    items = iter(items)
    with worker_environment(), process_pool(size) as pool:
        pending = set()

        def refill():
            while len(pending) < (2 * count if limit is None else limit()):
                try:
                    item = next(items)
                except StopIteration:
                    return
                pending.add(pool.submit(function, item))

        try:
            refill()
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                results = [future.result() for future in done]
                refill()
                yield from results
        finally:
            for future in pending:
                future.cancel()


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
            # A CHIM town (tools/chim_town.py) reads the CHIM world and the census palette.
            deps = ('chim', 'census')
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
            deps = (*deps, 'chim', *(n for n in names if n.startswith('chim-town-')))
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


def execute_parallel(steps, run, metadata, root):
    dependencies = stage_dependencies(steps, plan_skipped(metadata))
    budget = int(metadata['compiler_jobs'])
    run.mkdir(parents=True, exist_ok=False)
    (run / 'logs').mkdir()
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
        share = max(count, budget - serial - waiting)
        base, extra = divmod(share, count)
        values = [base + (1 if index < extra else 0) for index in range(count)]
        for value, state in zip(values, sorted(pooled, key=lambda s: s['start'])):
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
    try:
        while pending or active:
            ready = [item for item in pending if set(dependencies[item[1][0]]) <= passed]
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
                profile.finished(name, state['entry'])
                save()
                if code:
                    raise RuntimeError(f"{name} failed. Earlier results are retained. Read {state['entry']['log']}; use a new --name after fixing the problem.")
                passed.add(name)
                print(f"Completed {name}: {state['entry']['elapsed_seconds']:.1f}s", flush=True)
            if not active and pending and not any(set(dependencies[n]) <= passed for _, (n, _) in pending):
                raise ValueError('Build dependency cycle')
            if time.monotonic() - heartbeat >= 15:
                print('Building: ' + ', '.join(f"{n} ({s['entry']['jobs']} workers)" for n, s in active.items()), flush=True)
                heartbeat = time.monotonic()
            if active:
                time.sleep(.1)
    except BaseException as exc:
        stop_children()
        receipt['status'] = 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed'
        receipt['not_started'] = [name for _, (name, _) in pending]
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 3)
        save()
        profile.close(receipt)
        raise
    receipt.update(status='passed', elapsed_seconds=round(time.monotonic() - start, 3))
    save()
    profile.close(receipt)
