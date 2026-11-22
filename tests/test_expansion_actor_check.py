# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' actors at every build (tools/expansion_actor_check.py, the actor spec check's part 3).

At milestone 1 (config/expansion-stages.json, the shipped default) an incomplete expansion actor is a count; from
milestone 2 it is a failure line naming the actor, its reference, its place and the columns it lacks. A world-wide gap
listed under tracked_gaps with its register entry is counted and never a stop. With the base game alone the actor spec
check's report is exactly what it was (no part 3, no new key). No game data."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools' / 'chim', ROOT / 'tools', ROOT / 'src'):    # src first: tools/mwad.py is a command
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import expansion_actor_check as eac  # noqa: E402
import actor_spec_check as asc  # noqa: E402

SETTING = {'expansions': {'Tribunal.esm': {'land': 'Mournhold', 'milestone': 1},
                          'Bloodmoon.esm': {'land': 'Solstheim', 'milestone': 1}},
           'tracked_gaps': {'inventory levelled': {'register': 'ACTOR-LEVELLED-INVENTORY-ONE-PICK-66', 'why': '-'}}}


def actor(ident, master='Tribunal.esm', land='Mournhold', **over):
    row = {'ref': 4200000 + len(ident), 'id': ident, 'tag': 'NPC_', 'master': master, 'land': land,
           'cell': 'Mournhold, Test Room', 'placed': True, 'model': True, 'stats': {}, 'gear': {}, 'anim': {},
           'combat': 'same', 'script': None, 'script_bound': None, 'script_fields': {}}
    row.update(over)
    return row


ROWS = [actor('complete one'),
        actor('levelled roll only', gear={'inventory levelled': 'different'}),
        actor('unbound', script='guardscript', script_bound=False),
        actor('no bow', gear={'ranged weapon': 'different'}, anim={'anim walk': 'missing'}),
        actor('not placed', placed=False, model=False),
        actor('solstheim one', master='Bloodmoon.esm', land='Solstheim', combat='different style'),
        dict(actor('a levelled point'), tag='LEVC')]


