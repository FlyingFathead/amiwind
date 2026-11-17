#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Finished partitions taken from an earlier build when their inputs are the same (BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66).

A partition of the image step (the boot partition, the CHIM world volume, a volume of open-world maps) is a function
of what goes on it and of the code that writes it. Its key is

    SHA-256(FORMAT, partition, volume, size in MiB, boot block, every folder and file in write order with each file's
            size and SHA-256, the writer's code (CODE, each file's SHA-256), the amitools version and the xdftool
            program, the settings the writer reads (SETTINGS))

Keyed by content only: the version label of a build changes only the files that show it (the version-named icon
file and the engine on the boot partition), never the key of a partition that does not hold them. When an entry
with the key is stored, the partition is copied from it (its SHA-256 checked while it is copied: a damaged entry is a
miss) and the result the writer returned when it wrote it (its check, readback and layout gate receipts) is given
back; the partition is not written again. Otherwise the writer runs and the finished partition is stored (a hard
link where the file system allows it, so storing costs no copy).

The entries live in the image pass cache folder (AMIWIND_PASS_CACHE, tools/pass_cache.py: development builds, and
release builds only with --allow-release-reuse; off: every partition is written), under partitions/<partition>/, and
also in the cache of the --reuse-from workspace (read only, AMIWIND_CACHE_FALLBACK). A partition is up to 2 GiB, so a
partition name keeps its KEEP most recently used entries; older ones are removed when a new one is stored.

An update of an earlier partition in place (only the changed files written again) is not made: the boot partition is
written in sorted order and its first files are the engine binaries, whose size changes with nearly every build
(v0.0.66-dev9 to dev10 and dev10 to dev11: AmiWind and AmiWind060 grew by a few blocks; 3, then 4 of the 29,385
files changed and the two version-named icon files were renamed), and a file of another size moves every block after
it, so an in-place update would be the whole write again. The CHIM world volume was unchanged in both (0 of 35,658
files), which is the case this cache serves.
"""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

FORMAT = 'AmiWind partition cache 1'
NAME = 'partitions'
KEEP = 2
ROOT = Path(__file__).resolve().parents[1]
# the code a partition is made with, hashed whole (a change anywhere in these files is a new key)
CODE = ('tools/ffs_write.py', 'tools/ffs_chains.py', 'tools/amiga_fs.py', 'tools/world_volumes.py',
        'tools/chim/disk.py', 'tools/chim/format.py', 'tools/build_windows_xdftool.py', 'tools/partition_cache.py')
SETTINGS = ('AMIWIND_CHAIN_ORDER', 'AMIWIND_PARTITION_WRITER')
COPY_CHUNK = 8 << 20


def folder():
    """The partition cache folder, or None when the image pass cache is off."""
    import pass_cache
    root = pass_cache.folder()
    return None if root is None else Path(root) / NAME


def _sha_file(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


_CODE = None


def code_digest(xdftool):
    """SHA-256 of the writer's code: CODE, the amitools version, the xdftool program (once per process)."""
    global _CODE
    if _CODE is None:
        from importlib import metadata
        try:
            amitools = metadata.version('amitools')
        except metadata.PackageNotFoundError:
            amitools = None
        program = shutil.which(str(xdftool)) or str(xdftool)
        rows = [[rel, _sha_file(ROOT / rel)] for rel in CODE]
        rows.append(['amitools', amitools])
        rows.append(['xdftool', _sha_file(program) if os.path.isfile(program) else None])
        _CODE = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    return _CODE


def inputs(partition, xdftool, mib, volume, ops, boot=False, jobs=None):
    """The key inputs of a partition written from OPS (tools/ffs_write.py): every op in order, files with their size
    and SHA-256 (hashed on JOBS threads: by default the stage's own allowance, AMIWIND_BUILD_JOBS as the builder gives
    it to every stage, never a number written here), and what else decides the bytes."""
    from build_parallel import hash_files, live_jobs
    if jobs is None:
        try:
            jobs = live_jobs(int(os.environ.get('AMIWIND_BUILD_JOBS') or (os.cpu_count() or 1)))
        except ValueError:
            jobs = os.cpu_count() or 1
    ops = list(ops)
    sources = [op[1] for op in ops if op[0] == 'file']
    digests = iter(hash_files(sources, jobs))
    rows = []
    for op in ops:
        if op[0] == 'dir':
            rows.append(['dir', op[1]])
        else:
            rows.append(['file', op[2], os.stat(op[1]).st_size, next(digests)])
    return {'format': FORMAT, 'partition': partition, 'volume': volume, 'mib': int(mib), 'boot': bool(boot),
            'ops': rows, 'code': code_digest(xdftool),
            'settings': {name: os.environ.get(name, '') for name in SETTINGS}}


