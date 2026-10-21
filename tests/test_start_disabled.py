# SPDX-License-Identifier: GPL-3.0-only
"""Actors the original's start scripts disable at a new game (NPC-STORY-DISABLED-AT-START-42).

Synthetic script text and a synthetic master only (no game data): the Startup reader, the enable
rule reader, the table, the placement filter and the town resident stage's record."""
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import start_disabled as sd  # noqa: E402

MAIN = '''begin Main
; this script starts when the game is run
if ( MenuMode == 0 )
\tSet Random100 to Random, 101
endif
if  ( CharGenState == 1 )\t\t; new game
\tStartScript Startup
\tif ( ScriptRunning, CharGen == 0 )
\t\tStartScript CharGen
\tendif
endif
end
'''

STARTUP = '''begin Startup
;put RUN ONCE stuff here
short testVar
;for a quest
Fixture_Spider->Disable
"Fixture Sleeper 01"->Disable
"fixture prophet"->disable  ; lower case and a comment
"fixture_scaffold"->Disable
if ( testVar == 1 )
\t"Fixture Guarded"->Disable
endif
StopScript Startup
set testVar to 1
End
'''

CHARGEN = '''begin CharGen
short state
if ( state == 0 )
\t"chargen boat guard"->Disable
endif
end
'''

SLEEPER = '''begin fixture_sleeperEnable

short test
Short NoLore

Set test to GetJournalIndex FX_6thHouse

if ( GetDisabled == 0 )
\tReturn
endif

if ( test == 50 )
\tEnable
\tReturn
endif

End
'''

DIRECT = '''begin fixture_direct
if ( GetJournalIndex "FX quest" >= 20 )
\tEnable
endif
end
'''

COMPLEX = '''begin fixture_follow
short done
if ( MenuMode == 1 )
\treturn
endif
if ( done == 1 )
\tEnable
endif
end
'''

QUEST = '''begin fixture_quest
if ( GetJournalIndex FX_Quest == 10 )
\t"fixture prophet"->Enable
endif
end
'''


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def script(name, text):
    head = name.encode('ascii').ljust(32, b'\0') + bytes(20)
    return record('SCPT', sub('SCHD', head), sub('SCTX', text.encode('cp1252')))


def base(tag, ident, scri=None):
    return record(tag, sub('NAME', z(ident)), *([sub('SCRI', z(scri))] if scri else []))


def cell(name, flags, x, y, refs):
    parts = [sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', flags, x, y))]
    for number, ident in refs:
        parts += [sub('FRMR', struct.pack('<I', number)), sub('NAME', z(ident)),
                  sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))]
    return record('CELL', *parts)


def master():
    return b''.join([
        script('Main', MAIN), script('Startup', STARTUP), script('CharGen', CHARGEN),
        script('fixture_sleeperEnable', SLEEPER), script('fixture_quest', QUEST),
        base('CREA', 'Fixture_Spider'), base('NPC_', 'Fixture Sleeper 01', 'fixture_sleeperEnable'),
        base('NPC_', 'fixture prophet'), base('STAT', 'fixture_scaffold'), base('NPC_', 'Fixture Guarded'),
        base('NPC_', 'fixture villager'),
        cell('', 0, 2, -3, [(11, 'Fixture Sleeper 01'), (12, 'fixture villager'), (13, 'fixture_scaffold')]),
        cell('Fixture Underworks', 1, 0, 0, [(21, 'fixture prophet'), (22, 'Fixture_Spider')]),
        record('DIAL', sub('NAME', z('work'))),
        record('INFO', sub('INAM', z('1')), sub('BNAM', z('"Fixture_Spider"->Enable'))),
    ])


