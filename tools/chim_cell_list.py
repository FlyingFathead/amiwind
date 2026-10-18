#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Make a CHIM region cell list (aw-chim-cells-1) from the tracker's rings, never by hand.

A build's cell list (tools/build.py --chim-regions @FILE) is the union of:

  --rings A-B      every cell of those rings in the CHIM Progress Tracker data (cell-progress.json,
                   ring 1 = land touching the sea, then inwards; --island 1 = Vvardenfell)
  --region NAME    every cell of that Morrowind region in the tracker data (repeatable; the regional
                   CHIMport: a region in one step, so its towns are not cut at the CHIM edge)
  --include FILE   extra cells, e.g. ring-0 sea cells or a batch by weight (tools/chim_weight_table.py
                   --cells-out); any cell file tools/chim/regions.py reads
  --keep FILE      cells that are already on CHIM (the previous release's list, or a build run's
                   world-scenery/world-scenery.json, whose chim_region_cells it reads); repeatable
  --master FILE    the base master (Morrowind.esm): report every exterior cell that stays on the classic
                   open world with this list, as the build's exterior checklist sees it (a CELL record or a
                   LAND record with heights, not listed, not inside a town frame given by --covered), with
                   its tracker status. Open-sea cells with a CELL record are named apart: the build keeps a
                   classic map for each until the list selects them (CHIM-OCEAN-CELL-RECORD-CLASSIC-43)

A kept cell is never dropped silently: --drop X,Y=REASON names each one that leaves CHIM, and any other
kept cell missing from the result refuses the list. Origin: a hand-made rings 0-2 list dropped 35 cells
that were already on CHIM (lava cells moved to CHIM because their legacy maps exceed 4 MiB), and two
full builds failed on those maps (BUILD-LAVA-TERRAIN-BUDGET-38).

    python3 tools/chim_cell_list.py --progress cell-progress.json --rings 1-2 --include ring0.json \\
        --keep previous.json --reason "Rings 0, 1 and 2" --out cells.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chim.regions import CELLS_FORMAT, read_cell_file  # noqa: E402


def key(cell):
    return '%d,%d' % tuple(cell)


def ring_cells(progress, low, high, island):
    """Cells of rings low..high (inclusive) on that island, from the tracker's cell-progress.json."""
    cells = json.loads(Path(progress).read_text(encoding='utf-8'))['cells']
    return {k for k, v in cells.items()
            if v.get('ring') is not None and low <= v['ring'] <= high and v.get('island') == island}


def region_name(cell):
    region = cell.get('region')
    return region.get('name') if isinstance(region, dict) else region


def region_cells(progress, names, island):
    """Cells of the named regions on that island, from the tracker's cell-progress.json; an unknown name refuses."""
    cells = json.loads(Path(progress).read_text(encoding='utf-8'))['cells']
    known = {region_name(v) for v in cells.values() if v.get('island') == island}
    unknown = sorted(set(names) - known)
    if unknown:
        raise ValueError('unknown region(s) on island %d: %s (known: %s)' % (
            island, ', '.join(unknown), ', '.join(sorted(n for n in known if n))))
    return {k for k, v in cells.items() if v.get('island') == island and region_name(v) in names}


def file_cells(path):
    """Cells of a cell file, or of a build run's world-scenery.json (chim_region_cells)."""
    path = Path(path)
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'chim_region_cells' in data:
            return {key(c) for c in data['chim_region_cells']}
    cells, regions, _ = read_cell_file(path)
    if regions:
        raise ValueError('%s: region names are not expanded here; list the cells' % path.name)
    return {key(c) for c in cells}


