# SPDX-License-Identifier: GPL-3.0-only
"""Creature posing for the creature model library (EXPERIMENTAL; tools/creature_library.py; not used by any
default build stage, so the NPC, gallery and resident bakes keep their own code: tools/npc_geometry.py,
tools/creature_residents.py; CREATURE-BAKE-NIF-UNSUPPORTED-47).

How the original game animates a creature (behaviour read from OpenMW 0.51, our own implementation):

- The model drawn is the creature's mesh with an "x" before the file name when that animated version has its own
  keyframe file beside it (r/CliffRacer.NIF -> r/xCliffRacer.nif + r/xCliffRacer.kf; OpenMW
  components/misc/resourcehelpers.cpp correctActorModelPath), else the mesh itself.
- The animation comes from keyframe files (OpenMW mwrender/creatureanimation.cpp, animation.cpp addAnimSource):
  a two-legged creature (record flag 0x01) first takes the shared meshes/xbase_anim.kf, then its own x...kf; a
  group (text keys "idle: start" ...) is played from the newest file that has it. A KF file is a
  NiSequenceStreamHelper whose first extra data is the text keys and whose next extra data name, in order, the bone
  each keyframe controller moves (OpenMW nifosg/nifloader.cpp loadKf); a controller moves the first node of the
  model with that name (bone lookup by lower-case name; a later node of the same name keeps its own transform).
  So repeated node names in a model (guar "dummy15", rust rat "dummy03") are no error: the shapes are posed by node
  object, the names only bind the keyframes.
- Keys (OpenMW nifosg/controller.hpp interpolate, nif/nifkey.hpp): linear; quadratic and TCB vector and scale keys
  as a cubic Hermite curve through the keys with their tangents (quadratic: the stored in/out tangents; TCB: made
  from tension, continuity and bias over the neighbouring keys, generateTCBTangents); quaternion keys of every
  type slerped; constant keys jump at the half; before the first key the first value, after the last the last.
- Moving loops are sampled in place: the accumulation root ("bip01", else "root bone") keeps its idle x, y, and the
  removed motion is the group's own speed (as the NPC animation kit, tools/npc_anim.py).
"""
import bisect
import io
import math

import numpy as np

from mwad.audit import normpath

XBASE_KF = 'meshes/xbase_anim.kf'
ROOTS = ('bip01', 'root bone')             # OpenMW's accumulation root names, in priority order

# Group -> ([(start key, stop key), ...] tried in order, kind, moves). The creature keys of the game data
# ('walkforward: start' in the creature files, 'walkforward: loop start' in xbase_anim.kf).
GROUPS = {
    'idle': ([('idle: loop start', 'idle: loop stop'), ('idle: start', 'idle: stop')], 'loop', False),
    'walk': ([('walkforward: loop start', 'walkforward: loop stop'), ('walkforward: start', 'walkforward: stop')],
             'loop', True),
    'run': ([('runforward: loop start', 'runforward: loop stop'), ('runforward: start', 'runforward: stop')],
            'loop', True),
    'attack': ([('attack1: start', 'attack1: stop'), ('handtohand: chop start', 'handtohand: chop large follow stop')],
               'once', False),
    'hit': ([('hit1: start', 'hit1: stop')], 'once', False),
    'death': ([('death1: start', 'death1: stop')], 'hold', False),
}
ATTACK_HITS = ('attack1: hit', 'handtohand: chop hit')
STANDING = (('idle', 8), ('hit', 3), ('death', 5))                      # as the NPC 'react' profile
MOVER = (('idle', 8), ('walk', 8), ('run', 6), ('attack', 8), ('hit', 3), ('death', 5))
# An authored-dead creature (health 0: the corpses the game data lays out, 'dead rat'): one frame, the last of its own
# death group (a 'hold' group of one sample is its stop key), as the NPC corpses take 'death1: stop'
# (prepare_area.build_resident); ACTOR-LIBRARY-LEFT-OUT-48
CORPSE = (('death', 1),)


