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
}


def legacy_sources(name, sources):
    """The older whole-file keys under which units of cache NAME with the bake-reach digest SOURCES were stored."""
    return tuple(LEGACY_SOURCES.get((name, sources), ()))


def bake_keyed_cache(name, options, sources, previous, files, covered=()):
    """The unit cache NAME keyed on SOURCES (the digest of what its workers run), or None when the cache is off.
    OPTIONS as UnitCache.open makes them: the caller's options with the AMIWIND_* settings that FILES read; PREVIOUS:
    older key forms (pass_cache.previous_digests) with the LEGACY_SOURCES keys added."""
    import pass_cache
    root = pass_cache.folder()
    if root is None:
        return None
    return pass_cache.UnitCache(name, dict(options, environment=pass_cache.environment(*files)), sources, root,
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


def progress_line(label, done, total, name, seconds, failed=False):
    """'LABEL [done/total] NAME 41m12s' ('... FAILED 41m12s'): one short line per unit as it comes back, so the log
    always says how far a stage is (the maintainer asked for an X of Y next to every step, concise)."""
    minutes, rest = divmod(int(round(seconds)), 60)
    took = '%dm%02ds' % (minutes, rest) if minutes else '%ds' % rest
    return '%s [%d/%d] %s %s%s' % (label, done, total, name, 'FAILED ' if failed else '', took)


def run_each(costs, function, items, names, jobs, keep, fallback=None, label=None, already=0, log=print):
    """Run FUNCTION(task) for ITEMS [(index, task)] on the worker pool, longest first by the cost history COSTS (or
    FALLBACK(name) seconds), and call KEEP(index, result) for each unit the moment it is back. NAMES: one stable name
    per item. LABEL: print '[done/total]' for every unit as it comes back, ALREADY units counted done before (taken
    from the unit cache). Returns ['name: error'] of the units that failed (empty when all passed)."""
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
    seconds, failed = {}, []
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
            keep(index, result)
    finally:
        record(costs, [by_index[index] for index in seconds], [seconds[index] for index in seconds])
    return failed
