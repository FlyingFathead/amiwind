# SPDX-License-Identifier: GPL-3.0-only
"""DIALOGUE-TEXT-VARIABLES-67: the dialogue's text variables, who may be given an answer that names them, the letters
they are drawn with, and the Goodbye hint while a Choice waits (DIALOGUE-GOODBYE-BLOCKED-HINT-67).

1. An answer with a rank requirement and no faction is for members of the speaker's own faction (OpenMW 0.51
   mwdialogue/filter.cpp testActor, npc.cpp getPrimaryFactionRank: -1 without a faction). The builder read the NPC
   record's rank field instead, 0 for every NPC without a faction in Morrowind.esm, so Hul and Heddvild in Balmora
   answered Background with "I am %Name, %Class and %Rank of the %Faction." and two empty words
   (DIALOGUE-BACKGROUND-EMPTY-RANK-67, DIALOGUE-RANK-WITHOUT-FACTION-67).
2. The table's define check (tools/dialogue_lut.py define_check) fails the image step on an answer whose speaker define
   would be empty for a speaker who can be given it, and on an unknown define.
3. The console fonts draw a game text's Windows-1252 letters as their nearest ASCII (UI-CONSOLE-FONT-SPECIAL-LETTERS-67;
   the drawing itself runs natively in tests/aga_console_test.c).
4. Goodbye greyed out while a Choice waits and the hint when it is chosen (the box itself is measured natively in
   tests/aga_ui_layout_test.c).
Synthetic records only (no game data); seconds."""
import ast
import re
import struct
import sys
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):     # src first (TEST-WORKER-SYSPATH-32)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import dialogue_lut as D  # noqa: E402
import greeting_lut as G  # noqa: E402
import text_defines  # noqa: E402
import mwad.dialogue as dialogue  # noqa: E402
from test_greeting_lut import f, info  # noqa: E402
import test_dialogue_lut as TD  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
MEMBERS = 'I am %Name, %Class and %Rank of the %Faction.'      # the original's Background line for faction members
PLAIN = 'I am %Name, a %Race %Class.'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def body(text, start):
    i = text.index(start)
    return text[i:text.index('\n}', i) + 2]


def coded(name):
    """The builder's code for define NAME in a table text (text_defines.CODE and 1 + its number)."""
    return text_defines.CODE + chr(text_defines.NAMES.index(name) + 1)


def table(topics, glob=None):
    """(table, report, NPC order, topic names) of the dialogue table built from the fixture's NPCs and TOPICS."""
    k = TD.kinds()
    if glob:
        k['GLOB'] = dict(k['GLOB'], **glob)
    k['DIAL'] = {t: 0 for t in topics}
    dials = {t: (t.title() if t != 'info refusal' else 'Info Refusal', 0) for t in topics}
    raw, report = D.build(k, topics, dials)
    t = D.read(raw)
    return t, report, G.plan_npcs(k)[0], [n for n, _ in t['topics']]


