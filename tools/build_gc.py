#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The one garbage collector for build workspaces, the shared storage pool and job scratch.

One retention policy, applied the same way everywhere (docs/BUILD_CACHE.md):

  kept (pinned)    release and release-candidate references, the newest passed run of every build
                   line (the latest verified reuse source), and every owner pin (pins.json);
  expires (age)    a run of a release series older than the newest --keep-series (default 3: the line
                   being built and the last two releases with their dev builds), unless pinned or
                   still building, whatever its line (BUILD-CACHE-NO-RETENTION-55);
  kept (active)    items whose owning job is still running (registry state "active"), and runs that
                   are still building;
  expires          run folders, played or smoke disk copies, package and extraction scratch and test
                   workspaces whose owning job is done (registry state "done"); scratch left inside a
                   finished run; pooled objects that no kept reuse key names and that nothing outside this
                   plan's expiring items links; pool temporaries older than a day;
  unit entries     an entry of a unit cache whose every read is recorded (AGED_CACHES, and the pool's reuse keys
                   of AGED_KEY_NAMESPACES) is kept when a named run (a kept run, or a run a kept run's stage
                   last really ran in) used or wrote it, or when it was used or written within --grace-days
                   (default 14); otherwise it expires. A cache or sub-cache whose use is not recorded stays kept.
  unregistered     anything else: REPORTED with its size, never deleted (an item nobody owns is a
                   finding, not garbage).

Sizes are what deleting would really free: a file shared by hard links (a pooled object linked into
several runs) is counted only when every one of its links is in the deletion set.

The plan also reports, for each pool, the bytes the kept set alone needs, the order in which the runs that are not
kept free the most when retired one after another, and the lines of the caches' use logs a trim would move out
(older than the grace and not of a named run).

Dry run by default: the collector prints the list (path, kind, owner, reason, bytes freed) and
writes it as JSON with --json (and every expired path, one per line, beside it in FILE.expired-paths.txt). Only
--delete removes anything, and only items whose decision is "expire" (never pinned, active or unregistered items).
--item PATH limits deletion to the listed items (the maintainer approves a list; the collector deletes exactly that
list); --items-file FILE adds one PATH per line (for long lists, such as the pool objects of a clean-out archived first:
an --item each would pass the argument limit). A listed path is an item of the plan or one expired unit entry.

Registry (--registry FILE, JSON): {"items": [{"path": "...", "owner": "job", "purpose": "...",
"state": "active"|"done", "expires": "with-job"|"never"}]}; paths absolute or relative to the root
they are under. Pins (WORKSPACE/cache/pins.json, or --pins FILE): {"pins": [{"path": "build/RUN",
"kind": "release"|"rc"|"reuse-source"|"owner", "reason": "..."}]}; `build_gc.py pin` and `unpin` edit it.

Commands:
  build_gc.py plan ROOT... [--workspace W ...] [--registry FILE] [--pins FILE] [--work-pool ROOT] [--pool DIR]
                           [--grace-days N] [--jobs N] [--json FILE]
  build_gc.py plan ... --delete [--item PATH ...] [--items-file FILE]
  build_gc.py pin WORKSPACE RUN --kind owner --reason TEXT
  build_gc.py unpin WORKSPACE RUN
