#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The world map manifest (docs/BUILD_MANIFEST.md): which exterior maps of a build are on CHIM and which legacy
maps of CHIM-covered cells the build still makes, decided from the CHIM coverage before the first stage.

Rows (one per CHIM area and per CHIM region cell):
  map            the map name the engine loads (a town's map name, or the cell's open-world map vfNNNN)
  kind           chim-area | chim-region-cell
  cells          the game cells it covers ([] for an area: its frame is the town's)
  legacy         the legacy maps of those cells the build still makes, by name ([] when none)
  kept_because   why those legacy maps are still made (None when there are none); they never ship: the image
                 step removes them and checks that 0 reach the payload. Every CHIM area is prepared CHIM-native
                 (Seyda Neen too since v0.0.36-dev5): a legacy chain of an area is only kept for a labelled A/B
                 regression test with a retired flag (--legacy-area, --seyda-recorded, --chim-native-towns off);
                 otherwise the collision check refuses it
Standard library only; read by tools/build.py (written into the run folder and the receipt) and the image step.

    python3 tools/world_manifest.py summary MANIFEST.json
"""
import hashlib
import json
import sys

FORMAT = 'AmiWind world map manifest 1'
KINDS = ('chim-area', 'chim-region-cell')
# Why a legacy map of a CHIM cell is still made today (docs/BUILD_MANIFEST.md, "What still reads a legacy map").
# The one reason a CHIM area's legacy town chain is still made: a labelled A/B test of a historical regression with
# a retired flag (tools/retired_flags.py; refused in developer mode without --override). The earlier reason "source
# of the town frame maps until the town is prepared CHIM-native" (Seyda Neen until v0.0.36-dev5) is gone: no CHIM
# area takes its frame from a legacy chain any more (owner order 2026-10-11, BUILD-LEGACY-TOWN-MAPS-SHIPPED-36).
KEPT_RETIRED_FLAG = 'A/B regression test with a retired flag (%s): the legacy town chain, labelled, never shipped'
KEPT_REGION_MAP = ('source of the region frame map (--chim-region-rows legacy, the earlier method: worldspawn, player '
                   'start, flora sprites, sounds copied from it; every static checked against the CHIM placements)')
# The stages that make open-world legacy maps: each takes the CHIM region cells (--chim-regions-cells) and makes no
# map for them (docs/BUILD_MANIFEST.md step 2).
OPEN_WORLD_STAGES = ('world-terrain', 'world-scenery', 'world-flora')
CELLS_OPTION = '--chim-regions-cells'


def cell_name(cell):
    return '%d,%d' % tuple(cell)


def plan(chim_areas, native_towns=(), region_table=None, statuses=None, region_rows='game-data', retired=()):
    """The manifest of a build: chim_areas (builder chim_areas), native_towns (those prepared CHIM-native:
    no legacy town chain), region_table (tools/chim/regions.py plan, or None), statuses (its tracker statuses
    {(x, y): {'legacy_maps': [...], ...}}, for the legacy map of each region cell), region_rows (the build's
    chim_region_rows: with 'game-data' no stage makes a legacy map of a region cell; 'legacy', the earlier method,
    still reads it, so it is made, kept because of that), retired (the build's retired flag record,
    tools/retired_flags.check: the only reason an area is not CHIM-native; without one the area's legacy chain has
    no recorded reason and the collision check refuses the plan)."""
    native = set(native_towns)
    flags = ', '.join(r['flag'] for r in retired or ())
    rows = []
    for area in chim_areas:
        chain = area not in native
        rows.append({'map': area, 'kind': 'chim-area', 'cells': [],
                     'legacy': ['%s town chain' % area] if chain else [],
                     'kept_because': (KEPT_RETIRED_FLAG % flags if flags else None) if chain else None})
    statuses = statuses or {}
    for frame in (region_table or {}).get('frames', []):
        cell = tuple(frame['cell'])
        names = list((statuses.get(cell) or {}).get('legacy_maps') or [])
        legacy = names if region_rows == 'legacy' else []
        rows.append({'map': names[0] if len(names) == 1 else frame['id'], 'kind': 'chim-region-cell',
                     'cells': [cell_name(cell)], 'legacy': legacy,
                     'kept_because': KEPT_REGION_MAP if legacy else None})
    manifest = {'format': FORMAT, 'rows': rows}
    manifest['summary'] = summary(manifest)
    return manifest


def summary(manifest):
    """Counts by kind and the legacy maps of CHIM cells the build still makes, by reason."""
    counts = {kind: 0 for kind in KINDS}
    kept = {}
    for row in manifest['rows']:
        counts[row['kind']] += 1
        if row['legacy']:
            kept.setdefault(row['kept_because'], []).extend(row['legacy'])
    return {'kinds': counts,
            'legacy_maps_of_chim_cells_made': sum(len(v) for v in kept.values()),
            'kept_because': {reason: len(names) for reason, names in sorted(kept.items())}}


def region_cells(manifest):
    """The CHIM region cells of a manifest whose legacy map no stage may make (sorted (x, y))."""
    return sorted(tuple(int(v) for v in row['cells'][0].split(',')) for row in manifest['rows']
                  if row['kind'] == 'chim-region-cell' and not row['legacy'])


def collisions(manifest, steps, cells_text=None):
    """The preflight collision check, before any stage (owner order: never a CHIM map and a legacy map of the same
    cell): a list of refusals, empty when every cell has exactly one owner.
    - every open-world stage in STEPS ([(name, command)]) takes the CHIM region cells, exactly the manifest's, so
      its work list holds no legacy map of a CHIM cell;
    - a CHIM cell is listed once, and a legacy map of a CHIM cell is made only with a recorded "kept because".
    cells_text: the cells as the stages get them (chim.regions.encode_cells)."""
    problems = []
    skip = region_cells(manifest)
    seen = {}
    for row in manifest['rows']:
        for cell in row['cells']:
            if cell in seen:
                problems.append('cell %s is claimed by %s and by %s' % (cell, seen[cell], row['map']))
            seen[cell] = row['map']
        if row['legacy'] and not row['kept_because']:
            problems.append('%s: legacy maps %s of a CHIM cell are made with no recorded reason'
                            % (row['map'], ', '.join(row['legacy'])))
    if skip:
        from chim.regions import decode_cells
        for name, command in steps:
            if name not in OPEN_WORLD_STAGES:
                continue
            parts = [str(part) for part in command]
            given = parts[parts.index(CELLS_OPTION) + 1] if CELLS_OPTION in parts else None
            listed = sorted(decode_cells(given)) if given else []
            missing = sorted(set(skip) - set(listed))
            extra = sorted(set(listed) - set(skip))
            if missing:
                problems.append('stage %s would build the legacy maps of CHIM cells %s'
                                % (name, ' '.join(cell_name(c) for c in missing)))
            if extra:
                problems.append('stage %s leaves out cells that are not CHIM region cells: %s'
                                % (name, ' '.join(cell_name(c) for c in extra)))
    return problems


def text(manifest):
    return json.dumps(manifest, indent=1, sort_keys=True) + '\n'


def sha256(manifest):
    return hashlib.sha256(text(manifest).encode('utf-8')).hexdigest()


def legacy_region_maps(manifest):
    """{legacy map name: cell} of the CHIM region cells: the maps that must not reach the payload."""
    return {name: row['cells'][0] for row in manifest['rows'] if row['kind'] == 'chim-region-cell'
            for name in row['legacy']}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != 'summary':
        print('Usage: world_manifest.py summary MANIFEST.json', file=sys.stderr)
        return 2
    with open(args[1], encoding='utf-8') as stream:
        manifest = json.load(stream)
    print(json.dumps(manifest['summary'], indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
