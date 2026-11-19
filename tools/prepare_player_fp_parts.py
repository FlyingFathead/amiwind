#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The player's first-person arms assembled from parts by what is worn (docs/THIRD_PERSON.md "First-person arms";
PLAYER-GEAR-VISUAL-59, second slice).

The third-person body is assembled from parts (tools/prepare_player_parts.py); first person showed the baked bare
arms of the race and sex (tools/prepare_hand_catalog.py) whatever the hands wore. Here the same rule gives the arms:
the race's own hand, wrist, forearm and upper-arm parts (prepare_hands.appearance_parts: the first-person '.1st'
record first, then the third-person one, a woman then the man's, as the baked hands choose them), and over them the
parts the worn gloves, gauntlets, bracers, shirts and cuirasses give those slots, by the same ranks as the body.

Rules (read, not copied, from OpenMW 0.51 mwrender/npcanimation.cpp, which the baked hands follow too): first person
shows only the arm slots (hands, wrists, forearms, upper arms); for each part the record of the same id with '.1st'
appended is used when the game has one (the original's gauntlets and gloves have their own first-person meshes); the
first-person skeleton is meshes/base_anim.1st.nif. A robe shows its sleeves from its chest record's '.1st' (the
original's first-person robe mesh: chest shapes that hold only the sleeves, skinned to the arm bones) and covers the
forearms and upper arms under them; a robe without one leaves the arms as they are.

  id1/progs/humanoid_1st.awsk   the first-person table: the arms of base_anim.1st.nif (every finger joint: the hand
                                is seen close), 28 frames per stance in the baked hands' frame contract (prepare_hands
                                stance_clips: idle 8, draw 6, lower 4, punch 10) for the four stances in the engine's
                                order (bare hands, one-handed, two-handed close, two-handed wide; then bow, crossbow,
                                thrown and, last, the held light: the bare hands with the left arm on the original's
                                torch group, which a candle, candlestick or lantern takes). The root carries the
                                view: each stance's frames are taken from its first frame's Camera and turned to the
                                view axes, as prepare_hands bakes the arms, so a posed part is in view space and the
                                Weapon Bone tags of gfx/hand-weapons.aww place the weapon on it unchanged.
  id1/progs/parts/<2>/<10>.mdl  one skeletal model per (first-person skeleton, slot, mesh) (prepare_player_parts
                                part_path; the skeleton is in the key, so none is shared with the body's)
  id1/view/parts_1st.txt        the recipe (AWPP1, the body's format and reader, engine aw_player_parts.c): one
                                skeleton 'h' for every race (the baked hands use the one skeleton for all), the
                                races' skins, the items' first-person parts; '-/-' leaves the part under it showing.

Each part is a unit of the image unit cache ('player-fp-parts'). A part's triangles are capped by its slot (FP_CAP),
about the baked bare arms' own count, which keep the authored topology."""
import hashlib
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

FP_SKELETON = 'meshes/base_anim.1st.nif'
FP_TABLE = 'progs/humanoid_1st.awsk'
FP_RECIPE = 'view/parts_1st.txt'
UNIT_CACHE = 'player-fp-parts'
# the arm slots (mwad.npc.PART_NAMES): hands 6/7, wrists 8/9, forearms 11/12, upper arms 13/14
FP_SLOTS = (6, 7, 8, 9, 11, 12, 13, 14)
SLEEVES = (11, 12, 13, 14)
CHEST = 3
# the table's groups in the engine's stance order (aw_hand_models.c AW_HandStance + 1; 0 the bare hands)
STANCES = ('hh', '1h', '2c', '2w', 'bow', 'xb', '1t')     # the ranged three since v0.0.61 (FIRST-PERSON-WEAPONS-56)
# after them the held light (HELD-LIGHT-OWN-MODEL-61): the engine's stance 7 (aw_view.c HAND_PART_LIGHT)
LIGHT_STANCE = 'light'
# after the light the spell stance by range (PLAYER-CASTING-59, v0.0.66): the engine's stances 8 self, 9 touch,
# 10 target (aw_hand_models.h AW_HAND_SPELL_STANCE + range): the open hands and the cast of 'spellcast'
SPELL_STANCES = ('sps', 'spt', 'sp')
FRAMES = 28
# triangles per part by slot: the baked bare arms of a man keep about 700 of the source's (authored topology)
FP_CAP = {3: 160, 6: 320, 7: 320, 8: 48, 9: 48, 11: 120, 12: 120, 13: 80, 14: 80}
ROBE_RANK = 24
# a part keeps its authored (shared) vertices up to this many times its slot's cap of triangles; past it, the reduction
SOURCE_FACES = 2
# the view axes the baked hands use (prepare_hands: x = y, y = -x, z = z of the skeleton): p @ VIEW_AXES
VIEW_AXES = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


def fp_bones(skeleton):
    """The table's bones of the first-person skeleton (its parents {name: parent}): the root, the neck and every
    bone of both arms from the clavicle down (all finger joints, the shield and weapon bones); attachment nodes
    ('left hand') ride their bone (skeletal_actor.onto_kept)."""
    parents = skeleton.parents if hasattr(skeleton, 'parents') else skeleton
    keep = []
    for name in parents:
        n = name
        while n is not None and n not in ('bip01 l clavicle', 'bip01 r clavicle'):
            n = parents[n]
        if n is not None and (name.startswith('bip01 ') or name in ('shield bone', 'weapon bone')):
            keep.append(name)
    return tuple([n for n in ('bip01', 'bip01 neck') if n in parents and n not in keep] + keep)


def view_matrix(camera):
    """4 x 4 row-vector matrix: a skeleton point p to the view space of a camera at CAMERA (skeleton units):
    (p - camera) @ VIEW_AXES."""
    import numpy as np
    axes = np.array(VIEW_AXES)
    m = np.eye(4)
    m[:3, :3] = axes
    m[3, :3] = -np.asarray(camera, float) @ axes
    return m


def stance_times(skeleton):
    """[(stance, its 28 sample times)] in table order (prepare_hands.sample_clips: the baked hands' times)."""
    from prepare_hands import sample_clips
    return [(s, [float(t) for t in sample_clips(skeleton.events, s)[0]]) for s in STANCES]


def spell_times(skeleton):
    """[(spell stance, its 28 sample times)] in table order after the light (SPELL_STANCES)."""
    from prepare_hands import sample_clips
    return [(s, [float(t) for t in sample_clips(skeleton.events, s)[0]]) for s in SPELL_STANCES]


def camera_at(skeleton, t):
    import numpy as np
    return np.asarray(skeleton.pose(float(t))('camera'), float)[3, :3]


def light_times(skeleton, count=FRAMES):
    """The left arm's sample times of the light stance (HELD-LIGHT-OWN-MODEL-61): the original's first-person torch
    group (base_anim.1st.nif 'torch: start'..'torch: stop', the hold prepare_torch bakes in 8 phases), its 8 phases in
    turn over the stance's 28 frames."""
    start, stop = skeleton.events.get('torch: start'), skeleton.events.get('torch: stop')
    if start is None or stop is None or not stop > start:
        raise ValueError('The first-person skeleton has no torch group')
    return [float(start + (i % 8) / 8.0 * (stop - start)) for i in range(count)]


def left_arm(parents, bones):
    """The indices of the table's bones from the left clavicle down (the arm the carried light takes)."""
    out = set()
    for i, name in enumerate(bones):
        n = name
        while n is not None and n != 'bip01 l clavicle':
            n = parents.get(n)
        if n is not None:
            out.add(i)
    return sorted(out)


def fp_table(skeleton):
    """(table bytes, bone names, the bare hands' view matrix, the table's sample times): the first-person table of
    the skeleton (npc_geometry.Skeleton of base_anim.1st.nif). After the weapon stances the light stance
    (LIGHT_STANCE, HELD-LIGHT-OWN-MODEL-61): the bare hands' 28 frames with the left arm on the torch group, as the
    original layers a carried light over the hands."""
    import numpy as np
    import skeletal_actor as sa
    keep = fp_bones(skeleton)
    kept = sa.KeptSkeleton(skeleton, keep)
    bones = list(kept.nodes)
    parents = [-1 if kept.parents[b] is None else bones.index(kept.parents[b]) for b in bones]
    times, groups, views = [], {}, []
    for stance, t in stance_times(skeleton):
        if len(t) != FRAMES:
            raise ValueError('First-person stance %s has %d frames, not %d' % (stance, len(t), FRAMES))
        groups[stance] = (len(times), len(times) + FRAMES - 1)
        views.extend([view_matrix(camera_at(skeleton, t[0]))] * FRAMES)
        times.extend(t)
    rot, pos = sa.sample_table(kept, bones, times)
    hands = stance_times(skeleton)[0][1]
    groups[LIGHT_STANCE] = (len(times), len(times) + FRAMES - 1)
    views.extend([view_matrix(camera_at(skeleton, hands[0]))] * FRAMES)
    times.extend(hands)
    lrot, lpos = sa.sample_table(kept, bones, hands)
    trot, tpos = sa.sample_table(kept, bones, light_times(skeleton))
    arm = left_arm(kept.parents, bones)
    lrot[:, arm], lpos[:, arm] = trot[:, arm], tpos[:, arm]
    rot, pos = np.concatenate((rot, lrot)), np.concatenate((pos, lpos))
    for stance, t in spell_times(skeleton):
        groups[stance] = (len(times), len(times) + FRAMES - 1)
        views.extend([view_matrix(camera_at(skeleton, t[0]))] * FRAMES)
        times.extend(t)
        srot, spos = sa.sample_table(kept, bones, t)
        rot, pos = np.concatenate((rot, srot)), np.concatenate((pos, spos))
    for f, view in enumerate(views):
        for b, parent in enumerate(parents):
            if parent < 0:
                m = sa.local_matrix(rot[f, b], pos[f, b]) @ view
                rot[f, b] = sa.matrix_to_quat(m[:3, :3])
                pos[f, b] = m[3, :3]
    for f in range(1, len(times)):          # the shorter way between neighbouring frames (build_table's rule)
        flip = np.einsum('bi,bi->b', rot[f], rot[f - 1]) < 0
        rot[f, flip] = -rot[f, flip]
    q, p, scale = sa.quantise_table(rot, pos)
    data = sa.write_table(parents, groups, q, p, scale, sa.TABLE_RATE, sa.POSITION_TOLERANCE)
    return data, bones, views[0], times


def first_person_id(bodies, body):
    """The record a part of BODY shows in first person: BODY + '.1st' when the game has it, else BODY (ids
    case-folded; None stays None). bodies: {case-folded id: id}."""
    if not body:
        return None
    return bodies.get(body.casefold() + '.1st') or bodies.get(body.casefold())


def fp_item_rows(kinds, items=None):
    """The worn items' first-person parts: per item its rank and per arm slot [male, female] body ids (their '.1st'
    records where the game has them). A robe whose chest record has a '.1st' shows it in the chest slot (CHEST: the
    original's first-person robe mesh holds only the sleeves, skinned to the arm bones) and covers the forearms and
    upper arms under them (None: nothing shows, the robe's cover of the body); an explicit arm part of its own first.
    Items without an arm part are left out (they leave the arms as they are)."""
    import prepare_player_parts as ppp
    bodies = {b.casefold(): b for b in kinds.get('BODY', {})}
    out = []
    for row in (items if items is not None else ppp.item_rows(kinds)):
        slots = {}
        for s, pair in sorted(row['slots'].items()):
            if s in FP_SLOTS and pair and (pair[0] or pair[1]):
                slots[s] = [first_person_id(bodies, pair[0]), first_person_id(bodies, pair[1])]
        if row['rank'] == ROBE_RANK and (row['slots'].get(CHEST) or [None])[0]:
            male, female = row['slots'][CHEST]
            sleeve = [bodies.get((b or '').casefold() + '.1st') for b in (male, female)]
            if sleeve[0] or sleeve[1]:
                slots[CHEST] = sleeve
                for s in SLEEVES:
                    slots.setdefault(s, None)
        if slots:
            out.append({'id': row['id'], 'kind': row['kind'], 'rank': row['rank'], 'slots': slots})
    return out


def race_skins(kinds, assets=None):
    """Per playable race and sex its arm skin parts (prepare_hands.appearance_parts, the baked hands' choice; with
    ASSETS a hand record naming another race's or sex's mesh takes the race's own, FP-HANDS-PER-RACE-67):
    [{'race', 'female', 'skin': {slot: body id}, 'mesh': {body id: mesh}, 'record_mesh': {body id: the record's mesh}
    (only where they differ)}]."""
    from prepare_hands import appearance_parts
    from prepare_player_view import playable_races
    rows = []
    for race in playable_races(kinds):
        for female in (False, True):
            parts = appearance_parts(kinds, race, female, assets)
            rows.append({'race': race, 'female': female,
                         'skin': {p['slot']: p['id'] for p in parts if p['slot'] in FP_SLOTS},
                         'mesh': {p['id']: p['mesh'] for p in parts},
                         'record_mesh': {p['id']: p['record_mesh'] for p in parts if p.get('record_mesh')}})
    return rows


def recipe_text(races, items, models, bones):
    """The first-person recipe (AWPP1, the body's format: tools/prepare_player_parts.py recipe_text, read by the
    engine's aw_player_parts.c): one table 'h', no groups ('-'), every race at the unit scale, its skin per slot, the
    items' parts per slot as '<hex>/-' (no beast column), '-/-' where a part has no model (the one under it shows).
    models {(slot, body id): part path}; bones (weapon bone, shield bone) of the table."""
    from prepare_player_parts import part_hex

    def word(s):
        if any(c in s for c in '\t\n=,|') or not s.isascii():
            raise ValueError('Recipe id not plain ASCII: ' + s)
        return s.replace(' ', '|')
    lines = ['AWPP1', 'T h %s %d %d' % (FP_TABLE, bones[0], bones[1]), 'A h 0 -', 'A h 1 -']
    words = {}
    for item in items:
        if words.setdefault(word(item['id']), item['id']) != item['id']:
            raise ValueError('Two items share the recipe word %s' % word(item['id']))
    for r in races:
        race, f = word(r['race']), int(r['female'])
        lines.append('R %s %d h 1.0000 1.0000' % (race, f))
        for slot, body in sorted(r['skin'].items()):
            if (slot, body) in models:
                lines.append('S %s %d %d %s' % (race, f, slot, part_hex(models[(slot, body)])))
    for item in items:
        sides = []
        for slot, pair in sorted(item['slots'].items()):
            if pair is None:                              # covered: nothing shows (a robe over the arms)
                sides.append('%d=-,-' % slot)
                continue
            cols = []
            for body in (pair[0], pair[1] or pair[0]):    # a woman wears the man's part where none is hers
                path = models.get((slot, body)) if body else None
                cols.append('%s/-' % part_hex(path) if path else '-/-')
            sides.append('%d=%s' % (slot, ','.join(cols)))
        lines.append('I %s %d %s' % (word(item['id']), item['rank'], ' '.join(sides)))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- the bare hand's own skin

# FP-TORCH-HAND-REGRESSION-67 (the maintainer, 2026-11-18: the bare hand is the same colour as the arm). The game's
# first-person hand records of some races are another race's or sex's mesh, which names that one's skin textures: the
# Nord man's .1st hands are the Imperial man's (their textures about 146 97 76 against the Nord arm's 197 148 125), the
# Imperial woman's the Nord woman's, the Dark Elf and Redguard men's the women's. Such a bare hand (a skin part, BYDT
# type 0, in a hand slot) takes the race's and sex's own hand textures of the same part (TX_B_N_<race>_<M|F>_H<part>,
# the ones its third-person hand uses, which match its arm) where the game has them; every other part is untouched.
HAND_SLOTS = (6, 7)
SKIN_TEXTURE = re.compile(r'^tx_b_n_(.+)_([mf])_(h[a-z]+)\.([a-z0-9]+)$')
# Decided for the project, 2026-11-18: for every race and sex the bare hand matches its arm, as drawn. Where the drawn hand still differs from the drawn forearm of its side after its own textures (the
# Argonian and Khajiit men's own art: 56 and 63 per channel in their textures), its skin is tinted to the forearm's by
# a measured factor per channel (the drawn forearm's mean over the drawn hand's), put back on the game palette: the
# hand keeps its own detail and the gap in the mean goes (the arm's texture would not fit the hand's UVs). SKIN_GAP, the
# largest channel gap allowed between the drawn hand and the drawn forearm, in the image's 0..255 colours: 16, two steps
# of the game palette's skin ramps (a smaller difference is lost when a part is put on the palette); the original's own
# hands that match their arms draw 2 to 13 (the Breton, Imperial, Nord, Orc, Redguard and Wood Elf men).
SKIN_GAP = 16
FOREARM_OF = {6: 11, 7: 12}            # a hand slot and the forearm slot of its side
SKIN_COLOURS = 224                     # the palette's ordinary colours (224..255 are its full-bright ones)


TINT_ROUNDS = 4                        # bakes of a hand at most to bring it within SKIN_GAP of its forearm

# FP-HANDS-PER-RACE-67 (decided for the project, 2026-11-18: no steep colour step at any seam of the arm, whatever the
# race). The check above compared each hand's whole mean with its forearm's whole mean, but in first person the hand
# meets the WRIST part (slots 8 and 9) and the wrist the forearm, and a part's colour at a seam is not its whole mean:
# on the v0.0.67-dev2 image the step where the hand meets the wrist was up to 54.9 per channel (the Nord man), and with
# the hand-to-forearm tint still up to 40.2 (the Khajiit woman), while that check read 15.6; the game's own wrist and
# forearm parts step by up to 36.6 (the Khajiit man). SEAM_MATCH 'seams' (the default): along each arm the wrist is
# tinted to the forearm at their seam, then the hand to the wrist as it now draws, each by the measured factor (the
# part's colour at the seam over the other part's), until within SEAM_TARGET (one step of the palette's skin colours)
# or TINT_ROUNDS bakes, the best bake kept; the stage stops when a seam is left over SKIN_GAP. 'forearm' = the method of
# c1a11300 (the hand to the forearm's whole mean, check_hand_gaps); 'off' = no tint (the seams reported, not checked).
# The original's look = SEAM_MATCH 'off', OWN_SKIN False and player_own_skin.OWN_HAND_MESHES False.
SEAM_MATCH = 'seams'
SEAM_MATCHES = ('seams', 'forearm', 'off')
OWN_SKIN = True                        # own_skin below: a hand of another race's or sex's textures takes the race's own
SEAM_UNITS = 0.75                      # view-model units: a part's vertices this close to the other part are its seam
SEAM_TARGET = 8                        # the tint aims within one palette step; SKIN_GAP (two) stops the stage
SEAM_FRAME = 0                         # the table frame the seams are read at: the bare hands' first frame
ARM_CHAINS = (('right', 6, 8, 11), ('left', 7, 9, 12))   # side, hand, wrist and forearm slots


def _parsed(raw):
    """A part model's skin and triangles (the alias header at 48: skins, width, height, vertices, triangles)."""
    import struct
    import numpy as np
    _, w, h, nv, nt = struct.unpack_from('<5i', raw, 48)
    at = 88 + w * h
    return {'w': w, 'h': h, 'texels': np.frombuffer(raw, np.uint8, w * h, 88).reshape(h, w),
            'st': np.frombuffer(raw, '<i4', nv * 3, at).reshape(nv, 3),
            'tris': np.frombuffer(raw, '<i4', nt * 4, at + nv * 12).reshape(nt, 4)}


def covered_mean(m, tri_ids, palette):
    """The mean RGB of the skin texels the triangles TRI_IDS of the parsed model M cover, on PALETTE (drawn_skin_mean's
    rule), or None."""
    import numpy as np
    w, h, st = m['w'], m['h'], m['st']
    if len(tri_ids) == 0:
        return None
    ys, xs = np.mgrid[0:h, 0:w]
    used = np.zeros((h, w), bool)
    for front, *corner in m['tris'][tri_ids]:
        pts = [(int(min(max(st[v][1] + (w // 2 if not front and st[v][0] else 0), 0), w - 1)),
                int(min(max(st[v][2], 0), h - 1))) for v in corner]
        (ax, ay), (bx, by), (cx, cy) = pts
        x0, x1, y0, y1 = min(ax, bx, cx), max(ax, bx, cx), min(ay, by, cy), max(ay, by, cy)
        sx, sy = xs[y0:y1 + 1, x0:x1 + 1], ys[y0:y1 + 1, x0:x1 + 1]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if area == 0:
            used[y0:y1 + 1, x0:x1 + 1] = True
            continue
        w0 = ((bx - sx) * (cy - sy) - (cx - sx) * (by - sy)) / area
        w1 = ((cx - sx) * (ay - sy) - (ax - sx) * (cy - sy)) / area
        used[y0:y1 + 1, x0:x1 + 1] |= (w0 >= -.01) & (w1 >= -.01) & (w0 + w1 <= 1.01)
    colours = np.frombuffer(palette, np.uint8).reshape(256, 3).astype(float)
    return colours[m['texels'][used]].mean(0) if used.any() else None


def seam_pair_means(ma, pa, mb, pb, palette, units=SEAM_UNITS):
    """(A's colour at its seam with B, B's colour at its seam with A): the covered mean of each model's triangles that
    touch its vertices lying within UNITS of the other model's (PA, PB: the drawn vertex positions)."""
    import numpy as np
    pa, pb = np.asarray(pa, float), np.asarray(pb, float)
    d = np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=2)
    va, vb = np.where(d.min(1) < units)[0], np.where(d.min(0) < units)[0]
    ta = np.where(np.isin(ma['tris'][:, 1:], va).any(1))[0]
    tb = np.where(np.isin(mb['tris'][:, 1:], vb).any(1))[0]
    return covered_mean(ma, ta, palette), covered_mean(mb, tb, palette)


def _drawn_points(raw, table, frame=SEAM_FRAME):
    """A part model's vertices as the renderer draws them at the table FRAME (skeletal_actor.engine_pose, the alias
    scale and origin): view-model units."""
    import skeletal_actor as sa
    k = sa.read_skeletal(raw)
    return sa.engine_pose(k, table, frame) * k['scale'] + k['origin']


def seam_skin_means(raw_a, raw_b, table, palette):
    """seam_pair_means of two part models (bytes) posed on TABLE (skeletal_actor.read_table's)."""
    return seam_pair_means(_parsed(raw_a), _drawn_points(raw_a, table), _parsed(raw_b), _drawn_points(raw_b, table),
                           palette)


def _arm_seams(r, models):
    """[(side, seam name, part path, the path of the part it meets)] of a race row, each side's wrist and forearm first,
    then its hand and wrist (the hand and forearm when there is no wrist part)."""
    out = []
    for side, hand, wrist, arm in ARM_CHAINS:
        h, w, f = (models.get((s, r['skin'].get(s))) for s in (hand, wrist, arm))
        if w:
            out += [(side, 'wrist to forearm', w, f), (side, 'hand to wrist', h, w)]
        else:
            out.append((side, 'hand to forearm', h, f))
    return out


def seam_gaps(races, models, results, palette, table, means=seam_skin_means):
    """[{race, female, side, seam, part, meets, colours, gap}] of every race, sex and arm seam, from the baked models
    (RESULTS {path: (bytes, report)}, MODELS {(slot, body): path}); gap None when a part is not baked."""
    out = []
    for r in races:
        for side, seam, a, b in _arm_seams(r, models):
            ca, cb = means(results[a][0], results[b][0], table, palette) if a in results and b in results else (None,
                                                                                                                None)
            out.append({'race': r['race'], 'female': r['female'], 'side': side, 'seam': seam, 'part': a, 'meets': b,
                        'colours': [None if c is None else [round(float(v), 1) for v in c] for c in (ca, cb)],
                        'gap': skin_gap(ca, cb)})
    return out


def check_seams(gaps, limit=SKIN_GAP):
    """Stop the stage (ValueError naming them) when a seam of the arm steps by more than LIMIT per channel."""
    off = [g for g in gaps if g['gap'] is not None and g['gap'] > limit]
    if off:
        raise ValueError('FP-HANDS-PER-RACE-67: a first-person arm steps in colour at a seam by more than %d: %s' % (
            limit, '; '.join('%s %s %s %s: %s' % (g['race'], 'f' if g['female'] else 'm', g['side'], g['seam'], g['gap'])
                             for g in off)))


def match_seams(races, models, results, palette, table, tasks, bake, means=seam_skin_means):
    """In place on RESULTS: along each arm of every race and sex, the wrist part tinted to the forearm at their seam,
    then the hand to the wrist as it now draws (the part's 'skin_tint': the other part's colour at the seam over this
    one's, compounded each round), while the step is over SEAM_TARGET, at most TINT_ROUNDS bakes, the bake with the
    smallest step kept. A model is matched once (the first race that names it). TASKS {model path: task}; BAKE(task)
    -> (path, bytes, report). Returns [{race, female, side, seam, factor, gap_before, gap_after, bakes}]."""
    import numpy as np
    done, out = set(), []
    for r in races:
        for side, seam, part, ref in _arm_seams(r, models):
            if part in done or part not in results or ref not in results or part not in tasks:
                continue
            done.add(part)
            a, b = means(results[part][0], results[ref][0], table, palette)
            first = gap = skin_gap(a, b)
            if gap is None:
                continue
            factor, bakes = np.ones(3), 0
            best = (gap, results[part], factor)
            while gap > SEAM_TARGET and bakes < TINT_ROUNDS and not np.any(np.asarray(a) <= 0):
                factor = factor * (np.asarray(b) / np.asarray(a))
                data, pal, p, cap = tasks[part]
                _, raw, report = bake((data, pal, dict(p, skin_tint=[round(float(f), 4) for f in factor]), cap))
                bakes += 1
                a, _ = means(raw, results[ref][0], table, palette)
                gap = skin_gap(a, b)
                if gap is None:
                    break
                if gap < best[0]:
                    best = (gap, (raw, report), factor)
            results[part] = best[1]
            if bakes:
                out.append({'race': r['race'], 'female': r['female'], 'side': side, 'seam': seam,
                            'factor': [round(float(f), 4) for f in best[2]], 'gap_before': first,
                            'gap_after': best[0], 'bakes': bakes})
    return out


def check_own_hands(races, models, results, meshes=True, textures=True):
    """Stop the stage (ValueError naming them) when a race's or sex's bare first-person hand is drawn from another race's
    or sex's hand mesh (MESHES: its file name, player_own_skin.HAND_MESH_NAME) or skin textures (TEXTURES: a texture
    name SKIN_TEXTURE reads, not swapped by own_skin). The part reports carry the mesh and the textures drawn."""
    from player_own_skin import HAND_MESH_NAME, names_other, race_key
    off = []
    for r in races:
        race, sex = r['race'].casefold(), 'f' if r['female'] else 'm'
        for slot in HAND_SLOTS:
            path = models.get((slot, r['skin'].get(slot)))
            if path not in results:
                continue
            report = results[path][1]
            name = str(report.get('mesh', '')).replace('\\', '/').rsplit('/', 1)[-1].casefold()
            m = HAND_MESH_NAME.match(name)
            # the race read with or without its space (player_own_skin.race_key: 'DarkElf' is the Dark Elf's own)
            if meshes and m and names_other(m, race, r['female']):
                off.append('%s %s slot %d: mesh %s' % (race, sex, slot, report.get('mesh')))
            swapped = report.get('skin_textures') or {}
            for t in report.get('textures') or []:
                s = SKIN_TEXTURE.match(str(t).replace('\\', '/').rsplit('/', 1)[-1].casefold())
                if textures and s and (race_key(s.group(1)), s.group(2)) != (race_key(race), sex) and t not in swapped:
                    off.append('%s %s slot %d: texture %s' % (race, sex, slot, t))
    if off:
        raise ValueError('FP-HANDS-PER-RACE-67: a first-person hand is another race\'s or sex\'s: %s' % '; '.join(off))


def tint_textures(textures, factor):
    """In place on assemble's TEXTURES {name: RGBA}: the colours scaled per channel by FACTOR (before the bake puts them
    on the palette, as every part's colours are)."""
    import numpy as np
    f = np.asarray(factor, float)
    for name, image in list(textures.items()):
        if image is not None:
            out = np.array(image, dtype=float)
            out[..., :3] = np.clip(np.rint(out[..., :3] * f), 0, 255)
            textures[name] = out.astype(np.uint8)


def skin_gap(a, b):
    """The largest channel difference of two RGB means (None when either is missing)."""
    if a is None or b is None:
        return None
    return round(float(max(abs(float(x) - float(y)) for x, y in zip(a, b))), 1)


def drawn_skin_mean(raw, palette):
    """The mean RGB of the skin texels a part model's triangles cover (as drawn: its own skin on the game palette)."""
    import struct
    import numpy as np
    _, w, h, nv, nt = struct.unpack_from('<5i', raw, 48)
    texels = np.frombuffer(raw, np.uint8, w * h, 88).reshape(h, w)
    at = 88 + w * h
    st = np.frombuffer(raw, '<i4', nv * 3, at).reshape(nv, 3)
    tris = np.frombuffer(raw, '<i4', nt * 4, at + nv * 12).reshape(nt, 4)
    ys, xs = np.mgrid[0:h, 0:w]
    used = np.zeros((h, w), bool)
    for front, *corner in tris:
        pts = [(int(min(max(st[v][1] + (w // 2 if not front and st[v][0] else 0), 0), w - 1)),
                int(min(max(st[v][2], 0), h - 1))) for v in corner]
        (ax, ay), (bx, by), (cx, cy) = pts
        x0, x1, y0, y1 = min(ax, bx, cx), max(ax, bx, cx), min(ay, by, cy), max(ay, by, cy)
        sx, sy = xs[y0:y1 + 1, x0:x1 + 1], ys[y0:y1 + 1, x0:x1 + 1]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if area == 0:
            used[y0:y1 + 1, x0:x1 + 1] = True
            continue
        w0 = ((bx - sx) * (cy - sy) - (cx - sx) * (by - sy)) / area
        w1 = ((cx - sx) * (ay - sy) - (ax - sx) * (cy - sy)) / area
        used[y0:y1 + 1, x0:x1 + 1] |= (w0 >= -.01) & (w1 >= -.01) & (w0 + w1 <= 1.01)
    colours = np.frombuffer(palette, np.uint8).reshape(256, 3).astype(float)
    return colours[texels[used]].mean(0) if used.any() else None


def _hand_pairs(races, models):
    """(race row, hand slot, hand model path, forearm model path) of every race and sex and both hands."""
    for r in races:
        for slot, arm_slot in sorted(FOREARM_OF.items()):
            yield (r, slot, models.get((slot, r['skin'].get(slot))), models.get((arm_slot, r['skin'].get(arm_slot))))


def hand_arm_gaps(races, models, results, palette):
    """[{race, female, slot, hand, forearm, gap}] of every race, sex and hand: the drawn bare hand against the drawn
    forearm of its side, from the baked models (RESULTS {path: (bytes, report)}, MODELS {(slot, body): path})."""
    out = []
    for r, slot, hand, arm in _hand_pairs(races, models):
        a = drawn_skin_mean(results[hand][0], palette) if hand in results else None
        b = drawn_skin_mean(results[arm][0], palette) if arm in results else None
        out.append({'race': r['race'], 'female': r['female'], 'slot': slot,
                    'hand': None if a is None else a.round(1).tolist(),
                    'forearm': None if b is None else b.round(1).tolist(), 'gap': skin_gap(a, b)})
    return out


def check_hand_gaps(gaps):
    """Stop the stage (ValueError, naming them) when a race's bare hand differs from its forearm by more than SKIN_GAP;
    a hand or forearm not baked (gap None) is in the stage's 'failed' list already."""
    off = [g for g in gaps if g['gap'] is not None and g['gap'] > SKIN_GAP]
    if off:
        raise ValueError('FP-BARE-HAND-OTHER-SKIN-67: the first-person bare hand differs from its arm by more than %d: %s'
                         % (SKIN_GAP, '; '.join('%s %s slot %d: %s' % (g['race'], 'f' if g['female'] else 'm', g['slot'],
                                                                        g['gap']) for g in off)))


def match_hands(races, models, results, palette, tasks, bake):
    """In place on RESULTS: every bare hand drawn more than SKIN_GAP from the forearm of its side baked again with its
    textures tinted (the part's 'skin_tint': the drawn forearm's mean over the drawn hand's, compounded each round, at
    most TINT_ROUNDS bakes). TASKS {model path: task}; BAKE(task) -> (path, bytes, report). A hand model is matched
    once (the first race that names it). Returns [{race, female, slot, factor, gap_before, gap_after, bakes}]."""
    import numpy as np
    done, out = set(), []
    for r, slot, hand, arm in _hand_pairs(races, models):
        if hand in done or hand not in results or arm not in results or hand not in tasks:
            continue
        done.add(hand)
        b = drawn_skin_mean(results[arm][0], palette)
        a = drawn_skin_mean(results[hand][0], palette)
        first = gap = skin_gap(a, b)
        factor, bakes = np.ones(3), 0
        while gap is not None and gap > SKIN_GAP and bakes < TINT_ROUNDS and not np.any(a <= 0):
            factor = factor * (b / a)
            data, pal, part, cap = tasks[hand]
            _, raw, report = bake((data, pal, dict(part, skin_tint=[round(float(f), 4) for f in factor]), cap))
            bakes += 1
            a = drawn_skin_mean(raw, palette)
            gap = skin_gap(a, b)
            results[hand] = (raw, report)
        if bakes:
            out.append({'race': r['race'], 'female': r['female'], 'slot': slot,
                        'factor': [round(float(f), 4) for f in factor], 'gap_before': first, 'gap_after': gap,
                        'bakes': bakes})
    return out


def own_skin_name(texture, race, female):
    """The race's and sex's own counterpart (textures/tx_b_n_<race>_<m|f>_h<part>.<ext>) of a hand skin texture named
    for another race or sex; None for one of its own (the race read with or without its space, player_own_skin.race_key)
    or a texture that is no hand skin."""
    from player_own_skin import race_key
    m = SKIN_TEXTURE.match(str(texture or '').replace('\\', '/').rsplit('/', 1)[-1].casefold())
    sex = 'f' if female else 'm'
    if not m or not race or (race_key(m.group(1)) == race_key(race) and m.group(2) == sex):
        return None
    return 'textures/tx_b_n_%s_%s_%s.%s' % (race.casefold(), sex, m.group(3), m.group(4))


def own_skin(textures, kinds, part, assets):
    """In place on assemble's TEXTURES {name: image}: a bare hand part's skin textures of another race or sex replaced
    by the race's own of the same part where the game has them. Returns the swaps {name: own name}."""
    if part.get('slot') not in HAND_SLOTS:
        return {}
    from mwad.npc import first, text
    record = kinds.get('BODY', {}).get(part.get('id'))
    raw = first(record, 'BYDT') if record is not None else None
    if not raw or len(raw) < 4 or raw[3] != 0:              # BYDT: part, vampire, flags (1 female), type (0 skin)
        return {}
    race, female = text(record, 'FNAM') or '', bool(raw[2] & 1)
    swaps = {}
    for name in list(textures):
        own = own_skin_name(name, race, female)
        if not own:
            continue
        try:
            textures[name] = assets.texture(own)
        except ValueError:                                  # the game has no own one: the mesh's stays
            continue
        swaps[name] = own
    return swaps


def skin_tag(kinds, slot, body):
    """'<race>_<m|f>' of a bare hand part (a skin record in a hand slot), else None: its model is keyed by it, so two
    races' records on one hand mesh (the Nord man's and the Imperial man's) are two models when their skins differ."""
    if slot not in HAND_SLOTS:
        return None
    from mwad.npc import first, text
    record = kinds.get('BODY', {}).get(body)
    raw = first(record, 'BYDT') if record is not None else None
    if not raw or len(raw) < 4 or raw[3] != 0:
        return None
    race = (text(record, 'FNAM') or '').casefold()
    return '%s_%s' % (race, 'f' if raw[2] & 1 else 'm') if race else None


def fp_part_path(part):
    """The part's model path (prepare_player_parts.part_path on the first-person skeleton), a bare hand's own skin
    (skin_tag) in its key."""
    from prepare_player_parts import part_path
    skin = part.get('skin')
    return part_path(FP_SKELETON, dict(part, mesh=part['mesh'] + '|' + skin) if skin else part)


# ---------------------------------------------------------------- one part (a pool unit)

_rig = {}


def _fp_rig(assets):
    """(skeleton, table bytes, bone names, the bare hands' view matrix, the bare hands' times), once per process."""
    if 'rig' not in _rig:
        from npc_geometry import Skeleton
        rig = Skeleton(assets, FP_SKELETON)
        table, bones, view, _ = fp_table(rig)
        _rig['rig'] = (rig, table, bones, view, stance_times(rig)[0][1])
    return _rig['rig']


def bake_part(task):
    """Worker: one first-person part model. task = (data, palette, part, cap). Returns (path, mdl bytes, report)."""
    import numpy as np
    import prepare_player_view as ppv
    import skeletal_actor as sa
    from npc_geometry import assemble
    from prepare_player_parts import quotas_for
    data, palette, part, cap = task
    kinds, assets, _ = ppv._sources(data)
    rig, table, bones, view, times = _fp_rig(assets)
    appearance = {'id': 'first-person part ' + part['id'], 'skeleton': FP_SKELETON, 'female': False, 'weight': 1.0,
                  'height': 1.0, 'parts': [part]}
    shapes, materials, textures = assemble(assets, appearance, rig, times)
    if not shapes:
        raise ValueError('Part %s (%s) has no drawn shape' % (part['id'], part['mesh']))
    skin_swaps = own_skin(textures, kinds, part, assets) if OWN_SKIN else {}   # the bare hand in its race's own skin
    if part.get('skin_tint'):
        tint_textures(textures, part['skin_tint'])         # and tinted to its arm (match_hands)
    # into the view space as the baked hands (prepare_hands: model units, the camera at the first frame)
    for shape in shapes:
        shape['positions'] = np.asarray(shape['positions'], float) @ view[:3, :3] + view[3, :3] * .25
    sources = sa.export_actor(assets, appearance, rig)
    rest = rig.pose(float(times[0]))

    def rest_world(name):
        return np.asarray(rest(name), float) @ view
    common = (shapes, materials, textures, palette, sources, rest_world, [.25, .25, .25], table, bones)
    try:
        # the authored vertices, shared (FP-ARMS-PARTS-COST-59): the baked arms keep the source topology too; the
        # face-tile reduction gave every triangle its own three vertices, about three times the baked arms' count
        raw, facts = sa.skeletal_from_shapes(*common, table_path=FP_TABLE, parents=rig.parents, topology='source')
        if facts['faces'] > SOURCE_FACES * cap:
            raise ValueError('source topology past %d x the slot cap' % SOURCE_FACES)
    except ValueError:
        # a part the shared encoding cannot take (past its bounds, translucent, or much past the slot's cap)
        raw, facts = sa.skeletal_from_shapes(*common, table_path=FP_TABLE, budgets=(cap,),
                                             quotas=quotas_for(shapes, cap), head_detail='budget',
                                             body_skin_rows=480, parents=rig.parents)
    out = fp_part_path(part)
    return out, raw, {'id': part['id'], 'slot': part['slot'], 'mesh': part['mesh'], 'skeleton': FP_SKELETON,
                      'model': out, 'bytes': len(raw), 'faces': facts['faces'], 'vertices': facts['vertices'],
                      'topology': facts['topology'], 'skin_textures': skin_swaps, 'skin_tint': part.get('skin_tint'),
                      'textures': sorted(str(t) for t in textures),
                      'sha256': hashlib.sha256(raw).hexdigest()}


def _safe_bake(task):
    """bake_part; a part that cannot be baked is named and left out (the part under it shows)."""
    try:
        return bake_part(task)
    except Exception as error:  # noqa: BLE001  (named in the report; the slot falls back)
        return 'FAILED %s: %s: %s' % (unit_inputs(task)['entry']['name'], type(error).__name__, error)


def unit_inputs(task):
    data, palette, part, cap = task
    # a part's skin block names the table's frame count (aw_skel_load.c refuses a part whose count differs), so the
    # table's frames are part of the key: the light stance (v0.0.61) made every part again once
    return {'entry': {'name': 'first-person part %d %s' % (part['slot'], part['id'])}, 'skeleton': FP_SKELETON,
            'part': part, 'cap': cap, 'palette_sha256': hashlib.sha256(palette).hexdigest(),
            'table_frames': FRAMES * (len(STANCES) + 1 + len(SPELL_STANCES))}


def _unit_cache():
    from pass_cache import UnitCache, game_data_digest
    game = game_data_digest()
    if game is None:
        return None
    import skeletal_actor
    import npc_geometry
    import prepare_hands
    return UnitCache.open(UNIT_CACHE, {'game_data': game}, __file__, skeletal_actor.__file__, npc_geometry.__file__,
                          prepare_hands.__file__)


# ---------------------------------------------------------------- the stage

def prepare(data, id1, palette, jobs=None, log=print):
    """Bake the first-person parts, the table and the recipe into ID1. Returns the report."""
    import prepare_player_view as ppv
    from build_parallel import stage_pool
    from mwad.npc import text
    from pass_cache import forced
    from prepare_player_parts import part_dict, part_path, write_same
    started = time.monotonic()
    if SEAM_MATCH not in SEAM_MATCHES:
        raise ValueError('SEAM_MATCH must be one of %s: %r' % (SEAM_MATCHES, SEAM_MATCH))
    kinds, assets, _ = ppv._sources(data)
    races = race_skins(kinds, assets)
    items = fp_item_rows(kinds)
    need = set()
    # a race's skin part draws the mesh its row names (a hand record naming another race's mesh: the race's own,
    # player_own_skin.own_hand_mesh); an item's part the mesh its record names
    skin_mesh = {}
    for r in races:
        need.update(r['skin'].items())
        for slot, body in r['skin'].items():
            skin_mesh[(slot, body)] = r['mesh'].get(body)
    own_meshes = sorted({(r['race'], 'f' if r['female'] else 'm', body, named, r['mesh'][body])
                         for r in races for body, named in r['record_mesh'].items()})
    for race, sex, body, named, own in own_meshes:
        log('first-person parts: %s %s hand %s: the record names %s, the race\'s own %s is drawn '
            '(FP-HANDS-PER-RACE-67)' % (race, sex, body, named, own), flush=True)
    for item in items:
        for slot, pair in item['slots'].items():
            need.update((slot, b) for b in (pair or ()) if b)
    tasks = []
    for slot, body in sorted(need):
        record = kinds['BODY'].get(body)
        mesh = skin_mesh.get((slot, body)) or (text(record, 'MODL') if record is not None else None)
        if mesh:
            part = part_dict(slot, body, mesh)
            skin = skin_tag(kinds, slot, body)
            if skin:
                part['skin'] = skin
            tasks.append((str(data), palette, part, FP_CAP.get(slot, 64)))
    unique = {}
    for t in tasks:
        unique.setdefault(fp_part_path(t[2]), t)
    log('=== PHASE 1/3: first-person parts: %d part uses, %d models to bake or reuse ===' % (len(tasks), len(unique)),
        flush=True)
    cache = _unit_cache()
    todo, results, failed = [], {}, []
    for path, t in unique.items():
        found = None
        if cache is not None and not forced(UNIT_CACHE, unit_inputs(t)['entry']['name']):
            found = cache.load_unit(unit_inputs(t))
        if found is not None:
            row, files = found
            results[path] = (files['0'], row['report'])
        else:
            todo.append(t)
    reused = len(results)
    if todo:
        import unit_store
        from build_jobs import resolve_jobs
        workers = max(1, min(resolve_jobs(jobs), len(todo)))
        names = [unit_inputs(t)['entry']['name'] for t in todo]
        log('first-person parts: %d to bake on %d workers' % (len(todo), workers), flush=True)

        def keep(index, result):
            # each part into the unit cache the moment it is back (UNIT-STORED-AT-MAP-END-62)
            if isinstance(result, str):
                failed.append(result)
                return
            path, raw, report = result
            results[path] = (raw, report)
            if cache is not None:
                cache.store_files(unit_inputs(todo[index]), {'report': report}, {'0': raw})
        with stage_pool(jobs, 'first-person parts'):
            failed.extend(unit_store.run_each('player-fp-parts', _safe_bake, list(enumerate(todo)), names, workers,
                                              keep, fallback=lambda name: 1.0, label='First-person parts',
                                              already=reused, log=log))
    log('=== PHASE 2/3: first-person parts: the table ===', flush=True)
    models = {}
    for t in tasks:
        path = fp_part_path(t[2])
        if path in results:
            models[(t[2]['slot'], t[2]['id'])] = path
    # FP-BARE-HAND-OTHER-SKIN-67: every race's and sex's bare hand tinted to its forearm where they differ by more than
    # SKIN_GAP as drawn (SKIN_GAP above), then measured again: over SKIN_GAP stops the stage, naming them
    def bake_cached(task):
        # a tinted hand is a unit of its own (its tint in the part's key): baked once, then reused
        if cache is not None:
            found = cache.load_unit(unit_inputs(task))
            if found is not None:
                return fp_part_path(task[2]), found[1]['0'], found[0]['report']
        path, raw, report = bake_part(task)
        if cache is not None:
            cache.store_files(unit_inputs(task), {'report': report}, {'0': raw})
        return path, raw, report
    import skeletal_actor as sa
    from player_own_skin import OWN_HAND_MESHES
    rig, table, bones, _, _ = _fp_rig(assets)
    posed_table = sa.read_table(table)
    # FP-HANDS-PER-RACE-67: the colours matched along each arm at its seams (SEAM_MATCH above), every race and sex
    if SEAM_MATCH == 'seams':
        tinted = match_seams(races, models, results, palette, posed_table, unique, bake_cached)
    elif SEAM_MATCH == 'forearm':
        tinted = match_hands(races, models, results, palette, unique, bake_cached)
    else:
        tinted = []
    for path in unique:
        if path in results:
            write_same(Path(id1) / path, results[path][0])
    gaps = hand_arm_gaps(races, models, results, palette)
    worst = max((g['gap'] for g in gaps if g['gap'] is not None), default=0)
    log('first-person parts: bare hand against forearm (whole means), %d races and sexes, worst gap %.1f' % (
        len(gaps), worst), flush=True)
    seams = seam_gaps(races, models, results, palette, posed_table)
    worst_seam = max((g['gap'] for g in seams if g['gap'] is not None), default=0)
    log('first-person parts: the arm\'s seams (%s), %d races and sexes, worst step %.1f (limit %d, aim %d)' % (
        SEAM_MATCH, len(races), worst_seam, SKIN_GAP, SEAM_TARGET), flush=True)
    check_own_hands(races, models, results, meshes=OWN_HAND_MESHES, textures=OWN_SKIN or OWN_HAND_MESHES)
    if SEAM_MATCH == 'seams':
        check_seams(seams)
    elif SEAM_MATCH == 'forearm':
        check_hand_gaps(gaps)
    write_same(Path(id1) / FP_TABLE, table)
    names = [b.casefold() for b in bones]
    item_bones = (names.index('weapon bone') if 'weapon bone' in names else -1,
                  names.index('shield bone') if 'shield bone' in names else -1)
    log('=== PHASE 3/3: first-person parts: the recipe ===', flush=True)
    recipe = recipe_text(races, items, models, item_bones)
    (Path(id1) / FP_RECIPE).parent.mkdir(parents=True, exist_ok=True)
    (Path(id1) / FP_RECIPE).write_text(recipe, encoding='ascii', newline='\n')
    sizes = [r[1]['bytes'] for r in results.values()]
    faces = [r[1]['faces'] for r in results.values()]
    report = {'models': len(results), 'reused': reused, 'made': len(results) - reused, 'failed': failed,
              'bytes': sum(sizes), 'faces_median': sorted(faces)[len(faces) // 2] if faces else 0,
              'vertices': sum(r[1]['vertices'] for r in results.values()),
              'source_topology': sum(r[1].get('topology') == 'source' for r in results.values()),
              'table': FP_TABLE, 'table_bytes': len(table), 'table_bones': len(bones),
              'recipe_sha256': hashlib.sha256(recipe.encode('ascii')).hexdigest(), 'items': len(items),
              'hand_arm_gaps': gaps, 'hand_arm_gap_limit': SKIN_GAP, 'hand_tints': tinted,
              'seam_match': SEAM_MATCH, 'seam_gaps': seams, 'seam_gap_limit': SKIN_GAP, 'seam_target': SEAM_TARGET,
              'own_hand_meshes': [{'race': race, 'sex': sex, 'record': body, 'record_mesh': named, 'mesh': own}
                                  for race, sex, body, named, own in own_meshes],
              'races': len(races), 'seconds': round(time.monotonic() - started, 1)}
    log('First-person parts: %d models (%d reused, %d made, %d failed), %.1f MB, %d items, table %d bytes, %.1f s' % (
        report['models'], reused, report['made'], len(failed), report['bytes'] / 1e6, len(items), len(table),
        report['seconds']), flush=True)
    return report


def image_step(data_files, id1, out, jobs=None):
    """The image step's phase (tools/build_aga.py, after the player view; not with --no-player-body): the arm parts
    on the palette the body's parts use (prepare_player_view.prepare_image), the report as OUT/player-fp-parts.json.
    The baked arms of the hand catalogue stay for aw_hand_parts 0, the carried torch and the shield guard."""
    import json
    import build_profile
    from mwad.paths import resolve_data_files
    print('Converting the first-person arm parts (gloves, gauntlets, bracers, sleeves)...', flush=True)
    with build_profile.phase('Image: first-person parts', detail='after the player view'):
        report = prepare(resolve_data_files(Path(data_files)), Path(id1),
                         (Path(id1) / 'gfx/palette.lmp').read_bytes(), jobs=jobs)
    (Path(out) / 'player-fp-parts.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8',
                                                     newline='\n')
    return report
