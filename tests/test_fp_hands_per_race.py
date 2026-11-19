# SPDX-License-Identifier: GPL-3.0-only
"""Every race and sex draws its own first-person hand, with no steep colour step at the seams of the arm
(FP-HANDS-PER-RACE-67; tools/player_own_skin.py own_hand_mesh, tools/prepare_player_fp_parts.py match_seams,
check_seams, check_own_hands). Decided for the project on 18 November 2026, a deliberate departure from the original's
data: four of the game's first-person hand records name another race's or sex's mesh (the Nord man's names the Imperial
man's, the Imperial woman's the Nord woman's, the Dark Elf and Redguard men's the women's), and the game ships each
one's own mesh, used by no record. These checks fail on the old builder: it drew the mesh the record names, and its
colour check compared the hand with the forearm's whole mean while the hand meets the wrist part (the Nord man's step
at the wrist was 54.9 per channel on the v0.0.67-dev2 image, the Khajiit woman's 40.2 with c1a11300's tint, both
passed by that check)."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))

# the four records as Morrowind.esm has them (id, race, female, the mesh they name) and the race's own mesh
QUIRKS = (('b_n_nord_m_hands.1st', 'Nord', False, 'b\\B_N_Imperial_M_Hands.1st.nif', 'b\\b_n_nord_m_hands.1st.nif'),
          ('b_n_imperial_f_hands.1st', 'Imperial', True, 'b\\B_N_Nord_F_Hands.1st.nif',
           'b\\b_n_imperial_f_hands.1st.nif'),
          ('b_n_dark elf_m_hand.1st', 'Dark Elf', False, 'b\\B_N_Dark Elf_F_Hands.1st.NIF',
           'b\\b_n_dark elf_m_hands.1st.nif'),
          ('b_n_redguard_m_hands.1st', 'Redguard', False, 'b\\B_N_Redguard_F_Hands.1st.nif',
           'b\\b_n_redguard_m_hands.1st.nif'))
# the game's archive: every race's and sex's own first-person hand mesh (the Breton man's is "Hand", singular)
GAME_HANDS = ['meshes/b/b_n_%s_%s_hands.1st.nif' % (r, s) for r in (
    'argonian', 'breton', 'dark elf', 'high elf', 'imperial', 'khajiit', 'nord', 'orc', 'redguard', 'wood elf')
    for s in 'mf' if (r, s) != ('breton', 'm')] + ['meshes/b/b_n_breton_m_hand.1st.nif']


def body(race, female, part=5, mesh='x.nif'):
    """A BODY record as mwad.npc reads it: [(tag, bytes)]: BYDT part, vampire 0, flags (1 female), type 0 skin."""
    return [('NAME', b'x\0'), ('MODL', mesh.encode() + b'\0'), ('FNAM', race.encode() + b'\0'),
            ('BYDT', bytes((part, 0, 1 if female else 0, 0)))]


class Assets:
    """npc_geometry.Assets' read: KeyError for a file the game does not have."""
    def __init__(self, names):
        self.names = {n.casefold() for n in names}

    def read(self, name):
        if name.casefold().replace('\\', '/') not in self.names:
            raise KeyError(name)
        return b''


