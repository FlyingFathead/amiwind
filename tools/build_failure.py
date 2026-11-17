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

  python3 tools/build_failure.py RUN [--print]       write the failure files of a failed run (again), print the page
  python3 tools/build_failure.py RUN --out DIR       write them into DIR instead: the run folder is only read
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
import re
import shlex
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
           'failed_stages': stages, 'stages_recorded': len(steps),
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
