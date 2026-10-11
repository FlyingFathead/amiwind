#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Provenance of every cache and pool entry: who made it, when, from which version, and what it holds.

Every build cache is keyed by SHA-256 (stage records, image pass and unit caches, the CHIM unit cache, the world
terrain cache, the asset pool's reuse keys, stair-walk records). This module adds the facts the keys do not
carry, in ONE record format for all of them (schema aw-cache-provenance-1):

    schema, cache, key                       which cache, and the entry's key (SHA-256 of exactly its inputs)
    input_manifest                           {inputs: [{name, sha256, bytes}], parameters, sha256}: why the key
                                             is what it is, so a changed key can be explained (reuse audit)
    output_sha256, output_kind, output_bytes the entry's output (never null): bytes | row | files | pickle | tree
    created_at                               host clock, ISO 8601 with offset
    amiwind_version, commit, run, request,   the build that wrote it (the builder's run facts; owner = job + run,
    job                                      as in the Docker tracker)
    tools_sha256, chim_version, world_format the builder's tool hashes (one SHA-256 over the receipt's
                                             tool_sha256), the CHIM version and world format of that build
    retention                                {class: dev|rc|final|unknown, pins: []} for the one GC (pins are
                                             added later with `pin`, append-only)
    sources                                  how each field was found: "exact", "estimated (source: ...)",
                                             "inferred (source: ...)" or "N/A" (backfilled entries)

Where the record lives (never inside a payload; payload bytes are byte-identical with and without it):
  * JSON entries (pass/unit cache meta, stair-walk records, asset-pool keys, world terrain conversion.json):
    a "provenance" field in the entry's own JSON (written by the same atomic rename as before);
  * pickles and other binary entries: a sidecar <entry>.meta.json next to them, or <key>.meta.json next to an
    asset-pool key the writer did not build as a dict;
  * stage records (profile/manifests/STAGE.json): a "provenance" field;
  * entries written before 2026-10-11: <cache>/.provenance/backfill.jsonl (tools/cache_provenance.py backfill),
    one record per entry with estimated/inferred fields labelled; such an entry stays a valid reuse hit.
Reuse: <cache>/.provenance/reuse.jsonl, one appended line per reuse (O_APPEND: atomic for short lines).

