# SPDX-License-Identifier: GPL-3.0-only
"""What the selected expansion layers change, as a per-unit view for the unit caches (BUILD-UNIT-KEYS-LAYER-BLIND-66).

A unit baked from the base game is still right with Tribunal and Bloodmoon selected when nothing it reads changes. A
unit cache whose inputs already hold the records the stage resolved for the unit (a resident's appearance and
greeting) keys the rest of what it reads from the game data as a view of the layers:

  * delta(): every record the selected layers add, replace or delete against the base game, by its merge key (a
    record's type and id, a cell's name or grid, a dialogue topic), with the SHA-256 of the merged record; read once
    per process with the merging reader's own rules (src/mwad/masters.py);
  * overrides(): every archive file the layers' archives replace with other bytes (mwad.archives.layered_bsa: a
    later archive wins), with the SHA-256 of the file the layered archive hands out;
  * view(): the part of both a unit reads: the record keys it names, and the archive files its asset names point at
    (an override whose name is one of them, or whose texture name is in the bytes of a model it names);
  * identity(): the unit's game data identity: the input lock digest (pass_cache.game_data_digest without the
    layers) when the view is empty, so a unit the layers do not touch keeps its base-game key and is reused; else the
    lock digest with the view.

With the base game alone every view is empty and identity() is the lock digest: base-game keys never move.
A cache that cannot name what it reads keeps pass_cache.game_data_digest() (the selection itself in the key).
reads(): the layer archive files read in this process since begin() (the layered archives record them), for the check
that a unit read nothing its view left out (a gap costs reuse, never a stale unit).
"""
import hashlib
import json
from pathlib import Path

FORM = 'layer view 1'
_DELTA = {}
_OVERRIDES = {}
_NIFS = {}


def _selected(masters=None):
    from mwad.masters import selected_masters
    return selected_masters(masters)


def layers_selected(masters=None):
    """True when the build selects an expansion layer besides the base game (AMIWIND_MASTERS, or MASTERS)."""
    return len(_selected(masters)) > 1


def _entry_digest(entry):
    from mwad import masters as M
    h = hashlib.sha256()
    if isinstance(entry, M._Cell):
        h.update(repr(('cell', entry.flags, entry.header)).encode('utf-8', 'surrogateescape'))
        for ref, block in sorted(entry.refs.items()):
            h.update(repr((ref, block)).encode('utf-8', 'surrogateescape'))
    elif entry[0] == 'dial':
        _, unused, flags, subs, (order, deleted) = entry
        kept = [(item[0], item[3], item[4]) for item in order if not deleted.get(item[0])]
        h.update(repr(('dial', flags, subs, kept)).encode('utf-8', 'surrogateescape'))
    else:
        h.update(repr(('rec',) + tuple(entry[1:])).encode('utf-8', 'surrogateescape'))
    return h.hexdigest()


def _loaded(data, names):
    from mwad import masters as M
    from mwad.esm import subrecords
    from mwad.paths import child_ci
    merge = M._Merge()
    merge.names = M.selected_masters(names)
    for index, name in enumerate(merge.names):
        raw = child_ci(Path(data), name).read_bytes()
        masts = []
        for tag, _, _, payload in M._raw_records(raw):
            if tag == 'TES3':
                masts = [M._text(d) for t, d in subrecords(payload) if t == 'MAST']
            break
        merge.load(index, name, raw, masts)
    return merge


def record_key(tag, ident):
    """The merge key of a record of TAG named IDENT (case does not matter), as delta() holds it: 'CELL' with an
    interior name or (x, y) for an exterior cell, 'DIAL' a topic, else the record's type."""
    if tag == 'CELL':
        if isinstance(ident, (tuple, list)):
            return ('ext', int(ident[0]), int(ident[1]))
        return ('int', str(ident).casefold())
    return (tag, str(ident).casefold())


