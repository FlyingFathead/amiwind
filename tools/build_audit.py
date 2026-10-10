#!/usr/bin/env python3
"""Post-build audit of one builder run folder (docs/CI.md).

Reads RUN/build-state.json (and, when present, build-summary.json, reuse-report.json and the
reuse source's profile/fingerprints.json) and reports, without changing anything:

  * reuse audit: every stage that was NOT reused from --reuse-from, classified as expected
    (its inputs changed, the stage is never reused, the old run did not pass it) or UNEXPECTED
    (output manifest missing or unusable, old outputs changed, a fingerprint problem, or a
    source change limited to files that should never key a conversion stage, such as the
    release file list or documentation);
  * end-summary checks: the final status agrees with the steps, a passed build has a summary
    with an output hash, zero compiler warnings, complete media coverage;
  * time to fail: when and where a failed build stopped, and whether that was late
    (the builder motto: fail fast, keep failures cheap);
  * exclude effect: --exclude-video left no video in the payload, and an
    --exclude-unreferenced media stage did not take as long as a full one.

    python3 tools/build_audit.py RUN [--json] [--late-after S] [--media-ceiling S] [--suspicious GLOB ...]
    python3 tools/build_audit.py RUN --compare REFERENCE_RUN [--ignore GLOB ...] [--json]

--compare checks a run's stage outputs file by file (paths and SHA-256 from the stage output
manifests) against another run, such as a from-scratch build against the release build.

Exit status: 0 = nothing that needs attention, 1 = at least one finding marked "wake",
2 = RUN is not a readable builder run.
"""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

SCHEMA = 'amiwind-build-audit-v1'
# Files whose change must never force a conversion stage to rebuild (BUILD-KEY-OVERBROAD class).
DEFAULT_SUSPICIOUS = ('tools/release-files.json', 'docs/*', 'docs/**', '*.md', 'CHANGELOG*', 'README*')
LATE_AFTER_SECONDS = 600.0      # a failure later than this after the start is a late failure
MEDIA_CEILING_SECONDS = 300.0   # an --exclude-unreferenced media stage above this did not exclude early

# Fingerprint component names that tools/build_cache.py explain() can list after "changed: ".
COMPONENT_KEYS = frozenset(('command', 'sources', 'environment', 'external_inputs', 'fingerprint', 'machine', 'packages',
                            'schema', 'scope', 'stage', 'version', 'inputs', 'tools', 'parameters'))
EXPECTED_PREFIXES = (
    ('compiles with the Amiga SDK', 'never-reused'),
    ('final image', 'never-reused'),
    ('not passed in ', 'old-run-not-passed'),
)
UNEXPECTED_PREFIXES = (
    ('no output manifest', 'manifest-missing'),
    ('old output manifest incomplete', 'manifest-incomplete'),
    ('old outputs not reusable', 'outputs-not-reusable'),
    ('reuse would depend on rebuilt stages', 'dependency-closure'),
)
UNEXPECTED_PATTERNS = (
    (re.compile(r'^old output .* changed or missing since '), 'old-output-changed'),
    (re.compile(r'^its output .* was replaced later in '), 'output-replaced'),
)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def suspicious(path, globs):
    return any(fnmatch.fnmatch(path, pattern) for pattern in globs)


def changed_parts(reason):
    """'changed: dependency a, b, sources (x, y, +3 more), command' -> (parts, files, hidden_more)."""
    body = reason[len('changed: '):]
    files, more = [], 0
    match = re.search(r'sources \(([^)]*)\)', body)
    if match:
        for item in match.group(1).split(', '):
            plus = re.fullmatch(r'\+(\d+) more', item.strip())
            if plus:
                more = int(plus.group(1))
            elif item.strip():
                files.append(item.strip())
        body = body[:match.start()] + 'sources' + body[match.end():]
    parts = []
    for item in body.split(', '):
        item = item.strip()
        if item.startswith('dependency '):
            parts.append('dependency')
        elif item in COMPONENT_KEYS or not parts or parts[-1] != 'dependency':
            parts.append(item)
        # anything else right after "dependency" is one more dependency name
    return parts, files, more


def source_diff(old_details, new_details, stage):
    """Every source file whose hash differs for STAGE between two profile/fingerprints.json records."""
    old = ((old_details or {}).get(stage) or {}).get('sources') or {}
    new = ((new_details or {}).get(stage) or {}).get('sources') or {}
    old, new = old.get('by_file') or {}, new.get('by_file') or {}
    if not old and not new:
        return None
    return sorted(path for path in set(old) | set(new) if old.get(path) != new.get(path))


