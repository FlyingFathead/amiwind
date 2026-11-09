# SPDX-License-Identifier: GPL-3.0-only
"""ROBE-PART-NOT-BAKED-62: a player part whose mesh overflows the alias vertex budget at its slot cap is baked again at
smaller caps instead of being dropped (the Tarhiel robe's chest, c_m_robe_extrav_1t, was missing from the third-person
body and the inventory picture). The retry loop is driven here with a stand-in baker."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class PartCapFallbackTests(unittest.TestCase):
    def run_bake(self, fits_at, free_fits_at=None, grows=True):
        import prepare_player_parts as pp
        import npc_geometry
        calls = []

        def skeletal(*args, budgets, quotas, **kw):
            free = kw.get('preserve') is not None
            calls.append(-budgets[0] if free else budgets[0])
            limit = free_fits_at if free else fits_at
            if limit is None or budgets[0] > limit:
                raise npc_geometry.AliasOverflow('Alias vertex budget exceeded', 1)
            return b'mdl', {'faces': budgets[0], 'vertices': 1}
        rig = types.SimpleNamespace(idle_times=lambda n: ([0.0], None), pose=lambda t: None)
        fake_sa = types.SimpleNamespace(game_table=lambda *a: (None, {'bone_names': []}, None, 'p', None, None),
                                        export_actor=lambda *a: None, skeletal_from_shapes=skeletal)
        fake_ppv = types.SimpleNamespace(_sources=lambda d: (None, None, None))
        with patch.dict(sys.modules, {'skeletal_actor': fake_sa, 'prepare_player_view': fake_ppv}), \
                patch.object(pp, '_skeleton_of', lambda assets: (lambda name: rig)), \
                patch.object(pp, 'open_edges_grew', lambda shapes, cap: grows), \
                patch.object(npc_geometry, 'assemble', lambda *a: ([{'faces': [0] * 100}], [], [])):
            part = {'id': 'c_m_robe_extrav_1t', 'slot': 3, 'mesh': 'c\\C_M_Robe_Extrav_1t.NIF'}
            try:
                out = pp.bake_part(('/data', bytes(768), 'meshes/base_anim.nif', part, 72))
            except ValueError as error:
                return calls, error
        return calls, out

    def test_a_smaller_cap_is_kept(self):
        calls, (path, raw, report) = self.run_bake(fits_at=40)
        self.assertEqual(calls, [72, 54, 36])
        self.assertEqual((report['cap'], report['cap_used']), (72, 36))
        self.assertEqual(raw, b'mdl')

    def test_it_fits_at_once(self):
        calls, (_, _, report) = self.run_bake(fits_at=100)
        self.assertEqual(calls, [72])
        self.assertEqual(report['cap_used'], 72)

    def test_no_cap_fits_names_the_part(self):
        calls, error = self.run_bake(fits_at=0)          # and every panel-free try would open edges: not tried
        self.assertEqual(calls, [72, 54, 36, 24, 18, 12, 9])
        self.assertIn('c_m_robe_extrav_1t', str(error))

    def test_without_whole_panels_when_no_edge_opens(self):
        # measured: the beast skeleton's Tarhiel robe chest (152 faces this way; no part before)
        calls, (_, _, report) = self.run_bake(fits_at=0, free_fits_at=72, grows=False)
        self.assertEqual(calls, [72, 54, 36, 24, 18, 12, 9, -72])
        self.assertEqual(report['cap_used'], -72)


class PartCoverageTests(unittest.TestCase):
    def test_counts_per_skeleton_and_missing(self):
        import prepare_player_parts as pp
        h, k = 'meshes/base_anim.nif', 'meshes/base_animkna.nif'
        items = [{'id': 'robe_t', 'rank': 24, 'slots': {3: ['c_robe_t', None], 4: [None, None]}},
                 {'id': 'boots', 'rank': 3, 'slots': {15: ['a_boot', None], 16: ['a_boot', None]}},
                 {'id': 'shirt', 'rank': 2, 'slots': {3: ['c_shirt', 'c_shirt_f']}}]
        models = {(h, 3, 'c_robe_t'): 'x', (h, 15, 'a_boot'): 'x', (h, 16, 'a_boot'): 'x', (h, 3, 'c_shirt'): 'x',
                  (h, 3, 'c_shirt_f'): 'x', (k, 3, 'c_shirt'): 'x', (k, 3, 'c_shirt_f'): 'x'}
        cov = pp.part_coverage(items, models, {h, k})
        self.assertEqual((cov['items'], cov['robes'], cov['multi_part_items']), (3, 1, 2))
        self.assertEqual(cov['skeletons']['h'], {'parts': 5, 'built': 5, 'missing': 0})
        # the beast skeleton: boots are never drawn (no feet parts counted); the robe's chest is missing
        self.assertEqual(cov['skeletons']['k'], {'parts': 3, 'built': 2, 'missing': 1})
        self.assertEqual(cov['missing'], [{'item': 'robe_t', 'skeleton': k, 'slot': 3, 'body': 'c_robe_t'}])

    def test_known_missing_rows_carry_their_register_entry(self):
        import prepare_player_parts as pp
        known = pp.known_missing()
        self.assertIn(('meshes/base_anim.nif', 'a_tenpaceboot'), known)
        self.assertNotIn(('meshes/base_animkna.nif', 'c_m_robe_extrav_1t'), known)   # built since the panel fallback

    def test_open_edges_counted(self):
        import prepare_player_parts as pp
        self.assertEqual(pp.open_edges([[0, 1, 2]]), 3)
        self.assertEqual(pp.open_edges([[0, 1, 2], [2, 1, 3]]), 4)
        self.assertEqual(pp.open_edges([[0, 1, 2], [0, 2, 3], [0, 3, 1], [1, 3, 2]]), 0)   # a closed tetrahedron


if __name__ == '__main__':
    unittest.main()
