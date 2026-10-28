# SPDX-License-Identifier: GPL-3.0-only
"""Resource plan: the memory and threads each stage of a build needs, against what the build gets, before any stage.

Part of the input checks of every build (docs/BUILD_PROFILE.md "Resource plan"): from the build's own plan (the stages
that will actually run, after the reuse plan) and the measured history of earlier builds, every stage gets an estimate
of its parent process, its memory per worker unit, its largest single unit, the workers it will use, its peak total
memory, its threads and its wall time. Those are compared with the container the build runs in (cgroup memory.max and
cpu.max, or --resource-memory-gb / --resource-threads) and printed as a short checklist, one line per stage:

    OK              the stage runs with its planned workers
    WILL THROTTLE   fewer workers than planned (the number, and the reason: memory or threads)
    WILL NOT FIT    one unit alone is larger than the memory: the build is refused before any stage runs

and one ADVISORY line when more memory or threads would make the build measurably faster (the lease to ask for).

Models, each labelled with where its numbers come from:

* measured: the build-profile.json of earlier runs (the --reuse-from run and the runs it reused from, only stages
  that really ran there) and the workspace's own estimate-vs-actual history (WORKSPACE/cache/resource-history.jsonl,
  one line per stage after every passed build); per stage the largest single process (the parent, or one unit) and
  the memory of each further worker (peak memory less the largest process, over the workers it ran);
* the stair walk model (tools/chim/stair_pool.py, calibrated on the v0.0.41 world and the v0.0.42 Vivec frame:
  128 MiB + 18 x the frame's placed MiB per walk worker) for every stage that builds a CHIM world: the largest frame
  from the stair gate's own log line of an earlier run, else estimated from the stored frame's size on disk;
* estimated, no data yet: a stage never measured (512 MiB a worker, 256 MiB parent).

The plan is recorded as RESOURCE-PLAN.json in the run folder (schema resource-plan-1, SCHEMA_DOCUMENT below, validated
like the other receipts); after a passed build the actual peaks of every stage are written next to the estimates, a
stage whose actual peak is more than 25 % over its estimate is flagged, and the measured rows join the history, so the
models calibrate themselves.

While a build runs, the worker pools follow the memory and the CPU quota the container has at that moment
(MemoryGovernor, used by tools/build_parallel.py): a throttled stage grows back toward its planned workers when memory
frees up (for example a raised lease) and stops handing out new units when memory gets tight; a running unit is never
stopped.
"""
import json
import math
import os
import re
import time
from pathlib import Path

SCHEMA = 'resource-plan-1'
FILE = 'RESOURCE-PLAN.json'
HISTORY = 'resource-history.jsonl'
HISTORY_FORMAT = 'AmiWind resource history 1'
HEADROOM = 0.8                  # of the container's memory a build plans with (as the stair gate: tools/chim/stair_pool)
OVER_ESTIMATE = 1.25            # an actual peak more than 25 % over its estimate is flagged
DEFAULT_WORKER_MIB = 512        # estimated, no data yet
DEFAULT_PARENT_MIB = 256
CHAIN_RUNS = 6                  # runs read along the reuse chain for measurements
HISTORY_ROWS = 5                # newest history measurements per stage
ADVISORY_MIN_GAIN = 0.02        # an advisory only when the build would be at least 2 % faster
GOVERNOR_SECONDS = 30.0         # how often a running pool re-reads the container's memory and CPU quota
GOVERNOR_ENV = 'AMIWIND_GOVERNOR_SECONDS'
UNIT_MIB_ENV = 'AMIWIND_STAGE_UNIT_MIB'          # a stage's memory per worker unit (set by the scheduler from the plan)
PARENT_MIB_ENV = 'AMIWIND_STAGE_PARENT_MIB'
# The stored frame on disk vs its placed bytes (the stair model's input): whole-city Vivec, v0.0.42, 74 MiB of frame
# files for 150 MiB placed (chunk images plus the model image of every placement). One calibration point.
PLACED_PER_STORED = 2.03
# A worker unit is one process and at most one child of it (a converter it runs), neither larger than the stage's largest
# process: a measured row whose memory a worker exceeds that is not the stage's own (the container's peak taken for the
# stage's tree, BUILD-PLAN-MWSCRIPT-32GB-54) and is capped to it.
PLAUSIBLE_WORKER_PER_LARGEST = 2.0
# Like for like (BUILD-PLAN-SCOPE-54): a MiniWind's stages do a fraction of a full build's work (one area, not the
# island), so a plan uses only measurements of builds of its own scope; a stage measured only in builds of the other
# scope gets the no-data estimate, the other scope's numbers named in its model line.
SCOPES = ('miniwind', 'full')
MIB = float(1 << 20)
GIB = float(1 << 30)


# --------------------------------------------------------------------------
# What the build gets

def _read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _int(text):
    try:
        return None if text in (None, '', 'max') else int(text)
    except ValueError:
        return None


def cgroup_memory(root='/sys/fs/cgroup'):
    """(limit bytes or None, in use bytes or None, reclaimable file cache bytes) of this container (cgroup v2, else
    v1); limit None without a limit."""
    root = Path(root)
    limit, used = _int(_read(root / 'memory.max')), _int(_read(root / 'memory.current'))
    stat = _read(root / 'memory.stat')
    if limit is None and used is None:
        limit = _int(_read(root / 'memory' / 'memory.limit_in_bytes'))
        used = _int(_read(root / 'memory' / 'memory.usage_in_bytes'))
        stat = _read(root / 'memory' / 'memory.stat')
    if limit is not None and limit >= (1 << 50):
        limit = None
    cache = 0
    for line in (stat or '').splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in ('inactive_file', 'total_inactive_file'):
            cache = max(cache, _int(parts[1]) or 0)
    return limit, used, cache


def cgroup_threads(root='/sys/fs/cgroup'):
    """The CPU quota in threads (cgroup v2 cpu.max, else v1 cfs), or None without a quota."""
    root = Path(root)
    text = _read(root / 'cpu.max')
    if text:
        parts = text.split()
        if len(parts) == 2 and parts[0] != 'max':
            try:
                return max(1, int(math.ceil(int(parts[0]) / float(int(parts[1])))))
            except (ValueError, ZeroDivisionError):
                return None
        return None
    quota, period = _int(_read(root / 'cpu' / 'cpu.cfs_quota_us')), _int(_read(root / 'cpu' / 'cpu.cfs_period_us'))
    if quota and period and quota > 0:
        return max(1, int(math.ceil(quota / float(period))))
    return None


def host_threads():
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def host_memory():
    """MemTotal and MemAvailable of the machine (bytes), or (None, None)."""
    total = free = None
    for line in (_read('/proc/meminfo') or '').splitlines():
        if line.startswith('MemTotal:'):
            total = int(line.split()[1]) * 1024
        elif line.startswith('MemAvailable:'):
            free = int(line.split()[1]) * 1024
    return total, free


def limits(memory_gb=None, threads=None, root='/sys/fs/cgroup'):
    """What the build gets: {'memory_bytes', 'memory_source', 'used_bytes', 'threads', 'threads_source'}. Given values
    (--resource-memory-gb / --resource-threads: the container the build will run in, e.g. a lease) win over this
    process's own cgroup, which wins over the machine."""
    limit, used, _cache = cgroup_memory(root)
    total, _free = host_memory()
    if memory_gb is not None:
        memory, msource, used = int(float(memory_gb) * GIB), 'asked (--resource-memory-gb %g)' % float(memory_gb), 0
    elif limit is not None:
        memory, msource = limit, 'container limit (cgroup memory.max)'
    elif total is not None:
        memory, msource = total, 'no container limit: the machine (MemTotal)'
    else:
        memory, msource = None, 'unknown'
    quota = cgroup_threads(root)
    if threads is not None:
        count, tsource = int(threads), 'asked (--resource-threads %d)' % int(threads)
    elif quota is not None:
        count, tsource = min(quota, host_threads()), 'container CPU quota (cgroup cpu.max)'
    else:
        count, tsource = host_threads(), 'no CPU quota: the machine'
    return {'memory_bytes': memory, 'memory_source': msource, 'used_bytes': used or 0,
            'threads': count, 'threads_source': tsource, 'machine_bytes': total, 'machine_threads': host_threads()}


# --------------------------------------------------------------------------
# Measurements of earlier runs

def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def chain(run, hops=CHAIN_RUNS):
    """The run and the runs it reused from (build-profile.json reuse_from), newest first; folders that exist."""
    out, seen = [], set()
    current = Path(run) if run else None
    while current is not None and len(out) < hops:
        key = str(current)
        if key in seen or not current.is_dir():
            break
        seen.add(key)
        out.append(current)
        profile = _json(current / 'build-profile.json') or {}
        nxt = profile.get('reuse_from') or ((_json(current / 'build-state.json') or {}).get('stage_cache') or {}).get(
            'reuse_from')
        current = Path(nxt) if nxt else None
    return out


