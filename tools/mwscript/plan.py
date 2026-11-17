# SPDX-License-Identifier: GPL-3.0-only
"""The script engine's table sizes, counted from the game (EXPANSION-SCRIPT-LIMITS-66; MWVM-INSTANCES-256-66,
MWVM-PARKING-STORE-SMALL-66).

The interpreter (engine/aga/src/aw_mwvm.c) keeps four tables: the attached instances (the loaded map's scripted
objects plus the global scripts that run), their local values, the parked objects (an object's values while its map
is not loaded) and the parked values. Up to v0.0.66-dev11 they were constants (256 instances, 4,096 values, 2,816
parked objects, 9,216 parked values): a map with more scripted objects left the rest without their scripts, and a
long game lost values once the store was full. OpenMW keeps a reference's locals with the reference
(apps/openmw/mwworld/refdata.hpp:48 MWScript::Locals mLocals; refdata.cpp:203-207 setLocals) and its local scripts
in a list with no bound (mwworld/localscripts.cpp:96-121 add, :123-132 addCell), so nothing is dropped. Here the
builder counts what the whole game can need, every master included, writes the counts into the file (CONF, awms.py)
and the engine allocates exactly that at load; a count ever past the plan stops the game with a clear message at the
map change instead of dropping a script or a value.

What is counted (the loaded map is a 3 by 3 block of exterior cells, the activation range being one and a half cells,
or one interior; aw_mwhost.c attach_map):
- instances: the busiest map's scripted placements, its held items (at most HELD_MAX a map, the host's rule), and the
  levelled-list placements there that can give a scripted actor (one spawn a placement); plus every global script
  that can have an instance at once (the start scripts, every script a StartScript names, the new game's run-once
  scripts, the carried items' scripts, the scripts whose variables another script names), the copies the scripts'
  Place calls can make (PLACE_COPIES a row, the host's most for one call) and the two scratch instances (a dialogue
  result's run, the console's line);
- cells: the local values of the same;
- parked: every bound object whose script has a local value (all masters: the expansions' placements are counted
  although a base-game image binds only Vvardenfell's), the carried items' scripts with values, the levelled-list
  placements that can give a scripted actor with values, and the Place copies with values;
- park_cells: their values.
Objects whose script has no local value are not parked (nothing to keep; OpenMW's RefData::setLocals leaves such a
reference's locals empty too), so the parked rows count only objects with values.
"""
from collections import defaultdict

from .awms import pcadd_rows, levelled_actor_rows

HELD_MAX = 32            # held items attached per map (aw_mwhost.c HELD_MAX)
PLACE_COPIES = 16        # the most copies one Place call makes (aw_mwhost.c PLACE_COPIES)
# the live script-made copies planned per Place row: the game's calls ask for one copy at a time, and a deleted copy's
# values are forgotten with it (aw_mwhost.c deleted_script), so few live at once; past this the one Place call's script
# is refused with a console line and counted (never a stop: the plan's own objects are not involved)
PLANNED_COPIES = 4
SCRATCH_INSTANCES = 2    # a dialogue result's run on an unattached speaker, the console's line
# The engine's hard maxima (aw_mwvm.h AW_MWVM_*_MAX): a plan past one is refused by the builder (check_limits), as the
# interpreter would refuse the file. tests/test_mwvm_limits_native.py keeps them equal.
ENGINE_MAX_INSTANCES = 4096
ENGINE_MAX_CELLS = 65535
ENGINE_MAX_PARKED = 32768
ENGINE_MAX_PARK_CELLS = 65535


def block_of(cell):
    """The loaded map a binding's cell belongs to: an interior by its number, an exterior cell by its grid."""
    return ('room', cell) if not isinstance(cell, tuple) else ('cell', cell)


