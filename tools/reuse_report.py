#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reuse audit of a build run made with --reuse-from (docs/BUILD_PROFILE.md "Reuse audit").

Lists every stage that was NOT reused with the recorded reason, and classifies it:

- EXPECTED: a real input change (the stage's own fingerprint changed: its code, data files, game inputs,
  tools, settings or a stage it depends on), a stage that never reuses by policy (engine, the image), a stage
  that had not passed in the old run, an older fingerprint format, or a stage that follows an EXPECTED
  rebuild of a stage before it;
- UNEXPECTED: anything else (a record refused for an undeclared run-folder entry or an overlap, a missing or
  damaged old output, outputs of a rebuilt stage that differ although its inputs did not change, or a source
  change confined to files no stage output can depend on: the release file list, prose, tests). An unexpected
  rebuild is a builder bug: an over-broad key wastes time, an output that differs with unchanged inputs means
  non-deterministic output or an under-declared key.

  python3 tools/reuse_report.py RUN [--json FILE]      (or: tools/build.py --reuse-report RUN)

Exit status 0: every rebuild expected; 1: at least one unexpected; 2: not a --reuse-from run.
Read only.
"""
import argparse
import json
from pathlib import Path
import re
import sys

if str(Path(__file__).resolve().parent) not in sys.path:  # run as a script; never ahead of src/ when imported
    sys.path.append(str(Path(__file__).resolve().parent))

# Repository files no stage output can depend on: a change to only these that rebuilds a stage is an over-broad key.
NEVER_AN_INPUT = (re.compile(r'^tools/release-files\.json$'), re.compile(r'^docs/'), re.compile(r'\.md$'),
                  re.compile(r'^tests/'))
POLICY = ('engine', 'image', 'dry-run-image')


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def changed_sources(old, new):
    """Repository files whose part of the stage fingerprint changed (old/new: fingerprint components)."""
    old = ((old or {}).get('sources') or {}).get('by_file') or {}
    new = ((new or {}).get('sources') or {}).get('by_file') or {}
    return sorted(path for path in set(old) | set(new) if old.get(path) != new.get(path))


def upstream_difference(run, old_run, stage):
    """Why a rebuilt stage's outputs did not match its old run: its old record was refused (nothing to compare),
    or the files that differ (non-deterministic output when its inputs did not change)."""
    from build_cache import load_manifest, ran_manifest
    new, old = load_manifest(run, stage), ran_manifest(old_run, stage)
    if not new or not old:
        return f'{stage}: no record to compare'
    if not old.get('reusable'):
        return f"{stage}: old record refused ({'; '.join(old.get('reasons') or ['unknown'])[:120]})"
    if not new.get('reusable'):
        return f"{stage}: new record refused ({'; '.join(new.get('reasons') or ['unknown'])[:120]})"
    from unit_tree import describe, differences, of_manifest
    found = differences(new.get('tree') or of_manifest(new), old.get('tree') or of_manifest(old))
    return f'{stage}: {len(found)} units differ ({describe(found, 3)})' if found else f'{stage}: same outputs'


def classify(name, reason, ctx):
    """(class, cause, detail) for one stage that was not reused."""
    if name in POLICY or reason.startswith(('compiles with the Amiga SDK', 'final image')):
        return 'EXPECTED', 'policy', reason
    if reason.startswith('forced to run again'):
        return 'EXPECTED', 'forced', reason
    if reason.startswith('not passed in'):
        return 'EXPECTED', 'old run', reason
    if ' fingerprints, this builder makes ' in reason:
        return 'EXPECTED', 'fingerprint format', reason
    if reason.startswith('changed: '):
        old_parts, new_parts = ctx['old_details'].get(name), ctx['details'].get(name)
        if old_parts and new_parts:
            from build_cache import explain
            parts = explain(old_parts, new_parts)
            deps = sorted(d for d in set((old_parts.get('dependencies') or {})) | set((new_parts.get('dependencies') or {}))
                          if (old_parts.get('dependencies') or {}).get(d) != (new_parts.get('dependencies') or {}).get(d))
        else:  # no fingerprint details: the recorded text only
            text = reason[len('changed: '):]
            deps = [d.strip() for d in re.findall(r'dependency ([a-z0-9_, -]+?)(?=, [a-z_]+(?: \(|$|,)|$)', text)
                    for d in d.split(',')] if 'dependency ' in text else []
            parts = [part for part in re.split(r', (?=(?:sources|external_inputs|environment|command|python|'
                                                 r'packages|input_lock|tools))', text)]
        own = [part for part in parts if not part.startswith('dependency ')]
        # The changed files as the build saw them; the saved details only when the reason was cut short.
        listed = re.search(r'sources \(([^()]*)\)', reason)
        files = ([f.strip() for f in listed.group(1).split(',')] if listed and '+' not in listed.group(1)
                 else changed_sources(old_parts, new_parts))
        if own and all(part.startswith('sources') for part in own) and files \
                and all(any(rule.search(path) for rule in NEVER_AN_INPUT) for path in files):
            return 'UNEXPECTED', 'over-broad key', 'only files no output depends on changed: ' + ', '.join(files)
        if not own and deps and any(ctx['classes'].get(d) == 'UNEXPECTED' for d in deps):
            return 'UNEXPECTED', 'follows', 'follows an unexpected rebuild: ' + ', '.join(deps)
        return 'EXPECTED', 'input change', ', '.join(parts)
    if reason.startswith('old outputs not reusable') or reason.startswith(('no output manifest',
                                                                           'old output manifest incomplete',
                                                                           'old output ')):
        return 'UNEXPECTED', 'record refused', reason
    if reason.startswith(('reuse would depend on rebuilt stages', 'its output ')):
        return 'FOLLOWS', 'replaced outputs', reason
    if reason.startswith('an earlier stage it depends on ran again and its outputs differ'):
        upstream = [s.strip() for s in reason.rsplit(':', 1)[1].split(',')]
        if upstream and all(ctx['causes'].get(s) == 'input change' for s in upstream):
            return 'EXPECTED', 'upstream changed', reason
        # Which upstream stage really wrote different outputs, or whose old record could not be compared.
        notes = [upstream_difference(ctx['run'], ctx['old_run'], s) for s in upstream
                 if ctx['causes'].get(s) != 'input change']
        return 'UNEXPECTED', 'outputs differ', reason + ' [' + '; '.join(notes) + ']'
    if reason.startswith('its input '):
        return 'EXPECTED', 'input change', reason
    return 'UNEXPECTED', 'other', reason


def report(run):
    run = Path(run)
    state = load(run / 'build-state.json')
    if not state:
        raise ValueError('No build-state.json in ' + str(run))
    cache = state.get('stage_cache') or {}
    old_run = cache.get('reuse_from')
    if not old_run:
        return None
    details = load(run / 'profile' / 'fingerprints.json') or {}
    old_details = load(Path(old_run) / 'profile' / 'fingerprints.json') or {}
    reused = cache.get('reused') or {}
    not_reused = dict(cache.get('not_reused') or {})
    for name, row in reused.items():
        if row.get('refused'):
            not_reused[name] = row['refused']
    order = [step['name'] for step in state.get('steps', [])]
    ctx = {'details': details, 'old_details': old_details, 'classes': {}, 'causes': {}, 'run': run,
           'old_run': Path(old_run)}
    rows = []
    for name in sorted(not_reused, key=lambda n: order.index(n) if n in order else len(order)):
        verdict, cause, detail = classify(name, not_reused[name], ctx)
        ctx['classes'][name], ctx['causes'][name] = verdict, cause
        rows.append({'stage': name, 'class': verdict, 'cause': cause, 'reason': not_reused[name], 'detail': detail})
    # A stage that only follows replaced outputs takes the class of the rebuild it follows.
    for row in rows:
        if row['class'] == 'FOLLOWS':
            named = re.findall(r'by ([a-z0-9_-]+), which is rebuilt', row['reason']) \
                or re.findall(r'and ([a-z0-9_-]+) \(reused\)', row['reason'])
            upstream = [ctx['classes'].get(n) for n in named]
            row['class'] = 'UNEXPECTED' if 'UNEXPECTED' in upstream else 'EXPECTED'
    stages = len(order)
    really_reused = len([n for n in reused if not reused[n].get('refused')])
    unexpected = [row for row in rows if row['class'] == 'UNEXPECTED']
    return {'format': 'AmiWind reuse audit 1', 'run': str(run), 'reuse_from': old_run, 'stages': stages,
            'reused': really_reused, 'rebuilt': len(rows), 'unexpected': len(unexpected), 'rows': rows}


TOO_BROAD = ('over-broad key', 'not in the source diff')


def source_diff(old_sources, files):
    """{'changed', 'added', 'removed', 'recorded'}: repository files whose content differs between the reuse
    source's recorded source tree (build-state.json source_sha256) and FILES ({path: sha256}, the checkout now)."""
    old_sources = old_sources or {}
    changed = sorted(path for path in old_sources if path in files and files[path] != old_sources[path])
    added = sorted(path for path in files if path not in old_sources)
    removed = sorted(path for path in old_sources if path not in files)
    return {'changed': changed, 'added': added, 'removed': removed, 'recorded': len(old_sources)}