"""
import argparse
from datetime import datetime, timedelta, timezone
import bisect
import json
import os
from pathlib import Path
import re
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
# Release retention (BUILD-CACHE-NO-RETENTION-55): runs of the newest KEEP_SERIES release series are kept by the
# usual rules (the line being built, and the last two releases with their dev builds); a run of an older series
# expires unless it is pinned or still building, whatever its line. 0 turns the rule off.
KEEP_SERIES = 3
# Unit cache ageing (BUILD-CACHE-NO-RETENTION-55): an entry neither used nor written within GRACE_DAYS and named by no
# kept run expires. 0 turns the rule off (every cache kept whole, as before).
GRACE_DAYS = 14
USE_LOG = ('.provenance', 'reuse.jsonl')       # tools/cache_provenance.py: one line per read (REUSE_LOG)
# The unit caches whose every read writes a line in their use log (cache_provenance.reused: chim.units.UnitCache.get,
# pass_cache.PassCache.load, prepare_world_regions.unit_cache_lookup), the form of their entries, and their
# sub-caches that are read some other way or are records, not a cache: those stay kept whole.
AGED_CACHES = {
    'chim-units': ('pickle', frozenset({
        'heap'})),                       # chim/heap.py's frame results: no use line
    'image-passes': ('pass', frozenset({
        'stair-walk', 'stair-walk-checked', 'stair-walk-frames',     # the hashed walk records, never aged
        'partitions',                    # tools/partition_cache.py keeps its own most recently used
        'chim-frame-heap',               # chim/heap.py's frame results: no use line
        '.tally'})),                     # hit counters
    'world-terrain-v1': ('folder', frozenset()),
}
# Reuse key namespaces of the pool read through file_cache.FileCache.fetch, which writes a use line. The others are
# read through FileCache.lookup, which does not (CACHE-KEY-LOOKUP-NO-USE-68): their keys stay kept.
AGED_KEY_NAMESPACES = frozenset({'sound', 'video', 'mwscript', 'npc-resident-v2'})
LOG_CHUNK_BYTES = 128 << 20
WINDOW_MARGIN_SECONDS = 3600


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


def _epoch(text):
    """Seconds of an ISO 8601 stamp ('Z' or an offset), or None."""
    try:
        value = datetime.fromisoformat(str(text).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).timestamp()


def _stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Progress:
    """A progress line at most every few seconds for long phases (done / total, rate)."""

    def __init__(self, label, total, out=print, every=5.0):
        self.label, self.total, self.out, self.every = label, total, out, every
        self.started = self.last = time.time()
        self.done = 0

    def step(self, count=1):
        self.done += count
        moment = time.time()
        if moment - self.last >= self.every or self.done >= self.total:
            self.last = moment
            spent = moment - self.started
            self.out(f'  {self.label}: {self.done}/{self.total} ({spent:.0f} s)', flush=True)


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


def _walk_path(path):
    """Inodes.walk on a worker process (the plan's run folders)."""
    return Inodes().walk(path)


def run_state(folder):
    state = load_json(Path(folder) / 'build-state.json', {})
    return state if isinstance(state, dict) else {}


def run_line(state):
    """The build line a run belongs to: its recorded line, else version and builder type."""
    if state.get('line'):
        return str(state['line'])
    builder = state.get('builder') or (state.get('builder_options') or {}).get('builder') or 'legacy'
    return f"{state.get('runtime_version') or 'unknown'}:{builder}:{state.get('recipe') or 'build'}"


def series(version):
    """The release series of a version text: (0, 0, 55) for '0.0.55', '0.0.55-dev1' or 'v0.0.55-rc2'; None if unknown."""
    numbers = re.findall(r'\d+', str(version or '').split('-')[0])
    return tuple(int(n) for n in numbers[:3]) if len(numbers) >= 3 else None


def series_text(value):
    return 'v' + '.'.join(str(n) for n in value)


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


def _key_names(meta):
    """The pool objects one reuse key names: its sha256, and the objects a manifest key lists (a CHIMport cell)."""
    names = set()
    if isinstance(meta, dict) and meta.get('sha256'):
        names.add(meta['sha256'])
        objects = (meta.get('facts') or {}).get('objects') if isinstance(meta.get('facts'), dict) else None
        if isinstance(objects, list):
            names.update(str(o) for o in objects)
    return names


def referenced_objects(pool, skip=()):
    """SHA-256 values named by the pool's reuse keys and by prerendered manifests stored in it (less the keys in
    SKIP: the expired ones)."""
    names = set()
    skip = {os.path.normpath(str(p)) for p in skip}
    for here, _, files in os.walk(Path(pool) / 'keys'):
        for name in files:
            if name.endswith('.json') and not name.endswith('.meta.json'):
                path = os.path.join(here, name)
                if skip and os.path.normpath(path) in skip:
                    continue
                names |= _key_names(load_json(path, {}))
    return names


# --------------------------------------------------------------------------
# Unit cache ageing: the named runs, the use logs, the entries

def named_runs(kept_runs, now_seconds):
    """{run name: [start, end]}: the kept runs, and the runs their stages last really ran in, named by the stage
    records a run carries (profile/manifests-ran/STAGE.json: the record copied from the run where the stage last
    really ran, BUILD-REUSE-RECORD-RETIRED-36; profile/manifests/STAGE.json for the stages it ran itself). The
    window is when the run could have read or written a cache entry."""
    windows = {}

    def widen(name, start, end):
        row = windows.setdefault(name, [start, end])
        row[0], row[1] = min(row[0], start), max(row[1], end)

    def own(run):
        state = run_state(run)
        start = _epoch(state.get('build_started_at'))
        if start is None:
            return None
        elapsed = state.get('elapsed_seconds')
        end = start + float(elapsed) if isinstance(elapsed, (int, float)) and state.get('status') != 'running' \
            else now_seconds
        return start - WINDOW_MARGIN_SECONDS, end + WINDOW_MARGIN_SECONDS

    for run in kept_runs:
        run = Path(run)
        window = own(run) or (0.0, now_seconds)       # a kept run without a start: any time
        widen(run.name, *window)
        ran = run / 'profile' / 'manifests-ran'
        records = sorted(ran.glob('*.json')) if ran.is_dir() else []
        copied = {p.name for p in records}
        mine = run / 'profile' / 'manifests'
        records += [p for p in (sorted(mine.glob('*.json')) if mine.is_dir() else []) if p.name not in copied]
        for record in records:
            data = load_json(record, {})
            provenance = data.get('provenance') if isinstance(data, dict) else None
            if not isinstance(provenance, dict) or not provenance.get('run'):
                continue
            origin = str(provenance['run'])
            folder = run.parent / origin
            window = own(folder) if folder.is_dir() else None
            if window is None:
                # the origin is retired: from the day before its name's date to its stage record
                created = _epoch(provenance.get('created_at')) or now_seconds
                match = re.match(r'(\d{4})_(\d{2})_(\d{2})_', origin)
                day = datetime(*map(int, match.groups()), tzinfo=timezone.utc).timestamp() if match else created
                window = (min(day, created) - 86400, created + WINDOW_MARGIN_SECONDS)
            widen(origin, *window)
    return windows


def _key(text):
    """A cache key as stored in the use sets: the 32 bytes of a SHA-256 hex text, else the SHA-256 of the text."""
    if isinstance(text, str):
        text = text.encode('utf-8', 'surrogateescape')
    if len(text) == 64:
        try:
            return bytes.fromhex(text.decode('ascii'))
        except (ValueError, UnicodeDecodeError):
            pass
    import hashlib
    return hashlib.sha256(bytes(text)).digest()


class KeySet:
    """A frozen set of 32-byte keys as one sorted bytes object: millions of keys in 32 bytes each, and shared by the
    forked walk workers without copying (a Python set's members would be copied page by page as they are read)."""

    def __init__(self, keys=()):
        self.blob = b''.join(sorted(set(keys)))
        self.count = len(self.blob) // 32

    def __len__(self):
        return self.count

    def __contains__(self, key):
        blob, low, high = self.blob, 0, self.count
        while low < high:
            middle = (low + high) // 2
            found = blob[middle * 32:middle * 32 + 32]
            if found == key:
                return True
            if found < key:
                low = middle + 1
            else:
                high = middle
        return False


def _use_line(line):
    """(at, key, run) of one use log line (cache_provenance.canonical: sorted keys at, cache, job, key, run), or None."""
    if line.startswith(b'{"at":"'):
        quote = line.find(b'"', 7)
        at_key = line.find(b'"key":"', quote)
        at_run = line.find(b'"run":', quote)
        if quote > 0 and 0 < at_key < at_run:
            key = line[at_key + 7:line.find(b'"', at_key + 7)]
            tail = line[at_run + 6:].rstrip(b'}\r\n ')
            run = tail[1:-1] if tail.startswith(b'"') and tail.endswith(b'"') else None
            return line[7:quote], key, run
    try:
        row = json.loads(line)
        run = row.get('run')
        return str(row['at']).encode(), str(row['key']).encode(), str(run).encode() if run else None
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def _scan_log(path, start, end, cutoff, named):
    """One byte range of a use log: (keys used since CUTOFF, keys a named run used, lines, bytes, expiring lines,
    expiring bytes). A line belongs to the range its first byte is in."""
    cutoff_text = _stamp(cutoff)[:19].encode()
    recent, by_named = set(), set()
    lines = total = old_lines = old_bytes = 0
    with open(path, 'rb') as stream:
        position = start
        if start:
            stream.seek(start - 1)
            position = start - 1 + len(stream.readline())
        while position < end:
            line = stream.readline()
            if not line:
                break
            position += len(line)
            lines += 1
            total += len(line)
            row = _use_line(line)
            if row is None:
                continue                                   # unreadable: kept
            at, key, run = row
            if len(at) == 25 and at.endswith(b'+00:00'):
                before = at[:19] < cutoff_text
            else:
                seconds = _epoch(at.decode('utf-8', 'replace'))
                before = seconds is not None and seconds < cutoff
            key = _key(key)
            if not before:
                recent.add(key)
            if run is not None and run in named:
                by_named.add(key)
            elif before:
                old_lines += 1
                old_bytes += len(line)
    return recent, by_named, lines, total, old_lines, old_bytes


def _pool(jobs, tasks):
    """A process pool (fork: the workers share the plan's lookup sets) when the work is worth it, else None."""
    if jobs <= 1 or tasks < 8:
        return None
    try:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        return ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context('fork'))
    except (ImportError, ValueError, OSError):
        return None


