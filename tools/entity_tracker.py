#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Entity tracker: what the original game places versus what AmiWind places.

Original side: every placed reference in the owner's master file (one row per
placement: reference number, base record type, category, cell). AmiWind side:
the reference numbers carried by the shipped maps' entities (`aw_ref`, written
for scenery, doors, flora, harvest plants, NPCs and corpses). A reference
number identifies one placement in the master, so the two sides join on it.

The report holds counts, categories and cell names, plus per cell and category
a digest of the placed reference numbers (`placed_digests`), so one missing
placement is visible without listing them. The image build's own report (private,
beside the image) also lists the placed numbers (`placed_refs`) to name what went
missing; `baseline` strips them for the release baseline kept in the repository
(config/entity-baseline.json). A missing placement gets the reason the evidence
supports:
  cell_not_converted         no shipped map places anything from its cell
  outside_world_scope        only world maps (vf*) place things from its cell, and
                             they carry no placement of its category anywhere
  deliberately_skipped       an interior converter rule leaves it out (the rule's
                             own reason is counted under "skipped")
  category_not_implemented   nothing of its category is placed anywhere
  not_placed                 its cell and category are converted, it is not

Usage:
  entity_tracker.py report --master Morrowind.esm --maps DIR [--maps DIR...]
                    --out entity-tracker.json [--previous OLD.json] [--private]
  entity_tracker.py compare OLD.json NEW.json
  entity_tracker.py baseline REPORT.json --release vX.Y.Z --out config/entity-baseline.json
"""
import argparse, collections, hashlib, json, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import cell_data, records, string, subrecords  # noqa: E402
from mwad.interior import omission_reason  # noqa: E402
from world_flora import flora_kind  # noqa: E402
from world_scenery import scenery_kind  # noqa: E402

FORMAT = 'AW-ENTITY-TRACKER1'
ITEM_TYPES = ('MISC', 'WEAP', 'ARMO', 'CLOT', 'BOOK', 'ALCH', 'APPA', 'LOCK', 'PROB', 'REPA', 'INGR', 'LEVI')
PLACEABLE = ('STAT', 'DOOR', 'CONT', 'LIGH', 'ACTI', 'NPC_', 'CREA', 'LEVC', *ITEM_TYPES)
CATEGORIES = ('rock', 'giant_mushroom', 'tree', 'plant', 'harvest_plant', 'static', 'door', 'container',
              'light', 'activator', 'npc', 'creature', 'item')
REASONS = ('cell_not_converted', 'outside_world_scope', 'deliberately_skipped', 'category_not_implemented',
           'not_placed')
# The open-world maps carry the land, rocks, giant mushrooms, trees and flora
# outside the fully converted towns and interiors.
WORLD_MAP = re.compile(r'(^|/)vf[0-9]+\.bsp$', re.I)
# Compare gate: a category that had placements and now has none, or loses more
# than this share (and at least MIN_LOSS placements), fails.
MAX_LOSS_SHARE = 0.05
MIN_LOSS = 10
BASELINE_FORMAT = 'AW-ENTITY-BASELINE1'
ENTITY = re.compile(rb'\{([^{}]*)\}')
FIELD = re.compile(rb'"([^"]*)"\s+"([^"]*)"')


def category(record_type, model):
    """Tracker category of one base record (type plus model, as the converters classify)."""
    if record_type == 'NPC_':
        return 'npc'
    if record_type in ('CREA', 'LEVC'):
        return 'creature'
    if record_type in ITEM_TYPES:
        return 'item'
    if record_type in ('DOOR', 'LIGH', 'ACTI'):
        return {'DOOR': 'door', 'LIGH': 'light', 'ACTI': 'activator'}[record_type]
    kind = flora_kind(model) if model else None
    if record_type == 'CONT':
        # Organic containers are the pickable plants (flora_* models).
        return 'harvest_plant' if kind or Path(model.replace('\\', '/')).name.lower().startswith('flora_') else 'container'
    special = scenery_kind(None, {'type': record_type, 'model': model})
    if special:
        return special
    if kind == 'tree':
        return 'tree'
    if kind:
        return 'plant'
    return 'static'


def census(master):
    """One row per non-deleted placed reference: (number, category, cell key,
    interior converter omission reason or None)."""
    bases, cells = {}, []
    for tag, flags, payload in records(master):
        if flags & 0x20:
            continue
        if tag == 'CELL':
            cells.append(cell_data(list(subrecords(payload))))
        elif tag in PLACEABLE:
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'DELE' not in fields:
                model = string(fields.get('MODL', b''))
                bases[string(fields['NAME']).casefold()] = (category(tag, model), tag, model)
    rows, unresolved = [], 0
    for cell in cells:
        interior = bool(cell['flags'] & 1)
        key = 'interior:' + cell['name'] if interior else 'exterior:%d,%d' % (cell['x'], cell['y'])
        for ref in cell['refs']:
            if ref.get('deleted'):
                continue
            known = bases.get(ref['id'].casefold())
            if known is None:
                unresolved += 1
                continue
            cat, tag, model = known
            skip = omission_reason(dict(ref, type=tag, model=model)) if interior else None
            rows.append((ref['number'], cat, key, skip))
    numbers = collections.Counter(r[0] for r in rows)
    duplicated = sum(1 for n in numbers.values() if n > 1)
    if duplicated:
        raise ValueError('reference numbers are not unique in the master (%d repeated)' % duplicated)
    return rows, unresolved


def bsp_refs(data):
    """Reference numbers carried by one BSP29 map's entities."""
    version, offset, size = struct.unpack_from('<iii', data, 0)
    if version != 29:
        raise ValueError('not a BSP29 map')
    out = set()
    for body in ENTITY.findall(data[offset:offset + size]):
        value = dict(FIELD.findall(body)).get(b'aw_ref')
        if value is not None and value.isdigit():
            out.add(int(value))
    return out


