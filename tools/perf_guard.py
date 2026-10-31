#!/usr/bin/env python3
"""Perf guard: parallelization never regresses (docs/BUILD_PROFILE.md "Perf guard").

Runs at the end of every build (tools/build.py) and in the master builder's build result
(tools/aw_service.py). It reads the run's build-profile.json (the profiler's per-stage sections:
wall time, CPU, cores, units) and judges every stage section that ran for at least
MIN_WALL seconds:

* against a BASELINE for the same work, from the baselines ledger (one JSON line per section of
  earlier runs, keyed by stage, section, stage input fingerprint and unit count):
    - exact      same stage input fingerprint and the same units: time and cores are compared;
    - units      the same unit count (the stage inputs changed elsewhere): time and cores;
    - saturating both runs had at least as many independent units as cores, so both could fill
                 every core: cores (as a share of what the run could use) only, never time.
  Anything else is different work and is never compared.
  FAIL when a section that ran in parallel now runs serial, when its share of usable cores drops
  below CORE_DROP of the baseline's, or when its time grows beyond TIME_TOLERANCE (and TIME_SECONDS)
  with the same units. A section measured on a busy host (other work above the profiler's share,
  in this run or the baseline) is marked BUSY and not compared (HOST LOAD SKEWS TIMINGS).
* without a baseline: any section over FIX_SECONDS with independent units (a parallel map's items,
  a phase's unit total, or a section the policy declares per-unit) that used under FIX_SHARE of the
  cores it could use (min(cores held, units)) is a FIX-NOW finding, and fails the guard.

A failing section with a matching waiver in config/perf-guard.json (bug ID, owner, expiry date) is
WAIVED instead; a waiver past its date, or whose bug the register marks fixed, no longer counts.

    python tools/perf_guard.py check RUN [--baselines FILE] [--policy FILE] [--record] [--json]
    python tools/perf_guard.py show RUN [--json]
    python tools/perf_guard.py seed RUN|PROFILE ... --baselines FILE

check writes perf-guard.json and perf-guard.txt into the run folder and exits 1 on FAIL.
Reading and judging never changes a build output. Standard library only.
"""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'amiwind-perf-guard-v1'
BASELINE_SCHEMA = 'amiwind-perf-guard-baseline-v1'
PROFILE_NAME = 'build-profile.json'
RESULT_NAME = 'perf-guard.json'
TABLE_NAME = 'perf-guard.txt'
POLICY = ROOT / 'config' / 'perf-guard.json'
BUGS = ROOT / 'docs' / 'bugs' / 'bugs.json'
BASELINES_ENV = 'AMIWIND_PERF_GUARD_BASELINES'

MIN_WALL = 30.0          # sections shorter than this are not judged (too noisy)
SERIAL_CORES = 1.5       # under this many cores = serial ...
PARALLEL_CORES = 2.0     # ... when the baseline ran on at least this many
CORE_DROP = 0.5          # FAIL under this share of the baseline's usable-core share (and fewer cores)
MIN_USABLE = 4           # cores are compared only where at least this many cores were usable
TIME_TOLERANCE = 0.25    # FAIL when the same units take more than 25 % longer ...
TIME_SECONDS = 30.0      # ... and more than 30 s longer
FIX_SECONDS = 60.0       # FIX-NOW: over a minute ...
FIX_SHARE = 0.25         # ... on under a quarter of the cores it could use

OK, NO_BASELINE, BUSY, WAIVED, FAIL, FIX_NOW = 'ok', 'no baseline', 'BUSY HOST', 'WAIVED', 'FAIL', 'FIX-NOW'


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def profile_path(target):
    path = Path(target)
    return path / PROFILE_NAME if path.is_dir() else path


def load_profile(target):
    path = profile_path(target)
    return json.loads(path.read_text(encoding='utf-8')), sha256_file(path)


