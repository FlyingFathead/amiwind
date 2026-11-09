# SPDX-License-Identifier: GPL-3.0-only
"""Levelling (LEVEL-UP-58, docs/CHARACTER_CREATION.md "Levelling"): the rules in host C, the builder's data file
from synthetic records, and the source contracts that wire the skill uses, the save, the box and the dbg route in."""
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class LevelupNativeTests(unittest.TestCase):
    def test_rules_requirement_use_raises_multipliers_box_level_up_and_picture(self):
        native.NativeSourceTests().compile_run('aga_levelup_rules_test.c', [SRC / 'aw_levelup_rules.c'], cflags=UBSAN)

    def test_rest_rules_restoration_until_healed_interruption_refusals_and_beds(self):
        native.NativeSourceTests().compile_run('aga_rest_rules_test.c', [SRC / 'aw_rest_rules.c'], cflags=UBSAN)


def gmst(name, value):
    if name[0] == 'f':
        return {'NAME': name.encode() + b'\0', 'FLTV': struct.pack('<f', value)}
    if name[0] == 'i':
        return {'NAME': name.encode() + b'\0', 'INTV': struct.pack('<i', value)}
    return {'NAME': name.encode() + b'\0', 'STRV': value.encode('cp1252')}


def fixture_kinds():
    import prepare_levelup as p
    values = dict(zip(p.SETTINGS, (.75, 1.0, 1.25, .8, .1, 10, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 4, 4, 5)))
    kinds = {'GMST': {n.casefold(): gmst(n, v) for n, v in values.items()}, 'SKIL': {}, 'SOUN': {}}
    kinds['GMST']['snotifymessage39'] = gmst('sNotifyMessage39', 'Your %s skill increased to %d.')
    kinds['GMST']['slevelupmsg'] = gmst('sLevelUpMsg', 'Rest now.\n')
    for i in range(27):
        kinds['SKIL'][i] = {'INDX': struct.pack('<i', i), 'SKDT': struct.pack('<ii4f', i % 8, i % 3, 1 + i, .5, 0, 0)}
    return kinds


class LevelupBuilderTests(unittest.TestCase):
    def test_settings_text_has_every_setting_skill_row_text_and_level(self):
        import prepare_levelup as p
        text = p.settings_text(fixture_kinds(), {2: 'Two.', 3: 'Three.'}, 'levelup/skillraise.wav')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'AWLU1')
        self.assertIn('set fMajorSkillBonus 0.75', lines)
        self.assertIn('set iLevelupMiscMultAttriubte 1', lines)
        self.assertIn('set iLevelUp10Mult 5', lines)
        self.assertEqual(len([l for l in lines if l.startswith('set ')]), 22)
        self.assertIn('skill 5 5 2 6 0.5 0 0', lines)
        self.assertEqual(len([l for l in lines if l.startswith('skill ')]), 27)
        self.assertIn('sound skillraise levelup/skillraise.wav', lines)
        self.assertIn('text sNotifyMessage39 Your %s skill increased to %d.', lines)
        self.assertIn('text sLevelUpMsg Rest now.', lines)          # control characters folded away
        self.assertNotIn('sLevelUpMenu2', text)                     # a missing line is left out, never invented
        self.assertIn('level 2 Two.', lines)
        self.assertTrue(text.endswith('\n'))

    def test_engine_and_builder_agree_on_the_settings(self):
        import prepare_levelup as p
        names = re.findall(r'"(\w+)"', code('aw_levelup_rules.c').split('setting_names[AW_LEVELUP_SETTING_COUNT]={')[1]
                           .split('};')[0])
        self.assertEqual(tuple(names), p.SETTINGS)
        pictures = set(re.findall(r'"(\w+)"', code('aw_levelup_rules.c').split('AW_LevelupClassImage')[1]
                                  .split('void AW_LevelupBoxOpen')[0]))
        self.assertEqual(pictures, set(p.PICTURES))

    def test_missing_setting_or_skill_refuses(self):
        import prepare_levelup as p
        kinds = fixture_kinds()
        del kinds['GMST']['ilevelup07mult']
        with self.assertRaises(ValueError):
            p.settings_text(kinds, {}, None)
        kinds = fixture_kinds()
        del kinds['SKIL'][26]
        with self.assertRaises(ValueError):
            p.settings_text(kinds, {}, None)

    def test_skill_books_list(self):
        """SKILL-BOOKS-MISSING-62: every live book with a skill, in folded ID order, its index its read-list bit."""
        import prepare_levelup as p

        def record(tag, subs, flags=0):
            body = b''.join(k.encode() + struct.pack('<I', len(v)) + v for k, v in subs)
            return tag.encode() + struct.pack('<III', len(body), 0, flags) + body

        def book(ident, skill, flags=0, extra=()):
            return record('BOOK', [('NAME', ident.encode() + b'\0'),
                                   ('BKDT', struct.pack('<fiiii', 1.0, 10, 0, skill, 0))] + list(extra), flags)
        raw = (book('BookSkill_Axe2', 6) + book('bookskill_alchemy1', 16) + book('BK_plain', -1) +
               book('bk_gone', 3, flags=0x20) + book('bk_dele', 3, extra=[('DELE', b'\0\0\0\0')]) +
               book('bk two words', 25) + record('MISC', [('NAME', b'thing\0')]))
        text, count = p.books_text(raw)
        self.assertEqual(count, 3)
        self.assertEqual(text.splitlines(), ['AWLB1', 'book 0 25 bk two words', 'book 1 16 bookskill_alchemy1',
                                             'book 2 6 bookskill_axe2'])
        self.assertIn('sBookSkillMessage', p.TEXTS)
        self.assertEqual(p.BOOKS_MAX, int(re.search(r'#define AW_BOOKS_READ_MAX (\d+)',
                                                    (SRC / 'aw_character.h').read_text(encoding='utf-8')).group(1)))

    def test_level_texts_from_the_install_ini(self):
        import prepare_levelup as p
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'Data Files'
            data.mkdir()
            self.assertEqual(p.ini_levels(data), {})
            (Path(folder) / 'Morrowind.ini').write_bytes(b'[Level Up]\r\nLevel2=First  words.\r\nLevel3=Second.\r\n'
                                                         b'Default=Other.\r\n[Weather]\r\nLevel4=no\r\n')
            self.assertEqual(p.ini_levels(data), {2: 'First words.', 3: 'Second.'})