def delta(data, masters=None):
    """{merge key: SHA-256 of the merged record, or None for a deleted one} of every record the selected layers add,
    replace or delete against the base game; {} for the base game alone."""
    masters = _selected(masters)
    if len(masters) == 1:
        return {}
    key = (str(Path(data).resolve()), masters)
    if key not in _DELTA:
        base = _loaded(data, masters[:1])
        full = _loaded(data, masters)
        out = {}
        for k in full.order:
            value = _entry_digest(full.entries[k])
            if k not in base.entries or _entry_digest(base.entries[k]) != value:
                out[k] = value
        for k in base.order:
            if k not in full.entries:
                out[k] = None
        _DELTA[key] = out
    return _DELTA[key]


def merged_record(data, key, masters=None):
    """The subrecords [(tag, bytes)] of the merged record KEY (record_key), or None (not there, a cell or a topic)."""
    from mwad.esm import subrecords
    masters = _selected(masters)
    memo = ('merged', str(Path(data).resolve()), masters)
    if memo not in _DELTA:
        _DELTA[memo] = _loaded(data, masters)
    entry = _DELTA[memo].entries.get(key)
    if not isinstance(entry, tuple) or entry[0] != 'rec':
        return None
    return list(subrecords(entry[4]))


def footstep_records():
    """The merge keys of the sound records an actor bake's sound payload can name: the footstep, wading and swimming
    sounds of every foot kind (npc_anim.event_sounds; read by npc_anim.soun_records)."""
    import npc_anim
    return sorted({record_key('SOUN', s) for foot in npc_anim.FOOT for ids in npc_anim.event_sounds(foot).values()
                   for s in ids})


def overrides(data, masters=None):
    """{archive path: SHA-256} of the files the selected layers' archives replace with other bytes; {} for the base
    game alone."""
    masters = _selected(masters)
    if len(masters) == 1:
        return {}
    key = (str(Path(data).resolve()), masters)
    if key not in _OVERRIDES:
        from mwad.archives import BASE_ARCHIVE, layered_bsa
        from mwad.audit import BSA
        from mwad.esm import read_bsa_asset
        from mwad.paths import child_ci
        plain = BSA(child_ci(Path(data), BASE_ARCHIVE))
        layered = layered_bsa(Path(data), masters)
        out = {}
        for name, entry in dict.items(layered.entries):
            if name in plain.entries and entry.get('path') not in (None, plain.path):
                new = hashlib.sha256(read_bsa_asset(layered, name)).hexdigest()
                if new != hashlib.sha256(read_bsa_asset(plain, name)).hexdigest():
                    out[name] = new
        _OVERRIDES[key] = out
    return _OVERRIDES[key]