def _map(jobs, function, tasks, label, out, reduce=None):
    """function(*task) for every task, on the process pool when it pays: the results in task order, or, with REDUCE,
    each result handed to reduce(result) as it comes and dropped (nothing kept)."""
    tasks = list(tasks)
    progress = Progress(label, len(tasks), out)
    results = [None] * len(tasks)

    def take(index, result):
        if reduce is not None:
            reduce(result)
        else:
            results[index] = result
        progress.step()

    executor = _pool(jobs, len(tasks))
    if executor is None:
        for index, task in enumerate(tasks):
            take(index, function(*task))
    else:
        from concurrent.futures import as_completed
        with executor:
            futures = {executor.submit(function, *task): index for index, task in enumerate(tasks)}
            for future in as_completed(futures):
                take(futures.pop(future), future.result())
    return None if reduce is not None else results


def scan_use_log(path, cutoff, named, jobs=1, out=print):
    """The use log of one cache: {'recent': keys used since CUTOFF, 'named': keys a named run used, the trim
    numbers}, read in byte ranges on JOBS processes."""
    size = os.path.getsize(path)
    ranges = [(start, min(size, start + LOG_CHUNK_BYTES)) for start in range(0, size, LOG_CHUNK_BYTES)] or [(0, 0)]
    named = frozenset(str(n).encode() for n in named)
    recent, by_named = set(), set()
    numbers = [0, 0, 0, 0]

    def merge(part):
        recent.update(part[0])
        by_named.update(part[1])
        for index in range(4):
            numbers[index] += part[2 + index]

    _map(jobs, _scan_log, [(str(path), a, b, cutoff, named) for a, b in ranges],
         f'use log {path} ({size / 1e9:.2f} GB)', out, reduce=merge)
    recent, by_named = KeySet(recent), KeySet(by_named)
    return {'recent': recent, 'named': by_named, 'lines': numbers[0], 'bytes': numbers[1],
            'expiring_lines': numbers[2], 'expiring_bytes': numbers[3]}


# The plan's lookup sets, shared with the walk's worker processes (set before the pool forks them).
_AGE = {}


def _writer(layout, entry):
    """The run that wrote a cache entry, from its provenance (cache_provenance), or None."""
    path = Path(entry)
    if layout == 'pickle':
        record = load_json(path.with_name(path.name.split('.')[0] + '.meta.json'), {})
    elif layout == 'folder':
        data = load_json(path / 'conversion.json', {})
        record = data.get('provenance') if isinstance(data, dict) else None
    else:
        data = load_json(path, {})
        record = data.get('provenance') if isinstance(data, dict) else None
        if not isinstance(record, dict) or not record.get('run'):
            record = load_json(path.with_name(path.name[:-len('.json')] + '.meta.json'), {})
    return str(record['run']) if isinstance(record, dict) and record.get('run') else None


def _entry_shape(layout, name, is_dir):
    """(key text, role) of a name inside a shard folder: role 'entry' (the entry's main file or folder),
    'part' (a file belonging to the entry of that key), 'temporary', or None (not of this layout)."""
    if '.tmp' in name:
        return None, 'temporary'
    if layout == 'folder':
        return (name, 'entry') if is_dir and len(name) == 64 else (None, None)
    if is_dir:
        return None, None
    stem, _, suffix = name.partition('.')
    if len(stem) != 64:
        return None, None
    main = {'pickle': 'pickle', 'pass': 'json', 'keys': 'json', 'blob': 'bin'}[layout]
    if suffix == main:
        return stem, 'entry'
    if suffix == 'meta.json' or (layout == 'pass' and suffix == 'bin'):
        return stem, 'part'
    return None, None


