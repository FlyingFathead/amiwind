#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's CHIM frame against its town, before the world stage (BUILD-SEYDA-TOWN-CONTAINERS-67,
BUILD-IMAGE-CHECKS-EARLY-66): entries of the builder's early checks (tools/build_preflight.py EARLY_CHECKS).

The chim-town-seyda stage (tools/chim_town.py prepare_seyda) compares the CHIM frame's placements with the town's
statics both ways (seyda_statics_refusals). In v0.0.67-dev2 it stopped a full build about an hour in, after the world
stage, on the 19 containers that open which the frame had begun to place (SEYDA-CONTAINERS-NOT-DRAWN-67) and the
comparison did not count. The frame's own references are known long before the world stage, from the same inputs and
with the same functions the world stage uses (chim.seyda.prepare_area): its selection (chim.seyda.placements over the
scenery stage's index), the tutorial barrel (prepare_opening_refs.opening_references) and the containers that open
(chim.seyda.open_container_refs over the terrain stage's audit of the town's cells). This check puts them, with the
additions the frame declares (the dressing it keeps, the containers), through the stage's own comparison against the
town's statics (the bsp stage's scene entity list, cut by chim_town.seyda_maps_from), in about five seconds.

Left to the stage (made by the world stage itself, each declared in the frame's parity record and counted by the
comparison): the town flora, the apron owners' supplements and the harvest's removals.

- frame_town (phase stored): the bsp stage's scene is taken from an earlier run and chim-town-seyda will run in this
  build: the stored inputs, before the first stage;
- frame_town_after (phase after:bsp): the bsp stage made by this build: its scene and its inputs in the run folder,
  the moment it has passed, before the census and the world stage.
