"""The stage source analysis of the build's pre-flight on every core, kept per source tree
(BUILD-PREFLIGHT-SERIAL-REPEATED-66, BUILD-REUSE-CHECK-ONE-CORE-59; tools/build_cache.py fingerprint_steps).

Every stage key holds its stage script's source selection (build_cache.SourceIndex.selection: the code the stage can
reach, its data files, the engine C files by their use) and the same in its older forms (previous_selections), the
AMIWIND_* names that code reads and its reached units. Worked out one stage after another on one core, that was most
of the reuse check (the entry check's reuse preflight and the stage plan each worked them out again), and every
build start paid it three times: the check before the request, aw submit's check and the build itself (2026-11-14,
21 to 25 minutes on one core before the first stage).

prepare_index (tools/build.py turns it on: build_cache.PREFLIGHT_WORKERS, build_cache.ANALYSIS_STORE):
  1. takes the analysis of the same source tree when this process or an earlier check or build made it (the key:
     the SHA-256 of every file the index covers, the checkout folder, the index's form, the analysing code and the
     Python version; any difference, and it is worked out again). An option or environment switch of the build is
     no part of it: those count in each stage key itself (stage_components), which is always computed;
  2. works out what is missing on a process pool sized by --jobs (capped by the cores the build may use): first
     every Python module of the checkout once (each in one worker, merged here, so no worker parses a shared module
     again: what made the earlier opt-in method below slower than the serial path), then each stage script's
     selections, older forms, reach and names in forked workers that inherit those modules;
  3. keeps the analysis in WORKSPACE/cache/preflight-analysis-v1 for the next check or build of the tree
     (save_analyses, after the stage plan), and says in the log which it did.
Every result is the same function of the same files as the serial path (tests/test_build_cache_prefetch.py compares
the pool, the serial path and the stored analysis). AMIWIND_PREFLIGHT_JOBS=1 works it out in this process alone.

The earlier method, prefetch_selections (opt-in, AMIWIND_FINGERPRINT_JOBS=N), is kept: measured 2026-11-04 on the
v0.0.59 release run at --cpus 4 (busy host), the serial path 143.0 s, 4 workers 153.6 s, 16 workers 208.5 s: each
worker parsed the shared modules again, and that parsing was most of the work.
"""
import gc
import hashlib
import os
from pathlib import Path
import pickle
import sys
import time
import zlib

PREFETCH_ENV = 'AMIWIND_FINGERPRINT_JOBS'   # the earlier method's worker processes (unset or 1 = serial)
PREFLIGHT_ENV = 'AMIWIND_PREFLIGHT_JOBS'    # the pre-flight's worker processes (unset: --jobs capped by the cores)
STORE_FOLDER = 'preflight-analysis-v1'     # WORKSPACE/cache/<this>: one analysed source tree per file
STORE_SCHEMA = 'amiwind-preflight-analysis-1'
STORE_KEEP = 24                            # analysed trees kept (the most recently used; the store prunes itself)
MAGIC = b'AWPA1\n'
# The memos of a SourceIndex the analysis fills (pure functions of the checkout and the index's form)
MEMO_FIELDS = ('_closures', '_reached', '_keyed', '_symbols', '_includes', '_json_values', '_modules', '_exact',
               '_selections', '_own_names')
# The code that analyses (its SHA-256 is part of the key; build_cache's folder)
ANALYZER_FILES = ('build_cache.py', 'engine_facts.py', 'chim_compat.py', 'engine_loader_policy.py',
                  'fingerprint_prefetch.py')
PARSE_CHUNK = 6
_INDEX = None
_LIVE = {}       # key -> {'index': SourceIndex, 'origin': ..., 'loaded': entry count}: the analyses of this process


def _one(script):
    index = _INDEX
    selected = index.selection(script)
    previous = index.previous_selections(script) if not selected[1] and index.top_format != 1 else None
    return str(script), selected, previous


def _share(scripts):
    # one worker keeps its parsed modules and closures across its share of the scripts
    return [_one(script) for script in scripts]


def usable_cores():
    """Cores this process may use: the CPU affinity, capped by a cgroup v2 CPU quota (docker --cpus)."""
    cores = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    try:
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()[:2]
        if quota != 'max':
            cores = min(cores, max(1, int(int(quota) / int(period))))
    except (OSError, ValueError):
        pass
    return cores


