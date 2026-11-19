# SPDX-License-Identifier: GPL-3.0-only
"""The bare hand in first person has the skin of its arm (FP-TORCH-HAND-REGRESSION-67, register
FP-BARE-HAND-OTHER-SKIN-67; tools/prepare_player_fp_parts.py own_skin). The game's first-person hand records of some races
are another race's or sex's mesh with that one's skin textures (the Nord man's .1st hands are the Imperial man's: their
textures about 146 97 76 against the Nord arm's 197 148 125, a hand that looks gloved); the race's own hand textures of
the same part are used instead, and each such hand is its own model. These checks fail on the old bake, which drew the
mesh's textures as they are and gave the Nord and the Imperial man one hand model."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def body(race, female, kind=0, mesh='b\\B_N_Imperial_M_Hands.1st.nif'):
    """A BODY record as mwad.npc reads it: [(tag, bytes)]: BYDT part 5 (hand), vampire 0, flags, type."""
    return [('NAME', b'x\0'), ('MODL', mesh.encode() + b'\0'), ('FNAM', race.encode() + b'\0'),
            ('BYDT', bytes((5, 0, 1 if female else 0, kind)))]


class FakeAssets:
    def __init__(self, names):
        self.names = {n.casefold() for n in names}

    def texture(self, name):
        if name.casefold() not in self.names:
            raise ValueError('Missing texture ' + name)
        return np.full((2, 2, 4), 200, np.uint8)


class BareHandSkin(unittest.TestCase):
    def test_another_races_hand_texture_takes_the_races_own(self):
        import prepare_player_fp_parts as fp
        self.assertEqual(fp.own_skin_name('tx_b_n_imperial_m_hfinger.bmp', 'Nord', False),
                         'textures/tx_b_n_nord_m_hfinger.bmp')
        self.assertEqual(fp.own_skin_name('TX_B_N_Nord_F_Hpalm.BMP', 'Imperial', True),
                         'textures/tx_b_n_imperial_f_hpalm.bmp')
        self.assertEqual(fp.own_skin_name('textures/tx_b_n_dark elf_f_hthumb.bmp', 'Dark Elf', False),
                         'textures/tx_b_n_dark elf_m_hthumb.bmp')                     # the other sex's
        self.assertIsNone(fp.own_skin_name('tx_b_n_nord_m_hfinger.bmp', 'Nord', False))   # its own already
        self.assertIsNone(fp.own_skin_name('tx_b_n_imperial_m_la.bmp', 'Nord', False))     # no hand texture
        self.assertIsNone(fp.own_skin_name('tx_glove_leather.bmp', 'Nord', False))

    def test_the_bare_hand_is_swapped_a_glove_and_an_arm_are_not(self):
        import prepare_player_fp_parts as fp
        kinds = {'BODY': {'b_n_nord_m_hands.1st': body('Nord', False),
                          'c_glove_leather.1st': body('', False, kind=1),
                          'b_n_nord_m_forearm': body('Nord', False)}}
        assets = FakeAssets(['textures/tx_b_n_nord_m_hfinger.bmp', 'textures/tx_b_n_nord_m_hpalm.bmp'])
        textures = {'tx_b_n_imperial_m_hfinger.bmp': 'imperial', 'tx_b_n_imperial_m_hpalm.bmp': 'imperial',
                    'tx_b_n_imperial_m_hthumb.bmp': 'imperial'}
        swaps = fp.own_skin(textures, kinds, {'slot': 6, 'id': 'b_n_nord_m_hands.1st'}, assets)
        self.assertEqual(swaps, {'tx_b_n_imperial_m_hfinger.bmp': 'textures/tx_b_n_nord_m_hfinger.bmp',
                                 'tx_b_n_imperial_m_hpalm.bmp': 'textures/tx_b_n_nord_m_hpalm.bmp'})
        self.assertEqual(textures['tx_b_n_imperial_m_hthumb.bmp'], 'imperial')        # no own one: kept
        self.assertIsInstance(textures['tx_b_n_imperial_m_hfinger.bmp'], np.ndarray)    # the Nord's own image
        for slot, part in ((6, 'c_glove_leather.1st'), (11, 'b_n_nord_m_forearm')):
            kept = {'tx_b_n_imperial_m_hfinger.bmp': 'imperial'}
            self.assertEqual(fp.own_skin(kept, kinds, {'slot': slot, 'id': part}, assets), {})
            self.assertEqual(kept, {'tx_b_n_imperial_m_hfinger.bmp': 'imperial'})

    def test_every_hand_is_brought_to_its_arm_and_a_gap_stops_the_stage(self):
        """The maintainer: every race and sex consistent. A hand drawn more than SKIN_GAP from its forearm is baked again
        tinted by the measured factor until it is within it; a gap left over SKIN_GAP stops the stage."""
        import prepare_player_fp_parts as fp
        self.assertEqual(fp.SKIN_GAP, 16)
        image = np.zeros((2, 2, 4), np.uint8)
        image[..., :3], image[..., 3] = 100, 255
        textures = {'a': image}
        fp.tint_textures(textures, (1.5, 1.0, 0.5))
        self.assertEqual(textures['a'][0, 0].tolist(), [150, 100, 50, 255])
        self.assertEqual(fp.skin_gap((10, 20, 30), (12, 20, 10)), 20.0)
        # a fake bake: the drawn hand's mean is its base colour times the tint it was baked with
        base = {'hand_kh': np.array([90.0, 60.0, 30.0]), 'hand_ok': np.array([150.0, 120.0, 90.0]),
                'arm': np.array([180.0, 113.0, 71.0])}
        drawn = {}

        def bake(task):
            part = task[2]
            colour = base[part['id']] * np.asarray(part.get('skin_tint', (1, 1, 1)))
            raw = repr((part['id'], part.get('slot'), part.get('skin_tint'))).encode()
            drawn[raw] = colour
            return part['id'], raw, {'id': part['id']}
        races = [{'race': 'khajiit', 'female': False, 'skin': {6: 'hand_kh', 7: 'hand_kh', 11: 'arm', 12: 'arm'}},
                 {'race': 'breton', 'female': False, 'skin': {6: 'hand_ok', 7: 'hand_ok', 11: 'arm', 12: 'arm'}}]
        models = {(6, 'hand_kh'): 'kh6', (7, 'hand_kh'): 'kh7', (11, 'arm'): 'arm', (12, 'arm'): 'arm',
                  (6, 'hand_ok'): 'ok6', (7, 'hand_ok'): 'ok7'}
        tasks = {'kh6': (None, None, {'id': 'hand_kh', 'slot': 6}, 0), 'kh7': (None, None, {'id': 'hand_kh', 'slot': 7}, 0),
                 'ok6': (None, None, {'id': 'hand_ok', 'slot': 6}, 0), 'ok7': (None, None, {'id': 'hand_ok', 'slot': 7}, 0)}
        results = {p: bake(t)[1:] for p, t in tasks.items()}
        results['arm'] = bake((None, None, {'id': 'arm'}, 0))[1:]
        real = fp.drawn_skin_mean
        fp.drawn_skin_mean = lambda raw, palette: drawn[raw]
        try:
            with self.assertRaisesRegex(ValueError, 'khajiit m slot 6'):
                fp.check_hand_gaps(fp.hand_arm_gaps(races, models, results, None))     # the old bake: 90 off
            tinted = fp.match_hands(races, models, results, None, tasks, bake)
            gaps = fp.hand_arm_gaps(races, models, results, None)
            fp.check_hand_gaps(gaps)
        finally:
            fp.drawn_skin_mean = real
        self.assertEqual(sorted(t['slot'] for t in tinted if t['race'] == 'khajiit'), [6, 7])
        self.assertTrue(all(t['gap_after'] <= fp.SKIN_GAP for t in tinted))
        # a hand already within SKIN_GAP of its arm (the Breton's 30) is not tinted
        self.assertFalse([t for t in tinted if t['race'] == 'breton' and t['gap_before'] <= fp.SKIN_GAP])
        self.assertTrue(all(g['gap'] <= fp.SKIN_GAP for g in gaps))

    def test_two_races_on_one_hand_mesh_are_two_models(self):
        import prepare_player_fp_parts as fp
        from prepare_player_parts import part_dict
        mesh = 'b\\B_N_Imperial_M_Hands.1st.nif'
        kinds = {'BODY': {'b_n_nord_m_hands.1st': body('Nord', False), 'b_n_imperial_m_hands.1st': body('Imperial', False)}}
        paths = []
        for record in ('b_n_nord_m_hands.1st', 'b_n_imperial_m_hands.1st'):
            part = part_dict(6, record, mesh)
            part['skin'] = fp.skin_tag(kinds, 6, record)
            paths.append(fp.fp_part_path(part))
        self.assertEqual([fp.skin_tag(kinds, 6, r) for r in kinds['BODY']], ['nord_m', 'imperial_m'])
        self.assertNotEqual(paths[0], paths[1])
        self.assertIsNone(fp.skin_tag(kinds, 11, 'b_n_nord_m_hands.1st'))                 # not a hand slot
        self.assertTrue(all(p.startswith('progs/parts/') and p.endswith('.mdl') for p in paths))
        source = (ROOT / 'tools/prepare_player_fp_parts.py').read_text(encoding='utf-8')
        self.assertIn('skin_swaps = own_skin(textures, kinds, part, assets)', source)
        self.assertIn('out = fp_part_path(part)', source)


if __name__ == '__main__':
    unittest.main()
