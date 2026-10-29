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
A stage whose size can be read from its command line (WORK_MEASURES: the chim
stage counts its frames) takes only history runs with a known size, scaled to
this build's size; with none it says "no comparable history" and the ETA is a
lower bound (BUILD-PROGRESS-ETA-BASIS-36). Every expected duration carries its
basis (expected_basis) in the progress record.

While a stage runs, its estimate follows the work (fixlist B6; dev5's chim
stage was expected at 43 min from the frames of earlier runs and ran 85):
the stage's counter (its phase timer's done/total, else the last counted
progress line of its log, "[done/total unit] ...") gives the units done and
the time they took here; the remaining units at that rate, plus the history
time of the phases that follow, are blended with the history estimate by
sqrt(done/total), so the estimate moves to the measured rate as the stage
runs and equals it at the end. A stage past its history estimate with no
counter takes its phase history instead. The units a stage counted are kept
(units_seen) so the next build expects it per unit: unit counts x per-unit
cost. The basis is in every stage row (expected_basis, live) and in the ETA
basis, and the builder prints an "[eta]" line every 5 minutes
(AMIWIND_ETA_LINE_SECONDS; 0 = off).

    python tools/build.py status RUN [--json]

prints a one-screen summary of a running or finished build. The progress file
never changes a stage's command, environment or outputs; writing it never
fails a build. See docs/BUILD_PROFILE.md "Live progress and ETA".
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
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
PEAK_LOG_SHARE = 0.75      # a new memory peak above this share of the limit prints a [memory] line ...
PEAK_LOG_STEP_GIB = 0.5    # ... when it is at least this much above the last one printed (no line per sample)
LOW_RAM_SHARE = 0.10       # under this share of the limit available: a [memory] WARNING line ...
LOW_RAM_REPEAT_SECONDS = 300.0   # ... again at most this often while it lasts
# The monitor's warnings row (MONITOR-WARNINGS-ROW): the lines of the stage logs that are warnings. The builder's own
# forms: "WARNING" anywhere ([pool] WARNING, [memory] WARNING, size and perf warnings), the underuse lines and the
# scheduler's alarms and memory cuts
WARNING_LINE = re.compile(r'\bWARNING\b|\[underused\]|\[scheduler\] (ALARM|memory tight)')
WARNINGS_KEPT = 200              # warning lines kept in build-progress.json (the count goes on past it)
WARNINGS_READ_BYTES = 8 << 20    # at most this much new log text read per log and snapshot
DONE = ('passed',)
STOPPED = ('failed', 'cancelled')
COMPARABLE_RATIO = 2.0     # history of a run within this size ratio counts as the same size
NO_COMPARABLE = 'no comparable history'
LOG_TAIL_BYTES = 65536     # how much of a stage log's end is read for its last counted progress line
ETA_LINE_ENV = 'AMIWIND_ETA_LINE_SECONDS'
DEFAULT_ETA_LINE = 300.0   # the builder's "[eta]" stdout line, every this many seconds while stages run


# --------------------------------------------------------------------------
# Work measures: how much a stage does in this build, read from its command line, so that history
# from a run of another size is scaled instead of used as is (BUILD-PROGRESS-ETA-BASIS-36: the
# chim stage was expected at 154 s from three-area runs and ran 1 h 48 min on 273 frames).

def _option_values(command, option):
    args = [str(arg) for arg in command or ()]
    values = []
    for index, arg in enumerate(args):
        if arg == option and index + 1 < len(args):
            values.append(args[index + 1])
        elif arg.startswith(option + '='):
            values.append(arg.split('=', 1)[1])
    return values


def chim_frames(command):
    """Frames the chim stage builds: one per --area, one per --chim-regions-cells cell."""
    count = len(_option_values(command, '--area'))
    count += sum(len(value.split()) for value in _option_values(command, '--chim-regions-cells'))
    return count or None


WORK_MEASURES = {'chim': ('frames', chim_frames)}