def preflight(order, reasons, details, old_details, old_sources, files, reused=()):
    """Reuse preflight (BUILD-REUSE-KEYS-TOO-BROAD-35): before any stage runs, every stage the plan does not
    reuse, classified like the reuse audit, plus the check that the source diff explains it.

    A stage rebuilt only for a source change must name at least one file whose content really differs from
    the reuse source's recorded tree (or that the tree did not record); otherwise its key changed for no
    visible reason (UNEXPECTED). ORDER: the stage names; REASONS: {stage: reason not reused}; DETAILS /
    OLD_DETAILS: fingerprint components now and in the reuse source; OLD_SOURCES: its source_sha256; FILES:
    {path: sha256} now. Read only."""
    old_sources = old_sources or {}
    diff = source_diff(old_sources, files)
    moved = set(diff['changed']) | set(diff['removed']) | set(diff['added'])
    ctx = {'details': details, 'old_details': old_details, 'classes': {}, 'causes': {}, 'run': None, 'old_run': None}
    rows = []
    for name in order:
        if name not in reasons:
            continue
        verdict, cause, detail = classify(name, reasons[name], ctx)
        files_changed = changed_sources(old_details.get(name), details.get(name))
        touching = [path for path in files_changed if path in moved or path not in old_sources]
        if verdict == 'EXPECTED' and cause == 'input change' and files_changed and not touching:
            own = [part for part in explain_parts(old_details.get(name), details.get(name))
                   if not part.startswith(('sources', 'dependency '))]
            if not own:
                verdict, cause = 'UNEXPECTED', 'not in the source diff'
                detail = ('its source key changed, but none of these files differ from the reuse source: '
                          + ', '.join(files_changed[:6]))
        ctx['classes'][name], ctx['causes'][name] = verdict, cause
        rows.append({'stage': name, 'class': verdict, 'cause': cause, 'reason': reasons[name], 'detail': detail,
                     'diff_files': touching})
    for row in rows:
        if row['class'] == 'FOLLOWS':
            named = re.findall(r'by ([a-z0-9_-]+), which is rebuilt', row['reason']) \
                + re.findall(r'and ([a-z0-9_-]+) \(reused\)', row['reason'])
            row['class'] = 'UNEXPECTED' if 'UNEXPECTED' in [ctx['classes'].get(n) for n in named] else 'EXPECTED'
    taken = set(reused)
    return {'format': 'AmiWind reuse preflight 1', 'stages': len(order),
            'reused': sum(name in taken for name in order), 'rebuilt': len(rows),
            'unexpected': sum(row['class'] == 'UNEXPECTED' for row in rows),
            # Keys too broad (the preflight stops the build on these); a damaged or refused old record is
            # UNEXPECTED too, but the build simply runs the stage.
            'too_broad': [row['stage'] for row in rows if row['cause'] in TOO_BROAD
                          or (row['cause'] == 'follows' and any(ctx['causes'].get(d) in TOO_BROAD
                                                                for d in re.findall(r'[a-z0-9_-]+', row['detail'].split(':', 1)[-1])))],
            'policy': sum(row['cause'] == 'policy' for row in rows), 'source_diff': diff, 'rows': rows}