def classify(reason, globs=DEFAULT_SUSPICIOUS, full_files=None):
    """One not-reused reason -> (class, label, detail). class: 'expected' | 'unexpected' | 'info'."""
    if reason.startswith('changed: '):
        parts, files, more = changed_parts(reason)
        if full_files is not None:
            files, more = list(full_files), 0
        if 'sources' in parts and files:
            bad = [f for f in files if suspicious(f, globs)]
            if bad and len(bad) == len(files) and not more and parts == ['sources']:
                return 'unexpected', 'key-overbroad', 'rebuilt only because of ' + ', '.join(bad[:5])
            if bad:
                return 'info', 'key-includes-docs', 'source change includes ' + ', '.join(bad[:5])
        if parts == ['dependency']:
            return 'expected', 'dependency-rebuilt', reason
        return 'expected', 'inputs-changed', reason
    for prefix, label in EXPECTED_PREFIXES:
        if reason.startswith(prefix):
            return 'expected', label, reason
    for prefix, label in UNEXPECTED_PREFIXES:
        if reason.startswith(prefix):
            return 'unexpected', label, reason
    for pattern, label in UNEXPECTED_PATTERNS:
        if pattern.search(reason):
            return 'unexpected', label, reason
    if ' fingerprints, this builder makes ' in reason:
        return 'info', 'cache-schema-change', reason
    # unknown reasons and fingerprint problems: when unsure, it needs attention
    return 'unexpected', 'unknown-reason', reason


def finding(kind, severity, message, stage=None, **extra):
    item = {'kind': kind, 'severity': severity, 'message': message}
    if stage:
        item['stage'] = stage
    item.update(extra)
    return item


def reuse_audit(run, state, globs, report=None):
    cache = state.get('stage_cache') or {}
    steps = [step.get('name') for step in state.get('steps') or []]
    reused = cache.get('reused') or {}
    not_reused = cache.get('not_reused') or {}
    result = {'reuse_from': cache.get('reuse_from'), 'stages': len(steps), 'reused': len(reused),
              'not_reused': {}, 'findings': []}
    if report:  # the builder's own reuse report wins where it states an expectation
        for name, entry in (report.get('stages') or {}).items():
            if entry.get('reused'):
                continue
            expected = entry.get('expected')
            reason = entry.get('reason') or 'not reused'
            klass = 'expected' if expected else ('unexpected' if expected is False else classify(reason, globs)[0])
            result['not_reused'][name] = {'class': klass, 'label': entry.get('label') or 'reuse-report', 'reason': reason}
    if not cache.get('reuse_from'):
        result['findings'].append(finding('reuse', 'info', 'no --reuse-from: every stage ran (from-scratch or first build)'))
        return result
    old_details = new_details = None
    old_run = Path(cache['reuse_from'])
    local_old = run.parent / old_run.name  # the reuse source is usually a sibling run on the same volume
    for candidate in (old_run, local_old):
        old_details = load_json(candidate / 'profile' / 'fingerprints.json')
        if old_details is not None:
            break
    new_details = load_json(run / 'profile' / 'fingerprints.json')
    for name, reason in not_reused.items():
        if name in result['not_reused']:
            continue
        full = source_diff(old_details, new_details, name) if old_details and new_details else None
        klass, label, detail = classify(reason, globs, full)
        result['not_reused'][name] = {'class': klass, 'label': label, 'reason': reason}
        if full is not None:
            result['not_reused'][name]['changed_files'] = full[:50]
    for name, entry in result['not_reused'].items():
        if entry['class'] == 'unexpected':
            result['findings'].append(finding('unexpected-rebuild', 'wake',
                                              '%s rebuilt unexpectedly (%s): %s' % (name, entry['label'], entry['reason'][:300]),
                                              stage=name, label=entry['label']))
        elif entry['class'] == 'info':
            result['findings'].append(finding('reuse-note', 'info', '%s: %s' % (name, entry['reason'][:300]), stage=name))
    return result


def key_coverage(run):
    """Every stage whose read/call trace (profile/manifests/STAGE.json 'reads') holds repository code or files its
    fingerprint left out: an under-declared key, a wrong-reuse risk (BUILD-CHIM-KEY-UNDERDECLARED-35). The builder
    already refuses such a record as a reuse source; this makes it a finding of the run, for every stage."""
    findings = []
    folder = Path(run) / 'profile' / 'manifests'
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        manifest = load_json(path)
        reads = manifest.get('reads') if isinstance(manifest, dict) else None
        if not isinstance(reads, dict):
            continue
        stage = manifest.get('stage') or path.stem
        missed = list(reads.get('misses') or []) + list(reads.get('call_misses') or [])
        if missed:
            findings.append(finding('key-underdeclared', 'wake',
                                    '%s ran %d repository files/functions its fingerprint left out (first: %s): register a '
                                    'bug, fix the key (docs/BUILD_PROFILE.md, read trace)' % (stage, len(missed), missed[0]),
                                    stage=stage, missed=missed[:50]))
    return findings