class OwnHandMeshes(unittest.TestCase):
    def test_the_four_records_take_the_races_own_mesh(self):
        import player_own_skin as ph
        assets = Assets(GAME_HANDS)
        self.assertTrue(ph.OWN_HAND_MESHES)
        for _, race, female, named, own in QUIRKS:
            self.assertEqual(ph.own_hand_mesh(named, race.casefold(), female, assets), own)
            self.assertEqual(ph.own_hand_mesh(named, race.casefold(), female, None), named)   # no assets: as named
            self.assertEqual(ph.own_hand_mesh(named, race.casefold(), female, Assets([])), named)  # no own mesh

    def test_a_hand_of_its_own_and_other_meshes_are_kept(self):
        import player_own_skin as ph
        assets = Assets(GAME_HANDS)
        for mesh, race, female in (('b\\B_N_Nord_F_Hands.1st.nif', 'nord', True),
                                   ('b\\B_N_Breton_M_Hand.1st.NIF', 'breton', False),
                                   ('b\\b_n_khajiit_m_hands.1st.nif', 'khajiit', False),
                                   ('c\\c_glove_common1.1st.NIF', 'nord', False),
                                   ('b\\B_N_Nord_M_Skins.nif', 'nord', False)):
            self.assertEqual(ph.own_hand_mesh(mesh, race, female, assets), mesh)

    def test_appearance_parts_draws_the_own_hand_and_keeps_the_record(self):
        import prepare_hands as ph
        bodies = {}
        for rid, race, female, named, _ in QUIRKS:
            bodies[rid] = body(race, female, mesh=named)
        bodies['b_n_nord_m_wrist'] = body('Nord', False, part=6, mesh='b\\B_N_Nord_M_Wrist.nif')
        kinds = {'RACE': {'nord': [], 'imperial': [], 'dark elf': [], 'redguard': []}, 'BODY': bodies}
        assets = Assets(GAME_HANDS)
        for rid, race, female, named, own in QUIRKS:
            parts = ph.appearance_parts(kinds, race, female, assets)
            hands = [p for p in parts if p['slot'] in (6, 7)]
            self.assertEqual([(p['id'], p['mesh'], p['record_mesh']) for p in hands], [(rid, own, named)] * 2)
            old = ph.appearance_parts(kinds, race, female)                       # without the game's files: as named
            self.assertEqual({p['mesh'] for p in old if p['slot'] in (6, 7)}, {named})
        nord = ph.appearance_parts(kinds, 'nord', False, assets)
        self.assertEqual([p['mesh'] for p in nord if p['slot'] in (8, 9)], ['b\\B_N_Nord_M_Wrist.nif'] * 2)
        self.assertFalse([p for p in nord if p['slot'] in (8, 9) and 'record_mesh' in p])

    def test_the_third_person_body_takes_the_own_parts_too(self):
        """The High Elf man's upper legs name the woman's mesh; the game ships his own (the same decision)."""
        import prepare_player_parts as ppp
        kinds = {'BODY': {'b_n_high elf_m_upper leg': body('High Elf', False, part=9,
                                                            mesh='b\\B_N_High Elf_F_Upper Leg.nif'),
                          'b_n_argonian_m_forearm': body('Argonian', False, part=7,
                                                         mesh='b\\B_N_Argonian_M_Forearm.nif'),
                          'c_glove_common1.1st': body('Argonian', False, mesh='c\\c_glove_common1.1st.NIF')}}
        kinds['BODY']['c_glove_common1.1st'][3] = ('BYDT', bytes((5, 0, 0, 1)))       # clothing, not skin
        assets = Assets(['meshes/b/b_n_high elf_m_upper leg.nif'])
        self.assertEqual(ppp.own_skin_mesh(kinds, 'b_n_high elf_m_upper leg', 'b\\B_N_High Elf_F_Upper Leg.nif', assets),
                         'b\\b_n_high elf_m_upper leg.nif')
        self.assertEqual(ppp.own_skin_mesh(kinds, 'b_n_argonian_m_forearm', 'b\\B_N_Argonian_M_Forearm.nif', assets),
                         'b\\B_N_Argonian_M_Forearm.nif')                    # its own (the woman's fallback keeps it)
        self.assertEqual(ppp.own_skin_mesh(kinds, 'c_glove_common1.1st', 'c\\c_glove_common1.1st.NIF', assets),
                         'c\\c_glove_common1.1st.NIF')
        self.assertEqual(ppp.foreign_skin_parts(kinds, [('b_n_high elf_m_upper leg', 'b\\B_N_High Elf_F_Upper Leg.nif'),
                                                        ('b_n_argonian_m_forearm', 'b\\B_N_Argonian_M_Forearm.nif')]),
                         [('b_n_high elf_m_upper leg', 'b\\B_N_High Elf_F_Upper Leg.nif')])
        self.assertEqual(ppp.foreign_skin_parts(kinds, [('b_n_high elf_m_upper leg', 'b\\b_n_high elf_m_upper leg.nif')]),
                         [])
        source = (ROOT / 'tools/prepare_player_parts.py').read_text(encoding='utf-8')
        self.assertIn('own = own_skin_mesh(kinds, body, mesh, assets)', source)
        self.assertIn('if OWN_HAND_MESHES and foreign:', source)

    def test_tribunals_own_hairs_are_neither_replaced_nor_called_foreign(self):
        """PLAYER-PARTS-HAIR-FALSE-STOP-67: the hands image build of fc987e35 stopped in player-view on two of Tribunal's
        Dark Elf hairs (the expansion layers selected), their own race and sex: the mesh names write the race without its
        space. Hairs stay as the game names them (player_own_skin.rule_covers) and a race is read with or without its
        space (race_key). These fail on fc987e35."""
        import player_own_skin as pos
        import prepare_player_parts as ppp
        rows = (('b_n_dark elf_f_barenziahh', 'Dark Elf', True, 1, 'b\\B_N_DarkElf_F_BarenziahH.NIF'),
                ('b_n_dark elf_m_helsethhair', 'Dark Elf', False, 1, 'b\\B_N_DarkElf_M_HelsethHair.NIF'),
                # a hair naming another race's art (the game's shared hair art): left as it is
                ('b_n_breton_m_hair_x', 'Breton', False, 1, 'b\\B_N_Nord_M_Hair_01.nif'),
                # a skin part (a forearm) whose mesh writes its own race without the space: its own
                ('b_n_dark elf_m_forearm_x', 'Dark Elf', False, 7, 'b\\B_N_DarkElf_M_Forearm.nif'))
        kinds = {'BODY': {rid: body(race, female, part=part, mesh=mesh) for rid, race, female, part, mesh in rows}}
        parts = [(rid, mesh) for rid, _, _, _, mesh in rows]
        self.assertEqual(ppp.foreign_skin_parts(kinds, parts), [])
        assets = Assets(['meshes/b/b_n_breton_m_hair_01.nif', 'meshes/b/b_n_dark elf_f_barenziahh.nif',
                         'meshes/b/b_n_dark elf_m_forearm.nif'])
        for rid, mesh in parts:
            self.assertEqual(ppp.own_skin_mesh(kinds, rid, mesh, assets), mesh, rid)
        self.assertEqual([pos.race_key(r) for r in ('Dark Elf', 'dark elf', 'DarkElf', 'darkelf')], ['darkelf'] * 4)
        self.assertFalse(pos.rule_covers(bytes((1, 0, 0, 0))))           # a hair
        self.assertTrue(pos.rule_covers(bytes((0, 0, 0, 0))))            # a head: a skin part
        self.assertFalse(pos.rule_covers(bytes((5, 0, 0, 1))))           # clothing
        self.assertFalse(pos.rule_covers(bytes((5, 1, 0, 0))))           # a vampire's
        # the first-person checks read the race the same way
        import prepare_player_fp_parts as fp
        races = [{'race': 'Dark Elf', 'female': False, 'skin': {6: 'h', 7: 'h'}}]
        own = {'mesh': 'b\\B_N_DarkElf_M_Hands.1st.nif', 'textures': ['TX_B_N_DarkElf_M_Hpalm.BMP']}
        fp.check_own_hands(races, {(6, 'h'): 'p6', (7, 'h'): 'p7'}, {'p6': (b'', own), 'p7': (b'', own)})
        self.assertIsNone(fp.own_skin_name('textures/tx_b_n_darkelf_m_hpalm.dds', 'Dark Elf', False))
        # a real other race is still caught
        self.assertEqual(ppp.foreign_skin_parts({'BODY': {'b_n_high elf_m_upper leg': body(
            'High Elf', False, part=12, mesh='b\\B_N_High Elf_F_Upper Leg.nif')}},
            [('b_n_high elf_m_upper leg', 'b\\B_N_High Elf_F_Upper Leg.nif')]),
            [('b_n_high elf_m_upper leg', 'b\\B_N_High Elf_F_Upper Leg.nif')])

    def test_every_first_person_path_passes_the_games_files(self):
        """The arms from parts, the baked hands, the torch arms and the guard's arms all take the own hand."""
        for path, needle in (('tools/prepare_player_fp_parts.py', 'races = race_skins(kinds, assets)'),
                             ('tools/prepare_player_fp_parts.py', 'parts = appearance_parts(kinds, race, female, assets)'),
                             ('tools/prepare_hands.py', 'parts=appearance_parts(kinds,race,female,assets)'),
                             ('tools/prepare_torch.py', 'appearance_parts(kinds,race,female,assets)'),
                             ('tools/prepare_block_view.py', 'appearance_parts(kinds, race, female, assets)')):
            self.assertIn(needle, (ROOT / path).read_text(encoding='utf-8'), path)


