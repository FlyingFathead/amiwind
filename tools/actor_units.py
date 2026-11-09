# SPDX-License-Identifier: GPL-3.0-only
"""The actor library's NPC appearances and creature models in the unit cache (NPC-LIBRARY-NO-UNIT-CACHE-63).

The actor library stage baked every NPC appearance (tools/npc_library.py) and every creature and corpse model
(tools/creature_library.py) again whenever the stage was not reused: in the v0.0.63-dev1 build the stages it reads
(the CHIM towns, the census) ran again with other outputs, and the stage re-baked 418 appearances and 57 models whose
own inputs had not changed (2,600-2,750 s each time). Now each unit is kept in the image unit cache
(tools/pass_cache.py UnitCache) the moment its worker returns it (tools/unit_store.py run_each), keyed on:
- its own inputs (the appearance or creature as the bake reads it, the palette by SHA-256);
- the code the bake runs (pass_cache.source_digest of (module, function): npc_library.bake_standing,
  creature_library._unit), written in those modules so the stage key covers what the cache key reads;
- the AMIWIND_* settings that code reads (reach_environment: the settings named in the bake's reach, not the
  whole stage's);
- the game data by the input lock's SHA-256.
Which records the towns place, and so which appearances the stage bakes, is not part of any key.

This module holds the code around the bakes (keys, packing, the run) so that the two library modules keep their bake
reach, and so their unit keys, unchanged: a statement added at a module's top is import-time code and counts in the
reach of every function of that module.
"""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NPC_CACHE = 'npc-appearance'
CREATURE_CACHE = 'creature-model'
FIGHTER_CACHE = 'arena-fighter'
ROOM_ACTOR_CACHE = 'room-actor'
GUARD_SKIP_CACHE = 'guard-torch-skip'
NPC_FALLBACK_SECONDS = 20.0
CREATURE_FALLBACK_SECONDS = 30.0


def reach_environment(*entries):
    """{setting: value or None} of the AMIWIND_* settings the code of ENTRIES ((path, function), the bake's reach)
    can read, less bookkeeping (build_cache IGNORED_ENV) and the run's scratch folder; every AMIWIND_* setting when the
    reach builds names at run time."""
    from build_cache import ENV_ANY, ENV_PREFIX, IGNORED_ENV, SourceIndex, STAGE_TOP_FORMAT
    from build_scratch import ENV as SCRATCH_ENV
    index = SourceIndex(ROOT, top_format=STAGE_TOP_FORMAT)
    keyed = [(Path(path).resolve().relative_to(ROOT.resolve()).as_posix(), function) for path, function in entries]
    _, _, uncertain, names, _ = index.keyed_coverage(keyed)
    if uncertain or ENV_ANY in names:
        names = {key for key in os.environ if key.startswith(ENV_PREFIX)}
    return {key: os.environ.get(key) for key in sorted(names) if key not in IGNORED_ENV and key != SCRATCH_ENV}


def open_cache(name, entries, sources, previous, covered):
    """The unit cache NAME keyed on SOURCES (the bake-reach digest of ENTRIES, computed by the caller), or None: cache
    off, or no input lock naming the game data by SHA-256."""
    import pass_cache
    root = pass_cache.folder()
    game = pass_cache.game_data_digest()
    if root is None or game is None:
        return None
    return pass_cache.UnitCache(name, {'game_data': game, 'environment': reach_environment(*entries)}, sources, root,
                                previous=tuple(previous), covered=covered)


