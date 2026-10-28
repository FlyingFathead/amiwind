# SPDX-License-Identifier: GPL-3.0-only
"""Creature animation tables (CREATURE-TABLES): every creature record of the three masters on a table of its own
files.

A creature record (CREA) names its own model; the original plays that model's own keyframes (its x...kf beside the
animated model), and a two-legged creature (record flag 0x01) first the shared meshes/xbase_anim.kf, a later file
winning for every group it has (rule from OpenMW file mwrender/creatureanimation.cpp with animation.cpp
addAnimSource; tools/creature_pose.py reads the files). So one table per creature MESH serves every record that uses
it, as the humanoids share progs/humanoid.awsk (docs/MODULAR_NPCS.md, "Runtime method C"):

- table(rig): the mesh's own animation table (skeletal_actor.build_table): every group of its text keys (none chosen
  away: the Heart of Lorkhan's idle2 to idle5 and death1, Dagoth Ur's idlespell and knockout, a golden saint's whole
  xbase_anim set), on the bones its keyframes move (the creature's own skeleton, not the humanoid stick figure), the
  own file's groups over the shared ones for a two-legged creature (layered_spans);
- kit(rig, table): the engine's groups (idle, walk, run, attack, hit, death: the resident and mover logic,
  engine/aga/qc/world.qc) on that table's frames, the layout a skeletal model carries beside it (<model>.anm), with
  the own speed of the moving loops and the attack's hit fraction from the creature's keys (creature_pose.plan);
- model(...): the creature as one skeletal model on that table (halloween_cast.creature_model: the resident bake's
  reduction, one rest frame, the AWSB block naming the table), so every group of the table plays by name
  (dbg animkit play / cycle; MWScript's PlayGroup later) and nothing is baked per group;
- census: every record of the three masters with its mesh, table and what it plays, written as JSON.

Today the creatures are baked (tools/creature_library.py method 'kf': 38 frames of six groups per mesh, Morrowind.esm
only; tools/creature_residents.py: 8 idle frames). This module adds the method 'skeletal' beside them (DON'T DELETE
ANY METHOD); creature_library takes it with method='skeletal'.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    # run as a script, Python puts tools/ first and tools/mwad.py would hide the src/mwad package
    # (BUILD-ACTOR-LIBRARY-MWAD-PATH-47): src/ goes ahead of tools/, as in actor_library.py
    for _p in (ROOT / 'tools', ROOT / 'src'):
        while str(_p) in sys.path:
            sys.path.remove(str(_p))
        sys.path.insert(0, str(_p))

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
FORMAT = 'AmiWind creature tables 1'
TABLE_PREFIX = 'progs/k_'               # progs/k_<12 hex of the mesh>.awsk: 25 characters (AW_SKEL_TABLE_NAME 32)
BIPED = 0x01                            # CREA FLAG: two-legged (rule from OpenMW file components/esm3/loadcrea.hpp)
MAX_BONES = 64                          # engine/aga/src/aw_skel.h AW_SKEL_MAX_BONES
LAYOUT_MAX = 64                         # tools/npc_anim.py table_groups: a layout group takes at most 64 frames
# The engine's groups a creature plays (engine/aga/src/aw_anim.h, creature_pose.MOVER's order); a group the creature
# lacks stands on the idle (OpenMW falls back to idle, mwmechanics/character.cpp).
KIT = ('idle', 'walk', 'run', 'attack', 'hit', 'death')
# The model's reduction ladder (creature_residents.BUDGETS; npc_geometry.bake takes at most 480 without face quotas);
# a gallery profile's budget comes first when the mesh has one (config/gallery_model_quality.json).
BUDGETS = (480, 384, 320, 256, 192)
# Meshes whose model keeps more than the ladder allows, with the bake rules of the model the Halloween scene already
# ships for them (tools/halloween_cast.py: Dagoth Ur's mask and crest at up to 1,000 triangles).
LARGE = {'r/dagothr.nif': 'dagoth'}


def table_path(mesh):
    """The game path of a creature mesh's table (under AW_SKEL_TABLE_NAME)."""
    return '%s%s.awsk' % (TABLE_PREFIX, hashlib.sha256(mesh.casefold().encode('utf-8')).hexdigest()[:12])


def model_path(mesh):
    """The game path of a creature mesh's skeletal model (the baked library's c_ name with an _k: both can ship)."""
    return 'progs/c_%s_k.mdl' % table_path(mesh)[len(TABLE_PREFIX):-5]


# ---------------------------------------------------------------- the records

