#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""perf_db: one SQLite database of every build and gate measurement, kept intact and comparable.

Every run's numbers (stage times, CPU and cores, memory peaks, gate test counts, CHIM heap per frame, stair walks,
image and world sizes, host CPU samples) are read from the files the builder and the gate write and stored as
rows that are never changed again. Each file that was read is recorded with its SHA-256; a file already read with
the same SHA-256 is skipped, the same path with different bytes is refused (rows are append-only: the database
keeps what was measured, it never rewrites it). Growing JSON-lines ledgers are read in appended segments; a
ledger whose already-read part changed is refused the same way.

With --store DIR every file read is also kept, compressed, under its SHA-256 (DIR/sha/<ab>/<sha>.gz) and listed
in DIR/MANIFEST.jsonl, so the whole database can be rebuilt from exactly the bytes it saw (`rebuild`), even after
the run folders are deleted. Same inputs, same rows: two rebuilds give the same canonical SHA-256 (`canonical`).

Standard library only (sqlite3), Python 3.10 or newer, no game data. docs/PERF_DATABASE.md describes the tables,
the commands and how to run it in a container.

    perf_db.py --db FILE [--store DIR] ingest PATH [PATH ...]
    perf_db.py --db FILE compare --metric heap.peak --frame frames/x-03/y-02 [--runs A B C]
    perf_db.py --db FILE stage-history --stage chim [--like PATTERN]
    perf_db.py --db FILE run RUN
    perf_db.py --db FILE gate-summary [--day YYYY-MM-DD]
    perf_db.py --db FILE sources [--run RUN]
    perf_db.py --db FILE export --csv DIR | --table NAME
    perf_db.py --db FILE canonical
    perf_db.py --db FILE dump --sql OUT.sql.gz
    perf_db.py --store DIR rebuild --out NEW.db
    perf_db.py schema