def _walk_shard(layout, shard, blob_names):
    """The decisions for the entries of one shard folder of a unit cache (see AGED_CACHES)."""
    recent, by_named, cutoff = _AGE['recent'], _AGE['named'], _AGE['cutoff']
    starts, ends, runs = _AGE['starts'], _AGE['ends'], _AGE['runs']
    named_blobs = _AGE.get('blobs', {}).get(blob_names) if layout == 'blob' else None
    out = {'odd': [], 'entries': 0, 'kept': 0, 'kept_solo': 0, 'kept_shared': [], 'expired': [], 'expired_entries': 0,
           'expired_solo': 0, 'expired_shared': [], 'why': {}, 'blobs': set(), 'blob_unread': 0, 'expired_mains': []}
    groups = {}
    try:
        children = list(os.scandir(shard))
    except OSError:
        return out
    for child in children:
        is_dir = child.is_dir(follow_symlinks=False)
        key, role = _entry_shape(layout, child.name, is_dir)
        if role == 'temporary':
            continue
        if role is None:
            out['odd'].append(child.path)
            continue
        group = groups.setdefault(key, {'main': None, 'files': []})
        if role == 'entry':
            group['main'] = child.path
        if is_dir:
            for here, _, names in os.walk(child.path):
                for name in names:
                    group['files'].append(os.path.join(here, name))
        else:
            group['files'].append(child.path)
    for key, group in groups.items():
        files = []
        for path in group['files']:
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if stat_module.S_ISREG(info.st_mode):
                files.append((os.path.normpath(path), (info.st_dev, info.st_ino), info.st_size, info.st_nlink,
                              info.st_mtime))
        written = max([f[4] for f in files] or [0.0])
        if group['main'] is None:
            # a part left without its entry (a sidecar or output whose entry was never written): no reader can reach
            # it; it goes once it is older than the grace
            why = 'part without its entry, written within the grace' if written >= cutoff else None
            out['why'][why or 'part without its entry'] = out['why'].get(why or 'part without its entry', 0) + 1
            for path, inode, size, nlink, _ in files:
                target = 'kept' if why else 'expired'
                if nlink > 1:
                    out[target + '_shared'].append((path, inode, size, nlink))
                else:
                    out[target + '_solo'] += size
                if not why:
                    out['expired'].append(path)
            continue
        out['entries'] += 1
        if layout == 'folder':
            try:
                written = max(written, os.lstat(group['main']).st_mtime)
            except OSError:
                pass
        token = _key(key)
        if layout == 'blob':
            why = 'blob named by a kept entry' if named_blobs is None or token in named_blobs else \
                ('blob written within the grace' if written >= cutoff else None)
        elif token in recent:
            why = 'used within the grace'
        elif written >= cutoff:
            why = 'written within the grace'
        elif token in by_named:
            why = 'used by a named run'
        else:
            why = None
            at = bisect.bisect_right(starts, written) - 1          # STARTS/ENDS: disjoint, merged windows
            if at >= 0 and written <= ends[at]:
                writer = _writer(layout, group['main'])
                if writer is None:
                    why = 'written while a named run ran, writer not recorded'
                elif writer in runs:
                    why = 'written by a named run'
        target = 'kept' if why else 'expired'
        label = why or ('blob expired' if layout == 'blob' else 'expired')
        out['why'][label] = out['why'].get(label, 0) + 1
        for path, inode, size, nlink, _ in files:
            if nlink > 1:
                out[target + '_shared'].append((path, inode, size, nlink))
            else:
                out[target + '_solo'] += size
        if why:
            out['kept'] += 1
            if layout == 'pass' and blob_names:
                data = load_json(group['main'], None)
                row = data.get('row') if isinstance(data, dict) else None
                named = row.get('files') if isinstance(row, dict) else None
                if isinstance(named, dict):
                    out['blobs'].update(_key(str(v)) for v in named.values())
                else:
                    out['blob_unread'] += 1              # the blobs it may name cannot be told: all kept
        else:
            out['expired_entries'] += 1
            out['expired_mains'].append(os.path.normpath(group['main']))
            out['expired'] += [os.path.normpath(group['main'])] if layout == 'folder' else \
                sorted(path for path, *_ in files)
    return out


def _shards(folder):
    """The two-hex shard folders of FOLDER, and anything else in it (odd for an aged layout)."""
    shards, odd = [], []
    try:
        children = sorted(os.scandir(folder), key=lambda e: e.name)
    except OSError:
        return shards, odd
    for child in children:
        if child.name == '.provenance':
            continue
        if child.is_dir(follow_symlinks=False) and len(child.name) == 2 and \
                all(c in '0123456789abcdef' for c in child.name):
            shards.append(child.path)
        else:
            odd.append(child.path)
    return shards, odd