def _stage_cgroup_peak(row, timeline):
    """The container's peak memory while the stage ran (bytes), from the profiler's timeline, or None."""
    if not timeline:
        return None
    memory = timeline.get('memory_bytes') or []
    rows = (timeline.get('stages') or {}).get(row.get('name')) or []
    values = [memory[index] for index, _cores in rows if 0 <= index < len(memory) and memory[index]]
    if not values:
        times = timeline.get('t') or []
        values = [m for t, m in zip(times, memory) if m and row.get('start', 0) <= t <= row.get('end', 0)]
    return max(values) if values else None


def measure(row, timeline=None):
    """One stage row of a build profile -> a measurement: {'jobs', 'largest_mib' (the largest single process),
    'total_mib' (peak memory of the stage: its process tree, bounded by the container's own peak while it ran),
    'worker_mib' (the total less the largest process, per worker), 'wall', 'cores'}; None for a reused stage or a row
    without memory numbers."""
    if row.get('reused') or row.get('status') not in (None, 'passed', 'failed'):
        return None
    failed = row.get('status') == 'failed'
    largest = row.get('peak_process_rss_bytes')
    tree = row.get('peak_tree_rss_bytes')
    cgroup = _stage_cgroup_peak(row, timeline)
    if not largest and not tree:
        return None
    # a process tree's summed RSS counts shared pages once per process: the container's own peak bounds it. Without a
    # tree sample (a stage shorter than the sampler's interval) the container's peak is no measure of the stage: it
    # holds every stage beside it (BUILD-PLAN-MWSCRIPT-32GB-54: v0.0.48-dev2 try14's 0.7 s mwscript stage, largest
    # process 24.8 MiB, was recorded as 32,412 MiB a worker, the container's peak, and refused MiniWinds as WILL NOT FIT)
    total = min(v for v in (tree, cgroup) if v) if tree else largest
    largest = largest or total
    total = max(total, largest)
    jobs = max(1, int(row.get('jobs_max') or row.get('jobs') or 1))
    found = {'jobs': jobs, 'largest_mib': round(largest / MIB, 1), 'total_mib': round(total / MIB, 1),
             'worker_mib': round(max(0.0, total - largest) / MIB / jobs, 1),
             'wall': float(row.get('wall') or 0.0), 'cores': float(row.get('cores_avg') or 0.0)}
    if cgroup:
        # the whole container's peak while the stage ran: its own tree plus the stages beside it
        # (BUILD-SCHEDULER-MEMORY-STARVED-42: the chim stage planned alone at 21 GB met 26.5 GB in use)
        found['container_mib'] = round(cgroup / MIB, 1)
    if failed:
        # a failed stage still shows how much memory it reached (at least that much is needed); its time does not
        found.update(wall=None, cores=None, failed=True)
    return found


STAIR_LINE = re.compile(r'CHIM stair gate: workers: .*; largest frame (\S+) about (\d+(?:\.\d+)?) MiB a worker')


def stair_from_logs(run):
    """(frame, MiB a walk worker) of the largest frame the stair gate of RUN walked (its own log line), or None."""
    best = None
    logs = Path(run) / 'logs'
    if not logs.is_dir():
        return None
    for log in sorted(logs.glob('*chim*.log')):
        try:
            with log.open(encoding='utf-8', errors='replace') as handle:
                for line in handle:
                    if 'largest frame' not in line:
                        continue
                    found = STAIR_LINE.search(line)
                    if found and (best is None or float(found.group(2)) > best[1]):
                        best = (found.group(1), float(found.group(2)))
        except OSError:
            continue
    return best


def _folder_bytes(folder):
    total = 0
    for base, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return total


def stair_from_frames(run):
    """(frame, estimated MiB a walk worker) of the largest stored frame of RUN's CHIM world (its frame folder's bytes
    x PLACED_PER_STORED as the placed MiB of the stair model), or None."""
    from chim.stair_pool import WORKER_BASE_MIB, WORKER_MIB_PER_PLACED_MIB
    best = None
    for frames in sorted(Path(run).glob('chim-world*/chim/frames')) + sorted(Path(run).glob('chim-town-*/chim/frames')):
        for column in sorted(p for p in frames.iterdir() if p.is_dir()):
            for frame in sorted(p for p in column.iterdir() if p.is_dir()):
                stored = _folder_bytes(frame) / MIB
                if best is None or stored > best[1]:
                    best = ('%s/%s' % (column.name, frame.name), stored)
    if best is None:
        return None
    return best[0], round(WORKER_BASE_MIB + WORKER_MIB_PER_PLACED_MIB * best[1] * PLACED_PER_STORED, 1)


def run_scope(run, recorded=None):
    """'miniwind' or 'full': the scope of the build RUN (a run folder path). RECORDED (a history row's own 'scope')
    wins; then the run's build-state.json (a MiniWind preset, or --miniwind... in its command line); then its name (the
    naming rule: YYYY_MM_DD_vX.Y.Z_miniwind-<scene>_<git>). None when nothing tells."""
    if recorded in SCOPES:
        return recorded
    if not run:
        return None
    state = _json(Path(run) / 'build-state.json')
    if isinstance(state, dict) and ('miniwind_preset' in state or state.get('build_argv')):
        argv = [str(part) for part in state.get('build_argv') or ()]
        mini = state.get('miniwind_preset') or any(part.startswith('--miniwind') for part in argv)
        return 'miniwind' if mini else 'full'
    return 'miniwind' if '_miniwind-' in Path(str(run)).name else 'full'


def plausible(row):
    """ROW (a measurement) with its per-worker memory capped at PLAUSIBLE_WORKER_PER_LARGEST x its largest process,
    marked 'capped' with the measured value; the row itself when it is plausible."""
    largest = float(row.get('largest_mib') or 0.0)
    limit = PLAUSIBLE_WORKER_PER_LARGEST * largest
    if largest <= 0 or float(row.get('worker_mib') or 0.0) <= limit:
        return row
    jobs = max(1, int(row.get('jobs') or 1))
    return dict(row, worker_mib=round(limit, 1), total_mib=round(largest + jobs * limit, 1),
                capped={'worker_mib': row.get('worker_mib'), 'total_mib': row.get('total_mib')})


def read_history(workspace):
    """{stage: [measurement, ...]} newest last, from WORKSPACE/cache/resource-history.jsonl."""
    out = {}
    path = Path(workspace) / 'cache' / HISTORY if workspace else None
    if path is None or not path.is_file():
        return out
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and isinstance(item.get('measured'), dict) and item.get('stage'):
            out.setdefault(item['stage'], []).append(dict(item['measured'], run=item.get('run'),
                                                          estimate_total_mib=item.get('estimate_total_mib'),
                                                          **({'scope': item['scope']} if item.get('scope') else {})))
    return out


def gather(reuse_from=None, workspace=None, extra_runs=(), scope=None, stair_walk=None):
    """Every measurement this plan can use: {'stages': {stage: [measurement + 'run' + 'scope']}, 'stair': (frame, MiB,
    source) or None, 'runs': [run, ...], 'scope': SCOPE (the planned build's, 'miniwind' or 'full'; None: every
    measurement counts, the earlier method), 'stair_walk': STAIR_WALK (the build's stair walk scope; 'off': no stair
    figure is looked for)}. History rows: the newest HISTORY_ROWS per stage and scope."""
    stages, runs = {}, []
    order = []
    for start in [reuse_from, *extra_runs]:
        for run in chain(start) if start else ():
            if str(run) not in runs:
                runs.append(str(run))
                order.append(run)
    stair = None
    walks = stair_walk != 'off'
    scopes = {}
    for run in order:
        scopes[str(run)] = run_scope(run)
        profile = _json(run / 'build-profile.json') or {}
        timeline = profile.get('timeline')
        for row in profile.get('stages') or []:
            found = measure(row, timeline)
            if found:
                stages.setdefault(row['name'], []).append(dict(found, run=str(run), scope=scopes[str(run)]))
        if stair is None and walks:
            logged = stair_from_logs(run)
            if logged:
                stair = (logged[0], logged[1], 'measured: the stair gate of %s' % run.name)
    if stair is None and walks:
        for run in order:
            stored = stair_from_frames(run)
            if stored:
                stair = (stored[0], stored[1], 'estimated from the stored frame size of %s' % run.name)
                break
    for name, rows in read_history(workspace).items():
        newest = {}
        for row in rows:
            run = row.get('run')
            if run not in scopes:
                scopes[run] = run_scope(run)
            row = dict(row, scope=run_scope(run, row.get('scope')) if row.get('scope') else scopes[run])
            newest.setdefault(row['scope'], []).append(row)
        for kept in newest.values():
            stages.setdefault(name, []).extend(kept[-HISTORY_ROWS:])
    return {'stages': stages, 'stair': stair, 'runs': runs, 'scope': scope, 'stair_walk': stair_walk}


# --------------------------------------------------------------------------
# Models

def builds_chim_world(command):
    return any('chim_build.py' in str(part) for part in command or ())


