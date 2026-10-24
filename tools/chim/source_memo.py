"""Per-process memory of the CHIM source stage's repeated reads (B5, v0.0.42).

Every CHIM area runs the source stage (chim.build.source_stage -> import_town.collect): it reads the game's
master file for its 3x3 cells and every model placed there, and a frame with a reference margin exports its
models twice (the footprint probe, then the scenery). Region frames share most of their models with their
neighbours, and the stage pool keeps its workers for the whole step, so the same model was parsed up to a dozen
times in one worker (16 October 2026, dev5: 723 source stages, 24,500 CPU seconds; a light frame 21.9 s, of which
13.6 s parsing the whole master and 5.3 s listing and hashing the game files; a heavy frame 232 s, 213 s of it in
two model exports reading the same 168 models).

install() makes the reads of this process remember their results, keyed by the exact bytes they read
(SHA-256 of the model, the master's path, size and modification time) and the AMIWIND_* environment, and
hands out copies, so every caller sees exactly the values a fresh read would give: the stage writes the same
files, byte for byte (tests/test_chim_source_memo.py). The memory is bounded (AMIWIND_SOURCE_MEMO_MB, default
384 MiB per process, least recently used out first). AMIWIND_SOURCE_MEMO=off: the method before v0.0.42 (every
read done again).

Only the CHIM stage installs it (chim.build): other stages keep their code paths and their keys unchanged.
"""
import hashlib
import os
import pickle
from collections import OrderedDict

ENV = 'AMIWIND_SOURCE_MEMO'
LIMIT_ENV = 'AMIWIND_SOURCE_MEMO_MB'
DEFAULT_MB = 384

_STATE = {'installed': False, 'originals': {}}
_STATS = {'models': [0, 0], 'collision_markers': [0, 0], 'master': [0, 0]}   # [hits, misses]


def enabled():
    return os.environ.get(ENV, 'on') != 'off'


def _environment():
    return hashlib.sha256(repr(sorted((k, v) for k, v in os.environ.items()
                                      if k.startswith('AMIWIND_') and k not in (ENV, LIMIT_ENV))).encode()
                          ).hexdigest()


class _Memory:
    """Pickled values by key, least recently used out first beyond the byte limit."""

    def __init__(self):
        self.values, self.size = OrderedDict(), 0

    def limit(self):
        try:
            return max(0, int(os.environ.get(LIMIT_ENV, DEFAULT_MB))) * 1024 * 1024
        except ValueError:
            return DEFAULT_MB * 1024 * 1024

    def get(self, key):
        blob = self.values.get(key)
        if blob is None:
            return None
        self.values.move_to_end(key)
        return pickle.loads(blob)

    def put(self, key, value):
        blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        if len(blob) > self.limit():
            return
        old = self.values.pop(key, None)
        if old is not None:
            self.size -= len(old)
        self.values[key] = blob
        self.size += len(blob)
        while self.size > self.limit() and self.values:
            _, dropped = self.values.popitem(last=False)
            self.size -= len(dropped)


_MODELS = _Memory()
_MARKERS = _Memory()


def _read_raw(path, extent):
    from pathlib import Path
    with Path(path).open('rb') as source:
        source.seek(extent['offset'])
        return source.read(extent['bytes'])


def read_model(task):
    """prepare_scenery._read_model, remembered by the model's bytes (same tuple, a fresh copy)."""
    import prepare_scenery
    original = _STATE['originals'].get('read_model') or prepare_scenery._read_model
    if not enabled():
        return original(task)
    name, path, extent, collision = task
    try:
        raw = _read_raw(path, extent)
    except OSError:
        return original(task)
    key = (name, collision, hashlib.sha256(raw).hexdigest(), extent['bytes'], _environment())
    value = _MODELS.get(key)
    if value is not None:
        _STATS['models'][0] += 1
        return value
    _STATS['models'][1] += 1
    value = original(task)
    _MODELS.put(key, value)
    return value


def source_collision_metadata(raw, N):
    """prepare_scenery.source_collision_metadata, remembered by the model's bytes."""
    import prepare_scenery
    original = _STATE['originals'].get('source_collision_metadata') or prepare_scenery.source_collision_metadata
    if not enabled():
        return original(raw, N)
    # the AMIWIND_* environment too: the rule depends on AMIWIND_COLLISION_SOURCE (tools/collision_source_env.py)
    key = (hashlib.sha256(raw).hexdigest(), len(raw), _environment())
    value = _MARKERS.get(key)
    if value is not None:
        _STATS['collision_markers'][0] += 1
        return value
    _STATS['collision_markers'][1] += 1
    value = original(raw, N)
    _MARKERS.put(key, value)
    return value


def install():
    """Remember the source stage's model reads and master parse in this process (idempotent; a no-op with
    AMIWIND_SOURCE_MEMO=off). The master parse is shared by mwad.audit itself (load_esm_shared)."""
    if _STATE['installed'] or not enabled():
        return False
    import prepare_scenery
    _STATE['originals'] = {'read_model': prepare_scenery._read_model,
                           'source_collision_metadata': prepare_scenery.source_collision_metadata}
    prepare_scenery._read_model = read_model
    prepare_scenery.source_collision_metadata = source_collision_metadata
    from mwad import audit
    audit.share_master(True)
    _STATE['installed'] = True
    return True


def stats():
    """{'models': {'reused': n, 'read': n}, ...} of this process."""
    from mwad import audit
    rows = dict(_STATS, master=audit.shared_master_stats())
    return {k: {'reused': v[0], 'read': v[1]} for k, v in rows.items()}
