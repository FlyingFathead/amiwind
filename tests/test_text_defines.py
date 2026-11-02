"""The game's text defines (BOOK-TEXT-MACROS-58): one getter table (engine/aga/src/aw_textdef.c) fills %PCName and
the rest in books, journal entries, message boxes and dialogue, with OpenMW 0.51's rules (a define is a prefix
match without case; outside dialogue %Name, %Race and %Class are the player's and the speaker-only defines print
nothing; then the game's globals, longest name first; an unknown define prints as written)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_textdef.h"
static const char *const globals[] = {"Day", "DaysPassed", "GameHour", "PCVampire"};
static int global_prefix(const char *text, int run, int *length){
    int g, k, n, best = -1;
    *length = 0;
    for (g = 0; g < 4; g++) {
        n = (int)strlen(globals[g]);
        if (n > run || n <= *length) continue;
        for (k = 0; k < n && (globals[g][k] | 32) == (text[k] | 32); k++);
        if (k == n) { best = g; *length = n; }
    }
    return best;
}
static void global_text(int g, char *out, int capacity){
    if (g == 2) snprintf(out, (size_t)capacity, "%g", 13.5);
    else snprintf(out, (size_t)capacity, "%d", g == 3 ? 1 : g == 1 ? 12 : 3);
}
static const char *action_key(int action){ return action == 11 ? "E" : NULL; }
static void show(const char *label, const char *text, const aw_textdef_values_t *v){
    char out[256];
    AW_TextDefines(out, sizeof(out), text, v);
    printf("%s|%s\n", label, out);
}
int main(void){
    aw_textdef_values_t pc, talk;
    char coded[96], small[8];
    memset(&pc, 0, sizeof(pc));
    pc.pc_name = "Hors"; pc.pc_race = "Dark Elf"; pc.pc_class = "Battlemage"; pc.cell = "Seyda Neen";
    pc.pc_crime = 40; pc.global_prefix = global_prefix; pc.global_text = global_text; pc.action_key = action_key;
    talk = pc;
    talk.speaker = 1; talk.name = "Sellus Gravius"; talk.race = "Imperial"; talk.clas = "Guard";
    talk.faction = "Imperial Legion"; talk.rank = "Knight Errant"; talk.pc_rank = "Recruit"; talk.pc_next_rank = "Spearman";
    show("release", "Name: %PCName Race: %PCRace Class: %PCClass", &pc);
    show("player", "%pcname/%PCRACE/%PcClass^PCName", &pc);
    show("speaker", "%Name %Race %Class %Faction %Rank %Cell", &talk);
    show("outside", "%Name %Race %Class [%Faction][%Rank] %Cell", &pc);
    show("ranks", "%PCRank %PCNextRank %NextPCRank", &talk);
    show("ranks-out", "[%PCRank][%PCNextRank][%NextPCRank]", &pc);
    show("crime", "%PCCrimeLevel gold", &pc);
    show("globals", "%GameHour %DaysPassed %Day %PCVampire", &pc);
    show("unknown", "%PCClothes 50% off %% %", &pc);
    show("action", "%ActionActivate %ActionJump", &pc);
    snprintf(coded, sizeof(coded), "A\001%cB\004%c%cC", AW_TD_PCNAME + 1, 1, 3);
    show("coded", coded, &pc);
    /* the dialogue's link marks (2 and 3) pass through untouched, also right after a code */
    snprintf(coded, sizeof(coded), "Ask \002Balmora\003 \001%c\002x\003", AW_TD_PCNAME + 1);
    show("marks", coded, &talk);
    /* %GameHour: the clock's hour when the values carry the clock, coded or written */
    {
        aw_textdef_values_t clock = talk;
        clock.clock = 1; clock.game_hour = 9.25f;
        snprintf(coded, sizeof(coded), "\001%c|%%GameHour", AW_TD_GAMEHOUR + 1);
        show("clock", coded, &clock);
    }
    /* every speaker define coded, in one pass */
    snprintf(coded, sizeof(coded), "\001%c \001%c \001%c \001%c \001%c \001%c", AW_TD_NAME + 1, AW_TD_RACE + 1,
             AW_TD_CLASS + 1, AW_TD_FACTION + 1, AW_TD_RANK + 1, AW_TD_PCRANK + 1);
    show("speaker-coded", coded, &talk);
    AW_TextDefines(small, sizeof(small), "%PCName%PCName", &pc);
    printf("small|%s\n", small);
    show("null", "%PCName.", NULL);
    printf("names|%s %s %d\n", AW_TextDefineName(AW_TD_PCNAME), AW_TextDefineName(AW_TD_COUNT - 1), AW_TD_COUNT);
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class TextDefineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = Path(tempfile.mkdtemp(prefix='aw-textdef-'))
        try:
            (tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-DAW_TEXTDEF_HOST_TEST',
                                    '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(SRC),
                                    str(tmp / 'h.c'), str(SRC / 'aw_textdef.c'), '-o', str(tmp / 'h')],
                                   capture_output=True, text=True)
            assert built.returncode == 0, built.stdout + built.stderr
            run = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        cls.out = dict(line.split('|', 1) for line in run.splitlines())

    def test_release_identification_filled(self):
        self.assertEqual(self.out['release'], 'Name: Hors Race: Dark Elf Class: Battlemage')

    def test_player_defines_any_case_and_caret(self):
        self.assertEqual(self.out['player'], 'Hors/Dark Elf/BattlemageHors')

    def test_speaker_defines_in_dialogue(self):
        self.assertEqual(self.out['speaker'], 'Sellus Gravius Imperial Guard Imperial Legion Knight Errant Seyda Neen')

    def test_speaker_defines_outside_dialogue(self):
        # the player's name, race and class; faction and rank print nothing (OpenMW: not available outside dialogue)
        self.assertEqual(self.out['outside'], 'Hors Dark Elf Battlemage [][] Seyda Neen')

    def test_rank_defines(self):
        self.assertEqual(self.out['ranks'], 'Recruit Spearman Spearman')
        self.assertEqual(self.out['ranks-out'], '[][][]')

    def test_crime_level(self):
        self.assertEqual(self.out['crime'], '40 gold')

    def test_globals_longest_name_first(self):
        self.assertEqual(self.out['globals'], '13.5 12 3 1')

    def test_unknown_defines_print_as_written(self):
        self.assertEqual(self.out['unknown'], '%PCClothes 50% off %% %')

    def test_global_names_read_once(self):
        # DIALOGUE-OPEN-STALL-58: the global names are kept after one read, not looked up on disk per define
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        body = host[host.index('int AW_MwscriptGlobalPrefix('):]
        body = body[:body.index('\n}\n')]
        self.assertIn('global_names_load();', body)
        self.assertNotIn('COM_FOpenFile', body)
        self.assertNotIn('read_string_from', body)

    def test_action_bindings(self):
        self.assertEqual(self.out['action'], 'E Jump')

    def test_builder_codes(self):
        # code 1 = the getter after it; code 4 = global (1-1)*255 + (3-1) = 2 (GameHour)
        self.assertEqual(self.out['coded'], 'AHorsB13.5C')

    def test_dialogue_link_marks_pass_through(self):
        # DIALOGUE-LINK-MARK-AS-DEFINE-58: the link mark 2 was read as the global code and ate the link's first letters
        self.assertEqual(self.out['marks'], 'Ask \x02Balmora\x03 Hors\x02x\x03')

    def test_game_hour_from_the_clock(self):
        self.assertEqual(self.out['clock'], '9.25|9.25')

    def test_speaker_defines_coded(self):
        self.assertEqual(self.out['speaker-coded'], 'Sellus Gravius Imperial Guard Imperial Legion Knight Errant Recruit')

    def test_capacity_and_no_values(self):
        self.assertEqual(self.out['small'], 'HorsHor')
        self.assertEqual(self.out['null'], '.')
        self.assertEqual(self.out['names'], 'pcname gamehour 33')


class BuilderCodeTests(unittest.TestCase):
    """The builder writes the defines the engine knows as codes (src/mwad/text_defines.py)."""

    @classmethod
    def setUpClass(cls):
        import re
        import sys
        sys.path.insert(0, str(ROOT / 'src'))
        sys.path.insert(0, str(ROOT / 'tools'))
        import text_defines
        cls.td = text_defines
        source = (SRC / 'aw_textdef.c').read_text(encoding='utf-8')
        table = source[source.index('names[AW_TD_COUNT]'):source.index('};', source.index('names[AW_TD_COUNT]'))]
        cls.c_names = tuple(re.findall(r'"([a-z]+)"', table))

    def test_names_equal_the_engine_table(self):
        self.assertEqual(self.td.NAMES, self.c_names)

    def test_release_identification_coded(self):
        text, count = self.td.encode('Name: %PCName Race: %PCRace Class: %PCClass')
        self.assertEqual(count, 3)
        self.assertEqual(text, 'Name: \x01\x06 Race: \x01\x07 Class: \x01\x05')

    def test_globals_unknown_and_lone_percent_stay(self):
        self.assertEqual(self.td.encode('%DaysPassed 50% %PCClothes'), ('%DaysPassed 50% %PCClothes', 0))
        self.assertEqual(self.td.encode('^actionactivate %pccrimelevel')[0], '\x01\x19 \x01\x01')

    def test_game_hour_coded(self):
        # TEXT-MACROS-DIALOGUE-CODES-59: the clock's getter, the last of the table (33 = 1 + 32)
        self.assertEqual(self.td.encode('It is %GameHour.'), ('It is \x01\x21.', 1))

    def test_spans_move_with_the_codes(self):
        # 'As a %PCRank you know my ring.': the link 'my ring' at 22 moves to 22 - len('%PCRank') + 2 = 17
        text, spans, count = self.td.encode_spans('As a %PCRank you know my ring.', [(22, 7, 5)])
        self.assertEqual((text, spans, count), ('As a \x01\x08 you know my ring.', [(17, 7, 5)], 1))
        self.assertEqual(text[17:24], 'my ring')
        # a define inside a link moves its end; a define a link starts or ends inside stays written
        self.assertEqual(self.td.encode_spans('see %Name now', [(4, 9, 1)])[1], [(4, 6, 1)])
        self.assertEqual(self.td.encode_spans('see %Name now', [(6, 3, 1)]), ('see %Name now', [(6, 3, 1)], 0))

    def test_dialogue_stages_write_codes(self):
        for name in ('dialogue_lut.py', 'greeting_lut.py'):
            source = (ROOT / 'tools' / name).read_text(encoding='utf-8')
            self.assertIn('text_defines.', source)
            self.assertIn('text_defines.__file__', source)      # the stage's cache key follows the table

    def test_stages_write_codes(self):
        import struct
        from prepare_world_ui import journal_assets
        books = (ROOT / 'tools/prepare_books.py').read_text(encoding='utf-8')
        self.assertIn('text, _ = text_defines.encode(text)', books)

        def sub(tag, data):
            return tag.encode() + struct.pack('<I', len(data)) + data

        def record(tag, data):
            return tag.encode() + struct.pack('<III', len(data), 0, 0) + data
        raw = (record('DIAL', sub('NAME', b'q\0') + sub('DATA', b'\4')) +
               record('INFO', sub('INAM', b'1\0') + sub('DATA', struct.pack('<iiBbbb', 0, 5, 0, 0, 0, 0)) +
                      sub('NAME', b'Hello %PCName.\0')))
        _, blob, _ = journal_assets(raw)
        self.assertEqual(blob, b'Hello \x01\x06.\0')


class TextDefineWiringTests(unittest.TestCase):
    """Every text path goes through the one table."""

    def code(self, name):
        return (SRC / name).read_text(encoding='utf-8')

    def test_placed_book_fills_defines(self):
        reader = self.code('aw_reader.c')
        self.assertIn('if(!book_defines() || !paginate(book))', reader)
        self.assertIn('AW_TextDefines(out,capacity,source,&v);', reader)

    def test_journal_and_message_box(self):
        self.assertIn('AW_TextDefines(book->text', self.code('aw_worldui.c'))
        self.assertIn('AW_ExpandDialogue(text,sizeof(text),raw);', self.code('aw_msgbox.c'))

    def test_dialogue_goes_through_the_table(self):
        glut = self.code('aw_glut.c')
        self.assertIn('AW_ExpandDialogue(out,capacity,speaker);', glut)     # the previous chain, aw_text_lut 0
        # one pass (TEXT-MACROS-DIALOGUE-CODES-59): the voice table's lines and the conversation's answers
        self.assertIn('if(AW_GlutDefineValues(e,row,&v)){AW_TextDefines(out,capacity,raw,&v);return;}', glut)
        self.assertIn('if(!fill_line(marked,filled,sizeof(filled))){', self.code('aw_dialwin.c'))
        # the link marking keeps a code whole
        self.assertIn('int code=AW_TEXTDEF_CODE_BYTES(text+at);', self.code('aw_dial.c'))

    def test_action_keys_from_the_bindings(self):
        textdef = self.code('aw_textdef.c')
        self.assertIn('v->action_key = AW_TextDefineBoundKey;', textdef)
        keymaps = (ROOT / 'config/keymaps.cfg').read_text(encoding='utf-8')
        table = textdef[textdef.index('action_commands[AW_TD_ACTIONS]'):]
        table = table[:table.index('};')]
        import re
        for command in re.findall(r'"([^"]+)"', table):
            self.assertIn(command, keymaps)        # every command the table names is bound by default

    def test_player_values_from_the_character(self):
        textdef = self.code('aw_textdef.c')
        self.assertIn('v->pc_name = aw_story.name;', textdef)
        self.assertIn('aw_races[aw_character.race].name', textdef)
        self.assertIn('aw_classes[aw_character.clas].name', textdef)
        self.assertIn('aw_textdef.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
