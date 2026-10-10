#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Entry check and developer mode: build from the right source, at the right version, on a working pool.

Three entry points share this module (docs/BUILD_CACHE.md "Entry check" and "Developer mode"):

- the IMPORT GUARD runs on every build (BUILD-IMAGE-STALE-PYTHONPATH-35): a builder module (tools/, src/)
  loaded from outside the source tree being built, or any module loaded from ANOTHER AmiWind builder tree
  (for example an old copy that a container image puts on PYTHONPATH), stops the build and names the module.
  Entries of PYTHONPATH and sys.path that point into another builder tree are dropped before any stage runs,
  so stage processes cannot import old code either;
- `build.py --check-entry [--working-version FILE]`: the read-only worker entry check, in seconds;
- `build.py --developer-mode` (alias --devmode): the same checks before any stage of a build, refusing a
  version mismatch, plus the run name and a reuse preflight summary; recorded in build-state.json
  ("developer_mode").

The working-version record (JSON) names the version being worked on and, optionally, the integration head:
    {"working_version": "0.0.35-dev1", "integration_head": "6dcb10e", ...}
It is looked up in this order (the first that exists wins):
    1. --working-version FILE
    2. the environment variable AMIWIND_WORKING_VERSION (a file path)
    3. WORKSPACE/../WORKING_VERSION.json (the build pool's top folder when WORKSPACE is one of its workspaces)
    4. WORKING_VERSION.json in the storage pool folder, then in its parent (WORKSPACE/cache)
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENV = 'AMIWIND_WORKING_VERSION'
RECORD = 'WORKING_VERSION.json'
FORMAT = 'AmiWind entry check 1'
BUG = 'BUILD-IMAGE-STALE-PYTHONPATH-35'


# --------------------------------------------------------------------------
# Source: which builder tree the running code comes from

def _resolved(path):
    try:
        return Path(path).resolve()
    except (OSError, RuntimeError):
        return Path(os.path.abspath(path))


def _inside(path, folder):
    return path == folder or folder in path.parents


def tree_root(folder):
    """The root of the AmiWind builder tree FOLDER belongs to (FOLDER itself, its tools/ or src/ folder,
    or a folder below them), or None. A builder tree has tools/build_aga.py."""
    folder = _resolved(folder)
    for candidate in [folder, *list(folder.parents)[:4]]:
        if (candidate / 'tools' / 'build_aga.py').is_file():
            return candidate
    return None


def own_module_names(root=ROOT):
    """Top-level module and package names the source tree provides from tools/ and src/."""
    names = set()
    for folder in (Path(root) / 'tools', Path(root) / 'src'):
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.suffix == '.py':
                names.add(entry.stem)
            elif entry.is_dir() and (entry / '__init__.py').is_file():
                names.add(entry.name)
    return names


def foreign_imports(root=ROOT, modules=None):
    """[(module, file, why)] for every loaded module that comes from the wrong place: a module name the source
    tree provides, loaded from outside it, or any module loaded from another AmiWind builder tree."""
    root = _resolved(root)
    modules = sys.modules if modules is None else modules
    own = own_module_names(root)
    trees = {}
    found = []
    for name, module in sorted(list(modules.items()), key=lambda item: item[0]):
        filename = getattr(module, '__file__', None)
        if not filename or not isinstance(filename, str):
            continue
        path = _resolved(filename)
        if _inside(path, root):
            continue
        folder = path.parent
        if folder not in trees:
            trees[folder] = tree_root(folder)
        other = trees[folder]
        if other is not None and other != root:
            found.append((name, str(path), f'from another builder tree {other}'))
        elif name.split('.')[0] in own:
            found.append((name, str(path), 'a builder module loaded from outside the source tree ' + str(root)))
    return found


def foreign_path_entries(entries, root=ROOT):
    """The entries of a search path (PYTHONPATH or sys.path) that point into another builder tree."""
    root = _resolved(root)
    bad = []
    for entry in entries:
        if not entry:
            continue
        other = tree_root(entry) if os.path.isdir(entry) else None
        if other is not None and other != root:
            bad.append(entry)
    return bad


def guard_imports(root=ROOT, modules=None, environ=None, path=None, log=print):
    """The always-on import guard (BUILD-IMAGE-STALE-PYTHONPATH-35): drops other builder trees from
    PYTHONPATH and sys.path (so no later import or stage process can load them) and returns the refusal
    text when a module was already loaded from the wrong place, else None."""
    environ = os.environ if environ is None else environ
    path = sys.path if path is None else path
    value = environ.get('PYTHONPATH', '')
    dropped = foreign_path_entries(value.split(os.pathsep), root)
    if dropped:
        kept = [entry for entry in value.split(os.pathsep) if entry not in dropped]
        if kept:
            environ['PYTHONPATH'] = os.pathsep.join(kept)
        else:
            environ.pop('PYTHONPATH', None)
        if log:
            log('Import guard: dropped another builder tree from PYTHONPATH: ' + ', '.join(dropped)
                + f' (the source being built is {_resolved(root)}; {BUG})')
    for entry in foreign_path_entries(list(path), root):
        while entry in path:
            path.remove(entry)
    found = foreign_imports(root, modules)
    if not found:
        return None
    return (f'Import guard ({BUG}): builder code was loaded from outside the source tree {_resolved(root)}:\n  '
            + '\n  '.join(f'{name}: {filename} ({why})' for name, filename, why in found)
            + '\nRun with PYTHONPATH unset or set to SOURCE/src:SOURCE/tools of the source being built.')


# --------------------------------------------------------------------------
# Working version

def find_record(explicit=None, workspace=None, pool=None, environ=None):
    """(path, origin) of the working-version record, or (None, reason). Order: see the module docstring."""
    environ = os.environ if environ is None else environ
    if explicit:
        return Path(explicit), '--working-version'
    if environ.get(ENV):
        return Path(environ[ENV]), ENV
    candidates = []
    if workspace is not None:
        candidates.append((Path(workspace).absolute().parent / RECORD, 'WORKSPACE/../' + RECORD))
    if pool is not None:
        candidates.append((Path(pool) / RECORD, 'storage pool'))
        candidates.append((Path(pool).parent / RECORD, 'storage pool parent'))
    for candidate, origin in candidates:
        if candidate.is_file():
            return candidate, origin
    return None, 'no working-version record found (' + ', '.join(origin for _, origin in candidates) + ')' \
        if candidates else 'no working-version record given'


def read_record(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(record, dict) or not isinstance(record.get('working_version'), str):
        raise ValueError(f'{path}: a working-version record needs "working_version" (a string)')
    return record


def source_version(root=ROOT):
    return (Path(root) / 'VERSION').read_text(encoding='utf-8').strip()


# --------------------------------------------------------------------------
# Integration head

def contains_commit(root, commit, source_commit=None, run=subprocess.run):
    """(True|False|None, detail): whether the source contains COMMIT. None = cannot tell (no git checkout or
    no git program); with SOURCE_COMMIT (an exported tree) only an equal commit counts."""
    git = Path(root) / '.git'
    if git.exists():
        try:
            result = run(['git', '-C', str(root), 'merge-base', '--is-ancestor', commit, 'HEAD'],
                         capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            # No git program (a container): HEAD read from the .git files still proves the equal case.
            import run_name
            head = run_name.git_head(root) or (source_commit or '').lower()
            if head and head.startswith(commit.lower()):
                return True, f'HEAD is {commit}'
            return None, f'git is not usable here ({exc.__class__.__name__}); HEAD is ' + (head[:7] or 'unknown')
        if result.returncode == 0:
            return True, f'HEAD contains {commit}'
        if result.returncode == 1:
            return False, f'HEAD does not contain {commit}'
        return None, 'git: ' + (result.stderr.strip().splitlines() or ['unknown error'])[-1]
    if source_commit:
        short = min(len(source_commit), len(commit))
        if source_commit[:short].lower() == commit[:short].lower():
            return True, f'--source-commit {source_commit} is {commit}'
        return None, f'not a git checkout: --source-commit {source_commit} cannot be checked against {commit}'
    return None, 'not a git checkout and no --source-commit'


# --------------------------------------------------------------------------
# Storage pool

def pool_check(pool, probe=False, uid=None):
    """{'path', 'exists', 'writable', 'owner_uid', 'build_uid', 'hardlinks', 'ok', 'note'}. PROBE writes and
    removes two tiny files in the pool to prove hard links work (developer mode); without it read only."""
    pool = Path(pool)
    uid = (os.geteuid() if hasattr(os, 'geteuid') else None) if uid is None else uid
    row = {'path': str(pool), 'exists': pool.is_dir(), 'writable': False, 'owner_uid': None, 'build_uid': uid,
           'hardlinks': None, 'ok': False, 'note': ''}
    if not row['exists']:
        row['note'] = 'missing: the first pooled build creates it; until then outputs are stored in the run (no linking)'
        return row
    try:
        row['owner_uid'] = pool.stat().st_uid
    except OSError:
        pass
    row['writable'] = os.access(pool, os.W_OK | os.X_OK)
    if not row['writable']:
        row['note'] = f'not writable by uid {uid}: the build stores outputs in the run instead (cache never fails a build)'
        return row
    if not probe:
        row['ok'] = True
        row['note'] = 'hard links not probed (read-only check)'
        return row
    first = second = None
    try:
        handle, name = tempfile.mkstemp(prefix='.entry-check-', dir=pool)
        os.close(handle)
        first = Path(name)
        second = first.with_name(first.name + '.link')
        os.link(first, second)
        row['hardlinks'] = first.stat().st_nlink == 2
    except OSError as exc:
        row['hardlinks'] = False
        row['note'] = f'hard link probe failed ({exc.__class__.__name__}: {exc}); reuse falls back to copies'
    finally:
        for item in (second, first):
            if item is not None:
                try:
                    item.unlink()
                except OSError:
                    pass
    row['ok'] = bool(row['hardlinks'])
    if row['ok']:
        row['note'] = 'writable, hard links work'
    return row


# --------------------------------------------------------------------------
# Run name

def run_name_check(name, version):
    """(ok, detail) for the naming rule YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort>."""
    pattern = (r'\d{4}_\d{2}_\d{2}_v' + re.escape(version)
               + r'_[A-Za-z0-9][A-Za-z0-9.-]*?(-try[0-9]+)?_([0-9a-f]{4,40}|nogit)')
    if re.fullmatch(pattern, name or ''):
        return True, name
    return False, f'{name!r} does not follow YYYY_MM_DD_v{version}_<purpose>[-tryN]_<gitshort>'


# --------------------------------------------------------------------------
# The check

def check(root=ROOT, working_version=None, workspace=None, pool=None, source_commit=None, run_name=None,
          reuse_from=None, scope='units', probe_pool=False, accept_mismatch=None, modules=None, environ=None,
          git=subprocess.run):
    """Every entry check; returns the record (also stored in build-state.json "developer_mode").
    record['refusals'] lists what stops the build; record['warnings'] what only warns."""
    root = Path(root)
    refusals, warnings = [], []
    record = {'format': FORMAT, 'source': str(_resolved(root))}
    # (a) working version
    version = source_version(root)
    path, origin = find_record(working_version, workspace, pool, environ)
    entry = {'source_version': version, 'record': str(path) if path else None, 'from': origin}
    wanted = None
    if path is None:
        warnings.append('working version: ' + origin + f'; set --working-version FILE or {ENV}')
    else:
        try:
            data = read_record(path)
        except (OSError, ValueError) as exc:
            data = None
            refusals.append(f'working version: cannot read {path}: {exc}')
        if data is not None:
            wanted = data['working_version']
            entry['working_version'] = wanted
            entry['integration_head'] = data.get('integration_head')
            if wanted != version:
                text = f'source VERSION {version} != working version {wanted} ({path})'
                if accept_mismatch:
                    warnings.append(text + f'; accepted: {accept_mismatch}')
                    entry['accepted_mismatch'] = accept_mismatch
                else:
                    refusals.append('working version: ' + text
                                    + '; work on the current version, or give --accept-version-mismatch REASON')
    entry['ok'] = wanted == version
    record['working_version'] = entry
    # (b) source
    found = foreign_imports(root, modules)
    record['source_imports'] = {'ok': not found, 'foreign': [{'module': n, 'file': f, 'why': w} for n, f, w in found]}
    for name, filename, why in found:
        refusals.append(f'source: module {name} from {filename} ({why})')
    # (c) integration head
    head = entry.get('integration_head')
    if head:
        contained, detail = contains_commit(root, head, source_commit, run=git)
        record['integration_head'] = {'commit': head, 'contained': contained, 'detail': detail}
        if contained is False:
            refusals.append(f'integration head: {detail}; merge the integration head first')
        elif contained is None:
            warnings.append(f'integration head: cannot check {head}: {detail}')
    else:
        record['integration_head'] = {'commit': None, 'contained': None, 'detail': 'the record names no integration head'}
    # (d) storage pool
    if pool is not None:
        row = pool_check(pool, probe=probe_pool)
        record['pool'] = row
        if not row['ok']:
            warnings.append('storage pool: ' + row['path'] + ': ' + row['note'])
    # (e) run name
    if run_name is not None:
        ok, detail = run_name_check(run_name, version)
        record['run_name'] = {'name': run_name, 'ok': ok, 'detail': detail}
        if not ok:
            warnings.append('run name: ' + detail)
    # (f) reuse preflight
    if reuse_from is not None:
        record['reuse_preflight'] = reuse_summary(reuse_from, scope, root)
        if record['reuse_preflight'].get('error'):
            warnings.append('reuse preflight: ' + record['reuse_preflight']['error'])
    record['refusals'], record['warnings'] = refusals, warnings
    record['ok'] = not refusals
    return record


def reuse_summary(reuse_from, scope='units', root=ROOT):
    try:
        import build_cache
        result = build_cache.predict_preflight(Path(reuse_from), scope, root=root)
    except Exception as exc:  # a preflight problem never stops the check; the build's own preflight runs later
        return {'reuse_from': str(reuse_from), 'error': f'{exc.__class__.__name__}: {exc}'}
    return {'reuse_from': str(reuse_from), 'stages': result.get('stages'), 'reused': result.get('reused'),
            'rebuilt': result.get('rebuilt'), 'unexpected': result.get('unexpected'),
            'too_broad': result.get('too_broad', [])}


def lines(record, title='Developer mode'):
    """The printed block."""
    out = ['=' * 72, f'{title}: ' + ('OK' if record['ok'] else 'REFUSED') + f" (source {record['source']})"]
    wv = record['working_version']
    out.append(f"  (a) working version: source {wv['source_version']}, record "
               + (f"{wv.get('working_version')} ({wv['record']}, from {wv['from']})" if wv['record'] else wv['from']))
    imports = record['source_imports']
    out.append('  (b) source: ' + ('every builder module from the source tree' if imports['ok']
                                   else f"{len(imports['foreign'])} module(s) from elsewhere"))
    head = record['integration_head']
    out.append('  (c) integration head: ' + (f"{head['commit']}: {head['detail']}" if head['commit'] else head['detail']))
    if 'pool' in record:
        out.append(f"  (d) storage pool: {record['pool']['path']}: {record['pool']['note'] or 'ok'}")
    if 'run_name' in record:
        out.append('  (e) run name: ' + ('ok ' if record['run_name']['ok'] else '') + record['run_name']['detail'])
    if 'reuse_preflight' in record:
        pre = record['reuse_preflight']
        out.append('  (f) reuse preflight: ' + (pre['error'] if pre.get('error') else
                   f"{pre['reused']} of {pre['stages']} stages reusable, {pre['rebuilt']} rebuilt, "
                   f"{pre['unexpected']} unexpected" + (', keys too broad: ' + ', '.join(pre['too_broad'])
                                                        if pre['too_broad'] else '')))
    for text in record['warnings']:
        out.append('  WARNING: ' + text)
    for text in record['refusals']:
        out.append('  REFUSED: ' + text)
    out.append('=' * 72)
    return out


def main(argv=None, workspace_default=None, pool_for=None):
    """`build.py --check-entry`: read-only, prints the block, exit 0 (ok) or 1 (refused)."""
    import argparse
    parser = argparse.ArgumentParser(prog='build.py --check-entry',
                                     description='Read-only worker entry check: version, source, integration head, pool')
    parser.add_argument('--working-version', type=Path, metavar='FILE')
    parser.add_argument('--workspace', type=Path, default=workspace_default)
    parser.add_argument('--source-commit', metavar='HASH')
    parser.add_argument('--name', help='a run name to check against the naming rule')
    parser.add_argument('--accept-version-mismatch', metavar='REASON')
    parser.add_argument('--json', action='store_true', help='print the record as JSON instead of the block')
    args = parser.parse_args(argv)
    message = guard_imports(log=None)
    pool = pool_for(args) if pool_for and args.workspace is not None else None
    record = check(working_version=args.working_version, workspace=args.workspace, pool=pool,
                   source_commit=args.source_commit, run_name=args.name,
                   accept_mismatch=args.accept_version_mismatch)
    if message and not record['refusals']:
        record['refusals'].append(message)
        record['ok'] = False
    if args.json:
        print(json.dumps(record, indent=2))
    else:
        print('\n'.join(lines(record, 'Entry check')))
    return 0 if record['ok'] else 1


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'src'))
    raise SystemExit(main(workspace_default=ROOT / 'out'))
