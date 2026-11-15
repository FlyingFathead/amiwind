# SPDX-License-Identifier: GPL-3.0-only
"""tools/journey_smoke.py (GAMEPLAY-JOURNEY-SMOKE-66): the journey parses, its session scripts carry the probe
markers, and the judge reads the game's answers: a full journey passes; the dead coming back after a room
(ACTOR-STATE-NOT-READ-ON-SPAWN-54), a reward given twice, a taken item back on its table, a lost item after the load
and a part not run fail, each naming its step. JOURNEY-WALK-DIALOGUE-DESYNC-66: the walk uses the walker's steps
(each checked for its form), a session that stopped at a wrong turn names the step it stopped in and the checks it
never reached, and the journey saves with the game's own quicksave (JOURNEY-PART-B-SAVE-NOT-CARRIED-66)."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import journey_smoke as js  # noqa: E402

JOURNEY = ROOT / 'tests' / 'sessions' / 'journey_opening.txt'
VICTIM = 172001

# what a good run's game answers (the engine's own console forms: aw_mwhost.c, aw_mwconsole.c, aw_actors.c)
GOOD = {
    'fight_ship': 1, 'papers_before': 0, 'fight_before': 1, 'papers_after': 1, 'fight_after': 0, 'magic_after': 0,
    'dagger_before': 'BACK', 'dagger_taken': 'GONE', 'away_map': 'maps/sncourt-chim.chim', 'back_map': 'maps/census.bsp',
    'table_back': 'GONE', 'ring_taken': 1,
    'gold_before': 0, 'talk_screen': 'dialogue', 'papers_sellus': 0, 'package_sellus': 1, 'directions_sellus': 1,
    'gold_sellus': 87, 'journal_sellus': 1, 'package_again': 1, 'gold_again': 87, 'journal_again': 1,
    'release_map': 'maps/seyda-chim.chim', 'state_released': -1,
    'victim': VICTIM, 'list_killed': 'DEAD', 'room_map': 'maps/census.bsp', 'court_map': 'maps/sncourt-chim.chim',
    'list_back': 'DEAD',
    'health_hurt': 40, 'health_healed': 90, 'cast_list': 1, 'fighter': 172002, 'list_fight': 'FIGHTING',
    'health_fought': 84, 'state_saved': -1, 'package_loaded': 1, 'gold_loaded': 87, 'ring_loaded': 1,
    'journal_loaded': 1, 'state_loaded': -1, 'list_loaded': 'DEAD', 'door_from': 'maps/seyda-chim.chim',
    'door_to': 'maps/census.bsp', 'package_door': 1,
}


def answer(name, command, v):
    if command.startswith('player->getitemcount'):
        item = command.split(' ', 1)[1].strip('"')
        return ['getitemcount %s -> %d' % (item, v)]
    if 'disabled' in command:
        return ['dbg mwscript call %s: done, reads %d (%s); switches off now: mask %d'
                % (command.split()[-1], v, 'off' if v else 'on', 3 if v else 0)]
    if command.startswith('getjournalindex'):
        return ['dbg mwscript call journal: A1_1_FindSpymaster %d' % v]
    if command.startswith('aw_mwscript_status call getglobal'):
        return ['dbg mwscript call getglobal: CharGenState = %d (data start changed)' % v]
    if command == 'player->gethealth':
        return ['gethealth -> %d' % v]
    if command == 'chim actors kill':
        return ['chim actors kill: Seyda Neen guard (ref %d, edict 61)' % v]
    if command == 'chim actors fight':
        return ['chim actors fight: Fargoth (ref %d, edict 70)' % v]
    if command == 'chim actors list':
        state = '' if v == 'ALIVE' else ' ' + v
        rows = [] if v == 'GONE' else ['  61 Seyda Neen guard ref %d cell -2 -9 at 100 200 30%s' % (VICTIM, state)]
        return rows + [
                '  70 Fargoth ref 172002 cell -2 -9 at 140 210 30%s' % (' FIGHTING' if name == 'list_fight' else ''),
                'chim actors: 2 actors alive, 90 edicts; joins 1']
    if command == 'dbg cast spell list':
        return [' m0 Test spell (made) *', 'Selected: Test spell, cost 9, chance 100 %%; %d cast, 0 failed, 0 refused, %d landed' % (v, v)]
    if command == 'aw_placed aim':
        # aw_inventory.c AW_PlacedAimReport: the dagger's focus row switched off once taken, on again if it came back
        return ['aw_placed aim: reach 48, 154 rows (room), eye 130 191 79, aimed row 41',
                '  41 I 119577 Iron Dagger: at 130 177 67, edict 0 drawn 0 disabled %d, dist 18.5 along 18.4 off 1.2, '
                'sight 0.99 (0.3 short), ray -2.0' % (0 if v == 'BACK' else 1),
                '  43 I 119580 Silverware Plate: at 145 176 63, edict 0 drawn 0 disabled 0, dist 21.0',
                'aw_placed aim: use goes to no actor; actor none box -1.0..-1.0, item -1.0, plant -1.0']
    raise AssertionError('no answer form for %s' % command)


def fake_run(journey, part, values, stop_in=None):
    """steps.log and console.log as the session runner and the game write them for one part; STOP_IN = the step whose
    first walker step stops the session (a wrong turn)."""
    steps, con = [], ['AmiWind boot', 'CharGenState 10 / FindSpymaster 0 / papers 0 / ring 0 / package 0']
    step = 0
    for line in next(p for p in journey['parts'] if p['name'] == part)['lines']:
        m = re.fullmatch(r'cmd echo JOURNEY STEP (\d+)', line)
        if m:
            step = int(m.group(1))
        if stop_in is not None and step == stop_in and line.split(' ', 1)[0] in js.WALKER_WORDS:
            steps.append('08:00:05 smoke RESULT FAIL %s: not reached in 25 s; the player stands at local 20 -30 79' % line)
            return '\n'.join(steps) + '\n', '\n'.join(con) + '\n'
        steps.append('08:00:00 ' + line)
        m = re.fullmatch(r'cmd echo JOURNEY (PROBE|STEP) (\S+)', line)
        if m:
            con.append('JOURNEY %s %s' % m.groups())
            if m.group(1) == 'PROBE':
                pr = journey['probes'][m.group(2)]
                if pr['kind'] == 'console':
                    con += answer(m.group(2), pr['command'], values[m.group(2)])
        elif line.startswith('state '):
            key = line.split()[1]
            probe = next((n for n, p in journey['probes'].items() if p['command'] == line and n in values
                          and steps[-2].endswith('PROBE ' + n)), None)
            steps.append('08:00:01 state %s: %s' % (key, values[probe] if probe else 'x'))
    steps.append('08:00:09 smoke RESULT PASS script')
    return '\n'.join(steps) + '\n', '\n'.join(con) + '\n'


class JourneySmoke(unittest.TestCase):
    def setUp(self):
        self.j = js.parse(JOURNEY.read_text(encoding='utf-8'))

    def runs(self, **changed):
        v = dict(GOOD, **changed)
        return [fake_run(self.j, p['name'], v) for p in self.j['parts']]

    def test_the_journey_parses_with_nine_steps_and_two_parts(self):
        self.assertEqual([s['step'] for s in self.j['steps']], list(range(1, 10)))
        self.assertEqual([p['name'] for p in self.j['parts']], ['A', 'B'])
        self.assertEqual(self.j['probes']['package_loaded']['part'], 'B')
        self.assertEqual(js.main(['check', str(JOURNEY)]), 0)

    def test_the_scripts_carry_the_markers_and_the_session_and_walker_words_only(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(js.write_scripts(JOURNEY, d), ['A', 'B'])
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
            b = (Path(d) / 'part-B.txt').read_text(encoding='utf-8').splitlines()
        self.assertIn('cmd echo JOURNEY PROBE victim', a)
        self.assertIn('cmd chim actors kill', a)
        # the game's own quicksave in part A, its Load game window in part B (JOURNEY-PART-B-SAVE-NOT-CARRIED-66)
        self.assertIn('cmd aw_quicksave', a)
        self.assertFalse([l for l in a + b if l.startswith(('cmd save ', 'cmd load '))])
        self.assertIn('waitfor screen 10 save', b)
        # the papers are taken by aiming at them, Sellus' duties chosen by name (JOURNEY-WALK-DIALOGUE-DESYNC-66)
        self.assertIn('aimed 172859', a)
        self.assertIn('topic duties', a)
        for line in a + b:
            if line and not line.startswith('#'):
                word = line.split(' ', 1)[0]
                self.assertTrue(word in js.SESSION_WORDS or word in js.WALKER_WORDS, line)
        self.assertTrue(any(l == 'cmd dbg all on' for l in a) and any(l == 'cmd dbg all on' for l in b))

    def test_a_good_run_passes_every_check(self):
        ok, lines = js.judge(self.j, self.runs())
        self.assertTrue(ok, '\n'.join(l for l in lines if l.startswith('FAIL')))
        self.assertRegex(lines[-1], r'^JOURNEY RESULT PASS (\d+)/\1 checks, 9 steps$')

    def test_the_dead_coming_back_after_a_room_fails_step_6(self):
        ok, lines = js.judge(self.j, self.runs(list_back='ALIVE'))
        self.assertFalse(ok)
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('step 6', bad[0])
        self.assertIn('the dead came back', bad[0])
        self.assertIn('steps 6)', lines[-1])

    def test_the_dead_missing_after_the_load_fails_step_8(self):
        ok, lines = js.judge(self.j, self.runs(list_loaded='GONE'))
        self.assertFalse(ok)
        self.assertTrue(any('step 8' in l and 'not in the actor list' in l for l in lines), lines)

    def test_a_reward_given_twice_fails_step_4(self):
        ok, lines = js.judge(self.j, self.runs(gold_again=174, gold_loaded=174))
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('FAIL step 4') and 'gold_again' in l for l in lines), lines)

    def test_a_taken_item_back_on_the_table_fails_step_3(self):
        ok, lines = js.judge(self.j, self.runs(table_back='BACK'))
        bad = [l for l in lines if l.startswith('FAIL step 3')]
        self.assertTrue(any('has table_back 119577 Iron Dagger' in l and 'not in the answer' in l for l in bad), lines)

    def test_a_take_that_did_not_happen_fails_step_2(self):
        # the dev2 crab meat: E went to the plate, the item's row stayed on
        ok, lines = js.judge(self.j, self.runs(dagger_taken='BACK'))
        self.assertTrue(any(l.startswith('FAIL step 2') and 'dagger_taken' in l for l in lines), lines)

    def test_a_lost_package_after_the_load_fails_step_8(self):
        ok, lines = js.judge(self.j, self.runs(package_loaded=0))
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('FAIL step 8') and 'package_loaded' in l for l in lines), lines)

    def test_a_session_stopped_at_a_wrong_turn_names_its_step_and_the_checks_not_reached(self):
        v = dict(GOOD)
        runs = [fake_run(self.j, 'A', v, stop_in=2), fake_run(self.j, 'B', v)]
        ok, lines = js.judge(self.j, runs)
        self.assertFalse(ok)
        # step 1 was played and passes; the checks from step 2 on in part A were never reached and say so
        self.assertTrue(all(l.startswith('PASS') for l in lines if l.startswith(('PASS step 1', 'FAIL step 1'))), lines)
        taken = next(l for l in lines if 'has dagger_taken' in l)
        self.assertTrue(taken.startswith('FAIL step 2'), taken)
        self.assertIn('not reached: part A stopped in step 2 (FAIL walkto 38 28 25: not reached in 25 s', taken)
        self.assertIn('STOP part A in step 2: FAIL walkto 38 28 25: not reached in 25 s; the player stands at local '
                      '20 -30 79', lines)
        self.assertTrue(lines[-1].startswith('JOURNEY RESULT FAIL') and lines[-1].endswith('; part A stopped in step 2'),
                        lines[-1])

    def test_a_stop_before_the_first_step_is_named_so(self):
        steps = '08:00:00 waitfor map 90 prison\n08:00:01 smoke RESULT FAIL waitfor map prison: read \'none\' after 90 s\n'
        self.assertEqual(js.session_stop(steps), (0, "FAIL waitfor map prison: read 'none' after 90 s"))
        self.assertIsNone(js.session_stop('08:00:00 cmd echo JOURNEY STEP 1\n08:00:09 smoke RESULT PASS script\n'))

    def test_a_later_part_that_stops_before_its_first_step_is_in_the_last_step_of_the_part_before(self):
        # the dev2 journey's part B stopped in the Load game window, before its step 9: it was still step 8
        v = dict(GOOD)
        b_steps = '08:00:00 key Escape\n08:00:01 smoke RESULT FAIL waitfor screen game: read \'save\' after 60 s\n'
        ok, lines = js.judge(self.j, [fake_run(self.j, 'A', v), (b_steps, '')])
        self.assertFalse(ok)
        self.assertIn("STOP part B in step 8: FAIL waitfor screen game: read 'save' after 60 s", lines)
        self.assertTrue(lines[-1].endswith('; part B stopped in step 8'), lines[-1])

    def test_an_unknown_item_id_is_named_not_guessed(self):
        runs = self.runs()
        steps, con = runs[0]
        # the dev2 image's console answer for an item no script names (CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66)
        con = con.replace('getitemcount ring_keley -> 1', 'getitemcount: no such item id: ring_keley')
        ok, lines = js.judge(self.j, [(steps, con), runs[1]])
        self.assertFalse(ok)
        self.assertTrue(any('ring_taken' in l and 'no such item id' in l for l in lines), lines)

    def test_a_run_is_judged_by_the_journey_it_played(self):
        # the run's scripts/journey.json, not the journey file as it is now
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            runs = self.runs()
            for name, (steps, con) in zip(('A', 'B'), runs):
                Path(d, name, 'logs').mkdir(parents=True)
                Path(d, name, 'logs', 'steps.log').write_text(steps, encoding='utf-8')
                Path(d, name, 'logs', 'console.log').write_text(con, encoding='utf-8')
            import contextlib
            import io
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = js.main(['judge', str(Path(d, 'journey.json')), str(Path(d, 'A')), str(Path(d, 'B'))])
        self.assertEqual(code, 0, out.getvalue())
        self.assertRegex(out.getvalue().splitlines()[-1], r'^JOURNEY RESULT PASS (\d+)/\1 checks, 9 steps$')

    def test_part_b_not_run_fails(self):
        ok, lines = js.judge(self.j, [self.runs()[0], None])
        self.assertFalse(ok)
        self.assertIn('parts not run: B', lines[-1])

    def test_the_walkthrough_lists_every_step_the_talk_and_the_restart(self):
        text = js.walkthrough(JOURNEY.read_text(encoding='utf-8'))
        for n in range(1, 10):
            self.assertIn('Step %d: ' % n, text)
        self.assertIn('type: chim actors kill', text)
        self.assertIn('check: dead victim in list_back', text)
        self.assertIn('talk: choose the topic "duties" in the dialogue window', text)
        self.assertLess(text.index('load its quicksave'), text.index('Step 9: '))
        self.assertGreater(text.index('load its quicksave'), text.index('Step 8: '))

    def test_bad_journeys_are_refused(self):
        for text, why in (('step 1 x\nexpect nope == 1\n', 'before it is defined'),
                          ('probe a cmd\nprobe a cmd\nexpect a == 1\n', 'twice'),
                          ('frobnicate\nprobe a x\nexpect a == 1\n', 'unknown word'),
                          ('cmd echo JOURNEY STEP 1\nprobe a x\nexpect a == 1\n', 'marker'),
                          ('walkto 47 100\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('face 1 2\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('aimed papers\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('probe a x\nexpect lacks b y\n', 'before it is defined'),
                          ('probe a x\n', 'no expect')):
            with self.assertRaises(js.JourneyError) as c:
                js.parse(text)
            self.assertIn(why, str(c.exception))


if __name__ == '__main__':
    unittest.main()
