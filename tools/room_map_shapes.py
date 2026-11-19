# SPDX-License-Identifier: GPL-3.0-only
"""Source shapes of a room map's models drawn as the original draws them through the visual reduction
(PRISON-SHIP-FLOOR-STUCK-67, PRISON-SHIP-TABLE-DARK-TRIANGLE-67).

The prison ship's hold reduces its shell to 8 % of its faces and keeps the structural shapes whole: the profile's
preserve_shape_prefixes in tools/prepare_interior.py (hull, floors, ceiling, walls, steps, plank). Every other shape is
reduced, each connected part to about 8 % of its faces and at least 4. Two kinds of shape suffered from it (measured
on the v0.0.67-dev2 hold, docs/SHIP_INTERIOR.md "Drawn where it collides"):
- shapes whose authored collision stays: the two masts ('Tri mast' on the upper deck, 'Tri LLmast' below, five-sided
  columns of 30 faces) went to 4 faces each while their collision columns stayed, so the player walked into an
  invisible post with only the tile at its foot drawn; the raised deck at both ends ('Tri In_DE_ship_upperlevel 0',
  216 faces drawn as 85), a post on the lower deck, a pole by the stairs and four side boards of the stairs the same,
  less visibly (62 collision pieces lost, 40 of them taller than a step: tools/drawn_collision.py);
- the iron bands of the four tables ('Tri Furn_Com_Table_02 1' to '05 1', two bands of 40 faces each): reduced to 4
  faces a band, they became a slanted double-sided tent up to 1.6 units over the band, a dark triangle across the
  table top.

ROOM_MAP_WHOLE_SHAPES lists the shapes kept whole (their source faces, UVs and materials). ROOM_MAP_BOX_SHAPES lists
the shapes kept whole through the reduction and then drawn as the boxes of their parts (room_map_parts.box_polygons,
six faces a part in the part's material and texture scale, spanning it exactly): a band is a thin sleeve around the
table top, its box is the band as seen, for 6 faces instead of 40.

Names are exact (a prefix cannot name them alone: 'Tri mast' is also the start of 'Tri mast01' and 'Tri mast02', the
iron collars at the mast's foot and top, 645 faces each, which stay reduced). The keep is done in the room map's own
path (room_map_collision.prepare_room_models), without a change to the shared reducer (static_lod.reduce_for_profile,
whose functions are in the key of every CHIM model unit): the reducer gets a view of the model whose listed shapes
carry WHOLE_MARK before their name, and a profile whose preserve_shape_prefixes also hold WHOLE_MARK, so the shared
prefix rule keeps exactly those shapes, as an exact-name keep in the shared reducer would.

--room-shapes off (AMIWIND_ROOM_SHAPES, room_map_env) reduces the listed shapes like the rest, the method before.
"""
import numpy as np

# the switch (--room-shapes on|off, AMIWIND_ROOM_SHAPES; on by default) lives in room_map_env
from room_map_env import ROOM_SHAPES_MODES, ROOM_SHAPES_VARIABLE, export_room_shapes, room_shapes  # noqa: F401

# model source -> the exact names of its source shapes kept whole (as the original draws them)
ROOM_MAP_WHOLE_SHAPES = {
    'meshes/i/in_prison_ship.nif': (
        'Tri mast', 'Tri LLmast',                       # the masts: their collision columns stand on both decks
        'Tri In_DE_ship_upperlevel 0',                  # the raised deck at both ends: walls and floor plates
        'Tri Post11 0', 'Tri pose06 0',                 # a post on the lower deck, a pole by the stairs
        'Tri slat 0', 'Tri slat01 0', 'Tri slat04 0', 'Tri slat07 0',   # the stairs' side boards with collision
    ),
}

# model source -> the exact names of its source shapes drawn as the boxes of their parts
ROOM_MAP_BOX_SHAPES = {
    'meshes/i/in_prison_ship.nif': (
        'Tri Furn_Com_Table_02 1', 'Tri Furn_Com_Table_03 1', 'Tri Furn_Com_Table_04 1', 'Tri Furn_Com_Table_05 1',
    ),
}

