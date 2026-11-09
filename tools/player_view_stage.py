# SPDX-License-Identifier: GPL-3.0-only
"""The player view as its own early build stage (BUILD-RISKY-STAGES-FIRST-63).

The player bodies are the riskiest bake of a build (the v0.0.62 final build stopped twice on a player body, after 1 h
13 min and 5 h, in the last step) and need nothing of the world: the game data and the census palette. This stage
bakes every player-view unit into the image unit cache right after the census, beside the world stages, so a body
that does not fit fails in the first hour of a build, not in its last step; the image step then takes all of them
from the unit cache (the units, their keys and their bytes are the image's own: prepare_player_view.prepare).

First, in seconds, the pre-flight: every unit already in the unit cache is checked against the engine's model limits
(bytes, frames, vertices, triangles), all of them, and the step stops with the whole list when any is over
(collect-then-fail), before anything is baked.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# the engine's limits for a player model (engine/aga/src/r_local.h MAXALIASVERTS, gl_model.h MAXALIASTRIS and
# MAXALIASFRAMES; tools/npc_anim.py ALIAS_BYTE_BUDGET, the alias staging limit); tests/test_risky_stages_first.py
# keeps them equal to the headers
LIMITS = {'bytes': 512 * 1024, 'frames': 256, 'vertices': 3072, 'triangles': 2048}


def over_limits(name, row):
    """['NAME: field N over its limit L', ...] for one unit report row."""
    found = []
    for field, limit in LIMITS.items():
        value = row.get(field)
        if isinstance(value, (int, float)) and value > limit:
            found.append('%s: %s %d over its limit %d' % (name, field, value, limit))
    return found


def preflight(tasks, swim_tasks, cache, log=print):
    """Check every player-view unit the unit cache holds against LIMITS. Returns (checked, to bake, problems)."""
    import prepare_player_view as view
    units = [('body', t) for t in tasks] + [('swim', t) for t in swim_tasks] + [('inventory', t) for t in tasks]
    checked, missing, problems = 0, 0, []
    bodies = {}
    for unit in units:
        found = None if cache is None else cache.load_unit(view.unit_inputs(unit))
        if found is None:
            missing += 1
            continue
        result = view.unpack_result(*found)
        row = result[-1]
        checked += 1
        problems += over_limits(view.unit_name(unit), row)
        if unit[0] == 'body':
            bodies[(unit[1][2], unit[1][3])] = row
    for (race, female), row in sorted(bodies.items()):
        data, palette = tasks[0][0], tasks[0][1]
        torch = ('torch', (data, palette, race, female, {k: v for k, v in row.items() if k != '_item_tags'}))
        found = None if cache is None else cache.load_unit(view.unit_inputs(torch))
        if found is None:
            missing += 1
            continue
        checked += 1
        problems += over_limits(view.unit_name(torch), view.unpack_result(*found)[-1])
    missing += len(tasks) - len(bodies)      # the torch bodies of the bodies still to bake
    log('Player view pre-flight: %d units in the unit cache checked against the model limits (%s), %d to bake, '
        '%d over a limit' % (checked, ', '.join('%s %d' % kv for kv in LIMITS.items()), missing, len(problems)),
        flush=True)
    for line in problems:
        log('  OVER: ' + line, flush=True)
    return checked, missing, problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True, help='the census palette (intro-scene/id1/gfx/palette.lmp)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=None)
    a = p.parse_args(argv)
    import prepare_player_view as view
    from mwad.paths import resolve_data_files
    started = time.monotonic()
    print('=== PHASE 1/2: player view pre-flight (the stored models against the limits) ===', flush=True)
    data = resolve_data_files(a.data_files)
    kinds, _, _ = view._sources(data)
    palette = a.palette.read_bytes()
    races = view.playable_races(kinds)
    tasks = [(str(data), palette, race, female) for race in races for female in (False, True)]
    swim_tasks = [task + ({'model': view.body_path(task[2], task[3])},) for task in tasks]
    cache = view._unit_cache()
    a.out.mkdir(parents=True, exist_ok=True)
    if cache is None:
        # without the unit cache the image step could not take the units from here: it bakes them itself
        print('Player view stage: the unit cache is off (or no input lock): nothing baked here, the image step '
              'bakes the player view', flush=True)
        (a.out / 'player-view.json').write_text(json.dumps({'cache': 'off', 'baked': 0}) + '\n', encoding='utf-8',
                                                newline='\n')
        return 0
    checked, missing, problems = preflight(tasks, swim_tasks, cache)
    if problems:
        print('Player view pre-flight FAILED: %d stored models over a limit (listed above); nothing baked'
              % len(problems), flush=True)
        return 1
    print('=== PHASE 2/2: player view units (%d to bake; the image step takes them from the unit cache) ==='
          % missing, flush=True)
    if a.out.exists():
        shutil.rmtree(a.out)
    id1 = a.out / 'id1'
    (id1 / 'gfx').mkdir(parents=True)
    shutil.copyfile(a.palette, id1 / 'gfx/palette.lmp')
    report = view.prepare(data, id1, jobs=a.jobs)
    report['preflight'] = {'checked': checked, 'to_bake': missing, 'over_limits': problems,
                           'limits': LIMITS, 'cache': 'off' if cache is None else view.UNIT_CACHE}
    (a.out / 'player-view.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Player view stage: done in %.1f s' % (time.monotonic() - started), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
