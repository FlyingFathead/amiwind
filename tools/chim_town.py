#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""What a CHIM town needs beyond its CHIM world, made from the game data (builder stage chim-town-TOWN).

A town on CHIM is drawn and collided from its CHIM world (tools/chim_build.py). Its
legacy region maps (tools/import_town.py, the legacy chain) are not built: the
CHIM frame map takes its entities from here instead (CHIM-LEGACY-CHAIN-33):

  residents     every placed humanoid resident of the frame, baked like the legacy
                chain bakes them (import_town.residents: model, greeting voice),
                written to OUT/id1/progs and OUT/id1/sound/npc
  entities      OUT/entities.json: the frame map's worldspawn (message, hand
                timings, standing hull), the player start at the town arrival,
                and one aw_npc per resident with its source identity and its
                support fitted on the CHIM frame's own collision (the legacy
                fitter, actor_grounding, on chim.collision.FrameScene)
  region table  OUT/id1/<region file> (AWBR1): the town's sub-cells, arrival (a
                standing spot on the frame's collision, by the engine's arrival
                search) and return point; the engine, harvest catalogues and saves
                use it
  door bank     OUT/door-bank.txt: the exterior door table (import_town.door_bank_text),
                installed only when no converted-interiors stage wrote one

The town's scenery index and placements come from the CHIM world's own source
stage (CHIM_WORLD/work/TOWN), so nothing is converted twice. The legacy chain
stays selectable (--legacy-area TOWN; docs/chim/build_guide/BUILDER_TYPES.md).

    python3 tools/chim_town.py --town balmora --data-files DATA --scene RUN/intro-scene \\
        --chim-world RUN/chim-world --out RUN/chim-town-balmora [--ffmpeg FFMPEG] [--jobs N]
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

FORMAT = 'AmiWind CHIM town entities 1'
# Set by tools/build.py for every stage: the CHIM towns built without legacy region maps.
NATIVE_ENV = 'AMIWIND_CHIM_NATIVE_TOWNS'


def native_towns():
    """The towns of this build that are on CHIM with no legacy region maps (tools/build.py)."""
    import os
    return [t for t in os.environ.get(NATIVE_ENV, '').split(',') if t]
FIELD = re.compile(r'"([^"]*)"\s+"([^"]*)"')
GROUND_FIELDS = ('aw_source_id', 'aw_ground_mode')
BAKE_FIELDS = ('aw_ground_valid', 'aw_ground_baked', 'aw_authored_origin', 'aw_authored_z')


def parse_entity(text):
    return dict(FIELD.findall(text))


def worldspawn(settings, timings):
    """The frame map's worldspawn as the legacy region maps carry it after compilation:
    the hand timings (in key order, as compiled maps hold them), then classname, the
    standing hull profile and the message (checked against a legacy-chain build's
    frame map, CHIM-LEGACY-CHAIN-33)."""
    from player_hull import PROFILE
    from town_config import town_field
    row = dict(sorted(FIELD.findall(timings)))
    row.update({'classname': 'worldspawn', 'aw_hull': PROFILE, 'message': town_field(settings, 'message')})
    return row


def player_start(point):
    """info_player_start at the arrival, as the legacy home region holds it."""
    return {'angle': '90', 'classname': 'info_player_start', 'origin': ' '.join(map(str, point))}


def actor_rows(texts):
    """aw_npc rows with the identity fields last, as the image's annotation pass leaves them, in the
    frame map's point-entity order (chim.frame_map.frame_entities: by class, then by reference text)."""
    rows = []
    for text in texts:
        e = parse_entity(text)
        identity = {k: e.pop(k) for k in GROUND_FIELDS if k in e}
        e.update(identity)
        rows.append(e)
    return sorted(rows, key=lambda e: (e.get('classname', ''), str(e.get('aw_ref', ''))))


class FrameCollision:
    """The engine's arrival-search view (arrival_spot) of a CHIM frame's collision."""

    def __init__(self, world, index):
        from chim.collision import FrameScene
        self.hull = FrameScene(world, index)
        self.point = FrameScene(world, index, hull=0)

    def solid(self, p):
        hit = self.hull.trace(p, (p[0], p[1], p[2] - 1e-3))
        return bool(hit and hit['fraction'] == 0)

    def dry(self, p):
        from player_hull import MINS
        return self.point.contents((p[0], p[1], p[2] + MINS[2] + 1)) == -1

    def ground(self, p, depth):
        from player_hull import WALKABLE_Z
        hit = self.hull.trace(p, (p[0], p[1], p[2] - depth))
        if not hit or hit['fraction'] == 0 or hit['normal'][2] < WALKABLE_Z:
            return None
        return p[2] - depth * hit['fraction']


def frame_fitter(id1, scene):
    """actor_grounding's support fitter on one CHIM frame collision (no region cores to respect)."""
    from actor_grounding import _Fitter

    class FrameFitter(_Fitter):
        def __init__(self):
            super().__init__(Path(id1) / 'maps')

        def _scene(self, name):
            return scene

        def neighbourhood(self, name, point, samples):
            return scene

        def owned(self, name, candidate):
            return True
    return FrameFitter()