# before a listed shape's name in the reducer's view; no NIF shape name starts with it
WHOLE_MARK = '\x00room-whole\x00'


def whole_shapes(source):
    """The exact shape names model SOURCE keeps whole through the reduction (both tables), () with --room-shapes off."""
    if room_shapes() == 'off':
        return ()
    return tuple(ROOM_MAP_WHOLE_SHAPES.get(source, ())) + tuple(ROOM_MAP_BOX_SHAPES.get(source, ()))


def box_shapes(source):
    """The exact shape names model SOURCE draws as the boxes of their parts, () with --room-shapes off."""
    if room_shapes() == 'off':
        return ()
    return tuple(ROOM_MAP_BOX_SHAPES.get(source, ()))


def shape_materials(model, names):
    """{name: [material index, ...]} of the exact (any case) source shape NAMES in the scenery index's model record
    MODEL. A name not among the model's shapes is refused (the tables name the source's shapes)."""
    wanted = {name.casefold(): name for name in names}
    found = {}
    for k, mat in enumerate(model['materials']):
        name = wanted.get(mat.get('source_shape', '').casefold())
        if name is not None:
            found.setdefault(name, []).append(k)
    missing = sorted(name for name in wanted.values() if name not in found)
    if missing:
        raise ValueError('%s has no source shape %s (room_map_shapes)' % (model['source'], ', '.join(missing)))
    return found


def whole_shape_view(model, profile, names):
    """(model view, profile view, receipt) for the reducer: the shapes NAMES of the scenery index's model record MODEL
    kept whole by the visual profile PROFILE. Without names, or without a reducing profile, MODEL, PROFILE and {}."""
    if not names or not (profile or {}).get('ratio'):
        return model, profile, {}
    found = shape_materials(model, names)
    kept = sorted(k for ks in found.values() for k in ks)
    materials = [dict(mat, source_shape=WHOLE_MARK + mat.get('source_shape', '')) if k in kept else mat
                 for k, mat in enumerate(model['materials'])]
    view = dict(profile, preserve_shape_prefixes=[*profile.get('preserve_shape_prefixes', ()), WHOLE_MARK])
    receipt = {'shapes': sorted(found), 'materials': kept,
               'source_faces': sum(int(model['materials'][k].get('source_face_range', {}).get('count', 0))
                                   for k in kept)}
    return dict(model, materials=materials), view, receipt


def box_shape_parts(record, model, names):
    """Draw the shapes NAMES of one prepared model record (v, f, polys, parts, lod) as the boxes of their parts (the
    polygons joined by shared corners, room_map_parts.part_groups); a flat part stays as it is. Returns (record,
    receipt); the record's lod gets the receipt as 'box_shapes'."""
    from room_map_parts import _winding, box_polygons, part_groups
    v, f, polys, parts, lod = record
    if not names:
        return record, {}
    materials = {k for ks in shape_materials(model, names).values() for k in ks}
    mine = [p for p in polys if int(p[1]) in materials]
    rest = [p for p in polys if int(p[1]) not in materials]
    winding = _winding(polys[0]) if polys else 1
    kept, boxes, n = [], [], 0
    for group in part_groups(mine):
        pts = np.concatenate([np.asarray(mine[i][0], float) for i in group])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        if float((hi - lo).min()) <= 1e-6:
            kept.extend(mine[i] for i in group)
            continue
        scale = float(np.mean([np.linalg.norm(np.asarray(mine[i][2], float), axis=0).mean() for i in group]))
        boxes.extend(box_polygons(lo, hi, mine[group[0]][1], scale, winding))
        n += 1
    receipt = {'shapes': sorted(names), 'parts_boxed': n, 'faces_before': len(mine), 'faces_after': len(kept) + len(boxes)}
    lod = dict(lod, box_shapes=receipt)
    return (v, f, rest + kept + boxes, parts, lod), receipt
