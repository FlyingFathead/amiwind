#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM Progress Tracker: one record per exterior cell, filled from what the project already measures.

The tracker is a layer of the AmiWind Toolkit (docs/AMIWIND_TOOLKIT.md, "CHIM Progress Tracker"). This is its
ingester and the ONLY writer of the progress data: builds, audit jobs and the owner all go through it.

Inputs (all optional; anything missing is "not measured", never guessed):
  --progress  world-progress.json      the legacy mapping quality per cell (what is mapped, what share is placed)
  --metrics   world-metrics.json       the estimator's limits per cell (risk and cost, from tools/world_metrics.py)
  --cells     island-cells.json        place and region names
  --census    mesh-census.json        what each cell holds (written by --data-files DIR from your own Morrowind files)
  --chim-run  NAME=PATH               a CHIM world build folder (chim_build --validate --stats); repeatable
  --bugs      docs/bugs/bugs.json     the bug register, linked to cells by area name or coordinates
  --ledger    build-ledger.jsonl      the build and perf ledger: the last build per area
  --areas     config/cell-progress-areas.json   area names used to link bugs and builds to cells
  OUT/audits/*.json                    audit results from other tools (format aw-cell-audit-1), see `record`
  OUT/results/*.json                   per-cell conversion results (format aw-cell-result-1), see `result`
  OUT/owner-status.json                playtested / approved cells, see `owner`

Outputs in OUT (a private folder: the data is derived from the owner's game files):
  cell-progress.json   the tracker data the Toolkit loads (format aw-cell-progress-1)
  next.json            the sweep orders: spiral (coast inwards) and risk (scout list), cells not yet converted
  mesh-curve.json      the store-once mesh reuse curve; mesh-curve.png the same as a picture
  history.jsonl        one line whenever the counts changed; runs/NAME.json one digest per CHIM build

Usage:
  cell_progress.py ingest --out DIR [inputs...] [--data-files DIR] [--png]
  cell_progress.py record --out DIR --mechanism ID --build NAME (--results FILE | --status passed|failed --cells "x,y ...")
  cell_progress.py owner  --out DIR --status playtested|approved --cells "x,y ..." [--note TEXT]
  cell_progress.py result --out DIR --file RESULT.json     (the conversion job's per-cell stats, audits, errors)
  cell_progress.py export --out DIR [--csv FILE] [--json FILE]
  cell_progress.py status --out DIR
"""
import argparse
import collections
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cell_progress_chim as CH  # noqa: E402
import cell_progress_order as OR  # noqa: E402

FORMAT = 'aw-cell-progress-1'
AUDIT_FORMAT = 'aw-cell-audit-1'
CENSUS_FORMAT = 'aw-cell-census-1'
OUT_FILES = {'progress': 'cell-progress.json', 'next': 'next.json', 'curve': 'mesh-curve.json', 'png': 'mesh-curve.png',
             'history': 'history.jsonl', 'owner': 'owner-status.json', 'sources': 'sources.json'}
NEXT_LIMIT = 300

# Audit mechanisms: id -> label. Order is the display order.
MECHANISMS = collections.OrderedDict([
    ('format_validation', 'World format validation'),
    ('stair_walk', 'Stair walk'),
    ('memory_fit', 'Memory fit (zone ring / heap)'),
    ('seam_tears', 'Seam tears'),
    ('hull_bevels', 'Hull bevels / hull chain length'),
    ('sky_bank_texels', 'Sky-bank texels'),
    ('hidden_faces', 'Hidden faces'),
    ('far_terrain', 'Far-terrain coverage'),
    ('sprite_shape', 'Sprite shape'),
    ('actor_grounding', 'Actor grounding'),
    ('door_links', 'Doors / interior links'),
])
RESULTS = ('passed', 'failed', 'accepted', 'not_measured')   # accepted = failed but owner-accepted
OWNER_STATES = ('playtested', 'approved')
BUCKETS = ('complete', 'terrain_complete', 'approved', 'playtested', 'audits_passed', 'converted_failing', 'not_converted', 'converted_unmeasured', 'not_started',
           'empty_sea', 'hull_policy_pending')
# SUCCESS = every bucket that counts as passed (complete cells included). Precedence of the statuses, strongest first:
# complete > terrain_complete > approved > playtested > passed (audits_passed) > hull policy pending > failed > not converted.
SUCCESS = ('complete', 'terrain_complete', 'approved', 'playtested', 'audits_passed')
# Two completion levels (owner, 2026-10-09). Terrain complete: all audits pass and every placed object except actors is
# converted (actors may still be deferred). Cell complete: terrain complete and every actor converted too.
COMPLETE_LABEL = 'Cell complete'
TERRAIN_COMPLETE_LABEL = 'Terrain complete'
ACTOR_CATEGORIES = ('npcs', 'creatures')
# Nonvisual markers (door/travel/north/editor markers) are not drawn and not required: they never block either completion
# level (owner, 2026-10-09). Door destinations come from the door records. They stay in the by-type table.
MARKERS_BLOCK_COMPLETE = False
ISLAND_NAMES = {1: 'Vvardenfell', 2: 'Solstheim'}
# Audit outcome "kept as chain for memory": meshes the heap fallback deliberately left as hull chains. It passes. The result
# file marks it with outcome == KEPT_CHAIN_OUTCOME on the audit (PLACEHOLDER name until the conversion job fixes its field).
KEPT_CHAIN_OUTCOME = 'kept_as_chain'
OUTCOME_LABELS = {KEPT_CHAIN_OUTCOME: 'kept as chain for memory'}
HULL_CHAIN_DEPTH_LIMIT = 256     # standing-hull chain depth at or above this fails the hull audit (the conversion job's rule)
# Metrics that count for the risk score (lights are a "what if every light were dynamic" figure, not a limit).
RISK_EXCLUDE = ('lights',)
ITEM_TYPES = ('MISC', 'WEAP', 'ARMO', 'CLOT', 'REPA', 'APPA', 'LOCK', 'PROB', 'INGR', 'BOOK', 'ALCH', 'LEVI')
# Object categories of the per-type tables: record types -> category. Nonvisual source markers are split out of
# whatever type carries them (they are deferred with a reason that mentions "marker").
CATEGORIES = collections.OrderedDict([
    ('statics', 'Statics'), ('flora', 'Flora'), ('lights', 'Lights'), ('doors', 'Doors'), ('containers', 'Containers'),
    ('activators', 'Activators'), ('items', 'Items'), ('npcs', 'NPCs'), ('creatures', 'Creatures'), ('markers', 'Markers'),
    ('other', 'Other')])
TYPE_CATEGORY = dict([('STAT', 'statics'), ('LIGH', 'lights'), ('DOOR', 'doors'), ('CONT', 'containers'), ('ACTI', 'activators'),
                      ('NPC_', 'npcs'), ('CREA', 'creatures'), ('LEVC', 'creatures')] + [(t, 'items') for t in ITEM_TYPES])
MARKER_WORD = 'marker'


def read_json(path):
    path = Path(path)
    return json.loads(path.read_bytes().decode('utf-8')) if path.is_file() else None


def write_json(path, value, pretty=False):
    text = json.dumps(value, sort_keys=True, indent=1 if pretty else None, separators=None if pretty else (',', ':'))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((text + '\n').encode('utf-8'))


def ckey(x, y):
    return '%d,%d' % (x, y)


def parse_cell(text):
    x, _, y = str(text).strip().partition(',')
    return int(x), int(y)


def now_iso(now=None):
    return now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')


# ------------------------------------------------------------------ census (your own Morrowind files)

def _count_refs(e, refs, objects, meshes_of=None):
    """Count one cell's references into e (counts, meshes, placements, flora) and return its door records."""
    doors = []
    for r in refs:
        if r.get('del'):
            continue
        o = objects.get(r['id'])
        if not o or o['deleted']:
            continue
        tag = 'ITEM' if o['type'] in ITEM_TYPES else o['type']
        e['counts'][tag] += 1
        if r.get('dest'):
            e['counts']['LOAD_DOOR'] += 1
            p = r.get('p')
            doors.append({'ref': r.get('n'), 'object': r['id'], 'pos': [round(v) for v in p] if p else None,
                          'to': r.get('dcell') or ''})
        if o['model']:
            e['meshes'].add(o['model'])
            e['placements'] += 1
            if o['model'].startswith('meshes/f/') or 'flora' in o['model']:
                e['flora'] += 1
    return doors


def build_census(data_files, progress=print):
    """Parse the masters: per exterior cell what is placed, which meshes it uses and which doors lead where; per
    interior cell its counts and doors (the door links of the interiors tree)."""
    import world_estimate_data as D
    masters = D.census(data_files)
    objects, cells, land, names, shas = {}, {}, set(), {}, {}
    interiors = {}
    base_land, bm_land = set(), set()
    short = {'Morrowind.esm': 'vvardenfell', 'Tribunal.esm': 'tribunal', 'Bloodmoon.esm': 'bloodmoon'}
    for name in D.MASTERS:
        m = masters.get(name)
        if not m:
            continue
        shas[name] = m['sha256']
        objects.update(m['objects'])
        for xy in m['lands']:
            land.add(tuple(xy))
            (bm_land if name == 'Bloodmoon.esm' else base_land).add(tuple(xy))
        for c in m['cells']:
            if c['deleted']:
                continue
            if c['interior']:
                if not c['name']:
                    continue
                e = interiors.setdefault(c['name'].casefold(), {'name': c['name'], 'set': short.get(name, name),
                                                                'counts': collections.Counter(), 'meshes': set(),
                                                                'placements': 0, 'flora': 0, 'doors': []})
                e['doors'].extend(_count_refs(e, c['refs'], objects))
                continue
            xy = (c['x'], c['y'])
            e = cells.setdefault(xy, {'counts': collections.Counter(), 'meshes': set(), 'placements': 0, 'flora': 0,
                                      'doors': []})
            if c['name'] or c['region']:
                names[xy] = {'name': c['name'], 'region': c['region']}
            e['doors'].extend(_count_refs(e, c['refs'], objects))
        progress('census: %s parsed' % name)
    solstheim = bm_land - base_land
    meshes = sorted({m for e in cells.values() for m in e['meshes']})
    index = {m: i for i, m in enumerate(meshes)}
    return {'format': CENSUS_FORMAT, 'masters': shas, 'meshes': meshes,
            'land': sorted(ckey(*c) for c in land), 'land_bloodmoon': sorted(ckey(*c) for c in solstheim),
            'cells': {ckey(*xy): {'counts': dict(e['counts']), 'placements': e['placements'], 'flora': e['flora'],
                                  'meshes': sorted(index[m] for m in e['meshes']),
                                  'doors': [d for d in e['doors'] if d['to']]} for xy, e in sorted(cells.items())},
            'interiors': {k: {'name': e['name'], 'set': e['set'], 'counts': dict(e['counts']), 'placements': e['placements'],
                              'unique_meshes': len(e['meshes']), 'doors': e['doors']} for k, e in sorted(interiors.items())},
            'names': {ckey(*xy): v for xy, v in sorted(names.items())}}


# ------------------------------------------------------------------ small joins

def contents_of(census_cell):
    c = census_cell['counts']
    return {'source': 'census', 'refs_total': sum(c.values()) - c.get('LOAD_DOOR', 0),
            'statics': c.get('STAT', 0), 'flora': census_cell['flora'], 'actors': c.get('NPC_', 0) + c.get('CREA', 0),
            'npcs': c.get('NPC_', 0), 'creatures': c.get('CREA', 0), 'doors': c.get('DOOR', 0),
            'load_doors': c.get('LOAD_DOOR', 0), 'lights': c.get('LIGH', 0), 'containers': c.get('CONT', 0),
            'activators': c.get('ACTI', 0), 'items': c.get('ITEM', 0),
            'unique_meshes': len(census_cell['meshes']), 'placements': census_cell['placements']}


def contents_from_metrics(mc, regions):
    """Without a census: the counts of the regions whose core is in the cell, split evenly over their cells."""
    tot = collections.Counter()
    for rid in mc.get('regions', []):
        r = regions.get(rid) or {}
        share = 1.0 / max(1, len(r.get('cells') or [1]))
        for k in ('refs_total', 'npc', 'creatures', 'lights', 'load_doors', 'refs_items'):
            tot[k] += (r.get(k) or 0) * share
    return {'source': 'metrics (regions split over their cells)', 'refs_total': round(tot['refs_total']),
            'npcs': round(tot['npc']), 'creatures': round(tot['creatures']), 'actors': round(tot['npc'] + tot['creatures']),
            'lights': round(tot['lights']), 'load_doors': round(tot['load_doors']), 'items': round(tot['refs_items'])}


def risk_of(mc):
    """Risk and cost of a cell from the estimator: worst ratio of any engine limit, 'everything' content."""
    worst = (mc.get('worst') or {})
    evr, cur = worst.get('evr') or {}, worst.get('cur') or {}
    ratios = {k: v[1] for k, v in evr.items() if v and v[1] is not None}
    keyed = {k: r for k, r in ratios.items() if k not in RISK_EXCLUDE}
    if not keyed:
        return None, None
    lim = max(keyed, key=lambda k: (keyed[k], k))
    cur_r = {k: v[1] for k, v in cur.items() if v and v[1] is not None and k not in RISK_EXCLUDE}
    risk = {'score': keyed[lim], 'limiting': lim, 'ratios': {k: round(r, 4) for k, r in sorted(ratios.items())},
            'over': sorted(k for k, r in keyed.items() if r > 1), 'current_score': max(cur_r.values()) if cur_r else None}
    cost = {'heap_bytes': (evr.get('heap') or [None])[0], 'regions': len(mc.get('regions', []))}
    return risk, cost


def legacy_of(pc):
    """The legacy mapping quality of a cell, from world-progress.json (what the Toolkit already measures)."""
    if not pc:
        return None
    share = round(pc['placed'] / pc['original'], 4) if pc.get('original') else None
    kind = pc.get('map')
    if kind == 'full':
        grade = 'A' if share is not None and share >= .8 else 'B'
    elif kind == 'terrain':
        grade = 'C' if share else 'D'
    else:
        grade = 'E'
    labels = {'A': 'full town/area map, 80 % or more of the entities placed', 'B': 'full town/area map',
              'C': 'topomap terrain, some entities placed', 'D': 'topomap terrain only', 'E': 'no terrain'}
    return {'map': kind, 'grade': grade, 'grade_label': labels[grade], 'placed': pc.get('placed'),
            'original': pc.get('original'), 'placed_share': share, 'places': pc.get('places'),
            'interiors': pc.get('interiors'), 'interiors_converted': pc.get('interiors_converted'),
            'checked': bool(pc.get('checked')), 'maps': pc.get('maps') or []}


def derive(rec):
    """Audit summary, CHIM status and bucket of one record (in place)."""
    counts = collections.Counter(a['status'] for a in rec['audits'].values())
    for r in RESULTS:
        counts.setdefault(r, 0)
    rec['audit_counts'] = {r: counts[r] for r in RESULTS}
    chim = rec['chim']
    if chim.get('empty'):
        # CHIMport: terrain and water only, nothing placed. Its own status; never counted as passed or as converted.
        chim['status'], chim['bucket'] = 'empty_sea', 'empty_sea'
        return
    if chim.get('not_converted'):
        # The conversion job tried and could not finish the cell. A failure-type state: never counted as done.
        chim['status'], chim['bucket'] = 'not_converted', 'not_converted'
        return
    if not chim['converted']:
        if chim.get('failed'):      # attempted and not converted: a failure
            chim['status'], chim['bucket'] = 'failed', 'converted_failing'
        else:
            chim['status'], chim['bucket'] = 'not_started', 'not_started'
        return
    if chim.get('policy_pending'):
        # Only problem: hull-chain depth, waiting for one shared router/audit rule. Neither passed nor failed.
        chim['status'], chim['bucket'] = 'hull_policy_pending', 'hull_policy_pending'
        chim['successful'] = False
        chim['unmeasured_audits'] = counts['not_measured']
        return
    failing = counts['failed'] > 0 or bool(chim.get('failed'))
    measured = counts['passed'] + counts['accepted'] + counts['failed']
    owner = chim.get('owner')
    if failing:
        bucket = 'converted_failing'
    elif owner == 'approved':
        bucket = 'approved'
    elif owner == 'playtested':
        bucket = 'playtested'
    elif measured:
        bucket = 'audits_passed'
    else:
        bucket = 'converted_unmeasured'
    chim['bucket'] = bucket
    chim['status'] = {'approved': 'approved', 'playtested': 'playtested', 'audits_passed': 'audits_passed'}.get(bucket, 'converted')
    chim['successful'] = bucket in SUCCESS
    chim['unmeasured_audits'] = counts['not_measured']


def new_category():
    return {'placed': 0, 'converted': 0, 'failed': 0, 'deferred': {}, 'skipped': {}}


def add_category(a, b):
    """Add category record b into a (in place)."""
    for k in ('placed', 'converted', 'failed'):
        a[k] += b[k]
    for k in ('deferred', 'skipped'):
        for reason, n in b[k].items():
            a[k][reason] = a[k].get(reason, 0) + n
    return a


def categorize(records_by_type, flora=None):
    """{category: {placed, converted, failed, deferred{reason}, skipped{reason}}} from the conversion job's records_by_type.
    None when the cell has no such figures (not measured). Flora is a subset of statics (the job counts it by mesh folder,
    not by record type), so it only carries a placed count."""
    if not isinstance(records_by_type, dict):
        return None
    out = collections.OrderedDict((k, new_category()) for k in CATEGORIES)
    for ty, v in records_by_type.items():
        cat = TYPE_CATEGORY.get(ty, 'other')
        out[cat]['placed'] += v.get('placed') or 0
        out[cat]['converted'] += v.get('converted') or 0
        out[cat]['failed'] += v.get('failed') or 0
        for kind in ('deferred', 'skipped'):
            for reason, n in (v.get(kind) or {}).items():
                # Markers are not drawn and not required. Light emitters without a mesh are "nonvisual markers" in the job's
                # words too, but they cast light: they stay lights and keep blocking completion.
                if kind == 'deferred' and MARKER_WORD in reason and cat != 'lights':
                    # a marker leaves its type: it counts as a marker (deferred), not as a light/door/static
                    out['markers']['placed'] += n
                    out['markers']['deferred'][reason] = out['markers']['deferred'].get(reason, 0) + n
                    out[cat]['placed'] -= n
                else:
                    out[cat][kind][reason] = out[cat][kind].get(reason, 0) + n
    if flora:
        out['flora']['placed'] = flora
    return out


def is_complete(rec, actors=True):
    """Every placed object converted: nothing deferred, skipped or failed. actors=False leaves the actor categories out
    (the test of "terrain complete")."""
    cats = rec.get('categories')
    if not cats or not rec['chim']['converted']:
        return False
    for k, c in cats.items():
        if (not actors and k in ACTOR_CATEGORIES) or (k == 'markers' and not MARKERS_BLOCK_COMPLETE):
            continue
        if c['failed'] or c['deferred'] or c['skipped'] or (k != 'flora' and c['converted'] != c['placed']):
            return False
    return True


def promote_complete(cells):
    """Per-cell categories; then passed cells whose every placed object is converted become Cell complete (needs the stats)."""
    for rec in cells.values():
        st = rec.get('stats') or {}
        rec['categories'] = categorize(st.get('records_by_type'), (st.get('records') or {}).get('flora'))
        if rec['chim'].get('bucket') == 'audits_passed':
            level = 'complete' if is_complete(rec) else 'terrain_complete' if is_complete(rec, actors=False) else None
            if level:
                rec['chim']['bucket'] = rec['chim']['status'] = level


def island_headlines(cells):
    """Per island (land cells plus empty sea): the same done/complete figures, so islands are never mixed in one percentage."""
    out = []
    for i in sorted({c.get('island') for c in cells.values() if c.get('island')}):
        mine = [c for c in cells.values() if c.get('island') == i and (c['land'] or c['chim']['bucket'] == 'empty_sea')]
        n = collections.Counter(c['chim']['bucket'] for c in mine)
        done = sum(n[b] for b in SUCCESS) + n['empty_sea']
        row = {'island': i, 'name': ISLAND_NAMES.get(i, 'island %d' % i), 'cells': len(mine), 'done': done,
               'percent': round(100.0 * done / len(mine), 1) if mine else 0.0,
               'passed': sum(n[b] for b in SUCCESS), 'converted': sum(1 for c in mine if c['chim']['converted'])}
        row.update({b: n[b] for b in BUCKETS})
        out.append(row)
    return out


def headline(cells):
    land = [c for c in cells.values() if c['land']]
    n = collections.Counter(c['chim']['bucket'] for c in land)
    passed = sum(n[b] for b in SUCCESS)
    out = {b: n[b] for b in BUCKETS}
    out['empty_sea'] = sum(1 for c in cells.values() if c['chim']['bucket'] == 'empty_sea')     # land or not
    out['islands'] = island_headlines(cells)
    out['done'] = passed + out['empty_sea']      # cell complete + terrain complete + passed + empty sea (each has its own line)
    out.update({'land_cells': len(land), 'passed': passed,
                'percent': round(100.0 * passed / len(land), 2) if land else 0.0,
                'converted': sum(1 for c in land if c['chim']['converted']),
                'with_unmeasured_audits': sum(1 for c in land if c['chim']['converted'] and c['audit_counts']['not_measured'])})
    return out


# ------------------------------------------------------------------ bugs and ledger

def link_bugs(bugs, areas_cfg, area_cells, explicit=True):
    """{cell key: [bug ids]}: a bug is linked to the cells of an area its title/where/tags name, or to cells it names."""
    out = collections.defaultdict(list)
    pat = re.compile(r'cell\s*\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?', re.I)
    for b in bugs or []:
        text = ' '.join(str(b.get(k) or '') for k in ('title', 'where')) + ' ' + ' '.join(b.get('tags') or [])
        low = text.lower()
        linked = set()
        if explicit:
            linked |= {ckey(int(a), int(c)) for a, c in pat.findall(text)}
        for area, words in (areas_cfg or {}).get('areas', {}).items():
            if any(re.search(r'\b' + re.escape(w.lower()) + r'\b', low) for w in words):
                linked |= set(area_cells.get(area, ()))
        for k in linked:
            out[k].append(b['id'])
    return {k: sorted(set(v)) for k, v in out.items()}


def ledger_by_build(path):
    """{build basename: {wall_s, chim_stage_s, version, host_busy, started}} from the build and perf ledger."""
    out = {}
    p = Path(path) if path else None
    if not p or not p.is_file():
        return out
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        run = (r.get('run') or r.get('build') or '').rstrip('/')
        base = run.split('/')[-1].split(' ')[0]
        if not base:
            continue
        e = out.setdefault(base, {'build': base, 'elapsed_s': 0.0, 'chim_stage_s': None, 'version': r.get('version'),
                                  'host_busy': r.get('host_busy'), 'started': r.get('build_started_at')})
        end = (r.get('started_s') or 0) + (r.get('wall_s') or 0)
        e['elapsed_s'] = round(max(e['elapsed_s'], end), 3)
        if r.get('stage') == 'chim' and r.get('wall_s') is not None:
            e['chim_stage_s'] = r['wall_s']
    return out


# ------------------------------------------------------------------ the ingest

def load_runs(out, specs, labels, commits):
    """Digest the given CHIM runs into OUT/runs/NAME.json, then return every digest oldest build first."""
    runs_dir = out / 'runs'
    for spec in specs:
        name, _, path = spec.partition('=')
        if not path:
            raise SystemExit('--chim-run wants NAME=PATH, got %r' % spec)
        stamp = None
        rp = CH.report_path(path, 'receipt')
        if rp.is_file():
            stamp = datetime.datetime.fromtimestamp(rp.stat().st_mtime, datetime.timezone.utc).isoformat(timespec='seconds')
        d = CH.digest(name, path, labels.get(name), commits.get(name), stamp)
        write_json(runs_dir / (name + '.json'), d)
    digests = []
    for p in sorted(runs_dir.glob('*.json')) if runs_dir.is_dir() else []:
        d = read_json(p)
        if d and d.get('format') == CH.RUN_FORMAT:
            digests.append(d)
    digests.sort(key=lambda d: (d.get('built_at') or '', d['name']))
    return digests


def load_audits(out):
    """Drop-in audit results: {mechanism: {cell key: entry}}, later files winning."""
    got = collections.defaultdict(dict)
    adir = out / 'audits'
    files = sorted(adir.glob('*.json')) if adir.is_dir() else []
    docs = [d for d in (read_json(f) for f in files) if d and d.get('format') == AUDIT_FORMAT]
    docs.sort(key=lambda d: d.get('generated') or '')
    for d in docs:
        mech = d['mechanism']
        for k, v in d['cells'].items():
            got[mech][k] = {'status': v['status'], 'detail': v.get('detail'), 'build': d.get('build'),
                            'generated': d.get('generated')}
    return got


RESULT_FORMAT = 'aw-cell-result-1'
# Numeric stats summed per island and ring (dotted names into a cell's stats block).
STAT_SUMS = ('records.refs_total', 'meshes.new', 'meshes.reused', 'faces.before', 'faces.after', 'faces.chim_terrain',
             'faces.chim_placed', 'textures.count', 'textures.bytes', 'bytes.chim', 'bytes.legacy', 'chunks.count',
             'chunks.bytes', 'chunks.legacy_bytes', 'time.convert_s', 'time.cpu_s')
LEGACY_ESTIMATE = ('faces', 'texinfo', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes', 'edicts', 'inline_models', 'heap')


def deep_merge(a, b):
    """Merge dict b into dict a (nested dicts merge, anything else is replaced); returns a."""
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def dotted(d, name):
    for part in name.split('.'):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d if isinstance(d, (int, float)) and not isinstance(d, bool) else None


def norm_errors(errors):
    """Errors as dicts {stage, mechanism, message}: a plain string becomes {message}."""
    out = []
    for e in errors or []:
        if isinstance(e, dict):
            out.append({k: e.get(k) for k in ('stage', 'mechanism', 'message') if e.get(k) is not None} or {'message': str(e)})
        else:
            out.append({'message': str(e)})
    return out


def error_text(e):
    return ': '.join(x for x in ('/'.join(str(e[k]) for k in ('stage', 'mechanism') if e.get(k)), e.get('message')) if x)


def load_results(out):
    """Per-cell results of the conversion job (OUT/results/*.json, format aw-cell-result-1), later files winning."""
    rdir = Path(out) / 'results'
    docs = []
    if rdir.is_dir():
        docs = [d for d in (read_json(f) for f in sorted(rdir.glob('*.json'))) if d and d.get('format') == RESULT_FORMAT]
    docs.sort(key=lambda d: d.get('generated') or '')
    got = {}
    for d in docs:
        for k, v in d['cells'].items():
            e = got.setdefault(k, {'stats': {}, 'audits': {}, 'errors': [], 'converted': None, 'empty': False, 'policy_pending': None, 'failed': False, 'provenance': None})
            deep_merge(e['stats'], v.get('stats') or {})
            for m, a in (v.get('audits') or {}).items():
                e['audits'][m] = dict(a, build=a.get('build') or d.get('build'))      # numbers etc. ride along
                if a.get('outcome') == KEPT_CHAIN_OUTCOME:
                    e['audits'][m]['status'] = 'passed'          # deliberate, not a failure
            if 'errors' in v:
                e['errors'] = norm_errors(v['errors'])
            if v.get('converted') is not None:
                e['converted'] = bool(v['converted'])
            if v.get('policy_pending') is not None or v.get('status') is not None:
                e['policy_pending'] = bool(v.get('policy_pending')) or v.get('status') in ('hull_pending', 'policy_pending')
            if v.get('status') is not None:
                e['failed'] = v['status'] in ('failed', 'not_converted')
                e['not_converted'] = v['status'] == 'not_converted'
            if v.get('empty') is not None or v.get('status') is not None:
                e['empty'] = bool(v.get('empty')) or v.get('status') == 'empty'
            pv = dict(d.get('provenance') or {})
            pv.update(v.get('provenance') or {})
            if pv:
                e['provenance'] = dict(e['provenance'] or {}, **pv)
            e['build'] = d.get('build')
            e['generated'] = d.get('generated')
    return got


def assemble_stats(cells, cen_cells, met_cells, digest_cell, results):
    """Fill every record's `stats` block; unknown fields are left out (not measured)."""
    converted = [k for k, r in cells.items() if r['chim']['converted']]
    converted.sort(key=lambda k: ((cells[k]['provenance'] or {}).get('built_at') or '', cells[k]['spiral_rank'] or 0, k))
    seen = set()
    derived = {}
    for k in converted:
        if k in cen_cells:
            ms = set(cen_cells[k]['meshes'])
            derived[k] = {'unique': len(ms), 'new': len(ms - seen), 'reused': len(ms & seen),
                          'source': 'derived from the original references, in conversion order'}
            seen |= ms
    for k, rec in cells.items():
        st = {}
        if k in cen_cells and rec['contents']:
            c = cen_cells[k]['counts']
            st['records'] = {'refs_total': rec['contents']['refs_total'], 'by_type': dict(sorted(c.items()))}
        mc = met_cells.get(k)
        if mc:
            cur = (mc.get('worst') or {}).get('cur') or {}
            est = {m: cur[m][0] for m in LEGACY_ESTIMATE if cur.get(m)}
            if est:
                st['legacy_estimate'] = dict(est, basis='estimator, worst region of the cell, converters as they are today')
        if rec['chim']['converted']:
            if k in derived:
                st['meshes'] = derived[k]
            dc = digest_cell.get(k)
            if dc:
                d, e = dc
                if e.get('chunks') is not None:
                    st['chunks'] = {'count': e['chunks'], 'bytes': e.get('bytes')}
                    st['faces'] = {'chim_terrain': e.get('terrain_faces'), 'chim_placed': e.get('placed_faces')}
                    st['bytes'] = {'chim': e.get('bytes')}
                rs = d.get('run_stats') or {}
                mem = {m: rs[m] for m in ('frame_heap_peak_bytes', 'frame_heap_budget_bytes', 'zone_locked_peak_bytes',
                                          'zone_failed_chunk_loads', 'model_zone_peak_bytes') if m in rs}
                if mem:
                    st['memory'] = dict(mem, basis='run-level: shared by the cells of the build')
                if 'build_cpu_s' in rs:
                    st['time'] = {'cpu_s': rs['build_cpu_s'], 'basis': 'run-level: the whole build'}
        r = results.get(k)
        if r and r['stats']:
            deep_merge(st, r['stats'])
        rec['stats'] = st


def group_sums(recs):
    n = {'cells': len(recs), 'converted': 0, 'passed': 0, 'complete': 0, 'terrain_complete': 0, 'failing': 0, 'with_errors': 0, 'stats': {},
         'by_category': collections.OrderedDict((k, new_category()) for k in CATEGORIES)}
    for r in recs:
        if not r['chim']['converted']:
            continue
        n['converted'] += 1
        n['complete'] += 1 if r['chim']['bucket'] == 'complete' else 0
        n['terrain_complete'] += 1 if r['chim']['bucket'] == 'terrain_complete' else 0
        for k, c in (r.get('categories') or {}).items():
            add_category(n['by_category'][k], c)
        n['passed'] += 1 if r['chim']['bucket'] in SUCCESS else 0
        n['failing'] += 1 if r['chim']['bucket'] == 'converted_failing' else 0
        n['with_errors'] += 1 if r.get('errors') else 0
        for name in STAT_SUMS:
            v = dotted(r.get('stats') or {}, name)
            if v is not None:
                n['stats'][name] = round(n['stats'].get(name, 0) + v, 3)
    return n


def make_totals(cells):
    """Totals over all land cells, per island and per ring inside each island."""
    land = [r for r in cells.values() if r['land'] and r.get('island') is not None]
    out = {'all': group_sums([r for r in cells.values() if r['land']]), 'islands': []}
    for i in sorted({r['island'] for r in land}):
        mine = [r for r in land if r['island'] == i]
        isl = dict(group_sums(mine), island=i, rings=[])
        for k in sorted({r['ring'] for r in mine}):
            isl['rings'].append(dict(group_sums([r for r in mine if r['ring'] == k]), ring=k))
        out['islands'].append(isl)
    return out


def our_maps(config_dir):
    """{interior cell name (casefold): our map name} from every config file that lists scenes with a cell and a map."""
    out = {}

    def walk(v):
        if isinstance(v, dict):
            if isinstance(v.get('cell'), str) and isinstance(v.get('map'), str):
                out.setdefault(v['cell'].casefold(), v['map'])
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    for f in sorted(Path(config_dir).glob('*.json')) if config_dir and Path(config_dir).is_dir() else []:
        try:
            walk(json.loads(f.read_bytes().decode('utf-8')))
        except ValueError:
            continue
    return out


MAX_DEPTH = 8


def build_interiors(census, metrics, cells, pois, bugs, maps):
    """Interior records plus the door tree under every exterior cell.

    Returns (records list, {cell key: [tree nodes]}). A tree node is {id, ref, object, pos, children}: the door that
    leads into the interior (ref = its reference number, pos = its position in the cell the door stands in)."""
    cen_int = (census or {}).get('interiors') or {}
    cen_cells = (census or {}).get('cells') or {}
    mi = {}
    for r in (metrics or {}).get('interiors', []):
        mi[(r.get('name') or '').casefold()] = r
    legacy = {}
    for p in pois or []:
        if p.get('kind') not in ('place', 'exterior place') and p.get('name'):
            legacy[p['name'].casefold()] = bool(p.get('converted'))

    def iid(name_cf):
        return (mi.get(name_cf) or {}).get('id') or 'n:' + name_cf
    entrances, recs = {}, {}

    def node(name_cf, door, ancestors, depth):
        n = {'id': iid(name_cf), 'ref': door.get('ref'), 'object': door.get('object'), 'pos': door.get('pos'), 'children': []}
        rec = recs.get(name_cf)
        if rec is not None:
            rec['depth'] = min(rec['depth'], depth)
        if depth < MAX_DEPTH and name_cf in cen_int:
            seen = set()
            for d in cen_int[name_cf]['doors']:
                to = (d.get('to') or '').casefold()
                if to and to in cen_int and to not in ancestors and to not in seen and to != name_cf:
                    seen.add(to)
                    n['children'].append(node(to, d, ancestors | {name_cf}, depth + 1))
        return n
    for name_cf, c in cen_int.items():
        m = mi.get(name_cf) or {}
        cur = (m.get('cur') or {})
        recs[name_cf] = {
            'id': iid(name_cf), 'name': c['name'], 'set': c['set'], 'our_map': maps.get(name_cf),
            'contents': {'source': 'census', 'refs_total': sum(c['counts'].values()) - c['counts'].get('LOAD_DOOR', 0),
                         'npcs': c['counts'].get('NPC_', 0), 'creatures': c['counts'].get('CREA', 0),
                         'doors': c['counts'].get('DOOR', 0), 'load_doors': c['counts'].get('LOAD_DOOR', 0),
                         'lights': c['counts'].get('LIGH', 0), 'containers': c['counts'].get('CONT', 0),
                         'statics': c['counts'].get('STAT', 0), 'items': c['counts'].get('ITEM', 0),
                         'unique_meshes': c['unique_meshes']},
            'stats': {'records': {'refs_total': sum(c['counts'].values()) - c['counts'].get('LOAD_DOOR', 0),
                                  'by_type': dict(sorted(c['counts'].items()))},
                      'meshes': {'unique': c['unique_meshes']},
                      'legacy_estimate': {k: cur[k] for k in LEGACY_ESTIMATE if k in cur}},
            'legacy': {'converted': legacy.get(name_cf), 'known': name_cf in legacy},
            'risk_score': None, 'bugs': [], 'entrances': [], 'depth': MAX_DEPTH + 1,
            'chim': {'converted': False, 'status': 'not_started', 'bucket': 'not_started'},
        }
        ev = m.get('evr') or {}
        ratios = [ev[k] / metrics['limits'][k]['limit'] for k in ev if k not in RISK_EXCLUDE and ev[k] is not None
                  and k in (metrics or {}).get('limits', {})]
        recs[name_cf]['risk_score'] = round(max(ratios), 4) if ratios else None
    for k, c in cen_cells.items():
        trees = []
        seen = set()
        for d in c.get('doors', []):
            to = d['to'].casefold()
            if to in cen_int and to not in seen:
                seen.add(to)
                trees.append(node(to, d, frozenset(), 1))
        if trees:
            entrances[k] = trees

    by_id = {r['id']: r for r in recs.values()}

    def collect_fast(k, nodes, path):
        for n in nodes:
            r = by_id.get(n['id'])
            if r is not None and len(r['entrances']) < 6:
                r['entrances'].append({'cell': k, 'door_ref': n['ref'], 'door_object': n['object'], 'door_pos': n['pos'],
                                       'via': path})
            collect_fast(k, n['children'], path + [n['id']])
    for k, trees in entrances.items():
        collect_fast(k, trees, [])
    for r in recs.values():
        if r['depth'] > MAX_DEPTH:
            r['depth'] = None
    # bugs that name an interior (by its name or its map name)
    named = [(n, r) for n, r in recs.items() if len(n) >= 6]
    for b in bugs or []:
        text = ' '.join(str(b.get(k) or '') for k in ('title', 'where', 'status')).casefold() + ' ' + ' '.join(b.get('tags') or [])
        for n, r in named:
            if n in text or (r['our_map'] and re.search(r'\b' + re.escape(r['our_map'].casefold()) + r'\b', text)):
                r['bugs'].append(b['id'])
    return sorted(recs.values(), key=lambda r: (r['set'], r['name'].casefold())), entrances


def ingest(out, progress=None, metrics=None, cells_detail=None, census=None, chim_runs=(), labels=None, commits=None,
           bugs=None, ledger=None, areas=None, now=None, png=False, config_dir=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    now = now_iso(now)
    prog_cells = {ckey(c['x'], c['y']): c for c in (progress or {}).get('cells', [])}
    met_cells = {ckey(c['x'], c['y']): c for c in (metrics or {}).get('cells', [])}
    regions = (metrics or {}).get('regions', {})
    detail = (cells_detail or {}).get('cells', {})
    cen_cells = (census or {}).get('cells', {})
    mesh_names = (census or {}).get('meshes', [])
    digests = load_runs(out, chim_runs, labels or {}, commits or {})
    audits_in = load_audits(out)
    results = load_results(out)
    owner_doc = read_json(out / OUT_FILES['owner']) or {}
    owner = owner_doc.get('cells', {})
    ledger_map = ledger_by_build(ledger)

    # --- which cells exist, which are land
    if census:
        # The game's own LAND records: exactly the cells that have ground. (The legacy table also holds cells with
        # flat converted terrain but no LAND record; they are sea and stay out of the land count.)
        land = set(census.get('land', []))
    else:
        land = {k for k, c in prog_cells.items() if c.get('map') in ('terrain', 'full')}
        land |= {k for k, c in met_cells.items() if c.get('set') == 'bloodmoon'}
    keys = set(land) | set(met_cells) | set(cen_cells) | set(prog_cells)
    keys |= {k for d in digests for k, e in d['cells'].items() if e.get('converted')}
    keys |= {k for k, r in results.items() if r.get('empty')}
    cells = {}
    for k in sorted(keys, key=lambda s: parse_cell(s)):
        x, y = parse_cell(k)
        mc, pc, cc = met_cells.get(k), prog_cells.get(k), cen_cells.get(k)
        d = detail.get(k) or {}
        nm = ((census or {}).get('names') or {}).get(k) or {}
        risk, cost = risk_of(mc) if mc else (None, None)
        if cc:
            contents = contents_of(cc)
        elif census and k in land:
            contents = contents_of({'counts': {}, 'flora': 0, 'meshes': [], 'placements': 0})
        elif mc:
            contents = contents_from_metrics(mc, regions)
        else:
            contents = None
        if contents is not None and cost is not None:
            cost['refs_total'] = contents['refs_total']
        cells[k] = {
            'x': x, 'y': y, 'name': d.get('name') or nm.get('name') or '', 'region': d.get('region') or nm.get('region') or '',
            'set': (mc or {}).get('set') or '', 'land': k in land,
            'contents': contents, 'legacy': legacy_of(pc), 'risk': risk, 'cost': cost,
            'chim': {'converted': False, 'builds': [], 'owner': None},
            'audits': {m: {'status': 'not_measured', 'detail': None, 'build': None} for m in MECHANISMS},
            'bugs': [], 'last_build': None, 'provenance': None,
        }
    # --- CHIM builds, oldest first, so the latest build to convert a cell sets its record
    digest_cell = {}
    area_cells = collections.defaultdict(set)
    for d in digests:
        for k, e in d['cells'].items():
            rec = cells.get(k)
            if rec is None:
                continue
            ch = rec['chim']
            if not e.get('converted'):
                if not ch['converted']:
                    ch['partial_terrain'] = True
                    ch['coverage'] = {kk: e.get(kk) for kk in ('chunks', 'owned', 'terrain_faces', 'placed_faces', 'bytes')}
                continue
            for a in d['areas']:
                area_cells[a].add(k)
            ch.pop('partial_terrain', None)
            ch['converted'] = True
            ch['build'] = d['name']
            if d['name'] not in ch['builds']:
                ch['builds'].append(d['name'])
            ch['areas'] = sorted(set(ch.get('areas', [])) | set(d['areas']))
            ch['coverage'] = {kk: e.get(kk) for kk in ('chunks', 'owned', 'terrain_faces', 'placed_faces', 'bytes')}
            for m in MECHANISMS:
                rec['audits'][m] = {'status': 'not_measured', 'detail': None, 'build': None}
            for m, per in d['audits'].items():
                if k in per:
                    rec['audits'][m] = {'status': per[k]['status'], 'detail': per[k].get('detail'), 'build': d['name']}
            rec['provenance'] = {'build': d['name'], 'label': d.get('label'), 'source_commit': d.get('commit'),
                                 'chim_version': d.get('chim_version'), 'world_format': d.get('world_format'),
                                 'built_at': d.get('built_at'), 'builder': d.get('builder')}
            rec['last_build'] = ledger_map.get(d['name'])
            digest_cell[k] = (d, e)
    # --- per-cell results from the conversion job (see FORMAT.md): converted flag, stats, audits, errors
    result_ignored = []
    for k, r in results.items():
        rec = cells.get(k)
        if rec is None:
            result_ignored.append(k)
            continue
        ch = rec['chim']
        ch['result_generated'] = r.get('generated')
        rec['errors'] = r['errors']
        if r.get('empty'):
            ch['empty'] = True
            ch['build'] = r.get('build')
            ch['converted'] = False
        elif r['converted'] is False:
            ch['attempted'] = True
            ch['failed'] = True
        elif r['converted'] or r['stats']:
            ch['converted'] = True
            ch.pop('partial_terrain', None)
            if r.get('build'):
                ch['build'] = r['build']
                if r['build'] not in ch['builds']:
                    ch['builds'].append(r['build'])
            pv = dict(rec['provenance'] or {})
            pv.update({k2: v2 for k2, v2 in (r.get('provenance') or {}).items() if v2 is not None})
            pv.setdefault('build', r.get('build'))
            if r.get('generated'):
                pv.setdefault('built_at', r['generated'])
            rec['provenance'] = pv
        if ch['converted'] and r.get('policy_pending') is not None:
            ch['policy_pending'] = bool(r['policy_pending'])
        if r.get('failed') and not r.get('empty'):
            ch['failed'] = True      # the job's own verdict "failed" (also when no single audit failed)
            ch['not_converted'] = bool(r.get('not_converted'))
        if ch['converted']:
            for m, a in r['audits'].items():
                if m in MECHANISMS and a.get('status') in RESULTS:
                    rec['audits'][m] = {'status': a['status'], 'detail': a.get('detail'), 'build': a.get('build') or r.get('build')}
                    if a.get('numbers') is not None:
                        rec['audits'][m]['numbers'] = a['numbers']
                    if a.get('outcome') in OUTCOME_LABELS:
                        rec['audits'][m]['outcome'] = a['outcome']
    # --- audits from other tools
    for m, per in audits_in.items():
        for k, a in per.items():
            rec = cells.get(k)
            if rec is None or not rec['chim']['converted'] or m not in MECHANISMS:
                continue
            if a.get('build') and a['build'] != rec['chim'].get('build'):
                # Measured on another build than the one the cell last came from: shown, not counted.
                rec['audits'][m] = {'status': 'not_measured', 'detail': a.get('detail'), 'build': a['build'],
                                    'stale': True, 'stale_result': a['status']}
            else:
                rec['audits'][m] = {'status': a['status'], 'detail': a.get('detail'), 'build': a.get('build')}
    ignored = []
    for k, o in owner.items():
        rec = cells.get(k)
        if rec and rec['chim']['converted'] and o.get('status') in OWNER_STATES:
            rec['chim']['owner'] = o['status']
            rec['chim']['owner_date'] = o.get('date')
            rec['chim']['owner_note'] = o.get('note')
        else:
            ignored.append(k)
    for k, rec in cells.items():
        derive(rec)
    # --- bugs
    by_id = {b['id']: b for b in bugs or []}
    linked = link_bugs(bugs, areas, area_cells)
    bug_info = {}
    for k, ids in linked.items():
        if k in cells:
            cells[k]['bugs'] = ids
            for i in ids:
                b = by_id[i]
                bug_info[i] = {'title': b.get('title'), 'state': b.get('state'), 'severity': b.get('severity'),
                               'family': b.get('family')}
    # --- sweep orders
    land_set = {parse_cell(k) for k in land}
    sea_content = {parse_cell(k) for k, r in cells.items() if not r['land'] and r['contents'] and r['contents']['refs_total']}
    solst = {parse_cell(k) for k in (census or {}).get('land_bloodmoon', [])} if census else         {parse_cell(k) for k, c in met_cells.items() if c.get('set') == 'bloodmoon'}
    groups = {c: 'solstheim' for c in land_set & solst}
    spiral = OR.spiral(land_set, sea_content, groups)
    group_of = {c: (i, r) for c, r, i in spiral}
    for rank, (c, r, isl) in enumerate(spiral, 1):
        rec = cells[ckey(*c)]
        rec['ring'], rec['spiral_rank'], rec['island'] = r, rank, isl or None
    risky = [parse_cell(k) for k, r in cells.items() if r['risk']]
    ordered = OR.risk_order(risky, lambda c: cells[ckey(*c)]['risk']['score'],
                            lambda c: (cells[ckey(*c)]['contents'] or {}).get('refs_total'))
    for rank, c in enumerate(ordered, 1):
        cells[ckey(*c)]['risk_rank'] = rank
    for rec in cells.values():
        rec.setdefault('ring', None)
        rec.setdefault('spiral_rank', None)
        rec.setdefault('island', None)
        rec.setdefault('risk_rank', None)
    # --- per-cell stats: original records and meshes, the estimator's legacy figures, what the CHIM build wrote,
    #     and whatever the conversion job measured (its numbers win)
    assemble_stats(cells, cen_cells, met_cells, digest_cell, results)
    promote_complete(cells)
    totals = make_totals(cells)
    # --- mesh-first view
    curve = None
    if census:
        meshes = {parse_cell(k): set(c['meshes']) for k, c in cen_cells.items()}
        spiral_cells = [c for c, _, _ in spiral]
        sp = OR.reuse_curve(spiral_cells, meshes, group_of)
        rk = OR.reuse_curve(ordered, meshes)
        cells_per_mesh = collections.Counter(i for ms in meshes.values() for i in ms)
        exclusive = {i for i, n in cells_per_mesh.items() if n == 1}
        owners = {c for c, ms in meshes.items() if ms & exclusive}
        with_meshes = sum(1 for ms in meshes.values() if ms)
        total = len(mesh_names)
        curve = {
            'format': 'aw-mesh-curve-1', 'generated': now, 'unique_meshes': total, 'cells_with_meshes': with_meshes,
            'placements': sum(c['placements'] for c in cen_cells.values()),
            'meshes_in_one_cell_only': len(exclusive), 'cells_that_own_a_mesh': len(owners),
            'cells_placement_only_once_all_meshes_exist': with_meshes,
            'cells_with_no_exclusive_mesh': with_meshes - len(owners),
            'cells_without_new_mesh_spiral': sp['cells_without_new_mesh'],
            'cells_without_new_mesh_risk': rk['cells_without_new_mesh'],
            'spiral': {'points': OR.thin(sp['points']), 'rings': sp['rings']},
            'risk': {'points': OR.thin(rk['points'])},
        }
        if png:
            marks = []
            for r in sp['rings']:
                if r['ring'] and (r['ring'] % 3 == 0 or r['ring'] == 1):
                    marks.append((r['cumulative_cells'], ('' if r['island'] == 1 else 'island %d ' % r['island']) + 'ring %d' % r['ring']))
            series = [('spiral order: cumulative unique meshes', sp['points'], '#4fc3f7', 1, False),
                      ('risk order (cells with estimates): cumulative unique meshes', rk['points'], '#ffcf55', 1, False),
                      ('no reuse: every cell converts its own meshes (spiral order)', sp['points'], '#7a8b9c', 2, True)]
            OR.draw_curve(out / OUT_FILES['png'], series,
                          'CHIM store-once mesh reuse: %d unique meshes, %d cells with placements' % (total, curve['cells_with_meshes']),
                          marks)
        write_json(out / OUT_FILES['curve'], curve, pretty=True)
    # --- summary, next lists, history
    head = headline(cells)
    per_mech = {m: {r: sum(1 for c in cells.values() if c['chim']['converted'] and c['audits'][m]['status'] == r)
                    for r in RESULTS} for m in MECHANISMS}
    runs_meta = [{'name': d['name'], 'label': d.get('label'), 'commit': d.get('commit'), 'chim_version': d.get('chim_version'),
                  'world_format': d.get('world_format'), 'areas': d['areas'], 'built_at': d.get('built_at'),
                  'placements': d.get('placements'), 'models': d.get('models'), 'reports': d.get('reports')} for d in digests]
    history = update_history(out, head, [d['name'] for d in digests], now)
    interiors, entrances = build_interiors(census, metrics, cells, (cells_detail or {}).get('pois'), bugs, our_maps(config_dir))
    for k, trees in entrances.items():
        if k in cells:
            cells[k]['entrances'] = trees
    for rec in cells.values():
        rec.setdefault('entrances', [])
    for r in interiors:
        for b in r['bugs']:
            if b not in bug_info and b in by_id:
                bb = by_id[b]
                bug_info[b] = {'title': bb.get('title'), 'state': bb.get('state'), 'severity': bb.get('severity'),
                               'family': bb.get('family')}
    doc = {
        'format': FORMAT, 'generator': 'tools/cell_progress.py', 'generated': now,
        'mechanisms': [{'id': m, 'label': l} for m, l in MECHANISMS.items()],
        'headline': head, 'by_mechanism': per_mech, 'bugs': bug_info, 'runs': runs_meta, 'history': history,
        'sources': {'progress': bool(progress), 'metrics': bool(metrics), 'census': bool(census),
                    'names': bool(cells_detail), 'bugs': bool(bugs), 'ledger': bool(ledger_map)},
        'rings': max([r['ring'] for r in cells.values() if r['ring'] is not None] or [0]),
        'mesh_curve': {k: curve[k] for k in ('unique_meshes', 'cells_with_meshes', 'meshes_in_one_cell_only',
                                              'cells_without_new_mesh_spiral', 'cells_that_own_a_mesh')} if curve else None,
        'totals': totals, 'owner_ignored': sorted(ignored), 'result_ignored': sorted(result_ignored),
        'cells': cells, 'interiors': interiors,
    }
    write_json(out / OUT_FILES['progress'], doc)
    nxt = next_lists(cells, now)
    write_json(out / OUT_FILES['next'], nxt, pretty=True)
    return doc


def next_lists(cells, now):
    """The sweep orders for cells not yet converted: spiral (coast inwards) and risk (scout), first NEXT_LIMIT of each."""
    def row(r):
        c = r['contents'] or {}
        return {'x': r['x'], 'y': r['y'], 'name': r['name'] or r['region'], 'ring': r['ring'], 'spiral_rank': r['spiral_rank'],
                'risk_rank': r['risk_rank'], 'risk': (r['risk'] or {}).get('score'), 'limiting': (r['risk'] or {}).get('limiting'),
                'refs_total': c.get('refs_total'), 'unique_meshes': c.get('unique_meshes')}
    todo = [r for r in cells.values() if not r['chim']['converted'] and not r['chim'].get('empty')]
    sp = sorted((r for r in todo if r['spiral_rank']), key=lambda r: r['spiral_rank'])
    rk = sorted((r for r in todo if r['risk_rank']), key=lambda r: r['risk_rank'])
    return {'format': 'aw-cell-next-1', 'generated': now, 'not_started': len(todo),
            'spiral': {'rule': 'sea-only cells with content first, then land ring by ring from the coast inwards; inside a '
                               'ring the nearest unvisited cell next, clockwise, starting beside the end of the ring before',
                       'cells': [row(r) for r in sp[:NEXT_LIMIT]]},
            'risk': {'rule': 'scout list: highest share of any engine limit first (estimator, everything scenario), '
                             'then most placed references', 'cells': [row(r) for r in rk[:NEXT_LIMIT]]}}


def update_history(out, head, builds, now):
    """Append a history line when the counts changed; return one entry per day (the last of the day)."""
    path = out / OUT_FILES['history']
    lines = [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()] if path.is_file() else []
    entry = {'date': now, 'passed': head['passed'], 'land_cells': head['land_cells'], 'converted': head['converted'],
             'buckets': {b: head[b] for b in BUCKETS}, 'builds': builds}
    same = lines and {k: v for k, v in lines[-1].items() if k != 'date'} == {k: v for k, v in entry.items() if k != 'date'}
    if not same:
        lines.append(entry)
        path.write_bytes(('\n'.join(json.dumps(x, sort_keys=True, separators=(',', ':')) for x in lines) + '\n').encode('utf-8'))
    per_day = collections.OrderedDict()
    for x in lines:
        per_day[x['date'][:10]] = x
    return list(per_day.values())[-366:]


# ------------------------------------------------------------------ writers other tools use

def record_audit(out, mechanism, build, cells, status=None, detail=None, now=None):
    """Write one audit result file. `cells` is {key: status or {status, detail}} or a list of keys with `status`."""
    if mechanism not in MECHANISMS:
        raise ValueError('unknown mechanism %r; known: %s' % (mechanism, ', '.join(MECHANISMS)))
    if isinstance(cells, (list, tuple, set)):
        cells = {k: {'status': status, 'detail': detail} for k in cells}
    norm = {}
    for k, v in cells.items():
        v = {'status': v} if isinstance(v, str) else dict(v)
        parse_cell(k)
        if v.get('status') not in ('passed', 'failed', 'accepted'):
            raise ValueError('%s: status must be passed, failed or accepted' % k)
        norm[k] = v
    doc = {'format': AUDIT_FORMAT, 'mechanism': mechanism, 'build': build, 'generated': now_iso(now), 'cells': norm}
    adir = Path(out) / 'audits'
    adir.mkdir(parents=True, exist_ok=True)
    n = len(list(adir.glob('%s-%s-*.json' % (mechanism, re.sub(r'[^A-Za-z0-9_.-]', '_', build or 'none')))))
    path = adir / ('%s-%s-%03d.json' % (mechanism, re.sub(r'[^A-Za-z0-9_.-]', '_', build or 'none'), n + 1))
    write_json(path, doc, pretty=True)
    return path


def record_owner(out, status, cells, note=None, now=None):
    if status not in OWNER_STATES:
        raise ValueError('owner status must be one of %s' % ', '.join(OWNER_STATES))
    path = Path(out) / OUT_FILES['owner']
    doc = read_json(path) or {'format': 'aw-cell-owner-1', 'cells': {}}
    for k in cells:
        parse_cell(k)
        doc['cells'][k] = {'status': status, 'date': now_iso(now)[:10], 'note': note}
    write_json(path, doc, pretty=True)
    return path


def record_result(out, doc, now=None):
    """Validate and store one per-cell result file of the conversion job (format aw-cell-result-1, see FORMAT.md)."""
    if not isinstance(doc, dict) or doc.get('format') != RESULT_FORMAT:
        raise ValueError('not a %s file' % RESULT_FORMAT)
    if not doc.get('build') or not isinstance(doc.get('cells'), dict):
        raise ValueError('a result file needs "build" and "cells"')
    for k, v in doc['cells'].items():
        parse_cell(k)
        if not isinstance(v, dict):
            raise ValueError('%s: cell result must be an object' % k)
        for m, a in (v.get('audits') or {}).items():
            if m not in MECHANISMS:
                raise ValueError('%s: unknown mechanism %r' % (k, m))
            if a.get('status') not in RESULTS:
                raise ValueError('%s: audit %s needs a status of %s' % (k, m, ', '.join(RESULTS)))
        if v.get('stats') is not None and not isinstance(v['stats'], dict):
            raise ValueError('%s: stats must be an object' % k)
    doc = dict(doc, generated=doc.get('generated') or now_iso(now))
    rdir = Path(out) / 'results'
    rdir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r'[^A-Za-z0-9_.-]', '_', doc['build'])
    path = rdir / ('%s-%03d.json' % (stem, len(list(rdir.glob(stem + '-*.json'))) + 1))
    write_json(path, doc, pretty=True)
    return path


def flat_numbers(d, prefix, out):
    for k, v in (d or {}).items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[prefix + k] = v
        elif isinstance(v, dict):
            flat_numbers(v, prefix + k + '.', out)
    return out


def export_csv(doc):
    """The tracker's cells as CSV text: status, audits and every numeric stat (same columns as the page's export)."""
    cells = sorted(doc['cells'].values(), key=lambda c: (c.get('spiral_rank') is None, c.get('spiral_rank') or 0, c['x'], c['y']))
    flats = [flat_numbers(c.get('stats'), 'stats.', {}) for c in cells]
    keys = sorted({k for f in flats for k in f})
    mech = [m['id'] for m in doc['mechanisms']]
    head = (['x', 'y', 'name', 'region', 'island', 'ring', 'spiral_rank', 'risk_rank', 'risk_score', 'land', 'chim_status',
             'chim_bucket', 'legacy_grade', 'legacy_placed_share', 'open_bugs', 'build', 'source_commit', 'chim_version',
             'world_format', 'errors'] + ['audit.' + m for m in mech] + keys)
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(head)
    for c, f in zip(cells, flats):
        pv = c.get('provenance') or {}
        lg = c.get('legacy') or {}
        open_bugs = sum(1 for b in c.get('bugs', []) if (doc['bugs'].get(b) or {}).get('state') not in ('fixed', 'closed'))
        row = [c['x'], c['y'], c['name'], c['region'], c.get('island'), c.get('ring'), c.get('spiral_rank'), c.get('risk_rank'),
               (c.get('risk') or {}).get('score'), c['land'], c['chim']['status'], c['chim']['bucket'], lg.get('grade'),
               lg.get('placed_share'), open_bugs, pv.get('build'), pv.get('source_commit'), pv.get('chim_version'),
               pv.get('world_format'), ' | '.join(error_text(x) for x in c.get('errors') or [])]
        row += [c['audits'][m]['status'] for m in mech] + [f.get(k) for k in keys]
        w.writerow(['' if v is None else v for v in row])
    return buf.getvalue()


# ------------------------------------------------------------------ command line

SOURCE_KEYS = ('progress', 'metrics', 'cells', 'census', 'bugs', 'ledger', 'areas')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    ing = sub.add_parser('ingest', help='fill the records from everything that exists now')
    ing.add_argument('--out', type=Path, required=True)
    for k in SOURCE_KEYS:
        ing.add_argument('--' + k, type=Path)
    ing.add_argument('--data-files', type=Path, help='your Morrowind Data Files: (re)makes the mesh census')
    ing.add_argument('--chim-run', action='append', default=[], metavar='NAME=PATH')
    ing.add_argument('--run-label', action='append', default=[], metavar='NAME=TEXT')
    ing.add_argument('--run-commit', action='append', default=[], metavar='NAME=SHA')
    ing.add_argument('--config-dir', type=Path, help='the repo config folder (scene lists give our map names of interiors)')
    ing.add_argument('--png', action='store_true', help='also write the mesh reuse curve as a PNG')
    ing.add_argument('--now', help='timestamp to stamp (tests)')
    rec = sub.add_parser('record', help='record audit results from another tool')
    rec.add_argument('--out', type=Path, required=True)
    rec.add_argument('--mechanism', required=True, choices=list(MECHANISMS))
    rec.add_argument('--build', required=True)
    rec.add_argument('--results', type=Path, help='JSON {"x,y": "passed|failed|accepted" or {status, detail}}')
    rec.add_argument('--status', choices=('passed', 'failed', 'accepted'))
    rec.add_argument('--cells', help='"x,y x,y ..." (with --status)')
    rec.add_argument('--detail')
    own = sub.add_parser('owner', help='mark cells playtested or owner-approved')
    own.add_argument('--out', type=Path, required=True)
    own.add_argument('--status', required=True, choices=OWNER_STATES)
    own.add_argument('--cells', required=True)
    own.add_argument('--note')
    res = sub.add_parser('result', help='store per-cell results (stats, audits, errors) of the conversion job')
    res.add_argument('--out', type=Path, required=True)
    res.add_argument('--file', type=Path, required=True, help='an aw-cell-result-1 file (see FORMAT.md)')
    exp = sub.add_parser('export', help='write the cells as CSV (and JSON)')
    exp.add_argument('--out', type=Path, required=True)
    exp.add_argument('--csv', type=Path)
    exp.add_argument('--json', type=Path)
    md = sub.add_parser('render-md', help='write the generated public page docs/chim/CELL_TRACKER.md')
    md.add_argument('--out', type=Path, required=True)
    md.add_argument('--md', type=Path, help='page to write (default: docs/chim/CELL_TRACKER.md of this repo)')
    md.add_argument('--now', help='generated stamp to print (tests; default: the host clock)')
    ck = sub.add_parser('check-md', help='fail when the committed page lacks its header, shows private content or has a stale policy')
    ck.add_argument('--md', type=Path)
    st = sub.add_parser('status', help='print the headline counts')
    st.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    out = a.out
    if a.cmd == 'status':
        doc = read_json(out / OUT_FILES['progress'])
        if not doc:
            print('no tracker data in %s yet; run ingest' % out)
            return 1
        h = doc['headline']
        print('Cell complete %d | CHIM cells: %d / %d (%.2f%%) | approved %d, playtested %d, audits passed %d, converted with failing audits %d, '
              'converted unmeasured %d, not started %d' % (h['complete'], h['passed'], h['land_cells'], h['percent'], h['approved'],
              h['playtested'], h['audits_passed'], h['converted_failing'], h['converted_unmeasured'], h['not_started']))
        return 0
    if a.cmd in ('render-md', 'check-md'):
        import cell_progress_md as MD
        page = a.md or Path(__file__).resolve().parents[1] / 'docs' / 'chim' / 'CELL_TRACKER.md'
        if a.cmd == 'check-md':
            problems = MD.check(page.read_bytes().decode('utf-8'))
            print('\n'.join(problems) if problems else 'ok: %s' % page)
            return 1 if problems else 0
        doc = read_json(a.out / OUT_FILES['progress'])
        if not doc:
            print('no tracker data in %s yet; run ingest' % a.out)
            return 1
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_bytes(MD.render(doc, a.now).encode('utf-8'))
        print('wrote', page)
        return 0
    if a.cmd == 'export':
        doc = read_json(out / OUT_FILES['progress'])
        if not doc:
            print('no tracker data in %s yet; run ingest' % out)
            return 1
        if a.csv:
            a.csv.write_bytes(export_csv(doc).encode('utf-8'))
            print('wrote', a.csv)
        if a.json:
            write_json(a.json, {'format': doc['format'], 'generated': doc['generated'], 'headline': doc['headline'],
                                'totals': doc['totals'], 'cells': doc['cells']}, pretty=True)
            print('wrote', a.json)
        return 0
    src_path = out / OUT_FILES['sources']
    if a.cmd == 'result':
        print('recorded', record_result(out, read_json(a.file)))
    elif a.cmd == 'record':
        results = read_json(a.results) if a.results else None
        cells = results if results is not None else a.cells.split()
        path = record_audit(out, a.mechanism, a.build, cells, a.status, a.detail)
        print('recorded', path)
    elif a.cmd == 'owner':
        print('recorded', record_owner(out, a.status, a.cells.split(), a.note))
    remembered = read_json(src_path) or {}
    if a.cmd == 'ingest':
        for k in SOURCE_KEYS + ('data_files', 'config_dir'):
            v = getattr(a, k)
            if v:
                remembered[k] = str(v)
        runs = dict(remembered.get('chim_runs', {}))
        for s in a.chim_run:
            runs[s.partition('=')[0]] = s.partition('=')[2]
        remembered['chim_runs'] = runs
        for opt, key in (('run_label', 'labels'), ('run_commit', 'commits')):
            d = dict(remembered.get(key, {}))
            d.update(dict(s.partition('=')[::2] for s in getattr(a, opt)))
            remembered[key] = d
        write_json(src_path, remembered, pretty=True)
    elif not remembered:
        print('record written; run `ingest` once with the inputs first to refresh the tracker')
        return 0
    census = None
    cen_path = out / 'mesh-census.json'
    if a.cmd == 'ingest' and a.data_files:
        census = build_census(a.data_files)
        write_json(cen_path, census)
    elif remembered.get('census'):
        census = read_json(remembered['census'])
    else:
        census = read_json(cen_path)
    # Only runs given on this command line are re-read from their folders; the rest come from their digests.
    run_specs = list(a.chim_run) if a.cmd == 'ingest' else []
    doc = ingest(out, read_json(remembered['progress']) if remembered.get('progress') else None,
                 read_json(remembered['metrics']) if remembered.get('metrics') else None,
                 read_json(remembered['cells']) if remembered.get('cells') else None, census, run_specs,
                 remembered.get('labels'), remembered.get('commits'),
                 read_json(remembered['bugs']) if remembered.get('bugs') else None, remembered.get('ledger'),
                 read_json(remembered['areas']) if remembered.get('areas') else None,
                 getattr(a, 'now', None), getattr(a, 'png', False) or (out / OUT_FILES['png']).is_file(),
                 remembered.get('config_dir') or str(Path(__file__).resolve().parents[1] / 'config'))
    h = doc['headline']
    print('CHIM cells: %d / %d (%.2f%%); converted %d, not started %d; %d cells recorded' %
          (h['passed'], h['land_cells'], h['percent'], h['converted'], h['not_started'], len(doc['cells'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
