#!/usr/bin/env python3
"""Build profiler: per-stage CPU, memory, I/O and sub-stage timing; analysis and reports.

Always on and cheap. The builder runs each stage through a small wrapper
(`build_profile.py _stage`) that measures the stage and every child it waits
for (wall time, user and system CPU, largest process, block I/O). A sampling
thread in the builder records the CPU use of every running stage's process tree
about once per second. Long stages can time named sections with
`build_profile.section('name')` (context manager or decorator) or with the
table-driven `instrument(stage)`; sections cost nothing unless the builder set
AMIWIND_PROFILE_SECTIONS for that stage.

The analysis (critical path, idle-core warnings, slowest stages and sections,
suggestions) goes into build-profile.json in the run folder and a short table in
the build summary. Read and compare runs with:

    python tools/build_profile.py report RUN [--compare OLDER_RUN] [--html OUT.html]
    python tools/build_profile.py compare RUN OLDER_RUN [--fail-on-regression]
    python tools/build_profile.py optimize RUN [RUN ...]

(the same as `python tools/build.py profile report|compare|optimize ...`).
Live progress and ETA while a build runs: tools/build_progress.py
(`python tools/build.py status RUN`).

Profiling never changes a stage's command line, environment variables other
than AMIWIND_PROFILE_SECTIONS, working directory or outputs. Linux gives all
counters; other systems record wall time and the job budget only.
Set AMIWIND_BUILD_PROFILE=off (or pass --no-profile to tools/build.py) to run
stages unwrapped. See docs/BUILD_PROFILE.md.
"""
import argparse
from contextlib import contextmanager
import functools
import html as html_escape
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

SCHEMA = 'amiwind-build-profile-v1'
PROFILE_NAME = 'build-profile.json'
SECTIONS_ENV = 'AMIWIND_PROFILE_SECTIONS'
SWITCH_ENV = 'AMIWIND_BUILD_PROFILE'
INTERVAL_ENV = 'AMIWIND_PROFILE_INTERVAL'
DEFAULT_INTERVAL = 1.0
IDLE_SHARE = 0.5          # a stage using less than half its job budget ...
IDLE_SECONDS = 60.0       # ... for longer than this is reported
REGRESSION_SHARE = 0.10   # compare: slower by more than 10 % ...
REGRESSION_SECONDS = 5.0  # ... and by more than 5 s is a regression
HOST_BUSY_SHARE = 0.25   # other work above this share of the machine during a stage: host_busy
CHART_JS = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js'
# Stage read trace (tools/build_cache.py installs the hook and checks the lists).
TRACE_ENV = 'AMIWIND_STAGE_TRACE'
TRACE_HOOK_FOLDER = 'trace-hook'
READS_FOLDER = 'reads'


def enabled(metadata=None):
    """Profiling is on unless --no-profile (metadata) or AMIWIND_BUILD_PROFILE=off."""
    if metadata is not None and metadata.get('profile') is False:
        return False
    return os.environ.get(SWITCH_ENV, 'on').strip().lower() not in ('0', 'off', 'no', 'false')


def linux_proc():
    return sys.platform.startswith('linux') and Path('/proc/self/stat').is_file()


# --------------------------------------------------------------------------
# Counters (Linux /proc and cgroup v2; every reader returns None when absent)

def _clock_ticks():
    try:
        return os.sysconf('SC_CLK_TCK')
    except (AttributeError, ValueError, OSError):
        return 100


CLOCK_TICKS = _clock_ticks()
try:
    PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
except (AttributeError, ValueError, OSError):
    PAGE_SIZE = 4096


def read_proc_io(pid='self'):
    """/proc/PID/io (task I/O accounting; includes children the process waited for)."""
    try:
        rows = dict(line.split(': ', 1) for line in Path(f'/proc/{pid}/io').read_text().splitlines() if ': ' in line)
        return {'read_bytes': int(rows['read_bytes']), 'write_bytes': int(rows['write_bytes']),
                'rchar': int(rows['rchar']), 'wchar': int(rows['wchar'])}
    except (OSError, KeyError, ValueError):
        return None


def read_cgroup_io():
    """Bytes the whole cgroup (normally the build container) read from / wrote to block devices."""
    try:
        read = written = 0
        for line in Path('/sys/fs/cgroup/io.stat').read_text().splitlines():
            for field in line.split()[1:]:
                key, _, value = field.partition('=')
                if key == 'rbytes':
                    read += int(value)
                elif key == 'wbytes':
                    written += int(value)
        return {'read_bytes': read, 'write_bytes': written}
    except (OSError, ValueError):
        return None


def read_cgroup_cpu():
    """Total CPU seconds used by the cgroup."""
    try:
        for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines():
            key, _, value = line.partition(' ')
            if key == 'usage_usec':
                return int(value) / 1e6
    except (OSError, ValueError):
        pass
    return None


def read_host_cpu():
    """(busy, total) jiffies of the whole machine from /proc/stat (in a container:
    the VM's CPUs, shared with every other container and job), or None."""
    try:
        with open('/proc/stat') as stream:
            fields = stream.readline().split()
        if fields[0] != 'cpu':
            return None
        values = [int(v) for v in fields[1:9]]
        idle = values[3] + values[4]  # idle + iowait
        return sum(values) - idle, sum(values)
    except (OSError, ValueError, IndexError):
        return None


def host_cpus():
    return os.cpu_count() or 1


def read_cgroup_memory():
    try:
        return int(Path('/sys/fs/cgroup/memory.current').read_text())
    except (OSError, ValueError):
        return None


def proc_stat(pid):
    """(cpu ticks incl. waited-for children, rss bytes) of one process, or None."""
    try:
        raw = Path(f'/proc/{pid}/stat').read_bytes()
    except OSError:
        return None
    fields = raw[raw.rfind(b')') + 2:].split()
    try:
        return (int(fields[11]) + int(fields[12]) + int(fields[13]) + int(fields[14]),
                int(fields[21]) * PAGE_SIZE)
    except (IndexError, ValueError):
        return None


def proc_children(pid):
    """Direct children of PID from /proc/PID/task/*/children (None when unsupported)."""
    try:
        tasks = os.listdir(f'/proc/{pid}/task')
    except OSError:
        return []
    found = []
    supported = False
    for task in tasks:
        try:
            text = Path(f'/proc/{pid}/task/{task}/children').read_text()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        supported = True
        found.extend(int(child) for child in text.split())
    return found if supported else None


def all_parents():
    """{pid: ppid} for every visible process (fallback when children files are absent)."""
    parents = {}
    for name in os.listdir('/proc'):
        if name.isdigit():
            try:
                raw = Path(f'/proc/{name}/stat').read_bytes()
                parents[int(name)] = int(raw[raw.rfind(b')') + 2:].split()[1])
            except (OSError, IndexError, ValueError):
                continue
    return parents


def tree_usage(root, parents=None):
    """(cpu seconds, summed rss bytes, process count) of ROOT and its live descendants.

    Each process contributes its own CPU plus that of the children it has
    already waited for (cutime/cstime), so every finished process is counted
    exactly once, in the parent that reaped it.
    """
    ticks = rss = count = 0
    pending = [root]
    seen = set()
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stat = proc_stat(pid)
        if stat is None:
            continue
        ticks += stat[0]
        rss += stat[1]
        count += 1
        if parents is not None:
            children = [child for child, parent in parents.items() if parent == pid]
        else:
            children = proc_children(pid)
            if children is None:
                return tree_usage(root, all_parents())
        pending.extend(children)
    return ticks / CLOCK_TICKS, rss, count


def _rusage_children():
    try:
        import resource
    except ImportError:
        return None
    return resource.getrusage(resource.RUSAGE_CHILDREN)


# --------------------------------------------------------------------------
# Sections: named sub-stage timers inside a stage process

_local = threading.local()


def _section_file():
    return os.environ.get(SECTIONS_ENV)


def _write_section(record):
    path = _section_file()
    if not path:
        return
    line = (json.dumps(record, sort_keys=True) + '\n').encode()
    try:
        # One O_APPEND write per record: concurrent writers never interleave.
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(descriptor, line)
        finally:
            os.close(descriptor)
    except OSError:
        pass  # Profiling must never fail a build.


class section:
    """Time a named part of a stage: `with section('name'):` or `@section('name')`.

    Records wall time, own CPU and the CPU of children waited for inside the
    section. A no-op (two attribute reads) unless AMIWIND_PROFILE_SECTIONS is set.
    """

    def __init__(self, name, **fields):
        self.name = str(name)
        self.fields = fields
        self._stack = []

    def note(self, **fields):
        self.fields.update(fields)

    def __enter__(self):
        if _section_file():
            depth = getattr(_local, 'depth', 0)
            _local.depth = depth + 1
            self._stack.append((time.monotonic(), os.times(), depth))
        return self

    def __exit__(self, kind, value, traceback):
        if self._stack:
            start, before, depth = self._stack.pop()
            after = os.times()
            _local.depth = depth
            record = {'name': self.name, 'pid': os.getpid(), 'depth': depth,
                      'start': round(start, 4), 'wall': round(time.monotonic() - start, 4),
                      'cpu_self': round(after.user + after.system - before.user - before.system, 3),
                      'cpu_children': round(after.children_user + after.children_system
                                            - before.children_user - before.children_system, 3)}
            if kind is not None:
                record['error'] = kind.__name__
            record.update(self.fields)
            _write_section(record)
        return False

    def __call__(self, function):
        name, fields = self.name, self.fields

        @functools.wraps(function)
        def timed(*args, **kwargs):
            with section(name, **fields):
                return function(*args, **kwargs)
        timed.__amiwind_section__ = name
        return timed


def _timed_map(original, label):
    @functools.wraps(original)
    def timed(function, items, *args, **kwargs):
        timer = section(f'{label}: {getattr(function, "__name__", "work")}')
        count = 0
        with timer:
            for result in original(function, items, *args, **kwargs):
                count += 1
                yield result
            timer.note(items=count)
    timed.__amiwind_section__ = label
    return timed