def harvest_refs(raw):
    """Reference numbers of the plants of one AWH3/AWH4 harvest catalogue."""
    lines = raw.decode('ascii').splitlines()
    header = lines[0].split() if lines else []
    if not header or header[0] not in ('AWH3', 'AWH4'):
        return set()
    nodes, edges, plants = map(int, header[1:4])
    first = 1 + (int(header[6]) if header[0] == 'AWH4' else 0) + nodes + edges
    return {int(line.split()[2]) for line in lines[first:first + plants]}


def _path_refs(path):
    """Worker: reference numbers of one map file and of its harvest catalogue
    (harvestable plants are placed by the catalogue beside the maps folder)."""
    path = Path(path)
    catalogue = path.parent.parent / ('harvest-' + path.stem + '.txt')
    return bsp_refs(path.read_bytes()) | (harvest_refs(catalogue.read_bytes()) if catalogue.is_file() else set())


def refs_by_map(dirs, jobs=1):
    """{map file stem: reference numbers its entities carry} for every BSP.

    Maps are read by up to `jobs` workers (shared pool); the result keeps the
    serial order (directory order, then sorted paths; a later stem wins).
    """
    from build_parallel import ordered_map
    paths = [path for d in dirs for path in sorted(Path(d).rglob('*'))
             if path.suffix.lower() == '.bsp' and path.is_file()]
    out = {}
    for path, refs in zip(paths, ordered_map(_path_refs, [str(p) for p in paths], max(1, min(jobs, len(paths) or 1)))):
        out[path.stem.lower()] = refs
    return out


def split_placed(by_map):
    """(all placed numbers, numbers placed by a non-world map, map count)."""
    placed, full = set(), set()
    for name, refs in by_map.items():
        placed |= refs
        if not WORLD_MAP.search(name + '.bsp'):
            full |= refs
    return placed, full, len(by_map)


def placed_from_dirs(dirs):
    """(all placed numbers, numbers placed by a non-world map, map count)."""
    return split_placed(refs_by_map(dirs))