def load_policy(path=None):
    path = Path(path) if path else POLICY
    if not path.is_file():
        return {'independent_units': {}, 'waivers': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    data.setdefault('independent_units', {})
    data.setdefault('waivers', [])
    return data


def fixed_bugs(path=BUGS):
    """IDs the bug register marks fixed or closed: their waivers end with the fix."""
    try:
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    return {row['id'] for row in rows if isinstance(row, dict) and row.get('state') in ('fixed', 'closed')}


def run_name(profile):
    return Path(str(profile.get('run') or 'run')).name


def held_cores(stage):
    return float(stage.get('jobs_mean') or stage.get('jobs_max') or stage.get('jobs') or 1)


SATURATED_PERCENT = 90.0   # the whole host this busy: a stage's time is not this stage's alone


def host_busy(stage):
    """Other work above the profiler's share (host_busy), or the whole host saturated while the stage ran
    (busy_percent at least SATURATED_PERCENT, whoever's the work: other builds or this build's own stages beside it).
    PERF-GUARD-RESIDENT-BUSY-HOST-57: the v0.0.57-dev5 chim-town stages ran on a host 92.9 % busy with
    other_percent 22.4 % and were judged on time as if quiet (build_resident 129 s, was 52 s, the same code)."""
    host = stage.get('host') or {}
    return bool(host.get('host_busy')) or float(host.get('busy_percent') or 0) >= SATURATED_PERCENT


def free_cores(stage):
    """Cores other work left to this build while the stage ran (None without host samples)."""
    host = stage.get('host') or {}
    if host.get('cpus') is None or host.get('other_percent') is None:
        return None
    return round(host['cpus'] * (1 - host['other_percent'] / 100.0), 1)


def judged_sections(profile, policy=None, min_wall=MIN_WALL):
    """The rows the guard judges: every not-reused stage's outermost sections, phases and parallel maps
    that ran for at least MIN_WALL seconds (subprocess 'exec' timers are left out: they are parts of a
    phase). Each row: stage, section, units, independent, wall, cores, budget, usable, fingerprint, busy."""
    declared = (policy or {}).get('independent_units') or {}
    rows = []
    for stage in profile.get('stages', []):
        if stage.get('reused') or stage.get('status') not in (None, 'passed', 'failed'):
            continue
        budget = held_cores(stage)
        for item in stage.get('sections') or []:
            name = str(item.get('name'))
            wall = item.get('wall') or 0.0
            if wall < min_wall or item.get('missing') or item.get('errors') or name.startswith('exec'):
                continue
            if not (item.get('phase') or item.get('min_depth', 0) == 0 or name.startswith('parallel map:')):
                continue
            cores = item.get('cores_avg')
            if cores is None and wall > 0 and item.get('cpu') is not None:
                cores = round(item['cpu'] / wall, 2)
            if cores is None:
                continue
            units = item.get('items') or item.get('units')
            unit_name = declared.get(name)
            independent = bool(units and units >= 2) or bool(unit_name)
            usable = min(budget, float(units)) if units else budget
            rows.append({'stage': stage['name'], 'section': name, 'units': units, 'unit_name': unit_name,
                         'independent': independent, 'wall': round(wall, 1), 'cores': round(float(cores), 2),
                         'budget': round(budget, 1), 'usable': round(max(1.0, usable), 1),
                         'fingerprint': stage.get('fingerprint'), 'busy': host_busy(stage),
                         'free': free_cores(stage)})
    return rows


def baseline_records(profile, digest, policy=None):
    """The baseline ledger lines of one profile (all judged sections; busy ones carry the mark)."""
    return [{'schema': BASELINE_SCHEMA, 'run': run_name(profile), 'profile_sha256': digest,
             'version': profile.get('version'), 'started_at': profile.get('started_at'),
             **{key: row[key] for key in ('stage', 'section', 'units', 'wall', 'cores', 'budget', 'usable',
                                          'fingerprint', 'busy')}}
            for row in judged_sections(profile, policy)]


def read_baselines(path):
    if not path or not Path(path).is_file():
        return []
    records = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get('schema') == BASELINE_SCHEMA:
            records.append(record)
    return records


def append_baselines(path, records):
    """Append records whose profile SHA-256 is not in the ledger yet; returns how many were added."""
    path = Path(path)
    known = {record.get('profile_sha256') for record in read_baselines(path)}
    new = [record for record in records if record['profile_sha256'] not in known]
    if not new:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    data = ''.join(json.dumps(record, sort_keys=True) + '\n' for record in new).encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    return len(new)


def _median(values):
    values = sorted(values)
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _share(record):
    return record['cores'] / max(1.0, record.get('usable') or record.get('budget') or 1)


def pick_baseline(row, records, own_run=None):
    """The baseline for one row from earlier records of the same stage and section, never other work.
    Cores: the best share of usable cores demonstrated by any record of the same work scale (exact
    fingerprint, the same units, or both saturating: at least as many independent units as cores);
    parallelism never regresses from what it reached. Time: the median of the exact records, else of the
    same-units records (never across different unit counts). Busy-host records count only when no
    quiet one exists (and then the baseline is marked busy)."""
    same = [r for r in records if r.get('stage') == row['stage'] and r.get('section') == row['section']
            and r.get('run') != own_run]
    units = row['units']
    exact = [r for r in same if row['fingerprint'] and r.get('fingerprint') == row['fingerprint']
             and r.get('units') == units]
    by_units = [r for r in same if units and r.get('units') == units]
    saturating = [r for r in same if units and r.get('units') and units >= row['budget']
                  and r['units'] >= (r.get('budget') or 1)]
    scale = {id(r): r for r in exact + by_units + saturating}.values()
    if not scale:
        return None
    quiet = [r for r in scale if not r.get('busy')]
    pool = quiet or list(scale)
    best = max(pool, key=lambda r: (_share(r), r['run']))
    tier = 'exact' if best in exact else 'units' if best in by_units else 'saturating'
    timed = exact or by_units
    timed_quiet = [r for r in timed if not r.get('busy')] or timed
    return {'tier': tier, 'run': best['run'], 'cores': best['cores'],
            'usable': best.get('usable') or best.get('budget') or 1, 'share': round(_share(best), 3),
            'wall': round(_median([r['wall'] for r in timed_quiet]), 1) if timed else None,
            'time_tier': ('exact' if exact else 'units') if timed else None,
            'time_busy': bool(timed) and all(r.get('busy') for r in timed),
            'samples': len(pool), 'busy': not quiet}


def waiver_for(row, policy, today, fixed):
    for waiver in policy.get('waivers') or []:
        if not fnmatch.fnmatchcase(row['stage'], waiver.get('stage', '*')):
            continue
        if not any(fnmatch.fnmatchcase(row['section'], pattern) for pattern in waiver.get('sections') or ['*']):
            continue
        expires = waiver.get('expires')
        if waiver.get('id') in fixed:
            return dict(waiver, void=f"its bug {waiver.get('id')} is marked fixed: the waiver ended")
        if expires and today > expires:
            return dict(waiver, void=f'expired {expires}')
        return waiver
    return None


def judge(profile, records, policy=None, today=None, fixed=None):
    """Every judged row with its baseline and verdict, plus the overall verdict."""
    policy = policy if policy is not None else load_policy()
    today = today or datetime.date.today().isoformat()
    fixed = fixed if fixed is not None else fixed_bugs()
    own = run_name(profile)
    rows = []
    for row in judged_sections(profile, policy):
        reasons = []
        base = pick_baseline(row, records, own)
        share = row['cores'] / row['usable']
        verdict = OK if base else NO_BASELINE
        if base:
            # cores: compared on a busy host only when other work still left this build at least the baseline's
            # cores (then the drop is not the host's doing; said so in the reasons)
            # (or when the section left most of the cores it had free idle)
            free = row['free']
            cores_comparable = not row['busy'] or (free is not None and (free >= base['cores']
                                                                         or row['cores'] < CORE_DROP * free))
            if row['busy']:
                reasons.append('busy host in this run (%s cores free)%s' % (
                    free if free is not None else '?',
                    ': cores compared anyway' if cores_comparable else ': cores not compared'))
            if row['usable'] < MIN_USABLE:
                cores_comparable = False      # two or three units: one long unit sets the cores, not the code
                reasons.append('cores not compared: %.0f usable' % row['usable'])
            if cores_comparable:
                if base['cores'] >= PARALLEL_CORES and row['cores'] < SERIAL_CORES:
                    reasons.append('parallel -> serial: %.2f cores, was %.2f (%s, %s)' % (
                        row['cores'], base['cores'], base['tier'], base['run']))
                elif (base['cores'] >= PARALLEL_CORES and share < CORE_DROP * base['share']
                      and row['cores'] < base['cores']):
                    reasons.append('cores dropped: %.0f %% of usable, was %.0f %% (%s, %s)' % (
                        100 * share, 100 * base['share'], base['tier'], base['run']))
            if base['wall'] is not None:
                if row['busy'] or base['time_busy']:
                    reasons.append('time not compared: busy host in %s' % ('this run' if row['busy'] else 'the baseline'))
                else:
                    delta = row['wall'] - base['wall']
                    if delta > TIME_SECONDS and delta > TIME_TOLERANCE * base['wall']:
                        reasons.append('slower with the same %s units: %.0fs, was %.0fs (+%.0f %%)'
                                       % (row['units'], row['wall'], base['wall'], 100 * delta / base['wall']))
            failing = [text for text in reasons if text.startswith(('parallel ->', 'cores dropped', 'slower'))]
            if failing:
                verdict = FAIL
            elif row['busy']:
                verdict = BUSY
        if (row['independent'] and row['wall'] >= FIX_SECONDS and share < FIX_SHARE
                and row['usable'] >= 2):
            reasons.append('%.0fs on %.2f of %.0f usable cores with independent %s' % (
                row['wall'], row['cores'], row['usable'], row['unit_name'] or 'units'))
            if verdict != FAIL:
                verdict = FIX_NOW
        waiver = None
        if verdict in (FAIL, FIX_NOW):
            waiver = waiver_for(row, policy, today, fixed)
            if waiver and not waiver.get('void'):
                reasons.append('waived by %s until %s (%s)' % (waiver['id'], waiver.get('expires'),
                                                              waiver.get('owner', '?')))
                verdict = WAIVED
            elif waiver:
                reasons.append('waiver %s does not count: %s' % (waiver['id'], waiver['void']))
        rows.append(dict(row, baseline=base, verdict=verdict, reasons=reasons,
                         waiver=(waiver or {}).get('id')))
    counts = {}
    for row in rows:
        counts[row['verdict']] = counts.get(row['verdict'], 0) + 1
    failed = counts.get(FAIL, 0) + counts.get(FIX_NOW, 0)
    cpu = sum(row['cores'] * row['wall'] for row in rows)
    wall = sum(row['wall'] for row in rows)
    totals = {'sections': len(rows), 'units': sum(row['units'] or 0 for row in rows), 'wall': round(wall, 1),
              'cpu': round(cpu, 1), 'cores': round(cpu / wall, 2) if wall else None,
              'budget': profile.get('budget'), 'counts': counts}
    return {'schema': SCHEMA, 'run': own, 'version': profile.get('version'),
            'verdict': 'failed' if failed else 'passed', 'failed': failed, 'waived': counts.get(WAIVED, 0),
            'busy': counts.get(BUSY, 0), 'baselines': len(records), 'today': today,
            'thresholds': {'min_wall': MIN_WALL, 'serial_cores': SERIAL_CORES, 'parallel_cores': PARALLEL_CORES,
                           'core_drop': CORE_DROP, 'min_usable': MIN_USABLE, 'time_tolerance': TIME_TOLERANCE, 'time_seconds': TIME_SECONDS,
                           'fix_seconds': FIX_SECONDS, 'fix_share': FIX_SHARE},
            'rows': rows, 'totals': totals}


def _time(seconds):
    if seconds is None:
        return '-'
    seconds = float(seconds)
    return '%dm%02ds' % divmod(round(seconds), 60) if seconds >= 60 else '%.0fs' % seconds


def table_lines(result):
    """One table per build: section, units, cores used / budget, time, baseline, verdict; TOTALS last."""
    header = ('stage', 'section', 'units', 'cores/usable(held)', 'time', 'baseline', 'verdict')
    body = []
    for row in result['rows']:
        base = row['baseline']
        base_text = ('-' if not base else '%s %.2f/%.0f%s (%s)' % (
            base['tier'], base['cores'], base['usable'], ' ' + _time(base['wall']) if base['wall'] is not None
            else '', base['run'][-24:]))
        body.append((row['stage'], row['section'][:44], str(row['units'] or ('decl.' if row['unit_name'] else '-')),
                     '%.2f/%.0f(%.0f)' % (row['cores'], row['usable'], row['budget']), _time(row['wall']),
                     base_text, row['verdict']))
    totals = result['totals']
    counts = ', '.join('%s %d' % (key, value) for key, value in sorted(totals['counts'].items())) or 'none'
    body.append(('TOTALS', '%d sections' % totals['sections'], str(totals['units']),
                 '%s avg' % (totals['cores'] if totals['cores'] is not None else '-'),
                 _time(totals['wall']), '%d baseline records' % result['baselines'], counts))
    widths = [max(len(str(line[i])) for line in [header] + body) for i in range(len(header))]
    text = lambda line: '  '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(line)).rstrip()
    lines = ['Perf guard %s: %s (%d failing, %d waived, %d busy-host)' % (
        result['run'], result['verdict'].upper(), result['failed'], result['waived'], result['busy']),
        text(header), text(['-' * width for width in widths])]
    lines += [text(line) for line in body[:-1]] + [text(['-' * width for width in widths]), text(body[-1])]
    for row in result['rows']:
        if row['reasons'] and row['verdict'] != OK:
            lines.append('  %s %s / %s: %s' % (row['verdict'], row['stage'], row['section'], '; '.join(row['reasons'])))
    return lines