class ScriptReaderTests(unittest.TestCase):
    def test_disable_lines_read_quoted_bare_and_conditional(self):
        rows = sd.disable_lines(STARTUP)
        self.assertEqual([(r['id'], r['conditional']) for r in rows],
                         [('Fixture_Spider', False), ('Fixture Sleeper 01', False), ('fixture prophet', False),
                          ('fixture_scaffold', False), ('Fixture Guarded', True)])
        self.assertEqual(rows[0]['line'], 5)

    def test_started_scripts_follow_main(self):
        self.assertEqual(sd.started_scripts(MAIN), ['Startup', 'CharGen'])

    def test_journal_template_with_a_variable(self):
        self.assertEqual(sd.enable_rule(SLEEPER),
                         {'status': 'journal', 'journal': 'FX_6thHouse', 'operator': '==', 'value': 50})

    def test_journal_template_with_a_direct_call(self):
        self.assertEqual(sd.enable_rule(DIRECT),
                         {'status': 'journal', 'journal': 'FX quest', 'operator': '>=', 'value': 20})

    def test_anything_else_is_unknown_never_guessed(self):
        rule = sd.enable_rule(COMPLEX)
        self.assertEqual(rule['status'], sd.UNKNOWN)
        self.assertIn('MenuMode', rule['reason'])
        self.assertEqual(sd.enable_rule('begin x\nshort a\nend\n'), {'status': 'no enable'})
        self.assertEqual(sd.enable_rule('begin x\nif ( GetJournalIndex A == 1 )\nEnable\nendif\nif ( GetJournalIndex B == 2 )\n'
                                        'Enable\nendif\nend\n')['status'], sd.UNKNOWN)

    def test_enable_callers_match_the_id_only(self):
        texts = [('fixture_quest', QUEST), ('other', '"fixture prophet 2"->Enable'), ('topic: work', 'FIXTURE_SPIDER->enable'),
                 ('topic: work', '"Fixture_Spider"->Enable')]
        self.assertEqual(sd.enable_callers(texts, 'Fixture Prophet'), ['fixture_quest'])
        self.assertEqual(sd.enable_callers(texts, 'Fixture_Spider'), ['topic: work'])


class TableTests(unittest.TestCase):
    def setUp(self):
        self.document = sd.table(master())
        self.rows = {r['id']: r for r in self.document['rows']}

    def test_reads_only_unconditional_disables_of_the_scripts_main_starts(self):
        self.assertEqual(self.document['start_scripts'], ['Startup', 'CharGen'])
        self.assertEqual(sorted(self.rows), ['Fixture Sleeper 01', 'Fixture_Spider', 'fixture prophet', 'fixture_scaffold'])
        self.assertEqual(sorted(r['id'] for r in self.document['conditional_not_applied']),
                         ['Fixture Guarded', 'chargen boat guard'])

    def test_rows_carry_type_placements_and_enable_rule(self):
        sleeper = self.rows['Fixture Sleeper 01']
        self.assertEqual(sleeper['type'], 'NPC_')
        self.assertEqual(sleeper['placements'], [{'cell': [2, -3], 'reference': 11}])
        self.assertEqual(sleeper['enable']['status'], 'journal')
        self.assertEqual(sleeper['enable']['own_script'], 'fixture_sleeperEnable')
        prophet = self.rows['fixture prophet']
        self.assertEqual(prophet['placements'], [{'cell': 'Fixture Underworks', 'reference': 21}])
        self.assertEqual(prophet['enable'], {'own_script': None, 'status': 'no script', 'enabled_by': ['fixture_quest']})
        self.assertEqual(self.rows['Fixture_Spider']['enable']['enabled_by'], ['topic: work'])
        self.assertEqual(set(sd.actor_rows(self.document)), {'fixture sleeper 01', 'fixture_spider', 'fixture prophet'})

    def test_a_master_without_main_is_refused(self):
        with self.assertRaises(ValueError):
            sd.table(script('Startup', STARTUP))


