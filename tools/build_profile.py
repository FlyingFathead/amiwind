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
    python tools/build_profile.py timeline RUN [RUN ...] --png OUT.png [--samples JSONL] [--gates JSONL]

(the same as `python tools/build.py profile report|compare|optimize|timeline ...`).
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
import math
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
    """The build's memory in use (bytes): the container's memory.current, else the machine's MemTotal - MemAvailable
    (a build on a plain machine recorded no memory at all: TOOLKIT-MONITOR-NO-MEMORY-55), else None."""
    try:
        return int(Path('/sys/fs/cgroup/memory.current').read_text())
    except (OSError, ValueError):
        pass
    try:
        from resource_plan import host_memory
        total, free = host_memory()
        return total - free if total is not None and free is not None else None
    except Exception:  # noqa: BLE001 - the profile must never fail a build
        return None


def memory_limit_bytes():
    """The ceiling of the memory curve: the container's limit, else the machine's MemTotal, else None."""
    try:
        from resource_plan import build_memory
        return build_memory()[0]
    except Exception:  # noqa: BLE001
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


# --------------------------------------------------------------------------
# Phases: named, always-timed parts of a stage that say when they start and end
# (BUILD-PROFILE-SECTIONS-MISSING-36). This module is left out of every stage key
# (build_cache.INSTRUMENTATION_MODULES): changing the wording here never rebuilds a stage.

LOG_LEVEL_ENV = 'AMIWIND_LOG_LEVEL'      # quiet | normal | verbose (build.py --log-level, --quiet)
LOG_LEVELS = ('quiet', 'normal', 'verbose')
NOW_SUFFIX = '.now'                      # the stage's current phase, for the builder's heartbeat


def log_level():
    value = os.environ.get(LOG_LEVEL_ENV, 'normal').strip().lower()
    return value if value in LOG_LEVELS else 'normal'


BUILD_EPOCH_ENV = 'AMIWIND_BUILD_EPOCH'   # override of the build's start (epoch seconds) for the prefix
EPOCH_FILE = 'build-epoch.txt'            # RUN/profile/build-epoch.txt: written by the builder's profiling session
_PROCESS_START = time.time()
_EPOCH = []


def build_epoch():
    """The build's start: AMIWIND_BUILD_EPOCH, else RUN/profile/build-epoch.txt (found from the stage's sections
    file), else this process's start."""
    value = os.environ.get(BUILD_EPOCH_ENV)
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    if not _EPOCH:
        found = _PROCESS_START
        path = _section_file()
        if path:
            try:
                found = float((Path(path).parent.parent / EPOCH_FILE).read_text(encoding='utf-8').strip())
            except (OSError, ValueError):
                pass
        _EPOCH.append(found)
    return _EPOCH[0]


def stamp(now=None):
    """'[+1h02m] ' - the time since the build started (build_epoch), else since this
    process started: the prefix of every phase line and heartbeat, so a log tells when each step ran."""
    origin = build_epoch()
    return '[+%s] ' % _seconds(max(0.0, (time.time() if now is None else now) - origin))


def took_text(wall, cpu=None):
    """'took 41m12s, 21.4 cores' (cores = CPU of the process and everything under it / wall)."""
    text = 'took ' + _seconds(wall)
    if cpu is not None and wall and wall > 0:
        text += f', {cpu / wall:.1f} cores'
    return text


def counter_text(done, total=None, unit=None):
    """'112/273 frames': the counter of the builder's progress lines (tools/progress_line.py, one form for all)."""
    if total is None:
        return str(done) + (' ' + unit if unit else '')
    from progress_line import counter_text as one_form
    return one_form((done, total, unit) if unit else (done, total))


def progress(text, stream=None):
    """A per-unit progress line ('[112/273 frames] CHIM stats: x-03/y-02'): printed unless the log level is
    quiet. Start/end lines, heartbeats, warnings and errors are never quieted."""
    if log_level() != 'quiet':
        print(text, file=stream, flush=True)


def _tree_cpu():
    """CPU seconds of this process and every process under it (live children included), else own + reaped."""
    if linux_proc():
        try:
            return tree_usage(os.getpid())[0]
        except Exception:  # noqa: BLE001
            pass
    times = os.times()
    return times.user + times.system + times.children_user + times.children_system


def _write_now(state):
    path = _section_file()
    if not path:
        return
    try:
        temporary = path + NOW_SUFFIX + '.tmp'
        with open(temporary, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(state, sort_keys=True))
        os.replace(temporary, path + NOW_SUFFIX)
    except OSError:
        pass  # Profiling must never fail a build.


def read_now(sections_path):
    """The current phase of a stage ({name, started_at, done, total, unit}) or None."""
    try:
        return json.loads(Path(str(sections_path) + NOW_SUFFIX).read_text(encoding='utf-8')) or None
    except (OSError, ValueError):
        return None


_phases = []    # open phases of this process, innermost last


class phase:
    """A named part of a stage, always timed and never silent:

        with build_profile.phase('CHIM stats', detail='273 frames', total=273, unit='frames') as timer:
            for ...:
                timer.step(label=frame)            # counter for the heartbeat (+ a progress line with line=True)
            timer.done('CHIM stats: 2768 models')  # the summary; '- took 41m12s, 21.4 cores' is appended

    prints 'NAME: started[, detail]' on entry and the summary (or 'NAME: done' / 'NAME: FAILED (Error)') with
    its time and cores on exit, records the phase in the stage's sections file (wall, CPU of the whole process
    tree, cores, epoch start and end; `build_profile.py report` and the Build Timeline read it) and keeps the
    stage's current phase and counter where the builder's heartbeat reads it. Output files are never touched."""

    def __init__(self, name, detail=None, total=None, unit=None, stream=None):
        self.name, self.detail, self.total, self.unit = str(name), detail, total, unit
        self.stream = stream
        self.count, self.label, self.summary = 0, None, None
        self._written = 0.0

    def _state(self):
        return {'name': self.name, 'started_at': round(self.at, 3), 'done': self.count, 'total': self.total,
                'unit': self.unit, 'label': self.label, 'pid': os.getpid()}

    def __enter__(self):
        self.start = time.monotonic()
        self.at = time.time()
        self.cpu0 = _tree_cpu()
        self.depth = len(_phases)
        _phases.append(self)
        print(stamp() + f'{self.name}: started' + (f', {self.detail}' if self.detail else ''), file=self.stream,
              flush=True)
        _write_section({'name': self.name, 'event': 'start', 'phase': True, 'pid': os.getpid(), 'depth': self.depth,
                        'start': round(self.start, 4), 'at': round(self.at, 3), 'detail': self.detail})
        _write_now(self._state())
        return self

    def step(self, count=None, label=None, line=False):
        """Advance the counter (by one, or to COUNT); line=True also prints a progress line."""
        self.count = self.count + 1 if count is None else count
        self.label = label
        if line:
            from progress_line import line as progress_text
            counter = (self.count, self.total, self.unit) if self.total is not None else (self.count, '?', self.unit)
            progress(progress_text(self.name, label, None, counter), self.stream)
        now = time.monotonic()
        if now - self._written >= 1.0 or (self.total is not None and self.count >= self.total):
            self._written = now
            _write_now(self._state())

    def done(self, summary):
        self.summary = str(summary)

    def elapsed(self):
        return time.monotonic() - self.start

    def __exit__(self, kind, value, traceback):
        wall = time.monotonic() - self.start
        cpu = max(0.0, _tree_cpu() - self.cpu0)
        if kind is not None and not (kind is SystemExit and not getattr(value, 'code', 1)):
            text = f'{self.name}: FAILED ({kind.__name__})'
        else:
            text = self.summary or f'{self.name}: done'
        print(stamp() + f'{text} - {took_text(wall, cpu)}', file=self.stream, flush=True)
        record = {'name': self.name, 'phase': True, 'pid': os.getpid(), 'depth': self.depth, 'detail': self.detail,
                  'start': round(self.start, 4), 'at': round(self.at, 3), 'end_at': round(time.time(), 3),
                  'wall': round(wall, 4), 'cpu_self': round(cpu, 3), 'cpu_children': 0.0,
                  'cores': round(cpu / wall, 2) if wall > 0 else None}
        if self.total is not None:
            record.update(done=self.count, total=self.total)
        if kind is not None:
            record['error'] = kind.__name__
        _write_section(record)
        if _phases and _phases[-1] is self:
            _phases.pop()
        elif self in _phases:
            # a phase run in a thread beside another (the CHIM stats beside the zone walk) can end first: it leaves
            # the stack wherever it is, so the current phase stays the one still running
            _phases.remove(self)
        if _phases:
            _write_now(_phases[-1]._state())
        else:
            path = _section_file()
            if path:
                try:
                    os.remove(path + NOW_SUFFIX)
                except OSError:
                    pass
        return False

    def __call__(self, function):
        name, detail = self.name, self.detail

        @functools.wraps(function)
        def timed(*args, **kwargs):
            with phase(name, detail):
                return function(*args, **kwargs)
        timed.__amiwind_section__ = name
        return timed


