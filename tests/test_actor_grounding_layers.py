# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' id file beside the grounding policy (config/actor_grounding_layers.json): the people only the
expansions place outdoors are classed there and read by tools/actor_grounding_layers.py, so neither the base game's
policy file nor tools/actor_grounding.py moves (their code and file are in the room actor units' keys). No game data."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import actor_grounding as ag  # noqa: E402
import actor_grounding_layers as agl  # noqa: E402
import actor_grounding_census as census  # noqa: E402

POLICY = {'format': 2, 'unclassified': 'error', 'ground_npcs': ['fargoth'],
          'exceptions': {'tarhiel': {'mode': 'scripted_airborne', 'reason': 'falls from the sky by script'}}}
DEAD = {'mode': 'authored_dead', 'source': 'NPC_ record NPDT: health 0', 'reason': 'Authored initially dead NPC.'}


class Layers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.policy = root / 'actor_grounding.json'
        self.layers = root / 'actor_grounding_layers.json'
        self.policy.write_text(json.dumps(POLICY, indent=2) + '\n', encoding='utf-8')
        self.patches = [patch.object(ag, 'POLICY', self.policy), patch.object(ag, 'ROOMS', root / 'none.json')]
        for p in self.patches:
            p.start()
        agl._LAYERS.clear()
        ag._ROOMS.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        agl._LAYERS.clear()
        ag._ROOMS.clear()
        self.tmp.cleanup()

    def write_layers(self, ground, rules=None):
        doc = census.layers_doc((), {}, ground, rules or {}, ['Morrowind.esm', 'Tribunal.esm'])
        self.layers.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
        agl._LAYERS.clear()

    def test_the_file_is_looked_for_beside_the_policy(self):
        self.assertEqual(agl.layers_path(), self.layers)

    def test_without_the_file_an_expansion_id_is_refused_and_the_policy_holds(self):
        self.assertEqual(agl.outdoor_state('Fargoth'), 'ground')
        self.assertEqual(agl.outdoor_state('tarhiel'), 'scripted_airborne')
        with self.assertRaisesRegex(ValueError, 'Unclassified initial support state: plitinius mero'):
            agl.outdoor_state('plitinius mero')

    def test_an_id_of_the_file_is_classed_and_the_policy_file_is_not_touched(self):
        before = self.policy.read_bytes()
        self.write_layers(['Plitinius Mero'], {'db_victim': DEAD})
        self.assertEqual(agl.outdoor_state('plitinius mero'), 'ground')
        self.assertEqual(agl.outdoor_state('DB_Victim'), 'authored_dead')
        self.assertEqual(self.policy.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'Unclassified'):
            agl.outdoor_state('someone else')

    def test_the_policys_own_reader_does_not_read_the_file(self):
        """tools/actor_grounding.py is in the room actor units' keys: it stays as it was, and a room resident is
        classed by the policy and the room files only."""
        self.write_layers(['Plitinius Mero'])
        with self.assertRaisesRegex(ValueError, 'Unclassified'):
            ag.initial_state('plitinius mero')
        text = (ROOT / 'tools' / 'actor_grounding.py').read_text(encoding='utf-8')
        self.assertNotIn('actor_grounding_layers', text)

    def test_the_policy_wins_over_the_file(self):
        self.write_layers(['tarhiel'], {'fargoth': DEAD})
        self.assertEqual(agl.outdoor_state('tarhiel'), 'scripted_airborne')
        self.assertEqual(agl.outdoor_state('fargoth'), 'ground')

    def test_an_undocumented_rule_or_another_format_is_refused(self):
        self.write_layers([], {'ghost': {'mode': 'floating'}})
        with self.assertRaisesRegex(ValueError, 'undocumented'):
            agl.outdoor_state('ghost')
        self.layers.write_text(json.dumps({'format': 'something else'}), encoding='utf-8')
        agl._LAYERS.clear()
        with self.assertRaisesRegex(ValueError, 'Unsupported grounding layers file'):
            agl.outdoor_state('plitinius mero')

    def test_a_broken_policy_is_still_an_error(self):
        self.policy.write_text(json.dumps(dict(POLICY, format=1)), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsupported grounding policy'):
            agl.outdoor_state('fargoth')

    def test_the_file_keeps_what_it_held_and_adds_the_new(self):
        doc = census.layers_doc({'a'}, {'x': DEAD}, {'b'}, {'y': DEAD, 'x': {'mode': 'other'}}, ['Morrowind.esm'])
        self.assertEqual(doc['ground_npcs'], ['a', 'b'])
        self.assertEqual(doc['exceptions'], {'x': DEAD, 'y': DEAD})
        self.assertEqual(doc['format'], agl.FORMAT)

    def test_the_shipped_file_if_any_is_readable_and_names_no_policy_id(self):
        shipped = ROOT / 'config' / 'actor_grounding_layers.json'
        if not shipped.is_file():
            return                                  # no expansions' id file in the tree yet: nothing to hold
        ground, rules = agl.layer_policy(shipped)
        policy = json.loads((ROOT / 'config' / 'actor_grounding.json').read_text(encoding='utf-8'))
        named = {i.casefold() for i in policy['ground_npcs']} | {k.casefold() for k in policy['exceptions']}
        self.assertFalse((set(ground) | set(rules)) & named)

    def test_the_hand_classed_ids_stay_in_the_shipped_file(self):
        """Ids classed by hand from a measurement the census cannot write itself, each with its register entry:
        SOL-COVENTINA-NO-GROUND-CLASS-68: Coventina Celata (Solstheim cell -21,24) is measured 250 units above the land
        with nothing under her, alive, no levitation, her script moves her nowhere; the engine the game follows traces
        such a person down onto the ground below when the cell becomes active, so she is ground. A census --write
        keeps known ids (layers_doc), and this test keeps them from being dropped by hand."""
        shipped = ROOT / 'config' / 'actor_grounding_layers.json'
        ground, rules = agl.layer_policy(shipped)
        self.assertIn('coventina celata', ground)
        self.assertNotIn('coventina celata', rules)


if __name__ == '__main__':
    unittest.main()
