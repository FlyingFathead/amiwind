# SPDX-License-Identifier: GPL-3.0-only
"""A CHIM room's collision for offline checks (IMAGE-ROOM-MAPS-LATE-PASSES-48).

A CHIM room map (maps/<room>.chim) holds a shell world and its entities; its floors and walls are the placements of
its room record (<store>/rooms/<room>.crm), each a store model moved and turned at run time (chim/chim_room.c,
ChimChunks_ClipPlace). The image checks that stand something on a room's collision (the actor contact gate, a direct
start in a room) read it here as one audit_walkability.Scene, the same trace the room maps' checks use. Kept apart from
chim/collision.py so the stair walk's code key (chim.collision.STAIR_WALK_CODE) does not take in the store readers.
"""
from pathlib import Path
import struct

from audit_walkability import Scene, axes
from chim import format as F
from chim.cut import source_ref

HULL_ROOT = 10                  # dmodel field: head node 1, the standing hull (as chim.collision)


def relocate(scene, image, hull):
    """Append one brush image's planes and hull nodes to SCENE (chim.collision.FrameScene's relocation); returns its
    root."""
    lumps = F.read_brush_image(image)
    plane_base, node_base = len(scene.planes), len(scene.nodes)
    scene.planes += list(struct.iter_unpack('<4fi', lumps[1]))
    if hull == 1:
        for p, front, back in struct.iter_unpack('<iHH', lumps[9]):
            scene.nodes.append((p + plane_base, *(c - 65536 if c >= 0xFFF0 else c + node_base for c in (front, back))))
    else:
        leaves = [r[0] for r in struct.iter_unpack('<ii6h2H4B', lumps[10])]
        for p, front, back, *_ in struct.iter_unpack('<i2h6h2H', lumps[5]):
            scene.nodes.append((p + plane_base, *(c + node_base if c >= 0 else leaves[-c - 1] for c in (front, back))))
    root = struct.unpack_from('<9f7i', lumps[14])[HULL_ROOT - 1 + hull]
    return root + node_base if root >= 0 else root


class RoomScene(Scene):
    """A CHIM room's collision as one audit_walkability.Scene: the room map's own world and clip models (the closed
    edge, liquids, lava beds, activated objects) and every placement of its room record, its store model's hull moved
    by the record's origin and turned by its three angles (the turned-model path of ChimChunks_ClipPlace). Not read:
    the engine's piece tables, which it tries first for a turned placement; they are cut from the same collision, so a
    check on this scene is the model's own collision, said so in its receipt.
    MAP_PATH: an installed room map (id1/maps/<room>.chim beside id1/<store>)."""

    COLLISION = 'store models (each placement turned by its record angles), piece tables not read'

    def __init__(self, map_path, hull=0):
        from chim.interior import installed_room, store_model_images
        map_path = Path(map_path)
        super().__init__(map_path.read_bytes(), hull=hull)
        room = installed_room(map_path)
        if room is None:
            raise ValueError('%s is not a CHIM room map' % map_path.name)
        images = store_model_images(map_path.parent.parent, room['store'], [p['model'] for p in room['placements']])
        roots = {}
        for p in room['placements']:
            if p['model'] not in roots:
                roots[p['model']] = relocate(self, images[p['model']], hull)
            self.brushes.append((roots[p['model']], tuple(p['origin']), axes(tuple(p['angles'])),
                                 source_ref(p['ref'])))
        self.room = room['room']
        self.placements = len(room['placements'])


def room_collision(map_path):
    """arrival_spot.Collision of a CHIM room map: the standing hull and the point hull of RoomScene (the room map's
    world contents for the dry test)."""
    from arrival_spot import Collision
    collision = Collision.__new__(Collision)
    collision.hull = RoomScene(map_path, hull=1)
    collision.point = RoomScene(map_path, hull=0)
    return collision
