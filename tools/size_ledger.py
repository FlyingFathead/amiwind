#!/usr/bin/env python3
"""Size ledger: what the game data of a build weighs, per folder, in GiB (docs/BUILD_OUTPUT.md "Size ledger").

After the image step the builder groups the payload bytes of every partition by folder (classic maps, CHIM world,
NPC gallery, sound, music, video, progs, other), records each drive image's size, and compares the result with
the previous release's own record and, when given, a previous build's record (--size-baseline FILE). The previous
release is the one tools/previous-release.json names; its record is the ledger of its release build in the same
workspace (the newest passed run named ..._v<version>_release[-tryN]_<git>), else tools/size-baseline.json when that
is of the same release; a record of an older release is never compared (BUILD-SIZE-GUARD-OLD-BASELINE-45). Exact bytes stay in size-ledger.json in the run folder (and in build-summary.json); the
table prints GiB with two decimals.

Builds that do not hold the same content are never compared as like-for-like: an image without the NPC gallery,
a partial-area (MiniWind) image or one with excluded content (for example video) is labelled, its differences are
shown as "not like-for-like" and the size guard does not judge them.

The size guard: a folder that grew by more than the margin (default 0.05 GiB) against a like-for-like record
fails the build unless the growth is named (--size-growth-reason TEXT). In the default mode (auto) a -devN build
only warns; rc and final builds fail. --size-guard fail|warn|off overrides that.

The ledger is read from what the image step already left in the run: image/build.json (partitions, drives,
CHIM volume), the boot partition's staging folder image/boot and image/world-partitions.json (the world
partitions' file lists). Each partition's grouped bytes are checked against the payload bytes the image step
read back; a difference is named in the ledger's checks and the ledger says "partial".

Usage:
  python3 tools/size_ledger.py show RUN [--baseline FILE ...]   print the table (nothing written)
  python3 tools/size_ledger.py baseline RUN OUT [--note TEXT]     write a baseline record from a finished run
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from map_files import FRAME_EXT

SCHEMA = 'amiwind-size-ledger-v1'
FILE_NAME = 'size-ledger.json'
ROOT = Path(__file__).resolve().parents[1]
RELEASE_BASELINE = ROOT / 'tools' / 'size-baseline.json'
GIB = 1024 ** 3
DEFAULT_MARGIN_GIB = 0.05
GUARD_EXIT = 4   # the stages passed and their outputs are valid; the size guard failed the build result
GROUPS = ('classic-maps', 'chim-world', 'npc-gallery', 'sound', 'music', 'video', 'actors', 'progs', 'other')
# Stage 0 of the actor disk plan (docs/MODULAR_NPCS.md "Disk size plan for the actors"): the actors are their own
# group, so the size guard stops their silent growth: id1/progs/a_<id>[_m].* (standing and mover models with their
# animation and tag files) and id1/progs/skins (their skins); 39% of the v0.0.51 image.
ACTOR_PREFIX = 'a_'
ACTOR_FOLDERS = ('skins',)
TITLES = {'classic-maps': 'classic maps', 'chim-world': 'CHIM world', 'npc-gallery': 'NPC gallery',
          'sound': 'sound', 'music': 'music', 'video': 'video', 'actors': 'actors', 'progs': 'progs', 'other': 'other'}
FOLDERS = {'gallery': 'npc-gallery', 'sound': 'sound', 'music': 'music', 'intro': 'video', 'progs': 'progs',
           'chim': 'chim-world'}
CHIM_MAP_SUFFIXES = (FRAME_EXT, '.far')   # CHIM frame maps (tools/map_files.py) and their far terrain
VIDEO_SUFFIXES = ('.awv',)
DEV_VERSION = re.compile(r'-dev[0-9]+$')


def group_of(path):
    """The ledger group of a payload path relative to its partition root (e.g. id1/maps/vf0001.bsp)."""
    parts = path.replace('\\', '/').split('/')
    name = parts[-1].lower()
    if name.endswith(VIDEO_SUFFIXES):
        return 'video'
    if parts[0] != 'id1' or len(parts) < 3:
        return 'other'
    folder = parts[1].lower()
    if folder == 'maps':
        return 'chim-world' if name.endswith(CHIM_MAP_SUFFIXES) else 'classic-maps'
    if folder == 'progs' and ((len(parts) == 3 and name.startswith(ACTOR_PREFIX))
                              or (len(parts) > 3 and parts[2].lower() in ACTOR_FOLDERS)):
        return 'actors'
    return FOLDERS.get(folder, 'other')


def gib(value):
    """Bytes as GiB with two decimals; never "-0.00"."""
    text = '%.2f' % (value / GIB)
    return '0.00' if text in ('-0.00', '0.00') else text


def signed_gib(value):
    text = gib(value)
    return text if text == '0.00' or text.startswith('-') else '+' + text


def empty_groups():
    return {name: {'bytes': 0, 'files': 0} for name in GROUPS}


def add(groups, path, size):
    row = groups[group_of(path)]
    row['bytes'] += size
    row['files'] += 1


def walk(folder):
    """(relative posix path, bytes) of every file under FOLDER."""
    for base, _, names in os.walk(folder):
        for name in names:
            full = os.path.join(base, name)
            yield Path(full).relative_to(folder).as_posix(), os.path.getsize(full)


def profile(record):
    """What content the image holds, from its image/build.json: the NPC gallery, a partial area, exclusions."""
    excluded = sorted(set((record.get('excluded_content') or {}).get('groups') or []))
    gallery = record.get('npc_gallery') or {}
    gallery_on = 'npc-gallery' not in excluded and gallery.get('status') not in ('disabled', 'omitted', None)
    build_type = record.get('build_type') or {}
    partial = None
    if build_type:
        partial = 'MiniWind %s (%s)' % (build_type.get('town') or '?', build_type.get('scope') or 'full')
    return {'npc_gallery': bool(gallery_on), 'partial_area': partial,
            'excluded': [name for name in excluded if name != 'npc-gallery']}


def labels(content):
    """Plain words for a content profile; empty for a complete build."""
    out = []
    if not content.get('npc_gallery'):
        out.append('gallery off')
    if content.get('partial_area'):
        out.append('partial area: ' + content['partial_area'])
    out.extend('%s excluded' % name for name in content.get('excluded') or [])
    return out


def comparable_key(content):
    return json.dumps({'npc_gallery': bool(content.get('npc_gallery')), 'partial_area': content.get('partial_area'),
                       'excluded': sorted(content.get('excluded') or [])}, sort_keys=True)


def collect(run):
    """The ledger of a finished run (no comparison, no guard). Raises ValueError without an image receipt."""
    run = Path(run)
    image = run / 'image'
    receipt_path = image / 'build.json'
    if not receipt_path.is_file():
        raise ValueError('no image receipt (%s)' % receipt_path)
    record = json.loads(receipt_path.read_text(encoding='utf-8'))
    world_lists = {}
    world_path = image / 'world-partitions.json'
    if world_path.is_file():
        for row in json.loads(world_path.read_text(encoding='utf-8')).get('partitions') or []:
            world_lists[row.get('partition')] = row.get('files') or []
    chim_partition = (record.get('chim_world') or {}).get('partition')
    groups = empty_groups()
    partitions, checks = [], []
    for row in record.get('partitions') or []:
        name, expected = row.get('partition'), int(row.get('payload_bytes') or 0)
        before = sum(group['bytes'] for group in groups.values())
        if name in world_lists and name == chim_partition:
            # compact layout (tools/layout_plan.py): the CHIM volume also holds the open-world frame maps
            source = 'chim volume (id1/chim) + world-partitions.json maps'
            listed = 0
            for item in world_lists[name]:
                add(groups, item['path'], int(item['bytes']))
                listed += int(item['bytes'])
            groups['chim-world']['bytes'] += expected - listed
            groups['chim-world']['files'] += int(row.get('files') or 0) - len(world_lists[name])
        elif name in world_lists:
            source = 'world-partitions.json'
            for item in world_lists[name]:
                add(groups, item['path'], int(item['bytes']))
        elif name == chim_partition:
            source = 'chim volume (id1/chim)'
            groups['chim-world']['bytes'] += expected
            groups['chim-world']['files'] += int(row.get('files') or 0)
        elif name == 'DH0' and (image / 'boot').is_dir():
            source = 'image/boot'
            for path, size in walk(image / 'boot'):
                add(groups, path, size)
        else:
            source = 'no file list (counted as other)'
            groups['other']['bytes'] += expected
            groups['other']['files'] += int(row.get('files') or 0)
            checks.append('%s: no file list; %d bytes counted as other' % (name, expected))
        grouped = sum(group['bytes'] for group in groups.values()) - before
        if grouped != expected:
            checks.append('%s: grouped %d bytes from %s, the image step read back %d'
                          % (name, grouped, source, expected))
        partitions.append({'partition': name, 'hdf_file': row.get('hdf_file'), 'payload_bytes': expected,
                           'grouped_bytes': grouped, 'source': source})
    drives = [{'file': row.get('file'), 'bytes': int(row.get('bytes') or 0)} for row in record.get('hdf_files') or []]
    content = profile(record)
    total = sum(group['bytes'] for group in groups.values())
    return {'schema': SCHEMA, 'version': record.get('version'), 'run': run.name,
            'created': time.strftime('%Y-%m-%d %H:%M %z'),
            'status': 'partial' if checks else 'complete', 'checks': checks,
            'content': content, 'labels': labels(content),
            'payload_bytes': total, 'receipt_payload_bytes': int(record.get('payload_bytes') or 0),
            'groups': groups, 'partitions': partitions,
            'drives': drives, 'drive_bytes': sum(row['bytes'] for row in drives)}


def load_record(path):
    """A size ledger or baseline record; ValueError when it is not one."""
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != SCHEMA or not isinstance(record.get('groups'), dict):
        raise ValueError('%s is not a size ledger record (schema %s)' % (path, SCHEMA))
    for name in GROUPS:
        if not isinstance((record['groups'].get(name) or {}).get('bytes', 0), int):
            raise ValueError('%s: groups.%s.bytes is not a whole number of bytes' % (path, name))
    return record


def compare(current, baseline, margin_bytes, role, source):
    """One comparison: per-folder deltas, whether it is like-for-like, and the folders over the margin."""
    same = comparable_key(current['content']) == comparable_key(baseline.get('content') or {})
    reasons = [] if same else ['this build: ' + (', '.join(current['labels']) or 'complete content'),
                               'record: ' + (', '.join(labels(baseline.get('content') or {})) or 'complete content')]
    rows, grown = [], []
    for name in GROUPS:
        now = current['groups'][name]['bytes']
        then = int((baseline['groups'].get(name) or {}).get('bytes', 0))
        rows.append({'group': name, 'bytes': now, 'baseline_bytes': then, 'delta_bytes': now - then})
        # a group the record does not have (a record made before the group existed, e.g. actors before v0.0.52)
        # is not judged: its bytes were counted in another group then
        if same and name in baseline['groups'] and now - then > margin_bytes:
            grown.append(name)
    total = int(baseline.get('payload_bytes') or sum(int((row or {}).get('bytes', 0))
                                                     for row in baseline['groups'].values()))
    return {'role': role, 'source': str(source), 'version': baseline.get('version'), 'run': baseline.get('run'),
            'like_for_like': same, 'not_comparable_because': reasons, 'rows': rows,
            'payload_delta_bytes': current['payload_bytes'] - total, 'baseline_payload_bytes': total,
            'grown_over_margin': grown}


def guard_mode(mode, version):
    if mode != 'auto':
        return mode
    return 'warn' if DEV_VERSION.search(version or '') else 'fail'


def judge(comparisons, mode, reason, margin_bytes):
    """The size guard's verdict: off, not-comparable, passed, named (growth with a reason), warned or failed."""
    record = {'mode': mode, 'margin_bytes': margin_bytes, 'reason': reason or None, 'grown': []}
    for row in comparisons:
        for name in row['grown_over_margin']:
            delta = next(item['delta_bytes'] for item in row['rows'] if item['group'] == name)
            record['grown'].append({'against': row['role'], 'group': name, 'delta_bytes': delta})
    if mode == 'off':
        record['verdict'] = 'off'
    elif not any(row['like_for_like'] for row in comparisons):
        record['verdict'] = 'not-comparable'
    elif not record['grown']:
        record['verdict'] = 'passed'
    elif reason:
        record['verdict'] = 'named'
    else:
        record['verdict'] = 'failed' if mode == 'fail' else 'warned'
    return record