def records(masters):
    """{id: {mesh, name, flags, biped, dead, master}} of every creature record of MASTERS [(name, bytes)], in load
    order: a later master's record of the same id replaces the earlier (the three masters as the game loads them)."""
    import creature_library
    out = {}
    for name, raw in masters:
        planned = creature_library.plan(raw)
        for ident, base in planned['bases'].items():
            out[ident] = {'mesh': base['mesh'], 'name': base['name'], 'flags': base['flags'],
                          'biped': bool(base['flags'] & BIPED), 'dead': base['dead'], 'master': name}
    return out


def record_count(masters):
    """The creature records of every master, each master counted on its own (the v0.0.53 audit's 432: 260 + 97 +
    75), and the ids that remain after load order."""
    import creature_library
    per = {name: len(creature_library.plan(raw)['bases']) for name, raw in masters}
    return per, len(records(masters))


def meshes(recs):
    """{mesh: {'ids': [...], 'biped': bool}}: a mesh is two-legged when any record using it is."""
    out = {}
    for ident in sorted(recs):
        r = recs[ident]
        if not r['mesh']:
            continue
        m = out.setdefault(r['mesh'], {'ids': [], 'biped': False})
        m['ids'].append(ident)
        m['biped'] = m['biped'] or r['biped']
    return out


# ---------------------------------------------------------------- the table

def animated_bones(rig):
    """The bone names any of the rig's keyframe files moves, in node order, the accumulation root first among them
    (a creature's own skeleton: what the table must carry; every other node rides its nearest kept ancestor, which
    is exact for a node no key moves)."""
    moved = set()
    for src in rig.sources:
        moved |= set(src['channels'])
    # the scene roots too: a shape whose nodes no key moves (the Heart's fire) rides the root it hangs under
    names = [n[4] for n in rig.nodes if n[4] is not None and (n[4] in moved or n[1] < 0)]
    if rig.root is not None and rig.nodes[rig.root][4] not in names:
        names.insert(0, rig.nodes[rig.root][4])
    return names


class _WithAttachments:
    """A RigSkeleton with attachment bones it lacks added (EXTRA {bone: parent bone}): each rides its parent with no
    offset of its own. A creature on the humanoid skeleton without the humanoid's weapon and shield bones (an ash
    zombie, Dagoth Ur) has no part on them, so they only keep the table's bones the humanoid table's."""

    def __init__(self, skeleton, extra):
        import numpy as np
        self.skeleton, self.extra = skeleton, dict(extra)
        self.parents = dict(skeleton.parents, **self.extra)
        self.nodes = dict(skeleton.nodes, **{b: None for b in self.extra})
        self.keys, self.events = skeleton.keys, skeleton.events
        self._eye = np.eye(4)

    def local(self, name, time):
        return self._eye.copy() if name in self.extra else self.skeleton.local(name, time)

    def pose(self, time):
        world = self.skeleton.pose(time)
        return lambda name: world(self.extra.get(name.casefold(), name))


ATTACHMENTS = {'weapon bone': 'bip01 r hand', 'shield bone': 'bip01 l hand'}


def _kept(rig, source, keep, extra=None):
    """The rig's source seen through the kept bones, each bone's local transform without scale: the table holds
    none (aw_skel.h). A bone whose keys scale it (the Heart of Lorkhan's beat: 'heart' between 0.95 and 1) is
    recorded in .scaled {bone: (lowest, highest)} and played at its rest size (CREATURE-SCALE-KEYS-54)."""
    import numpy as np
    import skeletal_actor
    from halloween_cast import RigSkeleton

    class Kept(skeletal_actor.KeptSkeleton):
        scaled = {}

        def local(self, name, time):
            m = np.array(super().local(name, time), float)
            s = np.linalg.norm(m[:3, :3], axis=1)
            if np.all(s > 1e-6):
                if np.any(np.abs(s - 1) > 1e-3):
                    lo, hi = self.scaled.get(name, (1.0, 1.0))
                    self.scaled[name] = (min(lo, float(s.min())), max(hi, float(s.max())))
                m[:3, :3] /= s[:, None]
            return m
    skeleton = RigSkeleton(rig, source)
    kept = Kept(_WithAttachments(skeleton, extra) if extra else skeleton, keep)
    kept.scaled = {}
    return kept


# Data-driven bone merges (CREATURE-BONES-OVER-64-54; the humanoids' stick-figure rule, skeletal_actor.STICK_BONES:
# a part on a left-out node rides its nearest kept ancestor, exact for a node that never moves against it). A bone
# is merged into its nearest kept ancestor only when, over EVERY sampled frame of EVERY group of the creature's own
# files, the drift that ride gives its vertices stays under DRIFT_LIMIT (game units; 4 game units are one Quake unit,
# about one pixel at 5 m on the 320-wide screen): the drift of a bone is the largest distance any point within its
# reach (its subtree's node origins and its own length) moves away from where the bone itself puts it. Its children
# stay exact (a kept bone's world pose is the original's whatever is merged above it, skeletal_actor.KeptSkeleton).
# Past AW_SKEL_MAX_BONES the bones of least drift are merged until it fits, each named with its drift.
DRIFT_LIMIT = 1.0
SAMPLE_RATE = 8.0                       # samples a second over each file's keys (the table's own rate)