"""
import argparse
import contextlib
import csv
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
import tarfile

SCHEMA = 'perf-db-1'
PARSER = 3                      # bump when a parser reads a file differently (a rebuild re-reads every file)
SIZE_CAP = 32 * 1024 * 1024     # files bigger than this are not read (the 100+ MB image heap/stair dumps)
DB_ENV, STORE_ENV = 'AMIWIND_PERF_DB', 'AMIWIND_PERF_STORE'

# files read from a run folder (or a retired run's archive), by their path inside the run folder
RUN_FILES = {
    'build-state.json': 'build-state',
    'build-profile.json': 'build-profile',
    'build-progress.json': 'build-progress',
    'build-summary.json': 'build-summary',
    'chim-world/chim-heap.json': 'chim-heap',
    'chim-world/chim-stairs.json': 'chim-stairs',
    'chim-world/chim-timing.json': 'chim-timing',
    'chim-world/chim-validate.json': 'chim-validate',
    'chim-world/chim-receipt.json': 'chim-receipt',
    'image/chim-frame-heap.json': 'image-heap',
    'image/stair-walk.json': 'image-stairs',
    'image/world-partitions.json': 'world-partitions',
    'image/heap-watcher.json': 'heap-watcher',
}
# JSON-lines ledgers, by file name
LEDGERS = {
    'build-ledger.jsonl': 'ledger-build',
    'gate-ledger.jsonl': 'ledger-gate',
    'reuse-ledger.jsonl': 'ledger-reuse',
    'samples.jsonl': 'ledger-samples',
    'optimizer-list.jsonl': 'ledger-optimizer',
    'TRIALS.jsonl': 'ledger-trials',
    'aw-trials.jsonl': 'ledger-aw-trials',
}
# which origin wins when several files describe the same run / stage / frame (lower = closer to the measurement)
RANK = {'build-state': 10, 'build-summary': 11, 'build-profile': 12, 'build-progress': 13,
        'chim-heap': 20, 'image-heap': 21, 'chim-stairs': 20, 'image-stairs': 21, 'chim-validate': 22,
        'chim-receipt': 23, 'world-partitions': 24, 'chim-timing': 25, 'heap-watcher': 26,
        'aw-result': 30, 'aw-request': 31, 'trials': 40, 'ledger-build': 50, 'ledger-gate': 50, 'ledger-reuse': 51,
        'ledger-optimizer': 52, 'ledger-samples': 53}
ARCHIVE_SUFFIXES = ('.tar.gz', '.tgz', '.tar')


class PerfDbError(Exception):
    """A refusal or a broken input, with a message for the user."""


class Conflict(PerfDbError):
    """A path already read with other bytes: the database never overwrites what it recorded."""


# --------------------------------------------------------------------------
# Small helpers

def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def num(value):
    """A number as float, or None (booleans and text are not numbers)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def intv(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def text(value):
    return value if isinstance(value, str) and value != '' else None


def dig(data, *keys):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data


def as_json(value):
    return None if value in (None, {}, []) else canonical_json(value)


def now_stamp():
    return datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')


TIME_RE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?\s*(Z|[+-]\d{2}:?\d{2})?$')


def to_utc(value):
    """'2026-10-10 19:52:55 +0300', '2026-10-10T16:53:34+00:00', '...+0000' or '...Z' as 'YYYY-MM-DDTHH:MM:SSZ';
    None when the text has no zone (a local time without a zone cannot be ordered against the others)."""
    if not isinstance(value, str):
        return None
    m = TIME_RE.match(value.strip())
    if not m or not m.group(8):
        return None
    y, mo, d, h, mi = (int(m.group(i)) for i in range(1, 6))
    s = int(m.group(6) or 0)
    zone = m.group(8)
    offset = 0
    if zone != 'Z':
        sign = -1 if zone[0] == '-' else 1
        digits = zone[1:].replace(':', '')
        offset = sign * (int(digits[:2]) * 60 + int(digits[2:]))
    moment = datetime.datetime(y, mo, d, h, mi, s) - datetime.timedelta(minutes=offset)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def frame_key(path):
    """'chim/frames/x-03/y-02/frame.ccf' or '.../frame.bsp' -> 'frames/x-03/y-02' (other names unchanged)."""
    if not isinstance(path, str):
        return None
    p = path.replace('\\', '/').strip('/')
    if p.startswith('chim/'):
        p = p[5:]
    for tail in ('/frame.ccf', '/frame.bsp', '/frame.chim'):
        if p.endswith(tail):
            return p[:-len(tail)]
    return p


RUN_NAME_RE = re.compile(r'^(?P<date>\d{4}_\d{2}_\d{2})_(?P<version>v\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)_'
                         r'(?P<purpose>[A-Za-z0-9][A-Za-z0-9.-]*)_(?P<git>[0-9a-f]{4,40}|nogit)$')


def run_name(value):
    """The run name of a run folder path or a label ('NAME (what it was)' -> 'NAME')."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().split(' (', 1)[0].strip()
    return PurePosixPath(value.replace('\\', '/').rstrip('/')).name or None


def name_facts(name):
    """version, purpose and git short hash from a run name that follows the naming rule."""
    m = RUN_NAME_RE.match(name or '')
    if not m:
        return {}
    return {'version': m.group('version')[1:], 'purpose': m.group('purpose'), 'commit': m.group('git')}


def run_kind(name, hint=None):
    n = (name or '').lower()
    if n.startswith('gate-') or re.search(r'_gate(-|_|$)', n):
        return 'gate'
    if 'miniwind' in n or re.match(r'mw\d*-', n):
        return 'miniwind'
    return hint or 'build'


def tree_hash(files):
    """SHA-256 hash-tree root of {path: sha256} (sorted 'path\\0sha\\n' lines)."""
    if not isinstance(files, dict) or not files:
        return None
    body = ''.join(f'{path}\0{files[path]}\n' for path in sorted(files) if isinstance(files[path], str))
    return sha256(body.encode('utf-8'))


def flags_of(command):
    """The build.py arguments of a docker command line (the part after tools/build.py)."""
    if not isinstance(command, str) or 'tools/build.py' not in command or ' --check' in command:
        return None
    return command.split('tools/build.py', 1)[1].split()


# --------------------------------------------------------------------------
# Schema

TABLES = {
    'meta': '''key TEXT PRIMARY KEY, value TEXT NOT NULL''',
    'source_files': '''id INTEGER PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
        size INTEGER NOT NULL, byte_offset INTEGER NOT NULL DEFAULT 0, first_line INTEGER NOT NULL DEFAULT 0,
        lines INTEGER NOT NULL DEFAULT 0, file_sha256 TEXT, file_size INTEGER, run TEXT, via TEXT,
        stored INTEGER NOT NULL DEFAULT 0, ingested_at TEXT NOT NULL, row_count INTEGER NOT NULL DEFAULT 0, error TEXT,
        UNIQUE(path, byte_offset)''',
    'runs': '''run TEXT NOT NULL, kind TEXT, run_path TEXT, label TEXT, version TEXT, commit_hash TEXT, tree_hash TEXT,
        builder TEXT, chim_version TEXT, purpose TEXT, recipe TEXT, flags TEXT, flags_sha256 TEXT, requester TEXT,
        reason TEXT, started TEXT, started_utc TEXT, finished TEXT, finished_utc TEXT, wall_s REAL, result TEXT,
        failed_stage TEXT, reuse_from TEXT, stages_total INTEGER, stages_reused INTEGER, stages_rebuilt INTEGER,
        unexpected_rebuilds INTEGER, compiler_warnings INTEGER, host_load TEXT''',
    'stages': '''run TEXT NOT NULL, stage TEXT NOT NULL, status TEXT, reused INTEGER, wall_s REAL, cpu_s REAL,
        cores REAL, jobs INTEGER, jobs_mean REAL, started_s REAL, peak_rss_bytes INTEGER, peak_tree_rss_bytes INTEGER,
        read_bytes INTEGER, write_bytes INTEGER, expected_s REAL, expected_basis TEXT, fingerprint TEXT,
        returncode INTEGER, host TEXT''',
    'gates': '''run TEXT NOT NULL, gate INTEGER, commit_hash TEXT, status TEXT, tests_run INTEGER, failures INTEGER,
        errors INTEGER, skipped INTEGER, unexpected_skips INTEGER, engine_warnings INTEGER, wall_s REAL, suite_s REAL,
        queue_wait_s REAL, staging_s REAL, parts TEXT''',
    'heap': '''run TEXT NOT NULL, frame TEXT NOT NULL, map TEXT, peak_bytes INTEGER, budget_bytes INTEGER,
        headroom_bytes INTEGER, median_bytes INTEGER, positions INTEGER, positions_over INTEGER, ring_models INTEGER,
        ring_chunks INTEGER, ring_textures INTEGER, load_peak_bytes INTEGER, load_headroom_bytes INTEGER,
        load_positions_over INTEGER, zone_bytes INTEGER, streamed_bytes INTEGER, largest_block_bytes INTEGER,
        ok INTEGER, breakdown TEXT, extra TEXT''',
    'stair': '''run TEXT NOT NULL, frame TEXT NOT NULL, steps INTEGER, passed INTEGER, covered INTEGER, failed INTEGER,
        untestable INTEGER, gating_failures INTEGER, advisory_failures INTEGER, walked INTEGER, reused INTEGER,
        sampled INTEGER, seconds REAL, status TEXT, by_kind TEXT''',
    'sizes': '''run TEXT NOT NULL, item TEXT NOT NULL, class TEXT, bytes INTEGER, count INTEGER, sha256 TEXT''',
    'metrics': '''run TEXT NOT NULL, scope TEXT NOT NULL, name TEXT NOT NULL, value REAL, value_text TEXT''',
    'reuse': '''run TEXT NOT NULL, stage TEXT NOT NULL, class TEXT, cause TEXT''',
    'optimizer': '''run TEXT, label TEXT, added_at TEXT, stage TEXT, reason TEXT, detail TEXT, recoverable_s REAL,
        critical INTEGER, status TEXT''',
    'cpu_samples': '''t TEXT NOT NULL, container TEXT NOT NULL, cpu_pct REAL, cores REAL, mem TEXT''',
}
# every measurement table carries where its row came from
COMMON = '''id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES source_files(id), seq INTEGER NOT NULL,
        origin TEXT NOT NULL, rank INTEGER NOT NULL, line INTEGER'''
MEASUREMENTS = ('runs', 'stages', 'gates', 'heap', 'stair', 'sizes', 'metrics', 'reuse', 'optimizer', 'cpu_samples')
INDEXES = {'runs': 'run', 'stages': 'run, stage', 'gates': 'run', 'heap': 'frame, run', 'stair': 'frame, run',
           'sizes': 'run, item', 'metrics': 'run, scope, name', 'reuse': 'run', 'optimizer': 'run',
           'cpu_samples': 't'}
# merged views: one row per key, each column from the best-ranked row that has it
VIEWS = {
    'run_view': ('runs', ('run',)),
    'stage_view': ('stages', ('run', 'stage')),
    'heap_view': ('heap', ('run', 'frame')),
    'stair_view': ('stair', ('run', 'frame')),
    'gate_view': ('gates', ('run',)),
    'size_view': ('sizes', ('run', 'item')),
}


def columns(table):
    names = []
    for part in re.split(r',\s*(?![^()]*\))', TABLES[table]):
        part = part.strip()
        if part and not part.upper().startswith('UNIQUE'):
            names.append(part.split()[0])
    return names


def ddl():
    statements = []
    for table, body in TABLES.items():
        if table in MEASUREMENTS:
            body = COMMON + ',\n        ' + body + ',\n        UNIQUE(source_id, seq)'
        statements.append(f'CREATE TABLE {table} (\n        {body})')
    for table, cols in INDEXES.items():
        statements.append(f'CREATE INDEX idx_{table} ON {table} ({cols})')
    statements.append('CREATE INDEX idx_source_files_run ON source_files (run)')
    for table in TABLES:
        for action in ('UPDATE', 'DELETE'):
            statements.append(f"CREATE TRIGGER no_{action.lower()}_{table} BEFORE {action} ON {table} "
                              f"BEGIN SELECT RAISE(ABORT, 'perf db rows are append-only ({table})'); END")
    for view, (table, keys) in VIEWS.items():
        keyset = ' AND '.join(f'x.{k} = k.{k}' for k in keys)
        cols = [c for c in columns(table) if c not in keys]
        parts = [f'k.{k} AS {k}' for k in keys]
        for c in cols:
            parts.append(f'(SELECT x.{c} FROM {table} x WHERE {keyset} AND x.{c} IS NOT NULL '
                         f'ORDER BY x.rank, x.source_id, x.seq LIMIT 1) AS {c}')
        parts.append(f'(SELECT x.origin FROM {table} x WHERE {keyset} ORDER BY x.rank, x.source_id, x.seq LIMIT 1) '
                     f'AS origin')
        statements.append(f'CREATE VIEW {view} AS SELECT ' + ',\n    '.join(parts)
                          + f'\n  FROM (SELECT DISTINCT {", ".join(keys)} FROM {table}) k')
    return statements


# --------------------------------------------------------------------------
# Content store: every file read, compressed, under its SHA-256, plus the manifest of every read in order

class Store:
    def __init__(self, root, writable=True):
        self.root = Path(root)
        self.writable = writable
        if writable:
            (self.root / 'sha').mkdir(parents=True, exist_ok=True)

    def path(self, digest):
        return self.root / 'sha' / digest[:2] / f'{digest}.gz'

    def put(self, data, digest):
        target = self.path(digest)
        if target.is_file():
            if sha256(self.get(digest)) == digest:
                return
            raise PerfDbError(f'store: {target} does not hold {digest}')
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + f'.part{os.getpid()}')
        with open(part, 'wb') as handle:
            with gzip.GzipFile(fileobj=handle, mode='wb', mtime=0, filename='') as packed:
                packed.write(data)
        os.replace(part, target)
        if sha256(self.get(digest)) != digest:
            raise PerfDbError(f'store: {target} read back with another SHA-256')

    def get(self, digest):
        with gzip.open(self.path(digest), 'rb') as handle:
            data = handle.read()
        if sha256(data) != digest:
            raise PerfDbError(f'store: {self.path(digest)} does not hold {digest}')
        return data

    def append(self, entry):
        with open(self.root / 'MANIFEST.jsonl', 'a', encoding='utf-8', newline='\n') as handle:
            handle.write(canonical_json(entry) + '\n')
            handle.flush()
            os.fsync(handle.fileno())

    def manifest(self):
        path = self.root / 'MANIFEST.jsonl'
        if not path.is_file():
            return []
        entries = []
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except ValueError as error:
                    raise PerfDbError(f'{path}:{number}: not JSON ({error})')
        return entries


@contextlib.contextmanager
def write_lock(db_path):
    """One writer at a time (a lock file next to the database; best effort where flock is missing)."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    with open(str(db_path) + '.lock', 'ab') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


# --------------------------------------------------------------------------
# The database

class PerfDb:
    def __init__(self, path, store=None, create=True, stale_hours=6.0):
        self.path = str(path)
        self.store = store
        self.stale_hours = stale_hours
        if not create and not Path(self.path).is_file():
            raise PerfDbError(f'{self.path}: no such database')
        if create:
            self.db = sqlite3.connect(self.path, timeout=120, isolation_level=None)
            self.db.execute('PRAGMA foreign_keys = ON')
        else:   # queries open the file read-only: they can never change it
            uri = Path(self.path).resolve().as_uri() + '?mode=ro'
            self.db = sqlite3.connect(uri, uri=True, timeout=120, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout = 120000')
        self.messages = []
        self.parse_errors = []
        self.counts = {}
        exists = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()
        if not exists:
            if not create:
                raise PerfDbError(f'{self.path}: not a perf database')
            self.db.execute('BEGIN IMMEDIATE')
            for statement in ddl():
                self.db.execute(statement)
            self.db.executemany('INSERT INTO meta (key, value) VALUES (?, ?)',
                                [('schema', SCHEMA), ('parser', str(PARSER)), ('created_at', now_stamp())])
            self.db.execute('COMMIT')
        else:
            schema = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if not schema or schema[0] != SCHEMA:
                raise PerfDbError(f'{self.path}: schema {schema and schema[0]!r}, this tool writes {SCHEMA!r}')
            parser = self.db.execute("SELECT value FROM meta WHERE key='parser'").fetchone()
            if parser and parser[0] != str(PARSER):
                self.messages.append(f'note: database parsed with parser {parser[0]}, this tool is parser {PARSER}: '
                                     'new files use the new parser; `rebuild` re-reads everything with one parser')

    def close(self):
        self.db.close()

    def say(self, message):
        self.messages.append(message)

    # ---- source bookkeeping

    def _source_rows(self, path):
        return self.db.execute('SELECT id, sha256, size, byte_offset, first_line, lines, file_sha256, file_size '
                               'FROM source_files WHERE path = ? ORDER BY byte_offset', (path,)).fetchall()

    def ingest_blob(self, path, kind, data, run=None, via=None, ingested_at=None, store=True, parse=None):
        """One whole file (not a ledger). Returns 'new', 'same' or raises Conflict."""
        digest = sha256(data)
        rows = self._source_rows(path)
        if rows:
            if rows[0][1] == digest:
                return 'same'
            raise Conflict(f'{path}: already read with SHA-256 {rows[0][1][:16]}..., now {digest[:16]}... '
                           '(rows are append-only: the database never overwrites a measurement)')
        entry = {'path': path, 'kind': kind, 'sha256': digest, 'size': len(data), 'run': run, 'via': via,
                 'stored': bool(store and self.store is not None), 'ingested_at': ingested_at or now_stamp()}
        parse = parse if parse is not None else PARSERS.get(kind)
        self._record(entry, data, parse)
        return 'new'

    def _record(self, entry, data, parse):
        """Parses first (rows held in memory), then writes the source row and its rows in one transaction."""
        emitter = Emitter()
        error = None
        if parse is not None and data is not None:
            try:
                parse(emitter, data, entry)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError, UnicodeDecodeError) as exc:
                emitter.rows = []
                error = f'{type(exc).__name__}: {exc}'[:500]
                self.parse_errors.append(entry['path'])
                self.say(f'PARSE ERROR {entry["path"]}: {error} (bytes kept; rebuild after a parser fix)')
        if self.store is not None and entry.get('stored') and data is not None:
            self.store.put(data, entry['sha256'])
        self.db.execute('BEGIN IMMEDIATE')
        try:
            cur = self.db.execute(
                'INSERT INTO source_files (path, kind, sha256, size, byte_offset, first_line, lines, file_sha256, '
                'file_size, run, via, stored, ingested_at, row_count, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (entry['path'], entry['kind'], entry['sha256'], entry['size'], entry.get('byte_offset', 0),
                 entry.get('first_line', 0), entry.get('lines', 0), entry.get('file_sha256'), entry.get('file_size'),
                 entry.get('run'), entry.get('via'), 1 if entry.get('stored') else 0, entry['ingested_at'],
                 len(emitter.rows), error))
            source_id = cur.lastrowid
            emitter.write(self.db, source_id)
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        for table, *_ in emitter.rows:
            self.counts[table] = self.counts.get(table, 0) + 1
        self.counts['source_files'] = self.counts.get('source_files', 0) + 1
        if self.store is not None and entry.get('manifest', True):
            self.store.append({k: entry[k] for k in sorted(entry) if k != 'manifest'})
        return source_id

    def ingest_ledger(self, path, kind, data, via=None, ingested_at=None):
        """A JSON-lines ledger: only complete lines; a new segment for what was appended since the last read.
        Returns 'new', 'same' or raises Conflict when the part already read changed."""
        cut = data.rfind(b'\n') + 1
        data = data[:cut]
        rows = self._source_rows(path)
        start, first_line = 0, 1
        if rows:
            last = rows[-1]
            start = last[3] + last[2]
            first_line = last[4] + last[5]
            if len(data) < start or sha256(data[:start]) != last[6]:
                raise Conflict(f'{path}: the {start} bytes already read changed (a ledger is append-only; '
                               'the database never overwrites a measurement)')
        segment = data[start:]
        if not segment:
            return 'same'
        entry = {'path': path, 'kind': kind, 'sha256': sha256(segment), 'size': len(segment), 'byte_offset': start,
                 'first_line': first_line, 'lines': segment.count(b'\n'), 'file_sha256': sha256(data),
                 'file_size': len(data), 'via': via, 'stored': self.store is not None,
                 'ingested_at': ingested_at or now_stamp()}
        self._record(entry, segment, PARSERS.get(kind))
        return 'new'

    # ---- what a path is

    def ingest_path(self, path, ingested_at=None):
        """Any input: a run folder, a folder of inputs, a run archive, a result JSON, a ledger. Returns a list of
        (logical path, outcome) pairs."""
        p = Path(path)
        if p.is_dir():
            if is_run_dir(p):
                return self.ingest_run_dir(p, ingested_at)
            out = []
            for child in sorted(p.iterdir(), key=lambda c: c.name):
                if child.is_dir() and is_run_dir(child):
                    out += self.ingest_run_dir(child, ingested_at)
                elif child.is_file() and input_kind(child.name):
                    if input_kind(child.name) == 'aw-result' and not is_aw_result(child):
                        continue
                    out += self.ingest_path(child, ingested_at)
            if not out:
                self.say(f'{path}: nothing to read (no run files, archives, results or ledgers)')
            return out
        if not p.is_file():
            raise PerfDbError(f'{path}: no such file or folder')
        kind = input_kind(p.name)
        if kind is None:
            raise PerfDbError(f'{path}: not a run folder, run archive, result JSON or known ledger')
        data = p.read_bytes()
        if kind == 'archive':
            return self.ingest_archive(p.name, data, ingested_at)
        if kind in LEDGERS.values():
            logical = f'ledgers/{p.name}'
            return [(logical, self.ingest_ledger(logical, kind, data, ingested_at=ingested_at))]
        if not is_aw_result(p):
            raise PerfDbError(f'{path}: a JSON file but not an aw result (schema aw-result-1)')
        logical = f'aw-results/{p.name}'
        return [(logical, self.ingest_blob(logical, 'aw-result', data, run=p.name[:-5], ingested_at=ingested_at))]

    def ingest_run_dir(self, folder, ingested_at=None):
        folder = Path(folder)
        name = folder.name
        state = read_json_quiet(folder / 'build-state.json')
        progress = read_json_quiet(folder / 'build-progress.json')
        if (state or {}).get('status') == 'running' or (not state and (progress or {}).get('status') == 'running'):
            # a state that still says running but has not been written for hours belongs to a build that was
            # stopped; the time only decides WHETHER to read the run now, the rows are what the files say
            newest = max((f.stat().st_mtime for f in (folder / 'build-state.json', folder / 'build-progress.json')
                          if f.is_file()), default=0.0)
            age_h = (datetime.datetime.now().timestamp() - newest) / 3600.0
            if age_h < self.stale_hours:
                self.say(f'skipped {name}: still running (a run is read once it has finished)')
                return [(f'runs/{name}', 'running')]
            self.say(f'{name}: state says running but was last written {age_h:.1f} h ago: read as a stopped run')
        out = []
        for rel in sorted(RUN_FILES):
            p = folder / rel
            if not p.is_file():
                continue
            size = p.stat().st_size
            if size > SIZE_CAP:
                self.say(f'not read: runs/{name}/{rel} ({size} bytes, over the {SIZE_CAP} byte cap)')
                continue
            logical = f'runs/{name}/{rel}'
            out.append((logical, self.ingest_blob(logical, RUN_FILES[rel], p.read_bytes(), run=name,
                                                  ingested_at=ingested_at)))
        if not out:
            self.say(f'{name}: no run files found')
        return out

    def ingest_archive(self, filename, data, ingested_at=None):
        """A retired run's archive of its small records: the members land on the same paths as in the run folder,
        so a run read from its folder and later from its archive is recognised by SHA-256."""
        name = filename
        for suffix in ARCHIVE_SUFFIXES:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        logical = f'archives/{filename}'
        rows = self._source_rows(logical)
        digest = sha256(data)
        if rows:
            if rows[0][1] == digest:
                return [(logical, 'same')]
            raise Conflict(f'{logical}: already read with SHA-256 {rows[0][1][:16]}..., now {digest[:16]}...')
        out = []
        try:
            archive = tarfile.open(fileobj=io.BytesIO(data), mode='r:*')
        except tarfile.TarError as error:
            raise PerfDbError(f'{logical}: not a readable archive ({error})')
        with archive:
            members = {}
            for member in archive.getmembers():
                rel = member.name.lstrip('./') if member.name.startswith('./') else member.name
                rel = rel.lstrip('/')
                if member.isfile() and rel in RUN_FILES and member.size <= SIZE_CAP:
                    members[rel] = member
            for rel in sorted(members):
                content = archive.extractfile(members[rel]).read()
                path = f'runs/{name}/{rel}'
                out.append((path, self.ingest_blob(path, RUN_FILES[rel], content, run=name, via=logical,
                                                   ingested_at=ingested_at)))
        # the archive itself: recorded (SHA-256, size), its bytes are not kept (the members are)
        entry = {'path': logical, 'kind': 'archive', 'sha256': digest, 'size': len(data), 'run': name,
                 'stored': False, 'ingested_at': ingested_at or now_stamp()}
        self._record(entry, None, None)
        out.append((logical, 'new'))
        return out

    # ---- rebuild

    def replay(self, entries):
        """Re-reads every manifest entry from the store, in order, with its recorded time (rebuild)."""
        done = set()
        for entry in entries:
            key = (entry['path'], entry.get('byte_offset', 0), entry['sha256'])
            if key in done:
                continue
            done.add(key)
            data = self.store.get(entry['sha256']) if entry.get('stored') else None
            entry = dict(entry, manifest=False)
            self._record(entry, data, PARSERS.get(entry['kind']))


