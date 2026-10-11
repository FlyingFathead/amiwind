#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Give CHIM frame maps already on disk their .chim name, without recomputing anything.

Builds before the .chim extension wrote frame maps as maps/<name>.bsp (docs/chim/WORLD_FORMAT.md, "Frame
maps"). This tool finds them in build workspaces by their worldspawn key "_chim_frame" (never by file name;
tools/map_files.py is_chim_frame reads only the header and the entity lump) and renames each to
maps/<name>.chim: a hard link under the new name, then the old name is removed. The bytes, the inode and
the content hash stay the same; nothing is copied or rebuilt. The far-terrain sidecar maps/<name>.far keeps
its name (the engine finds it by the map name).

Records follow: in the run folder that holds a renamed map, each stage output manifest
(profile/manifests/<stage>.json, schema amiwind-stage-outputs-v1) whose "files" entry names the old path
with the file's own SHA-256 gets the new path, and its hash tree is recomputed (unit_tree.of_manifest), so
reuse checks keep matching recorded hashes. Receipts that describe what a build wrote (build.json, gate
reports) are history and stay as written.

Never touched: anything outside the given roots; folders named releases, archive, retired or sealed (and
everything under them); run folders of a release (a version without a -suffix, or a purpose naming
release, final or rc, also in an older name such as final4c-...) or holding a SEALED marker; disk images (.hdf files are never opened). Content
pools store files by hash, without names: they need nothing.

    python3 tools/chim/frame_ext_migrate.py ROOT [ROOT ...]            # dry run: lists what it would rename
    python3 tools/chim/frame_ext_migrate.py ROOT [ROOT ...] --apply    # renames and updates manifests
    [--json REPORT]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from map_files import FRAME_EXT, LEGACY_EXT, is_chim_frame  # noqa: E402

PROTECTED = ('releases', 'archive', 'retired', 'sealed')
SEALED_MARKERS = ('SEALED', 'SEALED.txt', 'sealed.json')
MANIFEST_SCHEMA = 'amiwind-stage-outputs-v1'
# A run folder name (YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<git>): version and purpose.
# release, final, rc (with any tail: final4c, rc1c) as a word of a folder name
RELEASE_WORD = re.compile(r'(^|[-_])(release|final|rc)[0-9a-z]*([-_]|$)')
RUN_NAME = re.compile(r'^\d{4}_\d{2}_\d{2}_v(?P<version>\d+\.\d+\.\d+)(?P<suffix>-[A-Za-z0-9.]+)?_(?P<purpose>.+)_[0-9a-f]{6,}$')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def protected_reason(path):
    """Why PATH (a folder) must not be touched, or None."""
    path = Path(path)
    for part in path.parts:
        if part.lower() in PROTECTED:
            return 'protected folder %s' % part
    if any((path / m).exists() for m in SEALED_MARKERS):
        return 'sealed (marker file)'
    m = RUN_NAME.match(path.name)
    if m:
        if not m.group('suffix'):
            return 'release run (v%s without a -suffix)' % m.group('version')
        if RELEASE_WORD.search(m.group('purpose')):
            return 'release run (purpose %s)' % m.group('purpose')
    elif RELEASE_WORD.search(path.name):
        # an older run named before the naming rule (final4c-..., rc1c-...): a release build, kept as it is
        return 'release run (%s)' % path.name
    return None


def run_folder(path, stop):
    """The nearest folder above PATH (up to STOP) that holds stage manifests (profile/manifests), or None."""
    path = Path(path).parent
    stop = Path(stop)
    while True:
        if (path / 'profile' / 'manifests').is_dir():
            return path
        if path == stop or path.parent == path:
            return None
        path = path.parent