def map_cells(rows, by_map):
    """{map stem: sorted exterior cell keys it places something from}."""
    cell_of = {number: key for number, _, key, _ in rows if key.startswith('exterior:')}
    out = {}
    for name, refs in sorted(by_map.items()):
        cells = sorted({cell_of[n] for n in refs if n in cell_of})
        if cells:
            out[name] = cells
    return out


def placed_digest(numbers):
    """Digest of a set of placed reference numbers: the first 16 hex digits of
    the SHA-256 of the sorted numbers, comma separated (a change detector)."""
    return hashlib.sha256(','.join(map(str, sorted(numbers))).encode('ascii')).hexdigest()[:16]


def report(rows, placed, maps, master_sha256, unresolved=0, full=None, private=False):
    """full: numbers placed by non-world maps (None: every map is a full map).
    private: also list the placed numbers per cell and category (build report)."""
    full = placed if full is None else full
    placed_cells = {key for number, _, key, _ in rows if number in placed}
    full_cells = {key for number, _, key, _ in rows if number in full}
    placed_cats = {cat for number, cat, _, _ in rows if number in placed}
    world_cats = {cat for number, cat, _, _ in rows if number in placed and number not in full}
    totals = {c: {s: dict(original=0, placed=0, **{r: 0 for r in REASONS}) for s in ('exterior', 'interior')}
              for c in CATEGORIES}
    skipped = collections.Counter()
    cells = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    numbers = collections.defaultdict(lambda: collections.defaultdict(list))
    for number, cat, key, skip in rows:
        space = key.split(':', 1)[0]
        t = totals[cat][space]; t['original'] += 1
        cells[key][cat][0] += 1
        if number in placed:
            t['placed'] += 1; cells[key][cat][1] += 1; numbers[key][cat].append(number)
        elif key not in placed_cells:
            t['cell_not_converted'] += 1
        elif key not in full_cells and cat not in world_cats:
            t['outside_world_scope'] += 1
        elif skip:
            t['deliberately_skipped'] += 1; skipped[skip] += 1
        elif cat not in placed_cats:
            t['category_not_implemented'] += 1
        else:
            t['not_placed'] += 1
    known = {number for number, _, _, _ in rows}
    out = {'format': FORMAT, 'master_sha256': master_sha256, 'maps': maps,
            'unresolved_base_records': unresolved,
            'placed_numbers_not_in_master': len(placed - known),
            'totals': totals,
            'skipped': dict(sorted(skipped.items())),
            'converted_cells': sorted(placed_cells),
            'world_only_cells': len(placed_cells - full_cells),
            'full_cells': sorted(full_cells),
            'cells': {k: {c: v for c, v in sorted(cats.items())} for k, cats in sorted(cells.items())},
            'placed_digests': {k: {c: placed_digest(v) for c, v in sorted(cats.items())}
                               for k, cats in sorted(numbers.items())}}
    if private:
        out['placed_refs'] = {k: {c: sorted(v) for c, v in sorted(cats.items())} for k, cats in sorted(numbers.items())}
    return out


def baseline(result, release):
    """The public release baseline of a report: counts and digests, no reference
    numbers; only cells with placements (the ones the comparison checks)."""
    digests = result['placed_digests']
    return {'format': BASELINE_FORMAT, 'release': release, 'master_sha256': result['master_sha256'],
            'totals': result['totals'],
            'cells': {k: {c: result['cells'][k][c] for c in cats} for k, cats in sorted(digests.items())},
            'placed_digests': digests}