def step_end(step):
    try:
        return float(step.get('started_seconds') or 0) + float(step.get('elapsed_seconds') or 0)
    except (TypeError, ValueError):
        return None


def time_to_fail(state, late_after):
    failed = [s for s in state.get('steps') or [] if s.get('status') == 'failed']
    if not failed:
        return None, []
    first = min(failed, key=lambda s: step_end(s) or 0)
    seconds = step_end(first)
    total = state.get('elapsed_seconds')
    info = {'stage': first.get('name'), 'seconds': seconds, 'returncode': first.get('returncode'),
            'build_seconds': total, 'failed_stages': [s.get('name') for s in failed]}
    findings = [finding('build-failed', 'wake', 'stage %s failed after %s s (rc %s)' % (
        first.get('name'), None if seconds is None else round(seconds), first.get('returncode')), stage=first.get('name'))]
    if seconds is not None and seconds > late_after:
        findings.append(finding('late-failure', 'wake', 'failure came %d s after the start (> %d s): a check that '
                                'could run first ran late' % (seconds, late_after), stage=first.get('name'),
                                seconds=round(seconds, 1)))
    return info, findings


def summary_checks(run, state):
    findings = []
    status = state.get('status')
    steps = state.get('steps') or []
    bad = [s.get('name') for s in steps if s.get('status') != 'passed']
    if status == 'passed' and bad:
        findings.append(finding('summary-mismatch', 'wake', 'status passed but stages not passed: ' + ', '.join(bad[:8])))
    if status == 'failed' and not [s for s in steps if s.get('status') == 'failed']:
        findings.append(finding('summary-mismatch', 'wake', 'status failed but no stage failed'))
    summary = load_json(run / 'build-summary.json')
    if status == 'passed':
        if summary is None:
            findings.append(finding('summary-missing', 'wake', 'passed build without build-summary.json'))
        else:
            if summary.get('status') != 'passed':
                findings.append(finding('summary-mismatch', 'wake', 'build-summary status %r' % summary.get('status')))
            sha = (summary.get('output') or {}).get('sha256') or ''
            if not re.fullmatch(r'[0-9a-f]{64}', sha):
                findings.append(finding('output-hash', 'wake', 'no SHA-256 for the build output in build-summary.json'))
            warnings = (summary.get('compiler_warnings') or {}).get('count')
            if warnings:
                findings.append(finding('compiler-warnings', 'wake', '%s compiler warnings (zero is the rule)' % warnings))
            coverage = summary.get('media_coverage') or {}
            if coverage and coverage.get('status') not in ('complete', None):
                findings.append(finding('media-coverage', 'wake', 'media coverage %s' % coverage.get('status')))
    return summary, findings


def exclude_effect(state, summary, media_ceiling):
    findings, info = [], {}
    commands = [' '.join(map(str, s.get('command') or [])) for s in state.get('steps') or []]
    joined = ' '.join(commands)
    info['exclude_video'] = '--exclude-video' in joined
    match = re.search(r'--exclude-unreferenced[ =](\S+)', joined)
    info['exclude_unreferenced'] = match.group(1) if match else None
    videos = ((((summary or {}).get('media_coverage') or {}).get('categories') or {}).get('videos') or {}).get('included')
    info['videos_included'] = videos
    if info['exclude_video'] and videos:
        findings.append(finding('exclude-no-effect', 'wake', '--exclude-video given but %s videos are in the payload' % videos))
    media = next((s for s in state.get('steps') or [] if s.get('name') == 'media'), None)
    if media is not None:
        try:
            seconds = float(media.get('elapsed_seconds') or 0)
        except (TypeError, ValueError):
            seconds = 0.0
        reused = bool(media.get('reused'))
        info['media_seconds'] = seconds
        if info['exclude_unreferenced'] and not reused and seconds > media_ceiling:
            findings.append(finding('exclude-late', 'wake', 'media stage took %d s with --exclude-unreferenced %s (> %d s): '
                                    'the exclusion did not apply before the import' % (seconds, info['exclude_unreferenced'],
                                                                                      media_ceiling), stage='media'))
    return info, findings