class OwnSkinOutsideTheNpcKeys(unittest.TestCase):
    """UNIT-KEY-WHOLE-FILE-63, seen again 2026-11-18: the resident bake (and the guard torches and the player view)
    import tools/prepare_hands.py for its stance tables, so that module's import-time code is part of their unit keys
    (pass_cache.source_digest of their bake functions). The own-mesh rule's switch and name patterns written there
    (f1a962c2) re-keyed all 2,323 stored residents, the 6 guard torch verdicts and the 100 player-view bodies, although
    no NPC runs the rule: the bake-reach digests went f8a636c6 -> 49e44fae, 82456386 -> 2d4c12b3 and 8f0e5928 ->
    6bedf786 by that one unit (measured in the container against a411ea0). The rule is tools/player_own_skin.py,
    imported only inside the first-person and player-body functions that use it; these fail on f1a962c2."""
    NPC_KEYS = (('prepare_area.py', 'build_resident'), ('prepare_area.py', 'publish_resident'),     # resident-bake
                ('prepare_guard_torches.py', '_convert_guard'),                                     # guard-torch-skip
                ('prepare_player_view.py', 'bake_unit'), ('player_inventory_pose.py', 'bake_body'))  # player-view
    RULE = ('OWN_HAND_MESHES', 'HAND_MESH_NAME', 'SKIN_MESH_NAME', 'own_hand_mesh', 'player_own_skin')

    @classmethod
    def setUpClass(cls):
        import build_cache
        import pass_cache
        # the index the unit keys are computed with (pass_cache._source_digest)
        cls.index = build_cache.SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        cls.top = build_cache.TOP_TEXT[pass_cache.PASS_KEY_FORM]

    def test_the_npc_bakes_do_not_reach_the_own_skin_rule(self):
        for module, function in self.NPC_KEYS:
            python, data, uncertain, units = self.index.entry_units(ROOT / 'tools' / module, function)
            self.assertFalse(uncertain, function)
            self.assertNotIn('tools/player_own_skin.py', set(python) | set(data), function)
            reached = set(units.get('tools/prepare_hands.py', ()))
            self.assertEqual(reached & {'appearance_parts', 'nord_parts', 'bake_appearance', 'own_hand_mesh'}, set(),
                             function)

    def test_prepare_hands_import_time_code_holds_no_part_of_the_rule(self):
        text = self.index._module_symbols('tools/prepare_hands.py')['texts'][self.top]
        for name in self.RULE:
            self.assertNotIn(name, text)
        self.assertIn('from player_own_skin import own_hand_mesh', inspect_source('prepare_hands', 'appearance_parts'))

    def test_the_first_person_and_body_paths_reach_the_rule(self):
        for module, function in (('prepare_hands.py', 'appearance_parts'), ('prepare_player_parts.py', 'own_skin_mesh'),
                                 ('prepare_player_parts.py', 'foreign_skin_parts'),
                                 ('prepare_player_fp_parts.py', 'check_own_hands')):
            python, _, uncertain, units = self.index.entry_units(ROOT / 'tools' / module, function)
            self.assertFalse(uncertain, function)
            self.assertIn('tools/player_own_skin.py', python, function)
        _, _, _, units = self.index.entry_units(ROOT / 'tools/prepare_hands.py', 'appearance_parts')
        self.assertIn('own_hand_mesh', units['tools/player_own_skin.py'])