def stage_model(name, command, measurements, stair=None, scope=None, stair_walk=None):
    """{'source', 'parent_mib', 'worker_mib', 'unit_mib', 'largest_unit', 'ref_jobs', 'ref_wall', 'ref_cores', 'runs'}
    of one stage, from its measurements (conservative: the largest of them; each capped by plausible()) and, for a CHIM
    world stage that walks stairs, the stair walk model. SCOPE ('miniwind' or 'full', the planned build's): only
    measurements of that scope count (a row without one counts everywhere); STAIR_WALK 'off' (the build's
    --stair-walk): no stair model, nothing is walked (BUILD-PLAN-STAIR-WALK-OFF-54)."""
    rows = [plausible(r) for r in measurements or []]
    other = []
    if scope in SCOPES:
        other = [r for r in rows if r.get('scope') not in (None, scope)]
        rows = [r for r in rows if r.get('scope') in (None, scope)]
    if rows:
        parent = max(r['largest_mib'] for r in rows)
        worker = max(r['worker_mib'] for r in rows)
        timed = [r for r in rows if r.get('wall') is not None]
        newest = timed[0] if timed else {'jobs': rows[0]['jobs'], 'wall': None, 'cores': None}
        model = {'source': 'measured (%d run%s%s)' % (len(rows), '' if len(rows) == 1 else 's',
                                                    ', %d failed' % (len(rows) - len(timed)) if len(timed) < len(rows)
                                                    else ''),
                 'parent_mib': parent, 'worker_mib': worker, 'unit_mib': max(parent, worker),
                 'largest_unit': 'the stage\'s largest process (measured %.0f MiB)' % parent,
                 'ref_jobs': newest['jobs'], 'ref_wall': round(newest['wall'], 1) if newest['wall'] is not None else None,
                 'ref_cores': round(newest['cores'], 2) if newest['cores'] is not None else None, 'runs': sorted({r.get('run') or '' for r in rows} - {''}),
                 # memory the stages beside it held at its peak, as measured (container peak less its own tree)
                 'beside_mib': max([0.0] + [max(0.0, r['container_mib'] - r['total_mib']) for r in rows
                                            if r.get('container_mib')])}
    else:
        model = {'source': 'estimated, no data yet', 'parent_mib': DEFAULT_PARENT_MIB,
                 'worker_mib': DEFAULT_WORKER_MIB, 'unit_mib': DEFAULT_WORKER_MIB,
                 'largest_unit': 'unknown (no measurement)', 'ref_jobs': None, 'ref_wall': None, 'ref_cores': None,
                 'runs': [], 'beside_mib': 0.0}
        if other:
            model['source'] = ('estimated, no data yet for a %s build (measured only in %s builds, largest process '
                               '%.0f MiB: not like for like)' % (scope, other[0].get('scope'),
                                                                max(r['largest_mib'] for r in other)))
    if stair_walk == 'off':
        stair = None
    if stair and builds_chim_world(command):
        frame, mib, how = stair
        if mib >= model['worker_mib']:
            model['worker_mib'] = mib
            model['largest_unit'] = 'stair walk of frame %s (about %.0f MiB a worker; %s)' % (frame, mib, how)
        model['unit_mib'] = max(model['unit_mib'], mib)
        model['stair'] = {'frame': frame, 'worker_mib': mib, 'source': how,
                          'model': 'tools/chim/stair_pool.py: 128 MiB + 18 x placed MiB'}
        if not rows:
            model['source'] = 'stair model (%s); rest estimated, no data yet' % how
        else:
            model['source'] += ' + stair model'
    return model


def _wall(model, workers):
    """Expected wall seconds of the stage at WORKERS, or None. Amdahl's law fitted to the measurement: a stage that
    ran W seconds on J workers and kept C cores busy on average has a parallel share p with 1 / ((1 - p) + p / J) = C;
    at N workers it takes W x ((1 - p) + p / N) / ((1 - p) + p / J). A stage that kept one core busy gains nothing."""
    if model.get('ref_wall') is None:
        return None
    wall = float(model['ref_wall'])
    jobs = max(1, int(model.get('ref_jobs') or 1))
    cores = max(1.0, min(float(model.get('ref_cores') or 1.0), float(jobs)))
    share = 0.0 if jobs <= 1 else max(0.0, min(1.0, (1 - 1 / cores) / (1 - 1 / float(jobs))))
    at = lambda n: (1 - share) + share / float(max(1, n))
    return round(wall * at(workers) / at(jobs), 1)


def _waits_for(steps):
    """{stage: every stage it waits for, directly or through others} from the scheduler's own table
    (build_parallel.stage_dependencies); a step list it does not know waits for nothing."""
    try:
        from build_parallel import stage_dependencies
        deps = stage_dependencies(steps)
    except (ImportError, ValueError, KeyError):
        deps = {}
    found = {}

    def walk(name, seen=()):
        if name not in found:
            found[name] = set()
            for dep in deps.get(name, ()):
                if dep not in seen:
                    found[name] |= {dep} | walk(dep, seen + (name,))
        return found[name]
    for name, _ in steps:
        walk(name)
    return found