class SpeakerRank(unittest.TestCase):
    """The rank an answer asks for without a faction is the speaker's own faction's (filter.cpp testActor): never a
    speaker's without a faction, in both tables."""

    def test_rank_requirement_without_faction(self):
        k = TD.kinds()
        # the fixture's NPC records carry the rank field 0 without a faction, as the original's do
        self.assertEqual(struct.unpack_from('<hBBBB', dict(k['NPC_']['dunmer_m'])['NPDT'])[4], 0)
        members = info('m0', MEMBERS, kind=0, rank=0, disp=30)
        senior = info('m3', MEMBERS, kind=0, rank=3)
        anyone = info('a0', PLAIN, kind=0)
        for ident in ('dunmer_m', 'dunmer_f', 'breton_m', 'imperial_m', 'fargoth'):
            with self.subTest(npc=ident):
                c = D.TopicContext(k, ident, G.NO_CELL)
                self.assertTrue(G.rank_without_faction(c.npc, members))
                self.assertIsNone(c.compile(members))                         # never for a speaker without a faction
                self.assertEqual(c.compile(anyone), [])
                self.assertFalse(G.rank_without_faction(c.npc, anyone))
        mage = D.TopicContext(k, 'mage', G.NO_CELL)
        self.assertFalse(G.rank_without_faction(mage.npc, members))
        self.assertEqual(mage.compile(members), [('Disposition', '', '3', 30)])   # rank 2 >= 0: the disposition left
        self.assertIsNone(mage.compile(senior))                                # rank 2 < 3
        # a named faction: as before (its own rank test)
        guild = info('g0', 'Guild line.', kind=0, rank=2, FNAM='Mages Guild')
        self.assertFalse(G.rank_without_faction(dialogue.speaker(k, 'dunmer_m'), guild))
        self.assertEqual(mage.compile(guild), [])
        self.assertIsNone(D.TopicContext(k, 'dunmer_m', G.NO_CELL).compile(guild))

    def test_the_voice_table_too(self):
        # a greeting that asks for a rank without a faction: only the faction member's candidates hold it
        k = TD.kinds()
        infos = [[info('g6', 'By your actions, you have lost the trust of the %Faction.', kind=2, rank=0),
                  info('g7', 'Hello.', kind=2)]]
        said = {ident: [line for _t, _i, line, _s, _r in G.speaker_entries(k, infos, ident, None)]
                for ident in ('dunmer_m', 'fargoth', 'mage')}
        self.assertEqual(said['dunmer_m'], ['Hello.'])
        self.assertEqual(said['fargoth'], ['Hello.'])
        # (the define kept for the engine, filled from the speaker's row when said)
        self.assertEqual(said['mage'], ['By your actions, you have lost the trust of the %Faction.', 'Hello.'])

    def test_the_shared_filter_is_left_alone(self):
        # the residents' build-time conversation greeting (mwad.dialogue.talk_greeting) keeps the shared filter: a
        # change there keys the CHIM towns again; the tables ask rank_without_faction before it
        source = (ROOT / 'src' / 'mwad' / 'dialogue.py').read_text(encoding='utf-8')
        self.assertIn("        elif rank != -1 and npc['rank'] < rank:\n            return None", source)
        self.assertIn('if G.rank_without_faction(self.npc, fields):\n            return None',
                      (ROOT / 'tools' / 'dialogue_lut.py').read_text(encoding='utf-8'))


class BackgroundAnswers(unittest.TestCase):
    """The original's Background shape: the members' line (rank 0, no faction) before the line for anyone."""

    @classmethod
    def setUpClass(cls):
        cls.t, cls.report, cls.order, cls.names = table({
            'background': [info('m0', MEMBERS, kind=0, rank=0, disp=30), info('a0', PLAIN, kind=0)],
            'info refusal': [info('x1', 'No.', kind=0)]})

    def answers(self, ident):
        return [a[0] for a in D.answers(self.t, self.order.index(ident), self.names.index('Background'))]

    def test_people_without_a_faction_get_the_line_for_anyone(self):
        for ident in ('dunmer_m', 'dunmer_f', 'breton_m', 'fargoth'):
            with self.subTest(npc=ident):
                said = self.answers(ident)
                self.assertEqual(len(said), 1)
                self.assertNotIn(coded('rank'), said[0])
                self.assertNotIn(coded('faction'), said[0])
                self.assertIn(coded('race'), said[0])

    def test_a_member_gets_the_members_line_first(self):
        said = self.answers('mage')
        self.assertEqual(len(said), 2)                                    # the disposition test, then the plain line
        for name in ('name', 'class', 'rank', 'faction'):
            self.assertIn(coded(name), said[0])

    def test_no_empty_or_unknown_define(self):
        d = self.report['defines']
        self.assertEqual((d['empty_count'], d['unknown_count']), (0, 0))
        self.assertEqual(D.define_refusal(self.report), '')
        self.assertEqual(d['uses'], {'class': 2, 'faction': 1, 'name': 2, 'race': 1, 'rank': 1})