def age_cache(root, layout, subs, log, windows, cutoff, jobs, out=print):
    """Decide every entry of one unit cache. Returns {sub: summary} and the use log's trim numbers; a summary holds
    the kept and expired entries (expired paths, bytes alone, hard-linked files), why each was kept, and 'untold'
    when the sub-cache holds something outside its layout (then it is kept whole)."""
    runs = frozenset(windows)
    log_numbers = scan_use_log(log, cutoff, runs, jobs, out)
    spans = []
    for start, end in sorted(tuple(w) for w in windows.values()):
        if spans and start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], end))
        else:
            spans.append((start, end))
    _AGE.clear()
    _AGE.update(recent=log_numbers.pop('recent'), named=log_numbers.pop('named'), cutoff=cutoff,
                starts=[s for s, _ in spans], ends=[e for _, e in spans], runs=runs)
    plan_subs, tasks = {}, []
    for sub, folder in subs:
        shards, odd = _shards(folder) if layout != 'folder' else _shards(root)
        files_folder = Path(folder) / 'files'
        has_blobs = layout == 'pass' and files_folder.is_dir()
        odd = [p for p in odd if not (has_blobs and Path(p) == files_folder)]
        plan_subs[sub] = {'folder': str(folder), 'odd': odd, 'parts': [], 'blobs': has_blobs}
        tasks += [(sub, (layout, shard, sub if has_blobs else None)) for shard in shards]
    results = _map(jobs, _walk_shard, [task for _, task in tasks], f'entries of {root}', out)
    for (sub, _), result in zip(tasks, results):
        plan_subs[sub]['parts'].append(result)
    # the shared blobs of the unit caches: kept when a kept entry names them (or written within the grace)
    blob_tasks = []
    _AGE['blobs'] = {}
    for sub, row in plan_subs.items():
        if not row['blobs']:
            continue
        unread = sum(part['blob_unread'] for part in row['parts']) or any(part['odd'] for part in row['parts'])
        _AGE['blobs'][sub] = None if unread or row['odd'] else KeySet(k for p in row['parts'] for k in p['blobs'])
        for part in row['parts']:
            part['blobs'] = set()
        shards, odd = _shards(Path(row['folder']) / 'files')
        row['odd'] += odd
        blob_tasks += [(sub, ('blob', shard, sub)) for shard in shards]
    for (sub, _), result in zip(blob_tasks, _map(jobs, _walk_shard, [t for _, t in blob_tasks],
                                                 f'shared blobs of {root}', out)):
        result['blob_entries'], result['blob_expired'] = result['entries'], result['expired_entries']
        result['entries'] = result['kept'] = result['expired_entries'] = 0
        result['expired_mains'] = []
        plan_subs[sub]['parts'].append(result)
    _AGE.clear()
    summaries = {}
    for sub, row in plan_subs.items():
        merged = {'folder': row['folder'], 'odd': list(row['odd']), 'entries': 0, 'kept': 0, 'kept_solo': 0,
                  'kept_shared': [], 'expired': [], 'expired_entries': 0, 'expired_solo': 0, 'expired_shared': [],
                  'why': {}, 'expired_mains': [], 'blob_entries': 0, 'blob_expired': 0}
        for part in row['parts']:
            merged['odd'] += part['odd']
            for name in ('entries', 'kept', 'kept_solo', 'expired_solo', 'expired_entries', 'blob_entries',
                         'blob_expired'):
                merged[name] += part.get(name, 0)
            for name in ('kept_shared', 'expired', 'expired_shared', 'expired_mains'):
                merged[name] += part[name]
            for why, count in part['why'].items():
                merged['why'][why] = merged['why'].get(why, 0) + count
        merged['untold'] = bool(merged['odd'])
        merged['dormant'] = not (merged['why'].get('used within the grace') or
                                 merged['why'].get('written within the grace'))
        summaries[sub] = merged
    return summaries, log_numbers


# --------------------------------------------------------------------------
# Planning

def pool_objects(pool, now_seconds):
    """[(path, inode, size, nlink, name)] of a storage pool's objects, and its temporaries older than a day."""
    objects, temporaries = [], []
    for here, _, names in os.walk(Path(pool) / 'objects'):
        for name in names:
            path = os.path.join(here, name)
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if name.endswith(TEMPORARY_SUFFIXES):
                if now_seconds - info.st_mtime > TEMPORARY_AGE_SECONDS:
                    temporaries.append(path)
            elif stat_module.S_ISREG(info.st_mode):
                objects.append((os.path.normpath(path), (info.st_dev, info.st_ino), info.st_size, info.st_nlink, name))
    return objects, temporaries


