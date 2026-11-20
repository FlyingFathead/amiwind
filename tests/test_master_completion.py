# SPDX-License-Identifier: GPL-3.0-only
"""The unified readiness count per land and the completion panel per master (TOOLKIT-EXPANSION-COMPLETION-67).

The numbers are pinned to their sources: the tracker data's cells and rooms (a synthetic doc here, and the repository's
own snapshot docs/chim/progress-state.json), the MWScript tracker (docs/mwscript-features.json, its states worked out by
tools/mwscript_features.py) and the census door records. The Toolkit counts the same as the generator
(tests/test_completion_panel.js, run with node), and the progress tracker page draws the generator's numbers.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'src', ROOT / 'tools'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import master_completion as MC  # noqa: E402

SCRIPTS = ROOT / 'docs' / 'mwscript-features.json'


def cell(island, land, bucket, state, group, name=''):
    return {'island': island, 'land': land, 'name': name,
            'chim': {'bucket': bucket, 'state': state, 'group': group},
            'contents': {'source': 'census', 'npcs': 1, 'creatures': 0, 'items': 2, 'containers': 0, 'doors': 0,
                         'activators': 1, 'lights': 0} if land else None}


def room(name, island, master, state, access='door', reasons=()):
    return {'id': name, 'name': name, 'island': island, 'master': master, 'state': state, 'access': access,
            'reasons': list(reasons)}


def fixture():
    cells = {
        '0,0': cell(1, True, 'audits_passed', 'audits_passed', 'in_game', 'Seyda Neen'),
        '1,0': cell(1, True, 'terrain_complete_unlit', 'terrain_complete_unlit', 'in_game'),
        '2,0': cell(1, False, 'empty_sea', 'sea_in_game', 'in_game'),
        '3,0': cell(1, False, 'ocean', 'sea_in_game', 'in_game'),          # open ocean: not counted
        '4,0': cell(1, False, 'ocean', 'settled', 'settled'),              # beyond the edge: not counted
        '5,0': cell(1, True, 'converted_failing', 'converted_failing', 'not_in_game'),
        '-20,20': cell(2, True, 'not_started', 'solstheim', 'not_in_game', 'Hrothmund\'s Barrow'),
        '-21,20': cell(2, True, 'not_started', 'solstheim', 'not_in_game'),
        '9,9': cell(None, False, 'not_started', 'solstheim', 'not_in_game'),  # no island: not counted
        '-3,-30': cell(3, True, 'audits_passed', 'audits_passed', 'in_game', 'Mournhold, Plaza Brindisi Dorom'),
        '-4,-30': cell(3, True, 'terrain_complete_unlit', 'terrain_complete_unlit', 'in_game', 'Mournhold, Plaza Brindisi Dorom'),
    }
    for k in ('-3,-30', '-4,-30'):          # the presented districts have no census cell of their own
        cells[k]['contents'] = None
    rooms = [
        room('Seyda Neen, Arrille\'s Tradehouse', 'Vvardenfell', 'Morrowind.esm', 'on_chim_rooms'),
        room('Imperial Prison Ship', 'Vvardenfell', 'Morrowind.esm', 'room_map'),
        room('ToddTest', 'none', 'Morrowind.esm', 'test_cell', 'unreachable', ['unreachable']),
        room('Raven Rock, Bar', 'Solstheim', 'Bloodmoon.esm', 'on_chim_rooms'),
        room('Fort Frostmoth, General Quarters', 'Solstheim', 'Morrowind.esm', 'on_chim_rooms'),
        room('Vor Lair, Interior', 'none', 'Bloodmoon.esm', 'no_entrance', 'unreachable', ['unreachable']),
        room('Mournhold, Plaza Brindisi Dorom', 'Mournhold', 'Tribunal.esm', 'not_started', 'teleport'),
        room('Mournhold, Great Bazaar', 'Mournhold', 'Tribunal.esm', 'converted', 'teleport'),
        room('Sotha Sil, Mournhold', 'Mournhold', 'Tribunal.esm', 'teleport_only', 'teleport_only', ['teleport_only']),
        room('Mournhold, Royal Palace', 'none', 'Tribunal.esm', 'no_entrance', 'unreachable', ['unreachable']),
        room('Mournhold Temple: High Chapel', 'Mournhold', 'Tribunal.esm', 'on_chim_rooms'),
        room('Old Mournhold: Abandoned Passageway', 'none', 'Tribunal.esm', 'on_chim_rooms', 'teleport'),
    ]
    interiors = [
        {'name': 'Mournhold Temple: High Chapel', 'set': 'tribunal',
         'contents': {'source': 'census', 'npcs': 3, 'creatures': 0, 'items': 5, 'containers': 2, 'doors': 1, 'lights': 4},
         'stats': {'records': {'by_type': {'NPC_': 3, 'ITEM': 5, 'CONT': 2, 'DOOR': 1, 'LIGH': 4, 'ACTI': 1}}}},
        {'name': 'Fort Frostmoth, General Quarters', 'set': 'vvardenfell',
         'contents': {'source': 'census', 'npcs': 2, 'creatures': 0, 'items': 1, 'containers': 1, 'doors': 1, 'lights': 1},
         'stats': {'records': {'by_type': {'NPC_': 2, 'ITEM': 1, 'CONT': 1, 'DOOR': 1, 'LIGH': 1}}}},
    ]
    doc = {'cells': cells, 'interior_rooms': {'rooms': rooms}, 'interiors': interiors, 'sources': {'census': True},
           'headline': {'in_game_label': 'v0.0.67 (2b086671)', 'eligible_release': 'v0.0.67',
                        'groups': {'in_game': 6, 'not_in_game': 4, 'settled': 1, 'accounted_for': 7, 'cells': 11},
                        'states': {'audits_passed': 2},
                        'islands': [{'island': 1, 'cells': 4, 'done': 3, 'percent': 75.0, 'complete': 0, 'terrain_complete': 0,
                                     'complete_unlit': 0, 'terrain_complete_unlit': 1, 'audits_passed': 1, 'eligible': 3},
                                    {'island': 2, 'cells': 2, 'done': 0, 'percent': 0.0},
                                    {'island': 3, 'cells': 2, 'done': 2, 'percent': 100.0, 'complete': 0, 'terrain_complete': 0,
                                     'complete_unlit': 0, 'terrain_complete_unlit': 1, 'audits_passed': 1, 'eligible': 2}]}}
    census = {
        'cells': {'0,0': {'doors': [{'to': 'Seyda Neen, Arrille\'s Tradehouse'}, {'to': 'Imperial Prison Ship'}]}},
        'interiors': {
            'seyda neen, arrille\'s tradehouse': {'name': 'Seyda Neen, Arrille\'s Tradehouse', 'set': 'vvardenfell',
                                                  'doors': [{'to': ''}]},
            'imperial prison ship': {'name': 'Imperial Prison Ship', 'set': 'vvardenfell', 'doors': []},
            'mournhold, plaza brindisi dorom': {'name': 'Mournhold, Plaza Brindisi Dorom', 'set': 'tribunal',
                                                'doors': [{'to': 'Mournhold Temple: High Chapel'},
                                                          {'to': 'Mournhold, Great Bazaar'}]},
            'mournhold temple: high chapel': {'name': 'Mournhold Temple: High Chapel', 'set': 'tribunal',
                                              'doors': [{'to': 'Mournhold, Plaza Brindisi Dorom'}]},
            'mournhold, great bazaar': {'name': 'Mournhold, Great Bazaar', 'set': 'tribunal', 'doors': []}}}
    return doc, census


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.doc, self.census = fixture()
        self.ready = MC.readiness(self.doc)
        self.lands = {x['id']: x for x in self.ready['lands']}

    def test_open_terrain_is_land_and_empty_sea_on_an_island(self):
        v, s, m = self.lands['vvardenfell'], self.lands['solstheim'], self.lands['mournhold']
        self.assertEqual((v['terrain']['ready'], v['terrain']['total']), (3, 4))     # ocean, settled, no island left out
        self.assertEqual(v['terrain']['not_ready'][0]['reason'], 'converted_failing')
        self.assertEqual((s['terrain']['ready'], s['terrain']['total']), (0, 2))
        self.assertEqual((m['terrain']['ready'], m['terrain']['total']), (2, 2))
        for land in self.ready['lands']:      # the same cells the headline's island rows count
            isl = next(i for i in self.doc['headline']['islands'] if i['island'] == land['island'])
            self.assertEqual(land['terrain']['total'], isl['cells'])

    def test_rooms_by_master_districts_once_and_still_to_build(self):
        v, s, m = self.lands['vvardenfell'], self.lands['solstheim'], self.lands['mournhold']
        # a base-game room on Solstheim counts for Solstheim; a no-entrance room for its master's land; the prison ship
        # (a room map of our own) is ready (TRACKER-ROOM-MAPS-NOT-READY-67)
        self.assertEqual((v['rooms']['ready'], v['rooms']['total']), (2, 3))
        self.assertEqual((s['rooms']['ready'], s['rooms']['total']), (2, 3))
        # the plaza is open terrain (its cells), so it is not a room as well; the others are not ready with a reason
        self.assertEqual(m['rooms']['as_terrain'], ['Mournhold, Plaza Brindisi Dorom'])
        self.assertEqual((m['rooms']['ready'], m['rooms']['total']), (2, 5))
        reasons = {r['reason']: [i['name'] for i in r['items']] for r in m['rooms']['not_ready']}
        self.assertEqual(reasons, {'converted': ['Mournhold, Great Bazaar'], 'teleport_only': ['Sotha Sil, Mournhold'],
                                   'no_entrance': ['Mournhold, Royal Palace']})
        sotha = m['rooms']['not_ready'][1]['items'][0]
        self.assertIn('script', sotha['leads'])
        # Vvardenfell's only room not ready is the test cell; the ship is named as a special interior, not as a reason
        self.assertEqual({r['reason']: [i['name'] for i in r['items']] for r in v['rooms']['not_ready']},
                         {'test_cell': ['ToddTest']})
        self.assertEqual(v['rooms']['special'], ['Imperial Prison Ship'])
        self.assertEqual((s['rooms']['special'], m['rooms']['special']), ([], []))

    def test_a_room_map_of_our_own_counts_ready(self):
        """TRACKER-ROOM-MAPS-NOT-READY-67, a regression of f87deed76 / b82bd6693 (19 November 2026): the ready room
        states left out 'room_map', so the opening sequence's two rooms, in the game as room maps of our own since
        v0.0.48, were counted not ready (Vvardenfell rooms 1,129 of 1,131). Fails on that rule."""
        rooms = [room('Imperial Prison Ship', 'Vvardenfell', 'Morrowind.esm', 'room_map', 'teleport_only'),
                 room('Seyda Neen, Census and Excise Office', 'Vvardenfell', 'Morrowind.esm', 'room_map'),
                 room('Seyda Neen, Arrille\'s Tradehouse', 'Vvardenfell', 'Morrowind.esm', 'on_chim_rooms')]
        ready = MC.readiness({'cells': {}, 'interior_rooms': {'rooms': rooms}})
        v = next(x for x in ready['lands'] if x['id'] == 'vvardenfell')
        self.assertEqual((v['rooms']['ready'], v['rooms']['total'], v['rooms']['percent']), (3, 3, 100.0))
        self.assertEqual(v['rooms']['not_ready'], [])
        self.assertEqual(v['rooms']['special'], ['Imperial Prison Ship', 'Seyda Neen, Census and Excise Office'])
        self.assertIn('room map of our own', ready['definition'])
        self.assertIn('special interiors', ready['definition'])
        summ = MC.summary(ready)['lands'][0]['rooms']
        self.assertEqual((summ['not_ready'], summ['not_ready_names'], summ['special']),
                         ([], [], ['Imperial Prison Ship', 'Seyda Neen, Census and Excise Office']))
        # no ready state is a reason: a not-ready label for one would put it under "not ready" again
        self.assertFalse(set(MC.READY_ROOM_STATES) & set(MC.ROOM_REASONS))

    def test_ready_rooms_are_the_in_game_group(self):
        """One definition: the ready room states are the tracker's in-game group (tools/cell_progress_rooms.py GROUPS),
        the states the Toolkit's tiles draw green; the Toolkit's own list is checked against it in ToolkitParityTests."""
        import cell_progress_rooms as RM
        self.assertEqual(tuple(MC.READY_ROOM_STATES), tuple(RM.GROUPS['in_game'][1]))
        self.assertTrue(set(MC.SPECIAL_ROOM_STATES) <= set(MC.READY_ROOM_STATES))

    def test_old_readiness_data_is_counted_again(self):
        """Data whose readiness was written by the old rule (format aw-land-readiness-1) is never drawn as it is."""
        self.assertNotEqual(MC.FORMAT, 'aw-land-readiness-1')

    def test_totals_and_all_lands(self):
        for land in self.ready['lands']:
            t, r, a = land['terrain'], land['rooms'], land['total']
            self.assertEqual((a['ready'], a['total']), (t['ready'] + r['ready'], t['total'] + r['total']))
        a = self.ready['all']
        self.assertEqual((a['total']['ready'], a['total']['total']), (11, 19))
        self.assertEqual(a['total']['percent'], 57.9)
        self.assertEqual((a['rooms']['ready'], a['rooms']['total']), (6, 11))
        self.assertEqual(MC.pct(1, 8), 12.5)
        self.assertEqual(MC.pct(1, 3), 33.3)
        self.assertEqual(MC.pct(2, 3), 66.7)
        self.assertIn('Ready = in the game on CHIM', self.ready['definition'])
        self.assertIn('Mournhold: open terrain 2 of 2 (100.0 %)', MC.line(self.ready))

    def test_completion_panel_sources(self):
        doc = dict(self.doc)
        MC.attach(doc, self.census, None)
        by = {m['id']: m for m in doc['completion']['masters']}
        self.assertEqual([m['id'] for m in doc['completion']['masters']], ['mournhold', 'solstheim', 'vvardenfell'])
        t = by['mournhold']
        self.assertIsNone(t['scripts'])                               # no MWScript tracker given: not measured
        self.assertIsNone(t['variables']['globals'])
        self.assertEqual(t['variables']['todo'], 'MOURNHOLD-STATE-TRACKING-PARITY-67')
        # placed in the original: the census counts of the land's own rooms (by_type, activators included)
        self.assertEqual(t['placed']['original']['people'], 3)
        self.assertEqual(t['placed']['original']['activators'], 1)
        self.assertIsNone(t['placed']['in_game'])
        # the base-game room on Solstheim counts for Solstheim, as in the readiness count (2), with its land cells (2 x 1)
        self.assertEqual(by['solstheim']['placed']['original']['people'], 4)
        self.assertEqual(by['vvardenfell']['placed']['original']['items'], 6)          # 3 land cells x 2
        # doors: the plaza's door to the bazaar has no door back; the chapel's way back is there
        d = t['doors']
        self.assertEqual((d['load_doors'], d['with_way_back']), (3, 2))
        self.assertEqual(d['one_way'], [{'from': 'Mournhold, Plaza Brindisi Dorom', 'to': 'Mournhold, Great Bazaar'}])
        self.assertIsNone(d['verified_in_build'])
        self.assertEqual(d['gap'], 'DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67')
        self.assertEqual([r['name'] for r in d['rooms_no_door']], ['Mournhold, Great Bazaar', 'Mournhold, Royal Palace',
                                                                   'Sotha Sil, Mournhold'])
        v = by['vvardenfell']['doors']        # the ship has no door out: one way
        self.assertEqual((v['load_doors'], v['with_way_back']), (3, 2))

    def test_scripts_are_the_mwscript_trackers_own_states(self):
        import mwscript_features as mf
        script_doc = MC.load_scripts(SCRIPTS)
        self.assertIsNotNone(script_doc, 'docs/mwscript-features.json')
        self.assertIsNone(MC.load_scripts(None))
        rows = MC.scripts(json.loads(json.dumps(script_doc)))
        mf.use(script_doc)
        for land in MC.LANDS:
            mine = [r for r in script_doc['scripts'] if r['master'] == land['master']]
            want = Counter(mf.state_of(r)[0] for r in mine)
            got = {s['state']: s['count'] for s in rows[land['id']]['states']}
            self.assertEqual(got, {s: want.get(s, 0) for s in mf.STATES}, land['master'])
            self.assertEqual(rows[land['id']]['used'], len(mine) - want['inert'])
            for s in rows[land['id']]['states']:
                self.assertEqual(len(s['items']), s['count'])
        trib = {s['state']: s for s in rows['mournhold']['states']}
        for item in trib['missing-function']['items']:
            self.assertTrue(item['missing'], item['id'])
        start = [s['id'] for s in rows['mournhold']['start']]
        self.assertEqual(start, sorted((r['id'] for r in script_doc['scripts']
                                        if r['master'] == 'Tribunal.esm' and r.get('start')), key=str.casefold))

    def test_snapshot_readiness_matches_its_own_counts(self):
        state = json.loads((ROOT / 'docs' / 'chim' / 'progress-state.json').read_text(encoding='utf-8'))
        r = state.get('readiness')
        self.assertIsNotNone(r, 'docs/chim/progress-state.json carries the readiness count (snapshot it again)')
        self.assertEqual(r['format'], MC.FORMAT, 'the snapshot is counted by the current rules (snapshot it again)')
        for land in r['lands']:      # a special interior is ready: never under "not ready" as well
            self.assertFalse(set(land['rooms'].get('special') or []) & set(land['rooms']['not_ready_names']), land['name'])
        islands = {i['island']: i for i in state['islands']}
        for land in r['lands']:
            if land['island'] in islands:
                self.assertEqual(land['terrain']['total'], islands[land['island']]['cells'], land['name'])
        rooms = sum(x['rooms']['total'] + len(x['rooms']['as_terrain']) for x in r['lands'])
        self.assertEqual(rooms, state['interiors']['totals']['total'], 'every room of the tracker is counted once')
        for k in ('terrain', 'rooms', 'total'):
            self.assertEqual(r['all'][k]['ready'], sum(x[k]['ready'] for x in r['lands']))
            self.assertEqual(r['all'][k]['total'], sum(x[k]['total'] for x in r['lands']))
        import cell_progress_state as cps
        page = (ROOT / 'docs' / 'chim' / 'PROGRESS_TRACKER.md').read_text(encoding='utf-8')
        self.assertIn('### Ready, per land', page)
        for line in cps.ready_block(state):
            self.assertIn(line, page)


class ToolkitParityTests(unittest.TestCase):
    def test_toolkit_counts_the_same_and_draws_the_generators_numbers(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable')
        doc, census = fixture()
        MC.attach(doc, census, MC.scripts(MC.load_scripts(SCRIPTS)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'doc.json'
            path.write_text(json.dumps(doc), encoding='utf-8')
            res = subprocess.run([node, str(ROOT / 'tests' / 'test_completion_panel.js'), str(ROOT / 'amiwind-toolkit'),
                                  str(path)], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn('PASS completion panel', res.stdout)
        counted = json.loads(res.stdout.splitlines()[0])
        self.assertEqual(counted, json.loads(json.dumps(doc['readiness'])), 'the page counts as the generator does')

    def test_toolkit_ready_room_states_are_the_generators(self):
        """The Toolkit's READY_ROOM_STATES, SPECIAL_ROOM_STATES and READY_FORMAT are the generator's
        (TRACKER-ROOM-MAPS-NOT-READY-67: the two lists were left without 'room_map' together)."""
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable')
        script = ('const v = require(process.argv[1]); console.log(JSON.stringify([v.READY_ROOM_STATES, '
                  'v.SPECIAL_ROOM_STATES, v.READY_FORMAT, v.SPECIAL_TEXT]))')
        res = subprocess.run([node, '-e', script, str(ROOT / 'amiwind-toolkit' / 'expansion-views.js')],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(json.loads(res.stdout), [list(MC.READY_ROOM_STATES), list(MC.SPECIAL_ROOM_STATES), MC.FORMAT,
                                                  MC.SPECIAL_TEXT])


if __name__ == '__main__':
    unittest.main()
