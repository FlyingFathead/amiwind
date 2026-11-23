# SPDX-License-Identifier: GPL-3.0-only
"""Scripted animation groups on placed objects: the end pose of each group a script plays (MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68).

The original plays a script's PlayGroup and LoopGroup on any object whose model holds the group, not only on people and
creatures (rule from OpenMW apps/openmw/mwmechanics/mechanicsmanagerimp.cpp playAnimationGroup: a non-actor goes to
mwmechanics/objects.cpp, whose character controller plays the group on the object's own animation). The model's
keyframe controllers move its nodes between the group's text keys ("Idle2: Start" .. "Idle2: Stop"), its visibility
controllers show and hide parts, and the object's collision follows the moved nodes (OpenMW components/nifbullet/
bulletnifloader.cpp: a shape under a keyframe-animated node is an animated shape; apps/openmw/mwphysics/object.cpp
animateCollisionShapes moves it with its node). A non-looping group's last pose stays after it ends (OpenMW
mwmechanics/character.cpp updateAnimQueue). The Halls of Penumbra's ice wall (bm_ice_wall, icewallScript: LoopGroup
idle2) shatters this way and its passage opens; the Clockwork City's doors open and close by their levers' scripts.

A CHIM room draws such an object as a placement of a store model with no entity and no skeleton, so the group cannot be
drawn as it plays. What this module gives the room conversion (tools/chim/interior.py) is the group's end state:

- scripted_groups: from the game's scripts and dialogue results (the merged master), every object (not a person or a
  creature) a PlayGroup or LoopGroup names, with the groups it plays: the objects whose own script calls it, and the
  object a call names (`"act_sotha_pre_door1"->PlayGroup idle2`).
- group_times: a model's groups from its text keys (start, stop, loop start, loop stop).
- posed_nif: the model in the pose its controllers give at the group's stop key (translations, rotations and scales
  of the keyframe controllers; the visibility controllers; a material's alpha controller at 0 hides its shapes), as a
  NIF of its own. It goes through the same converter as every model (prepare_scenery.model_geometry and the one
  collision rule, tools/collision_source.py), so its drawn faces and its collision are the end pose's.

The engine swaps the placement's model to the end pose's model when the group has played (its object poses module,
AW_ObjPosePlay); a group whose end pose is the model as placed (a lever's return, a door's close) swaps it back.
"""
import io
import math
import re

ACTOR_KINDS = ('NPC_', 'CREA')
# the record kinds whose placements a script can play a group on (the placed objects that are not actors)
OBJECT_KINDS = ('ACTI', 'DOOR', 'CONT', 'STAT', 'LIGH', 'MISC', 'WEAP', 'ARMO', 'CLOT', 'BOOK', 'ALCH', 'INGR', 'APPA',
                'LOCK', 'PROB', 'REPA')
# a PlayGroup or LoopGroup call: an optional `target->` (quoted or bare id), the function, the group (quoted or bare);
# the arguments may be parted by commas, as the game's scripts often write them ("PlayGroup, Idle2")
CALL = re.compile(r'(?:("[^"\r\n]+"|[A-Za-z0-9_\[\]\.\'\-]+)\s*->\s*)?\b(playgroup|loopgroup)\b[\s,]+("[^"\r\n]+"|[A-Za-z0-9_]+)',
                  re.I)
TEXT_KEY = re.compile(r'\s*([^:]+?)\s*:\s*(loop start|loop stop|start|stop)\s*$', re.I)
ACTIVE = 0x8                    # NiTimeController flags: the controller runs (OpenMW Nif::NiTimeController::isActive)
HIDDEN = 0x1                    # NiAVObject flags: the node is not drawn
ALPHA_OFF = 0.5 / 255           # a material alpha below this draws nothing
TRANSLATION_EPS = 0.01          # NIF units: a node moved less than this has not moved
ROTATION_EPS = 1e-4
SCALE_EPS = 1e-4


def _cstr(data):
    return data.split(b'\0', 1)[0].decode('cp1252', 'replace')


