#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The failure details of a failed build: RUN/FAILURE.md and RUN/failure.json (BUILD-FAILURE-NO-DETAILS-66).

When a stage or the build itself fails, the builder writes one page beside the logs that says what failed: first the
failure's kind when its marks are there (OUT OF MEMORY, OUT OF DISK: what was found and what to do), then the failed
stage, its exit, its error lines, the traceback when the log holds one, the last 60 lines of the stage's log, the units
it refused or left out (its "not converted: ..." lines), what was not completed (the stages not started or cancelled
with it), the settings the build ran with (its options as given, the file with every option's value, the builder and
its masters, the AMIWIND_ settings the failed stage read), the run's commit, the name of the full build report
(tools/build_report.py) and the command that builds again from this run. failure.json holds the same as data: the
Toolkit Monitor shows the failed stage and its error line under Progress, with a "See failure details" link to
FAILURE.md. The stage logs and the build's own output keep everything as before; the page is printed into the build's
output too, and the build's last line names it (last_line).

It reads the run's build-state.json, build-recipe.json, profile/fingerprints.json and the failed stages' logs (the last
BUILD_SCAN_BYTES of each, line by line) and writes only those two files; it never raises into the build (a page that
cannot be written is a warning). The Monitor's reader uses the same code read only (derive) for a failed run without
the files, a run of an earlier builder.

The page starts with the block the build also prints as its very last lines (tip_lines, BUILD-OOM-HELP-AND-TIP-68),
written for whoever ran the build: why it stopped (out of memory, out of disk, or the stage's own error), that the
finished work is kept, with the exact command that continues it (the same command, from the same folder), and what to
try for that cause.

  python3 tools/build_failure.py RUN [--print]       write the failure files of a failed run (again), print the page
  python3 tools/build_failure.py RUN --out DIR       write them into DIR instead: the run folder is only read
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import traceback
from pathlib import Path

SCHEMA = 'amiwind-build-failure-1'
MARKDOWN, RECORD = 'FAILURE.md', 'failure.json'
TAIL_LINES = 60                  # the last lines of the failed stage's log on the page
MAX_TRACEBACK_LINES = 200        # the newest lines of the traceback (with its chained parts)
MAX_ERROR_LINES = 20             # the newest error lines
MAX_LEFT_OUT = 200               # unit lines kept ("not converted: ..."); all of them are counted
MAX_LINE = 2000                  # characters kept of one log line
MAX_MESSAGE_LINES = 20           # lines of an exception's message after its type
BUILD_SCAN_BYTES = 256 << 20     # the builder reads at most the last 256 MiB of a failed stage's log
MONITOR_SCAN_BYTES = 16 << 20    # the Monitor's reader at most the last 16 MiB
MAX_STATE_BYTES = 64 << 20       # a build-state.json larger than this is not read
LOG_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,120}\.log$')   # as tools/monitor_read.py names stage logs
NUMBERED = re.compile(r'^([0-9]{1,3})-')
STAMP_PREFIX = re.compile(r'^\[\+[0-9hms.]{1,20}\] ')              # build_profile.stamp: "[+1h02m] "
# "Error: ...", the stage tools' exit line; "ERROR ...", "FATAL ..."; the stage wrapper's start failure
ERROR_LINE = re.compile(r'^(?:\[[^\]\s]{1,60}\] )?(?:Error|ERROR|FATAL|Fatal error|error)\b\s*[:!-]'
                        r'|^Cannot start stage command\b')
# the last line of a traceback: an exception's (qualified) name and its message
EXCEPTION_LINE = re.compile(r'^(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:Error|Exception|Exit|Interrupt|Refused)\b(?::|$)')
# a unit a stage refused or left out (tools/chim_room_batches.py "not converted: ROOM: reason", the libraries'
# "... left out: ...", the "REFUSED: ..." of the table tools)
LEFT_OUT_LINE = re.compile(r'not converted: |\bleft out: |\bREFUSED: ')
TRACEBACK_START = 'Traceback (most recent call last):'
CHAINED = ('During handling of the above exception, another exception occurred:',
           'The above exception was the direct cause of the following exception:')
# the full build report of a run (tools/build_report.py report_path): WORKSPACE/logs/BUILD-REPORT-<run>.txt, beside the
# build/ folder that holds the run
REPORT_FOLDER, REPORT_PREFIX, REPORT_SUFFIX = 'logs', 'BUILD-REPORT-', '.txt'
RECIPE = 'build-recipe.json'     # every option of the run with its value (tools/build.py --save-recipe)
MAX_STAGE_SETTINGS = 200         # AMIWIND_ settings shown per failed stage
MAX_SETTING = 300                # characters of one setting's value
# THE FAILURE'S KIND (BUILD-REPORT-MACHINE-ALL-OS-67): out of memory or out of disk, named at the top of FAILURE.md and
# of the build report (tools/build_report.py) when its marks are there, with what was found and what to do. A mark in a
# failed stage's error lines or traceback, or in the builder's own error, is the failure's; one only in the stage's last
# log lines is a hint. Proven: MemoryError, errno 28 or 122, or the memory controller's kill counter (cgroup
# memory.events oom_kill) risen between the build's start and the failure. Otherwise "likely, not proven" (a signal 9
# can come from elsewhere, and a read from a shared folder can end with errno 12 while memory is free), or "not proven"
# when the counter is there and did not rise. The counter and the free space of the workspace and the temp folder are
# read at the build's start (note_start, from tools/build_report.note_start) and at the failure, in the failing build;
# the Monitor's reader, later, judges the marks alone. Kept in this module, which the Monitor's Docker reader mounts.
MEMORY, DISK = 'OUT OF MEMORY', 'OUT OF DISK'
KILLED = (-9, 137)               # ended by signal 9 (SIGKILL): Python's -9, a shell's 128 + 9
# (kind, proves it, the pattern of a log or error line, what it says)
KIND_MARKS = (
    (MEMORY, True, re.compile(r'MemoryError\b'), 'MemoryError: Python could not get the memory it asked for'),
    (MEMORY, False, re.compile(r'BrokenProcessPool|A process in the process pool was terminated abruptly|'
                               r'A child process terminated abruptly'),
     'a worker process of a pool was ended while it ran, as the system ends one when memory runs out'),
    (MEMORY, False, re.compile(r'\[Errno 12\]|\bENOMEM\b|Cannot allocate memory'),
     'errno 12 (ENOMEM): memory could not be allocated (a read from a shared folder can also end so while memory '
     'is free)'),
    (MEMORY, False, re.compile(r'^Killed\s*$|\b\d+ Killed\b|\bSIGKILL\b|\bsignal 9\b'),
     'a process was ended by signal 9 (SIGKILL), as the system ends one when memory runs out'),
    (DISK, True, re.compile(r'\[Errno 28\]|No space left on device|\bENOSPC\b'),
     'errno 28 (ENOSPC): no space left on the device'),
    (DISK, True, re.compile(r'\[Errno 122\]|Disk quota exceeded|\bEDQUOT\b'), 'errno 122 (EDQUOT): the disk quota is used up'),
)
ERRNO_MARK = {12: 2, 28: 4, 122: 5}   # an OSError's errno: its mark in KIND_MARKS
KIND_ADVICE = {
    MEMORY: 'build again from this run with fewer workers (--jobs, about half of this run\'s) or with more memory for '
            'the build (a container\'s or virtual machine\'s memory limit); the stages and units it stored are taken again',
    DISK: 'free space in the workspace (python3 tools/build_gc.py plan WORKSPACE lists what can go) or build in another '
          'workspace with more room (--workspace); when the temp folder is the full one, point TMPDIR at a roomier folder; '
          'then build again from this run'}