def ground_actors(rows, id1, scene):
    """Fit every ground-mode actor on the frame collision and write the fields the
    legacy bake writes (actor_grounding._bake_map), in its order; returns the report."""
    report = []
    fitter = frame_fitter(id1, scene)
    for e in rows:
        if e.get('classname') != 'aw_npc' or float(e.get('aw_ground_mode', 0)):
            continue
        authored = [float(v) for v in e.get('aw_authored_origin', e['origin']).split()]
        authored[2] = float(e.get('aw_authored_z', authored[2]))
        angles = tuple(float(v) for v in e.get('angles', '0 0 0').split())
        result = fitter.fit('frame', e, authored, angles)
        for field in BAKE_FIELDS:
            e.pop(field, None)
        placed = result.get('placed_origin')
        if placed is not None:
            e['origin'] = ' '.join(f'{v:.5f}' for v in placed)
            e['aw_ground_valid'] = '1'
            e['aw_ground_baked'] = ' '.join(f'{v:.5f}' for v in placed)
        e['aw_authored_origin'] = ' '.join(f'{v:.5f}' for v in authored)
        e['aw_authored_z'] = f'{authored[2]:.5f}'
        report.append(result)
        print('Actor support (CHIM frame):', e.get('aw_ref'), result.get('mesh_contact', result['status']), flush=True)
    return report


def prepare(town, data_files, scene, chim_world, out, ffmpeg='ffmpeg', jobs=None):
    from build_jobs import resolve_jobs
    from mwad.npc import load_master
    from mwad.paths import child_ci, ensure_external, resolve_data_files
    from player_hull import lumps
    from town_config import load_settings, town_field
    from town_regions import regions
    from import_town import (arrival_point, door_bank_text, frame_references, region_directory_text, residents,
                             return_point, write_json)
    from arrival_spot import standing, standing_spot
    from chim.frame_map import frame_world
    if town == 'seyda':
        raise ValueError('Seyda Neen on CHIM takes the recorded legacy stage (chim.seyda), not chim_town')
    jobs = resolve_jobs(jobs)
    data = resolve_data_files(data_files)
    scene, chim_world = Path(scene), Path(chim_world)
    out = ensure_external(Path(out), town + ' CHIM town')
    out.mkdir(parents=True, exist_ok=False)
    for folder in ('id1/progs', 'id1/sound/npc'):
        (out / folder).mkdir(parents=True)
    settings = load_settings(town)
    work = chim_world / 'work' / town
    if not (work / 'audit/placements.json').is_file():
        raise ValueError('The CHIM world has no source stage for ' + town + ': ' + str(work))
    references = frame_references(work, settings)
    index = json.loads((work / 'scenery/scenery-index.json').read_text())
    kinds, _, topics = load_master(child_ci(data, 'Morrowind.esm'))
    palette = (scene / 'id1/gfx/palette.lmp').read_bytes()
    texts = residents(data, out, out, references, settings, kinds, topics, palette, ffmpeg, jobs)
    ext = lumps((scene / 'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings = '\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"', ext))
    # The frame's own collision: the arrival is a standing spot on it and the actors stand on it.
    cell = tuple(settings['source_cell'])
    world, frame_index = frame_world(chim_world, cell)
    authored_arrival, yaw = arrival_point(kinds, settings)
    collision = FrameCollision(world, frame_index)
    spot = standing_spot(collision, tuple(authored_arrival))
    if spot is None or not standing(collision, tuple(spot)):
        raise ValueError(town_field(settings, 'title') + ': the arrival has no standing spot on the CHIM frame')
    arrival = list(spot)
    returning, return_yaw = return_point(kinds, settings)
    entries = regions(settings)
    rows = [worldspawn(settings, timings), player_start(arrival), *actor_rows(texts)]
    grounding = ground_actors(rows, out / 'id1', collision.point)
    region_file = town_field(settings, 'region_file')
    (out / 'id1' / region_file).write_text(region_directory_text(settings, entries, arrival, yaw, returning, return_yaw),
                                           encoding='ascii', newline='\n')
    (out / 'door-bank.txt').write_text(door_bank_text(settings, references, index), encoding='cp1252', newline='\n')
    record = {'format': FORMAT, 'town': town, 'map': town_field(settings, 'map'),
              'door_file': town_field(settings, 'door_file'), 'region_file': region_file,
              'authored_arrival': list(authored_arrival), 'arrival': arrival, 'yaw': yaw,
              'rows': rows, 'grounding': grounding,
              'source': 'game data; CHIM world source stage ' + str(work.relative_to(chim_world))}
    write_json(out / 'entities.json', record)
    print('%s on CHIM: %d residents, arrival %s, %d actors fitted on the frame collision'
          % (town_field(settings, 'title'), len(texts), arrival, len(grounding)), flush=True)
    return record


def install(town_dir, id1):
    """Image step: copy a chim-town output's id1 files into the image and, when no
    converted-interiors stage wrote one, its exterior door bank. Returns the record."""
    import shutil
    town_dir, id1 = Path(town_dir), Path(id1)
    record = json.loads((town_dir / 'entities.json').read_text())
    if record.get('format') != FORMAT:
        raise ValueError('Not a CHIM town output: ' + str(town_dir))
    copied = []
    for path in sorted((town_dir / 'id1').rglob('*')):
        if path.is_file():
            rel = path.relative_to(town_dir / 'id1').as_posix()
            target = id1 / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            copied.append(rel)
    door = id1 / record['door_file']
    door_source = 'converted interiors stage'
    if not door.is_file():
        shutil.copyfile(town_dir / 'door-bank.txt', door)
        door_source = 'chim-town (no converted interiors)'
    return {'town': record['town'], 'files': len(copied), 'door_bank': door_source}


def main(argv=None):
    from build_jobs import add_jobs
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--town', required=True)
    for name in ('data-files', 'scene', 'chim-world', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    add_jobs(p)
    a = p.parse_args(argv)
    import build_profile; build_profile.instrument('chim-town')  # sub-stage timers (docs/BUILD_PROFILE.md)
    try:
        prepare(a.town, a.data_files, a.scene, a.chim_world, a.out, a.ffmpeg, a.jobs)
    except (OSError, ValueError) as error:
        p.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
