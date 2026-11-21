# SPDX-License-Identifier: GPL-3.0-only
"""Each CHIM area's source catalogue kept in the unit cache across runs (BUILD-TESTER-32GB-OOM-67).

The source stage of every CHIM area (chim.build.source_stage -> import_town.collect) writes the area's catalogue into
the area's work folder of the run: the audit of its source cells, its scenery export, the list of its references, its
emitters, lava pools, fixed visibility and coverage. Kept only there, a build that ran the CHIM stage again in a new
run folder made all of it again, for every area: 210 of the 294 CPU minutes of a CHIM stage whose other units all came
from the unit cache (the v0.0.67-dev2 full runs), 421 CPU minutes from scratch; so a build that stopped for memory and
was started again lost it too.

Each area's catalogue is one unit of the unit cache UNIT, keyed on
  - the code collect reaches (pass_cache.source_digest of tools/import_town.py collect) and the AMIWIND_* settings that
    code reads (unit_store.bake_keyed_cache);
  - the area's source receipt (import_town.source_receipt: its geometry, every game file it lists by SHA-256, the
    conversion's mode and code), the area's settings as the source stage is handed them, and the game data identity of
    the build's input lock (pass_cache.game_data_digest, with the selected expansion layers).
A new work folder takes the files back when all of that is unchanged: the files collect writes, byte for byte, as
collect would write them. The receipt file itself is written again from the key's receipt, not stored (1.7 GiB of the
5.6 GiB the source files of the v0.0.66 from-scratch build's 1,351 areas held; the rest, stored once by SHA-256, is
3.9 GiB). A cache that is off, a build without an input lock, --rebuild-unit UNIT:AREA, or a work folder that already
holds other bytes at one of the unit's paths: collect runs as before, and its files are stored.
"""
import hashlib
import json
import os
from pathlib import Path

UNIT = 'chim-area-source'
FORMAT = 1
RECEIPT = 'source-receipt.json'
_OPENED = {}


def receipt_text(receipt):
    """The receipt file's text as the source stage writes it."""
    return json.dumps(receipt, indent=2) + '\n'


def open_cache():
    """(unit cache, game data identity) of the source units, opened once per process for the same cache folder, input
    lock and AMIWIND_* settings (opening hashes the repository's sources; the identity reads the build's input lock);
    (None, None) when the cache is off or the build has no input lock."""
    import pass_cache
    from known_inputs import LOCK_ENV
    folder = pass_cache.folder()
    if folder is None:
        return None, None
    memo = (str(folder), os.environ.get(LOCK_ENV),
            tuple(sorted((k, v) for k, v in os.environ.items() if k.startswith('AMIWIND_'))))
    if memo not in _OPENED:
        import import_town
        from unit_store import WORK_PLACE_SETTINGS, bake_keyed_cache
        from pass_cache import covered_lines, game_data_digest, previous_digests, source_digest
        # keyed on what collect runs (its reach in every module it calls); the receipt in the inputs still counts
        # import_town.py and lava.py whole (import_town.source_receipt), as the source stage's own reuse always did
        cache = bake_keyed_cache(
            UNIT, {}, source_digest((import_town.__file__, 'collect')),
            previous_digests((import_town.__file__, 'collect')), (import_town.__file__,),
            covered_lines((import_town.__file__, 'collect')), neutral=WORK_PLACE_SETTINGS,
            entries=((import_town.__file__, 'collect'),))
        identity = game_data_digest() if cache is not None else None
        _OPENED[memo] = (cache, identity) if identity is not None else (None, None)
    return _OPENED[memo]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=repr).encode()).hexdigest()


def unit(settings, receipt):
    """(unit cache, inputs) of one area's source catalogue, or (None, None) (see open_cache). The inputs: the area (its
    town id, the unit's name in listings and --rebuild-unit), the unit's format, the receipt, the settings and the game
    data identity, each by SHA-256."""
    cache, identity = open_cache()
    if cache is None:
        return None, None
    from town_config import town_field
    return cache, {'entry': {'name': str(town_field(settings, 'id'))}, 'format': FORMAT, 'receipt': _digest(receipt),
                   'settings': _digest(settings), 'game_data': identity}


def files_of(folder):
    """The files under FOLDER, as posix paths relative to it (an empty set for a missing folder)."""
    folder = Path(folder)
    if not folder.is_dir():
        return set()
    return {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}


def restore(cache, inputs, work, receipt):
    """Write the stored catalogue of INPUTS into the work folder WORK and its receipt last; True when it was there.
    False (nothing written) without a complete stored unit, for a --rebuild-unit, or when WORK holds other bytes at one
    of its paths (a file there with the stored bytes, left by a restore that stopped midway, is kept as it is)."""
    from pass_cache import forced, unit_label
    if cache is None or forced(cache.name, unit_label(inputs)):
        return False
    found = cache.load_unit(inputs)
    if found is None:
        return False
    row, files = found
    if not isinstance(row, dict) or row.get('format') != FORMAT or RECEIPT in files:
        return False
    work = Path(work)
    for relative, data in files.items():
        target = work / relative
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            return False
    if (work / RECEIPT).exists():
        return False
    for relative, data in sorted(files.items()):
        target = work / relative
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + '.restoring')
        partial.write_bytes(data)
        os.replace(partial, target)
    (work / RECEIPT).write_text(receipt_text(receipt), encoding='utf-8', newline='\n')
    return True


def store(cache, inputs, work, before, label):
    """Store what the source stage wrote into WORK (every file not in BEFORE, the receipt left out) as the unit of
    INPUTS and read it back (unit_store.stored). Nothing for a cache that is off. A store not found again stops the
    stage, as every unit store does (UNIT-CACHE-STORE-ERRORS-SILENT-63): the next build would make it again."""
    if cache is None:
        return None
    from unit_store import stored
    work = Path(work)
    contents = {relative: (work / relative).read_bytes() for relative in sorted(files_of(work) - set(before))
                if relative != RECEIPT}
    if stored(cache, inputs, {'format': FORMAT, 'area': label}, contents):
        return True
    print('!! [chim] %s: STORE FAILED: the source catalogue of %s is not in the unit cache after it was stored (is the '
          'cache folder writable by this user?)' % (UNIT, label), flush=True)
    raise RuntimeError('%s: the unit cache did not keep the source catalogue of %s; the next build would make it again '
                       '(UNIT-CACHE-STORE-ERRORS-SILENT-63)' % (UNIT, label))
