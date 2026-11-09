# SPDX-License-Identifier: GPL-3.0-only
"""Every finished unit into the unit cache the moment it comes back (UNIT-STORED-AT-MAP-END-62).

A stage that bakes many independent units (the player view's bodies, say) keeps each unit in the checksummed unit
cache (tools/pass_cache.py UnitCache) so that a build that stops later starts again from the units still missing.
The player view stored its units only when its whole pool map had ended (one worker pool for the step since
BUILD-PLAYER-VIEW-UNDERUSED-48): a stage that stopped mid-map, or a container that was stopped, kept nothing of that
run, and every resume of the v0.0.62 release build baked every player body again (incident INC-20261108-V062BUILD).

run_each() hands each unit to the caller's KEEP the moment its worker returns it (build_parallel.completed_map), in
the parent, so KEEP stores it at once; a unit that fails is collected and named, never ends the map; the times of
every unit that came back go into the item cost history (build_costs) also when the map stops early.

LEGACY_SOURCES keeps a unit cache backwards compatible when its key changes form: a cache keyed on what its workers
run (pass_cache.source_digest of (module, function) entries) looks a missing unit up, once, under the whole-file key
its units were stored with before, but only while the code that makes the unit is exactly what it was then (the
bake-reach digest in the table), so a stored unit is never taken for code that changed. A hit is stored under the
current key (pass_cache.PassCache.load does that for every previous key).
"""
import time

# (unit cache name, bake-reach sources digest) -> whole-file sources digests its units were stored under.
LEGACY_SOURCES = {
    # tools/prepare_player_view.py at 70115402 (the v0.0.62 release build): the player view keyed every unit on the
    # whole files prepare_player_view.py and player_inventory_pose.py; its bake code (bake_unit, bake_body and what
    # they run) has the bake-reach digest below.
    ('player-view', '1eeb4b9a9b78f2df602772279ca9a9d280b94bc7f116ca6c518dbbea6a2a78ae'):
        ('9d09ca9cba358b6505d72a56ef908b7913d7002a2703693fe106326711a70d75',),
    # tools/prepare_area.py and tools/chim_room_batches.py at fe90f8ed (the v0.0.62 release build, whose residents and
    # rooms the v0.0.62 release runs reused): the resident and room unit caches keyed every unit on the whole file, so
    # the v0.0.63 edits elsewhere in prepare_area.py re-keyed all of them (UNIT-KEY-WHOLE-FILE-63). Bake reaches:
    # resident-bake = build_resident + publish_resident, interior-room = build_room (prepare_area.py),
    # interior-room-chim = build_shell (chim_room_batches.py).
    ('resident-bake', '4318d4be491911a8a2867bb8873f23a052a1616df08f4151d7344705a13ec576'):
        ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',),
    ('interior-room', '4a4ff8d268a2b8030c1bd8b294aa61c888f734bf66edbbb91e040b370a2c45a2'):
        ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',),
    ('interior-room-chim', '02b87fd3252e52456b3e2688fcc2ce3172853ef735ae43d159ef43f1a9983d49'):
        ('115d5e69098e1c5ffd0cf15e11c4431f326b8767ea01d5f650b0885fa1604b0a',),
}

# AMIWIND_* settings that say where a stage does its work, never what a unit is made of: left out of a unit key
# (as pass_cache.environment leaves out the run's scratch folder). AMIWIND_RESIDENT_WORK (prepare_area
# resident_work_folder) picks the folder the residents are baked in.
WORK_PLACE_SETTINGS = ('AMIWIND_RESIDENT_WORK',)
# (The list of unit caches still keyed on whole files lives in tests/test_unit_store.py, not here: file names written
# in this module would count as files its users' code reads, and so as part of their keys.)


def legacy_sources(name, sources):
    """The older whole-file keys under which units of cache NAME with the bake-reach digest SOURCES were stored."""
    return tuple(LEGACY_SOURCES.get((name, sources), ()))


def bake_keyed_cache(name, options, sources, previous, files, covered=(), neutral=()):
    """The unit cache NAME keyed on SOURCES (the digest of what its workers run), or None when the cache is off.
    OPTIONS as UnitCache.open makes them: the caller's options with the AMIWIND_* settings that FILES read, less the
    NEUTRAL ones (WORK_PLACE_SETTINGS); PREVIOUS: older key forms (pass_cache.previous_digests) with the
    LEGACY_SOURCES keys added."""
    import pass_cache
    root = pass_cache.folder()
    if root is None:
        return None
    environment = pass_cache.environment(*files)
    for setting in neutral:
        environment.pop(setting, None)
    return pass_cache.UnitCache(name, dict(options, environment=environment), sources, root,
                                previous=tuple(previous) + legacy_sources(name, sources), covered=covered)


class Failed:
    """A unit's error, returned by timed() instead of raised (picklable: the message only)."""

    def __init__(self, message):
        self.message = message


def timed(work):
    """Pool worker: WORK (index, function, task) -> (index, seconds, function(task) or Failed)."""
    index, function, task = work
    began = time.monotonic()
    try:
        result = function(task)
    except Exception as error:   # collected: run_each names every failed unit after keeping the rest
        result = Failed('%s: %s' % (type(error).__name__, error))
    return index, round(time.monotonic() - began, 3), result


