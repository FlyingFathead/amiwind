# SPDX-License-Identifier: GPL-3.0-only
"""tests/sessions/endgame_heart.txt (ENDGAME-HEART-SESSION-66): the end of the main quest played with a test character,
judged by tools/journey_smoke.py from the game's own answers. A good run passes with the gaps the first two runs
measured reported as known (the collapse, three console reads, another object's local read through the wrong script,
a health set to 0 that never kills); a strike the Heart's script did not take, Wraithguard not protecting, an end
script that never starts, Dagoth Ur killed before the Heart, Azura's spirit never hidden or never shown, no ending
video and a chamber that does not load fail, each naming its step. The session's order is checked as the original
asks it: the Facility Cavern before stage 20, Sunder strikes first, five Keening strikes after it, god mode held for
the fight, Dagoth Ur fought rather than killed by reference."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import journey_smoke as js  # noqa: E402

JOURNEY = ROOT / 'tests' / 'sessions' / 'endgame_heart.txt'
HEART, DAGOTH, DAGOTH_FIRST, WORKERS = 197602, 262014, 258093, (234367, 234368, 234371)


def status(matched, plays, misses=0, weather=0, off='teleporting', moved=1, binks=0):
    """aw_mwscript_status as aw_mwhost.c prints it (the lines the session reads, and the ones that must not mislead a
    pick: the not-yet list names hitonme, playgroup and positioncell with their call counts)."""
    return ['MWScript on: 8618 scripts, 1892184 bytes kept; map rifa4ef181ed: 9 objects',
            'not yet, most called: hitonme 900 playgroup %d positioncell 7; player cell 0 0 0' % (plays + misses),
            'carried item scripts: 4 started, 0 stopped, 2 inventory checks; levelled actors\' scripts: 0 attached, 0 '
            'refused; PlayBink %d played, 0 absent' % binks,
            'HitOnMe: %d weapon blows kept (0 of 8 rows held, 64 bytes), 3 by NPCs not kept; 1800 reads, %d matched'
            % (matched, matched),
            'region weather by scripts: %d ChangeWeather and ModRegion calls kept, 0 refused (24 bytes)' % weather,
            'player standing: crime level 0, reputation 0; calls 4 (0 not carried out); PlayGroup %d (%d with no '
            'skeletal actor or group); topics added 0' % (plays, misses),
            'PositionCell: %d moved here, 0 to another place, 0 not possible; arrivals spawned 0 (0 with no entity to '
            'spawn); 0 leaving' % moved,
            'Control switches: 3 calls (0 not kept); off now: %s; a new game\'s carried switches set 1 times' % off]


def actors(states):
    return ['  %d %s ref %d cell 0 0 (outside) at 0 0 0%s' % (i, 'Actor', ref, '' if st == 'ALIVE' else ' ' + st)
            for i, (ref, st) in enumerate(sorted(states.items()), 10)] + ['chim actors: %d actors alive' % len(states)]


def world(dagoth='FIGHTING', workers='ALIVE', heart='FIGHTING'):
    s = {HEART: heart, DAGOTH: dagoth}
    s.update({w: workers for w in WORKERS})
    return s


# a good run: the game's state at each probe (the engine's own console forms are built by answer()); the reads that
# are known gaps answer as runs 1 and 2 on the v0.0.66-dev10 image measured them: keening_count "no such item id",
# wraith_console 0, dagoth_y -0.43, ShowVars on the console's own instance (row 0), Dagoth Ur's shield held at the
# count-0 one, the dreamer workers and Dagoth Ur at health 0 still alive, the collapse finding no skeletal actor
GOOD = {
    'fight_on': 0, 'strength': 100, 'blunt': 100, 'shortblade': 100,
    'sunder_given': 'Sunder', 'keening_given': 'Keening', 'wraith_given': 'Wraithguard',
    'sunder_count': 1, 'keening_count': None, 'wraith_count': 1, 'wraith_console': 0, 'wraith_worn': 1,
    'worn': 'sunder', 'tools_journal': 15, 'health_armed': 920, 'health_wraith': 920,
    'quest_set': 10, 'heart_gone_before': 0, 'blight_before': 0, 'standing_before': 0,
    'dagoth_first': DAGOTH_FIRST, 'list_cavern': {DAGOTH_FIRST: 'DEAD'}, 'spirit_hidden': 1, 'ring_hidden': 1,
    'chamber_map': 'maps/rifa4ef181ed.chim', 'chamber_memory': 1943, 'list_arrival': world(heart='ALIVE'),
    'status_arrival': status(0, 0, moved=0),
    'stand': (0, 946, -45), 'heart_distance': 96, 'heart_fight': HEART, 'list_near': world(),
    'dagoth_y': -0.428955, 'dagoth_held': 1000, 'shield_first': 1, 'status_near': status(0, 0),
    'heart_before': 0, 'aim_sunder': HEART, 'heart_sunder': 1, 'heart_vars': 0,
    'status_k1': status(2, 1), 'shield_k1': 0, 'shield_one_k1': 1, 'status_k2': status(3, 2), 'shield_k2': 0,
    'status_k3': status(4, 3), 'shield_k3': 0, 'status_k4': status(5, 4), 'shield_k4': 0, 'heart_gone_k4': 0,
    'heart_gone': 1, 'status_k5': status(6, 5),
    'dagoth_capped': 200, 'worker_health': 0, 'list_destroyed': world(), 'status_struck': status(6, 5),
    'blight_end': -1, 'quest_end': 20, 'dagoth_end': 0, 'list_end': world(),
    'standing_end': 10, 'status_end': status(6, 5, misses=2, weather=2, off='none'),
    'status_before_end': status(6, 5, misses=2, weather=2, off='none'), 'spirit_shown': 0, 'controls_taken': 1,
    'quest_final': 50, 'sleepers_final': 50, 'ring_final': 0, 'controls_final': 0, 'spirit_gone': 1,
    'status_final': status(6, 5, misses=2, weather=2, off='none', binks=1),
}


def answer(name, command, v):
    if command.startswith('player->getitemcount'):
        item = command.split(' ', 1)[1]
        # an item outside the actor table's item list (CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66): None
        return ['getitemcount: no such item id: %s' % item] if v is None else ['getitemcount %s -> %d' % (item, v)]
    if command.startswith('dbg give '):
        # aw_inventory.c give_command's answer (None: a grant refused)
        if v is None:
            return ['Usage: dbg give [ID [N] / money [N]]']
        return ['DIAGNOSTIC %s added to your inventory. Now 1 carried (%s).' % (v, command.split()[-1])]
    if re.fullmatch(r'(\w+|"[^"]+")->get\w+( \w+)?', command) and command.split('->')[1].split()[0] in (
            'getstrength', 'getbluntweapon', 'getshortblade', 'gethealth', 'getspell', 'getdistance', 'getdisabled'):
        return ['%s -> %g' % (command.split('->')[1].split()[0], v)]
    if command == 'dagoth_ur_2->getpos y':
        return ['getpos Y -> %g' % v]
    if re.match(r'aw_mwscript_status call get\w+disabled$', command):
        f = command.split()[-1]
        return ['dbg mwscript call %s: done, reads %d (%s); switches off now: mask 0' % (f, v, 'off' if v else 'on')]
    if command.startswith('aw_mwscript_status call getglobal'):
        return ['dbg mwscript call getglobal: %s = %g (data start changed)' % (command.split()[-1], v)]
    if command.startswith('aw_mwscript_status call journal') or command.startswith('getjournalindex'):
        quest = command.split()[3] if command.startswith('aw_mwscript_status') else command.split()[1]
        return ['dbg mwscript call journal: %s %d' % (quest, v)]
    if command == 'aw_mwscript_status call getpccrimelevel':
        return ['dbg mwscript call getpccrimelevel: carried out, answer 0 (0.0); crime level 0, reputation %d, topics '
                'known 40' % v]
    if command == 'aw_mwscript_status call getlocal %d' % HEART:
        # the row of LorkhanHeart in the v0.0.66-dev10 image's script file (run1)
        return ['dbg mwscript call getlocal: ref %d script LorkhanHeart (row 319, 5 locals), local 0 = %d (%g)'
                % (HEART, v, v * 1.4e-45)]
    if command == 'heart_akulakhan->sv':
        # the console's ShowVars on a reference (aw_mwhost.c console_group_call): the script row it shows
        return ['ShowVars: script %d, 5 locals' % v, '  local 0 = 1 / 1.4013e-45', '  local 2 = 0 / 0']
    if command == 'aw_inventory worn':
        return ['  worn slot 7: wraithguard', '  right hand: %s' % v, '  left hand: -']
    if command == 'aw_mwscript_status':
        return v
    if command == 'chim actors list':
        return actors(v)
    if command == 'chim actors fight':
        return ['chim actors fight: Heart of Lorkhan (ref %d, edict 40)' % v]
    if command == 'chim actors kill %d' % DAGOTH_FIRST:
        return ['chim actors kill: Dagoth Ur (ref %d) at 9.0 game hours' % v]
    if command == 'dbg unstuck':
        return ['Unstuck: %d %d %d' % v]
    if command == 'dbg memcensus':
        return ['Memory now %d KiB free, largest block 2300 KiB; map rifa4ef181ed' % v]
    if command == 'aw_inspect':
        return ['class/name: aw_npc / Heart of Lorkhan', 'source id: heart_akulakhan', 'source ref: %d' % v]
    raise AssertionError('no answer form for %s' % command)


def fake_run(journey, values, stop_in=None, stop_line=None):
    """steps.log and console.log of the one part; STOP_IN: the step whose STOP_LINE (a walker step) stops the session."""
    steps, con, step = [], ['AmiWind boot'], 0
    for line in journey['parts'][0]['lines']:
        m = re.fullmatch(r'cmd echo JOURNEY STEP (\d+)', line)
        if m:
            step = int(m.group(1))
        if stop_in is not None and step == stop_in and line == stop_line:
            steps.append("08:00:05 smoke RESULT FAIL %s: read 'maps/seyda-chim.chim' after 150 s" % line)
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
            probe = next(n for n, p in journey['probes'].items() if p['command'] == line and steps[-2].endswith('PROBE ' + n))
            steps.append('08:00:01 state %s: %s' % (line.split()[1], values[probe]))
    steps.append('08:00:09 smoke RESULT PASS script')
    return '\n'.join(steps) + '\n', '\n'.join(con) + '\n'


class EndgameHeart(unittest.TestCase):
    def setUp(self):
        self.j = js.parse(JOURNEY.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as d:
            js.write_scripts(JOURNEY, d)
            self.lines = (Path(d) / 'part-A.txt').read_text(encoding='utf-8').splitlines()

    def judge(self, **changed):
        return js.judge(self.j, [fake_run(self.j, dict(GOOD, **changed))])

    def failing(self, lines):
        return [l for l in lines if l.startswith('FAIL')]

    KNOWN = {'ENDGAME-CHAMBER-COLLAPSE-63', 'CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66', 'CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66',
             'CONSOLE-GETPOS-SCRATCH-ORIGIN-66', 'CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66',
             'MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66', 'MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66'}
    ALL_KNOWN = ('CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66, CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66, CONSOLE-GETPOS-SCRATCH-ORIGIN-66, '
                 'CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66, ENDGAME-CHAMBER-COLLAPSE-63, MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66, '
                 'MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66')

    def test_one_part_nine_steps_and_the_known_gaps_are_registered_entries(self):
        self.assertEqual([s['step'] for s in self.j['steps']], list(range(1, 10)))
        self.assertEqual([p['name'] for p in self.j['parts']], ['A'])
        self.assertEqual(js.main(['check', str(JOURNEY)]), 0)
        known = {e['known'] for e in self.j['expects'] if e.get('known')}
        self.assertEqual(known, self.KNOWN)
        register = {b['id'] for b in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        self.assertLessEqual(known, register)
        for line in self.lines:
            if line and not line.startswith('#'):
                word = line.split(' ', 1)[0]
                self.assertTrue(word in js.SESSION_WORDS or word in js.WALKER_WORDS, line)

    def test_a_good_run_passes_with_the_known_gaps_reported(self):
        ok, lines = self.judge()
        self.assertTrue(ok, '\n'.join(self.failing(lines)))
        self.assertRegex(lines[-1], r'^JOURNEY RESULT PASS (\d+)/\1 checks, 9 steps; known gaps: 14 of 14 checks still '
                                    r'failing \(%s\)$' % re.escape(self.ALL_KNOWN))
        known = [l for l in lines if l.startswith('KNOWN')]
        self.assertEqual(len(known), 14, lines)
        self.assertEqual(sum('step 8' in l and '[known gap ENDGAME-CHAMBER-COLLAPSE-63]' in l for l in known), 2, known)
        self.assertTrue(any('keening_count == 1: no number in the answer (getitemcount: no such item id: keening)' in l
                            for l in known), known)
        self.assertTrue(any('dagoth_y > 1000: read -0.428955' in l for l in known), known)
        self.assertEqual(sum('[known gap MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66]' in l for l in known), 4, known)
        self.assertEqual(sum('[known gap MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66]' in l for l in known), 4, known)

    def test_the_collapse_playing_closes_its_known_gap(self):
        ok, lines = self.judge(status_end=status(6, 7, misses=0, weather=2, off='none'))
        self.assertTrue(ok, '\n'.join(self.failing(lines)))
        self.assertIn('known gaps: 12 of 14 checks still failing', lines[-1])
        self.assertTrue(lines[-1].endswith('closed now: ENDGAME-CHAMBER-COLLAPSE-63'), lines[-1])
        self.assertTrue(any('passes now, check the register' in l for l in lines))

    def test_the_member_read_closes_its_gap_when_the_shields_follow_the_count(self):
        # MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66 (run2): Dagoth Ur's shield stayed the count-0 one through the strikes
        ok, lines = self.judge(shield_k1=1, shield_one_k1=0, shield_k2=1, shield_k3=1)
        self.assertTrue(ok, '\n'.join(self.failing(lines)))
        self.assertIn('closed now: MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66', lines[-1])

    def test_the_cavern_comes_before_the_chamber_and_hides_azuras_spirit_below_stage_20(self):
        # run2 came to the Facility Cavern first at stage 20: the spirit had never been hidden, and AzuraEnd enables it
        # only when it is hidden, so the quest never ended
        a = self.lines
        cavern = a.index('cmd dbg tp ri71c3339d8b')
        self.assertLess(a.index('cmd aw_mwscript_status call journal C3_DestroyDagoth 10'), cavern)
        self.assertLess(cavern, a.index('cmd dbg tp heartchamber'))
        self.assertLess(a.index('cmd echo JOURNEY PROBE spirit_hidden'), a.index('cmd dbg tp heartchamber'))
        self.assertEqual(sum(l == 'cmd dbg tp ri71c3339d8b' for l in a), 2)
        ok, lines = self.judge(spirit_hidden=0)
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('step 3', bad[0])
        self.assertIn('spirit_hidden == 1', bad[0])

    def test_the_ending_video_and_the_quest_end_in_the_cavern(self):
        ok, lines = self.judge(status_final=status(6, 5, misses=2, weather=2, off='none', binks=0))
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('binks_final == binks_before+1', bad[0])
        # AzuraEnd never leaving its first state (run2): nothing of the end happens
        ok, lines = self.judge(spirit_shown=1, controls_taken=0, quest_final=20, sleepers_final=0, ring_final=1,
                               spirit_gone=1, status_final=status(6, 5, misses=2, weather=2, off='none', binks=0))
        bad = self.failing(lines)
        self.assertTrue(all('step 9' in l for l in bad), bad)
        for text in ('spirit_shown == 0', 'controls_taken == 1', 'quest_final == 50', 'sleepers_final == 50',
                     'ring_final == 0', 'binks_final == binks_before+1'):
            self.assertTrue(any(text in l for l in bad), (text, bad))

    def test_the_heart_moving_dagoth_ur_is_read_from_the_positioncell_count(self):
        # Dagoth Ur fights from the arrival and runs to the player after the Heart's PositionCell, so his place seconds
        # later says nothing (run1); the script host's count of a PositionCell carried out on this map does
        ok, lines = self.judge(status_near=status(0, 0, moved=0))
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('step 4', bad[0])
        self.assertIn('moved_near == moved_arrival+1', bad[0])

    def test_the_player_stands_on_the_platform_in_front_of_the_heart(self):
        # run1 put the view 34 units over the platform: the arrival search found no ground within its 32 units and took
        # the next spot, on top of the solid round the Heart (Unstuck: 0 964 -17)
        a = self.lines
        self.assertIn('cmd aw_view 0 946 -38 90 30', a)
        ok, lines = self.judge(stand=(0, 964, -17))
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('has stand Unstuck: 0 946', bad[0])

    def test_keening_carried_is_read_from_the_grant(self):
        # the console cannot count Keening (a known gap), so the grant's own answer says it is carried
        ok, lines = self.judge()
        self.assertTrue(any(l.startswith('PASS step 2 ') and 'has keening_given Now 1 carried (keening)' in l
                            for l in lines), lines)
        ok, lines = self.judge(keening_given=None)
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('has keening_given Now 1 carried (keening)', bad[0])

    def test_the_tools_are_given_before_the_chamber_and_sunder_strikes_before_keening(self):
        a = self.lines
        give = [a.index('cmd dbg give %s' % t) for t in ('sunder', 'keening', 'wraithguard')]
        tp = a.index('cmd dbg tp heartchamber')
        self.assertLess(max(give), tp)
        attacks = [i for i, l in enumerate(a) if l == 'cmd +attack']
        self.assertEqual(len(attacks), 6)                          # one Sunder strike, five Keening strikes
        sunder, keening = a.index('cmd aw_inventory equip sunder'), a.index('cmd aw_inventory equip keening')
        self.assertLess(sunder, attacks[0])
        self.assertLess(attacks[0], keening)
        self.assertLess(keening, attacks[1])
        # the quest at the stage before the Heart, before the teleport
        self.assertLess(a.index('cmd aw_mwscript_status call journal C3_DestroyDagoth 10'), tp)

    def test_dagoth_ur_is_fought_in_god_mode_not_killed_by_reference(self):
        a = self.lines
        tp = a.index('cmd dbg tp heartchamber')
        kills = [l for l in a if l.startswith('cmd chim actors kill')]
        self.assertEqual(kills, ['cmd chim actors kill %d' % DAGOTH_FIRST])   # only his first form, in the cavern
        self.assertGreater(a.index(kills[0]), a.index('cmd dbg tp ri71c3339d8b'))
        self.assertLess(a.index(kills[0]), tp)                     # defeated before the chamber, at stage 10
        god = [(i, l) for i, l in enumerate(a) if l.startswith('cmd dbg god ')]
        self.assertEqual(god[-1][1], 'cmd dbg god on')
        self.assertLess(god[-1][0], tp)                            # on for the whole chamber
        # the only time without it: four seconds with Sunder in hand and Wraithguard worn, before the chamber
        off = [i for i, l in god if l == 'cmd dbg god off']
        self.assertEqual(len(off), 1)
        self.assertLess(a.index('cmd aw_inventory equip wraithguard'), off[0])

    def test_the_heart_destroyed_global_is_set_by_the_console_only_after_the_strike_checks(self):
        a = self.lines
        put = a.index('cmd aw_mwscript_status call setglobal HeartDestroyed 1')
        self.assertGreater(put, a.index('cmd echo JOURNEY PROBE heart_gone'))
        self.assertGreater(put, a.index('cmd echo JOURNEY PROBE list_destroyed'))
        self.assertLess(put, a.index('cmd echo JOURNEY STEP 8'))

    def test_a_keening_strike_the_heart_did_not_take_fails_step_6(self):
        # the third Keening blow missed or landed elsewhere: HitOnMe matched and the PlayGroups stay at the second
        ok, lines = self.judge(status_k3=status(3, 2))
        bad = self.failing(lines)
        self.assertFalse(ok)
        self.assertTrue(all('step 6' in l for l in bad), bad)
        self.assertTrue(any('matched_k3 == matched_near+4' in l and 'read 3, wanted == 4' in l for l in bad), bad)
        self.assertTrue(any('plays_k3 == plays_near+3' in l for l in bad), bad)

    def test_sunder_not_taken_fails_step_5(self):
        # Sunder's strike not taken: the Heart's local 0 stays 0
        ok, lines = self.judge(heart_sunder=0)
        bad = self.failing(lines)
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith('FAIL step 5') and 'heart_sunder local 0 = 1 (' in l for l in bad), bad)

    def test_the_console_equip_is_a_known_gap_until_it_sets_wraithguards_global(self):
        # run1: player->equip wraithguard left wraithguardEquipped at 0 (CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66); the inventory
        # window's route set it, and that one is a counted check
        ok, lines = self.judge()
        self.assertTrue(any(l.startswith('KNOWN step 2') and 'wraith_console == 1' in l for l in lines), lines)
        ok, lines = self.judge(wraith_console=1)
        self.assertTrue(any(l.startswith('PASS step 2') and 'wraith_console == 1' in l and 'passes now' in l
                            for l in lines), lines)
        ok, lines = self.judge(wraith_worn=0)
        self.assertTrue(any(l.startswith('FAIL step 2') and 'wraith_worn == 1' in l for l in lines), lines)

    def test_wraithguard_not_protecting_fails_step_2(self):
        ok, lines = self.judge(health_wraith=780)
        self.assertTrue(any(l.startswith('FAIL step 2') and 'health_wraith == health_armed' in l for l in lines), lines)

    def test_the_console_showvars_on_the_consoles_own_instance_is_a_known_gap(self):
        # run2: "ShowVars: script 0, 0 locals" for the Heart, whose script is LorkhanHeart (row 319)
        ok, lines = self.judge()
        self.assertTrue(any(l.startswith('KNOWN step 5') and 'vars_row == heart_row' in l and 'read 0, wanted == 319' in l
                            for l in lines), lines)
        ok, lines = self.judge(heart_vars=319)
        self.assertIn('closed now: CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66', lines[-1])

    def test_an_end_script_that_never_starts_fails_step_8(self):
        ok, lines = self.judge(blight_end=0, quest_end=10, dagoth_end=200, standing_end=0,
                               status_end=status(6, 5, off='teleporting'))
        bad = self.failing(lines)
        self.assertFalse(ok)
        self.assertTrue(all('step 8' in l or 'step 9' in l for l in bad), bad)
        for text in ('blight_end == -1', 'quest_end == 20', 'dagoth_end <= 0', 'rep_end == rep_before+10',
                     'weather_end == weather_struck+2', 'lacks status_end off now: teleporting'):
            self.assertTrue(any(text in l for l in bad), (text, bad))

    def test_a_health_set_to_0_that_kills_closes_its_gap(self):
        # MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66 (run2): the workers and Dagoth Ur at health 0 stayed alive in the list
        ok, lines = self.judge(list_destroyed=world(workers='DEAD'), list_end=world(dagoth='DEAD', workers='DEAD'))
        self.assertTrue(ok, '\n'.join(self.failing(lines)))
        self.assertIn('closed now: MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66', lines[-1])
        # the workers' script not run at all: their health stays up, a counted check
        ok, lines = self.judge(worker_health=100)
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('worker_health <= 0', bad[0])

    def test_dagoth_ur_dead_before_the_heart_fails_step_7(self):
        ok, lines = self.judge(list_destroyed=world(dagoth='DEAD'))
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('alive 262014 in list_destroyed', bad[0])
        self.assertIn('reference 262014 is dead', bad[0])

    def test_dagoth_ur_not_fighting_fails_step_4(self):
        ok, lines = self.judge(list_near=world(dagoth='ALIVE'))
        bad = self.failing(lines)
        self.assertEqual(len(bad), 1, bad)
        self.assertTrue(any('reference 262014 is alive, not fighting' in l for l in bad), bad)

    def test_the_known_gaps_do_not_fail_the_journey_and_a_counted_check_does(self):
        # the run1 answers of the three console reads are not counted; the strike counts are
        ok, lines = self.judge(status_k5=status(5, 4))
        self.assertFalse(ok)
        self.assertTrue(all(l.startswith('FAIL step 6') for l in self.failing(lines)), self.failing(lines))
        self.assertIn('known gaps: 14 of 14 checks still failing', lines[-1])

    def test_the_chamber_not_loading_stops_in_step_3_and_names_the_checks_not_reached(self):
        run = fake_run(self.j, GOOD, stop_in=3, stop_line='waitfor map 150 rifa4ef181ed')
        ok, lines = js.judge(self.j, [run])
        self.assertFalse(ok)
        self.assertTrue(all(l.startswith('PASS') for l in lines if re.match(r'(PASS|FAIL) step [12] ', l)), lines)
        later = [l for l in lines if re.match(r'(PASS|FAIL|KNOWN) step [4-9] ', l)]
        self.assertTrue(later and all('not reached: part A stopped in step 3' in l for l in later), later)
        self.assertTrue(lines[-1].startswith('JOURNEY RESULT FAIL') and lines[-1].endswith('; part A stopped in step 3'),
                        lines[-1])

    def test_the_end_of_the_quest_in_the_cavern(self):
        ok, lines = self.judge(quest_final=20, sleepers_final=0, ring_final=1, controls_final=1, spirit_gone=0)
        bad = self.failing(lines)
        self.assertEqual(len(bad), 5, bad)
        self.assertTrue(all('step 9' in l for l in bad), bad)

    def test_the_walkthrough_lists_the_strikes_and_the_known_gap(self):
        text = js.walkthrough(JOURNEY.read_text(encoding='utf-8'))
        for n in range(1, 10):
            self.assertIn('Step %d: ' % n, text)
        self.assertIn('type: aw_mwscript_status call getlocal 197602', text)
        self.assertIn('read: the number before "matched" in the answer of status_k5', text)
        self.assertIn('(known gap ENDGAME-CHAMBER-COLLAPSE-63)', text)


if __name__ == '__main__':
    unittest.main()