def table_lines(ledger):
    """The short table printed at the end of the build."""
    comparisons = ledger.get('comparisons') or []
    head = '%-14s %8s' % ('folder (GiB)', 'this')
    for row in comparisons:
        title = 'v%s %s' % (row.get('version') or '?', row['role'])
        head += '  %18s' % (title[:18])
    lines = ['Size ledger: v%s, %s (%s; exact bytes in %s)'
             % (ledger.get('version'), ', '.join(ledger['labels']) or 'complete content', ledger['status'], FILE_NAME),
             head]
    for index, name in enumerate(GROUPS):
        line = '%-14s %8s' % (TITLES[name], gib(ledger['groups'][name]['bytes']))
        for row in comparisons:
            item = row['rows'][index]
            line += '  %8s %9s' % (gib(item['baseline_bytes']), signed_gib(item['delta_bytes']))
        lines.append(line)
    line = '%-14s %8s' % ('total payload', gib(ledger['payload_bytes']))
    for row in comparisons:
        line += '  %8s %9s' % (gib(row['baseline_payload_bytes']), signed_gib(row['payload_delta_bytes']))
    lines.append(line)
    lines.append('Drive images: ' + ', '.join('%s %s GiB' % (row['file'], gib(row['bytes'])) for row in ledger['drives'])
                 + ' (total %s GiB)' % gib(ledger['drive_bytes']))
    for row in comparisons:
        lines.append('Against v%s %s (%s): %s' % (row.get('version') or '?', row['role'], row['source'],
                     'like-for-like' if row['like_for_like']
                     else 'NOT like-for-like (' + '; '.join(row['not_comparable_because']) + ')'))
    lines.extend('Check: ' + text for text in ledger.get('checks') or [])
    guard = ledger.get('guard')
    if guard:
        lines.append(guard_line(guard))
    return lines