def palette_digest(palette):
    return hashlib.sha256(palette if isinstance(palette, bytes) else Path(palette).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------------
# NPC appearances (tools/npc_library.py build)

def npc_inputs(appearance, key, profile, palette_sha256):
    """What one appearance's standing model depends on besides the game data, the bake code and the settings it reads:
    the appearance as the bake reads it (its id names the face override and the body receipt rows), its library key
    (which holds the head and root settings) and profile, and the palette by SHA-256."""
    return {'entry': {'name': str(appearance.get('id', ''))}, 'key': key, 'profile': profile,
            'appearance': json.loads(json.dumps(appearance, sort_keys=True, default=str)),
            'palette_sha256': palette_sha256}


def pack_npc(result, seconds):
    """(row, {name: bytes}) of a bake_standing result; None when a part is not exact JSON (then not cached)."""
    from pass_cache import json_exact
    raw, layout, sounds, facts = result
    facts = dict(facts)
    table = facts.pop('_table', None)
    files = {'model': raw}
    files.update(('sound/' + name, data) for name, data in sounds.items())
    if table is not None:
        files['table'] = table[1]
    row = {'layout': layout, 'facts': facts, 'sounds': sorted(sounds), 'table': None if table is None else table[0],
           'seconds': round(float(seconds), 2)}
    return (row, files) if json_exact(row) else None


def unpack_npc(row, files):
    """(bake_standing result, seconds) of a row pack_npc stored."""
    facts = dict(row['facts'])
    if row.get('table') is not None:
        facts['_table'] = (row['table'], files['table'])
    return (files['model'], row['layout'], {name: files['sound/' + name] for name in row['sounds']}, facts), \
        row['seconds']


def bake_npc(task):
    """Worker: npc_library.bake_standing(TASK) and the seconds it took (an error is raised; run_each names it)."""
    import time
    import npc_library
    began = time.monotonic()
    result = npc_library.bake_standing(task)
    return result, time.monotonic() - began


def bake_appearances(tasks, names, jobs, cache, inputs, log=print):
    """({key: (result, seconds)}, {key: error}, cached) of TASKS [(key, data, palette, appearance, profile)]: an
    appearance stored for the same inputs (INPUTS(task)) is taken from CACHE (unless --rebuild-unit
    npc-appearance:ID names it); the rest are baked on the worker pool and each is stored the moment it is back.
    NAMES: {key: the record id in the '[d/t]' lines}. A failed appearance is collected with its error."""
    from pass_cache import forced
    done, todo = {}, []
    for task in tasks:
        if cache is not None and not forced(NPC_CACHE, names[task[0]]):
            found = cache.load_unit(inputs(task))
            if found is not None:
                try:
                    done[task[0]] = unpack_npc(*found)
                    continue
                except (KeyError, TypeError, AttributeError, IndexError, ValueError):
                    pass
        todo.append(task)
    cached, errors = len(done), {}
    if todo:
        import unit_store
        unstored = []

        def keep(index, value):
            # in the unit cache the moment the appearance is back (UNIT-STORED-AT-MAP-END-62)
            task = todo[index]
            done[task[0]] = value
            if cache is not None:
                packed = pack_npc(*value)
                if packed is None:
                    unstored.append(names[task[0]])
                else:
                    return unit_store.stored(cache, inputs(task), *packed)
        failed = unit_store.run_each(NPC_CACHE, bake_npc, [(index, task[1:]) for index, task in enumerate(todo)],
                                     [names[task[0]] for task in todo], max(1, jobs), keep,
                                     fallback=lambda name: NPC_FALLBACK_SECONDS, label='NPC library', already=cached,
                                     log=log)
        by_name = {names[task[0]]: task[0] for task in todo}
        for line in failed:
            name = max((n for n in by_name if line.startswith(n + ': ')), key=len)
            errors[by_name[name]] = line[len(name) + 2:]
        if unstored:
            log('NPC library: %d appearances not kept in the unit cache (a part is not exact JSON): %s' % (
                len(unstored), ', '.join(unstored[:8])), flush=True)
    return done, errors, cached


# ---------------------------------------------------------------------------------------------------------------------
# Creature and corpse models (tools/creature_library.py bake)

def creature_name(task):
    """A model's stable name: its library key (the mesh, '@scale', or the corpse key)."""
    import creature_library as L
    method, _, _, app, _, scale = task
    return L.corpse_key(app['mesh']) if method == 'corpse' else L.variant_key(app['mesh'], scale)


def creature_inputs(task, palette_sha256):
    """What one model depends on besides the game data, the bake code and the settings it reads: the method, the
    creature (id, mesh), two-legged or not, the scale and the palette by SHA-256."""
    method, _, _, app, bipedal, scale = task
    return {'entry': {'name': creature_name(task)}, 'method': method,
            'app': json.loads(json.dumps(app, sort_keys=True, default=str)), 'bipedal': bool(bipedal),
            'scale': float(scale), 'palette_sha256': palette_sha256}


def pack_creature(out, seconds):
    """(row, {name: bytes}) of a creature_library._unit result; None when it is not exact JSON (not cached)."""
    from pass_cache import json_exact
    files = {str(i): raw for i, (_, raw, _) in enumerate(out['files'])}
    row = {'files': [[role, path] for role, _, path in out['files']], 'record': out['record'],
           'seconds': round(float(seconds), 2)}
    return (row, files) if json_exact(row) else None


def unpack_creature(row, files):
    """(out, seconds) of a row pack_creature stored."""
    return {'files': [(role, files[str(i)], path) for i, (role, path) in enumerate(row['files'])],
            'record': row['record']}, row['seconds']


def bake_creatures(tasks, jobs, cache, inputs, log=print):
    """([(key, out, seconds, error)] of TASKS in input order, as ordered_map(creature_library._unit) gave them, and
    how many came from CACHE): a model stored for the same inputs is taken from it (unless --rebuild-unit
    creature-model:KEY names it); the rest are baked on the worker pool and each is stored the moment it is back.
    creature_library._unit returns a failed model with its error, so a failure never ends the map."""
    import creature_library as L
    from pass_cache import forced
    results, todo = [None] * len(tasks), []
    for index, task in enumerate(tasks):
        name = creature_name(task)
        if cache is not None and not forced(CREATURE_CACHE, name):
            found = cache.load_unit(inputs(task))
            if found is not None:
                try:
                    out, seconds = unpack_creature(*found)
                    results[index] = (name, out, seconds, None)
                    continue
                except (KeyError, TypeError, AttributeError, IndexError, ValueError):
                    pass
        todo.append(index)
    cached = len(tasks) - len(todo)
    if todo:
        import unit_store

        def keep(index, value):
            # in the unit cache the moment the model is back (UNIT-STORED-AT-MAP-END-62)
            _, out, seconds, _ = value
            results[index] = value
            if cache is not None and out is not None:
                packed = pack_creature(out, seconds)
                if packed is not None:
                    return unit_store.stored(cache, inputs(tasks[index]), *packed)
        failed = unit_store.run_each(CREATURE_CACHE, L._unit, [(index, tasks[index]) for index in todo],
                                     [creature_name(tasks[index]) for index in todo], max(1, jobs), keep,
                                     fallback=lambda name: CREATURE_FALLBACK_SECONDS, label='Creature library',
                                     already=cached, log=log)
        if failed:     # _unit returns its errors; only a broken worker gets here
            raise ValueError('Creature library: ' + '; '.join(failed))
    return results, cached


# ---------------------------------------------------------------------------------------------------------------------
# Guard torches (tools/prepare_guard_torches.py prepare, the image step): the skip verdicts

def guard_inputs(task, layout_of):
    """The guard cache's own inputs of one guard (prepare_guard_torches._convert_guard): the base model and palette by
    SHA-256, its layout, entry, appearance and the torch mesh name."""
    _, id1, entry, appearance, mesh, palette, _ = task
    original = (Path(id1) / entry['base_model']).read_bytes()
    return {'entry': {'name': '%s %s' % (entry.get('source_id'), entry.get('base_model'))}, 'base': _sha(original),
            'layout': layout_of(task), 'palette': _sha(palette), 'guard': json.loads(json.dumps(entry, default=str)),
            'appearance': json.loads(json.dumps(appearance, default=str)), 'mesh': mesh}


def known_guard_skips(tasks, cache, layout_of):
    """({index: {'skipped': reason, 'reused': True}} of the guards whose skip verdict CACHE holds, [indices to run])."""
    from pass_cache import forced
    known, todo = {}, []
    for index, task in enumerate(tasks):
        if cache is not None:
            inputs = guard_inputs(task, layout_of)
            if not forced(GUARD_SKIP_CACHE, inputs['entry']['name']):
                found = cache.load_unit(inputs)
                if found is not None and isinstance(found[0], dict) and found[0].get('skipped'):
                    known[index] = {'skipped': found[0]['skipped'], 'reused': True}
                    continue
        todo.append(index)
    return known, todo


def keep_guard_skip(cache, task, result, layout_of):
    """Keep one guard's skip verdict the moment it is back; a store not found again fails the step."""
    import unit_store
    if cache is not None and not unit_store.stored(cache, guard_inputs(task, layout_of),
                                                   {'skipped': result['skipped']}, {}):
        raise RuntimeError('Guard torches: 1 store FAILED (%s; UNIT-CACHE-STORE-ERRORS-SILENT-63)' % task[2]['base_model'])


# ---------------------------------------------------------------------------------------------------------------------
# CHIM room actor bake (tools/room_actor_bake.py _bake, the image step)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def room_actor_inputs(maps, task, memo):
    """What one room placement's fit depends on besides the fit code and its settings: the room map it is fitted in
    (its bytes before the bake writes the fitted origins), the store models that room places (their collision), the
    actor's model and layout (its soles), and the placement (entity, authored origin, angles). MEMO: per-room digests
    of this bake."""
    from chim.interior import installed_room, store_model_images
    from map_files import map_file
    _, _, selected, e, authored, angles = task
    maps = Path(maps)
    if ('room', selected) not in memo:
        path = map_file(maps, selected)
        raw = path.read_bytes()
        try:
            room = installed_room(path)
            images = store_model_images(maps.parent, room['store'], [p['model'] for p in room['placements']])
            store = {str(name): _sha(data if isinstance(data, bytes) else json.dumps(data, default=str).encode())
                     for name, data in sorted(images.items())}
        except (ValueError, KeyError, OSError, TypeError) as error:
            store = {'unread': str(error)}
        memo[('room', selected)] = {'map': _sha(raw), 'store': store}
    model = e.get('model', '')
    if ('model', model) not in memo:
        path = maps.parent / model
        layout = path.with_suffix('.anm')
        memo[('model', model)] = {'model': _sha(path.read_bytes()) if path.is_file() else None,
                                  'layout': _sha(layout.read_bytes()) if layout.is_file() else None}
    return {'entry': {'name': '%s %s' % (selected, e.get('aw_ref'))}, 'room': memo[('room', selected)],
            'actor': memo[('model', model)], 'entity': dict(sorted(e.items())), 'authored': [float(v) for v in authored],
            'angles': [float(v) for v in angles]}


def fit_room_actors(tasks, jobs, cache, maps, fit_all, log=print):
    """The final fit result of every placement TASK (room_actor_bake._bake's tasks, in their order): from CACHE when
    it was fitted before on the same inputs (room_actor_inputs; --rebuild-unit room-actor:'ROOM REF' fits it again),
    the rest by FIT_ALL(tasks, jobs, keep), each stored the moment its result is final, '[d/t]' per placement; a store
    not found again fails the bake (unit_store.stored)."""
    import time
    import unit_store
    from pass_cache import forced, json_exact
    memo, inputs, results, todo = {}, [], [None] * len(tasks), []
    for index, task in enumerate(tasks):
        inputs.append(room_actor_inputs(maps, task, memo) if cache is not None else None)
        if cache is not None and not forced(ROOM_ACTOR_CACHE, inputs[index]['entry']['name']):
            found = cache.load_unit(inputs[index])
            if found is not None and isinstance(found[0], dict) and 'result' in found[0]:
                results[index] = found[0]['result']
                continue
        todo.append(index)
    cached, lost, began = len(tasks) - len(todo), [], time.monotonic()
    log('CHIM room actor bake [%d/%d] cached, %d to fit' % (cached, len(tasks), len(todo)), flush=True)
    done = [cached]

    def keep(j, result):
        index = todo[j]
        try:
            # the JSON form for every fit, fitted now or taken from the cache (tuples as lists), so both write the same
            result = json.loads(json.dumps(result))
        except (TypeError, ValueError):
            pass
        results[index] = result
        done[0] += 1
        name = '%s %s' % (tasks[index][2], tasks[index][3].get('aw_ref'))
        log(unit_store.progress_line('CHIM room actor bake', done[0], len(tasks), name, time.monotonic() - began),
            flush=True)
        if cache is not None and json_exact(result):
            if not unit_store.stored(cache, inputs[index], {'result': result}, {}):
                lost.append(name)
                log('!! CHIM room actor bake: STORE FAILED: %s is not in the unit cache after it was stored' % name,
                    flush=True)
    if todo:
        fit_all([tasks[index] for index in todo], jobs, keep)
    log('CHIM room actor bake: %d placements (%d from the unit cache %s, %d fitted)' % (
        len(tasks), cached, ROOM_ACTOR_CACHE, len(todo)), flush=True)
    if lost:
        raise RuntimeError('CHIM room actor bake: %d stores FAILED (%s; UNIT-CACHE-STORE-ERRORS-SILENT-63)'
                           % (len(lost), ', '.join(lost[:8])))
    return results


# ---------------------------------------------------------------------------------------------------------------------
# Arena fighters (tools/prepare_combat.py prepare, the image step)

def fighter_inputs(task):
    """What one arena fighter depends on besides the game data, the bake code and the settings it reads: the NPC
    record id, its fighting stance and the palette by SHA-256. Its own bake (the fight groups, the carried weapon and
    shield), not the actor library's standing model: the two are different models of one record."""
    _, palette, identifier, stance = task
    return {'entry': {'name': identifier}, 'stance': stance, 'palette_sha256': palette_digest(palette)}


def pack_fighter(made):
    """(row, {name: bytes}) of a bake_fighter result; None when its record is not exact JSON."""
    from pass_cache import json_exact
    identifier, raw, record = made
    row = {'identifier': identifier, 'record': record}
    return (row, {'model': raw}) if json_exact(row) else None


def bake_fighters(tasks, jobs, cache, inputs, log=print):
    """([(identifier, raw, record)] of TASKS [(data, palette, identifier, stance)] in input order, cached): a fighter
    stored for the same inputs is taken from CACHE (unless --rebuild-unit arena-fighter:ID names it); the rest are
    baked on the worker pool and each is stored the moment it is back. A failed fighter fails the step, as before,
    after every other one is kept."""
    import prepare_combat
    from pass_cache import forced
    results, todo = [None] * len(tasks), []
    for index, task in enumerate(tasks):
        if cache is not None and not forced(FIGHTER_CACHE, task[2]):
            found = cache.load_unit(inputs(task))
            if found is not None and 'model' in found[1]:
                results[index] = (found[0]['identifier'], found[1]['model'], found[0]['record'])
                continue
        todo.append(index)
    cached = len(tasks) - len(todo)
    if todo:
        import unit_store

        def keep(index, made):
            results[index] = made
            if cache is not None:
                packed = pack_fighter(made)
                if packed is not None:
                    return unit_store.stored(cache, inputs(tasks[index]), *packed)
        failed = unit_store.run_each(FIGHTER_CACHE, prepare_combat.bake_fighter,
                                     [(index, tasks[index]) for index in todo], [tasks[index][2] for index in todo],
                                     max(1, jobs), keep, fallback=lambda name: 30.0, label='Arena fighters',
                                     already=cached, log=log)
        if failed:
            raise ValueError('Arena fighters: ' + '; '.join(failed))
    return results, cached