"""
import json
import os
from pathlib import Path

STAGE = 'bsp'                     # the stage that makes the town's statics (the scene entity list of the carrier)
TOWN_STAGE = 'chim-town-seyda'    # the stage whose comparison this runs early
TOWN = 'seyda'
# (the stage that makes it, the path in a run folder) of each input
AUDIT = ('terrain', 'work/generated/seyda-neen/placements.json')
INDEX = ('scenery', 'scenery/scenery-index.json')
SCENE = (STAGE, 'bsp-scene')
SHOWN = 6


def _data_files(context, run=None):
    """The game data folder: the build's option, else the run's own record of it (build-state.json data_files)."""
    if context.data_files:
        return Path(context.data_files)
    state = Path(run or context.run or '.') / 'build-state.json'
    if state.is_file():
        value = json.loads(state.read_text(encoding='utf-8')).get('data_files')
        if value:
            return Path(value)
    if os.environ.get('AMIWIND_DATA_FILES'):
        return Path(os.environ['AMIWIND_DATA_FILES'])
    return None


def predicted_frame(index, audit, data):
    """(placed reference numbers, parity) of Seyda Neen's frame as the world stage makes them (chim.seyda.prepare_area),
    before it: its selection, the tutorial barrel (placed from its own export when the selection lacks it), the
    containers that open, and the declared additions among them (the dressing it keeps, the containers). Without what
    the world stage adds or removes later (the town flora, the apron supplements, the harvest's removals)."""
    from chim import seyda
    from prepare_opening_refs import BARREL, opening_references
    selected, _, _ = seyda.placements(index)
    _, wanted, _ = opening_references(data)
    barrel = next(r for r in wanted if r['id'].casefold() == BARREL)
    have = {r['number'] for r in selected} | {barrel['number']}
    containers = sorted(r['number'] for r in seyda.open_container_refs(data, audit, have))
    return have | set(containers), {'source_dressing_added': seyda.added_dressing_refs(index, selected),
                                    'open_containers': containers}


def town_maps(scene):
    """({map: entity dicts}, region names) of the town in the scene folder SCENE (its entity list), as
    chim-town-seyda cuts it."""
    import chim_town
    import seyda_entities
    from prepare_seyda_regions import regions
    lump, models, _, _ = seyda_entities.source(scene)
    maps, _, _ = chim_town.seyda_maps_from(lump, models)
    return maps, [e['name'] for e in regions()]


def check(audit, index, scene, data_files, log=print):
    """[problem] of Seyda Neen's predicted frame (AUDIT: the terrain stage's placements.json, INDEX: the scenery stage's
    scenery-index.json, DATA_FILES: the game data) against the town of the scene folder SCENE."""
    import chim_town
    from mwad.paths import resolve_data_files
    missing = [str(p) for p in (audit, index, Path(scene) / 'seyda-entities.json') if not Path(p).is_file()]
    if missing:
        return ['Seyda Neen\'s frame and town cannot be compared: %s missing' % ', '.join(missing)]
    data = resolve_data_files(data_files)
    placed, parity = predicted_frame(json.loads(Path(index).read_text(encoding='utf-8')),
                                     json.loads(Path(audit).read_text(encoding='utf-8')), data)
    maps, names = town_maps(scene)
    refused, statics, _ = chim_town.seyda_statics_refusals(maps, names, placed, parity)
    if refused:
        return ['Seyda Neen\'s CHIM frame and its town disagree, so the chim-town-seyda stage would stop after the '
                'world stage (tools/chim_town.py seyda_statics_refusals; the frame\'s placements predicted from %s and '
                '%s, the town from %s): %s; fix: a reference the frame places as its own is declared in its parity '
                'record (chim.seyda.prepare_area) and counted by the comparison (chim_town.FRAME_ADDITIONS), or the '
                'town carrier holds it (as the tutorial barrel)' % (index, audit, scene, '; '.join(refused[:SHOWN]))]
    log('  %s: the frame\'s %d predicted placements (%d containers that open, %d kept dressing) and the town\'s %d '
        'statics agree' % (TOWN, len(placed), len(parity['open_containers']), len(parity['source_dressing_added']),
                           statics['statics']))
    return []


def _native(context):
    """Is Seyda Neen a CHIM-native town of this build? The plan's stages (phase stored), else the builder's own record
    of its CHIM-native towns (chim_town.NATIVE_ENV, set by tools/build.py for the build); unknown: True."""
    if TOWN_STAGE in context.steps:
        return True
    if context.steps and context.phase == 'stored':
        return False
    value = os.environ.get('AMIWIND_CHIM_NATIVE_TOWNS')   # chim_town.NATIVE_ENV (not imported: the check stays light)
    return True if value is None else TOWN in [t for t in value.split(',') if t]


def frame_town(context):
    """Phase stored: the bsp stage's scene this build takes from an earlier run (its inputs from the runs their stages
    come from, else from the bsp stage's own run)."""
    if not _native(context):
        return []
    if TOWN_STAGE in context.reused:
        context.log('  %s: taken from %s; its frame and town were compared when it was made'
                    % (TOWN_STAGE, Path(context.reused[TOWN_STAGE]).name))
        return []
    source = context.reused.get(STAGE)
    if source is None:
        context.log('  %s: made by this build; Seyda Neen\'s frame and town are compared the moment it has passed'
                    % STAGE)
        return []
    data = _data_files(context)
    if data is None:
        return ['no game data folder to read the containers and the tutorial barrel from (--data-files)']
    folder = lambda pair: Path(context.reused.get(pair[0]) or source) / pair[1]   # noqa: E731
    return ['the inputs this build takes from %s: %s' % (Path(source).name, p)
            for p in check(folder(AUDIT), folder(INDEX), folder(SCENE), data, context.log)]


def frame_town_after(context):
    """Phase after:bsp: the bsp stage this build has just made, with its inputs in the run folder."""
    if not _native(context):
        context.log('  %s: Seyda Neen is not a CHIM-native town of this build; nothing to compare' % STAGE)
        return []
    run = Path(context.run)
    data = _data_files(context, run)
    if data is None:
        return ['no game data folder to read the containers and the tutorial barrel from (the run\'s build-state.json '
                'data_files)']
    return check(run / AUDIT[1], run / INDEX[1], run / SCENE[1], data, context.log)