def read_json_quiet(path):
    try:
        with open(path, 'rb') as handle:
            return json.loads(handle.read().decode('utf-8'))
    except (OSError, ValueError):
        return None


def is_run_dir(path):
    return any((Path(path) / name).is_file() for name in ('build-state.json', 'build-summary.json',
                                                           'build-progress.json', 'build-profile.json'))


def is_aw_result(path):
    value = read_json_quiet(path)
    return isinstance(value, dict) and value.get('schema') == 'aw-result-1'


def input_kind(filename):
    if filename in LEDGERS:
        return LEDGERS[filename]
    if filename.endswith(ARCHIVE_SUFFIXES):
        return 'archive'
    if filename.endswith('.json'):
        return 'aw-result'
    return None


# --------------------------------------------------------------------------
# Rows

class Emitter:
    """Collects the rows one source makes; written together with the source row."""

    def __init__(self):
        self.rows = []

    def add(self, table, origin, line=None, **values):
        if table not in MEASUREMENTS:
            raise KeyError(table)
        allowed = set(columns(table))
        unknown = set(values) - allowed
        if unknown:
            raise KeyError(f'{table}: unknown columns {sorted(unknown)}')
        self.rows.append((table, origin, line, values))

    def write(self, db, source_id):
        seqs = {}
        for table, origin, line, values in self.rows:
            seq = seqs.get(table, 0) + 1
            seqs[table] = seq
            names = ['source_id', 'seq', 'origin', 'rank', 'line'] + list(values)
            args = [source_id, seq, origin, RANK.get(origin, 90), line] + list(values.values())
            db.execute(f'INSERT INTO {table} ({", ".join(names)}) VALUES ({", ".join("?" * len(names))})', args)