def preflight_workers(jobs=None):
    """Worker processes for the build's pre-flight (the cache walk, the stage source analysis): AMIWIND_PREFLIGHT_JOBS
    when set (1 = this process alone), else JOBS (--jobs) capped by the cores this process may use."""
    value = os.environ.get(PREFLIGHT_ENV, '').strip()
    if value:
        try:
            return max(1, int(value))
        except ValueError:
            pass
    cores = usable_cores()
    try:
        wanted = int(jobs) if jobs else cores
    except (TypeError, ValueError):
        wanted = cores
    return max(1, min(wanted, cores))


def prefetch_selections(index, scripts, workers=None, log=None):
    """Work out SCRIPTS' selections in WORKERS forked processes (default: AMIWIND_FINGERPRINT_JOBS, else serial) and
    keep them in INDEX (index._prefetched, read by SourceIndex.selection / previous_selections, forgotten by
    refresh). Returns the number of scripts done (0 = nothing done here, the serial path computes them).
    The earlier method (module doc); prepare_index is the build's."""
    global _INDEX
    scripts = sorted({str(Path(s).resolve()) for s in scripts})
    if workers is None:
        try:
            workers = int(os.environ.get(PREFETCH_ENV) or 1)
        except ValueError:
            workers = 1
    workers = min(workers, len(scripts))
    if workers < 2:
        return 0
    import multiprocessing
    try:
        context = multiprocessing.get_context('fork')
    except ValueError:   # no fork (Windows): the serial path
        return 0
    began = time.monotonic()
    _INDEX = index
    memo = index.__dict__.setdefault('_prefetched', {})
    try:
        shares = [scripts[i::workers] for i in range(workers)]   # interleaved: similar mixes per worker
        with context.Pool(workers) as pool:
            for done in pool.imap_unordered(_share, shares):
                for script, selected, previous in done:
                    memo[('selection', script, index.top_format)] = selected
                    if previous is not None:
                        memo[('previous', script, index.top_format)] = previous
    finally:
        _INDEX = None
    (log or print)('Stage fingerprints: source selections of %d stage scripts in %d worker processes, %.1f s'
                   % (len(scripts), workers, time.monotonic() - began))
    return len(scripts)


# --------------------------------------------------------------------------
# The analysis of one source tree: its key, its memos

def use_memo(index):
    """Turn INDEX's selection memo on (and its companion's, when it has one): the pre-flight's analysis fills it."""
    if index._selections is None:
        index._selections = {}
    companion = index._companion
    if companion is not None and companion is not index and companion._selections is None:
        companion._selections = {}


def pair(index):
    """INDEX and its companion (the older forms' index), or INDEX alone when it is its own."""
    companion = index.companion()
    return (index,) if companion is index else (index, companion)