def _timed_run(original):
    @functools.wraps(original)
    def run(*args, **kwargs):
        command = args[0] if args else kwargs.get('args')
        try:
            program = command if isinstance(command, (str, bytes, os.PathLike)) else command[0]
            label = 'exec ' + Path(os.fsdecode(program).split()[0]).name
        except (TypeError, IndexError, ValueError):
            label = 'exec'
        with section(label):
            return original(*args, **kwargs)
    run.__amiwind_section__ = 'exec'
    return run


# Stage -> functions to time. 'name' is looked up in the stage script (__main__);
# 'module:name' patches that module's attribute, which reaches every caller that
# imports it at call time (build_aga.py imports its helpers inside functions).
# tests/test_build_profile.py checks that every target still exists.
INSTRUMENT = {
    'build_aga image': (
        'finalize_image', 'install_world_scenery', 'write_content_fingerprint', 'harvest_fingerprint_entries',
        'audit_world_map_heap_with_receipt', 'stage_runtime', 'stage_fpu_support', 'check_image',
        'install_world_terrain:install', 'install_world_flora:install', 'install_town_flora:install',
        'prepare_seyda_regions:convert_builder_scene', 'repair_balmora_maps:repair',
        'actor_grounding:annotate', 'actor_grounding:bake_ground', 'prepare_world_ui:prepare',
        'build_gallery:stage_required', 'exterior_sky_build:configure_staged_maps',
        'hidden_surface_build:cull_staged_maps', 'optimize_world_maps:optimize_maps',
        'optimize_world_maps:verify_optimized_maps', 'check_actor_ground:require',
        'check_world_map_heap:audit_world_maps', 'entity_tracker:build_gate', 'night_lighting:stage',
        'world_volumes:pack', 'world_volumes:verify_combined',
        'build_parallel:ordered_map', 'build_parallel:completed_map'),
    'build_aga census': (
        'asset_census:scan_meshes', 'asset_census:collect_placements', 'asset_census:variant_table',
        'asset_census:simulate_cache', 'build_parallel:ordered_map', 'build_parallel:completed_map'),
    'world-terrain': ('plan', 'terrain_wad', 'region_directory', 'ordered_map'),
    'world-scenery': ('ordered_map',),
    'census': ('ui_palette:reserve', 'read_interior', 'export_refs', 'append_meshes', 'rebuild_world_hull',
               'prepare_doors', 'load_master'),
    # Stages the v0.0.32 from-scratch profile showed idle against the workers they held.
    'bsp': ('append_meshes', 'rebuild_world_hull', 'ordered_map'),
    'interior': ('export_refs', 'append_meshes', 'rebuild_world_hull', 'read_interior',
                 'collision_index:index_model_collision', 'prepare_doors:prepare'),
    'area': ('populate', 'load_master', 'prepare_doors', 'ordered_map'),
    'balmora': ('import_town:collect', 'import_town:residents', 'import_town:rebuild_world_hull',
                'import_town:append_meshes', 'import_town:bound_visuals', 'import_town:convert_interiors',
                'import_town:publish', 'import_town:ordered_map', 'town_interiors:convert',
                'town_interiors:write_room_banks', 'prepare_area:populate'),
    'town': ('collect', 'residents', 'rebuild_world_hull', 'append_meshes', 'bound_visuals', 'convert_interiors',
             'publish', 'ordered_map', 'town_interiors:convert', 'town_interiors:write_room_banks',
             'prepare_area:populate'),
    'balmora-interiors': ('populate', 'ordered_map', 'prepare_area:load_master', 'prepare_area:prepare_doors',
                          'prepare_area:ordered_map'),
    'actor-contact': ('convert_builder_scene', 'annotate', 'bake_ground', 'check_recorded', 'require',
                      'frozen_maps'),
    'media': ('discover', 'lookups', 'prepare_video:prepare_video'),
    'chim-town': ('import_town:residents', 'import_town:ordered_map', 'ground_actors', 'chim.frame_map:frame_world'),
}
# The stage script that owns each table's plain names (for the consistency test).
INSTRUMENT_SCRIPTS = {'build_aga image': 'build_aga', 'build_aga census': 'build_aga',
                      'world-terrain': 'prepare_world_regions', 'world-scenery': 'prepare_world_scenery',
                      'census': 'prepare_census', 'bsp': 'prepare_mesh_bsp', 'interior': 'prepare_interior',
                      'area': 'prepare_area', 'balmora': 'prepare_balmora', 'town': 'import_town',
                      'balmora-interiors': 'prepare_balmora_interiors', 'actor-contact': 'check_scene_actors',
                      'media': 'prepare_media_assets', 'chim-town': 'chim_town'}
MAP_FUNCTIONS = ('ordered_map', 'completed_map')


def resolve_target(target, namespace):
    """(holder, attribute) for a table entry; holder is a dict or a module."""
    if ':' in target:
        module_name, attribute = target.split(':', 1)
        import importlib
        module = importlib.import_module(module_name)
        return module, attribute
    return namespace, target


def instrument(stage, namespace=None):
    """Time the listed functions of STAGE and every subprocess.run in this process.

    Does nothing unless the builder set AMIWIND_PROFILE_SECTIONS. Returns the
    targets that could not be found (also recorded in the sections file).
    """
    if not _section_file():
        return []
    if namespace is None:
        namespace = sys.modules['__main__'].__dict__
    missing = []
    for target in INSTRUMENT.get(stage, ()):
        try:
            holder, attribute = resolve_target(target, namespace)
            original = holder.get(attribute) if isinstance(holder, dict) else getattr(holder, attribute, None)
        except ImportError:
            original = None
        if original is None or not callable(original):
            missing.append(target)
            continue
        if getattr(original, '__amiwind_section__', None):
            continue
        label = target.split(':')[-1]
        timed = _timed_map(original, 'parallel map') if label in MAP_FUNCTIONS else section(label)(original)
        if isinstance(holder, dict):
            holder[attribute] = timed
        else:
            setattr(holder, attribute, timed)
    if not getattr(subprocess.run, '__amiwind_section__', None):
        subprocess.run = _timed_run(subprocess.run)
    for target in missing:
        _write_section({'name': 'instrumentation missing: ' + target, 'missing': True, 'pid': os.getpid(),
                        'depth': 0, 'start': round(time.monotonic(), 4), 'wall': 0,
                        'cpu_self': 0, 'cpu_children': 0})
    return missing


def read_sections(path):
    """Aggregate a sections file: [{name, calls, wall, max_wall, cpu_self, cpu_children, ...}]."""
    rows = {}
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        row = rows.setdefault(record['name'], {'name': record['name'], 'calls': 0, 'wall': 0.0, 'max_wall': 0.0,
                                               'cpu_self': 0.0, 'cpu_children': 0.0, 'min_depth': 99,
                                               'first_start': record.get('start', 0)})
        row['calls'] += 1
        row['wall'] += record.get('wall', 0)
        row['max_wall'] = max(row['max_wall'], record.get('wall', 0))
        row['cpu_self'] += record.get('cpu_self', 0)
        row['cpu_children'] += record.get('cpu_children', 0)
        row['min_depth'] = min(row['min_depth'], record.get('depth', 0))
        row['first_start'] = min(row['first_start'], record.get('start', 0))
        if 'items' in record:
            row['items'] = row.get('items', 0) + record['items']
        if record.get('missing'):
            row['missing'] = True
        if record.get('error'):
            row['errors'] = row.get('errors', 0) + 1
    result = []
    for row in rows.values():
        for key in ('wall', 'max_wall', 'cpu_self', 'cpu_children'):
            row[key] = round(row[key], 3)
        cpu = row['cpu_self'] + row['cpu_children']
        row['cores_avg'] = round(cpu / row['wall'], 2) if row['wall'] > 0 else None
        result.append(row)
    return sorted(result, key=lambda row: (row['first_start'], row['name']))


# --------------------------------------------------------------------------
# Stage wrapper (runs as `build_profile.py _stage STATS SECTIONS -- command...`)

def reads_path(stats_path):
    """The read list of the stage whose wrapper statistics go to STATS_PATH."""
    stats_path = Path(stats_path)
    return stats_path.parent.parent / READS_FOLDER / (stats_path.stem + '.txt')


def trace_environment(stats_path, environment):
    """Environment additions for a traced stage: the hook first on PYTHONPATH, the list to write."""
    hook = Path(stats_path).parent.parent / TRACE_HOOK_FOLDER
    if environment.get(TRACE_ENV, '') == 'off' or not (hook / 'sitecustomize.py').is_file():
        return {}
    existing = environment.get('PYTHONPATH', '')
    return {TRACE_ENV: str(reads_path(stats_path)),
            'PYTHONPATH': str(hook) + (os.pathsep + existing if existing else '')}


