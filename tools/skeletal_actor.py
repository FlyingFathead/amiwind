# SPDX-License-Identifier: GPL-3.0-only
"""Shared animation tables (docs/MODULAR_NPCS.md, "Runtime method C"): the builder side.

Every humanoid in the game moves by one skeleton and one animation table (meshes/base_anim.nif and its keyframes).
Instead of baking each actor's motions into its own vertex frames, the builder writes:

- the animation table of a skeleton, once: its bones (parent first), and per bone its local transform sampled at a
  fixed rate over the animation groups the game uses, rotations as 16-bit quaternions and positions as 16-bit values
  on one scale; the groups by their text keys (start and stop frames);
- each actor part in its bones' rest space: per vertex the bone it hangs on (a rigid part: its attachment bone; a
  skinned part: the bone with the largest weight) and, at joints, a second bone and its weight.

The engine poses the bones from the table (one matrix per bone, parent first) and transforms each vertex by its
bone's matrix, as the alias renderer already transforms each vertex by the model's matrix. Matrices use row vectors,
as the NIF reader and tools/npc_geometry.py do: a point p in bone space is p @ M.

    pose_matrices(parents, locals_) -> world matrices of one sampled frame
    sample_table(skeleton, bones, times) -> local transforms [frame][bone] as (quaternion wxyz, position)
    quantise_table(rotations, positions) -> int16 arrays and the position scale; dequantise_table() back
    bind_skinned(vertices, weights_by_bone, inverse_binds, blend_min) -> bone, second bone, weight, rest positions
    skin(rest, bones, second, weight, world) -> posed vertices (the engine's arithmetic, for the tests)
    skeletal_model(assets, appearance, skeleton, palette, table, bone_names) -> one appearance's skeletal model: the
        resident bake's reduction and atlas, one rest frame, the "AWSB" block (skeletal_from_shapes does the work)
    read_table, read_skeletal, engine_pose -> the table and a model read back and posed as the engine does
"""
import numpy as np

# A joint vertex keeps a second bone when that bone carries at least this weight (25 October 2026: 7.7 % of the base
# game's skinned vertices have a second bone at 0.05, 6.8 % at 0.20). Below it the vertex follows its main bone alone.
BLEND_MIN = 0.20
# Frames per second of the sampled table: the engine interpolates between frames (nlerp of the quaternions). 8, not
# 15 (SKEL-TABLE-SIZE-52; the maintainer, 25 October 2026: it is fine to cut animation frames if it saves the rest;
# every animation must work, none needs a high frame rate or flawless motion).
TABLE_RATE = 8.0
QUAT_SCALE = 32767.0


def quat_to_matrix(q):
    """3 x 3 row-vector rotation of a unit quaternion (w, x, y, z): p @ R rotates p (npc_geometry.quat_matrix)."""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y)],
        [2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x)],
        [2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)]])


