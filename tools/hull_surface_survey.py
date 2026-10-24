#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Measure the collision surface gate on every exterior mesh of the base master and write the hull-surface table
(config/collision-hull-surface.json; CHIM-VIVEC-DOCK-WALKWAY-43, CHIM-HULL-SURFACE-RESURVEY-48).

The CHIM collision surface gate (chim.build.hull_surface_gate) fails a build when a mesh's walkable collision lies
more than a step (player_hull.STEP_HEIGHT) over its convex pieces (mesh_geometry.surface_loss_depth). The meshes that
need the surface rule (profile hull_surface_loss, mesh_geometry.collision_parts surface_loss) are listed in the table;
the list depends on the converter's defaults (the collision source, the stair collision method), so it is measured
again whenever those change. This tool does that measurement the way the CHIM model builder does it:

1. export: every exterior placement of the base master (Morrowind.esm), split as the CHIM source stage splits them
   (import_town.split_references, lava_split); one placement per distinct model is exported with the CHIM group
   profile (collision_source root_node_or_visual) by prepare_scenery.export_refs, under the collision source rule of
   the environment (collision_source_env: the shipped default unless AMIWIND_COLLISION_SOURCE is set).
2. measure, in parallel (largest first): each model gets the CHIM model builder's profile (chim.build.prepare_area:
   town_model_profile, stair plates, visible treads, the underside rule, surface flattening, the mesh method, the
   everywhere recipe; stair collision method 1 for a mesh with a flight as drawn), is prepared by the builder's own
   mesh worker (chim.build.mesh_unit or stair_mesh.mesh_unit_stair) and measured by the gate's own unit
   (chim.build.hull_surface_unit) with the gate's exclusions (ramps the visible-tread rule replaces; the collision
   triangles of flights stair collision method 1 replaced, lod stair_removed_triangles). Variant 'base':
   without the surface rule; variant 'rule': with it (for the meshes over a step without it and the meshes the
   current table lists). The standing-hull clipnodes of each prepared mesh are counted (chim.models.model_image_lumps).
3. table: the meshes over a step without the rule and within a step with it are the table's meshes; the meshes still
   over a step with it are its known list, with the reason. Placement counts and clipnodes (each mesh's clipnodes
   times its exterior placements) before (the current table) and after (the new one) go into the counts.

Each mesh is measured under every profile variant its placements get (survey_references: the visual recipe of a
cell that has one, a CHIM town's detail budget): a visual reduction changes the drawn mesh the visible-tread rule
and stair collision method 1 read (ex_de_ship under the Telvanni coast recipe). A mesh fails when any variant does.

What this does NOT measure: placed variants (scale, tilt), meshes no exterior placement of the base master uses. Nothing is walked; no game data is written to the
output (mesh paths, depths, counts only). The export goes to --work (a scratch folder the tool removes when done).

    hull_surface_survey.py --data-files DIR --work DIR --out FILE [--jobs N] [--limit N] [--table FILE]
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'src'), str(HERE)]

FORMAT = 1
GROUP = 'hull_surface_survey'
CHIM_TOWNS = ('balmora', 'seyda', 'vivec_city')     # the CHIM stage's towns (their detail budgets)
REASON_KNOWN = ('still over a step with the rule: another converter path (follow-up)')


def exterior_placements(data):
    """Every exterior placement of the base master as the CHIM audit writes it ({'cell': [x, y], **ref, **object}),
    deleted references left out."""
    from mwad.audit import load_esm
    from mwad.paths import child_ci
    esm = load_esm(child_ci(data, 'Morrowind.esm'))
    out = []
    for (cx, cy), cell in sorted(esm['cells'].items()):
        for ref in cell['refs']:
            if ref.get('deleted') or 'id' not in ref or 'position' not in ref:
                continue
            obj = esm['objects'].get(ref['id'].casefold())
            if obj is not None:
                out.append({'cell': [cx, cy], **ref, **obj})
    return out