def stage_main(argv):
    if len(argv) < 4 or argv[2] != '--':
        print('usage: build_profile.py _stage STATS SECTIONS -- command...', file=sys.stderr)
        return 2
    stats_path, sections_path, command = Path(argv[0]), argv[1], argv[3:]
    environment = dict(os.environ, **{SECTIONS_ENV: sections_path})
    try:  # The stage's read list, checked against its fingerprint (tools/build_cache.py).
        environment.update(trace_environment(stats_path, environment))
    except Exception as exc:  # noqa: BLE001 - tracing must never stop a stage
        print(f'[warning] Stage read trace not started: {exc}', file=sys.stderr, flush=True)
    start = time.monotonic()
    before = _rusage_children()
    io_before, cgroup_before = read_proc_io(), read_cgroup_io()
    record = {'command_started': True}
    try:
        child = subprocess.Popen(command, env=environment)
    except OSError as exc:
        print(f'Cannot start stage command {command[:1]}: {exc}', file=sys.stderr, flush=True)
        child, code = None, 127
        record['command_started'] = False
    if child is not None:
        while True:
            try:
                code = child.wait()
                break
            except KeyboardInterrupt:
                continue  # The stage got the same interrupt; record how it ends.
    wall = time.monotonic() - start
    after = _rusage_children()
    record.update(wall=round(wall, 4), returncode=code, pid=child.pid if child else None)
    if before is not None and after is not None:
        user = after.ru_utime - before.ru_utime
        system = after.ru_stime - before.ru_stime
        record.update(cpu_user=round(user, 3), cpu_system=round(system, 3), cpu=round(user + system, 3),
                      # ru_maxrss of waited-for children: the largest single process, in KiB on Linux.
                      peak_process_rss_bytes=after.ru_maxrss * 1024 if sys.platform != 'darwin' else after.ru_maxrss)
        block_read = (after.ru_inblock - before.ru_inblock) * 512
        block_write = (after.ru_oublock - before.ru_oublock) * 512
    else:
        block_read = block_write = 0
    io_after, cgroup_after = read_proc_io(), read_cgroup_io()
    if io_before and io_after:
        record.update(read_bytes=io_after['read_bytes'] - io_before['read_bytes'],
                      write_bytes=io_after['write_bytes'] - io_before['write_bytes'],
                      rchar=io_after['rchar'] - io_before['rchar'], wchar=io_after['wchar'] - io_before['wchar'],
                      io_source='proc')
    elif block_read or block_write:
        record.update(read_bytes=block_read, write_bytes=block_write, io_source='rusage')
    elif cgroup_before and cgroup_after:
        record.update(read_bytes=cgroup_after['read_bytes'] - cgroup_before['read_bytes'],
                      write_bytes=cgroup_after['write_bytes'] - cgroup_before['write_bytes'],
                      io_source='cgroup')
    try:
        import resource
        own = resource.getrusage(resource.RUSAGE_SELF)
        record['wrapper_cpu'] = round(own.ru_utime + own.ru_stime, 4)
    except ImportError:
        pass
    try:
        temporary = stats_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        temporary.replace(stats_path)
    except OSError:
        pass
    if code is not None and code < 0 and os.name == 'posix':
        # Die of the same signal so the builder sees exactly what the stage did.
        signal.signal(-code, signal.SIG_DFL)
        os.kill(os.getpid(), -code)
    return code


# --------------------------------------------------------------------------
# Sampler thread (in the builder)

class Sampler(threading.Thread):
    def __init__(self, interval, start):
        super().__init__(name='build-profile-sampler', daemon=True)
        self.interval = interval
        self.origin = start
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.active = {}      # stage -> root pid
        self.last = {}        # stage -> (time, cpu seconds)
        self.times, self.total, self.cgroup, self.memory = [], [], [], []
        self.stages = {}      # stage -> [[sample index, cores, rss bytes, processes], ...]
        self.peak_rss = {}
        self.cpu_seconds = 0.0
        self.samples = 0
        self.cgroup_last = None
        self.host = []        # machine CPU busy share (0..1) per sample, /proc/stat
        self.host_last = None
        self.cpus = host_cpus()

    def add(self, stage, pid):
        with self.lock:
            self.active[stage] = pid

    def remove(self, stage):
        with self.lock:
            self.active.pop(stage, None)

    def run(self):
        while not self.stop_event.wait(self.interval):
            begin = time.thread_time()
            try:
                self.sample()
            except Exception:  # noqa: BLE001 - a failed sample must never stop a build
                pass
            self.cpu_seconds += time.thread_time() - begin

    def sample(self):
        now = time.monotonic()
        with self.lock:
            active = dict(self.active)
        index = len(self.times)
        total = 0.0
        for stage, pid in active.items():
            cpu, rss, count = tree_usage(pid)
            if count == 0:
                continue
            previous = self.last.get(stage)
            self.last[stage] = (now, cpu)
            self.peak_rss[stage] = max(self.peak_rss.get(stage, 0), rss)
            if previous is None or now <= previous[0]:
                continue
            cores = max(0.0, (cpu - previous[1]) / (now - previous[0]))
            total += cores
            self.stages.setdefault(stage, []).append([index, round(cores, 3), rss, count])
        cgroup = read_cgroup_cpu()
        cgroup_cores = None
        if cgroup is not None and self.cgroup_last is not None and now > self.cgroup_last[0]:
            cgroup_cores = round(max(0.0, (cgroup - self.cgroup_last[1]) / (now - self.cgroup_last[0])), 3)
        if cgroup is not None:
            self.cgroup_last = (now, cgroup)
        host, busy = read_host_cpu(), None
        if host is not None and self.host_last is not None and host[1] > self.host_last[1]:
            busy = round(max(0.0, min(1.0, (host[0] - self.host_last[0]) / (host[1] - self.host_last[1]))), 4)
        if host is not None:
            self.host_last = host
        self.host.append(busy)
        self.times.append(round(now - self.origin, 3))
        self.total.append(round(total, 3))
        self.cgroup.append(cgroup_cores)
        self.memory.append(read_cgroup_memory())
        self.samples += 1

    def stop(self):
        self.stop_event.set()
        if self.is_alive():
            self.join(timeout=5)

    def timeline(self):
        return {'interval': self.interval, 't': self.times, 'cores': self.total,
                'cgroup_cores': self.cgroup if any(v is not None for v in self.cgroup) else None,
                'memory_bytes': self.memory if any(v is not None for v in self.memory) else None,
                'host_cpus': self.cpus,
                'host_busy': self.host if any(v is not None for v in self.host) else None,
                'stages': {name: [[row[0], row[1]] for row in rows] for name, rows in self.stages.items()}}


# --------------------------------------------------------------------------
# Session (the builder's hooks; tools/build.py and tools/build_parallel.py)

class NullSession:
    enabled = False

    def command(self, number, name, command, jobs):
        return command

    def started(self, name, pid):
        pass

    def finished(self, name, entry):
        pass

    def close(self, receipt):
        pass


