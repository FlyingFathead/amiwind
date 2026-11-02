#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The player's body assembled from parts by equipment slot (docs/THIRD_PERSON.md "The assembled body";
PLAYER-GEAR-VISUAL-59).

The original builds a character's body from BODY part records per slot: the race's skin parts, the chosen head and
hair, and over them the parts of the clothing and armour worn, by priority (mwad.npc.outfit is the builder's rule,
read from OpenMW npcanimation.cpp's part priorities; nothing copied). The baked player body (prepare_player_view.py)
is one whole model per race and sex in the starting clothes; it stays selectable (aw_player_body_parts 0).

Here every part mesh becomes ONE model in the shared model table (engine rule ONE SHARED MODEL DATABASE: one model
per mesh, never per instance): a skeletal model (skeletal_actor's type 2: one rest frame plus the AWSB block) at the
unit actor scale on the shared humanoid table (progs/humanoid.awsk, beast races progs/humanoid_kna.awsk), so every
part, skinned (cuirass, shirt, gauntlet) or rigid (helmet, boot), is posed by the same bones at the same table frame;
the engine scales the whole body by the race's weight and height. The engine assembles the body from the recipe
table when the equipment changes and draws each part as an entity of the player's pose.

  id1/progs/parts/<2>/<10>.mdl   one skeletal model per (part mesh, slot, skeleton), unit scale, cropped skin (12
                                 hex of its key; 256 folders, FFS-DIRECTORY-HASH-32)
  id1/view/parts_<s><f>.txt      the player's groups on the table frames (npc_anim.table_groups; s = h human, k
                                 beast; f = m male, f female): the same group names as the baked body's layout
  id1/view/parts.txt             AWPP1, the recipe table (format in recipe_text below)
  id1/progs/humanoid*.awsk       the tables the parts name (the same bytes the resident stage writes)

Each part is a unit of the image unit cache ('player-parts'), keyed by the SHA-256 of its inputs; a build with the
same inputs takes it byte for byte. A part's triangles are capped by its slot (SLOT_CAP), so the whole body in the
starting clothes stays near the baked body's cost.
"""
import hashlib
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

RECIPE_FORMAT = 'AWPP1'
RECIPE_PATH = 'view/parts.txt'
PARTS_DIR = 'progs/parts/'
UNIT_CACHE = 'player-parts'
SKELETONS = {'meshes/base_anim.nif': 'h', 'meshes/base_animkna.nif': 'k'}
TABLES = {'h': 'progs/humanoid.awsk', 'k': 'progs/humanoid_kna.awsk'}
# Triangles per part by slot (mwad.npc.PART_NAMES): head 0, hair 1, neck 2, chest 3, groin 4/5, hands 6/7, wrists
# 8/9, shield 10, forearms 11/12, upper arms 13/14, feet 15/16, ankles 17/18, knees 19/20, upper legs 21/22,
# clavicles 23/24, tail 26. The starting clothes on a man come to about 520 (the baked body: 357 on 1,071 vertices).
SLOT_CAP = {0: 96, 1: 48, 2: 16, 3: 72, 4: 32, 5: 32, 6: 32, 7: 32, 8: 12, 9: 12, 10: 64, 11: 20, 12: 20, 13: 24,
            14: 24, 15: 24, 16: 24, 17: 12, 18: 12, 19: 16, 20: 16, 21: 32, 22: 32, 23: 20, 24: 20, 26: 32}
# Item ranks (mwad.npc.outfit): clothing robe 24, skirt 8, other clothing 2; armour 3. A higher rank wins a slot.
ROBE, SKIRT, SHOES = 4, 7, 3          # CLOT types
SHIELD, BOOTS = 8, 5                  # ARMO types
ROBE_COVERS = (3, 4, 5, 11, 12, 13, 14, 19, 20, 21, 22)
SKIRT_COVERS = (4, 21, 22)
HELMET = 0
# The player's groups (prepare_player_view's body: the 'move' profile, block, jump, land and the hand-to-hand ready
# sections), so the assembled body plays what the baked one plays.
PROFILE = 'move'


def part_dict(slot, body_id, mesh):
    """One part as mwad.npc.outfit writes it."""
    from mwad.npc import PART_NAMES
    return {'slot': slot, 'attach': 'Head' if slot == 1 else PART_NAMES[slot], 'filter': PART_NAMES[slot],
            'id': body_id, 'mesh': mesh}


def part_path(skeleton, part):
    """The part model's game path from 12 hex of (skeleton, slot, mesh): progs/parts/<2 hex>/<10 hex>.mdl, 31
    characters, file names of 14 (FFS 30); the first two hex name one of 256 folders, so no folder holds more than a
    few dozen parts (FFS-DIRECTORY-HASH-32: 72 hash chains a directory block)."""
    key = '%s|%d|%s' % (skeleton, part['slot'], part['mesh'].casefold().replace('\\', '/'))
    h = hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]
    return PARTS_DIR + h[:2] + '/' + h[2:] + '.mdl'


def part_hex(path):
    """The 12 hex a recipe names a part by (part_path's)."""
    rest = path[len(PARTS_DIR):-4]
    return rest[:2] + rest[3:]


def race_rows(kinds):
    """Per playable race and sex: skeleton, weight, height and the skin part per slot (mwad.npc.outfit's rule: the
    sex's own part, else the male one), the heads and hairs (record order, the first the default)."""
    from mwad.npc import BODY_SLOTS, first, text, unpack
    from prepare_player_view import playable_races
    rows = []
    for race in playable_races(kinds):
        raw = first(kinds['RACE'][race], 'RADT')
        height, fheight, weight, fweight, flags = unpack('<4fI', raw, 'RACE RADT', max(len(raw) - 20, 0))
        skeleton = 'meshes/base_animkna.nif' if flags & 2 else 'meshes/base_anim.nif'
        for female in (False, True):
            skin, rank, heads, hairs = {}, {}, [], []
            for identifier, body in sorted(kinds['BODY'].items()):
                bydt = first(body, 'BYDT')
                if len(bydt) != 4:
                    continue
                part, vampire, bflags, kind = bydt
                if kind or vampire or identifier.endswith('.1st') or text(body, 'FNAM').casefold() != race:
                    continue
                own = bool(bflags & 1) == female
                if part == 0 and own:
                    heads.append(identifier)
                elif part == 1 and own:
                    hairs.append(identifier)
                if bflags & 1 and not female:
                    continue
                r = 1 if own else .5
                for slot in BODY_SLOTS.get(part, ()):
                    if r >= rank.get(slot, 0):
                        skin[slot], rank[slot] = identifier, r
            rows.append({'race': race, 'female': female, 'skeleton': skeleton,
                         'weight': fweight if female else weight, 'height': fheight if female else height,
                         'skin': skin, 'heads': heads, 'hairs': hairs})
    return rows


def item_rows(kinds):
    """Every clothing and armour piece with body parts (shields are held items, drawn on the shield bone): its rank,
    and per slot its male and female BODY id (None: the slot is covered and shows nothing, e.g. a helmet's hair),
    with the original's implied cover of robes and skirts (mwad.npc.outfit)."""
    from mwad.npc import PART_NAMES, first, string, unpack
    out = []
    for kind in ('CLOT', 'ARMO'):
        for identifier, fields in sorted(kinds[kind].items()):
            typ = unpack('<i', first(fields, 'CTDT' if kind == 'CLOT' else 'AODT'), kind + ' type data')[0]
            if kind == 'ARMO' and typ == SHIELD:
                continue
            rank = (24 if typ == ROBE else 8 if typ == SKIRT else 2) if kind == 'CLOT' else 3
            slot, groups = None, {}
            for tag, data in fields:
                if tag == 'INDX':
                    if len(data) != 1 or data[0] >= len(PART_NAMES):
                        slot = None
                        continue
                    slot = data[0]
                    groups[slot] = [None, None]
                elif tag == 'BNAM' and slot is not None:
                    groups[slot][0] = string(data).casefold() or None
                elif tag == 'CNAM' and slot is not None and string(data):
                    groups[slot][1] = string(data).casefold()
            if kind == 'ARMO' and typ == HELMET:
                groups.setdefault(1, [None, None])
            if kind == 'CLOT' and typ == ROBE:
                for s in ROBE_COVERS:
                    groups.setdefault(s, [None, None])
            if kind == 'CLOT' and typ == SKIRT:
                for s in SKIRT_COVERS:
                    groups.setdefault(s, [None, None])
            groups = {s: v for s, v in groups.items() if s != 10}
            if groups:
                # beast races wear no boots or shoes (the original refuses them: their feet have no such parts)
                footwear = (kind == 'ARMO' and typ == BOOTS) or (kind == 'CLOT' and typ == SHOES)
                out.append({'id': identifier, 'kind': kind, 'rank': rank, 'slots': groups, 'beast': not footwear})
    return out


def needed_parts(kinds, races, items):
    """{(skeleton, slot, body id)}: every part a playable character can show."""
    need = set()
    skeletons = sorted({r['skeleton'] for r in races})
    for r in races:
        for slot, body in r['skin'].items():
            need.add((r['skeleton'], slot, body))
        for body in r['heads']:
            need.add((r['skeleton'], 0, body))
        for body in r['hairs']:
            need.add((r['skeleton'], 1, body))
    for item in items:
        for slot, (male, female) in item['slots'].items():
            for body in (male, female):
                if body and body in kinds['BODY']:
                    for s in skeletons:
                        if item.get('beast', True) or s != 'meshes/base_animkna.nif':
                            need.add((s, slot, body))
    return need


def recipe_text(races, items, models, anms, tables, bones):
    """The recipe table, ASCII lines (the engine's aw_player_parts.c):
      AWPP1
      T <s> <table path> <weapon bone> <shield bone>     per skeleton (s: h or k), the item bones' table indices
      A <s> <0|1> <anm path>                              the player's groups per skeleton and sex
      R <race id> <0|1> <s> <weight> <height>             a race and sex
      S <race id> <0|1> <slot> <model>                    its skin part per slot
      H <race id> <0|1> <body id> <model>                 a head it may choose (the first is the default)
      K <race id> <0|1> <body id> <model>                 a hair it may choose (the first is the default)
      I <item id> <rank> <slot>=<male>,<female> ...       an item's parts per slot; '-' none (covered), a model is
                                                          its 12 hex (progs/parts/<hex 1-2>/<hex 3-12>.mdl); human
                                                          and beast models as <h hex>/<k hex>, '-' for none
    Ids are written with a space as '|' (ids hold both 'ember hand' and 'ember_hand'); an id holding '|', '=', ','
    or a tab is refused, and so are two items, or two heads or hairs of one race and sex, that would read the same."""
    def word(s):
        if any(c in s for c in '\t\n=,|') or not s.isascii():
            raise ValueError('Recipe id not plain ASCII: ' + s)
        return s.replace(' ', '|')

    hexof = part_hex
    lines = [RECIPE_FORMAT]
    words = {}
    for item in items:
        if words.setdefault(word(item['id']), item['id']) != item['id']:
            raise ValueError('Two items share the recipe word %s' % word(item['id']))
    for s in sorted(tables):
        lines.append('T %s %s %d %d' % (s, tables[s], bones[s][0], bones[s][1]))
    for (s, female), path in sorted(anms.items()):
        lines.append('A %s %d %s' % (s, female, path))
    for r in races:
        s, f, race = SKELETONS[r['skeleton']], int(r['female']), word(r['race'])
        lines.append('R %s %d %s %.4f %.4f' % (race, f, s, r['weight'], r['height']))
        for slot, body in sorted(r['skin'].items()):
            if (r['skeleton'], slot, body) in models:
                lines.append('S %s %d %d %s' % (race, f, slot, hexof(models[(r['skeleton'], slot, body)])))
        for tag, slot, ids in (('H', 0, r['heads']), ('K', 1, r['hairs'])):
            if len({word(b) for b in ids}) != len(ids):
                raise ValueError('Two %s parts of %s read the same as recipe words' % (tag, r['race']))
            for body in ids:
                if (r['skeleton'], slot, body) in models:
                    lines.append('%s %s %d %s %s' % (tag, race, f, word(body), hexof(models[(r['skeleton'], slot, body)])))
    for item in items:
        words = []
        for slot, pair in sorted(item['slots'].items()):
            sides = []
            # a woman wears the male part where the item names no female one (mwad.npc.outfit)
            for body in (pair[0], pair[1] or pair[0]):
                if not body:
                    sides.append('-')
                    continue
                h = models.get(('meshes/base_anim.nif', slot, body))
                k = models.get(('meshes/base_animkna.nif', slot, body))
                sides.append('%s/%s' % (hexof(h) if h else '-', hexof(k) if k else '-'))
            words.append('%d=%s' % (slot, ','.join(sides)))
        lines.append('I %s %d %s' % (word(item['id']), item['rank'], ' '.join(words)))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- one part (a pool unit)

_rigs = {}


def _skeleton_of(assets):
    from npc_geometry import Skeleton

    def of(name):
        if name not in _rigs:
            _rigs[name] = Skeleton(assets, name)
        return _rigs[name]
    return of


def quotas_for(shapes, cap):
    """Per-shape triangle quotas of one part: its shapes share CAP by their source triangles, at least 1 each and
    never more than a shape has."""
    import numpy as np
    n = np.array([len(s['faces']) for s in shapes], int)
    if int(n.sum()) <= cap:
        return n
    q = np.maximum(1, np.floor(n * cap / n.sum()).astype(int))
    return np.minimum(q, n)


def bake_part(task):
    """Worker: one part model. task = (data, palette, skeleton, part, cap). Returns (path, mdl bytes, report)."""
    data, palette, skeleton, part, cap = task
    import prepare_player_view as ppv
    import skeletal_actor as sa
    from npc_geometry import assemble
    kinds, assets, _ = ppv._sources(data)
    of = _skeleton_of(assets)
    rig = of(skeleton)
    appearance = {'id': 'part ' + part['id'], 'skeleton': skeleton, 'female': False, 'weight': 1.0, 'height': 1.0,
                  'parts': [part]}
    table, report, _, path, _, _ = sa.game_table(str(data), appearance, of)
    times, _ = rig.idle_times(8)
    shapes, materials, textures = assemble(assets, appearance, rig, times)
    if not shapes:
        raise ValueError('Part %s (%s) has no drawn shape' % (part['id'], part['mesh']))
    sources = sa.export_actor(assets, appearance, rig)
    raw, facts = sa.skeletal_from_shapes(shapes, materials, textures, palette, sources, rig.pose(float(times[0])),
                                         [.25, .25, .25], table, report['bone_names'], table_path=path,
                                         budgets=(cap,), quotas=quotas_for(shapes, cap), head_detail='budget',
                                         body_skin_rows=480, parents=getattr(rig, 'parents', None))
    out = part_path(skeleton, part)
    return out, raw, {'id': part['id'], 'slot': part['slot'], 'mesh': part['mesh'], 'skeleton': skeleton,
                      'model': out, 'bytes': len(raw), 'faces': facts['faces'], 'vertices': facts['vertices'],
                      'sha256': hashlib.sha256(raw).hexdigest()}


def player_layout(data, skeleton, female):
    """The player's groups on the table frames for one skeleton and sex: (layout text, table frames)."""
    import npc_anim
    import prepare_player_view as ppv
    import skeletal_actor as sa
    kinds, assets, _ = ppv._sources(data)
    of = _skeleton_of(assets)
    appearance = {'skeleton': skeleton, 'female': female, 'weight': 1.0, 'height': 1.0, 'parts': []}
    table_bytes, report, table, _, rig, over = sa.game_table(str(data), appearance, of)
    path = sa.table_view(sa.table_choice(appearance)[2], list(table['groups']))
    profile = list(npc_anim.profiles()[PROFILE]) + [list(g) for g in ppv.BODY_EXTRA + ppv.BODY_READY]
    _, groups = npc_anim.plan(rig, profile, over, 1.0, player_block_hit=True)
    kit = npc_anim.table_groups(table, groups, None, report['times'], prefix=sa.table_prefixes(path))
    return npc_anim.layout(kit), table['frames'], table_bytes, report['bone_names']


# ---------------------------------------------------------------- the stage

def unit_inputs(task):
    data, palette, skeleton, part, cap = task
    return {'entry': {'name': 'part %s %d %s' % (SKELETONS[skeleton], part['slot'], part['id'])},
            'skeleton': skeleton, 'part': part, 'cap': cap, 'palette_sha256': hashlib.sha256(palette).hexdigest()}


def _unit_cache():
    from pass_cache import UnitCache, game_data_digest
    game = game_data_digest()
    if game is None:
        return None
    import skeletal_actor
    import npc_geometry
    return UnitCache.open(UNIT_CACHE, {'game_data': game}, __file__, skeletal_actor.__file__, npc_geometry.__file__)


def write_same(path, raw):
    """Write RAW at PATH; a file already there must hold the same bytes (the tables are written by several stages)."""
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('%s is already in the image with other bytes' % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def prepare(data, id1, palette, jobs=None, log=print):
    """Bake the parts library, the layouts and the recipe table into ID1. Returns the report."""
    import prepare_player_view as ppv
    from build_parallel import stage_pool
    from pass_cache import forced
    started = time.monotonic()
    kinds, assets, _ = ppv._sources(data)
    races = race_rows(kinds)
    items = item_rows(kinds)
    need = needed_parts(kinds, races, items)
    tasks = []
    for skeleton, slot, body in sorted(need):
        record = kinds['BODY'].get(body)
        if record is None:
            continue
        from mwad.npc import text
        mesh = text(record, 'MODL')
        if not mesh:
            continue
        tasks.append((str(data), palette, skeleton, part_dict(slot, body, mesh), SLOT_CAP.get(slot, 32)))
    # one model per (skeleton, slot, mesh): parts that name the same mesh in the same slot share it
    unique = {}
    for t in tasks:
        unique.setdefault(part_path(t[2], t[3]), t)
    log('=== PHASE 1/3: player parts: %d part uses, %d models to bake or reuse ===' % (len(tasks), len(unique)))
    cache = _unit_cache()
    todo, results, failed = [], {}, []
    for path, t in unique.items():
        found = None
        if cache is not None and not forced(UNIT_CACHE, unit_inputs(t)['entry']['name']):
            found = cache.load_unit(unit_inputs(t))
        if found is not None:
            row, files = found
            results[path] = (files['0'], row['report'])
        else:
            todo.append(t)
    reused = len(results)
    if todo:
        from build_costs import costed_map
        from build_jobs import resolve_jobs
        workers = max(1, min(resolve_jobs(jobs), len(todo)))
        names = [unit_inputs(t)['entry']['name'] for t in todo]
        with stage_pool(jobs, 'player parts'):
            made = costed_map('player-parts', _safe_bake, todo, names, workers, fallback=lambda name: 1.0)
            done = 0
            for t, result in zip(todo, made):
                done += 1
                if done % 100 == 0 or done == len(todo):
                    log('player parts: %d / %d baked' % (done, len(todo)), flush=True)
                if isinstance(result, str):
                    failed.append(result)
                    continue
                path, raw, report = result
                results[path] = (raw, report)
                if cache is not None:
                    cache.store_files(unit_inputs(t), {'report': report}, {'0': raw})
    log('=== PHASE 2/3: player parts: layouts and tables ===', flush=True)
    models = {}
    for path, t in unique.items():
        if path in results:
            write_same(Path(id1) / path, results[path][0])
    for t in tasks:
        path = part_path(t[2], t[3])
        if path in results:
            models[(t[2], t[3]['slot'], t[3]['id'])] = path
    anms, tables, bones = {}, {}, {}
    for skeleton in sorted({r['skeleton'] for r in races}):
        s = SKELETONS[skeleton]
        for female in (0, 1):
            if skeleton == 'meshes/base_animkna.nif' and female:
                anms[(s, 1)] = anms[(s, 0)]
                continue
            layout, frames, table_bytes, bone_names = player_layout(data, skeleton, bool(female))
            # beside the recipe and not named .anm: every <model>.anm in the image belongs to a model of its name
            # (tools/actor_frames.py, the payload preflight); these belong to every part
            path = 'view/parts_' + s + ('f' if female else 'm') + '.txt'
            (Path(id1) / 'view').mkdir(parents=True, exist_ok=True)
            (Path(id1) / path).write_text(layout + '\n', encoding='ascii', newline='\n')
            anms[(s, female)] = path
            tables[s] = TABLES[s]
            write_same(Path(id1) / TABLES[s], table_bytes)
            names = [n.casefold() for n in bone_names]
            bones[s] = (names.index('weapon bone') if 'weapon bone' in names else -1,
                        names.index('shield bone') if 'shield bone' in names else -1)
    log('=== PHASE 3/3: player parts: the recipe table ===', flush=True)
    text = recipe_text(races, items, models, anms, tables, bones)
    (Path(id1) / RECIPE_PATH).parent.mkdir(parents=True, exist_ok=True)
    (Path(id1) / RECIPE_PATH).write_text(text, encoding='ascii', newline='\n')
    sizes = [r[1]['bytes'] for r in results.values()]
    faces = [r[1]['faces'] for r in results.values()]
    report = {'models': len(results), 'reused': reused, 'made': len(results) - reused, 'failed': failed,
              'bytes': sum(sizes), 'faces_median': sorted(faces)[len(faces) // 2] if faces else 0,
              'recipe_sha256': hashlib.sha256(text.encode('ascii')).hexdigest(), 'items': len(items),
              'races': len(races), 'seconds': round(time.monotonic() - started, 1)}
    log('Player parts: %d models (%d reused, %d made, %d failed), %.1f MB, %d items, %.1f s' % (
        report['models'], reused, report['made'], len(failed), report['bytes'] / 1e6, len(items), report['seconds']),
        flush=True)
    return report


def _safe_bake(task):
    """bake_part; a part that cannot be baked is named and left out (the slot then shows the skin under it, or
    nothing), never stopping the image step: 'FAILED <name>: <error>'."""
    try:
        return bake_part(task)
    except Exception as error:  # noqa: BLE001  (named in the report; the slot falls back)
        return 'FAILED %s: %s: %s' % (unit_inputs(task)['entry']['name'], type(error).__name__, error)