class DefineCheck(unittest.TestCase):
    """The table's define check fails the image step (fail fast, in the builder) on an empty or unknown define."""

    def test_a_members_line_given_to_people_without_a_faction_refuses(self):
        # an answer for anyone that names the speaker's faction and rank: what a filter that lets the members' line
        # through gives every speaker without a faction
        t, report, order, names = table({
            'background': [info('f0', 'I serve the %Faction as %Rank.', kind=0), info('a0', PLAIN, kind=0)],
            'info refusal': [info('x1', 'No.', kind=0)]})
        d = report['defines']
        factionless = [i for i in order if not dialogue.speaker(TD.kinds(), i)['faction']]
        self.assertEqual(d['empty_count'], 2 * len(factionless))
        self.assertIn(['fargoth', 'Background', '%faction'], d['empty'])
        self.assertIn(['fargoth', 'Background', '%rank'], d['empty'])
        self.assertEqual(d['data_empty_count'], 0)                        # the mage: Journeyman of the Mages Guild
        why = D.define_refusal(report)
        self.assertIn('DIALOGUE-TEXT-VARIABLES-67', why)
        self.assertIn('breton_m Background %faction', why)                # the first five named, in row order

    def test_the_game_records_own_gaps_are_reported_not_refused(self):
        # the original's own: a faction without rank names (Morrowind.esm's Sixth House, Talos Cult), an answer naming
        # one actor without a faction; drawn empty, as OpenMW draws them
        k = TD.kinds()
        from test_greeting_lut import npc
        k['NPC_'] = dict(k['NPC_'], cultist=npc('cultist', 'Cultist', 'Breton', faction='Talos Cult'))
        k['FACT'] = dict(k['FACT'], **{'talos cult': [f('NAME', 'Talos Cult'), f('FNAM', 'Talos Cult')]})
        topics = {'background': [info('f0', 'I serve the %Faction.', kind=0, ONAM='fargoth'),
                                 info('m0', MEMBERS, kind=0, rank=0), info('a0', PLAIN, kind=0)],
                  'info refusal': [info('x1', 'No.', kind=0)]}
        k['DIAL'] = {name: 0 for name in topics}
        raw, report = D.build(k, topics, {'background': ('Background', 0), 'info refusal': ('Info Refusal', 0)})
        d = report['defines']
        self.assertEqual(d['empty_count'], 0)
        self.assertEqual(sorted(d['data_empty']), [['cultist', 'Background', '%rank'],
                                                   ['fargoth', 'Background', '%faction']])
        self.assertEqual(D.define_refusal(report), '')

    def test_unknown_defines_globals_and_plain_percent_signs(self):
        glob = {'crimegoldturnin': [f('NAME', 'CrimeGoldTurnIn'), f('FNAM', 'l'), ('FLTV', struct.pack('<f', 0.0))]}
        t, report, order, names = table({
            'background': [info('u0', 'You owe %Bogus gold.', kind=0, ONAM='mage'),
                           info('p0', 'Pay %CrimeGoldTurnIn gold. I am 100% sure, %PCRank.', kind=0)],
            'info refusal': [info('x1', 'No.', kind=0)]}, glob=glob)
        d = report['defines']
        self.assertEqual(d['unknown_count'], 1)
        self.assertEqual(d['unknown'], [['Background', '%Bogus']])
        self.assertEqual(d['empty_count'], 0)
        self.assertEqual(d['uses']['global'], 1)
        # %PCRank of a speaker without a faction: '%', as OpenMW (getPCRank); counted, not refused
        self.assertEqual(d['pc_rank_without_faction'], sum(1 for i in order if not dialogue.speaker(TD.kinds(), i)['faction']))
        self.assertIn('%Bogus', D.define_refusal(report))

    def test_the_image_step_refuses(self):
        source = (ROOT / 'tools' / 'dialogue_lut.py').read_text(encoding='utf-8')
        step = source[source.index('def image_step('):source.index('def main(')]
        self.assertLess(step.index('why = define_refusal(report)'), step.index('target.write_bytes(raw)'))
        self.assertIn("report['defines'] = define_check(table, keep, facts, kinds.get('GLOB', {}))",
                      source[source.index('def build('):source.index('AMIGA_ANSWER')])


