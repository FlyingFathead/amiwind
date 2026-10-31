# SPDX-License-Identifier: GPL-3.0-only
"""Recipe collision preflight (RECIPE-ROW-MOVES-COLLISION-57): before the CHIM stage, every reduction row of the
everywhere recipe (config/visual-recipes.json) whose result is not cached yet is checked on its own mesh: the
collision surface gate's verdict (chim.build.hull_surface_gate's rule: depth over a step, ramps the visible-tread rule
replaced not measured) with the row and without it, through the CHIM model builder's own profile
(hull_surface_survey.measure). A row that makes the gate fail where the mesh without the row passes changes the
collision through the converter's visible-tread rule: the build is refused in seconds, naming the mesh, instead of
stopping in the CHIM stage after minutes (the v0.0.57-dev4 build stopped on ex_de_ship in Vivec City).

The meshes are the staged ones of the reuse source run (chim-world/work/*/scenery: scenery-index.json and
scenery.mwpak); without a reuse source, or for a mesh no staged index holds, the row is reported as not checked and
the CHIM stage's own gate stays the check. Each result is cached by the row's key (SHA-256 of the row, the mesh's
packet SHA-256, the meshoptimizer source and this rule's version), so only a new or changed row costs time; the
measurements run on all the cores the build has.
"""
import hashlib
import json
import os
from pathlib import Path

RULE_VERSION = 'recipe-collision-1'
STEP = 8.5            # player_hull.STEP_HEIGHT: the gate's step
BUG = 'RECIPE-ROW-MOVES-COLLISION-57'


def gate_fails(rows):
    """The collision surface gate's verdict on measured variants (hull_surface_survey rows): True when one of them
    is over a step and not an excluded replaced ramp; None when nothing was measured."""
    rows = [r for r in rows if r and 'error' not in r]
    if not rows:
        return None
    return any(r['depth'] > STEP and not r['replaced'] for r in rows)


def decide(results):
    """{source: {'row': rows with the row, 'none': rows without}} -> (refused sources, unchecked sources).
    A row is refused when the gate fails with it and passes without it; a mesh that fails both ways is the
    mesh's own matter (the hull-surface table), not the row's."""
    refused, unchecked = [], []
    for source, r in sorted(results.items()):
        with_row, without = gate_fails(r.get('row') or []), gate_fails(r.get('none') or [])
        if with_row is None or without is None:
            unchecked.append(source)
        elif with_row and not without:
            refused.append(source)
    return refused, unchecked


def row_key(source, entry, meshopt_sha):
    text = json.dumps({'source': source, 'row': entry, 'meshopt': meshopt_sha, 'rule': RULE_VERSION}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


def staged_indexes(reuse_run):
    """{source: scenery folder} of the first staged index of the reuse source that holds each mesh."""
    where = {}
    for idx in sorted(Path(reuse_run).glob('chim-world/work/*/scenery/scenery-index.json')):
        try:
            models = json.loads(idx.read_text(encoding='utf-8')).get('models', [])
        except (OSError, ValueError):
            continue
        for m in models:
            where.setdefault(m['source'].replace('\\', '/').lower(), str(idx.parent))
    return where


def _measure(task):
    """One mesh both ways; a mesh that cannot be measured is reported as not checked (its error kept), never a
    crash of the preflight."""
    try:
        return _measure_one(task)
    except Exception as error:      # noqa: BLE001 - reported with its reason
        return task[0], {'row': [{'error': '%s: %s' % (type(error).__name__, str(error)[:200])}], 'none': []}


def _measure_one(task):
    """One mesh both ways, in a worker process (the everywhere recipe switched by AMIWIND_VISUAL_EVERYWHERE)."""
    source, folder = task
    from hull_surface_survey import measure
    index = json.loads((Path(folder) / 'scenery-index.json').read_text(encoding='utf-8'))
    archive = str(Path(folder) / 'scenery.mwpak')
    model = next(m for m in index['models'] if m['source'].replace('\\', '/').lower() == source)
    group = {}
    for g in (index.get('groups') or {}).values():
        if model['source'] in (g.get('visual_profiles') or {}):
            group = g['visual_profiles'][model['source']]
            break
    out = {}
    for side, env in (('row', 'on'), ('none', 'off')):
        before = os.environ.get('AMIWIND_VISUAL_EVERYWHERE')
        os.environ['AMIWIND_VISUAL_EVERYWHERE'] = env
        try:
            out[side] = [measure((model, archive, index.get('textures', []), group, flight, False, ('recipe', None)))
                         for flight in (False, True)]
        finally:
            if before is None:
                os.environ.pop('AMIWIND_VISUAL_EVERYWHERE', None)
            else:
                os.environ['AMIWIND_VISUAL_EVERYWHERE'] = before
    for side in out:
        for r in out[side]:
            r.pop('note', None)
    return source, out


def run(reuse_run, cache_dir, jobs, recipes=None, log=print):
    """Check the everywhere recipe's rows; returns the record (refused, unchecked, checked, cached). Raises
    ValueError naming every refused mesh."""
    from visual_recipes import load_recipes, everywhere_recipe
    from mesh_methods import meshopt_sha
    doc = recipes or load_recipes()
    name = everywhere_recipe(doc)
    record = {'rule': RULE_VERSION, 'bug': BUG, 'refused': [], 'unchecked': [], 'checked': 0, 'cached': 0}
    if not name:
        record['skipped'] = 'no everywhere recipe'
        return record
    rows = {k: e for k, e in doc['recipes'][name]['models'].items() if 'ratio' in e}
    sha = meshopt_sha()
    cache = Path(cache_dir)
    results, todo = {}, []
    where = staged_indexes(reuse_run) if reuse_run else {}
    for source, entry in sorted(rows.items()):
        key = row_key(source, entry, sha)
        hit = cache / (key + '.json')
        if hit.is_file():
            results[source] = json.loads(hit.read_text(encoding='utf-8'))
            record['cached'] += 1
        elif source in where:
            todo.append((source, where[source], key))
        else:
            record['unchecked'].append(source)
    log('Recipe collision preflight: %d rows, %d cached, %d to measure on %d workers, %d without a staged mesh'
        % (len(rows), record['cached'], len(todo), jobs, len(record['unchecked'])))
    if todo:
        from concurrent.futures import ProcessPoolExecutor
        cache.mkdir(parents=True, exist_ok=True)
        with ProcessPoolExecutor(max(1, jobs)) as pool:
            done = 0
            for (source, out), (_, _, key) in zip(pool.map(_measure, [(s, f) for s, f, _ in todo]), todo):
                results[source] = out
                tmp = cache / (key + '.tmp-%d' % os.getpid())
                tmp.write_text(json.dumps(out), encoding='utf-8', newline='\n')
                os.replace(tmp, cache / (key + '.json'))
                done += 1
                log('Recipe collision preflight: %d/%d %s' % (done, len(todo), source))
        record['checked'] = len(todo)
    refused, unchecked = decide(results)
    record['refused'] = refused
    record['unchecked'] = sorted(set(record['unchecked']) | set(unchecked))
    if refused:
        raise ValueError('Recipe collision preflight: the reduction row of %s changes the collision (the collision '
                         'surface gate fails with the row and passes without it; %s): take the row out of '
                         'config/visual-recipes.json' % (', '.join(refused), BUG))
    return record