# Functions instrument() times as phases (start/end lines with time and cores) instead of quiet sections:
# the long, once-per-stage steps. (table stage, target) -> label; every target is also in INSTRUMENT.
PHASES = {
    ('build_aga image', 'install_world_scenery'): 'Image: world scenery',
    ('build_aga image', 'install_world_terrain:install'): 'Image: world terrain',
    ('build_aga image', 'install_world_flora:install'): 'Image: world flora',
    ('build_aga image', 'exterior_sky_build:configure_staged_maps'): 'Image: exterior sky',
    ('build_aga image', 'hidden_surface_build:cull_staged_maps'): 'Image: hidden surface cull',
    ('build_aga image', 'optimize_world_maps:optimize_maps'): 'Image: world map optimizer',
    ('build_aga image', 'optimize_world_maps:verify_optimized_maps'): 'Image: optimizer check',
    ('build_aga image', 'actor_grounding:annotate'): 'Image: actor annotate',
    ('build_aga image', 'actor_grounding:bake_ground'): 'Image: actor ground bake',
    ('build_aga image', 'room_actor_bake:bake_room_ground'): 'Image: CHIM room actor bake',
    ('build_aga image', 'audit_world_map_heap_with_receipt'): 'Image: world map heap audit',
    ('build_aga image', 'world_volumes:pack'): 'Image: pack volumes',
    ('build_aga image', 'finalize_image'): 'Image: finalize',
    ('build_aga image', 'check_image'): 'Image: check',
    ('build_aga image', 'payload_preflight'): 'Image: payload preflight',
    ('build_aga image', 'prepare_torch:prepare'): 'Image: torch',
    ('build_aga image', 'prepare_magic:prepare'): 'Image: magic effects',
    ('build_aga image', 'prepare_combat:prepare'): 'Image: combat data',
    ('build_aga image', 'prepare_player_view:prepare'): 'Image: player view',
    ('build_aga image', 'prepare_seyda_regions:convert_builder_scene'): 'Image: Seyda Neen legacy region maps',
    ('build_aga image', 'install_town_flora:install'): 'Image: town flora',
    ('build_aga image', 'prepare_shared_sky_assets:prepare_staged_sky'): 'Image: sky assets',
    ('build_aga image', 'prepare_guard_torches:prepare'): 'Image: guard torches',
    ('build_aga image', 'hand_metadata:stamp_staged_hands'): 'Image: hand metadata',
    ('build_aga image', 'cell_numbers:stamp_staged_cells'): 'Image: interior cell numbers',
    ('build_aga image', 'harvest_build:image_step'): 'Image: harvest',
    ('build_aga image', 'check_actor_ground:require'): 'Image: actor ground check',
    ('build_aga image', 'entity_tracker:build_gate'): 'Image: entity tracker',
    ('build_aga image', 'world_progress:build_step'): 'Image: world progress',
    ('build_aga image', 'stage_direct_start'): 'Image: direct start',
    ('build_aga image', 'night_lighting:stage'): 'Image: night lighting',
    ('build_aga image', 'chim.heap:require_frame_map_heap'): 'Image: CHIM frame-map heap',
    ('build_aga image', 'optimize_world_maps:rebind_chim_maps'): 'Image: optimizer rebind',
    ('build_aga image', 'map_engine_limits:check_maps'): 'Image: engine map limits',
    ('build_aga image', 'stair_walk:require'): 'Image: stair walk',
    ('build_aga image', 'write_content_fingerprint'): 'Image: content fingerprint',
    ('build_aga image', 'prepare_media_assets:stage_catalogue'): 'Image: media catalogue',
    ('build_aga image', 'add_chim_volume'): 'Image: CHIM world volume',
    ('build_aga image', 'world_volumes:write_boot_partition'): 'Image: boot partition',
    ('build_aga image', 'world_volumes:assemble_drives'): 'Image: drives',
    ('build_aga image', 'world_volumes:write_layout'): 'Image: partitions (all at once)',
    ('build_aga image', 'arrival_spot:require'): 'Image: arrival check',
    ('build_aga image', 'chim_frame_maps'): 'Image: CHIM frame maps',
    ('build_aga image', 'chim.frame_map:remove_legacy_areas'): 'Image: remove legacy areas',
    # the steps between the player view and finalize, and the untimed stretches inside finalize
    # (BUILD-IMAGE-FINALIZE-UNDERUSED-48; the world UI times itself: prepare_world_ui.prepare_image)
    ('build_aga image', 'prepare_inventory:prepare'): 'Image: inventory',
    ('build_aga image', 'prepare_logo:prepare_menu_logo'): 'Image: menu logo',
    ('build_aga image', 'prepare_logo:prepare_logo'): 'Image: logo stream',
    ('build_aga image', 'chim_rooms:install'): 'Image: CHIM town rooms install',
    ('build_aga image', 'chim_town:install'): 'Image: CHIM town install',
    # the room batches' 13,141 files hashed and copied (BUILD-IMAGE-UNDERUSED-32: 5 to 14 s, untimed)
    ('build_aga image', 'room_batches:install'): 'Image: room batches install',
    ('build_aga image', 'harvest_build:clear_baked'): 'Image: harvest baked removal',
    ('build_aga image', 'compile_quakec'): 'Image: QuakeC',
    ('build_aga image', 'actor_library:install'): 'Image: actor library',
    ('build_aga image', 'chim.actors:write_table'): 'Image: actor table',
    ('build_aga image', 'harvest_build:require_chim_coverage'): 'Image: harvest CHIM coverage',
    ('build_aga image', 'world_payload:prune'): 'Image: world payload prune',
    ('build_aga image', 'audit_gallery_budgets:world_allowances'): 'Image: world model allowances',
    ('build_aga image', 'payload_share:share_payload'): 'Image: payload sharing',
    ('build_aga image', 'compact_layout'): 'Image: layout plan and partitions',
    ('world-terrain', 'plan'): 'World terrain: plan',
    ('world-terrain', 'terrain_wad'): 'World terrain: texture WAD',
    ('world-terrain', 'region_directory'): 'World terrain: region directory',
    ('actor-contact', 'convert_builder_scene'): 'Actor contact: convert scene',
    ('actor-contact', 'annotate'): 'Actor contact: annotate',
    ('actor-contact', 'bake_ground'): 'Actor contact: bake ground',
    ('actor-contact', 'require'): 'Actor contact: check',
}


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
        'actor_grounding:annotate', 'actor_grounding:bake_ground', 'room_actor_bake:bake_room_ground',
        'prepare_world_ui:prepare',
        'build_gallery:stage_required', 'exterior_sky_build:configure_staged_maps',
        'hidden_surface_build:cull_staged_maps', 'optimize_world_maps:optimize_maps',
        'optimize_world_maps:verify_optimized_maps', 'check_actor_ground:require',
        'check_world_map_heap:audit_world_maps', 'entity_tracker:build_gate', 'night_lighting:stage',
        'world_volumes:pack', 'world_volumes:verify_combined',
        # every image sub-phase between the passes is a timed phase (BUILD-SILENT-PHASES-36)
        'payload_preflight', 'prepare_torch:prepare', 'prepare_magic:prepare', 'prepare_combat:prepare', 'prepare_player_view:prepare',
        'prepare_shared_sky_assets:prepare_staged_sky', 'prepare_guard_torches:prepare',
        'hand_metadata:stamp_staged_hands', 'cell_numbers:stamp_staged_cells', 'harvest_build:image_step',
        'world_progress:build_step', 'stage_direct_start', 'chim.heap:require_frame_map_heap',
        'optimize_world_maps:rebind_chim_maps', 'map_engine_limits:check_maps', 'stair_walk:require',
        'prepare_media_assets:stage_catalogue', 'add_chim_volume', 'world_volumes:write_boot_partition',
        'world_volumes:assemble_drives', 'world_volumes:write_layout',
        # from the build-timeline line: finalize_image between the optimizer and the final checks
        'arrival_spot:require', 'chim_frame_maps', 'chim.frame_map:remove_legacy_areas',
        # BUILD-IMAGE-FINALIZE-UNDERUSED-48: the untimed steps after the player view and inside finalize
        'prepare_inventory:prepare', 'prepare_logo:prepare_menu_logo', 'prepare_logo:prepare_logo',
        'chim_rooms:install', 'chim_town:install', 'room_batches:install', 'harvest_build:clear_baked',
        'compile_quakec',
        'actor_library:install', 'chim.actors:write_table',
        'harvest_build:require_chim_coverage', 'world_payload:prune', 'audit_gallery_budgets:world_allowances',
        'payload_share:share_payload', 'compact_layout',
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
        if (stage, target) in PHASES:
            timed = phase(PHASES[(stage, target)])(original)
        else:
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
        if record.get('event') == 'start':
            continue          # a phase's start line (the heartbeat and a running stage's chart read those)
        row = rows.setdefault(record['name'], {'name': record['name'], 'calls': 0, 'wall': 0.0, 'max_wall': 0.0,
                                               'cpu_self': 0.0, 'cpu_children': 0.0, 'min_depth': 99,
                                               'first_start': record.get('start', 0)})
        if record.get('phase'):
            row['phase'] = True
            if record.get('at') is not None:
                row['first_at'] = min(row.get('first_at', record['at']), record['at'])
        row['calls'] += 1
        row['wall'] += record.get('wall', 0)
        row['max_wall'] = max(row['max_wall'], record.get('wall', 0))
        row['cpu_self'] += record.get('cpu_self', 0)
        row['cpu_children'] += record.get('cpu_children', 0)
        row['min_depth'] = min(row['min_depth'], record.get('depth', 0))
        row['first_start'] = min(row['first_start'], record.get('start', 0))
        row['last_end'] = max(row.get('last_end', 0.0), record.get('start', 0) + record.get('wall', 0))
        if record.get('detail') and not row.get('detail'):
            row['detail'] = record['detail']
        if 'items' in record:
            row['items'] = row.get('items', 0) + record['items']
        if record.get('phase') and record.get('total') is not None:
            row['units'] = row.get('units', 0) + record['total']   # a phase's unit total (the perf guard reads it)
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


def _signal_child(child, sig):
    """Send SIG to the stage (None: kill it); a stage that already ended is no error."""
    try:
        child.kill() if sig is None else child.send_signal(sig)
    except OSError:
        pass


# Seconds a stage gets to end by itself after Ctrl-C before the wrapper hands the interrupt on to it.
STAGE_INTERRUPT_GRACE = 5


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
    interrupts = 0
    if child is not None:
        while True:
            try:
                code = child.wait()
                break
            except KeyboardInterrupt:
                # Ctrl-C cancels the stage, never only this wrapper (BUILD-STAGE-INTERRUPT-ABSORBED-36): a stage
                # in the same terminal group got the interrupt too and ends on its own; one that did not (another
                # group, or the interrupt was sent to this wrapper alone) gets it now; a second one stops it hard.
                # How it ends is recorded below, then the wrapper ends by the interrupt whatever the stage returned.
                interrupts += 1
                if interrupts == 1:
                    try:
                        code = child.wait(timeout=STAGE_INTERRUPT_GRACE)
                        break
                    except subprocess.TimeoutExpired:
                        _signal_child(child, signal.SIGINT)
                        continue
                    except KeyboardInterrupt:
                        interrupts += 1
                _signal_child(child, None)
    if interrupts:
        record['interrupted'] = True
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
    if interrupts and not (code is not None and code < 0):
        # The stage handled the interrupt (and may even have returned 0): the caller still sees a cancel.
        code = -signal.SIGINT if os.name == 'posix' else 130
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
            # The tree's CPU never really goes down: a dip is a child that ended between the walk's reads (or
            # before its parent reaped it). Keeping the higher baseline stops the reaped child's CPU, already
            # sampled while it ran, from being counted a second time when it shows up in the parent's cutime.
            self.last[stage] = (now, cpu if previous is None else max(cpu, previous[1]))
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
                'memory_limit_bytes': memory_limit_bytes(),
                'host_cpus': self.cpus,
                'host_busy': self.host if any(v is not None for v in self.host) else None,
                'stages': {name: [[row[0], row[1]] for row in rows] for name, rows in self.stages.items()}}


# --------------------------------------------------------------------------
# Session (the builder's hooks; tools/build.py and tools/build_parallel.py)

# --------------------------------------------------------------------------
# Heartbeat (in the builder): no stage runs silently

