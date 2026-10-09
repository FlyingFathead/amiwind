"""Seam-tear audit and gate (MESH-LOD-OPEN-SEAMS-33); synthetic, plus an optional owner-data check."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEPS = all(importlib.util.find_spec(n) for n in ('numpy', 'scipy', 'fast_simplification'))


@unittest.skipUnless(DEPS, 'optional geometry dependencies')
class SeamMeasureTests(unittest.TestCase):
    def test_default_reducer_tears_the_shared_seam_and_locked_does_not(self):
        from seam_audit import measure
        from static_lod import reduce_mesh
        from test_static_lod import _two_plates
        v, f = _two_plates()
        unreduced = measure(v, f, v, f)
        self.assertEqual(unreduced['seam']['edges'], 9)
        self.assertEqual(unreduced['seam']['torn_share'], 0)
        torn = measure(v, f, *reduce_mesh(v, f, .3)[:2])
        self.assertGreater(torn['seam']['torn_share'], .02)
        closed = measure(v, f, *reduce_mesh(v, f, .3, lock_boundaries=True)[:2])
        self.assertEqual(closed['seam']['torn_share'], 0)
        self.assertEqual(closed['rim']['torn_share'], 0)


class SeamGateTests(unittest.TestCase):
    def report(self, share, space='world', model='meshes/x/a.nif'):
        return {'ranked': [{'model': model, 'space': space, 'placements': 3, 'seam_torn_share': share,
                            'seam_torn_length': 1., 'rim_torn_share': 0., 'ratio': .5,
                            'source_triangles': 10, 'reduced_triangles': 5}]}

    def test_gate_fails_new_torn_mesh_and_passes_known_or_small(self):
        from seam_audit import check
        self.assertEqual(check(self.report(.01)), [])
        self.assertEqual(check(self.report(.10))[0]['reason'], 'new torn mesh')
        known = {'meshes/x/a.nif': {'world': {'seam_torn_share': .10, 'bug': 'X-33'}}}
        self.assertEqual(check(self.report(.10), known), [])
        self.assertIn('more than recorded', check(self.report(.2), known)[0]['reason'])
        self.assertEqual(check(self.report(.10, space='town'), known)[0]['reason'], 'new torn mesh')

    def test_closed_mesh_fails_on_any_tear(self):
        from seam_audit import check
        closed = [{'model': 'meshes/x/a.nif', 'bug': 'X-33'}]
        report = self.report(.001)
        self.assertIn('must stay closed', check(report, {}, closed=closed)[0]['reason'])
        report['ranked'][0]['seam_torn_share'] = 0
        self.assertEqual(check(report, {}, closed=closed), [])
        report['ranked'][0]['rim_torn_share'] = .01
        self.assertEqual(len(check(report, {}, closed=closed)), 1)

    def test_strider_must_stay_closed(self):
        from seam_audit import load_known
        _, closed = load_known()
        self.assertIn('meshes/r/siltstrider.nif', {row['model'] for row in closed})

    def test_audit_measures_the_profile_each_town_converter_builds(self):
        # The town builders (legacy and CHIM) read town_model_profile; the audit must measure exactly that
        # profile, besides the group profile alone (Seyda Neen's scenery path).
        from unittest import mock
        import seam_audit
        group = {'g': {'visual_profiles': {'meshes/f/flora_x.nif': {'ratio': .9, 'texture_size': 64}}}}
        with mock.patch('scenery_selection.load_groups', return_value=group),                 mock.patch('prepare_world_scenery.visual_profiles', return_value={'meshes/f/flora_x.nif': {}}),                 mock.patch('world_estimate_data.interior_profile', return_value=None):
            out = seam_audit.converter_profiles('meshes/f/flora_x.nif', 1000)
        from town_regions import town_model_profile
        self.assertEqual(out['group']['ratio'], .9)
        self.assertEqual(out['town'], town_model_profile({'ratio': .9, 'texture_size': 64}, 'meshes/f/flora_x.nif', 1000))
        self.assertEqual(out['town']['ratio'], .12)   # visual_profile's flora target wins in the town builders
        for name in ('import_town.py', 'chim/build.py', 'world_estimate_sample.py'):
            source = (Path(__file__).resolve().parents[1] / 'tools' / name).read_text(encoding='utf-8')
            self.assertIn('town_model_profile(', source, name)
            self.assertNotIn('**visual_profile(', source, name)

    def test_known_list_names_a_registered_bug_for_every_row(self):
        import json
        from seam_audit import KNOWN
        if not KNOWN.is_file():
            self.skipTest('no known torn meshes recorded')
        data = json.loads(KNOWN.read_text(encoding='utf-8'))
        bugs = {b['id'] for b in json.loads((KNOWN.parents[1] / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for row in data['known']:
            self.assertIn(row['bug'], bugs, row['model'])
            self.assertIn(row['space'], ('group', 'town', 'world', 'interior'))
        for row in data.get('closed', []):
            self.assertIn(row['bug'], bugs, row['model'])


if __name__ == '__main__':
    unittest.main()
