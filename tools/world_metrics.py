#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Turn a world estimate table into the Toolkit's map metrics layer.

Input: metrics.json or metrics.csv as written by the builder's world estimate
(one row per proposed map: exterior sub-cell regions and interior cells, with
cur_* = what the converters convert today and evr_* = every placed object).
Output: one compact layer file (format aw-world-metrics-1) for the World Map's
"Map metrics" layer, read by tools/toolkit_serve.py --metrics:

  cells      per exterior cell (x, y): for each metric and scenario the worst
             value of the regions whose core lies in the cell, its ratio to the
             limit and the region it comes from; the cell's region ids; set
  regions    per exterior region id: core cells, set, counts, all values
  interiors  per interior map: name, set, counts, all values
  summary    cells with objects, and per metric how many cells, regions and
             interiors are over the limit

Cell aggregation is the world heat map's: a region counts for every cell in
its core; regions without any placed object are left out. Limits are the
engine's and the builder's own constants (see LIMITS). The layer holds game
derived names and numbers: keep it with your own data, never in the repo.

Usage:
  world_metrics.py METRICS.json|.csv --out world-metrics.json [--texinfo-limit today|planned]
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FORMAT = 'aw-world-metrics-1'
SCENARIOS = {'cur': 'current content (what the converters convert today)',
             'evr': 'everything (every placed object converted, actors as edicts)'}
TEXINFO_LIMITS = {'today': 32767, 'planned': 65535}


def heap_budget():
    """The map heap budget: check_world_map_heap's reserve (AMIWIND_HEAP_MB in sys_amiga.c)."""
    from check_world_map_heap import HEAP_RESERVE_BYTES
    return HEAP_RESERVE_BYTES


# metric -> (column stem, shared by both scenarios, limit, label, where the limit comes from)
LIMITS = {
    'heap': ('heap', False, heap_budget(), 'Estimated map heap', 'map heap budget, AMIWIND_HEAP_MB (sys_amiga.c)'),
    'faces': ('faces', False, 65535, 'Faces', 'MAX_MAP_FACES (bspfile.h)'),
    'texinfo': ('texinfo', False, TEXINFO_LIMITS['today'], 'Texinfo', 'signed short face texinfo (bspfile.h); 65,535 planned'),
    'nodes': ('nodes', False, 32767, 'Hull-0 nodes', 'MAX_MAP_NODES (bspfile.h)'),
    'clipnodes': ('clipnodes', False, 65520, 'Clipnodes', 'clipnode count check (model.c)'),
    'marksurfaces': ('marksurfaces', False, 65535, 'Marksurfaces', 'MAX_MAP_MARKSURFACES (bspfile.h)'),
    'vertexes': ('vertexes', False, 65535, 'Vertexes', 'MAX_MAP_VERTS (bspfile.h)'),
    'edicts': ('edicts', False, 600, 'Edicts', 'MAX_EDICTS (quakedef.h)'),
    'inline_models': ('inline_models', False, 220, 'Inline brush models', 'inline model budget (prepare_area.py; MAX_MODELS 256)'),
    'flames': ('flames', False, 128, 'Static flames', 'STATIC_FLAME_MAX (aw_guard_torch.c)'),
    'lights': ('lights', True, 32, 'Lights (if all were dynamic lights)', 'MAX_DLIGHTS (client.h)'),
}
# Short column headings for the Toolkit's tables.
SHORT = {'heap': 'Heap', 'nodes': 'Nodes', 'inline_models': 'Inline models', 'flames': 'Flames', 'lights': 'Lights'}
COUNTS = ('refs_total', 'npc', 'creatures', 'lights', 'load_doors', 'refs_items')


