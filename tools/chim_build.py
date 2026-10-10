#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM builder: write an area's exterior as CHIM world files.

    python3 tools/chim_build.py --area balmora --data-files DIR --palette PALETTE.lmp
        --out DIR [--qbsp QBSP] [--jobs N] [--unit-cache DIR] [--validate] [--stats]
        [--texture-effect EFFECT ...]

Reads your own Morrowind files and writes OUT/chim/ (index, frame file, sector
files), OUT/chim-source.json and OUT/chim-receipt.json; --validate adds
OUT/chim-validate.json and the stair walkability gate OUT/chim-stairs.json,
--stats OUT/chim-stats.json (docs/chim/STATS.md).
PALETTE is the game palette of the same build (id1/gfx/palette.lmp of the
boot scene). --qbsp compiles exact collision unions as the legacy converter
does. tools/build.py runs this as its `chim` stage with --builder chim.
See docs/chim/WORLD_FORMAT.md.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# src/ before tools/: the src/mwad package, not tools/mwad.py (the script's own folder comes first otherwise)
for p in (ROOT / 'tools', ROOT / 'src'):
    while str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))


def main(argv=None):
    from build_jobs import add_jobs
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--area', '--town', dest='areas', action='append', default=None, metavar='TOWN',
                    help='Town id from config/towns.json (repeatable; default balmora)')
    ap.add_argument('--data-files', type=Path, required=True)
    ap.add_argument('--palette', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--qbsp', type=Path, help='qbsp for exact collision unions (as the legacy converter)')
    ap.add_argument('--grain', type=int, default=256, help='Chunk size in map units (divides the frame)')
    ap.add_argument('--detail-budget', default=None, metavar='NAME',
                    help='Apply a named per-mesh visual triangle budget (config/chim-detail-budgets.json; default none)')
    ap.add_argument('--cut-models-over', type=float, default=None, metavar='UNITS',
                    help='Cut placements of models wider than UNITS by chunk (chim.cut; default 0: none)')
    ap.add_argument('--draw-distance', type=float, default=None, metavar='UNITS',
                    help='World setting draw_distance (default 540): the ring the world is built, culled and '
                         'heap-gated for; a closer view is a DEBUG ONLY MiniWind setting (tools/build.py)')
    ap.add_argument('--harvest', type=Path,
                    help="The harvest step's output: its placements are left out, as the image removes them")
    ap.add_argument('--flora', type=Path,
                    help='The world flora assets: the town flora the image installs is added, as meshes')
    ap.add_argument('--legacy-run', type=Path,
                    help="The legacy builder's run folder: Seyda Neen's frame reads its terrain audit, scenery "
                         'and scene stage (work/, scenery/, alias-scene/)')
    ap.add_argument('--sdk', type=Path,
                    help='Amiga SDK: with --validate, the CHIM heap gate probes the engine target ABI sizes with its '
                         'compiler (as the strict world-map heap gate does)')
    ap.add_argument('--accept-known-stair-findings', action='append', default=[], metavar='ID',
                    help='PRIVATE -devN TESTS ONLY: accept the stair gate failures of this known finding '
                         '(tracker ID in config/known-stair-findings.json); recorded, refused for rc and final')
    ap.add_argument('--unit-cache', type=Path,
                    help='Unit cache folder kept between builds (default OUT/work/chim-units)')
    ap.add_argument('--validate', action='store_true', help='Run tools/chim/validate.py on the result')
    ap.add_argument('--stats', action='store_true', help='Write OUT/chim-stats.json (tools/chim/stats.py)')
    ap.add_argument('--no-cache', action='store_true',
                    help='Build every unit again instead of reusing units with unchanged fingerprints')
    ap.add_argument('--no-mesh-occluders', action='store_true',
                    help='Visibility rows without occluders from closed building meshes (for comparison)')
    ap.add_argument('--rebuild-mesh', action='append', default=[], metavar='SOURCE',
                    help='Build the units of this mesh again (e.g. meshes/x/ex_hlaalu_b_01.nif)')
    ap.add_argument('--texture-effect', action='append', default=[], metavar='EFFECT',
                    help='Apply a CHIM texture effect (a .chimfx file, or the name of one in tools/chim/effects, '
                         'e.g. autumn_glitter_leaves) to the textures it targets; repeatable, in order; none by '
                         'default (docs/chim/TEXTURE_EFFECTS.md)')
    ap.add_argument('--cell-progress', type=Path, metavar='DIR',
                    help='Print the command that writes the CHIM Progress Tracker data of this world into DIR '
                         '(tools/cell_progress_build.py; the builder runs it as its own stage, cell-progress, '
                         'unless --no-cell-progress)')
    from chim.light_types import TYPES, help_text
    ap.add_argument('--lighting-type', choices=list(TYPES), default=None, help=help_text())
    ap.add_argument('--no-far-terrain', action='store_true',
                    help='DEBUGGING ONLY: write no far terrain layer (the frame maps then draw no distant land '
                         'beyond the chunk ring; docs/chim/WORLD_FORMAT.md "Far terrain")')
    add_jobs(ap)
    a = ap.parse_args(argv)
    areas = list(dict.fromkeys(a.areas or ['balmora']))
    if a.accept_known_stair_findings:
        from project_version import public_version, require_private_test_version
        from chim.known import known_stair_findings
        try:
            require_private_test_version(public_version(), ['--accept-known-stair-findings'])
            known_stair_findings(a.accept_known_stair_findings)
        except ValueError as exc:
            ap.exit(1, 'Error: %s\n' % exc)
    from chim.light_types import DEFAULT as LIGHTING_DEFAULT, check as check_lighting
    try:
        lighting_type = check_lighting(a.lighting_type or LIGHTING_DEFAULT)
    except ValueError as exc:
        ap.exit(1, 'Error: %s\n' % exc)
    from chim.areas import area_problems
    problems = area_problems(areas)
    if problems:
        ap.exit(1, 'Error: %s\n' % '; '.join(problems))
    from chim.build import build_areas
    from chim.texfx import effect_path
    def build_world():
        try:
            build_areas(areas, a.data_files, a.out, a.palette, a.qbsp, a.jobs, dict({'grain': a.grain}, **({'cut_models_over': a.cut_models_over} if a.cut_models_over is not None else {}),
                     **({'detail_budget': a.detail_budget} if a.detail_budget else {}),
                     **({'draw_distance': a.draw_distance} if a.draw_distance is not None else {})), not a.no_cache,
                        set(a.rebuild_mesh), not a.no_mesh_occluders, a.unit_cache, a.harvest, a.flora,
                        a.legacy_run, [effect_path(e) for e in a.texture_effect], not a.no_far_terrain,
                        # the routed-hull heap fallback runs inside the shared builder (chim.build.build_areas)
                        hull_fallback_sdk=a.sdk if a.validate else None)
        except (OSError, ValueError) as exc:
            ap.exit(1, 'Error: %s\n' % exc)
    build_world()
    # The lighting type and what of it is implemented (docs/chim/LIGHTING_ROADMAP.md) go into the receipt.
    import json
    from chim.light_types import record as lighting_record
    receipt_path = a.out / 'chim-receipt.json'
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_bytes().decode('utf-8'))
        receipt['lighting'] = lighting_record(lighting_type)
        receipt_path.write_bytes((json.dumps(receipt, indent=1, sort_keys=True) + '\n').encode('utf-8'))
    if a.validate:
        from chim.validate import main as validate
        if validate([str(a.out), '--json', str(a.out / 'chim-validate.json'), '--palette', str(a.palette)]) != 0:
            ap.exit(1, 'Error: the CHIM world fails validation (%s)\n' % (a.out / 'chim-validate.json'))
        import json
        fallback = json.loads((a.out / 'chim-receipt.json').read_text(encoding='utf-8')).get('hull_fallback')
        if fallback:
            print('CHIM hull fallback: chains kept for %s (a ring did not fit with their routed hulls)'
                  % ', '.join(fallback['kept_as_chain']), flush=True)
        # Every flight of stairs walked on the frame's own collision (COLLISION-STAIR-SLOPE-32).
        from chim.collision import require_stairs
        try:
            report = require_stairs(a.out, a.jobs, accepted=a.accept_known_stair_findings)
        except ValueError as exc:
            ap.exit(1, 'Error: %s\n' % exc)
        print('CHIM stair gate: %s (%s steps and ramps tested, %d advisory, %d accepted known)'
              % (report['status'], report.get('tested', 0), len(report.get('advisory_failures', [])),
                 len(report.get('accepted_known_findings', []))), flush=True)
        if a.accept_known_stair_findings:
            # the receipt records the waiver (private test only)
            import json
            path = a.out / 'chim-receipt.json'
            receipt = json.loads(path.read_text(encoding='utf-8'))
            receipt['accepted_known_stair_findings'] = {
                'ids': sorted(a.accept_known_stair_findings),
                'failures': len(report.get('accepted_known_findings', [])),
                'policy': 'private -devN test only (require_private_test_version)'}
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        # Every ring fits the engine's CHIM zone: strict, no exceptions (chim.heap).
        from chim.heap import require_heap
        try:
            # frames in parallel; each frame's result kept by its content key beside the unit cache
            # (CHIM-WORLD-AUDIT-SCALING-33)
            heap = require_heap(a.out, a.sdk, jobs=a.jobs or 1,
                                cache_dir=(a.unit_cache / 'heap') if a.unit_cache and not a.no_cache else None)
        except ValueError as exc:
            ap.exit(1, 'Error: %s\n' % exc)
        print('CHIM heap gate: %s %s' % (heap['status'], ', '.join(
            '%s active ring peak %d, load ring peak %d (%d positions over), largest block %d, of %d bytes (gated: %s)'
            % (f['frame'], f['peak_bytes'], f['load_ring']['peak_bytes'], f['load_ring']['positions_over_budget'],
               f['largest_block_bytes'], f['budget_bytes'], f['gated_ring'])
            for f in heap.get('frames', []))), flush=True)
        # The engine's own zone allocator over a walk through every frame: never a step without ground
        # (CHIM-CHUNK-LOAD-FAIL-33, chim.zone_sim).
        from chim.zone_sim import require_zone_walk
        try:
            walk = require_zone_walk(a.out, a.sdk)
        except ValueError as exc:
            ap.exit(1, 'Error: %s\n' % exc)
        print('CHIM zone walk gate: %s %s' % (walk['status'], ', '.join(
            '%s: %d steps, %d loads without room, %d partial activations, %d+%d chunks released, %d model loads'
            % (w['name'], w['steps'], w['zone_fail'], w['partial'], w['released_band'], w['released_ring'],
               w['model_loads']) for w in walk.get('walks', []))), flush=True)
    if a.stats:
        from chim.stats import main as stats
        if stats([str(a.out)]) != 0:
            return 1
    if a.cell_progress:
        # The tracker is no longer run from here: the builder runs tools/cell_progress_build.py as its own stage
        # (cell-progress), so its code never keys this stage (BUILD-CHIM-KEY-UNDERDECLARED-35). Same data, same tool:
        print('CHIM cell progress: run `python3 tools/cell_progress_build.py --out %s --chim-world %s` '
              '(the builder does it in its cell-progress stage)' % (a.cell_progress, a.out), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
