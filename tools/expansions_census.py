#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Census of the two expansions (Tribunal, Bloodmoon) in the player's own Morrowind files.

Reads the masters and archives only; writes one JSON file and one Markdown table
block. Nothing derived from the game data is stored in this repository: the
numbers go to a private output folder, and docs/performance/EXPANSIONS-CENSUS-v0.0.64.md
carries only the counts.

Per expansion master it counts:
- exterior cells, split into land cells (a LAND record at the cell, in the
  expansion or the base game) and sea cells (no LAND record), and how many of
  them also exist in Morrowind.esm;
- interior cells;
- placed references per cell (maximum and median over the cells that hold at
  least one non-deleted placement), for exterior and interior cells;
- the models its placements use, and those that exist only in the expansion's
  own archive (not in Morrowind.bsa, not as a loose mesh);
- the tree references by model (TREES-DEPTH-56: the Solstheim spruces);
- the base-game cells the master edits: cells that also exist in Morrowind.esm
  and whose references carry a non-zero master index in the reference number
  (the decoding of tools/mwscript/gamedata.py: the top byte of FRMR is the
  1-based index into the file's own master list, 0 = new in this file).

Usage:
  expansions_census.py --data-files DIR --out DIR
"""
import argparse
import collections
import json
import os
import statistics
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_estimate_data as D  # noqa: E402
from mwad.audit import BSA, records, subrecords  # noqa: E402
from mwad.paths import child_ci  # noqa: E402

BASE = 'Morrowind.esm'
EXPANSIONS = (('Tribunal.esm', 'Tribunal.bsa', 'tribunal', 'Mournhold'),
              ('Bloodmoon.esm', 'Bloodmoon.bsa', 'bloodmoon', 'Solstheim'))
TREE_WORDS = ('tree', 'spruce', 'pine')
TOP_EDITED = 12


def master_names(path):
    """The file's own master list (TES3 MAST subrecords, in order)."""
    raw = Path(path).read_bytes()
    for tag, _flags, payload in records(raw):
        if tag == 'TES3':
            return [D.cstr(v) for t, v in subrecords(payload) if t == 'MAST']
        break
    return []


def moved_references(path):
    """Moved references (MVRF) per cell key in one master: a base-game reference this file moves into another cell.
    The census parser skips them, so they are counted here from the raw records."""
    moved = collections.Counter()
    for tag, _flags, payload in records(Path(path).read_bytes()):
        if tag != 'CELL':
            continue
        name, data, count = b'', b'', 0
        for k, v in subrecords(payload):
            if k == 'FRMR':
                break
            if k == 'NAME' and not name:
                name = v
            elif k == 'DATA' and not data:
                data = v
        for k, v in subrecords(payload):
            if k == 'MVRF':
                count += 1
        if count and len(data) == 12:
            flags, x, y = struct.unpack('<Iii', data)
            moved[('i', D.cstr(name).casefold()) if flags & 1 else ('e', x, y)] += count
    return moved


def archive_names(path):
    if path is None or not Path(path).is_file():
        return set()
    return set(BSA(Path(path)).entries)


def loose_names(data_files):
    """Lower-case relative paths of every loose file under a Meshes folder."""
    names = set()
    root = child_ci(Path(data_files), 'Meshes', required=False)
    if root is None or not root.is_dir():
        return names
    for dirpath, _dirs, files in os.walk(root):
        rel = Path(dirpath).relative_to(root.parent)
        for f in files:
            names.add((rel / f).as_posix().lower())
    return names


def _live(cell):
    return [r for r in cell['refs'] if not r.get('del')]


def _spread(counts):
    counts = [c for c in counts if c > 0]
    if not counts:
        return {'cells_with_placements': 0, 'max': 0, 'median': 0, 'total': 0}
    return {'cells_with_placements': len(counts), 'max': max(counts), 'median': _num(statistics.median(counts)),
            'total': sum(counts)}


def _cell_key(cell):
    return ('i', cell['name'].casefold()) if cell['interior'] else ('e', cell['x'], cell['y'])


def _cell_label(cell):
    if cell['interior']:
        return cell['name']
    return '%s (%d,%d)' % (cell['name'], cell['x'], cell['y']) if cell['name'] else 'exterior (%d,%d)' % (
        cell['x'], cell['y'])


def _num(x):
    return int(x) if x == int(x) else round(x, 1)


def census_one(master, parsed, objects, base_cells, base_lands, master_list, own_archive, base_archive, loose,
               moved=None):
    """The numbers of one expansion master. OBJECTS = every object definition up to this master."""
    cells = [c for c in parsed['cells'] if not c['deleted']]
    exts = [c for c in cells if not c['interior']]
    ints = [c for c in cells if c['interior']]
    own_lands = set(parsed['lands'])
    land = [c for c in exts if (c['x'], c['y']) in own_lands or (c['x'], c['y']) in base_lands]
    land_ids = {id(c) for c in land}
    sea = [c for c in exts if id(c) not in land_ids]
    in_base = [c for c in cells if _cell_key(c) in base_cells]
    new_ext = [c for c in exts if _cell_key(c) not in base_cells]
    new_land = [c for c in new_ext if id(c) in land_ids]
    ext_in_base = [c for c in in_base if not c['interior']]

    models = collections.Counter()           # model path -> placements
    tree_models = collections.Counter()
    tree_cells = collections.defaultdict(set)
    trees_per_cell = []
    for c in cells:
        in_cell = 0
        for r in _live(c):
            o = objects.get(r['id'])
            model = o['model'] if o else ''
            if model:
                models[model] += 1
                if not c['interior'] and any(w in model.rsplit('/', 1)[-1] for w in TREE_WORDS):
                    tree_models[model] += 1
                    tree_cells[model].add((c['x'], c['y']))
                    in_cell += 1
        trees_per_cell.append(in_cell)
    own_defined = {o['model'] for o in parsed['objects'].values() if o['model']}
    used = set(models) | own_defined
    not_in_base_archive = sorted(m for m in used if m in own_archive and m not in base_archive)
    only_here = [m for m in not_in_base_archive if m not in loose]
    missing = sorted(m for m in used if m not in own_archive and m not in base_archive and m not in loose)
    only_placed = [m for m in only_here if m in models]

    moved = moved or {}
    edited = []
    for c in in_base:
        owners = collections.Counter()
        new = 0
        for r in _live(c):
            top = r['n'] >> 24
            if top == 0:
                new += 1
            else:
                owners[master_list[top - 1] if top <= len(master_list) else '#%d' % top] += 1
        edited.append({'cell': _cell_label(c), 'interior': c['interior'], 'new_placements': new,
                       'edited_placements': sum(owners.values()), 'edits_of': dict(owners),
                       'deleted_references': len(c['refs']) - len(_live(c)),
                       'moved_references': moved.get(_cell_key(c), 0)})
    with_edits = [e for e in edited if e['edited_placements']]
    with_edits.sort(key=lambda e: (-e['edited_placements'], e['cell']))
    new_in_base = sorted((e for e in edited if e['new_placements']), key=lambda e: (-e['new_placements'], e['cell']))
    like_ext = [c for c in ints if c['flags'] & 0x80]
    like_ext_rows = sorted(({'cell': c['name'], 'placements': len(_live(c))} for c in like_ext),
                           key=lambda r: (-r['placements'], r['cell']))
    ref_top = collections.Counter()
    for c in cells:
        for r in _live(c):
            ref_top[r['n'] >> 24] += 1

    return {
        'master': master, 'sha256': parsed['sha256'], 'master_list': master_list,
        'records': parsed['counts'],
        'cells_total': len(cells),
        'exterior_cells': len(exts), 'exterior_land': len(land), 'exterior_sea': len(sea),
        'exterior_bounds': ([min(c['x'] for c in exts), max(c['x'] for c in exts),
                             min(c['y'] for c in exts), max(c['y'] for c in exts)] if exts else None),
        'exterior_in_base_game': len(ext_in_base),
        'exterior_new': len(new_ext), 'exterior_new_land': len(new_land),
        'exterior_new_sea': len(new_ext) - len(new_land),
        'placements_exterior_new': _spread([len(_live(c)) for c in new_ext]),
        'interior_cells': len(ints), 'interior_in_base_game': len(in_base) - len(ext_in_base),
        'interior_with_placements': sum(1 for c in ints if _live(c)),
        'land_records_own': len(own_lands),
        'placements_exterior': _spread([len(_live(c)) for c in exts]),
        'placements_interior': _spread([len(_live(c)) for c in ints]),
        'placements_all_cells': _spread([len(_live(c)) for c in cells]),
        'reference_master_index': {str(k): v for k, v in sorted(ref_top.items())},
        'models_referenced_distinct': len(models),
        'models_defined_by_this_master': len(own_defined),
        'interiors_behaving_like_exterior': len(like_ext),
        'interiors_behaving_like_exterior_cells': like_ext_rows,
        'moved_references_total': sum(moved.values()),
        'models_not_in_base_archive': len(not_in_base_archive),
        'models_not_in_base_archive_and_not_loose': len(only_here),
        'models_only_in_own_archive': len(only_here),
        'models_only_in_own_archive_placed': len(only_placed),
        'placements_of_those_models': sum(models[m] for m in only_placed),
        'models_missing_everywhere': len(missing),
        'own_archive_files': len(own_archive),
        'tree_models': [{'model': m, 'placements': n, 'cells': len(tree_cells[m]),
                         'only_in_own_archive': m in only_here}
                        for m, n in sorted(tree_models.items(), key=lambda kv: (-kv[1], kv[0]))],
        'tree_placements': sum(tree_models.values()),
        'tree_placements_per_cell': _spread(trees_per_cell),
        'models_top': [{'model': m, 'placements': n} for m, n in models.most_common(15)],
        'base_cells_edited': len(with_edits),
        'base_cells_edited_top': with_edits[:TOP_EDITED],
        'base_cells_with_new_placements': len(new_in_base),
        'base_cells_with_new_placements_top': new_in_base[:TOP_EDITED],
    }


def census_expansions(data_files, parsed=None):
    """The census of every expansion master present in DATA_FILES. PARSED = world_estimate_data.census()."""
    data_files = Path(data_files)
    parsed = parsed or D.census(data_files)
    base = parsed[BASE]
    base_cells = {_cell_key(c) for c in base['cells'] if not c['deleted']}
    base_lands = set(base['lands'])
    base_archive = archive_names(child_ci(data_files, 'Morrowind.bsa', required=False))
    loose = loose_names(data_files)
    objects = dict(base['objects'])
    out = {'base_game': {'master': BASE, 'sha256': base['sha256'], 'cells': len(base['cells']),
                         'archive_files': len(base_archive), 'loose_mesh_files': len(loose)},
           'expansions': {}}
    for master, bsa, key, place in EXPANSIONS:
        if master not in parsed:
            continue
        objects.update(parsed[master]['objects'])
        path = child_ci(data_files, master)
        res = census_one(master, parsed[master], objects, base_cells, base_lands, master_names(path),
                         archive_names(child_ci(data_files, bsa, required=False)), base_archive, loose,
                         moved_references(path))
        res['place'] = place
        out['expansions'][key] = res
    return out


# ---------------------------------------------------------------- output

def _row(*cells):
    return '| ' + ' | '.join(str(c) for c in cells) + ' |'


def render_markdown(result):
    exp = result['expansions']
    keys = list(exp)
    lines = []
    head = ['', *[exp[k]['place'] + ' (' + exp[k]['master'] + ')' for k in keys]]
    lines += [_row(*head), _row(*['---'] * len(head))]

    def line(label, fn):
        lines.append(_row(label, *[fn(exp[k]) for k in keys]))
    line('Cells (not deleted)', lambda e: e['cells_total'])
    line('Exterior cells', lambda e: e['exterior_cells'])
    line('Exterior land cells (a LAND record)', lambda e: e['exterior_land'])
    line('Exterior sea cells (no LAND record)', lambda e: e['exterior_sea'])
    line('LAND records in the master itself', lambda e: e['land_records_own'])
    line('Exterior cells not in Morrowind.esm (new ground): land / sea',
         lambda e: '%d / %d' % (e['exterior_new_land'], e['exterior_new_sea']))
    line('Placements per new exterior cell, maximum', lambda e: e['placements_exterior_new']['max'])
    line('Placements per new exterior cell, median', lambda e: e['placements_exterior_new']['median'])
    line('Placements in new exterior cells, total', lambda e: e['placements_exterior_new']['total'])
    line('Exterior cell box (x min, x max, y min, y max)', lambda e: e['exterior_bounds'])
    line('Interior cells', lambda e: e['interior_cells'])
    line('Interior cells with at least one placement', lambda e: e['interior_with_placements'])
    for label, k in (('exterior', 'placements_exterior'), ('interior', 'placements_interior')):
        line('Placements per %s cell, maximum' % label, lambda e, k=k: e[k]['max'])
        line('Placements per %s cell, median' % label, lambda e, k=k: e[k]['median'])
        line('Placements in %s cells, total' % label, lambda e, k=k: e[k]['total'])
    line('Models its placements use (distinct)', lambda e: e['models_referenced_distinct'])
    line('Interior cells that behave like an exterior (cell flag 0x80)', lambda e: e['interiors_behaving_like_exterior'])
    line('Models used by its placements that its own archive holds and Morrowind.bsa does not',
         lambda e: e['models_not_in_base_archive'])
    line('... of those, also not a loose mesh in the data folder', lambda e: e['models_only_in_own_archive'])
    line('Models used but in no archive and not loose', lambda e: e['models_missing_everywhere'])
    line('Files in its own archive', lambda e: e['own_archive_files'])
    line('Cells that also exist in Morrowind.esm (exterior / interior)',
         lambda e: '%d / %d' % (e['exterior_in_base_game'], e['interior_in_base_game']))
    line('... of those, with placements of its own', lambda e: e['base_cells_with_new_placements'])
    line('References with a non-zero master index (edits of a base-game placement)',
         lambda e: sum(v for k, v in e['reference_master_index'].items() if k != '0'))
    line('Moved references (MVRF)', lambda e: e['moved_references_total'])
    out = ['\n'.join(lines), '']
    for k in keys:
        e = exp[k]
        out.append('### %s: base-game cells that receive placements from %s' % (e['place'], e['master']))
        out.append('')
        out.append(_row('Cell', 'Kind', 'New placements', 'Edited references', 'Deleted references',
                        'Moved references'))
        out.append(_row('---', '---', '---', '---', '---', '---'))
        for c in e['base_cells_with_new_placements_top']:
            out.append(_row(c['cell'], 'interior' if c['interior'] else 'exterior', c['new_placements'],
                            c['edited_placements'], c['deleted_references'], c['moved_references']))
        out.append('')
        if e['interiors_behaving_like_exterior_cells']:
            out.append('### %s: interior cells that behave like an exterior' % e['place'])
            out.append('')
            out.append(_row('Cell', 'Placements'))
            out.append(_row('---', '---'))
            for c in e['interiors_behaving_like_exterior_cells']:
                out.append(_row(c['cell'], c['placements']))
            out.append('')
        if e['tree_models']:
            out.append('### %s: tree references by model (exterior cells; names containing %s)'
                       % (e['place'], ', '.join('"%s"' % w for w in TREE_WORDS)))
            out.append('')
            out.append(_row('Model', 'Placements', 'Cells', 'Only in its own archive'))
            out.append(_row('---', '---', '---', '---'))
            for t in e['tree_models']:
                out.append(_row(t['model'], t['placements'], t['cells'], 'yes' if t['only_in_own_archive'] else 'no'))
            out.append('')
            tp = e['tree_placements_per_cell']
            out.append('Tree placements, total: %d in %d exterior cells (per cell: maximum %s, median %s)'
                       % (e['tree_placements'], tp['cells_with_placements'], tp['max'], tp['median']))
            out.append('')
        out.append('### %s: the 15 most placed models' % e['place'])
        out.append('')
        out.append(_row('Model', 'Placements'))
        out.append(_row('---', '---'))
        for m in e['models_top']:
            out.append(_row(m['model'], m['placements']))
        out.append('')
    return '\n'.join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True, help='Your Morrowind Data Files folder')
    p.add_argument('--out', type=Path, required=True, help='Output folder (census.json, census.md)')
    args = p.parse_args(argv)
    print('=== PHASE 1/2: reading the masters and archives ===', flush=True)
    result = census_expansions(args.data_files)
    print('=== PHASE 2/2: writing the census ===', flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'census.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                          newline='\n')
    (args.out / 'census.md').write_text(render_markdown(result), encoding='utf-8', newline='\n')
    for k, e in result['expansions'].items():
        print('%s: %d exterior (%d land, %d sea), %d interior, %d tree placements' % (
            k, e['exterior_cells'], e['exterior_land'], e['exterior_sea'], e['interior_cells'],
            e['tree_placements']), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
