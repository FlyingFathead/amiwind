#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The model census (docs/MODEL_CENSUS.md): every model the game files place, its original triangles, what each of
AmiWind's mesh methods makes of it outdoors (the CHIM frames) and in the rooms, whether each method keeps the model
intact, and the method the builder uses today.

Everything is measured through the builder's own code, never a second implementation: the NIF reader the converter
uses (prepare_scenery.model_geometry), the profiles the CHIM frames and rooms start from
(world_estimate_data.exterior_profile, interior_profile; the flattening table), the method table
(config/mesh-methods.json, mesh_methods.apply), the everywhere recipe (config/visual-recipes.json,
visual_recipes.apply_recipe), method 2 (config/model-method-2.json, model_method2.row_for), the faces
(mesh_export.profile_faces) and the quality measures (mesh_methods.reduction_quality: the seam gate, the seam audit,
the shape error). Names, counts and paths only: no geometry and no texture data is written. The output is made from
your own game files: keep it private, or publish only its counts and model names.

One row per placed model: the records that use it, the archive it ships in, its NIF bytes and SHA-256, its placements
per land and space, its original triangles and texture repeats, and for each space it is placed in (outdoors, rooms)
the profile, one column per method (current = the converter's faces, merge, meshopt+merge, row = the everywhere
recipe's row, method 2 = the hand-made mesh) with faces, triangles and quality, the method in use, and the flags
heavier_than_original and row_heavier. A model with nothing static to count is a special case, marked by kind.

    python3 tools/model_census.py run --data-files DIR --out DIR [--jobs N] [--no-quality] [--limit N]
                                      [--models A,B] [--cache DIR] [--build-name NAME] [--build-commit SHA]
    python3 tools/model_census.py check CENSUS.json             the schema and the counts; exit 1 on a problem
    python3 tools/model_census.py diff PREVIOUS.json CENSUS.json
        the models that gained triangles since PREVIOUS and the new heavier-than-original ones; exit 1 when any
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first (as every tool: src/mwad before tools/mwad.py)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

FORMAT = 'amiwind-model-census-1'
LANDS = {'Morrowind.esm': 'Vvardenfell', 'Tribunal.esm': 'Mournhold', 'Bloodmoon.esm': 'Solstheim'}
SPACES = ('outdoors', 'rooms')
COLUMNS = ('current', 'merge', 'meshopt+merge', 'row', 'method 2')
DEFAULT_COLUMN = {'outdoors': 'merge', 'rooms': 'current'}
SPECIAL_KINDS = ('editor marker', 'particle effect', 'animated or skinned', 'nothing drawn', 'missing', 'unreadable')
QUALITY_KEYS = ('new_open', 'lost_open', 'seam_torn', 'rim_torn', 'shape_error')
REPEAT_LIMITS = (16, 64)
SWITCH = 'AMIWIND_MODEL_CENSUS'             # off: the build step is skipped; on: it runs in MiniWind builds too
CACHE_VERSION = 1
# the code every number passes through: part of each cached row's key and of the census record (code_sha256)
CODE = ('tools/model_census.py', 'tools/mesh_export.py', 'tools/mesh_methods.py', 'tools/planar_merge.py',
        'tools/static_lod.py', 'tools/meshopt.py', 'tools/seam_audit.py', 'tools/mesh_geometry.py',
        'tools/visual_primitives.py', 'tools/surface_flatten.py', 'tools/town_regions.py', 'tools/prepare_scenery.py',
        'tools/visual_recipes.py', 'tools/model_method2.py', 'tools/world_estimate_data.py')
TABLES = ('config/mesh-methods.json', 'config/visual-recipes.json', 'config/model-method-2.json',
          'config/chim-rooms.json', 'config/surface-flattening.json')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def files_sha256(names, root=ROOT):
    """{name: SHA-256 of the file, or 'missing'} and the SHA-256 over them all (in this order)."""
    each = {}
    for name in names:
        p = Path(root) / name
        each[name] = _sha(p.read_bytes()) if p.is_file() else 'missing'
    return each, _sha(json.dumps(each, sort_keys=True).encode('utf-8'))


# ------------------------------------------------------------------ the masters: who places what, where

def in_game_names(data_files):
    """{record id: in-game name (FNAM)} of every object record, later masters win."""
    import world_estimate_data as D
    from mwad.paths import child_ci
    out = {}
    for master in D.MASTERS:
        p = child_ci(Path(data_files), master, required=False)
        if p is None or not p.is_file():
            continue
        for tag, _, payload in D.records(p.read_bytes()):
            if tag not in D.OBJECT_TAGS:
                continue
            s = {}
            for k, v in D.subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' in s and 'FNAM' in s:
                out[D.cstr(s['NAME']).casefold()] = D.cstr(s['FNAM'])
    return out


def placements_of(masters, names=None):
    """({model: Counter({'<land> <space>': placements})}, {model: {record id: (type, in-game name)}}) of parsed masters
    (world_estimate_data.census). Deleted cells, deleted references and records without a model are left out; an
    expansion's copy of a base-game cell is left out too (it repeats the base cell's references)."""
    import world_estimate_data as D
    names = names or {}
    base = masters['Morrowind.esm']['cells']
    base_rooms = {c['name'].casefold() for c in base if c['interior']}
    base_land = {(c['x'], c['y']) for c in base if not c['interior']}
    placed = collections.defaultdict(collections.Counter)
    users = collections.defaultdict(dict)
    objects = {}
    for master in D.MASTERS:
        if master not in masters:
            continue
        objects.update(masters[master]['objects'])
        for c in masters[master]['cells']:
            if c['deleted']:
                continue
            if master != 'Morrowind.esm' and (c['name'].casefold() in base_rooms if c['interior']
                                              else (c['x'], c['y']) in base_land):
                continue
            space = 'rooms' if c['interior'] else 'outdoors'
            for r in c['refs']:
                if r.get('del'):
                    continue
                o = objects.get(r['id'])
                if not o or not o['model'] or o.get('deleted'):
                    continue
                placed[o['model']]['%s %s' % (LANDS[master], space)] += 1
                users[o['model']][r['id']] = (o['type'], names.get(r['id'], ''))
    return placed, users


def space_totals(where):
    """{'outdoors': n, 'rooms': n} of a row's placements by land and space."""
    out = {s: 0 for s in SPACES}
    for key, n in where.items():
        out[key.rsplit(' ', 1)[1]] += n
    return out


# ------------------------------------------------------------------ one model, through the builder's code

_STATE = {}


def load_tables():
    """The builder's tables and switches, as a build reads them (environment included)."""
    from chim.interior import everywhere_in_rooms
    from mesh_methods import load as load_methods
    from model_method2 import load_table, method_setting
    from scenery_selection import load_groups
    from surface_flatten import load_profiles
    from visual_recipes import everywhere_recipe, load_recipes
    recipes = load_recipes()
    groups = {}
    for name, group in sorted(load_groups().items()):
        for model, profile in sorted((group.get('visual_profiles') or {}).items()):
            groups.setdefault(model.replace('\\', '/').lower(), (name, dict(profile)))
    return {'methods': load_methods(), 'recipes': recipes, 'everywhere': everywhere_recipe(recipes), 'groups': groups,
            'everywhere_in_rooms': everywhere_in_rooms(), 'method2': load_table(), 'model_method': method_setting(),
            'flatten': {'outdoors': load_profiles(scene_kind='exterior'), 'rooms': load_profiles(scene_kind='interior')}}


def _state(data_files):
    if _STATE.get('data') != data_files:
        from world_estimate_data import MeshSource
        _STATE.clear()
        _STATE.update(data=data_files, source=MeshSource(data_files), tables=load_tables())
    return _STATE


def special_kind(source, error):
    """(kind, why) of a model the converter cannot read as static triangles."""
    stem = source.rsplit('/', 1)[-1]
    if stem.startswith('editormarker'):
        return 'editor marker', 'invisible in the game, nothing drawn'
    if any(w in stem for w in ('particle', 'spray', 'steam', 'mist', 'smoke', 'dust')):
        return 'particle effect', 'drawn as particles, no triangles'
    if 'static triangles' in error:
        return 'animated or skinned', 'not static geometry (counted by the creature and NPC tools)'
    return 'unreadable', error


def triangles_of(polys):
    """The triangles a face list draws (a convex face of k corners is k - 2 triangles)."""
    return int(sum(max(len(p) - 2, 0) for p, _ in polys))


def texture_repeats(vertices, faces, materials):
    """THE REPEAT CATCHER (docs/MODEL_CENSUS.md): how often a triangle repeats its texture, as the larger of its
    texture coordinates' two spans (1 = the texture once across the triangle). The largest, its texture, and the count
    of triangles over each of REPEAT_LIMITS."""
    import numpy as np
    uv = np.asarray(vertices, float)[np.asarray(faces, int)[:, :3], 3:5]
    span = (uv.max(axis=1) - uv.min(axis=1)).max(axis=1)
    worst = int(np.argmax(span))
    mat = int(faces[worst][3]) if len(faces[worst]) > 3 else 0
    texture = (materials[mat] or {}).get('texture_source') if mat < len(materials or []) else None
    out = {'repeat_max': round(float(span[worst]), 1),
           'repeat_texture': Path(str(texture).replace('\\', '/')).name.lower() if texture else None}
    for limit in REPEAT_LIMITS:
        out['repeat_over_%d' % limit] = int((span > limit).sum())
    return out


def _quality(v, f, rv, rf, memo):
    """mesh_methods.reduction_quality, measured once per distinct drawn mesh (current and merge share theirs); an
    unchanged mesh is exactly 0 without measuring."""
    import numpy as np
    if rv.shape == v.shape and rf.shape == f.shape and np.array_equal(rv, v) and np.array_equal(rf, f):
        return {'new_open': 0, 'lost_open': 0, 'seam_torn': 0.0, 'rim_torn': 0.0, 'shape_error': 0.0}
    key = _sha(np.ascontiguousarray(rv).tobytes() + b'|' + np.ascontiguousarray(rf).tobytes())
    if key not in memo:
        from mesh_methods import reduction_quality
        memo[key] = reduction_quality(v, f, rv, rf)
    return dict(memo[key])


def nif_sizes(data_files, names):
    """{model: its NIF's bytes} as the game files hold it (a loose file first, then the archives), from the
    directories only; a model not found counts 0."""
    from world_estimate_data import MeshSource
    source = MeshSource(data_files)
    out = {}
    for name in names:
        if name in source.loose:
            out[name] = source.loose[name].stat().st_size
            continue
        entry = next((b.entries[name] for b in source.bsas if name in b.entries), None)
        out[name] = int(entry['bytes']) if entry else 0
    return out


def _profile_summary(profile):
    return {'ratio': round(float(profile['ratio']), 4) if profile.get('ratio') else 1.0,
            'texture_size': int(profile.get('texture_size', 64)),
            **({'flatten': True} if profile.get('flatten') else {})}


def space_row(v, f, materials, model, space, tables, quality):
    """One space's columns, method in use and flags (module text)."""
    from mesh_export import profile_faces
    from mesh_methods import apply as apply_method, method_of
    from model_method2 import row_for
    from visual_recipes import apply_recipe
    from world_estimate_data import exterior_profile, interior_profile
    source, n = model['source'], len(f)
    group = tables['groups'].get(source) if space == 'outdoors' else None
    if group:
        # a named scenery group's own profile (config/scenery_groups.json: the arrival ship, the silt strider), as the
        # area that places the group reads it alone (chim.seyda)
        base = dict(group[1])
    else:
        base = dict(exterior_profile(source, n) if space == 'outdoors' else interior_profile(source, n))
    flat = tables['flatten'][space].get(source)
    if flat:
        base['flatten'] = flat
    memo, columns = {}, {}

    def column(profile):
        polys, rv, rf = profile_faces(v, f, materials, profile, source)
        out = {'faces': len(polys), 'triangles': triangles_of(polys)}
        if quality:
            out.update(_quality(v, f, rv, rf, memo))
        return out
    columns['current'] = column({k: x for k, x in base.items() if k != 'faces'})
    columns['merge'] = column(dict(base, faces='merge'))
    reduces = bool(base.get('ratio') and base['ratio'] < 1)
    if reduces:
        columns['meshopt+merge'] = column(apply_method(base, source, {'mesh_method': 'meshopt+merge'}))
    # method 1 as the builder applies it: outdoors the method table (chim.build apply_mesh_method), rooms the room
    # converter's own faces (chim.interior: no table; planar merge only for its merge_faces list)
    if space == 'outdoors':
        method1 = apply_method(base, source, None, tables['methods'])
        named = method_of(source, None, tables['methods'])
        in_use = {'converter': 'current', 'merge': 'merge'}.get(named, 'meshopt+merge' if reduces else 'merge')
    else:
        method1, in_use = base, 'current'
    default = in_use
    recipe = tables['everywhere'] if (space == 'outdoors' or tables['everywhere_in_rooms']) else None
    if recipe:
        profile = apply_recipe(method1, model, recipe, tables['recipes'])
        if 'visual_recipe' in profile:
            entry = tables['recipes']['recipes'][recipe]['models'].get(source, {})
            kind = next((k for k in ('primitive', 'panel', 'ratio', 'collision_tolerance') if k in entry), 'row')
            columns['row'] = dict(column(profile), recipe=recipe, kind=kind)
            in_use = 'row'
    row2 = row_for(model, tables['method2'])
    if row2 is not None:
        counts = row2.get('counts', {})
        faces = (counts.get('faces_outdoors') if space == 'outdoors'
                 else counts.get('faces_rooms', counts.get('faces_after')))
        columns['method 2'] = {'faces': faces, 'triangles': counts.get('triangles'), 'recorded': True,
                               'kind': row2['kind'], 'row_method': row2['method'],
                               'open_edges_before': counts.get('open_edges_before'),
                               'open_edges': counts.get('open_edges')}
        if row2['method'] == 2 and tables['model_method'] == 2:
            in_use = 'method 2'
    today = {'faces': columns[in_use]['faces'], 'triangles': columns[in_use]['triangles']}
    summary = _profile_summary(base)
    if group:
        summary['group'] = group[0]
    return {'profile': summary, 'in_use': in_use, 'default': default, 'columns': columns,
            'today': today, 'heavier_than_original': bool(today['triangles'] is not None and today['triangles'] > n),
            'row_heavier': bool(in_use != default and today['triangles'] is not None
                                and today['triangles'] > columns[default]['triangles'])}


def model_row(task):
    """The census row of one model (without its placements and records, which the caller adds); never raises."""
    import numpy as np
    from mwad.scene import unpack_geometry
    from prepare_scenery import bsa_read, model_geometry, nif_reader
    data_files, source, spaces, quality, cache = task
    st = _state(data_files)
    src = st['source']
    row = {'model': source}
    try:
        raw, where = src.read(source)
    except (OSError, ValueError, KeyError) as exc:
        return dict(row, status='special', special={'kind': 'missing', 'why': ('%s' % exc)[:160]})
    bsa = next((b for b in src.bsas if source in b.entries), None)
    shipped = bsa.path.name if bsa else 'loose only'
    if where == 'loose' and bsa is not None and raw != bsa_read(bsa, source):
        shipped += ' (loose copy differs)'
    row.update(file=shipped, nif_bytes=len(raw), nif_sha256=_sha(raw))
    key = None
    if cache:
        key = _sha(json.dumps([CACHE_VERSION, cache['code'], cache['tables'], cache['settings'], source,
                               row['nif_sha256'], sorted(s for s in SPACES if spaces.get(s)), bool(quality)]).encode())
        hit = Path(cache['dir']) / key[:2] / (key + '.json')
        if hit.is_file():
            try:
                return dict(json.loads(hit.read_text(encoding='utf-8')), file=shipped, cached=True)
            except ValueError:
                pass
    try:
        packet, materials, bounds, _ = model_geometry(raw, nif_reader(), repair_uv=True)
        vv, ff, _ = unpack_geometry(packet)
    except Exception as exc:  # noqa: BLE001 - a reader failure is a per-model special case
        kind, why = special_kind(source, ('%s: %s' % (type(exc).__name__, exc))[:160])
        row.update(status='special', special={'kind': kind, 'why': why})
        return _store(row, key, cache)
    v, f = np.array(vv, float), np.array(ff, int)
    if not len(f):
        row.update(status='special', special={'kind': 'nothing drawn', 'why': 'no triangles'})
        return _store(row, key, cache)
    model = {'source': source, 'sha256': _sha(packet), 'source_sha256': row['nif_sha256']}
    original = {'triangles': int(len(f)),
                'size_mw': [round(float(bounds[1][i] - bounds[0][i]), 1) for i in range(3)] if bounds else None,
                **texture_repeats(v, f, materials)}
    try:
        out = {s: space_row(v, f, materials, model, s, st['tables'], quality) for s in SPACES if spaces.get(s)}
    except Exception as exc:  # noqa: BLE001 - a method that fails on one model is that model's finding
        row.update(status='special', original=original,
                   special={'kind': 'unreadable', 'why': ('method failed: %s: %s' % (type(exc).__name__, exc))[:160]})
        return _store(row, key, cache)
    row.update(status='ok', original=original, spaces=out)
    return _store(row, key, cache)


def _store(row, key, cache):
    if key:
        target = Path(cache['dir']) / key[:2] / (key + '.json')
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(target.name + '.part%d' % os.getpid())
            part.write_text(json.dumps(row, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
            os.replace(part, target)
        except OSError:
            pass                              # a cache that cannot be written only costs time next build
    return row


# ------------------------------------------------------------------ the whole census

def census(data_files, jobs=None, quality=True, limit=None, models=None, cache_dir=None, build=None, log=print):
    """The census document of the game files (module text)."""
    import world_estimate_data as D
    from build_parallel import ordered_map
    started = time.monotonic()
    log('=== PHASE 1/3: the masters (placements per land and space, records, names) ===')
    masters = D.census(data_files)
    placed, users = placements_of(masters, in_game_names(data_files))
    names = sorted(placed)
    if models:
        wanted = {m.replace('\\', '/').lower() for m in models}
        names = [n for n in names if n in wanted]
    if limit:
        names = names[:limit]
    code, code_sha = files_sha256(CODE)
    tables, tables_sha = files_sha256(TABLES)
    t = load_tables()
    settings = {'everywhere': t['everywhere'], 'everywhere_in_rooms': t['everywhere_in_rooms'],
                'model_method': t['model_method'], 'quality': bool(quality)}
    cache = ({'dir': str(cache_dir), 'code': code_sha, 'tables': tables_sha, 'settings': settings}
             if cache_dir else None)
    log('  %d placed models, %d placements (%.1f s)' % (len(names), sum(sum(placed[n].values()) for n in names),
                                                         time.monotonic() - started))
    log('=== PHASE 2/3: every model through the builder\'s mesh code (%s) ===' % (
        'faces, triangles and quality' if quality else 'faces and triangles'))
    tasks = [(str(data_files), n, space_totals(placed[n]), quality, cache) for n in names]
    size = nif_sizes(data_files, names)
    rows, hits, last = [], 0, time.monotonic()
    # largest NIF first (a model's work grows with its triangles), so the heavy models do not finish alone at the end
    for i, row in enumerate(ordered_map(model_row, tasks, jobs, cost=lambda t: size.get(t[1], 0))):
        hits += bool(row.pop('cached', False))
        where = dict(sorted(placed[row['model']].items()))
        records = sorted(users[row['model']].items())
        row.update(placements=where, placed=space_totals(where), record_count=len(records),
                   records=[{'id': r, 'type': typ, 'name': nm} for r, (typ, nm) in records[:12]])
        rows.append(row)
        now = time.monotonic()
        if now - last >= 5 or i + 1 == len(tasks):
            el = now - started
            log('  %d/%d models, %d reused from the cache (%.0f s, about %.0f s left)' % (
                i + 1, len(tasks), hits, el, el / (i + 1) * (len(tasks) - i - 1)))
            last = now
    log('=== PHASE 3/3: the totals, the catchers and the checks ===')
    doc = {'format': FORMAT, 'code_sha256': code_sha, 'code': code, 'tables_sha256': tables_sha, 'tables': tables,
           'inputs': {k: v['sha256'] for k, v in sorted(masters.items())}, 'settings': settings,
           'build': build or None, 'models': rows}
    doc['summary'] = summarise(rows)
    return doc


def summarise(rows):
    """The totals per space, method and land, the catchers' lists and the special cases (one pass over the rows)."""
    spaces = {s: {'models': 0, 'placements': 0, 'original': 0, 'today': 0, 'by_method': {}} for s in SPACES}
    lands = collections.defaultdict(lambda: {'placements': 0, 'original': 0, 'today': 0})
    special = collections.Counter()
    heavier, row_heavier, intact, repeats = [], [], [], []
    for r in rows:
        if r['status'] != 'ok':
            special[r['special']['kind']] += 1
            continue
        o = r['original']['triangles']
        if r['original'].get('repeat_over_64'):
            repeats.append({'model': r['model'], 'repeat_max': r['original']['repeat_max'],
                            'texture': r['original'].get('repeat_texture'),
                            'over_16': r['original']['repeat_over_16'], 'over_64': r['original']['repeat_over_64']})
        for space, s in r['spaces'].items():
            n = r['placed'][space]
            tri = s['today']['triangles'] or 0
            t = spaces[space]
            t['models'] += 1
            t['placements'] += n
            t['original'] += o * n
            t['today'] += tri * n
            m = t['by_method'].setdefault(s['in_use'], {'models': 0, 'original': 0, 'today': 0})
            m['models'] += 1
            m['original'] += o * n
            m['today'] += tri * n
            for key, k in r['placements'].items():
                if key.endswith(' ' + space):
                    land = lands[key.rsplit(' ', 1)[0]]
                    land['placements'] += k
                    land['original'] += o * k
                    land['today'] += tri * k
            if s['heavier_than_original']:
                heavier.append({'model': r['model'], 'space': space, 'method': s['in_use'], 'original': o,
                                'today': tri, 'placed': n, 'added_placed': (tri - o) * n})
            if s['row_heavier']:
                row_heavier.append({'model': r['model'], 'space': space, 'method': s['in_use'], 'with': tri,
                                    'without': s['columns'][s['default']]['triangles'], 'default': s['default'],
                                    'placed': n})
            q = s['columns'][s['in_use']]
            if any(q.get(k) for k in ('new_open', 'lost_open', 'seam_torn', 'rim_torn')):
                # a replacement (a primitive, a panel, a hand-made mesh) is another shape: its edges are compared
                # with the source's too, and listed after the reductions
                intact.append({'model': r['model'], 'space': space, 'method': s['in_use'], 'placed': n,
                               'replacement': bool(s['in_use'] == 'method 2' or q.get('kind') in ('primitive', 'panel')
                                                   or s['profile'].get('flatten')),
                               **{k: q.get(k) for k in QUALITY_KEYS}})
    heavier.sort(key=lambda x: (-x['added_placed'], x['model'], x['space']))
    row_heavier.sort(key=lambda x: (-(x['with'] - x['without']) * x['placed'], x['model'], x['space']))
    intact.sort(key=lambda x: (x['replacement'], -x['placed'], x['model'], x['space']))
    repeats.sort(key=lambda x: (-x['repeat_max'], x['model']))
    total = {k: sum(spaces[s][k] for s in SPACES) for k in ('placements', 'original', 'today')}
    return {'models': len(rows), 'counted': sum(r['status'] == 'ok' for r in rows), 'special': dict(sorted(special.items())),
            'total': total, 'spaces': spaces, 'lands': dict(sorted(lands.items())),
            'heavier_than_original': heavier, 'row_heavier': row_heavier, 'not_intact': intact,
            'repeats_over_64': repeats}


# ------------------------------------------------------------------ the schema check

def _count(x):
    return isinstance(x, int) and not isinstance(x, bool) and x >= 0


def check(doc):
    """The problems of a census document ([] = it holds): a missing field, an unknown method or kind, an impossible
    count (negative, a face list with fewer triangles than faces, placements that do not add up), a flag that does
    not follow from the counts, or totals that differ from the rows."""
    p = []
    if not isinstance(doc, dict) or doc.get('format') != FORMAT:
        return ['not a model census (format %r)' % (doc.get('format') if isinstance(doc, dict) else None)]
    for key in ('code_sha256', 'tables_sha256', 'inputs', 'settings', 'models', 'summary'):
        if key not in doc:
            p.append('missing field: %s' % key)
    if p:
        return p
    seen = set()
    for r in doc['models']:
        m = r.get('model')
        at = 'model %r' % m
        if not isinstance(m, str) or not m.startswith('meshes/') or m != m.lower():
            p.append('%s: model is not a lower-case meshes/ path' % at)
        if m in seen:
            p.append('%s: listed twice' % at)
        seen.add(m)
        where = r.get('placements')
        if not isinstance(where, dict) or not all(_count(n) for n in where.values()):
            p.append('%s: placements missing or not counts' % at)
            continue
        if any(k.rsplit(' ', 1)[-1] not in SPACES or k.rsplit(' ', 1)[0] not in LANDS.values() for k in where):
            p.append('%s: a placement key is not "<land> <space>"' % at)
            continue
        if r.get('placed') != space_totals(where):
            p.append('%s: placed per space does not add up to the placements' % at)
        if r.get('status') == 'special':
            if (r.get('special') or {}).get('kind') not in SPECIAL_KINDS:
                p.append('%s: special case without a known kind' % at)
            continue
        if r.get('status') != 'ok':
            p.append('%s: status %r' % (at, r.get('status')))
            continue
        for key in ('file', 'nif_bytes', 'nif_sha256', 'original', 'spaces'):
            if key not in r:
                p.append('%s: missing field %s' % (at, key))
        if not all(k in r for k in ('original', 'spaces')):
            continue
        o = r['original'].get('triangles')
        if not _count(o) or o == 0:
            p.append('%s: original triangles %r' % (at, o))
            continue
        for space in SPACES:
            if bool(r['placed'][space]) != (space in r['spaces']):
                p.append('%s: %s measured %s but placed %d times there' % (
                    at, space, 'and' if space in r['spaces'] else 'not', r['placed'][space]))
        for space, s in r['spaces'].items():
            sat = '%s %s' % (at, space)
            cols = s.get('columns') or {}
            if s.get('in_use') not in COLUMNS or s.get('in_use') not in cols:
                p.append('%s: method in use %r is not one of its columns' % (sat, s.get('in_use')))
                continue
            if s.get('default') not in cols:
                p.append('%s: default method %r is not one of its columns' % (sat, s.get('default')))
                continue
            for name, c in cols.items():
                if name not in COLUMNS:
                    p.append('%s: unknown method %r' % (sat, name))
                    continue
                faces, tris = c.get('faces'), c.get('triangles')
                if name == 'method 2' and c.get('recorded'):
                    if tris is not None and not _count(tris):
                        p.append('%s: method 2 triangles %r' % (sat, tris))
                    continue
                if not _count(faces) or not _count(tris):
                    p.append('%s %s: faces / triangles %r / %r' % (sat, name, faces, tris))
                elif tris < faces:
                    p.append('%s %s: %d triangles cannot make %d faces' % (sat, name, tris, faces))
            today = s.get('today') or {}
            used = cols[s['in_use']]
            if today.get('faces') != used.get('faces') or today.get('triangles') != used.get('triangles'):
                p.append('%s: today differs from its method %s' % (sat, s['in_use']))
            tri = today.get('triangles')
            if s.get('heavier_than_original') != bool(tri is not None and tri > o):
                p.append('%s: heavier_than_original does not follow from %r > %d' % (sat, tri, o))
            want = bool(s['in_use'] != s['default'] and tri is not None and tri > cols[s['default']]['triangles'])
            if s.get('row_heavier') != want:
                p.append('%s: row_heavier does not follow from the counts' % sat)
    if not p:
        again = summarise(doc['models'])
        for key in ('total', 'spaces', 'lands', 'special'):
            if json.loads(json.dumps(again[key])) != doc['summary'].get(key):
                p.append('summary %s differs from the rows' % key)
    return p


# ------------------------------------------------------------------ build to build

def diff(previous, current):
    """{'gained': model/space pairs that draw more triangles than in PREVIOUS (a regression: stops a delivery until
    explained), 'new_heavier': heavier-than-original pairs PREVIOUS did not have, 'changed': every pair whose count
    changed, 'new_models', 'gone_models'}."""
    def pairs(doc):
        return {(r['model'], s): v for r in doc['models'] if r['status'] == 'ok' for s, v in r['spaces'].items()}
    a, b = pairs(previous), pairs(current)
    changed = []
    for key in sorted(set(a) & set(b)):
        before, after = a[key]['today']['triangles'], b[key]['today']['triangles']
        if before != after:
            changed.append({'model': key[0], 'space': key[1], 'before': before, 'after': after,
                            'method_before': a[key]['in_use'], 'method_after': b[key]['in_use']})
    new_heavier = [{'model': k[0], 'space': k[1], 'method': b[k]['in_use'], 'today': b[k]['today']['triangles']}
                   for k in sorted(b) if b[k]['heavier_than_original'] and not (k in a and a[k]['heavier_than_original'])]
    old_models = {r['model'] for r in previous['models']}
    new_models = {r['model'] for r in current['models']}
    return {'gained': [c for c in changed if (c['after'] or 0) > (c['before'] or 0)], 'new_heavier': new_heavier,
            'changed': changed, 'new_models': sorted(new_models - old_models),
            'gone_models': sorted(old_models - new_models)}


# ------------------------------------------------------------------ the files

CSV_COLUMNS = ('model', 'space', 'placed', 'record_ids', 'names', 'file', 'nif_bytes', 'original_triangles',
               'ratio', 'texture_size', 'in_use', 'today_faces', 'today_triangles',
               *[c.replace(' ', '') + '_' + x for c in COLUMNS for x in ('faces', 'triangles')],
               *QUALITY_KEYS, 'heavier_than_original', 'row_heavier', 'repeat_max', 'repeat_over_16',
               'repeat_over_64', 'status', 'special')


def csv_text(doc):
    """One line per model and space (a special case: one line, space empty)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(CSV_COLUMNS)
    for r in doc['models']:
        common = {'model': r['model'], 'record_ids': ' '.join(x['id'] for x in r.get('records', [])),
                  'names': ' / '.join(sorted({x['name'] for x in r.get('records', []) if x['name']})[:4]),
                  'file': r.get('file', ''), 'nif_bytes': r.get('nif_bytes', ''), 'status': r['status'],
                  'special': (r.get('special') or {}).get('kind', '')}
        o = r.get('original') or {}
        common.update(original_triangles=o.get('triangles', ''), repeat_max=o.get('repeat_max', ''),
                      repeat_over_16=o.get('repeat_over_16', ''), repeat_over_64=o.get('repeat_over_64', ''))
        if r['status'] != 'ok':
            w.writerow([common.get(c, '') for c in CSV_COLUMNS])
            continue
        for space, s in r['spaces'].items():
            line = dict(common, space=space, placed=r['placed'][space], ratio=s['profile']['ratio'],
                        texture_size=s['profile']['texture_size'], in_use=s['in_use'],
                        today_faces=s['today']['faces'], today_triangles=s['today']['triangles'],
                        heavier_than_original=int(s['heavier_than_original']), row_heavier=int(s['row_heavier']))
            for name, c in s['columns'].items():
                line[name.replace(' ', '') + '_faces'] = c.get('faces')
                line[name.replace(' ', '') + '_triangles'] = c.get('triangles')
            used = s['columns'][s['in_use']]
            line.update({k: used.get(k) for k in QUALITY_KEYS})
            w.writerow(['' if line.get(c) is None else line.get(c) for c in CSV_COLUMNS])
    return buf.getvalue()


def _n(x):
    return '{:,}'.format(x) if isinstance(x, int) else ('-' if x is None else str(x))


def _share(a, b):
    return '%.1f %%' % (100.0 * a / b) if b else '-'


def markdown(doc, top=60):
    """The readable summary: totals, the catchers' lists, the heaviest models today, the special cases."""
    s = doc['summary']
    b = doc.get('build') or {}
    out = ['# Model census', '',
           'Made from the game files through the builder\'s own mesh code (`tools/model_census.py`; how to read it: '
           'docs/MODEL_CENSUS.md). Private: made from your own game files.', '',
           '- Build: %s (commit %s)' % (b.get('name') or '-', b.get('commit') or '-'),
           '- Census code SHA-256: `%s`; tables: `%s`' % (doc['code_sha256'][:16], doc['tables_sha256'][:16]),
           '- Settings: %s' % ', '.join('%s %s' % kv for kv in sorted(doc['settings'].items())),
           '- %d models placed, %d counted, special cases: %s' % (
               s['models'], s['counted'], ', '.join('%s %d' % kv for kv in s['special'].items()) or 'none'), '',
           '## Placed triangles, original against today', '',
           '| Space | Models | Placements | Original | Today | Today / original |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for space in SPACES:
        t = s['spaces'][space]
        out.append('| %s | %s | %s | %s | %s | %s |' % (space, _n(t['models']), _n(t['placements']), _n(t['original']),
                                                         _n(t['today']), _share(t['today'], t['original'])))
    out.append('| all | | %s | %s | %s | %s |' % (_n(s['total']['placements']), _n(s['total']['original']),
                                                  _n(s['total']['today']), _share(s['total']['today'], s['total']['original'])))
    out += ['', '| Space | Method in use | Models | Original | Today | Today / original |',
            '| --- | --- | ---: | ---: | ---: | ---: |']
    for space in SPACES:
        for method, m in sorted(s['spaces'][space]['by_method'].items()):
            out.append('| %s | %s | %s | %s | %s | %s |' % (space, method, _n(m['models']), _n(m['original']),
                                                             _n(m['today']), _share(m['today'], m['original'])))
    out += ['', '| Land | Placements | Original | Today | Today / original |', '| --- | ---: | ---: | ---: | ---: |']
    for land, t in s['lands'].items():
        out.append('| %s | %s | %s | %s | %s |' % (land, _n(t['placements']), _n(t['original']), _n(t['today']),
                                                   _share(t['today'], t['original'])))
    out += ['', '## Heavier than the original (%d model and space pairs; a failure by default)' % len(
        s['heavier_than_original']), '',
        '| Model | Space | Method | Original | Today | Placed | Added, placed |', '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    out += ['| `%s` | %s | %s | %s | %s | %s | %s |' % (h['model'], h['space'], h['method'], _n(h['original']),
                                                       _n(h['today']), _n(h['placed']), _n(h['added_placed']))
            for h in s['heavier_than_original'][:top]]
    out += ['', '## A row or override heavier than the model without it (%d)' % len(s['row_heavier']), '',
            '| Model | Space | Method | With it | Without (%s) | Placed |' % 'default', '| --- | --- | --- | ---: | ---: | ---: |']
    out += ['| `%s` | %s | %s | %s | %s (%s) | %s |' % (h['model'], h['space'], h['method'], _n(h['with']), _n(h['without']),
                                                       h['default'], _n(h['placed'])) for h in s['row_heavier'][:top]]
    out += ['', '## The method in use does not keep the model intact (%d)' % len(s['not_intact']), '',
            'A replacement (a primitive, a panel, a hand-made mesh) is another shape; its edges are compared with the '
            'source\'s as well and listed after the reductions.', '',
            '| Model | Space | Method | Placed | New open edges | Lost open edges | Torn seam | Torn rim | Shape error |',
            '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    out += ['| `%s` | %s | %s%s | %s | %s | %s | %s | %s | %s |' % (
        h['model'], h['space'], h['method'], ' (replacement)' if h['replacement'] else '', _n(h['placed']),
        _n(h['new_open']), _n(h['lost_open']), _n(h['seam_torn']), _n(h['rim_torn']), _n(h['shape_error']))
        for h in s['not_intact'][:top]]
    out += ['', '## Texture repeats over 64 on one triangle (%d models)' % len(s['repeats_over_64']), '',
            '| Model | Largest repeat | Texture | Triangles over 16 | Over 64 |', '| --- | ---: | --- | ---: | ---: |']
    out += ['| `%s` | %s | %s | %s | %s |' % (h['model'], h['repeat_max'], h['texture'] or '-', _n(h['over_16']),
                                             _n(h['over_64'])) for h in s['repeats_over_64'][:top]]
    ranked = sorted(((r['spaces'][sp]['today']['triangles'] or 0) * r['placed'][sp], r['model'], sp, r)
                    for r in doc['models'] if r['status'] == 'ok' for sp in r['spaces'])
    out += ['', '## The %d heaviest today, by triangles x placements' % top, '',
            '| Model | Space | Method | Original | Today | Placed | Today x placed | Ships in |',
            '| --- | --- | --- | ---: | ---: | ---: | ---: | --- |']
    for total, model, sp, r in sorted(ranked, key=lambda x: (-x[0], x[1], x[2]))[:top]:
        sr = r['spaces'][sp]
        out.append('| `%s` | %s | %s | %s | %s | %s | %s | %s |' % (
            model, sp, sr['in_use'], _n(r['original']['triangles']), _n(sr['today']['triangles']), _n(r['placed'][sp]),
            _n(total), r['file']))
    out += ['', '## Special cases (%d)' % sum(s['special'].values()), '',
            '| Model | Kind | Why | Placed |', '| --- | --- | --- | ---: |']
    out += ['| `%s` | %s | %s | %s |' % (r['model'], r['special']['kind'], r['special']['why'].replace('|', '/'),
                                         _n(sum(r['placements'].values())))
            for r in doc['models'] if r['status'] != 'ok']
    return '\n'.join(out) + '\n'


def write(doc, out_dir):
    """model-census.json, model-census.csv and MODEL_CENSUS.md in OUT_DIR; returns their paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {'json': out_dir / 'model-census.json', 'csv': out_dir / 'model-census.csv', 'md': out_dir / 'MODEL_CENSUS.md'}
    paths['json'].write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    paths['csv'].write_text(csv_text(doc), encoding='utf-8', newline='\n')
    paths['md'].write_text(markdown(doc), encoding='utf-8', newline='\n')
    return paths


def summary_lines(doc):
    s = doc['summary']
    lines = ['%d models placed, %d counted, %d special cases' % (s['models'], s['counted'], sum(s['special'].values()))]
    for space in SPACES:
        t = s['spaces'][space]
        lines.append('%s: placed triangles %s original, %s today (%s)' % (
            space, _n(t['original']), _n(t['today']), _share(t['today'], t['original'])))
    lines.append('heavier than the original: %d model and space pairs; rows or overrides heavier than without: %d; '
                 'method in use not intact: %d; models with a texture repeated over 64 times on one triangle: %d' % (
                     len(s['heavier_than_original']), len(s['row_heavier']), len(s['not_intact']),
                     len(s['repeats_over_64'])))
    return lines


def build_step(run, data_files, jobs=None, cache_dir=None, name=None, commit=None, log=print):
    """The builder's model census after a passed image (tools/build.py): RUN/model-census/ (the JSON, the CSV, the
    readable summary), its lines in the build log, and the catchers' counts as warnings. A measurement: never raises
    and never fails the build. Returns the summary, None when skipped or not made."""
    started = time.monotonic()
    try:
        if os.environ.get(SWITCH, '').strip().lower() == 'off':
            log('Model census: skipped (%s=off)' % SWITCH)
            return None
        from build_jobs import resolve_jobs
        count = resolve_jobs(jobs)
        log('Model census: started (%d workers: every placed model through the builder\'s mesh code)' % count)
        doc = census(data_files, jobs=count, cache_dir=cache_dir, build={'name': name, 'commit': commit},
                     log=lambda line: log('Model census: ' + line.strip()))
        paths = write(doc, Path(run) / 'model-census')
        for line in summary_lines(doc):
            log('Model census: ' + line)
        problems = check(doc)
        for line in problems[:20]:
            log('Model census: WARNING: schema: ' + line)
        if doc['summary']['heavier_than_original']:
            log('Model census: WARNING: %d model and space pairs are converted heavier than the original (a failure '
                'by default; the list: %s)' % (len(doc['summary']['heavier_than_original']), paths['md']))
        log('Model census: written %s (took %.1f s)' % (paths['json'].parent, time.monotonic() - started))
        return doc['summary']
    except Exception as exc:  # noqa: BLE001 - a measurement; the build's own stages passed
        log('Model census: not made: %s: %s' % (type(exc).__name__, exc))
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='make the census')
    r.add_argument('--data-files', required=True, type=Path, help='your own Morrowind Data Files folder')
    r.add_argument('--out', required=True, type=Path)
    r.add_argument('--jobs', type=int)
    r.add_argument('--no-quality', action='store_true', help='faces and triangles only (no seam and shape measures)')
    r.add_argument('--limit', type=int, help='the first N models only (by path)')
    r.add_argument('--models', help='comma list of model paths (meshes/...)')
    r.add_argument('--cache', type=Path, help='a folder of per-model results to reuse (keyed by NIF, code and tables)')
    r.add_argument('--build-name')
    r.add_argument('--build-commit')
    c = sub.add_parser('check', help='check a census against its schema and counts')
    c.add_argument('census', type=Path)
    d = sub.add_parser('diff', help='compare a census with a previous one')
    d.add_argument('previous', type=Path)
    d.add_argument('census', type=Path)
    d.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    if a.cmd == 'run':
        build = {'name': a.build_name, 'commit': a.build_commit} if (a.build_name or a.build_commit) else None
        doc = census(a.data_files, jobs=a.jobs, quality=not a.no_quality, limit=a.limit,
                     models=[m.strip() for m in a.models.split(',') if m.strip()] if a.models else None,
                     cache_dir=a.cache, build=build, log=lambda line: print(line, flush=True))
        paths = write(doc, a.out)
        for line in summary_lines(doc):
            print(line)
        problems = check(doc)
        for line in problems:
            print('SCHEMA: ' + line)
        print('written: %s' % ', '.join(str(x) for x in paths.values()))
        return 1 if problems else 0
    if a.cmd == 'check':
        problems = check(json.loads(a.census.read_text(encoding='utf-8')))
        for line in problems:
            print('SCHEMA: ' + line)
        print('Model census check: %s' % ('holds' if not problems else '%d problem(s)' % len(problems)))
        return 1 if problems else 0
    out = diff(json.loads(a.previous.read_text(encoding='utf-8')), json.loads(a.census.read_text(encoding='utf-8')))
    if a.json:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        for g in out['gained']:
            print('GAINED: %s (%s) %s -> %s triangles (%s -> %s)' % (g['model'], g['space'], g['before'], g['after'],
                                                                    g['method_before'], g['method_after']))
        for h in out['new_heavier']:
            print('NEW HEAVIER THAN THE ORIGINAL: %s (%s, %s) %s triangles' % (h['model'], h['space'], h['method'],
                                                                             h['today']))
        print('Model census diff: %d changed, %d gained, %d new heavier than the original, %d new models, %d gone' % (
            len(out['changed']), len(out['gained']), len(out['new_heavier']), len(out['new_models']),
            len(out['gone_models'])))
    return 1 if (out['gained'] or out['new_heavier']) else 0


if __name__ == '__main__':
    sys.exit(main())
