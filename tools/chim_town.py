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
        raise ValueError('Seyda Neen is prepared by prepare_seyda (its scene chain, not the town converter)')
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


# ---------------------------------------------------------------- Seyda Neen, CHIM-native

SEYDA = 'seyda'


def chim_parity(chim_world, town):
    """The CHIM world's payload parity record of one area (chim.build: harvest_removed, town_flora_added, ...)."""
    receipt = json.loads((Path(chim_world) / 'chim-receipt.json').read_text(encoding='utf-8'))
    parity = receipt.get('parity') or {}
    if town in parity and isinstance(parity[town], dict):
        return parity[town]
    return parity if 'harvest_removed' in parity else {}


def seyda_maps(raw):
    """{map name: entity dicts} of the maps the legacy chain cuts from the complete converted town (the scene
    stage's maps/seyda.bsp, made from the game data): each region of the layout (prepare_seyda_regions.select on
    its coverage) and each special scene (prepare_intro_docks.keep_entity on its bounds, then select with its
    route polygon), by the same rules on the same entities, with nothing compiled. Returns (maps, entries,
    models): entries are the region table rows plus the specials, as the image's flora pass takes them."""
    import struct
    from compact_bsp import entities as town_entities
    from player_hull import lumps
    from prepare_intro_docks import keep_entity
    from prepare_seyda_regions import SPECIALS, regions as seyda_layout, select_entities, special_polygon
    data = lumps(raw)
    models = list(struct.iter_unpack('<9f7i', data[14]))
    town = town_entities(data[0])
    entries = [dict(e) for e in seyda_layout()]
    maps = {e['name']: select_entities(town, models, e['coverage']) for e in entries}
    for name, bounds in SPECIALS:
        coverage = [list(bounds[:2]), list(bounds[2:])]
        kept = [f for f in town if keep_entity(f, models, bounds)]
        maps[name] = select_entities(kept, models, coverage, special_polygon(name))
        entries.append({'name': name, 'coverage': coverage})
    return maps, entries, models


def seyda_flora(maps, entries, origin, flora, town_source_index, town_scene_report):
    """The image's town flora pass (install_town_flora) on the entity dicts of seyda_maps: per map, its legacy
    sprites bound to original flora (derive_bindings_fields) are replaced (bound_legacy_sprite) and the overlay's
    sprites (prepare_world_flora.sprite_rows) are added. The meshes and solid sprites' collision are CHIM world
    placements (chim.seyda town flora). Returns {map: {'added': n, 'removed': n}}."""
    from install_town_flora import derive_bindings_fields, load
    from prepare_world_flora import bound_legacy_sprite, identity, sprite_rows
    flora = Path(flora)
    receipt = load(flora / 'tree-sprites.json')
    index = load(flora / 'source/scenery-index.json')
    source_index = load(town_source_index)
    scene_report = load(town_scene_report) if town_scene_report else None
    record = {}
    for entry in entries:
        entry = dict(entry, origin=list(origin))
        rows = maps[entry['name']]
        retained, bindings = derive_bindings_fields(rows, source_index, scene_report, receipt, index, entry)
        added, selected = sprite_rows(index, receipt, entry, retained, bindings)
        available = {identity(r['source_key']): r for r in selected}
        kept, seen = [], set()
        for fields in rows:
            binding = bound_legacy_sprite(fields, bindings, available)
            if binding is None:
                kept.append(fields)
                continue
            key = identity(binding['source_key'])
            if key in seen:
                raise ValueError('Duplicate legacy sprite representation')
            seen.add(key)
        if seen != {identity(b['source_key']) for b in bindings}:
            raise ValueError('Required legacy sprite binding was not found: ' + entry['name'])
        maps[entry['name']] = kept + added
        record[entry['name']] = {'added': len(added), 'removed': len(rows) - len(kept)}
    return record