def survey_references(data, placements):
    """(one reference per distinct model of the converted scenery, {model path: placements}, {model path: the
    profile variants its placements get}), as the CHIM source stage selects scenery (split_references, lava_split).
    A variant is ('recipe', name or None): the visual recipe of the placement's cell (visual_recipes.cell_settings,
    bound per cell by visual_recipes.scope_reference_recipes; None: the everywhere recipe only), or ('budget', name):
    a CHIM town's detail budget (config/chim-detail-budgets.json) for the meshes it names. Visual reductions change
    the drawn mesh the visible-tread rule and stair collision method 1 read, so each variant is measured."""
    from import_town import split_references, lava_split
    from mwad.audit import normpath
    from visual_recipes import load_recipes
    from chim.build import detail_budget
    from town_config import registry_row
    selected, deferred = split_references(placements, data)
    selected, _, _ = lava_split(data, selected, deferred)
    cells = load_recipes().get('cell_settings', {})
    counts = Counter('meshes/' + normpath(r['model']) for r in selected)
    first, variants = {}, {}
    for r in selected:
        key = 'meshes/' + normpath(r['model'])
        first.setdefault(key, r)
        recipe = cells.get('%d,%d' % tuple(r['cell']), {}).get('visual_recipe')
        variants.setdefault(key, set()).add(('recipe', recipe))
    for town in CHIM_TOWNS:
        # the town's settings file (config/towns.json row); its detail_budget is an area cut key (chim.build)
        name = json.loads((HERE.parent / 'config' / registry_row(town)['config']).read_text(encoding='utf-8')
                          ).get('detail_budget')
        for mesh in detail_budget(name):
            if mesh in variants:
                variants[mesh].add(('budget', name))
    return ([first[k] for k in sorted(first)], dict(counts),
            {k: sorted(v, key=lambda x: (x[0], x[1] or '')) for k, v in variants.items()})


def export(data, work, refs, jobs):
    """The scenery export of refs (prepare_scenery.export_refs) with the CHIM group profile; returns the index."""
    from prepare_scenery import export_refs
    from mwad.audit import normpath
    groups = {GROUP: {'references': [r['number'] for r in refs],
                      'visual_profiles': {'meshes/' + normpath(r['model']): {'collision_source': 'root_node_or_visual'}
                                          for r in refs}}}
    report = export_refs(data, work / 'scenery', refs, groups, [0, 0, 0], jobs=jobs)
    index = json.loads((work / 'scenery' / 'scenery-index.json').read_text(encoding='utf-8'))
    return index, report


def chim_profile(model, group_profile, rule, flight, variant=('recipe', None)):
    """The CHIM model builder's profile for a mesh (chim.build.prepare_area). rule: the hull-surface rule
    (hull_surface_loss); flight: the mesh holds a flight as drawn (stair collision method 1 when that is the method);
    variant: ('recipe', a cell's visual recipe or None) or ('budget', a detail budget name), see survey_references."""
    from town_regions import town_model_profile
    from mesh_geometry import SURFACE_LOSS, UNDERSIDE_DEPTH
    from mesh_geometry_env import underside_mode, hull_points_mode
    from stair_collision_env import stair_collision_method
    from surface_flatten import load_profiles
    from visual_recipes import load_recipes, apply_recipe, everywhere_recipe
    from chim.build import apply_mesh_method
    underside = underside_mode()
    profile = town_model_profile(group_profile, model['source'], model['triangles'],
                                 underpass_names=underside == 'names')
    profile['stair_plates'] = True
    profile['visible_treads'] = True
    if flight and stair_collision_method() == '1':
        profile['stair_collision'] = 'mesh'
    if rule:
        profile['hull_surface_loss'] = SURFACE_LOSS
        if hull_points_mode() == 'table-whole':
            profile['hull_surface_points'] = 'all'
    if underside == 'whole':
        profile['underside_whole'] = UNDERSIDE_DEPTH
    elif underside in ('rule', 'split'):
        profile['underside_plates'] = UNDERSIDE_DEPTH
        if underside == 'split':
            profile['underside_split'] = True
    flatten = load_profiles(scene_kind='exterior')
    if model['source'] in flatten:
        profile['flatten'] = flatten[model['source']]
    kind, name = variant
    if kind == 'budget':
        from chim.build import detail_budget
        target = detail_budget(name).get(model['source'].replace(chr(92), '/').lower())
        if target and model['triangles'] > target:
            profile = dict(profile, ratio=target / model['triangles'], visual_triangle_target=target,
                           lod_preserve_border=True)
    profile = apply_mesh_method(profile, model['source'], None)
    recipes = load_recipes()
    if kind == 'recipe' and name:
        profile = apply_recipe(profile, model, name, recipes)
    everywhere = everywhere_recipe(recipes)
    if everywhere and 'visual_recipe' not in profile:
        profile = apply_recipe(profile, model, everywhere, recipes)
    return profile