def plan(roots, workspaces=(), registry_items=None, pin_files=None, now_seconds=None, extra_pools=(),
         keep_series=KEEP_SERIES, grace_days=GRACE_DAYS, jobs=None, out=print):
    """The collector's decisions: [{path, kind, decision, reason, owner, files}] plus totals."""
    now_seconds = now_seconds or time.time()
    if jobs is None:
        from build_jobs import resolve_jobs
        jobs = resolve_jobs(None)
    roots = [Path(root) for root in roots]
    workspaces = [Path(w) for w in workspaces] or [w for w in _find_workspaces(roots)]
    registry = Registry(registry_items, roots)
    pins = load_pins(workspaces, pin_files)
    inodes = Inodes()
    items = []
    covered = set()
    cutoff = now_seconds - grace_days * 86400
    walked = {}                                   # run folders walked ahead on the worker processes

    def add(path, kind, decision, reason, extra=None, files=None):
        owner = registry.owner(path)
        if files is None:
            files = walked.pop(os.path.normpath(str(path)), None)
            files = inodes.walk(path) if files is None else files
        row = {'path': str(path), 'kind': kind, 'decision': decision, 'reason': reason,
               'owner': owner.get('owner') if owner else None, 'purpose': owner.get('purpose') if owner else None,
               'files': files, 'solo': 0}
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

    out('=== PHASE 1/4: runs', flush=True)
    for workspace in workspaces:
        builds = workspace / 'build'
        runs = sorted(p for p in builds.iterdir() if p.is_dir()) if builds.is_dir() else []
        # every run folder's files on the worker processes (GC-RUN-WALK-ONE-CORE-68: one after another, the walk of a
        # large build volume's runs took about six minutes on one core)
        walked.update(zip((os.path.normpath(str(r)) for r in runs),
                          _map(jobs, _walk_path, [(str(r),) for r in runs], f'run folders of {workspace}', out)))
        states = {run: run_state(run) for run in runs}
        newest = {}
        for run, state in states.items():
            if state.get('status') == 'passed':
                line = run_line(state)
                stamp = state.get('build_started_at') or ''
                if line not in newest or stamp > newest[line][0]:
                    newest[line] = (stamp, run)
        latest = {run: line for line, (_, run) in newest.items()}
        known = sorted({s for s in (series(st.get('runtime_version')) for st in states.values()) if s}, reverse=True)
        kept_series = set(known[:keep_series]) if keep_series else set(known)
        kept_names = ', '.join(series_text(s) for s in sorted(kept_series))
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
            run_series = series(version)
            if pin:
                add(run, 'run', KEEP, f"pinned ({pin.get('kind', 'owner')}): {pin.get('reason', '')}".rstrip(': '),
                    extra)
            elif run_series and run_series not in kept_series:
                add(run, 'run', EXPIRE, f'release series {series_text(run_series)} is older than the kept series '
                    f'({kept_names}): retention rule', extra)
            elif run in latest:
                add(run, 'run', KEEP, f'latest passed run of line {latest[run]} (reuse source)', extra)
            else:
                decision, reason = by_owner(run, 'run', f'{status} run, superseded')
                add(run, 'run', decision, reason, extra)
    windows = named_runs([row['path'] for row in items if row['kind'] == 'run' and row['decision'] == KEEP],
                         now_seconds) if grace_days else {}

    out('=== PHASE 2/4: caches', flush=True)
    logs, expired_keys, pools = [], [], []
    for workspace in workspaces:
        caches = workspace / 'cache'
        for cache in sorted(p for p in caches.iterdir() if p.is_dir()) if caches.is_dir() else []:
            if cache == workspace / POOL:
                continue
            log = cache.joinpath(*USE_LOG)
            if not grace_days or cache.name not in AGED_CACHES:
                add(cache, 'cache', KEEP, 'build cache (content-addressed, verified on use)')
            elif not log.is_file():
                add(cache, 'cache', KEEP, 'build cache (content-addressed, verified on use); it has no use log, '
                    'so its use cannot be told: kept')
            else:
                layout, whole = AGED_CACHES[cache.name]
                if layout == 'folder':
                    subs = [('.', cache)]
                else:
                    subs = [(p.name, p) for p in sorted(cache.iterdir()) if p.is_dir() and p.name not in whole
                            and p.name != '.provenance']
                summaries, numbers = age_cache(cache, layout, subs, log, windows, cutoff, jobs, out)
                logs.append(dict(numbers, path=str(log)))
                _age_rows(add, cache, summaries, sorted(p.name for p in cache.iterdir() if p.name in whole),
                          grace_days)
        pools.append(workspace / POOL)
        covered.add(os.path.normpath(str(workspace)))
    # Pools named outside a workspace (--storage-pool-dir, AMIWIND_STORAGE_POOL): the same object rules.
    for pool in extra_pools or ():
        pools.append(Path(pool))
        covered.add(os.path.normpath(str(pool)))

    out('=== PHASE 3/4: storage pools', flush=True)
    pool_rows = []
    for pool in pools:
        if not (Path(pool) / 'objects').is_dir():
            continue
        log = Path(pool).joinpath(*USE_LOG)
        keys = Path(pool) / 'keys'
        if grace_days and log.is_file() and keys.is_dir():
            subs = [(p.name, p) for p in sorted(keys.iterdir()) if p.is_dir() and p.name in AGED_KEY_NAMESPACES]
            summaries, numbers = age_cache(keys, 'keys', subs, log, windows, cutoff, jobs, out)
            logs.append(dict(numbers, path=str(log)))
            for sub, summary in summaries.items():
                if summary['untold'] or not summary['expired']:
                    continue
                expired_keys += summary['expired_mains']
                add(Path(summary['folder']), 'reuse-keys', EXPIRE,
                    f"keys/{sub}: {summary['expired_entries']} of {summary['entries']} reuse keys neither used nor "
                    f"written within {grace_days} days and used or written by no named run",
                    _group_extra(summary), files=summary['expired_shared'])['solo'] = summary['expired_solo']
        named = referenced_objects(pool, expired_keys)
        named_by_expired = set().union(*[_key_names(load_json(path, {})) for path in expired_keys]) - named
        objects, temporaries = pool_objects(pool, now_seconds)
        pool_rows.append((pool, objects, named, named_by_expired))
        for path in temporaries:
            add(path, 'pool-temporary', EXPIRE, 'pool temporary older than a day')

    # Pool objects last: an object no kept key names expires when nothing outside this plan's expiring items
    # links it (an expiring run's files are pooled objects: they are freed in the same plan).
    expiring_links = {}
    for row in items:
        if row['decision'] == EXPIRE:
            for path, inode, _, nlink in row['files']:
                if nlink > 1:
                    expiring_links.setdefault(inode, set()).add(path)
    pool_report = []
    for pool, objects, named, named_by_expired in pool_rows:
        for path, inode, size, nlink, name in objects:
            if name in named:
                continue
            if nlink == 1:
                reason = 'pooled object no run links and no reuse key names' if name not in named_by_expired else \
                    'pooled object no run links and only expired reuse keys name'
            elif len(expiring_links.get(inode, ())) >= nlink - 1:
                reason = 'pooled object only expiring items link and no kept reuse key names'
            else:
                continue
            add(path, 'pool-object', EXPIRE, reason, files=[(path, inode, size, nlink)])
        pool_report.append({'pool': str(pool), 'objects': objects, 'named': named})

    out('=== PHASE 4/4: what everything else under the roots is', flush=True)
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
    result = finish(items, inodes, pool_report)
    result.update(grace_days=grace_days, cutoff=_stamp(cutoff) if grace_days else None,
                  named_runs=sorted(windows), log_trim=[dict(row, cutoff=_stamp(cutoff)) for row in logs])
    return result


def _group_extra(summary):
    members = summary['expired']
    return {'members': members, 'member_count': len(members), 'sample': members[:3], 'dormant': summary['dormant'],
            'why': summary['why'], 'entries': summary['entries'], 'expired_entries': summary['expired_entries'],
            'expired_blobs': summary['blob_expired']}