def inspect_source(module, function):
    import importlib
    import inspect
    return inspect.getsource(getattr(importlib.import_module(module), function))


class Seams(unittest.TestCase):
    PALETTE = bytes(np.arange(256, dtype=np.uint8).repeat(3))          # grey ramp: index i is (i, i, i)

    def strip(self, colours, x0):
        """A parsed model of len(colours) quads in a row along x from X0 (one unit each), quad k textured COLOURS[k]
        (palette index) on its own texel column; its drawn vertex positions."""
        n = len(colours)
        w, h = 4 * n, 4
        texels = np.zeros((h, w), np.uint8)
        st, tris, pts = [], [], []
        for k, c in enumerate(colours):
            texels[:, 4 * k:4 * k + 4] = c
            base = len(st)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                st.append((0, 4 * k + 1 + 2 * dx, 1 + 2 * dy))
                pts.append((x0 + k + dx, dy, 0.0))
            tris += [(1, base, base + 1, base + 2), (1, base + 1, base + 3, base + 2)]
        return {'w': w, 'h': h, 'texels': texels, 'st': np.array(st), 'tris': np.array(tris)}, np.array(pts, float)

    def test_the_seam_colour_is_where_the_parts_meet_not_the_whole_mean(self):
        import prepare_player_fp_parts as fp
        # a hand: 3 quads at 100 and the quad at its wrist end at 60; the wrist part beyond it at 160
        hand, hp = self.strip((100, 100, 100, 60), 0.0)
        wrist, wp = self.strip((160,), 4.0)
        a, b = fp.seam_pair_means(hand, hp, wrist, wp, self.PALETTE)
        self.assertEqual(a.tolist(), [60.0] * 3)                 # the hand at the seam, not its whole mean (90)
        self.assertEqual(b.tolist(), [160.0] * 3)
        whole = fp.covered_mean(hand, np.arange(len(hand['tris'])), self.PALETTE)
        self.assertEqual(whole.tolist(), [90.0] * 3)
        self.assertEqual(fp.skin_gap(a, b), 100.0)

    def fake(self, colours):
        """A fake bake and seam measure: a part's colour at its seam with another (COLOURS[(part, other)], the measured
        colours of the c1a11300 bake and the v0.0.67-dev2 image) times the tint it was baked with."""
        drawn = {}

        def bake(task):
            part = task[2]
            raw = repr((part['id'], part.get('slot'), part.get('skin_tint'))).encode()
            drawn[raw] = (part['id'], np.asarray(part.get('skin_tint', (1, 1, 1)), float))
            return part['id'], raw, {'id': part['id']}

        def means(raw_a, raw_b, table, palette):
            (a, ta), (b, tb) = drawn[raw_a], drawn[raw_b]
            return np.asarray(colours[(a, b)], float) * ta, np.asarray(colours[(b, a)], float) * tb
        return bake, means

    def test_the_old_check_passes_what_the_seam_check_stops_and_the_match_fixes_it(self):
        import prepare_player_fp_parts as fp
        self.assertEqual((fp.SEAM_MATCH, fp.SKIN_GAP, fp.SEAM_TARGET), ('seams', 16, 8))
        # at the seams: the Khajiit woman with c1a11300's tint (hand 83 60 38 at the wrist 123 92 65; her wrist 113 82 55
        # at the forearm 101 70 44); the Nord man on v0.0.67-dev2 (hand 139 109 74 at the wrist 194 154 125)
        colours = {('kf_hand', 'kf_wrist'): (83, 60, 38), ('kf_wrist', 'kf_hand'): (123, 92, 65),
                   ('kf_wrist', 'kf_arm'): (113, 82, 55), ('kf_arm', 'kf_wrist'): (101, 70, 44),
                   ('nm_hand', 'nm_wrist'): (139, 109, 74), ('nm_wrist', 'nm_hand'): (194, 154, 125),
                   ('nm_wrist', 'nm_arm'): (197, 155, 126), ('nm_arm', 'nm_wrist'): (196, 154, 125)}
        bake, means = self.fake(colours)
        races, models, tasks, results = [], {}, {}, {}
        for who, race, female in (('kf', 'khajiit', True), ('nm', 'nord', False)):
            skin = {}
            for slot, kind in ((6, 'hand'), (7, 'hand'), (8, 'wrist'), (9, 'wrist'), (11, 'arm'), (12, 'arm')):
                pid = '%s_%s' % (who, kind)
                skin[slot] = pid
                path = '%s%d' % (pid, slot)
                models[(slot, pid)] = path
                tasks[path] = (None, None, {'id': pid, 'slot': slot}, 0)
                results[path] = bake(tasks[path])[1:]
            races.append({'race': race, 'female': female, 'skin': skin})
        before = fp.seam_gaps(races, models, results, self.PALETTE, None, means=means)
        steps = {(g['race'], g['side'], g['seam']): g['gap'] for g in before}
        self.assertEqual(steps[('khajiit', 'right', 'hand to wrist')], 40.0)
        self.assertEqual(steps[('nord', 'left', 'hand to wrist')], 55.0)
        with self.assertRaisesRegex(ValueError, 'khajiit f right hand to wrist: 40.0'):
            fp.check_seams(before)
        tinted = fp.match_seams(races, models, results, self.PALETTE, None, tasks, bake, means=means)
        after = fp.seam_gaps(races, models, results, self.PALETTE, None, means=means)
        fp.check_seams(after)
        self.assertTrue(all(g['gap'] <= fp.SEAM_TARGET for g in after), after)
        # the wrist is matched to the forearm before the hand to the wrist (the chain along the arm)
        order = [(t['race'], t['side'], t['seam']) for t in tinted if t['race'] == 'khajiit']
        self.assertEqual(order[:2], [('khajiit', 'right', 'wrist to forearm'), ('khajiit', 'right', 'hand to wrist')])

    def test_a_foreign_hand_mesh_or_texture_stops_the_stage(self):
        import prepare_player_fp_parts as fp
        races = [{'race': 'nord', 'female': False, 'skin': {6: 'h', 7: 'h'}}]
        models = {(6, 'h'): 'p6', (7, 'h'): 'p7'}
        foreign = {'mesh': 'b\\B_N_Imperial_M_Hands.1st.nif', 'textures': ['TX_B_N_Imperial_M_Hpalm.BMP'],
                   'skin_textures': {}}
        with self.assertRaisesRegex(ValueError, 'nord m slot 6: mesh'):
            fp.check_own_hands(races, models, {'p6': (b'', foreign), 'p7': (b'', foreign)})
        swapped = dict(foreign, mesh='b\\b_n_nord_m_hands.1st.nif',
                       skin_textures={'TX_B_N_Imperial_M_Hpalm.BMP': 'textures/tx_b_n_nord_m_hpalm.bmp'})
        fp.check_own_hands(races, models, {'p6': (b'', swapped), 'p7': (b'', swapped)})
        with self.assertRaisesRegex(ValueError, 'nord m slot 7: texture'):
            fp.check_own_hands(races, models, {'p6': (b'', swapped), 'p7': (b'', dict(swapped, skin_textures={}))})
        own = {'mesh': 'b\\b_n_nord_m_hands.1st.nif', 'textures': ['TX_B_N_Nord_M_Hpalm.BMP']}
        fp.check_own_hands(races, models, {'p6': (b'', own), 'p7': (b'', own)})

    def test_the_stage_runs_the_seam_match_and_both_checks(self):
        source = (ROOT / 'tools/prepare_player_fp_parts.py').read_text(encoding='utf-8')
        for needle in ("SEAM_MATCH = 'seams'",
                       'tinted = match_seams(races, models, results, palette, posed_table, unique, bake_cached)',
                       'check_own_hands(races, models, results, meshes=OWN_HAND_MESHES',
                       'check_seams(seams)',
                       "'textures': sorted(str(t) for t in textures),"):
            self.assertIn(needle, source)