class Session:
    """Profiles one build run. All hooks are cheap and never raise into the build."""
    enabled = True

    def __init__(self, run, steps, metadata, dependencies=None, interval=None):
        self.run = Path(run)
        self.folder = self.run / 'profile'
        (self.folder / 'stages').mkdir(parents=True, exist_ok=True)
        (self.folder / 'sections').mkdir(exist_ok=True)
        self.metadata = metadata
        self.budget = int(metadata.get('compiler_jobs', 1) or 1)
        self.order = [name for name, _ in steps]
        if dependencies is None:
            try:
                from build_parallel import plan_skipped, stage_dependencies
                dependencies = stage_dependencies(steps, plan_skipped(metadata))
            except (ImportError, ValueError):
                dependencies = {name: tuple(self.order[i - 1:i]) for i, name in enumerate(self.order)}
        self.dependencies = {name: list(deps) for name, deps in dependencies.items()}
        self.start = time.monotonic()
        self.started_at = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        self.stages = {}
        self.wrap = linux_proc() or os.name == 'posix'
        if interval is None:
            try:
                interval = float(os.environ.get(INTERVAL_ENV, DEFAULT_INTERVAL))
            except ValueError:
                interval = DEFAULT_INTERVAL
        self.sampler = Sampler(max(0.01, interval), self.start) if linux_proc() else None
        if self.sampler:
            self.sampler.start()
        try:
            import build_cache
            self.cache = build_cache.Recorder(self.run, steps, metadata)
        except Exception as exc:  # noqa: BLE001 - output manifests are optional evidence
            print(f'[warning] Build output manifests disabled: {exc}', flush=True)
            self.cache = None
        # Live progress and ETA (build-progress.json; tools/build_progress.py).
        try:
            import build_progress
            self.progress = build_progress.start(self.run, self.order, self.dependencies, metadata,
                                                 self.sampler, self.start)
        except Exception as exc:  # noqa: BLE001 - progress must never fail a build
            print(f'[warning] Live build progress disabled: {exc}', flush=True)
            self.progress = None
        self.closed = False

    def _paths(self, number, name):
        stem = f'{number:02}-{name}'
        return self.folder / 'stages' / f'{stem}.json', self.folder / 'sections' / f'{stem}.jsonl'

    def command(self, number, name, command, jobs):
        """The command to start for this stage (the profiling wrapper around it)."""
        stats, sections = self._paths(number, name)
        self.stages[name] = {'name': name, 'number': number, 'jobs': jobs, 'start': round(time.monotonic() - self.start, 3),
                             'stats': stats, 'sections': sections, 'status': 'running'}
        if self.progress is not None:
            self.progress.stage_started(name, number, jobs)
        if self.cache is not None:
            try:
                self.cache.before(name, command)
            except Exception as exc:  # noqa: BLE001
                print(f'[warning] {name}: output manifest snapshot failed: {exc}', flush=True)
        if not self.wrap:
            return command
        return [sys.executable, str(Path(__file__).resolve()), '_stage', str(stats), str(sections), '--', *map(str, command)]

    def started(self, name, pid):
        if self.sampler and name in self.stages:
            self.sampler.add(name, pid)

    def finished(self, name, entry):
        stage = self.stages.get(name)
        if stage is None or stage['status'] != 'running':
            return
        stage['end'] = round(time.monotonic() - self.start, 3)
        stage['status'] = entry.get('status', 'unknown')
        if entry.get('worker_changes'):
            # Scheduler times count from its own start; shift them onto this session's clock.
            offset = stage['start'] - entry['started_seconds'] if entry.get('started_seconds') is not None else 0.0
            stage['worker_changes'] = [[round(at + offset, 3), int(value)] for at, value in entry['worker_changes']]
        if self.progress is not None:
            self.progress.stage_finished(name, stage['status'])
        if self.sampler:
            self.sampler.remove(name)
        try:
            stats = json.loads(stage['stats'].read_text()) if stage['stats'].is_file() else {}
        except (OSError, ValueError):
            stats = {}
        stage['measured'] = stats
        summary = {'jobs': stage['jobs']}
        low, high, mean = allowance_summary({'start': stage['start'], 'end': stage['end'], 'jobs': stage['jobs'],
                                             'worker_changes': stage.get('worker_changes')})
        if (low, high) != (stage['jobs'], stage['jobs']):
            summary.update(jobs_min=low, jobs_max=high, jobs_mean=mean)
        if 'cpu' in stats:
            wall = stats.get('wall') or (stage['end'] - stage['start'])
            summary.update(cpu_seconds=stats['cpu'], cores_avg=round(stats['cpu'] / wall, 2) if wall else None,
                           peak_process_rss_bytes=stats.get('peak_process_rss_bytes'))
        if 'read_bytes' in stats:
            summary.update(read_bytes=stats['read_bytes'], write_bytes=stats['write_bytes'], io_source=stats['io_source'])
        if self.cache is not None and entry.get('status') == 'passed':
            began = time.monotonic()
            try:
                manifest = self.cache.after(name, entry, reads=reads_path(stage['stats']) if self.wrap else None)
                if manifest:
                    summary['outputs'] = {'files': manifest['counts']['files'], 'bytes': manifest['counts']['bytes']}
            except Exception as exc:  # noqa: BLE001
                print(f'[warning] {name}: output manifest failed: {exc}', flush=True)
            stage['manifest_seconds'] = round(time.monotonic() - began, 3)
        entry['profile'] = summary
        reuse = (self.metadata.get('stage_cache') or {}).get('reused', {}).get(name)
        if reuse:
            refused = self.run / 'profile' / 'reuse-fallback' / f'{name}.txt'
            if refused.is_file():
                entry['reuse_refused'] = refused.read_text().strip()
                reuse['refused'] = entry['reuse_refused']
            else:
                entry['reused'] = f"reused (fingerprint {reuse['fingerprint']}) from {reuse['from']}"

    def close(self, receipt):
        if self.closed:
            return
        self.closed = True
        if self.progress is not None:
            self.progress.close(receipt.get('status'))
        if self.sampler:
            self.sampler.stop()
        try:
            if self.cache is not None:
                self.cache.close(receipt)
        except Exception as exc:  # noqa: BLE001
            print(f'[warning] Build output manifests incomplete: {exc}', flush=True)
        try:
            profile = self.collect(receipt)
            analysis = analyse(profile)
            profile['analysis'] = analysis
            temporary = self.run / (PROFILE_NAME + '.tmp')
            temporary.write_text(json.dumps(profile, indent=1) + '\n')
            temporary.replace(self.run / PROFILE_NAME)
        except Exception as exc:  # noqa: BLE001 - profiling must never fail a build
            print(f'[warning] Build profile not written: {exc}', flush=True)

    def collect(self, receipt):
        wall = time.monotonic() - self.start
        entries = {entry['name']: entry for entry in receipt.get('steps', [])}
        stages = []
        for name in self.order:
            stage = self.stages.get(name)
            entry = entries.get(name, {})
            if stage is None:
                continue
            measured = stage.get('measured', {})
            end = stage.get('end', round(wall, 3))
            row = {'name': name, 'number': stage['number'], 'status': entry.get('status', stage['status']),
                   'jobs': stage['jobs'], 'dependencies': self.dependencies.get(name, []),
                   'start': stage['start'], 'end': end, 'wall': round(end - stage['start'], 3)}
            if stage.get('worker_changes'):
                row['worker_changes'] = stage['worker_changes']
            row['jobs_min'], row['jobs_max'], row['jobs_mean'] = allowance_summary(row)
            for key in ('cpu_user', 'cpu_system', 'cpu', 'peak_process_rss_bytes', 'read_bytes', 'write_bytes',
                        'rchar', 'wchar', 'io_source', 'wrapper_cpu'):
                if key in measured:
                    row[key] = measured[key]
            if 'cpu' in row and row['wall'] > 0:
                row['cores_avg'] = round(row['cpu'] / row['wall'], 2)
            if self.sampler and name in self.sampler.peak_rss:
                row['peak_tree_rss_bytes'] = self.sampler.peak_rss[name]
            if stage.get('manifest_seconds') is not None:
                row['manifest_seconds'] = stage['manifest_seconds']
            sections = read_sections(stage['sections'])
            for item in sections:
                item['start'] = round(item.pop('first_start') - self.start, 3)
            if sections:
                row['sections'] = sections
            reuse = (receipt.get('stage_cache') or {}).get('reused', {}).get(name)
            if reuse and not reuse.get('refused'):
                row['reused'] = {'from': reuse.get('from'), 'fingerprint': reuse.get('fingerprint')}
            fingerprint = (receipt.get('stage_cache') or {}).get('fingerprints', {}).get(name)
            if fingerprint:
                row['fingerprint'] = fingerprint
            stages.append(row)
        timeline = self.sampler.timeline() if self.sampler else None
        for row in stages:
            load = host_load(row, timeline)
            if load:
                row['host'] = load
        # cgroup I/O is shared by every stage that ran at the same time.
        for row in stages:
            if row.get('io_source') == 'cgroup':
                row['io_shared_with'] = [other['name'] for other in stages if other is not row
                                         and other['start'] < row['end'] and row['start'] < other['end']]
        wrapper = sum(row.get('wrapper_cpu', 0) for row in stages)
        overhead = {'wrapper_cpu_seconds': round(wrapper, 3),
                    'manifest_seconds': round(sum(row.get('manifest_seconds', 0) for row in stages), 3)}
        if self.sampler:
            overhead.update(sampler_cpu_seconds=round(self.sampler.cpu_seconds, 4), sampler_samples=self.sampler.samples,
                            sampler_share_of_one_core=round(self.sampler.cpu_seconds / wall, 6) if wall > 0 else None)
        return {'schema': SCHEMA, 'run': str(self.run), 'version': receipt.get('runtime_version'),
                'status': receipt.get('status'), 'started_at': self.started_at,
                'wall_seconds': round(wall, 3), 'budget': self.budget,
                'scheduling': 'serial' if receipt.get('scheduler') is None else receipt.get('scheduler'),
                'platform': sys.platform, 'counters': 'linux-proc' if linux_proc() else 'wall-only',
                'overhead': overhead, 'stages': stages,
                'timeline': timeline,
                'host_cpus': host_cpus(),
                'reuse_from': (receipt.get('stage_cache') or {}).get('reuse_from')}


def start(run, steps, metadata, dependencies=None):
    """The builder's profiling session (a no-op session when profiling is off)."""
    if not enabled(metadata):
        return NullSession()
    try:
        return Session(run, steps, metadata, dependencies)
    except Exception as exc:  # noqa: BLE001
        print(f'[warning] Build profiling disabled: {exc}', flush=True)
        return NullSession()


# --------------------------------------------------------------------------
# Analysis

def critical_path(stages):
    """Longest dependency chain by stage wall time, and the chain the build actually waited on.

    ideal: the build's lower bound with unlimited cores (sum of the longest chain).
    actual: from the last stage to finish back through the dependency that finished last.
    slack: how long each stage could have been delayed without lengthening the ideal path.
    """
    by_name = {row['name']: row for row in stages}
    order = [row['name'] for row in sorted(stages, key=lambda r: (r['start'], r['name']))]
    earliest, previous = {}, {}

    def finish(name, trail=()):
        if name in earliest:
            return earliest[name] + by_name[name]['wall']
        if name in trail:
            raise ValueError('Dependency cycle at ' + name)
        start, best = 0.0, None
        for dep in by_name[name].get('dependencies', []):
            if dep in by_name:
                end = finish(dep, (*trail, name))
                if end > start:
                    start, best = end, dep
        earliest[name], previous[name] = start, best
        return start + by_name[name]['wall']

    if not stages:
        return {'ideal_seconds': 0, 'path': [], 'actual_path': [], 'slack': {}}
    ends = {name: finish(name) for name in order}
    last = max(ends, key=lambda name: (ends[name], name))
    path = []
    node = last
    while node:
        path.append(node)
        node = previous.get(node)
    path.reverse()
    total = ends[last]
    latest = {}
    for name in sorted(order, key=lambda n: -ends[n]):
        children = [other for other in order if name in by_name[other].get('dependencies', [])]
        latest_end = min([latest[c] for c in children if c in latest], default=total)
        latest[name] = latest_end - by_name[name]['wall']
    slack = {name: round(max(0.0, latest[name] - earliest[name]), 3) for name in order}
    actual = []
    node = max(stages, key=lambda r: (r['end'], r['name']))['name']
    while node:
        actual.append(node)
        deps = [by_name[d] for d in by_name[node].get('dependencies', []) if d in by_name]
        node = max(deps, key=lambda r: (r['end'], r['name']))['name'] if deps else None
    actual.reverse()
    return {'ideal_seconds': round(total, 3), 'path': path, 'actual_path': actual, 'slack': slack}


def host_load(stage, timeline, share=HOST_BUSY_SHARE):
    """Machine load while a stage ran: CPU count, machine busy %, this build's own
    cores and the share other work used; host_busy when that share exceeds `share`.

    /proc/stat counts the whole machine (in a container: the VM shared by every
    container and job). This build's use is the container cgroup when known, else
    the stage process trees. None without samples in the stage's time range."""
    if not timeline or not timeline.get('host_busy'):
        return None
    cpus = timeline.get('host_cpus') or 1
    own = timeline.get('cgroup_cores') or timeline.get('cores') or []
    busy, mine = [], []
    for index, at in enumerate(timeline['t']):
        value = timeline['host_busy'][index] if index < len(timeline['host_busy']) else None
        if value is None or not stage['start'] <= at <= stage['end']:
            continue
        busy.append(value)
        cores = own[index] if index < len(own) else None
        mine.append(cores if cores is not None else 0.0)
    if not busy:
        return None
    host = sum(busy) / len(busy)
    build = sum(mine) / len(mine)
    other = max(0.0, host - build / cpus)
    return {'cpus': cpus, 'busy_percent': round(100 * host, 1), 'build_cores': round(build, 2),
            'other_percent': round(100 * other, 1), 'samples': len(busy), 'host_busy': other > share}