def explain_parts(old, new):
    if not old or not new:
        return []
    from build_cache import explain
    return explain(old, new)


def print_preflight(result, stream=None, accepted=False):
    """The preflight table: per stage, reuse or rebuild with the reason and the changed files that touch it."""
    stream = stream or sys.stdout
    diff = result['source_diff']
    print(f"Reuse preflight: {result['reused']} of {result['stages']} stages planned for reuse, {result['rebuilt']} "
          f"rebuilt ({result['policy']} by policy), {result['unexpected']} UNEXPECTED. Source diff against the reuse "
          f"source: {len(diff['changed'])} changed, {len(diff['added'])} added, {len(diff['removed'])} removed files.",
          file=stream)
    for row in result['rows']:
        mark = '!!' if row['class'] == 'UNEXPECTED' else '  '
        files = row.get('diff_files') or []
        more = f' (+{len(files) - 5} more)' if len(files) > 5 else ''
        touched = f" | changed files: {', '.join(files[:5])}{more}" if files else ''
        print(f"{mark} rebuild {row['stage']:<24} {row['class']:<10} {row['cause']}: {row['detail'][:200]}{touched}",
              file=stream)
    reusable = result['stages'] - result['policy']
    rebuilt = result['rebuilt'] - result['policy']
    if reusable and result['reused'] == 0:
        print(f"!! NONE of the {reusable} reusable stages is reused - check the reasons above.", file=stream)
    elif reusable and rebuilt * 2 > reusable:
        print(f"!! {rebuilt} of {reusable} reusable stages are not reused - check.", file=stream)
    if result['too_broad']:
        print(f"!! {len(result['too_broad'])} rebuild(s) not explained by the source diff or the inputs (a key too "
              f"broad: {', '.join(result['too_broad'][:6])}): "
              + ('accepted with --accept-rebuild.' if accepted else
                 'stopping before any stage runs. Fix the key, or pass --accept-rebuild to build anyway.'),
              file=stream)
    elif result['unexpected']:
        print(f"!! {result['unexpected']} UNEXPECTED rebuild(s) (old records refused or damaged): the stages run; "
              "check the reuse source.", file=stream)