def plan(steps, running, jobs, got, gathered, reuse_from=None, stair_walk=None):
    """The resource plan document (schema resource-plan-1) of STEPS [(name, command)] of which RUNNING (names) will
    actually run, at --jobs JOBS, against GOT (limits()); the build's scope is GATHERED's (gather(scope=)), STAIR_WALK
    its stair walk scope ('off', 'flights', 'all'; None: GATHERED's, else not known and the stair model counts)."""
    scope = gathered.get('scope')
    stair_walk = stair_walk or gathered.get('stair_walk')
    memory_mib = got['memory_bytes'] / MIB if got.get('memory_bytes') else None
    room = memory_mib * HEADROOM if memory_mib else None
    threads = max(1, int(got.get('threads') or jobs or 1))
    jobs = max(1, int(jobs or 1))
    rows, refusals, models = [], [], {}
    # a stage without --jobs runs one process (the scheduler holds one worker for it)
    plans = {name: jobs if '--jobs' in [str(part) for part in command or ()] else 1 for name, command in steps}
    for name, command in steps:
        if name in running:
            models[name] = stage_model(name, command, gathered['stages'].get(name), gathered.get('stair'), scope,
                                       stair_walk)
    # BUILD-PLAN-BESIDE-STALE-48: the memory measured beside a stage in an earlier run counts only up to what the
    # other stages running in THIS build can hold at full speed; a reuse build that reruns four stages planned the
    # room batches at 1 of 24 workers against 43 GB that stages it no longer runs held in the measured run
    full = {n: m['parent_mib'] + plans[n] * m['worker_mib'] for n, m in models.items()}
    after = _waits_for(steps)
    for name, command in steps:
        if name not in running:
            continue
        model = models[name]
        planned = plans[name]
        by_threads = min(planned, threads)
        # only a stage that neither waits for this one nor is waited for can run beside it (the image waits for all)
        beside = min(model.get('beside_mib') or 0.0,
                     sum(v for n, v in full.items() if n != name and n not in after[name]
                         and name not in after[n]))
        if room is None or model['worker_mib'] <= 0:
            by_memory = planned
        else:
            fixed = model['parent_mib'] + beside
            by_memory = int((room - fixed) // model['worker_mib']) if room > fixed else 0
        status, reasons = 'OK', []
        if room is not None and model['unit_mib'] > room:
            status = 'WILL NOT FIT'
            reasons.append('one unit (%s) needs about %.0f MiB, the build plans with %.0f MiB (%.0f %% of %.1f GiB)'
                           % (model['largest_unit'], model['unit_mib'], room, HEADROOM * 100, memory_mib / 1024.))
            workers = 0
        else:
            workers = max(1, min(planned, by_threads, by_memory))
            if workers < planned:
                status = 'WILL THROTTLE'
                if by_memory < planned:
                    reasons.append('memory holds %d worker%s at about %.0f MiB each beside a %.0f MiB parent%s'
                                   % (max(1, by_memory), '' if by_memory == 1 else 's', model['worker_mib'],
                                      model['parent_mib'], ' and %.0f MiB the stages beside it held when it was '
                                      'measured' % beside if beside else ''))
                if by_threads < planned:
                    reasons.append('%d threads (%s)' % (threads, got.get('threads_source')))
        peak = model['parent_mib'] + max(workers, 1) * model['worker_mib']
        need = model['parent_mib'] + planned * model['worker_mib']
        lease_gb = math.ceil((need + beside) / HEADROOM / 1024.)   # the container memory for full speed
        row = {'stage': name, 'status': status, 'reasons': reasons, 'model': model['source'],
               'parent_mib': round(model['parent_mib'], 1), 'worker_mib': round(model['worker_mib'], 1),
               'largest_unit': model['largest_unit'], 'unit_mib': round(model['unit_mib'], 1),
               'planned_workers': planned, 'workers': workers, 'threads': min(workers or 1, threads),
               'peak_total_mib': round(peak, 1), 'full_speed_mib': round(need, 1),
               'wall_s': _wall(model, workers or 1), 'full_speed_wall_s': _wall(model, planned),
               'beside_mib': round(beside, 1), 'lease_gb_full_speed': lease_gb}
        if status != 'OK':
            reasons.append('a lease of %d GB runs it at its %d planned workers' % (lease_gb, planned))
        if model.get('stair'):
            row['stair'] = model['stair']
        if model['runs']:
            row['measured_in'] = model['runs'][:CHAIN_RUNS]
        rows.append(row)
        if status == 'WILL NOT FIT':
            refusals.append('%s: %s' % (name, reasons[0]))
    walls = [r['wall_s'] for r in rows if r['wall_s'] is not None]
    fulls = [r['full_speed_wall_s'] for r in rows if r['full_speed_wall_s'] is not None]
    doc = {'schema': SCHEMA, 'written': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'jobs': jobs,
           'got': {'memory_mib': round(memory_mib, 1) if memory_mib else None,
                   'memory_source': got.get('memory_source'), 'threads': threads,
                   'threads_source': got.get('threads_source'), 'headroom': HEADROOM},
           'reuse_from': str(reuse_from) if reuse_from else None, 'measured_runs': gathered.get('runs', []),
           'stages_total': len(steps), 'stages_running': len(rows), 'stages': rows,
           'wall_s': round(sum(walls), 1) if walls else None,
           'full_speed_wall_s': round(sum(fulls), 1) if fulls else None,
           'refusals': refusals, 'advisory': advisory(rows, got, threads, jobs, models)}
    if scope in SCOPES:
        doc['scope'] = scope
    if stair_walk:
        doc['stair_walk'] = str(stair_walk)
    doc['verdict'] = 'refused' if refusals else 'throttled' if any(r['status'] != 'OK' for r in rows) else 'ok'
    return doc


def _workers_at(row, model, room_mib, threads):
    if model['worker_mib'] <= 0:
        fit = row['planned_workers']
    else:
        fit = int((room_mib - model['parent_mib']) // model['worker_mib']) if room_mib > model['parent_mib'] else 0
    return max(1, min(row['planned_workers'], threads, fit))


def advisory(rows, got, threads, jobs, models=None):
    """{'gain', 'memory_gb', 'threads', 'more_memory_gb', 'more_threads', 'text'} when giving the build more memory or
    threads (never more than the machine has) makes it at least ADVISORY_MIN_GAIN faster, else None. Wall times add
    up the stages (they overlap in a parallel build, so the gain is an estimate); a throttled stage without a measured
    time counts by the share of its planned workers it gets back (an upper bound, said so)."""
    models = models or {}
    throttled = [r for r in rows if r['status'] == 'WILL THROTTLE' and r['stage'] in models]
    if not throttled:
        return None
    have_gb = (got.get('memory_bytes') or 0) / GIB
    need_mib = max(r['full_speed_mib'] for r in throttled) / HEADROOM
    memory_gb = int(math.ceil(max(need_mib / 1024., have_gb)))
    machine_gb = (got.get('machine_bytes') or 0) / GIB
    capped = ''
    if machine_gb and memory_gb > machine_gb:
        # never advise more than the machine has: the most it could give, and say so
        capped = ' (full speed needs about %d GiB, more than the machine has, %.0f GiB)' % (memory_gb, machine_gb)
        memory_gb = max(int(math.floor(have_gb + 1e-9)), int(math.floor(machine_gb)))
    # the threads the build can use: its largest planned stage (--jobs), never more than the machine has
    want_threads = max(r['planned_workers'] for r in rows)
    machine_threads = got.get('machine_threads')
    if machine_threads:
        want_threads = min(want_threads, int(machine_threads))
    room = memory_gb * 1024. * HEADROOM
    now = later = 0.0
    bound, worst = 0.0, None
    for r in rows:
        if r['wall_s'] is None:
            continue
        now += r['wall_s']
        later += _wall(models[r['stage']], _workers_at(r, models[r['stage']], room, want_threads))             if r['stage'] in models and r['status'] == 'WILL THROTTLE' else r['wall_s']
    for r in throttled:
        if r['wall_s'] is None:
            back = _workers_at(r, models[r['stage']], room, want_threads)
            share = 1 - r['workers'] / float(back)
            if share > bound:
                bound, worst = share, (r, back)
    gain = (now - later) / now if now > 0 else 0.0
    if worst is not None and bound > gain:
        r, back = worst
        gain = bound
        scope = 'up to %.0f %% faster in %s (no measured time: by its workers, %d instead of %d)' % (
            bound * 100, r['stage'], back, r['workers'])
    else:
        scope = 'about %.0f %% faster' % (gain * 100)
    if gain < ADVISORY_MIN_GAIN:
        return None
    more_m = max(0, memory_gb - int(math.floor(have_gb + 1e-9)))
    more_t = max(0, want_threads - threads)
    asks = [x for x in ('%d GiB more memory' % more_m if more_m else '',
                        '%d more threads' % more_t if more_t else '') if x]
    if not asks:
        return None
    return {'gain': round(gain, 3), 'memory_gb': memory_gb, 'threads': want_threads, 'more_memory_gb': more_m,
            'more_threads': more_t,
            'text': 'this build would run %s with %s (the lease to ask for: --threads %d --mem-gb %d)%s'
                    % (scope, ' / '.join(asks), want_threads, memory_gb, capped)}


# --------------------------------------------------------------------------
# Output

def checklist(doc):
    """The printed checklist: a header, one line per running stage, the advisory or the verdict."""
    got = doc['got']
    lines = ['Resource plan: %d of %d stages run; the build gets %s MiB (%s) and %d threads (%s); --jobs %d'
             % (doc['stages_running'], doc['stages_total'],
                '%.0f' % got['memory_mib'] if got['memory_mib'] else 'unknown', got['memory_source'],
                got['threads'], got['threads_source'], doc['jobs'])]
    for r in doc['stages']:
        detail = ('%d of %d workers' % (r['workers'], r['planned_workers']) if r['status'] != 'WILL NOT FIT'
                  else 'refused before any stage')
        lines.append('  %-13s %-24s %s; about %.0f MiB a worker + %.0f MiB parent, peak about %.0f MiB, %s%s [%s]'
                     % (r['status'], r['stage'], detail, r['worker_mib'], r['parent_mib'], r['peak_total_mib'],
                        'wall about %s' % _seconds(r['wall_s']) if r['wall_s'] is not None else 'wall unknown',
                        (': ' + '; '.join(r['reasons'])) if r['reasons'] else '', r['model']))
    if doc['advisory']:
        lines.append('ADVISORY: ' + doc['advisory']['text'])
    # stages with no measured time are not in the sum: named, so a short total is never read as the build's time
    # (BUILD-PLAN-WALL-UNMEASURED-54: v0.0.54 seyda-ui 3d6b612 planned about 8 min and took about 45, mostly the
    # chim-town-seyda stage, which had no MiniWind measurement)
    unknown = [r['stage'] for r in doc['stages'] if r['wall_s'] is None]
    lines.append('Resource plan: %s (%d OK, %d WILL THROTTLE, %d WILL NOT FIT)%s%s' % (
        doc['verdict'].upper(), sum(1 for r in doc['stages'] if r['status'] == 'OK'),
        sum(1 for r in doc['stages'] if r['status'] == 'WILL THROTTLE'),
        sum(1 for r in doc['stages'] if r['status'] == 'WILL NOT FIT'),
        '; expected wall about %s (stages added up)' % _seconds(doc['wall_s']) if doc['wall_s'] else '',
        '; time not known for %d stage%s (no measurement of this build\'s scope): %s' % (
            len(unknown), '' if len(unknown) == 1 else 's', ', '.join(unknown)) if unknown else ''))
    return lines


def _seconds(value):
    if value is None:
        return '?'
    value = int(round(value))
    return '%dh%02dm' % (value // 3600, value % 3600 // 60) if value >= 3600 else '%dm%02ds' % (value // 60, value % 60)


# The schema of RESOURCE-PLAN.json (JSON schema subset, checked with tools/aw.py validate). Kept here, not as a file in
# config/schemas: the stages that read that folder would take a new file there as a change of their inputs.
SCHEMA_DOCUMENT = json.loads(r"""
{
 "$schema": "https://json-schema.org/draft/2020-12/schema",
 "$id": "resource-plan-1",
 "title": "AmiWind resource plan (resource-plan-1)",
 "description": "The memory and threads each stage of a build needs against what the build gets, written before the first stage (RESOURCE-PLAN.json in the run folder; tools/resource_plan.py, tools/build.py --resource-plan); after a passed build each stage also carries its actual peak. See docs/BUILD_PROFILE.md \"Resource plan\".",
 "type": "object",
 "required": [
  "schema",
  "written",
  "jobs",
  "got",
  "reuse_from",
  "measured_runs",
  "stages_total",
  "stages_running",
  "stages",
  "wall_s",
  "full_speed_wall_s",
  "refusals",
  "advisory",
  "verdict"
 ],
 "additionalProperties": false,
 "properties": {
  "schema": {
   "const": "resource-plan-1"
  },
  "written": {
   "type": "string",
   "minLength": 1
  },
  "jobs": {
   "type": "integer",
   "minimum": 1
  },
  "got": {
   "type": "object",
   "required": [
    "memory_mib",
    "memory_source",
    "threads",
    "threads_source",
    "headroom"
   ],
   "additionalProperties": false,
   "properties": {
    "memory_mib": {
     "type": [
      "number",
      "null"
     ]
    },
    "memory_source": {
     "type": [
      "string",
      "null"
     ]
    },
    "threads": {
     "type": "integer",
     "minimum": 1
    },
    "threads_source": {
     "type": [
      "string",
      "null"
     ]
    },
    "headroom": {
     "type": "number"
    }
   }
  },
  "reuse_from": {
   "type": [
    "string",
    "null"
   ]
  },
  "measured_runs": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "stages_total": {
   "type": "integer",
   "minimum": 0
  },
  "stages_running": {
   "type": "integer",
   "minimum": 0
  },
  "stages": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "stage",
     "status",
     "reasons",
     "model",
     "parent_mib",
     "worker_mib",
     "largest_unit",
     "unit_mib",
     "planned_workers",
     "workers",
     "threads",
     "peak_total_mib",
     "full_speed_mib",
     "wall_s",
     "full_speed_wall_s"
    ],
    "additionalProperties": false,
    "properties": {
     "stage": {
      "type": "string",
      "minLength": 1
     },
     "status": {
      "enum": [
       "OK",
       "WILL THROTTLE",
       "WILL NOT FIT"
      ]
     },
     "reasons": {
      "type": "array",
      "items": {
       "type": "string"
      }
     },
     "model": {
      "type": "string",
      "minLength": 1
     },
     "parent_mib": {
      "type": "number",
      "minimum": 0
     },
     "worker_mib": {
      "type": "number",
      "minimum": 0
     },
     "largest_unit": {
      "type": "string"
     },
     "unit_mib": {
      "type": "number",
      "minimum": 0
     },
     "planned_workers": {
      "type": "integer",
      "minimum": 1
     },
     "workers": {
      "type": "integer",
      "minimum": 0
     },
     "threads": {
      "type": "integer",
      "minimum": 1
     },
     "peak_total_mib": {
      "type": "number",
      "minimum": 0
     },
     "full_speed_mib": {
      "type": "number",
      "minimum": 0
     },
     "wall_s": {
      "type": [
       "number",
       "null"
      ]
     },
     "full_speed_wall_s": {
      "type": [
       "number",
       "null"
      ]
     },
     "beside_mib": {
      "type": "number",
      "minimum": 0
     },
     "lease_gb_full_speed": {
      "type": "integer",
      "minimum": 0
     },
     "measured_in": {
      "type": "array",
      "items": {
       "type": "string"
      }
     },
     "stair": {
      "type": "object",
      "required": [
       "frame",
       "worker_mib",
       "source",
       "model"
      ],
      "additionalProperties": false,
      "properties": {
       "frame": {
        "type": "string"
       },
       "worker_mib": {
        "type": "number"
       },
       "source": {
        "type": "string"
       },
       "model": {
        "type": "string"
       }
      }
     },
     "actual": {
      "type": "object",
      "required": [
       "total_mib",
       "largest_mib",
       "worker_mib",
       "jobs",
       "wall_s",
       "cores",
       "over_estimate"
      ],
      "additionalProperties": false,
      "properties": {
       "total_mib": {
        "type": "number"
       },
       "largest_mib": {
        "type": "number"
       },
       "worker_mib": {
        "type": "number"
       },
       "jobs": {
        "type": "integer"
       },
       "wall_s": {
        "type": "number"
       },
       "cores": {
        "type": "number"
       },
       "over_estimate": {
        "type": "boolean"
       },
       "container_mib": {
        "type": "number"
       }
      }
     }
    }
   }
  },
  "wall_s": {
   "type": [
    "number",
    "null"
   ]
  },
  "full_speed_wall_s": {
   "type": [
    "number",
    "null"
   ]
  },
  "refusals": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "advisory": {
   "type": [
    "object",
    "null"
   ],
   "required": [
    "gain",
    "memory_gb",
    "threads",
    "more_memory_gb",
    "more_threads",
    "text"
   ],
   "additionalProperties": false,
   "properties": {
    "gain": {
     "type": "number"
    },
    "memory_gb": {
     "type": "integer"
    },
    "threads": {
     "type": "integer"
    },
    "more_memory_gb": {
     "type": "integer"
    },
    "more_threads": {
     "type": "integer"
    },
    "text": {
     "type": "string"
    }
   }
  },
  "verdict": {
   "enum": [
    "ok",
    "throttled",
    "refused"
   ]
  },
  "machine": {
   "type": "object"
  },
  "scope": {
   "enum": [
    "miniwind",
    "full"
   ]
  },
  "stair_walk": {
   "type": "string",
   "minLength": 1
  },
  "flagged_over_estimate": {
   "type": "array",
   "items": {
    "type": "string"
   }
  }
 }
}
""")


def validate(doc):
    """Schema errors of a resource plan (SCHEMA_DOCUMENT, resource-plan-1); [] = valid."""
    from aw import validate as check
    return check(doc, SCHEMA_DOCUMENT)


def write(run, doc):
    """RESOURCE-PLAN.json in RUN (validated first: an invalid plan is a builder bug and never written)."""
    errors = validate(doc)
    if errors:
        raise ValueError('Resource plan does not validate (%s): %s' % (SCHEMA, '; '.join(errors[:5])))
    path = Path(run) / FILE
    partial = path.with_name(path.name + '.part')
    partial.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    os.replace(partial, path)
    return path


def text(doc):
    errors = validate(doc)
    if errors:
        raise ValueError('Resource plan does not validate (%s): %s' % (SCHEMA, '; '.join(errors[:5])))
    return json.dumps(doc, indent=1, sort_keys=True) + '\n'


# --------------------------------------------------------------------------
# After the build: actual peaks next to the estimates, history for the next plan

def after_build(run, workspace=None, log=print):
    """Add every stage's actual peak (build-profile.json) to RUN's RESOURCE-PLAN.json, flag the stages more than 25 %
    over their estimate and append the measured rows to the workspace history. Returns the flagged stage names
    (empty without a plan or a profile). Never fails a build."""
    run = Path(run)
    doc = _json(run / FILE)
    profile = _json(run / 'build-profile.json')
    if not doc or not profile:
        return []
    rows = {r['name']: r for r in profile.get('stages') or []}
    timeline = profile.get('timeline')
    flagged, history = [], []
    for stage in doc['stages']:
        row = rows.get(stage['stage'])
        found = measure(row, timeline) if row else None
        if not found:
            continue
        stage['actual'] = {'total_mib': found['total_mib'], 'largest_mib': found['largest_mib'],
                           'worker_mib': found['worker_mib'], 'jobs': found['jobs'],
                           'wall_s': round(found['wall'] or 0.0, 1), 'cores': found['cores'] or 0.0,
                           **({'container_mib': found['container_mib']} if found.get('container_mib') else {})}
        estimate = stage['peak_total_mib']
        over = found['total_mib'] > OVER_ESTIMATE * estimate
        stage['actual']['over_estimate'] = bool(over)
        if over:
            flagged.append(stage['stage'])
        history.append({'format': HISTORY_FORMAT, 'run': str(run), 'stage': stage['stage'], 'measured': found,
                        'estimate_total_mib': estimate, 'estimate_model': stage['model'],
                        'written': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        **({'scope': doc['scope']} if doc.get('scope') in SCOPES else {})})
    doc['flagged_over_estimate'] = flagged
    try:
        write(run, doc)
    except (OSError, ValueError) as exc:
        log('Resource plan: actual peaks not recorded (%s)' % exc)
        return flagged
    if workspace and history:
        path = Path(workspace) / 'cache' / HISTORY
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8', newline='\n') as handle:
                for item in history:
                    handle.write(json.dumps(item, sort_keys=True) + '\n')
        except OSError as exc:
            log('Resource plan: history not written (%s)' % exc)
    for name in flagged:
        stage = next(s for s in doc['stages'] if s['stage'] == name)
        log('RESOURCE PLAN: %s peaked at %.0f MiB, more than 25 %% over its estimate of %.0f MiB (%s): the model is '
            'recalibrated from this run' % (name, stage['actual']['total_mib'], stage['peak_total_mib'],
                                            stage['model']))
    log('Resource plan: actual peaks recorded for %d stage(s), %d over their estimate (%s)'
        % (len(history), len(flagged), run / FILE))
    return flagged


# --------------------------------------------------------------------------
# The machine at a start (one line; INTERNAL STANDARD: say what you got)

def state_line(ask_threads=None, ask_mib=None, root='/sys/fs/cgroup', sample_s=0.5):
    """(line, record): this container's CPU use (cgroup cpu.stat over SAMPLE_S), its memory in use / limit, the
    machine's free memory and what the new work asks for."""
    def usage():
        for line in (_read(Path(root) / 'cpu.stat') or '').splitlines():
            if line.startswith('usage_usec '):
                return int(line.split()[1]) / 1e6
        return None
    first, began = usage(), time.monotonic()
    if first is not None and sample_s:
        time.sleep(sample_s)
    second = usage()
    busy = ((second - first) / max(1e-6, time.monotonic() - began)) if first is not None and second is not None else None
    limit, used, cache = cgroup_memory(root)
    total, free = host_memory()
    record = {'threads_busy': round(busy, 2) if busy is not None else None, 'threads': cgroup_threads(root) or host_threads(),
              'memory_used_mib': round((used or 0) / MIB) if used is not None else None,
              'memory_cache_mib': round(cache / MIB) if cache else 0,
              'memory_limit_mib': round(limit / MIB) if limit else None,
              'machine_free_mib': round(free / MIB) if free else None,
              'machine_total_mib': round(total / MIB) if total else None,
              'ask_threads': ask_threads, 'ask_mib': ask_mib}
    line = ('Machine at start: %s of %d threads busy in this container; memory %s / %s MiB in use (%s MiB file cache); '
            'machine free %s of %s MiB; asks %s threads, %s MiB' % (
                '%.1f' % busy if busy is not None else '?', record['threads'],
                record['memory_used_mib'], record['memory_limit_mib'] or 'no limit', record['memory_cache_mib'],
                record['machine_free_mib'], record['machine_total_mib'], ask_threads or '?',
                '%.0f' % ask_mib if ask_mib else '?'))
    return line, record


# --------------------------------------------------------------------------
# While a build runs: pools follow the memory and the CPU quota (fixlist A9)

class MemoryGovernor:
    """How many units a pool may have in flight now, by memory and CPU quota: re-read every GOVERNOR_SECONDS (between
    tasks), at most PLANNED. Memory: (limit - other) x HEADROOM holds floor(that / unit) units, where other = the
    container's memory in use less the reclaimable file cache less the in-flight units at their planned size (so a
    unit still growing towards its peak is counted at its peak; never less than it was with no unit in flight). A drop only stops new units; a running one is never
    stopped. Every change is printed with its reason."""

    def __init__(self, planned, unit_mib, label='stage', parent_mib=0.0, root='/sys/fs/cgroup', interval=None,
                 log=None, clock=time.monotonic, reader=None):
        self.planned, self.unit = max(1, int(planned)), max(1.0, float(unit_mib))
        self.label, self.parent = label, float(parent_mib or 0.0)
        self.root, self.clock = root, clock
        self.interval = float(os.environ.get(GOVERNOR_ENV, GOVERNOR_SECONDS) if interval is None else interval)
        self.log = log or (lambda line: print(line, flush=True))
        self.reader = reader or (lambda: (cgroup_memory(self.root), cgroup_threads(self.root)))
        self.at, self.value, self.changes, self.base, self.start_quota = None, None, [], None, None
        self.room_at, self.room = None, None       # admits(): the memory room of per-unit admission

    def _compute(self, in_flight):
        (limit, used, cache), quota = self.reader()
        reasons = []
        allowed = self.planned
        if limit is not None and used is not None:
            other = max(0.0, (used - cache) / MIB - in_flight * self.unit)
            if in_flight == 0:
                self.base = other          # the memory of everything but this pool's units
            other = max(other, self.base or 0.0)
            room = (limit / MIB - other) * HEADROOM
            fit = max(1, int(room // self.unit))
            if fit < allowed:
                allowed = fit
            reasons.append('memory: limit %.1f GiB, %.1f GiB in use besides %d unit%s in flight, room for %d at '
                           'about %.0f MiB each' % (limit / GIB, other / 1024., in_flight, '' if in_flight == 1 else 's',
                                                    fit, self.unit))
        if self.start_quota is None:
            self.start_quota = quota if quota is not None else 0
        if quota is not None and self.start_quota and quota < self.start_quota:
            # an explicit --jobs stays exact at the start; a quota lowered since (a changed lease) shrinks the pool
            by_quota = max(1, int(round(self.planned * quota / float(self.start_quota))))
            if by_quota < allowed:
                allowed = by_quota
                reasons.append('CPU quota lowered %d -> %d threads' % (self.start_quota, quota))
        return max(1, allowed), '; '.join(reasons) or 'no container limits'

    def admits(self, in_flight_mib, unit_mib, in_flight=0, reserve_mib=0.0):
        """Per-unit admission (BUILD-CHIM-SERIAL-SECTIONS-44): may a unit of about UNIT_MIB start beside the units in
        flight (IN_FLIGHT of them, IN_FLIGHT_MIB together at their planned sizes)? Room = (limit - other) x HEADROOM,
        other = what the container holds besides those units (re-read every interval, never less than with no unit
        in flight); RESERVE_MIB is kept free for a larger unit waiting at the head of the queue. With nothing in
        flight a unit always starts. The pool used to size every unit as its largest (the v0.0.44-dev1 stair gate:
        4 of 24 workers at 2,855 MiB each for frames that hold about 300 MiB)."""
        if in_flight == 0:
            return True
        now = self.clock()
        if self.room_at is None or now - self.room_at >= self.interval:
            self.room_at = now
            (limit, used, cache), _quota = self.reader()
            room = None
            if limit is not None and used is not None:
                other = max(0.0, (used - cache) / MIB - in_flight_mib)
                if self.base is None:
                    self.base = other
                other = max(other, self.base)
                room = (limit / MIB - other) * HEADROOM
                why = ('memory: limit %.1f GiB, %.1f GiB in use besides %d unit%s in flight (%.0f MiB planned), '
                       'room %.0f MiB') % (
                    limit / GIB, other / 1024., in_flight, '' if in_flight == 1 else 's', in_flight_mib, room)
                if self.room is None or abs(room - self.room) >= 1024:
                    self.changes.append({'room_mib': round(room), 'why': why})
            self.room = room
        if self.room is None:
            return True
        return in_flight_mib + float(unit_mib) + float(reserve_mib or 0.0) <= self.room

    def limit(self, in_flight=0):
        now = self.clock()
        if self.at is not None and now - self.at < self.interval:
            return self.value
        self.at = now
        value, why = self._compute(in_flight)
        if value != self.value:
            if self.value is None:
                if value < self.planned:
                    self.log('[pool] %s: %d of %d workers to start (%s)' % (self.label, value, self.planned, why))
            else:
                self.log('[pool] %s: workers %d -> %d of %d (%s; %s)' % (
                    self.label, self.value, value, self.planned, 'memory or threads freed up' if value > self.value
                    else 'memory tight: no new units until it frees up, running units go on', why))
            self.changes.append({'from': self.value, 'to': value, 'why': why})
            self.value = value
        return self.value


def governor_for(planned, unit_mib=None, label='stage', environ=None):
    """A MemoryGovernor for a pool of PLANNED workers with UNIT_MIB a unit (else the stage's unit from the scheduler,
    AMIWIND_STAGE_UNIT_MIB), or None when neither is known or the pool has one worker."""
    environ = os.environ if environ is None else environ
    if unit_mib is None:
        try:
            unit_mib = float(environ.get(UNIT_MIB_ENV) or 0) or None
        except ValueError:
            unit_mib = None
    if not unit_mib or planned <= 1:
        return None
    return MemoryGovernor(planned, unit_mib, label=label)


# Scheduler memory guard (fixlist A9, the resource plan's running half; tools/build_parallel.execute_parallel):
# every GOVERNOR_SECONDS the scheduler reads the container's memory and CPU quota. Above PRESSURE_HIGH of
# the limit in use (file cache not counted) the pooled stage with the most workers hands out no new units beyond
# three quarters of them; below PRESSURE_LOW a capped stage grows back toward its share, by as many workers as the
# free memory holds at its planned unit size (the resource plan's estimate; one at a time without one). A CPU quota
# lowered while the build runs (a changed lease: docker update --cpus) shrinks the shares, a raised one lets them grow
# back up to --jobs. Pools follow their allowance file at their next task; running units are never stopped.
PRESSURE_HIGH = 0.90
PRESSURE_LOW = 0.70
GROW_ROOM = 0.80          # a capped stage grows back by the planned units that fit under this share of the limit
# A pooled stage the guard holds below half its share for this long is an ALARM (BUILD-SCHEDULER-MEMORY-STARVED-42:
# the v0.0.42 final's chim stage sat on 1 of 6 workers for over an hour): one [scheduler] ALARM line naming the stage,
# its workers, the memory and the lease that would let it run, again every ALARM_SECONDS while it lasts.
ALARM_SECONDS = 300.0
ALARM_ENV = 'AMIWIND_SCHEDULER_ALARM_SECONDS'
# Measured worker memory (BUILD-STAGE-ALLOWANCE-STUCK-43). When the scheduler can read a stage's own processes
# (/proc: its main process and the pool workers under it), the guard decides from what the workers really hold, not
# from the plan's unit estimate:
# SUPERSEDED 2026-10-21 (SchedulerGuard docstring, BUILD-SCHEDULER-MEMORY-STARVED-42): below PRESSURE_CRITICAL no cut
# at all, --jobs kept and earlier cuts lifted; the two lines below describe the rule before that.
# - a cut is made only when the workers' own memory (above an idle worker's) can free what is over PRESSURE_HIGH; when
#   the memory is held by the stage's main process, fewer workers free nothing and the workers stay (one line says
#   so). Above PRESSURE_CRITICAL the guard cuts anyway, by as many workers as the excess needs;
# - a capped stage grows back by the workers whose measured size fits under MEASURED_GROW_ROOM of the limit.
# The v0.0.43-dev3 chim stage was cut 20 -> 1 worker in 3.5 minutes while its main process held about 35 of the
# container's 40 GiB: the cuts freed nothing (36.3 GiB in use at 20 workers, 36.8 at 2), and grow-back waited for room
# under 80 % for a planned 2,842 MiB unit that never came, while the visibility-row workers needed about 100 MiB each.
PRESSURE_CRITICAL = 0.96
MEASURED_GROW_ROOM = 0.88
MIN_WORKER_MIB = 64.0


def _proc_tree(root):
    """[(pid, ppid, rss MiB)] of ROOT and its live descendants (Linux /proc), or None when unreadable."""
    proc = Path('/proc')
    if not (proc / str(root)).is_dir():
        return None
    parents, rss = {}, {}
    try:
        names = os.listdir(proc)
    except OSError:
        return None
    for name in names:
        if not name.isdigit():
            continue
        try:
            raw = (proc / name / 'stat').read_bytes()
            fields = raw[raw.rfind(b')') + 2:].split()
            parents[int(name)] = int(fields[1])
            rss[int(name)] = int(fields[21]) * PAGE_BYTES / MIB
        except (OSError, IndexError, ValueError):
            continue
    if root not in parents:
        return None
    children = {}
    for pid, parent in parents.items():
        children.setdefault(parent, []).append(pid)
    tree, pending = [], [root]
    while pending:
        pid = pending.pop()
        tree.append((pid, parents.get(pid), rss.get(pid, 0.0)))
        pending.extend(children.get(pid, ()))
    return tree


try:
    PAGE_BYTES = os.sysconf('SC_PAGE_SIZE')
except (AttributeError, ValueError, OSError):
    PAGE_BYTES = 4096


def stage_memory(root):
    """{'main_mib', 'workers_mib': [...]} of a stage's process tree: the main process is the one with the most
    direct children (its pool workers; ties: the largest), the workers are every process below it. None when the
    tree cannot be read (not Linux, the stage gone)."""
    tree = _proc_tree(root)
    if not tree:
        return None
    direct = {}
    for pid, parent, _ in tree:
        direct[parent] = direct.get(parent, 0) + 1
    sizes = {pid: mib for pid, _, mib in tree}
    main = max(sizes, key=lambda pid: (direct.get(pid, 0), sizes[pid]))
    below, pending, by_parent = [], [main], {}
    for pid, parent, _ in tree:
        by_parent.setdefault(parent, []).append(pid)
    while pending:
        pid = pending.pop()
        for child in by_parent.get(pid, ()):
            below.append(sizes[child])
            pending.append(child)
    return {'main_mib': round(sizes[main], 1), 'workers_mib': [round(m, 1) for m in below]}


def worker_sizes(measured):
    """(freeable MiB, one more worker's MiB) from stage_memory: what the workers hold above an idle one, and the
    largest worker (a new worker may have to be started whole). None without workers."""
    workers = (measured or {}).get('workers_mib') or []
    if not workers:
        return None
    floor = min(workers) if len(workers) > 1 else 0.0
    return sum(w - floor for w in workers), max(MIN_WORKER_MIB, max(workers))


class SchedulerGuard:
    """The build's memory and CPU guard for pooled stages.

    THE RULE (maintainer 2026-10-21: "--jobs max" keeps its level at all points; BUILD-SCHEDULER-MEMORY-STARVED-42):
    below PRESSURE_CRITICAL (96 % of the container's memory limit) a pooled stage ALWAYS runs at its full --jobs
    share, and any earlier cut is lifted at once. Only above PRESSURE_CRITICAL does the guard cut workers, to keep the
    build out of the out-of-memory killer.

    Why, so this is never undone again: a cut does not free memory. A pool's worker processes stay alive between
    units and keep the memory they reached (Python does not hand freed heap back); a cut only stops handing them new
    units. Every cut between PRESSURE_HIGH and PRESSURE_CRITICAL therefore froze the memory where it was and, with the
    grow-back rule waiting for room that never came, ratcheted the stage down for good: the v0.0.42 final's chim stage
    sat on 1 of 6 workers for over an hour, and on 2026-10-21 the v0.0.47-dev3 clean public build's chim stage sat on
    1 of 24 for an hour at 39.5 of 44 GiB (main process 14 GB, 26 idle-but-alive workers 19 GiB).

    Do NOT reintroduce a cut below PRESSURE_CRITICAL, a "memory tight" cut on a share of the limit, or a cut that
    assumes idle workers shrink, unless the same change also ends the cut workers' processes (and a test proves the
    memory comes back). tests/test_build_stage_supervisor.py and tests/test_scheduler_memory_starved.py pin this.

    Since v0.0.48 (BUILD-POOL-MEMORY-PEAK-48) a cut above the critical line does free memory: each stage's pools end
    their idle worker processes above the stage's allowance once it has held more for about 20 s
    (build_parallel._watch_idle_workers; tests/test_pool_idle_retire.py measures the memory coming back), so the
    pressure falls under the line and the share comes back instead of both stages sitting on one worker. The rule
    above (no cut below the critical line) stays as it is.
    """

    def __init__(self, budget, units=None, reader=None, clock=time.monotonic, interval=None, log=None, parents=None,
                 alarm_seconds=None, stage_reader=None):
        self.budget, self.units, self.parents = budget, dict(units or {}), dict(parents or {})
        # stage name -> its process (the scheduler's track()); stage_reader(pid) -> stage_memory(...) or None
        self.pids = {}
        self.stage_reader = stage_reader or stage_memory
        self.holding = set()      # stages the guard left alone this episode: their main process holds the memory
        self.measured = {}        # stage -> its last stage_memory reading
        self.alarm_seconds = float(os.environ.get(ALARM_ENV, ALARM_SECONDS) if alarm_seconds is None else alarm_seconds)
        self.starved = {}         # stage -> (since, last alarm) while held below half its share
        self.alarms = []
        self.reader = reader or (lambda: (cgroup_memory(), cgroup_threads()))
        self.clock, self.at = clock, None
        self.interval = float(os.environ.get(GOVERNOR_ENV, GOVERNOR_SECONDS) if interval is None else interval)
        self.log = log or (lambda line: print(line, flush=True))
        self.quota = self.start_quota = None
        self.started = False
        self.caps = {}            # stage -> workers it may hold now by memory
        self.changes = []

    def effective_budget(self):
        """--jobs, unchanged (an explicit --jobs is exact, also above the CPU quota at the start), shrunk in
        proportion only when the quota drops below what it was when the build started (a lowered lease)."""
        if self.quota is None or self.start_quota is None or self.quota >= self.start_quota:
            return self.budget
        return max(1, int(round(self.budget * self.quota / float(self.start_quota))))

    def cap(self, name, value):
        held = self.caps.get(name)
        return value if held is None else max(1, min(value, held))

    def track(self, name, pid):
        """The scheduler started stage NAME as process PID: its workers' memory is measured from now on."""
        self.pids[name] = pid

    def untrack(self, name):
        self.pids.pop(name, None)
        self.measured.pop(name, None)
        self.holding.discard(name)

    def _measure(self, name):
        pid = self.pids.get(name)
        if pid is None:
            return None
        try:
            reading = self.stage_reader(pid)
        except (OSError, ValueError):
            reading = None
        if reading is not None:
            self.measured[name] = reading
        return reading

    def tick(self, pooled, now_share):
        """POOLED: {stage: workers held now}; NOW_SHARE: {stage: its share without a memory cap}."""
        now = self.clock()
        if self.at is not None and now - self.at < self.interval:
            return
        self.at = now
        (limit, used, cache), quota = self.reader()
        if not self.started:
            self.started, self.quota, self.start_quota = True, quota, quota
        elif quota != self.quota:
            self.quota = quota
            self.log('[scheduler] CPU quota %s -> %s threads (it was %s at the start): the stages share %d of '
                     '--jobs %d' % (self.changes[-1]['to'] if self.changes and self.changes[-1]['what'] == 'quota'
                                    else self.start_quota, quota, self.start_quota, self.effective_budget(),
                                    self.budget))
            self.changes.append({'what': 'quota', 'from': self.start_quota, 'to': quota})
        for name in list(self.caps):
            if name not in pooled:
                del self.caps[name]
        if limit is None or used is None or not pooled:
            return
        self._alarm(pooled, now_share, limit, max(0, used - cache), now)
        live = max(0, used - cache)
        pressure = live / float(limit)
        gib = float(1 << 30)
        measured = {name: self._measure(name) for name in pooled}
        if pressure <= PRESSURE_HIGH:
            self.holding.clear()
        if pressure <= PRESSURE_CRITICAL:
            # THE RULE (class docstring): below the critical line every pooled stage runs at its full --jobs share; a
            # cut made above it is lifted here at once, whatever the grow-back room says (the dev3 clean public build
            # sat at 89.8 %, under PRESSURE_HIGH, on 1 of 24 workers for an hour, waiting for room under 88 %).
            for capped in [n for n in list(self.caps) if n in pooled]:
                del self.caps[capped]
                self.log('[scheduler] memory %.1f of %.1f GiB: below the critical line (%d %%), %s back to its full '
                         'share of --jobs (a cut frees nothing while the worker processes stay alive)' % (
                             live / gib, limit / gib, round(PRESSURE_CRITICAL * 100), capped))
                self.changes.append({'what': 'memory-restore', 'stage': capped})
        if pressure > PRESSURE_HIGH:
            name = max(pooled, key=lambda n: (pooled[n], n))
            sizes = worker_sizes(measured.get(name))
            excess = (live - limit * PRESSURE_HIGH) / MIB
            if pooled[name] <= 1 and name not in self.caps:
                pass
            elif pressure <= PRESSURE_CRITICAL:
                # Below the critical line the stage keeps --jobs (maintainer 2026-10-21: "--jobs max" keeps its level
                # at all points). A cut never freed memory here: the pool's worker processes stay alive and keep what
                # they hold whether or not they get new units, so every cut only ratcheted the stage down, to one
                # worker for an hour on the v0.0.47-dev3 clean public build (BUILD-SCHEDULER-MEMORY-STARVED-42,
                # persisting since v0.0.42; before: BUILD-STAGE-ALLOWANCE-STUCK-43). An earlier cut is lifted.
                if self.caps.pop(name, None) is not None:
                    self.log('[scheduler] memory %.1f of %.1f GiB: below the critical line (%d %%), %s back to its '
                             'full %d workers (a cut frees nothing while the worker processes stay alive)' % (
                                 live / gib, limit / gib, round(PRESSURE_CRITICAL * 100), name, pooled[name]))
                    self.changes.append({'what': 'memory-restore', 'stage': name, 'workers': pooled[name]})
                if sizes is not None and name not in self.holding:
                    self.holding.add(name)
                    self.log('[scheduler] memory tight (%.1f of %.1f GiB in use), but %s\'s main process holds '
                             '%.1f GiB and its %d worker process(es) only %.0f MiB above an idle worker: fewer '
                             'workers would not free it; %s keeps %d workers (cut only above %d %%)' % (
                                 live / gib, limit / gib, name, measured[name]['main_mib'] / 1024.,
                                 len(measured[name]['workers_mib']), sizes[0], name, pooled[name],
                                 round(PRESSURE_CRITICAL * 100)))
                    self.changes.append({'what': 'memory-hold', 'stage': name, 'workers': pooled[name],
                                         'main_mib': measured[name]['main_mib'], 'freeable_mib': round(sizes[0], 1)})
            else:
                if sizes is not None:
                    # by as many workers as the excess needs, at the largest worker's size
                    need = int(math.ceil(excess / sizes[1]))
                    new = max(1, pooled[name] - max(1, need))
                else:
                    new = max(1, (pooled[name] * 3) // 4)
                self.caps[name] = new
                self.log('[scheduler] memory tight (%.1f of %.1f GiB in use): %s workers %d -> %d; no new units '
                         'beyond that until it frees up, running units go on' % (live / gib, limit / gib, name,
                                                                                 pooled[name], new))
                self.changes.append({'what': 'memory', 'stage': name, 'from': pooled[name], 'to': new})
        else:
            # grow back whenever the free memory under GROW_ROOM of the limit holds a planned unit, not only below
            # PRESSURE_LOW in use: a large parent kept the v0.0.42 final's chim stage above 70 % and on one worker
            # for over an hour (BUILD-SCHEDULER-MEMORY-STARVED-42). Units granted here are counted against the free
            # memory, so the stages together never plan past GROW_ROOM (below PRESSURE_HIGH, where the guard cuts).
            free = max(0.0, limit * GROW_ROOM - live) / MIB
            free_measured = max(0.0, limit * MEASURED_GROW_ROOM - live) / MIB
            for name in sorted(self.caps):
                held = self.caps[name]
                share = now_share.get(name, held)
                sizes = worker_sizes(measured.get(name))
                unit = self.units.get(name)
                if sizes is not None:
                    # the workers' measured size, up to MEASURED_GROW_ROOM (BUILD-STAGE-ALLOWANCE-STUCK-43)
                    unit = sizes[1]
                    grow = int(free_measured // unit)
                elif unit:
                    grow = int(free // unit)
                elif pressure < PRESSURE_LOW:
                    grow = 1                 # no size known: one at a time, only well below the limit, as before
                else:
                    grow = 0
                if grow < 1:
                    continue
                new = min(share, held + grow)
                if unit:
                    free -= (new - held) * unit
                    free_measured -= (new - held) * unit
                if new >= share:
                    del self.caps[name]
                else:
                    self.caps[name] = new
                if new != held:
                    self.log('[scheduler] memory freed up (%.1f of %.1f GiB in use): %s workers %d -> %d of %d' % (
                        live / gib, limit / gib, name, held, new, share))
                    self.changes.append({'what': 'memory', 'stage': name, 'from': held, 'to': new})

    def lease_gb(self, live, extra_mib):
        """The container memory (GB, whole) at which LIVE bytes in use plus EXTRA_MIB more stay under GROW_ROOM
        (where a capped stage grows back by the units that fit)."""
        return int(math.ceil((live / MIB + extra_mib) / GROW_ROOM / 1024.))

    def _alarm(self, pooled, now_share, limit, live, now):
        gib = float(1 << 30)
        for name in list(self.starved):
            if name not in pooled:
                del self.starved[name]
        for name, held in pooled.items():
            share = now_share.get(name, held)
            if share < 2 or held * 2 >= share:
                self.starved.pop(name, None)
                continue
            since, last = self.starved.setdefault(name, (now, None))
            if now - since < self.alarm_seconds or (last is not None and now - last < self.alarm_seconds):
                continue
            sizes = worker_sizes(self.measured.get(name))
            unit = sizes[1] if sizes is not None else self.units.get(name)   # measured first (STUCK-43)
            lease = self.lease_gb(live, (share - held) * unit) if unit else None
            self.log('[scheduler] ALARM: %s held at %d of %d workers for %.0f min by the memory guard (%.1f of %.1f '
                     'GiB in use, file cache not counted); %s' % (
                         name, held, share, (now - since) / 60., live / gib, limit / gib,
                         'a lease of %d GB would let it run at %d (%d more workers at about %.0f MiB each)'
                         % (lease, share, share - held, unit) if lease else 'its worker size is not known: give the '
                         'build more memory or fewer stages beside it'))
            self.starved[name] = (since, now)
            self.alarms.append({'stage': name, 'held': held, 'share': share, 'minutes': round((now - since) / 60., 1),
                                'live_gib': round(live / gib, 1), 'limit_gib': round(limit / gib, 1),
                                'lease_gb': lease})

    def start_check(self, name, jobs, running=()):
        """Before a pooled stage starts: does its parent plus JOBS workers fit beside what the container holds now
        (the stages RUNNING)? Prints one [scheduler] line when it does not (the guard would hold it back), with the
        lease that fits it; returns that line or None. Unknown sizes or no container limit: None."""
        unit = self.units.get(name)
        if not unit:
            return None
        (limit, used, cache), _quota = self.reader()
        if limit is None or used is None:
            return None
        live = max(0, used - cache)
        need = self.parents.get(name, 0.0) + jobs * unit
        room = (limit * PRESSURE_HIGH - live) / MIB
        if need <= room:
            return None
        gib = float(1 << 30)
        line = ('[scheduler] WILL NOT FIT AT FULL SPEED: %s needs about %.1f GiB (a %.0f MiB parent + %d workers x '
                '%.0f MiB) beside %.1f GiB in use%s, of %.1f GiB; the memory guard will hold it back; a lease of %d GB '
                'fits it' % (name, need / 1024., self.parents.get(name, 0.0), jobs, unit, live / gib,
                             ' (running: %s)' % ', '.join(sorted(running)) if running else '', limit / gib,
                             int(math.ceil((live / MIB + need) / PRESSURE_HIGH / 1024.))))
        self.log(line)
        self.alarms.append({'stage': name, 'start_check': True, 'need_mib': round(need, 1),
                            'live_gib': round(live / gib, 1), 'limit_gib': round(limit / gib, 1)})
        return line