def load(data):
    value = json.loads(data.decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('not a JSON object')
    return value


def host_summary(stages):
    """Wall-weighted host load over the stages that recorded one."""
    total = busy = other = 0.0
    cpus, busy_any, samples = None, False, 0
    for st in stages:
        host, wall = st.get('host'), num(st.get('wall'))
        if not isinstance(host, dict) or not wall:
            continue
        total += wall
        busy += wall * (num(host.get('busy_percent')) or 0.0)
        other += wall * (num(host.get('other_percent')) or 0.0)
        cpus = intv(host.get('cpus')) or cpus
        busy_any = busy_any or bool(host.get('host_busy'))
        samples += intv(host.get('samples')) or 0
    if not total:
        return None
    return {'busy_percent': round(busy / total, 1), 'other_percent': round(other / total, 1), 'cpus': cpus,
            'host_busy': busy_any, 'samples': samples}


def parse_build_state(out, data, entry):
    st = load(data)
    run = entry['run']
    facts = name_facts(run)
    cache = st.get('stage_cache') if isinstance(st.get('stage_cache'), dict) else {}
    prints = cache.get('fingerprints') if isinstance(cache.get('fingerprints'), dict) else {}
    options = st.get('builder_options') if isinstance(st.get('builder_options'), dict) else None
    flags = st.get('builder_options')
    steps = [s for s in st.get('steps') or [] if isinstance(s, dict) and s.get('name')]
    out.add('runs', 'build-state', run=run, kind=run_kind(run), version=text(st.get('runtime_version'))
            or text(st.get('version')) or facts.get('version'),
            commit_hash=text(dig(st, 'run_name', 'commit')) or facts.get('commit'),
            tree_hash=tree_hash(st.get('source_sha256')), builder=text(st.get('builder')),
            chim_version=text(st.get('chim_version')), purpose=text(dig(st, 'run_name', 'purpose'))
            or facts.get('purpose'), recipe=text(st.get('recipe')),
            flags=as_json(flags) if options is not None else None,
            flags_sha256=sha256(canonical_json(flags).encode('utf-8')) if options is not None else None,
            started=text(st.get('build_started_at')), started_utc=to_utc(st.get('build_started_at')),
            wall_s=num(st.get('elapsed_seconds')), result=text(st.get('status')),
            failed_stage=next((s['name'] for s in steps if s.get('status') == 'failed'), None),
            reuse_from=text(cache.get('reuse_from')), stages_total=len(steps) or None,
            stages_reused=sum(1 for s in steps if s.get('reused')) if steps else None)
    for s in steps:
        prof = s.get('profile') if isinstance(s.get('profile'), dict) else {}
        out.add('stages', 'build-state', run=run, stage=s['name'], status=text(s.get('status')),
                reused=1 if s.get('reused') else 0, wall_s=num(s.get('elapsed_seconds')),
                cpu_s=num(prof.get('cpu_seconds')), cores=num(prof.get('cores_avg')), jobs=intv(s.get('jobs')),
                started_s=num(s.get('started_seconds')), peak_rss_bytes=intv(prof.get('peak_process_rss_bytes')),
                read_bytes=intv(prof.get('read_bytes')), write_bytes=intv(prof.get('write_bytes')),
                fingerprint=text(prints.get(s['name'])), returncode=intv(s.get('returncode')))


def parse_build_profile(out, data, entry):
    pr = load(data)
    run = entry['run']
    stages = [s for s in pr.get('stages') or pr.get('steps') or [] if isinstance(s, dict)]
    host = host_summary(stages)
    out.add('runs', 'build-profile', run=run, kind=run_kind(run), version=text(pr.get('version')),
            started=text(pr.get('started_at')), started_utc=to_utc(pr.get('started_at')),
            wall_s=num(pr.get('wall_seconds')), result=text(pr.get('status')), reuse_from=text(pr.get('reuse_from')),
            host_load=as_json(host))
    for s in stages:
        name = s.get('name') or s.get('stage')
        if not name:
            continue
        out.add('stages', 'build-profile', run=run, stage=name, status=text(s.get('status')),
                reused=1 if s.get('reused') else 0, wall_s=num(s.get('wall')),
                cpu_s=num(s.get('cpu_seconds', s.get('cpu'))), cores=num(s.get('cores_avg')), jobs=intv(s.get('jobs')),
                jobs_mean=num(s.get('jobs_mean')), started_s=num(s.get('start')),
                peak_rss_bytes=intv(s.get('peak_process_rss_bytes')),
                peak_tree_rss_bytes=intv(s.get('peak_tree_rss_bytes')), read_bytes=intv(s.get('read_bytes')),
                write_bytes=intv(s.get('write_bytes')), fingerprint=text(s.get('fingerprint')),
                host=as_json(s.get('host')))
    for name, value in sorted((pr.get('overhead') or {}).items()) if isinstance(pr.get('overhead'), dict) else []:
        if num(value) is not None:
            out.add('metrics', 'build-profile', run=run, scope='profile.overhead', name=name, value=num(value))


def parse_build_progress(out, data, entry):
    pg = load(data)
    run = entry['run']
    out.add('runs', 'build-progress', run=run, kind=run_kind(run), started=text(pg.get('started_at')),
            started_utc=to_utc(pg.get('started_at')), wall_s=num(pg.get('elapsed_seconds')),
            result=text(pg.get('status')), host_load=as_json(pg.get('host')))
    for s in pg.get('stages') or []:
        if isinstance(s, dict) and s.get('name'):
            out.add('stages', 'build-progress', run=run, stage=s['name'], status=text(s.get('status')),
                    wall_s=num(s.get('elapsed_seconds')), jobs=intv(s.get('jobs')),
                    expected_s=num(s.get('expected_seconds')), expected_basis=text(s.get('expected_source')))


def parse_build_summary(out, data, entry):
    sm = load(data)
    run = entry['run']
    reuse = sm.get('reuse') if isinstance(sm.get('reuse'), dict) else {}
    out.add('runs', 'build-summary', run=run, kind=run_kind(run), version=text(sm.get('version')),
            started=text(sm.get('started_at')), started_utc=to_utc(sm.get('started_at')),
            finished=text(sm.get('finished_at')), finished_utc=to_utc(sm.get('finished_at')),
            wall_s=num(sm.get('elapsed_seconds')), result=text(sm.get('status')),
            failed_stage=text(sm.get('failed_stage')), reuse_from=text(reuse.get('reuse_from')),
            stages_total=intv(reuse.get('stages')), stages_reused=intv(reuse.get('reused')),
            stages_rebuilt=intv(reuse.get('rebuilt')), unexpected_rebuilds=intv(reuse.get('unexpected')),
            compiler_warnings=intv(dig(sm, 'compiler_warnings', 'count')))
    for row in reuse.get('rows') or []:
        if isinstance(row, dict) and row.get('stage'):
            out.add('reuse', 'build-summary', run=run, stage=row['stage'], cause=text(row.get('cause')),
                    **{'class': text(row.get('class'))})
    output = sm.get('output') if isinstance(sm.get('output'), dict) else {}
    if output.get('path') and intv(output.get('bytes')) is not None:
        out.add('sizes', 'build-summary', run=run, item='image/' + PurePosixPath(str(output['path'])).name,
                bytes=intv(output.get('bytes')), sha256=text(output.get('sha256')), **{'class': 'image'})
    profile = sm.get('profile') if isinstance(sm.get('profile'), dict) else {}
    for key in ('wall_seconds', 'cpu_seconds', 'critical_path_seconds'):
        if num(profile.get(key)) is not None:
            out.add('metrics', 'build-summary', run=run, scope='profile', name=key, value=num(profile.get(key)))
    if num(reuse.get('saved_seconds')) is not None:
        out.add('metrics', 'build-summary', run=run, scope='reuse', name='saved_seconds',
                value=num(reuse.get('saved_seconds')))


def heap_row(out, origin, run, frame, map_name=None):
    load_ring = frame.get('load_ring') if isinstance(frame.get('load_ring'), dict) else {}
    extra = {k: frame[k] for k in ('actor_cache', 'heap_mb', 'before_zone_bytes', 'after_zone_bytes')
             if k in frame}
    out.add('heap', origin, run=run, frame=frame_key(frame.get('frame')) or map_name or '?', map=map_name,
            peak_bytes=intv(frame.get('peak_bytes')), budget_bytes=intv(frame.get('budget_bytes')),
            headroom_bytes=intv(frame.get('headroom_bytes')), median_bytes=intv(frame.get('median_bytes')),
            positions=intv(frame.get('positions')), positions_over=intv(frame.get('positions_over_budget')),
            ring_models=intv(frame.get('ring_models')), ring_chunks=intv(frame.get('ring_chunks')),
            ring_textures=intv(frame.get('ring_textures')), load_peak_bytes=intv(load_ring.get('peak_bytes')),
            load_headroom_bytes=intv(load_ring.get('headroom_bytes')),
            load_positions_over=intv(load_ring.get('positions_over_budget')), zone_bytes=intv(frame.get('zone_bytes')),
            streamed_bytes=intv(frame.get('streamed_bytes')), largest_block_bytes=intv(frame.get('largest_block_bytes')),
            ok=intv(frame.get('ok')) if isinstance(frame.get('ok'), bool) else None,
            breakdown=as_json(frame.get('peak_breakdown')), extra=as_json(extra))


def parse_chim_heap(out, data, entry):
    heap = load(data)
    run = entry['run']
    for frame in heap.get('frames') or []:
        if isinstance(frame, dict):
            heap_row(out, 'chim-heap', run, frame)
    for key in ('zone_kib', 'pool_kib', 'pool_slots', 'active_radius', 'load_radius', 'sample_units'):
        if num(heap.get(key)) is not None:
            out.add('metrics', 'chim-heap', run=run, scope='chim-heap', name=key, value=num(heap.get(key)))
    if text(heap.get('status')):
        out.add('metrics', 'chim-heap', run=run, scope='chim-heap', name='status', value_text=heap['status'])


def parse_image_heap(out, data, entry):
    heap = load(data)
    run = entry['run']
    maps = heap.get('maps') if isinstance(heap.get('maps'), dict) else {}
    for name in sorted(maps):
        if isinstance(maps[name], dict):
            heap_row(out, 'image-heap', run, maps[name], map_name=name)


def parse_stairs(out, data, entry):
    st = load(data)
    run = entry['run']
    origin = 'chim-stairs' if entry['kind'] == 'chim-stairs' else 'image-stairs'
    cache = st.get('pass_cache') if isinstance(st.get('pass_cache'), dict) else {}
    sampled = cache.get('sampled') if isinstance(cache.get('sampled'), list) else None
    sampled_keys = {frame_key(s) for s in sampled or []}
    gating, advisory = {}, {}
    for key, rows in (('failures', gating), ('advisory_failures', advisory)):
        for row in st.get(key) or []:
            if isinstance(row, dict):
                fk = frame_key(row.get('map'))
                rows[fk] = rows.get(fk, 0) + 1
    summary = st.get('summary') if isinstance(st.get('summary'), dict) else {}
    totals = {}
    for frame in sorted(summary):
        kinds = summary[frame] if isinstance(summary[frame], dict) else {}
        counts = {}
        for kind in kinds.values():
            for result, count in (kind.items() if isinstance(kind, dict) else ()):
                if intv(count) is not None:
                    counts[result] = counts.get(result, 0) + intv(count)
        for result, count in counts.items():
            totals[result] = totals.get(result, 0) + count
        fk = frame_key(frame)
        out.add('stair', origin, run=run, frame=fk, steps=sum(counts.values()), passed=counts.get('passed', 0),
                covered=counts.get('covered', 0), failed=counts.get('failed', 0),
                untestable=counts.get('untestable', 0), gating_failures=gating.get(fk, 0),
                advisory_failures=advisory.get(fk, 0),
                sampled=(1 if fk in sampled_keys else 0) if sampled is not None else None, by_kind=as_json(kinds))
    walked = intv(cache.get('walked'))
    reused = intv(cache.get('reused'))
    if walked is None and intv(cache.get('misses')) is not None:
        walked, reused = intv(cache.get('misses')), intv(cache.get('hits'))
    out.add('stair', origin, run=run, frame='*', steps=intv(st.get('tested')) or sum(totals.values()) or None,
            passed=totals.get('passed'), covered=totals.get('covered'), failed=totals.get('failed'),
            untestable=totals.get('untestable'), gating_failures=len(st.get('failures') or []),
            advisory_failures=len(st.get('advisory_failures') or []), walked=walked, reused=reused,
            sampled=len(sampled) if sampled is not None else None, seconds=num(st.get('seconds')),
            status=text(st.get('status')),
            by_kind=as_json({k: st[k] for k in ('frames', 'maps', 'tasks', 'stair_rule', 'scope') if k in st}))


def parse_chim_timing(out, data, entry):
    tm = load(data)
    run = entry['run']
    for key, value in (('wall_seconds', tm.get('wall_seconds')), ('jobs', tm.get('jobs')),
                       ('seconds', dig(tm, 'timing', 'seconds')), ('cpu_seconds', dig(tm, 'timing', 'cpu_seconds'))):
        if num(value) is not None:
            out.add('metrics', 'chim-timing', run=run, scope='chim-timing', name=key, value=num(value))
    units = tm.get('units') if isinstance(tm.get('units'), dict) else {}
    for unit in sorted(units):
        for key in ('built', 'reused'):
            if num(dig(units, unit, key)) is not None:
                out.add('metrics', 'chim-timing', run=run, scope='chim-units', name=f'{unit}.{key}',
                        value=num(units[unit][key]))
    sections = {}
    for sec in dig(tm, 'timing', 'sections') or []:
        if isinstance(sec, dict) and sec.get('section'):
            agg = sections.setdefault(sec['section'], [0.0, 0.0, 0])
            agg[0] += num(sec.get('seconds')) or 0.0
            agg[1] += num(sec.get('cpu_seconds')) or 0.0
            agg[2] += 1
    for name in sorted(sections):
        seconds, cpu, count = sections[name]
        for key, value in (('seconds', round(seconds, 3)), ('cpu_seconds', round(cpu, 3)), ('calls', count)):
            out.add('metrics', 'chim-timing', run=run, scope='chim-section', name=f'{name}.{key}', value=value)


def parse_chim_validate(out, data, entry):
    va = load(data)
    run = entry['run']
    m = va.get('measured') if isinstance(va.get('measured'), dict) else {}
    if intv(m.get('bytes_total')) is not None:
        out.add('sizes', 'chim-validate', run=run, item='chim/total', bytes=intv(m['bytes_total']),
                **{'class': 'chim-world'})
    for group, prefix in (('bytes_by_kind', 'chim/kind/'), ('chunk_bytes', 'chim/chunks/'),
                          ('model_bytes', 'chim/models/')):
        values = m.get(group) if isinstance(m.get(group), dict) else {}
        for key in sorted(values):
            if intv(values[key]) is not None:
                out.add('sizes', 'chim-validate', run=run, item=prefix + key, bytes=intv(values[key]),
                        **{'class': group})
    for key in sorted(m):
        if num(m[key]) is not None:
            out.add('metrics', 'chim-validate', run=run, scope='chim-validate', name=key, value=num(m[key]))
    vis = m.get('visibility') if isinstance(m.get('visibility'), dict) else {}
    for key in sorted(vis):
        value = vis[key]
        if num(value) is not None:
            out.add('metrics', 'chim-validate', run=run, scope='chim-visibility', name=key, value=num(value))
        elif isinstance(value, dict):
            for sub in sorted(value):
                if num(value[sub]) is not None:
                    out.add('metrics', 'chim-validate', run=run, scope='chim-visibility', name=f'{key}.{sub}',
                            value=num(value[sub]))
    if intv(va.get('failure_count')) is not None:
        out.add('metrics', 'chim-validate', run=run, scope='chim-validate', name='failure_count',
                value=num(va['failure_count']))


def parse_chim_receipt(out, data, entry):
    rc = load(data)
    run = entry['run']
    frames, classes, kinds = {}, {}, {}
    for f in rc.get('files') or []:
        if not isinstance(f, dict) or intv(f.get('bytes')) is None:
            continue
        path = str(f.get('path') or '').replace('\\', '/')
        size = intv(f['bytes'])
        parts = path.split('/')
        cls = '/'.join(parts[:2]) if len(parts) > 2 else path
        agg = classes.setdefault(cls, [0, 0])
        agg[0] += size
        agg[1] += 1
        kind = text(f.get('kind'))
        if kind:
            agg = kinds.setdefault(kind, [0, 0])
            agg[0] += size
            agg[1] += 1
        if len(parts) >= 4 and parts[0] == 'chim' and parts[1] == 'frames':
            agg = frames.setdefault('/'.join(parts[1:4]), [0, 0])
            agg[0] += size
            agg[1] += 1
    far = [f for f in rc.get('far_terrain') or [] if isinstance(f, dict) and intv(f.get('bytes')) is not None]
    if far:
        classes['far'] = [sum(intv(f['bytes']) for f in far), len(far)]
    for group, values, prefix in (('chim-class', classes, 'chim/class/'), ('chim-record-kind', kinds, 'chim/record/'),
                                  ('chim-frame', frames, 'chim/frame/')):
        for key in sorted(values):
            out.add('sizes', 'chim-receipt', run=run, item=prefix + key, bytes=values[key][0], count=values[key][1],
                    **{'class': group})
    for key in ('chunks', 'meshes', 'models', 'model_variants', 'sectors', 'textures', 'placements',
                'largest_sector_bytes', 'reach_copies'):
        value = rc.get(key)
        if isinstance(value, list):
            value = len(value)
        if num(value) is not None:
            out.add('metrics', 'chim-receipt', run=run, scope='chim-receipt', name=key, value=num(value))


def parse_partitions(out, data, entry):
    wp = load(data)
    run = entry['run']
    for part in wp.get('partitions') or []:
        if isinstance(part, dict) and intv(part.get('bytes')) is not None:
            out.add('sizes', 'world-partitions', run=run,
                    item='partition/' + str(part.get('volume') or part.get('file') or '?'), bytes=intv(part['bytes']),
                    count=len(part.get('files') or []), sha256=text(part.get('sha256')), **{'class': 'partition'})


def parse_heap_watcher(out, data, entry):
    hw = load(data)
    run = entry['run']
    for key in sorted(hw):
        if num(hw[key]) is not None and not isinstance(hw[key], bool):
            out.add('metrics', 'heap-watcher', run=run, scope='heap-watcher', name=key, value=num(hw[key]))
    for key in ('status', 'worst_map'):
        if text(hw.get(key)):
            out.add('metrics', 'heap-watcher', run=run, scope='heap-watcher', name=key, value_text=hw[key])


def parse_aw_result(out, data, entry):
    res = load(data)
    if res.get('schema') != 'aw-result-1':
        raise ValueError(f'not an aw result (schema {res.get("schema")!r})')
    run = text(res.get('run_name')) or entry.get('run')
    kind = text(res.get('kind')) or 'build'
    numbers = res.get('numbers') if isinstance(res.get('numbers'), dict) else {}
    reuse = res.get('reuse') if isinstance(res.get('reuse'), dict) else {}
    timings = res.get('timings') if isinstance(res.get('timings'), dict) else {}
    flags = None
    for command in res.get('commands') or []:
        flags = flags_of(command) or flags
    version = text(res.get('version'))
    out.add('runs', 'aw-result', run=run, kind='gate' if kind == 'gate' else run_kind(run, kind),
            version=version.lstrip('v') if version else None, commit_hash=text(res.get('commit')),
            purpose=name_facts(run).get('purpose'), flags=as_json(flags),
            flags_sha256=sha256(canonical_json(flags).encode('utf-8')) if flags else None,
            requester=text(res.get('requester')), reason=text(res.get('reason')), started=text(res.get('started')),
            started_utc=to_utc(res.get('started')), finished=text(res.get('finished')),
            finished_utc=to_utc(res.get('finished')), wall_s=num(res.get('seconds')), result=text(res.get('status')),
            failed_stage=text(res.get('failed_stage')), reuse_from=text(reuse.get('from')),
            stages_total=intv(numbers.get('stages')), stages_reused=intv(numbers.get('reused_stages')),
            stages_rebuilt=intv(numbers.get('rebuilt_stages')), unexpected_rebuilds=intv(reuse.get('unexpected')))
    if kind == 'gate':
        steps = res.get('steps') if isinstance(res.get('steps'), dict) else {}
        out.add('gates', 'aw-result', run=run, gate=intv(res.get('gate')), commit_hash=text(res.get('commit')),
                status=text(res.get('status')), tests_run=intv(numbers.get('tests_run')),
                failures=intv(numbers.get('failures')), errors=intv(numbers.get('errors')),
                skipped=intv(numbers.get('skipped')), unexpected_skips=intv(numbers.get('unexpected_skips')),
                engine_warnings=intv(numbers.get('engine_warnings')), wall_s=num(res.get('seconds')),
                suite_s=num(timings.get('suite_s')), queue_wait_s=num(timings.get('queue_wait_s')),
                parts=as_json({name: dig(step, 'exit') for name, step in sorted(steps.items())}))
    for key in sorted(timings):
        if num(timings[key]) is not None and key not in ('queued_at', 'started_at'):
            out.add('metrics', 'aw-result', run=run, scope='aw-timings', name=key, value=num(timings[key]))


def parse_ledger(out, data, entry):
    kind = entry['kind']
    handler = LEDGER_LINES.get(kind)
    for number, raw in enumerate(data.decode('utf-8', errors='replace').split('\n')):
        if not raw.strip():
            continue
        line = entry.get('first_line', 1) + number
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict) and handler:
            handler(out, row, line)


