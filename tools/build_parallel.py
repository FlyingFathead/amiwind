"""Bounded, ordered process work and dependency-aware build scheduling."""
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import time

from build_jobs import resolve_jobs

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


def ordered_map(function, items, jobs=None):
    """Yield in input order, with at most twice the worker count in flight.

    Workers return data; the caller alone writes shared archives and indices.
    Spawn avoids inherited archive handles and numerical-library thread state.
    """
    count = resolve_jobs(jobs)
    if count == 1:
        yield from map(function, items)
        return
    items = iter(items)
    with worker_environment(), ProcessPoolExecutor(
            max_workers=count, mp_context=multiprocessing.get_context('spawn')) as pool:
        pending = deque()
        try:
            for _ in range(2 * count):
                try:
                    item = next(items)
                except StopIteration:
                    break
                pending.append(pool.submit(function, item))
            while pending:
                yield pending.popleft().result()
                try:
                    item = next(items)
                except StopIteration:
                    continue
                pending.append(pool.submit(function, item))
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
    'actor-contact': ('world-ui',), 'world-terrain': ('actor-contact',),
    'music': (), 'engine': (),
    'image': ('world-terrain', 'music', 'engine', 'dialogue-lookup'),
    'dry-run-image': ('engine',),
}


def stage_dependencies(steps):
    names = [name for name, _ in steps]
    if len(set(names)) != len(names):
        raise ValueError('Build stage names must be unique')
    result = {}
    for index, name in enumerate(names):
        deps = DEPENDENCIES.get(name, tuple(names[index - 1:index]))
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
            drain(state)
            state['reader'].close()
            state['writer'].close()

    print(f'Parallel build: {budget} total workers; shared scene writes remain ordered.', flush=True)
    save()
    try:
        while pending or active:
            free = budget - sum(s['entry']['jobs'] for s in active.values())
            ready = [item for item in pending if set(dependencies[item[1][0]]) <= passed]
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
                try:
                    process = subprocess.Popen(command, cwd=root, stdout=writer, stderr=subprocess.STDOUT,
                        env=dict(os.environ, **THREAD_LIMITS, PYTHONUNBUFFERED='1', AMIWIND_BUILD_JOBS=str(jobs)),
                        start_new_session=os.name == 'posix')
                except OSError as exc:
                    writer.close()
                    entry['status'] = 'failed'
                    raise RuntimeError(f'{name} failed to start. Read {log}.') from exc
                active[name] = {'process': process, 'writer': writer, 'reader': log.open(errors='replace'),
                                'entry': entry, 'start': time.monotonic()}
                free -= jobs
                print(f'Build [{number}/{len(steps)}]: {name}, {jobs} worker(s). Log: {log}', flush=True)
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
        raise
    receipt.update(status='passed', elapsed_seconds=round(time.monotonic() - start, 3))
    save()
