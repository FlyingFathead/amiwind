#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The failure details of a failed build: RUN/FAILURE.md and RUN/failure.json (BUILD-FAILURE-NO-DETAILS-66).

When a stage or the build itself fails, the builder writes one page beside the logs that says what failed: the failed
stage, its exit, its error lines, the traceback when the log holds one, the last 60 lines of the stage's log, the units
it refused or left out (its "not converted: ..." lines), the run's commit and the command that builds again from this
run. failure.json holds the same as data: the Toolkit Monitor shows the failed stage and its error line under Progress,
with a "See failure details" link to FAILURE.md. The stage logs and the build's own output keep everything as before;
the page is printed into the build's output too.

It reads the run's build-state.json and the failed stages' logs (the last BUILD_SCAN_BYTES of each, line by line) and
writes only those two files; it never raises into the build (a page that cannot be written is a warning). The Monitor's
reader uses the same code read only (derive) for a failed run without the files, a run of an earlier builder.

  python3 tools/build_failure.py RUN [--print]     write the failure files of a failed run (again), print the page
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
           'failed_stages': stages,
           'cancelled_stages': [str(s.get('name')) for s in steps if s.get('status') == 'cancelled'],
           'not_started': [str(n) for n in state.get('not_started') or []],
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


def render(rec):
    """FAILURE.md of a failure record: plain text that reads as Markdown too."""
    stages = rec.get('failed_stages') or []
    L = ['# Build failure: %s' % rec.get('run'), '',
         '_Written by the builder when the build failed (tools/build_failure.py). The stage logs and the build\'s '
         'own output keep everything; this is the short form._', '']
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
    stopped = []
    if rec.get('cancelled_stages'):
        stopped.append('cancelled with it: ' + ', '.join(rec['cancelled_stages']))
    if rec.get('not_started'):
        stopped.append('%d not started: %s' % (len(rec['not_started']), ', '.join(rec['not_started'][:40]) +
                                              (', ...' if len(rec['not_started']) > 40 else '')))
    if stopped:
        L.append('- **Other stages:** ' + '; '.join(stopped))
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
        rec['source'] = 'build'
        _replace(run / RECORD, json.dumps(rec, indent=1, sort_keys=True) + '\n')
        _replace(run / MARKDOWN, render(rec))
        return rec
    except Exception as exc:  # noqa: BLE001 - the failure page never hides the build's own failure
        print('[failure] the failure details were not written: %s: %s' % (type(exc).__name__, exc), flush=True)
        return None


def report(run, error=None, stream=None):
    """The build's own output on a failure: the failure files written unless the failed stage's run already has them
    (execute writes them as the stage fails), then the page printed between two banner lines. Never raises."""
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
    a = ap.parse_args(argv)
    if not (a.run / 'build-state.json').is_file():
        ap.exit(2, 'Error: %s has no build-state.json\n' % a.run)
    rec = write(a.run)
    if rec is None:
        return 1
    print('Failure details: %s (%s; %s)' % (a.run / MARKDOWN, rec.get('stage') or 'the build itself', rec.get('error')))
    if a.print:
        sys.stdout.write((a.run / MARKDOWN).read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
