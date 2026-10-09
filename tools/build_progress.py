#!/usr/bin/env python3
"""Live build progress and ETA: build-progress.json in the run folder.

While a build runs, the builder rewrites RUN/build-progress.json about every
10 seconds and on every stage start and end: which stages are done, running,
pending or failed; for each running stage its elapsed time, the cores it uses
now and its expected duration; the overall percent (weighted by expected stage
durations) and the ETA; the chain of stages the ETA waits on; idle-core
warnings; and the machine load.

Expected durations come from the build-profile.json files of earlier runs in
the same workspace (sibling run folders; median per stage, scaled to this
build's --jobs where the stage scales), else from the shipped table
config/build-stage-durations.json. A stage with neither says "no history".

    python tools/build.py status RUN [--json]

prints a one-screen summary of a running or finished build. The progress file
never changes a stage's command, environment or outputs; writing it never
fails a build. See docs/BUILD_PROFILE.md "Live progress and ETA".
"""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import statistics
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'amiwind-build-progress-v1'
PROGRESS_NAME = 'build-progress.json'
PROFILE_NAME = 'build-profile.json'
DEFAULTS = ROOT / 'config' / 'build-stage-durations.json'
INTERVAL_ENV = 'AMIWIND_PROGRESS_INTERVAL'
DEFAULT_INTERVAL = 10.0
HISTORY_RUNS = 10          # newest earlier runs read for expected durations
FALLBACK_SECONDS = 60.0    # weight of a stage without any history when nothing is known
REUSED_SECONDS = 5.0       # a stage copied by --reuse-from
RUNNING_CAP = 0.95         # a running stage never counts as finished
OVERRUN_SHARE = 0.10       # an overrunning stage is assumed to need 10 % of its elapsed time more ...
OVERRUN_MIN = 5.0          # ... and at least this many seconds
IDLE_SHARE = 0.5           # same rule as the profiler: under half of the jobs ...
IDLE_SECONDS = 60.0        # ... for longer than this
CORES_WINDOW = 10.0        # "cores now" = mean over the last this many seconds
DONE = ('passed',)
STOPPED = ('failed', 'cancelled')


# --------------------------------------------------------------------------
# Expected durations

def amdahl_share(cores, workers):
    """Parallel share (0..1) of a stage that averaged CORES with WORKERS workers (Amdahl's law)."""
    if cores is None or not workers or workers <= 1:
        return 0.0
    cores = max(1.0, min(float(cores), float(workers)))
    return max(0.0, min(1.0, (1 - 1 / cores) / (1 - 1 / workers)))


def scaled_seconds(wall, cpu, jobs, budget_then, budget_now):
    """WALL of a stage measured with budget BUDGET_THEN, scaled to BUDGET_NOW.

    A stage scales when it used more than one core: its parallel share comes
    from its average cores (cpu / wall) on the workers it had (its jobs, or more
    when the scheduler gave it more later), and that many workers grow or shrink
    with the budget. Serial stages and stages without CPU data keep their wall.
    """
    if not wall or cpu is None or not budget_then or not budget_now or budget_then == budget_now:
        return wall
    cores = cpu / wall
    workers = min(int(budget_then), max(int(jobs or 1), math.ceil(cores - 1e-9)))
    share = amdahl_share(cores, workers)
    if workers <= 1 or share <= 0:
        return wall
    serial_time = wall / ((1 - share) + share / workers)
    new_workers = max(1.0, workers * budget_now / budget_then)
    return serial_time * ((1 - share) + share / new_workers)


