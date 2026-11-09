# SPDX-License-Identifier: GPL-3.0-only
"""Scripted world events (SCRIPTED-EVENT-FALLING-MAGE-61, v0.0.62): the builder finds every actor standing on an object
some script disables (the falling mage north of Seyda Neen on his platform, by the general rule of
tools/mwscript/events.py, not by name), writes the pairs as the HELD section of id1/mwscript.awm, and lists the
distance-triggered world events for the script tracker. The engine reads the rows (aw_mwvm.c AW_MwvmHeld*), holds the
actor until its object is disabled and lets it fall (aw_fall.c; the fall rules in tests/aga_move_rules_test.c and
tests/aga_move_test.c). Synthetic master only (no game data); the native part runs in the Linux gate."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms, events  # noqa: E402
from test_mwscript import record, sub, scpt, cell_exterior, HARNESS  # noqa: E402

# the falling mage's journal, as the original's (a distance trigger, the platform disabled two seconds later, the two
# screams through the player)
JOURNAL = r'''begin FallTest
short fellonce
float timer
if ( "faller"->OnDeath == 1 )
	set fellonce to -1
	return
endif
if ( fellonce == 0 )
	if ( GetDistance Player <= 2000 )
		"faller"->enable
		"faller"->Fall
		set fellonce to 1
	endif
endif
if ( fellonce == 1 )
	set timer to ( timer + GetSecondsPassed )
	if ( timer >= 2 )
		"platform_x"->Disable
		"player"->Say "Vo\w\m\Hit_WM006.mp3" "AAARGH"
		set fellonce to 2
	endif
endif
end'''

SCRIPTS = {
    'FallTest': JOURNAL,
    # an object that disables itself (no reference before Disable): an actor on it is held too
    'SelfGone': 'begin SelfGone\nif ( GetJournalIndex QA_X >= 10 )\n\tDisable\nendif\nend',
    # a script that only reads GetDisabled: its object is no target
    'OnlyAsks': 'begin OnlyAsks\nshort x\nset x to GetDisabled\nend',
    'Twice': 'begin Twice\n"twice_x"->Disable\nend',
    # a distance trigger that starts a fight (an ambush)
    'Ambush': 'begin Ambush\nif ( GetDistance Player < 512 )\n\tStartCombat Player\nendif\nend',
}


def master(scripts=SCRIPTS):
    out = [record('TES3', sub('HEDR', b'\0' * 300))]
    out += [record('DIAL', sub('NAME', 'QA_X'), sub('DATA', b'\x04'))]
    out += [scpt(n, t) for n, t in scripts.items()]
    out += [record('NPC_', sub('NAME', 'faller')), record('NPC_', sub('NAME', 'bystander')),
            record('NPC_', sub('NAME', 'sitter')), record('NPC_', sub('NAME', 'rider')),
            record('NPC_', sub('NAME', 'twicer')), record('NPC_', sub('NAME', 'ambusher'), sub('SCRI', 'Ambush')),
            record('CREA', sub('NAME', 'below')),
            record('ACTI', sub('NAME', 'platform_x')), record('ACTI', sub('NAME', 'crate_y'), sub('SCRI', 'OnlyAsks')),
            record('ACTI', sub('NAME', 'self_x'), sub('SCRI', 'SelfGone')), record('ACTI', sub('NAME', 'twice_x')),
            record('BOOK', sub('NAME', 'journal_x'), sub('SCRI', 'FallTest'))]
    out.append(cell_exterior(-3, -8, [
        (301, 'platform_x', (0, 0, 3080)), (302, 'faller', (6, -13, 3132)),       # on it: 14 sideways, 52 above
        (303, 'bystander', (90, 0, 3132)),                                        # beside it: 90 sideways
        (304, 'below', (0, 0, 3000)),                                             # under it
        (305, 'journal_x', (0, 0, 668)),
        (306, 'crate_y', (500, 0, 10)), (307, 'sitter', (500, 0, 60)),           # on an object no script disables
        (308, 'self_x', (900, 0, 10)), (309, 'rider', (905, 5, 40)),             # on an object that disables itself
        (310, 'twice_x', (1500, 0, 10)), (311, 'twice_x', (2500, 0, 10)), (312, 'twicer', (1500, 0, 40)),
        (313, 'ambusher', (3000, 0, 0))]))
    return b''.join(out)


def loaded(scripts=SCRIPTS):
    tmp = Path(tempfile.mkdtemp(prefix='aw-events-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master(scripts))
        data = GameData().load(tmp)
        prog, compiled = compile_program(data, None, handwritten=('chargen*',), rooms={})
        return data, prog, compiled
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class HeldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.prog, cls.compiled = loaded()

    def test_disable_targets(self):
        t = events.disable_targets(self.data)
        self.assertIn('platform_x', t)                  # "platform_x"->Disable
        self.assertIn('self_x', t)                      # its own script's bare Disable
        self.assertIn('twice_x', t)
        self.assertNotIn('crate_y', t)                  # GetDisabled is no Disable

    def test_the_rule(self):
        r = events.check(self.data)
        rows = {row['actor_id']: row for row in r['rows']}
        self.assertEqual(sorted(rows), ['faller', 'rider'])
        self.assertEqual((rows['faller']['actor'], rows['faller']['support']), (302, 301))
        self.assertEqual(rows['faller']['position'], (6.0, -13.0, 3132.0))
        self.assertEqual(rows['rider']['support'], 308)
        near = {(n['actor_id'], n['support_id']): n['why'] for n in r['near']}
        self.assertIn('sideways', near[('bystander', 'platform_x')])      # beside it, not on it
        self.assertIn('below', near[('below', 'platform_x')])            # under it
        self.assertNotIn('twicer', rows)                # its object is placed twice: no single reference to watch
        self.assertNotIn('sitter', rows)                # its object is never disabled

    def test_the_file_holds_the_rows(self):
        self.prog.held = events.check(self.data)['rows']
        f = awms.read(awms.write(self.prog, self.compiled, bindings(self.prog))[0])
        self.assertIn('HELD', awms.RESIDENT)
        self.assertEqual(f['HELD_rows'], 2)
        rows = [struct.unpack_from('>IIfff', f['HELD'], 20 * i) for i in range(2)]
        self.assertEqual(rows[0][:2], (302, 301))
        self.assertEqual(rows[1][:2], (309, 308))       # sorted by actor
        self.assertAlmostEqual(rows[0][4], 3132.0)
        # an older program without rows writes an empty section
        self.prog.held = []
        f = awms.read(awms.write(self.prog, self.compiled, bindings(self.prog))[0])
        self.assertEqual(f['HELD_rows'], 0)

    def test_the_journal_script(self):
        # what the event needs of the compiled script: the Enable and Disable on their references, the player's Say,
        # Fall compiled to nothing
        c = self.compiled[self.prog.scripts.index['falltest']]
        self.assertIsNone(c.error)
        ops = [n for _, n, _ in awms.decode(c.code)]
        for op in ('ENABLE', 'DISABLE', 'SAY', 'DISTANCE', 'SECONDS'):
            self.assertIn(op, ops)
        self.assertNotIn('NOTYET', ops)

    def test_far_trigger(self):
        # SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62: the script that removes a held actor's support carries its own trigger
        # distance in the SCRP row, so the engine can fire it under the player's draw distance; others carry 0
        rows = events.check(self.data)['rows']
        self.assertEqual(events.far_triggers(self.data, rows), {'falltest': 2000})
        self.assertEqual(events.far_triggers(self.data, []), {})
        self.prog.held = rows
        self.prog.far = events.far_triggers(self.data, rows)
        f = awms.read(awms.write(self.prog, self.compiled, bindings(self.prog))[0])
        far = {}
        for i in range(f['SCRP_rows']):
            far[i] = struct.unpack_from('>H', f['SCRP'], 16 * i + 6)[0]
        self.assertEqual(far[self.prog.scripts.index['falltest']], 2000)
        self.assertEqual(far[self.prog.scripts.index['ambush']], 0)     # an ambush keeps its own distance
        self.prog.far = {}

    def test_census(self):
        rows = events.census(self.data)
        by = {r['script']: r for r in rows}
        self.assertIn('falltest', by)
        self.assertEqual(by['falltest']['reference'], 305)
        self.assertTrue({'enables', 'disables', 'falls', 'says'} <= set(by['falltest']['does']))
        self.assertEqual(by['ambush']['does'], ['attacks'])
        self.assertNotIn('selfgone', by)                # no distance test: not an event of this kind


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InterpreterTests(unittest.TestCase):
    def test_the_engine_reads_the_rows(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-events-vm-'))
        try:
            data, prog, compiled = loaded()
            prog.held = events.check(data)['rows']
            raw, _ = awms.write(prog, compiled, bindings(prog))
            (tmp / 'test.awm').write_bytes(raw)
            (tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                    '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                    str(tmp / 'h.c'), str(src / 'aw_mwvm.c'), str(src / 'aw_ledger.c'),
                                    '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            r = subprocess.run([str(tmp / 'h'), str(tmp / 'test.awm'), '1', '0.25'], capture_output=True, text=True,
                               env=dict(os.environ, HELD='1'))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = r.stdout.splitlines()
            self.assertIn('held 302 301 6.0 -13.0 3132.0 find 0', out)
            self.assertIn('held 309 308 905.0 5.0 40.0 find 1', out)
            self.assertIn('held rows 2 find-none -1', out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