def _sampled_worlds(rig):
    """[(world matrices (nodes, 4, 4) per sample)] over every source's whole key range at SAMPLE_RATE, and the
    reference pose (the idle's first sample, the pose the skeletal model is reduced from: halloween_cast rest)."""
    import numpy as np
    out = []
    for si, src in enumerate(rig.sources):
        times = [t for t, _ in src['keys']] or [0.0]
        n = int(max(2, min(2000, (max(times) - min(times)) * SAMPLE_RATE)))
        for t in np.linspace(min(times), max(times), n):
            out.append(np.array(rig.worlds(si, float(t))))
    idle = rig.window('idle')
    ref = np.array(rig.worlds(idle[0], idle[1])) if idle else out[0]
    return np.array(out), ref


def merge_plan(rig, keep, limit=None, drift_limit=None, only=None):
    """(kept bones, [(bone, into, drift in game units)] merged) of KEEP: every bone whose ride on its nearest kept
    ancestor drifts under DRIFT_LIMIT is merged (least drift first, re-measured after each merge), then, past LIMIT,
    the least drifting ones until it fits. The root and the scene roots are never merged."""
    import numpy as np
    limit = MAX_BONES if limit is None else limit
    drift_limit = DRIFT_LIMIT if drift_limit is None else drift_limit
    keep = list(keep)
    index = {n[4]: i for i, n in enumerate(rig.nodes) if n[4] is not None}
    parent = {i: n[1] for i, n in enumerate(rig.nodes)}
    fixed = {n[4] for n in rig.nodes if n[4] is not None and n[1] < 0}
    if rig.root is not None:
        fixed.add(rig.nodes[rig.root][4])
    worlds, ref = _sampled_worlds(rig)
    children = {}
    for i, p in parent.items():
        children.setdefault(p, []).append(i)

    kept_index = {index[b] for b in keep}

    def subtree(i):
        """i and the nodes that ride it: its descendants down to (not into) the next kept bone, whose own pose
        stays exact whatever rides above it."""
        out, todo = [], [i]
        while todo:
            j = todo.pop()
            out.append(j)
            todo.extend(c for c in children.get(j, ()) if c not in kept_index)
        return out
    reach = {}
    for b in keep:
        i = index[b]
        pts = [ref[j][3, :3] for j in subtree(i)]
        if parent[i] >= 0:
            # the bone's own length: as far again as its parent is (a leaf's vertices lie along it)
            pts.append(2 * ref[i][3, :3] - ref[parent[i]][3, :3])
        # the reach points in the bone's own space (homogeneous rows), from their reference world positions
        hom = np.column_stack((np.array(pts, float), np.ones(len(pts))))
        local = hom @ np.linalg.inv(ref[i])
        local[:, 3] = 1.0
        reach[b] = local

    def ancestor(b):
        p = parent[index[b]]
        while p >= 0 and rig.nodes[p][4] not in keep:
            p = parent[p]
        return p

    cache = {}

    def drift(b):
        i, a = index[b], ancestor(b)
        if a < 0:
            return float('inf')
        if (b, a) not in cache:
            cache[(b, a)] = measure(i, a, b)
        return cache[(b, a)]

    def measure(i, a, b):
        # the bone's pose relative to its kept ancestor: per sample against the reference
        rel_ref = ref[i] @ np.linalg.inv(ref[a])
        rel = worlds[:, i] @ np.linalg.inv(worlds[:, a])
        # a point p in the bone's space: true world p @ W_i; ridden: p @ rel_ref @ W_a; their difference is
        # p @ (rel - rel_ref) @ W_a, whose length is that of p @ (rel - rel_ref) (W_a turns and moves, no scale)
        diff = np.einsum('pk,skl->spl', reach[b], rel - rel_ref[None])[:, :, :3]
        return float(np.linalg.norm(diff, axis=2).max())
    merged = []
    while True:
        cands = [(drift(b), b) for b in keep if b not in fixed and (only is None or b in only)]
        if not cands:
            break
        d, b = min(cands)
        if d >= drift_limit and len(keep) <= limit:
            break
        into = rig.nodes[ancestor(b)][4]
        keep.remove(b)
        merged.append((b, into, round(d, 3)))
    return keep, merged