def dump_baseline(base):
    """Baseline text: JSON with one line per cell (small, diffable, LF)."""
    compact = dict(sort_keys=True, separators=(',', ':'))
    lines = ['{']
    for key in ('format', 'release', 'master_sha256', 'totals'):
        lines.append('%s: %s,' % (json.dumps(key), json.dumps(base[key], **compact)))
    for key in ('cells', 'placed_digests'):
        rows = sorted(base[key].items())
        lines.append('%s: {' % json.dumps(key))
        lines += ['%s: %s%s' % (json.dumps(k), json.dumps(v, **compact), ',' if i < len(rows) - 1 else '')
                  for i, (k, v) in enumerate(rows)]
        lines.append('},' if key == 'cells' else '}')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def cell_losses(old, new):
    """Per cell and category: fewer placements than before, or the same number
    of other placements (digest differs). Needs the same master (reference
    numbers are master-specific) and digests on both sides."""
    if old.get('master_sha256') != new.get('master_sha256') or 'placed_digests' not in old or 'placed_digests' not in new:
        return []
    problems = []
    for key, cats in sorted(old['placed_digests'].items()):
        for cat, digest in sorted(cats.items()):
            a = old['cells'][key][cat][1]
            b = new['cells'].get(key, {}).get(cat, [0, 0])[1]
            refs = old.get('placed_refs', {}).get(key, {}).get(cat)
            gone = sorted(set(refs) - set(new.get('placed_refs', {}).get(key, {}).get(cat, []))) if refs and 'placed_refs' in new else []
            named = ' (references %s)' % ', '.join(map(str, gone[:8])) if gone else ''
            if b < a:
                problems.append('%s %s: %d -> %d placed%s' % (key, cat, a, b, named))
            elif b == a and new['placed_digests'].get(key, {}).get(cat) != digest:
                problems.append('%s %s: %d placed, other placements than before%s' % (key, cat, a, named))
    return problems


def compare(old, new):
    """Failures for categories that vanished or lost many placements, and with
    digests (same master), for any cell and category that lost a placement."""
    problems = []
    for cat in CATEGORIES:
        for space in ('exterior', 'interior'):
            a = old['totals'].get(cat, {}).get(space, {}).get('placed', 0)
            b = new['totals'][cat][space]['placed']
            if a > 0 and b == 0:
                problems.append('%s %s: %d placed before, none now' % (space, cat, a))
            elif a - b >= MIN_LOSS and (a - b) > a * MAX_LOSS_SHARE:
                problems.append('%s %s: %d -> %d placed (-%d)' % (space, cat, a, b, a - b))
    return problems + cell_losses(old, new)


DRESSING_TRACK = 'dressing-track.json'


def dressing_placements(master, by_map, terms):
    """{map stem: [placed interior dressing pieces]}: placements in interior
    cells whose base model path contains one of `terms` (prepare_mesh_bsp
    DRESSING_EXCLUDED), with reference, id, model, rule and cell. Private:
    for the build report only (BUILD-DRESSING-EXCLUDED-32)."""
    models, cells = {}, []
    for tag, flags, payload in records(master):
        if flags & 0x20:
            continue
        if tag == 'CELL':
            cells.append(cell_data(list(subrecords(payload))))
        elif tag in PLACEABLE:
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'DELE' not in fields:
                models[string(fields['NAME']).casefold()] = string(fields.get('MODL', b''))
    pieces = {}
    for cell in cells:
        if not cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            model = models.get(ref['id'].casefold(), '') if not ref.get('deleted') else ''
            path = 'meshes/' + model.replace('\\', '/').lower()
            rule = next((term for term in terms if term in path), None) if model else None
            if rule:
                pieces[ref['number']] = dict(reference=ref['number'], id=ref['id'], model=path, rule=rule,
                                             cell=cell['name'])
    out = {}
    for name, refs in sorted(by_map.items()):
        found = [pieces[n] for n in sorted(refs) if n in pieces]
        if found:
            out[name] = found
    return out


def add_heap(track_path, world_heap):
    """Add each tracked map's modelled heap estimate (check_world_map_heap) to the dressing track."""
    track_path = Path(track_path)
    track = json.loads(track_path.read_text(encoding='utf-8'))
    rows = {Path(r['map']).stem.lower(): r for r in world_heap.get('maps', [])}
    for name, entry in track['maps'].items():
        row = rows.get(name)
        entry['heap'] = None if row is None else {k: row.get(k) for k in (
            'gate', 'estimated_total_bytes', 'estimated_clearance_bytes')}
    track['heap'] = 'modelled heap estimate of each map with its dressing (world-map-heap.json)'
    track_path.write_text(json.dumps(track, indent=1) + '\n', encoding='utf-8', newline='\n')
    return track


