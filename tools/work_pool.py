#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""One shared work pool: jobs lease a workspace (owner, purpose, quota, expiry) instead of keeping their own.

Layout of a work pool ROOT (one folder or volume shared by every job):

    ROOT/pool.json                  capacity and reserve of the pool
    ROOT/leases/LEASE.json          one lease per job workspace
    ROOT/work/LEASE/                the leased workspace (build workspace, scratch, play copy)

Rules (docs/BUILD_CACHE.md "Work pool"):
  * a lease names its owner (job), purpose, quota and expiry; a lease is granted only while the quotas of
    all active leases plus the new one fit the pool's capacity minus its reserve, so no job can fill the
    machine: a job that does not fit waits for a lease instead;
  * inputs and outputs come into a workspace by hard link from the shared content pool
    (tools/storage_pool.py): bytes shared with the pool or another workspace do not count against the
    quota, only bytes the workspace alone holds do;
  * a workspace over its quota is reported over quota, and `enforce --on-over-quota CMD` runs CMD for that
    lease only (for example a command that pauses the job's container): the job is paused, not the machine;
  * the job returns its lease when it ends (`return`); returned and expired leases are handed to the
    garbage collector (tools/build_gc.py --work-pool ROOT), which removes their workspaces with the same
    dry-run-first rules as everything else.

Commands:
  work_pool.py init ROOT --capacity GB [--reserve GB]
  work_pool.py lease ROOT --owner JOB --purpose TEXT --quota GB (--hours N | --expires ISO) [--container NAME]
  work_pool.py usage ROOT [--json]
  work_pool.py enforce ROOT [--on-over-quota CMD]      CMD may use {id} {owner} {container} {path} {used} {quota}
  work_pool.py return ROOT LEASE
  work_pool.py link ROOT LEASE POOL SHA256 RELATIVE   place a pooled object in the workspace (read-only link)
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shlex
import stat as stat_module
import subprocess
import sys
import uuid

SCHEMA = 'amiwind-work-pool-v1'
GB = 1000 ** 3
ACTIVE, OVER, RETURNED, EXPIRED = 'active', 'over-quota', 'returned', 'expired'
LIVE = (ACTIVE, OVER)
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_time(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    with open(temporary, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=1, sort_keys=True)
        handle.write('\n')
    os.replace(temporary, path)


class WorkPool:
    def __init__(self, root):
        self.root = Path(root)

    @property
    def config(self):
        try:
            return json.loads((self.root / 'pool.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError(f'{self.root} is not a work pool (run: work_pool.py init ROOT --capacity GB)')

    def init(self, capacity, reserve=0):
        if capacity <= reserve:
            raise ValueError('capacity must be larger than the reserve')
        _write(self.root / 'pool.json', {'schema': SCHEMA, 'capacity_bytes': int(capacity), 'reserve_bytes': int(reserve)})
        (self.root / 'leases').mkdir(parents=True, exist_ok=True)
        (self.root / 'work').mkdir(parents=True, exist_ok=True)

    def leases(self):
        found = []
        folder = self.root / 'leases'
        for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
            try:
                lease = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if lease.get('state') in LIVE and now() > parse_time(lease['expires']):
                lease['state'] = EXPIRED
                self.save(lease)
            found.append(lease)
        return found

    def get(self, lease_id):
        for lease in self.leases():
            if lease['id'] == lease_id:
                return lease
        raise ValueError(f'no lease {lease_id} in {self.root}')

    def save(self, lease):
        _write(self.root / 'leases' / f"{lease['id']}.json", lease)

    def lease(self, owner, purpose, quota, expires, container=None):
        """Grant a lease if every live quota plus QUOTA fits the capacity minus the reserve; the lease dict."""
        if not owner or not purpose:
            raise ValueError('a lease needs an owner and a purpose')
        if quota <= 0:
            raise ValueError('a lease needs a positive quota')
        config = self.config
        committed = sum(lease['quota_bytes'] for lease in self.leases() if lease['state'] in LIVE)
        room = config['capacity_bytes'] - config['reserve_bytes'] - committed
        if quota > room:
            raise ValueError(f'lease refused: {quota / GB:,.1f} GB asked, {max(room, 0) / GB:,.1f} GB free of quota '
                             f'in the pool ({committed / GB:,.1f} GB leased); wait for a lease to be returned')
        slug = re.sub(r'[^A-Za-z0-9._-]+', '-', owner).strip('-')[:40] or 'job'
        lease_id = f'{slug}-{uuid.uuid4().hex[:8]}'
        path = self.root / 'work' / lease_id
        path.mkdir(parents=True)
        lease = {'schema': SCHEMA, 'id': lease_id, 'owner': owner, 'purpose': purpose, 'quota_bytes': int(quota),
                 'created': stamp(now()), 'expires': stamp(expires), 'state': ACTIVE, 'container': container,
                 'path': str(path)}
        self.save(lease)
        return lease

    def used(self, lease):
        """Bytes only this workspace holds: files linked from the content pool or other workspaces are free."""
        total = 0
        seen = set()
        for here, _, names in os.walk(lease['path']):
            for name in names:
                try:
                    info = os.lstat(Path(here) / name)
                except OSError:
                    continue
                if not stat_module.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) in seen:
                    continue
                seen.add((info.st_dev, info.st_ino))
                if info.st_nlink == 1:
                    total += info.st_size
        return total

    def usage(self):
        rows = []
        for lease in self.leases():
            used = self.used(lease) if lease['state'] in LIVE and Path(lease['path']).is_dir() else 0
            rows.append(dict(lease, used_bytes=used))
        return rows

    def enforce(self, command=None, run=subprocess.run):
        """Mark live leases over or back under quota; run COMMAND for each lease newly over quota. The over leases."""
        over = []
        for row in self.usage():
            if row['state'] not in LIVE:
                continue
            lease = {key: value for key, value in row.items() if key != 'used_bytes'}
            if row['used_bytes'] > row['quota_bytes']:
                over.append(row)
                if lease['state'] != OVER:
                    lease['state'] = OVER
                    lease['over_since'] = stamp(now())
                    self.save(lease)
                    if command:
                        values = {key: shlex.quote(str(row.get(key) or '')) for key in ('id', 'owner', 'container', 'path')}
                        values.update(used=row['used_bytes'], quota=row['quota_bytes'])
                        run(command.format(**values), shell=True, check=False)
            elif lease['state'] == OVER:
                lease['state'] = ACTIVE
                lease.pop('over_since', None)
                self.save(lease)
        return over

    def give_back(self, lease_id):
        lease = self.get(lease_id)
        lease['state'] = RETURNED
        lease['returned'] = stamp(now())
        self.save(lease)
        return lease

    def link(self, lease_id, pool, digest, relative):
        """Place the content pool's object DIGEST at RELATIVE in the workspace (read-only hard link)."""
        import storage_pool
        lease = self.get(lease_id)
        if lease['state'] not in LIVE:
            raise ValueError(f'lease {lease_id} is {lease["state"]}')
        target = (Path(lease['path']) / relative).resolve()
        if Path(lease['path']).resolve() not in target.parents:
            raise ValueError(f'{relative} is outside the workspace')
        if not storage_pool.place(pool, digest, target):
            raise ValueError(f'{digest} is not in the content pool {pool}')
        return target

    def registry_items(self):
        """Owner registry for tools/build_gc.py: live leases are active, returned and expired ones are done."""
        return [{'path': lease['path'], 'owner': lease['owner'], 'purpose': lease['purpose'],
                 'state': 'active' if lease['state'] in LIVE else 'done', 'lease': lease['id']}
                for lease in self.leases()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('init')
    p.add_argument('root', type=Path)
    p.add_argument('--capacity', type=float, required=True, help='GB the pool may hold')
    p.add_argument('--reserve', type=float, default=0, help='GB kept free beyond every quota')
    p = sub.add_parser('lease')
    p.add_argument('root', type=Path)
    p.add_argument('--owner', required=True)
    p.add_argument('--purpose', required=True)
    p.add_argument('--quota', type=float, required=True, help='GB')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--hours', type=float)
    group.add_argument('--expires')
    p.add_argument('--container')
    p = sub.add_parser('usage')
    p.add_argument('root', type=Path)
    p.add_argument('--json', action='store_true')
    p = sub.add_parser('enforce')
    p.add_argument('root', type=Path)
    p.add_argument('--on-over-quota', metavar='CMD')
    p = sub.add_parser('return')
    p.add_argument('root', type=Path)
    p.add_argument('lease')
    p = sub.add_parser('link')
    p.add_argument('root', type=Path)
    p.add_argument('lease')
    p.add_argument('pool', type=Path)
    p.add_argument('sha256')
    p.add_argument('relative')
    args = parser.parse_args(argv)
    pool = WorkPool(args.root)
    try:
        if args.action == 'init':
            pool.init(args.capacity * GB, args.reserve * GB)
            print(f'Work pool {args.root}: {args.capacity:,.1f} GB, reserve {args.reserve:,.1f} GB')
        elif args.action == 'lease':
            expires = now() + timedelta(hours=args.hours) if args.hours else parse_time(args.expires)
            lease = pool.lease(args.owner, args.purpose, int(args.quota * GB), expires, args.container)
            print(json.dumps(lease, indent=1, sort_keys=True))
        elif args.action == 'usage':
            rows = pool.usage()
            if args.json:
                print(json.dumps(rows, indent=1, sort_keys=True))
            for row in rows if not args.json else []:
                print(f"{row['id']}  {row['state']:10} {row['used_bytes'] / GB:8,.2f} / {row['quota_bytes'] / GB:,.2f} GB  "
                      f"{row['owner']}: {row['purpose']} (expires {row['expires']})")
        elif args.action == 'enforce':
            over = pool.enforce(args.on_over_quota)
            for row in over:
                print(f"over quota: {row['id']} ({row['owner']}) {row['used_bytes'] / GB:,.2f} of {row['quota_bytes'] / GB:,.2f} GB")
            return 3 if over else 0
        elif args.action == 'return':
            pool.give_back(args.lease)
            print(f'returned {args.lease}; its workspace is collected by tools/build_gc.py')
        else:
            print(pool.link(args.lease, args.pool, args.sha256, args.relative))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