def merged_drift(rig, animated, kept):
    """[(bone, into, drift)] of the animated bones left out of KEPT, each measured on its nearest kept ancestor as
    merge_plan measures a merge (the drift of a whole chain left out is its worst bone's, each on the kept bone it
    rides)."""
    kept_set = set(kept)
    out = [b for b in animated if b not in kept_set]
    _, merged = merge_plan(rig, list(dict.fromkeys(list(kept) + list(animated))), limit=len(kept_set),
                           drift_limit=-1.0, only=out)
    return merged


def table(rig, path='own'):
    """(table bytes, build_table's report + 'sources', 'layered', 'scaled', 'path') of one creature rig
    (creature_pose.CreatureRig): the first source's groups, and for a two-legged creature with a file of its own that
    file's groups over them (a later source wins for every group it has). path 'humanoid': the stick figure's bones
    (Dagoth Ur's template, for a creature on the humanoid skeleton); 'own': its animated bones, merged under the
    drift limit (merge_plan)."""
    import skeletal_actor
    keep = tuple(animated_bones(rig))
    if not keep:
        raise ValueError('%s: no bone moved by its keyframes' % rig.model)
    bones_before = len(keep)
    if path == 'humanoid':
        # Dagoth Ur's template (tools/halloween_cast.py dagoth_ur, shipped in v0.0.53): the humanoid stick figure's
        # bones the creature has (skeletal_actor.STICK_BONES, BEAST_BONES), so its table has the shared humanoid
        # table's bones; every other node rides its nearest kept ancestor (onto_kept), measured like a merge
        names = {n[4] for n in rig.nodes if n[4] is not None}
        kept = [b for b in skeletal_actor.STICK_BONES + skeletal_actor.BEAST_BONES if b in names]
        dropped = merged_drift(rig, keep, kept)
    else:
        kept, dropped = merge_plan(rig, keep, MAX_BONES)
    keep = tuple(kept)
    if len(keep) > MAX_BONES:
        raise ValueError('%s: %d animated bones, the engine takes %d (aw_skel.h AW_SKEL_MAX_BONES)'
                         % (rig.model, len(keep), MAX_BONES))
    base = _kept(rig, 0, keep)
    over = _kept(rig, 1, keep) if len(rig.sources) > 1 else None
    data, report = skeletal_actor.build_table(base, over=over, tolerance=skeletal_actor.POSITION_TOLERANCE)
    if report['missing']:
        raise ValueError('%s: groups without start or stop keys: %s' % (rig.model, report['missing']))
    scaled = dict(base.scaled, **(over.scaled if over is not None else {}))
    return data, dict(report, sources=[s['name'] for s in rig.sources], layered=over is not None,
                      bones_left_out=dropped, bones_before=bones_before,
                      max_drift=max([d for _, _, d in dropped], default=0.0),
                      scaled={b: [round(lo, 4), round(hi, 4)] for b, (lo, hi) in sorted(scaled.items())})


APPENDED_VERSION = 3                    # engine/aga/src/aw_skel.h AW_SKEL_VERSION_APPENDED
BASE_NAME = 32                          # AW_SKEL_TABLE_NAME


def to_appended(data, base):
    """A version 2 table (skeletal_actor.write_table) as an APPENDED table extending BASE (aw_skel.h version 3: the
    base table's game path after the 24-byte header). Its bones must be the base's, in the base's order."""
    import struct
    raw = base.encode('ascii')
    if data[:4] != b'AWSK' or struct.unpack_from('>H', data, 4)[0] != 2 or not raw or len(raw) >= BASE_NAME \
            or b'|' in raw:
        raise ValueError('Not a version 2 table or not a base table name: %r' % base)
    return data[:4] + struct.pack('>H', APPENDED_VERSION) + data[6:24] + raw.ljust(BASE_NAME, b'\0') + data[24:]


def from_appended(data):
    """(version 2 table bytes, base path) of an appended table (to_appended's inverse), for skeletal_actor.read_table."""
    import struct
    if data[:4] != b'AWSK' or struct.unpack_from('>H', data, 4)[0] != APPENDED_VERSION:
        raise ValueError('Not an appended animation table')
    base = data[24:24 + BASE_NAME].rstrip(b'\0').decode('ascii')
    return data[:4] + struct.pack('>H', 2) + data[6:24] + data[24 + BASE_NAME:], base


HUMANOID_TABLE = 'progs/humanoid.awsk'  # skeletal_actor.GAME_TABLES: the common humanoid table every NPC shares
_humanoid = {}


