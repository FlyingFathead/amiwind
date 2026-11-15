# SPDX-License-Identifier: GPL-3.0-only
"""Per-node movers for animated world objects (ENDGAME-CHAMBER-COLLAPSE-63, with DOOR-MOVERS-56: its track mode,
beside the hinge and slide modes of gates and trapdoors).

An animated world object of the original (the Heart Chamber's collapse: in_akulakhan00 and in_dagoth_bridge00) is a
model whose NODES carry keyframes in its own x-files (meshes/i/xin_akulakhan00.nif with xin_akulakhan00.kf; rule
from OpenMW file mwrender/objectanimation.cpp with animation.cpp addAnimSource: an object plays its own .kf, and
MWScript's PlayGroup starts a group of it, mwscript/animationextensions.cpp). The pieces are rigid: no skinning
(measured 2026-11-11 on both collapse models). Far too many
triangles for an alias actor (in_akulakhan00: 15,217 on its body node; an alias model takes 666 faces), so each
moving node becomes a mover: its pieces one placed store model, its motion a track of world transforms the engine
plays when the group starts. Measured 2026-11-11 on the original data: in_akulakhan00 has 14 movers over Death1
(26.6 s), the rope bridge one.

This module is the builder's half:
- moved_nodes(rig, group): the nodes a group moves (any point of the node more than MOVE_LIMIT game units off its
  start, or a turn over TURN_LIMIT degrees), each with how far;
- tracks(rig, group, nodes): each mover's transform per frame at RATE frames a second (position in game units,
  rotation as a unit quaternion), relative to the object's own origin;
- pack / unpack: the track record (format below), read by the engine with the room;
- budget(...): the sheet's numbers (resident bytes, frames, movers).

Track record 'AWTK' version 1 (AWMV is the saved games' mover block, aw_hinged_door.c), big-endian like the
animation tables (aw_skel.h), read by engine/aga/src/aw_track.c:
  4s magic, u16 version, u16 movers, u16 frames, u16 rate x 16, f32 position unit (game units per step),
  u16 sound keys, u16 0; per mover u16 node number (in the model's node order), u16 0, 32-byte NUL-padded node name;
  per sound key u16 frame, 30-byte NUL-padded sound id; then per mover per frame 7 x s16: x, y, z in position units,
  quaternion w, x, y, z x 32767. The last frame is held (OpenMW holds an object's last pose when a group ends).
"""
import struct

MAGIC = b'AWTK'
VERSION = 1
RATE = 8.0                  # frames a second (the animation tables' rate, skeletal_actor)
MOVE_LIMIT = 1.0            # game units (4 are one Quake unit), as creature_tables.DRIFT_LIMIT
TURN_LIMIT = 0.5            # degrees
NAME = 32
SOUND = 30
MAX_MOVERS = 64
Q = 32767.0


def group_window(rig, group):
    """(source index, start, stop) of GROUP's 'start' and 'stop' text keys in the newest source that has them."""
    for si in range(len(rig.sources) - 1, -1, -1):
        ev = rig.sources[si]['events']
        a, b = '%s: start' % group, '%s: stop' % group
        if a in ev and b in ev and ev[b] > ev[a]:
            return si, float(ev[a]), float(ev[b])
    raise ValueError('%s: no %s group in its keyframe files' % (rig.model, group))


def sample_times(start, stop, rate=RATE):
    n = int(round((stop - start) * rate)) + 1
    return [start + i / rate for i in range(max(2, n))]


def _worlds(rig, si, times):
    import numpy as np
    return np.array([rig.worlds(si, float(t)) for t in times])