def allowance_steps(stage):
    """[(time, workers)] a stage held: its start value, then every rebalance of the parallel
    scheduler (worker_changes, profile time). BUILD-PROFILE-JOBS-START-ONLY-33: the start value
    alone is often 1 for a stage that held 12 workers a moment later."""
    start = stage.get('start') or 0.0
    steps = [(start, max(1, int(stage.get('jobs') or 1)))]
    for at, value in sorted(stage.get('worker_changes') or []):
        steps.append((max(start, at), max(1, int(value))))
    return steps


def allowance_at(steps, moment):
    value = steps[0][1]
    for at, workers in steps:
        if at > moment:
            break
        value = workers
    return value


def allowance_summary(stage):
    """(min, max, time-weighted mean) of the workers a stage held from its start to its end."""
    steps = allowance_steps(stage)
    start = stage.get('start') or 0.0
    end = stage.get('end', start)
    values = [workers for at, workers in steps if at <= end] or [steps[0][1]]
    if end <= start:
        return min(values), max(values), float(steps[-1][1])
    total = 0.0
    for index, (at, workers) in enumerate(steps):
        until = steps[index + 1][0] if index + 1 < len(steps) else end
        total += workers * max(0.0, min(until, end) - min(at, end))
    return min(values), max(values), round(total / (end - start), 2)


def jobs_text(stage):
    """The jobs column: the start value, or the range the scheduler moved it through."""
    low, high = stage.get('jobs_min'), stage.get('jobs_max')
    if low is None or high is None or low == high:
        return str(stage.get('jobs', '-'))
    return f'{low}-{high}'


def idle_periods(stage, timeline, share=IDLE_SHARE, minimum=IDLE_SECONDS):
    """Longest run of samples where STAGE used less than SHARE of the workers it held at that moment.

    The workers come from its start value and every rebalance (allowance_steps); 'jobs' in the
    result is their mean over the low samples, 'jobs_start' the start value."""
    steps = allowance_steps(stage)
    if timeline and stage['name'] in (timeline.get('stages') or {}):
        times = timeline['t']
        interval = timeline.get('interval') or DEFAULT_INTERVAL
        longest = current = 0.0
        low_cores, low_jobs = [], []
        previous_index = None
        for index, cores in timeline['stages'][stage['name']]:
            gap = interval if previous_index is None else (times[index] - times[previous_index] if index < len(times) else interval)
            previous_index = index
            jobs = allowance_at(steps, times[index]) if index < len(times) else steps[-1][1]
            if cores < share * jobs:
                current += gap
                low_cores.append(cores)
                low_jobs.append(jobs)
                longest = max(longest, current)
            else:
                current = 0.0
        if longest > minimum:
            return {'seconds': round(longest, 1), 'jobs': max(1, round(sum(low_jobs) / len(low_jobs))),
                    'jobs_start': steps[0][1],
                    'cores_while_idle': round(sum(low_cores) / len(low_cores), 2) if low_cores else None,
                    'source': 'timeline'}
        return None
    cpu, wall = stage.get('cpu'), stage.get('wall', 0)
    mean = stage.get('jobs_mean') or allowance_summary(stage)[2]
    if cpu is not None and wall > minimum and cpu / wall < share * mean:
        return {'seconds': round(wall, 1), 'jobs': max(1, round(mean)), 'jobs_start': steps[0][1],
                'cores_while_idle': round(cpu / wall, 2), 'source': 'average'}
    return None


def suggestions(profile, critical, warnings):
    lines = []
    on_path = set(critical['path'])
    for warning in warnings:
        sections = [row for row in warning.get('sections', [])]
        detail = (' Slowest sections: ' + ', '.join(f"{row['name']} {row['wall']:.0f}s ({row['cores_avg']} cores)"
                                                    for row in sections)) if sections else ''
        where = ' It is on the critical path, so this lengthens the whole build.' if warning['stage'] in on_path else ''
        lines.append(f"{warning['stage']}: used {warning['cores_while_idle']} of {warning['jobs']} cores for "
                     f"{warning['seconds']:.0f}s. Parallelize its serial loop or give the budget to other stages.{where}{detail}")
    stages = {row['name']: row for row in profile['stages']}
    for name in critical['path']:
        row = stages[name]
        held = row.get('jobs_max') or row.get('jobs', 1)
        if row['wall'] >= 30 and held == 1 and row.get('cores_avg', 0) and row['cores_avg'] < 1.5:
            lines.append(f"{name}: {row['wall']:.0f}s on one core on the critical path; it takes no --jobs budget. "
                         'A parallel inner loop would shorten the build directly.')
    budget = profile.get('budget') or 1
    timeline = profile.get('timeline')
    cpu = sum(row.get('cpu', 0) for row in profile['stages'])
    average = None
    if cpu and profile.get('wall_seconds'):
        average = cpu / profile['wall_seconds']
    elif timeline and timeline.get('cores'):
        average = sum(timeline['cores']) / len(timeline['cores'])
    if average is not None:
        if budget > 1 and average < 0.5 * budget:
            lines.append(f'Whole build: {average:.1f} of {budget} cores busy on average '
                         f'({100 * average / budget:.0f} %). The critical path, not the core count, sets the build time.')
    wall = profile.get('wall_seconds') or 0
    if wall and critical['ideal_seconds'] and wall > 1.25 * critical['ideal_seconds']:
        lines.append(f"Build took {wall:.0f}s; its longest dependency chain is {critical['ideal_seconds']:.0f}s. "
                     'The difference is waiting for job slots: stages off the critical path should get fewer jobs.')
    from build_cache import NON_REUSABLE
    reusable = [row for row in profile['stages'] if row.get('fingerprint') and not row.get('reused')
                and row['name'] not in NON_REUSABLE and row['wall'] >= 60]
    if reusable and not profile.get('reuse_from'):
        lines.append('Development rebuilds: --reuse-from THIS_RUN copies the outputs of stages whose fingerprint is '
                     f"unchanged (here {', '.join(row['name'] for row in reusable)}: "
                     f"{sum(row['wall'] for row in reusable):.0f}s). Never for releases; see docs/BUILD_PROFILE.md.")
    return lines


def analyse(profile, top=10):
    stages = profile.get('stages', [])
    critical = critical_path(stages)
    warnings = []
    for row in stages:
        period = idle_periods(row, profile.get('timeline'))
        if period:
            sections = sorted(row.get('sections', []), key=lambda s: -s['wall'])[:3]
            warnings.append({'stage': row['name'], **period,
                             'sections': [{'name': s['name'], 'wall': s['wall'], 'cores_avg': s.get('cores_avg')} for s in sections]})
    slowest = [{'name': row['name'], 'wall': row['wall'], 'cores_avg': row.get('cores_avg'), 'jobs': row.get('jobs'),
                'jobs_max': row.get('jobs_max'), 'jobs_mean': row.get('jobs_mean'),
                'critical': row['name'] in critical['path']}
               for row in sorted(stages, key=lambda r: -r['wall'])[:top]]
    sections = []
    for row in stages:
        for item in row.get('sections', []):
            if not item.get('missing'):
                sections.append({'stage': row['name'], 'name': item['name'], 'wall': item['wall'], 'calls': item['calls'],
                                 'cores_avg': item.get('cores_avg')})
    sections = sorted(sections, key=lambda s: -s['wall'])[:top]
    missing = [f"{row['name']}: {item['name'][len('instrumentation missing: '):]}" for row in stages
               for item in row.get('sections', []) if item.get('missing')]
    host = []
    for row in stages:
        load = row.get('host') or host_load(row, profile.get('timeline'))
        if load and load['host_busy']:
            host.append({'stage': row['name'], 'other_percent': load['other_percent'],
                         'busy_percent': load['busy_percent'], 'cpus': load['cpus']})
    result = {'critical_path': critical, 'idle_warnings': warnings, 'slowest_stages': slowest,
              'slowest_sections': sections, 'instrumentation_missing': missing, 'host_busy': host}
    result['suggestions'] = suggestions(profile, critical, warnings)
    return result


def _host_state(profile, row):
    load = row.get('host') or host_load(row, profile.get('timeline'))
    if load is None:
        return 'unknown'
    return 'busy' if load['host_busy'] else 'quiet'


def compare(new, old, share=REGRESSION_SHARE, seconds=REGRESSION_SECONDS):
    """Per-stage wall time of NEW against OLD; regressions are slower by > share and > seconds.

    Every row carries the host state of both runs (busy, quiet, unknown); a stage
    measured on a busy host in one run and a quiet one in the other is listed in
    host_mismatch, so such numbers are never compared silently."""
    old_stages = {row['name']: row for row in old.get('stages', [])}
    rows = []
    for row in new.get('stages', []):
        before = old_stages.get(row['name'])
        if before is None:
            rows.append({'name': row['name'], 'new': row['wall'], 'old': None, 'delta': None, 'status': 'new stage'})
            continue
        delta = row['wall'] - before['wall']
        status = 'slower' if delta > seconds and delta > share * before['wall'] else \
                 'faster' if -delta > seconds and -delta > share * before['wall'] else 'same'
        if row.get('reused'):
            status = 'reused'
        from build_cache import NON_REUSABLE
        same = (bool(row.get('fingerprint')) and row.get('fingerprint') == before.get('fingerprint')
                and row['name'] not in NON_REUSABLE)
        rows.append({'name': row['name'], 'new': row['wall'], 'old': before['wall'], 'delta': round(delta, 3),
                     'percent': round(100 * delta / before['wall'], 1) if before['wall'] else None, 'status': status,
                     'same_fingerprint': same, 'host_new': _host_state(new, row), 'host_old': _host_state(old, before)})
    for name in old_stages:
        if name not in {row['name'] for row in new.get('stages', [])}:
            rows.append({'name': name, 'new': None, 'old': old_stages[name]['wall'], 'delta': None, 'status': 'removed'})
    total = (new.get('wall_seconds') or 0) - (old.get('wall_seconds') or 0)
    mismatch = [row['name'] for row in rows if 'busy' in (row.get('host_new'), row.get('host_old'))
                and row.get('host_new') != row.get('host_old')]
    return {'stages': rows, 'wall_delta': round(total, 3),
            'regressions': [row['name'] for row in rows if row['status'] == 'slower'],
            'host_mismatch': mismatch,
            'busy_host': {'new': bool((new.get('analysis') or analyse(new))['host_busy']),
                          'old': bool((old.get('analysis') or analyse(old))['host_busy'])}}


