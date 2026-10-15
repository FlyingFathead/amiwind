# SPDX-License-Identifier: GPL-3.0-only
"""Original inventory poses in a separate ten-frame player alias.

Frames: unarmed, then original melee weapon types 0..8. Gameplay animation
models are unchanged. Torch, ranged weapons and dynamic worn-part composition
remain separate work; this does not claim those appearances are implemented.
"""
import hashlib
import numpy as np

# OpenMW InventoryPreview::update and WeaponType long groups. Missing specific
# melee groups use the original one-/two-handed fallback, never ordinary idle.
GROUPS = ('handtohand', 'shortbladeonehand', 'weapononehand', 'weapontwohand',
          'bluntonehand', 'blunttwohand', 'weapontwowide', 'weapontwowide',
          'bluntonehand', 'blunttwohand')
TWO_HANDED = frozenset((2, 4, 5, 6, 8))
FRAMES = len(GROUPS)


def inventory_path(base):
    if not base.startswith('progs/body/') or '..' in base or not base.endswith('.mdl'):
        raise ValueError('Unsafe player inventory body path')
    return base[:-4] + '_i.mdl'


def _window(rig, group):
    if rig is None:
        return None
    a, b = (rig.events.get(group + ': ' + key) for key in ('start', 'stop'))
    if a is None and b is None:
        return None
    if a is None or b is None or not np.isfinite((a, b)).all() or not 0 <= a <= b:
        raise ValueError('Invalid original inventory section: ' + group)
    return float(a), float(b)


def plan(base, female=None):
    from npc_anim import KitSkeleton
    samples, records = [], []
    for frame, group in enumerate(GROUPS):
        requested = 'inventory' + group
        subtype = frame - 1
        fallback = 'inventoryweapontwohand' if subtype in TWO_HANDED else 'inventoryweapononehand'
        choices = (requested,) if frame == 0 or requested == fallback else (requested, fallback)
        selected = None
        for choice in choices:
            for source, rig in (('female', female), ('base', base)):
                window = _window(rig, choice)
                if window is not None:
                    selected = (choice, source, rig, window)
                    break
            if selected:
                break
        if selected is None:
            raise ValueError('Missing original inventory pose: ' + requested)
        choice, source, rig, window = selected
        # Original preview starts the dedicated group and advances zero seconds.
        samples.append((rig, window[0], None))
        records.append(dict(frame=frame, weapon_type=subtype, requested=requested,
                            group=choice, source=source, time=window[0],
                            show_left=subtype not in TWO_HANDED))
    return KitSkeleton(base, samples), records


def bake_body(task):
    """Private asset worker; no original data is embedded in public source."""
    from npc_geometry import Skeleton, assemble, bake, animated_mdl, AliasOverflow, player_leg_section_ok
    from npc_items import bone_tags, tag_text
    from npc_anim import FEMALE_SKELETON, ALIAS_BYTE_BUDGET
    from prepare_player_view import _sources, body_appearance, body_path, BUDGETS
    data, palette, race, female = task
    kinds, assets, rigs = _sources(data)
    appearance = body_appearance(kinds, race, female)
    path = appearance['skeleton']
    if path not in rigs:
        rigs[path] = Skeleton(assets, path)
    override = None
    if female and path == 'meshes/base_anim.nif':
        if FEMALE_SKELETON not in rigs:
            rigs[FEMALE_SKELETON] = Skeleton(assets, FEMALE_SKELETON)
        override = rigs[FEMALE_SKELETON]
    skeleton, poses = plan(rigs[path], override)
    times = np.arange(FRAMES)
    shapes, materials, textures = assemble(assets, appearance, skeleton, times)
    errors, reference = [], None
    for budget in BUDGETS:
        try:
            parts = []
            frames, faces, uv, skin = bake(shapes, materials, textures, palette,
                budget=budget, reference_frames=1, body_skin_rows=96, face_parts=parts)
            if len(frames) != FRAMES or len(parts) != len(faces):
                raise ValueError('Inventory body frame/part count changed')
            if reference is None:
                reference = (frames[0], faces, parts)
            elif not player_leg_section_ok(reference[0], reference[1], frames[0], faces,
                    reference_parts=reference[2], candidate_parts=parts):
                raise AliasOverflow('Player inventory leg silhouette narrowed')
            raw = animated_mdl(frames, faces, uv, skin,
                               names=['inventory%02d' % i for i in range(FRAMES)])
            if len(raw)>ALIAS_BYTE_BUDGET:
                raise AliasOverflow('Inventory body exceeds alias staging budget')
            break
        except AliasOverflow as error:
            errors.append(str(error))
    else:
        raise ValueError('Inventory body does not fit: ' + '; '.join(errors))
    tags = tag_text(bone_tags(skeleton, times, appearance, {'weapon': True, 'shield': True}), {})
    output = inventory_path(body_path(race, female))
    report = dict(model=output, race=race, female=female, frames=FRAMES,
                  vertices=frames.shape[1], triangles=len(faces), budget=budget,
                  bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), poses=poses,
                  tag_sha256=hashlib.sha256(tags.encode('ascii')).hexdigest(),
                  scope='Dedicated unarmed/melee inventory poses; existing starting clothes and first race/sex head/hair')
    return output, raw, tags, report