def moved_nodes(rig, group, rate=RATE, move_limit=MOVE_LIMIT, turn_limit=TURN_LIMIT, ride=True, riders=None):
    """[{node, name, move, turn}] of the named nodes GROUP moves, in node order: move = the farthest the node's
    origin gets from its start pose (game units), turn = the largest rotation from it (degrees). RIDE: a moved node
    rigid on its nearest moved ancestor is no mover of its own (appended to RIDERS with 'rides')."""
    import numpy as np
    si, a, b = group_window(rig, group)
    worlds = _worlds(rig, si, sample_times(a, b, rate))
    out = []
    for i, node in enumerate(rig.nodes):
        name = node[0]
        if not name:
            continue
        p = worlds[:, i, 3, :3]
        move = float(np.linalg.norm(p - p[0], axis=1).max())
        r = worlds[:, i, :3, :3]
        cos = [(np.trace(r[0].T @ r[k]) - 1) / 2 for k in range(len(r))]
        turn = float(np.degrees(np.arccos(np.clip(min(cos), -1, 1))))
        if move > move_limit or turn > turn_limit:
            out.append({'node': i, 'name': name, 'move': round(move, 2), 'turn': round(turn, 2)})
    if not ride:
        return out
    # a moved node that keeps its pose on its nearest moved ancestor rides it (one mover, one track: the limbs'
    # geometry nodes and the blight emitters of in_akulakhan00), measured like creature_tables.merge_plan
    moved = {n['node'] for n in out}
    kept = []
    for n in out:
        p = rig.nodes[n['node']][1]
        while p >= 0 and p not in moved:
            p = rig.nodes[p][1]
        if p >= 0:
            rel = worlds[:, n['node']] @ np.linalg.inv(worlds[:, p])
            drift = float(np.linalg.norm(rel[:, 3, :3] - rel[0, 3, :3], axis=1).max())
            cos = [(np.trace(rel[0, :3, :3].T @ rel[k, :3, :3]) - 1) / 2 for k in range(len(rel))]
            turn = float(np.degrees(np.arccos(np.clip(min(cos), -1, 1))))
            if drift <= move_limit and turn <= turn_limit:
                n['rides'] = rig.nodes[p][0]
                if riders is not None:
                    riders.append(n)
                continue
        kept.append(n)
    return kept


