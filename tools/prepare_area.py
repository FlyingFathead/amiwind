#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert the starting area's rooms and residents from the user's owned master."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA
from mwad.interior import read_interior, select_geometry
from mwad.npc import load_master, outfit, greeting_fixture, behavior_record, greeting_settings, first
from mwad.paths import resolve_data_files, child_ci, ensure_external, replace_bytes, replace_copy
from area_config import SCENES, inside
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from vis_options import add_vis_option, light_args, map_threads, vis_args
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl, add_root_rule_arg, apply_root_rule
from npc_anim import foot_class, publish as publish_anim, voices_of
import npc_items
from prepare_scenery import export_refs
from prepare_mesh_bsp import add_dressing_option, append_meshes, apply_dressing_option, interior_dressing
from prepare_quake import box, wad, miptex, CENTRE, SCALE
from prepare_npcs import quote, display_text
from player_hull import lumps, pack_lumps, rebuild_world_hull
from prepare_doors import prepare as prepare_doors
import npc_lod


# The inline model budget of a converted interior (INTERIOR-INLINE-LIMIT-31; town_interiors.MODEL_LIMIT).
INLINE_MODEL_LIMIT = 220


# The room's own spawn (info_player_start: the map command, dbg tp to the room, a direct start) is the first
# original arrival that is not under the room's water (INTERIOR-SPAWN-UNDERWATER-41: the first arrival into
# Vivec's Hlaalu Underworks is the canal grate, 141 units under the water). Doors keep their own arrivals.
# AMIWIND_ROOM_SPAWN=first: the earlier rule, the first arrival whatever it is.
ROOM_SPAWN_ENV = 'AMIWIND_ROOM_SPAWN'


def spawn_entrance(cell):
    """The original arrival a converted room spawns at (see ROOM_SPAWN_ENV)."""
    import os
    mode = os.environ.get(ROOM_SPAWN_ENV, '') or 'dry'
    if mode not in ('dry', 'first'):
        raise ValueError('%s must be dry or first, not %r' % (ROOM_SPAWN_ENV, mode))
    entrances = cell['entrances']
    water = cell.get('water_height')
    if mode == 'first' or water is None:
        return entrances[0]
    return next((e for e in entrances if e['destination']['position'][2] >= water), entrances[0])


def entity(fields):
    return '{\n' + '\n'.join(quote(k)+' '+quote(v) for k,v in fields.items()) + '\n}'


class TalkGreetings:
    """The conversation greeting each placed NPC opens a talk with (mwad.dialogue.talk_greeting,
    the rule of OpenMW's DialogueManager::startDialogue), one evaluation per (NPC, cell), shared by
    every resident writer (towns, CHIM towns, rooms, Seyda Neen). fields() gives the entity keys:
    aw_greeting (first meeting) and aw_greeting_again (later talks) when they exist; record() is
    what the residents report keeps (topic, INFO, determined or not, and why)."""

    def __init__(self, data, kinds, topics, cells=()):
        from mwad.dialogue import dialogue_records, exterior_cell_names, greeting_topics
        # no Greeting topic (a synthetic master): nothing to pick, the master is not read again
        self.names = {}
        if greeting_topics(topics):
            kinds = dialogue_records(child_ci(data, 'Morrowind.esm'), kinds)
            self.names = exterior_cell_names(kinds, cells)
        self.kinds, self.topics = kinds, topics
        self.cache = {}

    def exterior_name(self, position):
        from town_grid import physical_cell
        return self.names.get(physical_cell({'position': position}))

    def lookup(self, identifier, cell):
        from mwad.dialogue import greeting_topics, talk_greeting
        key = (identifier.casefold(), cell)
        if key not in self.cache:
            self.cache[key] = (talk_greeting(self.kinds, self.topics, identifier, cell)
                               if greeting_topics(self.topics) else {'first': '', 'again': '', 'record': {}})
        return self.cache[key]

    def fields(self, identifier, cell):
        talk = self.lookup(identifier, cell)
        out = {}
        if talk['first']:
            out['aw_greeting'] = display_text(talk['first'])
            if talk['again']:
                out['aw_greeting_again'] = display_text(talk['again'])
        return out

    def record(self):
        return {f'{i}@{c or ""}': talk['record']
                for (i, c), talk in sorted(self.cache.items(), key=lambda kv: (kv[0][0], kv[0][1] or ''))}


ROOM_ROOF_TABLE = Path(__file__).resolve().parents[1]/'config/collision-room-roof.json'


_ROOM_ROOF = {}


def room_roof_meshes(path=ROOM_ROOF_TABLE):
    """The exterior meshes whose convex pieces may not stand a step over their own floor in a room
    (config/collision-room-roof.json 'meshes'; ROOM-PYLON-ROOF-48): source paths in lower case."""
    if path in _ROOM_ROOF:
        return _ROOM_ROOF[path]
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema') != 'aw-collision-room-roof-1':
        raise ValueError('Unsupported room roof table: %s' % Path(path).name)
    _ROOM_ROOF[path] = frozenset(m.replace(chr(92), '/').casefold() for m in data['meshes'])
    return _ROOM_ROOF[path]


def interior_visual_profile(model, area=None):
    """Visual/collision profile of one interior mesh ('meshes/...' path), or
    None when the mesh keeps the assembly default. Shared with the world
    estimate (tools/world_estimate_data.py) so both use the same rule."""
    if model in room_roof_meshes():
        # a listed exterior mesh placed in a room keeps the assembly default, except that a convex piece standing
        # more than a step over a walkable face of its own becomes its authored plates (mesh_geometry.roof_plates):
        # the pylons of the Ministry of Truth's Hall of Processing put a 16-unit slope over the floor two residents
        # stand on (ROOM-PYLON-ROOF-48; config/collision-room-roof.json)
        from player_hull import STEP_HEIGHT
        return {'roof_collision_beyond': STEP_HEIGHT}
    if not model.startswith('meshes/i/'):
        return None
    profile = {'ratio':1., 'texture_size':32,
               'collision_source':'root_node_or_visual',
               'hollow_collision':not ('rock' in model or 'boulder' in model)}
    if area == 'balmora' and profile['hollow_collision']:
        profile['exact_collision_bevels'] = True
    # the stair-plate rules (mesh_geometry.collision_pieces: steep toes cut to vertical steps, STAIRS-VIVEC-ROOMS-JOINT-36)
    profile['stair_plates'] = True
    return profile


ROOM_FORMS = ('compiled', 'shell')


def add_room_form_option(parser):
    """--room-form: how a room stage writes its rooms (BUILD-SEYDA-BSP-CARRIER-48). compiled: qbsp, vis and light (a
    room map the engine loads: --interior-format bsp, the legacy rooms); shell: the CHIM room's inputs only (scenery
    export, kept placements, entities and liquid brushes in a shell map with no faces, as the batch rooms,
    tools/chim_room_batches.py), for the CHIM interiors stage, which keeps nothing else of a compiled room. build.py
    passes shell whenever the build makes CHIM rooms."""
    parser.add_argument('--room-form', choices=ROOM_FORMS, default='compiled',
                        help='compiled (default: qbsp, vis, light) or shell (no compile; the CHIM interiors stage '
                             'makes the room); a room with an activated object is compiled either way')