class PartsReleasedAndRaceSwap(unittest.TestCase):
    """FP-ARMS-NO-MODEL-SLOT-67: after six race and sex changes in one place the first-person arm parts found no model
    slot (the old sets were only unpinned, never released), the arms fell back to the legacy hand model and the held
    light was not drawn for the rest of the session. DBG-RACE-SWAP-67: dbg race [N|NAME] [m|f]. Source contracts: each
    fails on the old engine (no release, a sticky refusal, no command)."""
    VIEW = (ROOT / 'engine/aga/src/aw_view.c').read_text(encoding='utf-8')
    QUICK = (ROOT / 'engine/aga/src/aw_quickchar.c').read_text(encoding='utf-8')

    def body(self, name):
        start = self.VIEW.index(name)
        return self.VIEW[start:self.VIEW.index('\n}\n', start)]

    def test_a_part_that_leaves_its_set_is_released(self):
        drop = self.body('static void part_drop(model_t *m) {')
        self.assertIn('Mod_ReleaseAlias(m)', drop)
        for guard in ('parts_in_use(m)', 'hparts_in_use(m)', 'pend_in_use(m)', 'strncmp(m->name,"progs/parts/",12)'):
            self.assertIn(guard, drop)                         # never a model a set still draws, never another model
        body = self.body('static int parts_ready(const char *race,int female) {')
        self.assertIn('for(k=0;k<g;k++)part_drop(gone[k]);', body)           # the body's old set, after the new is in
        arms = self.body('static int hand_parts_ready(const char *race,int female) {')
        self.assertEqual(arms.count('hparts_drop_old();'), 3)                 # the arms' old set on every way out
        self.assertIn('memcpy(hold_models,hpart_models,sizeof(hold_models));', arms)

    def test_a_refused_slot_holds_off_only_that_outfit(self):
        arms = self.body('static int hand_parts_ready(const char *race,int female) {')
        self.assertIn('if(noslot==next.count)strcpy(hparts_noslot_sig,sig);else hparts_failed=1;', arms)
        self.assertIn('if(hparts_noslot_sig[0] && !strcmp(sig,hparts_noslot_sig))return 0;', arms)
        self.assertIn('hparts_noslot_sig[0]=0;', self.body('void AW_ViewPartsUnload(void) {'))

    def test_the_released_state_is_model_cs(self):
        """aw_view.c mirrors model.c's private NL_UNREFERENCED (model.c and model.h stay as they are)."""
        model = (ROOT / 'engine/aga/src/model.c').read_text(encoding='utf-8', errors='replace')
        self.assertRegex(model, r'#define\s+NL_UNREFERENCED\s+2\b')
        self.assertIn('#define VIEW_NL_UNREFERENCED 2', self.VIEW)
        self.assertNotIn('NL_UNREFERENCED)', self.VIEW.replace('VIEW_NL_UNREFERENCED', ''))

    def test_the_model_table_is_read_back_by_number(self):
        self.assertIn('Model table: %d slots in use of %d known, %d of them player parts', self.VIEW)
        self.assertIn('Player parts released: model table %d slots in use', self.body('void AW_ViewPartsUnload(void) {'))

    def test_dbg_race_swaps_race_and_sex_with_the_games_rules(self):
        self.assertIn('Cmd_AddCommand("aw_race",swap_command);', self.QUICK)
        swap = self.QUICK[self.QUICK.index('static void swap_command(void){'):]
        swap = swap[:swap.index('\n}\n')]
        for needle in ('race_name_equal(value,aw_races[i].id)', '"m"', '"f"', 'AW_CharacterSet(&trial,"race"',
                       'AW_CharacterSet(&trial,"sex"', 'if(aw_race_swapped)dropped=aw_race_swapped(&beast);',
                       'aw_character.female=trial.female'):
            self.assertIn(needle, swap)
        self.assertNotIn('aw_character=trial', swap)                       # the stats are kept, not rebuilt
        swapped = self.body('static int race_swapped(int *beast) {')
        for needle in ('AW_ViewRaceBeast(', 'AW_InventoryBeastRefusal(&it,1)', 'AW_InventoryUnequip(&aw_state,it.id)',
                       'AW_ViewPartsUnload();'):
            self.assertIn(needle, swapped)
        self.assertIn('aw_race_swapped=race_swapped;', self.VIEW)
        rows = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8').splitlines()
        self.assertTrue(any(r.startswith('PLAYTESTING|race|aw_race|[N / NAME] [m / f]') for r in rows))


if __name__ == '__main__':
    unittest.main()
