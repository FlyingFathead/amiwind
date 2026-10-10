#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The one garbage collector for build workspaces, the shared storage pool and job scratch.

One retention policy, applied the same way everywhere (docs/BUILD_CACHE.md):

  kept (pinned)    release and release-candidate references, the newest passed run of every build
                   line (the latest verified reuse source), and every owner pin (pins.json);
  kept (active)    items whose owning job is still running (registry state "active"), and runs that
                   are still building;
  expires          run folders, played or smoke disk copies, package and extraction scratch and test
                   workspaces whose owning job is done (registry state "done"); scratch left inside a
                   finished run; pooled objects nothing links to or names any more; pool temporaries
                   older than a day;
  unregistered     anything else: REPORTED with its size, never deleted (an item nobody owns is a
                   finding, not garbage).

Sizes are what deleting would really free: a file shared by hard links (a pooled object linked into
several runs) is counted only when every one of its links is in the deletion set.

Dry run by default: the collector prints the list (path, kind, owner, reason, bytes freed) and
writes it as JSON with --json. Only --delete removes anything, and only items whose decision is
"expire" (never pinned, active or unregistered items). --item PATH limits deletion to the listed
items (the owner approves a list; the collector deletes exactly that list).

Registry (--registry FILE, JSON): {"items": [{"path": "...", "owner": "job", "purpose": "...",
"state": "active"|"done", "expires": "with-job"|"never"}]}; paths absolute or relative to the root
they are under. Pins (WORKSPACE/cache/pins.json, or --pins FILE): {"pins": [{"path": "build/RUN",
"kind": "release"|"rc"|"reuse-source"|"owner", "reason": "..."}]}; `build_gc.py pin` and `unpin` edit it.

Commands:
  build_gc.py plan ROOT... [--workspace W ...] [--registry FILE] [--pins FILE] [--work-pool ROOT] [--pool DIR]
                           [--json FILE]
  build_gc.py plan ... --delete [--item PATH ...]
  build_gc.py pin WORKSPACE RUN --kind owner --reason TEXT
  build_gc.py unpin WORKSPACE RUN
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat as stat_module
import sys
import time

SCHEMA = 'amiwind-build-gc-v1'
PINS = 'pins.json'
POOL = 'cache/asset-pool-v1'
PIN_KINDS = ('release', 'rc', 'reuse-source', 'owner')
KEEP, EXPIRE, UNREGISTERED = 'keep', 'expire', 'unregistered'
# A run whose state says "running" but whose folder has not changed for this long is reported stale.
STALE_RUNNING_SECONDS = 6 * 3600
TEMPORARY_AGE_SECONDS = 86400
TEMPORARY_SUFFIXES = ('.pool-tmp', '.amiwind-reuse-tmp', '.tmp')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with open(temporary, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=1, sort_keys=True)
        handle.write('\n')
    os.replace(temporary, path)


# --------------------------------------------------------------------------
# Inventory

class Inodes:
    """Regular files of each item, by inode, so sizes count a hard-linked file once and only when it frees space."""

    def walk(self, path):
        """[(path, inode, size, st_nlink)] of the regular files under PATH (or PATH itself)."""
        found = []
        path = Path(path)
        if path.is_symlink() or path.is_file():
            entries = [path]
        else:
            entries = (Path(here) / name for here, _, names in os.walk(path) for name in names)
        for entry in entries:
            try:
                info = os.lstat(entry)
            except OSError:
                continue
            if not stat_module.S_ISREG(info.st_mode):
                continue
            inode = (info.st_dev, info.st_ino)
            found.append((os.path.normpath(str(entry)), inode, info.st_size, info.st_nlink))
        return found

    def freed(self, members):
        """Bytes really freed by deleting every file in MEMBERS (lists from walk), hard links considered."""
        links = {}
        sizes = {}
        for files in members:
            for path, inode, size, nlink in files:
                links.setdefault(inode, set()).add(path)  # by path: overlapping items count a link once
                sizes[inode] = (size, nlink)
        return sum(size for inode, (size, nlink) in sizes.items() if len(links[inode]) >= nlink)


