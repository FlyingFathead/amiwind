#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert every registered Balmora interior and its placed humanoid residents."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import resolve_data_files, ensure_external
from area_config import BALMORA_INTERIORS
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from player_hull import lumps
from prepare_area import build_room, populate
from vis_options import add_vis_option, map_threads


def prepare(data_files, scene, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, vis_mode='fast'):
    data = resolve_data_files(data_files)
    scene = ensure_external(scene, 'Balmora interiors')
    exterior = lumps((scene / 'id1/maps/balmora.bsp').read_bytes())[0].decode('cp1252')
    timings = '\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"', exterior))
    # Rooms compile side by side: divide the job budget between them.
    threads = map_threads(resolve_jobs(jobs), min(resolve_jobs(jobs), max(1, len(BALMORA_INTERIORS))))
    tasks = [(data, scene, entry, qbsp, vis, light, timings, threads, vis_mode) for entry in BALMORA_INTERIORS]
    rooms, reports = {}, []
    for report, cell in ordered_map(build_room, tasks, min(resolve_jobs(jobs), len(tasks))):
        slug = report['map']
        rooms[slug] = cell
        reports.append(report)
        shutil.copyfile(scene / 'area-work' / slug / 'room.bsp', scene / 'id1/maps' / f'{slug}.bsp')
        print('Balmora interior ready:', slug, report['bytes'], flush=True)
    return populate(data, scene, rooms, reports, ffmpeg, jobs,
                    include_exterior=False, report_name='balmora-interiors.json')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('data-files', 'scene', 'qbsp', 'vis', 'light'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    add_jobs(p)
    add_vis_option(p)
    a = p.parse_args()
    report = prepare(a.data_files, a.scene, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs, a.vis_mode)
    print(json.dumps({'interiors': len(report['rooms']), 'residents': len(report['cast'])}))
