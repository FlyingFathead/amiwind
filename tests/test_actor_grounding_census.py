"""Island-wide actor grounding census and its build preflight (CHIM-ACTOR-GROUNDING-POLICY-36)."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import actor_grounding  # noqa: E402
import actor_grounding_census as census  # noqa: E402
import build_preflight  # noqa: E402

GNAAR_MOK_BLOCK = ('andilo thelas', 'anglalos', 'caryarel', 'dreamer_talker06', 'dreynis nothro', 'farvyn oreyn',
                   'nadene rotheran', 'vala herennius', 'valveli arelas')


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def record(tag, payload, flags=0):
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, flags) + payload


def cell(x, y, refs, interior=False):
    payload = sub('NAME', b'\0') + sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y))
    for number, (identifier, position, deleted) in enumerate(refs, 1):
        payload += sub('FRMR', struct.pack('<I', number)) + sub('NAME', identifier.encode() + b'\0')
        payload += sub('DATA', struct.pack('<6f', *position, 0, 0, 0))
        if deleted:
            payload += sub('DELE', b'\0\0\0\0')
    return record('CELL', payload)


def npc(identifier, health=50, spells=()):
    stats = bytearray(52)
    struct.pack_into('<h', stats, 38, health)
    payload = sub('NAME', identifier.encode() + b'\0') + sub('NPDT', bytes(stats))
    for spell in spells:
        payload += sub('NPCS', spell.encode().ljust(32, b'\0'))
    return record('NPC_', payload)


def master(*parts):
    return record('TES3', sub('HEDR', bytes(300))) + b''.join(parts)


CENTRE = (-53248.0, 20480.0, 100.0)  # the Gnaar Mok test block (config/bcoast_x7y2.json)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)

    def write(self, raw):
        (self.data / 'Morrowind.esm').write_bytes(raw)

    def test_area_residents_frame_filter(self):
        raw = master(npc('in frame'), npc('deleted one'), npc('far away'), npc('indoors'),
                     cell(-7, 2, [('In Frame', CENTRE, False), ('deleted one', CENTRE, True),
                                  ('crate', CENTRE, False)]),
                     cell(-2, 2, [('far away', (-14000.0, 20000.0, 0.0), False)]),
                     cell(-7, 2, [('indoors', CENTRE, False)], interior=True))
        cells, npcs = census._exterior_cells(raw)
        box = census.area_box('bcoast_x7y2')
        self.assertEqual(census.area_residents(cells, npcs, box), ['in frame'])
        self.assertEqual(census.area_residents(cells, npcs, box, skip={'in frame'}), [])

    def test_unclassified_resident_refused_with_its_id(self):
        self.write(master(npc('vala herennius'), npc('no such grounded npc'),
                          cell(-7, 2, [('vala herennius', CENTRE, False), ('no such grounded npc', CENTRE, False)])))
        problems = census.area_problems(self.data, ['bcoast_x7y2'])
        self.assertEqual(len(problems), 1)
        self.assertIn('1 of 2 NPC residents', problems[0])
        self.assertIn('no such grounded npc', problems[0])
        self.assertNotIn('vala herennius', problems[0])
        self.assertEqual(build_preflight.grounding_problems(self.data, ['bcoast_x7y2']), problems)

    def test_classified_area_passes(self):
        self.write(master(*[npc(i) for i in GNAAR_MOK_BLOCK],
                          cell(-7, 2, [(i, CENTRE, False) for i in GNAAR_MOK_BLOCK])))
        self.assertEqual(census.area_problems(self.data, ['bcoast_x7y2']), [])

    def test_preflight_skips_without_data_or_areas(self):
        self.assertEqual(build_preflight.grounding_problems(None, ['bcoast_x7y2']), [])
        self.assertEqual(build_preflight.grounding_problems(self.data, []), [])
        self.assertEqual(build_preflight.grounding_problems(self.data / 'missing', ['bcoast_x7y2']), [])

    def test_build_runs_it_before_any_stage(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        check = text.index('build_preflight.grounding_problems(')
        self.assertLess(text.index('build_preflight.run(args.workspace'), check)
        self.assertLess(check, text.index("raise ValueError('Build preflight failed before any stage:"))

    def test_record_facts(self):
        raw = master(npc('dead one', health=0), npc('levitator', spells=('lev ability',)),
                     record('SPEL', sub('NAME', b'lev ability\0') + sub('SPDT', struct.pack('<iii', 1, 0, 0))
                            + sub('ENAM', struct.pack('<hbbiiiii', 10, 0, 0, 0, 0, 0, 10, 10))))
        _, npcs = census._exterior_cells(raw)
        levitating = census.levitate_abilities(raw)
        self.assertEqual(levitating, {'lev ability'})
        self.assertTrue(census.npc_facts(npcs['dead one'])['dead'])
        self.assertEqual(census.npc_facts(npcs['levitator'], levitating)['levitate_abilities'], ['lev ability'])


class MeasurementTests(unittest.TestCase):
    def test_land_height_on_a_plane(self):
        heights = [[8.0 * x + 2.0 * y for x in range(65)] for y in range(65)]
        lands = {(1, -1): heights}
        x, y = 8192 + 300.0, -8192 + 1000.0
        self.assertAlmostEqual(census.land_height(lands, x, y), 8.0 * 300 / 128 + 2.0 * 1000 / 128)
        self.assertIsNone(census.land_height(lands, 0.0, 0.0))

    def test_surface_heights_and_support(self):
        import numpy as np
        tris = np.array([[[0, 0, 100], [100, 0, 100], [0, 100, 100]],
                         [[0, 0, 500], [100, 0, 500], [0, 100, 500]]], dtype=float)
        self.assertEqual(sorted(census.surface_heights(tris, 10, 10).tolist()), [100.0, 500.0])
        self.assertEqual(census.surface_heights(tris, 90, 90).tolist(), [])
        # the roof above the feet is not a support; the floor is
        self.assertEqual(census.support(130.0, 0.0, [(100.0, 'floor'), (500.0, 'roof')]), (100.0, 'floor'))
        self.assertEqual(census.support(130.0, None, []), (None, None))

    def test_tolerance_matches_the_support_fitter(self):
        # actor_grounding._Fitter._setup searches from 8 Quake units above the feet down 40, at scale 0.25
        self.assertEqual((census.STEP_UP, census.DROP), (8 / .25, (40 - 8) / .25))
        self.assertTrue(census.classify_gap(-census.STEP_UP) and census.classify_gap(census.DROP))
        self.assertFalse(census.classify_gap(census.DROP + .01) or census.classify_gap(-census.STEP_UP - .01))
        self.assertFalse(census.classify_gap(None))

    def test_classify_never_guesses(self):
        row = lambda identifier, gap, water=False: {'id': identifier, 'gap': gap,  # noqa: E731
                                                   'ground': census.classify_gap(gap), 'below_water': water}
        facts = {i: {'dead': False, 'levitate_abilities': []} for i in ('a', 'b', 'c', 'd', 'e', 'listed')}
        facts['d'] = {'dead': True, 'levitate_abilities': []}
        facts['e'] = {'dead': False, 'levitate_abilities': ['x']}
        rows = [row('a', 20), row('b', 20), row('b', 400), row('c', 0, water=True), row('d', 900), row('e', 0),
                row('listed', 999)]
        policy = {'format': 2, 'unclassified': 'error', 'ground_npcs': ['listed'], 'exceptions': {}}
        ground, dead, candidates, conflicts = census.classify(rows, facts, policy)
        self.assertEqual(ground, {'a'})
        self.assertEqual(list(dead), ['d'])
        self.assertEqual(sorted(candidates), ['b', 'c', 'e'])
        self.assertEqual([c['id'] for c in conflicts], ['listed'])
        merged = census.merged_policy(policy, ground, dead)
        self.assertEqual(merged['ground_npcs'], ['a', 'listed'])
        self.assertEqual(merged['exceptions']['d']['mode'], 'authored_dead')


class PolicyTests(unittest.TestCase):
    def test_gnaar_mok_block_is_ground(self):
        for identifier in GNAAR_MOK_BLOCK:
            self.assertEqual(actor_grounding.initial_state(identifier), 'ground', identifier)

    def test_policy_shape(self):
        policy = json.loads(actor_grounding.POLICY.read_text())
        ground = policy['ground_npcs']
        self.assertEqual(ground, sorted(set(ground)))
        self.assertEqual(ground, [g.casefold() for g in ground])
        self.assertFalse(set(ground) & {k.casefold() for k in policy['exceptions']})
        self.assertGreaterEqual(len(ground), 886)
        for identifier in policy['exceptions']:
            actor_grounding.initial_state(identifier)  # every exception documented and of a known mode


if __name__ == '__main__':
    unittest.main()