HEARTBEAT_ENV = 'AMIWIND_HEARTBEAT_SECONDS'
DEFAULT_HEARTBEAT = 30.0


def heartbeat_seconds():
    """Seconds of silence before a heartbeat line; 0 = off (AMIWIND_HEARTBEAT_SECONDS)."""
    value = os.environ.get(HEARTBEAT_ENV, '').strip().lower()
    if value in ('0', 'off', 'no', 'false'):
        return 0.0
    try:
        return max(0.05, float(value)) if value else DEFAULT_HEARTBEAT
    except ValueError:
        return DEFAULT_HEARTBEAT


class Heartbeat(threading.Thread):
    """Watches every running stage's log from the builder process. When a stage has written nothing for the
    heartbeat time, prints one line naming the stage, its current phase and counter (from the stage's own
    phase timer, build_profile.phase), how long that phase (else the stage) has run and the cores the stage's
    process tree uses (the profiler's sampler), and again after every further heartbeat time of silence. It
    covers a stage whose child writes nothing at all; the stage's own output is never touched."""

    def __init__(self, session, silence, stream=None):
        super().__init__(name='build-heartbeat', daemon=True)
        self.session, self.silence, self.stream = session, silence, stream
        self.tick = max(0.02, min(5.0, silence / 4))
        self.stop_event = threading.Event()
        self.seen = {}        # stage -> (log size, time it last changed, time of the last heartbeat)
        self.state = {}       # stage -> the last heartbeat (for build-progress.json)
        self.lines = 0

    def run(self):
        while not self.stop_event.wait(self.tick):
            try:
                self.check()
            except Exception:  # noqa: BLE001 - a heartbeat must never stop a build
                pass

    def cores(self, name):
        sampler = self.session.sampler
        if sampler is None:
            return None
        with sampler.lock:
            rows = list(sampler.stages.get(name) or ())
        return rows[-1][1] if rows else None

    def check(self, now=None):
        now = time.monotonic() if now is None else now
        running = {name: stage for name, stage in list(self.session.stages.items()) if stage['status'] == 'running'}
        for name in list(self.seen):
            if name not in running:
                self.seen.pop(name)
                self.state.pop(name, None)
        for name, stage in running.items():
            log = self.session.run / 'logs' / f"{stage['number']:02}-{name}.log"
            try:
                size = log.stat().st_size
            except OSError:
                size = -1
            last_size, changed, beat = self.seen.get(name, (None, now, None))
            if size != last_size:
                changed, beat = now, None
                self.state.pop(name, None)
            self.seen[name] = (size, changed, beat)
            silent = now - changed
            if silent < self.silence or (beat is not None and now - beat < self.silence):
                continue
            text = self.line(name, stage, silent)
            print(text, file=self.stream, flush=True)
            self.lines += 1
            self.seen[name] = (size, changed, now)
            self.state[name] = {'text': text, 'silent_seconds': round(silent, 1), 'at': round(time.time(), 3)}

    def line(self, name, stage, silent):
        current = read_now(stage['sections'])
        cores = self.cores(name)
        if current:
            where = current.get('name') or name
            if current.get('done') or current.get('total'):
                where = f"[{counter_text(current.get('done') or 0, current.get('total'), current.get('unit'))}] {where}"
            if current.get('label'):
                where += f": {current['label']}"
            elapsed = time.time() - float(current.get('started_at') or time.time())
        else:
            where = '(no phase recorded)'
            elapsed = time.monotonic() - self.session.start - stage['start']
        return (stamp() + f"[heartbeat] {name}: {where}: still working, {_seconds(elapsed)}"
                + (f", {cores:.1f} cores" if cores is not None else '') + f" (no output for {_seconds(silent)})")

    def stop(self):
        self.stop_event.set()
        if self.is_alive():
            self.join(timeout=5)


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
        try:   # the build's start for the stages' elapsed-time prefix (build_profile.stamp)
            (self.folder / EPOCH_FILE).write_text('%.3f' % time.time(), encoding='utf-8', newline=chr(10))
        except OSError:
            pass
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
                                                 self.sampler, self.start,
                                                 commands={name: command for name, command in steps})
        except Exception as exc:  # noqa: BLE001 - progress must never fail a build
            print(f'[warning] Live build progress disabled: {exc}', flush=True)
            self.progress = None
        silence = heartbeat_seconds()
        self.heartbeat = Heartbeat(self, silence) if silence else None
        if self.heartbeat is not None:
            self.heartbeat.start()
        if self.progress is not None:
            self.progress.heartbeat = self.heartbeat
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
        if self.heartbeat is not None:
            self.heartbeat.stop()
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
                # The sections schema the Build Timeline and the Toolkit Monitor read: name, start, end
                # (seconds after the first stage started), cpu (seconds), optional detail; plus calls, wall,
                # cores_avg, phase.
                item['start'] = round(item.pop('first_start') - self.start, 3)
                item['end'] = round(item.pop('last_end') - self.start, 3)
                item['cpu'] = round(item['cpu_self'] + item['cpu_children'], 3)
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
    """The builder's profiling session (a no-op session when profiling is off), with the disk watch of an image build
    (tools/disk_need.py: each stage's last figure checked before it starts, the build's figure written when it passes;
    BUILD-DISK-NEED-UNKNOWN-52), profiled or not."""
    import disk_need
    if not enabled(metadata):
        return disk_need.watched(NullSession(), run, metadata)
    try:
        session = Session(run, steps, metadata, dependencies)
    except Exception as exc:  # noqa: BLE001
        print(f'[warning] Build profiling disabled: {exc}', flush=True)
        session = NullSession()
    return disk_need.watched(session, run, metadata)


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


UNDERUSE_SHARE = 0.5      # a stage or phase under half of the workers its stage held ...
UNDERUSE_SECONDS = 30.0   # ... for longer than this: a fix item (BUILD-UNDERUSE-GATE-36)


def underused(profile, share=UNDERUSE_SHARE, seconds=UNDERUSE_SECONDS):
    """Every stage, and every phase or outermost section inside one, that ran longer than SECONDS on fewer than
    SHARE of the workers its stage held (time-weighted mean of the scheduler's allowance): [{stage, phase,
    wall, cores, jobs, why}]. 'why' is what the numbers say (one core: a serial loop or a single process;
    else part of the pool idle), never a guess at the code."""
    found = []
    for row in profile.get('stages', []):
        if row.get('reused'):
            continue
        held = row.get('jobs_mean') or row.get('jobs_max') or row.get('jobs') or 1
        limit = share * held
        candidates = [(None, row.get('wall') or 0, row.get('cores_avg'))]
        candidates += [(item['name'], item.get('wall') or 0, item.get('cores_avg'))
                       for item in row.get('sections', []) if not item.get('missing')
                       and (item.get('phase') or item.get('min_depth', 0) == 0)
                       and not str(item['name']).startswith('exec ')]
        for name, wall, cores in candidates:
            if wall > seconds and cores is not None and held > 1 and cores < limit:
                why = ('about one core: a serial loop or a single process' if cores < 1.5
                       else 'under half of the pool busy: a small pool, waits or a long last item')
                found.append({'stage': row['name'], 'phase': name, 'wall': round(wall, 1), 'cores': round(cores, 2),
                              'jobs': round(held, 1), 'why': why})
    return sorted(found, key=lambda item: (-item['wall'], item['stage'], item['phase'] or ''))


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
    result = {'critical_path': critical, 'idle_warnings': warnings, 'underused': underused(profile),
              'slowest_stages': slowest,
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
    elif item['kind'] == 'underused-phase':
        text = (f"{stage} ran {seconds} on {item.get('cores')} of the {item.get('jobs')} workers its stage held "
                f"({item.get('why')}). Run its independent items on the shared worker pool, cache its result by the "
                'SHA-256 of its inputs, or give the workers back to the scheduler while it runs.')
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
    for item in (analysis.get('underused') or underused(profile)):
        if item['phase'] is None:
            continue           # whole stages: the idle / tail / serial items above
        items.append({'run': run, 'stage': f"{item['stage']}: {item['phase']}", 'kind': 'underused-phase',
                      'seconds': item['wall'], 'cores': item['cores'], 'jobs': item['jobs'], 'wall': item['wall'],
                      'critical': item['stage'] in on_path, 'host_busy': False, 'why': item['why'],
                      'potential_seconds': round(item['wall'] * max(0.0, 1 - item['cores'] / item['jobs']), 1)})
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


def ledger_stats(rows, share=UNDERUSE_SHARE, seconds=UNDERUSE_SECONDS):
    """Per-stage statistics over many builds from a stage ledger (one JSON object per stage and build, the
    fields the profile's stage rows have: stage, build, wall_s, cpu_s, cores_avg, jobs_max, status): runs,
    median and max wall, median cores, the slowest build, and how many runs were underused (over SECONDS on
    fewer than SHARE of the workers held). Sorted by underused wall time, then median wall."""
    import statistics
    by = {}
    for row in rows:
        wall = row.get('wall_s', row.get('wall'))
        if row.get('stage') is None or wall is None or row.get('status') not in (None, 'passed', 'failed'):
            continue
        by.setdefault(row['stage'], []).append(row)
    table = []
    for stage, items in by.items():
        walls = [float(r.get('wall_s', r.get('wall'))) for r in items]
        cores = [float(r['cores_avg']) for r in items if r.get('cores_avg') is not None]
        under = [r for r in items if float(r.get('wall_s', r.get('wall'))) > seconds and r.get('cores_avg') is not None
                 and (r.get('jobs_max') or r.get('jobs') or 1) > 1
                 and float(r['cores_avg']) < share * float(r.get('jobs_max') or r.get('jobs') or 1)]
        slowest = max(items, key=lambda r: float(r.get('wall_s', r.get('wall'))))
        table.append({'stage': stage, 'runs': len(items), 'median_wall': round(statistics.median(walls), 1),
                      'max_wall': round(max(walls), 1), 'median_cores': round(statistics.median(cores), 2) if cores else None,
                      'slowest_build': slowest.get('build'), 'underused_runs': len(under),
                      'underused_seconds': round(sum(float(r.get('wall_s', r.get('wall'))) for r in under), 1)})
    table.sort(key=lambda r: (-r['underused_seconds'], -r['median_wall'], r['stage']))
    return table


def ledger_lines(table, top=40):
    lines = [f"{'stage':<26}{'runs':>5}{'median':>9}{'max':>9}{'cores':>7}{'underused':>12}  slowest build"]
    for row in table[:top]:
        under = f"{row['underused_runs']}x {_seconds(row['underused_seconds'])}" if row['underused_runs'] else '-'
        lines.append(f"{row['stage'][:25]:<26}{row['runs']:>5}{_seconds(row['median_wall']):>9}"
                     f"{_seconds(row['max_wall']):>9}{(str(row['median_cores']) if row['median_cores'] is not None else '-'):>7}"
                     f"{under:>12}  {row['slowest_build']}")
    return lines


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
    for item in (analysis.get('underused') or [])[:12]:
        lines.append(f"  [underused] {item['stage']}" + (f": {item['phase']}" if item['phase'] else '')
                     + f": {_seconds(item['wall'])} at {item['cores']} of {item['jobs']} cores ({item['why']})")
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
            'underused': analysis.get('underused') or underused(profile),
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


# --------------------------------------------------------------------------
# Build Timeline: one PNG of where the wall time went (stage bars per run, gates and
# other lanes, CPU cores in use stacked by job). docs/BUILD_PROFILE.md "Build Timeline".

TIMELINE_SCHEMA = 'amiwind-build-timeline-v1'
TIMELINE_STEP = 30.0          # CPU chart bucket, seconds
TIMELINE_SERIES = 8           # stacked series drawn; the rest fold into "other"
TIMELINE_SHORT_PX = 8         # a stage bar narrower than this is a tick on the run's "short" row
TIMELINE_FONTS = ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/TTF/DejaVuSans.ttf')
TIMELINE_BOLD = ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf')
# Light chart surface, ink, categorical slots in fixed order and a one-hue (blue) ramp, as the
# other charts in docs/images; status colours only with a text label beside them.
TL_SURFACE, TL_PANEL, TL_GRID, TL_AXIS = '#fcfcfb', '#f3f2ee', '#e1e0d9', '#c3c2b7'
TL_INK, TL_SECONDARY, TL_MUTED = '#0b0b0b', '#52514e', '#898781'
TL_SERIES = ('#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948')
TL_OTHER = '#a8a69e'
TL_RAMP = ('#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf',
           '#1c5cab', '#184f95', '#104281')
TL_GOOD, TL_CRITICAL, TL_RUNNING = '#0ca30c', '#d03b3b', '#898781'


def parse_utc_offset(text):
    """'+03:00', '-0500', '+3', 'UTC' or 'Z' -> seconds east of UTC; 'local' or None -> this machine's zone."""
    if text is None or str(text).strip().lower() == 'local':
        return local_utc_offset()
    value = str(text).strip()
    if value.upper() in ('UTC', 'Z', 'GMT'):
        return 0
    sign = -1 if value.startswith('-') else 1
    digits = value.lstrip('+-').replace(':', '')
    if not digits.isdigit() or len(digits) not in (1, 2, 4):
        raise ValueError(f'Not a UTC offset: {text!r} (use +HH:MM)')
    hours, minutes = (int(digits[:-2] or 0), int(digits[-2:])) if len(digits) == 4 else (int(digits), 0)
    if hours > 14 or minutes > 59:
        raise ValueError(f'Not a UTC offset: {text!r}')
    return sign * (hours * 3600 + minutes * 60)


def local_utc_offset(epoch=None):
    """The UTC offset of this machine's clock at EPOCH (a container usually runs in UTC)."""
    stamp = time.localtime(time.time() if epoch is None else epoch)
    return int(stamp.tm_gmtoff) if getattr(stamp, 'tm_gmtoff', None) is not None else -time.timezone


def to_epoch(value, offset=0):
    """Epoch seconds from a number or an ISO 8601 time. A time with an offset (or Z) is exact;
    a time without one is read in the zone OFFSET (seconds east of UTC), never in this machine's
    zone by accident. Returns None for None or ''."""
    from datetime import datetime, timedelta, timezone
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(' ', 'T', 1)
    if text.endswith('Z') or text.endswith('z'):
        text = text[:-1] + '+00:00'
    if len(text) >= 5 and text[-5] in '+-' and text[-4:].isdigit() and 'T' in text:
        text = text[:-2] + ':' + text[-2:]   # +0300 -> +03:00 (time.strftime('%z'))
    stamp = datetime.fromisoformat(text)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone(timedelta(seconds=offset)))
    return stamp.timestamp()