def variant_name(variant):
    kind, name = variant
    return 'default' if (kind, name) == ('recipe', None) else '%s:%s' % (kind, name)


def replaced_ramps(note):
    """The gate's exclusion (chim.build.hull_surface_gate): ramps the visible-tread rule replaced on purpose."""
    return 'visible plates' in str(note) and ' 0 ramp plates' not in str(note)


def clipnodes(pieces, lod):
    """Standing-hull clipnodes and planes of a prepared mesh's collision (chim.models.model_image_lumps)."""
    import numpy as np
    from chim.models import model_image_lumps
    from prepare_mesh_bsp import _bevels
    if not pieces:
        return 0, 0
    pts = np.vstack([np.asarray(p[0], float) for p in pieces])
    lumps, _ = model_image_lumps([], pieces, pts.min(axis=0), pts.max(axis=0), lambda m: 0,
                                 exact=_bevels(lod, range(len(pieces))))
    return len(lumps[9]) // 8, len(lumps[1]) // 20


def flight_count(task):
    from stair_mesh import flight_unit
    model, archive = task
    if (model.get('source_collision') or {}).get('mode') == 'nonsolid':
        return 0
    return flight_unit((model, archive))


def measure(task):
    """One mesh, one variant: the gate's depth over the prepared pieces, the gate's exclusion, the collision note,
    clipnodes and planes, the time it took."""
    from chim.build import mesh_unit, hull_surface_unit
    model, archive, textures, group_profile, flight, rule, variant = task
    row = {'source': model['source'], 'rule': rule, 'variant': variant_name(variant)}
    t = time.perf_counter()
    try:
        profile = chim_profile(model, group_profile, rule, flight, variant)
        item = (0, model, profile, archive, textures)
        if profile.get('stair_collision') == 'mesh':
            from stair_mesh import mesh_unit_stair
            prepared = mesh_unit_stair(item)
        else:
            prepared = mesh_unit(item)
        pieces, lod = prepared[3], prepared[4]
        note = lod.get('collision') or ''
        removed = tuple(lod.get('stair_removed_triangles', ()))
        row.update(depth=round(float(hull_surface_unit((archive, model, pieces, removed))), 2),
                   replaced=replaced_ramps(note), note=note, pieces=len(pieces), stair_removed=len(removed))
        row['clipnodes'], row['planes'] = clipnodes(pieces, lod)
    except Exception as error:      # reported with its reason, never skipped silently
        row['error'] = '%s: %s' % (type(error).__name__, error)
    row['seconds'] = round(time.perf_counter() - t, 2)
    return row


def over(row, step):
    """True when the gate fails this measured variant (depth over a step and not an excluded replaced ramp)."""
    return row is not None and 'error' not in row and row['depth'] > step and not row['replaced']


