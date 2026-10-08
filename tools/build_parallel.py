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
import time

from build_jobs import resolve_jobs
import build_profile

# One numerical-library thread per worker prevents N workers each starting N
# BLAS/OpenMP threads. Native make and map tools use their explicit job budget.
THREAD_LIMITS = {name: '1' for name in (
    'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
    'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}


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


def process_pool(count):
    """The one worker-pool factory of the builder (tests record its size).

    Spawn avoids inherited archive handles and numerical-library thread state.
    """
    return ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context('spawn'))


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


def _copy(task):
    import shutil
    shutil.copyfile(*task)


def copy_files(pairs, jobs=None):
    """Copy (source, destination) pairs with up to `jobs` workers (independent files)."""
    pairs = [(str(a), str(b)) for a, b in pairs]
    for _ in ordered_map(_copy, pairs, max(1, min(resolve_jobs(jobs), len(pairs) or 1))):
        pass


# Scheduler allowance: a running stage's Python pools follow the share the
# scheduler writes to this file (BUILD-SCHEDULER-JOBSHARE-32).
ALLOWANCE_ENV = 'AMIWIND_BUILD_JOBS_FILE'
BUDGET_ENV = 'AMIWIND_BUILD_BUDGET'


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


def ordered_map(function, items, jobs=None):
    """Yield in input order; at most the current limit running, twice it queued.

    Workers return data; the caller alone writes shared archives and indices.
    Spawn avoids inherited archive handles and numerical-library thread state.
    """
    count = resolve_jobs(jobs)
    size, limit = _throttle(count)
    if size == 1:
        yield from map(function, items)
        return
    items = iter(items)
    with worker_environment(), process_pool(size) as pool:
        pending = deque()
        exhausted = False
        try:
            while True:
                cap = count if limit is None else limit()
                # Static: queue twice the workers in the pool. Allowance: at
                # most `cap` unfinished tasks, so the stage never exceeds it.
                while (not exhausted and len(pending) < 2 * cap
                       and (limit is None or _running(pending) < cap)):
                    try:
                        item = next(items)
                    except StopIteration:
                        exhausted = True
                        break
                    pending.append(pool.submit(function, item))
                if not pending:
                    return
                if limit is None or pending[0].done() or exhausted or len(pending) >= 2 * cap:
                    yield pending.popleft().result()
                else:
                    wait([f for f in pending if not f.done()], timeout=1, return_when=FIRST_COMPLETED)
        finally:
            for future in pending:
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
    'world-scenery': ('world-terrain', 'world-scenery-assets'),
    # Census rewrites intro-scene/id1/gfx/palette.lmp (BUILD-PALETTE-RACE-32).
    'world-flora-assets': ('census',),
    'world-flora': ('world-terrain', 'world-scenery', 'world-flora-assets'),
    'hand-catalog': ('census',),
    'harvest': ('census',),
    'media': (), 'music': (), 'engine': (),
    'image': ('world-terrain', 'world-scenery', 'npc-gallery', 'music', 'media', 'engine', 'dialogue-lookup'),
    'dry-run-image': ('engine',),
}


def stage_dependencies(steps):
    names = [name for name, _ in steps]
    if len(set(names)) != len(names):
        raise ValueError('Build stage names must be unique')
    result = {}
    # Extra town imports (town-<id>: shipped towns by default, --extra-town
    # towns on request) extend the ordered scene chain after Balmora's
    # interiors; the chain continues from the last of them.
    towns = [name for name in names if name.startswith('town-')]
    for index, name in enumerate(names):
        deps = DEPENDENCIES.get(name, tuple(names[index - 1:index]))
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
    dependencies = stage_dependencies(steps)
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

    def rebalance(waiting):
        """Share the budget again: serial stages hold one worker, running pooled
        stages split the rest evenly, leaving one worker for each ready stage
        still waiting (BUILD-SCHEDULER-JOBSHARE-32). Pools inside a stage follow
        its allowance file at their next task; tool threads keep their start value."""
        pooled = [s for s in active.values() if s['parallel']]
        if not pooled:
            return
        serial = len(active) - len(pooled)
        share = max(len(pooled), budget - serial - waiting)
        base, extra = divmod(share, len(pooled))
        for index, state in enumerate(sorted(pooled, key=lambda s: s['start'])):
            value = base + (1 if index < extra else 0)
            if value != state['allowance']:
                state['allowance'] = value
                temporary = state['allowance_file'].with_suffix('.tmp')
                temporary.write_text(f'{value}\n')
                temporary.replace(state['allowance_file'])
                state['entry']['workers_now'] = value
                state['entry'].setdefault('worker_changes', []).append(
                    [round(time.monotonic() - start, 3), value])
    profile = build_profile.start(run, steps, metadata, dependencies)
    try:
        while pending or active:
            ready = [item for item in pending if set(dependencies[item[1][0]]) <= passed]
            rebalance(len(ready))
            free = budget - sum(held(s) for s in active.values())
            for item in ready:
                if free < 1:
                    break
                number, (name, original) = item
                # Reserve a slot for each other ready branch before handing the
                # remainder to a parallel stage. Never exceed the global budget.
                others = ready[ready.index(item) + 1:]
                serial = sum('--jobs' not in command for _, (_, command) in others)
                parallel = sum('--jobs' in command for _, (_, command) in others)
                jobs = max(1, (free - serial) // (parallel + 1)) if '--jobs' in original else 1
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
                        env=dict(os.environ, **THREAD_LIMITS, **limits, PYTHONUNBUFFERED='1', AMIWIND_BUILD_JOBS=str(jobs)),
                        start_new_session=os.name == 'posix')
                except OSError as exc:
                    writer.close()
                    entry['status'] = 'failed'
                    raise RuntimeError(f'{name} failed to start. Read {log}.') from exc
                profile.started(name, process.pid)
                active[name] = {'process': process, 'writer': writer, 'reader': log.open(errors='replace'),
                                'entry': entry, 'start': time.monotonic(), 'parallel': pooled_stage,
                                'allowance': jobs, 'allowance_file': allowance_file}
                free -= jobs
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