def seyda_activated(maps, models, names):
    """chim.frame_map.activated_entities on seyda_maps: the func_walls the engine activates by aw_ref in the
    maps `names`, each with its brush model's box from the complete town (the same brushes the region maps
    compile). Returns (rows, refusals)."""
    from chim.frame_map import activated_refs
    refs = activated_refs()
    found, refused = {}, []
    for name in sorted(names):
        for e in maps[name]:
            ref = e.get('aw_ref', '')
            if e.get('classname') != 'func_wall' or not ref.isdigit() or int(ref) not in refs:
                continue
            if not e.get('model', '').startswith('*'):
                refused.append('%s: activated object %s has no brush model' % (name, ref))
                continue
            m = models[int(e['model'][1:])]
            row = {k: v for k, v in e.items() if k != 'model'}
            row['_box'] = [[round(v, 4) for v in m[0:3]], [round(v, 4) for v in m[3:6]]]
            if ref in found and found[ref] != row:
                refused.append('%s: activated object %s differs between maps' % (name, ref))
                continue
            found[ref] = row
    return [found[k] for k in sorted(found, key=int)], refused


def seyda_static_check(maps, names, placed, parity):
    """(refusals, record): the frame_map.frame_entities statics rule both ways, on the entity dicts: every static
    (func_wall with a scenery aw_ref) of the maps `names`, with the town flora the image adds and without the
    harvest placements it removes (the CHIM world's parity record), is a CHIM placement of the frame, and the
    reverse (for the town; a special map holds a subset: one way only)."""
    from chim.frame_map import TERRAIN_REF
    statics = {int(e['aw_ref']) for name in names for e in maps[name]
               if e.get('classname') == 'func_wall' and e.get('model', '').startswith('*')
               and str(e.get('aw_ref', '')).isdigit() and int(e['aw_ref']) < TERRAIN_REF}
    statics |= set(parity.get('town_flora_added') or [])
    statics -= set(parity.get('harvest_removed') or [])
    placed = {int(r) for r in placed if str(r).isdigit()}
    maps_only = sorted(statics - placed)
    chim_only = sorted(placed - statics)
    refused = []
    if maps_only:
        refused.append('%d statics of the town are not in the CHIM world (%s)'
                       % (len(maps_only), ', '.join(map(str, maps_only[:8]))))
    return refused, {'statics': len(statics), 'in_chunks': len(statics & placed), 'town_only': maps_only,
                     'chim_only': chim_only}


def seyda_frame_rows(maps, names, default):
    """chim.frame_map.frame_entities on the point entities of the maps `names` (statics are CHIM placements,
    checked by seyda_static_check): the worldspawn, the default map's start and every point entity once."""
    from chim.frame_map import frame_entities
    points = {n: [e for e in maps[n] if not e.get('model', '').startswith('*')] for n in names}
    rows, report = frame_entities(points, set(), default)
    report['refused'] = [r for r in report['refused'] if 'CHIM statics are not in the final region maps' not in r]
    report.pop('chim_statics_not_in_maps', None)
    return rows, report


