# SPDX-License-Identifier: GPL-3.0-only
"""Carried items (weapon, shield) drawn as separate models that follow a hand bone.

The original engine attaches the wielded weapon to "Weapon Bone" and the carried
shield to "Shield Bone" (OpenMW npcanimation.cpp showWeapons / showCarriedLeft). A
Quake alias model cannot show or hide parts, so a resident that only holds its weapon
while fighting gets:

- one item model per weapon or shield mesh, baked once (items/<hash>.mdl, one frame,
  in the item's own axes, scaled like the actors: 0.25), shared by every actor;
- a tag table beside the resident model (<model>.tag): per frame of the model, the
  Weapon Bone and Shield Bone transforms in the model's own space, as an origin and
  Quake angles (pitch, yaw, roll; AngleVectors convention), the same frames as the
  model's layout (<model>.anm).

The engine draws the item as its own entity at the actor's origin plus the tag's
origin turned by the actor's yaw, with the tag's angles plus the actor's yaw
(engine/aga/src/aw_items.c). One mechanism for every actor (NPC-WEAPON-MESH-33);
the Arena fighters keep their weapon baked into the model (always fighting).

The item keeps its own size: the original also scales attached items with the
actor's race width and height, which a shared alias model cannot (the grip sits
exactly on the bone; measured on the owner's data: exact for a Hlaalu guard, up to
3.3 units at the blade tip for an Imperial guard).

Tag file (ASCII, LF):
    AWTG1 FRAMES
    weapon items/w0123456789ab.mdl      (or "weapon -")
    shield items/s0123456789ab.mdl      (or "shield -")
    then one line per frame: wx wy wz wpitch wyaw wroll sx sy sz spitch syaw sroll
"""
import hashlib
import math

import numpy as np

TAG_MAGIC = 'AWTG1'
BONES = (('weapon', 'Weapon Bone'), ('shield', 'Shield Bone'))


def carried_items(kinds, identifier):
    """The weapon and shield the combat rules use for this actor (prepare_combat.equipment:
    best melee weapon, the shield unless the weapon is two-handed), or None for none."""
    import struct
    from prepare_combat import equipment, first
    npc = kinds['NPC_'][identifier.casefold()]
    weapon, armor = equipment(kinds, npc, struct.unpack_from('<h', first(npc, 'NPDT'))[0])
    items = {'weapon': weapon[1] if weapon else None, 'shield': armor.get('shield', (None,))[0]}
    return items if items['weapon'] or items['shield'] else None


def quake_angles(rotation):
    """Quake angles (pitch, yaw, roll in degrees) of a 3x3 rotation in row-vector form
    (rows = images of the model's x, y, z axes). Quake: forward = model x, left = model y
    (right = -y), up = model z; AngleVectors gives forward (cp*cy, cp*sy, -sp),
    right.z = -sr*cp, up.z = cr*cp."""
    r = np.asarray(rotation, float)
    forward, left, up = r[0], r[1], r[2]
    right = -left
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -forward[2]))))
    yaw = math.degrees(math.atan2(forward[1], forward[0]))
    roll = math.degrees(math.atan2(-right[2], up[2]))
    return pitch, yaw, roll


def angle_matrix(pitch, yaw, roll):
    """Inverse of quake_angles (AngleVectors): rows forward, left, up."""
    p, y, r = (math.radians(a) for a in (pitch, yaw, roll))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    forward = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return np.array([forward, [-v for v in right], up])


def bone_tags(skeleton, times, appearance, items):
    """Per frame, (origin, angles) of each carried item's bone in the model's space, scaled
    like assemble() scales the vertices (weight, weight, height x 0.25). The rotation is
    re-orthonormalised (the actor scale is not uniform; the item keeps its own size)."""
    scale = np.array([appearance['weight'], appearance['weight'], appearance['height']]) * .25
    rows = []
    for t in times:
        pose = skeleton.pose(float(t))
        row = []
        for kind, bone in BONES:
            if not items.get(kind):
                row += [0.0] * 6
                continue
            m = pose(bone)
            u, _, vt = np.linalg.svd(m[:3, :3])
            rot = u @ vt
            row += [*(m[3, :3] * scale), *quake_angles(rot)]
        rows.append(row)
    return rows


# First-person view space (tools/prepare_hands.py): vertices are moved by -camera, then
# (x, y, z) -> (y, -x, z). As a row-vector matrix: v_view = (v - camera) @ VIEW_AXES.
VIEW_AXES = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])


