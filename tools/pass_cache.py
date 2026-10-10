# SPDX-License-Identifier: GPL-3.0-only
"""Content-addressed results of the image step's per-map passes (development builds).

A per-map pass (BSP optimizer, hidden-surface cull) turns one map's bytes into
new bytes and a receipt row, and nothing else: its result depends only on the
input bytes, the pass options and the pass's own source code. A development
build that changed a few maps therefore need not run the pass again on the
others. The key is

    SHA-256(pass name, pass options, SHA-256 of the pass's repository sources
            (its module and every repository module and data file it reads,
            transitively, build_cache.SourceIndex), input map SHA-256)

and the value is the receipt row plus the output bytes when they differ from
the input. A stored output is checked against its recorded SHA-256 when it is
read; a damaged entry is ignored and the pass runs. Entries are written
atomically, so builds can share the folder.

The builder sets AMIWIND_PASS_CACHE to WORKSPACE/cache/image-passes for
development (-devN) builds, and for release candidates and finals only with
--allow-release-reuse (owner decision 9 October 2026: the from-scratch reference
build runs separately on the same commit and its payload is compared file by file
before the release), so a release build that failed late in the image step resumes from
the maps it had finished (BUILD-IMAGE-NO-RESUME-33); otherwise they run every pass on
every map. Every pass
receipt records the run's hits and misses (`pass_cache`). Without the variable,
or with it set to "off", nothing is read or written. Outputs are byte-identical
with and without the cache (tests/test_pass_cache.py, tests/test_release_pass_rules.py;
BUILD-IMAGE-NOT-INCREMENTAL-33).
"""
import hashlib
import json
import os
from pathlib import Path

ENV = 'AMIWIND_PASS_CACHE'
FORMAT = 'AmiWind image pass cache 1'
ROOT = Path(__file__).resolve().parents[1]


def folder():
    """The cache folder, or None when the cache is off."""
    value = os.environ.get(ENV, '')
    if not value or value.lower() == 'off':
        return None
    return Path(value)


def setting(version, workspace, allow_release_reuse=False, release_reuse=None):
    """The builder's value for ENV: the workspace cache for development (-devN)
    versions; for release candidates and finals only with --allow-release-reuse (owner
    decision 9 October 2026: the same rule as the world terrain and media caches, the
    from-scratch reference build runs separately on the same commit and its payload is
    compared file by file before the release; every pass records its hits and misses in
    its receipt), otherwise "off" (every pass on every map)."""
    import re
    allow_release_reuse = allow_release_reuse or bool(release_reuse)  # the older keyword name
    if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version) or allow_release_reuse:
        return str(Path(workspace).resolve() / 'cache' / 'image-passes')
    return 'off'


_DIGESTS = {}


def source_digest(*scripts):
    """SHA-256 of the repository sources the given pass modules read, transitively
    (computed once per process: the repository index hashes every source file)."""
    key = tuple(str(Path(script).resolve()) for script in scripts)
    if key not in _DIGESTS:
        _DIGESTS[key] = _source_digest(scripts)
    return _DIGESTS[key]


def _source_digest(scripts):
    from build_cache import SourceIndex
    index = SourceIndex(ROOT)
    parts = []
    for script in scripts:
        value, _, uncertain = index.digest(Path(script).resolve())
        parts.append([str(Path(script).name), value, uncertain])
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