def mesh_placements(index, references=None, retain_dressing=False, centre=(0, 0)):
    """(kept reference numbers in index order, omitted rows, dressing retained rows, selection report): the placements
    prepare_mesh_bsp.append_meshes places as func_walls for these arguments (its selection, its dressing rule), without
    building anything. A shell room's placements.json is this list, so its CHIM room places what the compiled room
    map placed (tests/test_room_shell.py checks it against append_meshes)."""
    from prepare_mesh_bsp import DRESSING_EXCLUDED
    from scenery_selection import select_runtime_refs
    if references is None:
        selected, selection = select_runtime_refs(index, centre, SCALE, 736)
    else:
        wanted = set(references)
        selected = [dict(r) for r in index['references'] if r['number'] in wanted]
        if {r['number'] for r in selected} != wanted:
            raise ValueError('Explicit BSP references were not all converted')
        selection = {'selected_groups': [], 'omitted': [], 'explicit_references': len(wanted)}
    excluded = ([] if retain_dressing is True else
                [t for t in DRESSING_EXCLUDED if not retain_dressing or t not in retain_dressing])

    def term(ref, terms):
        return next((t for t in terms if t in index['models'][ref['model_index']]['source']), None)
    omitted = [dict(reference=r['number'], id=r.get('id'), model=index['models'][r['model_index']]['source'],
                    reason='dressing excluded by the mesh converter (%s)' % t)
               for r in selected for t in [term(r, excluded)] if t]
    retained = [dict(reference=r['number'], id=r.get('id'), model=index['models'][r['model_index']]['source'], rule=t)
                for r in selected for t in [term(r, DRESSING_EXCLUDED)] if t and t not in excluded]
    kept = [r['number'] for r in selected if not term(r, excluded)]
    return kept, omitted, retained, selection


def shell_room(root, index, refs, entry, label, timings, point_entities, textures, low, high, retain_selected,
               dressing, sprite_numbers, tree_numbers, tree_solid, plant_rows, lighting, palette, scene):
    """build_room's shell form (--room-form shell): ROOT/room.bsp a shell map (chim_room_batches.shell_map: no faces,
    the room's bounds, its worldspawn marked _chim_room_shell, the start, lava and loop entities, plant sprites; the
    "*water" and "*lava" textures in its texture lump), ROOT/placements.json the placements the compiled room map
    would place (mesh_placements). The room.map is written as before (its liquid brushes are what the CHIM interiors
    stage reads). Returns the report, or None when a kept placement is an object the engine activates (aw_activated.h):
    a shell room has no CHIM room form for its box yet (chim.interior.room_map), so that room is compiled."""
    import interior_plants
    from chim.frame_map import activated_refs
    from chim_room_batches import SHELL_KEY, shell_map
    solid_models = set(tree_solid)
    skipped = set(sprite_numbers) | {r['number'] for r in refs if r['number'] in tree_numbers and
                                     'meshes/' + r['model'].replace('\\', '/').casefold() not in solid_models}
    explicit = [r['number'] for r in index['references'] if r['number'] not in skipped] if retain_selected else None
    kept, omitted, retained, selection = mesh_placements(index, explicit, True if retain_selected else dressing)
    activated = sorted(set(kept) & set(activated_refs()))
    if activated:
        print('Room %s: activated object(s) %s: compiled, not a shell (no CHIM room form for their box yet)'
              % (entry['map'], ', '.join(map(str, activated))), flush=True)
        return None
    world = '{\n"classname" "worldspawn"\n"message" ' + quote(label) + '\n"%s" "1"\n' % SHELL_KEY + \
        (timings + '\n' if timings else '') + '}'
    entities = [world] + list(point_entities)
    report = {'form': 'chim room shell', 'placements': len(kept), 'references': len(index['references']),
              'omitted': omitted, 'dressing_retained': retained, 'selection': selection}
    if sprite_numbers or tree_numbers:
        sprites, plants = interior_plants.place(root / 'source', refs, sprite_numbers + tree_numbers, lighting, palette,
                                                (Path(scene) / 'id1/gfx/colormap.lmp').read_bytes(), root / 'id1')
        entities += sprites
        report['plant_sprites'] = {'placements': len(sprite_numbers) + len(tree_numbers),
                                   'sprite_files': plants['files'], 'sprites': plants['sprites'],
                                   'decisions': plant_rows, 'mode': interior_plants.plant_mode(),
                                   'trees': len(tree_numbers), 'collision_only_models': tree_solid,
                                   'rule': 'nonsolid static plants and static trees drawn as shaded sprites; a solid '
                                           'tree keeps its collision (tools/interior_plants.py)'}
    elif plant_rows:
        report['plant_sprites'] = {'placements': 0, 'decisions': plant_rows}
    liquids = [blob for name, _, blob in textures if name != 'voidwall']
    (root / 'room.bsp').write_bytes(shell_map(low, high, entities, liquids))
    (root / 'placements.json').write_text(json.dumps(kept) + '\n', encoding='utf-8', newline='\n')
    report['bytes'] = (root / 'room.bsp').stat().st_size
    return report


def room_folder(root):
    """ROOT made for one room build: new, or holding only empty folders (another stage's reuse made them,
    BUILD-REUSE-FOREIGN-DIRS-52: no earlier room). A file in it stops the room (FileExistsError)."""
    root = Path(root)
    if not (root.is_dir() and not any(path.is_file() or path.is_symlink() for path in root.rglob('*'))):
        root.mkdir(parents=True, exist_ok=False)
    return root


