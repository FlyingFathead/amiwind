#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Readied magic shows open hands, the bare hands' fists stay fists: a check of the first-person data an image ships
(READY-MAGIC-SHOWS-WEAPON-65, v0.0.66; docs/THIRD_PERSON.md "First-person arms").

In the original the readied-magic stance shows the open palms of base_anim.1st.nif's 'idlespell', and the bare hands
with no weapon the clenched fists of 'idlehh': the hands tell the player which one is ready (decided for the project,
14 November 2026: readying magic shows the open hands whatever is equipped). Both first-person paths bake these poses
from the same sample times (prepare_hands.sample_clips): the arms from parts as rows of progs/humanoid_1st.awsk
(tools/prepare_player_fp_parts.py: the fists 'hh', the spell stances 'sps', 'spt', 'sp'), the baked arms as
progs/hands/<stem>.mdl (the fists) and <stem>_sp.mdl (the spell stance; tools/prepare_hand_catalog.py). The image step
(tools/build_aga.py) runs image_check on the files it installed and stops on a failure, before the image is packed.

Two measures, at the frames a stance holds (its idle, the 8 first of the 28-frame contract):
- the curl of a hand in the table: the turn of its four fingers' middle and end joints (bip01 <side> fingerN1 and
  fingerN2, N 1 to 4) summed, in degrees. Measured on the original's first-person skeleton (the same in
  xbase_anim.1st.kf, the file OpenMW plays): idlehh 545 (fists), idlespell 103 to 130 (open, the fingers a little
  bent), the spell's release 12 (flat). The fists must reach FIST_MIN_CURL, every spell stance stay under OPEN_MAX_CURL.
- the reach of a hand in a baked model: how far its vertices go from the hand joint (95th percentile of the vertices
  nearer that joint than its forearm's and the other hand's), in model units. The spell stance must reach
  OPEN_MIN_REACH times the fists' (v0.0.66-dev1, all 20 appearances, both hands: 3.12 to 3.33 against 2.08 to 2.15,
  1.47 to 1.58 times).

    python3 tools/ready_hands.py --data-files DIR --id1 IMAGE/boot/id1 [--json OUT]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

FP_SKELETON = 'meshes/base_anim.1st.nif'
FP_TABLE = 'progs/humanoid_1st.awsk'
HAND_CATALOG = 'gfx/hand-models.awh'
FIST_STANCE = 'hh'
SPELL_STANCES = ('sps', 'spt', 'sp')     # prepare_player_fp_parts.SPELL_STANCES (self, touch, target)
BAKED_SPELL_STANCE = 'sp'                # prepare_hand_catalog.SPELL_STANCE: <stem>_sp.mdl
IDLE_FRAMES = 8                          # prepare_hands.stance_clips: the idle clip, frames 0 to 7
SIDES = ('r', 'l')
CURL_JOINTS = tuple('finger%d%d' % (n, j) for n in (1, 2, 3, 4) for j in (1, 2))
FIST_MIN_CURL = 400.0
OPEN_MAX_CURL = 250.0
OPEN_MIN_REACH = 1.25


def turn_degrees(matrix):
    """How far a rotation (3 x 3, or the rotation of a 4 x 4) turns, in degrees."""
    import numpy as np
    r = np.asarray(matrix, float)[:3, :3]
    return float(np.degrees(np.arccos(np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0))))


def hand_curl(rotation_of, side):
    """The curl of one hand (degrees): rotation_of(joint name) -> that joint's local rotation."""
    return sum(turn_degrees(rotation_of('bip01 %s %s' % (side, j))) for j in CURL_JOINTS)


def table_curls(table, bones, group, frames=IDLE_FRAMES):
    """[(right curl, left curl)] at the first FRAMES frames of GROUP of a table (skeletal_actor.read_table's dict),
    from its stored keys as the engine reads them. bones: the table's bone names in order."""
    import skeletal_actor as sa
    names = [b.casefold() for b in bones]
    if group not in table['groups']:
        raise ValueError('The first-person table has no group %s' % group)
    first, last = table['groups'][group]
    out = []
    for f in range(first, min(last + 1, first + frames)):
        rotations, _ = sa.dequantise_table(table['q'][f], table['p'][f], table['scale'])

        def rotation_of(name):
            if name not in names:
                raise ValueError('The first-person table has no joint %s' % name)
            return sa.quat_to_matrix(rotations[names.index(name)])
        out.append(tuple(hand_curl(rotation_of, s) for s in SIDES))
    return out