def build_gate(out, maps_dir, master_path, baseline=None, accepted_loss=None, jobs=1, dressing_terms=()):
    """Image build step: write entity-tracker.json for the final staged maps and
    compare with the previous build's report. An unexplained loss stops the
    build; --accept-entity-loss REASON records why a loss is intended."""
    out = Path(out)
    master = Path(master_path).read_bytes()
    rows, unresolved = census(master)
    by_map = refs_by_map([maps_dir], jobs)
    placed, full, maps = split_placed(by_map)
    result = report(rows, placed, maps, hashlib.sha256(master).hexdigest(), unresolved, full, private=True)
    result['map_cells'] = map_cells(rows, by_map)
    path = out / 'entity-tracker.json'
    path.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(terminal(result), end='', flush=True)
    dressing = None
    if dressing_terms:
        # Keep a track of the interior dressing the image places (owner, BUILD-DRESSING-EXCLUDED-32).
        found = dressing_placements(master, by_map, dressing_terms)
        track = dict(format='AW-DRESSING-TRACK1', rules=list(dressing_terms),
                     pieces=sum(len(v) for v in found.values()),
                     maps={name: dict(pieces=rows_) for name, rows_ in found.items()})
        (out / DRESSING_TRACK).write_text(json.dumps(track, indent=1) + '\n', encoding='utf-8', newline='\n')
        dressing = dict(report=DRESSING_TRACK, pieces=track['pieces'], maps=len(found))
        print('Interior dressing placed: %d pieces in %d maps (%s)' % (track['pieces'], len(found), DRESSING_TRACK),
              flush=True)
    problems = compare(json.loads(Path(baseline).read_text(encoding='utf-8')), result) if baseline else []
    if problems and not accepted_loss:
        raise ValueError('Entity tracker: placements lost against the baseline (pass '
                         '--accept-entity-loss REASON if intended): ' + '; '.join(problems))
    return dict(report=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                baseline_sha256=hashlib.sha256(Path(baseline).read_bytes()).hexdigest() if baseline else None,
                losses=problems, accepted_loss=accepted_loss if problems else None, dressing=dressing)


def terminal(result):
    lines = ['Entity tracker (%d maps): placed / original' % result['maps']]
    for cat in CATEGORIES:
        e, i = result['totals'][cat]['exterior'], result['totals'][cat]['interior']
        lines.append('  %-17s exterior %7d / %-7d interior %7d / %d' % (cat, e['placed'], e['original'], i['placed'], i['original']))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('report')
    r.add_argument('--master', type=Path, required=True)
    r.add_argument('--maps', type=Path, action='append', required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--previous', type=Path)
    r.add_argument('--private', action='store_true', help='also list the placed reference numbers')
    c = sub.add_parser('compare'); c.add_argument('old', type=Path); c.add_argument('new', type=Path)
    b = sub.add_parser('baseline'); b.add_argument('report', type=Path)
    b.add_argument('--release', required=True); b.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    if args.cmd == 'baseline':
        result = baseline(json.loads(args.report.read_text(encoding='utf-8')), args.release)
        args.out.write_text(dump_baseline(result), encoding='utf-8', newline='\n')
        return 0
    if args.cmd == 'compare':
        problems = compare(json.loads(args.old.read_text(encoding='utf-8')), json.loads(args.new.read_text(encoding='utf-8')))
    else:
        master = args.master.read_bytes()
        rows, unresolved = census(master)
        placed, full, maps = placed_from_dirs(args.maps)
        result = report(rows, placed, maps, hashlib.sha256(master).hexdigest(), unresolved, full, private=args.private)
        args.out.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(terminal(result), end='')
        problems = compare(json.loads(args.previous.read_text(encoding='utf-8')), result) if args.previous else []
    for line in problems:
        print('ENTITY LOSS: ' + line, file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