CGROUP_EVENTS = ('/sys/fs/cgroup/memory.events', '/sys/fs/cgroup/memory/memory.oom_control')
_START = {}                      # the build's start: {'oom_kill': n or None, 'free': {place: bytes or None}}
# THE TIP (BUILD-OOM-HELP-AND-TIP-68): the block a failed build ends with, for whoever ran it rather than a developer:
# (1) why it stopped: out of memory, out of disk, or the stage's own error; (2) the finished work is kept: the same
# command again, from the same folder, ready to copy (continue_options); (3) what to try for that cause. Out of memory,
# the advice follows where the stage's memory was (stage_memory): in one large process (its main process, as a rule:
# fewer workers do not help; swap or more memory) or in its workers (about half the workers first). The stage's figures
# come from this build's own profile, else an earlier build of its workspace (cache/resource-history.jsonl), else the
# reference build's measured peaks (config/build-memory.json). The same block heads FAILURE.md and the build report.
TIP_RULE = '=' * 72
TIP_WIDTH = 100                  # the tip's text lines are wrapped here; command lines stay whole
HELP_SECTION = 'docs/LINUX_BUILD.md, "The build stopped or ran out of memory: what now?"'
MEMORY_SCHEMA = 'amiwind-build-memory-1'
MEMORY_REFERENCE = Path(__file__).resolve().parent.parent / 'config' / 'build-memory.json'
GIB = float(1 << 30)
ONE_PROCESS_SHARE = 0.5          # a stage whose largest process held this share of its peak or more: one process holds it
SWAP_HEADROOM_GIB = 2.0          # the swap advised: the reference build's peak plus this, less the memory the build had,
SWAP_STEP_GIB = 4                # rounded up to whole steps of this,
MIN_SWAP_GIB = 8                 # and never less than this
# The command that continues a failed build leaves out the run's own options (a run name is used once, the commit is the
# checkout's own) and those that would make the finished work again (--clean also refuses a workspace cache that is no
# longer empty); a --reuse-from names the failed run instead, which holds what the earlier run gave and what it finished.
CONTINUE_DROPS = ('--name', '--save-recipe', '--source-commit')
FROM_SCRATCH_OPTIONS = ('--clean', '--no-reuse', '--release-from-scratch')
JOB_OPTIONS = ('-j', '--jobs', '--j', '--single-thread')
DOCKER_RUNTIME = 'docker-builder'   # tools/build_report.py RUNTIMES: the build ran in our Docker builder (tools/run_docker.py)


def _clean(raw):
    return raw.decode('utf-8', 'replace').rstrip('\r\n')[:MAX_LINE]


def scan_log(path, max_bytes=BUILD_SCAN_BYTES, tail_lines=TAIL_LINES):
    """What a failed stage's log PATH says: {'size', 'scanned_from', 'tail', 'error_lines', 'traceback', 'left_out',
    'left_out_count'}. Lines without their line ends, each cut at MAX_LINE characters; at most the last MAX_BYTES of
    the log are read, one line at a time. The traceback is the last one in the log with the tracebacks it is chained
    to ("During handling of the above exception ..."), its frames and its exception's message."""
    size = path.stat().st_size
    start = max(0, size - max_bytes) if max_bytes else 0
    tail = deque(maxlen=tail_lines)
    errors = deque(maxlen=MAX_ERROR_LINES)
    left, left_count = [], 0
    block, last, state = None, [], 'out'      # the traceback being read, the last complete one
    message = 0                                # lines of the exception's message read so far
    chained = None                             # a chain line right after the last traceback
    with open(path, 'rb') as f:
        if start:
            f.seek(start)
            f.readline()                       # the first line of a cut log is partial
        for raw in f:
            line = _clean(raw)
            tail.append(line)
            text = STAMP_PREFIX.sub('', line)
            if LEFT_OUT_LINE.search(text):
                left_count += 1
                if len(left) < MAX_LEFT_OUT:
                    left.append(line)
            if state != 'out' and text.startswith(TRACEBACK_START):
                last, state = block, 'out'       # a new traceback right after one: the first one is complete
            if state == 'frames':
                if text.startswith(' ') or not text:
                    block.append(line)
                    continue
                block.append(line)               # the exception's name and the start of its message
                if EXCEPTION_LINE.match(text):
                    errors.append(line)
                state, message = 'message', 0
                continue
            if state == 'message':
                if text and message < MAX_MESSAGE_LINES and not text.startswith(CHAINED) \
                        and not ERROR_LINE.match(text) and not text.startswith('['):
                    block.append(line)
                    message += 1
                    continue
                last, state, chained = block, 'out', None
            if text.startswith(TRACEBACK_START):
                block = (last + ['', chained, ''] if chained and last else []) + [line]
                state, chained = 'frames', None
                continue
            if text.startswith(CHAINED) and last:
                chained = text
                continue
            if text:
                chained = None
            if ERROR_LINE.match(text):
                errors.append(line)
    if state != 'out':
        last = block
    return {'size': size, 'scanned_from': start, 'tail': list(tail), 'error_lines': list(errors),
            'traceback': (last or [])[-MAX_TRACEBACK_LINES:], 'left_out': left, 'left_out_count': left_count}


def headline(row):
    """The one error line of a failed stage: its last error line, else its traceback's exception, else its last
    non-empty log line."""
    for line in reversed(row.get('error_lines') or []):
        return STAMP_PREFIX.sub('', line).strip()
    exception = [line for line in row.get('traceback') or [] if line and not line.startswith(' ')
                 and not line.startswith(TRACEBACK_START) and not line.startswith(CHAINED)]
    if exception:
        return exception[-1].strip()
    for line in reversed(row.get('tail') or []):
        if line.strip():
            return STAMP_PREFIX.sub('', line).strip()
    return ''


# Options of the failed run that the next run gets anew: its name, its reuse source, the recipe file it saved into the
# failed run's folder and the commit it was built from (the fix is a new commit; the checkout's own is used)
PER_RUN_OPTIONS = ('--name', '--reuse-from', '--save-recipe', '--source-commit')