def view_tags(skeleton, times, camera, items):
    """Per frame, (origin, angles) of each carried item's bone in the first-person view
    model's space, mapped exactly as prepare_hands maps the hand vertices (scale 0.25 with
    weight = height = 1, minus the camera, then the view axes). camera: the scaled Camera
    origin (prepare_hands). The item entity then follows the view model like a resident's."""
    rows = []
    for t in times:
        pose = skeleton.pose(float(t))
        row = []
        for kind, bone in BONES:
            if not items.get(kind):
                row += [0.0] * 6
                continue
            m = pose(bone)
            u, _, vt = np.linalg.svd(m[:3, :3])
            rot = (u @ vt) @ VIEW_AXES
            origin = (m[3, :3] * .25 - np.asarray(camera, float)) @ VIEW_AXES
            row += [*origin, *quake_angles(rot)]
        rows.append(row)
    return rows


def item_stem(kind, mesh):
    return ('w' if kind == 'weapon' else 's') + hashlib.sha256(mesh.casefold().encode()).hexdigest()[:12]


class _Rest:
    """A skeleton stand-in whose every bone is the identity: the item in its own axes."""
    def __init__(self, N):
        self.N = N

    def pose(self, time):
        return lambda name: np.eye(4)


def item_model(assets, part, palette, N):
    """One-frame alias model of a carried part (carried_parts row) in its own axes."""
    from npc_geometry import animated_mdl, assemble, bake
    appearance = {'parts': [part], 'weight': 1.0, 'height': 1.0}
    shapes, materials, textures = assemble(assets, appearance, _Rest(N), np.zeros(1))
    for budget in (240, 160, 96):
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget)
            break
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == 96:
                raise
    return animated_mdl(frames, faces, uv, skin, names=['item00'])


def publish(id1, record):
    """Write a resident's tag table beside its model (<model>.tag) and each item model
    once; the record keeps the tag's hash and the item paths (it is written as JSON)."""
    import hashlib
    from pathlib import Path
    tag = record.pop('_item_tag', None)
    items = record.pop('_items', {})
    mover_tag = record.pop('_mover_item_tag', None)
    if not tag:
        return
    model = Path(id1) / record['model']
    model.with_suffix('.tag').write_text(tag, encoding='ascii', newline='\n')
    if mover_tag:
        # beside the mover model (npc_anim.publish names it in record['anim']['mover']['model'])
        mover = Path(id1) / record['anim']['mover']['model']
        mover.with_suffix('.tag').write_text(mover_tag, encoding='ascii', newline='\n')
    for name, raw in sorted(items.items()):
        target = Path(id1) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != raw:
            target.write_bytes(raw)
    record['items'] = {'tag_sha256': hashlib.sha256(tag.encode('ascii')).hexdigest(), 'models': sorted(items)}
    if mover_tag:
        record['items']['mover_tag_sha256'] = hashlib.sha256(mover_tag.encode('ascii')).hexdigest()


def tag_text(rows, paths):
    lines = [f'{TAG_MAGIC} {len(rows)}']
    for kind, _ in BONES:
        lines.append(f'{kind} {paths.get(kind) or "-"}')
    lines += [' '.join(f'{v:.3f}' for v in row) for row in rows]
    return '\n'.join(lines) + '\n'


def attach_items(kinds, identifier, appearance):
    """For the resident callers (prepare_area, import_town): record the actor's carried
    items on its appearance (not drawn in the model: appearance['parts'] is unchanged)."""
    from mwad.npc import carried_parts
    items = carried_items(kinds, identifier)
    if items:
        appearance['carried_parts'] = {p['carried']: p for p in carried_parts(kinds, items, appearance.get('female', False))}
    return appearance


def resident_items(assets, palette, appearance, skeleton, times, mover_times=None):
    """For build_resident: (tag text, {item path: model bytes}) or (None, {}).

    times: one sample per frame of the model the tag sits beside (aw_items.c refuses a tag whose row
    count differs from the model's frames). mover_times: an animation kit actor's mover model frames
    (npc_anim.py, worn while it moves or fights): then (tag, models, mover tag); ANIMKIT-ITEM-TAG-FRAMES-35."""
    parts = appearance.get('carried_parts') or {}
    paths, models = {}, {}
    for kind, _ in BONES:
        part = parts.get(kind)
        if not part:
            continue
        path = 'items/' + item_stem(kind, part['mesh']) + '.mdl'
        models[path] = item_model(assets, part, palette, skeleton.N)
        paths[kind] = path
    if not paths:
        return (None, {}) if mover_times is None else (None, {}, None)
    rows = bone_tags(skeleton, times, appearance, {k: True for k in paths})
    if mover_times is None:
        return tag_text(rows, paths), models
    return tag_text(rows, paths), models, tag_text(bone_tags(skeleton, mover_times, appearance, {k: True for k in paths}), paths)
