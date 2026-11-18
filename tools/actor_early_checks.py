#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The outdoor creatures' models, checked on the actor library stage's own output before the image step
(OUTDOOR-CREATURES-REGRESSION-66, BUILD-IMAGE-CHECKS-EARLY-66): entries of the builder's early checks
(tools/build_preflight.py EARLY_CHECKS).

The engine spawns an outdoor creature only when its base in the actor table has a model (aw_actors.c: a base without
one is counted "without a model" and never spawned), and the table takes its creature models from the actor library
stage (tools/creature_library.py base_texts). The image step's actor spec check (tools/actor_spec_check.py) counts that
at the end of a build; this reads the library alone, in seconds, as soon as it exists: every creature the base game
places outdoors, and every creature the outdoor levelled lists can give at some level (nested lists followed), must
have a model in the library. A placed creature without one, or a levelled list that can give none, stops the build
before the world stages, naming the records.

- exterior_creature_models (phase stored): the actor library this build takes from an earlier run;
- exterior_creature_models_after (phase after:actor-library): the one this build has just made (the game data from
  the run's build-state.json, as the stage read it).

The expansions' outdoor references are not counted here (their creatures: CREATURE-EXPANSION-62; the image step's
check sets their places aside by name).
"""
import json
import os
from pathlib import Path

STAGE = 'actor-library'
MANIFEST = 'creature-library.json'
SHOWN = 12


def _data_files(context, run=None):
    """The game data folder: the build's option, else the run's own record of it (build-state.json data_files, written
    at the build's start)."""
    if context.data_files:
        return Path(context.data_files)
    state = Path(run or context.run or '.') / 'build-state.json'
    if state.is_file():
        value = json.loads(state.read_text(encoding='utf-8')).get('data_files')
        if value:
            return Path(value)
    return None


def missing_models(master_bytes, texts):
    """([placed creature ids without a model], [levelled list ids that can give no modelled creature], counts) of the
    base game's exterior references (actor_spec_check.read_original; master_of: the base game's own numbers) against
    TEXTS {creature id: entity text} of the library."""
    import actor_spec_check as asc
    tags, _flags, lists, refs = asc.read_original(master_bytes, numbers=True)
    base = asc.master_of(0)
    have = {i.casefold() for i in texts}

    def gives(ident, seen):
        if tags.get(ident) == 'CREA':
            return ident in have
        if tags.get(ident) != 'LEVC' or ident in seen:
            return False
        return any(gives(e, seen | {ident}) for e in lists.get(ident, ()) if e)

    placed, lev, n_crea, n_lev = set(), set(), 0, 0
    for interior, _xy, ident, number, _cell in refs:
        if interior or asc.master_of(number) != base:
            continue
        if tags.get(ident) == 'CREA':
            n_crea += 1
            if ident not in have:
                placed.add(ident)
        elif tags.get(ident) == 'LEVC':
            n_lev += 1
            if not gives(ident, frozenset()):
                lev.add(ident)
    return sorted(placed), sorted(lev), {'creatures': n_crea, 'levelled': n_lev}


def check_library(library, data_files, log=print):
    """[problem] of the actor library folder LIBRARY against the game data DATA_FILES."""
    from creature_library import base_texts
    from mwad.masters import master_path
    path = Path(library) / MANIFEST
    if not path.is_file():
        return ['%s has no %s: the outdoor creatures would have no model' % (library, MANIFEST)]
    placed, lev, n = missing_models(master_path(Path(data_files)).read_bytes(), base_texts(path))
    problems = []
    if placed:
        problems.append('%d of the outdoor creatures the base game places have no model in the actor library (%s), so '
                        'the engine spawns none of them: %s' % (len(placed), path, ', '.join(placed[:SHOWN])))
    if lev:
        problems.append('%d outdoor levelled creature lists can give no creature with a model in the actor library '
                        '(%s), so none of their points ever spawns: %s' % (len(lev), path, ', '.join(lev[:SHOWN])))
    if not problems:
        log('  %s: every outdoor creature (%d placed references) and every outdoor levelled list (%d points) has a '
            'model' % (path.parent.name, n['creatures'], n['levelled']))
    return problems


def exterior_creature_models(context):
    """Phase stored: the actor library this build takes from an earlier run."""
    if STAGE not in context.steps:
        return []
    source = context.reused.get(STAGE)
    if source is None:
        context.log('  %s: made by this build; its outdoor creature models are checked the moment it has passed' % STAGE)
        return []
    data = _data_files(context)
    if data is None:
        return ['no game data folder to read the outdoor creatures from (--data-files)']
    return ['the actor library this build takes from %s: %s' % (Path(source).name, p)
            for p in check_library(Path(source) / STAGE, data, context.log)]


def exterior_creature_models_after(context):
    """Phase after:actor-library: the actor library this build has just made."""
    run = Path(context.run)
    data = _data_files(context, run) or (Path(os.environ['AMIWIND_DATA_FILES'])
                                         if os.environ.get('AMIWIND_DATA_FILES') else None)
    if data is None:
        return ['no game data folder to read the outdoor creatures from (the run\'s build-state.json data_files)']
    return check_library(run / STAGE, data, context.log)