def _code(line):
    """A script line without its comment (a ';' outside quotes)."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == ';' and not quoted:
            return line[:i]
    return line


def group_calls(text):
    """[(target id or None for the script's own object, function, group)] of every PlayGroup / LoopGroup in a script
    text, ids and groups in lower case."""
    out = []
    for line in text.replace('\r', '\n').split('\n'):
        for m in CALL.finditer(_code(line)):
            target = m.group(1).strip('"').strip().lower() if m.group(1) else None
            out.append((target, m.group(2).lower(), m.group(3).strip('"').strip().lower()))
    return out


def scripted_groups(master):
    """Every placed-object id a script or a dialogue result plays a group on, from the merged master's bytes:
    {'objects': {object id: {group: [script names]}}, 'models': {object id: NIF path}, 'calls': all calls,
    'actor_calls': calls on a person, a creature or the player, 'unknown_targets': [named ids no record has]}."""
    from mwad.esm import records, subrecords
    kind, model, script_of, scripts, results = {}, {}, {}, {}, []
    for tag, flags, payload in records(master):
        if tag == 'TES3':
            continue
        if tag == 'SCPT':
            subs = list(subrecords(payload))
            head = next((v for k, v in subs if k == 'SCHD'), b'')
            name = _cstr(head[:32])
            scripts[name.lower()] = (name, next((v for k, v in subs if k == 'SCTX'), b'').decode('cp1252', 'replace'))
        elif tag == 'INFO':
            subs = list(subrecords(payload))
            text = next((v for k, v in subs if k == 'BNAM'), None)
            if text is not None and re.search(r'playgroup|loopgroup', text.decode('cp1252', 'replace'), re.I):
                results.append(('dialogue result %s' % _cstr(next((v for k, v in subs if k == 'INAM'), b'')),
                                text.decode('cp1252', 'replace')))
        elif tag in OBJECT_KINDS or tag in ACTOR_KINDS:
            subs = list(subrecords(payload))
            rid = _cstr(next((v for k, v in subs if k == 'NAME'), b'')).lower()
            if not rid:
                continue
            kind[rid] = tag
            mo = next((v for k, v in subs if k == 'MODL'), None)
            model[rid] = _cstr(mo) if mo is not None else ''
            s = next((v for k, v in subs if k == 'SCRI'), None)
            if s is not None:
                script_of[rid] = _cstr(s).lower()
            else:
                script_of.pop(rid, None)
    attached = {}
    for rid, s in script_of.items():
        attached.setdefault(s, []).append(rid)
    objects, calls, actor_calls, unknown = {}, 0, 0, set()
    sources = [(name, text, sorted(attached.get(key, []))) for key, (name, text) in sorted(scripts.items())]
    sources += [(where, text, []) for where, text in results]      # a dialogue result's own object is the speaker
    for where, text, own in sources:
        for target, _, group in group_calls(text):
            calls += 1
            if target is None:
                ids = own
            elif target == 'player':
                ids = []
            else:
                ids = [target]
                if target not in kind:
                    unknown.add(target)
            if target == 'player' or (target is not None and kind.get(target) in ACTOR_KINDS):
                actor_calls += 1
            for rid in ids:
                if kind.get(rid) in OBJECT_KINDS:
                    objects.setdefault(rid, {}).setdefault(group, set()).add(where)
                elif target is None and kind.get(rid) in ACTOR_KINDS:
                    actor_calls += 1
    return {'objects': {rid: {g: sorted(w) for g, w in sorted(groups.items())} for rid, groups in sorted(objects.items())},
            'models': {rid: model.get(rid, '') for rid in objects}, 'calls': calls, 'actor_calls': actor_calls,
            'unknown_targets': sorted(unknown)}


def _blocks(data):
    """Every NiObject reachable from the NIF's roots, each once, parents before children."""
    seen, out = set(), []

    def walk(b):
        if b is None or id(b) in seen:
            return
        seen.add(id(b))
        out.append(b)
        for attr in ('extra_data', 'controller', 'next_controller', 'next_extra_data'):
            walk(getattr(b, attr, None))
        for p in getattr(b, 'properties', []) or []:
            walk(p)
        for ch in getattr(b, 'children', []) or []:
            walk(ch)
    for r in data.roots:
        walk(r)
    return out


def group_times(data, N):
    """{group: {'start', 'stop', 'loop start', 'loop stop'}} from a NIF's text keys (the first key of each name, as
    OpenMW mwrender/animation.cpp getTextKeyTime finds it), group names in lower case."""
    out = {}
    for b in _blocks(data):
        if not isinstance(b, N.NiTextKeyExtraData):
            continue
        for k in b.text_keys:
            text = k.value.decode('cp1252', 'replace') if isinstance(k.value, bytes) else str(k.value)
            for line in text.replace('\r', '\n').split('\n'):
                m = TEXT_KEY.match(line)
                if m:
                    out.setdefault(m.group(1).lower(), {}).setdefault(m.group(2).lower(), float(k.time))
    return {g: v for g, v in out.items() if 'start' in v and 'stop' in v}


def controller_time(c, t):
    """The controller's own time at animation time T (rule from OpenMW components/nifosg/controller.cpp
    ControllerFunction::calculate: frequency and phase, then cycle, reverse or constant past its range)."""
    time = float(c.frequency) * t + float(c.phase)
    start, stop = float(c.start_time), float(c.stop_time)
    if start <= time <= stop:
        return time
    mode = (int(c.flags) & 6) >> 1
    delta = stop - start
    if mode in (0, 1):
        if delta <= 0:
            return start
        cycles = (time - start) / delta
        remainder = (cycles - math.floor(cycles)) * delta
        if mode == 1 and int(abs(math.floor(cycles))) % 2:
            return stop - remainder
        return start + remainder
    return start if time < start else stop


def _slerp(a, b, s):
    import numpy as np
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        q = a + s * (b - a)
        return q / np.linalg.norm(q)
    th = math.acos(min(1.0, d))
    return (math.sin((1 - s) * th) * a + math.sin(s * th) * b) / math.sin(th)


def interp(keys, t, quaternion=False):
    """(value, between) of [(time, value)] keys at T: the first value before the first key, the last after the last
    (OpenMW components/nifosg/controller.cpp interpKey), else between two keys linearly (quaternions by slerp; BETWEEN
    is True then: the end poses this module makes fall on or after a group's last key, and the receipt counts any that
    do not)."""
    import numpy as np
    if t <= keys[0][0]:
        return keys[0][1], False
    if t >= keys[-1][0]:
        return keys[-1][1], False
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t0 <= t < t1:
            if t == t0 or t1 <= t0:
                return v0, False
            s = (t - t0) / (t1 - t0)
            if quaternion:
                return _slerp(v0, v1, s), True
            return np.asarray(v0, float) + s * (np.asarray(v1, float) - np.asarray(v0, float)), True
    return keys[-1][1], False


def quaternion_matrix(q):
    """The NIF rotation matrix of quaternion (w, x, y, z): the transpose of the column-vector rotation, as a NIF node
    stores its rotation (checked against every bind pose that equals its first key: the ice wall's chunks and the
    Clockwork City door's collision nodes)."""
    import numpy as np
    w, x, y, z = (float(v) for v in q)
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return r.T


def _axis_matrix(axis, angle):
    import numpy as np
    c, s = math.cos(angle), math.sin(angle)
    if axis == 0:
        r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == 1:
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else:
        r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return r


def _keyframe_pose(N, data_block, t, info):
    """(translation, rotation 3x3 or None, scale or None) of a NiKeyframeData at controller time T (each None where
    the data has no keys: the node keeps its own; OpenMW KeyframeController::getCurrentTransformation)."""
    import numpy as np
    d = data_block
    rot = None
    if d.rotation_type == 4:
        angles = []
        for axis in range(3):
            group = d.xyz_rotations[axis]
            keys = [(float(k.time), float(k.value)) for k in group.keys]
            value, between = interp(keys, t) if keys else (0.0, False)
            info['between'] += int(between)
            angles.append(float(value))
        if any(len(d.xyz_rotations[a].keys) for a in range(3)):
            # OpenMW getXYZRotation, axis order XYZ (the TES3 data carries no order): x, then y, then z; as a NIF
            # node matrix, the transpose of the column-vector product
            rot = (_axis_matrix(0, angles[0]) @ _axis_matrix(1, angles[1]) @ _axis_matrix(2, angles[2])).T
    elif d.num_rotation_keys:
        keys = [(float(k.time), (k.value.w, k.value.x, k.value.y, k.value.z)) for k in d.quaternion_keys]
        value, between = interp(keys, t, quaternion=True)
        info['between'] += int(between)
        rot = quaternion_matrix(value)
    trans = None
    if d.translations.num_keys:
        keys = [(float(k.time), (k.value.x, k.value.y, k.value.z)) for k in d.translations.keys]
        value, between = interp(keys, t)
        info['between'] += int(between)
        trans = np.asarray(value, float)
    scale = None
    if d.scales.num_keys:
        keys = [(float(k.time), float(k.value)) for k in d.scales.keys]
        value, between = interp(keys, t)
        info['between'] += int(between)
        scale = float(value)
    return trans, rot, scale


def set_rotation(node, rot):
    """A node's rotation matrix from a 3x3 (rows as Matrix33.as_list gives them). PyFFI names the fields m_11 .. m_33;
    an assignment to any other name would only add an attribute the file never writes, so the result is checked."""
    import numpy as np
    m = node.rotation
    m.m_11, m.m_12, m.m_13 = (float(v) for v in rot[0])
    m.m_21, m.m_22, m.m_23 = (float(v) for v in rot[1])
    m.m_31, m.m_32, m.m_33 = (float(v) for v in rot[2])
    if np.abs(np.array(m.as_list(), float) - np.asarray(rot, float)).max() > 1e-6:
        raise ValueError('The node rotation of %r did not take the pose' % node.name)


def _controllers(owner):
    c = getattr(owner, 'controller', None)
    while c is not None:
        yield c
        c = getattr(c, 'next_controller', None)


def _vis_at(c, t):
    """A NiVisController's value at controller time T (OpenMW components/nifosg/controller.cpp VisController::calculate:
    the last key at or before T, the first key's value before it)."""
    keys = list(c.data.keys) if c.data is not None else []
    if not keys:
        return True
    for i in range(1, len(keys)):
        if float(keys[i].time) > t:
            return bool(keys[i - 1].value)
    return bool(keys[-1].value)


def pose(data, N, t):
    """Put the NIF's nodes into the pose at animation time T, in place: every active keyframe controller's node gets
    its translation, rotation and scale at T, every active visibility controller's node is shown or hidden, a shape
    whose material's active alpha controller is at 0 is hidden and any other such material takes its alpha at T.
    Returns {'moved': [node names], 'shown': [...], 'hidden': [...], 'alpha': [...], 'between': keys interpolated,
    'unsupported': [controller kinds a group cannot carry here (morphs, paths, rolls)]}."""
    import numpy as np
    info = {'moved': [], 'shown': [], 'hidden': [], 'alpha': [], 'between': 0, 'unsupported': []}
    blocks = _blocks(data)
    for b in blocks:
        if not isinstance(b, N.NiAVObject):
            continue
        name = b.name.decode('cp1252', 'replace') if isinstance(b.name, bytes) else str(b.name)
        for c in _controllers(b):
            if not int(c.flags) & ACTIVE:
                continue
            kind = type(c).__name__
            ct = controller_time(c, t)
            if kind == 'NiKeyframeController' and c.data is not None:
                trans, rot, scale = _keyframe_pose(N, c.data, ct, info)
                moved = False
                if trans is not None:
                    now = np.array([b.translation.x, b.translation.y, b.translation.z], float)
                    if np.abs(now - trans).max() > TRANSLATION_EPS:
                        moved = True
                    b.translation.x, b.translation.y, b.translation.z = (float(v) for v in trans)
                if rot is not None:
                    now = np.array(b.rotation.as_list(), float)
                    if np.abs(now - rot).max() > ROTATION_EPS:
                        moved = True
                    set_rotation(b, rot)
                if scale is not None:
                    if abs(float(b.scale) - scale) > SCALE_EPS:
                        moved = True
                    b.scale = float(scale)
                if moved:
                    info['moved'].append(name)
            elif kind == 'NiVisController':
                visible = _vis_at(c, ct)
                was = not (int(b.flags) & HIDDEN)
                if visible != was:
                    info['shown' if visible else 'hidden'].append(name)
                b.flags = (int(b.flags) & ~HIDDEN) if visible else (int(b.flags) | HIDDEN)
            elif kind in ('NiGeomMorpherController', 'NiPathController', 'NiRollController'):
                info['unsupported'].append('%s on %s' % (kind, name))
    # a material's alpha controller (OpenMW AlphaController: the material's alpha is its keys' value at T)
    for b in blocks:
        if not isinstance(b, N.NiTriShape):
            continue
        name = b.name.decode('cp1252', 'replace') if isinstance(b.name, bytes) else str(b.name)
        for p in getattr(b, 'properties', []) or []:
            if not isinstance(p, N.NiMaterialProperty):
                continue
            for c in _controllers(p):
                if type(c).__name__ != 'NiAlphaController' or not int(c.flags) & ACTIVE or c.data is None:
                    continue
                keys = [(float(k.time), float(k.value)) for k in c.data.data.keys]
                if not keys:
                    continue
                value, between = interp(keys, controller_time(c, t))
                info['between'] += int(between)
                value = float(value)
                if value < ALPHA_OFF:
                    if not int(b.flags) & HIDDEN:
                        info['hidden'].append(name)
                    b.flags = int(b.flags) | HIDDEN
                elif abs(float(p.alpha) - value) > 1e-3:
                    info['alpha'].append(name)
                    p.alpha = value
    return info


def read_nif(raw, N):
    data = N.Data()
    data.read(io.BytesIO(raw))
    return data


def write_nif(data):
    stream = io.BytesIO()
    data.write(stream)
    return stream.getvalue()


def group_end(times, count=0):
    """(end key time, seconds) of a group played once plus COUNT loops: the stop key, and how long it plays (rule from
    OpenMW mwmechanics/character.cpp playGroup: a non-actor loops COUNT more times between its loop keys, else between
    start and stop)."""
    start, stop = times['start'], times['stop']
    loop = times.get('loop stop', stop) - times.get('loop start', start)
    return stop, max(0.0, stop - start) + max(0, int(count)) * max(0.0, loop)


def posed_nif(raw, N, group):
    """The model in the end pose of GROUP: (NIF bytes, info) or (None, info) when the pose leaves the model as its file
    has it (nothing moved, shown, hidden or faded) or the model has no such group. INFO: the group's times, what the
    pose changed (pose) and 'reason' when no NIF is made."""
    data = read_nif(raw, N)
    times = group_times(data, N)
    if group not in times:
        return None, {'reason': 'the model has no group %s' % group, 'groups': sorted(times)}
    end, seconds = group_end(times[group])
    info = pose(data, N, end)
    info.update(times=times[group], end=end, seconds=seconds)
    if not (info['moved'] or info['shown'] or info['hidden'] or info['alpha']):
        info['reason'] = 'its end pose is the model as placed'
        return None, info
    return write_nif(data), info


NOTHING_DRAWN = 'No supported visible static triangles'


def _points(result):
    """The vertex positions of a model_geometry result, None for no result."""
    import numpy as np
    from mwad.scene import unpack_geometry
    if result is None:
        return None
    vertices, faces, _ = unpack_geometry(result[0])
    return np.asarray(vertices, float)[:, :3], len(faces)


def converted(raw, N):
    """(drawn, collision) of a NIF as the converter reads it: the drawn points and face count (None when it draws
    nothing) and the collision rule's (source, points and face count or None) (tools/collision_source.py: None when the
    drawn triangles are the collision)."""
    from prepare_scenery import model_geometry
    from collision_source import model_collision
    try:
        drawn = _points(model_geometry(raw, N))
    except ValueError as exc:
        if str(exc) != NOTHING_DRAWN:
            raise
        drawn = None
    source, result, _ = model_collision(raw, N)
    return drawn, (source, _points(result))


def _same_points(a, b, tolerance):
    import numpy as np
    if a is None or b is None:
        return a is None and b is None
    return a[1] == b[1] and len(a[0]) == len(b[0]) and bool(np.allclose(a[0], b[0], atol=tolerance))


def pose_same(base_raw, posed_raw, N, tolerance=1e-3):
    """True when two NIFs draw the same triangles at the same places and collide the same (the converter's own reading:
    prepare_scenery.model_geometry and the collision rule): a pose that moves only nodes with nothing under them changes
    nothing; a pose that moves only a RootCollisionNode's shapes (a door's leaf drawn by one node, collided by another)
    changes the collision."""
    a_drawn, (a_source, a_collision) = converted(base_raw, N)
    b_drawn, (b_source, b_collision) = converted(posed_raw, N)
    return (_same_points(a_drawn, b_drawn, tolerance) and a_source == b_source
            and _same_points(a_collision, b_collision, tolerance))


# ---- the room conversion (tools/chim/interior.py build: the chim-interiors stage) ----

# The pose table the engine reads with a room (engine/aga/src/aw_objpose.c): <store>/poses.txt, a header line, then one
# row per placement and group a script plays:
#   R <room record> <reference> <group> <kind> <store model id> <seconds> <loop seconds> <box: 6 ints>
# reference: the placement's source number as the room record holds it; kind M: the end pose is the model named, B: the
# end pose is the model as placed (its own model and box: a lever's return, a door's close), H: the end pose draws
# nothing (model -1); seconds: the group played once (start to stop key); loop seconds: one more loop (loop start to
# loop stop, else start to stop); box: the drawn box of the placement with that model (the record's stored form).
POSE_TABLE = 'poses.txt'
POSE_HEADER = 'AWPG1'
POSE_ROWS_MAX = 192             # the engine's table (aw_objpose.c AW_POSE_ROWS): more rows refuse the stage
POSE_GROUP_CHARS = 11           # the longest group name the engine keeps (aw_objpose.c AW_POSE_GROUP)
POSE_ROOM_CHARS = 23            # the longest room record name (aw_objpose.c AW_POSE_ROOM; CHIM_ROOM_NAME_CHARS)
PSEUDO_BASE = 1                 # the posed placements' own numbers in their frame_input (only they are in it)


def _export_texture(material, bsa, textures):
    """The room export's texture index of a material (prepare_scenery.export_refs' lookup: textures/<path>, the .dds
    first), None for a material without a texture; KeyError when the room's export does not hold that texture."""
    from pathlib import PurePosixPath
    from mwad.audit import normpath
    path = material['texture_source']
    if not path:
        return None
    requested = normpath(path)
    if not requested.startswith('textures/'):
        requested = 'textures/' + requested
    candidates = [str(PurePosixPath(requested).with_suffix('.dds')), requested]
    texture = next((p for p in candidates if p in bsa.entries), None)
    for i, t in enumerate(textures):
        if texture is not None and t.get('source') == texture:
            return i
    raise KeyError('texture %s is not in the room export' % (texture or requested))


def posed_record(name, posed_path, size, collision, bsa, textures, put):
    """The room export's model record of a posed NIF (prepare_scenery.export_refs' record, the same reader:
    prepare_scenery._read_model on POSED_PATH): its geometry and collision written through PUT into the pose archive,
    its materials pointed at the room export's TEXTURES. ValueError when it draws nothing."""
    import hashlib
    from prepare_scenery import _read_model, _flames, nif_reader, source_collision_metadata
    from exterior_visibility import source_visibility_issues
    from collision_source import AVOID_LABEL
    from mwad.scene import unpack_geometry
    _, raw, result, collision_result, error = _read_model((name, posed_path, {'offset': 0, 'bytes': size}, collision))
    if error is not None:
        raise ValueError(error)
    (packet, materials, bounds, skipped), flames = result
    collision_record = None
    if collision_result is not None:
        cpacket, cmaterials, cbounds, cskipped = collision_result
        cv, cf, _ = unpack_geometry(cpacket)
        authored = any(m['source_visibility']['collision_node'] for m in cmaterials)
        collision_record = {'source': 'NIF RootCollisionNode' if authored else AVOID_LABEL, 'bounds': cbounds,
                            'vertices': len(cv), 'triangles': len(cf), 'skipped_shapes': cskipped, **put(cpacket)}
    refs = []
    for material in materials:
        material['texture_index'] = _export_texture(material, bsa, textures)
        if material['texture_index'] is not None:
            refs.append(material['texture_index'])
    v, f, _ = unpack_geometry(packet)
    return {'source': name, 'source_sha256': hashlib.sha256(raw).hexdigest(), 'vertices': len(v), 'triangles': len(f),
            'bounds': bounds, 'materials': materials, 'textures': sorted(set(refs)), 'collision': collision_record,
            'source_collision': source_collision_metadata(raw, nif_reader()),
            'source_visibility_issues': source_visibility_issues(materials), 'exterior_visibility': None,
            'skipped_shapes': skipped, 'flames': _flames(flames), **put(packet)}


def room_poses(*, work, index, archive, selected, models, profiles, spec, objects, data_files, pose_dir, frame_args):
    """The end poses of one room's scripted placements (room_input calls it once its own frame input is made): (rows,
    pose spec) or (None, None) when no placement of the room is in OBJECTS (scripted_groups' 'objects').

    rows: one per (placement, group) a script plays: {'ref', 'group', 'kind', 'seconds', 'loop', ...}; kind 'model' (the
    end pose is a model of its own: 'pseudo', its placement in the pose spec), 'base' (the end pose is the model as
    placed), 'hide' (the end pose draws nothing) or 'failed' ('reason': the placement keeps its model; a pose never
    fails the room). The pose spec is a frame input (chim.build.frame_input, the room's own settings) of the posed
    models alone, each placed where its placement stands: its variants are the store models the stage adds."""
    import hashlib
    import shutil
    from pathlib import Path
    from chim.build import frame_input, mesh_fingerprint, mesh_result_keys, mesh_unit
    from chim.cut import source_ref
    from collision_source import export_collision
    from collision_source_env import collision_source_mode
    from model_method2 import run_mesh_units, unit_kind
    from mwad.archives import layered_bsa
    from mwad.esm import read_bsa_asset
    from prepare_scenery import nif_reader
    wanted = [(r, objects[str(r.get('id', '')).lower()]) for r in selected
              if str(r.get('id', '')).lower() in objects]
    if not wanted:
        return None, None
    room = Path(work).name
    placed = {}
    for p in spec['placements']:
        placed.setdefault(source_ref(p['ref']), []).append(p)
    bsa = layered_bsa(Path(data_files))
    N = nif_reader()
    export_profiles = {n: pr for group in index.get('groups', {}).values()
                       for n, pr in group.get('visual_profiles', {}).items()}
    rule = collision_source_mode()
    pose_dir = Path(pose_dir) / room
    pose_dir.mkdir(parents=True, exist_ok=True)
    pose_archive = pose_dir / 'scenery-poses.mwpak'
    shutil.copyfile(archive, pose_archive)
    stream = pose_archive.open('r+b')
    stream.seek(0, 2)

    def put(raw):
        pad = (-stream.tell()) % 512
        stream.write(bytes(pad))
        offset = stream.tell()
        stream.write(raw)
        return {'offset': offset, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    rows, poses, pose_models, pseudo = [], {}, [], []
    try:
        for ref, groups in wanted:
            base = models[ref['model_index']]
            name = base['source']
            for group in groups:
                row = {'ref': int(ref['number']), 'group': group, 'id': str(ref.get('id', '')), 'model': name}
                rows.append(row)
                if len(placed.get(int(ref['number']), [])) != 1:
                    row.update(kind='failed', reason='%d placements of the reference in the record (a cut model)'
                               % len(placed.get(int(ref['number']), [])))
                    continue
                if len(group) > POSE_GROUP_CHARS:
                    row.update(kind='failed', reason='group name longer than %d characters' % POSE_GROUP_CHARS)
                    continue
                key = (name, group)
                if key not in poses:
                    poses[key] = _pose_model(name, group, bsa, N, pose_dir, export_profiles, rule, index, put,
                                             export_collision, read_bsa_asset)
                found = poses[key]
                row.update({k: found[k] for k in ('kind', 'seconds', 'loop', 'reason', 'moved', 'hidden',
                                                  'between') if k in found})
                if found['kind'] != 'model':
                    continue
                if 'model_index' not in found:
                    found['model_index'] = len(models) + len(pose_models)
                    record = dict(found['record'], _profile=base.get('_profile', profiles.get(name)))
                    pose_models.append(record)
                row['pseudo'] = len(pseudo)
                pseudo.append(dict(ref, number=PSEUDO_BASE + len(pseudo), model_index=found['model_index']))
    finally:
        stream.close()
    if not pseudo:
        return rows, None
    every = list(models) + pose_models
    items = []
    for k, record in enumerate(pose_models):
        mi = len(models) + k
        profile = record['_profile']
        items.append((mesh_fingerprint(record, profile, index['textures'], unit_kind(profile)),
                      (mi, record, profile, pose_archive, index['textures'])))
    used = [len(models) + k for k in range(len(pose_models))]
    prepared = dict(zip(used, run_mesh_units(items, mesh_unit, frame_args['jobs'], frame_args['cache'])))
    mesh_fps = mesh_result_keys(items, prepared, used)
    pose_spec = frame_input(models=every, references=pseudo, prepared=prepared, profiles=profiles, mesh_fps=mesh_fps,
                            texture_records=index['textures'], archive=pose_archive, heights=None, materials=None,
                            floor=0.0, ceiling=0.0, ground_textures={}, mesh_occluders=False, terrain_on=False,
                            **frame_args)
    by_number = {p['ref']: k for k, p in enumerate(pose_spec['placements'])}
    for row in rows:
        if 'pseudo' in row:
            k = by_number.get(PSEUDO_BASE + row['pseudo'])
            if k is None:
                row.update(kind='failed', reason='the posed model was not placed (cut or left out by the frame input)')
                row.pop('pseudo')
            else:
                row['pseudo'] = k
    return rows, pose_spec


def _pose_model(name, group, bsa, N, pose_dir, export_profiles, rule, index, put, export_collision, read_bsa_asset):
    """One (model, group)'s end pose for room_poses: {'kind', 'seconds', 'loop', 'record' for kind 'model', ...}."""
    from pathlib import Path
    out = {'kind': 'failed'}
    try:
        raw = read_bsa_asset(bsa, name)
        data = read_nif(raw, N)
        times = group_times(data, N)
        if group not in times:
            out['reason'] = 'the model has no group %s' % group
            return out
        end, seconds = group_end(times[group])
        _, one_more = group_end(times[group], 1)
        out.update(seconds=round(seconds, 4), loop=round(one_more - seconds, 4))
        posed, info = posed_nif(raw, N, group)
        out.update(moved=len(info.get('moved', [])), hidden=len(info.get('hidden', [])), between=info.get('between', 0))
        if posed is None or pose_same(raw, posed, N):
            out['kind'] = 'base'
            return out
        drawn, _ = converted(posed, N)
        if drawn is None:
            out['kind'] = 'hide'
            return out
        path = Path(pose_dir) / ('%s@%s.nif' % (Path(name).stem, group))
        path.write_bytes(posed)
        collision = export_collision(export_profiles.get(name, {}).get('collision_source'), rule)
        out['record'] = posed_record(name, str(path), len(posed), collision, bsa, index['textures'], put)
        out['kind'] = 'model'
    except (ValueError, KeyError, OSError) as exc:
        out.update(kind='failed', reason='%s: %s' % (type(exc).__name__, exc))
    return out


def store_poses(store, out, pending, rows, record_parts):
    """The stage's last step before the store is written (interior.build): every room's end-pose models stored AFTER
    all the rooms' own models (so every other record and model id stays byte-identical), appended to that room's model
    list (its record written again), and the pose table OUT/<store>/poses.txt. PENDING: [(record name, room input)]
    of the rooms with poses; ROWS: the receipt's rooms rows by record name; RECORD_PARTS: {record name: (bounds, ids,
    records, {reference: (model id, origin, angles, box)})} from Store.add_room. Returns the receipt's 'poses' part."""
    from pathlib import Path
    from chim import placed as P
    from chim.interior import STORE, room_record
    from chim.world import stored_box
    import hashlib
    table, summary, added = [], {}, {}
    # the end-pose models in packs of their own, after every room's own models and packs (the rooms' packs as without
    # end poses; fit_poses can take a model out again without touching them)
    store.close_pack()
    first_model, first_pack = len(store.model_records), len(store.packs)
    for name, room in pending:
        bounds, ids, records, by_ref = record_parts[name]
        spec = room.get('pose_spec')
        extra = []
        kept = []
        for row in room['poses']:
            base = by_ref.get(row['ref'])
            if base is None and row['kind'] != 'failed':
                row.update(kind='failed', reason='the reference has no single placement in the record')
            if row['kind'] == 'failed':
                kept.append(row)
                continue
            mid, origin, angles, box = base
            if row['kind'] == 'model':
                p = spec['placements'][row['pseudo']]
                v = spec['variants'][p['variant']]
                mid = store.model_id(v, spec['textures'])
                box = stored_box(*P.placed_box(origin, angles, v['lo'], v['hi']))
                if mid not in ids and mid not in extra:
                    extra.append(mid)
                added[mid] = len(store.model_records[mid][1])
            elif row['kind'] == 'hide':
                mid = -1
            row['store_model'] = mid
            table.append((name, row['ref'], row['group'], KIND_LETTER[row['kind']], mid, row['seconds'], row['loop'],
                          box))
            kept.append(row)
        if extra:
            data = room_record(bounds, ids + extra, records)
            (Path(out) / STORE / 'rooms' / (name + '.crm')).write_bytes(data)
            if name in rows:
                rows[name]['models'] = len(ids) + len(extra)
                rows[name]['record_bytes'] = len(data)
                rows[name]['record_sha256'] = hashlib.sha256(data).hexdigest()
        summary[name] = [{k: r[k] for k in ('ref', 'id', 'group', 'kind', 'store_model', 'seconds', 'reason')
                          if k in r} for r in kept]
        if name in rows:
            rows[name]['poses'] = len([r for r in kept if r['kind'] != 'failed'])
            rows[name]['pose_models'] = extra
    if len(table) > POSE_ROWS_MAX:
        raise ValueError('CHIM rooms: %d pose rows, the engine keeps %d (its object poses table, AW_POSE_ROWS)'
                         % (len(table), POSE_ROWS_MAX))
    write_pose_table(Path(out) / STORE / POSE_TABLE, table)
    failed = [dict(room=n, **{k: r[k] for k in ('ref', 'id', 'group', 'reason') if k in r})
              for n, rs in summary.items() for r in rs if r['kind'] == 'failed']
    return {'rule': 'a script\'s PlayGroup or LoopGroup on a placed object: the room holds the model of the group\'s end '
                    'pose, the engine swaps it in when the group has played (MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68)',
            'table': POSE_TABLE, 'rows': len(table), 'rooms': summary, 'models_added': len(added),
            'model_bytes_added': sum(added.values()), 'failed': failed,
            'first_model': first_model, 'first_pack': first_pack}


KIND_LETTER = {'model': 'M', 'base': 'B', 'hide': 'H'}


def write_pose_table(path, table):
    """OUT/<store>/poses.txt (POSE_TABLE's form), rows sorted (room, reference, group)."""
    lines = [POSE_HEADER]
    for room, ref, group, kind, mid, seconds, loop, box in sorted(table, key=lambda t: (t[0], t[1], t[2])):
        lo, hi = box
        if len(room) > POSE_ROOM_CHARS:
            raise ValueError('CHIM rooms: room record name %r longer than %d characters (the pose table)'
                             % (room, POSE_ROOM_CHARS))
        lines.append('R %s %d %s %s %d %.4f %.4f %d %d %d %d %d %d' % (room, ref, group, kind, mid, seconds, loop,
                                                                       *lo, *hi))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')


def read_pose_table(path):
    """The rows of a pose table: [(room, reference, group, kind, model, seconds, loop, (lo, hi))]."""
    rows = []
    text = path.read_text(encoding='ascii').splitlines()
    if not text or text[0] != POSE_HEADER:
        raise ValueError('%s: not a pose table (%s)' % (path, POSE_HEADER))
    for line in text[1:]:
        w = line.split()
        if len(w) != 14 or w[0] != 'R' or w[4] not in ('M', 'B', 'H'):
            raise ValueError('%s: bad row %r' % (path, line))
        b = [int(x) for x in w[8:14]]
        rows.append((w[1], int(w[2]), w[3], w[4], int(w[5]), float(w[6]), float(w[7]),
                     (tuple(b[:3]), tuple(b[3:]))))
    return rows


def record_models(data, drop=(), mapping=None):
    """A room record's bytes with the store models DROP taken out of its model list and the ids of MAPPING renumbered
    (the end-pose models: no placement names them), everything else as it was."""
    import struct
    from chim import format as F
    from chim import placed as P
    from chim.interior import room_record
    from chim.room_records import ROOM_BLOCK, ROOM_KIND
    mapping = mapping or {}
    head = F.read_header(data, ROOM_KIND)
    v = ROOM_BLOCK.unpack_from(data, F.HEADER.size)
    models = [mapping.get(m, m) for m in struct.unpack_from('>%dI' % v[6], data, head['directory']) if m not in drop]
    at = head['data']
    records = [data[at + i * P.PLACEMENT.size:at + (i + 1) * P.PLACEMENT.size] for i in range(head['count'])]
    return room_record((v[0:3], v[3:6]), models, records)


def fit_poses(store, out, sdk, jobs, rows, poses, first_model, first_pack):
    """The stage's fit of the end poses, right after the store is written (interior.build): the rooms holding end-pose
    models measured as the early room heap check measures them (chim.heap.room_store_heap); a room the 32 MB minimum
    cannot hold with them keeps its record as before (its end-pose models out of its list, its rows of the kind M
    gone). End-pose models no room keeps are taken out of the store, the others renumbered after every room's own
    (FIRST_MODEL on; they are homed in the packs from FIRST_PACK on, store_poses), so the image carries no model nobody
    loads; the store is written again. Without an SDK nothing is measured (the image's room heap gate stays the check
    of record). Returns the receipt's 'fit' part."""
    import hashlib
    from pathlib import Path
    from chim.interior import STORE
    holding = sorted(n for n, r in rows.items() if r.get('pose_models'))
    result = {'measured': holding, 'left_out': {}, 'models_dropped': []}
    if not holding or sdk is None:
        result['status'] = 'not measured: %s' % ('no end-pose models' if not holding else 'no Amiga SDK given (--sdk)')
        return result
    from chim.heap import room_store_heap, room_failure_text
    from check_world_map_heap import compile_target_sizes
    reports = room_store_heap(out, compile_target_sizes(sdk)[0], rooms=holding, jobs=jobs)
    failed = sorted(n for n, r in reports.items() if not r['ok'])
    result['status'] = 'measured'
    if not failed:
        return result
    for name in failed:
        result['left_out'][name] = room_failure_text('end-pose models left out (the room stays as before)',
                                                     reports[name])
    kept_by = set()
    for name in holding:
        if name not in failed:
            kept_by.update(rows[name]['pose_models'])
    drop = {m for name in failed for m in rows[name]['pose_models'] if m not in kept_by and m >= first_model}
    keep = [m for m in range(first_model, len(store.model_records)) if m not in drop]
    mapping = {old: first_model + i for i, old in enumerate(keep)}
    result['models_dropped'] = sorted(drop)
    _store_drop_tail(store, first_model, first_pack, mapping)
    table = read_pose_table(Path(out) / STORE / POSE_TABLE)
    new_table = []
    for room, ref, group, kind, mid, seconds, loop, box in table:
        if room in failed and kind == 'M':
            continue
        new_table.append((room, ref, group, kind, mapping.get(mid, mid) if mid >= first_model else mid, seconds,
                          loop, box))
    write_pose_table(Path(out) / STORE / POSE_TABLE, new_table)
    poses['rows'] = len(new_table)
    for name in holding:
        path = Path(out) / STORE / 'rooms' / (name + '.crm')
        gone = set(rows[name]['pose_models']) if name in failed else set()
        data = record_models(path.read_bytes(), drop=gone, mapping=mapping)
        path.write_bytes(data)
        rows[name]['record_bytes'] = len(data)
        rows[name]['record_sha256'] = hashlib.sha256(data).hexdigest()
        rows[name]['models'] -= len(gone)
        rows[name]['pose_models'] = [] if name in failed else [mapping.get(m, m) for m in rows[name]['pose_models']]
        for r in poses.get('rooms', {}).get(name, []):
            if name in failed and r.get('kind') == 'model':
                r.update(kind='left out', reason='the room does not fit the 32 MB minimum with its end-pose models')
            elif r.get('store_model', -1) >= first_model:
                r['store_model'] = mapping.get(r['store_model'], r['store_model'])
    poses['models_added'] = len(keep)
    poses['model_bytes_added'] = sum(len(store.model_records[m][1]) for m in range(first_model,
                                                                                    len(store.model_records)))
    return result


def _store_drop_tail(store, first_model, first_pack, mapping):
    """The store's end-pose models (ids from FIRST_MODEL on, homed in the packs from FIRST_PACK on) kept by MAPPING
    (old id: new id) and renumbered; the others gone. The packs before FIRST_PACK and every id below FIRST_MODEL stay as
    they are (interior.Store's own fields)."""
    tail = store.packs[first_pack:]
    store.packs = store.packs[:first_pack]
    records = store.model_records[first_model:]
    store.model_records = store.model_records[:first_model] + [None] * len(mapping)
    for old, new in mapping.items():
        store.model_records[new] = records[old - first_model]
    store.model_content = {d: (mapping[m] if m >= first_model else m) for d, m in store.model_content.items()
                           if m < first_model or m in mapping}
    names = {d for d in store.model_content}
    store.model_names = {n: d for n, d in store.model_names.items() if d in names}
    store.home = {k: v for k, v in store.home.items() if v < first_pack}
    store.current, store.current_bytes = [], 0
    for entries in tail:
        for kind, rid, data in entries:
            if kind == b'MODL' and rid >= first_model:
                if rid not in mapping:
                    continue
                rid = mapping[rid]
            store._homed(kind, rid, data)
    store.close_pack()