def open_legacy_pockets(chosen, kept, progress, island, limit=64, covered=()):
    """Leave out, by name, the cells that open every legacy pocket (classic cells enclosed by CHIM cells, the
    builder's rule chim.regions.holes: every crossing there would load two maps). For each pocket the neighbour
    in the list with the highest ring that is not already on CHIM goes; repeated until no pocket is left.
    covered: cells on CHIM inside a town frame (no legacy map left); they count as CHIM in the pocket test, the
    builder's rule too (CHIM-REGION-POCKET-TOWN-CELLS-42), and are never written to the list.
    Returns report lines; changes chosen in place."""
    from chim.regions import holes
    rings = {k: v.get('ring') or 0 for k, v in json.loads(Path(progress).read_text(encoding='utf-8'))['cells'].items()
             if v.get('island') == island}
    lines = []
    for _ in range(limit):
        pockets = holes([tuple(int(v) for v in k.split(',')) for k in set(chosen) | set(covered)])
        if not pockets:
            return lines
        for pocket in pockets:
            near = {key((x + dx, y + dy)) for x, y in pocket for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
            candidates = sorted((k for k in near & chosen if k not in kept), key=lambda k: (-rings.get(k, 0), k))
            if not candidates:
                raise ValueError('legacy pocket %s is enclosed by cells already on CHIM'
                                 % ' '.join(key(c) for c in pocket))
            chosen.discard(candidates[0])
            lines.append('left out %s: opens the legacy pocket %s' % (candidates[0], ' '.join(key(c) for c in pocket)))
    raise ValueError('legacy pockets still open after %d rounds' % limit)


def classic_cells(source, chosen, covered, progress, island=1):
    """Report lines for the exterior cells that stay classic with this list. source: the master's exterior
    cells (exterior_plan.source_cells); chosen / covered: cell keys on CHIM (listed / inside a town frame)."""
    cells = json.loads(Path(progress).read_text(encoding='utf-8'))['cells']
    left = sorted((c for c in map(key, source) if c not in chosen and c not in covered
                   and cells.get(c, {}).get('island', island) == island),
                  key=lambda k: tuple(int(v) for v in k.split(',')))
    by_status = {}
    for c in left:
        by_status.setdefault(cells.get(c, {}).get('status', 'unknown'), []).append(c)
    lines = ['classic: %d exterior cell(s) of island %d stay on the classic open world with this list%s'
             % (len(left), island, ''.join('; %s %d' % (k, len(v)) for k, v in sorted(by_status.items())))]
    for status, group in sorted(by_status.items()):
        note = (' (open sea with a CELL record and no LAND: the build keeps a classic map for each; select them, '
                'they are admitted as ocean cells)' if status == 'ocean' else '')
        lines.append('classic %s: %s%s' % (status, ' '.join(group), note))
    return lines


def make(progress, rings, island=1, include=(), keep=(), drop=None, reason='', leave_out=None, open_pockets=False,
         regions=(), covered=(), master=None):
    """(document, report lines). Refuses (ValueError) when a kept cell is missing without a --drop reason."""
    if not rings and not regions and not include:
        # an --include alone is a batch list made from data (tools/chim_weight_table.py --cells-out)
        raise ValueError('give --rings, --region or --include')
    drop = dict(drop or {})
    leave_out = dict(leave_out or {})
    chosen, lines = set(), []
    if rings:
        low, _, high = rings.partition('-')
        low, high = int(low), int(high or low)
        chosen = ring_cells(progress, low, high, island)
        lines.append('rings %d-%d (island %d): %d cells' % (low, high, island, len(chosen)))
    for name in regions:
        extra = region_cells(progress, [name], island)
        lines.append('region %s: %d cells, %d new' % (name, len(extra), len(extra - chosen)))
        chosen |= extra
    for path in include:
        extra = file_cells(path)
        lines.append('include %s: %d cells, %d new' % (Path(path).name, len(extra), len(extra - chosen)))
        chosen |= extra
    kept = set()
    for path in keep:
        previous = file_cells(path)
        kept |= previous
        lines.append('keep %s: %d cells already on CHIM, %d outside the rings' % (Path(path).name, len(previous),
                                                                                  len(previous - chosen)))
        chosen |= previous
    unknown = sorted(set(drop) - kept)
    if unknown:
        raise ValueError('--drop names cells that are not kept cells: ' + ', '.join(unknown))
    for cell, why in sorted(drop.items()):
        if not why.strip():
            raise ValueError('--drop %s needs a reason (X,Y=REASON)' % cell)
        chosen.discard(cell)
        lines.append('DROPPED %s from CHIM: %s' % (cell, why))
    kept_out = sorted(set(leave_out) & kept)
    if kept_out:
        raise ValueError('--leave-out names cells already on CHIM (use --drop): ' + ', '.join(kept_out))
    for cell, why in sorted(leave_out.items()):
        if not why.strip():
            raise ValueError('--leave-out %s needs a reason (X,Y=REASON)' % cell)
        if cell in chosen:
            chosen.discard(cell)
            lines.append('left out %s: %s' % (cell, why))
    town = set()
    for path in covered:
        town |= file_cells(path)
        lines.append('covered %s: %d cells on CHIM inside a town frame (pocket test only)' % (Path(path).name, len(town)))
    if open_pockets:
        lines += open_legacy_pockets(chosen, kept, progress, island, covered=town - chosen)
    missing = sorted(kept - chosen - set(drop))
    if missing:   # cannot happen through the union above; kept as the guard the list exists for
        raise ValueError('kept CHIM cells missing from the list: ' + ', '.join(missing))
    ordered = sorted(chosen, key=lambda k: tuple(int(v) for v in k.split(',')))
    notes = '; '.join(lines)
    doc = {'format': CELLS_FORMAT, 'cells': [[int(v) for v in k.split(',')] for k in ordered],
           'reason': reason, 'notes': 'Made by tools/chim_cell_list.py: ' + notes}
    lines.append('total %d cells' % len(ordered))
    if master:
        src = str(Path(__file__).resolve().parents[1] / 'src')   # the mwad package, not the tools/mwad.py command
        if src not in sys.path[:1]:
            sys.path.insert(0, src)
            sys.modules.pop('mwad', None)
        from exterior_plan import source_cells
        lines += classic_cells(source_cells(master)[0], chosen, town, progress, island)
    return doc, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--progress', required=True, help="the tracker's cell-progress.json")
    ap.add_argument('--rings', help='A-B or A (inclusive)')
    ap.add_argument('--region', action='append', default=[], metavar='NAME',
                    help="every cell of a Morrowind region (the tracker's region name, e.g. \"Bitter Coast Region\"); repeatable")
    ap.add_argument('--island', type=int, default=1, help='1 = Vvardenfell (default), 2 = Solstheim')
    ap.add_argument('--include', action='append', default=[], metavar='FILE')
    ap.add_argument('--keep', action='append', default=[], metavar='FILE')
    ap.add_argument('--drop', action='append', default=[], metavar='X,Y=REASON')
    ap.add_argument('--leave-out', action='append', default=[], metavar='X,Y=REASON',
                    help='a ring cell not yet on CHIM left out of this list (failing audits, a legacy pocket), named')
    ap.add_argument('--open-pockets', action='store_true',
                    help='leave out, by name, the outermost neighbour of every legacy pocket the list would enclose')
    ap.add_argument('--covered', action='append', default=[], metavar='FILE',
                    help='cells on CHIM inside a town frame (no legacy map left): CHIM for the pocket test, not listed')
    ap.add_argument('--master', metavar='FILE',
                    help='the base master (Morrowind.esm): report the exterior cells that stay classic with this list')
    ap.add_argument('--reason', default='')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    try:
        drop = dict(d.partition('=')[::2] for d in a.drop)
        leave = dict(d.partition('=')[::2] for d in a.leave_out)
        doc, lines = make(a.progress, a.rings, a.island, a.include, a.keep, drop, a.reason, leave, a.open_pockets,
                          a.region, a.covered, a.master)
    except ValueError as error:
        print('REFUSED: %s' % error, file=sys.stderr)
        return 2
    Path(a.out).write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('\n'.join(lines))
    print('wrote', a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