def build_room(task):
    data, scene, entry, qbsp, vis, light, timings = task[:7]
    # Optional (vis threads, vis mode); older 7-field tasks keep -threads 1 -fast.
    vis_threads, vis_mode = task[7:9] if len(task) > 7 else (1, 'fast')
    # Optional 10th field: dressing kept by the Seyda Neen rooms (prepare below,
    # interior_dressing); other callers keep the earlier skip rule (receipted).
    dressing = task[9] if len(task) > 9 else False
    slug = entry['map']
    cell = read_interior(child_ci(data, 'Morrowind.esm'), entry['cell'],
                         include_interior_entrances=entry.get('original_door_arrivals', False))
    if entry.get('recentre'):
        # A room moved toward the origin (INTERIOR-COORDS-31; town_interiors.room_offsets): every position of
        # the cell, its lights and arrivals with the offset subtracted, before anything is converted.
        from town_interiors import recentre_cell
        cell = recentre_cell(cell, entry['recentre'])
    root = room_folder(scene/'area-work'/slug)
    refs, omitted = select_geometry(cell, harvest_references=entry.get('harvest_references', ()),
                                    harvest_master_sha256=entry.get('harvest_master_sha256'))
    profiles = {}
    for ref in refs:
        model = 'meshes/'+ref['model'].replace('\\','/').lower()
        profile = interior_visual_profile(model, entry.get('area'))
        if profile is not None:
            profiles[model] = profile
    retain_selected=entry.get('area')=='balmora' or entry.get('retain_selected_geometry',False)
    # Plants drawn as sprites (interior_plants: every room by default, AMIWIND_INTERIOR_PLANTS; a room over its
    # inline model limit in mode over-limit, town_interiors.build_room_checked): those placements are left out
    # of the mesh models. A solid static tree is a sprite too and keeps its collision as a collision-only model
    # (decided here, before the export, so the model's profile carries it; INTERIOR-MORAG-TONG-FPS-43).
    sprite_numbers,plant_rows,tree_numbers,tree_solid=[],[],[],[]
    import interior_plants
    if retain_selected and interior_plants.room_wants_sprites(entry):
        from prepare_scenery import bsa_read, nif_reader
        from prepare_tree_sprites import collision_metadata
        from world_flora import flora_kind
        bsa=BSA(child_ci(data,'Morrowind.bsa'));reader=nif_reader();collisions={}
        def collision_of(model):
            if model not in collisions:
                collisions[model]=collision_metadata(bsa_read(bsa,'meshes/'+model),reader,flora_kind(model))
            return collisions[model]
        sprite_numbers,plant_rows=interior_plants.candidates(refs,collision_of)
        if interior_plants.trees_too() or entry.get('tree_sprites'):
            tree_numbers,tree_solid,tree_rows=interior_plants.tree_candidates(refs,collision_of)
            plant_rows=plant_rows+tree_rows
        for model in tree_solid:
            profiles[model]={**profiles.get(model,{}),'collision_only':True}
    groups = {slug:{'references':[r['number'] for r in refs], 'visual_profiles':profiles}}
    refs = [dict(r, scene_groups=[slug]) for r in refs]
    from interior_lighting import cell_lighting
    lighting = cell_lighting(cell)
    if slug=='addamasartus':
        lighting={**lighting,'lights':[],'shared_ambient':True}
    # Lava pools become Quake liquid brushes (tools/lava.py, docs/LAVA.md); --lava static keeps
    # the earlier rule (the pool activator is left out, select_geometry).
    import lava as lava_rules
    lava_mode=lava_rules.lava_mode()
    pools=(lava_rules.pools_of(data,cell['refs'],lava_rules.molten_objects_of(child_ci(data,'Morrowind.esm')))
           if lava_mode=='quake' else [])
    if pools:
        lighting={**lighting,'lights':list(lighting.get('lights',[]))+
                  [light for p in pools for light in lava_rules.glow_lights(p['hull'],p['top'])]}
    parts = root/'source'
    export_refs(data, parts, refs, groups, [0,0,0], 8192, 128,
                {'cell':cell['name'], 'lighting':lighting}, jobs=1)
    index = json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError(slug+': '+str(index['errors']))
    low = np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*SCALE)-32
    high = np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*SCALE)+32
    pool_box=lava_rules.quake_bounds(pools,[0,0,0],SCALE)
    if pool_box:
        low=np.minimum(low,np.floor(np.array(pool_box[0]))-32);high=np.maximum(high,np.ceil(np.array(pool_box[1]))+32)
    walls = []
    for axis in range(3):
        a=low.copy();b=high.copy();b[axis]=low[axis]+8;walls.append(box(a,b,'voidwall'))
        a=low.copy();b=high.copy();a[axis]=high[axis]-8;walls.append(box(a,b,'voidwall'))
    palette = (scene/'id1/gfx/palette.lmp').read_bytes()
    tile = Image.new('P',(16,16),255);tile.putpalette(palette)
    textures=[('voidwall',0x43,miptex('voidwall',tile))]
    water=cell.get('water_height')
    if water is not None:
        level=water*SCALE
        if not low[2]<level<high[2]:raise ValueError(slug+': water outside room bounds')
        a=low+8;b=high-8;b[2]=level
        walls.append(box(a,b,'*water'))
        liquid=Image.new('RGB',(64,64),(65,87,91)).quantize(palette=tile,dither=Image.Dither.NONE)
        textures.append(('*water',0x43,miptex('*water',liquid)))
    lava_brushes,lava_entities,lava_records=lava_rules.map_parts(pools,[0,0,0],SCALE)
    if pools:
        walls+=lava_brushes
        assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
        layers=max((p['layers'] for p in pools),key=len)
        textures+=lava_rules.wad_entries(assets.texture,layers,tile)
    (root/'room.wad').write_bytes(wad(textures))
    if not cell['entrances']:raise ValueError('No source entrance for '+cell['name'])
    entrance = spawn_entrance(cell)['destination']
    spawn = [v*SCALE for v in entrance['position']];spawn[2]+=16.875
    yaw = (90-math.degrees(entrance['rotation_radians'][2]))%360
    label = cell['name'].removeprefix('Seyda Neen, ').removeprefix('Balmora, ')
    source = '{\n"classname" "worldspawn"\n"wad" "room.wad"\n"message" '+quote(label)+'\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    point_entities = [entity({'classname':'info_player_start','origin':' '.join(map(str,spawn)),'angle':yaw})]
    point_entities += list(lava_entities)
    if pools:
        # the pools' "lava layer" loop (their script's sound), at most lava.LOOP_LIMIT emitters per room
        lava_volumes,lava_sound_receipts=lava_rules.convert_sounds(data,pools,scene/'id1/sound',shutil.which('ffmpeg') or 'ffmpeg')
        point_entities += list(lava_rules.loop_entities(pools,[0,0,0],SCALE,lava_volumes))
    source += ''.join(text+'\n' for text in point_entities)
    (root/'room.map').write_text(source,encoding='cp1252')
    # the room stages of a build with CHIM rooms (--room-form shell, build.py chim_interior_commands): a shell map, no
    # compile (BUILD-SEYDA-BSP-CARRIER-48: the CHIM interiors stage keeps only the entities, boxes and liquid brushes)
    if entry.get('room_form') == 'shell':
        shell = shell_room(root, index, refs, entry, label, timings, point_entities, textures, low, high,
                           retain_selected, dressing, sprite_numbers, tree_numbers, tree_solid, plant_rows,
                           lighting, palette, scene)
        if shell is not None:
            report = shell
            report.update(map=slug,cell=cell['name'],spawn=spawn,yaw=yaw,omitted=omitted+report['omitted'],
                          water_height=water,master_sha256=cell['master_sha256'],
                          lava={'mode':lava_mode,'pools':lava_records})
            if entry.get('original_door_arrivals') or entry.get('harvest_references'):
                report.update(original_arrivals=cell['entrances'],
                              harvest_excluded_references=[r['number'] for r in entry.get('harvest_references', ())],
                              retained_geometry_references=[r['number'] for r in refs],
                              bsp_sha256=hashlib.sha256((root/'room.bsp').read_bytes()).hexdigest())
            (root/'conversion.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            return report, cell
    with (root/'compile.log').open('w') as log:
        for exe,args in [(qbsp,['-nopercent','room.map']),
                         (vis,vis_args('room.bsp',vis_threads,vis_mode)),
                         (light,light_args('-minlight','24','room.bsp'))]:
            subprocess.run([str(Path(exe).resolve()),*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    base=root/'base.bsp';(root/'room.bsp').rename(base)
    rebuild_world_hull(base,root/'room.map',qbsp)
    # a solid tree's collision-only model stays placed (its collision); a nonsolid tree is left out like a plant
    solid_models=set(tree_solid)
    skipped=set(sprite_numbers)|{r['number'] for r in refs if r['number'] in tree_numbers and
                                 'meshes/'+r['model'].replace('\\','/').casefold() not in solid_models}
    report=append_meshes(base,root/'room.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=1,
                         references=[r['number'] for r in index['references'] if r['number'] not in skipped] if retain_selected else None,
                         retain_dressing=True if retain_selected else dressing,
                         map_identity='bmtemple' if slug=='bmtemple' else None)
    sprite_files={}
    if sprite_numbers or tree_numbers:
        entities,plants=interior_plants.place(parts,refs,sprite_numbers+tree_numbers,lighting,palette,
                                              (scene/'id1/gfx/colormap.lmp').read_bytes(),root/'id1')
        # the sprite files live in the room's folder (cached with it); the room converter installs them
        interior_plants.add_entities(root/'room.bsp',entities)
        sprite_files=plants['files']
        report['plant_sprites']={'placements':len(sprite_numbers)+len(tree_numbers),'sprite_files':plants['files'],
                                 'sprites':plants['sprites'],'decisions':plant_rows,'mode':interior_plants.plant_mode(),
                                 'trees':len(tree_numbers),'collision_only_models':tree_solid,
                                 'rule':'nonsolid static plants and static trees drawn as shaded sprites; a solid '
                                        'tree keeps its collision (tools/interior_plants.py)'}
        report['bytes']=(root/'room.bsp').stat().st_size
    elif plant_rows:
        report['plant_sprites']={'placements':0,'decisions':plant_rows}
    # A sprite file takes one model slot of the map, as an inline model does.
    models_used=report['unique_models']+len(sprite_files)
    report['model_slots']=models_used
    if models_used>INLINE_MODEL_LIMIT:
        raise ValueError('%s: inline model budget exceeded (%d > %d inline models)'
                         % (slug, models_used, INLINE_MODEL_LIMIT))
    report.update(map=slug,cell=cell['name'],spawn=spawn,yaw=yaw,omitted=omitted+report['omitted'],
                  water_height=water,master_sha256=cell['master_sha256'],
                  lava={'mode':lava_mode,'pools':lava_records})
    if entry.get('original_door_arrivals') or entry.get('harvest_references'):
        report.update(original_arrivals=cell['entrances'],
                      harvest_excluded_references=[r['number'] for r in entry.get('harvest_references', ())],
                      retained_geometry_references=[r['number'] for r in refs],
                      bsp_sha256=hashlib.sha256((root/'room.bsp').read_bytes()).hexdigest())
    (root/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report, cell


def room_unit(task):
    """(unit cache, inputs) of one interior room (build_room), or (None, None) when the cache is off or the
    game data identity is unknown (BUILD-IMAGE-NO-RESUME-33: a stage resumes from its finished rooms)."""
    import hashlib
    from pass_cache import UnitCache, game_data_digest, tool_digest
    cache = UnitCache.open('interior-room', {}, __file__)
    data_identity = game_data_digest() if cache is not None else None
    if data_identity is None:
        return None, None
    data, scene, entry, qbsp, vis, light, timings = task[:7]
    vis_mode = task[8] if len(task) > 8 else 'fast'
    dressing = task[9] if len(task) > 9 else False
    palette = hashlib.sha256((Path(scene) / 'id1/gfx/palette.lmp').read_bytes()).hexdigest()
    from interior_plants import plant_mode
    return cache, {'entry': entry, 'plants': plant_mode(), 'timings': timings, 'vis_mode': vis_mode, 'dressing': dressing,
                   'palette': palette, 'tools': tool_digest(qbsp, vis, light), 'game_data': data_identity}


def build_room_cached(task):
    """Worker: build_room, or the room recorded for the same inputs (its folder and receipt). Rows that do not
    survive JSON exactly are never cached, so a cached room returns what a built one would."""
    try:
        cache, inputs = room_unit(task)
        if cache is not None:
            from pass_cache import input_digest
            input_digest(inputs)  # every input has a content key
    except (TypeError, ValueError, OSError):
        cache = None
    if cache is None:
        return build_room(task)
    from pass_cache import json_exact
    root = Path(task[1]) / 'area-work' / task[2]['map']
    row = cache.restore_unit(inputs, root)
    if row is not None:
        return row['report'], row['cell']
    report, cell = build_room(task)
    if json_exact({'report': report, 'cell': cell}):
        cache.store_unit(inputs, {'report': report, 'cell': cell}, root)
    return report, cell


RESIDENT_UNIT = 'resident-bake'
RESIDENT_UNIT_FORMAT = 1
RESIDENT_LEVELS = '.levels'       # a unit folder's near/far level files (npc_lod '_levels'), not installed


def open_residents():
    """(unit cache, game data identity) of the resident bakes, or (None, None) when the cache is off or the game data
    identity is unknown. Opened once per stage (ROOM-RESIDENTS-KEY-SERIAL-49): opening the cache analyses the
    repository's sources for its environment and the identity reads the build's input lock (about 7 MB of JSON);
    once per resident that was 233 s on one core for 1,769 residents before the first restore. The same values
    whichever way it is opened, so the same keys."""
    from pass_cache import UnitCache, game_data_digest
    cache = UnitCache.open(RESIDENT_UNIT, {}, __file__)
    identity = game_data_digest() if cache is not None else None
    if identity is None:
        return None, None
    return cache, identity


def resident_unit(task, opened=None, digests=None):
    """(unit cache, inputs) of one resident bake (build_resident and the files it publishes), or (None, None) when
    the cache is off or an input has no content key (ROOM-RESIDENTS-NOT-CACHED-48: the room stages baked every
    resident again on every run). The key is what the bake reads: the appearance and greeting the stage resolved
    from the game data, the game data identity (the input lock: models, textures, sounds), the palette, the level
    settings (not the asset pool's folder), ffmpeg by content, and the code and AMIWIND_* settings this module reaches
    (UnitCache: the animation profile and head settings come from the environment).
    OPENED: open_residents() of the stage (opened here when not given); DIGESTS: a dict the stage shares between its
    residents for the SHA-256 of the level list file (read once, not once per resident). Same inputs either way."""
    import hashlib
    import shutil as _shutil
    from pass_cache import tool_digest
    cache, identity = open_residents() if opened is None else opened
    if cache is None or identity is None:
        return None, None
    data, palette, appearance, greeting, ffmpeg = task[:5]
    lod = dict(task[5]) if len(task) > 5 and task[5] is not None else None
    if lod is not None:
        pool = lod.pop('pool', None)          # where bakes are pooled, not what they are
        if lod.get('list'):
            listed = str(lod['list'])
            known = digests.get(listed) if digests is not None else None
            if known is None:
                known = hashlib.sha256(Path(listed).read_bytes()).hexdigest()
                if digests is not None:
                    digests[listed] = known
            lod['list'] = known
    program = _shutil.which(str(ffmpeg)) or str(ffmpeg)
    if not Path(program).is_file():
        return None, None

    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, default=repr).encode()).hexdigest()
    return cache, {'entry': {'name': appearance['id']}, 'format': RESIDENT_UNIT_FORMAT,
                   'appearance': digest(appearance), 'greeting': digest(greeting),
                   'palette': hashlib.sha256(palette).hexdigest(), 'lod': lod, 'ffmpeg': tool_digest(program),
                   'game_data': identity}


def resident_files(task, folder):
    """build_resident, then its files written into FOLDER (publish_resident). Returns (identifier, record)."""
    return publish_resident(folder, *build_resident(task))


def publish_resident(folder, identifier, raw, voice, record):
    """A baked resident's files written into FOLDER as they go into id1 (the model, its layouts, item models and
    sounds, the greeting voice; npc_lod level files under RESIDENT_LEVELS). Returns (identifier, record)."""
    folder = Path(folder)
    stem = 'a_' + hashlib.sha256(identifier.encode()).hexdigest()[:12]
    record.update(model='progs/' + stem + '.mdl', voice='npc/' + stem + '.wav' if voice else '')
    (folder / 'progs').mkdir(parents=True, exist_ok=True)
    (folder / record['model']).write_bytes(raw)
    publish_anim(folder, record)
    npc_items.publish(folder, record)
    if voice:
        target = folder / 'sound' / record['voice']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(voice)
    levels = record.pop('_levels', None)
    if levels is not None:
        (folder / RESIDENT_LEVELS).mkdir()
        for level, data in levels.items():
            (folder / RESIDENT_LEVELS / ('%d.mdl' % int(level))).write_bytes(data)
    return identifier, record


def restore_resident(task, folder, opened=None, digests=None):
    """(cache, inputs, record or None) of one resident: its record and files restored into FOLDER from the unit cache
    when its inputs are unchanged. OPENED, DIGESTS: as resident_unit (the stage's shared open)."""
    folder = Path(folder)
    shutil.rmtree(folder, ignore_errors=True)
    try:
        cache, inputs = resident_unit(task, opened, digests)
    except (TypeError, ValueError, OSError):
        cache, inputs = None, None
    if cache is None:
        return None, None, None
    row = cache.restore_unit(inputs, folder)
    if row is None:
        shutil.rmtree(folder, ignore_errors=True)
        return cache, inputs, None
    return cache, inputs, row['record']


def json_record(record):
    """A resident's record as JSON holds it (tuples become lists, numpy numbers plain numbers): the stage writes it to
    its report as JSON anyway, and a baked and a restored resident then hand the stage the same record (the first
    measured run stored only 69 of its residents: the others' records held tuples, so json_exact refused them)."""
    def plain(value):
        if hasattr(value, 'tolist'):
            return value.tolist()
        if hasattr(value, 'item'):
            return value.item()
        raise TypeError('not JSON: %r' % type(value))
    return json.loads(json.dumps(record, default=plain))


def store_resident(cache, inputs, folder, identifier, record):
    """Record a baked resident's folder and record (json_record) in the unit cache. A record that does not survive JSON
    exactly is never stored, so a restored resident is what a baked one would be."""
    from pass_cache import json_exact
    if cache is not None and json_exact(record):
        cache.store_unit(inputs, {'identifier': identifier, 'record': record}, folder)


def build_resident_cached(job):
    """One resident's bake into its unit folder: restored from the unit cache when its inputs are unchanged, else
    baked and stored. Returns (identifier, record, made)."""
    task, folder = job
    cache, inputs, record = restore_resident(task, folder)
    if record is not None:
        return task[2]['id'], record, False
    identifier, record = resident_files(task, folder)
    record = json_record(record)
    store_resident(cache, inputs, folder, identifier, record)
    return identifier, record, True


def install_resident(folder, id1, record):
    """Copy one resident's unit folder into id1 (each file replaced whole: BUILD-POOL-READONLY-SCENE-WRITE-35);
    the level files go back into the record for npc_lod.publish. Removes the folder."""
    folder, id1 = Path(folder), Path(id1)
    for path in sorted(p for p in folder.rglob('*') if p.is_file()):
        relative = path.relative_to(folder)
        if relative.parts[0] == RESIDENT_LEVELS:
            record.setdefault('_levels', {})[int(path.stem)] = path.read_bytes()
            continue
        target = id1 / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != path.read_bytes():
            replace_bytes(target, path.read_bytes())
    shutil.rmtree(folder, ignore_errors=True)


_resident_assets={}
_resident_rigs={}
_resident_sounds={}

class ResidentBudgetError(ValueError):
    """A resident's animation kit model does not fit the alias byte budget at any rung of the vertex budget ladder
    (npc_geometry.bake's full-sample check at budget 192, or npc_anim.fit at the smallest frame counts)."""


RESIDENT_LADDER = (480, 384, 320, 256, 192)
BYTE_BUDGET_ERROR = 'Alias byte budget exceeded with full samples'


def resident_levels(profile_name):
    """The animation levels a resident bake tries, in order (RESIDENT-ANIM-BYTE-BUDGET-48): (level, profile).
    'kit' = the build's profile (e.g. react+full: the standing model and its mover); 'standing' = the kit's
    standing profile alone, no mover (only when the build's profile has a mover and its standing profile is not
    idle); 'idle' = the previous method (8 idle frames, the town residents' older models). The engine plays all
    three (aw_anim.c: a layout without a mover never swaps models; a model without a layout plays its idle frames)."""
    import npc_anim
    if profile_name == 'idle':
        return [('kit', 'idle')]
    standing, mover = npc_anim.split_profile(profile_name)
    levels = [('kit', profile_name)]
    if mover and standing != 'idle':
        levels.append(('standing', standing))
    return levels + [('idle', 'idle')]


def build_resident(task):
    """One resident's bake: (identifier, model bytes, voice bytes, record). The build's animation profile first; a
    resident whose kit model does not fit the alias byte budget at any rung of the ladder falls back to the kit's
    standing model alone, else to the idle-only model (resident_levels), and its record says so
    (record['anim_fallback']: the build's profile, the level and profile baked, the reasons). The same inputs
    take the same path, so the same bytes."""
    import npc_anim
    profile_name, _ = npc_anim.selected_profile()
    reasons = []
    for level, name in resident_levels(profile_name):
        try:
            identifier, raw, voice, record = _bake_resident(task, name)
        except ResidentBudgetError as error:
            if level == 'idle':
                raise
            reasons.append('%s (%s): %s' % (level, name, error))
            continue
        if reasons:
            record['anim_fallback'] = {'profile': profile_name, 'level': level, 'baked': name, 'reasons': reasons}
            print('Resident animation fallback: %s: profile %s does not fit the alias byte budget (%s); baked as %s '
                  '(%s)' % (identifier, profile_name, '; '.join(reasons), level, name), flush=True)
        return identifier, raw, voice, record
    raise AssertionError('resident_levels ends with idle')


def anim_fallbacks(models):
    """[{id, level, baked, profile, reasons}] of the residents (populate's models) that fell back, by id."""
    return [dict(id=identifier, **record['anim_fallback']) for identifier, record in sorted(models.items())
            if record.get('anim_fallback')]


def greeting_voice(assets,greeting,ffmpeg):
    """(WAV bytes, seconds) of a resident's greeting: 11025 Hz 8-bit mono, at most 15 seconds."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);(tmp/'voice.mp3').write_bytes(assets.read('sound/'+greeting['voice']))
        subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(tmp/'voice.mp3'),
                        '-ac','1','-ar','11025','-c:a','pcm_u8',str(tmp/'voice.wav')],check=True)
        with wave.open(str(tmp/'voice.wav')) as sound:
            duration=sound.getnframes()/sound.getframerate()
            if duration>15:raise ValueError('Greeting exceeds 15-second budget')
        return (tmp/'voice.wav').read_bytes(),duration


_resident_guards={}


def _guard_torch(key,data,assets,appearance,palette):
    """A skeletal guard's torch item (prepare_guard_torches.torch_item) when the guard carries the original torch
    (guard_eligibility: a guard class with a carryable torch light in its inventory), else None. The baked guards
    (--npc-anim-type 1) get theirs from the image step's guard torch registry instead."""
    import prepare_guard_torches as G
    if key not in _resident_guards:
        npcs,lights,mesh=G.guard_sources(child_ci(data,'Morrowind.esm'))
        _resident_guards[key]={'npcs':npcs,'lights':lights,'mesh':mesh,'items':{}}
    guards=_resident_guards[key]
    fields=guards['npcs'].get(appearance['id'].casefold())
    if fields is None or not G.guard_eligibility(fields,guards['lights'],guards['mesh'])[1]:
        return None
    shade=hashlib.sha256(palette).hexdigest()
    if shade not in guards['items']:
        guards['items'][shade]=G.torch_item(assets,guards['mesh'],palette,_resident_rigs[(key,appearance['skeleton'])].N)
    return guards['items'][shade]


def _skeletal_resident(task, profile_name, profile, key, assets):
    """build_resident's --npc-anim-type 2 bake (skeletal_actor.skeletal_resident): the model, its layout on the
    table's frames (no mover), its carried items' skeletal tag (AWTS1, SKEL-ITEM-TAGS-52), sounds and voice as the
    kit bake gives them; the table itself rides along (record['anim']['_table'], written once by npc_anim.publish).
    No near/far levels: those are baked idle frames (--npc-lod)."""
    import npc_anim
    import skeletal_actor
    data, palette, appearance, greeting, ffmpeg = task[:5]
    def rig_of(path):
        rig=(key,path)
        if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,path)
        return _resident_rigs[rig]
    raw,groups,skel,tag,items=skeletal_actor.skeletal_resident(key,assets,appearance,palette,profile,rig_of,
                                                               torch=_guard_torch(key,data,assets,appearance,palette))
    table_bytes,_,_,table_path,_,_=skeletal_actor.game_table(key,appearance,rig_of)
    foot=appearance.get('foot','bare')
    if key not in _resident_sounds:
        _resident_sounds[key]=npc_anim.soun_records(child_ci(data,'Morrowind.esm'))
    lines={t:[(s,tuple(tuple(x) for x in c) if c else None) for s,c in v] for t,v in (appearance.get('voices') or {}).items()}
    barks=npc_anim.voice_words(lines)
    described=[{k:v for k,v in g.items() if k!='events'}|{'events':[list(e) for e in g['events']]} for g in groups]
    anim={'type':2,'profile':profile_name,'layout':(npc_anim.layout(groups,foot)+' '+barks).strip(),'foot':foot,
          'voices':{t:[[s,[list(x) for x in c] if c else None] for s,c in v] for t,v in lines.items()},
          'groups':described,'skeletal':skel,'frame_bytes':0,
          '_sounds':npc_anim.sound_payload(assets,_resident_sounds[key],npc_anim.needed_sounds(groups,foot)),
          '_table':(table_path,table_bytes)}
    voice,duration=greeting_voice(assets,greeting,ffmpeg)
    lo=np.asarray(skel['model']['box_lo']);hi=lo+255*np.asarray(skel['model']['box_step'])
    record={'appearance':appearance,'greeting':greeting,
        'step':float(groups[0]['step']),'triangles':skel['model']['faces'],'frames':skel['table_frames'],
        'bounds':[lo.tolist(),hi.tolist()],
        'sha256':hashlib.sha256(raw).hexdigest(),'voice_seconds':duration,'anim':anim,
        **({'_item_tag':tag,'_items':items} if tag else {})}
    return appearance['id'],raw,voice,record


def _bake_resident(task, profile_name):
    # Optional 6th field: the near/far model settings (tools/npc_lod.py task_settings);
    # older 5-field tasks bake the single model as before.
    data, palette, appearance, greeting, ffmpeg = task[:5]
    lod = task[5] if len(task) > 5 else None
    key=str(Path(data).resolve())
    if key not in _resident_assets:_resident_assets[key]=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
    assets=_resident_assets[key];rig=(key,appearance['skeleton'])
    if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,appearance['skeleton'])
    skeleton=_resident_rigs[rig]
    dead=appearance.get('initially_dead',False)
    import npc_anim
    profile=npc_anim.plan_profile(profile_name)
    kit=None
    if npc_anim.anim_type()==2 and not dead:
        # --npc-anim-type 2 (the default): one rest frame on the shared table of its skeleton, every group of the
        # profile played from the table's frames, no mover (docs/MODULAR_NPCS.md "Runtime method C"). An actor that
        # starts dead keeps its one baked death pose below: one frame, as a static model.
        return _skeletal_resident(task,profile_name,profile,key,assets)
    if dead:times,step=np.array([skeleton.events['death1: stop']]),0.
    elif profile_name=='idle':times,step=skeleton.idle_times(8)   # the previous method, unchanged
    else:
        # Animation kit (docs/ANIMATION.md): idle first, then the profile's groups.
        female=None
        if appearance.get('female') and appearance['skeleton']=='meshes/base_anim.nif':
            rig=(key,npc_anim.FEMALE_SKELETON)
            if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,npc_anim.FEMALE_SKELETON)
            female=_resident_rigs[rig]
        kit,groups=npc_anim.plan(skeleton,profile,female,appearance.get('weight',1.),
                                 attack_stance=appearance.get('attack_stance'))
        times=npc_anim.idle_compatible_times(groups);step=groups[0]['step']
    anim={}
    item_times=times;mover_item_times=None
    if lod is not None and not kit:
        # The same bake (npc_lod.bake_far is this ladder), plus the other levels with --npc-lod on.
        # The animation kit (kit) bakes one model; near/far levels are for idle-only residents.
        import npc_lod
        levels,lod_facts=npc_lod.resident_bake(data,assets,skeleton,appearance,palette,times,lod)
        raw=levels[npc_lod.MAP_LEVEL]
        facts={'triangles':lod_facts['far_triangles'],'frames':lod_facts['frames'],'bounds':lod_facts['bounds']}
    else:
        shapes,materials,textures=assemble(assets,appearance,kit or skeleton,times)
        for budget in RESIDENT_LADDER:
            # reference_frames=8: the face quotas of the idle-only model (head topology unchanged).
            try:frames,faces,uv,skin=bake(shapes,materials,textures,palette,budget=budget,reference_frames=8 if kit else None,
                                               full_frame_budget=npc_anim.ACTOR_BYTE_BUDGET if kit else None);break
            except ValueError as error:
                if str(error) not in ('Alias vertex budget exceeded',BYTE_BUDGET_ERROR) or budget==RESIDENT_LADDER[-1]:
                    # over the byte budget at every rung: build_resident falls back (resident_levels)
                    kind=ResidentBudgetError if kit and str(error)==BYTE_BUDGET_ERROR else ValueError
                    raise kind(appearance['id']+': '+str(error)) from error
        if kit:
            # One bake gives both models: the standing model is a subset of the mover's frames (react+full).
            standing_name,mover_name=npc_anim.split_profile(profile_name)
            nv,nt,(sw,sh)=frames.shape[1],len(faces),skin.size
            def model(gs,index):
                names=[g['name']+'%02d'%i for g in gs for i in range(g['count'])]
                return animated_mdl(frames[index],faces,uv,skin,names=names)
            def describe(gs):
                return [{k:v for k,v in g.items() if k!='events'}|{'events':[list(e) for e in g['events']]} for g in gs]
            foot=appearance.get('foot','bare')
            if key not in _resident_sounds:
                _resident_sounds[key]=npc_anim.soun_records(child_ci(data,'Morrowind.esm'))
            try:
                if mover_name:
                    mover_groups,mover_index=npc_anim.fit(groups,nv,nt,sw,sh,npc_anim.ACTOR_BYTE_BUDGET)
                    keep={g['name']:g['count'] for g in groups if g['name'] in dict(npc_anim.profiles()[standing_name])}
                    standing_groups,standing_index=npc_anim.select(groups,keep)
                else:
                    mover_groups=None
                    standing_groups,standing_index=npc_anim.fit(groups,nv,nt,sw,sh,npc_anim.ACTOR_BYTE_BUDGET)
            except npc_anim.AliasBudgetError as error:
                raise ResidentBudgetError(appearance['id']+': '+str(error)) from error
            raw=model(standing_groups,standing_index)
            # Item tags (<model>.tag) have one row per frame of THIS model (aw_items.c refuses any other
            # count): the standing model's frames, not every kit sample (ANIMKIT-ITEM-TAG-FRAMES-35).
            item_times=np.asarray(standing_index,dtype=float)
            sound_groups=mover_groups or standing_groups
            # Voice barks: the lines this actor can say per voice topic (mwad.npc.voice_lines), both models.
            # (the callers resolve them with the master's topics: appearance['voices'], npc_anim.voices_of)
            lines={t:[(s,tuple(tuple(x) for x in c) if c else None) for s,c in v] for t,v in (appearance.get('voices') or {}).items()}
            barks=npc_anim.voice_words(lines)
            anim={'profile':profile_name,'layout':(npc_anim.layout(standing_groups,foot)+' '+barks).strip(),'foot':foot,
                  'voices':{t:[[s,[list(x) for x in c] if c else None] for s,c in v] for t,v in lines.items()},
                  'groups':describe(standing_groups),'frame_bytes':npc_anim.frame_bytes(nv),
                  '_sounds':npc_anim.sound_payload(assets,_resident_sounds[key],npc_anim.needed_sounds(sound_groups,foot))}
            if mover_name:
                mover=model(mover_groups,mover_index)
                anim['mover']={'profile':mover_name,'layout':(npc_anim.layout(mover_groups,foot)+' '+barks).strip(),'groups':describe(mover_groups),
                               'bytes':len(mover),'frames':len(mover_index),'sha256':hashlib.sha256(mover).hexdigest()}
                anim['_mover']=mover
                mover_item_times=np.asarray(mover_index,dtype=float)
        else:raw=animated_mdl(frames,faces,uv,skin)
        facts={'triangles':len(faces),'frames':len(frames),
               'bounds':[frames.min((0,1)).tolist(),frames.max((0,1)).tolist()]}
    # Carried weapon/shield (both animation methods): drawn while fighting as separate item
    # models on the hand bones' per-frame tags (tools/npc_items.py; NPC-WEAPON-MESH-33).
    tag,items,mover_tag=(None,{},None) if dead else (npc_items.resident_items(assets,palette,appearance,kit or skeleton,item_times)+(None,)
        if mover_item_times is None else npc_items.resident_items(assets,palette,appearance,kit,item_times,mover_item_times))
    voice,duration=(b'',0.) if dead else greeting_voice(assets,greeting,ffmpeg)
    record={'appearance':appearance,'greeting':greeting,
        'step':float(step),'triangles':facts['triangles'],'frames':facts['frames'],
        'bounds':facts['bounds'],
        'sha256':hashlib.sha256(raw).hexdigest(),'voice_seconds':duration,
        **({'anim':anim} if anim else {}),**({'_item_tag':tag,'_items':items} if tag else {}),**({'_mover_item_tag':mover_tag} if mover_tag else {})}
    if lod is not None and lod.get('mode')=='on' and not kit:
        record['lod']={k:lod_facts.get(k) for k in ('head_error','levels')}
        record['_levels']=levels
    return appearance['id'],raw,voice,record


