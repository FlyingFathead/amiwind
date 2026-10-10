#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Shared content-addressed storage pool: every stage output, disk image and package stored once.

The pool is the asset pool's object store (tools/file_cache.py): POOL/objects/SHA[:2]/SHA, one
file per content, named by its SHA-256. This module lets the rest of the builder put any file into
that store and place it in a run folder as a HARD LINK to the pooled object, so a second run, a
reused stage, a prerendered entry or a package that holds the same bytes costs no extra space:

  * put(pool, path)        store PATH once (by hard link when it is on the pool's file system, so
                           not even the first copy is written twice) and replace PATH by a link to
                           the pooled object; pooled files are read-only (a shared inode must never
                           be changed in place: writers replace files, they never edit them);
  * place(pool, sha, dst)  link the pooled object SHA to DST, verified against SHA (copied only
                           across file systems or when hard links cannot protect the object);
  * adopt(pool, folder)    put every regular file of FOLDER at or above a size limit (a finished
                           run, a prerendered entry, a package folder); dry run by default;
  * scan(roots)            report duplicate bytes under ROOTS by content hash, grouped by kind
                           (disk images, stage outputs, packages, caches); read-only.

Safety rules (tests/test_storage_pool.py):
  * the object's SHA-256 is checked when it is first stored and whenever a link is placed
    (place verifies the object unless the caller passes verify=False with a SHA-256 it has
    just checked itself); a damaged object is never linked and is replaced from a good copy;
  * as root (and on Windows) read-only modes do not protect a shared file: put skips pooling and
    place copies instead of linking; put also skips a file on another file system than the pool
    (pooling it would add a copy);
  * every change goes through a temporary name and a rename: a run folder never holds a partial
    file, and builds sharing one pool never see one;
  * the pool never deletes anything; tools/build_gc.py decides what expires.

Disk images that an emulator will write to (played copies) must be real copies, never links:
place(..., link=False) or an ordinary copy. Release candidates and finals may write to the pool,
but their stage outputs are built from scratch as always (the pool only saves space, it never
decides what is rebuilt).

Commands:
  storage_pool.py scan ROOT... [--min-size BYTES] [--json FILE] [--jobs N]
  storage_pool.py adopt POOL FOLDER... [--min-size BYTES] [--apply]
  storage_pool.py stats POOL
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
import json
import os
from pathlib import Path
import stat as stat_module
import sys
import threading

SCHEMA = 'amiwind-storage-pool-v1'
# Same object layout as the asset pool (tools/file_cache.py): one store for converter outputs,
# stage outputs, disk images and packages.
OBJECTS = 'objects'
# Small files cost more in links and metadata than they save; the builder pools files from 64 KiB.
DEFAULT_MIN_SIZE = 64 * 1024
TEMPORARY = '.pool-tmp'
SKIP_NAMES = {'build-state.json', 'build-profile.json', 'build-summary.json'}
IMAGE_SUFFIXES = ('.hdf', '.adf', '.img', '.iso', '.vhdx', '.hdz')
PACKAGE_SUFFIXES = ('.zip', '.7z', '.tar', '.tgz', '.gz', '.xz', '.lha', '.lzx')


# The pool folder: --storage-pool-dir DIR (builder and CHIMporter) > the build config key storage_pool_dir >
# this environment variable > WORKSPACE/cache/asset-pool-v1 (the default; unchanged when nothing is set).
# Several workspaces and the CHIMporter share ONE pool by naming the same folder.
ENV = 'AMIWIND_STORAGE_POOL'
CONFIG_KEY = 'storage_pool_dir'
DEFAULT_RELATIVE = Path('cache') / 'asset-pool-v1'


def default_dir(workspace):
    return Path(workspace) / DEFAULT_RELATIVE


def resolve_dir(workspace=None, cli=None, config=None, config_base=None, environ=None):
    """(pool folder, origin) by the order above. CONFIG is the build config's value (relative to CONFIG_BASE,
    the config file's folder); origin is 'option', 'build config', 'environment' or 'workspace default'."""
    environ = os.environ if environ is None else environ
    if cli:
        return Path(cli).expanduser().absolute(), 'option'
    if config:
        path = Path(config).expanduser()
        if not path.is_absolute() and config_base is not None:
            path = Path(config_base) / path
        return path.absolute(), 'build config'
    if environ.get(ENV):
        return Path(environ[ENV]).expanduser().absolute(), 'environment'
    if workspace is None:
        return None, 'none'
    return default_dir(workspace), 'workspace default'


