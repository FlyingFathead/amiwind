# SPDX-License-Identifier: GPL-3.0-only
"""The short part of the build summary: per stage, what needs attention, and against the last build of the same kind.

Written into RUN/build-summary.json (key 'digest', schema amiwind-build-summary-v2; tools/build_summary.py writes the
rest of that file at the end of the build) and as RUN/build-summary.md, a page of under about 60 lines. Updated at
every stage end (tools/build_parallel.py execute_parallel) and at the end of the build, after the perf guard
(tools/build.py).

Per stage: wall time, cores allowed and used (mean over the stage, from the scheduler's live supervisor,
tools/stage_watch.py), the longest stretch under half its share, whether it was reused, and its warnings. Warnings
come from the run's own records: underuse occurrences (RUN/underused.jsonl), the perf guard (perf-guard.json), the
size guard (size-ledger.json), waivers (perf guard rows with a waiver) and retired flags (build-state.json).

'Needs attention' is a list of entries with a stable one-line key ('underused:chim', 'perf-guard:chim:CHIM world
conversion', 'stage-failed:image', 'size-growth:chim-world', 'retired-flag:--seyda-recorded', 'slower:chim', ...):
empty when all is well; a watcher can wake on a new key. Read only on the run's files; never fails a build.
"""
import json
import os
import re
import time
from pathlib import Path

SCHEMA = 'amiwind-build-summary-v2'
MD = 'build-summary.md'
JSON = 'build-summary.json'
CHANGE_SHARE = 0.20        # a stage time up or down by more than this against the last build of the same kind
CHANGE_MIN_SECONDS = 30.0  # ... and by at least this many seconds (reused stages take under a second)
MD_STAGE_ROWS = 25
NAME = re.compile(r'^(\d{4}_\d{2}_\d{2})_v([^_]+)_(.+)_([0-9a-f]{7,})$')


def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _lines(path):
    rows = []
    try:
        with Path(path).open(encoding='utf-8') as source:
            for line in source:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def kind(name):
    """The purpose of a run name without its reason and try suffix (2026_10_18_v0.0.43-dev3_full-batch5_ef7e464 ->
    'full'), or None for a name off the naming rule."""
    match = NAME.match(name or '')
    if not match:
        return None
    return match.group(3).split('-')[0]


def previous_run(run):
    """The newest other run beside RUN of the same kind with a passed build-state.json, started before RUN."""
    run = Path(run)
    mine = kind(run.name)
    if mine is None:
        return None
    try:
        started = (run / 'build-state.json').stat().st_mtime if (run / 'build-state.json').exists() else time.time()
        candidates = []
        for other in run.parent.iterdir():
            if other == run or kind(other.name) != mine:
                continue
            state = other / 'build-state.json'
            try:
                stat = state.stat()
            except OSError:
                continue
            candidates.append((stat.st_mtime, other))
    except OSError:
        return None
    for _, other in sorted(candidates, key=lambda c: c[0], reverse=True):
        record = _json(other / 'build-state.json') or {}
        if record.get('status') == 'passed' and _ < started:
            return other
    return None


def _wall(step, now_seconds):
    if step.get('elapsed_seconds') is not None:
        return float(step['elapsed_seconds'])
    if step.get('status') == 'running' and step.get('started_seconds') is not None and now_seconds is not None:
        return max(0.0, now_seconds - float(step['started_seconds']))
    return None