def run_state(folder):
    state = load_json(Path(folder) / 'build-state.json', {})
    return state if isinstance(state, dict) else {}


def run_line(state):
    """The build line a run belongs to: its recorded line, else version and builder type."""
    if state.get('line'):
        return str(state['line'])
    builder = state.get('builder') or (state.get('builder_options') or {}).get('builder') or 'legacy'
    return f"{state.get('runtime_version') or 'unknown'}:{builder}:{state.get('recipe') or 'build'}"


def newest_mtime(folder, limit=2000):
    """Newest modification time of FOLDER and a bounded sample of its entries (a liveness hint)."""
    newest = 0.0
    seen = 0
    for here, directories, names in os.walk(folder):
        for name in directories + names:
            try:
                newest = max(newest, os.lstat(Path(here) / name).st_mtime)
            except OSError:
                pass
            seen += 1
            if seen >= limit:
                return newest
    return newest


class Registry:
    """Owner registry: which job owns which path, and whether that job is still active."""

    def __init__(self, items, roots):
        self.items = []
        for item in items or ():
            path = Path(item['path'])
            candidates = [path] if path.is_absolute() else [Path(root) / path for root in roots]
            for candidate in candidates:
                self.items.append(dict(item, resolved=os.path.normpath(str(candidate))))

    def owner(self, path):
        """The most specific registry item containing PATH, or None."""
        path = os.path.normpath(str(path))
        best = None
        for item in self.items:
            base = item['resolved']
            if path == base or path.startswith(base.rstrip(os.sep) + os.sep):
                if best is None or len(base) > len(best['resolved']):
                    best = item
        return best


def load_pins(workspaces, extra=None):
    """[(resolved path, pin)] from every workspace's cache/pins.json and --pins files."""
    pins = []
    for workspace in workspaces:
        for pin in load_json(Path(workspace) / 'cache' / PINS, {}).get('pins', []):
            pins.append((os.path.normpath(str(Path(workspace) / pin['path'])), pin))
    for path in extra or ():
        data = load_json(path, {})
        for pin in data.get('pins', []):
            base = Path(pin['path'])
            if not base.is_absolute():
                base = Path(path).parent / base
            pins.append((os.path.normpath(str(base)), pin))
    return pins


def pinned(path, pins):
    path = os.path.normpath(str(path))
    for base, pin in pins:
        if path == base or path.startswith(base.rstrip(os.sep) + os.sep):
            return pin
    return None


def referenced_objects(pool):
    """SHA-256 values named by the pool's reuse keys and by prerendered manifests stored in it."""
    names = set()
    keys = Path(pool) / 'keys'
    for here, _, files in os.walk(keys):
        for name in files:
            if name.endswith('.json'):
                meta = load_json(Path(here) / name, {})
                if isinstance(meta, dict) and meta.get('sha256'):
                    names.add(meta['sha256'])
                    # A manifest key (a CHIMport cell, tools/chimport.py) also names the objects it lists.
                    objects = (meta.get('facts') or {}).get('objects') if isinstance(meta.get('facts'), dict) else None
                    if isinstance(objects, list):
                        names.update(str(o) for o in objects)
    return names


# --------------------------------------------------------------------------
# Planning

def pool_items(pool, add, now_seconds):
    """The retention rules for one storage pool: an object nothing links to and no key names expires; a pool
    temporary older than a day expires."""
    if not (Path(pool) / 'objects').is_dir():
        return
    named = referenced_objects(pool)
    orphans, temporaries = [], []
    for here, _, names in os.walk(Path(pool) / 'objects'):
        for name in names:
            path = Path(here) / name
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if name.endswith(TEMPORARY_SUFFIXES):
                if now_seconds - info.st_mtime > TEMPORARY_AGE_SECONDS:
                    temporaries.append(path)
            elif info.st_nlink == 1 and name not in named:
                orphans.append(path)
    for path in orphans:
        add(path, 'pool-object', EXPIRE, 'pooled object no run links and no reuse key names')
    for path in temporaries:
        add(path, 'pool-temporary', EXPIRE, 'pool temporary older than a day')