def clock_text(epoch, offset, pattern='%H:%M'):
    from datetime import datetime, timedelta, timezone
    return datetime.fromtimestamp(epoch, timezone(timedelta(seconds=offset))).strftime(pattern)


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def timeline_run(path, label=None):
    """One build run as the Build Timeline draws it, from the files every build writes.

    A finished run: build-profile.json (stage times, CPU, the sampled CPU timeline, critical
    path). A run still going or without a profile: build-state.json (each stage's start and
    duration on the scheduler clock, reuse, CPU) and build-progress.json (the clock origin and
    the last update, which is where a running stage ends on the chart); build-summary.json gives
    the end of a finished run without a profile. All times are epoch seconds."""
    folder = Path(path)
    if folder.is_file():
        folder = folder.parent
    state = _read_json(folder / 'build-state.json') or {}
    progress = _read_json(folder / 'build-progress.json') or {}
    summary = _read_json(folder / 'build-summary.json') or {}
    received = to_epoch(state.get('build_started_at') or summary.get('started_at'))
    run = {'name': folder.name, 'label': label or folder.name, 'started': received, 'stages': [],
           'cores': [], 'host': [], 'interval': None, 'critical_path': [], 'running': False}
    profile = None
    if (folder / PROFILE_NAME).is_file():
        try:
            profile = load(folder)
        except (OSError, ValueError):
            profile = None
    if profile is not None:
        origin = to_epoch(profile.get('started_at'))
        run.update(source='build-profile.json', origin=origin, end=origin + (profile.get('wall_seconds') or 0),
                   status=profile.get('status'), version=profile.get('version'), budget=profile.get('budget'),
                   host_cpus=profile.get('host_cpus'),
                   critical_path=list(((profile.get('analysis') or {}).get('critical_path') or {}).get('path') or []))
        for row in profile.get('stages', []):
            run['stages'].append({'name': row['name'], 'start': origin + row['start'], 'end': origin + row['end'],
                                  'status': row.get('status'), 'cpu': row.get('cpu'),
                                  'jobs': row.get('jobs_max') or row.get('jobs'), 'reused': bool(row.get('reused')),
                                  'running': False})
        timeline = profile.get('timeline') or {}
        times = timeline.get('t') or []
        own = timeline.get('cgroup_cores') or timeline.get('cores') or []
        busy = timeline.get('host_busy') or []
        cpus = timeline.get('host_cpus') or profile.get('host_cpus') or 1
        run['interval'] = timeline.get('interval') or DEFAULT_INTERVAL
        run['cores'] = [[origin + at, own[i]] for i, at in enumerate(times) if i < len(own) and own[i] is not None]
        run['host'] = [[origin + at, busy[i] * cpus] for i, at in enumerate(times) if i < len(busy) and busy[i] is not None]
    else:
        origin = to_epoch(progress.get('started_at')) or received
        if origin is None:
            raise ValueError(f'{folder}: no build-profile.json, build-progress.json or build-state.json start time')
        updated = progress.get('updated_epoch')
        finished = to_epoch(summary.get('finished_at'))
        status = summary.get('status') or progress.get('status') or state.get('status')
        running = status == 'running'
        last = finished or (float(updated) if updated is not None else None)
        elapsed = {row['name']: row.get('elapsed_seconds') for row in progress.get('stages', [])}
        ends = []
        for step in state.get('steps', []):
            if step.get('started_seconds') is None:
                continue
            start = origin + float(step['started_seconds'])
            seconds = step.get('elapsed_seconds')
            if seconds is None:
                seconds = elapsed.get(step['name'])
            is_running = step.get('status') == 'running'
            if seconds is not None:
                end = start + float(seconds)
            else:
                end = max(start, last if last is not None else start)
            ends.append(end)
            run['stages'].append({'name': step['name'], 'start': start, 'end': end, 'status': step.get('status'),
                                  'cpu': (step.get('profile') or {}).get('cpu_seconds'),
                                  'jobs': step.get('jobs'), 'reused': 'reused' in step, 'running': is_running})
        run.update(source='build-state.json + build-progress.json' if progress else 'build-state.json',
                   origin=origin, end=max([last] if last is not None else ends or [origin]), status=status,
                   version=state.get('runtime_version') or summary.get('version'),
                   budget=progress.get('budget') or state.get('worker_budget') or state.get('compiler_jobs'),
                   host_cpus=(progress.get('host') or {}).get('cpus'), running=running,
                   pending=[row['name'] for row in progress.get('stages', []) if row.get('status') == 'pending'])
    # Phases inside each stage (build_profile.phase records in profile/sections/NN-stage.jsonl).
    for row in run['stages']:
        phases = stage_phases(folder, row['name'], run['end'])
        if phases:
            row['phases'] = phases
    # What the live progress expected of each stage, and on what basis (BUILD-PROGRESS-ETA-BASIS-36).
    expected = {row['name']: row for row in progress.get('stages', []) if row.get('name')}
    for row in run['stages']:
        entry = expected.get(row['name']) or {}
        if entry.get('expected_source') not in (None, 'reused'):
            row['expected'] = entry.get('expected_seconds')
            row['expected_basis'] = entry.get('expected_basis') or entry.get('expected_source')
    if run.get('running') and progress.get('eta_seconds') is not None:
        run['eta'] = {'seconds': progress['eta_seconds'], 'basis': progress.get('eta_basis'),
                      'lower_bound': bool(progress.get('eta_lower_bound'))}
    run['stages'].sort(key=lambda row: (row['start'], row['name']))
    return run


def stage_phases(folder, name, end):
    """[{name, start, end, cores, running}] of a stage's outermost phases from its sections file (epoch times);
    a phase that started and has not ended runs to END (the run's last update)."""
    paths = sorted((Path(folder) / 'profile' / 'sections').glob(f'*-{name}.jsonl'))
    paths = [path for path in paths if path.name.split('-', 1)[1] == f'{name}.jsonl']
    if not paths:
        return []
    found, open_phases = [], {}
    try:
        lines = paths[0].read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not record.get('phase') or record.get('depth', 0) != 0 or record.get('at') is None:
            continue
        key = (record.get('pid'), record['name'], record['at'])
        if record.get('event') == 'start':
            open_phases[key] = record
            continue
        open_phases.pop(key, None)
        found.append({'name': record['name'], 'start': float(record['at']),
                      'end': float(record.get('end_at') or record['at'] + record.get('wall', 0)),
                      'cores': record.get('cores'), 'running': False, 'error': record.get('error')})
    for record in open_phases.values():
        found.append({'name': record['name'], 'start': float(record['at']), 'end': max(float(record['at']), end),
                      'cores': None, 'running': True, 'error': None})
    return sorted(found, key=lambda item: (item['start'], item['name']))