def key_of(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _paths(root, partition, key):
    base = Path(root) / partition
    return base / (key + '.json'), base / (key + '.hdf')


def take(root, partition, key, part):
    """Copy the stored partition KEY into PART (its SHA-256 checked while it is copied); returns its record, or None
    (nothing left at PART) when there is no complete, intact entry."""
    meta_path, blob = _paths(root, partition, key)
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if meta.get('format') != FORMAT or meta.get('key') != key or meta.get('partition') != partition:
            return None
        digest = hashlib.sha256()
        with open(blob, 'rb') as source, open(part, 'xb') as target:
            for chunk in iter(lambda: source.read(COPY_CHUNK), b''):
                digest.update(chunk)
                target.write(chunk)
        if digest.hexdigest() != meta['sha256'] or Path(part).stat().st_size != meta['bytes']:
            Path(part).unlink()
            return None
        return meta
    except FileExistsError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        try:
            Path(part).unlink()
        except OSError:
            pass
        return None


def store(root, partition, key, part, result, record, written_seconds):
    """Store the finished PART under KEY with the writer's RESULT; keeps the KEEP most recently used entries of the
    partition name. Never fails a build: returns the stored record or None."""
    meta_path, blob = _paths(root, partition, key)
    try:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        sha256 = result.get('sha256') if isinstance(result, dict) and result.get('sha256') else _sha_file(part)
        partial = blob.with_name('%s.%d.tmp' % (blob.name, os.getpid()))
        try:
            os.link(part, partial)
        except OSError:
            shutil.copyfile(part, partial)
        os.replace(partial, blob)
        meta = {'format': FORMAT, 'key': key, 'partition': partition, 'sha256': sha256,
                'bytes': Path(part).stat().st_size, 'result': result, 'written_seconds': written_seconds,
                'stored_at': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'stored_by': str(part),
                'files': sum(1 for row in record['ops'] if row[0] == 'file'), 'mib': record['mib'],
                'volume': record['volume']}
        partial = meta_path.with_name('%s.%d.tmp' % (meta_path.name, os.getpid()))
        partial.write_text(json.dumps(meta, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        os.replace(partial, meta_path)
        prune(root, partition, keep_key=key)
        return meta
    except (OSError, TypeError, ValueError):
        return None


def prune(root, partition, keep_key=None, keep=None):
    """Remove all but the KEEP most recently used entries of PARTITION (KEEP_KEY always stays); returns the keys
    removed. Only this cache's own entries (a .json and its .hdf in partitions/<partition>/)."""
    keep = KEEP if keep is None else keep
    base = Path(root) / partition
    entries = []
    for meta in base.glob('*.json'):
        try:
            entries.append((meta.stat().st_mtime, meta.stem))
        except OSError:
            continue
    entries.sort(reverse=True)
    kept = [k for _, k in entries if k == keep_key][:1]
    kept += [k for _, k in entries if k != keep_key][:max(0, keep - len(kept))]
    removed = []
    for _, key in entries:
        if key in kept:
            continue
        for path in _paths(root, partition, key):
            try:
                path.unlink()
            except OSError:
                pass
        removed.append(key)
    return removed


def _log(line):
    print(line, flush=True)


def reuse_or_write(partition, part, write, xdftool, mib, volume, ops, boot=False, log=_log):
    """PART from the stored entry whose key (inputs() of XDFTOOL, MIB, VOLUME, OPS, BOOT) is this partition's, else
    WRITE() and store it. WRITE writes PART and returns its result (JSON). Returns the result. With the cache off
    nothing is hashed or stored: WRITE() alone."""
    root = folder()
    if root is None:
        return write()
    started = time.monotonic()
    record = inputs(partition, xdftool, mib, volume, ops, boot)
    key = key_of(record)
    from file_cache import fallback_root
    for where in (root, fallback_root(root)):
        if where is None:
            continue
        meta = take(where, partition, key, part)
        if meta is None:
            continue
        if where == root:
            try:
                os.utime(_paths(root, partition, key)[0])     # most recently used
            except OSError:
                pass
        else:
            store(root, partition, key, part, meta['result'], record, meta.get('written_seconds'))
        log('Image: partition %s taken from the partition cache (BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66): the same %d '
            'files, size, volume and writer as when %s wrote it (key %s); copied and its SHA-256 checked in %.1fs, '
            'not written again (it took %ss to write)'
            % (partition, meta.get('files', 0), meta.get('stored_by', '?'), key[:16], time.monotonic() - started,
               meta.get('written_seconds')))
        return meta['result']
    result = write()
    seconds = round(time.monotonic() - started, 3)
    if store(root, partition, key, part, result, record, seconds) is not None:
        log('Image: partition %s stored in the partition cache (key %s) for a later build with the same inputs'
            % (partition, key[:16]))
    return result