def plan(roots, workspaces=(), registry_items=None, pin_files=None, now_seconds=None, extra_pools=()):
    """The collector's decisions: [{path, kind, decision, reason, owner, files}] plus totals."""
    now_seconds = now_seconds or time.time()
    roots = [Path(root) for root in roots]
    workspaces = [Path(w) for w in workspaces] or [w for w in _find_workspaces(roots)]
    registry = Registry(registry_items, roots)
    pins = load_pins(workspaces, pin_files)
    inodes = Inodes()
    items = []
    covered = set()

    def add(path, kind, decision, reason, extra=None):
        owner = registry.owner(path)
        row = {'path': str(path), 'kind': kind, 'decision': decision, 'reason': reason,
               'owner': owner.get('owner') if owner else None, 'purpose': owner.get('purpose') if owner else None,
               'files': inodes.walk(path)}
        row.update(extra or {})
        items.append(row)
        covered.add(os.path.normpath(str(path)))
        return row

    def by_owner(path, kind, default_reason):
        """Pinned > active owner > done owner (expires) > unregistered (reported)."""
        pin = pinned(path, pins)
        if pin:
            return KEEP, f"pinned ({pin.get('kind', 'owner')}): {pin.get('reason', '')}".rstrip(': ')
        owner = registry.owner(path)
        if owner is None:
            return UNREGISTERED, 'no owner registered'
        if owner.get('expires') == 'never':
            return KEEP, f"kept by its owner {owner.get('owner')}"
        if owner.get('state') == 'done':
            return EXPIRE, f"{default_reason}; owning job {owner.get('owner')} is done"
        return KEEP, f"owning job {owner.get('owner')} is active"

    for workspace in workspaces:
        builds = workspace / 'build'
        runs = sorted(p for p in builds.iterdir() if p.is_dir()) if builds.is_dir() else []
        states = {run: run_state(run) for run in runs}
        newest = {}
        for run, state in states.items():
            if state.get('status') == 'passed':
                line = run_line(state)
                stamp = state.get('build_started_at') or ''
                if line not in newest or stamp > newest[line][0]:
                    newest[line] = (stamp, run)
        latest = {run: line for line, (_, run) in newest.items()}
        for run, state in states.items():
            status = state.get('status') or 'unknown'
            version = str(state.get('runtime_version') or '')
            extra = {'status': status, 'line': run_line(state), 'version': version}
            if status == 'running' and now_seconds - newest_mtime(run) < STALE_RUNNING_SECONDS:
                add(run, 'run', KEEP, 'still building', extra)
                continue
            scratch = run / 'scratch'
            if scratch.is_dir() and status in ('passed', 'failed', 'cancelled'):
                add(scratch, 'run-scratch', EXPIRE, f'scratch left in a {status} run', extra)
            pin = pinned(run, pins)
            if pin:
                add(run, 'run', KEEP, f"pinned ({pin.get('kind', 'owner')}): {pin.get('reason', '')}".rstrip(': '),
                    extra)
            elif run in latest:
                add(run, 'run', KEEP, f'latest passed run of line {latest[run]} (reuse source)', extra)
            else:
                decision, reason = by_owner(run, 'run', f'{status} run, superseded')
                add(run, 'run', decision, reason, extra)
        caches = workspace / 'cache'
        for cache in sorted(p for p in caches.iterdir() if p.is_dir()) if caches.is_dir() else []:
            if cache != workspace / POOL:
                add(cache, 'cache', KEEP, 'build cache (content-addressed, verified on use)')
        pool_items(workspace / POOL, add, now_seconds)
        covered.add(os.path.normpath(str(workspace)))
    # Pools named outside a workspace (--storage-pool-dir, AMIWIND_STORAGE_POOL): the same object rules.
    for pool in extra_pools or ():
        pool_items(Path(pool), add, now_seconds)
        covered.add(os.path.normpath(str(pool)))

    # Everything else under the roots: registered items by their owner; the rest reported.
    workspace_set = {os.path.normpath(str(w)) for w in workspaces}
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            normal = os.path.normpath(str(child))
            if normal in workspace_set or normal in covered:
                continue
            if any(normal.startswith(w + os.sep) for w in workspace_set):
                continue
            owned = [item for item in registry.items if item['resolved'].startswith(normal + os.sep)]
            if owned and not registry.owner(child):
                for item in owned:
                    if Path(item['resolved']).exists() and item['resolved'] not in covered:
                        decision, reason = by_owner(item['resolved'], 'item', 'job scratch')
                        add(Path(item['resolved']), _kind(item['resolved']), decision, reason)
                continue
            decision, reason = by_owner(child, 'item', 'job scratch')
            add(child, _kind(normal), decision, reason)
    return finish(items, inodes)