def link_check(pool, folder):
    """Can files under FOLDER be hard-linked with POOL? (True, '') or (False, reason). Makes POOL if needed, never
    FOLDER; a probe file is linked and both names are removed again (hard links need one file system AND one
    mount)."""
    if not _can_protect():
        return False, 'hard links cannot be protected here (root or Windows)'
    folder, pool = Path(folder).absolute(), Path(pool)
    # The run folder may not exist yet (the builder makes it itself): probe its nearest existing folder.
    while not folder.is_dir() and folder.parent != folder:
        folder = folder.parent
    probe = folder / f'.pool-link-probe.{os.getpid()}.{threading.get_ident()}'
    other = pool / f'.pool-link-probe.{os.getpid()}.{threading.get_ident()}{TEMPORARY}'
    try:
        pool.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b'')
        os.link(probe, other)
        return True, ''
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            return False, f'{pool} is on another file system or mount than {folder}'
        return False, f'hard link from {folder} to {pool} failed ({exc.strerror or exc})'
    finally:
        for path in (probe, other):
            try:
                path.unlink()
            except OSError:
                pass


def setting(pool, origin, folder, log=print):
    """The pool record for a receipt: {'dir', 'origin', 'links', 'warning'}. When hard links between FOLDER (the
    run) and POOL are impossible, links is False and ONE loud warning is printed: callers then copy (never fail).
    As root or on Windows (the pool never links there, as before) the reason is recorded without the alarm."""
    links, reason = link_check(pool, folder)
    record = {'dir': str(pool), 'origin': origin, 'links': links, 'warning': None}
    if not links and not _can_protect():
        # Root or Windows: the pool never links there (put/adopt skip, reuse copies), as before; no alarm.
        record['warning'] = reason
    elif not links:
        record['warning'] = (f'STORAGE POOL WITHOUT HARD LINKS: {reason}. Reused files are COPIED instead of linked '
                             f'and outputs are not pooled (pooling would add a copy). Put the pool on the same '
                             f'file system and mount as the run to store every byte once.')
        log('[warning] ' + record['warning'])
    return record


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def object_path(pool, digest):
    return Path(pool) / OBJECTS / digest[:2] / digest


def _can_protect():
    """Hard links are safe only when a read-only mode stops writers: never for root, and not on Windows
    (a read-only file there cannot be replaced by a rename, which every writer of the builder relies on)."""
    if os.name == 'nt':
        return False
    return not (hasattr(os, 'geteuid') and os.geteuid() == 0)


def _temporary(path):
    return path.with_name(f'{path.name}.{os.getpid()}.{threading.get_ident()}{TEMPORARY}')


def _read_only(path):
    mode = stat_module.S_IMODE(os.stat(path).st_mode)
    if mode & 0o222:
        os.chmod(path, mode & ~0o222)


def _intact(path, digest):
    try:
        return path.is_file() and sha256_file(path) == digest
    except OSError:
        return False


def _store(pool, source, digest):
    """Make sure POOL holds DIGEST, from SOURCE (already hashed to DIGEST); the object path."""
    blob = object_path(pool, digest)
    if _intact(blob, digest):
        return blob
    blob.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary(blob)
    temporary.unlink(missing_ok=True)
    try:
        linked = False
        if _can_protect():
            try:
                os.link(source, temporary)
                linked = True
            except OSError as exc:
                if exc.errno not in (errno.EXDEV, errno.EPERM, errno.EMLINK, errno.ENOTSUP):
                    raise
        if not linked:
            with open(source, 'rb') as reader, open(temporary, 'wb') as writer:
                for block in iter(lambda: reader.read(1 << 20), b''):
                    writer.write(block)
        if sha256_file(temporary) != digest:
            raise OSError(f'{source} changed while it was pooled')
        _read_only(temporary)
        os.replace(temporary, blob)
    finally:
        temporary.unlink(missing_ok=True)
    return blob