def quaternion(m):
    """(w, x, y, z) of a 3x3 rotation in row-vector form (p' = p @ m), as a unit quaternion with w >= 0."""
    import numpy as np
    r = np.asarray(m, float).T              # column form
    t = r[0, 0] + r[1, 1] + r[2, 2]
    if t > 0:
        s = (t + 1.0) ** .5 * 2
        q = [s / 4, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s]
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = (1.0 + r[0, 0] - r[1, 1] - r[2, 2]) ** .5 * 2
        q = [(r[2, 1] - r[1, 2]) / s, s / 4, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s]
    elif r[1, 1] > r[2, 2]:
        s = (1.0 + r[1, 1] - r[0, 0] - r[2, 2]) ** .5 * 2
        q = [(r[0, 2] - r[2, 0]) / s, (r[0, 1] + r[1, 0]) / s, s / 4, (r[1, 2] + r[2, 1]) / s]
    else:
        s = (1.0 + r[2, 2] - r[0, 0] - r[1, 1]) ** .5 * 2
        q = [(r[1, 0] - r[0, 1]) / s, (r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, s / 4]
    q = np.array(q) / np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def tracks(rig, group, nodes, rate=RATE):
    """{node number: [(x, y, z, qw, qx, qy, qz)] per frame}: each node's world transform over GROUP."""
    si, a, b = group_window(rig, group)
    worlds = _worlds(rig, si, sample_times(a, b, rate))
    return {n['node']: [tuple(float(v) for v in w[n['node'], 3, :3]) + tuple(float(v) for v in
                        quaternion(w[n['node'], :3, :3])) for w in worlds] for n in nodes}


def sound_keys(rig, group, rate=RATE):
    """[(frame, sound id)] of the 'sound: X' text keys inside GROUP (the collapse's endboom1-4, the bridge's
    ropebridge), on the track's frames."""
    si, a, b = group_window(rig, group)
    out = []
    for t, line in rig.sources[si]['keys']:
        if line.startswith('sound:') and a <= t <= b:
            out.append((int(round((t - a) * rate)), line.split(':', 1)[1].strip()))
    return out


def pack(names, track, rate=RATE, sounds=()):
    """The track record of TRACK ({node number: frames}); NAMES {node number: node name}."""
    order = sorted(track)
    if not order or len(order) > MAX_MOVERS:
        raise ValueError('%d movers: 1 to %d' % (len(order), MAX_MOVERS))
    frames = len(track[order[0]])
    if any(len(track[n]) != frames for n in order) or not 2 <= frames <= 0xFFFF:
        raise ValueError('every mover needs the same number of frames (2 to 65535)')
    reach = max(abs(v) for n in order for f in track[n] for v in f[:3]) or 1.0
    unit = reach / 32000.0
    out = bytearray(MAGIC + struct.pack('>HHHHfHH', VERSION, len(order), frames, int(round(rate * 16)), unit,
                                        len(sounds), 0))
    for n in order:
        raw = names[n].encode('cp1252')
        if len(raw) >= NAME:
            raise ValueError('node name too long: %r' % names[n])
        out += struct.pack('>HH', n, 0) + raw.ljust(NAME, b'\0')
    for frame, sound in sounds:
        raw = sound.encode('cp1252')
        if len(raw) >= SOUND or not 0 <= frame < frames:
            raise ValueError('bad sound key %r at %d' % (sound, frame))
        out += struct.pack('>H', frame) + raw.ljust(SOUND, b'\0')
    for n in order:
        for f in track[n]:
            out += struct.pack('>7h', *[int(round(v / unit)) for v in f[:3]],
                               *[max(-32767, min(32767, int(round(v * Q)))) for v in f[3:]])
    return bytes(out)


def unpack(data):
    """{'rate', 'unit', 'names': {node: name}, 'sounds': [(frame, id)], 'track': {node: [(x, y, z, qw, qx, qy, qz)]}}."""
    if data[:4] != MAGIC:
        raise ValueError('Not a mover track record')
    version, movers, frames, rate16, unit, nsounds, _ = struct.unpack_from('>HHHHfHH', data, 4)
    if version != VERSION:
        raise ValueError('Mover track version %d' % version)
    at = 4 + struct.calcsize('>HHHHfHH')
    names = {}
    order = []
    for _ in range(movers):
        n = struct.unpack_from('>H', data, at)[0]
        names[n] = data[at + 4:at + 4 + NAME].rstrip(b'\0').decode('cp1252')
        order.append(n)
        at += 4 + NAME
    sounds = []
    for _ in range(nsounds):
        frame = struct.unpack_from('>H', data, at)[0]
        sounds.append((frame, data[at + 2:at + 2 + SOUND].rstrip(b'\0').decode('cp1252')))
        at += 2 + SOUND
    track = {}
    for n in order:
        rows = []
        for _ in range(frames):
            v = struct.unpack_from('>7h', data, at)
            rows.append(tuple(x * unit for x in v[:3]) + tuple(x / Q for x in v[3:]))
            at += 14
        track[n] = rows
    if at != len(data):
        raise ValueError('Mover track record: %d bytes left over' % (len(data) - at))
    return {'rate': rate16 / 16.0, 'unit': unit, 'names': names, 'sounds': sounds, 'track': track}


def budget(data, movers, triangles=None):
    """The budget sheet's numbers of one object's movers: resident bytes (the record, read with the room and freed
    with it), frames, seconds, transforms a frame while it plays, triangles that move."""
    info = unpack(data)
    frames = len(next(iter(info['track'].values())))
    return {'record_bytes': len(data), 'movers': len(movers), 'frames': frames,
            'seconds': round((frames - 1) / info['rate'], 2), 'transforms_per_frame': len(movers),
            'moving_triangles': triangles, 'bytes_per_mover_frame': 14}


def measure(N, read, mesh, group='death1', rate=RATE):
    """(record bytes, report) of one animated object mesh: its movers for GROUP, the record and the budget."""
    import creature_pose
    rig = creature_pose.CreatureRig(N, read, mesh, False)
    riders = []
    nodes = moved_nodes(rig, group, rate, riders=riders)
    if not nodes:
        raise ValueError('%s: %s moves no node' % (mesh, group))
    track = tracks(rig, group, nodes, rate)
    sounds = sound_keys(rig, group, rate)
    data = pack({n['node']: n['name'] for n in nodes}, track, rate, sounds)
    return data, {'mesh': mesh, 'model': rig.model, 'group': group, 'window': list(group_window(rig, group)),
                  'movers': nodes, 'riders': riders, 'sounds': sounds, 'budget': budget(data, nodes)}


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='a folder: movers.json and one .awv per mesh')
    p.add_argument('--group', default='death1')
    p.add_argument('meshes', nargs='+')
    a = p.parse_args(argv)
    from mwad.audit import BSA, normpath
    from mwad.paths import child_ci
    from npc_geometry import Assets
    from prepare_scenery import nif_reader
    assets = Assets(a.data_files, BSA(child_ci(a.data_files, 'Morrowind.bsa')))
    a.out.mkdir(parents=True, exist_ok=True)
    doc = {}
    for i, mesh in enumerate(a.meshes, 1):
        print('=== PHASE %d/%d: %s ===' % (i, len(a.meshes), mesh), flush=True)
        data, rep = measure(nif_reader(), assets.read, normpath(mesh), a.group)
        name = Path(mesh).stem.casefold() + '.awv'
        (a.out / name).write_bytes(data)
        doc[mesh] = dict(rep, record=name)
        print('Movers: %s: %d movers, %d bytes' % (mesh, len(rep['movers']), len(data)), flush=True)
    (a.out / 'movers.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    import sys
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parents[1]
    for _p in (_root / 'tools', _root / 'src'):
        while str(_p) in sys.path:
            sys.path.remove(str(_p))
        sys.path.insert(0, str(_p))
    main()