def resume_command(argv, run_path):
    """The command that builds again from RUN_PATH: the build's own options without PER_RUN_OPTIONS (a new run name
    is chosen) and with --reuse-from RUN_PATH, so the stages this run finished are reused."""
    out, skip = [], False
    for part in argv or []:
        if skip:
            skip = False
            continue
        if part in PER_RUN_OPTIONS:
            skip = True
            continue
        if part.startswith(tuple(option + '=' for option in PER_RUN_OPTIONS)):
            continue
        out.append(part)
    return 'python3 tools/build.py ' + shlex.join(out + ['--reuse-from', str(run_path)])


def _stamp():
    now = datetime.now(timezone.utc)
    local = now.astimezone()
    return local.strftime('%Y-%m-%d %H:%M %z') + ' / ' + now.strftime('%Y-%m-%d %H:%M UTC')


def _load_state(path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
            return {}
        state = json.loads(path.read_bytes().decode('utf-8'))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def full_report(run):
    """The full build report of the run folder RUN (tools/build_report.py), or None when there is none."""
    run = Path(run)
    path = run.parent.parent / REPORT_FOLDER / (REPORT_PREFIX + run.name + REPORT_SUFFIX)
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def settings(state, where, failed):
    """The settings the build ran with, from the run's own files (read only, never raises): its options as given
    (build-state.json build_argv), the file with every option's value (build-recipe.json), the builder and its CHIM
    areas, the masters in load order, the data folder, and for each stage named in FAILED the AMIWIND_ settings it read
    that were set (its key's environment in profile/fingerprints.json)."""
    out = {'command_line': None, 'recipe': None, 'builder': None, 'masters': [], 'data_files': None, 'stages': {}}
    argv = state.get('build_argv')
    if isinstance(argv, list):
        out['command_line'] = [str(part) for part in argv]
    try:
        if where(RECIPE).is_file():
            out['recipe'] = RECIPE
    except (OSError, ValueError):
        pass
    options = state.get('builder_options') if isinstance(state.get('builder_options'), dict) else {}
    builder = options.get('builder') or (state.get('builder') if isinstance(state.get('builder'), str) else None)
    if builder:
        areas = options.get('chim_areas')
        out['builder'] = str(builder) + (' (CHIM areas: %s)' % ', '.join(str(a) for a in areas)
                                         if isinstance(areas, list) and areas else '')
    layers = state.get('expansion_layers') if isinstance(state.get('expansion_layers'), dict) else {}
    if isinstance(layers.get('masters'), list):
        out['masters'] = [str(name) for name in layers['masters']]
    data = state.get('data_files')
    if isinstance(data, str) and data:
        out['data_files'] = data
    if failed:
        try:
            fingerprints = _load_state(where('profile', 'fingerprints.json'))
        except (OSError, ValueError):
            fingerprints = {}
        for name in failed:
            row = fingerprints.get(name)
            environment = row.get('environment') if isinstance(row, dict) else None
            if isinstance(environment, dict):
                set_ones = [(str(key), str(value)[:MAX_SETTING]) for key, value in sorted(environment.items(), key=lambda kv: str(kv[0]))
                            if value is not None]
                out['stages'][name] = dict(set_ones[:MAX_STAGE_SETTINGS])
    return out


def record(run, error=None, scan_bytes=BUILD_SCAN_BYTES, path=None):
    """The failure record of the build run folder RUN, from its build-state.json and its failed stages' logs; ERROR:
    the builder's own exception (its message, and its traceback when no stage failed). PATH(*parts) gives the file
    of the run to read (the Monitor's reader passes its checked one). Read only."""
    run = Path(run)
    where = path or (lambda *parts: run.joinpath(*parts))
    state = _load_state(where('build-state.json'))
    steps = [s for s in state.get('steps') or [] if isinstance(s, dict)]
    stages, run_path = [], None
    for step in steps:
        logged = str(step.get('log') or '')
        if run_path is None and logged.startswith('/') and Path(logged).parent.name == 'logs':
            run_path = str(Path(logged).parent.parent)       # the run as the builder named it
        if step.get('status') != 'failed':
            continue
        name = Path(logged).name if logged else ''
        number = NUMBERED.match(name)
        row = {'name': str(step.get('name') or '?'), 'number': int(number.group(1)) if number else None,
               'returncode': _int(step.get('returncode')), 'elapsed_seconds': step.get('elapsed_seconds'),
               'jobs': _int(step.get('jobs')), 'log': 'logs/' + name if LOG_NAME.match(name) else None,
               'size': None, 'scanned_from': None, 'tail': [], 'error_lines': [], 'traceback': [], 'left_out': [],
               'left_out_count': 0}
        if row['log']:
            try:
                log = where('logs', name)
                if log.is_file():
                    row.update(scan_log(log, scan_bytes))
            except (OSError, ValueError) as exc:
                row['log_error'] = '%s: %s' % (type(exc).__name__, exc)
        row['error'] = headline(row)
        stages.append(row)
    named = state.get('run_name') if isinstance(state.get('run_name'), dict) else {}
    out = {'schema': SCHEMA, 'run': run.name, 'status': state.get('status') or 'failed', 'written_at': _stamp(),
           'commit': named.get('commit'), 'version': named.get('version') or state.get('runtime_version'),
           'failed_stages': stages, 'stages_recorded': len(steps), 'jobs': _int(state.get('compiler_jobs')),
           'cancelled_stages': [str(s.get('name')) for s in steps if s.get('status') == 'cancelled'],
           'not_started': [str(n) for n in state.get('not_started') or []],
           'settings': settings(state, where, [row['name'] for row in stages]),
           'resume': {'command': resume_command(state.get('build_argv') or [], run_path or str(run)),
                      'from_options': bool(state.get('build_argv'))}}
    if error is not None:
        builder = {'type': type(error).__name__, 'message': str(error)[:4000]}
        if not stages:
            builder['traceback'] = [line.rstrip('\n') for part in traceback.format_exception(
                type(error), error, error.__traceback__) for line in part.splitlines()][-MAX_TRACEBACK_LINES:]
        out['builder_error'] = builder
    first = stages[0] if stages else None
    if first:
        out['stage'] = first['name']
        out['error'] = first['error'] or 'the stage ended with exit %s' % first['returncode']
    elif error is not None:
        out['stage'] = None
        out['error'] = ('%s: %s' % (type(error).__name__, str(error).strip().splitlines()[0] if str(error).strip()
                                    else '')).strip()
    else:
        out['stage'] = None
        out['error'] = 'no failed stage is recorded in build-state.json'
    try:
        out['kinds'] = kinds(out, error)          # the marks alone; write() judges again in the failing build
    except Exception:  # noqa: BLE001 - the kind never hides the failure
        out['kinds'] = []
    return out


def _seconds(value):
    if not isinstance(value, (int, float)):
        return '-'
    value = int(round(value))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    return ('%d h %d min' % (hours, minutes)) if hours else ('%d min %d s' % (minutes, seconds)) if minutes else \
        '%d s' % seconds


def _size(value):
    if not isinstance(value, int):
        return 'not found'
    return '%.1f MB' % (value / 1048576) if value >= 1048576 else '%d KB' % (value // 1024) if value >= 1024 \
        else '%d bytes' % value


def _block(lines):
    """A fenced text block (a fence inside the text is broken up so the block stays whole)."""
    return ['```text'] + [line.replace('```', '` ` `') for line in lines] + ['```']


def _names(names, most=40):
    return ', '.join(names[:most]) + (', ...' if len(names) > most else '')


def _read_text(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def oom_kills(read=None):
    """The memory controller's kill counter of this process's control group (cgroup v2 memory.events, v1
    memory.oom_control: the oom_kill line), or None where there is none. READ(path) stands in for the files in tests."""
    read = read or _read_text
    places = []
    for row in (read('/proc/self/cgroup') or '').splitlines():
        if row.startswith('0::/') and row.strip() != '0::/':
            places.append('/sys/fs/cgroup' + row[3:].strip() + '/memory.events')
    for path in places + list(CGROUP_EVENTS):
        for row in (read(path) or '').splitlines():
            key, _, value = row.strip().partition(' ')
            if key == 'oom_kill' and value.strip().isdigit():
                return int(value.strip())
    return None


def free_space(workspace=None):
    """{'workspace': bytes, 'temp folder': bytes} free now (None where not read; no workspace without one)."""
    import shutil
    import tempfile
    out = {}
    for name, folder in (('workspace', workspace), ('temp folder', tempfile.gettempdir())):
        if folder is None:
            continue
        try:
            folder = Path(folder)
            while not folder.exists() and folder.parent != folder:
                folder = folder.parent
            out[name] = shutil.disk_usage(folder).free
        except OSError:
            out[name] = None
    return out


def note_start(workspace=None, read=None):
    """The build's start, for its failure's kind: the memory controller's kill counter and the free space."""
    _START.clear()
    _START.update(oom_kill=oom_kills(read), free=free_space(workspace))


def note_workspace(workspace):
    """The workspace's free space at the start, once the builder knows its workspace."""
    _START.setdefault('free', {})['workspace'] = free_space(workspace).get('workspace')


def _free(value):
    if not isinstance(value, int):
        return 'not read'
    return '%.1f GiB' % (value / (1 << 30)) if value >= 1 << 30 else _size(value)


def _causes(error):
    seen = []
    while isinstance(error, BaseException) and all(error is not e for e in seen) and len(seen) < 10:
        seen.append(error)
        error = error.__cause__ or error.__context__
    return seen


def kinds(rec, error=None, live=False, workspace=None, read=None):
    """The kinds of a failure record's failure whose marks are there: [{'kind', 'proof', 'marks', 'found', 'advice'}],
    [] when none. ERROR: the builder's exception (and the errors it was raised from). LIVE: called in the build that
    failed, so the kill counter and the free space now are compared with the build's start; otherwise the marks alone."""
    found = {}

    def mark(kind, strong, what):
        row = found.setdefault(kind, {'strong': False, 'marks': []})
        row['strong'] = row['strong'] or strong
        if what not in row['marks'] and what + ' (in the last log lines)' not in row['marks']:
            row['marks'].append(what)

    def scan(lines, primary):
        for line in lines:
            text = STAMP_PREFIX.sub('', str(line)).strip()
            for kind, strong, pattern, what in KIND_MARKS:
                if pattern.search(text) and (primary or what not in (found.get(kind) or {}).get('marks', ())):
                    mark(kind, strong and primary, what if primary else what + ' (in the last log lines)')
    stages = rec.get('failed_stages') or []
    for stage in stages:
        if stage.get('returncode') in KILLED:
            mark(MEMORY, False, 'the stage %s was ended by signal 9 (exit %s)' % (stage.get('name'), stage['returncode']))
        scan(list(stage.get('error_lines') or []) + list(stage.get('traceback') or []), True)
    builder = rec.get('builder_error') or {}
    if builder:
        scan(['%s: %s' % (builder.get('type'), builder.get('message'))] + list(builder.get('traceback') or []), True)
    for cause in _causes(error):
        if isinstance(cause, MemoryError):
            mark(*KIND_MARKS[0][:2], KIND_MARKS[0][3])
        elif isinstance(cause, OSError) and cause.errno in ERRNO_MARK:
            kind, strong, _, what = KIND_MARKS[ERRNO_MARK[cause.errno]]
            mark(kind, strong, what)
        elif type(cause).__name__ == 'BrokenProcessPool':
            mark(KIND_MARKS[1][0], KIND_MARKS[1][1], KIND_MARKS[1][3])
    for stage in stages:
        scan(stage.get('tail') or [], False)
    out = []
    for kind in (MEMORY, DISK):
        row = found.get(kind)
        if row is None:
            continue
        proof, evidence = ('proven' if row['strong'] else 'likely, not proven'), []
        if live and kind == MEMORY:
            before, now = _START.get('oom_kill'), oom_kills(read)
            if before is not None and now is not None and now > before:
                proof = 'proven'
                evidence.append('the memory controller ended %d process%s for memory during the build (cgroup '
                                'oom_kill %d -> %d)' % (now - before, '' if now - before == 1 else 'es', before, now))
            elif before is not None and now is not None and not row['strong']:
                proof = 'not proven'
                evidence.append('the memory controller\'s kill counter stayed at %d (cgroup oom_kill): it ended no '
                                'process of this build\'s group for memory' % now)
            elif now is None:
                evidence.append('no memory controller kill counter here (cgroup memory.events) to prove it')
        if live and kind == DISK:
            start = _START.get('free') or {}
            evidence.append('free space at the start and now: ' + '; '.join(
                '%s %s, now %s' % (place, _free(start.get(place)), _free(value))
                for place, value in free_space(workspace).items()))
        out.append({'kind': kind, 'proof': proof, 'marks': row['marks'], 'found': evidence,
                    'advice': KIND_ADVICE[kind]})
    return out


def kind_lines(found, markdown=False):
    """The lines that name a failure's kinds, at the top of FAILURE.md (MARKDOWN) or of the build report."""
    lines = []
    for row in found or []:
        head = '%s (%s): %s' % (row['kind'], row['proof'], '; '.join(row.get('marks') or []))
        if markdown:
            lines.append('- **Kind:** ' + head)
            lines += ['- **Found:** ' + text for text in row.get('found') or []]
            lines.append('- **What to do:** ' + row['advice'])
        else:
            lines.append('Kind: ' + head)
            lines += ['  Found: ' + text for text in row.get('found') or []]
            lines.append('  What to do: ' + row['advice'])
    return lines


def _split_option(part):
    """(option, its value when written into the same word, else None): --name=X, -j4 and -j=4 carry their value."""
    if part.startswith('--') and '=' in part:
        option, _, value = part.partition('=')
        return option, value
    if part.startswith('-j') and not part.startswith('--') and len(part) > 2:
        return '-j', part[2:].lstrip('=')
    return part, None


def continue_options(argv, run_path=None, jobs=None):
    """(options, notes): ARGV, the failed build's own options, as the command that continues it from the same folder.
    Left out: the run's own options (CONTINUE_DROPS: a new run name is chosen by itself) and FROM_SCRATCH_OPTIONS, each
    said in NOTES; a --reuse-from names RUN_PATH, the failed run, instead (it holds what the earlier run gave and what it
    finished). Without a reuse option the builder's default (v0.0.67 and later) takes every finished stage of the build
    folder back, and every finished unit comes from its cache either way. JOBS: -j JOBS in place of the build's own
    worker option."""
    out, notes, skip = [], [], False
    for part in [str(item) for item in argv or []]:
        if skip:
            skip = False
            continue
        option, attached = _split_option(part)
        if option in CONTINUE_DROPS:
            skip = attached is None
            if option == '--name':
                note = '--name is left out: a run name is used once (add --name NEW to choose one)'
                if note not in notes:
                    notes.append(note)
            continue
        if option == '--reuse-from' and run_path is not None:
            skip = attached is None
            out += ['--reuse-from', str(run_path)]
            continue
        if option in FROM_SCRATCH_OPTIONS:
            notes.append('%s is left out: it would make the finished work again (build from scratch only on purpose, in '
                         'a new build folder)' % option)
            continue
        if jobs is not None and option in JOB_OPTIONS:
            skip = attached is None and option != '--single-thread'
            continue
        out.append(part)
    if jobs is not None:
        out += ['-j', str(jobs)]
    return out, notes


def command_line(options, system=None):
    """The build command with OPTIONS as the player types it: ./build.sh on Linux and macOS, .\\build.cmd on Windows
    (both start tools/build.py with the same options)."""
    if (system or platform.system()) == 'Windows':
        return ('.\\build.cmd ' + subprocess.list2cmdline(list(options))).rstrip()
    return ('./build.sh ' + shlex.join(list(options))).rstrip()


def _gib(value):
    return '%.1f GiB' % (value / GIB)


def reference_memory(path=None):
    """The reference build's measured stage peaks (config/build-memory.json), {} when it cannot be read."""
    doc = _load_state(Path(path) if path else MEMORY_REFERENCE)
    return doc if doc.get('schema') == MEMORY_SCHEMA else {}


def _history_row(workspace, stage):
    """(peak, largest, workers) bytes of STAGE's newest full-build row in the workspace's resource history
    (WORKSPACE/cache/resource-history.jsonl, tools/resource_plan.py), or None."""
    path = Path(workspace) / 'cache' / 'resource-history.jsonl'
    try:
        if not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
            return None
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except ValueError:
            continue
        measured = item.get('measured') if isinstance(item, dict) else None
        if item.get('stage') != stage or not isinstance(measured, dict) or item.get('scope') == 'miniwind':
            continue
        total, largest = measured.get('total_mib'), measured.get('largest_mib')
        if isinstance(total, (int, float)) and total > 0:
            largest = largest if isinstance(largest, (int, float)) else total
            return int(total * (1 << 20)), int(largest * (1 << 20)), _int(measured.get('jobs'))
    return None


def stage_memory(run, stage, workspace=None, reference=None):
    """Where the memory of STAGE was: {'stage', 'peak', 'largest', 'workers', 'source', 'one_process'} (bytes; workers:
    the most it ran), from this build's own profile (RUN/build-profile.json), else the workspace's earlier builds, else
    the reference build (config/build-memory.json); None when none of them measured it. one_process: its largest single
    process (its main process, as a rule) held ONE_PROCESS_SHARE of its peak or more, or it ran one worker, so fewer
    workers would not free its memory."""
    found = None
    if run is not None:
        for row in _load_state(Path(run) / 'build-profile.json').get('stages') or []:
            if isinstance(row, dict) and row.get('name') == stage and not row.get('reused'):
                peak, largest = _int(row.get('peak_tree_rss_bytes')), _int(row.get('peak_process_rss_bytes'))
                if peak or largest:
                    found = (peak, largest, _int(row.get('jobs_max')) or _int(row.get('jobs')), 'measured in this build')
                break
    if found is None and workspace is not None:
        row = _history_row(workspace, stage)
        if row:
            found = row + ('measured in an earlier build of this build folder',)
    if found is None:
        reference = reference_memory() if reference is None else reference
        row = (reference.get('stages') or {}).get(stage)
        if isinstance(row, dict) and (_int(row.get('peak_bytes')) or _int(row.get('largest_process_bytes'))):
            found = (_int(row.get('peak_bytes')), _int(row.get('largest_process_bytes')), _int(row.get('workers')),
                     'measured in %s' % (reference.get('measured_in_short') or 'the reference build'))
    if found is None:
        return None
    peak, largest, workers, source = found
    peak = max(peak or 0, largest or 0)
    largest = largest or peak
    return {'stage': stage, 'peak': peak, 'largest': largest, 'workers': workers, 'source': source,
            'one_process': (workers or 1) <= 1 or largest >= ONE_PROCESS_SHARE * peak}


def build_memory_seen(run):
    """{'limit', 'source', 'peak', 'peak_stages'} of the memory the build saw (bytes; source: 'the container\'s limit'
    or 'the machine') and its peak so far, the file cache not counted (RUN/build-progress.json); {} when not recorded."""
    memory = _load_state(Path(run) / 'build-progress.json').get('memory') if run is not None else None
    if not isinstance(memory, dict) or not isinstance(memory.get('limit_gib'), (int, float)):
        return {}
    peak = memory.get('peak_gib')
    return {'limit': int(memory['limit_gib'] * GIB),
            'source': 'the container\'s limit' if memory.get('source') == 'container' else 'the machine',
            'peak': int(peak * GIB) if isinstance(peak, (int, float)) else None,
            'peak_stages': [str(name) for name in memory.get('peak_stages') or []]}


def swap_now():
    """(total, free, how) of the swap now (tools/build_report.py swap), or None where it cannot be read."""
    try:
        import build_report
        total, free, how = build_report.swap()
    except Exception:  # noqa: BLE001 - the tip never stops on a reader
        return None
    return (total, free, how) if total is not None else None


def advised_swap_gib(limit, reference):
    """The swap to add, in GiB: the reference build's peak plus SWAP_HEADROOM_GIB less the memory LIMIT the build had,
    rounded up to whole SWAP_STEP_GIB, at least MIN_SWAP_GIB."""
    peak = _int((reference or {}).get('build_peak_bytes'))
    if not peak or not limit:
        return MIN_SWAP_GIB
    need = peak / GIB + SWAP_HEADROOM_GIB - limit / GIB
    steps = -(-max(0.0, need) // SWAP_STEP_GIB)
    return max(MIN_SWAP_GIB, int(steps * SWAP_STEP_GIB))


def _one_line(text, most=400):
    text = ' '.join(str(text).split())
    return text if len(text) <= most else text[:most] + ' ...'


def _para(text, first='  ', rest=None):
    """TEXT wrapped at TIP_WIDTH for a terminal, each line starting with FIRST (then REST); words are never broken, so
    a path or a command stays whole."""
    import textwrap
    return textwrap.wrap(text, width=TIP_WIDTH, initial_indent=first, subsequent_indent=first if rest is None else rest,
                         break_long_words=False, break_on_hyphens=False) or [first.rstrip()]


def _bullet(text):
    return _para(text, '  - ', '    ')


def _report_of(run, report):
    if report is not None:
        return Path(report)
    if run is not None:
        run = Path(run)
        return run.parent.parent / REPORT_FOLDER / (REPORT_PREFIX + run.name + REPORT_SUFFIX)
    return None


def tip_lines(rec, run=None, workspace=None, argv=None, live=False, system=None, environ=None, reference=None,
              report=None, files=True):
    """The block a failed build ends with (THE TIP above): plain lines for whoever ran the build. REC: the failure
    record (record(), or bare_record() for a stop before the run folder); RUN: the run folder; ARGV: the build's own
    options (default: the record's); LIVE: in the failing build, so the swap is read now; REPORT: the build report's
    path (default: the run's); FILES: False reads no file of the run or the workspace (the Monitor's reader, which reads
    a run only through its checked paths). Never raises."""
    try:
        return _tip_lines(rec, run, workspace, argv, live, system, os.environ if environ is None else environ,
                          reference_memory() if reference is None else reference, report, files)
    except Exception as exc:  # noqa: BLE001 - the tip never hides the failure
        return [TIP_RULE, 'The build stopped; the advice could not be written (%s). Run the same command again from '
                          'the same folder: the finished work is kept.' % type(exc).__name__, TIP_RULE]


def _tip_lines(rec, run, workspace, argv, live, system, environ, reference, report, files):
    run = Path(run) if run is not None else None
    if workspace is None and run is not None:
        workspace = run.parent.parent
    readable = run if files else None             # the run's own files, read for the memory figures
    stages = rec.get('failed_stages') or []
    first = stages[0] if stages else {}
    stage = rec.get('stage')
    kind = next(iter(rec.get('kinds') or []), None)
    if argv is None:
        argv = (rec.get('settings') or {}).get('command_line') or []
    elapsed = first.get('elapsed_seconds')
    if stage:
        where = ' in the stage %s%s' % (stage, ', after %s' % _seconds(elapsed) if isinstance(elapsed, (int, float))
                                         else '')
    else:
        where = ' before its first stage' if not rec.get('stages_recorded') else ' outside its stages'
    L = [TIP_RULE]
    if kind:
        L.append('THE BUILD STOPPED%s: %s (%s).' % (where, kind['kind'], kind['proof']))
    else:
        L += ['THE BUILD STOPPED%s, on its own error:' % where] + _para(_one_line(rec.get('error') or 'not recorded'))
    memory = (stage_memory(readable, stage, workspace if files else None, reference)
              if kind and kind['kind'] == MEMORY and stage else None)
    seen = build_memory_seen(readable) if readable is not None and kind and kind['kind'] == MEMORY else {}
    swap = swap_now() if live and kind and kind['kind'] == MEMORY else None
    if memory and memory['one_process']:
        L += _para('The stage reached %s; one process of it (its main process, as a rule) held %s of that (%s).' % (
            _gib(memory['peak']), _gib(memory['largest']), memory['source']))
    elif memory:
        L += _para('The stage reached %s, most of it in its workers (its largest process: %s; %s).' % (
            _gib(memory['peak']), _gib(memory['largest']), memory['source']))
    if seen or swap:
        parts = []
        if seen:
            parts.append('%s of memory (%s)' % (_gib(seen['limit']), seen['source']))
        if swap:
            parts.append('no swap' if not swap[0] else '%s of swap' % _gib(swap[0]))
        text = 'This build had ' + ' and '.join(parts)
        if seen.get('peak'):
            text += '; its peak: %s%s' % (_gib(seen['peak']), ', with %s running' % ', '.join(seen['peak_stages'])
                                         if seen.get('peak_stages') else '')
        L += _para(text + '.')
    # (2) the finished work is kept: the same command, ready to copy
    options, notes = continue_options(argv, run)
    if stages or rec.get('stages_recorded'):
        L += ['', 'Your finished work is kept: do not delete the build folder. Run the same command again,',
              'from the same folder; every stage and unit that finished is taken back (each checked by SHA-256):']
    else:
        L += ['', 'Nothing of this build was made yet; earlier builds in the build folder are kept and taken back.',
              'Fix what the error names, then run the command again, from the same folder:']
    L += ['', '  ' + command_line(options, system)]
    for note in notes:
        L += _para('(%s)' % note)
    if environ.get('AW_RUNTIME') == DOCKER_RUNTIME:
        L += _para('(This build ran in the AmiWind Docker builder: run the same docker builder command again with a '
                   'new --name; it builds in the same volume and takes the finished work back.)')
    L.append('')
    # (3) what to try for that cause
    L.append('Before you run it again:')
    budget = rec.get('jobs') or _int(first.get('jobs')) or (memory or {}).get('workers')
    more = ('give the build more memory (the memory limit of its container or virtual machine: Docker --memory and '
            '--memory-swap, WSL 2 memory= and swap= in .wslconfig), or close other programs')
    if kind and kind['kind'] == MEMORY:
        swap_gib = advised_swap_gib(seen.get('limit'), reference)
        if memory and memory['one_process'] or not budget or budget <= 1:
            if memory and memory['one_process']:
                L += _bullet('Fewer workers (-j) do not help in this stage: one process holds most of its memory.')
            L += _bullet('Add swap (about %d GiB or more), or %s.' % (swap_gib, more))
        else:
            half = max(1, budget // 2)
            L += _bullet('Use about half the workers (this build had %d): the same command with -j %d:' % (budget, half))
            L.append('      ' + command_line(continue_options(argv, run, jobs=half)[0], system))
            if memory is None:
                L += _bullet('If one process of the stage holds the memory, fewer workers do not help: add swap (about '
                             '%d GiB or more), or %s.' % (swap_gib, more))
            else:
                L += _bullet('If it stops again: add swap (about %d GiB or more), or %s.' % (swap_gib, more))
        L += _bullet('./build.sh --resource-plan with the same options lists what each stage needs against what the '
                     'build gets.')
    elif kind and kind['kind'] == DISK:
        L += _bullet('Free space on the disk of the build folder: python3 tools/build_gc.py plan %s lists what can go '
                     'and deletes nothing (--delete removes exactly what it lists as expired).'
                     % (workspace if workspace is not None else 'WORKSPACE'))
        L += _bullet('When the temp folder is the full one, point TMPDIR at a folder with room.')
        L += _bullet('A --workspace on a roomier disk starts that folder empty: free space here first if you can.')
    elif stages:
        L += _bullet('Fix what the error line names (the failure page has its traceback and the stage\'s last log '
                     'lines).')
        L += _bullet('If it stops the same way again, send the build report when you ask for help.')
    else:
        L += _bullet('Fix what the error line names (the build report below has the details).')
        L += _bullet('If it stops the same way again, send the build report when you ask for help.')
    found = _report_of(run, report)
    if found is not None:
        L.append('Build report (the one file to send when you ask for help): %s' % found)
    L += ['Help: ' + HELP_SECTION, TIP_RULE]
    return L


def tip_text(rec, **options):
    return '\n'.join(tip_lines(rec, **options))


def bare_record(error=None, argv=None):
    """The failure record of a build that stopped before it made its run folder: its error and kind only."""
    message = (str(error.code if error.code is not None else '') if isinstance(error, SystemExit)
               else '%s: %s' % (type(error).__name__, str(error).strip())) if error is not None else 'not recorded'
    rec = {'error': message.strip().splitlines()[0] if message.strip() else 'not recorded', 'stage': None,
           'failed_stages': [], 'stages_recorded': 0,
           'settings': {'command_line': [str(part) for part in argv or []]}}
    if error is not None and not isinstance(error, SystemExit):
        rec['builder_error'] = {'type': type(error).__name__, 'message': str(error)[:4000]}
    try:
        rec['kinds'] = kinds(rec, error, live=True)
    except Exception:  # noqa: BLE001 - the kind never hides the failure
        rec['kinds'] = []
    return rec


def not_completed(rec):
    """What the failed build did not complete: the stages not started and those cancelled with it, and the units the
    failed stages refused or left out."""
    parts = []
    if rec.get('not_started'):
        n = len(rec['not_started'])
        parts.append('%d stage%s not started: %s' % (n, '' if n == 1 else 's', _names(rec['not_started'])))
    if rec.get('cancelled_stages'):
        parts.append('cancelled with it: ' + _names(rec['cancelled_stages']))
    left = sum(s.get('left_out_count') or 0 for s in rec.get('failed_stages') or [])
    if left:
        parts.append('%d unit%s refused or left out (listed below)' % (left, '' if left == 1 else 's'))
    if parts:
        return '; '.join(parts)
    if not rec.get('stages_recorded') and not rec.get('failed_stages'):
        return 'the whole build: it stopped before its stages ran'
    return 'no other stage was stopped or left to run'


def render_settings(found, report=None):
    """The "Build settings" part of FAILURE.md (settings())."""
    found = found or {}
    L = ['', '## Build settings', '']
    if found.get('command_line') is not None:
        L += ['The options as given:', ''] + _block(['tools/build.py ' + shlex.join(found['command_line'])])
    else:
        L.append('_This run did not record its options._')
    facts = []
    if found.get('recipe'):
        facts.append('- **Every option with its value:** %s in the run folder' % found['recipe'])
    if found.get('builder'):
        facts.append('- **Builder:** ' + found['builder'])
    if found.get('masters'):
        facts.append('- **Masters, in load order:** ' + ', '.join(found['masters']))
    if found.get('data_files'):
        facts.append('- **Game data:** ' + found['data_files'])
    if report:
        facts.append('- **Everything else** (the versions, the game data copies by SHA-256, the machine, the stage '
                     'plan, the reuse state): ' + str(report))
    if facts:
        L += [''] + facts
    for name, values in (found.get('stages') or {}).items():
        L += ['', 'The AMIWIND_ settings the stage %s read, those set (its key, profile/fingerprints.json):' % name, '']
        L += _block(['%s=%s' % pair for pair in values.items()]) if values else ['_None of them was set._']
    return L


def render(rec):
    """FAILURE.md of a failure record: plain text that reads as Markdown too."""
    stages = rec.get('failed_stages') or []
    L = ['# Build failure: %s' % rec.get('run'), '',
         '_Written by the builder when the build failed (tools/build_failure.py). The stage logs and the build\'s '
         'own output keep everything; this is the short form._', '']
    tip = [line for line in rec.get('tip') or [] if line != TIP_RULE]
    if tip:
        # the block the build printed as its last lines (BUILD-OOM-HELP-AND-TIP-68): what happened and what to do now
        L += ['## What to do now', ''] + _block(tip) + ['']
    L += kind_lines(rec.get('kinds'), markdown=True)       # out of memory, out of disk: first, when their marks are there
    if stages:
        for s in stages:
            L.append('- **Failed stage:** %s (stage %s, exit %s, after %s, %s worker%s)' % (
                s['name'], s['number'] if s['number'] is not None else '?',
                s['returncode'] if s['returncode'] is not None else 'not recorded', _seconds(s.get('elapsed_seconds')),
                s['jobs'] if s['jobs'] is not None else '?', '' if s.get('jobs') == 1 else 's'))
    else:
        L.append('- **Failed:** the build itself, outside its stages')
    L.append('- **Error:** %s' % (rec.get('error') or '-'))
    L.append('- **Commit:** %s, version %s' % (rec.get('commit') or 'not recorded', rec.get('version') or 'not recorded'))
    L.append('- **Not completed:** ' + not_completed(rec))
    if rec.get('report'):
        L.append('- **Full report:** %s (every option, the versions, the game data copies, the machine, the stage plan, '
                 'the reuse state)' % rec['report'])
    L.append('- **Written:** %s' % rec.get('written_at'))
    for s in stages:
        title = '' if len(stages) == 1 else ' (%s)' % s['name']
        log = s.get('log') or 'its log'
        L += ['', '## Error lines%s' % title, '']
        L += _block(s['error_lines']) if s.get('error_lines') else ['_No error line in %s._' % log]
        L += ['', '## Traceback%s' % title, '']
        L += _block(s['traceback']) if s.get('traceback') else [
            '_No traceback in %s: the stage printed none (an error it reported itself, or a tool that is not '
            'Python)._' % log]
        if s.get('left_out_count'):
            L += ['', '## Units refused or left out%s: %d' % (title, s['left_out_count']), '']
            L += _block(s['left_out'] + (['... %d more in %s' % (s['left_out_count'] - len(s['left_out']), log)]
                                         if s['left_out_count'] > len(s['left_out']) else []))
        L += ['', '## The last %d lines of %s (%s)' % (len(s.get('tail') or []), log, _size(s.get('size'))), '']
        if s.get('log_error'):
            L.append('_The log could not be read: %s._' % s['log_error'])
        L += _block(s['tail']) if s.get('tail') else ['_The log is empty or missing._']
    builder = rec.get('builder_error')
    if builder:
        L += ['', '## The builder\'s error', '']
        L += _block(builder.get('traceback') or ['%s: %s' % (builder['type'], builder['message'])])
    L += render_settings(rec.get('settings'), rec.get('report'))
    L += ['', '## Build again from this run', '',
          'Fix the cause first. The stages this run finished are reused; a new run name is chosen (add --name to pick '
          'one). Through the Docker builder or the master builder, pass the same --reuse-from.' +
          ('' if (rec.get('resume') or {}).get('from_options') else ' This run did not record its options: add '
                                                                     'them to the command.'), '']
    L += _block([(rec.get('resume') or {}).get('command') or ''])
    return '\n'.join(L) + '\n'


def render_refusal(run, refusals, tail, commit=None, version=None):
    """The page of a build the master builder refused at its check, before any stage (tools/aw_service.py
    refused_check_pages; BUILD-FLAGS-MARK-SILENT-REFUSAL-66): its refusals and the last lines of the check's own
    output, in the form of FAILURE.md. No run folder exists, so the page lies beside the build logs."""
    reasons = [text for text in refusals or [] if '\n' not in text]
    L = ['# Build refused: %s' % run, '',
         '_Written by the master builder when it refused the build at its check (tools/aw_service.py); the build did '
         'not start, so there is no run folder._', '',
         '- **Refused at:** the build check, before any stage',
         '- **Error:** %s' % (reasons[0] if reasons else '-'),
         '- **Commit:** %s, version %s' % (commit or 'not recorded', version or 'not recorded'),
         '- **Written:** %s' % _stamp(), '', '## Refusals', '']
    L += _block(reasons or ['-'])
    L += ['', '## The last %d lines of the check\'s own output' % len(tail or []), '']
    L += _block(tail) if tail else ['_The check printed nothing._']
    return '\n'.join(L) + '\n'


def _replace(path, text):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    temporary.replace(path)


def _read_record(run):
    try:
        doc = json.loads((Path(run) / RECORD).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) and doc.get('schema') == SCHEMA else None


def _save(folder, rec):
    _replace(folder / RECORD, json.dumps(rec, indent=1, sort_keys=True) + '\n')
    _replace(folder / MARKDOWN, render(rec))


def write(run, error=None):
    """Write RUN/FAILURE.md and RUN/failure.json for a failed build (ERROR: the builder's exception, if any). Never
    raises: returns the record, or None when there is no run folder or the files could not be written (a warning).
    Written again without an ERROR, the record keeps the builder's error an earlier write recorded."""
    try:
        run = Path(run)
        if not run.is_dir():
            return None
        rec = record(run, error)
        if error is None:
            earlier = _read_record(run)
            if earlier and earlier.get('builder_error'):
                rec['builder_error'] = earlier['builder_error']
        try:
            # in the failing build: the kill counter and the free space now against the build's start
            rec['kinds'] = kinds(rec, error, live=True, workspace=run.parent.parent)
        except Exception:  # noqa: BLE001 - the kind never hides the failure
            pass
        report_file = full_report(run)
        if report_file is not None:
            rec['report'] = str(report_file)
        rec['tip'] = tip_lines(rec, run, live=True)      # what to do now, with the command that continues the build
        rec['source'] = 'build'
        _save(run, rec)
        return rec
    except Exception as exc:  # noqa: BLE001 - the failure page never hides the build's own failure
        print('[failure] the failure details were not written: %s: %s' % (type(exc).__name__, exc), flush=True)
        return None


def ensure(run, error=None):
    """The failure files of RUN, written now unless the failed stage wrote them (execute does as the stage fails), so
    the build report written next can name them. Never raises; returns the record or None."""
    return _read_record(run) or write(run, error)


def last_line(run):
    """The build's last line on a failure: it names the failure page."""
    return ('Failure details: %s (the failed stage, its error, the traceback, the last log lines, the settings and '
            'what was not completed)' % (Path(run) / MARKDOWN))


def report(run, error=None, stream=None):
    """The build's own output on a failure: the failure files written unless the failed stage's run already has them
    (execute writes them as the stage fails), then the page printed between two banner lines. A build report written
    since (tools/build_report.py) is named in them. Never raises."""
    stream = stream or sys.stdout
    try:
        run = Path(run)
        if not run.is_dir():
            return None
        rec = _read_record(run)
        if rec is None:
            rec = write(run, error)
        if rec is None:
            return None
        report_file = full_report(run)
        if report_file is not None and rec.get('report') != str(report_file):
            rec['report'] = str(report_file)
            _save(run, rec)
        text = (run / MARKDOWN).read_text(encoding='utf-8', errors='replace')
        stream.write('=== FAILURE DETAILS (also in %s) ===\n%s=== END OF FAILURE DETAILS ===\n'
                     % (run / MARKDOWN, text))
        stream.flush()
        return rec
    except Exception as exc:  # noqa: BLE001 - the failure page never hides the build's own failure
        print('[failure] the failure details were not printed: %s: %s' % (type(exc).__name__, exc), flush=True)
        return None


def derive(run, path=None, scan_bytes=MONITOR_SCAN_BYTES):
    """(record, FAILURE.md text) of a failed run without failure files, read only (the Monitor's reader); (None,
    None) for a run that did not fail."""
    run = Path(run)
    where = path or (lambda *parts: run.joinpath(*parts))
    if _load_state(where('build-state.json')).get('status') != 'failed':
        return None, None
    rec = record(run, None, scan_bytes, where)
    rec['tip'] = tip_lines(rec, run, files=path is None)
    rec['source'] = 'derived'
    return rec, render(rec)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run', type=Path, help='the build run folder (it holds build-state.json and logs/)')
    ap.add_argument('--print', action='store_true', help='print the page after writing it')
    ap.add_argument('--out', type=Path, help='write FAILURE.md and failure.json into this folder instead of the run '
                                             'folder (the run is only read: a run on a read-only volume)')
    a = ap.parse_args(argv)
    if not (a.run / 'build-state.json').is_file():
        ap.exit(2, 'Error: %s has no build-state.json\n' % a.run)
    if a.out is not None:
        rec = record(a.run)
        report_file = full_report(a.run)
        if report_file is not None:
            rec['report'] = str(report_file)
        rec['tip'] = tip_lines(rec, a.run)
        rec['source'] = 'command'
        a.out.mkdir(parents=True, exist_ok=True)
        _save(a.out, rec)
        folder = a.out
    else:
        rec = write(a.run)
        if rec is None:
            return 1
        folder = a.run
    print('Failure details: %s (%s; %s)' % (folder / MARKDOWN, rec.get('stage') or 'the build itself', rec.get('error')))
    if a.print:
        sys.stdout.write((folder / MARKDOWN).read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