def worst(rows, step):
    """The row of a mesh's profile variants the gate judges hardest: an error first, then a failing one, deepest
    first; None for no rows."""
    rows = [r for r in rows if r is not None]
    if not rows:
        return None
    return max(rows, key=lambda r: ('error' in r, over(r, step), r.get('depth', 0)))


def table_rows(meshes, step):
    """(table meshes, known {mesh: {depth, reason}}, {recipe: meshes}) from survey mesh rows: a mesh over a step
    without the rule (in any profile variant) and within a step with it -> table; over a step with it too -> known.
    A mesh that needs the rule only under cells' visual recipes (every other variant within a step without it) is
    listed for those recipes only (recipe_meshes): the rule costs clipnodes in every copy of the mesh it is on."""
    table, known, recipes = [], {}, {}
    for m in meshes:
        key = m['source'].replace(chr(92), '/').casefold()
        variants = m.get('variants') or {'default': {'base': m.get('base'), 'rule': m.get('rule')}}
        need = [v for v, r in variants.items() if over(r['base'], step)]
        if not need:
            continue
        still = [variants[v]['rule'] for v in need
                 if variants[v]['rule'] is None or 'error' in variants[v]['rule'] or over(variants[v]['rule'], step)]
        if still:
            deepest = worst(still, step)
            known[key] = {'depth': deepest['depth'] if deepest and 'error' not in deepest
                          else worst([variants[v]['base'] for v in need], step)['depth'], 'reason': REASON_KNOWN}
        elif all(v.startswith('recipe:') for v in need):
            for v in need:
                recipes.setdefault(v.split(':', 1)[1], []).append(key)
        else:
            table.append(key)
    return sorted(table), dict(sorted(known.items())), {r: sorted(ms) for r, ms in sorted(recipes.items())}


def counts(meshes, chosen, weighted=True):
    """Placements of the chosen meshes and the placement-weighted clipnodes of every measured mesh with the chosen
    meshes on the rule (the rest without it); weighted False: each mesh's clipnodes once (a model stored once)."""
    total, placed = 0, 0
    for m in meshes:
        key = m['source'].replace(chr(92), '/').casefold()
        c = m.get('counted', m)     # the default profile variant (survey_references) when there are several
        row = c.get('rule') if key in chosen and c.get('rule') else c.get('base')
        if not row or 'error' in row:
            continue
        total += row['clipnodes'] * (m['placements'] if weighted else 1)
        if key in chosen:
            placed += m['placements']
    return placed, total