def find(roots):
    """(renames, skipped): frame maps named .bsp under the roots, by their key; protected folders skipped."""
    renames, skipped = [], []
    for root in roots:
        root = Path(root)
        reason = protected_reason(root)
        if reason:
            skipped.append({'path': str(root), 'reason': reason})
            continue
        for folder, dirs, files in os.walk(root):
            here = Path(folder)
            keep = []
            for d in sorted(dirs):
                why = protected_reason(here / d)
                if why:
                    skipped.append({'path': str(here / d), 'reason': why})
                else:
                    keep.append(d)
            dirs[:] = keep
            if here.name != 'maps':
                continue
            for name in sorted(files):
                if not name.lower().endswith(LEGACY_EXT):
                    continue
                source = here / name
                if source.is_symlink() or not is_chim_frame(source):
                    continue
                target = source.with_suffix(FRAME_EXT)
                row = {'from': str(source), 'to': str(target), 'bytes': source.stat().st_size,
                       'sha256': sha256(source), 'run': None}
                run = run_folder(source, root)
                if run is not None:
                    row['run'] = str(run)
                if target.exists():
                    if target.stat().st_ino == source.stat().st_ino or sha256(target) == row['sha256']:
                        row['state'] = 'duplicate name (same content): the .bsp name goes'
                    else:
                        row['state'] = 'conflict: %s holds other bytes; left alone' % target.name
                else:
                    row['state'] = 'rename'
                renames.append(row)
    return renames, skipped


def manifest_updates(run, rows):
    """{manifest path: manifest} for the stage manifests of RUN that name a renamed map with its own hash."""
    run = Path(run)
    by_rel = {}
    for row in rows:
        rel = Path(row['from']).relative_to(run).as_posix()
        by_rel[rel] = (Path(row['to']).relative_to(run).as_posix(), row['sha256'])
    out = {}
    for path in sorted((run / 'profile' / 'manifests').glob('*.json')):
        try:
            manifest = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict) or manifest.get('schema') != MANIFEST_SCHEMA:
            continue
        files = manifest.get('files') or {}
        hits = [rel for rel in files if rel in by_rel and files[rel].get('sha256') == by_rel[rel][1]]
        if not hits:
            continue
        renamed = {}
        for rel, value in files.items():
            renamed[by_rel[rel][0] if rel in hits else rel] = value
        manifest['files'] = renamed
        out[path] = (manifest, hits)
    return out


def apply(renames):
    """Rename (hard link, then unlink) and update each run's stage manifests. Returns the manifest rows."""
    done = []
    for row in renames:
        source, target = Path(row['from']), Path(row['to'])
        if row['state'] == 'rename':
            os.link(source, target)                 # the same inode under the new name: nothing copied
            if sha256(target) != row['sha256']:
                os.unlink(target)
                raise ValueError('content changed while renaming: ' + str(source))
            os.unlink(source)
            done.append(row)
        elif row['state'].startswith('duplicate'):
            os.unlink(source)
            done.append(row)
    manifests = []
    runs = sorted({row['run'] for row in done if row['run']})
    for run in runs:
        updates = manifest_updates(run, [r for r in done if r['run'] == run])
        for path, (manifest, hits) in updates.items():
            from unit_tree import of_manifest
            if 'tree' in manifest:
                manifest['tree'] = of_manifest(manifest)
            temporary = path.with_name(path.name + '.renaming')
            temporary.write_text(json.dumps(manifest, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
            os.replace(temporary, path)
            manifests.append({'manifest': str(path), 'renamed': hits})
    return manifests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roots', nargs='+', type=Path, help='build workspaces or run folders to search')
    ap.add_argument('--apply', action='store_true', help='rename (default: dry run, lists what it would do)')
    ap.add_argument('--json', type=Path, help='write the report here')
    a = ap.parse_args(argv)
    for root in a.roots:
        if not root.is_dir():
            ap.exit(1, 'Error: not a folder: %s\n' % root)
    renames, skipped = find(a.roots)
    report = {'mode': 'apply' if a.apply else 'dry-run', 'frame_maps': len(renames),
              'to_rename': sum(1 for r in renames if r['state'] == 'rename'),
              'conflicts': sum(1 for r in renames if r['state'].startswith('conflict')),
              'bytes': sum(r['bytes'] for r in renames), 'renames': renames, 'skipped': skipped}
    if a.apply:
        report['manifests'] = apply(renames)
    for row in renames:
        print('%s %s -> %s (%s)' % ('renamed' if a.apply and row['state'] == 'rename' else 'would rename'
                                    if row['state'] == 'rename' else 'skip', row['from'], Path(row['to']).name,
                                    row['state']))
    for row in skipped:
        print('not searched: %s (%s)' % (row['path'], row['reason']))
    print('%s: %d frame map(s) named .bsp found by their key, %d to rename, %d conflict(s), %d bytes (nothing copied)'
          % (report['mode'], report['frame_maps'], report['to_rename'], report['conflicts'], report['bytes']))
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