def check_curls(fists, spells):
    """fists [(right, left)]; spells {stance: [(right, left)]}. Raises ValueError when a fist is not closed or a spell
    hand not open; returns {stance: [lowest, highest]}."""
    summary = {FIST_STANCE: [min(min(c) for c in fists), max(max(c) for c in fists)]}
    if summary[FIST_STANCE][0] < FIST_MIN_CURL:
        raise ValueError('First-person fists not closed: the bare hands curl %.0f degrees, at least %.0f wanted' % (
            summary[FIST_STANCE][0], FIST_MIN_CURL))
    for stance, curls in spells.items():
        summary[stance] = [min(min(c) for c in curls), max(max(c) for c in curls)]
        if summary[stance][1] > OPEN_MAX_CURL:
            raise ValueError('Readied-magic hands not open: spell stance %s curls %.0f degrees, at most %.0f '
                             '(the fists curl %.0f)' % (stance, summary[stance][1], OPEN_MAX_CURL, summary[FIST_STANCE][0]))
    return summary


def table_check(table_bytes, bones, spells=SPELL_STANCES):
    """The arms from parts: the table's fists against each spell stance (check_curls)."""
    import skeletal_actor as sa
    table = sa.read_table(table_bytes)
    return check_curls(table_curls(table, bones, FIST_STANCE),
                       {s: table_curls(table, bones, s) for s in spells})


def model_frame(raw, frame):
    """The vertices (nv, 3) of one frame of a vertex-animated alias model, in model units (scale and origin applied)."""
    import numpy as np
    if raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        raise ValueError('Not an alias model')
    scale = np.array(struct.unpack_from('<3f', raw, 8))
    origin = np.array(struct.unpack_from('<3f', raw, 20))
    skins, w, h, nv, nt, nf = struct.unpack_from('<6i', raw, 48)
    if skins != 1 or not 0 <= frame < nf:
        raise ValueError('Alias model outside the hand contract')
    at = 84 + 4 + w * h + nv * 12 + nt * 16 + frame * (28 + nv * 4)
    if struct.unpack_from('<i', raw, at)[0] != 0:
        raise ValueError('Alias model frame is not a single frame')
    verts = np.frombuffer(raw, np.uint8, nv * 4, at + 28).reshape(nv, 4)[:, :3].astype(float)
    return verts * scale + origin


def view_joints(skeleton, stance, frame=0):
    """{(side, 'hand'|'forearm'): position} of the hands' joints at FRAME of STANCE, in the baked arms' model space
    (prepare_hands.bake_appearance: skeleton units x 0.25, less the stance's first Camera, the view axes)."""
    import numpy as np
    from prepare_hands import sample_clips
    times, _ = sample_clips(skeleton.events, stance)
    camera = skeleton.pose(float(times[0]))('Camera')[3, :3] * .25
    pose = skeleton.pose(float(times[frame]))
    out = {}
    for side in SIDES:
        for joint in ('hand', 'forearm'):
            p = np.asarray(pose('bip01 %s %s' % (side, joint)), float)[3, :3] * .25 - camera
            out[(side, joint)] = p[[1, 0, 2]] * np.array([1.0, -1.0, 1.0])
    return out


def hand_reach(points, joints, side):
    """How far one hand reaches from its hand joint (95th percentile of the vertices nearer that joint than its
    forearm's and than the other hand's: the hands held close together keep their own vertices)."""
    import numpy as np
    other = 'l' if side == 'r' else 'r'
    hand, forearm = joints[(side, 'hand')], joints[(side, 'forearm')]
    d = np.linalg.norm(points - hand, axis=1)
    near = (d < np.linalg.norm(points - forearm, axis=1)) & (d < np.linalg.norm(points - joints[(other, 'hand')], axis=1))
    if near.sum() < 8:
        raise ValueError('Too few vertices at the %s hand joint' % ('right' if side == 'r' else 'left'))
    return float(np.percentile(d[near], 95))