def _find_workspaces(roots):
    for root in roots:
        candidates = [root] + (sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else [])
        for candidate in candidates:
            if (candidate / 'build').is_dir() and (candidate / 'cache').is_dir():
                yield candidate


def _kind(path):
    name = Path(path).name.lower()
    if name.startswith('smoke') or name.endswith(('.hdf', '.adf')):
        return 'disk-copy'
    if name.startswith('pkg') or name.endswith('.zip'):
        return 'package'
    if name in ('src', 'p1', 'p2') or name.startswith('src'):
        return 'source-copy'
    return 'item'


def finish(items, inodes):
    for row in items:
        row['bytes'] = sum({inode: size for _, inode, size, _ in row['files']}.values())
        row['freed_alone'] = inodes.freed([row['files']])
    expire = [row for row in items if row['decision'] == EXPIRE]
    totals = {decision: {'items': 0, 'bytes': 0} for decision in (KEEP, EXPIRE, UNREGISTERED)}
    for row in items:
        totals[row['decision']]['items'] += 1
        totals[row['decision']]['bytes'] += row['bytes']
    totals['expire']['freed'] = inodes.freed([row['files'] for row in expire])
    for row in items:
        row['file_count'] = len(row.pop('files'))
    return {'schema': SCHEMA, 'created': now(), 'items': items, 'totals': totals}


# --------------------------------------------------------------------------
# Output and deletion

def human(value):
    return f'{value / 1e9:,.2f} GB'


def report(result, out=print):
    totals = result['totals']
    out(f"Garbage collector (dry run unless --delete): {totals['expire']['items']} items expire, "
        f"{human(totals['expire']['freed'])} freed; {totals['unregistered']['items']} unregistered "
        f"({human(totals['unregistered']['bytes'])}, reported only); {totals['keep']['items']} kept "
        f"({human(totals['keep']['bytes'])}).")
    for decision in (EXPIRE, UNREGISTERED, KEEP):
        rows = sorted((r for r in result['items'] if r['decision'] == decision), key=lambda r: -r['bytes'])
        if not rows:
            continue
        out(f'{decision.upper()}:')
        for row in rows:
            out(f"  {row['path']}  [{row['kind']}]  {human(row['bytes'])} (frees {human(row['freed_alone'])} alone)  "
                f"owner {row['owner'] or '-'}: {row['reason']}")


def _writable(function, path, _):
    os.chmod(os.path.dirname(path), stat_module.S_IRWXU)
    function(path)