def ledger_build(out, row, line):
    source = row.get('source')
    run = run_name(row.get('run')) if source == 'build-state' and row.get('run') else run_name(row.get('build'))
    if not run or not row.get('stage'):
        return
    origin = 'ledger-build'
    out.add('runs', origin, line=line, run=run, kind=run_kind(run), run_path=text(row.get('run')),
            label=text(row.get('build')), version=text(row.get('version')) or name_facts(run).get('version'),
            started=text(row.get('build_started_at') or row.get('started_at')),
            started_utc=to_utc(row.get('build_started_at') or row.get('started_at')),
            reuse_from=text(row.get('reuse_from')))
    out.add('stages', origin, line=line, run=run, stage=row['stage'], status=text(row.get('status')),
            reused=None if row.get('reused') is None else (1 if row.get('reused') else 0),
            wall_s=num(row.get('wall_s')), cpu_s=num(row.get('cpu_s')), cores=num(row.get('cores_avg')),
            jobs=intv(row.get('jobs')), jobs_mean=num(row.get('jobs_mean')), started_s=num(row.get('started_s')),
            returncode=intv(row.get('returncode')), host=as_json(row.get('host')))


def ledger_gate(out, row, line):
    gate = intv(row.get('gate'))
    if gate is None:
        return
    run = f'gate-{gate}'
    status = 'passed' if row.get('ok') else ('failed' if row.get('complete') else 'incomplete')
    out.add('runs', 'ledger-gate', line=line, run=run, kind='gate', commit_hash=text(row.get('head')),
            started=text(row.get('start')), started_utc=to_utc(row.get('start')), finished=text(row.get('end')),
            finished_utc=to_utc(row.get('end')), wall_s=num(row.get('wall_seconds')), result=status)
    staging = num(row.get('staging_ms'))
    out.add('gates', 'ledger-gate', line=line, run=run, gate=gate, commit_hash=text(row.get('head')), status=status,
            tests_run=intv(row.get('tests_run')), failures=intv(row.get('failures')), errors=intv(row.get('errors')),
            wall_s=num(row.get('wall_seconds')), suite_s=num(row.get('suite_seconds')),
            queue_wait_s=num(row.get('queue_wait_s')), staging_s=staging / 1000.0 if staging is not None else None,
            parts=as_json({'exit_codes': row.get('exit_codes'), 'parts_end_s': row.get('parts_end_s'),
                           'host_cpu_mean': row.get('host_cpu_mean'), 'overlap_gates': row.get('overlap_gates')}))