def matrix_to_quat(m):
    """Unit quaternion (w, x, y, z), w >= 0, of a 3 x 3 row-vector rotation (the inverse of quat_to_matrix)."""
    r = np.asarray(m, float).T            # column-vector form
    t = np.trace(r)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        q = [0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s]
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
        q = [(r[2, 1] - r[1, 2]) / s, 0.25 * s, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s]
    elif r[1, 1] > r[2, 2]:
        s = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
        q = [(r[0, 2] - r[2, 0]) / s, (r[0, 1] + r[1, 0]) / s, 0.25 * s, (r[1, 2] + r[2, 1]) / s]
    else:
        s = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
        q = [(r[1, 0] - r[0, 1]) / s, (r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, 0.25 * s]
    q = np.array(q) / np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def local_matrix(q, position):
    """4 x 4 row-vector transform of a bone: rotation q, then translation."""
    m = np.eye(4)
    m[:3, :3] = quat_to_matrix(q)
    m[3, :3] = position
    return m


def pose_matrices(parents, locals_):
    """World matrices of one frame: bone i's world = local i @ world of its parent (parents[i] < i, or -1)."""
    world = []
    for i, p in enumerate(parents):
        if p >= i:
            raise ValueError('Bone %d has its parent %d after it: bones must be parent first' % (i, p))
        world.append(locals_[i] if p < 0 else locals_[i] @ world[p])
    return world


def bone_order(parents_by_name, wanted):
    """The bones a table needs, parent first: every wanted bone and its ancestors, in a stable order."""
    order, seen = [], set()

    def add(name):
        if name in seen:
            return
        parent = parents_by_name[name]
        if parent is not None:
            add(parent)
        seen.add(name)
        order.append(name)
    for name in wanted:
        add(name)
    return order


def sample_table(skeleton, bones, times):
    """[frame][bone] (quaternion wxyz, position) of the bones' local transforms at the given times.
    skeleton.local(name, time) gives the 4 x 4 row-vector local transform (npc_geometry.Skeleton). A bone with scale
    other than 1 is refused (the base game's humanoid bones have none: the table holds rotation and position)."""
    rotations = np.zeros((len(times), len(bones), 4))
    positions = np.zeros((len(times), len(bones), 3))
    for fi, t in enumerate(times):
        for bi, name in enumerate(bones):
            m = np.asarray(skeleton.local(name, float(t)), float)
            scale = np.linalg.norm(m[:3, :3], axis=1)
            if np.any(np.abs(scale - 1) > 1e-3):
                raise ValueError('Bone %s is scaled (%s) at %.3f s: the table holds no scale' % (name, scale, t))
            q = matrix_to_quat(m[:3, :3])
            if fi and np.dot(q, rotations[fi - 1, bi]) < 0:
                q = -q                    # the shorter way from the previous frame, so the engine's nlerp never flips
            rotations[fi, bi] = q
            positions[fi, bi] = m[3, :3]
    return rotations, positions


def quantise_table(rotations, positions):
    """int16 rotations (q x 32767) and int16 positions on one scale (units per step), and that scale."""
    reach = float(np.max(np.abs(positions))) if positions.size else 0.0
    scale = reach / 32767.0 if reach > 0 else 1.0
    q = np.clip(np.round(rotations * QUAT_SCALE), -32767, 32767).astype(np.int16)
    p = np.clip(np.round(positions / scale), -32767, 32767).astype(np.int16)
    return q, p, scale


def stored_quats(q):
    """The quaternions as the table stores them (three parts, w >= 0) and the engine rebuilds them: the sign turned
    so that w >= 0 (q and -q are one rotation), then w from x, y and z. Float, on the int16 scale."""
    q = np.asarray(q).astype(float)
    q = np.where(q[..., :1] < 0, -q, q)
    q[..., 0] = np.sqrt(np.maximum(0.0, QUAT_SCALE * QUAT_SCALE - np.sum(q[..., 1:] ** 2, axis=-1)))
    return q


def dequantise_table(q, p, scale):
    """Rotations as the engine reads them (stored_quats, normalised) and positions in units."""
    rotations = stored_quats(q) / QUAT_SCALE
    rotations /= np.linalg.norm(rotations, axis=-1, keepdims=True)
    return rotations, p.astype(float) * scale


def nlerp(a, b, u):
    """The engine's blend of two table quaternions (AW_SkelPose): b turned to a's side (the stored w >= 0 can put
    neighbouring frames on opposite sides), the normalised lerp."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.dot(a, b) < 0:
        b = -b
    q = a * (1 - u) + b * u
    return q / np.linalg.norm(q)


def bind_skinned(vertices, weights_by_bone, inverse_binds, blend_min=BLEND_MIN):
    """A skinned shape in its bones' rest space.
    vertices: (n, 3) in the shape's own space; weights_by_bone: {bone index: (vertex ids, weights)}; inverse_binds:
    {bone index: 4 x 4 row-vector inverse bind (shape space to bone space)}.
    Returns (bone, second, weight, rest, rest2): per vertex its main bone, its second bone (-1 none), the second's
    weight (renormalised over the two), and its position in each bone's space (rest2 zero without a second)."""
    n = len(vertices)
    table = np.zeros((n, max(weights_by_bone) + 1 if weights_by_bone else 1))
    for b, (ids, w) in weights_by_bone.items():
        table[np.asarray(ids, int), b] += np.asarray(w, float)
    if np.any(table.sum(axis=1) <= 0):
        raise ValueError('A skinned vertex has no bone')
    order = np.argsort(-table, axis=1)
    bone = order[:, 0]
    second = np.where(table[np.arange(n), order[:, 1]] >= blend_min, order[:, 1], -1) if table.shape[1] > 1 \
        else np.full(n, -1)
    w1 = table[np.arange(n), bone]
    w2 = np.where(second >= 0, table[np.arange(n), np.maximum(second, 0)], 0.0)
    weight = w2 / (w1 + w2)
    hom = np.column_stack((np.asarray(vertices, float), np.ones(n)))
    rest = np.zeros((n, 3))
    rest2 = np.zeros((n, 3))
    for v in range(n):
        rest[v] = (hom[v] @ inverse_binds[bone[v]])[:3]
        if second[v] >= 0:
            rest2[v] = (hom[v] @ inverse_binds[second[v]])[:3]
    return bone, second, weight, rest, rest2


def skin(rest, bones, second, weight, world, rest2=None):
    """The posed vertices: each by its bone's world matrix; a joint vertex blends its two bones' results."""
    rest = np.asarray(rest, float)
    out = np.zeros_like(rest)
    for v in range(len(rest)):
        a = np.append(rest[v], 1.0) @ world[bones[v]]
        if second[v] >= 0:
            b = np.append(rest2[v], 1.0) @ world[second[v]]
            a = (1 - weight[v]) * a + weight[v] * b
        out[v] = a[:3]
    return out


def export_actor(assets, appearance, skeleton):
    """One appearance's parts in bone space, read as npc_geometry.assemble reads them (same nodes, filters,
    attachments, mirroring and materials), but not posed: per shape its vertices' bones (names), joint blends and
    rest positions. The weight/height scale and the * 0.25 map scale are the model's, applied with its matrix.
    Returns [{'name', 'part', 'bones': [names], 'bone', 'second', 'weight', 'rest', 'rest2', 'faces', 'uv',
    'texture'}]."""
    import io
    from mwad.audit import normpath
    from npc_geometry import rigid_attachment, root_local, check_root_rule, _root_rule
    N = skeleton.N
    out = []
    for part in appearance['parts']:
        data = N.Data()
        data.read(io.BytesIO(assets.read(normpath('meshes/' + part['mesh']))))
        nodes = []

        def walk(node, parent, hidden=False, root=False, rule='morrowind'):
            if not isinstance(node, N.NiAVObject):
                return
            if isinstance(node, N.NiNode) and node.name.lower() == b'rootcollisionnode':
                return
            local = np.array(node.get_transform().as_list())
            if root:
                local = root_local(local, rule)
            transform = local @ parent
            hidden = hidden or bool(node.flags & 1)
            nodes.append((node, transform, hidden))
            for child in getattr(node, 'children', []):
                if child:
                    walk(child, transform, hidden)
        rule = check_root_rule(appearance.get('root_rule') or _root_rule)
        for root in data.roots:
            walk(root, np.eye(4), root=True, rule=rule)
        rig = any(isinstance(n, N.NiTriShape) and n.skin_instance for n, _, _ in nodes)
        offset = next((np.array(n.translation.as_list()) for n, _, _ in nodes if n.name.lower() == b'boneoffset'),
                      np.zeros(3))
        for node, transform, hidden in nodes:
            if hidden or not isinstance(node, N.NiTriShape) or not node.data:
                continue
            name = node.name.decode('cp1252')
            if rig and (not node.skin_instance or
                        not name.casefold().removeprefix('tri ').startswith(part['filter'].casefold())):
                continue
            g = node.data
            if not g.num_triangles:
                continue
            vertices = np.array([v.as_list() for v in g.vertices])
            faces = np.array(g.get_triangles(), int)
            if node.skin_instance:
                sk = node.skin_instance
                names = [b.name.decode('cp1252').casefold() for b in sk.bones]
                weights, inverse = {}, {}
                for i, info in enumerate(sk.data.bone_list):
                    ids = [w.index for w in info.vertex_weights]
                    ws = [w.weight for w in info.vertex_weights]
                    if ids and any(ws):
                        weights[i] = (ids, ws)
                    inverse[i] = np.array(info.get_transform().as_list())
                bone, second, weight, rest, rest2 = bind_skinned(vertices, weights, inverse)
            else:
                mirror = rigid_attachment(part, offset)
                if part['attach'].startswith('Left') and not part.get('carried_light'):
                    faces = faces[:, [0, 2, 1]]
                hom = np.column_stack((vertices, np.ones(len(vertices))))
                names = [part['attach'].casefold()]
                bone = np.zeros(len(vertices), int)
                second = np.full(len(vertices), -1)
                weight = np.zeros(len(vertices))
                rest = (hom @ transform @ mirror)[:, :3]
                rest2 = np.zeros_like(rest)
            uv = np.array([[u.u, u.v] for u in g.uv_sets[0]]) if g.num_uv_sets else np.zeros((len(vertices), 2))
            texture = None
            for prop in node.properties:
                if isinstance(prop, N.NiTexturingProperty) and prop.has_base_texture and prop.base_texture.source:
                    texture = normpath(prop.base_texture.source.file_name.decode('cp1252'))
            out.append({'name': name, 'part': part['slot'], 'bones': names, 'bone': bone, 'second': second,
                        'weight': weight, 'rest': rest, 'rest2': rest2, 'faces': faces, 'uv': uv,
                        'texture': texture})
    return out


def posed_shape(shape, world_by_name):
    """A shape of export_actor posed by a skeleton pose (name -> 4 x 4 world matrix, npc_geometry.Skeleton.pose)."""
    world = [np.asarray(world_by_name(n)) for n in shape['bones']]
    return skin(shape['rest'], shape['bone'], shape['second'], shape['weight'], world, shape['rest2'])


TABLE_MAGIC = b'AWSK'
TABLE_VERSION = 2
TABLE_NAME = 24                 # engine aw_skel.h AW_SKEL_NAME
KEY_TEXT = 32                   # AW_SKEL_KEY_TEXT ('slash large follow start' is 24)
BLOCK_VERSION = 1               # engine aw_skel.h AW_SKEL_BLOCK_VERSION
# What a bone stores per frame (engine aw_skel.h AW_SKEL_STILL ...; SKEL-TABLE-SIZE-52: of the base game's 61
# humanoid nodes 27 never move and 23 only turn): nothing, its rotation, or its rotation and position.
STILL, TURNS, MOVES = 0, 1, 2


# A bone whose position moves less than this over the whole table (skeleton units: a quarter of it in the game) is
# stored without positions, at the middle of its range: of the stick figure's 10 moving bones the neck, the
# clavicles and a thumb joint move under one unit (25 October 2026).
POSITION_TOLERANCE = 1.0


def bone_kinds(q, p, steps=0):
    """Per bone STILL, TURNS or MOVES, from the stored keys (three-part quaternions with w >= 0, positions); a bone
    whose positions span at most `steps` on every axis does not move."""
    s = np.where(q[..., :1] < 0, -q, q)[..., 1:]
    kinds = []
    for b in range(q.shape[1]):
        turns = bool(np.any(s[:, b] != s[0, b]))
        span = p[:, b].astype(int).max(axis=0) - p[:, b].astype(int).min(axis=0)
        moves = bool(np.any(span > steps))
        kinds.append(MOVES if moves else TURNS if turns else STILL)
    return kinds


NO_GROUP = 0xFFFF


def write_table(parents, groups, q, p, scale, rate=TABLE_RATE, tolerance=0.0, keys=()):
    """The table the engine reads (engine/aga/src/aw_skel.h), big-endian: header (its count of text keys in the last
    u16), parents, each bone's kind (STILL, TURNS, MOVES), groups {name: (first frame, last frame)}, the text keys
    [(text, group index, frame)] (text_keys: a group's phases such as 'self release' or 'chop hit', and the sound
    events), every bone's first-frame key (i16 x y z of its quaternion with w >= 0, i16 x y z position), then per
    frame the keys of the bones that change: i16 x y z of the quaternion, and the position too for a bone that MOVES.
    tolerance (units): a bone whose position spans no more is stored at the middle of its range, without positions
    (POSITION_TOLERANCE)."""
    import struct
    frames, bones = q.shape[0], q.shape[1]
    if p.shape[:2] != (frames, bones) or len(parents) != bones or not 1 <= bones <= 64:
        raise ValueError('Table shape mismatch')
    if any(not -1 <= parent < i for i, parent in enumerate(parents)):
        raise ValueError('Every parent must come before its child')
    kinds = bone_kinds(q, p, int(tolerance / scale))
    p = np.array(p)
    for b, kind in enumerate(kinds):
        if kind != MOVES:
            p[0, b] = np.round((p[:, b].astype(int).max(axis=0) + p[:, b].astype(int).min(axis=0)) / 2)
    if len(keys) > 0xFFFF:
        raise ValueError('Too many text keys')
    out = bytearray(TABLE_MAGIC + struct.pack('>HHIffHH', TABLE_VERSION, bones, frames, rate, scale, len(groups),
                                              len(keys)))
    out += struct.pack('>%dh' % bones, *parents)
    out += bytes((-len(out)) % 4)
    out += bytes(kinds)
    out += bytes((-len(out)) % 4)
    for name, (first, last) in groups.items():
        raw = name.encode('ascii')
        if len(raw) >= TABLE_NAME or not 0 <= first <= last < frames:
            raise ValueError('Bad group %r' % name)
        out += raw.ljust(TABLE_NAME, b'\0') + struct.pack('>II', first, last)
    for text, group, frame in keys:
        raw = text.encode('ascii')
        if len(raw) >= KEY_TEXT or not 0 <= frame < frames or not (group == NO_GROUP or 0 <= group < len(groups)):
            raise ValueError('Bad text key %r' % text)
        out += raw.ljust(KEY_TEXT, b'\0') + struct.pack('>HHI', group, 0, frame)
    xyz = np.where(q[..., :1] < 0, -q, q)[..., 1:]
    # big-endian after joining: concatenate returns the host's order
    out += np.concatenate((xyz[0], p[0]), axis=1).astype('>i2').tobytes()
    columns = []
    for b, kind in enumerate(kinds):
        if kind != STILL:
            columns.append(xyz[:, b])
        if kind == MOVES:
            columns.append(p[:, b])
    if columns:
        out += np.concatenate(columns, axis=1).astype('>i2').tobytes()
    return bytes(out)


# Text keys that are events, not animation groups (OpenMW animation.cpp handleTextKey: footsteps and sounds).
EVENT_KEYS = frozenset(('soundgen', 'sound'))


VERT_BYTES = 16                 # engine aw_skel.h AW_SKEL_VERT_BYTES
NONE = 255                      # AW_SKEL_NONE


def write_verts(bone, second, weight, rest, rest2):
    """A skeletal model's vertices as the engine reads them (aw_skel.h): per vertex u8 bone, u8 second bone (255
    none), u8 its weight (0-255), u8 0, i16 x 3 rest position, i16 x 3 the second bone's rest position, big-endian,
    positions on one scale. Returns (bytes, rest scale)."""
    import struct
    rest = np.asarray(rest, float)
    rest2 = np.asarray(rest2, float)
    reach = float(max(np.max(np.abs(rest)) if rest.size else 0, np.max(np.abs(rest2)) if rest2.size else 0))
    scale = reach / 32767.0 if reach > 0 else 1.0
    out = bytearray()
    for v in range(len(rest)):
        s = int(second[v])
        w = int(round(float(weight[v]) * 255)) if s >= 0 else 0
        a = np.clip(np.round(rest[v] / scale), -32767, 32767).astype(int)
        b = np.clip(np.round(rest2[v] / scale), -32767, 32767).astype(int) if s >= 0 else (0, 0, 0)
        if not 0 <= int(bone[v]) < NONE or s >= NONE:
            raise ValueError('Bone index out of range at vertex %d' % v)
        out += struct.pack('>BBBx3h3h', int(bone[v]), NONE if s < 0 else s, w, *a, *b)
    return bytes(out), scale


BLOCK_MAGIC = b'AWSB'
BLOCK_HEAD = 76                 # engine aw_skel.h AW_SKEL_BLOCK_HEAD
BLOCK_TABLE_NAME = 32           # AW_SKEL_TABLE_NAME


def write_block(table_path, verts_blob, rest_scale, nv, table_frames, pose_origin, pose_step):
    """A skeletal model's block (engine aw_skel.h "AWSB"), appended after the frames of an ordinary MDL holding one
    rest frame: the shared table's game path, the vertices (write_verts) and how a posed vertex is quantised into the
    model's bytes (pose_origin, pose_step: the model's scale_origin and scale divided by the actor's own scale)."""
    import struct
    raw = table_path.encode('ascii')
    if not raw or len(raw) >= BLOCK_TABLE_NAME:
        raise ValueError('Table path must be 1 to %d characters' % (BLOCK_TABLE_NAME - 1))
    if len(verts_blob) != nv * VERT_BYTES or nv < 1 or table_frames < 1 or not rest_scale > 0:
        raise ValueError('Skeletal block shape mismatch')
    if any(not s > 0 for s in pose_step):
        raise ValueError('Pose step must be positive')
    head = BLOCK_MAGIC + struct.pack('>HH', BLOCK_VERSION, 0) + raw.ljust(BLOCK_TABLE_NAME, b'\0') + \
        struct.pack('>fII3f3f', rest_scale, nv, table_frames, *pose_origin, *pose_step)
    assert len(head) == BLOCK_HEAD
    return head + verts_blob


def all_groups(keys):
    """Every animation group named by the skeleton's text keys (lower case), in first-seen order: the table holds
    them all, never a chosen subset (the maintainer, 25 October 2026: if a humanoid can do it, it is in the table)."""
    out = []
    for _, line in keys:
        if ':' in line:
            group = line.split(':', 1)[0].strip()
            if group and group not in EVENT_KEYS and group not in out:
                out.append(group)
    return out


# Seconds between two keys of one phased group beyond which they are two places in the file (the beast spellcast's
# two parts are 193 s apart; the longest pause between keys within one place is 3.33 s, the beast swimknockout).
GROUP_GAP = 5.0


def group_spans(keys, wanted):
    """{group: (first time, last time)}: the group's start and stop keys when it has them, else (the attack, cast,
    block and inventory groups, whose keys name their phases: 'equip start', 'chop min attack', 'shoot release' ...)
    from its first key to its last, so every phase of the group is in the table."""
    spans = groups_of(keys, wanted)
    times = {}
    for t, line in keys:
        if ':' not in line:
            continue
        group = line.split(':', 1)[0].strip()
        if group in wanted and group not in spans:
            times.setdefault(group, []).append(t)
    for g, ts in times.items():
        # SKEL-GROUP-SPAN-52: a phased group's keys can lie in separate places of the file (the beast skeleton's
        # spellcast: equip and unequip at 64 s, the casts at 260 s); each cluster is its own span (the first keeps
        # the group's name, the next ones name_2, name_3 ...: the base game has groups named idle2), never the
        # 200 s between them
        ts = sorted(ts)
        clusters = [[ts[0]]]
        for t in ts[1:]:
            if t - clusters[-1][-1] > GROUP_GAP:
                clusters.append([])
            clusters[-1].append(t)
        for k, c in enumerate(clusters):
            spans[g if k == 0 else '%s_%d' % (g, k + 1)] = (c[0], c[-1])  # one key (inventory poses): one pose
    return spans


def resolve_hierarchy(parents, rot, pos):
    """Every bone's transform relative to the actor instead of its parent, per frame (the AmiQuake plan, 25 October
    2026: resolve the hierarchy at conversion, so the engine only reads each bone's pose; AW_SkelPose takes a bone
    without a parent as it is). rot [frame][bone] wxyz, pos [frame][bone] xyz. Returns (rot, pos)."""
    out_r, out_p = np.zeros_like(rot), np.zeros_like(pos)
    for f in range(len(rot)):
        world = pose_matrices(parents, [local_matrix(r, p) for r, p in zip(rot[f], pos[f])])
        for b, m in enumerate(world):
            q = matrix_to_quat(np.asarray(m)[:3, :3])
            if f and np.dot(q, out_r[f - 1, b]) < 0:
                q = -q
            out_r[f, b] = q
            out_p[f, b] = np.asarray(m)[3, :3]
    return out_r, out_p


# AmiWind's own groups, named spans over frames the table already holds (no frames of their own): the enhanced
# combat's dodge (docs/COMBAT.md: a swing whose roll missed shows why: the target raises its shield, the base
# game's shield group, or dodges; Morrowind has no dodge group, so a dodge is the loop of the walk-left or
# walk-right group in place while the combat code moves the actor sideways), as tools/npc_anim.py's kit samples it.
# {name: (group, first key, last key)}.
EXTRA_GROUPS = {'dodgel': ('walkleft', 'loop start', 'loop stop'),
                'dodger': ('walkright', 'loop start', 'loop stop')}


def extra_groups(groups, keys):
    """EXTRA_GROUPS as {name: (first frame, last frame)} from the table's groups and text keys [(text, group index,
    frame)]; one whose group or keys the table lacks is left out."""
    index = {g: i for i, g in enumerate(groups)}
    out = {}
    for name, (group, first, last) in EXTRA_GROUPS.items():
        if group not in index:
            continue
        frames = {text: frame for text, g, frame in keys if g == index[group]}
        if first in frames and last in frames and frames[first] <= frames[last]:
            out[name] = (frames[first], frames[last])
    return out


def text_keys(keys, ranges, groups, rate=TABLE_RATE):
    """The text keys as table frames [(text, group index, frame)]: a group's own keys by their phase ('start', 'self
    release', 'chop min hit', 'equip stop': what OpenMW's character controller and MWScript's PlayGroup play between)
    in the span that holds them (a phased group's later places included), and the sound events ('soundgen: left',
    'sound: swishm') whole, in the span that holds them, or NO_GROUP. A key outside every span (a group the table
    lacks) is left out. ranges: {span: (start time, stop time)} (group_spans); groups: {span: (first frame, last
    frame)} in table order. Sorted by frame."""
    import re
    index = {g: i for i, g in enumerate(groups)}
    by_group = {}
    for g in groups:
        by_group.setdefault(re.sub(r'_\d+$', '', g), []).append(g)     # spellcast_2 is spellcast's second place

    def frame_in(span, t):
        first, last = groups[span]
        return min(last, first + int(round((t - ranges[span][0]) * rate)))
    out = []
    for t, line in keys:
        if ':' not in line:
            continue
        group, what = (s.strip() for s in line.split(':', 1))
        if group in EVENT_KEYS:
            span = next((g for g in groups if ranges[g][0] - 1e-6 <= t <= ranges[g][1] + 1e-6), None)
            if span is not None:
                out.append((line, index[span], frame_in(span, t)))
            continue
        span = next((g for g in by_group.get(group, ()) if ranges[g][0] - 1e-6 <= t <= ranges[g][1] + 1e-6), None)
        if span is not None:
            out.append((what, index[span], frame_in(span, t)))
    out.sort(key=lambda k: (k[2], k[1]))
    return out


def source_spans(skeleton):
    """(ordered spans, ranges, missing) of one skeleton's text keys: every group's span (group_spans) in first-seen
    order, a phased group's later places (name_2 ...) after it; 'missing' the groups without a start or stop key."""
    names = all_groups(skeleton.keys)
    ranges = group_spans(skeleton.keys, names)
    missing = [g for g in names if g not in ranges]
    ordered = []
    for g in names:
        if g not in ranges:
            continue
        ordered.append(g)
        k = 2
        while '%s_%d' % (g, k) in ranges:      # a phased group's later places (group_spans)
            ordered.append('%s_%d' % (g, k))
            k += 1
    return ordered, ranges, missing


def span_family(name):
    """'spellcast_2' -> 'spellcast': the group a span belongs to."""
    import re
    return re.sub(r'_\d+$', '', name)


def layered_spans(skeleton, over=None):
    """[(span, source skeleton, its ranges)] in table order: the skeleton's spans, and with OVER (a skeleton whose
    groups play over the first's, as OpenMW stacks animation sources: NpcAnimation adds xbase_anim_female after
    xbase_anim for a female human, and a later source wins for every group it has) each group OVER has taken from it
    whole (all its places) at the first one's position; OVER's own new groups at the end. Returns (spans, missing)."""
    ordered, ranges, missing = source_spans(skeleton)
    if over is None:
        return [(g, skeleton, ranges) for g in ordered], missing
    over_ordered, over_ranges, over_missing = source_spans(over)
    families = {span_family(g) for g in over_ordered}
    out, placed = [], set()
    for g in ordered:
        family = span_family(g)
        if family not in families:
            out.append((g, skeleton, ranges))
        elif family not in placed:
            placed.add(family)
            out.extend((h, over, over_ranges) for h in over_ordered if span_family(h) == family)
    out.extend((h, over, over_ranges) for h in over_ordered if span_family(h) not in placed)
    return out, missing + [g for g in over_missing if g not in missing]


def appended_spans(skeleton, over, prefix, more=()):
    """[(span, source skeleton, its ranges)] in table order: every span of the skeleton, then every span of OVER
    under PREFIX + its name ('f:walkforward'), so one table holds both and a view of it plays OVER's groups first
    (SKEL-TABLE-SHARED-FEMALE-52); then each of MORE [(skeleton, prefix)] the same way (an NPC's own animation file,
    'd:idle9': DANCER-OWN-ANIM-IGNORED-53). Returns (spans, missing)."""
    ordered, ranges, missing = source_spans(skeleton)
    spans = [(g, skeleton, ranges) for g in ordered]
    for source, pre in ((over, prefix),) + tuple(more):
        own_ordered, own_ranges, own_missing = source_spans(source)
        prefixed = {pre + g: r for g, r in own_ranges.items()}
        spans += [(pre + h, source, prefixed) for h in own_ordered]
        missing = missing + [pre + g for g in own_missing]
    return spans, missing


def build_table(skeleton, bones=None, rate=TABLE_RATE, tolerance=0.0, resolved=False, over=None, append=None,
                more=()):
    """The whole table of one skeleton (npc_geometry.Skeleton): every group of its text keys, sampled at rate, the
    groups' frames one after another. over: a second skeleton of the same bones whose groups replace the first's
    (layered_spans: the female human groups over the common ones), or with APPEND (a group name prefix, 'f:') are
    added after them under that prefix (appended_spans); more [(skeleton, prefix)]: further skeletons of the same
    bones appended after those the same way (the NPCs' own animation files, OWN_ANIMATIONS; with APPEND only).
    Returns (table bytes, report {'groups',
    'missing', 'frames', 'bones', 'bytes', 'names', 'bone_names', 'times', 'over'}): 'missing' names the groups
    whose start or stop key is absent (a build check refuses them); 'bone_names' the table's bones in its order (a
    skeletal model's bone indices); 'times' the animation time of every table frame (in its source's file); 'over'
    the spans taken from OVER."""
    if more and not (over is not None and append):
        raise ValueError('More appended skeletons need an appended OVER')
    spans, missing = appended_spans(skeleton, over, append, more) if over is not None and append else \
        layered_spans(skeleton, over)
    if bones is None:
        bones = bone_order(skeleton.parents, list(skeleton.nodes))
    parents = [-1 if skeleton.parents[b] is None else bones.index(skeleton.parents[b]) for b in bones]
    for other in ([over] if over is not None else []) + [s for s, _ in more]:
        if [other.parents.get(b, 0) for b in bones] != [skeleton.parents[b] for b in bones]:
            raise ValueError('The layered skeleton does not have the same bones')
    times, groups = [], {}
    for g, _, ranges in spans:
        frames = table_frames(*ranges[g], rate=rate)
        groups[g] = (len(times), len(times) + len(frames) - 1)
        times.extend(frames)
    rot = np.zeros((len(times), len(bones), 4))
    pos = np.zeros((len(times), len(bones), 3))
    keys = []
    names = list(groups)
    prefix_of = {id(s): pre for s, pre in more}
    if append and over is not None:
        prefix_of[id(over)] = append
    for source in (skeleton, over) + tuple(s for s, _ in more):
        if source is None:
            continue
        mine = [(g, r) for g, s, r in spans if s is source]
        if not mine:
            continue
        rows = [f for g, _ in mine for f in range(groups[g][0], groups[g][1] + 1)]
        r, p = sample_table(source, bones, [times[f] for f in rows])
        rot[rows], pos[rows] = r, p
        # the source's own group names for its keys (an appended span 'f:walkforward' holds 'walkforward: ...')
        cut = len(prefix_of.get(id(source), '')) if source is not skeleton else 0
        own = (lambda g, cut=cut: g[cut:])
        sub = {own(g): groups[g] for g, _ in mine}
        local = [g for g, _ in mine]
        keys.extend((text, names.index(local[gi]) if gi != NO_GROUP else NO_GROUP, frame)
                    for text, gi, frame in text_keys(source.keys, {own(g): r[g] for g, r in mine}, sub, rate))
    for f in range(1, len(times)):               # the shorter way between neighbouring frames of two sources too
        flip = np.einsum('bi,bi->b', rot[f], rot[f - 1]) < 0
        rot[f, flip] = -rot[f, flip]
    keys.sort(key=lambda k: (k[2], k[1]))
    hold_in_place(pos, bones, groups)
    if resolved:
        rot, pos = resolve_hierarchy(parents, rot, pos)
        parents = [-1] * len(bones)
    q, p, scale = quantise_table(rot, pos)
    groups.update(extra_groups(groups, keys))       # after the keys: their group indices stay the source groups'
    data = write_table(parents, groups, q, p, scale, rate, tolerance, keys)
    return data, {'groups': len(groups), 'missing': missing, 'frames': len(times), 'bones': len(bones),
                  'bytes': len(data), 'names': list(groups), 'bone_names': list(bones), 'keys': len(keys),
                  'times': [float(t) for t in times], 'over': [g for g, s, _ in spans if over is not None and s is over]}


# The stick figure (the maintainer, 25 October 2026: "think of a stick figure skeleton"): the bones the table keeps of
# the base game's 61 nodes. The two lower spine links and the attachment nodes are left out, and the hand is a thumb
# and one finger unit (the maintainer: "4 out of 5 fingers are in a singular thing"), each with both of its joints:
# the base game's hand has a thumb (finger0, finger01) and two fingers (finger1, finger11; finger2, finger21), and
# the second finger rides the first, joint for joint (STICK_ALIAS), so a hand still closes around a weapon ("hands
# should curl around weapons"). A part on a left-out node rides its nearest kept ancestor (onto_kept); the torso
# bends at the chest only.
STICK_BONES = ('bip01', 'bip01 pelvis', 'bip01 spine2', 'bip01 neck', 'bip01 head',
               'bip01 l clavicle', 'bip01 l upperarm', 'bip01 l forearm', 'bip01 l hand', 'shield bone',
               'bip01 l finger0', 'bip01 l finger01', 'bip01 l finger1', 'bip01 l finger11',
               'bip01 r clavicle', 'bip01 r upperarm', 'bip01 r forearm', 'bip01 r hand', 'weapon bone',
               'bip01 r finger0', 'bip01 r finger01', 'bip01 r finger1', 'bip01 r finger11',
               'bip01 l thigh', 'bip01 l calf', 'bip01 l foot', 'bip01 r thigh', 'bip01 r calf', 'bip01 r foot')
STICK_ALIAS = {'bip01 %s finger2%s' % (side, j): 'bip01 %s finger1%s' % (side, j) for side in 'lr' for j in ('', '1')}


def kept_ancestor(parents, keep, name, alias=STICK_ALIAS):
    """name itself when kept, its alias when that is kept (a finger riding the hand's kept finger), else its nearest
    kept ancestor (None when it has none)."""
    while name is not None and name not in keep:
        if alias.get(name) in keep:
            return alias[name]
        name = parents[name]
    return name


class KeptSkeleton:
    """A skeleton (npc_geometry.Skeleton) seen through only the kept bones: each kept bone's parent is its nearest
    kept ancestor and its local transform the one relative to that ancestor, so the kept bones' world matrices are
    the original's. keys and pose as the skeleton's."""

    def __init__(self, skeleton, keep=STICK_BONES):
        missing = [b for b in keep if b not in skeleton.parents]
        if missing:
            raise ValueError('The skeleton lacks the kept bones %s' % missing)
        self.skeleton, self.keep = skeleton, frozenset(keep)
        self.keys = skeleton.keys
        self.parents = {b: kept_ancestor(skeleton.parents, self.keep, skeleton.parents[b]) for b in keep}
        self.nodes = {b: None for b in bone_order(self.parents, list(keep))}
        self._time, self._world = None, None

    def pose(self, time):
        return self.skeleton.pose(time)

    def local(self, name, time):
        if self._time != time:
            self._time, self._world = time, self.skeleton.pose(time)
        m = np.asarray(self._world(name), float)
        parent = self.parents[name]
        return m if parent is None else m @ np.linalg.inv(np.asarray(self._world(parent), float))


def onto_kept(src, parents, keep, rest_world):
    """An export_actor shape with every bone that is not kept moved onto its nearest kept ancestor: its rest
    positions taken into that bone's space through the rest pose (exact at rest); a vertex whose two bones land on
    one bone keeps one."""
    names = list(src['bones'])
    target = [kept_ancestor(parents, keep, n) for n in names]
    if any(t is None for t in target):
        raise ValueError('Shape %s hangs on a bone with no kept ancestor' % src.get('name'))
    if target == names:
        return src
    new_names = list(dict.fromkeys(target))
    at = {n: i for i, n in enumerate(new_names)}
    move = [np.asarray(rest_world(n), float) @ np.linalg.inv(np.asarray(rest_world(t), float))
            for n, t in zip(names, target)]

    def carried(points, bones):
        out = np.array(points, float)
        for b in np.unique(bones[bones >= 0]):
            ids = np.flatnonzero(bones == b)
            out[ids] = out[ids] @ move[b][:3, :3] + move[b][3, :3]
        return out
    bone = np.asarray(src['bone'])
    second = np.asarray(src['second'])
    rest = carried(src['rest'], bone)
    rest2 = carried(src['rest2'], second)
    new_bone = np.array([at[target[b]] for b in bone], int)
    new_second = np.array([at[target[c]] if c >= 0 else -1 for c in second], int)
    weight = np.asarray(src['weight'], float).copy()
    same = new_second == new_bone
    new_second[same] = -1
    weight[same] = 0.0
    rest2[new_second < 0] = 0.0
    return {**src, 'bones': new_names, 'bone': new_bone, 'second': new_second, 'weight': weight,
            'rest': rest, 'rest2': rest2}


# The beast races' skeleton (base_animkna.nif: Argonians and Khajiit walk on their toes and have a tail; the
# maintainer, 25 October 2026: "beast races have a different walk style"): the toes and every other tail bone kept
# too (tail1 rides tail, tail3 rides tail2).
BEAST_BONES = ('bip01 l toe0', 'bip01 r toe0', 'bip01 tail', 'bip01 tail2')


def stick_table(skeleton, rate=TABLE_RATE, resolved=False, over=None, append=None, more=()):
    """The table the game ships for a skeleton: the stick figure (KeptSkeleton, STICK_BONES, and BEAST_BONES where
    the skeleton has them) at rate, bones that hardly move stored without positions (POSITION_TOLERANCE). The game
    has three (GAME_TABLES): the common humanoid (base_anim.nif), the female groups layered over it (over =
    base_anim_female.nif) and the beast races (base_animkna.nif), chosen per actor by table_choice. more
    [(skeleton, prefix)]: the NPCs' own animation files appended under their prefixes (OWN_ANIMATIONS). Returns
    build_table's (bytes, report)."""
    keep = STICK_BONES + tuple(b for b in BEAST_BONES if b in skeleton.parents)
    return build_table(KeptSkeleton(skeleton, keep), rate=rate, tolerance=POSITION_TOLERANCE, resolved=resolved,
                       over=None if over is None else KeptSkeleton(over, keep), append=append,
                       more=tuple((KeptSkeleton(s, keep), p) for s, p in more))


# The tables a build ships (--npc-anim-type 2) and which actor plays which, as OpenMW chooses the animation sources
# (mwrender/npcanimation.cpp updateNpcBase): every humanoid on base_anim; a female human with base_anim_female's
# groups over it (its walk and two idles); the beast races (Argonian, Khajiit) on base_animkna. A beast female
# takes the beast table alone, as today's baked kit does (npc_anim.plan is given no female skeleton for a beast).
# {(skeleton, over or None): the name a model's block gives} (each under 32 characters, aw_skel.h
# AW_SKEL_TABLE_NAME). The female groups live in the common table under FEMALE_PREFIX (SKEL-TABLE-SHARED-FEMALE-52:
# a table of their own repeated the common one whole, 561 KB of Fast RAM for its three groups): a female human's
# model names the view 'progs/humanoid.awsk|f', which the engine loads once with the common table (aw_skel_load.c)
# and whose group lookup tries 'f:' + the name first; the layouts point at the female frames directly.
FEMALE_SKELETON = 'meshes/base_anim_female.nif'
FEMALE_PREFIX = 'f:'
TABLE_VIEW = '|'
GAME_TABLES = {('meshes/base_anim.nif', None): 'progs/humanoid.awsk',     # SKEL_TABLE_PATH (defined below)
               ('meshes/base_anim.nif', FEMALE_SKELETON): 'progs/humanoid.awsk|f',
               ('meshes/base_animkna.nif', None): 'progs/humanoid_kna.awsk'}
# a skeleton whose table carries a second skeleton's groups appended under a prefix
APPENDED = {'meshes/base_anim.nif': (FEMALE_SKELETON, FEMALE_PREFIX)}
# An NPC's own animation (DANCER-OWN-ANIM-IGNORED-53): an NPC record's MODL can name an animation file of its own
# (mwad.npc.outfit 'animation'); OpenMW's NpcAnimation adds that file's groups after base_anim's (and the female
# groups), and a later source wins for each group it has. The base game has one, anim_dancingGirl.nif, named by
# the three dancers of Desele's House of Earthly Delights in Suran and by Yakov of the Suran slave market: its only
# group is idle9, the dance, which their wander packages (AI_W) pick as an idle. Each such file is appended to the
# common table under its prefix ('d:idle9'), when the user's data has it, as the female groups are (a few KB, no
# second table in Fast RAM); the NPC's model names the view 'progs/humanoid.awsk|d' ('|d|f' for a woman: her own
# file's groups first, then hers, then the common ones). {file: prefix without ':'}; an NPC naming a file not
# listed here plays the common table (the residents report says so).
OWN_ANIMATIONS = {'meshes/anim_dancinggirl.nif': 'd'}
TABLE_NAME_MAX = BLOCK_TABLE_NAME - 1


def table_file(name):
    """The game path of the file a table name reads: 'progs/humanoid.awsk|f' -> 'progs/humanoid.awsk'."""
    return name.split(TABLE_VIEW, 1)[0]


def table_prefixes(name):
    """The group prefixes a table name's view plays first, in order ('progs/humanoid.awsk|d|f' -> ['d:', 'f:'])."""
    return [p + ':' for p in name.split(TABLE_VIEW)[1:]]


def table_prefix(name):
    """The group prefix a table name's view plays first ('f:'), or ''."""
    return (table_prefixes(name) or [''])[0]


def own_animation(appearance):
    """The prefix (without ':') of an appearance's own animation file in its table (OWN_ANIMATIONS), or None: none
    named, a beast's (the beast table carries none), or a file the table does not carry."""
    name = appearance.get('animation')
    if not name or appearance['skeleton'] != 'meshes/base_anim.nif':
        return None
    return OWN_ANIMATIONS.get(name.replace('\\', '/').casefold())


def table_choice(appearance):
    """(skeleton file, over skeleton file or None, the table name the model gives) of one appearance
    (mwad.npc.outfit): with an own animation file (own_animation) its view first ('progs/humanoid.awsk|d|f')."""
    skeleton = appearance['skeleton']
    over = FEMALE_SKELETON if appearance.get('female') and skeleton == 'meshes/base_anim.nif' else None
    path = GAME_TABLES.get((skeleton, over))
    if path is None:
        raise ValueError('No shared animation table for skeleton %s' % skeleton)
    own = own_animation(appearance)
    if own:
        path = table_file(path) + TABLE_VIEW + own + path[len(table_file(path)):]
    if len(path.encode('ascii')) > TABLE_NAME_MAX:
        raise ValueError('Animation table name %s is over %d characters' % (path, TABLE_NAME_MAX))
    return skeleton, over, path


def table_view(path, names):
    """PATH without the view prefixes whose groups the table (its group NAMES) does not hold (an own animation file
    the user's data lacks), so a model names only what its table has."""
    keep = [p for p in path.split(TABLE_VIEW)[1:] if any(n.startswith(p + ':') for n in names)]
    return TABLE_VIEW.join([table_file(path)] + keep)


# Carried items of a skeletal actor (SKEL-ITEM-TAGS-52): the tag names the item models and the table bones they
# hang on; the engine poses them from the table at the actor's frame (origin = the bone's world position x the
# actor scale, rotation = the bone's world rotation re-orthonormalised: npc_items.bone_tags' rows, computed in the
# game instead of one row per frame). Today's tag magic (AWTG1) is refused for it, so an engine without the
# skeletal item path shows no carried item rather than a wrong one.
SKEL_TAG_MAGIC = 'AWTS1'


def skeletal_tag(frames, paths, bone_names, scale, bones=(('weapon', 'weapon bone'), ('shield', 'shield bone')),
                 light=None):
    """The tag text of a skeletal actor's carried items: paths {kind: item model path}; bone_names the table's
    bones in order; scale the actor's model scale (weight, weight, height x 0.25); light: a carried light (a
    guard's torch) as (item model path, its flame point in the shield bone's space, unscaled): two optional last
    lines 'light PATH' and 'emitter X Y Z'. The light rides the shield bone; the engine shows it while torches are
    wanted (the day and night cycle) and the shield otherwise (aw_items.c AW_ItemsParseSkel, aw_guard_torch.c)."""
    index = {b: i for i, b in enumerate(bone_names)}
    lines = ['%s %d' % (SKEL_TAG_MAGIC, frames)]
    lines += ['%s %s' % (kind, paths.get(kind) or '-') for kind, _ in bones]
    lines.append('bones ' + ' '.join(str(index.get(bone, -1)) for _, bone in bones))
    lines.append('scale ' + ' '.join('%.6f' % float(s) for s in scale))
    if light is not None:
        lines.append('light ' + light[0])
        lines.append('emitter ' + ' '.join('%.6f' % float(v) for v in light[1]))
    return '\n'.join(lines) + '\n'


def read_skeletal_tag(text):
    """skeletal_tag's text back: {'frames', 'paths' {kind: path or None}, 'bones' [index], 'scale' [x, y, z]},
    and 'light' (path) and 'emitter' [x, y, z] when the tag carries a light."""
    lines = text.rstrip('\n').split('\n')
    magic, frames = lines[0].split()
    if magic != SKEL_TAG_MAGIC or len(lines) not in (5, 7):
        raise ValueError('Not a skeletal item tag')
    light = None
    if len(lines) == 7:
        lhead, path = lines[5].split(' ', 1)
        head, *emitter = lines[6].split()
        if lhead != 'light' or head != 'emitter' or len(emitter) != 3:
            raise ValueError('Not a skeletal item tag')
        light = {'light': path, 'emitter': [float(v) for v in emitter]}
    paths = {}
    for line in lines[1:3]:
        kind, path = line.split(' ', 1)
        paths[kind] = None if path == '-' else path
    head, *bones = lines[3].split()
    shead, *scale = lines[4].split()
    if head != 'bones' or shead != 'scale' or len(bones) != 2 or len(scale) != 3:
        raise ValueError('Not a skeletal item tag')
    return {'frames': int(frames), 'paths': paths, 'bones': [int(b) for b in bones],
            'scale': [float(s) for s in scale], **(light or {})}


def is_skeletal(model):
    """True when MODEL (MDL bytes) carries a skeletal block after its standard frames (read_skeletal's layout)."""
    import struct
    if len(model) < MDL_HEAD or model[:4] != b'IDPO':
        return False
    try:
        _, w, h, nv, nt, nf = struct.unpack_from('<6i', model, 48)
    except struct.error:
        return False
    standard = MDL_HEAD + 4 + w * h + nv * 12 + nt * 16 + nf * (4 + 24 + nv * 4)
    return model[standard:standard + 4] == BLOCK_MAGIC


# The resident bake of --npc-anim-type 2 (tools/prepare_area.py and tools/npc_library.py call it): the head at the
# budget detail, so every actor fits the alias stream reader, the only reader of the skeletal block today
# (SKEL-VERTEX-LIMIT-52: today's full-detail head takes a model to about 3,000 vertices).
RESIDENT_HEAD_DETAIL = 'budget'
_tables = {}


def own_sources(skeleton_of):
    """[(skeleton, prefix)] of the OWN_ANIMATIONS files the user's data has, in file order (the common table appends
    them): the same for every caller, so the table is one file whatever actor builds it first."""
    out = []
    for name in sorted(OWN_ANIMATIONS):
        try:
            skeleton = skeleton_of(name)
        except (KeyError, FileNotFoundError, OSError):
            continue                # not in this data: its NPCs play the common table (table_view)
        out.append((skeleton, OWN_ANIMATIONS[name] + ':'))
    return out


def game_table(data_key, appearance, skeleton_of):
    """(table bytes, build report, read_table, the table file's game path, skeleton, over skeleton) of an
    appearance's table, built once per process and data folder (a female human's view and the common table are one
    file, built once). skeleton_of(path) -> npc_geometry.Skeleton (the caller's cache)."""
    name, over, path = table_choice(appearance)
    key = (data_key, name)
    if key not in _tables:
        appended, prefix = APPENDED.get(name, (None, None))
        if over is not None and appended != over:
            raise ValueError('Animation table %s: %s is not the skeleton its table appends' % (path, over))
        data, report = stick_table(skeleton_of(name), over=skeleton_of(appended) if appended else None,
                                   append=prefix, more=own_sources(skeleton_of) if appended else ())
        if report['missing']:
            raise ValueError('Animation table %s: groups without start or stop keys: %s'
                             % (table_file(path), report['missing']))
        _tables[key] = (data, report, read_table(data))
    data, report, table = _tables[key]
    return data, report, table, table_file(path), skeleton_of(name), skeleton_of(over) if over else None


def skeletal_resident(data_key, assets, appearance, palette, profile, skeleton_of, head_detail=RESIDENT_HEAD_DETAIL,
                      torch=None):
    """One resident as a skeletal model on its shared table: (MDL bytes, kit groups on table frames (npc_anim
    layout input), report {'table', 'table_bytes', 'table_sha256', 'model' (skeletal_from_shapes' facts)}, the
    tag text or None, {item path: bytes}). profile: the kit profile's groups (npc_anim.plan_profile: the mover's
    when the build's profile has one, since one skeletal model plays every group). torch: a guard's carried torch
    (item path, model bytes, flame point in the shield bone's space: prepare_guard_torches.torch_item), named on
    the tag's 'light' and 'emitter' lines beside the guard's own shield."""
    import hashlib
    import npc_anim
    import npc_items
    data, report, table, _, skeleton, over = game_table(data_key, appearance, skeleton_of)
    # the name the model gives: a view for a female human or an NPC with its own animation file
    path = table_view(table_choice(appearance)[2], list(table['groups']))
    poser, groups = npc_anim.plan(skeleton, profile, over, appearance.get('weight', 1.),
                                  attack_stance=appearance.get('attack_stance'))
    kit = npc_anim.table_groups(table, groups, appearance.get('attack_stance'), report['times'],
                                prefix=table_prefixes(path))
    own = own_animation(appearance)
    own_idle = npc_anim.own_idle(table, report['times'], appearance,
                                 own + ':' if own and own + ':' in table_prefixes(path) else None)
    # reduced from the baked kit's own poses (SKEL-GROUND-SOLES-52); its first sample is the idle start, the rest pose
    raw, facts = skeletal_model(assets, appearance, skeleton, palette, data, report['bone_names'],
                                times=npc_anim.idle_compatible_times(groups), poser=poser,
                                rest_time=poser.samples[0][1], table_path=path, head_detail=head_detail)
    paths, items = npc_items.carried_models(assets, palette, appearance, skeleton.N)
    light = None
    if torch is not None:
        items[torch[0]] = torch[1]
        light = (torch[0], torch[2])
    scale = [appearance['weight'] * .25, appearance['weight'] * .25, appearance['height'] * .25]
    tag = skeletal_tag(table['frames'], paths, report['bone_names'], scale, light=light) \
        if paths or light else None
    model = {k: v for k, v in facts.items() if k not in ('shape_of', 'distance', 'nearest', 'rest_model')}
    return raw, kit, {'table': path, 'table_bytes': len(data), 'table_sha256': hashlib.sha256(data).hexdigest(),
                      'table_frames': table['frames'], 'model': model,
                      **({'own_idle': own_idle} if own_idle else {})}, tag, items


def table_files():
    """{game path: table bytes} of the tables this process built (game_table), for the stage to write once."""
    out = {}
    for (_, name), (data, _, _) in _tables.items():
        out[table_file(GAME_TABLES[(name, None)])] = data
    return out


# Groups whose root travels across the ground (the accumulating root, OpenMW animation.cpp: the movement comes from
# the game, not the animation): the table holds them in place, as the kit bake does (npc_geometry.assemble).
MOVING_GROUPS = ('walk', 'run', 'sneak', 'swimwalk', 'swimrun', 'jump')
ROOT_BONE = 'bip01'


def hold_in_place(pos, bones, groups, root=ROOT_BONE):
    """In place, the root bone's horizontal (x, y) travel within each moving group taken out, relative to the group's
    first frame; its height (the body's bob) is kept. pos: [frame][bone] positions (sample_table)."""
    if root not in bones:
        return
    b = bones.index(root)
    for name, (first, last) in groups.items():
        if name.startswith(MOVING_GROUPS):
            pos[first:last + 1, b, :2] = pos[first, b, :2]


def table_frames(start, stop, rate=TABLE_RATE):
    """Sample times of one animation group, both ends included."""
    if stop <= start:
        return np.array([float(start)])
    count = max(1, int(np.floor((stop - start) * rate + 1e-9))) + 1
    return np.linspace(start, stop, count)


def groups_of(keys, wanted):
    """{group: (start time, stop time)} from the skeleton's text keys ('walkforward: start' ... 'walkforward: stop',
    the loop keys of a group included as its own range); only the wanted groups (lower case)."""
    starts, stops = {}, {}
    for t, line in keys:
        if ':' not in line:
            continue
        group, what = (s.strip() for s in line.split(':', 1))
        if group not in wanted:
            continue
        if what == 'start' and group not in starts:
            starts[group] = t
        elif what == 'stop':
            stops[group] = t
    return {g: (starts[g], stops[g]) for g in wanted if g in starts and g in stops and stops[g] > starts[g]}


# A skeletal model (docs/MODULAR_NPCS.md method C, step C3): one appearance reduced and atlased as today's bake does
# it, written as an ordinary MDL of one rest frame followed by the "AWSB" block.
SKEL_TABLE_PATH = 'progs/humanoid.awsk'   # the humanoid table's game path (under 32 characters, aw_skel.h)
# The quantisation box: every Nth table frame plus every group's first and last frame. 1 (every frame): every 8th
# missed 11 of 5,046 frames of the base game's table, clamping up to 3.95 units; all of them take seconds to pose.
BOX_EVERY = 1
SKEL_VERTEX_LIMIT = 1999        # the alias stream reader (model_alias_stream.inc) reads the block; it takes <= 2000
RESIDENT_BUDGETS = (480, 384, 320, 256, 192)    # tools/prepare_area.py RESIDENT_LADDER
SHAPE_TAG = 1000.0              # the extra frame that tells which shape each baked vertex came from (see below)
MDL_HEAD = 84                   # struct '<4si3f3ff3f8if' (npc_geometry.animated_mdl)


def read_table(data):
    """The table write_table wrote: {'parents', 'groups', 'q', 'p', 'scale', 'rate'} (the engine's AW_SkelParse)."""
    import struct
    magic, version, bones, frames, rate, scale, groups, nkeys = struct.unpack_from('>4sHHIffHH', data, 0)
    if magic != TABLE_MAGIC or version != TABLE_VERSION:
        raise ValueError('Not an animation table')
    at = 24
    parents = list(struct.unpack_from('>%dh' % bones, data, at))
    at += 2 * bones
    at += (-at) % 4
    kinds_at = at
    at += bones
    at += (-at) % 4
    named = {}
    for _ in range(groups):
        name = data[at:at + TABLE_NAME].rstrip(b'\0').decode('ascii')
        named[name] = struct.unpack_from('>II', data, at + TABLE_NAME)
        at += TABLE_NAME + 8
    text = []
    for _ in range(nkeys):
        group, _, frame = struct.unpack_from('>HHI', data, at + KEY_TEXT)
        text.append((data[at:at + KEY_TEXT].rstrip(b'\0').decode('ascii'), group, frame))
        at += KEY_TEXT + 8
    kinds = list(data[kinds_at:kinds_at + bones])
    base = np.frombuffer(data, '>i2', bones * 6, at).reshape(bones, 6).astype(np.int32)
    at += bones * 12
    width = sum(3 if k == TURNS else 6 if k == MOVES else 0 for k in kinds)
    if len(data) != at + frames * width * 2:
        raise ValueError('Animation table size mismatch')
    rows = np.frombuffer(data, '>i2', frames * width, at).reshape(frames, width).astype(np.int32)
    xyz = np.repeat(base[None, :, :3], frames, axis=0)
    pos = np.repeat(base[None, :, 3:], frames, axis=0)
    col = 0
    for b, kind in enumerate(kinds):
        if kind != STILL:
            xyz[:, b] = rows[:, col:col + 3]
            col += 3
        if kind == MOVES:
            pos[:, b] = rows[:, col:col + 3]
            col += 3
    q = stored_quats(np.concatenate((np.zeros((frames, bones, 1)), xyz), axis=2))
    return {'parents': parents, 'groups': named, 'q': q, 'p': pos, 'scale': scale, 'kinds': kinds, 'keys': text,
            'rate': rate, 'frames': frames, 'bones': bones}


def table_world(table, frame):
    """The bones' world matrices at one table frame, from the quantised keys as the engine reads them (AW_SkelPose
    at a whole frame): (bones, 4, 4) row-vector matrices."""
    rot, pos = dequantise_table(table['q'][frame], table['p'][frame], table['scale'])
    return np.array(pose_matrices(table['parents'], [local_matrix(r, p) for r, p in zip(rot, pos)]))


def skin_many(rest, bone, second, weight, rest2, world):
    """skin() for many vertices at once: world is (bones, 4, 4)."""
    world = np.asarray(world, float)
    second = np.asarray(second)
    w = world[np.asarray(bone)]
    out = np.einsum('vi,vij->vj', np.asarray(rest, float), w[:, :3, :3]) + w[:, 3, :3]
    two = second >= 0
    if np.any(two):
        w2 = world[second[two]]
        b = np.einsum('vi,vij->vj', np.asarray(rest2, float)[two], w2[:, :3, :3]) + w2[:, 3, :3]
        out[two] += (b - out[two]) * np.asarray(weight, float)[two][:, None]
    return out


def box_frames(table, every=BOX_EVERY):
    """The table frames that set a skeletal model's quantisation box: every Nth, and every group's first and last."""
    picked = set(range(0, table['frames'], max(1, int(every))))
    for first, last in table['groups'].values():
        picked.update((first, last))
    return sorted(picked)


def carry_bones(sources, points, shape_of, rest_world, actor_scale):
    """Bones of a reduced model's vertices. The reduction (npc_geometry._bake: fast_simplification's quadric collapse,
    or the head reducer) moves vertices: a kept one sits on an original vertex (to the 5 decimals of its weld), a
    collapsed one somewhere new. Each takes the bone, second bone and weight of the nearest original vertex of the
    same shape, and its rest positions are that vertex's plus the offset, turned into each bone's space by the
    bone's rest-pose rotation (a kept vertex: exactly the original's).
    sources: export_actor shapes, each with 'points' (its rest-pose vertices in model units, assemble's frame 0) and
    'index' (its bones' table indices); points: the reduced model's rest vertices (model units); shape_of: each
    one's source shape; rest_world: name -> 4 x 4 world matrix of the rest pose; actor_scale: assemble's x y z scale.
    Returns (bone, second, weight, rest, rest2, distance in model units to the chosen original vertex, its index in
    its shape)."""
    from scipy.spatial import cKDTree
    n = len(points)
    bone = np.zeros(n, int)
    second = np.full(n, -1)
    weight = np.zeros(n)
    rest = np.zeros((n, 3))
    rest2 = np.zeros((n, 3))
    distance = np.full(n, np.inf)
    nearest = np.full(n, -1)
    for k, src in enumerate(sources):
        ids = np.flatnonzero(shape_of == k)
        if not len(ids):
            continue
        d, near = cKDTree(src['points']).query(points[ids])
        distance[ids] = d
        nearest[ids] = near
        delta = (points[ids] - src['points'][near]) / actor_scale
        inverse = [np.linalg.inv(np.asarray(rest_world(name), float))[:3, :3] for name in src['bones']]
        for v, s, dv in zip(ids, near, delta):
            b = int(src['bone'][s])
            bone[v] = src['index'][b]
            rest[v] = src['rest'][s] + dv @ inverse[b]
            c = int(src['second'][s])
            if c >= 0:
                second[v] = src['index'][c]
                weight[v] = src['weight'][s]
                rest2[v] = src['rest2'][s] + dv @ inverse[c]
    if np.any(~np.isfinite(distance)):
        raise ValueError('A reduced vertex has no source shape')
    return bone, second, weight, rest, rest2, distance, nearest


def skeletal_mdl(rest_model, faces, uv, skin_image, lo, step, block, vertex_limit=SKEL_VERTEX_LIMIT):
    """The MDL of a skeletal model: npc_geometry.animated_mdl's layout with one rest frame quantised in the box
    lo + step x 0..255 that holds every pose (its frame box is the whole 0..255, so culling holds every pose; light
    normal index 0, as animated_mdl writes it), then the block. vertex_limit: the engine reads the block only in the
    alias stream reader, which takes at most 2,000 vertices (25 October 2026); a larger limit (2331, 3072: an
    original-head bake past 666 faces) writes a model today's engine does not read as skeletal."""
    import struct
    from npc_geometry import animated_mdl
    nv = len(rest_model)
    if nv > vertex_limit:
        raise ValueError('A skeletal model takes at most %d vertices (the alias stream reader): %d'
                         % (vertex_limit, nv))
    data = bytearray(animated_mdl(np.asarray(rest_model, float)[None], faces, uv, skin_image,
                                  vertex_limit=None if vertex_limit > SKEL_VERTEX_LIMIT else 1999, names=['rest']))
    lo = np.asarray(lo, float)
    step = np.asarray(step, float)
    corners = np.array([[lo[i] + (255 * step[i] if (c >> i) & 1 else 0) for i in range(3)] for c in range(8)])
    struct.pack_into('<3f3ff', data, 8, *step, *lo, float(np.linalg.norm(corners, axis=1).max()))
    xyz = np.clip(np.rint((np.asarray(rest_model, float) - lo) / step), 0, 255).astype(np.uint8)
    at = len(data) - 4 * nv
    struct.pack_into('<4B4B', data, at - 24, 0, 0, 0, 0, 255, 255, 255, 0)
    data[at:] = np.column_stack((xyz, np.zeros(nv, np.uint8))).tobytes()
    return bytes(data) + block


def read_skeletal(model):
    """A skeletal model's parts as the engine reads them: header fields, the rest frame's bytes, the block's
    vertices (bones, second bone -1 none, weight 0-255, dequantised rest positions) and its pose origin and step."""
    import struct
    scale = struct.unpack_from('<3f', model, 8)
    origin = struct.unpack_from('<3f', model, 20)
    _, w, h, nv, nt, nf = struct.unpack_from('<6i', model, 48)
    standard = MDL_HEAD + 4 + w * h + nv * 12 + nt * 16 + nf * (4 + 24 + nv * 4)
    b = model[standard:]
    if b[:4] != BLOCK_MAGIC:
        raise ValueError('No skeletal block')
    rest_scale, count, frames = struct.unpack_from('>fII', b, 40)
    verts = np.frombuffer(b, np.uint8, count * VERT_BYTES, BLOCK_HEAD).reshape(count, VERT_BYTES)
    pos = verts[:, 4:].copy().view('>i2').astype(float) * rest_scale
    return {'nv': nv, 'nt': nt, 'frames': nf, 'scale': np.array(scale), 'origin': np.array(origin),
            'standard': standard, 'block_bytes': len(b),
            'frame_box': np.frombuffer(model, np.uint8, 8, standard - nv * 4 - 24),
            'rest_bytes': np.frombuffer(model, np.uint8, nv * 4, standard - nv * 4).reshape(nv, 4),
            'table': b[8:8 + BLOCK_TABLE_NAME].rstrip(b'\0').decode('ascii'), 'table_frames': frames,
            'bone': verts[:, 0].astype(int), 'second': np.where(verts[:, 1] == NONE, -1, verts[:, 1].astype(int)),
            'weight': verts[:, 2].astype(int), 'rest': pos[:, :3], 'rest2': pos[:, 3:],
            'pose_origin': np.array(struct.unpack_from('>3f', b, 52)),
            'pose_step': np.array(struct.unpack_from('>3f', b, 64))}


def engine_pose(model, table, frame):
    """AW_SkelPoseVerts at one table frame (float64 here, float32 in the engine): the model's byte vertices
    (nv, 3), rounded and clamped to 0..255 as the engine does. model: read_skeletal's; table: read_table's."""
    second = np.where(model['weight'] > 0, model['second'], -1)
    posed = skin_many(model['rest'], model['bone'], second, model['weight'] / 255.0, model['rest2'],
                      table_world(table, frame))
    return np.clip(np.floor((posed - model['pose_origin']) / model['pose_step'] + 0.5), 0, 255).astype(int)


def ground_grid(lo, hi, ground):
    """The quantisation box (lo, step) of a skeletal model: x and y as the box over every pose (lo + 255 steps), z on
    a grid with the rest pose's lowest point (GROUND, the soles the actor stands and is grounded on) exactly on a
    step, one spare step so the box still holds every pose. A box over every table frame is much taller than the
    idle's (lying, jumping), so its grid fell where it fell: the soles came out up to a step (about 0.17 units) above
    their true height and the ground check's half-unit sole band took in points above them as well
    (SKEL-GROUND-SOLES-52: in dev1-try8 Hefadmir's soles spread 0.5 units in height against the baked idle's 0.15,
    and no spot on his sloped floor fitted)."""
    import math
    lo = np.array(lo, float)
    hi = np.asarray(hi, float)
    step = np.maximum((hi - lo) / 255, .0001)
    step[2] = max((hi[2] - lo[2]) / 254, .0001)
    lo[2] = ground - math.ceil((ground - lo[2]) / step[2] - 1e-9) * step[2]
    return lo, step


def skeletal_from_shapes(shapes, materials, textures, palette, sources, rest_world, actor_scale, table_bytes,
                         bone_names, table_path=SKEL_TABLE_PATH, budgets=RESIDENT_BUDGETS, every=BOX_EVERY,
                         vertex_limit=SKEL_VERTEX_LIMIT, parents=None, **bake_args):
    """A skeletal model from an appearance assembled as today's resident (npc_geometry.assemble at its sample
    times, frame 0 the rest pose) and the same appearance's export_actor shapes. The reduction and atlas are
    npc_geometry.bake's, unchanged, on the same inputs, down the resident budget ladder; one frame is added to its
    input to learn each baked vertex's shape: frame 0 moved by (shape + 1) x SHAPE_TAG along x. bake carries a
    reduced vertex into every frame by the best-fit motion of its nearest original triangle, which is exact for a
    pure translation, so the added frame minus frame 0 names the shape; reference_frames keeps the face quotas of
    the frames without it. The box: the model's vertices posed at box_frames of the table and scaled by the actor.
    parents: the skeleton's {node: parent}; given, a shape on nodes the table lacks rides their nearest kept
    ancestors (onto_kept: the stick figure). Returns (MDL bytes, report)."""
    from npc_geometry import bake
    if len(sources) != len(shapes):
        raise ValueError('export_actor and assemble disagree on the shapes (%d, %d)' % (len(sources), len(shapes)))
    actor_scale = np.asarray(actor_scale, float)
    count = len(shapes[0]['positions'])
    tagged = []
    for k, (shape, src) in enumerate(zip(shapes, sources)):
        if shape['positions'].shape[1] != len(src['rest']):
            raise ValueError('Shape %s: vertex counts differ' % shape.get('name'))
        rest = shape['positions'][0]
        tagged.append({**shape, 'positions': np.concatenate((shape['positions'],
                                                              (rest + [(k + 1) * SHAPE_TAG, 0, 0])[None]))})
    for budget in budgets:
        try:
            try:
                frames, faces, uv, skin_image = bake(tagged, materials, textures, palette, budget=budget,
                                                     reference_frames=count, **bake_args)
            except ValueError as error:
                # More than 8 frames give a head shape up to 120 faces before the split (npc_geometry._budget_quotas):
                # an outfit of many head shapes then fits no budget of the ladder (dev1-try10, a Vivec resident,
                # SKEL-BUDGET-SHAPES-52). That budget again with the idle's 8-frame rule (the bake before
                # SKEL-GROUND-SOLES-52 passed 8 samples); the poses stay every sample.
                if str(error) != 'Too many separate shapes for budget' or count <= 8:
                    raise
                frames, faces, uv, skin_image = bake(tagged, materials, textures, palette, budget=budget,
                                                     reference_frames=8, **bake_args)
            break
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == budgets[-1]:
                raise
    rest_model = frames[0]
    if len(rest_model) > vertex_limit:
        raise ValueError('A skeletal model takes at most %d vertices (the alias stream reader): %d'
                         % (vertex_limit, len(rest_model)))
    tag = frames[-1] - rest_model
    shape_of = np.rint(tag[:, 0] / SHAPE_TAG).astype(int) - 1
    if np.any(np.abs(tag[:, 0] - (shape_of + 1) * SHAPE_TAG) > 1e-3) or np.any(np.abs(tag[:, 1:]) > 1e-3) or \
            np.any(shape_of < 0) or np.any(shape_of >= len(shapes)):
        raise ValueError('A baked vertex lost its shape tag')
    index = {name: i for i, name in enumerate(bone_names)}
    carried = []
    for shape, src in zip(shapes, sources):
        if parents is not None:
            src = onto_kept(src, parents, set(bone_names), rest_world)     # the stick figure (STICK_BONES)
        missing = [n for n in src['bones'] if n not in index]
        if missing:
            raise ValueError('Shape %s hangs on bones the table lacks: %s' % (src['name'], missing))
        carried.append({**src, 'points': shape['positions'][0], 'index': [index[n] for n in src['bones']]})
    bone, second, weight, rest, rest2, distance, nearest = carry_bones(carried, rest_model, shape_of, rest_world,
                                                                       actor_scale)
    table = read_table(table_bytes)
    picked = box_frames(table, every)
    lo = rest_model.min(axis=0)
    hi = rest_model.max(axis=0)
    for f in picked:
        posed = skin_many(rest, bone, second, weight, rest2, table_world(table, f)) * actor_scale
        lo = np.minimum(lo, posed.min(axis=0))
        hi = np.maximum(hi, posed.max(axis=0))
    lo, step = ground_grid(lo, hi, rest_model[:, 2].min())
    blob, rest_scale = write_verts(bone, second, weight, rest, rest2)
    block = write_block(table_path, blob, rest_scale, len(rest), table['frames'], lo / actor_scale,
                        step / actor_scale)
    model = skeletal_mdl(rest_model, faces, uv, skin_image, lo, step, block, vertex_limit)
    return model, {'vertices': len(rest), 'faces': len(faces), 'bytes': len(model), 'block_bytes': len(block),
                   'budget': budget, 'box_frames': len(picked), 'box_lo': lo.tolist(), 'box_step': step.tolist(),
                   'kept_vertices': int(np.sum(distance < 1e-4)), 'moved_vertices': int(np.sum(distance >= 1e-4)),
                   'largest_move': float(distance.max()), 'joint_vertices': int(np.sum(second >= 0)),
                   'shape_of': shape_of, 'distance': distance, 'nearest': nearest, 'rest_model': rest_model}


def skeletal_model(assets, appearance, skeleton, palette, table_bytes, bone_names, times=None, poser=None,
                   rest_time=None, **options):
    """One appearance's skeletal model (MDL bytes, report), exported by export_actor and reduced from the poses
    assemble gives at TIMES: by default the idle samples (npc_geometry.Skeleton.idle_times(8), the first the rest
    pose); with POSER (npc_anim.plan's KitSkeleton: TIMES are its sample indices, REST_TIME the skeleton time of its
    first sample, the rest pose) every pose the baked kit samples, so the reduction keeps what the motions need, as
    the baked kit's does (SKEL-GROUND-SOLES-52: reduced from the idle alone, two residents' soles came out unlike
    their baked idle's and found no spot on their sloped floors)."""
    from npc_geometry import assemble
    if times is None:
        times, _ = skeleton.idle_times(8)
    if poser is None:
        poser, rest_time = skeleton, float(times[0])
    shapes, materials, textures = assemble(assets, appearance, poser, times)
    sources = export_actor(assets, appearance, skeleton)
    scale = np.array([appearance['weight'], appearance['weight'], appearance['height']]) * .25
    return skeletal_from_shapes(shapes, materials, textures, palette, sources, skeleton.pose(float(rest_time)), scale,
                                table_bytes, bone_names, parents=getattr(skeleton, 'parents', None), **options)