def ensure(pool, source, digest):
    """The object path of DIGEST in POOL, pooling SOURCE (already known to have DIGEST) by a hard link if absent."""
    blob = object_path(pool, digest)
    if _intact(blob, digest):
        return blob
    return _store(pool, source, digest)


def place(pool, digest, target, link=True, verify=True, mode=None):
    """Put the pooled object DIGEST at TARGET (hard link, or a verified copy); False when not pooled."""
    blob = object_path(pool, digest)
    if verify and not _intact(blob, digest):
        return False
    if not blob.is_file():
        return False
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary(target)
    temporary.unlink(missing_ok=True)
    try:
        linked = False
        if link and _can_protect():
            try:
                os.link(blob, temporary)
                linked = True
            except OSError as exc:
                if exc.errno not in (errno.EXDEV, errno.EPERM, errno.EMLINK, errno.ENOTSUP):
                    raise
        if linked:
            _read_only(temporary)
        else:
            hasher = hashlib.sha256()
            with open(blob, 'rb') as reader, open(temporary, 'wb') as writer:
                for block in iter(lambda: reader.read(1 << 20), b''):
                    hasher.update(block)
                    writer.write(block)
            if hasher.hexdigest() != digest:
                raise OSError(f'pooled object {digest} is damaged')
            if mode is not None:
                os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def put(pool, path, digest=None):
    """Store PATH in POOL and make PATH a link to the pooled object. ('linked'|'already'|'skipped', sha, bytes saved)."""
    path = Path(path)
    info = os.stat(path)
    if not _can_protect():
        return 'skipped', digest, 0
    existing = Path(pool).absolute()
    while not existing.exists() and existing.parent != existing:
        existing = existing.parent
    try:
        pool_device = os.stat(existing).st_dev
    except OSError:
        pool_device = None
    if pool_device != info.st_dev:
        # Pooling across file systems would add a copy, never save one.
        return 'skipped', digest, 0
    digest = digest or sha256_file(path)
    before = _same_inode(object_path(pool, digest), info)
    blob = _store(pool, path, digest)
    if _same_inode(blob, info):
        # PATH itself is the pooled inode: it was stored by a link (no bytes written) or was pooled before.
        _read_only(path)
        return ('already' if before else 'linked'), digest, 0
    # The run's file is replaced by the pooled inode: its own bytes are freed once nothing else links them.
    saved = info.st_size if info.st_nlink == 1 else 0
    place(pool, digest, path, verify=False)
    return 'linked', digest, saved


def candidates(folder, min_size=DEFAULT_MIN_SIZE):
    """Regular files under FOLDER worth pooling (no symlinks, no temporaries, no build bookkeeping)."""
    folder = Path(folder)
    for here, directories, names in os.walk(folder):
        directories[:] = sorted(d for d in directories if d not in (OBJECTS, 'keys') or Path(here) != folder)
        for name in sorted(names):
            if name in SKIP_NAMES or name.endswith(TEMPORARY):
                continue
            path = Path(here) / name
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if stat_module.S_ISREG(info.st_mode) and info.st_size >= min_size:
                yield path, info