class PassCache:
    """One pass's view of the cache; picklable, so pool workers get it in their task."""

    def __init__(self, name, options, sources, root=None, tally=None):
        self.name = name
        self.options = options
        self.sources = sources
        self.root = None if root is None else str(root)
        # Hit and miss counts across pool workers: one character per lookup, appended to a
        # per-process file in a folder of this pass run (summary() sums and removes it).
        self.tally = None if tally is None else str(tally)

    @classmethod
    def open(cls, name, options, *scripts):
        """None when the cache is off; otherwise the pass's cache (sources hashed once, here)."""
        root = folder()
        if root is None:
            return None
        tally = None
        try:
            (Path(root) / '.tally').mkdir(parents=True, exist_ok=True)
            import tempfile
            tally = tempfile.mkdtemp(prefix=name + '-', dir=Path(root) / '.tally')
        except OSError:
            pass
        return cls(name, options, source_digest(*scripts), root, tally)

    def _count(self, hit):
        if self.tally is None:
            return
        try:
            with open(Path(self.tally) / f'{os.getpid()}.txt', 'a', encoding='utf-8', newline='\n') as stream:
                stream.write('h' if hit else 'm')
        except OSError:
            pass

    def summary(self):
        """{'sources_sha256', 'hits', 'misses'} of this pass run (for its receipt); removes the tally."""
        hits = misses = 0
        if self.tally is not None:
            folder = Path(self.tally)
            for part in sorted(folder.glob('*.txt')) if folder.is_dir() else []:
                try:
                    text = part.read_text(encoding='ascii')
                except OSError:
                    continue
                hits += text.count('h'); misses += text.count('m')
            import shutil
            shutil.rmtree(folder, ignore_errors=True)
        return {'sources_sha256': self.sources, 'hits': hits, 'misses': misses}

    def key(self, input_sha256):
        return hashlib.sha256(json.dumps([FORMAT, self.name, self.options, self.sources, input_sha256],
                                         sort_keys=True).encode()).hexdigest()

    def _paths(self, input_sha256, root=None):
        key = self.key(input_sha256)
        base = Path(root or self.root) / self.name / key[:2]
        return base / (key + '.json'), base / (key + '.bin')

    def load(self, input_sha256):
        """(row, output bytes or None) recorded for this input, or None. A miss is looked up in the
        --reuse-from workspace's cache (file_cache.fallback_root, read-only) and pooled here on a hit
        (BUILD-CACHE-PER-WORKSPACE-33)."""
        found = self._load(input_sha256)
        if found is None:
            from file_cache import fallback_root
            other = fallback_root(self.root)
            if other is not None:
                found = self._load(input_sha256, other)
                if found is not None:
                    self.store(input_sha256, found[0], found[1])
        self._count(found is not None)
        return found

    def _load(self, input_sha256, root=None):
        meta_path, blob_path = self._paths(input_sha256, root)
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            if meta.get('format') != FORMAT or meta.get('input_sha256') != input_sha256:
                return None
            output = None
            if meta.get('output_sha256') is not None:
                output = blob_path.read_bytes()
                if hashlib.sha256(output).hexdigest() != meta['output_sha256']:
                    return None
            return meta['row'], output
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def store(self, input_sha256, row, output=None):
        """Record a result (output None: the pass left the map unchanged). Never fails a build."""
        meta_path, blob_path = self._paths(input_sha256)
        try:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            suffix = f'.{os.getpid()}.tmp'
            if output is not None:
                partial = blob_path.with_name(blob_path.name + suffix)
                partial.write_bytes(output)
                os.replace(partial, blob_path)
            meta = {'format': FORMAT, 'pass': self.name, 'input_sha256': input_sha256,
                    'output_sha256': None if output is None else hashlib.sha256(output).hexdigest(),
                    'row': row}
            partial = meta_path.with_name(meta_path.name + suffix)
            # Key order kept: rows go into receipts exactly as the pass made them.
            partial.write_text(json.dumps(meta) + '\n', encoding='utf-8', newline='\n')
            os.replace(partial, meta_path)
        except (OSError, TypeError, ValueError):
            pass


def environment(*scripts):
    """The AMIWIND_* settings the given modules' code can read, with their values
    (build_cache.stage_environment: worker counts and bookkeeping never count), less
    the run's own scratch folder: a unit's result never depends on where scratch is."""
    from build_cache import SourceIndex, stage_environment
    from build_scratch import ENV as SCRATCH_ENV
    index = SourceIndex(ROOT)
    result = {}
    for script in scripts:
        result.update(stage_environment(Path(script).resolve(), index))
    result.pop(SCRATCH_ENV, None)
    return result