def number(v):
    """CSV text or JSON value -> int/float, or None when empty or not a number."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def read_rows(path):
    """Rows of a metrics.json ({"rows": [...]}) or metrics.csv; returns (rows, file limits or {})."""
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix.lower() == '.csv' or not raw.lstrip().startswith(b'{'):
        return list(csv.DictReader(raw.decode('utf-8-sig').splitlines())), {}
    doc = json.loads(raw.decode('utf-8'))
    if not isinstance(doc, dict) or not isinstance(doc.get('rows'), list):
        raise ValueError('%s: not a metrics table (no "rows" list)' % path.name)
    return doc['rows'], doc.get('limits') or {}


def limits_table(texinfo='today'):
    if texinfo not in TEXINFO_LIMITS:
        raise ValueError('texinfo limit must be one of %s' % ', '.join(TEXINFO_LIMITS))
    out = {}
    for k, (_, shared, limit, label, source) in LIMITS.items():
        out[k] = {'limit': TEXINFO_LIMITS[texinfo] if k == 'texinfo' else limit, 'label': label,
                  'short': SHORT.get(k, label), 'source': source, 'shared': shared}
    out['texinfo']['choices'] = dict(TEXINFO_LIMITS)
    out['texinfo']['choice'] = texinfo
    return out


def values(row, scen):
    """{metric: value or None} of one row in one scenario."""
    out = {}
    for k, (stem, shared, _, _, _) in LIMITS.items():
        out[k] = number(row.get(stem if shared else scen + '_' + stem))
    return out


def cells_of(text):
    out = []
    for c in str(text or '').split():
        x, _, y = c.partition(',')
        try:
            out.append((int(x), int(y)))
        except ValueError:
            raise ValueError('bad core cell %r' % c) from None
    return out


def ratio(v, limit):
    return None if v is None else round(v / limit, 4)


def convert(rows, texinfo='today', source=None):
    """Rows -> the aw-world-metrics-1 layer (a dict)."""
    limits = limits_table(texinfo)
    lim = {k: v['limit'] for k, v in limits.items()}
    regions, interiors, cells = {}, [], {}
    skipped = {'exterior_without_objects': 0, 'interior_without_objects': 0, 'other': 0}
    for r in rows:
        space, ident = str(r.get('space', '')).strip(), str(r.get('map', '')).strip()
        refs = number(r.get('refs_total'))
        if not ident or space not in ('exterior', 'interior'):
            skipped['other'] += 1
            continue
        if refs is not None and refs <= 0:   # sea-only regions and empty cells: nothing to build
            skipped[space + '_without_objects'] += 1
            continue
        entry = {'set': str(r.get('set') or ''), 'cur': values(r, 'cur'), 'evr': values(r, 'evr')}
        for k in COUNTS:
            if r.get(k) not in (None, ''):
                entry[k] = number(r.get(k))
        if space == 'interior':
            entry['id'] = ident
            entry['name'] = str(r.get('name') or '')
            interiors.append(entry)
            continue
        core = cells_of(r.get('core_cells'))
        if not core:
            skipped['other'] += 1
            continue
        if ident in regions:
            raise ValueError('duplicate region id %s' % ident)
        entry['frame'] = str(r.get('frame') or '')
        entry['cells'] = [list(c) for c in core]
        regions[ident] = entry
        for c in core:
            cell = cells.setdefault(c, {'x': c[0], 'y': c[1], 'sets': set(), 'regions': []})
            cell['sets'].add(entry['set'])
            cell['regions'].append(ident)
    out_cells = []
    over = {s: {k: {'cells': 0, 'regions': 0, 'interiors': 0, 'max_ratio': 0.0} for k in LIMITS} for s in SCENARIOS}
    for (x, y), cell in sorted(cells.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        worst = {}
        for s in SCENARIOS:
            worst[s] = {}
            for k in LIMITS:
                best = None
                for ident in cell['regions']:
                    v = regions[ident][s][k]
                    if v is not None and (best is None or v > best[0]):
                        best = (v, ident)
                if best is None:
                    continue
                worst[s][k] = [best[0], ratio(best[0], lim[k]), best[1]]
                if best[0] > lim[k]:
                    over[s][k]['cells'] += 1
        sets = sorted(cell['sets'])
        out_cells.append({'x': x, 'y': y, 'set': 'bloodmoon' if 'bloodmoon' in sets else sets[0] if sets else '',
                          'regions': cell['regions'], 'worst': worst})
    for s in SCENARIOS:
        for k in LIMITS:
            for kind, items in (('regions', regions.values()), ('interiors', interiors)):
                for e in items:
                    v = e[s][k]
                    if v is None:
                        continue
                    if v > lim[k]:
                        over[s][k][kind] += 1
                    over[s][k]['max_ratio'] = max(over[s][k]['max_ratio'], round(v / lim[k], 4))
    sets = sorted({e['set'] for e in list(regions.values()) + interiors if e['set']})
    return {
        'format': FORMAT, 'generator': 'tools/world_metrics.py', 'source': source or {},
        'scenarios': SCENARIOS, 'metrics': list(LIMITS), 'limits': limits,
        'aggregation': 'cell value = highest value of the regions whose core lies in the cell; regions without objects left out',
        'cells': out_cells, 'regions': regions, 'interiors': interiors,
        'summary': {'cells': len(out_cells), 'regions': len(regions), 'interiors': len(interiors), 'sets': sets,
                    'bloodmoon_cells': sum(1 for c in out_cells if c['set'] == 'bloodmoon'),
                    'skipped': skipped, 'over': over},
    }


def convert_file(path, texinfo='today'):
    path = Path(path)
    rows, _ = read_rows(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return convert(rows, texinfo, {'file': path.name, 'sha256': digest, 'rows': len(rows)})


def is_layer(doc):
    return isinstance(doc, dict) and doc.get('format') == FORMAT


def dumps(layer):
    return json.dumps(layer, separators=(',', ':'), sort_keys=False) + '\n'


def load_any(path, texinfo='today'):
    """A layer file as is, or a metrics table converted on the fly: returns the layer dict."""
    path = Path(path)
    if path.suffix.lower() == '.json':
        doc = json.loads(path.read_bytes().decode('utf-8'))
        if is_layer(doc):
            return doc
    return convert_file(path, texinfo)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('metrics', type=Path, help='metrics.json or metrics.csv from the world estimate')
    p.add_argument('--out', type=Path, required=True, help='layer file to write (aw-world-metrics-1)')
    p.add_argument('--texinfo-limit', choices=sorted(TEXINFO_LIMITS), default='today',
                   help='texinfo limit for the stored ratios and counts (the Toolkit can switch it too)')
    a = p.parse_args(argv)
    layer = convert_file(a.metrics, a.texinfo_limit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(dumps(layer).encode('utf-8'))
    s = layer['summary']
    heap = s['over']['evr']['heap']
    print('%s: %d cells, %d regions, %d interiors; everything: %d cells hold at least one region over the heap budget'
          % (a.out.name, s['cells'], s['regions'], s['interiors'], heap['cells']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
