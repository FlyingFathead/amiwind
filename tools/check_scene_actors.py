#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check converted actor contact before scheduling the expensive world terrain."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from actor_grounding import annotate, bake_ground
from check_actor_ground import require
from mwad.paths import child_ci, ensure_external
from prepare_seyda_regions import convert_builder_scene
from recorded_stage import check as check_recorded, frozen_maps
from vis_options import add_vis_option
from build_jobs import add_jobs, resolve_jobs


def check(scene, data_files, output, allow_known=None, *, ericw_bin, canonical_land_source=None, vis_mode='fast',
          jobs=None, seyda_recorded=None):
    scene = Path(scene)
    jobs = resolve_jobs(jobs)  # --jobs exactly; otherwise the stage budget or auto
    output = ensure_external(output, 'actor preflight')
    output.mkdir(parents=True, exist_ok=False)
    # Work on copies. The retained scene and later terrain inputs stay untouched.
    id1 = output/'id1'
    maps = id1/'maps'; maps.mkdir(parents=True)
    shutil.copytree(scene/'id1/progs', id1/'progs')
    for source in sorted((scene/'id1/maps').glob('*.bsp')):
        if not re.fullmatch(r'vf[0-9]{4}\.bsp', source.name):
            shutil.copyfile(source, maps/source.name)
    # Seyda's directory is regenerated below; converted towns keep theirs.
    from town_config import FIXED_TOWNS, runtime_towns
    for name in [town['regions'] for town in runtime_towns()[FIXED_TOWNS.index('balmora'):]]:
        source = scene/'id1'/name
        if source.is_file(): shutil.copyfile(source, id1/name)
    shutil.copyfile(scene/'seyda.bsp', maps/'seyda.bsp')
    # The image step's own conversion call, with this scene's inputs.
    convert_builder_scene(maps, scene_map=scene/'seyda.map', palette=scene/'id1/gfx/palette.lmp',
                          ericw_bin=ericw_bin, work_dir=output/'bounded-seyda',
                          canonical_land_source=canonical_land_source, vis_mode=vis_mode, jobs=jobs,
                          recorded=seyda_recorded)
    # Recorded-stage maps (BUILD-SEYDA-REGEN-30) keep their recorded placements.
    frozen = frozen_maps(output/'bounded-seyda')
    annotate(maps, child_ci(data_files, 'Morrowind.esm'), jobs=jobs, exclude=frozen)
    (output/'actor-ground-support.json').write_text(
        json.dumps(bake_ground(maps, jobs=jobs, exclude=frozen), indent=2)+'\n')
    check_recorded(id1, output/'bounded-seyda', 'actor-contact actor grounding', jobs=jobs)
    report = require(maps, output/'actor-initial-contact.json', allow_known, before_world=True,
                     jobs=jobs)
    (output/'actor-ground-acceptance.json').write_text(json.dumps(report['acceptance'], indent=2)+'\n')
    print('Early actor check finished. Final image assembly repeats the complete audit.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scene', 'data-files', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--allow-known-actor-ground-findings', type=Path)
    parser.add_argument('--ericw-bin', type=Path, required=True, help='ericw-tools directory (qbsp, vis, light)')
    parser.add_argument('--canonical-land-source', type=Path,
                        help='World-survey terrain-source.npz; required while Seyda terrain culling is enabled')
    parser.add_argument('--seyda-recorded', type=Path,
                        help='Recorded-stage exception BUILD-SEYDA-REGEN-30: owner-provided recorded Seyda Neen maps '
                             '(tools/recorded_stage.py) instead of the Seyda region conversion')
    add_vis_option(parser)
    add_jobs(parser)
    args = parser.parse_args()
    try: check(args.scene, args.data_files, args.out, args.allow_known_actor_ground_findings,
               ericw_bin=args.ericw_bin, canonical_land_source=args.canonical_land_source, vis_mode=args.vis_mode,
               jobs=args.jobs, seyda_recorded=args.seyda_recorded)
    except (ValueError, OSError) as exc: parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__': main()