def _age_rows(add, cache, summaries, whole, grace_days):
    """The rows of one aged cache: one kept row for the cache (its kept entries and the sub-caches kept whole) and
    one expired row per sub-cache with expired entries."""
    kept_solo, kept_shared, kept_entries, notes = 0, [], 0, []
    whole_paths = [cache / name for name in whole]
    for sub, summary in sorted(summaries.items()):
        if summary['untold']:
            whole_paths.append(Path(summary['folder']))
            notes.append(f"{sub}: holds {len(summary['odd'])} files outside its form ({summary['odd'][0]}), kept whole")
            continue
        kept_solo += summary['kept_solo']
        kept_shared += summary['kept_shared']
        kept_entries += summary['kept']
        if summary['expired']:
            label = cache.name if sub == '.' else f'{cache.name}/{sub}'
            dormant = '; dormant: no use or write within the grace' if summary['dormant'] else ''
            blobs = f" and {summary['blob_expired']} of {summary['blob_entries']} shared files no kept entry names" \
                if summary['blob_entries'] else ''
            row = add(Path(summary['folder']), 'unit-entries', EXPIRE,
                      f"{label}: {summary['expired_entries']} of {summary['entries']} entries neither used nor "
                      f"written within {grace_days} days and used or written by no named run{blobs}{dormant}",
                      _group_extra(summary), files=summary['expired_shared'])
            row['solo'] = summary['expired_solo']
    inodes = Inodes()
    for path in whole_paths:
        for entry in inodes.walk(path):
            if entry[3] > 1:
                kept_shared.append(entry)
            else:
                kept_solo += entry[2]
    reason = (f'build cache, aged: {kept_entries} entries used or written within {grace_days} days or by a named '
              f'run kept' + (f"; kept whole: {', '.join(p.name for p in whole_paths)} (use not recorded per entry, "
                             f"or records)" if whole_paths else ''))
    row = add(cache, 'cache', KEEP, reason, {'notes': notes}, files=kept_shared)
    row['solo'] = kept_solo


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


def retire_order(items, objects, named):
    """The runs that are not kept, in the order that frees the most when each goes together with every run before it
    (greedy: each step takes the run whose retirement frees the most then). A hard-linked file is freed when every
    one of its links is in a retired run, or is a pooled object no kept reuse key names."""
    candidates = sorted((row for row in items if row['kind'] == 'run' and row['decision'] in (EXPIRE, UNREGISTERED)),
                        key=lambda row: row['path'])
    pooled = {inode: name for _, inode, _, _, name in objects}
    links, sizes, owners = {}, {}, {}
    gain = []
    for index, row in enumerate(candidates):
        solo = 0
        for path, inode, size, nlink in row['files']:
            if nlink == 1:
                solo += size
                continue
            links.setdefault(inode, set()).add(path)
            sizes[inode] = (size, nlink)
            owners.setdefault(inode, set()).add(index)
        gain.append(solo)
    need, by_run = {}, {}
    for inode, paths in links.items():
        size, nlink = sizes[inode]
        free_pool = 1 if inode in pooled and pooled[inode] not in named else 0
        if len(paths) + free_pool >= nlink:
            need[inode] = set(owners[inode])
            for index in owners[inode]:
                by_run.setdefault(index, []).append(inode)
            if len(need[inode]) == 1:
                gain[next(iter(need[inode]))] += size
    order, total, remaining = [], 0, set(range(len(candidates)))
    while remaining:
        pick = max(remaining, key=lambda i: (gain[i], -i))
        remaining.discard(pick)
        total += gain[pick]
        row = candidates[pick]
        order.append({'path': row['path'], 'version': row.get('version'), 'decision': row['decision'],
                      'frees_with_those_before': gain[pick], 'cumulative_freed': total})
        for inode in by_run.get(pick, ()):
            waiting = need[inode]
            waiting.discard(pick)
            if len(waiting) == 1:
                gain[next(iter(waiting))] += sizes[inode][0]
    return order


def finish(items, inodes, pools=()):
    """Sizes and totals (hard links considered), the pool accounting and the retire order."""
    def freed(rows):
        return sum(row['solo'] for row in rows) + inodes.freed([row['files'] for row in rows])

    for row in items:
        row['bytes'] = row['solo'] + sum({inode: size for _, inode, size, _ in row['files']}.values())
        row['freed_alone'] = freed([row])
    expire = [row for row in items if row['decision'] == EXPIRE]
    totals = {decision: {'items': 0, 'bytes': 0} for decision in (KEEP, EXPIRE, UNREGISTERED)}
    for row in items:
        totals[row['decision']]['items'] += 1
        totals[row['decision']]['bytes'] += row['bytes']
    totals['expire']['freed'] = freed(expire)
    kept_inodes = {inode for row in items if row['decision'] == KEEP for _, inode, _, nlink in row['files']
                   if nlink > 1}
    expiring_objects = {row['path'] for row in expire if row['kind'] == 'pool-object'}
    accounting, every_object, every_named = [], [], set()
    for pool in pools:
        objects, named = pool['objects'], pool['named']
        total = sum(size for _, _, size, _, _ in objects)
        needed = sum(size for _, inode, size, _, name in objects if inode in kept_inodes or name in named)
        going = sum(size for path, _, size, _, _ in objects if path in expiring_objects)
        accounting.append({'pool': pool['pool'], 'objects': len(objects), 'bytes': total, 'kept_needs_bytes': needed,
                           'expiring_bytes': going, 'held_by_others_bytes': total - needed - going})
        every_object += objects
        every_named |= named
    order = retire_order(items, every_object, every_named)
    for row in items:
        files = row.pop('files')
        row['file_count'] = row['member_count'] if 'member_count' in row else len(files)
        row.pop('solo')
    return {'schema': SCHEMA, 'created': now(), 'items': items, 'totals': totals, 'pools': accounting,
            'retire_order': order}


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
            count = f" {row['member_count']} entries," if row.get('member_count') else ''
            out(f"  {row['path']}  [{row['kind']}]{count}  {human(row['bytes'])} (frees {human(row['freed_alone'])} "
                f"alone)  owner {row['owner'] or '-'}: {row['reason']}")
    for pool in result.get('pools') or ():
        out(f"POOL {pool['pool']}: {pool['objects']} objects, {human(pool['bytes'])}; the kept set alone needs "
            f"{human(pool['kept_needs_bytes'])}; expiring in this plan {human(pool['expiring_bytes'])}; held only by "
            f"items that are not kept {human(pool['held_by_others_bytes'])}")
    if result.get('retire_order'):
        out('RETIRE ORDER (runs not kept; each with every run above it, pooled objects included):')
        for at, row in enumerate(result['retire_order'], 1):
            out(f"  {at:3d}. {row['path']} [{row['decision']}]  +{human(row['frees_with_those_before'])}  "
                f"= {human(row['cumulative_freed'])}")
    for log in result.get('log_trim') or ():
        out(f"USE LOG {log['path']}: {log['lines']} lines, {human(log['bytes'])}; older than {log['cutoff']} and of no "
            f"named run: {log['expiring_lines']} lines, {human(log['expiring_bytes'])} (a trim moves them out)")