def ledger_reuse(out, row, line):
    run = run_name(row.get('run'))
    if not run:
        return
    out.add('runs', 'ledger-reuse', line=line, run=run, kind=run_kind(run), run_path=text(row.get('run')),
            reuse_from=text(row.get('reuse_from')), result=text(row.get('status')),
            stages_total=intv(row.get('stages')), stages_reused=intv(row.get('reused')),
            stages_rebuilt=intv(row.get('rebuilt')), unexpected_rebuilds=intv(row.get('unexpected')))
    for r in row.get('rows') or []:
        if isinstance(r, dict) and r.get('stage'):
            out.add('reuse', 'ledger-reuse', line=line, run=run, stage=r['stage'], cause=text(r.get('cause')),
                    **{'class': text(r.get('class'))})


def ledger_samples(out, row, line):
    if not row.get('t') or not row.get('name'):
        return
    out.add('cpu_samples', 'ledger-samples', line=line, t=str(row['t']), container=str(row['name']),
            cpu_pct=num(row.get('cpu_pct')), cores=num(row.get('cores')), mem=text(row.get('mem')))


def ledger_optimizer(out, row, line):
    out.add('optimizer', 'ledger-optimizer', line=line, run=run_name(row.get('build')), label=text(row.get('build')),
            added_at=text(row.get('added_at')), stage=text(row.get('stage')), reason=text(row.get('reason')),
            detail=text(row.get('detail')), recoverable_s=num(row.get('recoverable_s')),
            critical=intv(row.get('critical')) if isinstance(row.get('critical'), bool) else None,
            status=text(row.get('status')))


def ledger_trials(out, row, line):
    run = text(row.get('run_name')) or run_name(row.get('run'))
    if not run:
        return
    facts = name_facts(run)
    version = text(row.get('version'))
    out.add('runs', 'trials', line=line, run=run, kind=run_kind(run), run_path=text(row.get('run')),
            label=text(row.get('note')), version=version.lstrip('v') if version else facts.get('version'),
            commit_hash=text(row.get('commit')) or facts.get('commit'), builder=text(row.get('builder')),
            requester=text(row.get('requester')), reason=text(row.get('reason')),
            started=text(row.get('started')), started_utc=to_utc(row.get('started')),
            finished=text(row.get('finished') or row.get('retired_at')),
            finished_utc=to_utc(row.get('finished') or row.get('retired_at')), result=text(row.get('result')),
            failed_stage=text(row.get('failed_stage')), reuse_from=text(row.get('reuse_from')))
    if intv(row.get('bytes')) is not None:
        out.add('sizes', 'trials', line=line, run=run, item='run-folder', bytes=intv(row['bytes']),
                **{'class': 'run-folder'})


