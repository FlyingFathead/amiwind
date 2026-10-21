#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The image step's stair walk on every core (BUILD-IMAGE-STAIR-WALK-SERIAL-36).

tools/stair_walk.py check hands the worker pool one whole map per task, so one heavy map (a room whose
standing hull is a long routed chain: the Vivec Arena Pit walked 2,057 steps and ramps in 808 s) keeps one
core busy while the rest of the pool has finished. Here every map that is walked is split into units: a
slice of its candidate steps and ramps (stair_walk.candidates, in their order). The units of all maps go
to the pool together, largest first; each unit walks its slice on the map's own collision with the same
code (stair_walk._check_items), and a map's rows are its units' rows put back in order: byte for byte the
rows of the whole-map walk (stair_walk.check_map), so the report and the stored records are the same as
with stair_walk.check.

Records: one per map, keyed exactly as stair_walk.check keys them (SHA-256 of the map's bytes and its core,
in the 'stair-walk' pass cache whose sources are the walk's workers, stair_walk.walk_key_sources: check_map and
walk_unit with what they reach): an unchanged map is never walked again, and the orchestration here, the
progress counter and the records are not part of any walk's key (BUILD-STAIR-KEY-BOOKKEEPING-36).

stair_walk.check (one map per task) stays as the reference method; tests compare the two.
"""
import json
import os
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

UNITS_PER_WORKER = 16   # units handed out per worker: the slowest unit bounds the pass's tail
UNIT_MIN = 16           # steps and ramps per unit at least (each unit reads the map and builds its scenes)
UNIT_MAX = 128          # and at most: a heavy room walks 0.4 s per step (the Arena Pit), so a unit stays under a minute
UNIT_MIN_HEAVY = 4      # a heavy map's units may be this short (BUILD-IMAGE-STAIR-WALK-CORES-43: 128-step units of a
                        # room walking about a second a step ran alone for minutes at the end of the pass)
COST_POOL = 'image-stair-walk'   # cost history (build_costs): map name -> seconds its walk took
_SCENES = {}            # per worker process: the last maps' polygons, candidates and scenes (units of one map come in a row)
_SCENES_KEPT = 2


def _read_items(path, core, scope):
    import stair_walk as sw
    raw = Path(path).read_bytes()
    polys = sw._faces(raw)
    items = sw.candidates(polys, core)
    if scope == 'flights':
        items = sw.flight_items(items)
    return raw, polys, items


def plan_map(task):
    """Worker: how a map is taken. TASK (path, core, models, cache, scope, again). Returns (action, count,
    stored rows or None, provenance or None): 'reused' (a record checked by a passed master build; its rows),
    'walk' (count candidates to walk; a sampled reused map also carries its stored rows to compare)."""
    import hashlib
    import stair_walk as sw
    path, core, models, cache, scope, again = task
    name = Path(path).stem
    stored = origin = None
    if cache is not None:
        import stair_records
        raw = Path(path).read_bytes()
        key = hashlib.sha256(raw).hexdigest() + ':' + json.dumps(core)
        record, mark = stair_records.lookup(cache, key)
        if record is None or mark is None:
            record, mark = sw.flight_rows_of_all_walk(cache, key, record, mark)
        if record is not None and mark is not None:
            # same keys in the same order; only the map name is this map's (aliases share bytes)
            stored = [{k: (name if k == 'map' else v) for k, v in row.items()} for row in record['rows']]
            origin = stair_records.provenance(mark)
            if not again:
                return 'reused', len(stored), stored, origin
    _, _, items = _read_items(path, core, scope)
    return 'walk', len(items), stored, origin


def walk_unit(task):
    """Worker: rows of the candidates START..STOP of one map (stair_walk.check_map on a slice).
    TASK (path, core, models, scope, start, stop)."""
    import stair_walk as sw
    from audit_walkability import Scene
    path, core, models, scope, start, stop = task
    import hashlib
    raw = Path(path).read_bytes()
    key = (hashlib.sha256(raw).hexdigest(), json.dumps(core), scope)   # the map's content, never its name
    if key not in _SCENES:
        # the map parsed once per worker for its units in a row (the scenes are read-only: the same rows)
        polys = sw._faces(raw)
        items = sw.candidates(polys, core)
        if scope == 'flights':
            items = sw.flight_items(items)
        try:
            world = Scene(raw, hull=0)
        except ValueError as error:     # name the map (BUILD-STAIR-WALK-UNNAMED-MAP-36)
            raise ValueError('%s (sha256 %s): %s' % (path, key[0], error)) from error
        while len(_SCENES) >= _SCENES_KEPT:
            _SCENES.pop(next(iter(_SCENES)))
        _SCENES[key] = (polys, items, sw.Collision(raw), lambda p, w=world: sw._contents(w, p), sw.Collision(raw, hull=0))
    polys, items, scene, contents, proxy = _SCENES[key]
    # copies: _check_items takes keys out of its items
    items = [dict(item) for item in items[start:stop]]
    if not items:
        return []
    rows = sw._check_items(items, polys, scene, contents, proxy)
    for row in rows:
        row['map'] = Path(path).stem
        row['model'] = models.get(str(row['ref']), '')
    return rows


def unit_size(total, workers):
    """Steps and ramps per unit: about UNITS_PER_WORKER units per worker over the whole walk."""
    return min(UNIT_MAX, max(UNIT_MIN, int(math.ceil(total / float(max(1, workers) * UNITS_PER_WORKER)))))


def plan_units(maps, workers, total_steps):
    """[(map index, start, stop, cost)] of the maps to walk, MAPS [(index, count, cost)] where cost is the map's
    estimated walk (seconds from the cost history, else the fallback measure on the same scale). Every map is cut
    into units of unit_size steps, and a heavy map (its cost per step high) into shorter ones, so no unit costs much
    more than the pass's total over UNITS_PER_WORKER units per worker: a heavy map's units no longer run alone at
    the end of the pass (BUILD-IMAGE-STAIR-WALK-CORES-43). A unit's cost is its share of the map's cost."""
    base = unit_size(total_steps, workers)
    total = sum(cost for _, count, cost in maps if count)
    target = total / float(max(1, workers) * UNITS_PER_WORKER) if total else 0.0
    units = []
    for index, count, cost in maps:
        per_step = cost / float(count) if count else 0.0
        size = base
        if target > 0 and per_step * size > target:
            size = max(UNIT_MIN_HEAVY, int(target // per_step) if per_step else base)
        for start, stop in split(count, size):
            units.append((index, start, stop, per_step * (stop - start)))
    return units


def split(count, size):
    """(start, stop) slices of COUNT candidates, at most SIZE each, in order."""
    return [(start, min(count, start + size)) for start in range(0, count, size)] or [(0, 0)]


def check(id1, jobs=1, only=None, models=None, exempt=(), scope=None):
    """stair_walk.check, with each walked map split into units over the worker pool (same report)."""
    import hashlib
    import stair_walk as sw
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache
    import progress_line
    started = time.monotonic()
    scope = scope or sw.scope_setting()
    if scope not in sw.SCOPES:
        raise ValueError('Stair walk scope must be one of %s, not %r' % (', '.join(sw.SCOPES), scope))
    # a targeted walk (--stair-walk-places): only the maps its places name, nothing reused or stored; the watch list:
    # its maps walked again every build (chim.collision watch list, BUILD-STAIR-WALK-SCOPE-KEY-46)
    from chim.collision import PLACES_ENV, load_watch, parse_places, watched_maps
    places = parse_places(os.environ.get(PLACES_ENV, ''))
    if places is not None:
        named = set(watched_maps(places))
        only = [name for name in named if not only or name in only]
        print('Stair walk: TARGETED walk (--stair-walk-places): maps %s only; rows reported, never stored'
              % (', '.join(sorted(only)) or 'none'), flush=True)
    tasks = sw.map_tasks(id1, models, only) if places is None or only else []
    sw.hull_preflight(tasks)
    options = {'stair_mode': stair_mode(), 'models': hashlib.sha256(
        json.dumps(models or {}, sort_keys=True).encode()).hexdigest()}
    if scope != 'all':
        options['scope'] = scope
    # the walker's records: the same cache and key as stair_walk.check (sources: the walker module)
    cache = (PassCache.open('stair-walk', options, *sw.walk_key_sources())
             if sw.walk_cache_mode() != 'full' and places is None else None)
    sample = set(sw.pick_sample([t[0] for t in tasks], sw.walk_sample(), 'legacy:%d' % len(tasks))) if cache else set()
    watched = watched_maps(load_watch()) if cache else {}
    watch_paths = {t[0] for t in tasks if Path(t[0]).stem in watched}
    if watch_paths:
        print('Stair walk: watch list: %d maps walked again: %s' % (len(watch_paths), ', '.join(
            '%s (%s)' % (Path(p).stem, ', '.join(watched[Path(p).stem])) for p in sorted(watch_paths))), flush=True)
    sample |= watch_paths
    workers = max(1, resolve_jobs(jobs))
    work = [(*task, cache, scope, task[0] in sample) for task in tasks]
    plans = list(ordered_map(plan_map, work, max(1, min(workers, len(tasks) or 1)), cost=sw._map_cost))
    walk_total = sum(count for action, count, _, _ in plans if action == 'walk')
    stairs_total = sum(count for _, count, _, _ in plans)
    print('Stair walk: %d steps and ramps to check or reuse in %d maps' % (stairs_total, len(tasks)), flush=True)
    size = unit_size(walk_total, workers)
    # each map's walk estimated in seconds by the cost history of earlier builds (build_costs, map name -> seconds),
    # else by its size times its steps (the measure before v0.0.44), scaled to seconds by the maps that have both
    import build_costs
    sizes = {t[0]: sw._map_cost(t) for t in tasks}
    walking = [i for i, plan in enumerate(plans) if plan[0] == 'walk']
    names = [Path(tasks[i][0]).stem for i in walking]
    measure = {Path(tasks[i][0]).stem: float(max(1, sizes[tasks[i][0]]) * max(1, plans[i][1])) for i in walking}
    estimate = build_costs.estimator(COST_POOL, names, lambda name: measure[name]) if names else None
    known = sum(1 for name in names if name in build_costs.load(COST_POOL)) if names else 0
    planned = plan_units([(i, plans[i][1], estimate(Path(tasks[i][0]).stem)) for i in walking], workers, walk_total)
    units, owner, unit_cost = [], [], []
    for index, start, stop, cost in planned:
        path, core, models_ = tasks[index][0], tasks[index][1], tasks[index][2]
        units.append((path, core, models_, scope, start, stop))
        owner.append(index)
        unit_cost.append(cost)
    walked_maps = len(set(owner))
    print('Stair walk: %d maps reused, %d maps to walk (%d steps and ramps) in %d units of up to %d on %d workers '
          '(largest first by %s; heavy maps in shorter units, %d units under %d steps)'
          % (len(tasks) - walked_maps, walked_maps, walk_total, len(units), size, workers,
             'the walk times of %d of %d maps in earlier builds' % (known, len(names)) if known
             else 'map size x steps (no walk times recorded yet)',
             sum(1 for u in units if 0 < u[5] - u[4] < min(size, UNIT_MIN)), min(size, UNIT_MIN)), flush=True)
    cost_of = {id(u): c for u, c in zip(units, unit_cost)}
    # largest first: the slice length times the map's size (heavy rooms have long hull chains); rows come back in
    # unit order, so a map's units arrive in order and the map is complete at its last unit
    rows_of = {i: list(plan[2]) for i, plan in enumerate(plans) if plan[0] == 'reused'}
    how, stored, pending, done_maps, stairs_done = {}, {}, {}, 0, 0
    for i, plan in enumerate(plans):
        if plan[0] == 'reused':
            how[i] = plan[3]
            done_maps += 1
            stairs_done += plan[1]
    last = {i: k for k, i in enumerate(owner)}
    try:
        timings = []
        for k, found in enumerate(ordered_map(walk_unit, units, max(1, min(workers, len(units) or 1)),
                                              cost=lambda u: cost_of[id(u)], timings=timings)):
            i = owner[k]
            pending.setdefault(i, []).extend(found)
            if last[i] != k:
                continue
            path, core = tasks[i][0], tasks[i][1]
            name = Path(path).stem
            rows = pending.pop(i)
            action, count, saved, origin = plans[i]
            if cache is not None:
                rows = json.loads(json.dumps(rows))   # the form stored rows have
                if saved is not None:
                    # a sampled reused map: walked again, must equal its stored rows
                    if sw.rows_digest(rows) != sw.rows_digest(saved):
                        raise ValueError('Stair walk cache: %s walked again differs from its stored rows: the key '
                                         'does not cover everything the walk reads' % name)
                    rows, how[i] = saved, 'walked again: ' + origin
                else:
                    import cache_provenance
                    import stair_records
                    key = hashlib.sha256(Path(path).read_bytes()).hexdigest() + ':' + json.dumps(core)
                    cache_provenance.name_unit(cache, key, lambda: name,
                                               lambda: [('map bytes', Path(path).read_bytes()), ('core', core)])
                    stored[i] = stair_records.store(cache, key, rows)
                    how[i] = 'walked'
            else:
                how[i] = 'walked'
            rows_of[i] = rows
            done_maps += 1
            stairs_done += count
            progress_line.emit('Stair walk', name, '%d steps and ramps, %d failed (%s)' % (
                len(rows), sum(1 for r in rows if r['result'] == 'failed'), how[i]),
                (stairs_done, stairs_total, 'stairs'), (done_maps, len(tasks), 'maps'))
    finally:
        cached = cache.summary() if cache is not None else None
    # this run's walk time of each walked map for the next build's order and unit sizes (never part of a key)
    seconds = {}
    for i, t in zip(owner, timings):
        seconds[i] = seconds.get(i, 0.0) + t
    walked = sorted(seconds)
    build_costs.record(COST_POOL, [Path(tasks[i][0]).stem for i in walked], [seconds[i] for i in walked])
    rows = [r for i in range(len(tasks)) for r in rows_of.get(i, [])]
    exempt = set(exempt)
    failures = [r for r in rows if sw._gating(r) and r['map'] not in exempt]
    exempted = [r for r in rows if sw._gating(r) and r['map'] in exempt]
    advisory = [r for r in rows if r['result'] == 'failed' and not sw._gating(r)]
    summary = {}
    for r in rows:
        kind = 'flight step' if r['kind'] == 'step' and r.get('flight') else r['kind']
        bucket = summary.setdefault(sw.family(r['map']), {}).setdefault(kind, {})
        bucket[r['result']] = bucket.get(r['result'], 0) + 1
    report = dict(format=1, status='failed' if failures else 'passed', maps=len(tasks), step_height=sw.STEP_HEIGHT,
                  walkable_normal_z=sw.WALKABLE_Z, walkable_degrees=round(math.degrees(math.acos(sw.WALKABLE_Z)), 2),
                  reference='Morrowind (OpenMW 0.51): step 8.5 (34 units), slope 46 degrees, authored collision',
                  gate='flights of stairs (3+ steps, 2+ vertical risers) the standing box cannot walk up and down',
                  summary=summary, failures=failures, exempt_failures=exempted, advisory_failures=advisory,
                  rows=rows)
    if scope != 'all':
        report['scope'] = ('flight steps only (release build): ramps and single steps are not walked; '
                           'their advisory findings come from a full walk (development or nightly build)')
    if cached is not None:
        cached['walked_again'] = sorted(Path(p).stem for p in sample)
        cached['maps'] = {Path(tasks[i][0]).stem: how[i] for i in range(len(tasks))}
        cached['stored'] = [stored[i] for i in sorted(stored)]
        report['pass_cache'] = cached
        values = cached['maps'].values()
        reused = sum(1 for v in values if v.startswith('reused'))
        print('Stair walk records: %d maps reused (checked by a passed master build), %d walked, %d walked again '
              'to check the cache.' % (reused, len(cached['maps']) - reused,
                                       sum(1 for v in values if v.startswith('walked again'))), flush=True)
    else:
        print('Stair walk: every map walked (--stair-walk full)', flush=True)
    # the units are bookkeeping (they depend on --jobs): printed, never in the report, which is the same for
    # every worker count
    print('Stair walk: %d maps walked in %d units on %d workers, %d reused, took %.1f s'
          % (walked_maps, len(units), workers, len(tasks) - walked_maps, time.monotonic() - started), flush=True)
    return report


def require(id1, output, jobs=1, only=None, models=None, exempt=(), accepted=None):
    """stair_walk.require on the unit walk (check above)."""
    import stair_walk as sw
    report = sw.accept_known(check(id1, jobs, only, models, exempt), accepted)
    Path(output).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if report['failures']:
        first = report['failures'][0]
        raise ValueError('Stair walkability gate failed: %d flight steps cannot be walked (first %s ref %s at %s, '
                         'rise %s); see %s' % (len(report['failures']), first['map'], first['ref'], first['point'],
                                               first.get('rise'), output))
    return report


def main():
    import argparse
    import stair_walk as sw
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('id1', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--maps', nargs='*')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--scope', choices=sw.SCOPES, help="'flights' (default, or AMIWIND_STAIR_WALK) or 'all'")
    a = parser.parse_args()
    report = check(a.id1, a.jobs, a.maps, scope=a.scope)
    a.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(status=report['status'], summary=report['summary'], failures=len(report['failures']))))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