def adopt(pool, folders, min_size=DEFAULT_MIN_SIZE, apply=False, jobs=None, log=print):
    """Pool every file of FOLDERS (dry run unless APPLY). Summary dict."""
    pool = Path(pool)
    if apply and not _can_protect():
        log('Storage pool not used: hard links cannot be protected here (root or Windows); nothing pooled.')
        return {'schema': SCHEMA, 'apply': True, 'files': 0, 'bytes': 0, 'linked': 0, 'already': 0, 'skipped': 0,
                'saved_bytes': 0, 'duplicate_bytes': 0, 'errors': []}
    pool_root = pool.resolve()
    files = []
    for folder in folders:
        for path, info in candidates(folder, min_size):
            if pool_root in path.resolve().parents:
                continue
            files.append((path, info))
    summary = {'schema': SCHEMA, 'apply': bool(apply), 'files': len(files), 'bytes': sum(i.st_size for _, i in files),
               'linked': 0, 'already': 0, 'skipped': 0, 'saved_bytes': 0, 'duplicate_bytes': 0, 'errors': []}
    with ThreadPoolExecutor(max_workers=jobs or min(8, os.cpu_count() or 1)) as executor:
        digests = list(executor.map(lambda item: _safe_hash(item[0]), files))
    seen = {}
    lock = threading.Lock()
    for (path, info), digest in zip(files, digests):
        if digest is None:
            summary['errors'].append(f'{path}: unreadable')
            continue
        inode = (info.st_dev, info.st_ino)
        first = seen.setdefault(digest, inode)
        blob = object_path(pool, digest)
        pooled = blob.is_file()
        if first != inode or pooled and _same_inode(blob, info) is False:
            summary['duplicate_bytes'] += info.st_size
        if not apply:
            continue
        try:
            outcome, _, saved = put(pool, path, digest)
        except OSError as exc:
            summary['errors'].append(f'{path}: {exc}')
            continue
        with lock:
            summary[outcome] += 1
            summary['saved_bytes'] += saved
    verb = 'pooled' if apply else 'would pool (dry run; --apply to link)'
    log(f"Storage pool {pool}: {summary['files']} files, {summary['bytes'] / 1e9:,.2f} GB {verb}; "
        f"duplicate bytes {summary['duplicate_bytes'] / 1e9:,.2f} GB"
        + (f"; freed {summary['saved_bytes'] / 1e9:,.2f} GB ({summary['linked']} linked, {summary['already']} already "
           f"pooled, {summary['skipped']} skipped)" if apply else ''))
    for error in summary['errors']:
        log(f'[warning] {error}')
    return summary


def _safe_hash(path):
    try:
        return sha256_file(path)
    except OSError:
        return None


def _same_inode(blob, info):
    try:
        other = os.stat(blob)
    except OSError:
        return None
    return (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino)


def kind_of(relative):
    """Coarse kind of a file for the duplicate report: image, package, cache, stage-output, other."""
    lower = relative.lower()
    parts = lower.split('/')
    if lower.endswith(IMAGE_SUFFIXES):
        return 'image'
    if lower.endswith(PACKAGE_SUFFIXES):
        return 'package'
    if 'cache' in parts or any(part.startswith('cache') or part.startswith('asset-pool') for part in parts) \
            or 'prerendered' in lower:
        return 'cache'
    if 'build' in parts:
        return 'stage-output'
    return 'other'


def _quick_key(path, size):
    """Size plus the first and last MiB: a cheap filter before a full SHA-256."""
    digest = hashlib.sha256(str(size).encode())
    with open(path, 'rb') as stream:
        digest.update(stream.read(1 << 20))
        if size > 2 << 20:
            stream.seek(-(1 << 20), os.SEEK_END)
            digest.update(stream.read(1 << 20))
    return digest.hexdigest()