def ledger_aw_trials(out, row, line):
    """aw's own trial log: the gate requests carry the requester and reason that gate results leave out."""
    request = row.get('request') if isinstance(row.get('request'), dict) else None
    if row.get('event') != 'request' or not request or request.get('kind') != 'gate' or not request.get('id'):
        return
    version = text(request.get('version'))
    out.add('runs', 'aw-request', line=line, run=request['id'], kind='gate',
            version=version.lstrip('v') if version else None, commit_hash=text(request.get('commit')),
            purpose=text(request.get('purpose')), requester=text(request.get('requester')),
            reason=text(request.get('reason')))


LEDGER_LINES = {'ledger-build': ledger_build, 'ledger-gate': ledger_gate, 'ledger-reuse': ledger_reuse,
                'ledger-samples': ledger_samples, 'ledger-optimizer': ledger_optimizer, 'ledger-trials': ledger_trials,
                'ledger-aw-trials': ledger_aw_trials}
PARSERS = {'build-state': parse_build_state, 'build-profile': parse_build_profile,
           'build-progress': parse_build_progress, 'build-summary': parse_build_summary, 'chim-heap': parse_chim_heap,
           'image-heap': parse_image_heap, 'chim-stairs': parse_stairs, 'image-stairs': parse_stairs,
           'chim-timing': parse_chim_timing, 'chim-validate': parse_chim_validate, 'chim-receipt': parse_chim_receipt,
           'world-partitions': parse_partitions, 'heap-watcher': parse_heap_watcher, 'aw-result': parse_aw_result}
PARSERS.update({kind: parse_ledger for kind in LEDGERS.values()})


# --------------------------------------------------------------------------
# Queries

METRICS = {
    'heap.peak': ('heap_view', 'peak_bytes', 'frame'), 'heap.headroom': ('heap_view', 'headroom_bytes', 'frame'),
    'heap.budget': ('heap_view', 'budget_bytes', 'frame'), 'heap.median': ('heap_view', 'median_bytes', 'frame'),
    'heap.positions_over': ('heap_view', 'positions_over', 'frame'),
    'heap.load_peak': ('heap_view', 'load_peak_bytes', 'frame'),
    'heap.ring_models': ('heap_view', 'ring_models', 'frame'), 'heap.ring_chunks': ('heap_view', 'ring_chunks', 'frame'),
    'heap.ring_textures': ('heap_view', 'ring_textures', 'frame'),
    'stage.wall': ('stage_view', 'wall_s', 'stage'), 'stage.cpu': ('stage_view', 'cpu_s', 'stage'),
    'stage.cores': ('stage_view', 'cores', 'stage'), 'stage.rss': ('stage_view', 'peak_rss_bytes', 'stage'),
    'stair.steps': ('stair_view', 'steps', 'frame'), 'stair.failed': ('stair_view', 'failed', 'frame'),
    'stair.gating': ('stair_view', 'gating_failures', 'frame'), 'size.bytes': ('size_view', 'bytes', 'item'),
}


def fmt(value):
    if value is None:
        return '-'
    if isinstance(value, float):
        return f'{value:,.3f}'.rstrip('0').rstrip('.') if not value.is_integer() else f'{int(value):,}'
    if isinstance(value, int):
        return f'{value:,}'
    return str(value)