def input_digest(value):
    """SHA-256 of a JSON value (a unit's inputs: content hashes, its record, its options)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class UnitCache(PassCache):
    """Content-addressed results of a stage's independent work units (BUILD-IMAGE-NO-RESUME-33).

    A unit is one item of a stage's worker pool that writes a folder of files and returns a
    JSON row (a world region overlay, say). A stage that failed late, or runs again after a
    small change, takes every finished unit whose inputs are unchanged from here and runs only
    the rest. The key is the PassCache key (unit name, options, the modules' sources) plus the
    AMIWIND_* settings those modules read (environment()) and the unit's input digest. Files
    are stored once by SHA-256 and checked when read; a damaged or missing file is a miss.
    Same folder and on/off rule as the per-map passes (AMIWIND_PASS_CACHE)."""

    @classmethod
    def open(cls, name, options, *scripts):
        root = folder()
        if root is None:
            return None
        return cls(name, dict(options, environment=environment(*scripts)), source_digest(*scripts), root)

    def _blob(self, sha256):
        return Path(self.root) / self.name / 'files' / sha256[:2] / (sha256 + '.bin')

    def load_unit(self, inputs):
        """(row, {relative path: bytes}) recorded for these inputs, or None."""
        found = self.load(input_digest(inputs))
        if found is None or not isinstance(found[0], dict) or 'files' not in found[0]:
            return None
        files = {}
        try:
            for relative, sha256 in found[0]['files'].items():
                data = self._blob(sha256).read_bytes()
                if hashlib.sha256(data).hexdigest() != sha256:
                    return None
                files[relative] = data
        except (OSError, AttributeError, TypeError):
            return None
        return found[0]['row'], files

    def store_unit(self, inputs, row, directory):
        """Record a finished unit: its row and every file under DIRECTORY. Never fails a build."""
        try:
            directory = Path(directory)
            files = {}
            for path in sorted(p for p in directory.rglob('*') if p.is_file()):
                data = path.read_bytes()
                sha256 = hashlib.sha256(data).hexdigest()
                blob = self._blob(sha256)
                if not blob.is_file():
                    blob.parent.mkdir(parents=True, exist_ok=True)
                    partial = blob.with_name(f'{blob.name}.{os.getpid()}.tmp')
                    partial.write_bytes(data)
                    os.replace(partial, blob)
                files[path.relative_to(directory).as_posix()] = sha256
            self.store(input_digest(inputs), {'row': row, 'files': files, 'label': unit_label(inputs)})
        except (OSError, TypeError, ValueError):
            pass

    def restore_unit(self, inputs, directory):
        """Write a recorded unit's files into the empty or new DIRECTORY and return its row;
        None (nothing written) when the cache has no complete record for these inputs."""
        if forced(self.name, unit_label(inputs)):
            return None  # --rebuild-unit: built again (and stored again)
        found = self.load_unit(inputs)
        if found is None:
            return None
        row, files = found
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        if any(directory.iterdir()):
            raise ValueError('Unit folder is not empty: ' + str(directory))
        for relative, data in files.items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return row


def game_data_digest():
    """The game data identity of this build: SHA-256 over the (file, SHA-256) pairs of the build's input lock
    (AMIWIND_INPUTS_LOCK, every game input file), or None without a lock (then units read from game data are
    not cached: their inputs would be unknown)."""
    from known_inputs import LOCK_ENV, LOCK_SCHEMA
    path = os.environ.get(LOCK_ENV)
    if not path:
        return None
    try:
        record = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if record.get('schema') != LOCK_SCHEMA or not record.get('files'):
        return None
    pairs = sorted((key, (row or {}).get('sha256')) for key, row in record['files'].items())
    if any(value is None for _, value in pairs):
        return None
    return input_digest(pairs)


_TOOLS = {}


def tool_digest(*paths):
    """SHA-256 of external programs (map compilers) by content, once per process."""
    key = tuple(str(Path(p).resolve()) for p in paths)
    if key not in _TOOLS:
        from build_cache import sha256_file
        _TOOLS[key] = input_digest([sha256_file(p) for p in key])
    return _TOOLS[key]


def json_exact(value):
    """True when VALUE survives a JSON round trip unchanged (so a cached row equals the computed one)."""
    try:
        return json.loads(json.dumps(value)) == value
    except (TypeError, ValueError):
        return False


REBUILD_ENV = 'AMIWIND_REBUILD_UNITS'


def unit_label(inputs):
    """A unit's readable name: its record's map/name (a room, a region), for listings and --rebuild-unit."""
    entry = inputs.get('entry') if isinstance(inputs, dict) else None
    if isinstance(entry, dict):
        return str(entry.get('map') or entry.get('name') or '')
    return ''


def forced(unit, label):
    """True when --rebuild-unit (AMIWIND_REBUILD_UNITS="unit:label,...", "unit:*" for every one) names it."""
    wanted = [item.split(':', 1) for item in os.environ.get(REBUILD_ENV, '').split(',') if ':' in item]
    return any(name == unit and value in (label, '*') for name, value in wanted)


def list_units(root, unit=None):
    """[(unit, label, key, files, bytes)] of the stage units stored in a cache folder."""
    rows = []
    for meta in sorted(Path(root).glob('*/??/*.json')):
        if unit and meta.parent.parent.name != unit:
            continue
        try:
            record = json.loads(meta.read_text(encoding='utf-8'))
            files = record['row']['files']
        except (OSError, ValueError, KeyError, TypeError):
            continue
        size = sum((Path(root) / meta.parent.parent.name / 'files' / h[:2] / (h + '.bin')).stat().st_size
                   for h in files.values() if (Path(root) / meta.parent.parent.name / 'files' / h[:2] / (h + '.bin')).is_file())
        rows.append((meta.parent.parent.name, record['row'].get('label', ''), meta.stem, len(files), size))
    return rows


def main(argv=None):
    """python tools/pass_cache.py list FOLDER [UNIT]: the stage units stored in a cache folder."""
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in (2, 3) or args[0] != 'list':
        print('Usage: pass_cache.py list FOLDER [UNIT]', file=sys.stderr)
        return 2
    for name, label, key, files, size in list_units(args[1], args[2] if len(args) == 3 else None):
        print(f'{name:<22} {label:<24} {key[:16]}  {files:>4} files {size:>12,} B')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