def actor_files(read, mesh):
    """(model path, own KF path or None): OpenMW's correctActorModelPath. READ(name) returns bytes or raises."""
    mesh = normpath(mesh if mesh.startswith('meshes/') else 'meshes/' + mesh)
    cut = mesh.rfind('/') + 1
    xmodel = mesh[:cut] + 'x' + mesh[cut:]
    kf = xmodel[:-4] + '.kf' if xmodel.endswith('.nif') else xmodel + '.kf'
    try:
        read(kf)
    except Exception:  # noqa: BLE001 (no animated version: the mesh itself, no own keyframes)
        return mesh, None
    return xmodel, kf


# ---------------------------------------------------------------- keys

def _hermite(a, b, out_a, in_b, u):
    t2 = u * u
    t3 = t2 * u
    return a * (2 * t3 - 3 * t2 + 1) + b * (-2 * t3 + 3 * t2) + out_a * (t3 - 2 * t2 + u) + in_b * (t3 - t2)


def tcb_tangents(times, values, tcb):
    """[(in, out)] per key of a TCB channel (OpenMW generateTCBTangents, own implementation)."""
    n = len(values)
    abcd = [((1 - t) * (1 - c) * (1 + b), (1 - t) * (1 + c) * (1 - b), (1 - t) * (1 + c) * (1 + b),
             (1 - t) * (1 - c) * (1 - b)) for t, b, c in tcb]
    out = [(values[0] * 0, values[0] * 0) for _ in range(n)]
    if n <= 1:
        return out
    d = values[1] - values[0]
    A, B, C, D = abcd[0]
    out[0] = (d * ((A + B) * .5), d * ((C + D) * .5))
    for i in range(1, n - 1):
        span = times[i + 1] - times[i - 1]
        if span == 0:
            continue
        A, B, C, D = abcd[i]
        prev, nxt = values[i] - values[i - 1], values[i + 1] - values[i]
        out[i] = ((prev * A + nxt * B) * ((times[i] - times[i - 1]) / span),
                  (prev * C + nxt * D) * ((times[i + 1] - times[i]) / span))
    d = values[-1] - values[-2]
    A, B, C, D = abcd[-1]
    out[-1] = (d * ((A + B) * .5), d * ((C + D) * .5))
    return out


def _slerp(a, b, u):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    dot = float(a @ b)
    if dot < 0:
        b, dot = -b, -dot
    if dot < .9995:
        th = math.acos(min(1.0, max(-1.0, dot)))
        v = (math.sin((1 - u) * th) * a + math.sin(u * th) * b) / math.sin(th)
    else:
        v = (1 - u) * a + u * b
    return v / np.linalg.norm(v)


def sample(channel, time):
    """The value of one key channel {times, values, type, quaternion, tangents} at TIME."""
    times, values = channel['times'], channel['values']
    hi = bisect.bisect_right(times, time)
    if hi == 0:
        return values[0].copy()
    if hi == len(times):
        return values[-1].copy()
    lo = hi - 1
    span = times[hi] - times[lo]
    u = (time - times[lo]) / span if span > 0 else 0.0
    kind = channel['type']
    if kind == 5:                                   # constant
        return (values[hi] if u > .5 else values[lo]).copy()
    if channel['quaternion']:
        return _slerp(values[lo], values[hi], u)
    if kind in (2, 3):
        tan = channel['tangents']
        return _hermite(values[lo], values[hi], tan[lo][1], tan[hi][0], u)
    return values[lo] + (values[hi] - values[lo]) * u


def channels_of(N, data):
    """{'rotation'|'position'|'scale': channel} of one NiKeyframeData."""
    out = {}
    if data.num_rotation_keys:
        if data.rotation_type not in (1, 2, 3, 5):
            raise ValueError('Unsupported rotation key type %d' % data.rotation_type)
        keys = data.quaternion_keys
        out['rotation'] = {'times': [k.time for k in keys], 'type': int(data.rotation_type), 'quaternion': True,
                           'values': np.array([[k.value.w, k.value.x, k.value.y, k.value.z] for k in keys])}
    for field, group in (('position', data.translations), ('scale', data.scales)):
        if not len(group.keys):
            continue
        kind = int(group.interpolation)
        if kind not in (1, 2, 3, 5):
            raise ValueError('Unsupported %s key type %d' % (field, kind))
        vec = (lambda v: np.array(v.as_list(), float)) if field == 'position' else (lambda v: np.array(float(v)))
        times = [k.time for k in group.keys]
        values = np.array([vec(k.value) for k in group.keys])
        ch = {'times': times, 'values': values, 'type': kind, 'quaternion': False, 'tangents': None}
        if kind == 2:
            ch['tangents'] = [(vec(k.backward), vec(k.forward)) for k in group.keys]
        elif kind == 3:
            ch['tangents'] = tcb_tangents(times, list(values), [(k.tbc.t, k.tbc.b, k.tbc.c) for k in group.keys])
        out[field] = ch
    return out