# --------------------------------------------------------------------------
# Optimizer: where the cores went idle, with concrete suggestions

TAIL_CORES = 1.5        # a stage that ran on 2+ cores and then on fewer than this ...
TAIL_SECONDS = 30.0     # ... for longer than this ...
TAIL_SHARE = 0.10       # ... and longer than this share of its wall time has a single-core tail
SERIAL_SECONDS = 60.0   # a one-core stage on the critical path longer than this is listed


def single_core_tail(stage, timeline, cores=TAIL_CORES, minimum=TAIL_SECONDS, share=TAIL_SHARE):
    """The stretch at the end of a parallel stage that ran on about one core, or None.

    Typical cause: the largest item of a worker pool finishes last while the
    other workers have nothing left. Needs the profiler's CPU timeline."""
    rows = ((timeline or {}).get('stages') or {}).get(stage['name'])
    if not rows:
        return None
    times = timeline.get('t') or []
    interval = timeline.get('interval') or DEFAULT_INTERVAL
    points = [(times[index], value) for index, value in rows if index < len(times)]
    seconds, first = 0.0, len(points)
    for index in range(len(points) - 1, -1, -1):
        if points[index][1] >= cores:
            break
        seconds += points[index][0] - points[index - 1][0] if index > 0 else interval
        first = index
    before = [value for _, value in points[:first]]
    if not before or max(before) < 2 or seconds <= minimum or seconds <= share * (stage.get('wall') or 0):
        return None
    tail = [value for _, value in points[first:]]
    return {'seconds': round(seconds, 1), 'cores': round(sum(tail) / len(tail), 2),
            'peak_cores_before': round(max(before), 2)}


def _suggestion(item):
    stage, seconds = item['stage'], _seconds(item.get('seconds'))
    sections = item.get('sections') or []
    where = (' Slowest sections: ' + ', '.join(f"{s['name']} {_seconds(s['wall'])} ({s.get('cores_avg')} cores)"
                                                for s in sections) + '.') if sections else ''
    if item['kind'] == 'idle':
        text = (f"{stage} used {item.get('cores')} of {item.get('jobs')} cores for {seconds}. Find its serial loop or "
                'the waits (timed sections show where), run independent items on the shared worker pool '
                '(tools/build_parallel.py ordered_map or completed_map), or give the idle workers to other stages; '
                f'prove byte-identical outputs against --jobs 1.{where}')
    elif item['kind'] == 'tail':
        text = (f"{stage} ran on up to {item.get('peak_cores_before')} cores, then spent its last {seconds} on "
                f"{item.get('cores')} core(s): one large item finished last. Submit the largest items first "
                '(completed_map over a size-sorted list), split the largest item, or let the next stage start on '
                f'the finished part.{where}')
    elif item['kind'] == 'serial-critical':
        held = item.get('jobs_max') or 1
        budget = ('takes no --jobs budget' if held <= 1 else
                  f'held up to {held} workers without using them')
        text = (f"{stage} runs {seconds} on one core on the critical path and {budget}; a parallel "
                f'inner loop shortens the whole build directly.{where}')
    else:
        text = (f"The build waited {seconds} for job slots (wall {_seconds(item.get('wall'))} against a longest "
                f"dependency chain of {_seconds(item.get('ideal'))}): give stages off the critical path fewer "
                "workers; the report lists each stage's slack.")
    if item.get('critical') and item['kind'] in ('idle', 'tail'):
        text += ' It is on the critical path, so this lengthens the build.'
    if item.get('host_busy'):
        text += ' Measured while other work loaded the machine: re-measure on a quiet host before acting.'
    return text


def optimize(profile, share=IDLE_SHARE, minimum=IDLE_SECONDS):
    """Optimizer items of one profile: idle-core stages, single-core tails, serial stages on the
    critical path and waiting for job slots. potential_seconds is an upper bound of the wall time
    the item could save (the low-core stretch run at the stage's parallel width)."""
    analysis = profile.get('analysis') or analyse(profile)
    critical = analysis['critical_path']
    on_path = set(critical['path'])
    timeline = profile.get('timeline')
    run = Path(str(profile.get('run') or '')).name
    interval = (timeline or {}).get('interval') or DEFAULT_INTERVAL
    items = []
    for row in profile.get('stages', []):
        if row.get('reused'):
            continue
        common = {'run': run, 'stage': row['name'], 'wall': row.get('wall'), 'jobs': row.get('jobs'),
                  'jobs_max': row.get('jobs_max') or row.get('jobs'), 'jobs_start': row.get('jobs'),
                  'critical': row['name'] in on_path, 'host_busy': bool((row.get('host') or {}).get('host_busy')),
                  'sections': [{'name': s['name'], 'wall': s['wall'], 'cores_avg': s.get('cores_avg')}
                               for s in sorted(row.get('sections', []), key=lambda s: -s['wall'])
                               if not s.get('missing')][:3]}
        idle = idle_periods(row, timeline, share, minimum)
        tail = single_core_tail(row, timeline)
        if idle and not (tail and tail['seconds'] >= idle['seconds'] - 2 * interval):
            cores = idle.get('cores_while_idle') or 0.0
            items.append(dict(common, kind='idle', seconds=idle['seconds'], cores=cores, jobs=idle['jobs'],
                              jobs_start=idle['jobs_start'], method=idle['source'],
                              potential_seconds=round(idle['seconds'] * max(0.0, 1 - cores / idle['jobs']), 1)))
        if tail:
            items.append(dict(common, kind='tail', seconds=tail['seconds'], cores=tail['cores'],
                              peak_cores_before=tail['peak_cores_before'],
                              potential_seconds=round(tail['seconds'] * (1 - 1 / tail['peak_cores_before']), 1)))
        if (not idle and not tail and row['name'] in on_path and (row.get('wall') or 0) >= SERIAL_SECONDS
                and row.get('cores_avg') is not None and row['cores_avg'] < TAIL_CORES):
            items.append(dict(common, kind='serial-critical', seconds=row['wall'], cores=row['cores_avg'],
                              potential_seconds=None))
    wall, ideal = profile.get('wall_seconds') or 0, critical['ideal_seconds']
    if wall and ideal and wall > 1.25 * ideal:
        items.append({'run': run, 'stage': '(whole build)', 'kind': 'slot-wait', 'seconds': round(wall - ideal, 1),
                      'wall': wall, 'ideal': ideal, 'critical': True, 'host_busy': bool(analysis.get('host_busy')),
                      'potential_seconds': round(wall - ideal, 1)})
    for item in items:
        item['suggestion'] = _suggestion(item)
    return items


def optimize_runs(profiles, share=IDLE_SHARE, minimum=IDLE_SECONDS):
    """Items of several profiles grouped by (stage, kind): how often, worst case, best saving."""
    groups = {}
    for profile in profiles:
        for item in optimize(profile, share, minimum):
            group = groups.setdefault((item['stage'], item['kind']), {'stage': item['stage'], 'kind': item['kind'],
                                                                    'runs': [], 'items': []})
            group['runs'].append(item['run'])
            group['items'].append(item)
    rows = []
    for group in groups.values():
        worst = max(group['items'], key=lambda item: item.get('seconds') or 0)
        potentials = [item['potential_seconds'] for item in group['items'] if item.get('potential_seconds') is not None]
        rows.append({'stage': group['stage'], 'kind': group['kind'], 'runs': group['runs'], 'of_runs': len(profiles),
                     'worst_seconds': worst.get('seconds'), 'cores': worst.get('cores'), 'jobs': worst.get('jobs'),
                     'critical': any(item.get('critical') for item in group['items']),
                     'host_busy': any(item.get('host_busy') for item in group['items']),
                     'potential_seconds': max(potentials) if potentials else None,
                     'suggestion': worst['suggestion']})
    rows.sort(key=lambda row: (not row['critical'], -(row['potential_seconds'] or row['worst_seconds'] or 0)))
    return rows


def optimize_lines(rows, runs):
    lines = [f"Optimizer: {len(runs)} run(s): " + ', '.join(runs),
             f"Items: a stage under {int(100 * IDLE_SHARE)} % of its jobs for > {IDLE_SECONDS:.0f} s (idle), a parallel "
             f"stage ending on about one core for > {TAIL_SECONDS:.0f} s (tail), a one-core stage on the critical path "
             '(serial-critical), waiting for job slots (slot-wait). Critical-path items first.']
    if not rows:
        return lines + ['', 'Nothing to optimize: no idle cores, tails or slot waits found.']
    lines += ['', f"{'#':>3} {'stage':<24}{'kind':<16}{'runs':>6}{'worst':>9}{'cores/jobs':>12}{'saves up to':>13}  note"]
    for number, row in enumerate(rows, 1):
        used = f"{row['cores']}/{row['jobs']}" if row.get('cores') is not None and row.get('jobs') else (
            str(row['cores']) if row.get('cores') is not None else '-')
        note = ', '.join(text for flag, text in ((row['critical'], 'critical'), (row['host_busy'], 'host busy')) if flag)
        runs_text = f"{len(row['runs'])}/{row['of_runs']}"
        lines.append(f"{number:>3} {row['stage'][:23]:<24}{row['kind']:<16}{runs_text:>6}"
                     f"{_seconds(row['worst_seconds']):>9}{used:>12}{_seconds(row['potential_seconds']):>13}  {note}")
    lines.append('')
    for number, row in enumerate(rows, 1):
        lines.append(f"{number:>3}. {row['suggestion']}")
    return lines


