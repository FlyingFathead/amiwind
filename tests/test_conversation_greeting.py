# SPDX-License-Identifier: GPL-3.0-only
"""The conversation greeting a manual talk opens with (mwad.dialogue, NPC-DREAMER-GREETING-DEFAULT-42).

Synthetic records only (no game data). The rule is OpenMW's DialogueManager::startDialogue: the
Greeting topics in ID order, the first INFO in each that passes actor, player, condition and
disposition tests. Fixtures: a class-filtered greeting that must win over a generic later one, a
first-meeting / later-talk pair (TalkedToPc), a journal-gated line that must not fire at the start,
a line on a script local, a player-dependent line that is passed over and reported, the speaker's
defines filled at build time and the player's left in the engine's spelling.
"""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import mwad.dialogue as dialogue  # noqa: E402


def f(tag, value):
    return (tag, value.encode('cp1252') + b'\0' if isinstance(value, str) else value)


def info(identifier, line, disp=0, rank=-1, gender=-1, pcrank=-1, **filters):
    fields = [f('INAM', identifier), ('DATA', struct.pack('<iibbbb', 2, disp, rank, gender, pcrank, 0))]
    for tag in ('ONAM', 'RNAM', 'CNAM', 'FNAM', 'ANAM', 'DNAM'):
        if tag in filters:
            fields.append(f(tag, filters[tag]))
    for rule, value in filters.get('scvr', ()):
        fields += [('SCVR', rule.encode('cp1252')), ('INTV', struct.pack('<i', value))]
    return fields + [f('NAME', line)]


def npc(identifier, name, race='Dark Elf', cls='Dreamers', faction='Sixth House', script='', female=False):
    return [f('NAME', identifier), f('FNAM', name), f('RNAM', race), f('CNAM', cls), f('ANAM', faction),
            f('SCRI', script), ('FLAG', struct.pack('<I', 1 if female else 0)),
            ('NPDT', struct.pack('<hBBBBBBi', 5, 40, 3, 1, 0, 0, 0, 0)),
            ('AIDT', struct.pack('<HBBB3xI', 30, 10, 20, 0, 0))]


def kinds(**extra):
    out = {'NPC_': {'dreamer_talker07': npc('dreamer_talker07', 'Dreamer'),
                    'trader': npc('trader', 'Trader Ralen', cls='Trader', faction='', script='traderscript'),
                    'player': [f('NAME', 'player'), ('NPCO', struct.pack('<i', 1) + b'shirt'.ljust(32, b'\0'))]},
           'CLOT': {'shirt': [f('NAME', 'shirt'), ('CTDT', struct.pack('<ifhh', 2, 1.0, 10, 0))]},
           'ARMO': {}, 'RACE': {'dark elf': [f('NAME', 'Dark Elf'), f('FNAM', 'Dark Elf')]},
           'CLAS': {'trader': [f('NAME', 'Trader'), f('FNAM', 'Trader')]},
           'FACT': {}, 'REGN': {}, 'GLOB': {'sleeperon': [f('NAME', 'SleeperOn'), ('FLTV', struct.pack('<f', 0))]},
           'SCPT': {'traderscript': [('SCHD', b'TraderScript'.ljust(52, b'\0')),
                                     ('SCTX', b'begin TraderScript\nshort NoLore\nend\n')]},
           'DIAL': {'greeting 0': 2, 'greeting 1': 2, 'greeting 9': 2}}
    out.update(extra)
    return out


TOPICS = {
    'greeting 0': [info('journal', 'The Sixth House sees you, hero.', CNAM='Dreamers',
                        scvr=[('04JX0A2_2_6thHouse', 50)])],
    'greeting 1': [info('first', 'We have you in our eye, %PCName.', CNAM='Dreamers',
                        scvr=[('01630', 0)]),
                   info('again', 'Lord Dagoth has awakened.', CNAM='Dreamers'),
                   info('same race', 'Hello, kinsman.', scvr=[('01450', 1)]),
                   info('local', 'I am %Name, a %class.', scvr=[('03sX0nolore', 0)])],
    'greeting 9': [info('generic', 'What do you want?')],
}