def work_measure(name, command):
    """(unit, amount) of stage NAME from its command, or None when the stage has no measure."""
    entry = WORK_MEASURES.get(name)
    if entry is None or not command:
        return None
    try:
        amount = entry[1](command)
    except Exception:  # noqa: BLE001 - a measure never stops progress
        return None
    return (entry[0], amount) if amount else None


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
        commands = None
        counted = run_units(folder)
        for row in profile.get('stages', []):
            if row.get('status') != 'passed' or row.get('reused') or not row.get('wall'):
                continue
            sample = {'wall': row['wall'], 'cpu': row.get('cpu'), 'jobs': row.get('jobs_max') or row.get('jobs'),
                      'budget': budget, 'run': folder.name}
            if counted.get(row['name']):
                sample['units'] = counted[row['name']]
            phases = [{'name': item['name'], 'start': item.get('start') or 0.0, 'wall': item.get('wall') or 0.0}
                      for item in row.get('sections') or () if item.get('phase') and not item.get('min_depth')]
            if phases:
                sample['phases'] = sorted(phases, key=lambda item: item['start'])
            if row['name'] in WORK_MEASURES:
                if commands is None:
                    commands = run_commands(folder)
                measure = work_measure(row['name'], commands.get(row['name']))
                sample['work'] = measure[1] if measure else None
            samples.setdefault(row['name'], []).append(sample)
            found = True
        if found:
            used.append(folder.name)
    return samples, used