def expectation_text(row):
    """'expected 3 min (basis)' when the live progress's expectation was off by more than 2x, or had
    no comparable history; '' otherwise."""
    basis = row.get('expected_basis')
    if not basis:
        return ''
    took = row['end'] - row['start']
    if row.get('expected') is None:
        return 'expected: ' + basis
    expected = float(row['expected'])
    if expected <= 0 or 0.5 <= took / expected <= 2.0:
        return ''
    return f"expected {_minutes(expected)} ({basis})"


def read_cpu_samples(path, offset=0, cpus=None):
    """CPU samples, one JSON object per line: {"t": time, "name": job, "cores": float}
    (optional "group": the series to stack it in). The name HOST is the whole machine: "cores",
    or "cpu_pct" = percent of all of its CPUs (CPUS). t = epoch seconds or ISO 8601;
    without an offset in the zone OFFSET. Unreadable lines are skipped.
    Returns {name: [[epoch, cores, group], ...]} sorted by time."""
    found = {}
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            item = json.loads(line)
            name = str(item['name'])
            at = to_epoch(item['t'], offset)
        except (ValueError, KeyError, TypeError):
            continue
        cores = item.get('cores')
        if cores is None and item.get('cpu_pct') is not None:
            cores = float(item['cpu_pct']) / 100.0 * ((cpus or host_cpus()) if name == 'HOST' else 1)
        if cores is None or at is None:
            continue
        found.setdefault(name, []).append([at, float(cores), item.get('group')])
    for rows in found.values():
        rows.sort(key=lambda row: row[0])
    return found


def read_lane_events(path, offset=0, lane='gates'):
    """Lane events (gates, kits, any timed job), one JSON object per line:
    {"name": "1615", "start": time, "end": time or null (still running),
     "result": "passed" | "failed" | "running", "lane": optional lane name, "label": optional text}."""
    events = []
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            start = to_epoch(item['start'], offset)
            end = to_epoch(item.get('end'), offset)
        except (ValueError, KeyError, TypeError):
            continue
        if start is None:
            continue
        result = str(item.get('result') or ('running' if end is None else 'passed'))
        events.append({'lane': str(item.get('lane') or lane), 'name': str(item.get('name', '')),
                       'start': start, 'end': end, 'result': result, 'label': item.get('label')})
    return events


def read_commits(spec, start, end):
    """[{'t', 'sha', 'merge'}] of REPO[:BRANCH] between START and END (commit time, epoch)."""
    repo, branch = str(spec), ''
    head, sep, tail = repo.rpartition(':')
    if sep and len(head) > 1 and Path(head).is_dir():   # REPO:BRANCH (a drive letter alone is no split)
        repo, branch = head, tail
    command = ['git', '-C', repo, 'log', '--format=%H %ct %P', f'--since=@{int(start) - 1}', f'--until=@{int(end) + 1}']
    if branch:
        command.insert(4, branch)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f'git log failed for {spec}: {result.stderr.strip()[:200]}')
    commits = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and start <= int(parts[1]) <= end:
            commits.append({'t': float(parts[1]), 'sha': parts[0][:7], 'merge': len(parts) > 3})
    return sorted(commits, key=lambda row: (row['t'], row['sha']))