def plan(program, compiled, binds, data=None):
    """{'instances', 'cells', 'parked', 'park_cells', 'report'} for the file written from PROGRAM, COMPILED and the
    bindings BINDS (every master's: compiler.bindings(program, compiled, addons=...)). DATA: the game data, for the
    levelled lists (None: program.data)."""
    data = data if data is not None else program.data
    nloc = [c.nlocals for c in compiled]
    # the scripted actors a levelled list can give, and the lists that can give one (with values)
    lact_scripts = {s for _, s in levelled_actor_rows(program)}
    actor_script = {}
    for ident, (tag, script) in (getattr(data, 'bases', None) or {}).items():
        if tag in ('CREA', 'NPC_') and script and script in program.scripts.index:
            actor_script[ident] = program.scripts.index[script]
    list_locals = {}                 # folded list id -> the most locals of a scripted actor it can give (-1 none)
    for lid, names in (getattr(data, 'levelled_lists', None) or {}).items():
        best = -1
        for n in names:
            s = actor_script.get(n)
            if s is not None and s in lact_scripts:
                best = max(best, nloc[s])
        if best >= 0:
            list_locals[lid] = best
    # placements of those lists, per map (every master)
    levelled = defaultdict(list)     # block -> [locals of the actor it can give]
    placed_lists = []
    for lid, refs in (getattr(data, 'object_refs', None) or {}).items():
        if lid in list_locals:
            placed_lists += [lid] * len(refs)
    for r in getattr(data, '_placed_addon', None) or ():
        if r['id'].casefold() in list_locals:
            placed_lists.append(r['id'].casefold())
    # where each levelled placement stands: the Morrowind.esm ones through data.placements (actors and objects that
    # events.py keeps) are not listed by type, so the per-map count takes every list placement as the worst map's:
    # the lists stand in the wild, the busiest map is a town; the sum is a few hundred (the report says how many)
    lev_rows = len(placed_lists)
    lev_values = sum(list_locals[lid] for lid in placed_lists)
    lev_max_locals = max(list_locals.values()) if list_locals else 0
    # per map: placements, held items, their values
    maps = defaultdict(lambda: {'placed': 0, 'held': 0, 'values': 0, 'held_values': []})
    ext = defaultdict(list)
    for b in binds:
        if isinstance(b['cell'], tuple):
            ext[b['cell']].append(b)
        else:
            m = maps[('room', b['cell'])]
            if b['flags'] & 8:
                m['held'] += 1
                m['held_values'].append(nloc[b['script']])
            else:
                m['placed'] += 1
                m['values'] += nloc[b['script']]
    for (gx, gy) in list(ext.keys()):
        m = maps[('cell', (gx, gy))]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for b in ext.get((gx + dx, gy + dy), []):
                    if b['flags'] & 8:
                        m['held'] += 1
                        m['held_values'].append(nloc[b['script']])
                    else:
                        m['placed'] += 1
                        m['values'] += nloc[b['script']]
    busiest = {'key': None, 'instances': 0, 'cells': 0}
    for key, m in maps.items():
        held = min(m['held'], HELD_MAX)
        held_values = sum(sorted(m['held_values'], reverse=True)[:held])
        inst = m['placed'] + held
        cells = m['values'] + held_values
        if inst > busiest['instances'] or (inst == busiest['instances'] and cells > busiest['cells']):
            busiest = {'key': key, 'instances': inst, 'cells': cells, 'placed': m['placed'], 'held': held}
    # the global scripts that can have an instance at once
    from .codegen import SCRIPT_START, SCRIPT_GLOBAL
    starts = {i for i, c in enumerate(compiled) if c.flags & (SCRIPT_START | SCRIPT_GLOBAL)}
    newg = {program.scripts.index[s] for s in getattr(data, 'new_game', []) if s in program.scripts.index}
    carried = {s for _, s, _ in pcadd_rows(program)}
    named = {r['script'] for r in program.objects.rows if r['kind'] == 'script' and r['script'] is not None}
    global_set = starts | newg | carried | named
    global_cells = sum(nloc[i] for i in global_set)
    # the copies the Place calls can make
    places = program.place_rows() if hasattr(program, 'place_rows') else []
    place_scripts = [r['script'] for r in places if r['script'] != 0xFFFF]
    copies = PLANNED_COPIES * len(place_scripts)
    copy_cells = PLANNED_COPIES * sum(nloc[s] for s in place_scripts)
    copies_with_values = PLANNED_COPIES * sum(1 for s in place_scripts if nloc[s])
    max_locals = max(nloc) if nloc else 0
    instances = busiest['instances'] + lev_rows_in_a_map(lev_rows) + len(global_set) + copies + SCRATCH_INSTANCES
    cells = busiest['cells'] + lev_rows_in_a_map(lev_rows) * lev_max_locals + global_cells + copy_cells + max_locals
    with_values = [b for b in binds if nloc[b['script']]]
    parked = len(with_values) + sum(1 for s in carried if nloc[s]) + sum(1 for lid in placed_lists if list_locals[lid]) \
        + copies_with_values
    park_cells = sum(nloc[b['script']] for b in with_values) + sum(nloc[s] for s in carried) + lev_values + copy_cells
    report = {'busiest_map': {'map': list(busiest['key']) if isinstance(busiest['key'], tuple) and
                              isinstance(busiest['key'][1], tuple) else busiest['key'],
                              'placed': busiest.get('placed', 0), 'held': busiest.get('held', 0),
                              'values': busiest['cells']},
              'maps_with_scripts': len(maps),
              'global_scripts': {'start_or_started': len(starts), 'new_game': len(newg), 'carried': len(carried),
                                 'named': len(named), 'distinct': len(global_set), 'values': global_cells},
              'levelled': {'placements': lev_rows, 'in_one_map_allowance': lev_rows_in_a_map(lev_rows),
                           'values': lev_values, 'max_locals': lev_max_locals},
              'place_copies': {'rows': len(place_scripts), 'copies': copies, 'values': copy_cells},
              'bound': {'rows': len(binds), 'with_values': len(with_values),
                        'values': sum(nloc[b['script']] for b in with_values)},
              'max_locals': max_locals}
    out = {'instances': instances, 'cells': cells, 'parked': parked, 'park_cells': park_cells, 'report': report}
    check_plan(out)
    return out


def lev_rows_in_a_map(total):
    """The levelled-list placements one loaded map can spawn at once: the busiest 3 by 3 block of Vvardenfell's wilds
    holds a few dozen (the lists stand one or two a cell); 64 covers it, never more than the game has."""
    return min(total, 64)


def check_plan(p):
    """Raise ValueError when the engine would refuse this plan (aw_mwvm.h AW_MWVM_*_MAX)."""
    for key, limit in (('instances', ENGINE_MAX_INSTANCES), ('cells', ENGINE_MAX_CELLS), ('parked', ENGINE_MAX_PARKED),
                       ('park_cells', ENGINE_MAX_PARK_CELLS)):
        if p[key] > limit:
            raise ValueError('%d %s: the engine takes at most %d (the interpreter refuses more)' % (p[key], key, limit))
        if p[key] < 0:
            raise ValueError('%s: a negative count' % key)
