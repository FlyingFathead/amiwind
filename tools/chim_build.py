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
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# src/ before tools/: the src/mwad package, not tools/mwad.py (the script's own folder comes first otherwise)
for p in (ROOT / 'tools', ROOT / 'src'):
    while str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))


def main(argv=None):
    """The command line, with the stair walk off by default (BUILD-STAIR-WALK-OFF-46; an explicit
    AMIWIND_STAIR_WALK wins); the default is restored when it returns."""
    path = list(sys.path)
    import stair_walk
    sys.path[:] = path   # stair_walk puts tools/ first again; src/mwad must stay ahead of tools/mwad.py
    before = stair_walk.DEFAULT_OFF
    stair_walk.DEFAULT_OFF = True
    try:
        return _cli(argv)
    finally:
        stair_walk.DEFAULT_OFF = before


def _cli(argv=None):
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
    ap.add_argument('--terrain-shoreline', choices=('on', 'off'), default='on',
                    help='Town frames: triangulate the shoreline tiles with the sampler of the legacy region maps '
                         '(on, default; CHIM-STITCH-SHORELINE-36) or keep the plain tile grid (off)')
    ap.add_argument('--terrain-resident-detail', choices=('on', 'off'), default='on',
                    help='Town frames: terrain tiles under residents who stand on the ground keep the original '
                         'LAND samples (on, default; CHIM-VIVEC-FRAME-WIDE-41) or the plain tile grid (off: the '
                         'method before v0.0.41)')
    ap.add_argument('--terrain-hull', choices=('auto', 'routed', 'compiled'), default='auto',
                    help='Standing hull of chunk terrain: auto (default: compiled by qbsp for irregular ground, '
                         'routed chains for the regular grid), routed or compiled for every chunk')
    ap.add_argument('--terrain-refs', choices=('off', 'on'), default='off',
                    help='Terrain references (world format 0.7, EXPERIMENTAL): chunk terrain stored once per content '
                         'in chunk-local units and placed at an offset by every chunk with it; off (default) keeps '
                         'a copy in every chunk (format 0.5)')
    ap.add_argument('--model-hull-patch', choices=('off', 'on'), default='on',
                    help='Compiled model hulls whose compiler lost pieces under a walkable surface get those pieces '
                         'added exactly (on, default), or stay as compiled with the check recorded (off: the '
                         'previous method); CHIM-COMPILED-HULL-SHORT-36')
    ap.add_argument('--model-bevels', default='profile',
                    help='Edge bevels of the model standing hulls (EXPERIMENTAL; CHIM-COMPILED-HULL-OVERFILL-46): profile '
                         '(default: only meshes whose profile asks for them, the method before), exact (every model) or '
                         'tol:N (every model: the bevels whose omission reaches more than N units past the exact '
                         'expansion)')
    ap.add_argument('--placement-format', choices=('0.7', '0.8'), default='0.7',
                    help='World format of the placements (EXPERIMENTAL; CHIM-TILT-VARIANTS-SPLIT-33): 0.7 (default: '
                         'scale and tilt baked into one model per variant, the yaw in the record, the method before) '
                         'or 0.8 (one model per mesh + scale, the full rotation in a 56-byte record, collision from '
                         "the mesh's own pieces placed at run time)")
    ap.add_argument('--terrain-pack', choices=('bsp29', 'compact', 'generate'), default='bsp29',
                    help='How terrain records are stored (EXPERIMENTAL): bsp29 (default: the BSP29 brush image, the '
                         'method before) or compact (world format 0.10: a lossless repack the engine expands to the '
                         'same bytes; needs --terrain-refs on) or generate (world format 0.11: regular-path records '
                         'as heights the engine generates the same bytes from, the rest compact)')
    ap.add_argument('--reach-index', choices=('copies', 'refs'), default='copies',
                    help='Placements a chunk reaches but does not own (EXPERIMENTAL; CHIM-PLACEMENT-MARGIN-COPIES-46): '
                         'copies (default: a whole record in every chunk the drawn box touches, the method before) or '
                         'refs (world format 0.9: a 4-byte reference to the owner record in the same frame; needs '
                         '--placement-format 0.8)')
    ap.add_argument('--mesh-method', choices=('table', 'converter', 'merge', 'meshopt+merge'), default='table',
                    help='How meshes become faces (docs/chim/MESH_METHODS.md): table (default: config/mesh-methods.json, '
                         'planar merge for every mesh, meshoptimizer + planar merge for the meshes it names), or one '
                         'method for every mesh: converter (the method before v0.0.36-dev3), merge, meshopt+merge')
    ap.add_argument('--uv-scroll', choices=('off', 'turbulent'), default='off',
                    help='Shapes whose texture scrolls in the original (the Ghostfence curtain, waterfalls, the ash mire; '
                         'not lava): off (default) a still texture; turbulent a Quake turbulent texture that ripples '
                         'over time, unlit (GHOSTFENCE-NO-ANIMATION-46)')
    ap.add_argument('--model-weld', choices=('base', 'placed'), default='base',
                    help='How a model variant shares its vertices: base (default: as its base, the prepared mesh '
                         'unscaled, so every scale and tilt has the same vertices and edges; '
                         'CHIM-STRIDER-SCALED-SEAMS-36) or placed (by the placed position, the method before '
                         'v0.0.36-dev3)')
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
    ap.add_argument('--chim-regions-cells', metavar='CELLS',
                    help='CHIM regions (docs/chim/CHIM_REGIONS.md): exterior cells on CHIM inside the legacy open '
                         'world, one frame per cell, as tools/build.py resolves --chim-regions: "x,y:k ..." (k = s '
                         'seabed, l land, o explicitly admitted ocean); none by default')
    ap.add_argument('--chim-regions', action='append', default=[], metavar='SET',
                    help='CHIM regions by name for a run of this tool alone: seabed, coast, sea-ring, a region name '
                         'or @FILE (CSV x,y / aw-chim-cells-1 JSON / Toolkit World Map state); needs '
                         '--chim-regions-status')
    ap.add_argument('--chim-regions-status', type=Path, metavar='FILE',
                    help='The CHIM progress tracker file --chim-regions is checked against (cell-progress.json)')
    ap.add_argument('--pool', choices=('stage', 'batch'), default='stage',
                    help='Worker pool of the step: stage (default: ONE pool kept from the world conversion to the '
                         'last gate, every map of the step on the same workers, largest first; the validation\'s '
                         'whole-world cross-checks split into frame units on it) or batch (the method before '
                         'v0.0.42: a pool started and stopped for every map, cross-checks on one core); same '
                         'results (BUILD-CHIM-STAGE-SERIAL-TAIL-36)')
    ap.add_argument('--stair-walk-area', choices=('owned', 'frame'), default=None,
                    help='Where a region frame\'s stair walk walks: owned (default: its cell plus the map-switch '
                         'margin) or frame (the whole frame with its border copies, the method before v0.0.42); '
                         'sets AMIWIND_STAIR_WALK_AREA (chim.collision.walk_area_mode)')
    ap.add_argument('--stair-collision-method', choices=('0', '1'), default=None,
                    help='How a flight of stairs gets its collision: 0 (default) the convex proxies with the stair '
                         'rules, proven by the stair walk; 1 (EXPERIMENTAL) a stairway collision mesh (one ramp, or one '
                         'block per tread) for every flight whose collision fails the geometric stair check '
                         '(tools/stair_mesh.py); sets AMIWIND_STAIR_COLLISION_METHOD')
    ap.add_argument('--collision-underside', choices=('rule', 'split', 'whole', 'names'), default=None,
                    help='How a model keeps collision a convex piece closes under an authored ceiling: names '
                         '(default: a list of mesh names) or the EXPERIMENTAL general rules rule, split, whole '
                         '(mesh_geometry_env.underside_mode); sets AMIWIND_COLLISION_UNDERSIDE')
    ap.add_argument('--scale-snap', choices=('on', 'off'), default=None,
                    help='Placements of a mesh without collision scaled to the nearest 0.1 (on, the default) or as '
                         'placed (off); sets AMIWIND_SCALE_SNAP (chim.build.scale_snap_step)')
    ap.add_argument('--stair-walk-cache', choices=('records', 'cached', 'full'), default=None,
                    help='How the stair walk reuses its walks (default: AMIWIND_STAIR_WALK_CACHE, else cached): '
                         'records (also the known-good stair records shipped with the source; a frame in neither is '
                         'reported, not walked), cached (walk what changed) or full (walk every frame); sets '
                         'AMIWIND_STAIR_WALK_CACHE')
    ap.add_argument('--stair-walk', choices=('all', 'flights'), default=None,
                    help='What the stair walk covers (default: AMIWIND_STAIR_WALK, else flights): flights (the steps '
                         'that gate the build) or all (every step and ramp, the advisory findings too); sets '
                         'AMIWIND_STAIR_WALK')
    ap.add_argument('--stair-walk-key', choices=('reach', 'frame'), default=None,
                    help='How the walk of a frame is keyed (default: reach, frame with --stair-walk-cache records): reach '
                         '(per core: its steps and ramps and the collision within reach of their walks) or frame (every '
                         'chunk and placement of the frame, the key before v0.0.46); sets AMIWIND_STAIR_WALK_KEY')
    ap.add_argument('--stair-walk-places', metavar='FILE|ID,...', default=None,
                    help='A targeted stair walk of the named places only (watch-list file, or IDs of '
                         'config/stair-watch.json, cells x:y, frames/... paths, ref:N); rows reported, not stored; '
                         'sets AMIWIND_STAIR_WALK_PLACES')
    ap.add_argument('--stair-watch', metavar='FILE|off', default=None,
                    help='The stair watch list whose frames are walked again every build (default '
                         'config/stair-watch.json; off: none); sets AMIWIND_STAIR_WATCH')
    ap.add_argument('--gate-order', choices=('stairs-first', 'stairs-last'), default='stairs-first',
                    help='When the stair gate runs among the CHIM checks: stairs-first (default since v0.0.42: right '
                         'after the validation, before the statistics, heap gate and zone walk; with the stored '
                         'passes only the frames that changed are walked, so a stair failure stops the step in '
                         'minutes) or stairs-last (the order before v0.0.42: heap gate and zone walk first, the '
                         'stair gate last); same reports either way')
    add_jobs(ap)
    a = ap.parse_args(argv)
    from chim.bevels import model_bevels_mode
    try:
        model_bevels_mode({'model_bevels': a.model_bevels})     # refused before any stage (fail fast)
    except ValueError as error:
        ap.error(str(error))
    if a.placement_format == '0.8' and a.model_bevels.startswith('tol:'):
        ap.error('--placement-format 0.8 does not take --model-bevels tol:N (its collision is the placed pieces)')
    if a.terrain_pack != 'bsp29' and a.terrain_refs != 'on':
        ap.error('--terrain-pack %s needs --terrain-refs on' % a.terrain_pack)
    if a.reach_index == 'refs' and a.placement_format != '0.8':
        ap.error('--reach-index refs (world format 0.9) needs --placement-format 0.8')
    import build_parallel
    with build_parallel.stage_pool(a.jobs, 'CHIM', mode=a.pool):
        return _main(ap, a)