class FilterTests(unittest.TestCase):
    TOWN = [{'number': 11, 'id': 'FIXTURE SLEEPER 01', 'type': 'NPC_'},
            {'number': 12, 'id': 'fixture villager', 'type': 'NPC_'},
            {'number': 13, 'id': 'fixture_scaffold', 'type': 'STAT'},
            {'number': 22, 'id': 'Fixture_Spider', 'type': 'CREA'}]

    def setUp(self):
        self.document = sd.table(master())

    def test_original_holds_the_disabled_actors_only(self):
        kept, held = sd.held(self.TOWN, self.document, 'fixture_town', active=True)
        self.assertEqual([r['number'] for r in kept], [12, 13])
        self.assertEqual([(r['map'], r['reference'], r['type']) for r in held],
                         [('fixture_town', 11, 'NPC_'), ('fixture_town', 22, 'CREA')])
        self.assertIn('journal FX_6thHouse == 50', held[0]['reason'])
        self.assertEqual(held[0]['disabled_by'], 'Startup line 6')

    def test_placed_keeps_everything(self):
        with mock.patch.dict(os.environ, {sd.ENV: 'placed'}):
            kept, held = sd.held(self.TOWN, self.document)
        self.assertEqual((kept, held), (self.TOWN, []))

    def test_mode_default_is_placed_and_refusal(self):
        # off by default: nothing enables a held actor during play yet (NPC-STORY-DISABLED-AT-START-42)
        with mock.patch.dict(os.environ, {sd.ENV: ''}):
            self.assertEqual(sd.mode(), 'placed')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sd.mode(), 'placed')
            kept, held = sd.held(self.TOWN, self.document)
            self.assertEqual((kept, held), (self.TOWN, []))
        with mock.patch.dict(os.environ, {sd.ENV: 'hidden'}), self.assertRaises(ValueError):
            sd.mode()

    def test_builder_exports_the_mode_for_the_resident_stages(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("export_start_disabled(getattr(args, 'start_disabled', None) or 'placed')", text)
        self.assertIn('start_disabled.add_option(p)', text)
        import build
        self.assertIsNone(build.parser().parse_args(['--data-files', 'x']).start_disabled)   # = placed
        with mock.patch.dict(os.environ, {sd.ENV: 'original'}):
            sd.export_mode('placed')
            self.assertNotIn(sd.ENV, os.environ)    # a default build's environment is as before
            sd.export_mode('original')
            self.assertEqual(os.environ[sd.ENV], 'original')


class TownStageTests(unittest.TestCase):
    def test_town_residents_record_the_held_actor(self):
        from import_town import residents
        from town_config import load_settings
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {sd.ENV: 'original'}):
            out = Path(tmp)
            (out / 'id1').mkdir()
            (out / 'Morrowind.esm').write_bytes(master())
            settings = load_settings('lava_x1ym2')
            refs = [{'number': 11, 'id': 'Fixture Sleeper 01', 'type': 'NPC_', 'position': [0, 0, 0],
                     'rotation_radians': [0, 0, 0], 'scale': 1.0}]
            entities = residents(out, out, out, refs, settings, {'NPC_': {}}, {}, b'', 'ffmpeg', 4)
            self.assertEqual(entities, [])
            manifest = json.loads((out / 'residents.json').read_text())
            self.assertEqual(manifest['cast'], [])
            self.assertEqual(manifest['start_disabled']['mode'], 'original')
            self.assertEqual([(r['reference'], r['enable']['journal']) for r in manifest['start_disabled']['held']],
                             [(11, 'FX_6thHouse')])

    def test_default_town_record_is_as_before(self):
        from import_town import residents
        from town_config import load_settings
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(sd.ENV, None)
            out = Path(tmp)
            (out / 'id1').mkdir()
            residents(out, out, out, [], load_settings('lava_x1ym2'), {'NPC_': {}}, {}, b'', 'ffmpeg', 4)
            self.assertNotIn('start_disabled', json.loads((out / 'residents.json').read_text()))


if __name__ == '__main__':
    unittest.main()