def text_keys(N, node):
    keys = []
    e = node.extra_data
    while e:
        if isinstance(e, N.NiTextKeyExtraData):
            for key in e.text_keys:
                for line in key.value.decode('cp1252').splitlines():
                    keys.append((float(key.time), line.strip().casefold()))
        e = getattr(e, 'next_extra_data', None)
    return keys


def load_kf(N, raw, name):
    """{'name', 'keys': [(time, line)], 'events': {line: last time}, 'channels': {bone (lower case): channels}} of
    a KF file (OpenMW loadKf's reading: text keys first, then one bone name per keyframe controller)."""
    d = N.Data()
    d.read(io.BytesIO(raw))
    seq = next((r for r in d.roots if type(r).__name__ == 'NiSequenceStreamHelper'), None)
    if seq is None:
        raise ValueError('%s: no NiSequenceStreamHelper root' % name)
    extras = []
    e = seq.extra_data
    while e:
        extras.append(e)
        e = getattr(e, 'next_extra_data', None)
    if not extras or not isinstance(extras[0], N.NiTextKeyExtraData):
        raise ValueError('%s: the first extra data is not the text keys' % name)
    keys = text_keys(N, seq)
    channels = {}
    ctrl = seq.controller
    for extra in extras[1:]:
        if ctrl is None:
            break
        if isinstance(extra, N.NiStringExtraData) and isinstance(ctrl, N.NiKeyframeController) and ctrl.data:
            bone = extra.string_data.decode('cp1252').casefold()
            channels.setdefault(bone, channels_of(N, ctrl.data))
        ctrl = ctrl.next_controller
    events = {}
    for t, line in keys:
        events[line] = t
    return {'name': name, 'keys': keys, 'events': events, 'channels': channels}


# ---------------------------------------------------------------- the rig