def humanoid_table(assets):
    """(table bytes, build report) of the shared humanoid table exactly as the NPC residents ship it
    (skeletal_actor.game_table: base_anim.nif with the female and own-animation groups appended), once per process."""
    key = id(assets)
    if key not in _humanoid:
        import skeletal_actor
        from npc_geometry import Skeleton
        rigs = {}

        def skeleton_of(path):
            if path not in rigs:
                rigs[path] = Skeleton(assets, path)
            return rigs[path]
        data, report, _t, path, _s, _o = skeletal_actor.game_table('creature-tables', {'skeleton': 'meshes/base_anim.nif'},
                                                                  skeleton_of)
        if path != HUMANOID_TABLE:
            raise ValueError('The common humanoid table is %s, not %s' % (path, HUMANOID_TABLE))
        _humanoid[key] = (data, report)
    return _humanoid[key]


def appended_table(rig, humanoid):
    """(appended table bytes, report) of a creature on the humanoid skeleton (CREATURE-APPENDED-TABLE-54): its OWN
    file's groups only (the last source: its x...kf; xbase_anim's groups are the humanoid table's own), on exactly the
    humanoid table's bones in its order, as a version 3 table extending progs/humanoid.awsk. HUMANOID: humanoid_table's
    (bytes, report). Refused (ValueError) when the creature lacks a bone of the table or its bones hang differently."""
    import skeletal_actor
    hum_data, hum_report = humanoid
    bones = list(hum_report['bone_names'])
    names = {n[4] for n in rig.nodes if n[4] is not None}
    missing = [b for b in bones if b not in names]
    if [b for b in missing if b not in ATTACHMENTS]:
        raise ValueError('%s lacks bones of the humanoid table: %s' % (rig.model, ', '.join(missing)))
    extra = {b: ATTACHMENTS[b] for b in missing}
    own = _kept(rig, len(rig.sources) - 1, tuple(bones), extra)
    parents = [-1 if own.parents[b] is None else bones.index(own.parents[b]) for b in bones]
    if parents != skeletal_actor.read_table(hum_data)['parents']:
        raise ValueError('%s: its bones hang differently from the humanoid table\'s' % rig.model)
    data, report = skeletal_actor.build_table(own, bones=bones, tolerance=skeletal_actor.POSITION_TOLERANCE)
    if report['missing']:
        raise ValueError('%s: groups without start or stop keys: %s' % (rig.model, report['missing']))
    hum_frames = skeletal_actor.read_table(hum_data)['frames']
    left = merged_drift(rig, animated_bones(rig), [b for b in bones if b in names])
    return to_appended(data, HUMANOID_TABLE), dict(
        report, own_table=data, sources=[rig.sources[-1]['name']], layered=False, appended=HUMANOID_TABLE,
        base_frames=hum_frames, base_groups=len(hum_report['names']), total_frames=report['frames'] + hum_frames,
        bones_left_out=left, bones_before=len(animated_bones(rig)),
        max_drift=max([d for _, _, d in left], default=0.0),
        scaled={b: [round(lo, 4), round(hi, 4)] for b, (lo, hi) in sorted(own.scaled.items())})


def patch_block_frames(model, frames):
    """A skeletal model's block frame count set to FRAMES (an appended table: the own frames and the base's); the
    builder's skeletal_from_shapes writes the count of the table it was handed (the own one)."""
    import struct
    import skeletal_actor
    info = skeletal_actor.read_skeletal(model)
    at = info['standard'] + 48
    return model[:at] + struct.pack('>I', int(frames)) + model[at + 4:]