class LevelupSourceContractTests(unittest.TestCase):
    def test_skill_uses_are_reported_where_they_happen(self):
        combat = code('aw_combat.c')
        self.assertIn('AW_LevelupUse(AW_SK_BLOCK,0,1);', combat)
        self.assertIn('AW_LevelupUse(you.weapon?you.weapon_skill:AW_SK_H2H,0,1);', combat)
        self.assertIn('AW_LevelupUse(c==1?AW_SK_LIGHT:c==2?AW_SK_MEDIUM:c==3?AW_SK_HEAVY:AW_SK_UNARMORED,0,1);', combat)
        move = code('aw_move.c')
        self.assertIn('if(jumped)AW_LevelupUse(AW_LU_ACROBATICS,AW_USE_JUMP,1);', move)
        self.assertIn('(p->v.button2 || prev_jump)', move)     # a tapped jump counts (SKILL-RAISE-NOT-SEEN-62)
        self.assertIn('AW_LevelupMoveSeconds(', move)
        self.assertIn('AW_LevelupRaise(which,AW_RAISE_TRAINER)', code('aw_dialwin.c'))
        self.assertIn('AW_LevelupUse(25,r.success?0:1,1);', code('aw_dialwin.c'))
        # Mercantile_Success once per accepted trade, after the trade, scaled by the share haggled
        trade = code('aw_dialwin.c').split('static void trade(int k){')[1].split('\n}')[0]
        self.assertEqual(trade.count('AW_LevelupUse('), 1)
        self.assertLess(trade.index('AW_MwscriptTrade('), trade.index(
            'AW_LevelupUse(AW_LU_MERCANTILE,AW_USE_MERCANTILE_SUCCESS,AW_LevelupMercantileScale(buying,price,price));'))

    def test_the_box_has_no_cancel(self):
        ui = code('aw_worldui.c')
        self.assertLess(ui.index('if(key==K_ESCAPE && modal==4 && aw_worldui_panel_holds_escape)'),
                        ui.index('if(key==K_ESCAPE || (modal==1'))
        self.assertIn('aw_worldui_panel_holds_escape=0;', ui.split('static void close_panel(void){')[1][:80])
        box = code('aw_levelup.c')
        self.assertIn('aw_worldui_panel_holds_escape=1;', box)
        self.assertIn('if(key==K_ESCAPE)return 1;', box)

    def test_save_carries_the_levelling(self):
        codec = code('aw_save_codec.c')
        self.assertIn('(levelling_used(&copy.character)?64U:0U)', codec)
        self.assertIn("if(!error && data[3]=='4' && (features&64))levelling_fields(&candidate.character);", codec)
        # bit 128: the dated journal history (JOURNAL-ORIGINAL-VIEW-59), 256: up to 128 kinds of item, 512: any number
        # of kinds (INVENTORY-ORIGINAL-LIMITS-61)
        # bit 1024: the skill books read (SKILL-BOOKS-MISSING-62)
        self.assertIn('if(features>2047)error=1;', codec)
        self.assertIn('(books_words(&copy.character)?1024U:0U)', codec)
        self.assertIn("if(!error && data[3]=='4' && (features&1024))books_fields(&candidate.character);", codec)

    def test_skill_book_read_and_held_raise_line(self):
        # SKILL-BOOKS-MISSING-62: the placed book's reader reports the read; the rule marks it read once
        self.assertIn('AW_LevelupBookRead(id);', code('aw_reader.c'))
        lu = code('aw_levelup.c')
        self.assertIn('return AW_LevelupRaise(book_skill,AW_RAISE_BOOK);', lu)
        self.assertIn('if(aw_character.books_read[index>>5]&bit)return 0;', lu)
        # SKILL-RAISE-NOT-SEEN-62: the raise line is held against the same blow's voice and hit lines
        self.assertIn('AW_UIHeldNotice(line,due?6:4,3);', lu)
        self.assertNotIn('AW_UISubtitle("",line,due?6:4)', lu)
        # LEVEL-UP-INGAME-62: Acrobatics from a landing that hurt without a knockdown
        self.assertIn('if(!knockdown)AW_LevelupUse(AW_LU_ACROBATICS,AW_USE_FALL,1);', code('aw_move.c'))

    def test_engine_wiring_build_route_and_budget(self):
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn(' aw_levelup_rules.c aw_levelup.c ', make)
        self.assertIn('AW_LevelupInit();', code('aw_debug.c'))
        self.assertIn('Cmd_AddCommand("aw_levelup",levelup_command);', code('aw_levelup.c'))
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('PLAYTESTING|levelup|aw_levelup|', catalogue)
        self.assertIn('PLAYTESTING|skill progress|aw_levelup|', catalogue)
        budget = json.loads((ROOT / 'tests/resident_registry_budget.json').read_text(encoding='utf-8'))
        self.assertIn('aw_levelup', budget['entries']['commands'])
        combat = (ROOT / 'tools/prepare_combat.py').read_text(encoding='utf-8')
        self.assertIn("report['levelup'] = prepare_levelup(data_files, id1)", combat)
        self.assertIn('triumph_id=manual_lookup("mw_triumph",&group);', code('aw_music.c'))
        shipped = set(json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8')))
        for path in ('engine/aga/src/aw_levelup.c', 'engine/aga/src/aw_levelup.h', 'engine/aga/src/aw_levelup_rules.c',
                     'tools/prepare_levelup.py', 'tests/aga_levelup_rules_test.c', 'tests/test_levelup.py'):
            self.assertIn(path, shipped)

    def test_docs_describe_levelling(self):
        docs = (ROOT / 'docs/CHARACTER_CREATION.md').read_text(encoding='utf-8')
        self.assertIn('## Levelling', docs)
        self.assertIn('dbg levelup', docs)
        self.assertIn('Levelling', (ROOT / 'docs/COMBAT.md').read_text(encoding='utf-8'))


class SpawnHealthTests(unittest.TestCase):
    """PLAYER-HEALTH-OVER-MAX-63: a map loaded fresh (a console map, a restart) gave the player Quake's 100 of a
    sheet maximum of 40; the spawn takes the sheet's health, never above its maximum."""

    def test_fresh_spawn_takes_the_sheet_health_capped_at_the_maximum(self):
        scene = code('aw_scene.c')
        spawn = scene[scene.index('void AW_SceneSpawn(edict_t *p)'):scene.index('void AW_SceneTick(void)')]
        fresh = spawn[spawn.index('aw_scene_followers(p,-1)'):spawn.index('AW_IntroSpawn();')]
        self.assertIn('if(aw_character.valid && aw_character.maximum[0]>0)', fresh)
        self.assertIn('p->v.health=aw_character.current[0]>0&&aw_character.current[0]<=aw_character.maximum[0]?'
                      'aw_character.current[0]:aw_character.maximum[0];', re.sub(r'\s+', '', fresh))
        # a load sets its own health after this
        self.assertLess(spawn.index('aw_character.maximum[0]>0'), spawn.index('AW_SaveSpawn();'))

    def test_the_fight_sheet_reads_the_characters_maxima_and_caps_the_current(self):
        # v0.0.63-dev5 release check: in the arena after dbg maxstats the status read 920/93: the set fighter's
        # maximum (93) beside the entity's health (920, the sheet's new maximum). The fight sheet takes the
        # character's maxima (the arena copies the set fighter's into the character at the start) and never a
        # current value above them, with a set fighter and without
        combat = code('aw_combat.c')
        sheet = combat[combat.index('void AW_CombatPlayerSheet(aw_fighter_t *o) {'):]
        sheet = sheet[:sheet.index('\n}\n')]
        preset = sheet[sheet.index('if(aw_combat_player_preset){'):sheet.index('return;')]
        self.assertIn('if(aw_character.valid && aw_character.maximum[0]>o->health_max)o->health_max=aw_character.maximum[0];',
                      preset)
        self.assertIn('if(aw_character.valid && aw_character.maximum[2]>o->fatigue_max)o->fatigue_max=aw_character.maximum[2];',
                      preset)
        self.assertIn('if(o->health>o->health_max)o->health=o->health_max;', preset)
        self.assertIn('if(o->fatigue>o->fatigue_max)o->fatigue=o->fatigue_max;', preset)
        own = sheet[sheet.index('return;'):]
        self.assertIn('if(o->health>o->health_max)o->health=o->health_max;', own)
        arena = code('aw_arena.c')
        self.assertIn('aw_character.maximum[0]=player_preset.health_max;', arena)


if __name__ == '__main__':
    unittest.main()
