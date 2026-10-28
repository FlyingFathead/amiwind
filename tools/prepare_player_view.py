#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The player's view data for the image (docs/THIRD_PERSON.md): the game settings the camera and the
death scene read, and the player's body for the third-person view, one per playable race and sex.

  id1/view/settings.txt   AWVS1, then 'NAME VALUE' lines from the owned master's game settings:
                          fVanityDelay (seconds idle before the vanity orbit), sLoadLastSaveMsg (the
                          death prompt, '%s' = the save; newlines written as \\n), sYes, sNo
  id1/view/bodies.txt     AWPB1, then RACE<TAB>0|1<TAB>MODEL lines (1 = female)
  id1/progs/body/*.mdl    the bodies; *.anm beside each: the animation kit's layout (tools/npc_anim.py)
  id1/progs/body/*_t.mdl torch-pose body; *_h.mdl original held torch; both have matching *.anm;
  id1/progs/body/*_t.awt frame-aligned emitter points
  id1/progs/body/*_w.mdl water-only body; *_w.anm original swimidle/swim motion
  id1/progs/body/*_i.mdl ten static inventory poses; *_i.tag matching melee/shield attachments

The body (a stand-in for the full player appearance): the original's new-game player record ('player' in
Morrowind.esm: a common shirt, pants and shoes) worn by the race's own skin parts, with the race and sex's
first head and hair (by record ID), baked through the same resident pipeline as the town NPCs
(npc_geometry.assemble/bake, npc_anim.plan, the 'move' profile plus block: idle, walk, run, hit, death, block from the
skeleton's own text keys; female humans take base_anim_female.nif's overrides; beast races their own
skeleton). Jump takeoff/air hold and landing use the original jump text keys.
Bare-hand ready idle/walk/run/jump use the corresponding original hh sections;
equip/lower and punch are baked over independently advancing movement poses.
A separate torch-held body overlays the original left-clavicle torch pose on locomotion.
A separate water body carries the original idle-swim and forward-swim groups without reducing their frames.
Not yet: the character's chosen head and hair and the inventory's worn equipment.

The 80 bakes (body, torch body, water body, inventory poses per race and sex) run in one worker pool for the whole
step, longest first, and each is kept in the image unit cache (tools/pass_cache.py UnitCache 'player-view') by the
SHA-256 of its inputs: the game data (the build's input lock), the palette, race and sex, the body fields a torch or
water body reads, the code and the AMIWIND_* settings it reads. A build with the same inputs takes them from there
byte for byte (BUILD-PLAYER-VIEW-UNDERUSED-48).

Build switches (tools/build.py): --player-body on|off (default on; off bakes no body: third person is then
refused in game) and --death-retry on|off (default on; off writes aw_death_retry 0 into default-game.cfg).
"""
import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

SETTINGS_FORMAT = 'AWVS1'
BODIES_FORMAT = 'AWPB1'
NUMBERS = ('fVanityDelay',)
STRINGS = ('sLoadLastSaveMsg', 'sYes', 'sNo', 'sNotifyMessage2')   # sNotifyMessage2: no rest/wait, enemies nearby
PLAYER_RECORD = 'player'
BODY_PROFILE = 'move'
# Plus the shield block (COMBAT-BLOCKING-36): base_anim 'shield: block start..stop', played while the player
# guards (hold to block, an AmiWind extension) and after a blocked blow (OpenMW refreshHitRecoilAnims).
BODY_EXTRA = (('block', 5), ('jump', 4), ('land', 4))
BODY_READY = (('ready', 8), ('readywalk', 8), ('readyrun', 6), ('readyjump', 4), ('readyland', 4))
BODY_SWIM = (('idle', 8), ('swimidle', 8), ('swim', 8), ('death', 2))
BODY_DIR = 'progs/body/'
BUDGETS = (480, 384, 320, 256)
TORCH_FORMAT = b'AWBT'
TORCH_FRAME_MAX = 256
OPTIONS = {'player_body': '--player-body', 'death_retry': '--death-retry'}
DEATH_RETRY_OFF_LINES = (b'// --death-retry off: no quick retry after a lost fight (the original choices only)\n'
                         b'aw_death_retry 0\n')


# ---------------------------------------------------------------- build switches

def add_options(parser):
    parser.add_argument('--player-body', dest='player_body', choices=('on', 'off'), default=None,
                        help="Bake the player's body (one per playable race and sex) for the third-person view, "
                             'the vanity orbit and the death scene. Default: on. off: no body; the game then stays '
                             'in first person (docs/THIRD_PERSON.md)')
    parser.add_argument('--death-retry', dest='death_retry', choices=('on', 'off'), default=None,
                        help='After a lost fight the death prompt also offers "Retry fight" (an AmiWind extension; '
                             'the original offers the last save or the main menu). Default: on. off writes '
                             'aw_death_retry 0 into the game defaults')


def configure(args):
    """{'player_body', 'death_retry', 'source'}: the switches resolved before any work (the receipt keeps it)."""
    record = {}
    given = []
    for key, option in OPTIONS.items():
        value = getattr(args, key, None)
        record[key] = (value or 'on') == 'on'
        if value:
            given.append(option + ' ' + value)
    record['source'] = ', '.join(given) or 'default'
    return record


def image_arguments(record):
    """The image step's extra arguments: nothing when both are on (the default), so a default build's image
    command does not change; --no-player-body / --no-death-retry when off."""
    if not record:
        return []
    return (['--no-player-body'] if not record.get('player_body', True) else []) + \
           (['--no-death-retry'] if not record.get('death_retry', True) else [])


def stage_death_retry(no_retry, id1):
    """--death-retry off: aw_death_retry 0 at the end of default-game.cfg. Returns the record."""
    if not no_retry:
        return {'on': True}
    path = Path(id1) / 'default-game.cfg'
    raw = path.read_bytes() if path.exists() else b''
    if raw and not raw.endswith(b'\n'):
        raw += b'\n'
    path.write_bytes(raw + DEATH_RETRY_OFF_LINES)
    return {'on': False, 'config': 'id1/default-game.cfg', 'line': 'aw_death_retry 0'}


# ---------------------------------------------------------------- game settings

def _gmst(kinds, name):
    from mwad.npc import first
    fields = kinds['GMST'].get(name.casefold())
    if not fields:
        raise ValueError('Game setting missing from the master: ' + name)
    for tag in ('FLTV', 'INTV', 'STRV'):
        raw = first(fields, tag, None)
        if raw is None:
            continue
        if tag == 'FLTV':
            return struct.unpack('<f', raw)[0]
        if tag == 'INTV':
            return struct.unpack('<i', raw)[0]
        return raw.rstrip(b'\0').decode('cp1252')
    raise ValueError('Game setting without a value: ' + name)


def settings_text(kinds):
    """view/settings.txt from the master's game settings (never hard-coded values)."""
    lines = [SETTINGS_FORMAT]
    for name in NUMBERS:
        value = float(_gmst(kinds, name))
        if not 0 < value <= 3600:
            raise ValueError(f'{name} out of range: {value}')
        lines.append(f'{name} {value:.6g}')
    for name in STRINGS:
        value = _gmst(kinds, name)
        if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 and c != '\n' for c in value):
            raise ValueError('Unsupported text in game setting ' + name)
        if name == 'sLoadLastSaveMsg' and (value.count('%') != 1 or '%s' not in value):
            raise ValueError('sLoadLastSaveMsg must hold exactly one %s')
        value = value.replace('\n', '\\n')
        if len(value) > 150 or not value.isascii():
            raise ValueError('Game setting text too long or not ASCII: ' + name)
        lines.append(f'{name} {value}')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- bodies

def playable_races(kinds):
    from mwad.npc import first
    out = []
    for name, record in kinds['RACE'].items():
        radt = first(record, 'RADT')
        if len(radt) >= 20 and struct.unpack_from('<I', radt, len(radt) - 4)[0] & 1:
            out.append(name)
    return sorted(out)


def body_path(race, female):
    slug = race.casefold().replace(' ', '_')
    if not slug.replace('_', '').isalnum() or not slug.isascii() or len(slug) > 20:
        raise ValueError('Race ID cannot form a body model name: ' + race)
    return BODY_DIR + slug + ('_f' if female else '_m') + '.mdl'


def first_part(kinds, race, female, part):
    """The race and sex's first head (part 0) or hair (1) skin part by record ID (the original's chargen
    lists them in record order; a deterministic stand-in for the character's own choice)."""
    from mwad.npc import first, text
    found = []
    for identifier, body in kinds['BODY'].items():
        raw = first(body, 'BYDT')
        if len(raw) != 4:
            continue
        kind_part, vampire, flags, kind = raw
        if kind_part != part or vampire or kind or text(body, 'FNAM').casefold() != race:
            continue
        if bool(flags & 1) == female:
            found.append(identifier)
    return sorted(found)[0] if found else None


def body_appearance(kinds, race, female):
    """The new-game player record ('player') as the given race and sex: its clothes over the race's skin."""
    from mwad.npc import outfit
    source = kinds['NPC_'].get(PLAYER_RECORD)
    if source is None:
        raise ValueError('The master has no player record')
    head, hair = first_part(kinds, race, female, 0), first_part(kinds, race, female, 1)
    record = []
    for tag, data in source:
        if tag == 'RNAM':
            data = race.encode('cp1252') + b'\0'
        elif tag == 'FLAG':
            data = struct.pack('<I', (struct.unpack('<I', data)[0] & ~1) | (1 if female else 0))
        elif tag == 'BNAM':
            data = (head or '').encode('cp1252') + b'\0'
        elif tag == 'KNAM':
            data = (hair or '').encode('cp1252') + b'\0'
        record.append((tag, data))
    key = 'aw_player_body'
    view = dict(kinds)
    view['NPC_'] = dict(kinds['NPC_'])
    view['NPC_'][key] = record
    appearance = outfit(view, key)
    appearance.update(id='player body ' + race + (' female' if female else ' male'), head=head, hair=hair)
    return appearance


_cache = {}


def _sources(data):
    key = str(data)
    if key not in _cache:
        from mwad.audit import BSA
        from mwad.npc import load_master
        from mwad.paths import child_ci
        from npc_geometry import Assets
        kinds, _, _ = load_master(child_ci(Path(data), 'Morrowind.esm'))
        _cache[key] = (kinds, Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa'))), {})
    return _cache[key]


def _fit_body(identifier, shapes, materials, textures, palette, groups):
    """_fit_body_search with the configured head reducer; when the boundary-locked head reducer leaves no body
    that fits (it keeps every rim vertex), the search runs again with the previous head reducer and the fallback
    is logged, as the NPC bake does (npc_geometry._retry_head_reducer; v0.0.44-dev1 build: the image step
    stopped on the Argonian female player body, NPC-HEAD-DECIMATION-33)."""
    import os
    from mesh_geometry_env import NPC_HEAD_REDUCER_VARIABLE, npc_head_reducer
    from npc_geometry import hair_share
    try:
        return _fit_body_search(identifier, shapes, materials, textures, palette, groups)
    except ValueError as error:
        # the player body's byte budget holds every gait frame: with the whole hair or the head's share for the hair
        # (NPC-HAIR-BACK-MISSING-53) no body fitted (the breton female: 1,359 vertices at 480, over the byte budget):
        # the search again with the hair's previous share (v0.0.53, 'plain'), which fits
        if hair_share() != 'plain' and 'no body fits the existing budgets' in str(error):
            print('player body %s: no fit with the %s hair share; this body uses the previous share for its hair'
                  % (identifier, hair_share()), flush=True)
            saved_share = os.environ.get('AMIWIND_NPC_HAIR_SHARE')
            os.environ['AMIWIND_NPC_HAIR_SHARE'] = 'plain'
            try:
                return _fit_body(identifier, shapes, materials, textures, palette, groups)
            finally:
                if saved_share is None:
                    os.environ.pop('AMIWIND_NPC_HAIR_SHARE', None)
                else:
                    os.environ['AMIWIND_NPC_HAIR_SHARE'] = saved_share

        if npc_head_reducer() != 'locked' or 'no body fits the existing budgets' not in str(error):
            raise
        print('player body %s: no fit with the locked head reducer; this body uses the previous head reducer'
              % identifier, flush=True)
        saved = os.environ.get(NPC_HEAD_REDUCER_VARIABLE)
        os.environ[NPC_HEAD_REDUCER_VARIABLE] = 'default'
        try:
            return _fit_body_search(identifier, shapes, materials, textures, palette, groups)
        finally:
            if saved is None:
                os.environ.pop(NPC_HEAD_REDUCER_VARIABLE, None)
            else:
                os.environ[NPC_HEAD_REDUCER_VARIABLE] = saved


def _fit_body_search(identifier, shapes, materials, textures, palette, groups):
    """Keep the first model that fits full normal and ready gait plus actions.

    Search for a full-frame fit before accepting a reduced animation. If no
    full fit exists, keep the valid candidate with most animation samples;
    equal counts retain the earlier mesh. Every fallback passes the same leg
    section check against the untouched budget-480 reference.
    """
    import npc_anim
    from npc_geometry import AliasOverflow, bake, player_leg_section_ok
    failures = []
    reference = None
    best = None
    full_count = sum(g['count'] for g in groups)
    for rows, contour in ((96, 0), (80, 0), (80, 1), (80, 2)):
        for budget in BUDGETS:
            try:
                face_parts = []
                frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget,
                                              reference_frames=8, body_skin_rows=rows,
                                              body_leg_contour=contour, face_parts=face_parts)
                if len(face_parts) != len(faces):
                    raise ValueError('Player body bake omitted face-part labels')
                if reference is None:
                    reference = (frames[0], faces, face_parts)
                elif not player_leg_section_ok(reference[0], reference[1], frames[0], faces,
                                               reference_parts=reference[2],candidate_parts=face_parts):
                    raise AliasOverflow('Player visible leg silhouette narrowed versus budget-480 body')
                nv, nt, (sw, sh) = frames.shape[1], len(faces), skin.size
                fitted, index = npc_anim.fit(groups, nv, nt, sw, sh)
            except npc_anim.AliasBudgetError as error:
                mode='thigh' if contour==2 else 'knee' if contour else 'plain'
                failures.append('%d/%d/%s: %s (%d vertices, %d triangles)' %
                                (budget,rows,mode,error,nv,nt))
                continue
            except AliasOverflow as error:
                mode='thigh' if contour==2 else 'knee' if contour else 'plain'
                failures.append('%d/%d/%s: %s' % (budget,rows,mode,error))
                continue
            except ValueError as error:
                raise ValueError(identifier + ': ' + str(error)) from error
            candidate = (budget, frames, faces, uv, skin, fitted, index)
            if len(index) == full_count:
                return candidate
            if best is None or len(index) > len(best[-1]):
                best = candidate
    if best is not None:
        return best
    raise ValueError(identifier + ': no body fits the existing budgets (' + '; '.join(failures) + ')')


def bake_body(task):
    """Worker: one race/sex body. (path, model bytes, layout, report)."""
    data, palette, race, female = task
    import npc_anim
    from npc_geometry import Skeleton, assemble, animated_mdl
    kinds, assets, rigs = _sources(data)
    appearance = body_appearance(kinds, race, female)
    if appearance['skeleton'] not in rigs:
        rigs[appearance['skeleton']] = Skeleton(assets, appearance['skeleton'])
    skeleton = rigs[appearance['skeleton']]
    female_rig = None
    if female and appearance['skeleton'] == 'meshes/base_anim.nif':
        if npc_anim.FEMALE_SKELETON not in rigs:
            rigs[npc_anim.FEMALE_SKELETON] = Skeleton(assets, npc_anim.FEMALE_SKELETON)
        female_rig = rigs[npc_anim.FEMALE_SKELETON]
    profile = list(npc_anim.profiles()[BODY_PROFILE]) + [list(g) for g in BODY_EXTRA + BODY_READY]
    kit, groups = npc_anim.plan(skeleton, profile, female_rig, appearance.get('weight', 1.), player_block_hit=True)
    required = set(npc_anim.AIR_GROUPS) | {name for name, _ in BODY_READY}
    missing = [g['name'] for g in groups if g['name'] in required and g['source'] == 'idle']
    if missing:
        raise ValueError(appearance['id'] + ': missing original player sections: ' + ', '.join(missing))
    kit, groups = npc_anim.player_layers(kit, groups, compact=True)
    times = npc_anim.idle_compatible_times(groups)
    shapes, materials, textures = assemble(assets, appearance, kit, times)
    # Keep the first geometry budget that fits: normal and ready walk/run keep
    # their full authored frame counts. Temporary arm actions use small grids.
    budget, frames, faces, uv, skin, fitted, index = _fit_body(
        appearance['id'], shapes, materials, textures, palette, groups)
    nv, nt = frames.shape[1], len(faces)
    # Alias frame labels are diagnostic only; ANM owns full group names and
    # indices. Reserve two of the format's 15 ASCII bytes for the frame index.
    names = [g['name'][:13] + '%02d' % i for g in fitted for i in range(g['count'])]
    raw = animated_mdl(frames[index], faces, uv, skin, names=names)
    layout = npc_anim.player_layout(fitted)
    from npc_items import bone_tags, tag_text
    all_tags = bone_tags(kit, times, appearance, {'weapon': True, 'shield': True})
    item_tags = tag_text([all_tags[int(i)] for i in index], {})
    if len(index) != len(frames[index]):
        raise ValueError('Player equipment tags changed body frame indexing')
    path = body_path(race, female)
    report = {'race': race, 'female': female, 'model': path, 'bytes': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(), 'frames': len(index), 'triangles': nt, 'vertices': nv,
              'budget': budget, 'skeleton': appearance['skeleton'], 'head': appearance.get('head'),
              'hair': appearance.get('hair'), 'parts': [p['id'] for p in appearance['parts']],
              'groups': {g['name']: g['count'] for g in fitted}, 'layout': layout,
              'group_sources': {g['name']: g['source'] for g in fitted},
              '_item_tags': item_tags, 'item_tags_sha256': hashlib.sha256(item_tags.encode('ascii')).hexdigest()}
    return path, raw, layout, report


def torch_paths(base):
    """Derive the torch assets from an unchanged AWPB1 body path."""
    if not base.startswith(BODY_DIR) or not base.endswith('.mdl'):
        raise ValueError('Invalid player body path for torch companion')
    stem = base[:-4]
    return stem + '_t.mdl', stem + '_h.mdl', stem + '_t.awt'


def swim_path(base):
    """Derive the water-only body from an unchanged AWPB1 body path."""
    if not base.startswith(BODY_DIR) or not base.endswith('.mdl'):
        raise ValueError('Invalid player body path for water companion')
    return base[:-4] + '_w.mdl'


def torch_emitters(positions):
    """AWBT: BE frame count and one signed 16.16 XYZ emitter per frame."""
    import numpy as np
    points = np.asarray(positions, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 3 or
            not 1 <= len(points) <= TORCH_FRAME_MAX or not np.isfinite(points).all() or
            np.max(np.abs(points)) > 128):
        raise ValueError('Player torch emitter count or coordinates outside bounds')
    return struct.pack('>4sHH', TORCH_FORMAT, len(points), 0) + np.rint(points * 65536).astype('>i4').tobytes()


class PlayerTorchLayer:
    """Original left-clavicle torch hold over each ordinary body motion pose."""
    def __init__(self, base, normal, count):
        import numpy as np
        from npc_anim import BoneLayer
        self.N, self.normal = base.N, normal
        self.times = np.arange(count)
        start, stop = (base.events.get('torch: ' + key) for key in ('start', 'stop'))
        if start is None or stop is None or not np.isfinite((start, stop)).all() or not 0 < stop-start < 60:
            raise ValueError('Missing or invalid original third-person torch section')
        # The guard companion samples this same authored torch range. Its last
        # eighth is a stable grip; locomotion still supplies the moving legs.
        self.torch_time = start + .875*(stop-start)
        self.layer = BoneLayer(base, ('bip01 l clavicle',))

    def pose(self, index):
        i = int(index)
        if i != index or not 0 <= i < len(self.times):
            raise ValueError('Invalid player torch frame')
        return self.layer.pose(self.normal.pose(i), self.torch_time)


class SelectedTorchLayer:
    """The same torch pose restricted to the fitted body's ordered frames."""
    def __init__(self, layer, index):
        import numpy as np
        self.N, self.layer, self.index = layer.N, layer, tuple(index)
        self.times = np.arange(len(index))

    def pose(self, index):
        i = int(index)
        if i != index or not 0 <= i < len(self.index):
            raise ValueError('Invalid selected player torch frame')
        return self.layer.pose(self.index[i])


def bake_torch_body(task):
    """Worker: frame-aligned body and original Shield Bone torch companions."""
    data, palette, race, female, base_row = task
    import npc_anim
    from npc_geometry import AliasOverflow, Skeleton, assemble, bake, animated_mdl, player_leg_section_ok
    from prepare_guard_torches import _equipment, _source_records
    from mwad.npc import text
    from mwad.paths import child_ci
    kinds, assets, rigs = _sources(data)
    appearance = body_appearance(kinds, race, female)
    if appearance['skeleton'] not in rigs:
        rigs[appearance['skeleton']] = Skeleton(assets, appearance['skeleton'])
    skeleton = rigs[appearance['skeleton']]
    female_rig = None
    if female and appearance['skeleton'] == 'meshes/base_anim.nif':
        if npc_anim.FEMALE_SKELETON not in rigs:
            rigs[npc_anim.FEMALE_SKELETON] = Skeleton(assets, npc_anim.FEMALE_SKELETON)
        female_rig = rigs[npc_anim.FEMALE_SKELETON]
    profile = list(npc_anim.profiles()[BODY_PROFILE]) + [list(g) for g in BODY_EXTRA + BODY_READY]
    kit, groups = npc_anim.plan(skeleton, profile, female_rig, appearance.get('weight', 1.))
    keep = {g['name']: base_row['groups'][g['name']] for g in groups}
    fitted, index = npc_anim.select(groups, keep)
    if len(fitted) != len(groups) or any(g['count'] != keep[g['name']] for g in fitted):
        raise ValueError('Player torch motion groups differ from base body')
    layer = PlayerTorchLayer(skeleton, kit, sum(g['count'] for g in groups))
    shapes, materials, textures = assemble(assets, appearance, layer, npc_anim.idle_compatible_times(groups))
    reference = fit = None
    for rows, contour in ((96, 0), (80, 0), (80, 1), (80, 2)):
        for budget in BUDGETS:
            parts = []
            try:
                frames, faces, uv, skin = bake(shapes, materials, textures, palette,
                    budget=budget, reference_frames=8, body_skin_rows=rows,
                    body_leg_contour=contour, face_parts=parts)
                if reference is None:
                    reference = (frames[0], faces, parts)
                elif not player_leg_section_ok(reference[0], reference[1], frames[0], faces,
                                              reference_parts=reference[2], candidate_parts=parts):
                    raise AliasOverflow('Player torch visible leg silhouette narrowed')
                if npc_anim.alias_bytes(len(index), frames.shape[1], len(faces), *skin.size) > npc_anim.ALIAS_BYTE_BUDGET:
                    continue
                fit = (budget, rows, contour, frames, faces, uv, skin)
                break
            except AliasOverflow:
                continue
        if fit is not None:
            break
    if fit is None:
        raise ValueError(appearance['id'] + ': original torch pose body exceeds alias/leg budget')
    budget, rows, contour, frames, faces, uv, skin = fit
    names = [g['name'][:13] + '%02d' % i for g in fitted for i in range(g['count'])]
    held_body = animated_mdl(frames[index], faces, uv, skin, names=names)
    if len(held_body) > npc_anim.ALIAS_BYTE_BUDGET:
        raise ValueError('Player torch body exceeded alias byte budget')
    lights = _source_records(child_ci(Path(data), 'Morrowind.esm'))
    mesh = text(lights['torch'], 'MODL')
    # The guard converter preserves the original 238 visible torch triangles,
    # the Shield Bone rigid attachment and the flame emitter geometry.
    selected_layer = SelectedTorchLayer(layer, index)
    held_item, emitters = _equipment(assets, appearance, selected_layer, None, mesh, palette)
    if len(held_item) > npc_anim.ALIAS_BYTE_BUDGET:
        raise ValueError('Player held torch exceeded alias byte budget')
    metadata = torch_emitters(emitters)
    body_path_, held_path, metadata_path = torch_paths(base_row['model'])
    layout = npc_anim.player_layout(fitted)
    report = {'race': race, 'female': female, 'base_model': base_row['model'],
              'body_model': body_path_, 'held_model': held_path, 'metadata': metadata_path,
              'frames': len(index), 'body_bytes': len(held_body), 'held_bytes': len(held_item),
              'triangles': len(faces), 'budget': budget, 'skin_rows': rows, 'contour': contour,
              'source_torch_triangles': 238,
              'source_torch_key_seconds': [float(skeleton.events['torch: start']),
                                           float(skeleton.events['torch: stop'])],
              'pose': 'original left-clavicle torch hold over normal/ready movement',
              'groups': {g['name']: g['count'] for g in fitted},
              'body_sha256': hashlib.sha256(held_body).hexdigest(),
              'held_sha256': hashlib.sha256(held_item).hexdigest(),
              'metadata_sha256': hashlib.sha256(metadata).hexdigest()}
    return body_path_, held_body, layout, held_path, held_item, metadata_path, metadata, report


def bake_swim_body(task):
    """Worker: original full swim loops in a separate bounded water-only alias."""
    data, palette, race, female, base_row = task
    import npc_anim
    from npc_geometry import AliasOverflow, Skeleton, assemble, bake, animated_mdl, player_leg_section_ok
    kinds, assets, rigs = _sources(data)
    appearance = body_appearance(kinds, race, female)
    if appearance['skeleton'] not in rigs:
        rigs[appearance['skeleton']] = Skeleton(assets, appearance['skeleton'])
    skeleton = rigs[appearance['skeleton']]
    female_rig = None
    if female and appearance['skeleton'] == 'meshes/base_anim.nif':
        if npc_anim.FEMALE_SKELETON not in rigs:
            rigs[npc_anim.FEMALE_SKELETON] = Skeleton(assets, npc_anim.FEMALE_SKELETON)
        female_rig = rigs[npc_anim.FEMALE_SKELETON]
    kit, groups = npc_anim.plan(skeleton, BODY_SWIM, female_rig, appearance.get('weight', 1.))
    missing = [g['name'] for g in groups if g['name'] in ('swimidle', 'swim') and g['source'] == 'idle']
    if missing:
        raise ValueError(appearance['id'] + ': missing original swim sections: ' + ', '.join(missing))
    shapes, materials, textures = assemble(assets, appearance, kit, npc_anim.idle_compatible_times(groups))
    reference = fit = None
    for rows, contour in ((96, 0), (80, 0), (80, 1), (80, 2)):
        for budget in BUDGETS:
            parts = []
            try:
                frames, faces, uv, skin = bake(shapes, materials, textures, palette,
                    budget=budget, reference_frames=8, body_skin_rows=rows,
                    body_leg_contour=contour, face_parts=parts)
                if reference is None:
                    reference = (frames[0], faces, parts)
                elif not player_leg_section_ok(reference[0], reference[1], frames[0], faces,
                                               reference_parts=reference[2], candidate_parts=parts):
                    raise AliasOverflow('Player swim visible leg silhouette narrowed')
                if npc_anim.alias_bytes(sum(g['count'] for g in groups), frames.shape[1], len(faces),
                                        *skin.size) > npc_anim.ALIAS_BYTE_BUDGET:
                    continue
                fit = (budget, rows, contour, frames, faces, uv, skin)
                break
            except AliasOverflow:
                continue
        if fit is not None:
            break
    if fit is None:
        raise ValueError(appearance['id'] + ': original swim body exceeds alias/leg budget')
    budget, rows, contour, frames, faces, uv, skin = fit
    names = [g['name'][:13] + '%02d' % i for g in groups for i in range(g['count'])]
    raw = animated_mdl(frames, faces, uv, skin, names=names)
    if len(raw) > npc_anim.ALIAS_BYTE_BUDGET:
        raise ValueError('Player swim body exceeded alias byte budget')
    path = swim_path(base_row['model'])
    layout = npc_anim.player_layout(groups)
    report = {'race': race, 'female': female, 'base_model': base_row['model'],
              'model': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'frames': len(frames), 'triangles': len(faces), 'vertices': frames.shape[1],
              'budget': budget, 'skin_rows': rows, 'contour': contour,
              'groups': {g['name']: g['count'] for g in groups},
              'group_sources': {g['name']: g['source'] for g in groups},
              'scope': 'water-only original swim loops; not native or matched-reference acceptance'}
    return path, raw, layout, report


# ---------------------------------------------------------------- units: one pool, kept by their inputs

# BUILD-PLAYER-VIEW-UNDERUSED-48: the four bakes (body, torch body, water body, inventory poses) of the 20 race/sex
# bodies ran as four pools one after the other, each started fresh: every worker loaded the master, the archive and
# the skeletons again (about 9 s) for about 2 s of work per torch, water or inventory unit, at most 20 of 24 cores
# were busy, and all 80 units were made again in every build. Now they run in one worker pool kept for the whole
# step (water and inventory beside the bodies, torch bodies after them: they need the body's frame groups), the
# longest first, and every unit is kept in the image unit cache by the SHA-256 of its inputs.
UNIT_CACHE = 'player-view'
UNIT_COSTS = 'player-view'
UNIT_FALLBACK_SECONDS = {'body': 30.0, 'torch': 3.0, 'swim': 3.0, 'inventory': 3.0}


def _unit_worker(kind):
    if kind == 'inventory':
        from player_inventory_pose import bake_body as inventory_body
        return inventory_body
    return {'body': bake_body, 'torch': bake_torch_body, 'swim': bake_swim_body}[kind]


def bake_unit(unit):
    """Pool worker: one unit (kind, task) of the player view: kind 'body', 'torch', 'swim' or 'inventory'."""
    kind, task = unit
    return _unit_worker(kind)(task)


def unit_name(unit):
    kind, task = unit
    return '%s %s %s' % (kind, task[2], 'female' if task[3] else 'male')


def unit_inputs(unit):
    """What one unit's result depends on besides the game data, the code and its settings (the cache's options and
    sources): kind, race, sex, the palette by SHA-256 and, for the torch and water bodies, the body row fields they
    read (its model path and, for the torch body, its frame groups)."""
    kind, task = unit
    _, palette, race, female = task[:4]
    inputs = {'entry': {'name': unit_name(unit)}, 'kind': kind, 'race': race, 'female': bool(female),
              'palette_sha256': hashlib.sha256(palette).hexdigest()}
    if kind == 'torch':
        inputs['base'] = {'model': task[4]['model'], 'groups': task[4]['groups']}
    elif kind == 'swim':
        inputs['base'] = {'model': task[4]['model']}
    return inputs


def pack_result(result):
    """(row, {name: bytes}) of a unit's result tuple for the unit cache: its bytes as files, the rest as JSON; None
    when a part does not survive a JSON round trip unchanged (then the unit is not cached)."""
    from pass_cache import json_exact
    parts, files = [], {}
    for part in result:
        if isinstance(part, bytes):
            name = str(len(files))
            files[name] = part
            parts.append({'file': name})
        else:
            parts.append({'value': part})
    row = {'parts': parts}
    return (row, files) if json_exact(row) else None


def unpack_result(row, files):
    """The result tuple pack_result stored."""
    return tuple(files[part['file']] if 'file' in part else part['value'] for part in row['parts'])


def _unit_cache():
    """The player view's share of the image unit cache (tools/pass_cache.py UnitCache, WORKSPACE/cache/image-passes),
    or None: cache off, or no input lock naming the game data by SHA-256 (the inputs are then not known exactly)."""
    from pass_cache import UnitCache, game_data_digest
    game = game_data_digest()
    if game is None:
        return None
    import player_inventory_pose
    return UnitCache.open(UNIT_CACHE, {'game_data': game}, __file__, player_inventory_pose.__file__)


def run_units(units, cache, jobs):
    """Results of UNITS [(kind, task)] in input order and how many came from CACHE: a unit recorded for the same
    inputs is taken from it byte for byte (unless --rebuild-unit player-view:NAME names it); the rest run on the
    worker pool, longest first by their recorded seconds, and are recorded."""
    from pass_cache import forced
    results = [None] * len(units)
    todo = []
    for index, unit in enumerate(units):
        if cache is not None and not forced(UNIT_CACHE, unit_name(unit)):
            found = cache.load_unit(unit_inputs(unit))
            if found is not None:
                try:
                    results[index] = unpack_result(*found)
                    continue
                except (KeyError, TypeError, AttributeError):
                    pass
        todo.append(index)
    if todo:
        from build_costs import costed_map
        from build_jobs import resolve_jobs
        items = [units[index] for index in todo]
        workers = max(1, min(resolve_jobs(jobs), len(items)))
        # list(): run the map to its end, where costed_map records this run's unit seconds for the next build
        made = list(costed_map(UNIT_COSTS, bake_unit, items, [unit_name(unit) for unit in items], workers,
                               fallback=lambda name: UNIT_FALLBACK_SECONDS[name.split(' ', 1)[0]]))
        for index, result in zip(todo, made):
            if cache is not None:
                packed = pack_result(result)
                if packed is not None:
                    cache.store_files(unit_inputs(units[index]), *packed)
            results[index] = result
    return results, len(units) - len(todo)


def bodies_text(entries):
    lines = [BODIES_FORMAT]
    seen = set()
    for race, female, path in entries:
        if (race, female) in seen or '\t' in race or len(race) > 31 or len(path) > 47:
            raise ValueError('Bad body catalogue row')
        seen.add((race, female))
        lines.append(f'{race}\t{1 if female else 0}\t{path}')
    return '\n'.join(lines) + '\n'


def prepare(data_files, id1, jobs=None, bodies=True):
    from mwad.paths import resolve_data_files
    data = resolve_data_files(Path(data_files))
    id1 = Path(id1)
    kinds, _, _ = _sources(data)
    (id1 / 'view').mkdir(parents=True, exist_ok=True)
    text = settings_text(kinds)
    (id1 / 'view/settings.txt').write_text(text, encoding='ascii', newline='\n')
    report = {'settings': text.splitlines()[1:], 'settings_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'bodies': [], 'torch_bodies': [], 'swim_bodies': [], 'scope': 'stand-in body: the new-game player record (clothes) over the race skin, '
                                      'first head and hair of the race and sex; idle, walk, run, hit, death, block, jump, land '
                                      'and hand-to-hand ready locomotion with equip/lower/punch arm layers; '
                                      'original left-arm torch hold and held torch companion; original swim loops in a water-only body'}
    if not bodies:
        report['bodies_off'] = '--player-body off: no body; the game stays in first person'
        return report
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    races = playable_races(kinds)
    if not races or len(races) * 2 > 32:
        raise ValueError('Playable race count outside the body catalogue bounds')
    tasks = [(str(data), palette, race, female) for race in races for female in (False, True)]
    # The water body reads only the body's model path (swim_path), so it runs beside the bodies.
    swim_tasks = [task + ({'model': body_path(task[2], task[3])},) for task in tasks]
    from build_parallel import stage_pool
    cache = _unit_cache()
    (id1 / BODY_DIR).mkdir(parents=True, exist_ok=True)
    entries = []
    count = len(tasks)
    started = time.monotonic()
    with stage_pool(jobs, 'player view'):
        first, reused = run_units([('body', t) for t in tasks] + [('swim', t) for t in swim_tasks] +
                                  [('inventory', t) for t in tasks], cache, jobs)
        for path, raw, layout, row in first[:count]:
            (id1 / path).write_bytes(raw)
            (id1 / (path[:-4] + '.anm')).write_text(layout + '\n', encoding='ascii', newline='\n')
            (id1 / path).with_suffix('.tag').write_text(row.pop('_item_tags'), encoding='ascii', newline='\n')
            entries.append((row['race'], row['female'], path))
            report['bodies'].append(row)
        torch_tasks = [(str(data), palette, row['race'], row['female'], row) for row in report['bodies']]
        torch, torch_reused = run_units([('torch', t) for t in torch_tasks], cache, jobs)
    reused += torch_reused
    for body_path_, body_raw, layout, held_path, held_raw, metadata_path, metadata, row in torch:
        for path, raw in ((body_path_, body_raw), (held_path, held_raw), (metadata_path, metadata)):
            (id1 / path).write_bytes(raw)
        (id1 / body_path_[:-4]).with_suffix('.anm').write_text(layout + '\n', encoding='ascii', newline='\n')
        (id1 / held_path[:-4]).with_suffix('.anm').write_text(layout + '\n', encoding='ascii', newline='\n')
        report['torch_bodies'].append(row)
    for path, raw, layout, row in first[count:2 * count]:
        (id1 / path).write_bytes(raw)
        (id1 / path[:-4]).with_suffix('.anm').write_text(layout + '\n', encoding='ascii', newline='\n')
        report['swim_bodies'].append(row)
    report['inventory_bodies'] = []
    for path, raw, tags, row in first[2 * count:]:
        (id1 / path).write_bytes(raw)
        (id1 / path).with_suffix('.tag').write_text(tags, encoding='ascii', newline='\n')
        report['inventory_bodies'].append(row)
    catalogue = bodies_text(entries)
    (id1 / 'view/bodies.txt').write_text(catalogue, encoding='ascii', newline='\n')
    report['catalogue_sha256'] = hashlib.sha256(catalogue.encode()).hexdigest()
    units = len(first) + len(torch)
    report['unit_cache'] = {'units': units, 'reused': reused, 'made': units - reused,
                            'cache': 'off' if cache is None else UNIT_CACHE}
    print('Player view: %d units (%d from the unit cache, %d made) in %.1f s' %
          (units, reused, units - reused, time.monotonic() - started), flush=True)
    return report


def prepare_image(data_files, id1, jobs=None, bodies=True):
    """The image step's player view (prepare) as its own timed phase: tools/build_aga.py runs it in a spawned worker
    beside the combat data, which neither reads nor writes view/ or progs/body/ (BUILD-IMAGE-FINALIZE-UNDERUSED-48)."""
    import build_profile
    with build_profile.phase('Image: player view', detail='beside the combat data'):
        return prepare(data_files, id1, jobs=jobs, bodies=bodies)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--id1', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=None)
    p.add_argument('--no-bodies', action='store_true')
    a = p.parse_args()
    print(json.dumps(prepare(a.data_files, a.id1, a.jobs, not a.no_bodies), indent=2))


if __name__ == '__main__':
    main()