def expired_paths(result):
    """Every path the plan's expired items would remove, one per member entry for the unit-cache rows."""
    paths = []
    for row in result['items']:
        if row['decision'] == EXPIRE:
            paths += row.get('members') or [row['path']]
    return paths


def public(result):
    """The plan as written to --json: the unit-cache rows give their entry count and a sample, not every member."""
    copy = dict(result, items=[{k: v for k, v in row.items() if k != 'members'} for row in result['items']])
    return copy


def _writable(function, path, _):
    os.chmod(os.path.dirname(path), stat_module.S_IRWXU)
    function(path)


def _remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, onerror=_writable)
    else:
        return False  # already gone (inside an item deleted before it)
    return True


def delete(result, only=None, out=print):
    """Delete the expired items (only those listed in ONLY when given: an item's path, or one expired unit entry of
    an item). Returns the deleted paths."""
    wanted = {os.path.normpath(str(p)) for p in only} if only else None
    deleted, matched = [], set()
    for row in result['items']:
        if row['decision'] != EXPIRE:
            continue
        members = row.get('members')
        if members is not None:
            whole = wanted is None or os.path.normpath(row['path']) in wanted
            chosen = members if whole else [p for p in members if os.path.normpath(p) in wanted]
            if whole and wanted is not None:
                matched.add(os.path.normpath(row['path']))
            removed = 0
            for member in chosen:
                matched.add(os.path.normpath(member))
                if _remove(Path(member)):
                    deleted.append(str(member))
                    removed += 1
            if removed:
                out(f'Deleted {removed} files of {row["path"]}')
            continue
        if wanted is not None and os.path.normpath(row['path']) not in wanted:
            continue
        path = Path(row['path'])
        if row['kind'] == 'run' and run_state(path).get('status') == 'running':
            out(f'[warning] {path}: started building again; not deleted')
            continue
        if not _remove(path):
            continue
        deleted.append(str(path))
        matched.add(os.path.normpath(str(path)))
        out(f'Deleted {path} ({human(row["bytes"])})')
    if wanted is not None:
        for path in sorted(wanted - matched):
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
    p.add_argument('--json', type=Path, help='write the plan here, and every expired path, one per line, in '
                                            'FILE.expired-paths.txt beside it')
    p.add_argument('--keep-series', type=int, default=KEEP_SERIES,
                   help='release series whose runs are kept by the usual rules (default %(default)s: the line being '
                        'built and the last two releases); runs of older series expire unless pinned; 0 = off')
    p.add_argument('--grace-days', type=int, default=GRACE_DAYS,
                   help='unit cache entries used or written within this many days are kept (default %(default)s); '
                        'older ones expire unless a kept run, or a run a kept run\'s stage came from, used or wrote '
                        'them; 0 = no ageing (the caches kept whole)')
    p.add_argument('--jobs', type=int, help='processes for the use logs and the cache walks (default: the build '
                                            'job count, AMIWIND_BUILD_JOBS)')
    p.add_argument('--delete', action='store_true', help='really delete the expired items (default: report only)')
    p.add_argument('--item', action='append', type=Path, help='with --delete: delete only these expired items')
    p.add_argument('--items-file', type=Path, help='with --delete: more --item paths, one per line')
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
    items = list(args.item or [])
    if args.items_file:
        items += [Path(line.strip()) for line in args.items_file.read_text(encoding='utf-8').splitlines() if line.strip()]
        if not items:
            parser.error('--items-file %s lists no item' % args.items_file)
    if items and not args.delete:
        parser.error('--item and --items-file need --delete')
    result = plan(roots, args.workspace, registry, args.pins, extra_pools=args.pool, keep_series=args.keep_series,
                  grace_days=max(0, args.grace_days), jobs=args.jobs)
    report(result)
    if args.json:
        stem = args.json.name[:-len('.json')] if args.json.name.endswith('.json') else args.json.name
        listing = args.json.with_name(stem + '.expired-paths.txt')
        paths = expired_paths(result)
        listing.parent.mkdir(parents=True, exist_ok=True)
        listing.write_text(''.join(p + '\n' for p in paths), encoding='utf-8', newline='\n')
        write_json(args.json, dict(public(result), expired_paths_file=str(listing), expired_paths_count=len(paths)))
        print(f'Plan: {args.json}; expired paths ({len(paths)}): {listing}')
    if args.delete:
        delete(result, items or None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