def guard_line(guard):
    margin = gib(guard.get('margin_bytes', 0))
    grown = ', '.join('%s %s GiB vs %s' % (TITLES[row['group']], signed_gib(row['delta_bytes']), row['against'])
                      for row in guard.get('grown') or [])
    text = {'off': 'off (--size-guard off)',
            'not-comparable': 'not judged (no like-for-like record)',
            'passed': 'passed (no folder grew more than %s GiB)' % margin,
            'named': 'growth named: %s (%s)' % (guard.get('reason'), grown),
            'warned': 'WARNING: grew more than %s GiB without a named reason: %s (--size-guard %s: warning only; '
                      '--size-growth-reason TEXT names it)' % (margin, grown, guard.get('mode')),
            'failed': 'FAILED: grew more than %s GiB without a named reason: %s (--size-growth-reason TEXT names '
                      'it)' % (margin, grown),
            'error': 'could not run: %s' % guard.get('detail')}[guard['verdict']]
    return 'Size guard: ' + text


PREVIOUS_RELEASE = ROOT / 'tools' / 'previous-release.json'
AUTO = 'auto'


def previous_release_version(path=PREVIOUS_RELEASE):
    """The version of the previous published release (tools/previous-release.json), or None."""
    try:
        version = json.loads(Path(path).read_text(encoding='utf-8')).get('version')
    except (OSError, ValueError, AttributeError):
        return None
    return str(version).lstrip('v') if version else None