def _main(ap, a):
    # default Balmora, unless the world holds CHIM region frames only
    areas = list(dict.fromkeys(a.areas or ([] if a.chim_regions or a.chim_regions_cells else ['balmora'])))
    regions_table = None
    if a.chim_regions or a.chim_regions_cells:
        # CHIM region frames: the ownership table (chim.regions, its one writer), its frames registered as
        # generated areas and built into this world beside the towns
        from chim import regions as chim_regions
        from town_config import register_generated
        try:
            if a.chim_regions_cells and a.chim_regions:
                raise ValueError('give --chim-regions-cells or --chim-regions, not both')
            if a.chim_regions_cells:
                kinds = chim_regions.decode_cells(a.chim_regions_cells)
                problems = ['cells %s: a legacy pocket enclosed by CHIM region cells'
                            % ' '.join(map(chim_regions.cell_key, p)) for p in chim_regions.holes(kinds)]
                regions_table = chim_regions.ownership(kinds, {'cells': 'resolved by tools/build.py'})
            else:
                if not a.chim_regions_status:
                    raise ValueError('--chim-regions needs --chim-regions-status FILE')
                regions_table, problems = chim_regions.plan(a.chim_regions, a.chim_regions_status, towns=areas)
                kinds = chim_regions.table_kinds(regions_table)
            problems += chim_regions.ocean_land_problems(kinds, a.data_files)
            problems += chim_regions.owned_land_problems(kinds, a.data_files)
        except (OSError, ValueError) as exc:
            ap.exit(1, 'Error: CHIM regions: %s\n' % exc)
        if problems:
            ap.exit(1, 'Error: CHIM regions preflight:\n  %s\n' % '\n  '.join(problems))
        areas += register_generated([chim_regions.frame_settings(f, regions_table['terrain_margin'])
                                     for f in regions_table['frames']])
        print('CHIM regions: %d cells (%s) in %d frames'
              % (regions_table['counts']['cells'], chim_regions.kind_summary(regions_table['counts']),
                 regions_table['counts']['frames']), flush=True)
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
    if a.stair_walk_area:
        os.environ['AMIWIND_STAIR_WALK_AREA'] = a.stair_walk_area
    if a.collision_underside:
        os.environ['AMIWIND_COLLISION_UNDERSIDE'] = a.collision_underside
    if a.stair_collision_method:
        from stair_collision_env import export_stair_collision_method
        export_stair_collision_method(a.stair_collision_method)
    if a.scale_snap:
        os.environ['AMIWIND_SCALE_SNAP'] = '' if a.scale_snap == 'on' else 'off'
    if a.stair_walk_cache:
        os.environ['AMIWIND_STAIR_WALK_CACHE'] = a.stair_walk_cache
    for value, name in ((a.stair_walk, 'AMIWIND_STAIR_WALK'), (a.stair_walk_key, 'AMIWIND_STAIR_WALK_KEY'),
                        (a.stair_walk_places, 'AMIWIND_STAIR_WALK_PLACES'), (a.stair_watch, 'AMIWIND_STAIR_WATCH')):
        if value:
            os.environ[name] = value
    from chim.build import build_areas
    from chim.texfx import effect_path
    def build_world():
        try:
            build_areas(areas, a.data_files, a.out, a.palette, a.qbsp, a.jobs, dict({'grain': a.grain}, **({'cut_models_over': a.cut_models_over} if a.cut_models_over is not None else {}),
                     **({'detail_budget': a.detail_budget} if a.detail_budget else {}),
                     **({'draw_distance': a.draw_distance} if a.draw_distance is not None else {}),
                     **({'terrain_shoreline': a.terrain_shoreline} if a.terrain_shoreline != 'on' else {}),
                     **({'terrain_resident_detail': a.terrain_resident_detail} if a.terrain_resident_detail != 'on' else {}),
                     **({'terrain_hull': a.terrain_hull} if a.terrain_hull != 'auto' else {}),
                     **({'terrain_refs': a.terrain_refs} if a.terrain_refs != 'off' else {}),
                     **({'model_hull_patch': a.model_hull_patch} if a.model_hull_patch != 'on' else {}),
                     **({'model_bevels': a.model_bevels} if a.model_bevels != 'profile' else {}),
                     **({'placement_format': a.placement_format} if a.placement_format != '0.7' else {}),
                     **({'reach_index': a.reach_index} if a.reach_index != 'copies' else {}),
                     **({'terrain_pack': a.terrain_pack} if a.terrain_pack != 'bsp29' else {}),
                     **({'model_weld': a.model_weld} if a.model_weld != 'base' else {}),
                     **({'uv_scroll': a.uv_scroll} if a.uv_scroll != 'off' else {}),
                     **({'mesh_method': a.mesh_method} if a.mesh_method != 'table' else {})), not a.no_cache,
                        set(a.rebuild_mesh), not a.no_mesh_occluders, a.unit_cache, a.harvest, a.flora,
                        a.legacy_run, [effect_path(e) for e in a.texture_effect], not a.no_far_terrain,
                        # the routed-hull heap fallback runs inside the shared builder (chim.build.build_areas)
                        hull_fallback_sdk=a.sdk if a.validate else None)
        except (OSError, ValueError) as exc:
            ap.exit(1, 'Error: %s\n' % exc)
    import build_profile      # phase timer: start/end lines with time and cores, never part of a stage key
    with build_profile.phase('CHIM world conversion', '%d areas' % len(areas)):
        build_world()
    import build_parallel
    stage = build_parallel.active_stage_pool()
    if stage is not None:
        # the conversion's workers hold whole areas' meshes: the checks start on fresh workers (one restart)
        stage.recycle('world conversion done, its workers released')
    if regions_table is not None:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / 'chim-regions.json').write_bytes(chim_regions.dumps(regions_table).encode('utf-8'))
    # The lighting type and what of it is implemented (docs/chim/LIGHTING_ROADMAP.md) go into the receipt.
    import json
    from chim.light_types import record as lighting_record
    receipt_path = a.out / 'chim-receipt.json'
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_bytes().decode('utf-8'))
        receipt['lighting'] = lighting_record(lighting_type)
        receipt_path.write_bytes((receipt_text(receipt, a.jobs) + '\n').encode('utf-8'))
    validated = None
    if a.validate:
        # One validation per build (BUILD-CHIM-STATS-SERIAL-TAIL-36): the stats below reuse its world and
        # measurements; the report and stdout are what `chim/validate.py OUT --json ... --palette ...` writes.
        from build_jobs import resolve_jobs
        from chim.validate import report_text, report_world
        with build_profile.phase('CHIM validation', '%d frames' % len(areas)) as timer:
            src_path = a.out / 'chim-source.json'
            source_doc = json.loads(src_path.read_text(encoding='utf-8')) if src_path.is_file() else None
            report, world, _ = report_world(a.out, source_doc, a.palette.read_bytes(),
                                            jobs=resolve_jobs(a.jobs),
                                            cross_checks='serial' if a.pool == 'batch' else 'pool')
            text = report_text(report)
            (a.out / 'chim-validate.json').write_bytes(text.encode('utf-8'))
            sys.stdout.write(text)
            timer.done('CHIM validation: %s (%d failures)' % ('passed' if report['ok'] else 'FAILED',
                                                               report['failure_count']))
        if not report['ok']:
            ap.exit(1, 'Error: the CHIM world fails validation (%s)\n' % (a.out / 'chim-validate.json'))
        # the source manifest is let go (about 700 MB of JSON for 1,351 frames, several GB as objects: the stair
        # gate's workers need that memory); the stats read it again (one C JSON parse, seconds)
        source_doc = None
        validated = (world, report['measured'])
        # the gates below read the world the validation read (--pool stage), instead of reading and decoding
        # every file again each (--pool batch: the method before v0.0.42); the same world, the same reports
        shared = world if a.pool == 'stage' else None

        from stair_collision_env import stair_collision_method
        if stair_collision_method() == '1':
            # stair collision method 1: the geometric stair check of every mesh with flights, collected from the
            # frames' work folders (no walk); a mesh failing it under the method it ships with fails the stage
            import stair_mesh
            check_timer = build_profile.phase('CHIM stair check').__enter__()
            try:
                found = stair_mesh.require(a.out)
            except ValueError as exc:
                check_timer.__exit__(ValueError, exc, None)
                ap.exit(1, 'Error: %s\n' % exc)
            check_timer.done('CHIM stair check: %s (%d meshes with %d flights, %d ship a stairway collision mesh)'
                             % (found['status'], found['meshes'], found['flights'], len(found['ships_method_1'])))
            check_timer.__exit__(None, None, None)

        def stair_gate():
            """The stair gate and its receipt entries (gate order: --gate-order)."""
            import json
            # Every flight of stairs walked on the frame's own collision (COLLISION-STAIR-SLOPE-32).
            from chim.collision import require_stairs
            stair_timer = build_profile.phase('CHIM stair gate').__enter__()
            try:
                report = require_stairs(a.out, a.jobs, accepted=a.accept_known_stair_findings, world=shared)
            except ValueError as exc:
                stair_timer.__exit__(ValueError, exc, None)
                ap.exit(1, 'Error: %s\n' % exc)
            reuse = report.get('pass_cache') or {}
            stair_timer.done('CHIM stair gate: %s (%s steps and ramps tested, %d advisory, %d accepted known; walk %s: '
                             '%s frames reused, %s walked, %d walked again to check the cache)'
                             % (report['status'], report.get('tested', 0), len(report.get('advisory_failures', [])),
                                len(report.get('accepted_known_findings', [])), reuse.get('mode', 'cached'),
                                reuse.get('reused', 0), reuse.get('walked', '?'), len(reuse.get('sampled', []))))
            stair_timer.__exit__(None, None, None)
            # the CHIM receipt records the walk's reuse (BUILD-CHIM-HEAP-GATE-LATE-36)
            receipt_path = a.out / 'chim-receipt.json'
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            # (the candidate records this run stored are listed in chim-stairs.json, which the promotion reads)
            receipt['stair_walk'] = dict({k: v for k, v in reuse.items() if k != 'stored'}, status=report['status'],
                                         tested=report.get('tested', 0))
            receipt_path.write_text(receipt_text(receipt, a.jobs) + '\n', encoding='utf-8', newline='\n')
            if a.accept_known_stair_findings:
                # the receipt records the waiver (private test only)
                path = a.out / 'chim-receipt.json'
                receipt = json.loads(path.read_text(encoding='utf-8'))
                receipt['accepted_known_stair_findings'] = {
                    'ids': sorted(a.accept_known_stair_findings),
                    'failures': len(report.get('accepted_known_findings', [])),
                    'policy': 'private -devN test only (require_private_test_version)'}
                path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        if a.gate_order == 'stairs-first':
            # Order (B15, v0.0.42): the stair gate first. Its stored passes make an unchanged frame cost nothing, so
            # the walk is the frames that changed, and a stair failure stops the step before anything else runs.
            stair_gate()
        import json
        fallback = json.loads((a.out / 'chim-receipt.json').read_text(encoding='utf-8')).get('hull_fallback')
        if fallback:
            print('CHIM hull fallback: chains kept for %s (a ring did not fit with their routed hulls)'
                  % ', '.join(fallback['kept_as_chain']), flush=True)
        if a.stats:
            # While the validation's world is in memory (the gates never change the world).
            write_stats(a, build_profile, validated)
            validated = None
        # Order with --gate-order stairs-last (BUILD-CHIM-HEAP-GATE-LATE-36, the method before v0.0.42): the checks that
        # take seconds per frame first (heap, zone walk), the stair walk last, so a ring over the zone stops the stage at
        # once.
        # Every ring fits the engine's CHIM zone: strict, no exceptions (chim.heap).
        from chim.heap import require_heap
        heap_timer = build_profile.phase('CHIM heap gate', '%d frames' % len(areas)).__enter__()
        try:
            # frames in parallel; each frame's result kept by its content key beside the unit cache
            # (CHIM-WORLD-AUDIT-SCALING-33)
            heap = require_heap(a.out, a.sdk, jobs=resolve_jobs(a.jobs),
                                cache_dir=(a.unit_cache / 'heap') if a.unit_cache and not a.no_cache else None,
                                world=shared)
        except ValueError as exc:
            heap_timer.__exit__(ValueError, exc, None)
            ap.exit(1, 'Error: %s\n' % exc)
        heap_timer.done('CHIM heap gate: %s %s' % (heap['status'], ', '.join(
            '%s active ring peak %d, load ring peak %d (%d positions over), largest block %d, of %d bytes (gated: %s)'
            % (f['frame'], f['peak_bytes'], f['load_ring']['peak_bytes'], f['load_ring']['positions_over_budget'],
               f['largest_block_bytes'], f['budget_bytes'], f['gated_ring'])
            for f in heap.get('frames', []))))
        heap_timer.__exit__(None, None, None)
        # The engine's own zone allocator over a walk through every frame: never a step without ground
        # (CHIM-CHUNK-LOAD-FAIL-33, chim.zone_sim).
        from chim.zone_sim import require_zone_walk
        walk_timer = build_profile.phase('CHIM zone walk gate').__enter__()
        try:
            walk = require_zone_walk(a.out, a.sdk, jobs=resolve_jobs(a.jobs), world=shared)
        except ValueError as exc:
            walk_timer.__exit__(ValueError, exc, None)
            ap.exit(1, 'Error: %s\n' % exc)
        walk_timer.done('CHIM zone walk gate: %s %s' % (walk['status'], ', '.join(
            '%s: %d steps, %d loads without room, %d partial activations, %d+%d chunks released, %d model loads'
            % (w['name'], w['steps'], w['zone_fail'], w['partial'], w['released_band'], w['released_ring'],
               w['model_loads']) for w in walk.get('walks', []))))
        walk_timer.__exit__(None, None, None)
        if a.gate_order == 'stairs-last':
            stair_gate()
    if a.stats and not a.validate:
        if write_stats(a, build_profile, None) != 0:
            return 1
    if a.cell_progress:
        # The tracker is no longer run from here: the builder runs tools/cell_progress_build.py as its own stage
        # (cell-progress), so its code never keys this stage (BUILD-CHIM-KEY-UNDERDECLARED-35). Same data, same tool:
        print('CHIM cell progress: run `python3 tools/cell_progress_build.py --out %s --chim-world %s` '
              '(the builder does it in its cell-progress stage)' % (a.cell_progress, a.out), flush=True)
    return 0


def receipt_text(receipt, jobs):
    """The CHIM receipt as JSON (indent 1, sorted keys), its long lists encoded on the worker pool (the same
    bytes as json.dumps; chim.build.RECEIPT_LISTS, BUILD-CHIM-SERIAL-SECTIONS-44)."""
    import parallel_json
    from build_jobs import resolve_jobs
    from chim.build import RECEIPT_LISTS
    return parallel_json.dumps(receipt, RECEIPT_LISTS, jobs=resolve_jobs(jobs))


def write_stats(a, build_profile, validated):
    """chim-stats.json (chim.stats), timed; with VALIDATED (world, measurements) of this build's validation the
    world is not validated a second time."""
    from chim.stats import main as stats
    with build_profile.phase('CHIM stats', 'reusing this build\'s validation' if validated else 'validating the world'):
        from build_jobs import resolve_jobs
        code = stats([str(a.out)], *(validated or (None, None)), jobs=resolve_jobs(a.jobs))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