def kit(rig, data, times, base=None):
    """The engine's groups (KIT) on the table's frames: [{name, base, count, step, kind, source, speed | hit}],
    loops and 'once' groups without the stop key's frame (it is the start's pose again), 'hold' groups ending on it,
    as npc_anim.table_groups does for the humanoids. A group the creature lacks stands on the idle's first frame
    (source 'idle'). The own speed of a moving loop and the attack's hit fraction come from the creature's keys
    (creature_pose.CreatureRig.plan). times: build_table's report 'times' (each table frame's animation time).
    BASE: an appended table's base (its bytes): a group the creature's own file lacks is the base's, at the base's
    frames after the own ones (source 'base'; walk and run then carry no speed of their own)."""
    import creature_pose
    import skeletal_actor
    t = skeletal_actor.read_table(data)
    names = list(t['groups'])
    at = {}
    for text, gi, frame in t['keys']:
        if gi < len(names):
            at.setdefault((names[gi], text), frame)
    from_base = set()
    if base is not None:
        bt = skeletal_actor.read_table(base)
        bnames = list(bt['groups'])
        for text, gi, frame in bt['keys']:
            if gi < len(bnames) and (bnames[gi], text) not in at:
                at[(bnames[gi], text)] = frame + t['frames']
                from_base.add((bnames[gi], text))
        times = list(times) + [i / float(bt['rate']) for i in range(bt['frames'])]
    _, planned = rig.plan(creature_pose.MOVER)
    by_name = {g['name']: g for g in planned}
    step0 = 1.0 / float(t['rate'])

    def frames_of(start, stop):
        g1, a = (s.strip() for s in start.split(':', 1))
        g2, b = (s.strip() for s in stop.split(':', 1))
        fa, fb = at.get((g1, a)), at.get((g2, b))
        return (fa, fb, (g1, a) in from_base) if fa is not None and fb is not None and fb > fa else None
    idle = next((f for pair in creature_pose.GROUPS['idle'][0] for f in [frames_of(*pair)] if f), None)
    if idle is None:
        raise ValueError('%s: the table has no idle group' % rig.model)
    out = []
    for name in KIT:
        pairs, kind, _moves = creature_pose.GROUPS[name]
        span = next((f for pair in pairs for f in [frames_of(*pair)] if f), None)
        entry = {'name': name, 'kind': kind}
        if span is None:
            out.append(dict(entry, base=idle[0], count=1, step=step0, source='idle'))
            continue
        a, b, based = span
        count = b - a + 1 if kind == 'hold' else max(1, b - a)
        if count > LAYOUT_MAX:
            raise ValueError('%s: group %s is %d table frames, the layout takes at most %d'
                             % (rig.model, name, count, LAYOUT_MAX))
        step = (times[b] - times[a]) / (b - a) if b > a else step0
        entry.update(base=int(a), count=int(count), step=float(step), source='base' if based else 'table')
        g = {} if based else by_name.get(name, {})
        if 'speed' in g:
            entry['speed'] = g['speed']
        if 'hit' in g:
            entry['hit'] = g['hit']
        out.append(entry)
    return out


def layout(groups):
    """The layout string of the kit groups (npc_anim.layout's NAME:BASE:COUNT:STEP[:X]); no sound events yet
    (SNDG-TRIBUNAL-BLOODMOON, v054-combat: the creature sound generators)."""
    import creature_pose
    return creature_pose.layout(groups)


# ---------------------------------------------------------------- the model

def model(N, assets, palette, rig, data, report, budgets=None, **bake_args):
    """(MDL bytes, facts) of the creature as one skeletal model on its table, reduced from its idle's poses (8 samples
    of the source that plays the idle)."""
    import numpy as np
    import halloween_cast
    from halloween_cast import RigSkeleton
    idle = rig.window('idle')
    if idle is None:
        raise ValueError('%s: no idle group' % rig.model)
    source, a, b = idle
    times = np.linspace(a, b, 8, endpoint=False)
    raw, facts = halloween_cast.creature_model(N, rig.raw, RigSkeleton(rig, source).pose, times, assets, palette,
                                               data, report['bone_names'], table_path(rig.mesh),
                                               budgets or BUDGETS, **bake_args)
    return raw, halloween_cast._facts(facts)


def humanoid_rig(rig):
    """{'humanoid_rig': bool, 'stick_missing': [...]}: whether the creature's model carries every bone of the
    humanoid stick figure (skeletal_actor.STICK_BONES, the weapon and shield bones aside), so it can play the shared
    humanoid table (progs/humanoid.awsk) with only its own groups added, as the dancers do."""
    import skeletal_actor
    names = {n[4] for n in rig.nodes if n[4] is not None}
    missing = [b for b in skeletal_actor.STICK_BONES if b not in names and b not in ('weapon bone', 'shield bone')]
    return {'humanoid_rig': not missing, 'stick_missing': missing}


def source_size(N, raw):
    """{'source_vertices', 'source_triangles'} of a model's visible shapes (what a whole-model profile would keep;
    the skeletal reader takes at most 1,999 vertices: skeletal_actor.SKEL_VERTEX_LIMIT)."""
    import io
    d = N.Data()
    d.read(io.BytesIO(raw))
    verts = tris = 0

    def walk(node, hidden):
        nonlocal verts, tris
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252').casefold()
        if isinstance(node, N.NiNode) and name in ('rootcollisionnode', 'bounding box'):
            return
        hidden = hidden or bool(node.flags & 1)
        if isinstance(node, N.NiTriShape):
            if not hidden and node.data and node.data.num_triangles:
                verts += int(node.data.num_vertices)
                tris += int(node.data.num_triangles)
            return
        for child in getattr(node, 'children', []) or []:
            if child:
                walk(child, hidden)
    for root in d.roots:
        walk(root, False)
    return {'source_vertices': verts, 'source_triangles': tris}