def history_samples(run, limit=HISTORY_RUNS):
    """({stage: [{wall, cpu, jobs, budget, run}]}, [run names]) from earlier runs next to RUN."""
    run = Path(run)
    try:
        here = run.resolve()
        folders = [child for child in run.parent.iterdir()
                   if child.resolve() != here and (child / PROFILE_NAME).is_file()]
    except OSError:
        return {}, []
    folders.sort(key=lambda folder: ((folder / PROFILE_NAME).stat().st_mtime, folder.name), reverse=True)
    samples, used = {}, []
    for folder in folders[:limit]:
        try:
            profile = json.loads((folder / PROFILE_NAME).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        budget = profile.get('budget')
        found = False
        for row in profile.get('stages', []):
            if row.get('status') != 'passed' or row.get('reused') or not row.get('wall'):
                continue
            samples.setdefault(row['name'], []).append({'wall': row['wall'], 'cpu': row.get('cpu'),
                                                         'jobs': row.get('jobs_max') or row.get('jobs'), 'budget': budget,
                                                         'run': folder.name})
            found = True
        if found:
            used.append(folder.name)
    return samples, used


def load_defaults(path=DEFAULTS):
    """(budget, {stage: {wall, cpu, jobs}}) of the shipped table, or (None, {})."""
    try:
        table = json.loads(Path(path).read_text(encoding='utf-8'))
        return table.get('budget'), table.get('stages', {})
    except (OSError, ValueError):
        return None, {}


def expected_durations(names, budget, samples=None, defaults=(None, {}), reused=()):
    """{stage: {'seconds', 'cores', 'source', 'samples'}}; seconds None = no history."""
    samples = samples or {}
    default_budget, default_stages = defaults
    result = {}
    for name in names:
        if name in reused:
            result[name] = {'seconds': REUSED_SECONDS, 'cores': 1.0, 'source': 'reused', 'samples': 0}
            continue
        rows = samples.get(name)
        if rows:
            seconds = statistics.median(scaled_seconds(r['wall'], r.get('cpu'), r.get('jobs'), r.get('budget'), budget)
                                        for r in rows)
            cores = [r['cpu'] / r['wall'] for r in rows if r.get('cpu') is not None and r['wall']]
            result[name] = {'seconds': round(seconds, 1), 'cores': round(statistics.median(cores), 2) if cores else None,
                            'source': 'history', 'samples': len(rows)}
            continue
        row = default_stages.get(name)
        if row and row.get('wall'):
            seconds = scaled_seconds(row['wall'], row.get('cpu'), row.get('jobs'), default_budget, budget)
            result[name] = {'seconds': round(seconds, 1),
                            'cores': round(row['cpu'] / row['wall'], 2) if row.get('cpu') is not None else None,
                            'source': 'default', 'samples': 0}
            continue
        result[name] = {'seconds': None, 'cores': None, 'source': 'none', 'samples': 0}
    return result


# --------------------------------------------------------------------------
# Estimate (pure: tested with synthetic builds)

def trailing_idle(points, limit, interval=1.0):
    """Seconds at the end of POINTS [(t, cores), ...] during which cores stayed below LIMIT."""
    seconds = 0.0
    for index in range(len(points) - 1, -1, -1):
        if points[index][1] >= limit:
            break
        seconds += points[index][0] - points[index - 1][0] if index > 0 else interval
    return round(seconds, 1)


def estimate(order, dependencies, stages, expected, budget):
    """Percent, ETA and the chain the ETA waits on.

    order: every stage of the build. stages: {name: {'status', 'elapsed'}} for
    stages that started (status running, passed, failed or cancelled); others
    are pending. expected: expected_durations(). Percent weights each stage by
    its expected duration (the median of known stages for one without history);
    a running stage counts its elapsed share, at most 95 %. The ETA is the later
    of the longest remaining dependency chain and the remaining CPU work spread
    over the budget.
    """
    known = [entry['seconds'] for entry in expected.values() if entry.get('seconds')]
    fallback = statistics.median(known) if known else FALLBACK_SECONDS
    weight = {name: (expected.get(name) or {}).get('seconds') or fallback for name in order}
    status = {name: (stages.get(name) or {}).get('status', 'pending') for name in order}
    remaining, overrun, done_weight = {}, [], 0.0
    for name in order:
        state, wall = status[name], weight[name]
        elapsed = (stages.get(name) or {}).get('elapsed') or 0.0
        if state in DONE:
            done_weight += wall
            remaining[name] = 0.0
        elif state == 'running' or state in STOPPED:
            done_weight += wall * min(elapsed / wall, RUNNING_CAP) if wall else 0.0
            if state in STOPPED:
                remaining[name] = 0.0
            elif elapsed < wall:
                remaining[name] = wall - elapsed
            else:
                remaining[name] = max(OVERRUN_MIN, OVERRUN_SHARE * elapsed)
                overrun.append(name)
        else:
            remaining[name] = wall
    total = sum(weight.values())
    finished = bool(order) and all(status[name] in DONE for name in order)
    percent = 100.0 if finished else round(min(99.9, 100.0 * done_weight / total), 1) if total else 0.0
    finish, via = {}, {}

    def finish_of(name, trail=()):
        if name in finish:
            return finish[name]
        if name in trail:
            raise ValueError('Dependency cycle at ' + name)
        start, best = 0.0, None
        if status[name] not in DONE and status[name] != 'running':
            for dep in dependencies.get(name, ()):
                if dep in status:
                    end = finish_of(dep, (*trail, name))
                    if end > start:
                        start, best = end, dep
        finish[name], via[name] = start + remaining[name], best
        return finish[name]

    for name in order:
        finish_of(name)
    open_stages = [name for name in order if status[name] not in DONE and status[name] not in STOPPED]
    path = []
    if open_stages:
        node = max(open_stages, key=lambda name: (finish[name], -order.index(name)))
        while node and status[node] not in DONE:
            path.append(node)
            node = via.get(node)
        path.reverse()
    chain = max(finish.values(), default=0.0)
    work = sum(remaining[name] * max(1.0, min((expected.get(name) or {}).get('cores') or 1.0, budget or 1))
               for name in order) / max(1, budget or 1)
    stopped = any(status[name] in STOPPED for name in order)
    if finished or stopped:
        eta, basis = (0.0 if finished else None), None
    else:
        eta, basis = (chain, 'critical path') if chain >= work else (work, 'CPU budget')
    unknown = [name for name in order if (expected.get(name) or {}).get('source', 'none') == 'none']
    return {'percent': percent, 'eta_seconds': None if eta is None else round(eta, 1), 'eta_basis': basis,
            'critical_path': path, 'critical_path_seconds': round(chain, 1), 'work_seconds': round(work, 1),
            'overrun': overrun, 'no_history': unknown, 'fallback_seconds': round(fallback, 1),
            'remaining': {name: round(value, 1) for name, value in remaining.items()}}


# --------------------------------------------------------------------------
# Tracker (in the builder; fed by the profiler session's hooks and sampler)

def _now_iso(epoch=None):
    moment = datetime.fromtimestamp(time.time() if epoch is None else epoch).astimezone()
    return moment.isoformat(timespec='seconds')


class Tracker:
    """Writes RUN/build-progress.json; every method is cheap and never raises into the build."""

    def __init__(self, run, order, dependencies, metadata, sampler=None, origin=None, interval=None):
        self.run = Path(run)
        self.order = list(order)
        self.dependencies = {name: list(deps) for name, deps in (dependencies or {}).items()}
        self.budget = int(metadata.get('compiler_jobs', 1) or 1)
        self.sampler = sampler
        self.origin = time.monotonic() if origin is None else origin
        self.started_epoch = time.time() - (time.monotonic() - self.origin)
        reused = set(((metadata.get('stage_cache') or {}).get('reused') or {}).keys())
        samples, self.history_runs = history_samples(self.run)
        defaults = load_defaults()
        self.expected = expected_durations(self.order, self.budget, samples, defaults, reused)
        self.defaults_used = any(entry['source'] == 'default' for entry in self.expected.values())
        self.stages = {}
        self.status = 'running'
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()
        if interval is None:
            try:
                interval = float(os.environ.get(INTERVAL_ENV, DEFAULT_INTERVAL))
            except ValueError:
                interval = DEFAULT_INTERVAL
        self.interval = max(0.05, interval)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name='build-progress', daemon=True)
        self.writes = 0
        self.write()
        self.thread.start()

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self.write()

    def stage_started(self, name, number, jobs):
        with self.lock:
            self.stages[name] = {'status': 'running', 'number': number, 'jobs': jobs,
                                 'start': time.monotonic() - self.origin}
        self.write()

    def stage_finished(self, name, status):
        with self.lock:
            stage = self.stages.get(name)
            if stage is None or stage['status'] != 'running':
                return
            stage.update(status=status, end=time.monotonic() - self.origin)
        self.write()

    def close(self, status):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=5)
        with self.lock:
            self.status = status or 'unknown'
            for stage in self.stages.values():
                if stage['status'] == 'running':
                    stage.update(status=self.status if self.status in STOPPED else 'unknown',
                                 end=time.monotonic() - self.origin)
        self.write()

    def _jobs_now(self, name, stage):
        """The stage's current worker allowance (the parallel scheduler rebalances it), else its start value."""
        try:
            return int((self.run / 'jobs' / f"{stage['number']:02}-{name}").read_text().strip())
        except (OSError, ValueError, KeyError):
            return stage.get('jobs')

    def _cores(self, now):
        """({stage: [(t, cores)]}, [(t, build cores)], timeline) from the profiler's sampler, or empties."""
        sampler = self.sampler
        if sampler is None:
            return {}, [], None
        with sampler.lock:
            times = list(sampler.times)
            total = list(sampler.total)
            rows = {name: list(values) for name, values in sampler.stages.items()}
        per_stage = {name: [(times[index], cores) for index, cores, *_ in values if index < len(times)]
                     for name, values in rows.items()}
        build = list(zip(times, total))
        try:
            timeline = sampler.timeline()
        except Exception:  # noqa: BLE001
            timeline = None
        return per_stage, build, timeline

    def snapshot(self):
        now = time.monotonic() - self.origin
        with self.lock:
            stages = {name: dict(stage) for name, stage in self.stages.items()}
            status = self.status
        per_stage, build_cores, timeline = self._cores(now)
        interval = getattr(self.sampler, 'interval', 1.0) if self.sampler else 1.0
        states, rows, warnings = {}, [], []
        for name in self.order:
            stage = stages.get(name)
            entry = self.expected.get(name, {})
            row = {'name': name, 'status': stage['status'] if stage else 'pending',
                   'expected_seconds': entry.get('seconds'), 'expected_source': entry.get('source')}
            if stage:
                end = stage.get('end', now)
                elapsed = max(0.0, end - stage['start'])
                row.update(elapsed_seconds=round(elapsed, 1), jobs=stage.get('jobs'))
                states[name] = {'status': row['status'], 'elapsed': elapsed}
                if row['status'] == 'running':
                    jobs = self._jobs_now(name, stage) or 1
                    row['jobs'] = jobs
                    points = per_stage.get(name, [])
                    recent = [cores for t, cores in points if t >= now - CORES_WINDOW]
                    row['cores_now'] = round(sum(recent) / len(recent), 2) if recent else None
                    if points:
                        idle = trailing_idle(points, IDLE_SHARE * jobs, interval)
                        row['idle_seconds'] = idle
                        if idle > IDLE_SECONDS:
                            low = [cores for t, cores in points if t >= points[-1][0] - idle]
                            warnings.append({'stage': name, 'cores': round(sum(low) / len(low), 2) if low else None,
                                             'jobs': jobs, 'seconds': idle})
            rows.append(row)
        result = estimate(self.order, self.dependencies, states, self.expected, self.budget)
        for row in rows:
            if row['status'] == 'running':
                row['remaining_seconds'] = result['remaining'].get(row['name'])
                row['overrun'] = row['name'] in result['overrun']
        build_idle = None
        if build_cores and status == 'running':
            idle = trailing_idle(build_cores, IDLE_SHARE * self.budget, interval)
            if idle > IDLE_SECONDS:
                low = [cores for t, cores in build_cores if t >= build_cores[-1][0] - idle]
                build_idle = {'cores': round(sum(low) / len(low), 2) if low else None, 'jobs': self.budget,
                              'seconds': idle}
        host = None
        if timeline:
            try:
                from build_profile import host_load
                host = host_load({'start': now - CORES_WINDOW, 'end': now + 1}, timeline)
            except Exception:  # noqa: BLE001
                host = None
        counts = {key: sum(1 for row in rows if row['status'] == key) for key in ('passed', 'running', 'pending')}
        counts['failed'] = sum(1 for row in rows if row['status'] in STOPPED)
        counts['total'] = len(rows)
        epoch = time.time()
        eta = result['eta_seconds']
        recent_build = [cores for t, cores in build_cores if t >= now - CORES_WINDOW]
        return {'schema': SCHEMA, 'run': self.run.name, 'status': status,
                'started_at': _now_iso(self.started_epoch), 'updated_at': _now_iso(epoch),
                'updated_epoch': round(epoch, 3), 'interval': self.interval,
                'elapsed_seconds': round(now, 1), 'budget': self.budget,
                'percent': result['percent'], 'eta_seconds': eta, 'eta_basis': result['eta_basis'],
                'eta_at': _now_iso(epoch + eta) if eta is not None else None,
                'critical_path': result['critical_path'], 'critical_path_seconds': result['critical_path_seconds'],
                'work_seconds': result['work_seconds'], 'counts': counts,
                'cores_now': round(sum(recent_build) / len(recent_build), 2) if recent_build else None,
                'stages': rows, 'idle_warnings': warnings, 'build_idle': build_idle, 'host': host,
                'no_history': result['no_history'], 'fallback_seconds': result['fallback_seconds'],
                'history': {'runs': self.history_runs, 'defaults': self.defaults_used},
                'writes': self.writes + 1}

    def write(self):
        try:
            with self.write_lock:  # the builder thread and the timer thread
                data = self.snapshot()
                self.writes += 1
                temporary = self.run / (PROGRESS_NAME + '.tmp')
                temporary.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
                temporary.replace(self.run / PROGRESS_NAME)
        except Exception:  # noqa: BLE001 - progress must never fail a build
            pass