def asset_names(value):
    """Every string in VALUE (nested dicts, lists, tuples) that names a game asset (a model, texture or sound file),
    lower case with forward slashes."""
    found = set()

    def walk(v):
        if isinstance(v, dict):
            for item in v.values():
                walk(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                walk(item)
        elif isinstance(v, str) and '.' in v[-5:]:
            name = v.replace('\\', '/').casefold()
            if name.rsplit('.', 1)[-1] in ('nif', 'kf', 'dds', 'tga', 'bmp', 'wav', 'mp3'):
                found.add(name)
    walk(value)
    return found


def _candidates(name):
    """The archive paths an asset NAME can be read from (with and without its folder prefix)."""
    out = {name}
    folder = {'nif': 'meshes/', 'kf': 'meshes/', 'dds': 'textures/', 'tga': 'textures/', 'bmp': 'textures/',
              'wav': 'sound/', 'mp3': 'sound/'}.get(name.rsplit('.', 1)[-1])
    if folder and not name.startswith(folder):
        out.add(folder + name)
    return out


def _model_textures(data, model, masters):
    """The overridden texture paths whose names are in the bytes of MODEL (an archive path), as the layered archive
    holds it (a model names its textures; read once per process)."""
    from mwad.archives import layered_bsa
    from mwad.esm import read_bsa_asset
    key = (str(Path(data).resolve()), masters, model)
    if key not in _NIFS:
        hits = set()
        stems = {path: path.rsplit('/', 1)[-1].rsplit('.', 1)[0].encode() for path in overrides(data, masters)
                 if path.startswith('textures/')}
        if stems:
            memo = ('archive', str(Path(data).resolve()), masters)
            if memo not in _NIFS:
                _NIFS[memo] = layered_bsa(Path(data), masters)
            archive = _NIFS[memo]
            if dict.__contains__(archive.entries, model):
                raw = read_bsa_asset(archive, model).lower()
                hits = {path for path, stem in stems.items() if stem in raw}
        _NIFS[key] = hits
    return _NIFS[key]


def view(data, records=(), assets=(), masters=None):
    """The part of the layers' changes a unit reads: sorted [kind, key, SHA-256] rows of the RECORDS (merge keys,
    record_key) the layers change and of the archive files the ASSETS (asset names, asset_names) point at that the
    layers replace (the asset itself, or a texture named in a model's bytes). [] for the base game alone."""
    masters = _selected(masters)
    if len(masters) == 1:
        return []
    changed = delta(data, masters)
    rows = [['record', list(k), changed[k]] for k in sorted({tuple(k) for k in records}, key=repr) if tuple(k) in changed]
    replaced = overrides(data, masters)
    files = set()
    for name in assets:
        for path in _candidates(name):
            if path in replaced:
                files.add(path)
            if path.startswith('meshes/') and path.endswith('.nif'):
                files |= _model_textures(data, path, masters)
    rows += [['archive', path, replaced[path]] for path in sorted(files)]
    return rows


def identity(data, records=(), assets=(), masters=None, base=None):
    """A unit's game data identity (see the module text): the lock digest when the layers change nothing it reads,
    else the lock digest with its view; None without a lock (pass_cache.game_data_digest). BASE: the lock digest when
    the caller has it (read once per stage: the lock is several MB of JSON)."""
    if base is None:
        import pass_cache
        base = pass_cache.game_data_digest(layers=False)
    if base is None:
        return None
    rows = view(data, records, assets, masters)
    if not rows:
        return base
    return hashlib.sha256(json.dumps([base, FORM, rows], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


# The archive paths this process read from a layer's archive since begin(). The layered archive reader itself
# (src/mwad/archives.py) is left as it is: its code is what the unit keys stored before the content-keyed readers
# were keyed by, and those keys are looked up as an older form (pass_cache.previous_digests). begin() wraps its
# layered_bsa (and every module's imported name of it) so that the entries it hands out record a lookup of a layer's
# file; the entries are the same ones.
READS = set()
_WRAPPED = []


class _LayerEntries(dict):
    """A layered archive's entries: a lookup of an entry that comes from a layer's archive (it carries the 'path' of
    that archive) is recorded in READS."""

    def __getitem__(self, key):
        entry = dict.__getitem__(self, key)
        if 'path' in entry:
            READS.add(key)
        return entry

    def get(self, key, default=None):
        entry = dict.get(self, key, default)
        if isinstance(entry, dict) and 'path' in entry:
            READS.add(key)
        return entry


def _watch():
    if _WRAPPED:
        return
    import sys
    from mwad import archives
    original = archives.layered_bsa

    def layered_bsa(data_files, masters=None):
        archive = original(data_files, masters)
        if not isinstance(archive.entries, _LayerEntries) and any('path' in e for e in archive.entries.values()):
            archive.entries = _LayerEntries(archive.entries)
        return archive
    layered_bsa.__doc__ = original.__doc__
    for module in list(sys.modules.values()):
        if getattr(module, 'layered_bsa', None) is original:
            module.layered_bsa = layered_bsa
    _WRAPPED.append((original, layered_bsa))


def begin():
    """Start recording the layer archive files this process reads (the layered archives made from now on)."""
    _watch()
    READS.clear()


def reads():
    """The archive paths read from a layer's archive in this process since begin() (sorted)."""
    return sorted(READS)


def gaps(read, rows, data, masters=None):
    """The layer archive files of READ (reads()) that the layers replace with other bytes but the unit's view ROWS
    leave out: a unit with any is not stored under its view key."""
    replaced = overrides(data, masters)
    named = {row[1] for row in rows if row[0] == 'archive'}
    return sorted(path for path in read if path in replaced and path not in named)