def prepare_seyda(data_files, scene, chim_world, out, flora=None, town_source_index=None, town_scene_report=None,
                  jobs=None):
    """Seyda Neen on CHIM with no legacy region maps (owner order 2026-10-11: "we can't have that kind of a
    workflow, first builds it, then throws them away"). The legacy chain compiled the complete converted town
    into 64 region maps and two special scenes, passed them through the image's flora, harvest and grounding
    passes, made the CHIM frame maps from their entities and deleted them. Here the same entities come from the
    scene stage's complete town (maps/seyda.bsp, converted from the game data), cut by the same rules
    (seyda_maps), with the image's town flora rule (seyda_flora); the actors are fitted on the CHIM frame's own
    collision (ground_actors), the arrival is checked on it, and the statics are checked against the CHIM
    placements (seyda_static_check). Writes OUT/entities.json (rows of the town frame map and of each special
    frame map, the activated objects) and OUT/id1/seyda-regions.txt (the region table: harvest catalogues and
    saves follow it)."""
    import hashlib
    from mwad.paths import ensure_external
    from import_town import write_json
    from prepare_seyda_regions import SPECIALS, default_region, directory_text, regions as seyda_layout
    from chim.frame_map import chim_placements, frame_world
    from chim.seyda import source_cell
    from harvest_build import town_origin
    scene, chim_world = Path(scene), Path(chim_world)
    raw = (scene / 'id1/maps/seyda.bsp').read_bytes()
    out = ensure_external(Path(out), 'Seyda Neen CHIM town')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'id1').mkdir()
    maps, entries, models = seyda_maps(raw)
    origin = town_origin(SEYDA)
    flora_record = None
    if flora is not None:
        flora_record = seyda_flora(maps, entries, origin, flora, town_source_index, town_scene_report)
    layout = seyda_layout()
    region_names = [e['name'] for e in layout]
    cell = tuple(source_cell())
    world, index = frame_world(chim_world, cell)
    placed = chim_placements(chim_world, cell)
    parity = chim_parity(chim_world, SEYDA)
    refused, statics = seyda_static_check(maps, region_names, placed, parity)
    if statics['chim_only']:       # the town frame holds the whole town: both ways
        refused.append('%d CHIM statics are not in the town (first: %s)'
                       % (len(statics['chim_only']), ', '.join(map(str, statics['chim_only'][:5]))))
    rows, report = seyda_frame_rows(maps, region_names, default_region(layout)['name'])
    refused += report['refused']
    activated, bad = seyda_activated(maps, models, region_names)
    refused += bad
    collision = FrameCollision(world, index)
    # the residents' models are the scene stage's (read only)
    grounding = ground_actors(rows, scene / 'id1', collision.point)
    fitted = {e['aw_ref']: e for e in rows if e.get('classname') == 'aw_npc' and 'aw_ref' in e}
    specials = {}
    for name, _ in SPECIALS:
        srows, sreport = seyda_frame_rows(maps, [name], name)
        refused += sreport['refused']
        # the special maps' actors are the town's actors on the same frame: their fit is the town's
        srows = [dict(fitted.get(e.get('aw_ref'), e)) if e.get('classname') == 'aw_npc' else e for e in srows]
        sact, bad = seyda_activated(maps, models, [name])
        refused += bad
        srefused, sstatics = seyda_static_check(maps, [name], placed, parity)
        refused += srefused
        specials[name] = {'rows': srows, 'activated': sact, 'statics': sstatics, 'report': sreport}
    if refused:
        raise ValueError('Seyda Neen on CHIM: ' + '; '.join(refused[:6]))
    (out / 'id1/seyda-regions.txt').write_text(directory_text(layout), encoding='ascii', newline='\n')
    record = {'format': FORMAT, 'town': SEYDA, 'map': SEYDA, 'door_file': None, 'region_file': 'seyda-regions.txt',
              'rows': rows, 'activated': activated, 'grounding': grounding, 'specials': specials,
              'statics': statics, 'report': report, 'flora': flora_record,
              'source': 'game data: the scene stage\'s complete converted town maps/seyda.bsp (sha256 %s); '
                        'no legacy region maps' % hashlib.sha256(raw).hexdigest()}
    write_json(out / 'entities.json', record)
    print('Seyda Neen on CHIM: %d frame entities (%d actors fitted on the frame collision), special frames %s, '
          '%d statics checked against the CHIM frame; no legacy region maps'
          % (len(rows), len(grounding), ', '.join('%s %d' % (n, len(s['rows'])) for n, s in specials.items()),
             statics['statics']), flush=True)
    return record


def output_record(town_dir):
    """The entities.json record of a chim-town output (checked format)."""
    record = json.loads((Path(town_dir) / 'entities.json').read_text())
    if record.get('format') != FORMAT:
        raise ValueError('Not a CHIM town output: ' + str(town_dir))
    return record


def output_files(town_dir):
    """{id1-relative path: file} of a chim-town output's id1 files (what install copies)."""
    base = Path(town_dir) / 'id1'
    return {path.relative_to(base).as_posix(): path for path in sorted(base.rglob('*')) if path.is_file()}


def same_bytes(a, b):
    return a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def legacy_claims(id1, town):
    """id1-relative files of the legacy chain for `town` staged in an image: its legacy exterior map
    (maps/<map>.bsp), its region maps (maps/<prefix>NNN.bsp) and a frame map maps/<map>-chim.chim (or .bsp)
    already there. A CHIM-native town has none: its frame map is written from the chim-town output."""
    from chim.frame_map import SPECIALS, map_name
    from town_config import runtime_towns
    id1 = Path(id1)
    row = next((t for t in runtime_towns() if t['id'] == town), None)
    if row is None:
        raise ValueError('Unknown town: ' + town)
    from map_files import map_rel
    names = ['maps/%s.bsp' % row['name'], map_rel(id1, map_name(row['name']))]
    if town == SEYDA:   # its special scenes (legacy maps) and their frame maps
        names += [n for name in SPECIALS for n in ('maps/%s.bsp' % name, map_rel(id1, map_name(name)))]
    names += sorted('maps/' + p.name for p in (id1 / 'maps').glob(row['prefix'] + '[0-9][0-9][0-9].bsp'))
    return [n for n in dict.fromkeys(names) if (id1 / n).is_file()]