def write_table(path, report, previous):
    """The hull-surface table (schema aw-collision-hull-surface-1) from a survey report; previous: the table it
    replaces (its rule text is kept)."""
    step = report['step_height']
    table, known = report['table']['meshes'], report['table']['known_over_step']
    d = report['defaults']
    doc = {'schema': 'aw-collision-hull-surface-1',
           'bug': 'CHIM-VIVEC-DOCK-WALKWAY-43',
           'rule': previous['rule'],
           'measured': ('%s, every exterior mesh of the base master (%d; %d not converted as statics), by '
                        'tools/hull_surface_survey.py under the shipped defaults (collision source %s, stair collision '
                        'method %s, underside rule %s), the CHIM model builder profile with the stair-plate and '
                        'visible-tread rules: walkable collision more than a step (%.1f) over the extreme-point pieces, '
                        'and within a step with this rule, in every profile variant its placements get (a cell\'s '
                        'visual recipe, a town\'s detail budget); recipe_meshes: meshes that need it only in the cells '
                        'of that visual recipe' % (
                            report['measured'], report['exterior_models'], report['not_converted'],
                            d['collision_source'], d['stair_collision'], d['underside'], step)),
           'counts': {'meshes': len(table),
                      'placements': report['table']['placements'],
                      'clipnodes_before_after': report['table']['clipnodes_before_after'],
                      'clipnodes_stored_once_before_after': report['table']['clipnodes_stored_once_before_after'],
                      'clipnodes_weighting': 'standing-hull clipnodes of each measured mesh times its exterior '
                                             'placements (stored once: each mesh once); before: the table this one '
                                             'replaced, after: this table'},
           'meshes': table,
           'recipe_meshes': report['table'].get('recipe_meshes', {}),
           'known_over_step': known}
    Path(path).write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8', newline='\n')
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--data-files', required=True)
    ap.add_argument('--work', required=True, help='scratch folder for the export (must not exist; removed when done)')
    ap.add_argument('--out', required=True, help='the survey report (JSON)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--limit', type=int, default=0, help='measure at most this many meshes (0: all; tests)')
    ap.add_argument('--table', help='write the hull-surface table here (config/collision-hull-surface.json)')
    ap.add_argument('--keep-work', action='store_true', help='keep the scratch export')
    ap.add_argument('--previous', help='the table to compare with (default: config/collision-hull-surface.json)')
    a = ap.parse_args(argv)
    from mwad.paths import resolve_data_files
    a.data_files = resolve_data_files(a.data_files)
    from player_hull import STEP_HEIGHT
    from mesh_geometry import SURFACE_LOSS
    from collision_source_env import collision_source_mode
    from stair_collision_env import stair_collision_method
    from mesh_geometry_env import underside_mode, hull_points_mode
    from chim.build import hull_surface_table, HULL_SURFACE_TABLE
    work = Path(a.work)
    if work.exists():
        raise SystemExit('--work must not exist: ' + str(work))
    work.mkdir(parents=True)
    t0 = time.perf_counter()
    try:
        placements = exterior_placements(a.data_files)
        refs, placed, profile_variants = survey_references(a.data_files, placements)
        print('[hull-survey] profile variants: %d meshes in cells with their own visual recipe or in a detail budget'
              % sum(1 for v in profile_variants.values() if v != [('recipe', None)]), flush=True)
        print('[hull-survey] %d exterior placements, %d distinct scenery models; exporting on %d workers'
              % (len(placements), len(refs), a.jobs), flush=True)
        t = time.perf_counter()
        index, export_report = export(a.data_files, work, refs, a.jobs)
        archive = str(work / 'scenery' / 'scenery.mwpak')
        models = index['models']
        group = index['groups'][GROUP]['visual_profiles']
        print('[hull-survey] export took %.0f s: %d models converted, %d errors' % (
            time.perf_counter() - t, len(models), len(index.get('errors', ()))), flush=True)
        order = sorted(range(len(models)), key=lambda i: -models[i].get('triangles', 0))     # largest first
        if a.limit:
            order = order[:a.limit]
        with ProcessPoolExecutor(a.jobs) as pool:
            t = time.perf_counter()
            flights = dict(zip(order, pool.map(flight_count, [(models[i], archive) for i in order], chunksize=4)))
            print('[hull-survey] flights found in %.0f s: %d meshes with a flight as drawn' % (
                time.perf_counter() - t, sum(1 for n in flights.values() if n)), flush=True)

            def variants_of(i):
                return [tuple(v) for v in profile_variants.get(models[i]['source'].casefold(), [('recipe', None)])]

            def run(label, ids, rule):
                rows, t1 = {}, time.perf_counter()
                keys = [(i, v) for i in ids for v in variants_of(i)]
                tasks = [(models[i], archive, index['textures'], group[models[i]['source']], bool(flights[i]), rule, v)
                         for i, v in keys]
                for k, (key, row) in enumerate(zip(keys, pool.map(measure, tasks, chunksize=1)), 1):
                    rows[key] = row
                    if k % 100 == 0 or k == len(keys):
                        print('[hull-survey] %s: %d/%d mesh variants, %d over a step, %d errors, %.0f s on %d workers'
                              % (label, k, len(keys), sum(1 for r in rows.values() if over(r, STEP_HEIGHT)),
                                 sum(1 for r in rows.values() if 'error' in r), time.perf_counter() - t1, a.jobs),
                              flush=True)
                return rows
            base = run('base', order, False)
            current = hull_surface_table(a.previous) if a.previous else hull_surface_table()
            again = [i for i in order if any(over(base[(i, v)], STEP_HEIGHT) for v in variants_of(i))
                     or models[i]['source'].replace(chr(92), '/').casefold() in current]
            rule = run('rule', again, True)
        meshes = []
        for i in order:
            m = models[i]
            vs = variants_of(i)
            default = ('recipe', None) if ('recipe', None) in vs else vs[0]
            meshes.append({'source': m['source'], 'triangles': m.get('triangles'),
                           'collision': (m.get('collision') or {}).get('source') or 'drawn triangles',
                           'source_collision': (m.get('source_collision') or {}).get('mode'),
                           'flights': flights[i], 'placements': placed.get(m['source'].casefold(), 0)
                           or placed.get(m['source'], 0),
                           'base': worst([base[(i, v)] for v in vs], STEP_HEIGHT),
                           'rule': worst([rule.get((i, v)) for v in vs], STEP_HEIGHT),
                           'counted': {'variant': variant_name(default), 'base': base[(i, default)],
                                       'rule': rule.get((i, default))},
                           'variants': {variant_name(v): {'base': base[(i, v)], 'rule': rule.get((i, v))}
                                        for v in vs}})
        table, known, recipe_table = table_rows(meshes, STEP_HEIGHT)
        chosen = set(table)
        before_placed, before_clip = counts(meshes, current)
        after_placed, after_clip = counts(meshes, chosen)
        report = {'format': FORMAT, 'tool': 'tools/hull_surface_survey.py',
                  'measured': datetime.date.today().strftime('%d %B %Y').lstrip('0'),
                  'defaults': {'collision_source': collision_source_mode(), 'stair_collision': stair_collision_method(),
                               'underside': underside_mode(), 'hull_points': hull_points_mode()},
                  'step_height': STEP_HEIGHT, 'surface_loss': SURFACE_LOSS,
                  'exterior_placements': len(placements), 'exterior_models': len(refs),
                  'converted_models': len(models), 'not_converted': len(refs) - len(models),
                  'export_errors': index.get('errors', [])[:200],
                  'measured_meshes': len(order), 'errors': sum(1 for x in meshes if 'error' in x['base']),
                  'wall_s': round(time.perf_counter() - t0, 1), 'jobs': a.jobs,
                  'table': {'meshes': table, 'known_over_step': known, 'recipe_meshes': recipe_table,
                            'placements': after_placed,
                            'previous_meshes': len(current), 'previous_placements': before_placed,
                            'clipnodes_before_after': [before_clip, after_clip],
                            'clipnodes_stored_once_before_after': [counts(meshes, current, False)[1],
                                                                   counts(meshes, chosen, False)[1]],
                            'added': sorted(chosen - current), 'removed': sorted(current - chosen)},
                  'meshes': meshes}
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
        print('[hull-survey] %d meshes measured (%d errors): table %d meshes (was %d; %d added, %d removed), %d for a '
              'visual recipe only %s, %d known; placement-weighted clipnodes %d -> %d; %.0f s' % (
                  len(order), report['errors'], len(table), len(current), len(chosen - current),
                  len(current - chosen), sum(len(x) for x in recipe_table.values()), recipe_table, len(known),
                  before_clip, after_clip, time.perf_counter() - t0), flush=True)
        if a.table and report['errors']:
            raise SystemExit('%d meshes failed to measure (report: %s): no table written' % (report['errors'], a.out))
        if a.table:
            previous = json.loads(Path(HULL_SURFACE_TABLE).read_text(encoding='utf-8'))
            write_table(a.table, report, previous)
            print('[hull-survey] table written: %s' % a.table, flush=True)
    finally:
        if not a.keep_work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