class CreatureRig:
    """One creature model and its animation sources (see the module text).

    nodes: the model's NiNodes in depth-first order (the order prepare_scenery.model_geometry visits them), each
    (name lower case, parent index or -1, rest transform, the bone name it answers to or None for a later node of
    a repeated name)."""

    def __init__(self, N, read, mesh, bipedal):
        self.N = N
        self.model, own_kf = actor_files(read, mesh)
        self.raw = read(self.model)
        self.sources = []
        if bipedal:
            self.sources.append(load_kf(N, read(XBASE_KF), XBASE_KF))
        if own_kf:
            self.sources.append(load_kf(N, read(own_kf), own_kf))
        if not self.sources:
            raise ValueError('%s: no keyframe file (not two-legged, no %s)' % (mesh, 'x...kf'))
        d = N.Data()
        d.read(io.BytesIO(self.raw))
        self.nodes, seen = [], set()

        def visit(node, parent):
            if not isinstance(node, N.NiAVObject):
                return
            index = parent
            if isinstance(node, N.NiNode):
                name = node.name.decode('cp1252').casefold()
                bone = name if name not in seen else None
                seen.add(name)
                self.nodes.append((name, parent, np.array(node.get_transform().as_list()), float(node.scale), bone))
                index = len(self.nodes) - 1
            for child in getattr(node, 'children', []):
                if child is not None:
                    visit(child, index)
        for root in d.roots:
            visit(root, -1)
        self.duplicates = sorted({n for n, *_ , b in self.nodes if b is None})
        self.root = next((i for r in ROOTS for i, n in enumerate(self.nodes) if n[4] == r), None)

    def window(self, group):
        """(source index, start, stop) of a group in the newest source that has it, or None."""
        for si in range(len(self.sources) - 1, -1, -1):
            ev = self.sources[si]['events']
            for a, b in GROUPS[group][0]:
                if a in ev and b in ev and ev[b] > ev[a]:
                    return si, ev[a], ev[b]
        return None

    def local(self, index, source, time):
        name, parent, rest, scale, bone = self.nodes[index]
        m = rest.copy()
        ch = self.sources[source]['channels'].get(bone) if bone else None
        if ch:
            if 'rotation' in ch:
                w, x, y, z = sample(ch['rotation'], time)
                from scipy.spatial.transform import Rotation
                m[:3, :3] = Rotation.from_quat([x, y, z, w]).as_matrix().T * scale
            if 'position' in ch:
                m[3, :3] = sample(ch['position'], time)
            if 'scale' in ch:
                m[:3, :3] *= float(sample(ch['scale'], time)) / scale
        return m

    def worlds(self, source, time, fixed=None):
        """World matrices of every node (row vectors), in node order; FIXED: the root's x, y (moving loops)."""
        out = []
        for i, (name, parent, *_rest) in enumerate(self.nodes):
            local = self.local(i, source, time)
            if fixed is not None and i == self.root:
                local = local.copy()
                local[3, :2] = fixed
            out.append(local @ (out[parent] if parent >= 0 else np.eye(4)))
        return out

    def pose_world(self, source, time, fixed=None):
        """A pose_world callback for prepare_scenery.model_geometry: it is called once per NiNode in this same
        depth-first order, so the matrices are handed out by position (repeated names stay apart); the name it
        gets is checked against the node's."""
        matrices = self.worlds(source, time, fixed)
        state = {'i': 0}

        def call(name):
            i = state['i']
            if i >= len(self.nodes) or self.nodes[i][0] != name.casefold():
                raise ValueError('Node order differs from the rig at %d (%s)' % (i, name))
            state['i'] = i + 1
            return matrices[i]
        return call

    def plan(self, profile=MOVER):
        """[(source, time, fixed xy or None)] samples and the groups (name, base, count, kind, step, speed or hit,
        source file, or 'idle' standing in for a group the creature does not have: OpenMW plays idle then)."""
        idle = self.window('idle')
        if idle is None:
            raise ValueError('%s: no idle group in %s' % (self.model, ', '.join(s['name'] for s in self.sources)))
        isrc = idle[0]
        root_xy = self.worlds(isrc, idle[1])[self.root][3, :2].copy() if self.root is not None else None
        samples, groups = [], []
        for name, count in profile:
            kind, moves = GROUPS[name][1], GROUPS[name][2]
            entry = {'name': name, 'base': len(samples), 'count': count, 'kind': kind, 'events': []}
            win = self.window(name)
            if win is None:
                a, b = idle[1], idle[2]
                samples.extend([(isrc, a, None)] * count)
                entry.update(step=(b - a) / 8, source='idle')
                groups.append(entry)
                continue
            si, a, b = win
            if kind == 'hold':
                times = list(np.linspace(a, b, count - 1, endpoint=False)) + [b] if count > 1 else [b]
                step = (b - a) / max(1, count - 1)
            else:
                times = list(np.linspace(a, b, count, endpoint=False))
                step = (b - a) / count
            entry.update(step=step, source=self.sources[si]['name'])
            fixed = root_xy if moves and self.root is not None else None
            if moves and self.root is not None:
                ya = self.worlds(si, a)[self.root][3, :2]
                yb = self.worlds(si, b)[self.root][3, :2]
                entry['speed'] = float(np.linalg.norm(yb - ya) / (b - a) * .25)
            if name == 'attack':
                ev = self.sources[si]['events']
                hit = next((ev[h] for h in ATTACK_HITS if h in ev and a <= ev[h] <= b), None)
                entry['hit'] = (hit - a) / (b - a) if hit is not None else .5
            samples.extend((si, float(t), fixed) for t in times)
            groups.append(entry)
        return samples, groups


def layout(groups):
    """The animation layout string of the NPC kit's format (npc_anim.layout: NAME:BASE:COUNT:STEP[:X]); creature
    sound events are not converted yet."""
    words = []
    for g in groups:
        word = '%s:%d:%d:%.4f' % (g['name'], g['base'], g['count'], g['step'])
        if 'speed' in g:
            word += ':%.2f' % g['speed']
        elif 'hit' in g:
            word += ':%.3f' % g['hit']
        words.append(word)
    return ' '.join(words)