# --------------------------------------------------------------------------
# Reports

def load(path):
    path = Path(path)
    if path.is_dir():
        path = path / PROFILE_NAME
    profile = json.loads(path.read_text())
    if profile.get('schema') != SCHEMA:
        raise ValueError(f'{path}: not a build profile ({profile.get("schema")})')
    if 'analysis' not in profile:
        profile['analysis'] = analyse(profile)
    return profile


def _seconds(value):
    if value is None:
        return '-'
    value = float(value)
    if value >= 3600:
        return f'{int(value // 3600)}h{int(value % 3600 // 60):02d}m'
    if value >= 60:
        return f'{int(value // 60)}m{int(value % 60):02d}s'
    return f'{value:.1f}s'


def _bytes(value):
    if value is None:
        return '-'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(value) < 1024 or unit == 'TiB':
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


def summary_lines(profile, top=5):
    """Short footer for the build summary."""
    analysis = profile.get('analysis') or analyse(profile)
    critical = analysis['critical_path']
    cpu = sum(row.get('cpu', 0) for row in profile['stages'])
    wall = profile.get('wall_seconds') or 0
    lines = [f"Build profile: {_seconds(wall)} wall, {cpu / 3600:.2f} CPU hours, "
             f"{cpu / wall if wall else 0:.1f} of {profile.get('budget')} cores busy on average"]
    if critical['path']:
        lines.append(f"Critical path ({_seconds(critical['ideal_seconds'])}): " + ' > '.join(critical['path']))
    lines.append(f"  {'Slowest stages':<26}{'wall':>9}{'cores':>7}{'jobs':>6}{'peak RSS':>11}")
    stages = {row['name']: row for row in profile['stages']}
    for item in analysis['slowest_stages'][:top]:
        row = stages[item['name']]
        rss = row.get('peak_tree_rss_bytes') or row.get('peak_process_rss_bytes')
        mark = '*' if item['critical'] else ' '
        reused = ' reused' if row.get('reused') else ''
        lines.append(f"  {mark}{row['name']:<25}{_seconds(row['wall']):>9}"
                     f"{(str(row.get('cores_avg')) if row.get('cores_avg') is not None else '-'):>7}"
                     f"{jobs_text(row):>6}{_bytes(rss):>11}{reused}")
    for warning in analysis['idle_warnings']:
        lines.append(f"  [idle] {warning['stage']}: {warning['cores_while_idle']} of {warning['jobs']} cores "
                     f"for {_seconds(warning['seconds'])}"
                     + (f" (started with {warning['jobs_start']})" if warning.get('jobs_start') not in (None, warning['jobs']) else ''))
    for warning in analysis.get('host_busy', []):
        lines.append(f"  [host busy] {warning['stage']}: other work used {warning['other_percent']} % of the "
                     f"{warning['cpus']} CPUs (machine {warning['busy_percent']} % busy); its timings are not comparable "
                     "with a quiet host")
    reused = [row['name'] for row in profile['stages'] if row.get('reused')]
    if reused:
        lines.append(f"Reused from {profile.get('reuse_from')}: {', '.join(reused)}")
    lines.append('Profile: ' + str(Path(profile['run']) / PROFILE_NAME) +
                 ' (report: python tools/build_profile.py report RUN)')
    return lines


def summary_record(run):
    """The build summary's profile block, or None when the run has no profile."""
    path = Path(run) / PROFILE_NAME
    if not path.is_file():
        return None
    try:
        profile = load(path)
    except (OSError, ValueError):
        return None
    analysis = profile['analysis']
    return {'path': str(path), 'wall_seconds': profile['wall_seconds'],
            'cpu_seconds': round(sum(row.get('cpu', 0) for row in profile['stages']), 3),
            'critical_path': analysis['critical_path']['path'],
            'critical_path_seconds': analysis['critical_path']['ideal_seconds'],
            'idle_warnings': [w['stage'] for w in analysis['idle_warnings']],
            'host_busy': [w['stage'] for w in analysis.get('host_busy', [])],
            'reused': [row['name'] for row in profile['stages'] if row.get('reused')],
            'overhead': profile.get('overhead')}


def report_lines(profile, comparison=None, top=10):
    analysis = profile['analysis']
    critical = analysis['critical_path']
    lines = [f"Build profile: {profile['run']}",
             f"Status {profile.get('status')}, wall {_seconds(profile['wall_seconds'])}, budget {profile.get('budget')} jobs, "
             f"counters {profile.get('counters')}"]
    overhead = profile.get('overhead') or {}
    if overhead.get('sampler_cpu_seconds') is not None:
        lines.append(f"Profiler overhead: sampler {overhead['sampler_cpu_seconds']:.3f}s CPU over {overhead.get('sampler_samples')} samples "
                     f"({100 * (overhead.get('sampler_share_of_one_core') or 0):.3f} % of one core), wrappers "
                     f"{overhead.get('wrapper_cpu_seconds', 0):.3f}s, output manifests {overhead.get('manifest_seconds', 0):.1f}s")
    lines.append('')
    header = f"{'#':>3} {'stage':<24}{'start':>8}{'wall':>9}{'cpu':>9}{'cores':>7}{'jobs':>6}{'peak RSS':>11}{'read':>11}{'written':>11}  note"
    lines.append(header)
    slack = critical.get('slack', {})
    for row in profile['stages']:
        note = []
        if row['name'] in critical['path']:
            note.append('critical')
        elif row['name'] in slack:
            note.append(f"slack {_seconds(slack[row['name']])}")
        if row.get('reused'):
            note.append('reused')
        if row.get('status') != 'passed':
            note.append(row.get('status', '?'))
        if row.get('io_source') == 'cgroup' and row.get('io_shared_with'):
            note.append('I/O shared')
        load = row.get('host')
        if load:
            note.append(f"host {load['busy_percent']} % busy, other {load['other_percent']} %"
                        + (' HOST BUSY' if load['host_busy'] else ''))
        rss = row.get('peak_tree_rss_bytes') or row.get('peak_process_rss_bytes')
        lines.append(f"{row['number']:>3} {row['name']:<24}{_seconds(row['start']):>8}{_seconds(row['wall']):>9}"
                     f"{_seconds(row.get('cpu')):>9}{(str(row.get('cores_avg')) if row.get('cores_avg') is not None else '-'):>7}"
                     f"{jobs_text(row):>6}{_bytes(rss):>11}{_bytes(row.get('read_bytes')):>11}"
                     f"{_bytes(row.get('write_bytes')):>11}  {', '.join(note)}")
    lines += ['', f"Critical path {_seconds(critical['ideal_seconds'])} (unlimited cores): " + ' > '.join(critical['path']),
              'Waited on: ' + ' > '.join(critical['actual_path'])]
    if analysis['slowest_sections']:
        lines += ['', f"{'slowest sections':<48}{'calls':>6}{'wall':>9}{'cores':>7}"]
        for item in analysis['slowest_sections'][:top]:
            lines.append(f"{(item['stage'] + ': ' + item['name'])[:47]:<48}{item['calls']:>6}{_seconds(item['wall']):>9}"
                         f"{(str(item['cores_avg']) if item['cores_avg'] is not None else '-'):>7}")
    if analysis['idle_warnings']:
        lines += ['', 'Idle-core warnings (stage used < 50 % of its jobs for > 60 s):']
        for warning in analysis['idle_warnings']:
            lines.append(f"  {warning['stage']}: {warning['cores_while_idle']} of {warning['jobs']} cores for "
                         f"{_seconds(warning['seconds'])} ({warning['source']})")
    if analysis.get('host_busy'):
        lines += ['', f"Host busy (other work used more than {int(100 * HOST_BUSY_SHARE)} % of the machine; "
                      "timings are not comparable with a quiet host):"]
        for warning in analysis['host_busy']:
            lines.append(f"  {warning['stage']}: other {warning['other_percent']} %, machine {warning['busy_percent']} % "
                         f"of {warning['cpus']} CPUs")
    if analysis.get('instrumentation_missing'):
        lines += ['', 'Section targets not found (renamed?): ' + ', '.join(analysis['instrumentation_missing'])]
    if analysis['suggestions']:
        lines += ['', 'Suggestions:'] + [f'  - {text}' for text in analysis['suggestions']]
    if comparison:
        lines += [''] + compare_lines(comparison)
    return lines


def compare_lines(comparison):
    """The comparison table of `report --compare` and `compare`."""
    lines = [f"Compared with {comparison['old_run']}: wall {comparison['wall_delta']:+.1f}s",
             f"{'stage':<26}{'old':>9}{'new':>9}{'delta':>10}{'%':>8}  status"]
    for row in comparison['stages']:
        delta = f"{row['delta']:+.1f}s" if row.get('delta') is not None else '-'
        percent = f"{row['percent']:+.1f}" if row.get('percent') is not None else '-'
        status = row['status'].upper() if row['status'] == 'slower' else row['status']
        if row.get('same_fingerprint') and row['status'] not in ('reused',):
            status += ' (same fingerprint: reusable)'
        if row.get('host_new') == 'busy' or row.get('host_old') == 'busy':
            status += f" [host {row.get('host_old')} -> {row.get('host_new')}]"
        lines.append(f"{row['name']:<26}{_seconds(row.get('old')):>9}{_seconds(row.get('new')):>9}{delta:>10}{percent:>8}  {status}")
    if comparison['regressions']:
        lines.append('REGRESSION: slower stages: ' + ', '.join(comparison['regressions']))
    busy = comparison.get('busy_host') or {}
    if busy.get('new') or busy.get('old'):
        lines.append('WARNING: busy host in ' + ' and '.join(n for n in ('new', 'old') if busy.get(n))
                     + ' run; wall times include other work on the machine')
    if comparison.get('host_mismatch'):
        lines.append('WARNING: busy host in one run and quiet in the other, not comparable: '
                     + ', '.join(comparison['host_mismatch']))
    return lines