def run_units(folder):
    """{stage: {unit: total}} a run's stages counted (build-progress.json units_seen; {} when unknown)."""
    try:
        progress = json.loads((Path(folder) / PROGRESS_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return {row['name']: dict(row['units_seen']) for row in progress.get('stages', [])
            if row.get('name') and isinstance(row.get('units_seen'), dict) and row['units_seen']}


def run_commands(folder):
    """{stage: command} recorded in a run's build-state.json ({} when unreadable)."""
    try:
        state = json.loads((Path(folder) / 'build-state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return {step['name']: step.get('command') for step in state.get('steps', []) if step.get('name')}


def load_defaults(path=DEFAULTS):
    """(budget, {stage: {wall, cpu, jobs}}) of the shipped table, or (None, {})."""
    try:
        table = json.loads(Path(path).read_text(encoding='utf-8'))
        return table.get('budget'), table.get('stages', {})
    except (OSError, ValueError):
        return None, {}


def expected_durations(names, budget, samples=None, defaults=(None, {}), reused=(), work=None):
    """{stage: {'seconds', 'cores', 'source', 'samples', 'basis'}}; seconds None = no (comparable) history.

    WORK: {stage: (unit, amount)} of this build (work_measure). A stage with a measure uses only the
    history runs of a known size, each scaled by amount here / amount then (linear); with none it is
    'no comparable history' (the default table has no sizes either)."""
    samples = samples or {}
    work = work or {}
    default_budget, default_stages = defaults
    result = {}
    for name in names:
        if name in reused:
            result[name] = {'seconds': REUSED_SECONDS, 'cores': 1.0, 'source': 'reused', 'samples': 0,
                            'basis': 'reused'}
            continue
        rows = samples.get(name)
        measure = work.get(name)
        if measure:
            unit, amount = measure
            sized = [r for r in rows or () if r.get('work')]
            if not sized:
                result[name] = {'seconds': None, 'cores': None, 'source': NO_COMPARABLE, 'samples': 0,
                                'work': amount, 'work_unit': unit,
                                'basis': f'{NO_COMPARABLE}: {amount} {unit} here, '
                                         f'{len(rows or ())} earlier run(s) of unknown size'}
                continue
            seconds = statistics.median(scaled_seconds(r['wall'], r.get('cpu'), r.get('jobs'), r.get('budget'), budget)
                                        * amount / r['work'] for r in sized)
            then = statistics.median(r['work'] for r in sized)
            cores = [r['cpu'] / r['wall'] for r in sized if r.get('cpu') is not None and r['wall']]
            ratio = amount / then
            if 1 / COMPARABLE_RATIO <= ratio <= COMPARABLE_RATIO:
                basis = f'history ({len(sized)} run(s), {then:g} {unit} there, {amount} here)'
            else:
                basis = f'history scaled by {unit}: {amount} here, {then:g} in {len(sized)} earlier run(s)'
            result[name] = {'seconds': round(seconds, 1), 'cores': round(statistics.median(cores), 2) if cores else None,
                            'source': 'history', 'samples': len(sized), 'work': amount, 'work_unit': unit,
                            'basis': basis}
            continue
        if rows:
            seconds = statistics.median(scaled_seconds(r['wall'], r.get('cpu'), r.get('jobs'), r.get('budget'), budget)
                                        for r in rows)
            cores = [r['cpu'] / r['wall'] for r in rows if r.get('cpu') is not None and r['wall']]
            result[name] = {'seconds': round(seconds, 1), 'cores': round(statistics.median(cores), 2) if cores else None,
                            'source': 'history', 'samples': len(rows), 'basis': f'history ({len(rows)} run(s))'}
            continue
        row = default_stages.get(name)
        if row and row.get('wall'):
            seconds = scaled_seconds(row['wall'], row.get('cpu'), row.get('jobs'), default_budget, budget)
            result[name] = {'seconds': round(seconds, 1),
                            'cores': round(row['cpu'] / row['wall'], 2) if row.get('cpu') is not None else None,
                            'source': 'default', 'samples': 0, 'basis': 'default table'}
            continue
        result[name] = {'seconds': None, 'cores': None, 'source': 'none', 'samples': 0, 'basis': 'no history'}
    return result


# --------------------------------------------------------------------------
# Live correction from the work done (fixlist B6; pure: tested with synthetic counters)

COUNTER_LINE = re.compile(r'^(?:\[\+[^\]]*\]\s*)?\[(\d+)/(\d+)(?: ([^\]|]*?))?\s*(?:\|[^\]]*)?\]\s*([^:\n]+)')


def log_counter(path, limit=LOG_TAIL_BYTES):
    """{name, done, total, unit} of the last counted progress line ("[done/total unit] name: ...",
    tools/progress_line.py) in the end of a stage log, or None."""
    try:
        with open(path, 'rb') as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - limit))
            text = stream.read().decode('utf-8', errors='replace')
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        match = COUNTER_LINE.match(line.strip())
        if match and int(match.group(2)) > 0:
            return {'name': match.group(4).strip(), 'done': int(match.group(1)), 'total': int(match.group(2)),
                    'unit': (match.group(3) or '').strip() or None}
    return None


def per_unit_expected(rows, unit, total, budget):
    """(seconds, seconds per unit, runs) for TOTAL units of UNIT from history rows that counted that unit
    (wall scaled to this budget, then per unit), or None."""
    costs = [scaled_seconds(r['wall'], r.get('cpu'), r.get('jobs'), r.get('budget'), budget) / r['units'][unit]
             for r in rows or () if (r.get('units') or {}).get(unit)]
    if not costs or not total:
        return None
    each = statistics.median(costs)
    return each * total, each, len(costs)


def phase_history(rows, phase, ratio=1.0):
    """(median wall of PHASE, median wall of the outermost phases after it) in history rows, scaled by
    RATIO (this build's work / the run's); (None, None) when no history run had that phase."""
    walls, tails = [], []
    for row in rows or ():
        phases = row.get('phases') or ()
        found = next((item for item in phases if item['name'] == phase), None)
        if found is None:
            continue
        scale = ratio(row) if callable(ratio) else ratio
        end = found['start'] + found['wall']
        walls.append(found['wall'] * scale)
        tails.append(sum(item['wall'] for item in phases if item['start'] >= end - 1.0) * scale)
    if not walls:
        return None, None
    return statistics.median(walls), statistics.median(tails)


def corrected_remaining(prior, elapsed, counted_seconds, done_since, done, total, tail=0.0, overrun=False):
    """The stage's remaining seconds from its counter, blended with the history estimate.

    prior: the history estimate's remaining seconds (None when unknown); counted_seconds: the time the
    DONE_SINCE units took here; done/total: the counter now; tail: the history seconds of the phases after
    the counted one. The measured remaining (rate x units left + tail) gets weight sqrt(done/total), 1 when
    the history estimate is unknown or already overrun: it converges to the measured rate as the stage
    runs and equals it when the counter is complete. Returns {remaining, measured, weight, each} or None
    when the counter cannot give a rate yet."""
    if not total or done_since <= 0 or counted_seconds <= 0:
        return None
    each = counted_seconds / done_since
    measured = each * max(0, total - done) + max(0.0, tail or 0.0)
    fraction = max(0.0, min(1.0, done / total))
    weight = 1.0 if prior is None or overrun else math.sqrt(fraction)
    remaining = measured if prior is None else (1 - weight) * prior + weight * measured
    return {'remaining': round(max(0.0, remaining), 1), 'measured': round(measured, 1), 'weight': round(weight, 3),
            'each': round(each, 3)}


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


def estimate(order, dependencies, stages, expected, budget, live=None):
    """Percent, ETA and the chain the ETA waits on.

    order: every stage of the build. stages: {name: {'status', 'elapsed'}} for
    stages that started (status running, passed, failed or cancelled); others
    are pending. expected: expected_durations(). Percent weights each stage by
    its expected duration (the median of known stages for one without history);
    a running stage counts its elapsed share, at most 95 %. The ETA is the later
    of the longest remaining dependency chain and the remaining CPU work spread
    over the budget. live: {stage: remaining seconds} of running stages corrected from their work done
    (corrected_remaining); such a stage weighs its elapsed time plus that.
    """
    live = live or {}
    known = [entry['seconds'] for entry in expected.values() if entry.get('seconds')]
    fallback = statistics.median(known) if known else FALLBACK_SECONDS
    weight = {name: (expected.get(name) or {}).get('seconds') or fallback for name in order}
    status = {name: (stages.get(name) or {}).get('status', 'pending') for name in order}
    remaining, overrun, done_weight = {}, [], 0.0
    for name in order:
        state, wall = status[name], weight[name]
        elapsed = (stages.get(name) or {}).get('elapsed') or 0.0
        if state == 'running' and live.get(name) is not None:
            remaining[name] = live[name]
            weight[name] = elapsed + live[name]
            done_weight += elapsed
            continue
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
    unknown = [name for name in order if (expected.get(name) or {}).get('source', 'none') in ('none', NO_COMPARABLE)]
    incomparable = [name for name in order if (expected.get(name) or {}).get('source') == NO_COMPARABLE
                    and status[name] not in DONE and status[name] not in STOPPED]
    if basis and incomparable:   # not a confident number: say what it leaves out
        basis += ', lower bound: ' + NO_COMPARABLE + ' for ' + ', '.join(incomparable)
    return {'percent': percent, 'eta_seconds': None if eta is None else round(eta, 1), 'eta_basis': basis,
            'eta_lower_bound': bool(incomparable),
            'critical_path': path, 'critical_path_seconds': round(chain, 1), 'work_seconds': round(work, 1),
            'overrun': overrun, 'no_history': unknown, 'fallback_seconds': round(fallback, 1),
            'remaining': {name: round(value, 1) for name, value in remaining.items()}}


# --------------------------------------------------------------------------
# Tracker (in the builder; fed by the profiler session's hooks and sampler)

def clock_text(iso):
    """A clock time from an ISO stamp, in UTC and, when the host's offset is known, in local time.

    The builder runs in a container whose clock is UTC; the launcher passes the host's offset in
    AMIWIND_LOCAL_UTC_OFFSET (for example "+0300", the form `date +%z` prints) so a reader at the
    host sees both; without it the builder's own local offset is used (BUILD-ETA-CLOCK-UTC-ONLY-46)."""
    if not iso:
        return ''
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return iso[11:19]
    if moment.tzinfo is None:
        moment = moment.astimezone()
    utc = moment.astimezone(timezone.utc)
    text = utc.strftime('%H:%M:%S') + ' UTC'
    offset = (os.environ.get('AMIWIND_LOCAL_UTC_OFFSET', '').strip()
              or datetime.now().astimezone().strftime('%z'))
    match = re.fullmatch(r'([+-])(\d\d):?(\d\d)', offset)
    if match and (match.group(2), match.group(3)) != ('00', '00'):
        sign = 1 if match.group(1) == '+' else -1
        local = utc.astimezone(timezone(sign * timedelta(hours=int(match.group(2)), minutes=int(match.group(3)))))
        text += f" / {local.strftime('%H:%M:%S')} local ({match.group(1)}{match.group(2)}{match.group(3)})"
    return text


def _now_iso(epoch=None):
    moment = datetime.fromtimestamp(time.time() if epoch is None else epoch).astimezone()
    return moment.isoformat(timespec='seconds')


class Tracker:
    """Writes RUN/build-progress.json; every method is cheap and never raises into the build."""

    def __init__(self, run, order, dependencies, metadata, sampler=None, origin=None, interval=None, commands=None):
        self.run = Path(run)
        self.order = list(order)
        self.dependencies = {name: list(deps) for name, deps in (dependencies or {}).items()}
        self.budget = int(metadata.get('compiler_jobs', 1) or 1)
        self.sampler = sampler
        self.origin = time.monotonic() if origin is None else origin
        self.started_epoch = time.time() - (time.monotonic() - self.origin)
        reused = set(((metadata.get('stage_cache') or {}).get('reused') or {}).keys())
        samples, self.history_runs = history_samples(self.run)
        self.samples = samples
        self.counters = {}     # stage -> the counter it is corrected from (key, base time and units, completion)
        defaults = load_defaults()
        work = {}
        for name in self.order:
            measure = work_measure(name, (commands or {}).get(name))
            if measure:
                work[name] = measure
        self.expected = expected_durations(self.order, self.budget, samples, defaults, reused, work)
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
        try:
            self.eta_every = float(os.environ.get(ETA_LINE_ENV, DEFAULT_ETA_LINE))
        except ValueError:
            self.eta_every = DEFAULT_ETA_LINE
        self.eta_printed = time.monotonic()
        self.last = None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name='build-progress', daemon=True)
        self.writes = 0
        self.write()
        self.thread.start()

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self.write()
            if self.eta_every > 0 and time.monotonic() - self.eta_printed >= self.eta_every:
                self.eta_printed = time.monotonic()
                text = eta_line(self.last)
                if text:
                    print(text, flush=True)

    def _live(self, name, stage, row, elapsed, entry):
        """The running stage's estimate corrected from its work done (row['live']), or None."""
        now = time.time()
        current = row.get('phase') or {}
        if current.get('total'):
            counter = {'source': 'phase timer', 'name': current.get('name'), 'done': int(current.get('done') or 0),
                       'total': int(current['total']), 'unit': current.get('unit')}
            start = now - float(current.get('elapsed_seconds') or 0.0)
        else:
            counter = log_counter(self.run / 'logs' / f"{stage['number']:02}-{name}.log")
            if counter:
                counter['source'] = 'log counter'
            start = None
        phase = current.get('name')
        state = self.counters.get(name)
        if counter:
            key = (counter['source'], counter['name'], counter['total'], counter['unit'], phase)
            if state is None or state['key'] != key or counter['done'] < state['base_done']:
                state = {'key': key, 'base_epoch': start if start is not None else now,
                         'base_done': 0 if start is not None else counter['done'], 'complete_epoch': None}
                self.counters[name] = state
            if counter['done'] >= counter['total'] and state['complete_epoch'] is None:
                state['complete_epoch'] = now
            seen = stage.setdefault('units_seen', {})
            unit = counter['unit'] or 'units'
            seen[unit] = max(seen.get(unit, 0), counter['total'])
            row['counter'] = dict(counter)
        rows = self.samples.get(name) or ()
        prior, basis = entry.get('seconds'), entry.get('basis') or entry.get('source')
        unit = (counter or {}).get('unit') or 'units'
        if counter:
            per_unit = per_unit_expected(rows, unit, counter['total'], self.budget)
            if per_unit:
                prior = per_unit[0]
                basis = f'history per unit: {per_unit[1]:.2f} s each ({per_unit[2]} run(s)) x {counter["total"]} {unit}'
                row['expected_per_unit'] = {'seconds': round(per_unit[0], 1), 'each': round(per_unit[1], 3),
                                            'runs': per_unit[2], 'unit': unit, 'total': counter['total']}
        overrun = prior is not None and elapsed >= prior
        prior_left = None if prior is None else max(0.0, prior - elapsed)
        work_here = entry.get('work') or (counter or {}).get('total')

        def ratio(sample):
            there = sample.get('work') if entry.get('work') else (sample.get('units') or {}).get(unit)
            return work_here / there if work_here and there else 1.0

        phase_wall, tail = phase_history(rows, phase, ratio) if phase else (None, None)
        result = None
        if counter and state:
            tail_left = tail or 0.0
            if state['complete_epoch'] is not None and tail_left:
                tail_left = max(OVERRUN_MIN, tail_left - (now - state['complete_epoch']))
            result = corrected_remaining(prior_left, elapsed, now - state['base_epoch'],
                                         counter['done'] - state['base_done'], counter['done'], counter['total'],
                                         tail_left, overrun)
            if result:
                result.update(source=counter['source'], tail=round(tail_left, 1),
                              basis=(f"{counter['done']}/{counter['total']} {unit} done, {result['each']:.2f} s each "
                                     f"here ({counter['source']} '{counter['name']}'), weight {result['weight']:.2f} "
                                     f"against {basis or 'no history'}"
                                     + (f'; later phases {duration(tail_left)} from history' if tail else '')))
        if result is None and phase_wall is not None and (prior is None or overrun):
            left = max(OVERRUN_MIN, phase_wall - float(current.get('elapsed_seconds') or 0.0)) + (tail or 0.0)
            result = {'remaining': round(left, 1), 'source': 'phase history', 'weight': 1.0,
                      'basis': f"phase '{phase}' and the phases after it from history (the stage estimate "
                               f"{'is overrun' if overrun else 'is unknown'})"}
        if result:
            row['live'] = result
        return result

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

    def _phase_now(self, name, stage, row):
        """The running stage's current phase (its phase timer) and the builder's last heartbeat for it."""
        try:
            from build_profile import read_now
            current = read_now(self.run / 'profile' / 'sections' / f"{stage['number']:02}-{name}.jsonl")
        except Exception:  # noqa: BLE001
            current = None
        if current:
            row['phase'] = {key: current.get(key) for key in ('name', 'done', 'total', 'unit', 'label')}
            row['phase']['elapsed_seconds'] = round(max(0.0, time.time() - float(current.get('started_at') or 0)), 1)
        beat = getattr(self, 'heartbeat', None)
        state = (beat.state.get(name) if beat is not None else None)
        if state:
            row['heartbeat'] = dict(state)

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
        states, rows, warnings, live = {}, [], [], {}
        for name in self.order:
            stage = stages.get(name)
            entry = self.expected.get(name, {})
            row = {'name': name, 'status': stage['status'] if stage else 'pending',
                   'expected_seconds': entry.get('seconds'), 'expected_source': entry.get('source'),
                   'expected_basis': entry.get('basis')}
            if entry.get('work'):
                row.update(work=entry['work'], work_unit=entry.get('work_unit'))
            if stage:
                end = stage.get('end', now)
                elapsed = max(0.0, end - stage['start'])
                row.update(elapsed_seconds=round(elapsed, 1), jobs=stage.get('jobs'))
                states[name] = {'status': row['status'], 'elapsed': elapsed}
                if row['status'] == 'running':
                    self._phase_now(name, stage, row)
                    try:
                        corrected = self._live(name, self.stages.get(name, stage), row, elapsed, entry)
                    except Exception:  # noqa: BLE001 - the correction never stops progress
                        corrected = None
                    if corrected:
                        live[name] = corrected['remaining']
                    jobs = self._jobs_now(name, stage) or 1
                    row['jobs'] = jobs
                    points = per_stage.get(name, [])
                    recent = [cores for t, cores in points if t >= now - CORES_WINDOW]
                    row['cores_now'] = round(sum(recent) / len(recent), 2) if recent else None
                    # live form of the profiler's fix-item rule (build_profile.underused): a phase over 30 s
                    # on fewer than half of the stage's workers
                    if (row.get('phase') and (row['phase'].get('elapsed_seconds') or 0) > 30
                            and row['cores_now'] is not None and row['cores_now'] < 0.5 * jobs):
                        row['underused'] = True
                    if points:
                        idle = trailing_idle(points, IDLE_SHARE * jobs, interval)
                        row['idle_seconds'] = idle
                        if idle > IDLE_SECONDS:
                            low = [cores for t, cores in points if t >= points[-1][0] - idle]
                            warnings.append({'stage': name, 'cores': round(sum(low) / len(low), 2) if low else None,
                                             'jobs': jobs, 'seconds': idle})
            seen = (self.stages.get(name) or {}).get('units_seen')
            if seen:
                row['units_seen'] = dict(seen)   # the next build's per-unit history (run_units)
            rows.append(row)
        result = estimate(self.order, self.dependencies, states, self.expected, self.budget, live)
        if result['eta_basis'] and live:
            result['eta_basis'] += '; corrected from the work done: ' + ', '.join(
                f"{row['name']} ({row['live']['source']}"
                + (f", {row['counter']['done']}/{row['counter']['total']} {row['counter'].get('unit') or 'units'}"
                   if row.get('counter') and row['live']['source'] != 'phase history' else '') + ')'
                for row in rows if row['name'] in live)
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
        memory = self.memory_reading(now, [row['name'] for row in rows if row['status'] == 'running'])
        try:
            build_warnings = self.warnings_reading(now)
        except Exception:  # noqa: BLE001 - progress must never fail a build
            build_warnings = None
        return {'schema': SCHEMA, 'run': self.run.name, 'status': status,
                'started_at': _now_iso(self.started_epoch), 'updated_at': _now_iso(epoch),
                'updated_epoch': round(epoch, 3), 'interval': self.interval,
                'elapsed_seconds': round(now, 1), 'budget': self.budget,
                'percent': result['percent'], 'eta_seconds': eta, 'eta_basis': result['eta_basis'],
                'eta_at': _now_iso(epoch + eta) if eta is not None else None,
                'critical_path': result['critical_path'], 'critical_path_seconds': result['critical_path_seconds'],
                'work_seconds': result['work_seconds'], 'counts': counts,
                'cores_now': round(sum(recent_build) / len(recent_build), 2) if recent_build else None,
                'memory': memory,
                'warnings': build_warnings,
                'stages': rows, 'idle_warnings': warnings, 'build_idle': build_idle, 'host': host,
                'no_history': result['no_history'], 'fallback_seconds': result['fallback_seconds'],
                'history': {'runs': self.history_runs, 'defaults': self.defaults_used},
                'writes': self.writes + 1}

    def memory_reading(self, now, running):
        """The build's memory now and its peak so far (the Toolkit monitor's memory curve, TOOLKIT-MONITOR-NO-MEMORY-55):
        {'used_gib', 'limit_gib', 'source', 'peak_gib', 'peak_seconds', 'peak_stages'}, from the container's limit or,
        without one, the machine (resource_plan.build_memory); None when neither can be read. A new peak above
        PEAK_LOG_SHARE of the limit prints one [memory] line naming the stages that ran then."""
        try:
            from resource_plan import build_memory, cgroup_memory
            limit, used, cache = build_memory()
            source = 'container' if cgroup_memory()[0] is not None else 'machine'
        except Exception:  # noqa: BLE001 - progress must never fail a build
            return None
        if not limit or used is None:
            return None
        gib = float(1 << 30)
        live = max(0, used - cache) / gib
        peak = getattr(self, 'memory_peak', None)
        if peak is None or live > peak[0]:
            peak = (live, round(now, 1), list(running))
            self.memory_peak = peak
            logged = getattr(self, 'memory_peak_logged', 0.0)
            if live >= PEAK_LOG_SHARE * limit / gib and live >= logged + PEAK_LOG_STEP_GIB:
                self.memory_peak_logged = live
                print('[memory] new peak %.1f of %.1f GiB (%s) at +%s, running: %s' % (
                    live, limit / gib, source, duration(now), ', '.join(running) or 'nothing'), flush=True)
        # nearly out of memory: one WARNING line every LOW_RAM_REPEAT_SECONDS while under LOW_RAM_SHARE available (the
        # scheduler's guard cuts workers above its critical line; this says so in the log and in the monitor)
        available = max(0.0, limit / gib - live)
        low = available < LOW_RAM_SHARE * limit / gib
        warned = getattr(self, 'low_ram_warned', None)
        if low and (warned is None or now - warned >= LOW_RAM_REPEAT_SECONDS):
            self.low_ram_warned = now
            self.low_ram_count = getattr(self, 'low_ram_count', 0) + 1
            print('[memory] WARNING: RAM nearly exhausted: %.1f GiB available of %.1f (%s) at +%s, running: %s; the '
                  'memory guard holds new units back and cuts workers above its critical line' % (
                      available, limit / gib, source, duration(now), ', '.join(running) or 'nothing'), flush=True)
        return {'used_gib': round(live, 2), 'limit_gib': round(limit / gib, 2), 'source': source,
                'available_gib': round(available, 2), 'low': low, 'low_warnings': getattr(self, 'low_ram_count', 0),
                'peak_gib': round(peak[0], 2), 'peak_seconds': peak[1], 'peak_stages': peak[2]}

    def warnings_reading(self, now):
        """Every warning the build has printed so far, gathered from the stage logs (MONITOR-WARNINGS-ROW): the new
        bytes of each logs/*.log since the last snapshot are read, and each line matching WARNING_LINE is kept with the
        build time it was seen at and its stage; at most WARNINGS_KEPT lines are kept (the count goes on). Returns
        {'count', 'lines': [{'seconds', 'stage', 'line'}]}; a log that cannot be read is skipped (progress never fails)."""
        seen = getattr(self, 'warning_offsets', None)
        if seen is None:
            seen = self.warning_offsets = {}
            self.warning_lines, self.warning_count = [], 0
        try:
            logs = sorted((self.run / 'logs').glob('*.log'))
        except OSError:
            logs = []
        for log in logs:
            try:
                size = log.stat().st_size
                start = seen.get(log.name, 0)
                if size <= start:
                    continue
                with open(log, 'rb') as fh:
                    fh.seek(start)
                    data = fh.read(min(size - start, WARNINGS_READ_BYTES))
            except OSError:
                continue
            cut = data.rfind(b'\n') + 1          # a line still being written is read next time, whole
            if not cut:
                continue
            seen[log.name] = start + cut
            stage = re.sub(r'^\d+-', '', log.stem)
            for raw in data[:cut].decode('utf-8', 'replace').splitlines():
                if WARNING_LINE.search(raw):
                    self.warning_count += 1
                    if len(self.warning_lines) < WARNINGS_KEPT:
                        self.warning_lines.append({'seconds': round(now, 1), 'stage': stage, 'line': raw.strip()[:400]})
        return {'count': self.warning_count, 'lines': list(self.warning_lines)}

    def write(self):
        try:
            with self.write_lock:  # the builder thread and the timer thread
                data = self.snapshot()
                self.last = data
                self.writes += 1
                temporary = self.run / (PROGRESS_NAME + '.tmp')
                temporary.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
                temporary.replace(self.run / PROGRESS_NAME)
        except Exception:  # noqa: BLE001 - progress must never fail a build
            pass


def eta_line(progress):
    """The builder's periodic "[eta]" line from a progress record (None when nothing runs)."""
    if not progress or progress.get('status') != 'running':
        return None
    running = [row for row in progress.get('stages', []) if row.get('status') == 'running']
    if not running:
        return None
    eta = progress.get('eta_seconds')
    head = (f"[eta] {progress.get('percent') or 0:.1f} %, ETA "
            + (f"{duration(eta)} (at {clock_text(progress.get('eta_at'))})" if eta is not None else 'unknown'))
    parts = []
    for row in running:
        text = row['name']
        if row.get('live'):
            text += f": ~{duration(row['live']['remaining'])} left, {row['live']['basis']}"
        elif row.get('remaining_seconds') is not None:
            text += f": ~{duration(row['remaining_seconds'])} left ({row.get('expected_basis') or 'no history'})"
        parts.append(text)
    return head + ' | ' + ' | '.join(parts)


def start(run, order, dependencies, metadata, sampler=None, origin=None, commands=None):
    """The builder's progress tracker, or None when it cannot start. COMMANDS: {stage: command line},
    read for the work measures."""
    try:
        return Tracker(run, order, dependencies, metadata, sampler, origin, commands=commands)
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
        head += f", ETA {duration(progress['eta_seconds'])}" + (f" (at {clock_text(at)}, {progress.get('eta_basis')})" if at else '')
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
            elif row.get('expected_source') == NO_COMPARABLE:
                note.append(row.get('expected_basis') or NO_COMPARABLE)
            elif 'scaled' in (row.get('expected_basis') or ''):
                note.append(row['expected_basis'])
            elif row.get('expected_source') == 'default':
                note.append('default table')
            if row.get('live'):
                note.append('live: ' + row['live']['basis'])
            if row.get('overrun'):
                note.append('OVERRUN')
            current = row.get('phase')
            if current:
                where = current.get('name') or ''
                if current.get('total'):
                    where = '[%s/%s%s] %s' % (current.get('done') or 0, current['total'],
                                              ' ' + current['unit'] if current.get('unit') else '', where)
                note.append('%s %s' % (where, duration(current.get('elapsed_seconds'))))
            if row.get('heartbeat'):
                note.append('silent %s' % duration(row['heartbeat'].get('silent_seconds')))
            if row.get('underused'):
                note.append('UNDERUSED (under half of its workers)')
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
