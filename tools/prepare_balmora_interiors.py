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
from prepare_area import build_room_cached, populate
from vis_options import add_vis_option, map_threads


def prepare(data_files, scene, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, vis_mode='fast', rooms=True,
            room_form='compiled'):
    """rooms=False: a quick test build without interiors (--exclude interiors,
    tools/build_exclusions.py): no room is compiled; the door tables are still
    written, so Balmora's doors say the area is unavailable. room_form: compiled or shell
    (prepare_area.add_room_form_option: a shell room is not compiled; the CHIM interiors stage makes it)."""
    from prepare_area import ROOM_FORMS
    if room_form not in ROOM_FORMS:
        raise ValueError('room_form must be one of %s' % ', '.join(ROOM_FORMS))
    listed = [dict(e, room_form='shell') for e in BALMORA_INTERIORS] if room_form == 'shell' else BALMORA_INTERIORS
    data = resolve_data_files(data_files)
    scene = ensure_external(scene, 'Balmora interiors')
    from mwad.paths import unshare_tree
    unshare_tree(scene)  # in place: BUILD-POOL-READONLY-SCENE-WRITE-35
    # The hand timings every converted map carries: the hands stage's report (BUILD-SEYDA-BSP-CARRIER-48; a legacy
    # balmora.bsp took the same fields from the same report through seyda.bsp).
    from hand_metadata import scene_timings
    timings = scene_timings(scene)
    # Rooms compile side by side: divide the job budget between them.
    threads = map_threads(resolve_jobs(jobs), min(resolve_jobs(jobs), max(1, len(BALMORA_INTERIORS))))
    tasks = [(data, scene, entry, qbsp, vis, light, timings, threads, vis_mode) for entry in listed]
    if not rooms:
        print(f'Quick test build: {len(tasks)} Balmora rooms left out (--exclude interiors).', flush=True)
        tasks = []
    rooms, reports = {}, []
    # Longest room first: history, else its placed references (BUILD-ORDERED-WINDOW-33).
    from build_costs import costed_map, room_sizes
    sizes = room_sizes(data, [(e['map'], e['cell']) for e in BALMORA_INTERIORS])
    # A quick test build without interiors runs no room (and records no room times).
    for report, cell in (costed_map('balmora-interiors-rooms', build_room_cached, tasks, [t[2]['map'] for t in tasks],
                                    max(1, min(resolve_jobs(jobs), len(tasks))), fallback=sizes.get if sizes else None)
                         if tasks else ()):
        slug = report['map']
        rooms[slug] = cell
        reports.append(report)
        shutil.copyfile(scene / 'area-work' / slug / 'room.bsp', scene / 'id1/maps' / f'{slug}.bsp')
        from interior_plants import install_room_files
        install_room_files(scene, slug, report)
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
    p.add_argument('--no-rooms', action='store_true',
                   help='Quick test build (--exclude interiors): do not compile the rooms')
    from prepare_area import add_room_form_option
    add_room_form_option(p)
    import npc_lod
    npc_lod.add_converter_options(p)
    a = p.parse_args()
    npc_lod.apply_options(a)
    import build_profile; build_profile.instrument('balmora-interiors')  # sub-stage timers (docs/BUILD_PROFILE.md)
    report = prepare(a.data_files, a.scene, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs, a.vis_mode, rooms=not a.no_rooms,
                     room_form=a.room_form)
    print(json.dumps({'interiors': len(report['rooms']), 'residents': len(report['cast'])}))