class ConversationGreeting(unittest.TestCase):
    def test_class_greeting_wins_over_generic_and_first_meeting_first(self):
        got = dialogue.conversation_greeting(kinds(), TOPICS, 'dreamer_talker07')
        self.assertEqual((got['topic'], got['info']), ('greeting 1', 'first'))
        self.assertTrue(got['determined'])
        later = dialogue.conversation_greeting(kinds(), TOPICS, 'dreamer_talker07', talked_to=True)
        self.assertEqual(later['info'], 'again')

    def test_journal_gate_is_closed_at_the_start(self):
        topics = {'greeting 0': TOPICS['greeting 0'], 'greeting 9': TOPICS['greeting 9']}
        self.assertEqual(dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07')['info'], 'generic')

    def test_player_dependent_line_passed_over_and_reported(self):
        got = dialogue.conversation_greeting(kinds(), TOPICS, 'trader')
        self.assertEqual(got['info'], 'local')            # the script declares NoLore, 0 at the start
        self.assertFalse(got['determined'])
        self.assertEqual(got['unknown_before'], ['greeting 1:same race'])

    def test_local_without_script_fails(self):
        k = kinds()
        k['NPC_']['trader'] = npc('trader', 'Trader Ralen', cls='Trader', faction='')
        self.assertEqual(dialogue.conversation_greeting(k, TOPICS, 'trader')['info'], 'generic')

    def test_topic_order_is_by_id(self):
        topics = {'greeting 9': TOPICS['greeting 9'], 'greeting 1': TOPICS['greeting 1']}
        self.assertEqual(dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07')['topic'], 'greeting 1')

    def test_cell_filter(self):
        topics = {'greeting 1': [info('cell', 'Welcome to the shrine.', ANAM='Ilunibi')],
                  'greeting 9': TOPICS['greeting 9']}
        here = dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07', cell="Ilunibi, Soul's Rattle")
        self.assertEqual(here['info'], 'cell')
        elsewhere = dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07', cell='Hla Oad')
        self.assertEqual((elsewhere['info'], elsewhere['determined']), ('generic', True))
        unknown = dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07')
        self.assertEqual((unknown['info'], unknown['determined']), ('generic', False))

    def test_sex_and_faction_filters(self):
        topics = {'greeting 1': [info('women', 'Hello.', gender=1), info('guild', 'Brother.', FNAM='Mages Guild'),
                                 info('none', 'Free.', FNAM='FFFF')],
                  'greeting 9': TOPICS['greeting 9']}
        self.assertEqual(dialogue.conversation_greeting(kinds(), topics, 'dreamer_talker07')['info'], 'generic')
        self.assertEqual(dialogue.conversation_greeting(kinds(), topics, 'trader')['info'], 'none')

    def test_clothing_value_of_the_starting_inventory(self):
        self.assertEqual(dialogue.starting_clothing_value(kinds()), 10)
        topics = {'greeting 1': [info('rags', 'Rags!', scvr=[('01424', 20)])], 'greeting 9': TOPICS['greeting 9']}
        self.assertEqual(dialogue.conversation_greeting(kinds(), topics, 'trader')['info'], 'rags')

    def test_defines(self):
        self.assertEqual(dialogue.fill_defines(kinds(), 'trader', 'I am %Name, a %class. You, %pcname the %PCRace?'),
                         'I am Trader Ralen, a Trader. You, %PCName the %PCRace?')
        self.assertIsNone(dialogue.fill_defines(kinds(), 'trader', 'Give me 10%.'))

    def test_talk_fields(self):
        talk = dialogue.talk_greeting(kinds(), TOPICS, 'dreamer_talker07')
        self.assertEqual(talk['first'], 'We have you in our eye, %PCName.')
        self.assertEqual(talk['again'], 'Lord Dagoth has awakened.')
        self.assertEqual(talk['record']['first']['info'], 'first')

    def test_dialogue_records_reader(self):
        def sub(tag, data):
            data = data.encode('cp1252') + b'\0' if isinstance(data, str) else data
            return tag.encode() + struct.pack('<I', len(data)) + data

        def rec(tag, *subs):
            body = b''.join(subs)
            return tag.encode() + struct.pack('<III', len(body), 0, 0) + body
        raw = (rec('GLOB', sub('NAME', 'SleeperOn'), sub('FLTV', struct.pack('<f', 1)))
               + rec('SCPT', sub('SCHD', b'TraderScript'.ljust(52, b'\0')), sub('SCTX', b'short NoLore'))
               + rec('DIAL', sub('NAME', 'Greeting 1'), sub('DATA', bytes([2]))))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.esm'
            path.write_bytes(raw)
            out = dialogue.dialogue_records(path, {'NPC_': {}})
        self.assertEqual(out['DIAL'], {'greeting 1': 2})
        self.assertIn('traderscript', out['SCPT'])
        self.assertEqual(dialogue.globals_of(out), {'sleeperon': 1.0})


if __name__ == '__main__':
    unittest.main()