def prepare(data_files,scene,qbsp,vis,light,ffmpeg='ffmpeg',jobs=None,vis_mode='fast',rooms=True,room_form='compiled'):
    """rooms=False: a quick test build without interiors (--exclude interiors,
    tools/build_exclusions.py). The rooms are not compiled; the exterior residents
    are placed and the door tables written as usual, so their doors say the area is
    unavailable. room_form: compiled or shell (add_room_form_option)."""
    if room_form not in ROOM_FORMS:
        raise ValueError('room_form must be one of %s' % ', '.join(ROOM_FORMS))
    data=resolve_data_files(data_files);scene=ensure_external(scene,'area conversion')
    from mwad.paths import unshare_tree
    unshare_tree(scene)  # in place: BUILD-POOL-READONLY-SCENE-WRITE-35
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    # the hand timings every converted map carries: the hands stage's report (BUILD-SEYDA-BSP-CARRIER-48)
    from hand_metadata import scene_timings
    timings=scene_timings(scene)
    entries=[s for s in SCENES if s['interior'] and s['map'] not in ('prison','census')
             and s.get('area', 'seyda') == 'seyda']
    if room_form=='shell':
        entries=[dict(s,room_form='shell') for s in entries]
    if not rooms:
        print(f'Quick test build: {len(entries)} Seyda Neen rooms left out (--exclude interiors).',flush=True)
        entries=[]
    # Rooms compile side by side: divide the job budget between them.
    workers=min(resolve_jobs(jobs),max(1,len(entries)))
    tasks=[(data,scene,s,qbsp,vis,light,timings,map_threads(resolve_jobs(jobs),workers),vis_mode,interior_dressing())
           for s in entries]
    rooms={};reports=[]
    # Longest room first: history, else its placed references (BUILD-ORDERED-WINDOW-33).
    from build_costs import costed_map, room_sizes
    sizes=room_sizes(data,[(e['map'],e['cell']) for e in entries])
    # A quick test build without interiors runs no room (and records no room times).
    for report,cell in (costed_map('area-rooms',build_room_cached,tasks,[e['map'] for e in entries],max(1,min(resolve_jobs(jobs),len(tasks))),
                                  fallback=sizes.get if sizes else None)
                        if tasks else ()):
        slug=report['map'];rooms[slug]=cell;reports.append(report)
        replace_copy(scene/'area-work'/slug/'room.bsp',scene/'id1/maps'/f'{slug}.bsp')
        from interior_plants import install_room_files;install_room_files(scene,slug,report)
        print('Interior ready:',slug,report['bytes'],'bytes',flush=True)
    return populate(data,scene,rooms,reports,ffmpeg,jobs)