def plan_main(argv=None):
    """`build.py --reuse-plan OLD_RUN`: the preflight alone, read only, in seconds (no game data read)."""
    parser = argparse.ArgumentParser(prog='build.py --reuse-plan',
                                     description='Reuse preflight: which stages of OLD_RUN this checkout would reuse')
    parser.add_argument('old_run', type=Path)
    parser.add_argument('--fingerprint-scope', choices=('units', 'symbols', 'modules'), default='units')
    parser.add_argument('--accept-rebuild', action='store_true', help='exit 0 even with unexpected rebuilds')
    parser.add_argument('--json', type=Path, help='also write the preflight as JSON')
    args = parser.parse_args(argv)
    import build_cache
    try:
        result = build_cache.predict_preflight(args.old_run, args.fingerprint_scope)
    except (OSError, ValueError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 2
    print_preflight(result, accepted=args.accept_rebuild)
    print("(A dry run with the reuse source's own commands and game inputs; the build also checks outputs, so it "
          "can only reuse fewer stages.)")
    if args.json:
        args.json.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    return 1 if result['too_broad'] and not args.accept_rebuild else 0


def print_report(result, stream=None):
    stream = stream or sys.stdout  # looked up at call time (redirected output)
    print(f"Reuse audit: {result['reused']} of {result['stages']} stages reused from {Path(result['reuse_from']).name}, "
          f"{result['rebuilt']} rebuilt, {result['unexpected']} unexpected", file=stream)
    for row in result['rows']:
        mark = '!!' if row['class'] == 'UNEXPECTED' else '  '
        print(f"{mark} {row['class']:<10} {row['stage']:<26} {row['cause']}: {row['detail'][:240]}", file=stream)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('run', type=Path)
    parser.add_argument('--json', type=Path, help='also write the audit as JSON')
    args = parser.parse_args(argv)
    try:
        result = report(args.run)
    except ValueError as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 2
    if result is None:
        print(f'{args.run}: not a --reuse-from run; nothing to audit.')
        return 2
    print_report(result)
    if args.json:
        args.json.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    return 1 if result['unexpected'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