def open_rig(N, read, mesh, biped):
    """creature_pose.CreatureRig with the record's mesh kept as .mesh (the table and model paths are keyed by it)."""
    import creature_pose
    rig = creature_pose.CreatureRig(N, read, mesh, biped)
    rig.mesh = mesh
    return rig


_assets = {}


def _open(data):
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets
    key = str(Path(data).resolve())
    if key not in _assets:
        _assets[key] = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
    return _assets[key]


def unit(task):
    """Worker (module level for the process pool): one mesh -> (mesh, result or None, error or None). result:
    {'table': bytes, 'model': bytes or None, 'layout': str, 'report': {...}}; census_only: no model."""
    import time
    mesh, data, palette, biped, census_only = task
    t0 = time.time()
    try:
        from prepare_scenery import nif_reader
        from prepare_gallery import quality_profiles
        from mwad.audit import normpath
        assets = _open(data)
        N = nif_reader()
        rig = open_rig(N, assets.read, mesh, biped)
        # the maintainer's order (2026-10-27): (1) the shared humanoid table with only its own groups appended,
        # (2) its own skeleton reduced under the drift limit, (3) a table of its own (2 and 3 are merge_plan)
        hum = None
        if humanoid_rig(rig)['humanoid_rig']:
            try:
                hum = humanoid_table(assets)
                tdata, report = appended_table(rig, hum)
                path, why = 'appended', 'on the humanoid skeleton: its own groups appended to %s' % HUMANOID_TABLE
            except ValueError as error:
                hum = None
                path, why = 'own', 'the humanoid table does not carry it: %s' % error
        else:
            path, why = 'own', 'not on the humanoid skeleton: missing %s' % ', '.join(humanoid_rig(rig)['stick_missing'][:4])
        if hum is None:
            tdata, report = table(rig, 'own')
        own_data = report.get('own_table', tdata)
        groups = kit(rig, own_data, report['times'], base=hum[0] if hum else None)
        rep = {'mesh': mesh, 'animated_model': rig.model, 'sources': report['sources'], 'layered': report['layered'],
               'table': table_path(mesh), 'table_bytes': len(tdata),
               'table_sha256': hashlib.sha256(tdata).hexdigest(), 'bones': report['bones'],
               'frames': report['frames'], 'groups': report['names'], 'keys': report['keys'],
               'kit': {g['name']: g['source'] for g in groups}, 'repeated_node_names': rig.duplicates,
               'scaled_bones': report['scaled'], 'bones_left_out': report['bones_left_out'],
               'bones_before': report['bones_before'], 'max_drift': report['max_drift'], 'path': path,
               'path_reason': why}
        out = {'table': tdata, 'model': None, 'layout': layout(groups), 'report': rep}
        rep.update(source_size(N, rig.raw))
        rep.update(humanoid_rig(rig))
        rep.update({k: report[k] for k in ('appended', 'base_frames', 'base_groups', 'total_frames') if k in report})
        if not census_only:
            profile = quality_profiles().get(normpath(mesh))
            if LARGE.get(normpath(mesh)) == 'dagoth':
                import halloween_cast
                budgets, bake_args = halloween_cast.DAGOTH_BUDGETS, dict(halloween_cast.DAGOTH_BAKE)
            elif profile:
                top = min(int(profile['budget']), BUDGETS[0])
                budgets = (top,) + tuple(b for b in BUDGETS if b < top)
                bake_args = {'minimum_faces': profile['minimum_faces']} if profile.get('minimum_faces') else {}
            else:
                budgets, bake_args = BUDGETS, {}
            raw, facts = model(N, assets, palette, rig, own_data, report, budgets, **bake_args)
            if hum is not None:
                raw = patch_block_frames(raw, report['total_frames'])   # the own frames and the humanoid table's
            out['model'] = raw
            rep.update(model=model_path(mesh), model_bytes=len(raw), model_sha256=hashlib.sha256(raw).hexdigest(),
                       vertices=facts.get('vertices'), faces=facts.get('faces'), budget=facts.get('budget'))
        rep['seconds'] = round(time.time() - t0, 2)
        return mesh, out, None
    except Exception as error:  # noqa: BLE001 (each mesh left out with its reason; the census lists it)
        return mesh, None, '%s: %s' % (type(error).__name__, error)