def start(run, order, dependencies, metadata, sampler=None, origin=None):
    """The builder's progress tracker, or None when it cannot start."""
    try:
        return Tracker(run, order, dependencies, metadata, sampler, origin)
    except Exception as exc:  # noqa: BLE001
        print(f'[warning] Live build progress disabled: {exc}', flush=True)
        return None


# --------------------------------------------------------------------------
# Status (tools/build.py status RUN)

def duration(value):
    if value is None:
        return '?'
    value = int(round(max(0.0, float(value))))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    if minutes:
        return f'{minutes}m{seconds:02d}s'
    return f'{seconds}s'


def read_progress(run):
    """The run's progress record; without build-progress.json, a reduced one from build-state.json."""
    run = Path(run)
    path = run / PROGRESS_NAME
    if path.is_file():
        return json.loads(path.read_text(encoding='utf-8'))
    state_path = run / 'build-state.json'
    if not state_path.is_file():
        raise ValueError(f'{run}: neither {PROGRESS_NAME} nor build-state.json (not a build run folder?)')
    state = json.loads(state_path.read_text(encoding='utf-8'))
    rows = [{'name': step['name'], 'status': step.get('status', '?'), 'jobs': step.get('jobs'),
             'elapsed_seconds': step.get('elapsed_seconds')} for step in state.get('steps', [])]
    rows += [{'name': name, 'status': 'pending'} for name in state.get('not_started', [])]
    counts = {key: sum(1 for row in rows if row['status'] == key) for key in ('passed', 'running', 'pending')}
    counts['failed'] = sum(1 for row in rows if row['status'] in STOPPED)
    counts['total'] = len(rows)
    return {'schema': SCHEMA, 'run': run.name, 'status': state.get('status'), 'stages': rows, 'counts': counts,
            'percent': None, 'eta_seconds': None, 'reduced': 'no build-progress.json (a --no-profile run or an '
            'older builder): stage states from build-state.json, no percent or ETA; stages not started yet '
            'are unknown while it runs',
            'updated_epoch': state_path.stat().st_mtime, 'elapsed_seconds': state.get('elapsed_seconds')}