Rules (tests/test_cache_provenance.py):
  * provenance never changes a key: the writers call this module only through statements build_cache strips
    before computing any key (build_cache.strip_provenance), and this module is output-neutral
    (build_cache.INSTRUMENTATION_MODULES); it reads only the environment, never a repository file;
  * a missing, estimated or N/A field is never a reason to rebuild; only a changed key or a failed output
    SHA-256 check is (verify_* raise ProvenanceMismatch inside the reader's own error handling = a miss);
  * a provenance problem never fails a build (every writer here swallows OSError).

Commands:
  cache_provenance.py show KEY|PATH [--cache DIR]   the provenance of one entry
  cache_provenance.py summary CACHE_DIR [--json]   entries, bytes, with/without provenance, oldest/newest,
                                                   versions, commits, reuse counts per cache
  cache_provenance.py pin CACHE_DIR KEY --by RUN --reason TEXT   pin an entry for the GC (append-only)
  cache_provenance.py backfill CACHE_ROOT... [--builds DIR] [--trials FILE] [--dry-run] [--jobs N]
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

SCHEMA = 'aw-cache-provenance-1'
BACKFILL_TOOL = 'cache_provenance backfill 1'
SIDECAR = '.meta.json'
FOLDER = '.provenance'
REUSE_LOG = 'reuse.jsonl'
PINS_LOG = 'pins.jsonl'
BACKFILL_LOG = 'backfill.jsonl'
NA = 'N/A'
EXACT = 'exact'
# The builder's run facts (tools/build.py sets them once per run; bookkeeping, build_cache.IGNORED_ENV).
RUN_ENV = {'run': 'AMIWIND_RUN_NAME', 'commit': 'AMIWIND_RUN_COMMIT', 'amiwind_version': 'AMIWIND_RUN_VERSION',
           'request': 'AMIWIND_AW_REQUEST', 'job': 'AMIWIND_RUN_JOB', 'tools_sha256': 'AMIWIND_RUN_TOOLS_SHA256',
           'chim_version': 'AMIWIND_RUN_CHIM_VERSION', 'world_format': 'AMIWIND_RUN_WORLD_FORMAT'}
FIELDS = ('created_at', 'amiwind_version', 'commit', 'run', 'request', 'job', 'tools_sha256', 'chim_version',
          'world_format')


class ProvenanceMismatch(ValueError):
    """A cache entry's output does not have the SHA-256 its provenance names: the reader treats it as a miss."""


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


def sha256_of(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def files_digest(files):
    """SHA-256 of a {relative path: sha256} map (an entry made of several files)."""
    return sha256_of(sorted(dict(files).items()))


def version_class(version):
    import re
    if not version:
        return 'unknown'
    if re.search(r'-dev[0-9]*$', version) or '-dev' in version:
        return 'dev'
    if '-rc' in version:
        return 'rc'
    if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        return 'final'
    return 'unknown'


def run_facts(environ=None):
    environ = os.environ if environ is None else environ
    facts = {name: environ.get(var) or None for name, var in RUN_ENV.items()}
    if not facts['job']:
        facts['job'] = environ.get('AW_REQUESTER') or None
    return facts


def input_manifest(inputs=(), parameters=None, unit=None):
    """{unit, inputs: [{name, sha256, bytes}], parameters, sha256} (sha256 binds the rest). UNIT: a stable name
    of the unit (map, frame, region, sector, stage, file) that stays the same when its inputs change, so the
    reuse audit can say which input of a recomputed unit changed."""
    rows = []
    for row in inputs or ():
        if isinstance(row, dict):
            rows.append({'name': str(row.get('name')), 'sha256': row.get('sha256'), 'bytes': row.get('bytes')})
        else:
            name, digest, *size = row
            rows.append({'name': str(name), 'sha256': digest, 'bytes': size[0] if size else None})
    manifest = {'unit': unit, 'inputs': rows, 'parameters': parameters if parameters is not None else {}}
    manifest['sha256'] = sha256_of(manifest)
    return manifest


def make(cache, key, output_sha256, output_kind, output_bytes=None, inputs=(), parameters=None, environ=None,
         created_at=None, extra=None, unit=None):
    """A new provenance record (every field exact; None where the build did not say: then 'N/A' in sources)."""
    if not output_sha256:
        raise ValueError('output_sha256 is required')
    facts = run_facts(environ)
    record = {'schema': SCHEMA, 'cache': cache, 'key': key, 'output_sha256': output_sha256,
              'output_kind': output_kind, 'output_bytes': output_bytes,
              'input_manifest': input_manifest(inputs, parameters, unit), 'created_at': created_at or now(), **facts,
              'retention': {'class': version_class(facts['amiwind_version']), 'pins': []}}
    record['sources'] = {name: (EXACT if record.get(name) else NA) for name in FIELDS}
    if extra:
        record.update(extra)
    return record


# --------------------------------------------------------------------------
# Writer hooks: each is called as a bare statement (build_cache.strip_provenance) and never raises.

def _quiet(function):
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ProvenanceMismatch:
            raise
        except Exception as exc:  # noqa: BLE001 - provenance never fails a build
            _warn_once(function.__name__, exc)
            return None
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


_WARNED = set()
_LOCK = threading.Lock()


def _warn_once(name, exc):
    with _LOCK:
        if name in _WARNED:
            return
        _WARNED.add(name)
    print(f'[warning] cache provenance not recorded ({name}: {exc}); the build continues', flush=True)


def _pass_output(meta, output):
    row = meta.get('row')
    if output is not None:
        return sha256_bytes(output), 'bytes', len(output)
    if isinstance(row, dict) and isinstance(row.get('files'), dict):
        return files_digest(row['files']), 'files', None
    return sha256_of(row), 'row', None


@_quiet
def attach_pass(meta, output, cache, key, options, sources, owner=None):
    """Pass/unit cache entry (tools/pass_cache.PassCache.store): META gets its "provenance" field in place.
    Output: the stored bytes; for a pass that left the map unchanged, the row (the input map is the output map,
    named by input_sha256); for a unit, the SHA-256 of its {file: sha256} map. The unit's name and its inputs
    one by one come from the pass's name_unit call (OWNER: the PassCache), else from the row; the pass's own
    sources and options are inputs too, so a changed key always names what changed."""
    digest, kind, size = _pass_output(meta, output)
    named, extra = _named(owner, meta.get('input_sha256'))
    inputs = ([('input', meta.get('input_sha256'))] + list(extra)
              + [('pass sources', sources), ('pass options', sha256_of(options))])
    meta['provenance'] = make(cache, key, digest, kind, size, inputs,
                              {'pass': meta.get('pass'), 'options_sha256': sha256_of(options),
                               'sources_sha256': sources, 'unchanged_input': output is None and kind == 'row'},
                              unit=named or unit_name(meta.get('row')))


def _input_row(name, value):
    """(name, sha256, bytes) of one named input: bytes are hashed, a 64-hex string is a SHA-256 already,
    anything else is hashed in its canonical JSON form."""
    if isinstance(value, (bytes, bytearray)):
        return (str(name), sha256_bytes(bytes(value)), len(value))
    if isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value):
        return (str(name), value, None)
    return (str(name), sha256_of(value), None)


@_quiet
def name_unit(cache, input_key, unit, inputs=()):
    """A pass names the unit it is about to store under INPUT_KEY (a map, frame, region, route, head) and the
    inputs its key was made from, one by one: [(name, bytes | sha256 | JSON value)]. Kept on the cache object
    until store() records it (attach_pass); never part of a key."""
    if cache is None or input_key is None:
        return
    # A pass hands its name and inputs as functions (lambda: ...): they run here, where a mistake can only
    # cost this record, never the pass (an argument evaluated in the pass could raise there).
    unit = unit() if callable(unit) else unit
    inputs = inputs() if callable(inputs) else inputs
    store = cache.__dict__.setdefault('_provenance_units', {})
    if len(store) > 100000:
        store.clear()
    store[input_key] = (None if unit is None else str(unit), [_input_row(n, v) for n, v in inputs or ()])


@_quiet
def head_name(part):
    """A character head's unit name: its part id (or the part itself, short)."""
    if isinstance(part, dict):
        return 'head %s' % (part.get('id') or part.get('name') or sha256_of(part)[:16])
    return 'head %s' % (part,)


def _named(owner, input_key):
    try:
        return owner.__dict__.get('_provenance_units', {}).pop(input_key, (None, []))
    except Exception:  # noqa: BLE001
        return None, []


@_quiet
def stair_frame_inputs(frame_row, models):
    """The inputs of a CHIM frame's stair walk one by one (chim.collision.frame_stair_key reads the same)."""
    path, frame, chunks = frame_row
    rows = [('frame', [path, sorted((k, v) for k, v in frame.items() if not isinstance(v, (bytes, bytearray)))])]
    used = set()
    for c in chunks:
        rows.append(('chunk %s,%s terrain' % (c.get('cx'), c.get('cy')), c['image']))
        rows.append(('chunk %s,%s placements' % (c.get('cx'), c.get('cy')), c['owned'] + c['reach']))
        used.update(r['model'] for r in c['owned'] + c['reach'])
    for m in sorted(used):
        rows.append(('model %d' % m, models[m]['image'] if 0 <= m < len(models) else b''))
    return rows


def unit_name(row):
    """A stable unit name from a cache row (its label, map, frame, region, sector or name), or None."""
    if not isinstance(row, dict):
        return None
    for field in ('label', 'map', 'frame', 'region', 'sector', 'cell', 'name', 'file'):
        value = row.get(field)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    inner = row.get('row')
    return unit_name(inner) if isinstance(inner, dict) else None


def verify_pass(meta, output):
    """Raise ProvenanceMismatch when a pass/unit entry's output differs from its provenance (old entries: no-op)."""
    record = meta.get('provenance') if isinstance(meta, dict) else None
    if not isinstance(record, dict) or not record.get('output_sha256'):
        return
    digest, _, _ = _pass_output(meta, output)
    if digest != record['output_sha256']:
        _mismatch(record.get('cache'), record.get('key'), record['output_sha256'], digest)
        raise ProvenanceMismatch(f"{record.get('cache')} {record.get('key')}: output SHA-256 {digest} != "
                                 f"{record['output_sha256']}")


def _name(cache):
    """A cache's name in records: the path from the cache folder on (asset-pool-v1/keys/NAMESPACE)."""
    parts = Path(str(cache)).parts
    for at, part in enumerate(parts):
        if part == 'keys' and at:
            return '/'.join(parts[at - 1:])
    return str(cache)


def _mismatch(cache, key, expected, found):
    print(f'[warning] cache entry {cache} {str(key)[:16]}: output SHA-256 differs from its provenance '
          f'({found[:16]} != {expected[:16]}); not used, the unit is built again', flush=True)


@_quiet
def remember_key(cache, source_sha256, settings):
    """FileCache.key: keep the inputs of the key being made, so the entry written under it can name them."""
    schema = getattr(sys.modules.get(type(cache).__module__), 'SCHEMA', None)
    key = hashlib.sha256(json.dumps({'schema': schema, 'source_sha256': source_sha256, 'settings': settings,
                                     'identity': cache.identity}, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()
    text = canonical(settings)
    parameters = {'settings': settings if len(text) <= 4096 else None, 'settings_sha256': sha256_of(settings),
                  'identity_sha256': sha256_of(cache.identity), 'schema': schema}
    store = cache.__dict__.setdefault('_provenance_inputs', {})
    if len(store) > 200000:
        store.clear()
    store[key] = ([('source', source_sha256)], parameters)


def recalled(cache, key):
    """(inputs, parameters) remember_key kept for KEY, or (None, None)."""
    try:
        return cache.__dict__.get('_provenance_inputs', {}).get(key) or (None, None)
    except Exception:  # noqa: BLE001
        return None, None


@_quiet
def attach_key(meta, cache, inputs=None, parameters=None):
    """Asset pool key (tools/file_cache.FileCache.store): META gets "provenance" in place."""
    meta['provenance'] = make(_name(cache), meta.get('key'), meta.get('sha256'), 'bytes', meta.get('bytes'),
                              inputs or (), parameters)


@_quiet
def sidecar_key(key_path, key, digest, size, cache, inputs=None, parameters=None):
    """Asset pool key written as one literal (FileCache.point): provenance in KEY.meta.json beside it."""
    write_sidecar(Path(key_path), make(_name(cache), key, digest, 'bytes', size, inputs or (), parameters))


@_quiet
def sidecar_file(path, key, cache, kind='pickle', inputs=None, parameters=None):
    """A binary entry (CHIM unit pickle): provenance in PATH-without-suffix.meta.json, output = its bytes."""
    path = Path(path)
    write_sidecar(path, make(cache, key, sha256_file(path), kind, path.stat().st_size, inputs or (), parameters))


_UNITS = {}


@_quiet
def remember_unit(kind, blob):
    """chim.units.fingerprint: keep the unit's input manifest (tool fingerprint + SHA-256 of each input part)."""
    fp = hashlib.sha256(blob.encode()).hexdigest()
    tools, parts = json.loads(blob)
    if len(_UNITS) > 200000:
        _UNITS.clear()
    first = parts[0] if parts else None
    name = first if isinstance(first, str) else unit_name(first) if isinstance(first, dict) else None
    _UNITS[fp] = ([('tools', tools)] + [(f'part{i}', sha256_of(part)) for i, part in enumerate(parts)],
                  {'kind': kind, 'unit': name})


@_quiet
def sidecar_unit(path, kind, fp):
    """A CHIM unit pickle: sidecar FP.meta.json (output = the pickle's bytes; payload unchanged)."""
    inputs, parameters = _UNITS.get(fp) or ([], {'kind': kind})
    path = Path(path)
    write_sidecar(path, make('chim-units/' + kind, fp, sha256_file(path), 'pickle', path.stat().st_size,
                             inputs, parameters, unit=(parameters or {}).get('unit')))


def verify_file(path):
    """Raise ProvenanceMismatch when PATH's bytes differ from its sidecar (no sidecar: no-op)."""
    record = read_sidecar(Path(path))
    if not record or not record.get('output_sha256'):
        return
    digest = sha256_file(path)
    if digest != record['output_sha256']:
        _mismatch(record.get('cache'), record.get('key'), record['output_sha256'], digest)
        raise ProvenanceMismatch(f'{path}: SHA-256 {digest} != {record["output_sha256"]}')


@_quiet
def attach_tree(record, cache, key, files, inputs=None, parameters=None):
    """An entry made of several files (world terrain conversion.json): RECORD gets "provenance" in place."""
    record['provenance'] = make(cache, key, files_digest(files), 'files', None, inputs or (), parameters)


@_quiet
def attach_terrain(record, folder, unit, result):
    """World terrain cache entry (tools/prepare_world_regions.unit_cache_store): RECORD (conversion.json) gets
    "provenance"; output = the SHA-256 of its {file: sha256} map (conversion.json itself not included)."""
    folder = Path(folder)
    files = {p.name: sha256_file(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name != 'conversion.json'}
    record['provenance'] = make('world-terrain', unit, files_digest(files), 'files',
                                sum((folder / name).stat().st_size for name in files),
                                [('map text + texture WAD (input_sha256)', result.get('input_sha256'))]
                                + [(name, digest) for name, digest in sorted(files.items())],
                                {'name': result.get('name'), 'scene_sha256': (result.get('converted') or {}).get('sha256')},
                                unit=result.get('name'))


@_quiet
def attach_stage(manifest, run):
    """A stage record (build_cache.Recorder): output = its unit tree's stage hash, inputs = its input files."""
    tree = manifest.get('tree') or {}
    inputs = sorted((manifest.get('inputs') or {}).items())
    manifest['provenance'] = make('stage-cache/' + str(manifest.get('stage')), manifest.get('fingerprint'),
                                  tree.get('stage_hash') or sha256_of(manifest.get('files') or {}), 'tree',
                                  (manifest.get('counts') or {}).get('bytes'), inputs,
                                  {'fingerprint': manifest.get('fingerprint'), 'run_folder': Path(str(run)).name},
                                  unit=manifest.get('stage'))


@_quiet
def object_stored(pool, digest, source):
    """A new object in the storage pool (tools/storage_pool._store): one line in POOL/.provenance/objects.jsonl
    (objects are named by their SHA-256; this names who stored them, when, and from which file)."""
    facts = run_facts()
    row = {'sha256': digest, 'bytes': os.stat(source).st_size, 'source': Path(str(source)).name, 'at': now(),
           **{name: facts[name] for name in ('run', 'commit', 'amiwind_version', 'job')}}
    _append(Path(pool) / FOLDER / 'objects.jsonl', canonical(row) + '\n')


def _append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        os.write(handle, line.encode('utf-8'))
    finally:
        os.close(handle)


@_quiet
def reused(cache_root, cache, key, hit=True):
    """One line in CACHE_ROOT/.provenance/reuse.jsonl per reuse (append-only; reuse_count = lines per key)."""
    if not hit or cache_root is None or key is None:
        return
    facts = run_facts()
    line = canonical({'key': key, 'cache': cache, 'at': now(), 'run': facts['run'], 'job': facts['job']}) + '\n'
    folder = Path(cache_root) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    handle = os.open(folder / REUSE_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        os.write(handle, line.encode('utf-8'))
    finally:
        os.close(handle)


# --------------------------------------------------------------------------
# Sidecars and lookups

def sidecar_path(path):
    path = Path(path)
    if path.name.endswith(SIDECAR):
        return path
    return path.with_name(path.name.split('.')[0] + SIDECAR) if '.' in path.name else path.with_name(path.name + SIDECAR)


def write_sidecar(path, record):
    target = sidecar_path(path)
    temporary = target.with_name(f'{target.name}.{os.getpid()}.{threading.get_ident()}.tmp')
    try:
        temporary.write_bytes((json.dumps(record, sort_keys=True) + '\n').encode('utf-8'))
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


def read_sidecar(path):
    try:
        record = json.loads(sidecar_path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) and record.get('schema') == SCHEMA else None


def inline(path):
    """The "provenance" field of a JSON entry, or None."""
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    record = data.get('provenance') if isinstance(data, dict) else None
    return record if isinstance(record, dict) and record.get('schema') == SCHEMA else None


def read_jsonl(path):
    rows = []
    try:
        with open(path, encoding='utf-8') as stream:
            for line in stream:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def backfilled(cache_root):
    """{entry relative path: record} of a cache's backfill index (latest record per entry wins)."""
    found = {}
    for row in read_jsonl(Path(cache_root) / FOLDER / BACKFILL_LOG):
        if isinstance(row, dict) and row.get('entry'):
            found[row['entry']] = row
    return found


def lookup(path, cache_root=None):
    """(record, where) of one entry: inline field, sidecar, or the backfill index; (None, 'none')."""
    path = Path(path)
    if path.suffix == '.json' and not path.name.endswith(SIDECAR):
        record = inline(path)
        if record:
            return record, 'inline'
    for candidate in (path, path / 'conversion.json'):
        if candidate.is_file() and candidate.suffix == '.json' and not candidate.name.endswith(SIDECAR):
            record = inline(candidate)
            if record:
                return record, 'inline'
    record = read_sidecar(path)
    if record:
        return record, 'sidecar'
    root = Path(cache_root) if cache_root else _cache_root_of(path)
    if root is not None:
        rows = backfilled(root)
        relative = _relative(path, root)
        if relative in rows:
            return rows[relative], 'backfill'
    return None, 'none'


def _cache_root_of(path):
    for parent in [path, *path.parents]:
        if (parent / FOLDER).is_dir():
            return parent
    return None


def _relative(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def reuse_counts(cache_root):
    counts, last = {}, {}
    for row in read_jsonl(Path(cache_root) / FOLDER / REUSE_LOG):
        key = row.get('key')
        counts[key] = counts.get(key, 0) + 1
        last[key] = max(last.get(key, ''), row.get('at') or '')
    return counts, last


def pins(cache_root):
    """{key: [pin rows]} of a cache (tools/build_gc.py retention input)."""
    found = {}
    for row in read_jsonl(Path(cache_root) / FOLDER / PINS_LOG):
        found.setdefault(row.get('key'), []).append(row)
    return found


def pin(cache_root, key, by, reason):
    row = canonical({'key': key, 'by': by, 'reason': reason, 'at': now()}) + '\n'
    folder = Path(cache_root) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / PINS_LOG, 'a', encoding='utf-8', newline='\n') as stream:
        stream.write(row)


# --------------------------------------------------------------------------
# Entries of a cache folder (summary and backfill)

KINDS = ('asset-pool', 'pass-cache', 'chim-units', 'world-terrain', 'unknown')


def cache_kind(root):
    root = Path(root)
    if (root / 'objects').is_dir() or (root / 'keys').is_dir():
        return 'asset-pool'
    if root.name.startswith('world-terrain'):
        return 'world-terrain'
    if root.name.startswith('npc-gallery'):
        # The gallery's key hashes tools/gallery_cache.py whole (cache_implementation): its writer is not hooked
        # (any edit would rebuild every model); its entries get provenance from the backfill only.
        return 'world-terrain'
    if root.name == 'chim-units' or any(root.glob('*/??/*.pickle')):
        return 'chim-units'
    if root.name == 'image-passes' or any(root.glob('*/??/*.json')):
        return 'pass-cache'
    return 'unknown'


def entries(root, kind=None):
    """Yield (relative entry path, payload paths, key, sub-cache) of every entry of a cache folder."""
    root = Path(root)
    kind = kind or cache_kind(root)
    if kind == 'asset-pool':
        for path in sorted((root / 'keys').rglob('*.json')):
            if path.name.endswith(SIDECAR) or '.tmp' in path.name:
                continue
            yield path.relative_to(root).as_posix(), [path], path.stem, path.parent.parent.relative_to(root).as_posix()
        for path in sorted((root / 'objects').glob('??/*')):
            if path.is_file() and len(path.name) == 64:
                yield path.relative_to(root).as_posix(), [path], path.name, 'objects'
    elif kind == 'pass-cache':
        for path in sorted(root.glob('*/??/*.json')):
            if path.name.endswith(SIDECAR) or '.tmp' in path.name:
                continue
            blob = path.with_suffix('.bin')
            yield (path.relative_to(root).as_posix(), [path] + ([blob] if blob.is_file() else []), path.stem,
                   path.parent.parent.name)
        for path in sorted(root.glob('*/files/??/*.bin')):
            yield path.relative_to(root).as_posix(), [path], path.stem, path.parent.parent.parent.name + '/files'
        for path in sorted(root.glob('stair-walk-checked/**/*')):
            if path.is_file() and not path.name.endswith(SIDECAR):
                yield path.relative_to(root).as_posix(), [path], path.stem, 'stair-walk-checked'
    elif kind == 'chim-units':
        for path in sorted(root.glob('*/??/*.pickle')):
            yield path.relative_to(root).as_posix(), [path], path.stem, path.parent.parent.name
    elif kind == 'world-terrain':
        for folder in sorted(root.glob('??/*')):
            if folder.is_dir() and '.tmp' not in folder.name:
                files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.endswith(SIDECAR))
                yield folder.relative_to(root).as_posix(), files, folder.name, root.name


def _size(paths):
    total = 0
    for path in paths:
        try:
            total += os.lstat(path).st_size
        except OSError:
            pass
    return total


def summary(root, kind=None):
    """Per cache: entries, bytes, with/without provenance (and where), oldest/newest, versions, commits, reuse."""
    root = Path(root)
    kind = kind or cache_kind(root)
    backfill = backfilled(root)
    counts, last = reuse_counts(root)
    out = {'cache': str(root), 'kind': kind, 'entries': 0, 'bytes': 0, 'with_provenance': 0,
           'without_provenance': 0, 'where': {}, 'sub_caches': {}, 'oldest': None, 'newest': None,
           'versions': {}, 'commits': {}, 'confidence': {}, 'reused_entries': 0, 'reuse_lines': sum(counts.values())}
    for relative, paths, key, sub in entries(root, kind):
        out['entries'] += 1
        size = _size(paths)
        out['bytes'] += size
        row = out['sub_caches'].setdefault(sub, {'entries': 0, 'bytes': 0, 'with_provenance': 0})
        row['entries'] += 1
        row['bytes'] += size
        record, where = _entry_record(root, relative, paths, backfill)
        out['where'][where] = out['where'].get(where, 0) + 1
        if key in counts:
            out['reused_entries'] += 1
        if record is None:
            out['without_provenance'] += 1
            continue
        out['with_provenance'] += 1
        row['with_provenance'] += 1
        created = record.get('created_at')
        if created and created != NA:
            out['oldest'] = min(out['oldest'] or created, created)
            out['newest'] = max(out['newest'] or created, created)
        version = record.get('amiwind_version') or NA
        out['versions'][version] = out['versions'].get(version, 0) + 1
        commit = record.get('commit') or NA
        out['commits'][commit] = out['commits'].get(commit, 0) + 1
        for field, label in (record.get('sources') or {}).items():
            level = str(label).split(' ')[0]
            out['confidence'].setdefault(field, {})
            out['confidence'][field][level] = out['confidence'][field].get(level, 0) + 1
    return out


def _entry_record(root, relative, paths, backfill):
    first = paths[0] if paths else None
    if first is not None:
        if first.suffix == '.json':
            record = inline(first)
            if record:
                return record, 'inline'
        conversion = Path(root) / relative / 'conversion.json'
        if conversion.is_file():
            record = inline(conversion)
            if record:
                return record, 'inline'
        record = read_sidecar(first)
        if record:
            return record, 'sidecar'
    if relative in backfill:
        return backfill[relative], 'backfill'
    return None, 'none'


# --------------------------------------------------------------------------
# Backfill: provenance for entries written before 2026-10-11 (additive: payloads never touched)

def run_name_facts(name):
    """{version, commit, date} from a run name YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>_<git> (or {})."""
    import re
    match = re.match(r'^(\d{4})_(\d{2})_(\d{2})_v([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9]+)?)_.*_([0-9a-f]{7,40})$',
                     str(name))
    if not match:
        return {}
    year, month, day, version, commit = match.groups()
    return {'version': version, 'commit': commit, 'date': f'{year}-{month}-{day}'}


def load_runs(builds=None, trials=None):
    """[{run, started, version, commit, source}] of the build runs (live folders, then retired TRIALS lines)."""
    runs = {}
    if trials:
        for row in read_jsonl(trials):
            name = Path(str(row.get("run") or row.get("name") or "")).name
            if not name:
                continue
            facts = run_name_facts(name)
            runs[name] = {'run': name, 'started': row.get('started') or row.get('started_at'),
                          'version': row.get('version') or facts.get('version'),
                          'commit': row.get('commit') or facts.get('commit'), 'source': 'TRIALS.jsonl'}
    for folder in sorted(Path(builds).iterdir()) if builds and Path(builds).is_dir() else []:
        state = folder / 'build-state.json'
        if not state.is_file():
            continue
        try:
            data = json.loads(state.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        facts = run_name_facts(folder.name)
        runs[folder.name] = {'run': folder.name,
                             'started': data.get('build_started_at') or data.get('started_at') or data.get('started'),
                             'version': data.get('runtime_version') or facts.get('version'),
                             'commit': data.get('source_commit') or data.get('builder_commit') or facts.get('commit'),
                             'source': 'build-state.json', 'folder': str(folder)}
    return runs


def _iso(seconds):
    return datetime.datetime.fromtimestamp(seconds).astimezone().isoformat(timespec='seconds')


def _link_index(builds, roots_devices):
    """{(dev, inode): earliest run name} over every regular file of the run folders that shares an inode
    with a cache file (hard links: the asset pool's objects and pooled stage outputs)."""
    index = {}
    if not builds or not Path(builds).is_dir():
        return index
    for folder in sorted(Path(builds).iterdir()):
        if not folder.is_dir():
            continue
        for here, _, names in os.walk(folder):
            for name in names:
                try:
                    info = os.lstat(os.path.join(here, name))
                except OSError:
                    continue
                if info.st_nlink < 2 or info.st_dev not in roots_devices:
                    continue
                inode = (info.st_dev, info.st_ino)
                previous = index.get(inode)
                if previous is None or folder.name < previous:
                    index[inode] = folder.name  # names start with the date: the earliest run sorts first
    return index


def _infer_run(created, runs):
    """The run whose start is the latest one at or before CREATED (seconds), or None."""
    best = None
    for row in runs.values():
        started = row.get('started')
        try:
            moment = datetime.datetime.fromisoformat(str(started).replace('Z', '+00:00')).timestamp()
        except (TypeError, ValueError):
            continue
        if moment <= created and (best is None or moment > best[0]):
            best = (moment, row)
    return best[1] if best else None


def backfill_record(root, relative, paths, key, sub, kind, runs, links, hashes=None):
    """A backfill record for one entry (output_sha256 exact from the stored bytes; the rest labelled).
    HASHES: {file name: sha256} of PATHS when the caller has just computed them."""
    hashes = dict(hashes) if hashes else {path.name: sha256_file(path) for path in paths}
    if kind == 'world-terrain':
        output, out_kind = files_digest(hashes), 'files'
    elif kind == 'pass-cache' and paths[0].suffix == '.json':
        try:
            meta = json.loads(paths[0].read_text(encoding='utf-8'))
            blob = paths[1].read_bytes() if len(paths) > 1 else None
            output, out_kind, _ = _pass_output(meta, blob)
        except (OSError, ValueError, IndexError):
            output, out_kind = hashes[paths[0].name], 'bytes'
    elif kind == 'asset-pool' and sub != 'objects':
        try:
            meta = json.loads(paths[0].read_text(encoding='utf-8'))
            output, out_kind = meta.get('sha256') or hashes[paths[0].name], 'bytes'
        except (OSError, ValueError):
            output, out_kind = hashes[paths[0].name], 'bytes'
    else:
        output, out_kind = hashes[paths[0].name], ('pickle' if kind == 'chim-units' else 'bytes')
    info = os.lstat(paths[0])
    sources = {}
    name = Path(root).name if sub == Path(root).name else f'{Path(root).name}/{sub}'
    record = {'schema': SCHEMA, 'cache': name, 'key': key, 'entry': relative,
              'output_sha256': output, 'output_kind': out_kind, 'output_bytes': _size(paths),
              'payload_sha256': hashes, 'input_manifest': None,
              'backfilled_at': now(), 'backfill_tool': BACKFILL_TOOL}
    owner = None
    for path in paths:
        try:
            owner = links.get((os.lstat(path).st_dev, os.lstat(path).st_ino))
        except OSError:
            owner = None
        if owner:
            break
    if owner and owner in runs:
        row = runs[owner]
        record['run'] = owner
        sources['run'] = 'inferred (source: earliest run folder hard-linking it)'
        started = row.get('started')
        record['created_at'] = started or _iso(min(info.st_mtime, info.st_ctime))
        sources['created_at'] = ('estimated (source: build-state.json start of that run)' if started
                                 else 'estimated (source: file mtime/ctime)')
    elif owner:
        record['run'] = owner
        sources['run'] = 'inferred (source: earliest run folder hard-linking it)'
        record['created_at'] = _iso(min(info.st_mtime, info.st_ctime))
        sources['created_at'] = 'estimated (source: file mtime/ctime)'
    else:
        record['created_at'] = _iso(min(info.st_mtime, info.st_ctime))
        sources['created_at'] = 'estimated (source: file mtime/ctime)'
        row = _infer_run(min(info.st_mtime, info.st_ctime), runs)
        if row:
            record['run'] = row['run']
            sources['run'] = f"inferred (source: latest run started before the file time, {row.get('source')})"
            owner = row['run']
    row = runs.get(owner) if owner else None
    facts = run_name_facts(owner) if owner else {}
    record['amiwind_version'] = (row or {}).get('version') or facts.get('version')
    record['commit'] = (row or {}).get('commit') or facts.get('commit')
    for field in ('amiwind_version', 'commit'):
        sources[field] = (f"inferred (source: run {owner}, {(row or {}).get('source') or 'run name'})"
                          if record[field] else NA)
    for field in ('request', 'job', 'tools_sha256', 'chim_version', 'world_format'):
        record[field] = None
        sources[field] = NA
    if 'run' not in record:
        record['run'] = None
        sources['run'] = NA
    sources['output_sha256'] = EXACT + ' (source: stored bytes)'
    record['sources'] = sources
    record['retention'] = {'class': version_class(record['amiwind_version']), 'pins': []}
    record['provenance_note'] = 'provenance: backfilled (pre-2026-10-11)'
    return record


def backfill(roots, builds=None, trials=None, dry_run=True, log=print, jobs=None, batch=2000):
    """Write CACHE/.provenance/backfill.jsonl for each cache root (entries without provenance only).
    Payloads are read, hashed before and after, never written. Streaming: entries are read BATCH at a time and
    each record is written out as soon as it is made (a dry run keeps only counts), so memory stays flat.
    Returns {cache: counts}."""
    from concurrent.futures import ThreadPoolExecutor
    import itertools
    runs = load_runs(builds, trials)
    devices = set()
    for root in roots:
        try:
            devices.add(os.stat(root).st_dev)
        except OSError:
            pass
    links = _link_index(builds, devices) if builds else {}
    log(f'Backfill: {len(runs)} runs known, {len(links)} hard-linked inodes indexed'
        + (' (dry run)' if dry_run else ''))
    report = {}
    for root in roots:
        root = Path(root)
        kind = cache_kind(root)
        existing = set(backfilled(root))
        counts = {'kind': kind, 'entries': 0, 'already': 0, 'backfilled': 0, 'payload_changed': 0, 'errors': 0,
                  'bytes': 0, 'confidence': {}}

        def one(item):
            relative, paths, key, sub = item
            try:
                before = {p.name: sha256_file(p) for p in paths}
                record = backfill_record(root, relative, paths, key, sub, kind, runs, links, before)
                after = {p.name: sha256_file(p) for p in paths}
                return record, before == after == record['payload_sha256']
            except OSError as exc:
                return {'error': str(exc), 'entry': relative}, True

        folder = root / FOLDER
        target = folder / BACKFILL_LOG
        temporary = folder / f'{BACKFILL_LOG}.{os.getpid()}.tmp'
        stream = None
        if not dry_run:
            folder.mkdir(parents=True, exist_ok=True)
            stream = open(temporary, 'wb')
            if target.is_file():
                with open(target, 'rb') as previous:
                    shutil_copy = __import__('shutil').copyfileobj
                    shutil_copy(previous, stream)
        log(f'{root}: {kind}, reading and hashing its entries ({batch:,} at a time)')
        try:
            pending = (item for item in entries(root, kind) if not _skip(root, item, existing, counts))
            with ThreadPoolExecutor(max_workers=jobs or min(8, os.cpu_count() or 1)) as executor:
                while True:
                    chunk = list(itertools.islice(pending, batch))
                    if not chunk:
                        break
                    for record, unchanged in executor.map(one, chunk):
                        if 'error' in record:
                            counts['errors'] += 1
                            continue
                        if not unchanged:
                            counts['payload_changed'] += 1
                            continue
                        counts['backfilled'] += 1
                        counts['bytes'] += record.get('output_bytes') or 0
                        for field, label in record['sources'].items():
                            level = str(label).split(' ')[0]
                            counts['confidence'].setdefault(field, {})
                            counts['confidence'][field][level] = counts['confidence'][field].get(level, 0) + 1
                        if stream is not None:
                            stream.write((json.dumps(record, sort_keys=True) + '\n').encode('utf-8'))
                    log(f"  [{counts['entries']:,} entries read, {counts['backfilled']:,} "
                        f"{'would be ' if dry_run else ''}backfilled] {root.name}")
            if stream is not None:
                stream.close()
                stream = None
                os.replace(temporary, target)
        finally:
            if stream is not None:
                stream.close()
            if not dry_run:
                try:
                    temporary.unlink()
                except OSError:
                    pass
        report[str(root)] = counts
        log(f"{root}: {counts['entries']} entries, {counts['already']} with provenance, "
            f"{counts['backfilled']} {'would be ' if dry_run else ''}backfilled, "
            f"{counts['payload_changed']} payload changed during the read, {counts['errors']} errors")
    return report


def _skip(root, item, existing, counts):
    """Count an entry; True when it already has provenance (inline, sidecar or an earlier backfill)."""
    relative, paths, _, _ = item
    counts['entries'] += 1
    if relative in existing:
        counts['already'] += 1
        return True
    record, _ = _entry_record(root, relative, paths, {})
    if record is not None:
        counts['already'] += 1
        return True
    return False


# --------------------------------------------------------------------------

def show(target, cache=None):
    path = Path(target)
    if path.exists():
        record, where = lookup(path, cache)
        root = Path(cache) if cache else _cache_root_of(path)
        key = (record or {}).get('key') or path.stem
    else:
        if not cache:
            raise SystemExit('show KEY needs --cache DIR')
        record, where, key, root = None, 'none', str(target), Path(cache)
        for relative, paths, entry_key, _ in entries(root):
            if entry_key == key or entry_key.startswith(key):
                record, where = _entry_record(root, relative, paths, backfilled(root))
                key = entry_key
                break
    counts, last = reuse_counts(root) if root else ({}, {})
    return {'key': key, 'where': where, 'provenance': record, 'reuse_count': counts.get(key, 0),
            'last_reused_at': last.get(key), 'pins': pins(root).get(key, []) if root else []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('show', help='provenance of one entry (path, or key with --cache)')
    p.add_argument('target')
    p.add_argument('--cache', type=Path)
    p = sub.add_parser('summary', help='per-cache counts')
    p.add_argument('caches', nargs='+', type=Path)
    p.add_argument('--json', action='store_true')
    p = sub.add_parser('pin', help='pin an entry for the GC (append-only)')
    p.add_argument('cache', type=Path)
    p.add_argument('key')
    p.add_argument('--by', required=True)
    p.add_argument('--reason', required=True)
    p = sub.add_parser('backfill', help='provenance for entries written before it existed (additive)')
    p.add_argument('caches', nargs='+', type=Path)
    p.add_argument('--builds', type=Path, help='the run folders (build/), for hard links and run starts')
    p.add_argument('--trials', type=Path, help='TRIALS.jsonl of retired runs')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--jobs', type=int)
    p.add_argument('--report', type=Path, help='write the counts as JSON here')
    args = parser.parse_args(argv)
    if args.action == 'show':
        result = show(args.target, args.cache)
        record = result['provenance'] or {}
        print(f"key {result['key']} ({result['where']})")
        if not record:
            print('provenance: unknown (pre-2026-10-11, not backfilled)')
        for field in ('cache', 'created_at', 'amiwind_version', 'commit', 'run', 'request', 'job', 'output_sha256',
                      'output_kind', 'output_bytes', 'chim_version', 'world_format', 'tools_sha256'):
            if field in record:
                label = (record.get('sources') or {}).get(field)
                print(f'  {field:16} {record.get(field)}' + (f'   [{label}]' if label and label != EXACT else ''))
        print(f"  {'reuse_count':16} {result['reuse_count']}   last {result['last_reused_at']}")
        for row in result['pins']:
            print(f"  pinned by {row.get('by')}: {row.get('reason')} ({row.get('at')})")
        return 0
    if args.action == 'summary':
        rows = [summary(cache) for cache in args.caches]
        if args.json:
            print(json.dumps(rows, indent=1, sort_keys=True))
            return 0
        for row in rows:
            print(f"{row['cache']} ({row['kind']}): {row['entries']:,} entries, {row['bytes']:,} B; "
                  f"with provenance {row['with_provenance']:,}, without {row['without_provenance']:,} "
                  f"(pre-2026-10-11: provenance unknown); where {row['where']}")
            print(f"  oldest {row['oldest']}  newest {row['newest']}  versions {row['versions']}")
            print(f"  reused entries {row['reused_entries']:,} ({row['reuse_lines']:,} reuse lines)")
            for name, sub_row in sorted(row['sub_caches'].items()):
                print(f"    {name:40} {sub_row['entries']:>8,} entries {sub_row['bytes']:>16,} B "
                      f"{sub_row['with_provenance']:>8,} with provenance")
        return 0
    if args.action == 'pin':
        pin(args.cache, args.key, args.by, args.reason)
        return 0
    report = backfill(args.caches, args.builds, args.trials, args.dry_run, jobs=args.jobs)
    if args.report:
        args.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return 1 if any(row['payload_changed'] or row['errors'] for row in report.values()) else 0


if __name__ == '__main__':
    sys.exit(main())
