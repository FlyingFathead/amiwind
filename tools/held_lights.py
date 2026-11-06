# SPDX-License-Identifier: GPL-3.0-only
"""A held carried light as itself (HELD-LIGHT-OWN-MODEL-61): what the engine needs to draw a candle, candlestick or
lantern in the hand with its own item model and the flames its placed copy has.

The original carries every light with the can-carry flag in the left hand on "Shield Bone", turned -90 degrees about
X (OpenMW npcanimation.cpp: a carried light's mesh; npc_geometry.rigid_attachment). The item model table already
holds each light's mesh (tools/prepare_item_models.py, npc_items.item_model: the mesh in its own axes with its
BoneOffset added, x 0.25), so nothing new is converted: beside that model the image gets one small text file,

  progs/items/m<16 hex>.hld   (the model's own name, .hld for .mdl)
    AWHL1
    offset X Y Z PITCH YAW ROLL     the item model placed on the shield bone: origin (model units) and Quake angles
                                    (AngleVectors convention), the carried-light turn about the mesh's BoneOffset
    flame X Y Z SIZE PARTICLE RISE SPREAD
                                    one line per flame emitter, at most FLAMES (the three-candle holders have three):
                                    the point in the item model's units, the flame size class and the emitter's
                                    particle size, rise and spread in model units, exactly the numbers a placed copy's
                                    aw_flame row carries (prepare_mesh_bsp.flame_entities, prepare_scenery.model_flames)

read by the engine once when the light is equipped (aw_torch.c AW_HeldLightParse): one file of about 100 bytes, no
search. A light whose mesh is the torch's gets no file: the torch keeps its own path. The light's radius and its
flicker come from its catalogue row (prepare_inventory.py), the torch's radius from the torch's record."""
import io
import math

import numpy as np

FORMAT = 'AWHL1'
FLAMES = 4          # engine/aga/src/aw_torch.h AW_HELD_FLAMES
SCALE = 0.25        # the item models' scale (npc_geometry.assemble)
# npc_geometry.rigid_attachment: a carried light turns -90 degrees about X on the shield bone (row-vector form)
CARRIED_TURN = np.array(((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))


def _nodes(data, N):
    """[(node, world 4x4)] of a NIF as npc_geometry.assemble walks it (the same root rule), every node."""
    from nif_common import root_local
    from npc_geometry import get_root_rule
    out = []

    def walk(node, parent, root=False):
        if not isinstance(node, N.NiAVObject):
            return
        local = np.array(node.get_transform().as_list())
        if root:
            local = root_local(local, get_root_rule())
        world = local @ parent
        out.append((node, world))
        for child in getattr(node, 'children', []):
            if child:
                walk(child, world)
    for root in data.roots:
        walk(root, np.eye(4), root=True)
    return out


def held_light(raw, N, name=''):
    """{'offset': [x y z pitch yaw roll], 'flames': [[x y z size particle rise spread]]} of one light mesh (its NIF
    bytes RAW): in the item model's units (its BoneOffset added, x 0.25, as item_model bakes it)."""
    from prepare_scenery import FLAME_SKIP
    data = N.Data()
    data.read(io.BytesIO(raw))
    nodes = _nodes(data, N)
    worlds = {id(n): w for n, w in nodes}
    offset = next((np.array(n.translation.as_list(), float) for n, _ in nodes if n.name.lower() == b'boneoffset'),
                  np.zeros(3))
    place = carried_place(offset)
    stem = name.casefold()
    size = (0.8 if any(k in stem for k in ('candle', 'lantern', 'sconce', 'lamp', 'chandelier', 'torch'))
            else 8.0 if any(k in stem for k in ('fire', 'brazier', 'pit')) else 2.0)   # prepare_scenery.model_flames
    flames = []
    for block in data.blocks:
        if type(block).__name__ != 'NiParticleSystemController' or block.emitter is None:
            continue
        if id(block.emitter) not in worlds:
            continue
        if any(k in block.emitter.name.decode('cp1252', 'replace').lower() for k in FLAME_SKIP):
            continue
        p = (worlds[id(block.emitter)][3, :3] + offset) * SCALE
        rise = max(0.0, float(block.speed)) * max(0.0, float(block.lifetime))
        spread = rise * math.tan(min(max(float(block.vertical_angle), 0.0), 1.2))
        flames.append([float(p[0]), float(p[1]), float(p[2]), size, max(0.0, float(block.size)) * SCALE,
                       rise * SCALE, spread * SCALE])
    if len(flames) > FLAMES:
        flames = flames[:FLAMES]
    return {'offset': place, 'flames': flames}


def carried_place(bone_offset):
    """[x y z pitch yaw roll]: the item model (its BoneOffset BONE_OFFSET already added, x 0.25) on the shield bone as
    npc_geometry.rigid_attachment carries a light: item point q = p + bo, held = p @ R + bo = q @ R + (bo - bo @ R)."""
    from npc_items import quake_angles
    bo = np.asarray(bone_offset, float)
    origin = (bo - bo @ CARRIED_TURN) * SCALE
    return [float(v) for v in origin] + [float(a) for a in quake_angles(CARRIED_TURN)]


def text(record):
    """The .hld file of HELD_LIGHT's record."""
    lines = [FORMAT, 'offset ' + ' '.join('%.4f' % v for v in record['offset'])]
    lines += ['flame ' + ' '.join('%.4f' % v for v in f) for f in record['flames'][:FLAMES]]
    return '\n'.join(lines) + '\n'


def read(raw):
    """text()'s record back (for the tests and the receipt check)."""
    lines = raw.decode('ascii').rstrip('\n').split('\n')
    if lines[0] != FORMAT or not lines[1].startswith('offset '):
        raise ValueError('Not a held light file')
    offset = [float(v) for v in lines[1].split()[1:]]
    flames = [[float(v) for v in line.split()[1:]] for line in lines[2:]]
    if len(offset) != 6 or any(not line.startswith('flame ') for line in lines[2:]) or \
            any(len(f) != 7 for f in flames) or len(flames) > FLAMES:
        raise ValueError('Damaged held light file')
    return {'offset': offset, 'flames': flames}


def sidecar_path(model):
    """The held light file beside an item model path (progs/items/m....mdl -> .hld)."""
    if not model.endswith('.mdl'):
        raise ValueError('Not an item model path: ' + model)
    return model[:-4] + '.hld'


# LHDT flags (OpenMW esm3 loadligh.hpp): dynamic 1, can carry 2, negative 4, flicker 8, fire 16, off by default 32,
# flicker slow 64, pulse 128, pulse slow 256
FLICKERS = 0x8 | 0x40 | 0x80 | 0x100
FIRE = 0x10


def catalogue_flags(lhdt_flags):
    """Byte 511 of a carried light's catalogue row: 0x80 (the byte is written) | 1 the light flickers or pulses |
    2 it is a fire. 0 in older catalogues (the engine then treats it as the torch did: flickering)."""
    return 0x80 | (1 if lhdt_flags & FLICKERS else 0) | (2 if lhdt_flags & FIRE else 0)