def release_run_ledger(workspace, version, exclude=None):
    """The size ledger of the previous release's own build in WORKSPACE (the folder holding the run folders): the
    newest run named YYYY_MM_DD_v<VERSION>_release[-tryN]_<git> whose build passed and whose ledger is complete;
    (path, run name) or None. EXCLUDE: a run name never taken (the build being measured)."""
    pattern = re.compile(r'^\d{4}_\d{2}_\d{2}_v%s_release(?:-try(\d+))?_[0-9a-f]+$' % re.escape(version))
    found = []
    try:
        names = os.listdir(workspace)
    except OSError:
        return None
    for name in names:
        match = pattern.match(name)
        if not match or name == exclude:
            continue
        folder = Path(workspace) / name
        try:
            state = json.loads((folder / 'build-state.json').read_text(encoding='utf-8'))
            record = load_record(folder / FILE_NAME)
        except (OSError, ValueError):
            continue
        if state.get('status') == 'passed' and record.get('status') == 'complete':
            found.append((name[:10], int(match.group(1) or 1), name))
    if not found:
        return None
    name = max(found)[2]
    return Path(workspace) / name / FILE_NAME, name


def resolve_release_baseline(run, previous=None, committed=RELEASE_BASELINE):
    """(record path or None, note) of the release record a build is compared with: the previous release's own
    ledger (tools/previous-release.json names the release; its release build in the same workspace holds the
    ledger), else the committed record tools/size-baseline.json when it is of that release. A committed record of
    an older release is not used: it compared v0.0.45 with v0.0.41 and called 0.44 GiB of CHIM world growth that
    v0.0.42 to v0.0.44 had already shipped a failure (BUILD-SIZE-GUARD-OLD-BASELINE-45)."""
    previous = previous_release_version() if previous is None else previous
    run = Path(run)
    if not previous:
        return committed, 'no previous release named (tools/previous-release.json): the committed record'
    found = release_run_ledger(run.parent, previous, exclude=run.name)
    if found is not None:
        return found[0], 'v%s release build %s' % (previous, found[1])
    try:
        record = load_record(committed)
    except (OSError, ValueError) as exc:
        return None, 'no record of v%s (no release build of it in this workspace; %s)' % (previous, exc)
    if str(record.get('version') or '').lstrip('v') == previous:
        return committed, 'v%s committed record %s' % (previous, Path(committed).name)
    return None, ('no record of v%s: no release build of it in this workspace, and %s is of v%s (a record of another '
                  'release is not compared)' % (previous, Path(committed).name, record.get('version')))