def build(data, palette, wanted, out_id1=None, jobs=1, census_only=False):
    """Tables (and models unless census_only) of every mesh in WANTED ({mesh: {'ids', 'biped'}}), in parallel, one
    unit per mesh, largest first is not known ahead so in mesh order. Writes OUT_ID1/progs/k_*.awsk, c_*_k.mdl and
    their .anm layouts when OUT_ID1 is given. Returns ({mesh: report}, {mesh: error})."""
    from build_parallel import ordered_map
    tasks = [(mesh, data, palette, info['biped'], census_only) for mesh, info in sorted(wanted.items())]
    done, failed = {}, {}
    for mesh, out, error in ordered_map(unit, tasks, jobs=max(1, jobs)):
        if out is None:
            failed[mesh] = error
            print('Creature tables: %s left out (%s)' % (mesh, error), flush=True)
            continue
        rep = out['report']
        if out_id1 is not None:
            root = Path(out_id1)
            files = [(rep['table'], out['table'])]
            if out['model'] is not None:
                files += [(rep['model'], out['model']), (rep['model'][:-4] + '.anm', (out['layout'] + '\n').encode())]
            for path, raw in files:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        rep['layout'] = out['layout']
        done[mesh] = rep
        print('Creature tables: %s -> %s (%d bones, %d groups, %d frames, %d bytes%s, %.1f s)' % (
            mesh, rep['table'], rep['bones'], len(rep['groups']), rep['frames'], rep['table_bytes'],
            ', model %d vertices' % rep['vertices'] if 'vertices' in rep else '', rep['seconds']), flush=True)
    return done, failed


def census(recs, done, failed, per_master):
    """The census document: every record with its mesh, table and what it plays; every mesh's table facts; the
    meshes left out with their reasons; totals."""
    by_mesh = meshes(recs)
    rows = {}
    for ident, r in sorted(recs.items()):
        m = done.get(r['mesh'])
        rows[ident] = {'master': r['master'], 'mesh': r['mesh'], 'biped': r['biped'], 'dead': r['dead'],
                       'table': m['table'] if m else None,
                       'left_out': failed.get(r['mesh']) if not m else None}
    kit_missing = {}
    for mesh, m in done.items():
        for g, src in m['kit'].items():
            if src == 'idle':
                kit_missing.setdefault(g, []).append(mesh)
    return {'format': FORMAT, 'records_per_master': per_master, 'records': len(recs), 'meshes': len(by_mesh),
            'tables': len(done), 'left_out': failed,
            'records_on_a_table': sum(1 for r in rows.values() if r['table']),
            'table_bytes': sum(m['table_bytes'] for m in done.values()),
            'model_bytes': sum(m.get('model_bytes', 0) for m in done.values()),
            'kit_groups_standing_on_idle': {g: sorted(v) for g, v in sorted(kit_missing.items())},
            'by_mesh': done, 'by_record': rows}


def read_masters(data):
    """[(name, bytes)] of the masters the data folder has, in load order."""
    from mwad.paths import child_ci
    out = []
    for name in MASTERS:
        try:
            out.append((name, child_ci(Path(data), name).read_bytes()))
        except (FileNotFoundError, OSError):
            continue
    if not out or out[0][0] != MASTERS[0]:
        raise ValueError('No Morrowind.esm in %s' % data)
    return out


def main(argv=None):
    import argparse
    import time
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, help='the runtime palette (gfx/palette.lmp): needed for the models')
    p.add_argument('--out', type=Path, required=True, help='a folder: creature-tables.json, and id1/progs unless '
                   '--census-only')
    p.add_argument('--only', help='comma-separated creature ids: only their meshes')
    p.add_argument('--census-only', action='store_true', help='tables and the census, no models')
    p.add_argument('--jobs', type=int, default=1)
    a = p.parse_args(argv)
    if not a.census_only and not a.palette:
        p.error('--palette is needed for the models (or --census-only)')
    t0 = time.time()
    masters = read_masters(a.data_files)
    per_master, _ = record_count(masters)
    recs = records(masters)
    wanted = meshes(recs)
    if a.only:
        want = {i.strip().casefold() for i in a.only.split(',')}
        wanted = {m: v for m, v in wanted.items() if want & set(v['ids'])}
    print('Creature tables: %d records (%s), %d meshes, %d jobs' % (
        len(recs), ', '.join('%s %d' % kv for kv in per_master.items()), len(wanted), a.jobs), flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    palette = a.palette.read_bytes() if a.palette else None
    done, failed = build(a.data_files, palette, wanted, None if a.census_only else a.out / 'id1', a.jobs,
                         a.census_only)
    doc = census(recs, done, failed, per_master)
    doc['seconds'] = round(time.time() - t0, 1)
    (a.out / 'creature-tables.json').write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                               newline='\n')
    print('Creature tables: done - took %.1fs, %d tables, %d left out, %d of %d records on a table' % (
        doc['seconds'], len(done), len(failed), doc['records_on_a_table'], len(recs)), flush=True)


if __name__ == '__main__':
    main()