def default_baselines(run):
    """AMIWIND_PERF_GUARD_BASELINES, else <workspace>/cache/perf-guard/baselines.jsonl beside the run's
    build folder (the shared cache of the build pool)."""
    if os.environ.get(BASELINES_ENV):
        return Path(os.environ[BASELINES_ENV])
    run = Path(run)
    folder = run if run.is_dir() else run.parent
    return folder.parent.parent / 'cache' / 'perf-guard' / 'baselines.jsonl'


def check(run, baselines=None, policy=None, record=False, today=None, write=True, quiet=False):
    """Judge RUN, write perf-guard.json/.txt into it, print the table; with record, a passed run on a
    quiet host adds its sections to the baselines ledger."""
    profile, digest = load_profile(run)
    baselines = Path(baselines) if baselines else default_baselines(run)
    policy_data = load_policy(policy)
    records = read_baselines(baselines)
    result = judge(profile, records, policy_data, today)
    result['profile_sha256'] = digest
    result['baselines_file'] = str(baselines)
    lines = table_lines(result)
    added = 0
    if record and result['verdict'] == 'passed':
        try:
            added = append_baselines(baselines, baseline_records(profile, digest, policy_data))
        except OSError as exc:
            lines.append(f'[warning] perf guard: baselines not recorded: {exc}')
    result['recorded'] = added
    folder = profile_path(run).parent
    if write:
        try:
            (folder / RESULT_NAME).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                              newline='\n')
            (folder / TABLE_NAME).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        except OSError as exc:
            lines.append(f'[warning] perf guard: result not written: {exc}')
    if not quiet:
        print('\n'.join(lines), flush=True)
    return result