def populate(data,scene,rooms,reports,ffmpeg='ffmpeg',jobs=None,
             include_exterior=True,report_name='area-report.json',doors=True,exclude_residents=()):
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    kinds,cells,topics=load_master(child_ci(data,'Morrowind.esm'))
    # Actors the original's start scripts disable at a new game stay out with --start-disabled original
    # (tools/start_disabled.py; off by default), listed in left_out with their enable rule.
    import start_disabled
    def hold(refs,where):
        live=[r for r in refs if not r.get('deleted')]
        if not live or start_disabled.mode()!='original':return list(refs),[]
        _,held=start_disabled.held(live,start_disabled.table_for(data),where,active=True)
        out={id(r) for r in live if any(h['reference']==r.get('number') and h['id']==r['id'] for h in held)}
        kept=[r for r in refs if id(r) not in out]
        for row in held:print('Resident left out at a new game:',where,row['id'],'(reference %s):'%row['reference'],row['reason'],flush=True)
        return kept,held
    cast=[];left_out=[]
    exterior=[ref for cell in (cells if include_exterior else []) for ref in cell['refs']
              if not ref.get('deleted') and ref['id'].casefold() in kinds['NPC_']
              and not ref['id'].casefold().startswith('chargen ') and inside(ref['position'])]
    exterior,held=hold(exterior,'seyda');left_out.extend(held)
    cast.extend(('seyda',ref) for ref in exterior)
    # Every room reference the resident stage does not place is listed with its reason (left_out).
    import creature_residents
    creatures=[]
    for slug,cell in list(rooms.items()):
        refs,held=hold(cell['refs'],slug);left_out.extend(held)
        cell=dict(cell,refs=refs)
        cast.extend((slug,r) for r in cell['refs'] if not r.get('deleted') and r['type']=='NPC_'
                    and r['id'].casefold() not in exclude_residents)
        left_out.extend({'map':slug,'reference':r['number'],'id':r['id'],'type':r['type'],
                         'reason':'excluded by the town settings (resident exclusions)'}
                        for r in cell['refs'] if not r.get('deleted') and r['type']=='NPC_'
                        and r['id'].casefold() in exclude_residents)
        # Interior creatures (tools/creature_residents.py, INTERIOR-CREATURES-MISSING-41).
        placed_creatures,left=creature_residents.select(cell['refs'],kinds,slug)
        creatures.extend((slug,r) for r in placed_creatures);left_out.extend(left)
    identifiers=sorted({r['id'].casefold() for _,r in cast})
    tasks=[];models={}
    for identifier in identifiers:
        appearance=npc_items.attach_items(kinds,identifier,outfit(kinds,identifier))
        stats=first(kinds['NPC_'][identifier],'NPDT')
        appearance['initially_dead']=len(stats)==52 and struct.unpack_from('<h',stats,38)[0]<=0
        appearance['foot']=foot_class(kinds,appearance)
        if not appearance['initially_dead']:appearance['voices']=voices_of(topics,appearance)
        greeting={'text':'','voice':''} if appearance['initially_dead'] else greeting_fixture(topics,appearance)
        tasks.append((data,palette,appearance,greeting,ffmpeg,npc_lod.task_settings()))
    # one unit per resident through the unit cache (resident-bake, ROOM-RESIDENTS-NOT-CACHED-48): a resident baked
    # once is restored while its inputs are unchanged; each bakes into its own folder, installed in identifier order
    units=scene/'resident-work'
    done={};pending=[]
    # ROOM-RESIDENTS-KEY-SERIAL-49: the unit cache and the game data identity are opened once for the stage (once per
    # resident was 233 s on one core for 1,769 residents), and the restores (file reads, SHA-256 checks, writes, each
    # into its own folder) run on the stage's threads; the same keys and files, in the same order afterwards
    import time
    started=time.perf_counter()
    try:opened=open_residents() if tasks else (None,None)
    except (TypeError,ValueError,OSError):opened=(None,None)
    digests={}
    folders=[units/('a_'+hashlib.sha256(task[2]['id'].encode()).hexdigest()[:12]) for task in tasks]
    from concurrent.futures import ThreadPoolExecutor
    from build_parallel import live_jobs
    threads=max(1,min(live_jobs(resolve_jobs(jobs)),len(tasks) or 1))
    def restore(pair):
        return restore_resident(pair[0],pair[1],opened,digests)
    pairs=list(zip(tasks,folders))
    # the first one alone: it fills the shared digests (ffmpeg by content, the level list) the others then read
    restored_rows=[restore(pair) for pair in pairs[:1]]
    with ThreadPoolExecutor(threads) as restorers:
        restored_rows+=list(restorers.map(restore,pairs[1:]))
    for task,folder,(cache,inputs,record) in zip(tasks,folders,restored_rows):
        if record is not None:done[task[2]['id']]=(record,folder,False)
        else:pending.append((task,cache,inputs,folder))
    if tasks:print('Residents: %d looked up in the unit cache %s (%d found) in %.1f s on %d threads'%(
        len(tasks),RESIDENT_UNIT,len(tasks)-len(pending),time.perf_counter()-started,threads),flush=True)
    # the bakes left, on the shared pool as before (only the misses)
    for (task,cache,inputs,folder),baked in zip(pending,ordered_map(build_resident,[p[0] for p in pending],max(1,min(resolve_jobs(jobs),len(pending) or 1))) if pending else ()):
        identifier,record=publish_resident(folder,*baked)
        record=json_record(record)
        store_resident(cache,inputs,folder,identifier,record)
        done[identifier]=(record,folder,True)
    restored=0
    for identifier in [t[2]['id'] for t in tasks]:
        record,folder,made=done[identifier]
        install_resident(folder,scene/'id1',record)
        restored+=not made
        behavior=behavior_record(kinds['NPC_'][identifier],SCALE)
        record['behavior']=behavior;record['settings']=greeting_settings(kinds,behavior,SCALE)
        models[identifier]=record
        print('Resident ready:',identifier,'' if made else '(unit cache)',flush=True)
    shutil.rmtree(units,ignore_errors=True)
    if tasks:print(f'Residents: {len(tasks)} ({restored} from the unit cache {RESIDENT_UNIT}, {len(tasks)-restored} baked)',flush=True)
    # residents whose kit model did not fit the alias byte budget (build_resident, RESIDENT-ANIM-BYTE-BUDGET-48)
    fallbacks=anim_fallbacks(models)
    if fallbacks:
        print('Residents with a smaller animation level (alias byte budget): %d: %s'%(len(fallbacks),
              ', '.join('%s (%s)'%(f['id'],f['level']) for f in fallbacks)),flush=True)
    # Near/far models (tools/npc_lod.py): near files and the pairing manifest (NPC records only).
    lod_report=npc_lod.publish(scene/'id1',models,kinds)
    creature_ids=sorted({r['id'].casefold() for _,r in creatures})
    creature_tasks=[(data,palette,creature_residents.appearance(kinds,i)) for i in creature_ids]
    baked=set()
    for identifier,raw,record in (ordered_map(creature_residents.safe_bake,creature_tasks,
                                              max(1,min(resolve_jobs(jobs),len(creature_tasks))))
                                  if creature_tasks else ()):
        if raw is None:
            # 'all' mode: a model that does not bake leaves its references out, with the error
            left_out.extend({'map':slug,'reference':r['number'],'id':r['id'],'type':'CREA','reason':'model: '+record}
                            for slug,r in creatures if r['id'].casefold()==identifier)
            continue
        stem='a_'+hashlib.sha256(identifier.encode()).hexdigest()[:12]
        record.update(model='progs/'+stem+'.mdl',voice='')
        replace_bytes(scene/'id1'/record['model'],raw)
        behavior=behavior_record(kinds['CREA'][identifier],SCALE)
        # no creature greeting or dialogue yet: hello distance 0 (the entity never greets)
        record['behavior']=behavior;record['settings']={'distance':0,'reset_distance':0,'duration':0}
        models[identifier]=record;baked.add(identifier)
        print('Creature resident ready:',identifier,f"({record['frames']} frames, {record['triangles']} triangles, idle {record['idle']['group']})",flush=True)
    cast.extend((slug,r) for slug,r in creatures if r['id'].casefold() in baked)
    placed=[];talk=TalkGreetings(data,kinds,topics,cells)
    for slug in (['seyda'] if include_exterior else []) + list(rooms):
        path=scene/'id1/maps'/f'{slug}.bsp';raw=path.read_bytes();b=lumps(raw)
        # Seyda Neen's entities come from the scene entity list, not the carrier's lump (BUILD-SEYDA-ENTITY-BUS-48)
        if slug=='seyda':
            from seyda_entities import writer_lump
            b[0]=writer_lump(scene,raw)
        # Replace the three prototype residents, retaining scripted intro actors.
        entities=re.findall(r'\{[^{}]*\}',b[0].decode('cp1252'))
        entities=[e for e in entities if
                  not any('"classname" "'+kind+'"' in e for kind in ('aw_npc','aw_corpse'))
                  or '"aw_intro_role"' in e]
        for place,ref in cast:
            if place!=slug:continue
            if abs(ref['scale']-1)>1e-5:raise ValueError('Resident instance scale requires separate bake')
            record=models[ref['id'].casefold()];settings=record['settings']
            pos=[(v-(CENTRE[a] if slug=='seyda' and a<2 else 0))*SCALE for a,v in enumerate(ref['position'])]
            from actor_grounding import fields as grounding_fields
            from npc_anim import own_idle_fields
            fields={**grounding_fields(ref['id'],ref['number']),'classname':'aw_corpse' if record['appearance'].get('initially_dead') else 'aw_npc','aw_ref':ref['number'],'model':record['model'],
                    'origin':' '.join(f'{v:.5f}' for v in pos),
                    'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",
                    'netname':display_text(record['appearance']['name']),'aw_voice':record['voice'],
                    'aw_line':display_text(record['greeting']['text']),'aw_idle_step':record['step'],
                    'aw_hello_distance':settings['distance'],'aw_hello_reset':settings['reset_distance'],
                    'aw_greet_duration':settings['duration'],**own_idle_fields(record)}
            if fields['classname']=='aw_npc' and record['voice']:
                fields.update(talk.fields(ref['id'],talk.exterior_name(ref['position']) if slug=='seyda'
                                          else rooms[slug].get('name')))
            entities.append(entity(fields));placed.append({'map':slug,'reference':ref['number'],'id':ref['id'],'position':pos})
        # replaced whole: an earlier stage made this map (BUILD-POOL-READONLY-SCENE-WRITE-35)
        b[0]=('\n'.join(entities)+'\n\0').encode('cp1252');replace_bytes(path,pack_lumps(b))
        if slug=='seyda':
            replace_copy(path,scene/'seyda.bsp')
            from seyda_entities import publish as publish_entities;publish_entities(scene,path.read_bytes())
    # Town interiors (import_town.py) write their own door banks.
    doors=prepare_doors(data,scene) if doors else None
    left_out.sort(key=lambda r:(r['map'],r['reference']))
    if left_out:
        print(f'Resident stage: {len(left_out)} room references left out (reasons in {report_name} left_out)',flush=True)
    report={'rooms':reports,'cast':placed,'models':models,'doors':doors,'npc_lod':lod_report,**({'anim_fallback':fallbacks} if fallbacks else {}),
            'creatures':{'mode':creature_residents.mode(),'placed':sum(1 for _,r in creatures if r['id'].casefold() in baked)},
            'left_out':left_out,'talk_greetings':talk.record(),
            **({'start_disabled':{'mode':'original','held':sum(1 for r in left_out if 'disabled_by' in r)}}
               if start_disabled.mode()=='original' else {}),
            'scope':'original placed humanoid residents, blocking idle actors and bounded greetings; combat, services, schedules and small-item interactions remain separate systems'}
    (scene/report_name).write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data-files','scene','qbsp','vis','light'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ffmpeg',default='ffmpeg');add_jobs(p);add_vis_option(p);add_dressing_option(p);add_root_rule_arg(p)
    p.add_argument('--no-rooms',action='store_true',help='Quick test build (--exclude interiors): do not compile the rooms')
    add_room_form_option(p)
    npc_lod.add_converter_options(p)
    a=p.parse_args()
    apply_root_rule(a)
    apply_dressing_option(a);npc_lod.apply_options(a)
    import build_profile; build_profile.instrument('area')  # sub-stage timers (docs/BUILD_PROFILE.md)
    prepare(a.data_files,a.scene,a.qbsp,a.vis,a.light,a.ffmpeg,a.jobs,a.vis_mode,rooms=not a.no_rooms,
            room_form=a.room_form)