def delete(result, only=None, out=print):
    """Delete the expired items (only those listed in ONLY when given). Returns the deleted paths."""
    wanted = {os.path.normpath(str(p)) for p in only} if only else None
    deleted = []
    for row in result['items']:
        if row['decision'] != EXPIRE:
            continue
        if wanted is not None and os.path.normpath(row['path']) not in wanted:
            continue
        path = Path(row['path'])
        if row['kind'] == 'run' and run_state(path).get('status') == 'running':
            out(f'[warning] {path}: started building again; not deleted')
            continue
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, onerror=_writable)
        else:
            continue  # already gone (inside an item deleted before it)
        deleted.append(str(path))
        out(f'Deleted {path} ({human(row["bytes"])})')
    if wanted is not None:
        missing = wanted - {os.path.normpath(p) for p in deleted}
        for path in sorted(missing):
            out(f'[warning] {path}: not an expired item of this plan; not deleted')
    return deleted


def edit_pin(workspace, run, kind=None, reason='', remove=False):
    path = Path(workspace) / 'cache' / PINS
    data = load_json(path, {'schema': SCHEMA, 'pins': []})
    relative = Path(run)
    if relative.is_absolute():
        relative = relative.relative_to(Path(workspace))
    relative = relative.as_posix()
    data['pins'] = [pin for pin in data.get('pins', []) if pin.get('path') != relative]
    if not remove:
        if kind not in PIN_KINDS:
            raise ValueError(f'pin kind must be one of {", ".join(PIN_KINDS)}')
        data['pins'].append({'path': relative, 'kind': kind, 'reason': reason, 'created': now()})
    data['schema'] = SCHEMA
    write_json(path, data)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan', help='list what the retention policy keeps, expires and cannot place (dry run)')
    p.add_argument('roots', nargs='*', type=Path, help='folders to inspect (a build volume, a workspace)')
    p.add_argument('--workspace', action='append', type=Path, default=[],
                   help='build workspace (default: every folder under the roots with build/ and cache/)')
    p.add_argument('--registry', type=Path, help='owner registry JSON')
    p.add_argument('--pins', action='append', type=Path, default=[], help='extra pins JSON')
    p.add_argument('--work-pool', action='append', type=Path, default=[],
                   help='work pool (tools/work_pool.py): its leases are owners; returned and expired ones expire')
    p.add_argument('--pool', action='append', type=Path, default=[],
                   help='a storage pool outside the workspaces (--storage-pool-dir / AMIWIND_STORAGE_POOL)')
    p.add_argument('--json', type=Path, help='write the plan here')
    p.add_argument('--delete', action='store_true', help='really delete the expired items (default: report only)')
    p.add_argument('--item', action='append', type=Path, help='with --delete: delete only these expired items')
    for name in ('pin', 'unpin'):
        p = sub.add_parser(name)
        p.add_argument('workspace', type=Path)
        p.add_argument('run', type=Path)
        if name == 'pin':
            p.add_argument('--kind', choices=PIN_KINDS, default='owner')
            p.add_argument('--reason', default='')
    args = parser.parse_args(argv)
    if args.action in ('pin', 'unpin'):
        edit_pin(args.workspace, args.run, getattr(args, 'kind', None), getattr(args, 'reason', ''),
                 remove=args.action == 'unpin')
        print(f'{args.action}ned {args.run}')
        return 0
    registry = load_json(args.registry, {}).get('items', []) if args.registry else []
    roots = list(args.roots)
    if args.work_pool:
        from work_pool import WorkPool
        for root in args.work_pool:
            registry += WorkPool(root).registry_items()
            roots.append(Path(root) / 'work')
    if not roots and not args.pool:
        parser.error('plan needs a folder, --work-pool or --pool')
    result = plan(roots, args.workspace, registry, args.pins, extra_pools=args.pool)
    report(result)
    if args.json:
        write_json(args.json, result)
    if args.delete:
        delete(result, args.item)
    elif args.item:
        parser.error('--item needs --delete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
