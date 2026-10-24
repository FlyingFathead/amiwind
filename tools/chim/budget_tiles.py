# SPDX-License-Identifier: GPL-3.0-only
"""Models over one brush image's index budgets, stored as tiles of their own frame (CHIM-ROOM-CLIPNODE-BUDGET-48).

A model's brush image addresses its clipnodes, point-hull nodes and vertices with 16-bit indices and its texture
mappings with up to 65,536 rows (chim.models.BrushLumps). A model whose collision needs more cannot be one image: the
standing hull chain of Akulakhan's cave shell (in_akulacave00, 6,281 authored collision plates with exact standing
bevels) is 162,975 clipnodes against 65,520, and neither the routed hull (one chain per routed part, no copies) nor
the qbsp union (the cave shells' compile fails) fits. Before this, such a model failed its whole frame or room.

The repair is the large-model cut's tiles (chim.cut.model_tiles, mode 'tiles') applied to that model alone, whatever
the area's cut settings: the model is cut in its own frame at the frame's grain, halved until every tile fits one
image (never under TILE_MIN local units, at most TILE_MAX tiles: chim.cut.piece_ref numbers 1..127). Every convex
collision piece and every face goes whole to one tile, so the union of the tiles is the model: what is drawn and what
is solid do not change, only the number of images. Every placement of the model places every tile (the tiled
placements of chim.build.frame_input).

This module is apart from chim.models and chim.cut on purpose: the unit keys of the variant and tile workers cover
the import-time code of every module they reach (tools/code_key.py), so nothing here rekeys a unit of any model that
fits. The variant units run as before; only when a run stops on a budget error are its units run one by one, so the
models that fit are made (and cached) exactly as before and the one that does not is named.
"""
TILE_MIN = 16.0
TILE_MAX = 127
# The index budgets of one brush image (chim.models.BrushLumps): a model past one of them cannot be one image.
BUDGET_ERRORS = ('Clipnode budget exceeded', 'Point node budget exceeded', 'Vertex budget exceeded',
                 'Texture mapping budget exceeded', 'Compiled collision node budget exceeded')


def over_budget(error):
    """True when error is BrushLumps refusing a model past one of the image's index budgets (BUDGET_ERRORS)."""
    return isinstance(error, ValueError) and any(str(error).startswith(m) for m in BUDGET_ERRORS)


def run_fitting(run_units, kind, items, worker, jobs, cache, log=print):
    """run_units(kind, items, worker, jobs, cache) with the units over the brush image budget named in that one run
    (CHIM-BUDGET-RERUN-SERIAL-48): such a unit hands back its budget error as its result (chim.units.run_units SOFT,
    never cached) and gets {'over_budget': the error}; the units that fit get their results and their cache entries,
    keys unchanged. Any other error is raised as before.

    AMIWIND_BUDGET_RERUN=serial: the method before v0.0.48, when the run stops on a budget error every unit runs again
    on its own, one by one on one core (the v0.0.48-dev2 try 9 chim-interiors stage: 58 variant units, about 36 s on
    one core of 24). The same results either way."""
    import os
    if os.environ.get('AMIWIND_BUDGET_RERUN', 'named') != 'serial':
        # (helpers in chim.units, which no unit key holds: this module's import-time text stays as it was)
        from chim.units import SoftError, unit_name
        out = []
        named = []
        for (fp, task), result in zip(items, run_units(kind, items, worker, jobs, cache, soft=BUDGET_ERRORS)):
            if isinstance(result, SoftError):           # the unit's budget error
                out.append({'over_budget': str(result)[:400]})
                named.append(unit_name(task, fp))
            else:
                out.append(result)
        if named:
            log('[chim] %d %s unit(s) over the brush image budget, named in the one run of %d units: %s'
                % (len(named), kind, len(items), ', '.join(named[:8]) + (' ...' if len(named) > 8 else '')))
        return out
    try:
        return run_units(kind, items, worker, jobs, cache)
    except ValueError as error:
        if not over_budget(error):
            raise
        log('[chim] a %s unit is over the brush image budget (%s): the %d units run one by one to name it'
            % (kind, error, len(items)))
    out = []
    for item in items:
        try:
            out.append(run_units(kind, [item], worker, 1, cache)[0])
        except ValueError as error:
            if not over_budget(error):
                raise
            out.append({'over_budget': str(error)[:400]})
    return out


def fit_tiles(task, tiles_of):
    """(grain, tiles) of a model over the image budget: tiles_of(task with grain) (chim.cut.tile_unit, or
    chim.placed.tile_unit_placed for format 0.8 images) at the coarsest grain, from task['grain'] down by halves, whose
    every tile fits one image."""
    grain, last = float(task['grain']), None
    while grain >= TILE_MIN:
        try:
            tiles = tiles_of(dict(task, grain=grain))
        except ValueError as error:
            if not over_budget(error):
                raise
            last, grain = error, grain / 2
            continue
        if len(tiles) > TILE_MAX:
            raise ValueError('Model over the image budget: %d tiles at grain %g, at most %d (%s)'
                             % (len(tiles), grain, TILE_MAX, last))
        return grain, tiles
    raise ValueError('Model over the image budget: no tile grain down to %g fits (%s)' % (TILE_MIN, last))


def budget_tile_unit(task):
    """fit_tiles with chim.cut.tile_unit (a pool worker; unit kind 'tiles-budget')."""
    from chim.cut import tile_unit
    return fit_tiles(task, tile_unit)


def budget_tile_unit_placed(task):
    """fit_tiles with format 0.8 tiles, their piece tables in every image (unit kind 'tiles-budget-placed')."""
    from chim.placed import tile_unit_placed
    return fit_tiles(task, tile_unit_placed)


def whole_of(tiles):
    """The model's own box and texture keys from its tiles: lo, hi (each tile's box moved by its centre) and
    {texture key: material}."""
    lo = [min(t['lo'][a] + t['centre'][a] for t in tiles) for a in range(3)]
    hi = [max(t['hi'][a] + t['centre'][a] for t in tiles) for a in range(3)]
    materials = {}
    for t in tiles:
        materials.update(t['materials'])
    return lo, hi, materials
