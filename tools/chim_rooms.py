#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The listed rooms of a CHIM-native town (builder stage chim-rooms-TOWN).

A town's config may list interior cells ("interiors", tools/town_config.py). The legacy town chain converts them
inside its import stage (tools/import_town.py convert_interiors, town-TOWN). A CHIM-native town runs chim-town-TOWN
instead and has no legacy region maps, so its rooms need their own stage (BUILD-MINIWIND-ARENA-PIT-REFUSED-36,
a regression against v0.0.35, which shipped the Vivec Arena Pit vai000 through the legacy chain):

  rooms         every listed room that is not excluded, converted by the same converter as the legacy chain
                (town_interiors.convert -> prepare_area.build_room_cached: one hashed unit per room in the
                interior-room unit cache, the routed hulls and exact standing bevels of interiors), with its
                residents (prepare_area.populate): OUT/id1/maps/<room>.bsp, progs, sounds
  room banks    OUT/id1/doors-<room>.txt: doors into other listed rooms and exits to the town frame, by the
                same rule as the legacy chain (the town's map name; the engine loads its CHIM frame map)
  door bank     OUT/id1/<door file>: the town's exterior door table with the doors into the converted rooms
                linked (import_town.door_bank_text with the rooms); chim_town.install keeps this bank instead
                of its own unlinked one

Nothing is written to the shared scene: the stage works in OUT/scene (with the run's palette) and the image step
installs OUT/id1 (install, before chim_town.install). The legacy chain stays selectable (it converts the same rooms
inside town-TOWN). docs/chim/build_guide/BUILDER_TYPES.md, docs/TOWN_IMPORT.md.

    python3 tools/chim_rooms.py --town vivec_arena --data-files DATA --scene RUN/intro-scene \\
        --chim-world RUN/chim-world --out RUN/chim-rooms-vivec_arena --qbsp Q --vis V --light L [--jobs N]
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

FORMAT = 'AmiWind CHIM town rooms 1'
RECORD = 'rooms.json'


def listed_rooms(town, root=None):
    """The rooms the town converts (listed, not excluded), in list order: its own, then those of the towns
    its "interiors_from" names (town_interiors.listed_rooms; all of Vivec in one frame)."""
    from town_config import load_settings
    from town_interiors import listed_rooms as town_rooms
    return [room for room in town_rooms(load_settings(town, root), root) if room['exclude'] is None]


def has_rooms(town, root=None):
    try:
        return bool(listed_rooms(town, root))
    except (KeyError, ValueError, OSError):
        return False


def prepare(town, data_files, scene, chim_world, out, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, vis_mode='fast'):
    if town == 'seyda':
        raise ValueError('Seyda Neen keeps its rooms in its own stages, not chim_rooms')
    from build_jobs import resolve_jobs
    from mwad.paths import ensure_external, resolve_data_files
    from player_hull import lumps
    from town_config import load_settings, town_field
    from import_town import convert_interiors, door_bank_text, frame_references, write_json
    jobs = resolve_jobs(jobs)
    data = resolve_data_files(data_files)
    scene, chim_world = Path(scene), Path(chim_world)
    out = ensure_external(Path(out), town + ' CHIM rooms')
    out.mkdir(parents=True, exist_ok=False)
    settings = load_settings(town)
    if not listed_rooms(town):
        raise ValueError(town_field(settings, 'title') + ' lists no rooms to convert')
    # A private scene: the run's palette in, the rooms, their residents and banks out (never the shared scene).
    work_scene = out / 'scene'
    for folder in ('id1/gfx', 'id1/maps', 'id1/progs', 'id1/sound/npc'):
        (work_scene / folder).mkdir(parents=True)
    shutil.copyfile(scene / 'id1/gfx/palette.lmp', work_scene / 'id1/gfx/palette.lmp')
    # The hand timings every converted map carries (as chim_town and import_town take them).
    ext = lumps((scene / 'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings = '\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"', ext))
    rooms = convert_interiors(data, work_scene, settings, qbsp, vis, light, ffmpeg, jobs, vis_mode, timings)
    # The town's exterior door bank with its doors into the converted rooms (the CHIM world's own source stage).
    work = chim_world / 'work' / town
    if not (work / 'audit/placements.json').is_file():
        raise ValueError('The CHIM world has no source stage for ' + town + ': ' + str(work))
    references = frame_references(work, settings)
    index = json.loads((work / 'scenery/scenery-index.json').read_text())
    door_file = town_field(settings, 'door_file')
    (work_scene / 'id1' / door_file).write_text(door_bank_text(settings, references, index, rooms['cells']),
                                                encoding='cp1252', newline='\n')
    # OUT/id1 = what the image installs: everything the rooms wrote except the palette (the run's own).
    shutil.rmtree(work_scene / 'id1/gfx')
    (work_scene / 'id1').rename(out / 'id1')
    files = {path.relative_to(out / 'id1').as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted((out / 'id1').rglob('*')) if path.is_file()}
    record = {'format': FORMAT, 'town': town, 'map': town_field(settings, 'map'), 'door_file': door_file,
              'rooms': rooms['receipt'], 'excluded': rooms['excluded'], 'files': files,
              'source': 'game data; town_interiors.convert (interior-room units); door bank from the CHIM world '
                        'source stage ' + str(work.relative_to(chim_world))}
    write_json(out / RECORD, record)
    print('%s on CHIM: %d rooms (%s), %d excluded; door bank %s links %d doors'
          % (town_field(settings, 'title'), len(rooms['receipt']), ', '.join(r['map'] for r in rooms['receipt']),
             len(rooms['excluded']), door_file, sum(1 for line in (out / 'id1' / door_file).read_text(
                 encoding='cp1252').splitlines()[1:] if line.split(' ', 2)[1] != '-')), flush=True)
    return record


def output_record(rooms_dir):
    record = json.loads((Path(rooms_dir) / RECORD).read_text())
    if record.get('format') != FORMAT:
        raise ValueError('Not a CHIM rooms output: ' + str(rooms_dir))
    return record


def install(rooms_dir, id1):
    """Image step, before chim_town.install: copy a chim-rooms output's id1 files into the image. A file the image
    already holds with other bytes is refused (one file, two sources); the same bytes are the same file. Returns
    the record."""
    rooms_dir, id1 = Path(rooms_dir), Path(id1)
    record = output_record(rooms_dir)
    conflicts, copied = [], []
    for rel, sha in record['files'].items():
        source, target = rooms_dir / 'id1' / rel, id1 / rel
        if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
            conflicts.append('%s: changed since the stage wrote it' % rel)
        elif target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            conflicts.append('%s: staged in the image with other bytes' % rel)
    if conflicts:
        raise ValueError('CHIM rooms of %s collide with the image: %s' % (record['town'], '; '.join(conflicts[:8])))
    for rel in record['files']:
        target = id1 / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rooms_dir / 'id1' / rel, target)
        copied.append(rel)
    return {'town': record['town'], 'rooms': [r['map'] for r in record['rooms']], 'files': len(copied),
            'door_bank': record['door_file']}


def main(argv=None):
    from build_jobs import add_jobs
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--town', required=True)
    for name in ('data-files', 'scene', 'chim-world', 'out', 'qbsp', 'vis', 'light'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    p.add_argument('--vis-mode', default='fast')
    add_jobs(p)
    import npc_lod
    npc_lod.add_converter_options(p)  # the residents' near/far models, as import_town takes them
    a = p.parse_args(argv)
    npc_lod.apply_options(a)
    import build_profile; build_profile.instrument('chim-rooms')  # sub-stage timers (docs/BUILD_PROFILE.md)
    try:
        prepare(a.town, a.data_files, a.scene, a.chim_world, a.out, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs,
                a.vis_mode)
    except (OSError, ValueError) as error:
        p.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
