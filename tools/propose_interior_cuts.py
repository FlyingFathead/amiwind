#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Propose section cuts for an interior over its model limit (docs/INTERIOR_SECTIONS.md step 3).

Reads one converted room (the room converter's folder: conversion.json and source/scenery-index.json) and
proposes cuts where the player walks through a narrow passage anyway: a vertical plane through a doorway
or hallway piece (model names with doorway, hall, door jamb or door markers), on the x and on the y axis.
Each cut is scored by the model slots of each side, counted by the converter's own rule (a lit placement is
its own model, an unlit one shares its model with its equal placements, a plant sprite file is one slot)
and by how many placements straddle the plane (they would have to belong to one side).

The proposal is for review only: the maintainer checks each cut in the 3D Map Inspector's sub-cell divider
(docs/POLYCOUNT_INSPECTOR.md) before tools/prepare_interior_sections.py builds sections from it. Nothing
here changes a build. Floor narrowings are not searched yet (the inspector's divider tries any plane).

    python3 tools/propose_interior_cuts.py ROOM_FOLDER [ROOM_FOLDER ...] --out proposal.json [--limit 220]
"""
import argparse
import json
from pathlib import Path
import re

PASSAGE = re.compile(r'doorway|_hall|_dj_|ndoor|_door_|entrance', re.I)
LIMIT = 220


def room_placements(folder):
    """(placements, receipt) of one converted room: [{number, model, low, high, centre, slot}], slot = the
    model slot key the converter gives the placement."""
    folder = Path(folder)
    report = json.loads((folder / 'conversion.json').read_text())
    index = json.loads((folder / 'source/scenery-index.json').read_text())
    unlit = set((report.get('shared_ambient') or {}).get('unlit_references', ()))
    sprites = {row['reference']: row['sprite'] for row in (report.get('plant_sprites') or {}).get('sprites', ())}
    out = []
    for ref in index['references']:
        model = index['models'][ref['model_index']]['source']
        low = [v * .25 for v in ref['bounds'][0]]; high = [v * .25 for v in ref['bounds'][1]]
        number = ref['number']
        if number in sprites:
            slot = ('sprite', sprites[number])
        elif number in unlit:
            slot = ('shared', model, round(ref.get('scale', 1.), 6))
        else:
            slot = ('own', number)
        out.append({'number': number, 'model': model, 'low': low, 'high': high,
                    'centre': [(a + b) / 2 for a, b in zip(low, high)], 'slot': slot})
    return out, report


def side_slots(placements):
    return len({p['slot'] for p in placements})


def score_cut(placements, axis, split):
    front = [p for p in placements if p['centre'][axis] < split]
    back = [p for p in placements if p['centre'][axis] >= split]
    straddle = [p['number'] for p in placements if p['low'][axis] < split < p['high'][axis]]
    return {'axis': 'xyz'[axis], 'split': round(split, 2), 'slots': [side_slots(front), side_slots(back)],
            'placements': [len(front), len(back)], 'straddling': len(straddle),
            'straddling_references': straddle[:40]}


def propose(folder, limit=LIMIT, keep=3):
    placements, report = room_placements(folder)
    total = side_slots(placements)
    pieces = [p for p in placements if PASSAGE.search(p['model'].rsplit('/', 1)[-1])]
    cuts = []
    for piece in pieces:
        for axis in (0, 1):
            cut = score_cut(placements, axis, piece['centre'][axis])
            if min(cut['placements']) == 0:
                continue
            cut['through'] = {'reference': piece['number'], 'model': piece['model']}
            cut['fits'] = max(cut['slots']) <= limit
            cuts.append(cut)
    # fitting cuts first, then the fewest placements crossed by the plane, then the most even split
    cuts.sort(key=lambda c: (not c['fits'], c['straddling'], max(c['slots'])))
    seen, best = set(), []
    for cut in cuts:
        key = (cut['axis'], cut['split'])
        if key in seen:
            continue
        seen.add(key); best.append(cut)
        if len(best) == keep:
            break
    return {'map': report.get('map', Path(folder).name), 'cell': report.get('cell'), 'model_slots': total,
            'limit': limit, 'passage_pieces': len(pieces), 'cuts': best,
            'review': 'PENDING: maintainer review in the inspector divider before any section build'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rooms', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--limit', type=int, default=LIMIT)
    a = p.parse_args(argv)
    rows = []
    for folder in a.rooms:
        row = propose(folder, a.limit)
        rows.append(row)
        best = row['cuts'][0] if row['cuts'] else None
        print('%s (%s): %d slots; best cut %s' % (row['map'], row['cell'], row['model_slots'],
              'none' if best is None else '%s=%.0f through %s: sides %s, %d straddling%s' % (
                  best['axis'], best['split'], best['through']['model'].rsplit('/', 1)[-1], best['slots'],
                  best['straddling'], '' if best['fits'] else ' (still over)')), flush=True)
    a.out.write_text(json.dumps({'format': 'AmiWind interior cut proposal 1', 'rooms': rows}, indent=1) + '\n',
                     encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