class ExpansionActorCheckTests(unittest.TestCase):
    def test_the_stores_of_frames_place_actors(self):
        # EXPANSION-SCRIPTS-NOT-ATTACHED-66 (v0.0.68): the districts' and Solstheim's frames place their people and
        # creatures in the image's stores; the check read only the rooms' tracker and the open world's actor table,
        # so all 258 such actors of the v0.0.68-dev5 build were counted as not placed
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(eac.store_actor_refs(tmp), set())                   # no stores: none, as before
            (Path(tmp) / 'chim-layer-stores.json').write_text(json.dumps([
                {'store': 'chimmh', 'maps': [{'cell': [-12, -30], 'actors': {'actors': [{'reference': 4202005}]}}]},
                {'store': 'chimsol', 'maps': [{'cell': [-22, 16], 'actors': {'actors': [{'reference': 8396993},
                                                                                         {'id': 'no number'}]}},
                                              {'cell': [-28, 19], 'actors': {}}]}]), encoding='utf-8')
            self.assertEqual(eac.store_actor_refs(tmp), {4202005, 8396993})

    def test_an_inert_script_needs_no_binding(self):
        # nolore and nohello only declare the locals the dialogue reads: the compiler leaves them out of the bindings
        # in the base game too, so they are not an unattached script (74 expansion people on 18 November 2026)
        inert = {'nolore', 'nohello'}
        self.assertIsNone(eac.script_bound('NoLore', 4201741, set(), inert))
        self.assertIsNone(eac.script_bound(None, 4201741, set(), inert))
        self.assertFalse(eac.script_bound('guardscript', 4201741, set(), inert))
        self.assertTrue(eac.script_bound('guardscript', 4201741, {4201741}, inert))
        self.assertEqual(eac.failing(actor('lore keeper', script='nolore', script_bound=None), {}), [])

    def test_columns_and_the_tracked_gap(self):
        tracked = SETTING['tracked_gaps']
        self.assertEqual(eac.failing(ROWS[0], tracked), [])
        self.assertEqual(eac.failing(ROWS[1], tracked), [])                     # the tracked roll is never a stop
        self.assertEqual(eac.failing(ROWS[2], tracked), ['script attached'])
        self.assertEqual(eac.failing(ROWS[3], tracked), ['inventory/equipment', 'animations'])
        self.assertEqual(eac.failing(ROWS[4], tracked), ['placed', 'model'])
        self.assertEqual(eac.failing(ROWS[5], tracked), ['combat style'])

    def test_milestone_one_counts_and_never_stops(self):
        self.assertEqual(eac.verdict(ROWS, SETTING), [])
        lands = eac.summary(ROWS, SETTING, {'Mournhold': {'rooms with a map': '1 of 1'}}, None)
        m = lands['Mournhold']
        self.assertEqual((m['stage 2 actor placements'], m['stage 2 actors placed'], m['stage 2 actors complete']),
                         (5, 4, 2))
        self.assertEqual(m['stage 2 failing columns'], {'animations': 1, 'inventory/equipment': 1, 'model': 1,
                                                        'placed': 1, 'script attached': 1})
        self.assertEqual(m['stage 2 tracked gaps (not a stop)'],
                         {'inventory levelled': {'placements': 1, 'register': 'ACTOR-LEVELLED-INVENTORY-ONE-PICK-66'}})
        self.assertEqual(m['levelled points placed'], '1 of 1')
        self.assertEqual(lands['Solstheim']['stage 2 actors complete'], 0)

    def test_milestone_two_names_every_incomplete_actor_of_that_expansion(self):
        setting = json.loads(json.dumps(SETTING))
        setting['expansions']['Tribunal.esm']['milestone'] = 2
        lines = eac.verdict(ROWS, setting)
        self.assertEqual(len(lines), 3)                       # Tribunal's three incomplete; Bloodmoon stays at 1
        self.assertIn('expansion actor unbound (reference 4200007, Tribunal.esm, Mournhold, Test Room): lacks script '
                      'attached', lines)
        self.assertTrue(all('solstheim one' not in line for line in lines))
        self.assertEqual(eac.verdict(ROWS * 30, setting, limit=5)[-1], '... and 85 more incomplete expansion actors')

    def test_the_shipped_setting(self):
        setting = eac.load_setting()
        self.assertEqual({m: e['milestone'] for m, e in setting['expansions'].items()},
                         {'Tribunal.esm': 1, 'Bloodmoon.esm': 1})
        bugs = {b['id'] for b in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for field, gap in setting['tracked_gaps'].items():
            self.assertIn(field, eac.GEAR_FIELDS + eac.STAT_FIELDS)
            self.assertIn(gap['register'], bugs)

    def test_base_game_alone_keeps_the_report_as_it_was(self):
        audit = {'fields': {}, 'rows': []}
        with mock.patch.object(asc, 'placement', return_value=({}, {'places': [], 'totals': {}})), \
                mock.patch.object(asc, 'records_report', return_value=audit), \
                mock.patch.object(asc, 'set_aside_lines', return_value=[]), \
                mock.patch('mwad.masters.master_path', return_value=Path(__file__)), \
                mock.patch.object(eac, 'check') as part3:
            with mock.patch('mwad.masters.selected_masters', return_value=('Morrowind.esm',)):
                base = asc.check('/nowhere', '/nowhere')
            part3.assert_not_called()
            self.assertNotIn('expansion_actors', base)
            self.assertNotIn('_expansion_rows', base)
            part3.return_value = {'setting': {}, 'lands': {}, 'failures': ['expansion actor x: lacks placed'],
                                  'rows': []}
            with mock.patch('mwad.masters.selected_masters',
                            return_value=('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')):
                both = asc.check('/nowhere', '/nowhere')
            self.assertEqual(both['expansion_actors']['failures'], ['expansion actor x: lacks placed'])
            self.assertIn('expansion actor x: lacks placed', both['failures'])
        self.assertEqual(set(both) - set(base), {'expansion_actors', '_expansion_rows'})

    def test_early_check_is_silent_at_milestone_one(self):
        context = mock.Mock(masters=['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'], args=mock.Mock(reuse_from=None))
        self.assertEqual(eac.early(context), [])


if __name__ == '__main__':
    unittest.main()