def html_page(profile, comparison=None):
    """Self-contained chart page: stage Gantt and CPU timeline (Chart.js from cdnjs)."""
    analysis = profile['analysis']
    critical = set(analysis['critical_path']['path'])
    stages = profile['stages']
    gantt = {'labels': [row['name'] for row in stages],
             'bars': [[row['start'], row['end']] for row in stages],
             'colors': ['#d03b3b' if row['name'] in critical else '#1baf7a' if row.get('reused') else '#2a78d6'
                        for row in stages],
             'cores': [row.get('cores_avg') for row in stages],
             'jobs': [row.get('jobs_max') or row.get('jobs') for row in stages]}
    timeline = profile.get('timeline') or {}
    data = {'gantt': gantt, 't': timeline.get('t', []), 'cores': timeline.get('cores', []),
            'cgroup': timeline.get('cgroup_cores'), 'budget': profile.get('budget'),
            'memory': timeline.get('memory_bytes')}
    rows = '\n'.join('<tr><td>' + '</td><td>'.join(html_escape.escape(str(cell)) for cell in (
        row['number'], row['name'], _seconds(row['start']), _seconds(row['wall']), _seconds(row.get('cpu')),
        row.get('cores_avg', '-'), jobs_text(row),
        _bytes(row.get('peak_tree_rss_bytes') or row.get('peak_process_rss_bytes')),
        ('critical ' if row['name'] in critical else '') + ('reused' if row.get('reused') else ''))) + '</td></tr>'
        for row in stages)
    tips = ''.join(f'<li>{html_escape.escape(text)}</li>' for text in analysis['suggestions']) or '<li>None.</li>'
    compare_rows = ''
    if comparison:
        compare_rows = ('<h2>Compared with ' + html_escape.escape(comparison['old_run']) + '</h2><table><tr><th>stage</th>'
                        '<th>old</th><th>new</th><th>delta</th><th>status</th></tr>' + ''.join(
                            f"<tr class=\"{'bad' if r['status'] == 'slower' else ''}\"><td>{html_escape.escape(r['name'])}</td>"
                            f"<td>{_seconds(r.get('old'))}</td><td>{_seconds(r.get('new'))}</td>"
                            f"<td>{'-' if r.get('delta') is None else format(r['delta'], '+.1f') + 's'}</td>"
                            f"<td>{html_escape.escape(r['status'])}</td></tr>" for r in comparison['stages']) + '</table>')
    title = 'Build profile'
    height = max(240, 22 * len(stages) + 60)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#ffffff; --fg:#1d1d1f; --muted:#666; --line:#e3e3e3; --bad:#fde8e8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16171a; --fg:#ececec; --muted:#a0a0a0; --line:#33353a; --bad:#4a1f1f; }} }}
body {{ background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, sans-serif; margin:0 auto; padding:16px; max-width:1200px; }}
h1 {{ font-size:20px; margin:0 0 4px; }} h2 {{ font-size:16px; margin:24px 0 8px; }}
.muted {{ color:var(--muted); }} table {{ border-collapse:collapse; width:100%; font-size:13px; }}
td, th {{ border-bottom:1px solid var(--line); padding:3px 6px; text-align:left; white-space:nowrap; }}
tr.bad {{ background:var(--bad); }} .wrap {{ overflow-x:auto; }} canvas {{ max-width:100%; }}
</style></head><body>
<h1>{title}</h1>
<p class="muted">{html_escape.escape(profile['run'])} | {html_escape.escape(str(profile.get('status')))} |
wall {_seconds(profile['wall_seconds'])} | budget {profile.get('budget')} jobs |
critical path {_seconds(analysis['critical_path']['ideal_seconds'])}: {html_escape.escape(' > '.join(analysis['critical_path']['path']))}</p>
<h2>Stages (red: critical path, green: reused)</h2>
<div style="height:{height}px"><canvas id="gantt"></canvas></div>
<h2>CPU in use (cores)</h2>
<div style="height:280px"><canvas id="cpu"></canvas></div>
<h2>Suggestions</h2><ul>{tips}</ul>
<h2>Stage table</h2><div class="wrap"><table><tr><th>#</th><th>stage</th><th>start</th><th>wall</th><th>cpu</th>
<th>cores</th><th>jobs</th><th>peak RSS</th><th>note</th></tr>{rows}</table></div>
{compare_rows}
<script src="{CHART_JS}"></script>
<script>
const data = {json.dumps(data)};
if (window.Chart) {{
  const grid = getComputedStyle(document.documentElement).getPropertyValue('--line');
  const text = getComputedStyle(document.documentElement).getPropertyValue('--fg');
  Chart.defaults.color = text; Chart.defaults.borderColor = grid;
  new Chart(document.getElementById('gantt'), {{type: 'bar',
    data: {{labels: data.gantt.labels, datasets: [{{data: data.gantt.bars, backgroundColor: data.gantt.colors, borderSkipped: false}}]}},
    options: {{indexAxis: 'y', maintainAspectRatio: false, plugins: {{legend: {{display: false}},
      tooltip: {{callbacks: {{label: c => {{ const b = data.gantt.bars[c.dataIndex];
        return (b[1]-b[0]).toFixed(1) + ' s, ' + (data.gantt.cores[c.dataIndex] ?? '-') + ' of ' + data.gantt.jobs[c.dataIndex] + ' cores'; }} }} }} }},
      scales: {{x: {{title: {{display: true, text: 'seconds since build start'}}}}}}}}}});
  const sets = [{{label: 'build stages', data: data.cores, borderColor: '#2a78d6', pointRadius: 0, borderWidth: 1.5}},
                {{label: 'job budget', data: data.t.map(() => data.budget), borderColor: '#d03b3b', borderDash: [6, 4], pointRadius: 0, borderWidth: 1}}];
  if (data.cgroup) sets.push({{label: 'whole container', data: data.cgroup, borderColor: '#eda100', pointRadius: 0, borderWidth: 1}});
  new Chart(document.getElementById('cpu'), {{type: 'line', data: {{labels: data.t, datasets: sets}},
    options: {{maintainAspectRatio: false, animation: false, scales: {{x: {{type: 'linear', title: {{display: true, text: 'seconds'}}}},
      y: {{beginAtZero: true, title: {{display: true, text: 'cores'}}}}}}}}}});
}}
</script></body></html>
"""


def main(argv=None, prog=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['_stage']:
        return stage_main(argv[1:])
    parser = argparse.ArgumentParser(prog=prog, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    report = sub.add_parser('report', help='Print the profile table of a build run (or a sections .jsonl file)')
    report.add_argument('run', type=Path, help='Build run folder, its build-profile.json, or a sections .jsonl file')
    report.add_argument('--compare', type=Path, metavar='OLDER_RUN', help='Diff against an older run; slower stages are flagged')
    report.add_argument('--html', type=Path, metavar='OUT', help='Also write a self-contained chart page')
    report.add_argument('--top', type=int, default=10)
    report.add_argument('--fail-on-regression', action='store_true', help='Exit 3 when --compare finds a slower stage')
    report.add_argument('--json', action='store_true', help='Print the analysis (and comparison) as JSON')
    versus = sub.add_parser('compare', help='Per-stage wall time of a run against an older run; slower stages are flagged')
    versus.add_argument('run', type=Path, help='Newer build run folder or its build-profile.json')
    versus.add_argument('older', type=Path, help='Older build run folder or its build-profile.json')
    versus.add_argument('--fail-on-regression', action='store_true', help='Exit 3 when a stage is slower')
    versus.add_argument('--json', action='store_true', help='Print the comparison as JSON')
    tune = sub.add_parser('optimize', help='Idle-core stages, single-core tails, serial critical stages and slot '
                                           'waits of one or more runs, with suggestions')
    tune.add_argument('runs', type=Path, nargs='+', metavar='run', help='Build run folders or build-profile.json files')
    tune.add_argument('--share', type=float, default=IDLE_SHARE, help='Idle below this share of the jobs (default 0.5)')
    tune.add_argument('--seconds', type=float, default=IDLE_SECONDS, help='... for longer than this (default 60)')
    tune.add_argument('--json', action='store_true', help='Print the items as JSON')
    args = parser.parse_args(argv)
    try:
        if args.action == 'compare':
            comparison = compare(load(args.run), load(args.older))
            comparison['old_run'] = str(args.older)
            print(json.dumps(comparison, indent=2) if args.json else '\n'.join(compare_lines(comparison)))
            return 3 if args.fail_on_regression and comparison['regressions'] else 0
        if args.action == 'optimize':
            profiles = [load(path) for path in args.runs]
            rows = optimize_runs(profiles, args.share, args.seconds)
            names = [Path(str(profile.get('run') or path)).name for profile, path in zip(profiles, args.runs)]
            if args.json:
                print(json.dumps({'runs': names, 'items': rows}, indent=2))
            else:
                print('\n'.join(optimize_lines(rows, names)))
            return 0
        if args.run.suffix == '.jsonl':
            rows = read_sections(args.run)
            print(f"{'section':<48}{'calls':>6}{'wall':>9}{'cores':>7}")
            for row in sorted(rows, key=lambda r: -r['wall']):
                print(f"{row['name'][:47]:<48}{row['calls']:>6}{_seconds(row['wall']):>9}"
                      f"{(str(row['cores_avg']) if row['cores_avg'] is not None else '-'):>7}")
            return 0
        profile = load(args.run)
        comparison = None
        if args.compare:
            comparison = compare(profile, load(args.compare))
            comparison['old_run'] = str(args.compare)
        if args.json:
            print(json.dumps({'analysis': profile['analysis'], 'comparison': comparison}, indent=2))
        else:
            print('\n'.join(report_lines(profile, comparison, args.top)))
        if args.html:
            args.html.write_text(html_page(profile, comparison), encoding='utf-8', newline='\n')
            print(f'Chart page: {args.html}')
        if args.fail_on_regression and comparison and comparison['regressions']:
            return 3
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