def catalog_models(raw):
    """[(race, female, bare hands model)] of an AWH1 hand catalogue (prepare_hand_catalog.pack_catalog)."""
    magic, count, size = struct.unpack_from('>4sHH', raw, 0)
    if magic != b'AWH1' or len(raw) != 8 + count * size:
        raise ValueError('Not a hand catalogue')
    out = []
    for i in range(count):
        at = 8 + i * size
        race = raw[at:at + 64].rstrip(b'\0').decode('ascii')
        hand = raw[at + 68:at + 132].rstrip(b'\0').decode('ascii')
        out.append((race, bool(raw[at + 64]), hand))
    return out


def baked_check(skeleton, id1):
    """The baked arms: each appearance's spell arms (<stem>_sp.mdl) reach OPEN_MIN_REACH times its fists' (<stem>.mdl),
    both hands, at the idle's first frame. Returns {model: [right ratio, left ratio]}; raises ValueError."""
    id1 = Path(id1)
    fists, spell = view_joints(skeleton, FIST_STANCE), view_joints(skeleton, BAKED_SPELL_STANCE)
    out = {}
    for race, female, hand in catalog_models((id1 / HAND_CATALOG).read_bytes()):
        sp = hand[:-4] + '_sp.mdl'
        if not (id1 / sp).is_file():
            raise ValueError('The hand catalogue lacks its spell arms: ' + sp)
        a, b = model_frame((id1 / hand).read_bytes(), 0), model_frame((id1 / sp).read_bytes(), 0)
        ratios = [hand_reach(b, spell, s) / hand_reach(a, fists, s) for s in SIDES]
        out[sp] = [round(r, 3) for r in ratios]
        if min(ratios) < OPEN_MIN_REACH:
            raise ValueError('Readied-magic hands not open in %s: they reach %.2f times the fists of %s, at least %.2f'
                             % (sp, min(ratios), hand, OPEN_MIN_REACH))
    return out


def image_check(data_files, id1, log=print):
    """The check of an image's first-person data (the module text): the table of the arms from parts when the image
    has it, the baked arms when it has the hand catalogue. Returns the report; raises ValueError on a failure."""
    import prepare_player_fp_parts as fp
    import skeletal_actor as sa
    from mwad.audit import BSA
    from mwad.paths import resolve_data_files
    from npc_geometry import Assets, Skeleton
    data = resolve_data_files(Path(data_files))
    id1 = Path(id1)
    skeleton = Skeleton(Assets(data, BSA(data / 'Morrowind.bsa')), FP_SKELETON)
    report = {'fist_min_curl': FIST_MIN_CURL, 'open_max_curl': OPEN_MAX_CURL, 'open_min_reach': OPEN_MIN_REACH}
    if (id1 / FP_TABLE).is_file():
        bones = list(sa.KeptSkeleton(skeleton, fp.fp_bones(skeleton)).nodes)
        report['table'] = table_check((id1 / FP_TABLE).read_bytes(), bones)
        log('Readied-magic hands, arms from parts: fists curl %.0f-%.0f, spell stances %s (degrees; open below %.0f)' % (
            report['table'][FIST_STANCE][0], report['table'][FIST_STANCE][1],
            ', '.join('%s %.0f-%.0f' % (s, *report['table'][s]) for s in SPELL_STANCES), OPEN_MAX_CURL), flush=True)
    if (id1 / HAND_CATALOG).is_file():
        report['baked'] = baked_check(skeleton, id1)
        lows = [min(r) for r in report['baked'].values()]
        log('Readied-magic hands, baked arms: %d spell models reach %.2f-%.2f times their fists (at least %.2f)' % (
            len(lows), min(lows), max(lows), OPEN_MIN_REACH), flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--id1', type=Path, required=True)
    p.add_argument('--json', type=Path)
    a = p.parse_args(argv)
    try:
        report = image_check(a.data_files, a.id1)
    except ValueError as error:
        print('READY-HANDS FAIL: %s' % error, flush=True)
        return 1
    if a.json:
        a.json.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('READY-HANDS PASS', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