def scan(roots, min_size=DEFAULT_MIN_SIZE, jobs=None, log=print):
    """Duplicate bytes under ROOTS by content (read-only). Hard links of one inode count once."""
    by_size = {}
    totals = {'files': 0, 'bytes': 0, 'small_files': 0, 'small_bytes': 0, 'hardlinked_bytes': 0}
    inodes = set()
    for root in roots:
        root = Path(root)
        for here, directories, names in os.walk(root):
            directories.sort()
            for name in names:
                path = Path(here) / name
                try:
                    info = os.lstat(path)
                except OSError:
                    continue
                if not stat_module.S_ISREG(info.st_mode):
                    continue
                inode = (info.st_dev, info.st_ino)
                if inode in inodes:
                    totals['hardlinked_bytes'] += info.st_size
                    continue
                inodes.add(inode)
                totals['files'] += 1
                totals['bytes'] += info.st_size
                if info.st_size < min_size:
                    totals['small_files'] += 1
                    totals['small_bytes'] += info.st_size
                    continue
                relative = f'{root.as_posix().rstrip("/")}/{path.relative_to(root).as_posix()}'
                by_size.setdefault(info.st_size, []).append((path, relative))
    groups = [members for members in by_size.values() if len(members) > 1]
    log(f'Scanned {totals["files"]:,} files, {totals["bytes"] / 1e9:,.1f} GB; '
        f'{sum(len(g) for g in groups):,} files share a size with another ({len(groups):,} sizes): hashing them.')
    workers = jobs or min(4, os.cpu_count() or 1)

    def keyed(fn, members):
        with ThreadPoolExecutor(max_workers=workers) as executor:
            keys = list(executor.map(lambda item: _try(fn, item), members))
        buckets = {}
        for member, key in zip(members, keys):
            if key is not None:
                buckets.setdefault(key, []).append(member)
        return [(key, bucket) for key, bucket in buckets.items() if len(bucket) > 1]

    quick = []
    for size, members in ((s, m) for s, m in by_size.items() if len(m) > 1):
        quick.extend(bucket for _, bucket in keyed(lambda item, s=size: _quick_key(item[0], s), members))
    duplicates = []
    for members in quick:
        size = os.lstat(members[0][0]).st_size
        for digest, bucket in keyed(lambda item: sha256_file(item[0]), members):
            duplicates.append({'sha256': digest, 'size': size, 'paths': sorted(relative for _, relative in bucket)})
    by_kind = {}
    for row in duplicates:
        for relative in row['paths'][1:]:
            kind = kind_of(relative)
            entry = by_kind.setdefault(kind, {'files': 0, 'bytes': 0})
            entry['files'] += 1
            entry['bytes'] += row['size']
    duplicates.sort(key=lambda row: -row['size'] * (len(row['paths']) - 1))
    report = {'schema': SCHEMA, 'roots': [str(r) for r in roots], 'min_size': min_size, 'totals': totals,
              'duplicate_bytes': sum(e['bytes'] for e in by_kind.values()), 'by_kind': by_kind,
              'groups': duplicates}
    log(f"Duplicate bytes: {report['duplicate_bytes'] / 1e9:,.2f} GB in {len(duplicates):,} groups "
        f"(already hard-linked, counted once: {totals['hardlinked_bytes'] / 1e9:,.2f} GB)")
    for kind, entry in sorted(by_kind.items(), key=lambda item: -item[1]['bytes']):
        log(f"  {kind:13} {entry['bytes'] / 1e9:10,.2f} GB in {entry['files']:,} extra copies")
    return report


def _try(function, item):
    try:
        return function(item)
    except OSError:
        return None


def stats(pool):
    """Objects in POOL, their bytes, and how many are linked from somewhere else (link count > 1)."""
    pool = Path(pool)
    counts = {'objects': 0, 'bytes': 0, 'linked_objects': 0, 'unlinked_objects': 0, 'unlinked_bytes': 0}
    for path, info in candidates(pool / OBJECTS, 0):
        counts['objects'] += 1
        counts['bytes'] += info.st_size
        if info.st_nlink > 1:
            counts['linked_objects'] += 1
        else:
            counts['unlinked_objects'] += 1
            counts['unlinked_bytes'] += info.st_size
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('scan', help='report duplicate bytes under the given folders (read-only)')
    p.add_argument('roots', nargs='+', type=Path)
    p.add_argument('--min-size', type=int, default=1 << 20)
    p.add_argument('--jobs', type=int)
    p.add_argument('--json', type=Path, help='write the full report here')
    p = sub.add_parser('adopt', help='store files in the pool and replace them by links (dry run by default)')
    p.add_argument('pool', type=Path)
    p.add_argument('folders', nargs='+', type=Path)
    p.add_argument('--min-size', type=int, default=DEFAULT_MIN_SIZE)
    p.add_argument('--jobs', type=int)
    p.add_argument('--apply', action='store_true', help='really link (default: report only)')
    p = sub.add_parser('stats', help='objects in the pool and how many are linked from run folders')
    p.add_argument('pool', type=Path)
    args = parser.parse_args(argv)
    if args.action == 'scan':
        report = scan(args.roots, args.min_size, args.jobs)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            with open(args.json, 'w', encoding='utf-8', newline='\n') as handle:
                json.dump(report, handle, indent=1)
                handle.write('\n')
        return 0
    if args.action == 'adopt':
        summary = adopt(args.pool, args.folders, args.min_size, args.apply, args.jobs)
        return 1 if summary['errors'] else 0
    print(json.dumps(stats(args.pool), indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