def _duration(seconds):
    if seconds is None:
        return '-'
    seconds = int(round(seconds))
    if seconds < 60:
        return '%ds' % seconds
    if seconds < 3600:
        return '%dm%02ds' % divmod(seconds, 60)
    return '%dh%02dm' % (seconds // 3600, seconds % 3600 // 60)


def digest(run, receipt=None, watch=None, now_seconds=None, previous=None):
    """The digest record of RUN (see the module text). RECEIPT: build-state.json as the scheduler holds it (else read);
    WATCH: the scheduler's StageWatch (live core numbers); PREVIOUS: the run to compare with (else previous_run)."""
    run = Path(run)
    state = receipt if receipt is not None else (_json(run / 'build-state.json') or {})
    reused = set(((state.get('stage_cache') or {}).get('reused') or {}))
    refused = {n for n, r in ((state.get('stage_cache') or {}).get('reused') or {}).items()
               if isinstance(r, dict) and r.get('refused')}
    reused -= refused
    underused = _lines(run / 'underused.jsonl')
    guard = _json(run / 'perf-guard.json')
    sizes = _json(run / 'size-ledger.json')
    stages, attention = [], []

    def need(key, text):
        if key not in {row['key'] for row in attention}:
            attention.append({'key': key, 'text': text})
    for step in state.get('steps') or []:
        name = step['name']
        cores = step.get('cores') or (watch.summary(name) if watch is not None else None) or {}
        warnings = []
        for row in underused:
            if row.get('stage') == name:
                warnings.append('underused: %.1f of %s cores for %.0f s, slowest %s' % (
                    row.get('cores_used') or 0, max(row.get('allowed') or 0, row.get('share') or 0),
                    row.get('seconds') or row.get('since_seconds') or 0,
                    (row.get('slowest') or {}).get('unit') or 'not named'))
        if any(row.get('stage') == name for row in underused):
            need('underused:%s' % name, '%s ran under half its cores with units queued (%d time(s); underused.jsonl)'
                 % (name, sum(row.get('stage') == name for row in underused)))
        for row in (guard or {}).get('rows') or []:
            if row.get('stage') != name:
                continue
            if row.get('verdict') == 'FAIL':
                warnings.append('perf guard FAIL: %s (%s)' % (row.get('section'), '; '.join(row.get('reasons') or [])))
                need('perf-guard:%s:%s' % (name, row.get('section')), 'perf guard failed: %s / %s' % (
                    name, row.get('section')))
            if row.get('waiver'):
                warnings.append('waived: %s (%s)' % (row.get('section'), row.get('waiver')))
                need('waiver:%s:%s' % (name, row.get('section')), 'perf guard waiver used: %s / %s' % (
                    name, row.get('section')))
        if step.get('status') in ('failed', 'cancelled'):
            need('stage-%s:%s' % (step['status'], name), '%s %s (log %s)' % (name, step['status'], step.get('log')))
        stages.append({'name': name, 'status': step.get('status'), 'wall_seconds': _round(_wall(step, now_seconds)),
                       'jobs_start': step.get('jobs'), 'workers_now': step.get('workers_now'),
                       'cores_allowed_mean': cores.get('allowed_mean'), 'cores_used_mean': cores.get('cores_mean'),
                       'under_half_longest_seconds': cores.get('under_half_longest_seconds'),
                       'reused': name in reused, 'warnings': warnings})
    size_guard = (sizes or {}).get('guard') or {}
    for row in size_guard.get('grown') or []:
        if size_guard.get('verdict') in ('warned', 'failed'):
            need('size-growth:%s' % row.get('group'), 'payload folder %s grew without a named reason (size-ledger.json)'
                 % row.get('group'))
    for flag in state.get('retired_flags_used') or []:
        label = flag.get('flag') if isinstance(flag, dict) else str(flag)
        need('retired-flag:%s' % label, 'retired flag used: %s' % label)
    comparison = []
    previous = previous if previous is not None else previous_run(run)
    if previous is not None:
        old = {s['name']: s for s in (_json(Path(previous) / 'build-state.json') or {}).get('steps') or []}
        for row in stages:
            before = old.get(row['name'])
            if before is None or row['status'] != 'passed' or before.get('status') != 'passed':
                continue
            new, was = row['wall_seconds'], before.get('elapsed_seconds')
            if new is None or was is None or abs(new - was) < CHANGE_MIN_SECONDS:
                continue
            change = (new - was) / max(was, 1e-9)
            if abs(change) > CHANGE_SHARE:
                comparison.append({'stage': row['name'], 'seconds': new, 'previous_seconds': was,
                                   'change': round(change, 3)})
                if change > 0:
                    need('slower:%s' % row['name'], '%s took %s, %+.0f %% against %s (%s)' % (
                        row['name'], _duration(new), change * 100, Path(previous).name, _duration(was)))
    return {'schema': SCHEMA, 'run': run.name, 'kind': kind(run.name), 'status': state.get('status'),
            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'worker_budget': state.get('worker_budget'),
            'needs_attention': attention, 'stages': stages,
            'compared_with': Path(previous).name if previous is not None else None, 'stage_changes': comparison}


def _round(value):
    return None if value is None else round(value, 1)


def markdown(record):
    """The digest as a page of under about 60 lines."""
    lines = ['# Build summary: %s' % record['run'], '',
             'Status: %s | updated %s | worker budget %s' % (record['status'], record['updated_at'],
                                                               record['worker_budget']), '', '## Needs attention', '']
    if record['needs_attention']:
        lines.extend('- `%s` %s' % (row['key'], row['text']) for row in record['needs_attention'][:15])
        if len(record['needs_attention']) > 15:
            lines.append('- ... %d more in build-summary.json' % (len(record['needs_attention']) - 15))
    else:
        lines.append('Nothing: all is well.')
    lines.extend(['', '## Stages', '', '| Stage | Status | Wall | Cores used / allowed | Longest under half | Reused |'
                  ' Warnings |', '| --- | --- | --- | --- | --- | --- | --- |'])
    ran = sorted(record['stages'], key=lambda s: -(s['wall_seconds'] or 0))
    shown = [s for s in ran if not s['reused'] or s['warnings']][:MD_STAGE_ROWS]
    for s in shown:
        cores = ('%.1f / %.1f' % (s['cores_used_mean'], s['cores_allowed_mean'])
                 if s['cores_used_mean'] is not None and s['cores_allowed_mean'] is not None else '-')
        lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            s['name'], s['status'], _duration(s['wall_seconds']), cores, _duration(s['under_half_longest_seconds']),
            'yes' if s['reused'] else 'no', len(s['warnings']) or ''))
    hidden = len(record['stages']) - len(shown)
    if hidden:
        lines.append('')
        lines.append('%d more stage(s) reused or short; every stage is in build-summary.json.' % hidden)
    lines.extend(['', '## Against the last build of the same kind', ''])
    if record['compared_with'] is None:
        lines.append('No earlier build of this kind beside this run.')
    elif not record['stage_changes']:
        lines.append('%s: no stage time changed by more than %d %%.' % (record['compared_with'], CHANGE_SHARE * 100))
    else:
        lines.append('%s:' % record['compared_with'])
        lines.extend('- %s %s -> %s (%+.0f %%)' % (row['stage'], _duration(row['previous_seconds']),
                                                    _duration(row['seconds']), row['change'] * 100)
                     for row in record['stage_changes'][:10])
    return '\n'.join(lines) + '\n'


def _atomic(path, text):
    # fixed temporary names, listed with the files in build_cache.RUN_PRIVATE (never a stage's output)
    temporary = path.with_name('build-summary.tmp' if path.suffix == '.json' else path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    os.replace(temporary, path)


def update(run, receipt=None, watch=None, now_seconds=None):
    """Write the digest into RUN/build-summary.json (merged: the rest of the file, written by build_summary.py at the
    end, is kept) and RUN/build-summary.md. Returns the digest."""
    run = Path(run)
    if not run.is_dir():
        return None
    record = digest(run, receipt, watch, now_seconds)
    summary = _json(run / JSON) or {'schema': SCHEMA, 'status': record['status'] or 'running'}
    summary['schema'] = SCHEMA
    summary['digest'] = record
    _atomic(run / JSON, json.dumps(summary, indent=2) + '\n')
    write_page(run, record)
    return record


def write_page(run, record):
    """RUN/build-summary.md of a digest record."""
    _atomic(Path(run) / MD, markdown(record))
