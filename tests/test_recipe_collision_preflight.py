# SPDX-License-Identifier: GPL-3.0-only
"""The recipe collision preflight's decision (RECIPE-ROW-MOVES-COLLISION-57): a reduction row is refused when the
collision surface gate fails with it and passes without it; cached results are reused by the row's key."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import recipe_collision_preflight as rcp  # noqa: E402


def row(depth, replaced):
    return {'depth': depth, 'replaced': replaced}


# measured on the v0.0.57-dev2 build's staged meshes, 30 October 2026 (the shape of the hull survey's rows)
TENT_03 = {'row': [row(64.0, False), row(64.0, False)], 'none': [row(64.0, True), row(64.0, True)]}
HUT = {'row': [row(0.0, False), row(0.0, False)], 'none': [row(0.0, False), row(0.0, False)]}
BOTH_FAIL = {'row': [row(20.0, False)], 'none': [row(20.0, False)]}
ERROR = {'row': [{'error': 'ValueError: x'}], 'none': [row(0.0, False)]}


class Decision(unittest.TestCase):
    def test_gate_rule(self):
        self.assertTrue(rcp.gate_fails([row(9.0, False)]))
        self.assertFalse(rcp.gate_fails([row(9.0, True)]))      # a replaced ramp is not measured
        self.assertFalse(rcp.gate_fails([row(8.5, False)]))     # a step is allowed
        self.assertIsNone(rcp.gate_fails([{'error': 'x'}]))

    def test_flip_is_refused(self):
        refused, unchecked = rcp.decide({'meshes/x/ex_ashl_tent_03.nif': TENT_03, 'meshes/x/hut.nif': HUT,
                                         'meshes/x/both.nif': BOTH_FAIL, 'meshes/x/err.nif': ERROR})
        self.assertEqual(refused, ['meshes/x/ex_ashl_tent_03.nif'])
        self.assertEqual(unchecked, ['meshes/x/err.nif'])

    def test_key_changes_with_the_row(self):
        a = rcp.row_key('meshes/x/a.nif', {'ratio': .1, 'error_share': .01, 'sha256': 'a' * 64}, 'm')
        b = rcp.row_key('meshes/x/a.nif', {'ratio': .1, 'error_share': .02, 'sha256': 'a' * 64}, 'm')
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, rcp.row_key('meshes/x/a.nif', {'ratio': .1, 'error_share': .01, 'sha256': 'a' * 64}, 'n'))


class Run(unittest.TestCase):
    def doc(self):
        return {'format': 1, 'everywhere': 'everywhere-v1', 'recipes': {'everywhere-v1': {'models': {
            'meshes/x/ex_ashl_tent_03.nif': {'sha256': 'b' * 64, 'ratio': .1, 'error_share': .005},
            'meshes/x/hut.nif': {'sha256': 'c' * 64, 'ratio': .1, 'error_share': .01}}}}}

    def test_cached_flip_refuses_in_seconds_and_names_the_mesh(self):
        with tempfile.TemporaryDirectory() as d, mock.patch('mesh_methods.meshopt_sha', return_value='m'):
            doc = self.doc()
            for source, result in (('meshes/x/ex_ashl_tent_03.nif', TENT_03), ('meshes/x/hut.nif', HUT)):
                key = rcp.row_key(source, doc['recipes']['everywhere-v1']['models'][source], 'm')
                (Path(d) / (key + '.json')).write_text(json.dumps(result))
            with self.assertRaises(ValueError) as caught:
                rcp.run(None, d, 2, recipes=doc, log=lambda line: None)
            self.assertIn('ex_ashl_tent_03', str(caught.exception))
            self.assertIn(rcp.BUG, str(caught.exception))

    def test_no_staged_mesh_is_reported_not_refused(self):
        with tempfile.TemporaryDirectory() as d, mock.patch('mesh_methods.meshopt_sha', return_value='m'):
            record = rcp.run(None, d, 2, recipes=self.doc(), log=lambda line: None)
        self.assertEqual(record['refused'], [])
        self.assertEqual(len(record['unchecked']), 2)


if __name__ == '__main__':
    unittest.main()
