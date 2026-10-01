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
from prepare_seyda_regions import convert


def check(scene, data_files, output, allow_known=None):
    scene = Path(scene)
    output = ensure_external(output, 'actor preflight')
    output.mkdir(parents=True, exist_ok=False)
    # Work on copies. The retained scene and later terrain inputs stay untouched.
    id1 = output/'id1'
    maps = id1/'maps'; maps.mkdir(parents=True)
    shutil.copytree(scene/'id1/progs', id1/'progs')
    for source in sorted((scene/'id1/maps').glob('*.bsp')):
        if not re.fullmatch(r'vf[0-9]{4}\.bsp', source.name):
            shutil.copyfile(source, maps/source.name)
    for name in ('balmora-regions.txt',):
        source = scene/'id1'/name
        if source.is_file(): shutil.copyfile(source, id1/name)
    shutil.copyfile(scene/'seyda.bsp', maps/'seyda.bsp')
    convert(maps/'seyda.bsp', maps)
    annotate(maps, child_ci(data_files, 'Morrowind.esm'))
    (output/'actor-ground-support.json').write_text(json.dumps(bake_ground(maps), indent=2)+'\n')
    report = require(maps, output/'actor-initial-contact.json', allow_known, before_world=True)
    (output/'actor-ground-acceptance.json').write_text(json.dumps(report['acceptance'], indent=2)+'\n')
    print('Early actor check finished. Final image assembly repeats the complete audit.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scene', 'data-files', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--allow-known-actor-ground-findings', type=Path)
    args = parser.parse_args()
    try: check(args.scene, args.data_files, args.out, args.allow_known_actor_ground_findings)
    except (ValueError, OSError) as exc: parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__': main()