def stale_seconds(progress, now=None):
    """Seconds since the last update when a running build stopped writing, else None."""
    if progress.get('status') != 'running' or not progress.get('updated_epoch'):
        return None
    age = (time.time() if now is None else now) - progress['updated_epoch']
    return age if age > 3 * (progress.get('interval') or DEFAULT_INTERVAL) + 30 else None


def status_lines(progress, now=None):
    now = time.time() if now is None else now
    counts = progress.get('counts') or {}
    head = f"Build {progress.get('run')}: {progress.get('status')}"
    if progress.get('percent') is not None:
        head += f", {progress['percent']:.1f} %"
    if progress.get('elapsed_seconds') is not None:
        head += f", elapsed {duration(progress['elapsed_seconds'])}"
    if progress.get('status') == 'running' and progress.get('eta_seconds') is not None:
        at = progress.get('eta_at') or ''
        head += f", ETA {duration(progress['eta_seconds'])}" + (f" (at {at[11:19]}, {progress.get('eta_basis')})" if at else '')
    lines = [head,
             f"Stages: {counts.get('passed', 0)} done, {counts.get('running', 0)} running, {counts.get('pending', 0)} "
             f"pending, {counts.get('failed', 0)} failed/cancelled (of {counts.get('total', 0)})"]
    if progress.get('reduced'):
        lines.append('Note: ' + progress['reduced'])
    stale = stale_seconds(progress, now)
    if stale is not None:
        lines.append(f'STALE: no update for {duration(stale)}; the builder may have stopped')
    running = [row for row in progress.get('stages', []) if row.get('status') == 'running']
    if running:
        lines.append(f"  {'running':<26}{'elapsed':>9}{'expected':>12}{'cores':>8}{'jobs':>6}  note")
        for row in running:
            expected = row.get('expected_seconds')
            note = []
            if row.get('expected_source') == 'none':
                note.append('no history')
            elif row.get('expected_source') == 'default':
                note.append('default table')
            if row.get('overrun'):
                note.append('OVERRUN')
            if (row.get('idle_seconds') or 0) > IDLE_SECONDS:
                note.append(f"idle {duration(row['idle_seconds'])}")
            cores = row.get('cores_now')
            lines.append((f"  {row['name'][:25]:<26}{duration(row.get('elapsed_seconds')):>9}"
                          f"{('~' + duration(expected)) if expected else 'no history':>12}"
                          f"{(f'{cores:.1f}' if cores is not None else '-'):>8}{str(row.get('jobs') or '-'):>6}  "
                          + ', '.join(note)).rstrip())
    failed = [row['name'] for row in progress.get('stages', []) if row.get('status') in STOPPED]
    if failed:
        lines.append('Failed/cancelled: ' + ', '.join(failed))
    if progress.get('critical_path') and progress.get('status') == 'running':
        lines.append(f"ETA waits on ({duration(progress.get('critical_path_seconds'))}): "
                     + ' > '.join(progress['critical_path']))
    for warning in progress.get('idle_warnings') or []:
        lines.append(f"[idle] {warning['stage']}: {warning.get('cores')} of {warning.get('jobs')} cores for "
                     f"{duration(warning.get('seconds'))}")
    if progress.get('build_idle'):
        idle = progress['build_idle']
        lines.append(f"[idle] whole build: {idle.get('cores')} of {idle.get('jobs')} cores for {duration(idle.get('seconds'))}")
    host = progress.get('host')
    if host:
        lines.append(f"Host: {host.get('cpus')} CPUs, {host.get('busy_percent')} % busy, this build "
                     f"{host.get('build_cores')} cores, other work {host.get('other_percent')} %"
                     + (' (HOST BUSY: timings not comparable with a quiet host)' if host.get('host_busy') else ''))
    elif progress.get('cores_now') is not None:
        lines.append(f"Cores in use: {progress['cores_now']} of {progress.get('budget')}")
    if progress.get('no_history'):
        lines.append(f"No history ({duration(progress.get('fallback_seconds'))} weight each): "
                     + ', '.join(progress['no_history']))
    history = progress.get('history') or {}
    if history:
        source = f"{len(history.get('runs') or [])} earlier run(s)" if history.get('runs') else 'no earlier runs'
        if history.get('defaults'):
            source += ' + the default table'
        lines.append('Expected durations from ' + source)
    if progress.get('updated_epoch'):
        stamp = progress.get('updated_at') or datetime.fromtimestamp(progress['updated_epoch']).astimezone().isoformat(timespec='seconds')
        lines.append(f"Updated {stamp} ({duration(now - progress['updated_epoch'])} ago)")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(prog='build.py status', description='One-screen progress of a build run.')
    parser.add_argument('run', type=Path, help='Build run folder (WORKSPACE/build/NAME)')
    parser.add_argument('--json', action='store_true', help='Print the progress record as JSON')
    args = parser.parse_args(argv)
    try:
        progress = read_progress(args.run)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    if args.json:
        record = dict(progress)
        stale = stale_seconds(progress)
        record['stale_seconds'] = None if stale is None else round(stale, 1)
        print(json.dumps(record, indent=2))
    else:
        print('\n'.join(status_lines(progress)))
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