class ConsoleFontLetters(unittest.TestCase):
    """UI-CONSOLE-FONT-SPECIAL-LETTERS-67: the console fonts' Windows-1252 table, against the code page itself."""

    @classmethod
    def setUpClass(cls):
        glyphs = code('aw_console_glyphs.c')
        start = glyphs.index('static const char cp1252_plain[129]=')
        block = glyphs[start:glyphs.index(';', start)]
        cls.plain = ''.join(ast.literal_eval(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', block))
        cls.glyphs = glyphs

    def test_every_character_has_a_printable_ascii_one(self):
        self.assertEqual(len(self.plain), 128)
        self.assertTrue(all(32 <= ord(c) <= 126 for c in self.plain))

    def test_letters_lose_their_accents(self):
        own = {'Æ': 'A', 'æ': 'a', 'Ð': 'D', 'ð': 'd', 'Ø': 'O', 'ø': 'o', 'Þ': 'T', 'þ': 't', 'ß': 's', '×': 'x',
               '÷': '/', 'Œ': 'O', 'œ': 'o', '€': 'E', 'ƒ': 'f', '™': 'T'}
        for b in range(0x80, 0x100):
            try:
                ch = bytes([b]).decode('cp1252')
            except UnicodeDecodeError:
                continue                                                      # 0x81 0x8D 0x8F 0x90 0x9D: unused
            base = unicodedata.normalize('NFKD', ch)[0]
            if ch in own:
                expected = own[ch]
            elif base.isascii() and base.isalpha():
                expected = base
            else:
                continue
            with self.subTest(byte=hex(b), char=ch):
                self.assertEqual(self.plain[b - 0x80], expected)

    def test_punctuation_and_the_letters_of_the_dialogue(self):
        want = {'’': "'", '‘': "'", '“': '"', '”': '"', '„': '"', '‚': ',', '–': '-', '—': '-', '…': '.', '\xa0': ' ',
                '«': '<', '»': '>', '•': '*', '´': "'",
                # the dialogue texts' three (the masters' INFO texts, 2026-11-18): He’ll, protégé, gro-Muzgúb
                'é': 'e', 'ú': 'u'}
        for ch, expected in want.items():
            with self.subTest(char=ch):
                self.assertEqual(self.plain[ch.encode('cp1252')[0] - 0x80], expected)

    def test_every_console_font_draw_goes_through_it(self):
        self.assertNotIn('c&=127', self.glyphs)
        self.assertIn('int r,col,bits;byte *p;c=AW_ConsoleTextGlyph(c);', body(self.glyphs, 'void AW_ConsoleCharacter(int x,int y,int c) {'))
        self.assertIn('c=AW_ConsoleTextGlyph(c);', body(self.glyphs, 'void AW_ConsoleCharacterRed('))
        self.assertIn('c=AW_ConsoleTextGlyph((unsigned char)*text);', body(self.glyphs, 'void AW_SmallString('))
        self.assertIn('c=AW_ConsoleTextGlyph((unsigned char)*text);', body(self.glyphs, 'void AW_SmallStringColor('))
        self.assertIn('int AW_ConsoleTextGlyph(int c);', code('quakedef.h'))


class GoodbyeHint(unittest.TestCase):
    """DIALOGUE-GOODBYE-BLOCKED-HINT-67: OpenMW 0.51 disables Goodbye and the topic list while a Choice is open
    (DialogueWindow::updateTopicsPane); AmiWind draws Goodbye greyed with the topics and, when it is chosen anyway (its
    button or Escape), shows "Continue the conversation first." over the window through the shared layout."""

    def test_goodbye_greyed_and_the_hint(self):
        win = code('aw_dialwin.c')
        self.assertIn('#define CONTINUE_FIRST "Continue the conversation first."', win)
        draw = body(win, 'static void draw(void){')
        self.assertIn('if(choice_count)for(;*g && x+char_w()<=right;g++,x+=char_w())char_in(x,button_y(),'
                      '(unsigned char)*g,AW_UIColor(96,90,80));', draw)
        self.assertIn('if(choice_count && hint_until>realtime)AW_UIHintBox(BOX_X,BOX_Y,BOX_W,BOX_H,CONTINUE_FIRST,2);',
                      draw)
        # the hint is drawn last, over the list and the conversation
        self.assertGreater(draw.index('AW_UIHintBox('), draw.index('draw_bar(BAR_LIST);'))
        keys = body(win, 'static int choice_key(int k,int mouse_x,int mouse_y){')
        self.assertIn('case K_ESCAPE:hint_until=realtime+AW_MsgBoxSeconds(CONTINUE_FIRST);return 1;', keys)
        self.assertIn('if(on_goodbye(mouse_x,mouse_y)){hint_until=realtime+AW_MsgBoxSeconds(CONTINUE_FIRST);return 1;}',
                      keys)
        # Goodbye's button is one hit test for the choice keys and the window's keys
        self.assertIn('if(on_goodbye(mouse_x,mouse_y))return 0;', body(win, 'static int key(int k,int mouse_x,int mouse_y){'))
        # the hint goes when the row is picked and when the window closes
        self.assertIn('choice_count=0;choice_focus=-1;hint_until=0;', body(win, 'static void pick_choice(int k){'))
        self.assertIn('choice_count=0;choice_focus=-1;hint_until=0;', body(win, 'static void release(void){'))

    def test_the_hint_box_is_the_shared_layout(self):
        ui = code('aw_ui.c')
        hint = body(ui, 'int AW_UIHintBox(int x,int y,int w,int h,const char *text,int most) {')
        self.assertIn('bh=AW_LayoutBoxHeight(AW_UICenteredLinesInk(bw,text,most),0,0,0);', hint)
        self.assertIn('AW_LayoutBox(&l,x+(w-bw)/2,y+(h-bh)/2,bw,bh,0,0,NULL,0);', hint)
        self.assertIn('AW_UICenteredLinesUpTo(l.box[0],l.content[1],l.box[2],l.content[3],text,most);', hint)
        self.assertIn('int AW_UIHintBox(int x,int y,int w,int h,const char *text,int most);', code('quakedef.h'))


if __name__ == '__main__':
    unittest.main()
