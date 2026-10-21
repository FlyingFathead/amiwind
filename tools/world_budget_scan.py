#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Record the region budget scan of a public default world build (BUILD-LAVA-TERRAIN-BUDGET-38).

A public default build (no --chim-regions selection) converts every open-world region as a BSP29 map, including the
dense lava and Molag Mar regions that the project's own builds put on CHIM. Those regions are only measured by a
from-scratch default build, so this tool keeps the result in config/world-region-budget-scan.json: the largest
regions of the world-scenery stage against the per-region limits, for the refinement table it was measured with.
tests/test_world_region_budget.py refuses a refinement table the scan was not measured with, and any recorded
region over a limit.

  python tools/world_budget_scan.py record --terrain RUN/world-terrain --scenery RUN/world-scenery \\
      --version 0.0.47-dev1 --commit abc1234 [--out config/world-region-budget-scan.json]

The scenery directory may be from a failed stage: every region it converted has its scene.bsp, including the
regions over budget (the stage names them all, then stops).
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
REFINEMENTS = ROOT / 'config/world-region-refinements.json'
RECORD = ROOT / 'config/world-region-budget-scan.json'
# The world-scenery stage's per-region limits (prepare_world_scenery.convert_region).
LIMITS = {'bytes': 4 * 1024 * 1024, 'faces': 30000, 'clipnodes': 32767}
KEEP = 25


def bsp_metrics(path):
    """Bytes, faces and clipnodes of a BSP29 map (header lump table)."""
    raw = Path(path).read_bytes()
    if struct.unpack_from('<i', raw, 0)[0] != 29:
        raise ValueError('Not a BSP29 map: %s' % path)
    lump = lambda i: struct.unpack_from('<ii', raw, 4 + 8 * i)[1]
    return {'bytes': len(raw), 'faces': lump(7) // 20, 'clipnodes': lump(9) // 8}


def refinements_sha256(path=REFINEMENTS):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scan(terrain, scenery):
    """Every region the terrain stage made a map for, measured in the scenery output."""
    receipt = json.loads((Path(terrain) / 'world-regions.json').read_text(encoding='utf-8'))
    made = [r for r in receipt['regions'] if not (r.get('chim_region') or r.get('routing_only'))]
    rows, missing = [], []
    for r in made:
        path = Path(scenery) / r['name'] / 'scene.bsp'
        if not path.is_file():
            missing.append(r['name'])
            continue
        rows.append({'name': r['name'], 'cell': r['cell'], 'divisions': r.get('divisions', 1), 'subcell': r.get('subcell'),
                     'terrain_bytes': (r.get('converted') or {}).get('bytes'), **bsp_metrics(path)})
    if missing:
        raise ValueError('%d region(s) without a scenery map (the stage did not finish them): %s'
                         % (len(missing), ' '.join(missing[:20])))
    rows.sort(key=lambda row: (-row['bytes'], row['name']))
    return receipt, rows


def record(terrain, scenery, version, commit, out=RECORD):
    receipt, rows = scan(terrain, scenery)
    over = [row for row in rows if any(row[k] > v for k, v in LIMITS.items())]
    doc = {'format': 'AmiWind world region budget scan 1',
           'about': 'Largest open-world regions of a public default build (every region a BSP29 map, no CHIM region '
                    'selection), measured after the world-scenery stage. Re-measure after any change to '
                    'config/world-region-refinements.json (tools/world_budget_scan.py, BUILD-LAVA-TERRAIN-BUDGET-38).',
           'refinements_sha256': refinements_sha256(),
           'survey_sha256': receipt.get('survey_sha256'),
           'measured_with': {'version': version, 'commit': commit},
           'limits': LIMITS,
           'regions_measured': len(rows),
           'regions_over': [row['name'] for row in over],
           'largest': rows[:KEEP]}
    Path(out).write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('World budget scan: %d regions, %d over a limit; largest %s %s bytes (limit %s)'
          % (len(rows), len(over), rows[0]['name'], format(rows[0]['bytes'], ','), format(LIMITS['bytes'], ',')))
    for row in over:
        print('  OVER: %s cell %s divisions %s subcell %s: bytes %s faces %s clipnodes %s'
              % (row['name'], row['cell'], row['divisions'], row['subcell'], format(row['bytes'], ','),
                 format(row['faces'], ','), format(row['clipnodes'], ',')))
    return doc


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('record', help='measure a default build\'s world-scenery output and write the scan record')
    r.add_argument('--terrain', type=Path, required=True)
    r.add_argument('--scenery', type=Path, required=True)
    r.add_argument('--version', required=True)
    r.add_argument('--commit', required=True)
    r.add_argument('--out', type=Path, default=RECORD)
    a = p.parse_args()
    doc = record(a.terrain, a.scenery, a.version, a.commit, a.out)
    raise SystemExit(1 if doc['regions_over'] else 0)


if __name__ == '__main__':
    main()