def analyzer_digest():
    """SHA-256 of the code that analyses (ANALYZER_FILES next to build_cache) and the Python version."""
    import build_cache as B
    folder = Path(B.__file__).resolve().parent
    rows = {}
    for name in ANALYZER_FILES:
        try:
            rows[name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        except OSError:
            rows[name] = None
    return B.digest_json({'files': rows, 'python': sys.version})


def index_key(index):
    """The key of INDEX's analysis: every file it covers by SHA-256 (the raw bytes), its checkout folder, its form
    and the analysing code."""
    import build_cache as B
    files = index.files
    tree = {}
    for path in sorted(files):
        tree[path] = B.sha256_file(Path(index.root) / path) if path == B.MACHINE_SETTINGS_FILE else files[path]
    return B.digest_json({'schema': STORE_SCHEMA, 'root': str(Path(index.root).resolve()), 'tree': B.digest_json(tree),
                          'options': {'scope': index.scope, 'top_format': index.top_format,
                                      'chim_label_keys': index.chim_label_keys, 'narrow_headers': index.narrow_headers,
                                      'engine_facts': index.engine_facts, 'content_keyed': index.content_keyed},
                          'analyzer': analyzer_digest()})


def memo_state(index):
    """INDEX's memos (the objects themselves, not copies)."""
    state = {field: getattr(index, field) or {} for field in MEMO_FIELDS}
    state['_chim_line'] = index._chim_line
    return state


def merge(index, state):
    """Add the entries of STATE (memo_state of an index of the same tree and form, from any process) that INDEX
    lacks; every entry is a pure function of the files, so any process gives the same. A closure comes with its
    reach and keyed code, as _closure_symbols leaves them together."""
    closures = state.get('_closures') or {}
    reached, keyed = state.get('_reached') or {}, state.get('_keyed') or {}
    for key, value in closures.items():
        if key not in index._closures:
            index._closures[key] = value
            if key in reached:
                index._reached[key] = reached[key]
            if key in keyed:
                index._keyed[key] = keyed[key]
    for field in ('_symbols', '_includes', '_json_values', '_modules', '_exact', '_selections', '_own_names'):
        values = state.get(field) or {}
        if not values:
            continue
        mine = getattr(index, field)
        if mine is None:
            mine = {}
            setattr(index, field, mine)
        for key, value in values.items():
            mine.setdefault(key, value)
    if index._chim_line is None and state.get('_chim_line') is not None:
        index._chim_line = state['_chim_line']


def entries(index):
    return sum(len(getattr(ix, field) or {}) for ix in pair(index) for field in MEMO_FIELDS)


def analysed(index, script):
    """True when INDEX holds SCRIPT's selection and reach (and its companion the reach of the older forms)."""
    name = str(Path(script).resolve())
    if (name, index.top_format) not in (index._selections or {}) or name not in index._closures:
        return False
    companion = index.companion()
    return companion is index or name in companion._closures


# --------------------------------------------------------------------------
# The pool

_SENT = None


def _start_worker():
    """A worker remembers which memo entries it inherited, so it sends back only what it worked out."""
    global _SENT
    _SENT = [{field: set(getattr(ix, field) or ()) for field in MEMO_FIELDS} for ix in pair(_INDEX)]
    _SENT.append(set(_INDEX.files._hashes))


def _delta():
    parts = []
    for ix, sent in zip(pair(_INDEX), _SENT):
        part = {}
        for field in MEMO_FIELDS:
            values = getattr(ix, field) or {}
            new = {key: value for key, value in values.items() if key not in sent[field]}
            sent[field].update(new)
            part[field] = new
        part['_chim_line'] = ix._chim_line
        parts.append(part)
    hashes = _INDEX.files._hashes
    new = {key: value for key, value in hashes.items() if key not in _SENT[-1]}
    _SENT[-1].update(new)
    return parts, new


def _parse_task(relatives):
    for relative in relatives:
        for ix in pair(_INDEX):
            ix._module_symbols(relative)
    return _delta()


def _queries(index, script):
    """Everything a stage key and the stage plan ask the index for about SCRIPT (stage_components, stage_closures,
    stage_units): its selection, the older forms', the AMIWIND_* names in both forms and its reached units."""
    selected, uncertain = index.selection(script)
    if not uncertain and index.top_format != 1:
        index.previous_selections(script)
    index.environment_names(script)
    companion = index.companion()
    if companion is not index:
        companion.environment_names(script)
    index.reached_units(script)


def _analyse_task(script):
    _queries(_INDEX, script)
    return _delta()


def _take(index, result):
    parts, hashes = result
    for ix, part in zip(pair(index), parts):
        merge(ix, part)
    for key, value in hashes.items():
        index.files._hashes.setdefault(key, value)


RESULT_TIMEOUT_S = 900    # no result for this long: the pool is stopped and this process works on alone


def _run_pool(index, task, items, workers):
    """TASK(item) for every item on WORKERS processes forked at once, each result merged into INDEX as it comes. A
    pool with no result for RESULT_TIMEOUT_S (a worker that died: multiprocessing.Pool would wait for its task without
    end) is stopped with an error; the caller then works on alone."""
    import multiprocessing
    global _INDEX
    context = multiprocessing.get_context('fork')
    _INDEX = index
    gc.collect()
    gc.freeze()      # the inherited objects stay out of the workers' collections (no copy of every page)
    try:
        with context.Pool(workers, initializer=_start_worker) as pool:
            results = pool.imap_unordered(task, items)
            for _ in range(len(items)):
                _take(index, results.next(timeout=RESULT_TIMEOUT_S))
    finally:
        gc.unfreeze()
        _INDEX = None


def modules(index):
    """The Python modules of INDEX's checkout not analysed yet, the largest first."""
    found = []
    for path in index.files:
        if path.endswith('.py') and any(path not in ix._symbols for ix in pair(index)):
            try:
                size = (Path(index.root) / path).stat().st_size
            except OSError:
                continue
            found.append((-size, path))
    return [path for _, path in sorted(found)]


def analyse(index, scripts, workers):
    """Work out SCRIPTS' analysis in INDEX on WORKERS processes: the checkout's modules not read yet, once each, then
    the scripts (in this process when one is left). Returns the number of modules read on the pool."""
    import build_cache as B
    use_memo(index)
    pair(index)                       # the companion exists before the fork, so its memos come back too
    todo = modules(index) if workers > 1 else []
    if todo:
        chunks = [todo[i:i + PARSE_CHUNK] for i in range(0, len(todo), PARSE_CHUNK)]
        _run_pool(index, _parse_task, chunks, min(workers, len(chunks)))
        # every index of this process that reads the same text in the same form takes the module from here
        for relative in todo:
            try:
                raw = (Path(index.root) / relative).read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for ix in pair(index):
                if relative in ix._symbols:
                    B._SYMBOL_MEMO.setdefault(ix.symbol_key(relative, raw), ix._symbols[relative])
    scripts = [str(Path(s).resolve()) for s in scripts]
    if workers > 1 and len(scripts) > 1:
        _run_pool(index, _analyse_task, scripts, min(workers, len(scripts)))
    else:
        for script in scripts:
            _queries(index, script)
    return len(todo)


# --------------------------------------------------------------------------
# The store

class Store:
    """WORKSPACE/cache/preflight-analysis-v1: one analysed source tree per file (KEY.pickle.zlib: MAGIC, the SHA-256 of
    the compressed body, the body). A file that does not check out is ignored (worked out again); a store problem
    never stops a build."""

    def __init__(self, folder):
        self.folder = Path(folder)

    def path(self, key):
        return self.folder / (key + '.pickle.zlib')

    def load(self, key):
        path = self.path(key)
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if not raw.startswith(MAGIC):
            return None
        head, _, body = raw[len(MAGIC):].partition(b'\n')
        if hashlib.sha256(body).hexdigest().encode() != head:
            return None
        try:
            doc = pickle.loads(zlib.decompress(body))
        except Exception:  # noqa: BLE001 - a damaged entry is worked out again
            return None
        if not isinstance(doc, dict) or doc.get('schema') != STORE_SCHEMA or doc.get('key') != key:
            return None
        try:
            os.utime(path)        # the most recently used are kept (prune)
        except OSError:
            pass
        return doc

    def save(self, key, doc):
        body = zlib.compress(pickle.dumps(doc, protocol=pickle.HIGHEST_PROTOCOL), 1)
        path = self.path(key)
        self.folder.mkdir(parents=True, exist_ok=True)
        partial = path.with_name('%s.%d.tmp' % (path.name, os.getpid()))
        partial.write_bytes(MAGIC + hashlib.sha256(body).hexdigest().encode() + b'\n' + body)
        os.replace(partial, path)
        self.prune()
        return path, len(body)

    def prune(self, keep=STORE_KEEP):
        """Keep the KEEP most recently used analyses; remove the rest (and stale partial writes of this store)."""
        now = time.time()
        kept = []
        for path in self.folder.glob('*'):
            try:
                info = path.stat()
            except OSError:
                continue
            if path.name.endswith('.tmp'):
                if now - info.st_mtime > 3600:
                    path.unlink(missing_ok=True)
            elif path.name.endswith('.pickle.zlib'):
                kept.append((info.st_mtime, path))
        for _, path in sorted(kept, reverse=True)[keep:]:
            path.unlink(missing_ok=True)


def store():
    import build_cache as B
    return Store(B.ANALYSIS_STORE) if B.ANALYSIS_STORE is not None else None


def attach(index, key, log=None):
    """INDEX takes the analysis of KEY: from this process (an index of the same tree and form; their memos shared),
    or from the store. Returns where it came from ('this process', the stored origin, or None: nothing yet)."""
    live = _LIVE.get(key)
    if live is not None:
        other = live['index']
        if other is not index:
            for ix, ox in zip(pair(index), pair(other)):
                merge(ix, memo_state(ox))
            for name, value in other.files._hashes.items():
                index.files._hashes.setdefault(name, value)
            live['index'] = index          # now the fuller of the two: it is the one kept
        return 'this process'
    _LIVE[key] = {'index': index, 'origin': None, 'loaded': 0}
    kept = store()
    if kept is None:
        return None
    try:
        doc = kept.load(key)
    except Exception as exc:  # noqa: BLE001 - the store never stops a build
        (log or print)('Pre-flight: the stored analysis could not be read (%s); worked out again' % exc)
        doc = None
    if doc is None:
        return None
    states = doc.get('states') or []
    for ix, state in zip(pair(index), states):
        merge(ix, state)
    _LIVE[key].update(origin=doc.get('origin') or {}, loaded=entries(index))
    return doc.get('origin') or {}


def origin_text(origin):
    if origin == 'this process':
        return 'taken from this process (the same source tree)'
    kind = origin.get('kind') or 'run'
    return 'taken from the %s of %s (%s)' % (kind, origin.get('made') or '?', origin.get('run') or '?')


def prepare_index(index, scripts, log=print):
    """The build's pre-flight analysis of SCRIPTS in INDEX (module doc): taken where it exists, the rest on the pool.
    Prints one line saying which. Never raises: anything it cannot do, the serial path does (the stage keys are the
    same either way)."""
    try:
        return _prepare_index(index, scripts, log)
    except Exception as exc:  # noqa: BLE001 - an accelerator never stops the reuse check or the build
        log('Pre-flight: the stage source analysis is worked out in this process (%s: %s)' % (type(exc).__name__, exc))
        return None


def _prepare_index(index, scripts, log):
    import build_cache as B
    began = time.monotonic()
    use_memo(index)
    key = index_key(index)
    origin = attach(index, key, log)
    missing = [script for script in scripts if not analysed(index, script)]
    try:
        workers = int(os.environ.get(PREFETCH_ENV) or 0) or B.PREFLIGHT_WORKERS or 1
    except ValueError:
        workers = B.PREFLIGHT_WORKERS or 1
    where = '' if origin is None else origin_text(origin) + '; '
    if not missing:
        if scripts:
            log('Pre-flight: stage source analysis %s%d stage scripts, %.1f s (source tree %s)'
                % (origin_text(origin) + ': ' if origin is not None else 'taken: ', len(scripts),
                   time.monotonic() - began, key[:12]))
        return key
    if workers < 2:
        log('Pre-flight: stage source analysis: %s%d of %d stage scripts computed in this process (one worker; '
            'source tree %s)' % (where, len(missing), len(scripts), key[:12]))
        return key
    try:
        read = analyse(index, missing, workers)
    except Exception as exc:  # noqa: BLE001 - the pool is an accelerator: this process works out the rest
        log('Pre-flight: the analysis pool stopped (%s: %s); this process computes the rest'
            % (type(exc).__name__, exc))
        return key
    log('Pre-flight: stage source analysis computed: %s%d of %d stage scripts and %d modules on %d worker processes '
        '(%d cores usable), %.1f s (source tree %s)' % (where, len(missing), len(scripts), read, workers,
                                                        usable_cores(), time.monotonic() - began, key[:12]))
    return key


def _stderr(line):
    print(line, file=sys.stderr, flush=True)


def attach_old(index, log=_stderr):
    """An index of an earlier run's checkout (engine_facts.translate): its analysis taken from the store when kept,
    and kept with the others. Never stops the caller."""
    try:
        use_memo(index)
        origin = attach(index, index_key(index), log)
        log('Pre-flight: analysis of the earlier checkout %s %s' % (
            index.root, origin_text(origin) if origin is not None else 'computed in this process (kept afterwards)'))
    except Exception as exc:  # noqa: BLE001 - only an accelerator
        log('Pre-flight: the analysis of %s is worked out here (%s)' % (index.root, exc))


def save_analyses(log=print):
    """Keep every analysis of this process that grew since it was taken (the store's files; one line each)."""
    import build_cache as B
    kept = store()
    if kept is None or B.ANALYSIS_READ_ONLY:
        return []
    written = []
    for key, live in list(_LIVE.items()):
        index = live['index']
        count = entries(index)
        if count <= live['loaded']:
            continue
        began = time.monotonic()
        origin = dict(B.ANALYSIS_ORIGIN or {})
        origin.setdefault('kind', 'run')
        origin['made'] = time.strftime('%Y-%m-%d %H:%M:%S %z')
        doc = {'schema': STORE_SCHEMA, 'key': key, 'root': str(index.root), 'origin': origin,
               'states': [memo_state(ix) for ix in pair(index)]}
        try:
            path, size = kept.save(key, doc)
        except Exception as exc:  # noqa: BLE001 - the store never stops a build
            log('Pre-flight: the analysis of %s was not kept (%s: %s)' % (index.root, type(exc).__name__, exc))
            continue
        live['loaded'] = count
        written.append(path)
        log('Pre-flight: stage source analysis of %s kept for the next check or build of this source tree (%s, '
            '%.1f MiB, %.1f s)' % (index.root, path.name[:12], size / 2 ** 20, time.monotonic() - began))
    return written


def forget():
    """This process's analyses forgotten (tools/build.py at its end; tests)."""
    _LIVE.clear()