def sample_intervals(points, nominal=None, cap=3.0):
    """[(start, end, cores)] for timeline points [(t, cores), ...]: each value covers the time
    since the previous point (how the profiler's sampler measures it: CPU used over the real gap,
    divided by that gap). The first point covers NOMINAL seconds before it (default: the median
    gap); a gap longer than CAP x NOMINAL (a sampler pause) is cut to NOMINAL, so a late sample
    never spreads its rate over time it did not see (TEST-PROFILE-TIMELINE-SUM-33)."""
    points = sorted((float(at), float(value)) for at, value in points)
    if not points:
        return []
    gaps = sorted(b[0] - a[0] for a, b in zip(points, points[1:]) if b[0] > a[0])
    if nominal is None:
        nominal = gaps[len(gaps) // 2] if gaps else TIMELINE_STEP
    nominal = max(float(nominal), 1e-6)
    intervals, previous = [], None
    for at, value in points:
        start = at - nominal if previous is None or at - previous > cap * nominal else previous
        if at > start:
            intervals.append((start, at, value))
        previous = at
    return intervals


def core_seconds(intervals):
    """CPU seconds under a set of intervals (cores x seconds)."""
    return sum((end - start) * value for start, end, value in intervals)


def bucket_series(intervals, start, step, count):
    """Time-weighted mean cores per bucket [start + i*step, start + (i+1)*step): each interval adds
    cores x overlap / step to every bucket it overlaps, so the buckets keep exactly the area of the
    intervals inside the window, never more (TEST-PROFILE-TIMELINE-SUM-33). Also returns the
    covered seconds per bucket (0 = no data there)."""
    values, covered = [0.0] * count, [0.0] * count
    end_all = start + step * count
    for a, b, cores in intervals:
        a, b = max(a, start), min(b, end_all)
        if b <= a:
            continue
        first, last = int((a - start) // step), min(count - 1, int((b - start) // step))
        for index in range(first, last + 1):
            lo, hi = start + index * step, start + (index + 1) * step
            overlap = min(b, hi) - max(a, lo)
            if overlap > 0:
                values[index] += cores * overlap / step
                covered[index] += overlap
    return values, covered


def timeline_data(runs, start=None, end=None, samples=None, events=(), commits=(), cpus=None, step=TIMELINE_STEP,
                  title=None, offset=0, top=TIMELINE_SERIES):
    """Everything the chart draws, as plain data (`timeline --json` writes it)."""
    spans = [(run['started'] or run['origin'], run['end']) for run in runs]
    spans += [(item['start'], item['end'] or item['start']) for item in events]
    first = min([a for a, _ in spans if a is not None] or [0.0])
    last = max([b for _, b in spans if b is not None] or [first + 60.0])
    if start is None or end is None:
        pad = max(60.0, 0.02 * (last - first))
        start = first - pad if start is None else start
        end = last + pad if end is None else end
    if end <= start:
        raise ValueError('The time window is empty (end before start)')
    cpus = cpus or max([run.get('host_cpus') or 0 for run in runs] + [0]) or host_cpus()
    data_end = max([run['end'] for run in runs] + [item['end'] or item['start'] for item in events]
                   + [rows[-1][0] for rows in (samples or {}).values() if rows] + [start])
    for item in events:
        if item['end'] is None:   # still running: drawn to the end of the data
            item['end'] = max(item['start'], min(data_end, end))
    count = max(1, int(math.ceil((end - start) / step)))
    # CPU series: samples grouped (explicit group, else the run whose folder name the sample name
    # contains, else the name), then each run's own profiler timeline where no sample covers it.
    series, order = {}, []

    def add(name, values, covered, first_seen):
        if name not in series:
            series[name] = {'name': name, 'values': [0.0] * count, 'covered': [0.0] * count, 'first': first_seen}
            order.append(name)
        entry = series[name]
        entry['values'] = [a + b for a, b in zip(entry['values'], values)]
        entry['covered'] = [max(a, b) for a, b in zip(entry['covered'], covered)]
        entry['first'] = min(entry['first'], first_seen)

    host_line, host_source = None, None
    for name in sorted(samples or {}):
        rows = samples[name]
        if not rows:
            continue
        intervals = sample_intervals([(at, cores) for at, cores, _ in rows])
        values, covered = bucket_series(intervals, start, step, count)
        if name == 'HOST':
            host_line, host_source = [v if c > 0 else None for v, c in zip(values, covered)], 'samples'
            continue
        group = rows[0][2] or next((run['label'] for run in runs if run['name'] in name), name)
        add(group, values, covered, rows[0][0])
    sampled = {name for name in series}
    host_profile = [0.0] * count
    host_covered = [0.0] * count
    for run in runs:
        if run['cores']:
            values, covered = bucket_series(sample_intervals(run['cores'], run['interval']), start, step, count)
            if run['label'] in sampled:
                entry = series[run['label']]
                entry['values'] = [have if have_cov > 0 else value for have, have_cov, value in
                                   zip(entry['values'], entry['covered'], values)]
                entry['covered'] = [max(a, b) for a, b in zip(entry['covered'], covered)]
            elif any(covered):
                add(run['label'], values, covered, run['cores'][0][0])
        if run['host']:
            values, covered = bucket_series(sample_intervals(run['host'], run['interval']), start, step, count)
            host_profile = [a + b if c > 0 else a for a, b, c in zip(host_profile, values, covered)]
            host_covered = [max(a, b) for a, b in zip(host_covered, covered)]
    if host_line is None and any(host_covered):
        host_line = [v if c > 0 else None for v, c in zip(host_profile, host_covered)]
        host_source = 'build profiler (/proc/stat)'
    ordered = sorted(order, key=lambda name: (series[name]['first'], name))
    totals = {name: sum(series[name]['values']) * step for name in ordered}
    if len(ordered) > top:
        keep = set(sorted(ordered, key=lambda name: (-totals[name], name))[:top - 1])
        other = {'name': 'other', 'values': [0.0] * count, 'covered': [0.0] * count, 'first': 0.0}
        for name in ordered:
            if name not in keep:
                other['values'] = [a + b for a, b in zip(other['values'], series[name]['values'])]
        ordered = [name for name in ordered if name in keep]
        series['other'] = other
        totals['other'] = sum(other['values']) * step
        ordered.append('other')
    return {'schema': TIMELINE_SCHEMA, 'title': title, 'window': [start, end], 'data_end': data_end,
            'sampled': bool(sampled),
            'utc_offset': offset, 'step': step, 'host_cpus': cpus, 'runs': runs, 'events': list(events),
            'commits': list(commits),
            'series': [{'name': name, 'values': [round(v, 4) for v in series[name]['values']],
                        'core_seconds': round(totals[name], 1)} for name in ordered],
            'host': {'values': None if host_line is None else [None if v is None else round(v, 4) for v in host_line],
                     'source': host_source}}


def _timeline_font(size, bold=False):
    from PIL import ImageFont
    for path in (TIMELINE_BOLD if bold else TIMELINE_FONTS):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:   # Pillow < 10.1: one small bitmap font
        return ImageFont.load_default()


def _rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def _dark(colour):
    red, green, blue = _rgb(colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue < 140


def _pack(items, gap=6):
    """Rows of items {'x0', 'x1'} so that no two in a row overlap (first row that is free)."""
    rows = []
    for item in sorted(items, key=lambda row: (row['x0'], row['key'])):
        for row in rows:
            if row[-1]['x1'] + gap <= item['x0']:
                row.append(item)
                break
        else:
            rows.append([item])
    return rows


def _minutes(seconds):
    if seconds < 90:
        return f'{seconds:.0f} s'
    if seconds < 5400:
        return f'{seconds / 60:.0f} min'
    return f'{seconds / 3600:.1f} h'


def render_timeline(data):
    """The Build Timeline as PNG bytes. Same data -> byte-identical PNG (no time stamps, no
    metadata; fonts and Pillow version are the only other inputs)."""
    from PIL import Image, ImageDraw
    import io
    offset = data['utc_offset']
    start, end = data['window']
    width = 2000
    left, right = 340, width - 40
    fonts = {key: _timeline_font(size, bold) for key, (size, bold) in {
        'title': (40, True), 'sub': (18, False), 'lane': (20, True), 'lanesub': (15, False),
        'bar': (13, False), 'small': (12, False), 'axis': (15, False), 'legend': (15, False)}.items()}

    def x_of(at):
        return left + (min(max(at, start), end) - start) * (right - left) / (end - start)

    image = Image.new('RGB', (width, 6000), _rgb(TL_SURFACE))
    draw = ImageDraw.Draw(image)
    runs, events, commits = data['runs'], data['events'], data['commits']
    title = data.get('title') or (runs[0]['label'] if len(runs) == 1 else
                                  (runs[0].get('version') and f"v{runs[0]['version']} builds") or 'Builds')
    draw.text((30, 20), f'{title}: where the wall time went', font=fonts['title'], fill=TL_INK)
    zone = f'UTC{offset // 3600:+03d}:{abs(offset) % 3600 // 60:02d}'
    host_source = (data['host'] or {}).get('source')
    lines = [f'Build Timeline. Host local time ({zone}); times in the build records (UTC) converted. '
             f'Window {clock_text(start, offset)} - {clock_text(end, offset)} '
             f'({clock_text(start, offset, "%Y-%m-%d")}), data to {clock_text(data["data_end"], offset)}.',
             'Stages from each run\'s build-profile.json, or build-state.json + build-progress.json while it runs; '
             'CPU from ' + ('the CPU samples and ' if data.get('sampled') else '')
             + 'the build profiler' + (f'; whole-machine line from {host_source}' if host_source else '') + '.']
    for index, line in enumerate(lines):
        draw.text((30, 76 + 24 * index), line, font=fonts['sub'], fill=TL_SECONDARY)
    y = 160
    top = y + 26

    def panel(y0, height, name, sub=None):
        draw.rectangle((left, y0, right, y0 + height), fill=TL_PANEL)
        middle = y0 + min(height, 60) / 2
        draw.text((30, middle - (20 if sub else 12)), name, font=fonts['lane'], fill=TL_INK)
        if sub:
            draw.text((30, middle + 4), sub, font=fonts['lanesub'], fill=TL_SECONDARY)

    def bar(a, b, y0, height, fill, outline=None, width_=1):
        xa, xb = x_of(a), max(x_of(b), x_of(a) + 2)
        draw.rectangle((xa, y0, xb, y0 + height), fill=fill, outline=outline, width=width_)
        return xa, xb

    y = top
    if commits:
        height = 40
        panel(y, height, f'commits ({len(commits)})', 'short tick = merge')
        for commit in commits:
            x = x_of(commit['t'])
            draw.line((x, y + (height / 2 if commit['merge'] else 6), x, y + height - 6), fill=TL_SERIES[0], width=2)
        y += height + 10

    lanes = []
    for item in events:
        if item['lane'] not in lanes:
            lanes.append(item['lane'])
    for lane in lanes:
        items = [item for item in events if item['lane'] == lane and item['end'] >= start and item['start'] <= end]
        boxes = []
        for item in items:
            text = str(item.get('label') or item['name'])
            x0, x1 = x_of(item['start']), max(x_of(item['end']), x_of(item['start']) + 2)
            label_w = draw.textlength(text, font=fonts['small']) + 6
            inside = x1 - x0 >= label_w
            boxes.append({'key': (item['start'], item['name']), 'x0': x0, 'x1': x1 if inside else x1 + label_w,
                          'item': item, 'text': text, 'bar1': x1, 'inside': inside})
        rows = _pack(boxes)
        row_h = 22
        height = max(1, len(rows)) * row_h + 8
        failed = sum(1 for item in items if item['result'] == 'failed')
        panel(y, height, f'{lane} ({len(items)})', f'{failed} failed; green passed, red failed, grey running')
        for number, row in enumerate(rows):
            yy = y + 5 + number * row_h
            for box in row:
                item = box['item']
                colour = {'passed': TL_GOOD, 'failed': TL_CRITICAL}.get(item['result'], TL_RUNNING)
                draw.rectangle((box['x0'], yy, box['bar1'], yy + row_h - 6), fill=TL_SURFACE, outline=colour, width=2)
                text_x = box['x0'] + 3 if box['inside'] else box['bar1'] + 3
                draw.text((text_x, yy + 1), box['text'], font=fonts['small'], fill=TL_INK)
        y += height + 10

    short_seen = []
    for run in runs:
        stages = [row for row in run['stages'] if row['end'] >= start and row['start'] <= end]
        reused = [row for row in stages if row['reused']]
        ran = [row for row in stages if not row['reused']]
        budget = run.get('budget') or data['host_cpus']
        critical = set(run.get('critical_path') or [])
        boxes, short = [], []
        for row in ran:
            cores = (row['cpu'] or 0) / max(row['end'] - row['start'], 1e-6) if row.get('cpu') is not None else None
            x0, x1 = x_of(row['start']), max(x_of(row['end']), x_of(row['start']) + 2)
            if x1 - x0 < TIMELINE_SHORT_PX and not row['running']:
                short.append(row)   # too short to read at this scale: a tick on the "short" row
                continue
            parts = [row['name'], _minutes(row['end'] - row['start'])]
            if cores is not None and not row['running']:
                parts.append(f'{cores:.1f} cores')
            if row['running']:
                parts.append('running')
            elif row['status'] not in ('passed', None):
                parts.append(str(row['status']).upper())
            note = expectation_text(row)
            if note:
                parts.append(note)
            text = ', '.join(parts)
            label_w = draw.textlength(text, font=fonts['bar']) + 8
            boxes.append({'key': (row['start'], row['name']), 'x0': x0, 'x1': x1 if x1 - x0 >= label_w else x1 + label_w,
                          'bar1': x1, 'inside': x1 - x0 >= label_w, 'row': row, 'text': text, 'cores': cores})
        short_seen += short
        # A stage with phases gets its own row and a strip of its phases under its bar.
        rows = _pack([box for box in boxes if not box['row'].get('phases')])
        rows += [[box] for box in sorted((box for box in boxes if box['row'].get('phases')), key=lambda b: b['key'])]
        rows.sort(key=lambda row: (row[0]['key']))
        row_h = 22
        heights = [row_h * (2 if row[0]['row'].get('phases') else 1) for row in rows]
        head = 92
        height = head + sum(heights) + 4
        draw.rectangle((left, y, right, y + height), fill=TL_PANEL)
        draw.text((30, y + 6), run['label'] if len(run['label']) <= 24 else run['label'][:22] + '..',
                  font=fonts['lane'], fill=TL_INK)
        failed = [row['name'] for row in stages if row['status'] not in ('passed', 'running', None)]
        status = 'running' if run.get('running') else str(run.get('status'))
        wall = run['end'] - (run['started'] or run['origin'])
        info = [f'{len(stages)} stages: {len(ran)} ran, {len(reused)} reused',
                f'{status}, {_minutes(wall)}, budget {budget}']
        if failed:
            info.append('failed: ' + ', '.join(failed)[:36])
        elif run.get('pending'):
            info.append(f"{len(run['pending'])} stages still to run")
        for index, line in enumerate(info):
            draw.text((30, y + 32 + 17 * index), line, font=fonts['lanesub'], fill=TL_SECONDARY)
        # Whole run: from the receipt's start (preflight, checks) to the end of the data; its folder name below.
        if run['started'] is not None and run['started'] < run['origin']:
            bar(run['started'], run['origin'], y + 6, 10, TL_AXIS)
        bar(run['origin'], run['end'], y + 6, 10, TL_SECONDARY)
        name = run['name'] if len(run['name']) < 120 else run['name'][:118] + '..'
        if run.get('eta'):
            eta = run['eta']
            name += (f" | ETA {'at least ' if eta['lower_bound'] else ''}{_minutes(eta['seconds'])} at the last "
                     f"update ({eta['basis']})")
        name_x = min(max(left + 6, x_of(run['started'] or run['origin'])),
                     right - 6 - draw.textlength(name, font=fonts['small']))
        draw.text((max(left + 6, name_x), y + 19), name, font=fonts['small'], fill=TL_SECONDARY)
        # Reused stages and stages too short to label: ticks on one row each, counted on the left.
        for offset_y, title_text, items, colour in ((38, f'reused ({len(reused)})', reused, TL_AXIS),
                                                    (60, f'short ({len(short)})', short, TL_RAMP[6])):
            draw.text((left - 8 - draw.textlength(title_text, font=fonts['small']), y + offset_y),
                      title_text, font=fonts['small'], fill=TL_SECONDARY)
            for row in items:
                bad = row['status'] not in ('passed', None)
                bar(row['start'], row['end'], y + offset_y + 1, 14, TL_CRITICAL if bad else colour)
                if bad:
                    draw.text((x_of(row['end']) + 5, y + offset_y), f"{row['name']} {str(row['status']).upper()}",
                              font=fonts['small'], fill=TL_INK)
        yy = y + head
        if rows:
            draw.text((left - 8 - draw.textlength('ran', font=fonts['small']), yy + 2), 'ran', font=fonts['small'],
                      fill=TL_SECONDARY)
        for number, row in enumerate(rows):
            ry = yy + sum(heights[:number])
            for box in row:
                stage = box['row']
                for item in stage.get('phases') or ():   # the strip under the bar
                    pa, pb = x_of(item['start']), max(x_of(item['end']), x_of(item['start']) + 2)
                    share = min(1.0, (item['cores'] or 0) / float(budget or 1))
                    shade = TL_CRITICAL if item.get('error') else TL_RAMP[min(len(TL_RAMP) - 1,
                                                                              int(share * (len(TL_RAMP) - 1) + 0.5))]
                    draw.rectangle((pa, ry + row_h, pb, ry + 2 * row_h - 6), fill=shade, outline=TL_SURFACE)
                    label = item['name'][len('CHIM '):] if item['name'].startswith('CHIM ') else item['name']
                    label += ' ' + _minutes(item['end'] - item['start'])
                    if item['cores'] is not None:
                        label += f", {item['cores']:.1f} c"
                    elif item['running']:
                        label += ', running'
                    if draw.textlength(label, font=fonts['small']) + 6 <= pb - pa:
                        draw.text((pa + 3, ry + row_h + 2), label, font=fonts['small'],
                                  fill='#ffffff' if _dark(shade) else TL_INK)
                if stage['running']:
                    fill = TL_RAMP[3]
                elif stage['status'] not in ('passed', None):
                    fill = TL_CRITICAL
                elif box['cores'] is None:
                    fill = TL_AXIS
                else:
                    share = min(1.0, max(0.0, box['cores'] / float(budget or 1)))
                    fill = TL_RAMP[min(len(TL_RAMP) - 1, int(share * (len(TL_RAMP) - 1) + 0.5))]
                outline = TL_INK if stage['name'] in critical else None
                xa, xb = box['x0'], box['bar1']
                draw.rectangle((xa, ry, xb, ry + row_h - 5), fill=fill, outline=outline, width=2 if outline else 1)
                if stage['running']:   # open end: diagonal hatching, the bar keeps growing
                    for hx in range(int(xa) - (row_h - 5), int(xb), 8):
                        draw.line((max(xa, hx), ry + row_h - 5 - max(0, xa - hx), min(xb, hx + row_h - 5),
                                   ry + max(0, hx + row_h - 5 - xb)), fill=TL_SURFACE, width=1)
                if box['inside']:
                    draw.text((xa + 4, ry + 2), box['text'], font=fonts['bar'],
                              fill='#ffffff' if _dark(fill) else TL_INK)
                else:
                    draw.text((xb + 4, ry + 2), box['text'], font=fonts['bar'], fill=TL_INK)
        y += height + 10
    lanes_bottom = y

    # CPU cores in use, stacked by series; whole-machine line; the machine's CPU count dashed.
    series = data['series']
    step = data['step']
    count = len(series[0]['values']) if series else max(1, int(math.ceil((end - start) / step)))
    stack_top = [0.0] * count
    for entry in series:
        stack_top = [a + b for a, b in zip(stack_top, entry['values'])]
    host = (data['host'] or {}).get('values')
    peak = max([data['host_cpus']] + stack_top + [v for v in (host or []) if v is not None])
    scale = 4 if peak <= 32 else 8 if peak <= 64 else 16
    y_max = scale * math.ceil(peak * 1.08 / scale)
    chart_h = 380
    c0, c1 = y + 10, y + 10 + chart_h
    draw.rectangle((left, c0, right, c1), fill=TL_PANEL)
    draw.text((30, c0 + 4), 'CPU cores in use', font=fonts['lane'], fill=TL_INK)
    draw.text((30, c0 + 32), f'stacked by job, {step:.0f} s means\n(time-weighted)', font=fonts['lanesub'],
              fill=TL_SECONDARY)

    def y_of(cores):
        return c1 - min(cores, y_max) * chart_h / y_max

    for tick in range(0, int(y_max) + 1, scale):
        draw.line((left, y_of(tick), right, y_of(tick)), fill=TL_GRID)
        label = str(tick)
        draw.text((left - 8 - draw.textlength(label, font=fonts['axis']), y_of(tick) - 9), label,
                  font=fonts['axis'], fill=TL_MUTED)
    colours = {}
    slot = 0
    for entry in series:
        if entry['name'] == 'other':
            colours['other'] = TL_OTHER
        else:
            colours[entry['name']] = TL_SERIES[slot % len(TL_SERIES)]
            slot += 1
    base = [0.0] * count
    for entry in series:
        for index, value in enumerate(entry['values']):
            if value <= 0:
                continue
            a = start + index * step
            xa, xb = x_of(a), x_of(min(end, a + step))
            if xb <= xa:
                continue
            draw.rectangle((xa, y_of(base[index] + value), xb, y_of(base[index])), fill=colours[entry['name']])
        base = [a + b for a, b in zip(base, entry['values'])]
    for xx in range(left, right, 16):
        draw.line((xx, y_of(data['host_cpus']), min(right, xx + 8), y_of(data['host_cpus'])), fill=TL_SECONDARY, width=2)
    draw.text((left + 6, y_of(data['host_cpus']) - 18), f"{data['host_cpus']} CPU threads", font=fonts['small'],
              fill=TL_SECONDARY)
    if host:
        points = []
        for index, value in enumerate(host):
            if value is None:
                if len(points) > 1:
                    draw.line(points, fill=TL_INK, width=2)
                points = []
                continue
            points.append((x_of(start + (index + 0.5) * step), y_of(value)))
        if len(points) > 1:
            draw.line(points, fill=TL_INK, width=2)

    # Time axis over every lane and the chart.
    span = end - start
    tick = next((value for value in (300, 600, 900, 1800, 3600, 7200, 14400, 43200, 86400) if span / value <= 14), 86400)
    at = (math.floor((start + offset) / tick) + 1) * tick - offset
    while at < end:
        x = x_of(at)
        draw.line((x, top, x, lanes_bottom - 10), fill=TL_GRID, width=1)
        draw.line((x, c0, x, c1), fill=TL_GRID, width=1)
        label = clock_text(at, offset)
        draw.text((x - draw.textlength(label, font=fonts['axis']) / 2, top - 22), label, font=fonts['axis'],
                  fill=TL_MUTED)
        draw.text((x - draw.textlength(label, font=fonts['axis']) / 2, c1 + 4), label, font=fonts['axis'],
                  fill=TL_MUTED)
        at += tick

    # Legend: CPU series with core-minutes, lines, stage colours.
    y = c1 + 34
    x = left
    entries = [(colours[entry['name']], f"{entry['name']} ({entry['core_seconds'] / 60:.0f} core-min)")
               for entry in series]
    if host:
        entries.append((TL_INK, 'whole machine'))
    for colour, text in entries:
        w = 30 + draw.textlength(text, font=fonts['legend'])
        if x + w > right:
            x, y = left, y + 24
        draw.rectangle((x, y + 3, x + 16, y + 19), fill=colour)
        draw.text((x + 22, y), text, font=fonts['legend'], fill=TL_INK)
        x += w + 24
    y += 30
    x = left
    every = [row for run in runs for row in run['stages'] if row['end'] >= start and row['start'] <= end]
    shown = {'running': any(row['running'] for row in every),
             'failed': any(row['status'] not in ('passed', 'running', None) for row in every),
             'reused': any(row['reused'] for row in every), 'short': bool(short_seen),
             'critical': any(run.get('critical_path') for run in runs),
             'phases': any(row.get('phases') for row in every)}
    for colour, text, outline, kind in ((TL_RAMP[1], 'stage, few cores of its budget', None, None),
                                        (TL_RAMP[-2], 'stage, all cores of its budget', None, None),
                                        (TL_PANEL, 'critical path (outline)', TL_INK, 'critical'),
                                        (TL_RAMP[3], 'running (hatched)', None, 'running'),
                                        (TL_CRITICAL, 'failed', None, 'failed'), (TL_AXIS, 'reused', None, 'reused'),
                                        (TL_RAMP[6], 'short (too short to label)', None, 'short'),
                                        (TL_RAMP[4], 'phases inside a stage (strip under its bar)', None, 'phases')):
        if kind and not shown[kind]:
            continue
        w = 30 + draw.textlength(text, font=fonts['legend'])
        if x + w > right:
            x, y = left, y + 24
        draw.rectangle((x, y + 3, x + 16, y + 19), fill=colour, outline=outline, width=2 if outline else 1)
        draw.text((x + 22, y), text, font=fonts['legend'], fill=TL_INK)
        x += w + 24
    y += 30
    for line in ('Core-minutes count only the window. A stage label gives its wall time and its average cores '
                 '(CPU / wall); the run bar at the top of each run starts at the build receipt (light: checks before '
                 'the first stage).',
                 'Sampled CPU is a snapshot per sample interval, so where jobs overlap the stack can pass the '
                 'whole-machine line; the gap below that line is load no series covers.'):
        draw.text((left, y), line, font=fonts['small'], fill=TL_SECONDARY)
        y += 18
    image = image.crop((0, 0, width, y + 20))
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def timeline_main(args):
    try:
        import PIL  # noqa: F401
    except ImportError:
        if not args.json:
            raise ValueError('The Build Timeline needs Pillow (python -m pip install Pillow; the builder Docker '
                             'image has it). --json writes the chart data without it.')
    offset = parse_utc_offset(args.utc_offset)
    if args.labels and len(args.labels) != len(args.runs):
        raise ValueError(f'--labels: {len(args.labels)} labels for {len(args.runs)} runs')
    runs = [timeline_run(path, args.labels[i] if args.labels else None) for i, path in enumerate(args.runs)]
    runs.sort(key=lambda run: (run['started'] or run['origin'], run['name']))
    cpus = args.host_cpus
    samples = read_cpu_samples(args.samples, offset, cpus or max([r.get('host_cpus') or 0 for r in runs] + [0]) or None) \
        if args.samples else {}
    events = []
    for path in args.gates or []:
        events += read_lane_events(path, offset, 'gates')
    for path in args.events or []:
        events += read_lane_events(path, offset, 'events')
    start, end = to_epoch(args.start, offset), to_epoch(args.end, offset)
    if start is not None:
        samples = {name: [row for row in rows if row[0] >= start - 600] for name, rows in samples.items()}
    if end is not None:
        samples = {name: [row for row in rows if row[0] <= end + 600] for name, rows in samples.items()}
    data = timeline_data(runs, start, end, samples, events, cpus=cpus, step=args.step, title=args.title,
                         offset=offset)
    if args.commits:
        data['commits'] = read_commits(args.commits, data['window'][0], data['window'][1])
    if args.json:
        args.json.write_text(json.dumps(data, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        print(f'Chart data: {args.json}')
    if args.png:
        png = render_timeline(data)
        args.png.write_bytes(png)
        import hashlib
        print(f'Build Timeline: {args.png} ({len(png)} bytes, sha256 {hashlib.sha256(png).hexdigest()})')
    return 0


# --------------------------------------------------------------------------
# Unit reuse audit (HASH EVERYTHING): per stage, the units a run computed and reused, the input whose hash
# changed for each computed unit, and loud failures for a unit computed again with an unchanged key.
# Reads the cache provenance records (schema aw-cache-provenance-1, tools/cache_provenance.py): a "provenance"
# field in a JSON cache entry or a <entry>.meta.json sidecar, and <cache>/.provenance/reuse.jsonl.

PROVENANCE_SCHEMA = 'aw-cache-provenance-1'
# Which stage writes which cache (the folder name under the shared cache root). A stage that ran without any of
# its caches being touched, or that has none here, is "unkeyed": it is reused or rebuilt only as a whole stage.
STAGE_CACHES = {
    'world-terrain': ('world-terrain-v1',),
    'world-scenery': ('image-passes/world-scenery-region',),
    'world-flora': ('image-passes/world-flora-region',),
    'chim': ('chim-units', 'image-passes/stair-walk', 'chim-units/heap', 'image-passes/chim-validate',
             'image-passes/chim-zone-walk'),
    'character': ('image-passes/character-head',),
    'image': ('image-passes/hidden-surface-cull', 'image-passes/optimize-world-maps', 'image-passes/exterior-sky',
              'image-passes/stair-walk', 'image-passes/interior-room', 'image-passes/town-region',
              'image-passes/character-head'),
    'balmora': ('image-passes/town-region',),
    'balmora-interiors': ('image-passes/interior-room',),
    'chim-room-batches': ('image-passes/interior-room-chim',),
}


def _provenance_records(cache_root):
    """(records, reuse lines) of one cache folder: every provenance record found (entry JSON field, sidecar, or
    backfill log) and every reuse line."""
    root = Path(cache_root)
    records, reuses = [], []
    if not root.is_dir():
        return records, reuses
    for path in sorted(root.rglob('*.json')):
        if '.provenance' in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        record = data if path.name.endswith('.meta.json') else (data.get('provenance') if isinstance(data, dict) else None)
        if isinstance(record, dict) and record.get('schema') == PROVENANCE_SCHEMA:
            records.append(dict(record, _path=str(path.relative_to(root))))
    folder = root / '.provenance'
    for name, target in (('backfill.jsonl', records), ('reuse.jsonl', reuses)):
        try:
            lines = (folder / name).read_text(encoding='utf-8').splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                target.append(row)
    return records, reuses


def _unit_of(record):
    manifest = record.get('input_manifest') or {}
    return record.get('unit') or manifest.get('unit')


def changed_inputs(new, old):
    """Names of the inputs whose SHA-256 differs between two input manifests (added and removed inputs too),
    plus 'parameters' when those differ."""
    a = {row.get('name'): row.get('sha256') for row in ((new or {}).get('inputs') or [])}
    b = {row.get('name'): row.get('sha256') for row in ((old or {}).get('inputs') or [])}
    changed = sorted(str(name) for name in set(a) | set(b) if a.get(name) != b.get(name))
    if (new or {}).get('parameters') != (old or {}).get('parameters'):
        changed.append('parameters')
    return changed


def unit_reuse(run, cache_roots, stages=None):
    """The unit reuse audit of RUN (its folder name or path) over CACHE_ROOTS (cache folders).

    Returns {'run', 'caches': {cache: {'computed', 'reused', 'units': [...]}}, 'failures': [...],
    'unexplained': [...], 'unkeyed': [...]}. A computed unit lists the inputs whose hash changed against the
    newest earlier entry of the same unit; a computed unit whose key an earlier entry (or an earlier computation
    in this run) already had is a FAILURE: it should have been reused. A computed unit without a unit name or
    without an earlier entry is listed as new (no earlier entry) or unexplained (no unit name to compare)."""
    name = Path(str(run)).name
    report = {'run': name, 'caches': {}, 'failures': [], 'unexplained': [], 'unkeyed': []}
    touched = set()
    for root in cache_roots:
        root = Path(root)
        records, reuses = _provenance_records(root)
        if not records and not reuses:
            continue
        label = root.name
        mine = [r for r in records if r.get('run') == name]
        reused = [r for r in reuses if r.get('run') == name]
        before = sorted((r for r in records if r.get('run') != name), key=lambda r: str(r.get('created_at')))
        # Keys that existed before a unit was computed: earlier entries, and keys other runs reused earlier (an
        # overwritten entry leaves only the new record, but its reuse lines remain).
        known = [(str(r.get('created_at')), r.get('key')) for r in before if r.get('key')]
        known += [(str(r.get('at')), r.get('key')) for r in reuses if r.get('run') != name and r.get('key')]
        computed_here = set()
        units = []
        for record in sorted(mine, key=lambda r: (str(r.get('created_at')), str(r.get('key')))):
            unit, key = _unit_of(record), record.get('key')
            when = str(record.get('created_at'))
            seen_keys = {k for at, k in known if at < when} | computed_here
            row = {'unit': unit, 'key': key, 'entry': record.get('_path')}
            if key in seen_keys:
                row['status'] = 'FAILURE: computed again with an unchanged key'
                report['failures'].append(dict(row, cache=label))
            elif unit is None:
                row['status'] = 'unexplained: no unit name in the input manifest'
                report['unexplained'].append(dict(row, cache=label))
            else:
                earlier = [r for r in before if _unit_of(r) == unit]
                if earlier:
                    row['status'] = 'changed'
                    row['changed_inputs'] = changed_inputs(record.get('input_manifest'), earlier[-1].get('input_manifest'))
                else:
                    row['status'] = 'new unit'
            computed_here.add(key)
            units.append(row)
        report['caches'][label] = {'computed': len(mine), 'reused': len(reused), 'units': units}
        if mine or reused:
            touched.add(label)
    for stage in stages or ():
        caches = {Path(c).name for c in STAGE_CACHES.get(stage, ())}
        if not caches or not caches & touched:
            report['unkeyed'].append(stage)
    return report


def unit_reuse_lines(report, top=20):
    lines = [f"Unit reuse audit: {report['run']}"]
    for cache, row in sorted(report['caches'].items()):
        changed = [u for u in row['units'] if u['status'] == 'changed']
        lines.append(f"  {cache}: {row['computed']} computed, {row['reused']} reused"
                     + (f" ({len(changed)} with a changed input)" if changed else ''))
        for unit in changed[:top]:
            lines.append(f"    {unit['unit']}: {', '.join(unit['changed_inputs']) or 'no input named'}")
    for unit in report['failures']:
        lines.append(f"  RECOMPUTED WITH AN UNCHANGED KEY: {unit['cache']} {unit['unit'] or unit['entry']} "
                     f"(key {str(unit['key'])[:16]}) - a reuse bug")
    if report['unexplained']:
        lines.append(f"  unexplained (no unit name to compare): {len(report['unexplained'])}")
    if report['unkeyed']:
        lines.append('  unkeyed stages (reused or rebuilt only as a whole): ' + ', '.join(report['unkeyed']))
    return lines


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
    tune.add_argument('runs', type=Path, nargs='*', metavar='run', help='Build run folders or build-profile.json files')
    tune.add_argument('--share', type=float, default=IDLE_SHARE, help='Idle below this share of the jobs (default 0.5)')
    tune.add_argument('--seconds', type=float, default=IDLE_SECONDS, help='... for longer than this (default 60)')
    tune.add_argument('--json', action='store_true', help='Print the items as JSON')
    tune.add_argument('--ledger', type=Path, metavar='JSONL',
                      help='Also (or only) per-stage statistics over many builds from a stage ledger: one JSON object '
                           'per stage and build (stage, build, wall_s, cores_avg, jobs_max, status)')
    chart = sub.add_parser('timeline', help='Build Timeline: a PNG of where the wall time went (stages of one or '
                                            'more runs, gates and other lanes, CPU cores stacked by job)')
    chart.add_argument('runs', type=Path, nargs='+', metavar='run', help='Build run folders (finished or running)')
    chart.add_argument('--png', type=Path, metavar='OUT', help='Write the chart here')
    chart.add_argument('--json', type=Path, metavar='OUT', help='Write the chart data here (works without Pillow)')
    chart.add_argument('--start', help='Window start, host local time (YYYY-MM-DD HH:MM) or ISO 8601 with offset')
    chart.add_argument('--end', help='Window end (default: the end of the data)')
    chart.add_argument('--utc-offset', default='local',
                       help='The zone to draw in and to read times without an offset (+HH:MM; default: this '
                            "machine's zone, which inside a container is usually UTC)")
    chart.add_argument('--samples', type=Path, metavar='JSONL', help='CPU samples: {"t", "name", "cores"} per line '
                       '(name HOST = the whole machine, "cores" or "cpu_pct")')
    chart.add_argument('--gates', type=Path, action='append', metavar='JSONL',
                       help='Gate runs: {"name", "start", "end", "result"} per line (repeatable)')
    chart.add_argument('--events', type=Path, action='append', metavar='JSONL',
                       help='Other timed jobs, same fields plus "lane" (repeatable)')
    chart.add_argument('--commits', metavar='REPO[:BRANCH]', help='Commit ticks from git log')
    chart.add_argument('--labels', nargs='+', help='Short names for the runs, in the order given')
    chart.add_argument('--title', help='Title before ": where the wall time went"')
    chart.add_argument('--host-cpus', type=int, help='CPU threads of the machine (default: from the profiles)')
    chart.add_argument('--step', type=float, default=TIMELINE_STEP, help='CPU chart bucket in seconds (default 30)')
    audit = sub.add_parser('reuse', help='Unit reuse audit: per cache the units a run computed and reused, the input '
                                         'whose hash changed, and units computed again with an unchanged key')
    audit.add_argument('run', type=Path, help='Build run folder (or its name)')
    audit.add_argument('--cache', type=Path, action='append', required=True, metavar='DIR',
                       help='A cache folder with provenance records (repeatable)')
    audit.add_argument('--json', action='store_true')
    audit.add_argument('--fail-on-recompute', action='store_true',
                       help='Exit 3 when a unit was computed again with an unchanged key')
    args = parser.parse_args(argv)
    try:
        if args.action == 'reuse':
            stages = None
            state = _read_json(Path(args.run) / 'build-state.json')
            if state:
                stages = [step['name'] for step in state.get('steps', []) if 'reused' not in step]
            report = unit_reuse(args.run, args.cache, stages)
            print(json.dumps(report, indent=1) if args.json else chr(10).join(unit_reuse_lines(report)))
            return 3 if args.fail_on_recompute and report['failures'] else 0
        if args.action == 'timeline':
            if not args.png and not args.json:
                parser.error('timeline: give --png OUT.png and/or --json OUT.json')
            return timeline_main(args)
        if args.action == 'compare':
            comparison = compare(load(args.run), load(args.older))
            comparison['old_run'] = str(args.older)
            print(json.dumps(comparison, indent=2) if args.json else '\n'.join(compare_lines(comparison)))
            return 3 if args.fail_on_regression and comparison['regressions'] else 0
        if args.action == 'optimize':
            if args.ledger:
                rows = [json.loads(line) for line in args.ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
                table = ledger_stats(rows, args.share, max(UNDERUSE_SECONDS, 0.0))
                print(json.dumps({'ledger': table}, indent=2) if args.json and not args.runs
                      else chr(10).join(ledger_lines(table)))
                if not args.runs:
                    return 0
                print()
            if not args.runs:
                parser.error('optimize: give run folders and/or --ledger FILE')
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