def audit(run, globs=DEFAULT_SUSPICIOUS, late_after=LATE_AFTER_SECONDS, media_ceiling=MEDIA_CEILING_SECONDS):
    run = Path(run)
    state = load_json(run / 'build-state.json')
    if not isinstance(state, dict):
        return None
    report = load_json(run / 'reuse-report.json')
    result = {'schema': SCHEMA, 'run': str(run), 'name': run.name, 'status': state.get('status'),
              'version': state.get('runtime_version'), 'started_at': state.get('build_started_at'),
              'elapsed_seconds': state.get('elapsed_seconds'), 'findings': []}
    if state.get('status') not in ('passed', 'failed'):
        result['findings'].append(finding('not-finished', 'info', 'run status %r: audited when it ends' % state.get('status')))
        return result
    reuse = reuse_audit(run, state, globs, report)
    result['reuse'] = {k: v for k, v in reuse.items() if k != 'findings'}
    result['findings'] += reuse['findings']
    result['findings'] += key_coverage(run)
    result['time_to_fail'], found = time_to_fail(state, late_after)
    result['findings'] += found
    summary, found = summary_checks(run, state)
    result['findings'] += found
    result['exclude'], found = exclude_effect(state, summary, media_ceiling)
    result['findings'] += found
    if summary:
        result['output_sha256'] = (summary.get('output') or {}).get('sha256')
    result['wake'] = any(f['severity'] == 'wake' for f in result['findings'])
    return result


def stage_files(run):
    """{stage: {path: sha256}} from RUN/profile/manifests/*.json (the stage output manifests)."""
    out = {}
    folder = Path(run) / 'profile' / 'manifests'
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        manifest = load_json(path)
        if isinstance(manifest, dict):
            out[path.stem] = {name: (info or {}).get('sha256') for name, info in (manifest.get('files') or {}).items()}
    return out


def compare_runs(run, reference, ignore=()):
    """File-by-file comparison of two runs' stage outputs (MANDATORY from-scratch check).

    Returns {'same': bool, 'stages': {stage: {'missing','extra','different'}}, 'output': {...}};
    paths matching an IGNORE glob (documented build-time stamps) are left out."""
    mine, theirs = stage_files(run), stage_files(reference)
    result = {'run': str(run), 'reference': str(reference), 'stages': {}, 'compared_files': 0}
    for stage in sorted(set(mine) | set(theirs)):
        a, b = mine.get(stage, {}), theirs.get(stage, {})
        keep = lambda p: not any(fnmatch.fnmatch(p, g) for g in ignore)  # noqa: E731
        missing = sorted(p for p in b if p not in a and keep(p))
        extra = sorted(p for p in a if p not in b and keep(p))
        different = sorted(p for p in a if p in b and a[p] != b[p] and keep(p))
        result['compared_files'] += len([p for p in a if p in b and keep(p)])
        if missing or extra or different:
            result['stages'][stage] = {'missing': missing[:50], 'extra': extra[:50], 'different': different[:50],
                                       'counts': [len(missing), len(extra), len(different)]}
    outputs = [((load_json(Path(r) / 'build-summary.json') or {}).get('output') or {}).get('sha256') for r in (run, reference)]
    result['output'] = {'run': outputs[0], 'reference': outputs[1], 'same': bool(outputs[0]) and outputs[0] == outputs[1]}
    result['same'] = not result['stages']
    if not mine or not theirs:
        result['same'] = False
        result['error'] = 'no stage output manifests in %s' % ('the run' if not mine else 'the reference')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run', type=Path)
    ap.add_argument('--json', action='store_true', help='print the audit as JSON')
    ap.add_argument('--compare', type=Path, metavar='REFERENCE_RUN',
                    help='instead of the audit: compare the stage outputs file by file with another run')
    ap.add_argument('--ignore', action='append', default=[], help='with --compare: glob of paths left out (repeatable)')
    ap.add_argument('--late-after', type=float, default=LATE_AFTER_SECONDS)
    ap.add_argument('--media-ceiling', type=float, default=MEDIA_CEILING_SECONDS)
    ap.add_argument('--suspicious', action='append', help='glob of files that must never key a stage (repeatable; '
                                                          'replaces the default list)')
    a = ap.parse_args(argv)
    if a.compare:
        result = compare_runs(a.run, a.compare, tuple(a.ignore))
        if a.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print('%s vs %s: %s (%d files compared; final output %s)' % (
                a.run.name, a.compare.name, 'SAME' if result['same'] else 'DIFFERENT', result['compared_files'],
                'identical' if result['output']['same'] else 'differs'))
            for stage, d in result['stages'].items():
                print('  %-20s missing %d, extra %d, different %d' % (stage, *d['counts']))
            if result.get('error'):
                print('  ' + result['error'])
        return 0 if result['same'] else 1
    result = audit(a.run, tuple(a.suspicious or DEFAULT_SUSPICIOUS), a.late_after, a.media_ceiling)
    if result is None:
        print('build_audit: %s is not a readable builder run (no build-state.json)' % a.run, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        reuse = result.get('reuse') or {}
        print('%s: %s, reused %s of %s stages from %s' % (result['name'], result['status'], reuse.get('reused', '-'),
                                                         reuse.get('stages', '-'), reuse.get('reuse_from') or '-'))
        for item in result['findings']:
            print('  %-5s %-18s %s' % (item['severity'].upper(), item['kind'], item['message']))
    return 1 if result.get('wake') else 0


if __name__ == '__main__':
    sys.exit(main())