def summary(result):
    """One JSON-able line for the master builder's result."""
    if not result:
        return None
    return {'verdict': result['verdict'], 'failed': result['failed'], 'waived': result['waived'],
            'busy': result['busy'], 'sections': result['totals']['sections'],
            'failing': ['%s / %s: %s' % (row['stage'], row['section'], '; '.join(row['reasons']))
                        for row in result['rows'] if row['verdict'] in (FAIL, FIX_NOW)][:20],
            'waivers': sorted({row['waiver'] for row in result['rows'] if row['verdict'] == WAIVED})}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='perf_guard.py', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('check', help='judge a run, write perf-guard.json/.txt, exit 1 on FAIL')
    c.add_argument('run')
    c.add_argument('--baselines', help='baselines ledger (default: the build pool cache, or %s)' % BASELINES_ENV)
    c.add_argument('--policy', help='waivers and declared per-unit sections (default config/perf-guard.json)')
    c.add_argument('--record', action='store_true', help='a passed run adds its sections to the baselines')
    c.add_argument('--today', help='date for waiver expiry (YYYY-MM-DD; default today)')
    c.add_argument('--json', action='store_true', help='print the result summary as the last line')
    s = sub.add_parser('show', help="print a run's perf-guard result (exit 1 when it failed)")
    s.add_argument('run')
    s.add_argument('--json', action='store_true')
    d = sub.add_parser('seed', help='add the sections of finished runs to a baselines ledger (by SHA-256)')
    d.add_argument('runs', nargs='+')
    d.add_argument('--baselines', required=True)
    d.add_argument('--policy')
    args = parser.parse_args(argv)
    if args.command == 'check':
        result = check(args.run, args.baselines, args.policy, args.record, args.today)
        if args.json:
            print(json.dumps(summary(result), sort_keys=True))
        return 1 if result['verdict'] == 'failed' else 0
    if args.command == 'show':
        path = Path(args.run) / RESULT_NAME if Path(args.run).is_dir() else Path(args.run)
        if not path.is_file():
            print(json.dumps({'verdict': 'missing', 'detail': f'no {RESULT_NAME} in the run'}) if args.json
                  else f'no {RESULT_NAME} in the run')
            return 0
        result = json.loads(path.read_text(encoding='utf-8'))
        if args.json:
            print(json.dumps(summary(result), sort_keys=True))
        else:
            print('\n'.join(table_lines(result)))
        return 1 if result['verdict'] == 'failed' else 0
    policy = load_policy(args.policy)
    total = 0
    for target in args.runs:
        try:
            profile, digest = load_profile(target)
        except (OSError, ValueError) as exc:
            print(f'{target}: skipped ({exc})')
            continue
        added = append_baselines(args.baselines, baseline_records(profile, digest, policy))
        total += added
        print(f'{run_name(profile)}: {added} section records added')
    print(f'{total} records added to {args.baselines}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