def build_ledger(run, version, baselines=(), mode='auto', margin_gib=DEFAULT_MARGIN_GIB, reason=None,
                 release_baseline=AUTO):
    """Collect, compare and judge; returns the ledger (not written). RELEASE_BASELINE: a record file, None (no
    release comparison) or 'auto': the previous release's own record (resolve_release_baseline)."""
    ledger = collect(run)
    margin = int(round(margin_gib * GIB))
    comparisons = []
    if isinstance(release_baseline, str) and release_baseline == AUTO:
        release_baseline, note = resolve_release_baseline(run)
        ledger['release_baseline'] = {'record': str(release_baseline) if release_baseline else None, 'note': note}
        if release_baseline is None:
            ledger['checks'].append('release record: ' + note)
    sources = ([('release', Path(release_baseline))] if release_baseline else []) + \
              [('build', Path(path)) for path in baselines or ()]
    for role, path in sources:
        try:
            comparisons.append(compare(ledger, load_record(path), margin, role, path))
        except (OSError, ValueError) as exc:
            ledger['checks'].append('%s record %s not read: %s' % (role, path, exc))
    ledger['comparisons'] = comparisons
    ledger['guard'] = judge(comparisons, guard_mode(mode, version), reason, margin)
    return ledger


def write(run, ledger):
    path = Path(run) / FILE_NAME
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(ledger, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)
    return path


def read(run):
    """The run's ledger, or None (summary use; never raises)."""
    try:
        return json.loads((Path(run) / FILE_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def step(run, version, baselines=(), mode='auto', margin_gib=DEFAULT_MARGIN_GIB, reason=None,
         release_baseline=AUTO, log=print):
    """The builder's size ledger step: writes size-ledger.json; returns the guard verdict. A ledger that cannot
    be made is an "error" verdict: it fails the build where the guard would fail, else it warns."""
    if not (Path(run) / 'image' / 'build.json').is_file():
        log('Size ledger: skipped (no image receipt in this run: nothing to measure)')
        return 'skipped'
    log('Size ledger: started (1 worker: reads the image receipt and the payload file lists)')
    started = time.monotonic()
    effective = guard_mode(mode, version)
    try:
        ledger = build_ledger(run, version, baselines, mode, margin_gib, reason, release_baseline)
    except Exception as exc:  # noqa: BLE001 - reported, and judged like a failed guard in fail mode
        ledger = {'schema': SCHEMA, 'version': version, 'run': Path(run).name, 'status': 'error',
                  'guard': {'mode': effective, 'verdict': 'error', 'detail': '%s: %s' % (type(exc).__name__, exc)}}
        try:
            write(run, ledger)
        except OSError:
            pass
        log(guard_line(ledger['guard']))
        return 'failed' if effective == 'fail' else 'warned'
    path = write(run, ledger)
    log('Size ledger: written %s (took %.1f s)' % (path, time.monotonic() - started))
    return ledger['guard']['verdict']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    show = sub.add_parser('show', help='print the size table of a finished run (writes nothing)')
    show.add_argument('run', type=Path)
    show.add_argument('--baseline', type=Path, action='append', default=[], help='a previous build record')
    show.add_argument('--release-baseline', default=AUTO,
                      help='a release record (default auto: the previous release build\'s own ledger)')
    show.add_argument('--json', action='store_true')
    base = sub.add_parser('baseline', help='write a baseline record from a finished run')
    base.add_argument('run', type=Path)
    base.add_argument('out', type=Path)
    base.add_argument('--note', default='')
    args = parser.parse_args(argv)
    if args.command == 'show':
        ledger = build_ledger(args.run, None, args.baseline, 'warn', release_baseline=args.release_baseline)
        print(json.dumps(ledger, indent=1, sort_keys=True) if args.json else '\n'.join(table_lines(ledger)))
        return 0
    ledger = collect(args.run)
    if ledger['status'] != 'complete':
        raise SystemExit('refused: the ledger of %s is partial: %s' % (args.run, '; '.join(ledger['checks'])))
    record = {key: ledger[key] for key in ('schema', 'version', 'run', 'status', 'content', 'labels',
                                           'payload_bytes', 'groups', 'drives', 'drive_bytes')}
    record['note'] = args.note
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('\n'.join(table_lines(dict(ledger, comparisons=[], guard=None))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