def collisions(id1, town_dirs, areas=None, installed=False):
    """The CHIM-native towns' collision check (BUILD-IMAGE-CHIM-NATIVE-TOWN-36), read only: one line per
    conflict, naming the file and its two sources. A CHIM-native town's area is taken from its chim-town
    output only, so a conflict is (1) a legacy-chain file of that town staged in the image (legacy_claims),
    (2) a file the output installs that the image already holds with other bytes (identical bytes are the
    same stored file), (3) one file from two chim-town outputs with other bytes, (4) a town that is not an
    area of the CHIM world (`areas`; its frame map would never be written) or listed twice.
    installed: the image step already installed these outputs into id1 (its chim-towns.json record) and
    its later passes rewrite models in place, so (2) does not apply to that payload; the rest does."""
    id1 = Path(id1)
    found, seen, towns = [], {}, {}
    for town_dir in town_dirs or []:
        town_dir = Path(town_dir)
        town = output_record(town_dir)['town']
        source = 'chim-town output %s (CHIM-native %s)' % (town_dir.name, town)
        if town in towns:
            found.append('%s: CHIM-native town listed twice (%s and %s)' % (town, towns[town], town_dir.name))
            continue
        towns[town] = town_dir.name
        if areas is not None and town not in areas:
            found.append('%s: CHIM-native town is not an area of the CHIM world (%s): no frame map would '
                         'carry it' % (town, source))
        for rel in legacy_claims(id1, town):
            found.append('%s: legacy chain file staged in the image and %s' % (rel, source))
        for rel, path in output_files(town_dir).items():
            if not installed and (id1 / rel).is_file() and not same_bytes(id1 / rel, path):
                found.append('%s: staged in the image with other bytes and in %s' % (rel, source))
            if rel in seen and not same_bytes(seen[rel][0], path):
                found.append('%s: %s and %s with other bytes' % (rel, seen[rel][1], source))
            seen.setdefault(rel, (path, source))
    return found


def install(town_dir, id1):
    """Image step: copy a chim-town output's id1 files into the image and, when no
    converted-interiors stage wrote one, its exterior door bank. Returns the record.
    Refuses a collision (collisions): the area takes the CHIM-native files and no legacy piece."""
    import shutil
    town_dir, id1 = Path(town_dir), Path(id1)
    record = output_record(town_dir)
    conflicts = collisions(id1, [town_dir])
    if conflicts:
        raise ValueError('CHIM-native town %s collides with the image: %s' % (record['town'], '; '.join(conflicts[:8])))
    copied = []
    for path in sorted((town_dir / 'id1').rglob('*')):
        if path.is_file():
            rel = path.relative_to(town_dir / 'id1').as_posix()
            target = id1 / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            copied.append(rel)
    if record.get('door_file') is None:      # Seyda Neen: its doors are scenes (config/seyda_area.json)
        return {'town': record['town'], 'files': len(copied), 'door_bank': None}
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
    p.add_argument('--flora', type=Path, help='Seyda Neen: the world flora assets (the image\'s town flora rule)')
    p.add_argument('--town-source-index', type=Path, help='Seyda Neen: the town scenery\'s scenery-index.json')
    p.add_argument('--town-scene-report', type=Path, help='Seyda Neen: the scene stage\'s scene-report.json')
    add_jobs(p)
    a = p.parse_args(argv)
    import build_profile; build_profile.instrument('chim-town')  # sub-stage timers (docs/BUILD_PROFILE.md)
    try:
        if a.town == SEYDA:
            if a.flora is not None and (a.town_source_index is None or a.town_scene_report is None):
                raise ValueError('--flora needs --town-source-index and --town-scene-report')
            prepare_seyda(a.data_files, a.scene, a.chim_world, a.out, a.flora, a.town_source_index,
                          a.town_scene_report, a.jobs)
            return
        prepare(a.town, a.data_files, a.scene, a.chim_world, a.out, a.ffmpeg, a.jobs)
    except (OSError, ValueError) as error:
        p.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
