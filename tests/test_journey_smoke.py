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
VICTIM = 128960   # step 6's fixed victim, Erene Llenim (DOOR-ARRIVAL-INSIDE-ACTOR-66)
FIGHTER_SOURCE = 128967   # step 7's fixed armed fighter, the Seyda Neen guard (JOURNEY-STEP7-FIGHTER-NEAREST-66)

# what a good run's game answers (the engine's own console forms: aw_mwhost.c, aw_mwconsole.c, aw_actors.c)
GOOD = {
    'fight_ship': 1, 'papers_before': 0, 'fight_before': 1, 'papers_after': 1, 'fight_after': 0, 'magic_after': 0,
    'dagger_before': 'BACK', 'dagger_taken': 'GONE', 'away_map': 'maps/sncourt-chim.chim', 'back_map': 'maps/census.bsp',
    'table_back': 'GONE', 'crab_before': 0, 'crab_after': 1, 'plate_ledger': 'CLEAN', 'ring_taken': 1,
    'gold_before': 0, 'talk_screen': 'dialogue', 'papers_sellus': 0, 'package_sellus': 1, 'directions_sellus': 1,
    'gold_sellus': 87, 'journal_sellus': 1, 'package_again': 1, 'gold_again': 87, 'journal_again': 1,
    'release_map': 'maps/seyda-chim.chim', 'state_released': -1, 'autosaves_released': 1,
    'victim': VICTIM, 'list_killed': 'DEAD', 'room_map': 'maps/census.bsp', 'court_map': 'maps/sncourt-chim.chim',
    'list_back': 'DEAD',
    'health_hurt': 40, 'health_healed': 90, 'cast_list': 1, 'fighter': 172002, 'list_fight': 'FIGHTING',
    'health_fought': 84, 'state_saved': -1, 'package_loaded': 1, 'gold_loaded': 87, 'ring_loaded': 1,
    'journal_loaded': 1, 'state_loaded': -1, 'list_loaded': 'DEAD', 'door_from': 'maps/seyda-chim.chim',
    'door_to': 'maps/census.bsp', 'package_door': 1, 'creatures_seyda': 4, 'saves_held': 3,
    'dock_walk': 'POST',
    # the fake game's map changes (fake_run): a map whose arrival writes no autosave, and where the autosave waits
    # behind the next map change instead (both None: every arrival from the release on writes one)
    'no_autosave_at': None,
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
    if command == 'chim actors kill %d' % VICTIM:
        # aw_actors.c's answer to a kill by reference
        return ['chim actors kill: Erene Llenim (ref %d) at 9.0 game hours' % v]
    if command == 'chim actors fight':
        return ['chim actors fight: Fargoth (ref %d, edict 70)' % v]
    if command == 'chim actors list':
        state = '' if v == 'ALIVE' else ' ' + v
        rows = [] if v == 'GONE' else ['  4 Erene Llenim ref %d cell 0 0 (outside) at -862 20 4%s' % (VICTIM, state)]
        return rows + [
                '  70 Fargoth ref 172002 cell -2 -9 at 140 210 30%s' % (' FIGHTING' if name == 'list_fight' else ''),
                'chim actors: 2 actors alive, 90 edicts; joins 1']
    if command == 'chim actors creatures on':
        # aw_actors.c: the switch's answer counts the creatures alive in the loaded area
        return ['Creatures on: %d alive, 0 released now, 0 spawns skipped while off (outdoor creatures; not saved)' % v]
    if command == 'aw_save_status':
        # aw_save.c save_status (SAVE-AUTOSAVE-REGRESSED-67): the autosaves of the character, what holds the next one
        # (V a text: what holds it, with one autosave kept)
        held, v = (v, 1) if isinstance(v, str) else ('nothing', v)
        return ['Autosave: on, 5 kept (aw_autosaves); character folder %s' % ('made' if v else 'not made yet'),
                'autosaves -> %d' % v,
                'Next autosave: at the next map change or in 296 s',
                'Held by: %s' % held,
                'Last save: %s' % ('Autosave 1 written (12698 bytes, generation 1)' if v else
                                   'refused: the items\' script values could not be kept')]
    if command == 'aw_intro_status':
        # aw_intro.c status and aw_opening.c AW_OpeningDockStatus (PIER-GUARD-POST-STUCK-67): at his post after the
        # fixed walk (POST), or stopped among the posts and pilings at the pier's end with his box in a solid (SOLID)
        dock = ('Dock guard at 286 -214 31 / leg 1 / route started 0 failed 0 done 1 / retries 0 / from the post 0 / '
                'box in solid 0 / waits 0 / route fixed' if v == 'POST' else
                'Dock guard at 371 -250 22 / leg 1 / route started 1 failed 0 done 0 / retries 0 / from the post 92 / '
                'box in solid 37 / waits 0 / route direct')
        return ['Intro active 0 / Jiub -1 / guard -1 / prompt 0 / unlocked 1 / failed 0',
                'Deck guard state 0 / nearby timer 0 ms', 'Opening 3 / dock -1 / census 0 / hall 0 / captain 0',
                'CharGenState 10 / FindSpymaster 0 / papers 0 / ring 0 / package 0', dock]
    if command == 'dbg cast spell list':
        return [' m0 Test spell (made) *', 'Selected: Test spell, cost 9, chance 100 %%; %d cast, 0 failed, 0 refused, %d landed' % (v, v)]
    if command == 'aw_placed ledger':
        # the theft ledger (aw_placed.c): the plate named when it was stolen instead of the crab meat taken
        return (['aw_placed ledger: 1 stolen, 0 drops', '  stolen misc_imp_silverware_plate_01 from a shady smuggler: 1']
                if v == 'PLATE' else ['aw_placed ledger: 0 stolen, 0 drops'])
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
        # the game's own lines of a map change (aw_scene.c, aw_save.c): every arrival says Scene ready; from the release
        # (step 5) on each one writes an autosave, but at NO_AUTOSAVE_AT; part B's load of the quicksave is restored
        m = re.fullmatch(r'waitfor (?:map|server) \d+ (\S+)', line)
        if m:
            con.append('Scene ready: %s, 912 ms, 2210304 hunk bytes, arrival checked' % m.group(1))
            if step >= 5 and m.group(1) != values.get('no_autosave_at'):
                con.append('Saved Autosave %d (12698 bytes, generation %d).' % (len(con), len(con)))
        elif line == 'waitfor screen 60 game':
            con += ['Scene ready: seyda, 1410 ms, 2210304 hunk bytes, arrival checked', 'Game restored: Hors.']
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

    def test_an_emu_line_goes_into_the_parts_script(self):
        # an emulator option for a part's session (CHIM-SEYDA-BALMORA-LOAD-HANG-43: emu deterministic=1), passed as it
        # stands for tools/engine_smoke.py to take; an unknown word is still refused
        j = js.parse('part A\nemu deterministic=1\nstep 1 one\nprobe x cmd getpos x\nexpect x == 1\n')
        self.assertIn('emu deterministic=1', j['parts'][0]['lines'])
        with self.assertRaises(js.JourneyError):
            js.parse('part A\nemux deterministic=1\nstep 1 one\nprobe x cmd getpos x\nexpect x == 1\n')

    def test_the_scripts_carry_the_markers_and_the_session_and_walker_words_only(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(js.write_scripts(JOURNEY, d), ['A', 'B'])
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
            b = (Path(d) / 'part-B.txt').read_text(encoding='utf-8').splitlines()
        self.assertIn('cmd echo JOURNEY PROBE victim', a)
        self.assertIn('cmd chim actors kill %d' % VICTIM, a)
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

    def test_god_mode_is_on_for_the_kill_only_and_off_before_the_hurt_and_heal(self):
        # the v0.0.66-dev4 journey retry: god mode, on from the kill, held step 7's hurt, heal and fight at one health
        # (920 against 920); it blocks every kind of damage, the console's modcurrenthealth included
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
        kill = a.index('cmd chim actors kill %d' % VICTIM)
        hurt = a.index('cmd player->modcurrenthealth -60')
        god = [(i, l) for i, l in enumerate(a) if l.startswith('cmd dbg god ')]
        before = [l for i, l in god if i < kill]
        between = [l for i, l in god if kill < i < hurt]
        self.assertEqual(before[-1:], ['cmd dbg god on'], god)
        self.assertEqual(between, ['cmd dbg god off'], god)
        # right after the kill: the next line past the probe's own wait
        self.assertEqual(next(l for l in a[kill + 1:] if not l.startswith('wait ')), 'cmd dbg god off',
                         a[kill - 2:kill + 4])

    def test_step_6_kills_a_fixed_resident_away_from_the_door_then_walks_through_it_and_back(self):
        # DOOR-ARRIVAL-INSIDE-ACTOR-66: a plain "chim actors kill" takes the nearest resident; in the v0.0.66-dev6 and
        # dev8 journeys that was the guard (128967) by the census office's street door, whose body then took the use
        # key in front of it. The victim is now named by reference: Erene Llenim, who stays by his shack in the west.
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
            b = (Path(d) / 'part-B.txt').read_text(encoding='utf-8').splitlines()
        kills = [l for l in a + b if l.startswith('cmd chim actors kill')]
        self.assertEqual(kills, ['cmd chim actors kill 128960'])
        kill = a.index(kills[0])
        # after it, unchanged: into the captain's room by the street door, and out again by the exit door
        door = a.index('aimed 113833', kill)
        self.assertEqual(a[door - 1:door + 3], ['face 242.6 10.3 61', 'aimed 113833', 'key e', 'waitfor map 45 census'])
        out = a.index('aimed 119659', door)
        self.assertEqual(a[out - 1:out + 3], ['face 292.7 -186 71', 'aimed 119659', 'key e', 'waitfor server 45 seyda'])
        # a kill that finds nobody fails step 6 and says why
        runs = self.runs()
        steps, con = runs[0]
        con = con.replace('chim actors kill: Erene Llenim (ref %d) at 9.0 game hours' % VICTIM,
                          'chim actors kill: no living actor of reference %d here' % VICTIM)
        ok, lines = js.judge(self.j, [(steps, con), runs[1]])
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('FAIL step 6') and 'no living actor' in l for l in lines), lines)

    def test_the_fighter_is_put_at_the_players_feet_before_the_fight(self):
        # JOURNEY-STEP7-FIGHT-UNREACHABLE-66 (the v0.0.66-dev5 journey): the nearest resident was the hall guard inside the
        # census office ("Combat: Guard cannot reach you and flees"), so no hit landed; the copy at the player's feet is
        # made after the seed and before the fight command
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
        seed = a.index('cmd dbg combat seed 7')
        summon = a.index('cmd chim actors summon %d' % FIGHTER_SOURCE)
        fight = a.index('cmd chim actors fight')
        self.assertLess(seed, summon)
        self.assertLess(summon, fight)

    def test_step_7_summons_a_fixed_armed_resident_by_reference(self):
        # JOURNEY-STEP7-FIGHTER-NEAREST-66: a plain "chim actors summon" copies the nearest resident, which was Fargoth
        # (unarmed: misses and fatigue damage only) on the v0.0.66-dev9 and dev10 images, so the health check failed by
        # chance; step 7 names the Seyda Neen guard (128967, armed) by reference, as step 6 names its victim
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
            b = (Path(d) / 'part-B.txt').read_text(encoding='utf-8').splitlines()
        summons = [l for l in a + b if l.startswith('cmd chim actors summon')]
        self.assertEqual(summons, ['cmd chim actors summon 128967'])
        self.assertEqual(FIGHTER_SOURCE, 128967)
        # the rest of step 7 is as it was: the hurt, the heal, then the summon, the fight and the health check
        self.assertLess(a.index('cmd dbg cast now'), a.index(summons[0]))
        self.assertLess(a.index('cmd chim actors fight'), a.index('cmd echo JOURNEY PROBE health_fought'))
        # a run whose fight lands no hit still fails step 7
        ok, lines = js.judge(self.j, self.runs(health_fought=90))
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('FAIL step 7') for l in lines), lines)

    def test_step_9_walks_to_the_door_before_it_aims(self):
        # JOURNEY-STEP9-REACH-67 (the v0.0.67-dev2 journey): the quicksave held the player where step 7's dodges left it,
        # 48.6 units along the aim from the census street door's point, past the use reach of 48, and part B aimed from
        # there. Step 9 now walks to the door's arrival point first, then turns, aims and uses it; the aim, its retries and
        # the reach are those of every other door (no step widens them)
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            b = (Path(d) / 'part-B.txt').read_text(encoding='utf-8').splitlines()
        step = b.index('cmd echo JOURNEY STEP 9')
        door = b.index('aimed 113833', step)
        self.assertEqual(b[door - 2:door + 3], ['walkto 264 34 20', 'face 242.6 10.3 61', 'aimed 113833', 'key e',
                                                'waitfor map 45 census'])
        # the walk comes after the door_from probe, so that probe still reads the map the restored game stands in
        self.assertLess(b.index('cmd echo JOURNEY PROBE door_from', step), b.index('walkto 264 34 20', step))
        # one aim at the door, as part A's: no extra time or other form of the aim in part B
        self.assertEqual([l for l in b if l.startswith('aimed ')], ['aimed 113833'])
        # a walk that does not reach the arrival point (step 9's first walker step) stops step 9 and names it
        runs = self.runs()
        ok, lines = js.judge(self.j, [runs[0], fake_run(self.j, 'B', dict(GOOD), stop_in=9)])
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('STOP part B in step 9') and 'walkto 264 34 20' in l for l in lines), lines)

    def test_a_good_run_passes_every_check(self):
        ok, lines = js.judge(self.j, self.runs())
        self.assertTrue(ok, '\n'.join(l for l in lines if l.startswith('FAIL')))
        self.assertRegex(lines[-1], r'^JOURNEY RESULT PASS (\d+)/\1 checks, 9 steps$')

    def test_the_dock_guard_stuck_among_the_pier_posts_fails_step_1(self):
        """PIER-GUARD-POST-STUCK-67: after the race form the player stays on the pier for the dock guard's whole walk,
        then aw_intro_status: done at his post, his box never inside a solid, the fixed route."""
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
        probe = a.index('cmd echo JOURNEY PROBE dock_walk')
        self.assertEqual(a[probe + 1], 'cmd aw_intro_status')
        race = a.index('waitfor screen 20 game')
        self.assertLess(race, probe)
        self.assertEqual([l for l in a[race:probe] if not l.startswith('wait ')], ['waitfor screen 20 game'],
                         'the player moves before the guard has walked')
        self.assertGreaterEqual(sum(int(l.split()[1]) for l in a[race + 1:probe] if l.startswith('wait ')), 45)
        ok, lines = js.judge(self.j, self.runs(dock_walk='SOLID'))
        self.assertFalse(ok)
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertEqual(len(bad), 4, lines)
        self.assertTrue(all('step 1' in l for l in bad), bad)
        self.assertTrue(any('dock_in_solid' in l for l in bad), bad)

    def test_the_crab_meat_step_checks_the_crab_meat_taken_and_the_plate_left(self):
        # CENSUS-CRAB-PLATE-FOCUS-66: aimed at the crab meat, the use key takes it, never the plate under it
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
        self.assertIn('aimed 454283', a)
        self.assertLess(a.index('aimed 454283'), a.index('cmd echo JOURNEY PROBE crab_after'))
        self.assertIn('cmd player->getitemcount ingred_crab_meat_01', a)
        ok, lines = js.judge(self.j, self.runs(crab_after=0))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('step 2', bad[0])
        ok, lines = js.judge(self.j, self.runs(plate_ledger='PLATE'))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('step 2', bad[0])
        self.assertIn('plate_ledger', bad[0])

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

    def test_no_autosave_after_the_release_fails_step_5(self):
        # SAVE-AUTOSAVE-REGRESSED-67: the release's map change must leave the game's own autosave on disk; the journey
        # asks dbg save status after it, and a game that wrote none fails step 5 with the status's answer in the line
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            a = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()
        self.assertLess(a.index('shot a6-released'), a.index('cmd echo JOURNEY PROBE autosaves_released'))
        self.assertEqual(a[a.index('cmd echo JOURNEY PROBE autosaves_released') + 1], 'cmd aw_save_status')
        ok, lines = js.judge(self.j, self.runs(autosaves_released=0))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('step 5', bad[0])
        self.assertIn('autosaves_released', bad[0])

    def test_a_map_change_without_its_autosave_fails_and_is_named(self):
        """ENGINE-REGRESSION-GUARDS-67: from the release on every map change writes the game's autosave; a map change
        without one fails the journey's last step and names the map and the part. The load of the quicksave (part B)
        and the map changes before the release are none; at the end nothing holds the autosave back."""
        e = [x for x in self.j['expects'] if x['kind'] == 'autosaves']
        self.assertEqual([(x['from'], x['step']) for x in e], [(5, 9)])
        self.assertEqual(js.autosave_misses(self.j, {'A': self.runs()[0][1], 'B': self.runs()[1][1]}, 5), (6, []))
        ok, lines = js.judge(self.j, self.runs(no_autosave_at='sncourt'))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1, lines)
        self.assertEqual(bad[0], 'FAIL step 9 (through a door: the restored game goes on): autosaves from step 5: 1 of 6 '
                                 'map changes wrote no autosave: sncourt (part A, the next map loaded first)')
        # the last map change of a part: before the part ended
        ok, lines = js.judge(self.j, self.runs(no_autosave_at='census'))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertIn('3 of 6 map changes wrote no autosave: census (part A, the next map loaded first); census (part A, '
                      'the next map loaded first); census (part B, before the part ended)', bad[0])
        # the arrivals before the release write none, and no map change of theirs is judged
        a = self.runs()[0][1]
        before = a[:a.index('JOURNEY STEP 5')]
        self.assertIn('Scene ready: sncourt', before)
        self.assertNotIn('Saved Autosave', before)
        # a streamed crossing is no map change; a load of a save is none either
        con = ('JOURNEY STEP 5\nScene ready: vf0877, 0 ms, streamed crossing (type 1), CHIM frame 3 4, 812 us\n'
               'Scene ready: seyda, 1410 ms, 2210304 hunk bytes, arrival checked\nGame restored: Hors.\n'
               'Scene ready: census, 912 ms, 2210304 hunk bytes, arrival checked\nSaved Autosave 2 (1 bytes, generation 2).\n')
        self.assertEqual(js.autosave_misses(self.j, {'A': con}, 5), (1, []))
        # something holds the autosave back at the end
        ok, lines = js.judge(self.j, self.runs(saves_held='a fight'))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('has saves_held Held by: nothing: not in the answer', bad[0])
        self.assertIn('Held by: a fight', bad[0])

    def test_no_creature_alive_in_seyda_neen_fails_step_5(self):
        # ENGINE-REGRESSION-GUARDS-67 (OUTDOOR-CREATURES-MISSING-66): the town is outdoors, its creatures are alive
        ok, lines = js.judge(self.j, self.runs(creatures_seyda=0))
        bad = [l for l in lines if l.startswith('FAIL')]
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1, lines)
        self.assertIn('step 5', bad[0])
        self.assertIn('creatures_alive >= 1', bad[0])

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

    def test_a_warp_run_says_so_on_its_result_line(self):
        """Decided 17 November 2026: warp is off for every performance and bench test. A journey whose sessions ran in
        the emulator's warp mode (the session's own result line ends with the mark) still checks the game's state, and
        its result line ends with the same mark, PASS or FAIL alike; a stop reason is read without it."""
        import engine_smoke
        self.assertEqual(js.WARP_MARK, engine_smoke.WARP_MARK)
        runs = self.runs()
        ok, lines = js.judge(self.j, runs)
        self.assertTrue(ok)
        self.assertFalse(lines[-1].endswith(js.WARP_MARK))
        warp = [(s.replace('smoke RESULT PASS script', 'smoke RESULT PASS script' + js.WARP_MARK), c) for s, c in runs]
        ok, lines = js.judge(self.j, warp)
        self.assertTrue(ok)
        self.assertRegex(lines[-1], r'^JOURNEY RESULT PASS (\d+)/\1 checks, 9 steps \[warp run: no timing verdict\]$')
        # a stopped warp part: FAIL, the mark once at the end, and the stop's reason without it
        v = dict(GOOD)
        stopped = [fake_run(self.j, 'A', v, stop_in=3), fake_run(self.j, 'B', v)]
        stopped = [(s.replace('25 s; the player stands at local 20 -30 79',
                              '25 s; the player stands at local 20 -30 79' + js.WARP_MARK), c) for s, c in stopped]
        ok, lines = js.judge(self.j, stopped)
        self.assertFalse(ok)
        self.assertTrue(lines[-1].startswith('JOURNEY RESULT FAIL') and lines[-1].endswith(js.WARP_MARK))
        self.assertEqual(lines[-1].count(js.WARP_MARK), 1)
        stop = [l for l in lines if l.startswith('STOP part A')]
        self.assertTrue(stop and js.WARP_MARK not in stop[0], stop)

    def test_until_steps_take_their_forms(self):
        """ACCELERATED-PLAYTHROUGH-66 step 1: waits by condition (tools/engine_smoke.py UNTIL-STEPS) pass into the parts'
        scripts as written; a wrong form is refused with the step's name."""
        head = 'part A\nstep 1 x\nprobe a getjournalindex A1_1_FindSpymaster\nexpect a == 1\n'
        for good in ('until map census 45', 'until screen game 10', 'until server seyda 60', 'until loaded 60',
                     'until journal A1_1_FindSpymaster 1 30', 'until journal A1_1_FindSpymaster -1 5',
                     'until map seyda-chim.chim 30'):
            j = js.parse(head + good + '\n')
            self.assertIn(good, j['parts'][0]['lines'], good)
        for bad in ('until loaded', 'until map census', 'until journal A1_1_FindSpymaster 30', 'until fly 3',
                    'until loaded soon', 'until journal A1 1 x'):
            with self.assertRaises(js.JourneyError, msg=bad) as e:
                js.parse(head + bad + '\n')
            self.assertIn("until", str(e.exception))

    def test_the_opening_waits_for_its_loads_by_condition(self):
        """ACCELERATED-PLAYTHROUGH-66 step 1: no fixed wait follows a map change in the opening journey: each waitfor map
        or server is followed by until loaded, and Sellus Gravius' journal entry is waited for by its index."""
        lines = [l.strip() for l in JOURNEY.read_text(encoding='utf-8').splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        changes = [i for i, l in enumerate(lines) if re.match(r'waitfor (map|server) ', l)]
        for i in changes:
            self.assertFalse(lines[i + 1].startswith('wait '), 'a fixed wait after %r' % lines[i])
        self.assertGreaterEqual(sum(lines[i + 1] == 'until loaded 60' for i in changes), 10)
        self.assertIn('until journal A1_1_FindSpymaster 1 15', lines)

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

    def test_pick_reads_a_number_after_or_before_a_text_of_an_earlier_answer(self):
        # ENDGAME-HEART-SESSION-66: the counts of a long status answer; the not-yet list names the same words with other
        # numbers, so the text is matched as given (case and the "; " before PlayGroup)
        text = ('step 1 counts\nprobe s aw_mwscript_status\npick plays s after ; PlayGroup\npick seen s before matched\n'
                'pick none s after no such words\nexpect plays == 5\nexpect seen == 6\nexpect none == 1\n')
        j = js.parse(text)
        self.assertEqual(j['probes']['plays']['kind'], 'pick')
        self.assertEqual(j['parts'][0]['lines'], ['cmd echo JOURNEY STEP 1', 'cmd echo JOURNEY PROBE s',
                                                  'cmd aw_mwscript_status', 'wait %d' % js.PROBE_WAIT])
        con = ('JOURNEY STEP 1\nJOURNEY PROBE s\nnot yet, most called: HitOnMe 900 PlayGroup 7\n'
               'HitOnMe: 6 weapon blows kept, 0 by NPCs not kept; 1800 reads, 6 matched\n'
               'player standing: crime level 0, reputation 0; calls 4 (0 not carried out); PlayGroup 5 (2 with no '
               'skeletal actor or group)\n')
        ok, lines = js.judge(j, [('08:00:00 cmd echo JOURNEY STEP 1\n08:00:09 smoke RESULT PASS script\n', con)])
        self.assertTrue(lines[0].startswith('PASS') and lines[1].startswith('PASS'), lines)
        self.assertTrue(lines[2].startswith('FAIL') and 'no number' in lines[2], lines)
        self.assertEqual(js.pick_number(['a 12 matched'], 'before', 'matched'), 12.0)
        self.assertEqual(js.pick_number(['ShowVars: script 811, 5 locals'], 'after', 'ShowVars: script'), 811.0)
        self.assertIsNone(js.pick_number(['nothing'], 'after', 'x'))

    def test_alive_fighting_and_dead_take_a_reference_number(self):
        text = ('step 1 actors\nprobe l chim actors list\nexpect alive 197602 in l\nexpect fighting 262014 in l\n'
                'expect dead 234367 in l\nexpect alive 5 in l\n')
        con = ('JOURNEY STEP 1\nJOURNEY PROBE l\n  10 Heart of Lorkhan ref 197602 cell 0 0 (outside) at 0 0 0\n'
               '  11 Dagoth Ur ref 262014 cell 0 0 (outside) at 0 0 0 FIGHTING\n'
               '  12 Dreamer ref 234367 cell 0 0 (outside) at 0 0 0 DEAD\n')
        ok, lines = js.judge(js.parse(text), [('08:00:09 smoke RESULT PASS script\n', con)])
        self.assertEqual([l.split()[0] for l in lines[:4]], ['PASS', 'PASS', 'PASS', 'FAIL'], lines)
        self.assertIn('reference 5 is not in the actor list', lines[3])
        con2 = con.replace(' FIGHTING', '').replace(' DEAD\n', '\n')
        ok, lines = js.judge(js.parse(text), [('08:00:09 smoke RESULT PASS script\n', con2)])
        self.assertIn('reference 262014 is alive, not fighting', lines[1])
        self.assertIn('reference 234367 is alive, not dead', lines[2])

    def test_a_known_gap_is_reported_and_not_counted(self):
        text = 'step 1 the end\nprobe a x\nprobe b y\nexpect a == 1\nexpect known ENDGAME-CHAMBER-COLLAPSE-63 b == 2\n'
        j = js.parse(text)
        self.assertEqual(j['expects'][1]['known'], 'ENDGAME-CHAMBER-COLLAPSE-63')
        run = lambda b: [('08:00:09 smoke RESULT PASS script\n',
                          'JOURNEY STEP 1\nJOURNEY PROBE a\nx -> 1\nJOURNEY PROBE b\ny -> %d\n' % b)]
        ok, lines = js.judge(j, run(0))
        self.assertTrue(ok, lines)
        self.assertTrue(lines[1].startswith('KNOWN step 1') and lines[1].endswith('[known gap ENDGAME-CHAMBER-COLLAPSE-63]'),
                        lines)
        self.assertEqual(lines[-1], 'JOURNEY RESULT PASS 1/1 checks, 1 steps; known gaps: 1 of 1 checks still failing '
                                    '(ENDGAME-CHAMBER-COLLAPSE-63)')
        ok, lines = js.judge(j, run(2))
        self.assertIn('passes now, check the register', lines[1])
        self.assertTrue(lines[-1].endswith('closed now: ENDGAME-CHAMBER-COLLAPSE-63'), lines[-1])

    def test_bad_journeys_are_refused(self):
        for text, why in (('pick a b after x\nprobe c x\nexpect c == 1\n', 'before it is defined'),
                          ('probe a x\npick a a after y\nexpect a == 1\n', 'twice'),
                          ('probe a x\npick b a near y\nexpect a == 1\n', 'pick NAME PROBE after|before TEXT'),
                          ('probe a x\nexpect known a == 1\n', 'expect known REGISTER-ID'),
                          ('probe a x\nexpect alive 12 in nolist\n', 'before it is defined'),
                          ('step 1 x\nexpect nope == 1\n', 'before it is defined'),
                          ('probe a cmd\nprobe a cmd\nexpect a == 1\n', 'twice'),
                          ('frobnicate\nprobe a x\nexpect a == 1\n', 'unknown word'),
                          ('cmd echo JOURNEY STEP 1\nprobe a x\nexpect a == 1\n', 'marker'),
                          ('walkto 47 100\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('face 1 2\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('aimed papers\nprobe a x\nexpect a == 1\n', "not the walker step's form"),
                          ('probe a x\nexpect lacks b y\n', 'before it is defined'),
                          ('step 1 x\nexpect autosaves from step 2\n', 'no step 2 before it'),
                          ('step 1 x\nexpect autosaves since 1\n', 'expect autosaves from step N'),
                          ('probe a x\n', 'no expect')):
            with self.assertRaises(js.JourneyError) as c:
                js.parse(text)
            self.assertIn(why, str(c.exception))


if __name__ == '__main__':
    unittest.main()