def timed_raising(call, work):
    """Pool worker: WORK (index, task) -> (index, seconds, call(task)); an error is raised as call raised it (the CHIM
    units: chim.units.run_units stores every unit that came back before it, then the map ends with that error)."""
    index, task = work
    began = time.monotonic()
    value = call(task)
    return index, round(time.monotonic() - began, 3), value


def completed_units(call, items, jobs):
    """(index, seconds, call(task)) for ITEMS [(index, task)] as each comes back from the worker pool
    (build_parallel.completed_map); the first error ends the map, after every unit handed back before it."""
    from functools import partial
    from build_parallel import completed_map
    return completed_map(partial(timed_raising, call), items, jobs)


def progress_line(label, done, total, name, seconds, failed=False):
    """'LABEL [done/total] NAME 41m12s' ('... FAILED 41m12s'): one short line per unit as it comes back, so the log
    always says how far a stage is (the maintainer asked for an X of Y next to every step, concise)."""
    minutes, rest = divmod(int(round(seconds)), 60)
    took = '%dm%02ds' % (minutes, rest) if minutes else '%ds' % rest
    return '%s [%d/%d] %s %s%s' % (label, done, total, name, 'FAILED ' if failed else '', took)


def stored(cache, inputs, row, contents):
    """Store a unit (UnitCache.store_files) and read its entry back: True when the record and every file are there
    with their SHA-256 (UNIT-CACHE-STORE-ERRORS-SILENT-63: a store never raises, so a folder the build cannot write,
    made by another user, lost every unit without a word). The read-back looks at the files only: it is no lookup, so
    it counts no hit and records no reuse."""
    import hashlib
    import json
    from pass_cache import input_digest
    cache.store_files(inputs, row, contents)
    meta, _ = cache._paths(input_digest(inputs))
    try:
        record = json.loads(meta.read_text(encoding='utf-8'))
        files = record['row']['files']
        if record.get('input_sha256') != input_digest(inputs) or set(files) != set(contents):
            return False
        return all(hashlib.sha256(cache._blob(digest).read_bytes()).hexdigest() == digest ==
                   hashlib.sha256(contents[name]).hexdigest() for name, digest in files.items())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def unwritable_folders(root, user=None):
    """The folders of the unit and pass cache ROOT (each cache's folder and its two-letter and files folders) this
    process cannot write: a build run as the build user stops on them in its first minute instead of losing every
    unit it makes (UNIT-CACHE-STORE-ERRORS-SILENT-63: a seed run as root left a cache folder the builds could not
    write). Missing folders are fine (made when first needed)."""
    import os
    from pathlib import Path
    root = Path(root)
    if not root.is_dir():
        return []
    out = [] if os.access(root, os.W_OK | os.X_OK) else [str(root)]
    for cache in sorted(p for p in root.iterdir() if p.is_dir()):
        folders = [cache] + [p for p in cache.iterdir() if p.is_dir()]
        folders += [p for p in (cache / 'files').iterdir() if p.is_dir()] if (cache / 'files').is_dir() else []
        out += [str(p) for p in folders if not os.access(p, os.W_OK | os.X_OK)]
    return out


def run_each(costs, function, items, names, jobs, keep, fallback=None, label=None, already=0, log=print):
    """Run FUNCTION(task) for ITEMS [(index, task)] on the worker pool, longest first by the cost history COSTS (or
    FALLBACK(name) seconds), and call KEEP(index, result) for each unit the moment it is back. NAMES: one stable name
    per item. LABEL: print '[done/total]' for every unit as it comes back, ALREADY units counted done before (taken
    from the unit cache). Returns ['name: error'] of the units that failed (empty when all passed).
    A KEEP that returns False (its store was not found again, stored()) gets a loud line at once; when the map has
    ended, the count ('K stores FAILED') is printed and the stage fails (UNIT-CACHE-STORE-ERRORS-SILENT-63)."""
    from build_costs import estimator, record
    from build_parallel import completed_map
    names = [str(n) for n in names]
    if len(names) != len(items):
        raise ValueError('run_each needs one name per item')
    total = already + len(items)
    if label:
        log('%s [%d/%d] cached, %d to make' % (label, already, total, len(items)), flush=True)
    by_index = {index: name for (index, _), name in zip(items, names)}
    estimate = estimator(costs, names, fallback)
    cost = None if estimate is None else (lambda work: estimate(by_index[work[0]]))
    seconds, failed, lost = {}, [], []
    try:
        for index, took, result in completed_map(timed, [(index, function, task) for index, task in items], jobs,
                                                 cost=cost):
            seconds[index] = took
            if label:
                log(progress_line(label, already + len(seconds), total, by_index[index], took,
                                  isinstance(result, Failed)), flush=True)
            if isinstance(result, Failed):
                failed.append('%s: %s' % (by_index[index], result.message))
                continue
            if keep(index, result) is False:
                lost.append(by_index[index])
                log('!! %s: STORE FAILED: %s is not in the unit cache after it was stored (is the cache folder '
                    'writable by this user?)' % (label or costs, by_index[index]), flush=True)
    finally:
        record(costs, [by_index[index] for index in seconds], [seconds[index] for index in seconds])
    if lost:
        log('!! %s: %d stores FAILED (%s)' % (label or costs, len(lost), ', '.join(lost[:8])), flush=True)
        raise RuntimeError('%s: %d stores FAILED: the unit cache did not keep %s; every unit made here would be made '
                           'again by the next build (UNIT-CACHE-STORE-ERRORS-SILENT-63)'
                           % (label or costs, len(lost), ', '.join(lost[:8])))
    return failed