def table_text(headers, rows):
    cells = [[fmt(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    lines = ['  '.join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(),
             '  '.join('-' * w for w in widths)]
    for raw, r in zip(rows, cells):
        lines.append('  '.join(c.rjust(w) if isinstance(v, (int, float)) and not isinstance(v, bool) else c.ljust(w)
                               for v, c, w in zip(raw, r, widths)).rstrip())
    return '\n'.join(lines)


def compare(db, metric, key, runs=None):
    """(headers, rows) of one metric for one frame/stage/item across runs, in run start order."""
    if metric not in METRICS:
        raise PerfDbError(f'unknown metric {metric!r}; known: {", ".join(sorted(METRICS))}')
    view, column, keycol = METRICS[metric]
    if keycol == 'frame':
        key = frame_key(key)
    query = (f'SELECT m.run, r.version, r.result, r.started_utc, m.{column}, m.origin FROM {view} m '
             f'LEFT JOIN run_view r ON r.run = m.run WHERE m.{keycol} = ?')
    args = [key]
    if runs:
        query += f' AND m.run IN ({", ".join("?" * len(runs))})'
        args += list(runs)
    rows = db.execute(query, args).fetchall()
    order = {name: i for i, name in enumerate(runs or [])}
    rows.sort(key=lambda r: (order.get(r[0], 0), r[3] or '', r[0]))
    first = next((r[4] for r in rows if r[4] is not None), None)
    out = []
    for r in rows:
        delta = r[4] - first if r[4] is not None and first is not None else None
        out.append((r[0], r[1], r[2], r[3], r[4], delta, r[5]))
    if runs:
        missing = [name for name in runs if name not in {r[0] for r in rows}]
        out += [(name, None, None, None, None, None, 'not in the database') for name in missing]
    return ['run', 'version', 'result', 'started (UTC)', metric, 'delta vs first', 'from'], out


def stage_history(db, stage, like=None):
    query = ('SELECT s.run, r.version, r.started_utc, s.status, s.reused, s.wall_s, s.cpu_s, s.cores, s.jobs, '
             's.peak_rss_bytes, s.origin FROM stage_view s LEFT JOIN run_view r ON r.run = s.run WHERE s.stage = ?')
    args = [stage]
    if like:
        query += ' AND s.run LIKE ?'
        args.append(like)
    rows = sorted(db.execute(query, args).fetchall(), key=lambda r: (r[2] or '', r[0]))
    return ['run', 'version', 'started (UTC)', 'status', 'reused', 'wall s', 'cpu s', 'cores', 'jobs', 'peak RSS',
            'from'], rows


def gate_summary(db, day=None):
    query = ('SELECT g.run, g.gate, g.status, g.tests_run, g.failures, g.errors, g.wall_s, r.started '
             'FROM gate_view g LEFT JOIN run_view r ON r.run = g.run')
    rows = db.execute(query).fetchall()
    if day:
        rows = [r for r in rows if (r[7] or '')[:10] == day]
    rows.sort(key=lambda r: (r[7] or '', r[0]))
    counts = {}
    for r in rows:
        counts[r[2] or '?'] = counts.get(r[2] or '?', 0) + 1
    return counts, ['run', 'gate', 'status', 'tests', 'failures', 'errors', 'wall s', 'started'], rows


def canonical_lines(db):
    """Every table, rows sorted, as JSON lines (volatile meta keys left out): the content, not the file."""
    for table in sorted(TABLES):
        names = [d[1] for d in db.execute(f'PRAGMA table_info({table})')]
        order = ', '.join(str(i) for i in range(1, len(names) + 1))
        for row in db.execute(f'SELECT * FROM {table} ORDER BY {order}'):
            if table == 'meta' and row[0] not in ('schema', 'parser'):
                continue
            yield canonical_json({'table': table, 'row': dict(zip(names, row))})


def canonical_sha(db):
    digest = hashlib.sha256()
    count = 0
    for line in canonical_lines(db):
        digest.update(line.encode('utf-8') + b'\n')
        count += 1
    return digest.hexdigest(), count


def sql_dump(db, out_path):
    """A gzip SQL text dump (gzip without a time stamp: the same database gives the same bytes)."""
    out_path = Path(out_path)
    if out_path.exists():
        raise PerfDbError(f'{out_path} exists: dumps are never overwritten')
    part = out_path.with_name(out_path.name + '.part')
    digest = hashlib.sha256()
    with open(part, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as packed:
            for line in db.iterdump():
                packed.write((line + '\n').encode('utf-8'))
    with open(part, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    os.replace(part, out_path)
    with open(str(out_path) + '.sha256', 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(f'{digest.hexdigest()}  {out_path.name}\n')
    return digest.hexdigest(), out_path.stat().st_size


def export_csv(db, folder=None, table=None):
    names = list(TABLES) + list(VIEWS)
    targets = [table] if table else names
    for name in targets:
        if name not in names:
            raise PerfDbError(f'unknown table or view {name!r}')
        cur = db.execute(f'SELECT * FROM {name}')
        headers = [d[0] for d in cur.description]
        rows = sorted(cur.fetchall(), key=lambda r: canonical_json(list(r)))
        handle = open(Path(folder) / f'{name}.csv', 'w', encoding='utf-8', newline='') if folder else \
            io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='', write_through=True)
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(rows)
        if folder:
            handle.close()
        else:
            handle.detach()


# --------------------------------------------------------------------------
# Command line

OPENED = []


def open_db(args, create=False):
    path = args.db or os.environ.get(DB_ENV)
    if not path:
        raise PerfDbError(f'no database: give --db FILE or set {DB_ENV}')
    store_dir = args.store or os.environ.get(STORE_ENV)
    store = Store(store_dir) if store_dir and create else None
    db = PerfDb(path, store=store, create=create, stale_hours=getattr(args, 'stale_hours', 6.0))
    OPENED.append(db)
    return db


def print_table(headers, rows, args):
    if getattr(args, 'json', False):
        print(json.dumps([dict(zip(headers, r)) for r in rows], indent=1))
    elif getattr(args, 'csv_out', False):
        writer = csv.writer(sys.stdout, lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(rows)
    else:
        print(table_text(headers, rows))


def cmd_ingest(args):
    db = open_db(args, create=True)
    problems = 0
    totals = {}
    try:
        with write_lock(db.path):
            for path in args.paths:
                try:
                    results = db.ingest_path(path)
                except Conflict as error:
                    problems += 1
                    print(f'CONFLICT: {error}', file=sys.stderr)
                    continue
                except (PerfDbError, OSError) as error:
                    problems += 1
                    print(f'ERROR: {path}: {error}', file=sys.stderr)
                    continue
                for logical, outcome in results:
                    totals[outcome] = totals.get(outcome, 0) + 1
                    if args.verbose or outcome not in ('same',):
                        print(f'{outcome:8} {logical}')
                if args.strict and (not results or any(o == 'running' for _, o in results)):
                    problems += 1
                    print(f'STRICT: {path}: ' + ('still running' if results else 'nothing was read'), file=sys.stderr)
        if args.strict and db.parse_errors:
            problems += len(db.parse_errors)
            print(f'STRICT: {len(db.parse_errors)} files could not be parsed', file=sys.stderr)
    finally:
        for message in db.messages:
            print(message, file=sys.stderr if message.startswith(('PARSE ERROR', 'CONFLICT')) else sys.stdout)
        rows = ', '.join(f'{t} {n}' for t, n in sorted(db.counts.items()))
        print(f'perf db: {totals.get("new", 0)} new, {totals.get("same", 0)} already read, '
              f'{totals.get("running", 0)} still running, {problems} refused; rows added: {rows or "none"}')
        db.close()
    return 1 if problems else 0


def cmd_rebuild(args):
    store_dir = args.store or os.environ.get(STORE_ENV)
    if not store_dir:
        raise PerfDbError(f'rebuild needs --store DIR (or {STORE_ENV})')
    out = Path(args.out)
    if out.exists():
        raise PerfDbError(f'{out} exists: rebuild writes a new database file, it never overwrites one')
    store = Store(store_dir, writable=False)
    entries = store.manifest()
    db = PerfDb(out, store=store, create=True)
    try:
        db.replay(entries)
        digest, count = canonical_sha(db.db)
    finally:
        for message in db.messages:
            print(message, file=sys.stderr)
        db.close()
    print(f'rebuilt {out} from {len(entries)} manifest entries: canonical sha256 {digest} ({count} rows)')
    return 0


def cmd_compare(args):
    db = open_db(args)
    key = args.frame or args.stage or args.item
    if not key:
        raise PerfDbError('compare needs --frame, --stage or --item')
    headers, rows = compare(db.db, args.metric, key, args.runs)
    print(f'{args.metric} at {key}')
    print_table(headers, rows, args)
    return 0


def cmd_stage_history(args):
    db = open_db(args)
    headers, rows = stage_history(db.db, args.stage, args.like)
    print_table(headers, rows, args)
    return 0


def cmd_gate_summary(args):
    db = open_db(args)
    counts, headers, rows = gate_summary(db.db, args.day)
    print_table(headers, rows, args)
    print('counts: ' + ', '.join(f'{k} {v}' for k, v in sorted(counts.items())))
    return 0


def cmd_run(args):
    db = open_db(args)
    cur = db.db.execute('SELECT * FROM run_view WHERE run = ?', (args.run,))
    row = cur.fetchone()
    if row is None:
        raise PerfDbError(f'{args.run}: not in the database')
    for name, value in zip([d[0] for d in cur.description], row):
        if value is not None:
            print(f'{name:20} {value}')
    print()
    stages = db.db.execute('SELECT stage, status, reused, wall_s, cpu_s, cores, jobs, peak_rss_bytes, expected_s, '
                           'origin FROM stage_view WHERE run = ? ORDER BY started_s IS NULL, started_s, stage',
                           (args.run,)).fetchall()
    if stages:
        print(table_text(['stage', 'status', 'reused', 'wall s', 'cpu s', 'cores', 'jobs', 'peak RSS', 'expected s',
                          'from'], stages))
        print()
    heap = db.db.execute('SELECT frame, peak_bytes, budget_bytes, headroom_bytes, positions_over, origin FROM heap_view '
                         'WHERE run = ? ORDER BY headroom_bytes LIMIT ?', (args.run, args.limit)).fetchall()
    if heap:
        print(f'heap, tightest {len(heap)} frames')
        print(table_text(['frame', 'peak', 'budget', 'headroom', 'positions over', 'from'], heap))
        print()
    sources = db.db.execute('SELECT path, sha256, size, ingested_at, row_count, error FROM source_files '
                            'WHERE run = ? ORDER BY path', (args.run,)).fetchall()
    print(table_text(['source', 'sha256', 'bytes', 'ingested', 'rows', 'error'],
                     [(p, s[:16], z, i, n, e) for p, s, z, i, n, e in sources]))
    return 0


def cmd_sources(args):
    db = open_db(args)
    query = 'SELECT id, path, kind, byte_offset, size, sha256, row_count, ingested_at, error FROM source_files'
    args_ = []
    if args.run:
        query += ' WHERE run = ?'
        args_.append(args.run)
    rows = db.db.execute(query + ' ORDER BY id', args_).fetchall()
    print_table(['id', 'path', 'kind', 'offset', 'bytes', 'sha256', 'rows', 'ingested', 'error'], rows, args)
    return 0


def cmd_export(args):
    db = open_db(args)
    if args.csv:
        Path(args.csv).mkdir(parents=True, exist_ok=True)
        export_csv(db.db, folder=args.csv)
        print(f'exported {len(TABLES) + len(VIEWS)} tables and views to {args.csv}')
    else:
        export_csv(db.db, table=args.table)
    return 0


def cmd_canonical(args):
    db = open_db(args)
    digest, count = canonical_sha(db.db)
    print(f'{digest}  {count} rows')
    return 0


def cmd_dump(args):
    db = open_db(args)
    digest, size = sql_dump(db.db, args.sql)
    canon, count = canonical_sha(db.db)
    print(json.dumps({'dump': str(args.sql), 'sha256': digest, 'bytes': size, 'canonical_sha256': canon,
                      'rows': count}, sort_keys=True))
    return 0


def cmd_schema(args):
    for statement in ddl():
        print(statement + ';')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='perf_db.py', description=__doc__.split('\n\n')[0])
    ap.add_argument('--db', help=f'database file (or {DB_ENV})')
    ap.add_argument('--store', help=f'content store folder: keeps every file read, for rebuild (or {STORE_ENV})')
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('ingest', help='read run folders, run archives, result JSON files and ledgers')
    p.add_argument('paths', nargs='+')
    p.add_argument('--verbose', action='store_true', help='also list files already read')
    p.add_argument('--stale-hours', type=float, default=6.0,
                   help='a run whose state says running but was not written for this long is read as stopped')
    p.add_argument('--strict', action='store_true',
                   help='exit 1 unless every path gave at least one file and none is still running (retire flow)')
    p.set_defaults(func=cmd_ingest)
    p = sub.add_parser('compare', help='one metric across runs')
    p.add_argument('--metric', required=True, help=', '.join(sorted(METRICS)))
    p.add_argument('--frame')
    p.add_argument('--stage')
    p.add_argument('--item')
    p.add_argument('--runs', nargs='*')
    p.set_defaults(func=cmd_compare)
    p = sub.add_parser('stage-history', help='one stage across runs')
    p.add_argument('--stage', required=True)
    p.add_argument('--like', help='SQL LIKE pattern on the run name, e.g. %%v0.0.36-dev3%%')
    p.set_defaults(func=cmd_stage_history)
    p = sub.add_parser('gate-summary', help='gates and their results')
    p.add_argument('--day', help='YYYY-MM-DD as written in the gate start time')
    p.set_defaults(func=cmd_gate_summary)
    p = sub.add_parser('run', help='everything about one run')
    p.add_argument('run')
    p.add_argument('--limit', type=int, default=10)
    p.set_defaults(func=cmd_run)
    p = sub.add_parser('sources', help='the files read')
    p.add_argument('--run')
    p.set_defaults(func=cmd_sources)
    p = sub.add_parser('export', help='CSV of every table and merged view, or one of them to stdout')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--csv', metavar='DIR')
    group.add_argument('--table')
    p.set_defaults(func=cmd_export)
    p = sub.add_parser('canonical', help='SHA-256 of the content (every row, sorted)')
    p.set_defaults(func=cmd_canonical)
    p = sub.add_parser('dump', help='gzip SQL text dump (never overwrites)')
    p.add_argument('--sql', required=True)
    p.set_defaults(func=cmd_dump)
    p = sub.add_parser('rebuild', help='a new database from the content store, in the order it was read')
    p.add_argument('--out', required=True)
    p.set_defaults(func=cmd_rebuild)
    p = sub.add_parser('schema', help='print the schema')
    p.set_defaults(func=cmd_schema)
    for name in ('compare', 'stage-history', 'gate-summary', 'sources'):
        sub.choices[name].add_argument('--json', action='store_true')
        sub.choices[name].add_argument('--csv-out', action='store_true', help='CSV to stdout')
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except PerfDbError as error:
        print(f'perf_db: {error}', file=sys.stderr)
        return 2
    finally:
        while OPENED:
            OPENED.pop().close()


if __name__ == '__main__':
    sys.exit(main())
