# SPDX-License-Identifier: GPL-3.0-only
"""Melee combat for every NPC and the Vivec Arena debug minigame (docs/COMBAT.md):
the rules (host C), the engine layer and the minigame with synthetic servers, the
builder's combat data, and the source contracts that keep the layer shared, cheap,
deterministic and wired in."""
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import wave
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
class CombatNativeTests(unittest.TestCase):
    def test_rules_hit_chance_damage_armour_block_knockdown_fatigue_and_rolls(self):
        native.NativeSourceTests().compile_run('aga_combat_rules_test.c', [SRC / 'aw_combat_rules.c'], cflags=UBSAN)

    def test_engine_layer_chase_swings_punch_bar_music_death_and_residents(self):
        native.NativeSourceTests().compile_run(
            'aga_combat_test.c', [SRC / n for n in ('aw_combat.c', 'aw_combat_rules.c', 'aw_npcpath.c', 'mathlib.c', 'aw_anim.c')],
            defines=('AW_ANIM_HOST_TEST',), cflags=UBSAN)

    def test_carried_item_tags_parse_and_pose(self):
        native.NativeSourceTests().compile_run('aga_items_test.c', [SRC / 'aw_items.c'],
                                               defines=('AW_ITEMS_HOST_TEST',), cflags=UBSAN)

    def test_arena_minigame_choice_map_spawn_title_fight_result_and_keys(self):
        native.NativeSourceTests().compile_run('aga_arena_test.c', [SRC / n for n in ('aw_arena.c', 'mathlib.c')],
                                               defines=('_GNU_SOURCE',), cflags=UBSAN)


class CombatSourceContractTests(unittest.TestCase):
    def test_no_allocation_and_no_unseeded_randomness(self):
        for name in ('aw_combat.c', 'aw_combat_rules.c', 'aw_arena.c'):
            with self.subTest(name=name):
                text = code(name)
                self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', text))
                self.assertIsNone(re.search(r'\b(rand|srand|random)\s*\(', text))

    def test_settings_names_match_the_builder(self):
        names = re.findall(r'"(\w+)"', code('aw_combat_rules.c').split('names[AW_COMBAT_SETTING_COUNT]={')[1].split('};')[0])
        import prepare_combat
        self.assertEqual(tuple(names), prepare_combat.SETTINGS)
        count = int(re.search(r'#define AW_COMBAT_SETTING_COUNT (\d+)', code('aw_combat.h')).group(1))
        self.assertEqual(count, len(names))

    def test_miss_presentation_never_changes_the_resolved_swing(self):
        # docs/ROADMAP.md miss feedback: resolve once at contact, react only from
        # the chase state, no block effects for a cosmetic block, block clip on contact.
        combat = code('aw_combat.c')
        react = combat[combat.index('static void npc_react_miss'):combat.index('static void player_react_miss')]
        self.assertIn("s->state!=S_CHASE", react)
        self.assertIn('start_block(s)', react)
        self.assertNotIn('AW_CombatSwing', react)
        self.assertNotIn('shield_health', react)
        player = combat[combat.index('static void player_react_miss'):combat.index('static void player_dodge_step')]
        self.assertIn('punch_started>=0 && !punch_struck', player)
        self.assertNotIn('AW_CombatSwing', player)
        start = combat[combat.index('static void start_block'):combat.index('static void npc_react_miss')]
        self.assertIn('*block_hit', start)
        self.assertEqual(combat.count('AW_CombatSwing('), 2)        # one per strike, at the hit key

    def test_right_mouse_button_default_bind(self):
        # COMPANION-PICK-RMB-33: the Amiga right button arrives as MOUSE3 (vid_amiga.c maps
        # IECODE_RBUTTON to K_MOUSE3, the middle button to K_MOUSE2); the default keymap and the
        # saved-config migration bind it to the context action +aw_alt, which picks in pick mode.
        video = code('vid_amiga.c')
        self.assertLess(video.index('IECODE_RBUTTON:'), video.index('Key_Event (K_MOUSE3, true)'))
        self.assertIn('bind "MOUSE3" +aw_alt', (ROOT / 'config' / 'keymaps.cfg').read_text(encoding='utf-8'))
        self.assertIn('Key_SetBinding(K_MOUSE3,"+aw_alt")', code('keys.c'))
        combat = code('aw_combat.c')
        self.assertIn('Cmd_AddCommand("+aw_alt",alt_down)', combat)
        self.assertIn('if(AW_CompanionPickAim())return;', combat)
        self.assertIn('int AW_CompanionPickAim(void)', code('aw_companion.c'))

    def test_world_loadout_uses_the_arena_sheets(self):
        combat = code('aw_combat.c')
        world = combat[combat.index('static void loadout_command'):combat.index('static void command')]
        self.assertIn('AW_CombatLoadout(name,&world_loadout,used)', world)
        self.assertIn('aw_combat_player_preset==&world_loadout', world)   # off never clears the arena's sheet
        self.assertIn('loadout NAME/off', (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8'))

    def test_shared_layer_is_wired_in(self):
        physics = code('sv_phys.c')
        self.assertLess(physics.index('AW_CompanionPhysics ()'), physics.index('AW_CombatPhysics ()'))
        scene = code('aw_scene.c')
        self.assertLess(scene.index('if(aw_combat_scene)aw_combat_scene();'), scene.index('AW_GallerySpawn(p);'))
        self.assertIn('AW_CombatInit();', code('aw_debug.c'))
        self.assertIn('aw_combat_enemy_bar(&fraction,&alpha))AW_UIEnemyBar(fraction,alpha);', code('aw_ui.c'))
        self.assertIn('y=vid.height-26-9', code('aw_ui.c'))   # just above the health bar
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_companion.c aw_combat_rules.c aw_combat.c aw_items.c aw_arena.c', makefile)
        gallery = code('aw_gallery.c')
        self.assertIn('AW_ArenaInit();', gallery)
        self.assertIn('arena_here());', gallery)               # attacks are not stripped in the arena
        # the combat layer acts on any resident, not an arena-only path
        combat = code('aw_combat.c')
        self.assertIn('GetEdictFieldValue(t,"aw_source_id")', combat)
        self.assertIn('AW_CombatActorLoad(id,&sheet)', combat)

    def test_battle_music_rule_and_death_track(self):
        music = code('aw_music.c')
        body = music[music.index('void AW_MusicCombat(int on)'):]
        body = body[:body.index('\n}')]
        for guard in ('!available', 'held', 'title_playing', 'counts[want]<1'):
            self.assertIn(guard, body)
        self.assertIn('advance(want?"combat":"combat-end")', body)
        death = music[music.index('void AW_MusicDeath(void)'):]
        self.assertIn('manual_lookup("mw_death",&g)', death[:400])
        combat = code('aw_combat.c')
        self.assertIn('AW_MusicCombat(want)', combat)
        self.assertIn('AW_MusicDeath()', combat)

    def test_commands_aliases_and_docs(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        routes = {line.split('|')[1]: line.split('|')[2] for line in catalogue.splitlines()
                  if line.count('|') == 3 and not line.startswith('#')}
        for word in ('arenapit', 'battlearena', 'arenatest', 'arena'):
            self.assertEqual(routes[word], 'aw_arenapit', word)
        self.assertEqual(routes['combattest'], 'aw_combattest')
        self.assertEqual(routes['combat'], 'aw_combat')
        self.assertIn('combattest gallery', catalogue)
        arena = code('aw_arena.c')
        for handler in ('aw_arenapit', 'dbgmode', 'testarena'):
            self.assertIn('Cmd_AddCommand("%s",' % handler, arena)
        self.assertIn('Cmd_AddCommand("aw_combat",', code('aw_combat.c'))
        docs = (ROOT / 'docs' / 'COMBAT.md').read_text(encoding='utf-8')
        for words in ('dbgmode arenapit', 'dbg battlearena', 'dbg arenatest', 'testarena', 'dbg arena',
                      'dbg combattest gallery', 'dbg combat readout', 'aw_combat_seed', 'fNPCHealthBarTime',
                      'battle', 'OpenMW'):
            self.assertIn(words, docs)
        changelog = (ROOT / 'docs' / 'CHANGELOG.md').read_text(encoding='utf-8')
        unreleased = changelog[changelog.index('## v0.0.33: '):]
        unreleased = unreleased[:unreleased.index('\n## ', 5)]
        self.assertIn('dbgmode arenapit', unreleased)
        self.assertIn('dbg combattest gallery', unreleased)
        shipped = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for path in ('engine/aga/src/aw_combat.c', 'engine/aga/src/aw_combat_rules.c', 'engine/aga/src/aw_combat.h',
                     'engine/aga/src/aw_arena.c', 'tools/prepare_combat.py', 'config/arena_fighters.json',
                     'docs/COMBAT.md', 'tests/test_combat.py', 'tests/aga_combat_rules_test.c',
                     'tests/aga_combat_test.c', 'tests/aga_arena_test.c'):
            self.assertIn(path, shipped)

    def test_image_step_builds_the_combat_data_by_default(self):
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("combat_report=prepare_combat(args.data_files,boot/'id1',jobs=jobs)", build)
        self.assertIn("'combat_data':combat_summary(combat_data)", build)
        import build_aga
        self.assertEqual(build_aga.combat_summary(None), {'status': 'not_built'})
        summary = build_aga.combat_summary({'actors': {'count': 2}, 'sounds': {'miss': {}, 'health': {}},
                                            'fighters': {'a': {'model': 'arena/f.mdl', 'bytes': 9, 'frames': 31, 'x': 1}}})
        self.assertEqual(summary['sounds'], ['health', 'miss'])
        self.assertEqual(summary['fighters']['a'], {'model': 'arena/f.mdl', 'bytes': 9, 'frames': 31})
        ui = (ROOT / 'tools' / 'prepare_ui.py').read_text(encoding='utf-8')
        self.assertIn("atlas.paste(yellow, (48,32), yellow)", ui)


def rec(tag, data):
    return (tag, data)


class CombatBuilderTests(unittest.TestCase):
    def test_carried_weapon_and_shield_parts(self):
        # NPC-WEAPON-MESH-33: weapon = its own model on Weapon Bone; shield = the armour's
        # Shield body part (female CNAM for women), else its ground model, on Shield Bone.
        from mwad.npc import carried_parts
        z = lambda s: s.encode() + b'\0'
        kinds = {'WEAP': {'sword': [('NAME', z('sword')), ('MODL', z('w\\sword.nif'))]},
                 'ARMO': {'shield': [('NAME', z('shield')), ('MODL', z('a\\shield_gnd.nif')), ('INDX', bytes([10])),
                                     ('BNAM', z('shield_m')), ('CNAM', z('shield_f'))],
                          'buckler': [('NAME', z('buckler')), ('MODL', z('a\\buckler_gnd.nif'))]},
                 'BODY': {'shield_m': [('MODL', z('a\\shield_m.nif'))], 'shield_f': [('MODL', z('a\\shield_f.nif'))]}}
        parts = carried_parts(kinds, {'weapon': 'Sword', 'shield': 'shield'}, female=False)
        self.assertEqual([(p['attach'], p['mesh'], p['slot']) for p in parts],
                         [('Weapon Bone', 'w\\sword.nif', 25), ('Shield Bone', 'a\\shield_m.nif', 10)])
        self.assertEqual(carried_parts(kinds, {'shield': 'shield'}, female=True)[0]['mesh'], 'a\\shield_f.nif')
        self.assertEqual(carried_parts(kinds, {'shield': 'buckler'}, female=False)[0]['mesh'], 'a\\buckler_gnd.nif')
        self.assertEqual(carried_parts(kinds, {'weapon': None, 'shield': None}, female=False), [])
        with self.assertRaises(ValueError):
            carried_parts(kinds, {'weapon': 'nothing'}, female=False)
        bake = (ROOT / 'tools' / 'prepare_combat.py').read_text(encoding='utf-8')
        self.assertIn("appearance = outfit(kinds, identifier, carried=carried)", bake)   # the rules' own pick
        self.assertIn("b'rootcollisionnode'", (ROOT / 'tools' / 'npc_geometry.py').read_text(encoding='utf-8'))

    def test_item_tags_angles_and_file(self):
        # tools/npc_items.py: Quake angles round trip (AngleVectors convention), tag rows from a
        # bone pose (scaled like the vertices), the tag file the engine parses (aw_items.c).
        import numpy as np
        import npc_items
        for angles in ((0, 0, 0), (10, 20, 30), (-45, 170, -60), (80, -90, 5)):
            back = npc_items.quake_angles(npc_items.angle_matrix(*angles))
            np.testing.assert_allclose(back, angles, atol=1e-6)

        class Pose:
            N = None
            def pose(self, t):
                def bone(name):
                    m = np.eye(4)
                    m[:3, :3] = npc_items.angle_matrix(0, 90, 0)
                    m[3, :3] = (4.0 * (t + 1), 8.0, 12.0)
                    return m
                return bone
        rows = npc_items.bone_tags(Pose(), [0, 1], {'weight': 1.0, 'height': 2.0}, {'weapon': True})
        np.testing.assert_allclose(rows[0][:6], [1.0, 2.0, 6.0, 0.0, 90.0, 0.0], atol=1e-6)
        np.testing.assert_allclose(rows[1][:3], [2.0, 2.0, 6.0], atol=1e-6)
        self.assertEqual(rows[0][6:], [0.0] * 6)                       # no shield
        text = npc_items.tag_text(rows, {'weapon': 'items/w0123456789ab.mdl'})
        self.assertTrue(text.startswith('AWTG1 2\nweapon items/w0123456789ab.mdl\nshield -\n'))
        self.assertEqual(len(text.splitlines()), 5)
        self.assertEqual(npc_items.item_stem('weapon', 'W\\Mace.nif'), npc_items.item_stem('weapon', 'w\\mace.nif'))
        area = (ROOT / 'tools' / 'prepare_area.py').read_text(encoding='utf-8')
        town = (ROOT / 'tools' / 'import_town.py').read_text(encoding='utf-8')
        # one tag row per frame of the model beside it: the standing model's and the mover's (ANIMKIT-ITEM-TAG-FRAMES-35)
        self.assertIn('npc_items.resident_items(assets,palette,appearance,kit or skeleton,item_times)', area)
        self.assertIn('npc_items.resident_items(assets,palette,appearance,kit,item_times,mover_item_times)', area)
        for source in (area, town):
            self.assertIn('npc_items.publish(scene', source)
        for source in (area, town):
            self.assertIn('npc_items.attach_items(kinds', source)
        combat = code('aw_combat.c')
        self.assertIn('AW_ItemsShow(e,s->item)', combat)
        self.assertIn('AW_ItemsUpdate(s->e,s->item)', combat)
        self.assertIn('AW_ItemsPrep(G_EDICT(OFS_PARM0))', code('pr_cmds.c'))

    def test_actor_file_index_reaches_every_row(self):
        import prepare_combat
        rows = sorted(['1st guard\tA\t1', 'a guard\tB\t1', 'ab\tC\t1', 'mevil molor\tD\t9', 'zz top\tE\t2'])
        text = prepare_combat.actor_file(rows)
        lines = text.split('\n')
        self.assertEqual(lines[0], 'AWCA1 5')
        offsets = [int(v) for v in lines[1].split()[1:]]
        self.assertEqual(len(offsets), 27)
        self.assertEqual(len(lines[1]), 1 + 27 * 9)
        data = text.encode('ascii')[len(lines[0]) + len(lines[1]) + 2:]
        for row in rows:
            identifier = row.split('\t')[0]
            start = offsets[prepare_combat.bucket(identifier)]
            found = None
            for line in data[start:].decode('ascii').split('\n'):
                key = line.split('\t')[0]
                if key > identifier:
                    break
                if key == identifier:
                    found = line
                    break
            self.assertEqual(found, row)
        # an empty letter reads nothing: it points at the next letter's rows
        self.assertEqual(offsets[1], offsets[12])           # b..l empty -> m
        self.assertEqual(prepare_combat.actor_file([]).split('\n')[0], 'AWCA1 0')

    def test_autocalculated_sheet_follows_the_original_rules(self):
        import prepare_combat
        race = struct.pack('<14i', 4, 10, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0)
        race += b''.join(struct.pack('<2i', 40, 30) for _ in range(8)) + struct.pack('<4fI', 1, 1, 1, 1, 0)
        cls = struct.pack('<3i', 0, 5, 0) + b''.join(struct.pack('<2i', a, b) for a, b in
                                                     ((1, 4), (2, 5), (3, 6), (7, 8), (9, 10))) + struct.pack('<2i', 1, 0)
        kinds = {'RACE': {'test': [rec('RADT', race)]}, 'CLAS': {'warrior': [rec('CLDT', cls)]},
                 'SKIL': {i: [rec('SKDT', struct.pack('<2i4f', i % 8, i % 3, 0, 0, 0, 0))] for i in range(27)}}
        npc = [rec('FLAG', struct.pack('<I', 0)), rec('RNAM', b'Test\0'), rec('CNAM', b'Warrior\0')]
        attributes, skills, health = prepare_combat.autocalc(kinds, npc, 1)
        self.assertEqual(attributes, [50, 40, 40, 40, 40, 50, 40, 40])
        self.assertEqual(health, 50)
        self.assertEqual((skills[4], skills[1], skills[0]), (40, 15, 10))
        attributes, skills, health = prepare_combat.autocalc(kinds, npc, 5)
        self.assertEqual((attributes[0], attributes[5]), (56, 56))   # 50 + 4 x 1.6 and 50 + 4 x 1.4, halves to even
        self.assertEqual(health, 80)                                 # 56 + (3 + 2 combat + 1 endurance) x 4
        self.assertEqual((skills[4], skills[0]), (44, 12))
        self.assertEqual(prepare_combat.round_even(2.5), 2.0)
        self.assertEqual(prepare_combat.round_even(3.5), 4.0)

    def test_arena_player_preset_sheet(self):
        import prepare_combat
        race = struct.pack('<14i', 26, 10, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0)
        race += b''.join(struct.pack('<2i', 40, 30) for _ in range(8)) + struct.pack('<4fI', 1, 1, 1, 1, 0)
        cls = struct.pack('<3i', 0, 5, 0) + b''.join(struct.pack('<2i', a, b) for a, b in
                                                     ((1, 26), (2, 5), (3, 6), (7, 8), (9, 10))) + struct.pack('<2i', 1, 0)
        helm = struct.pack('<ifiiii', 0, 3.0, 10, 100, 0, 10)
        shield = struct.pack('<ifiiii', 8, 3.0, 10, 100, 0, 10)
        kinds = {'RACE': {'nord': [rec('RADT', race)]}, 'CLAS': {'monk': [rec('CLDT', cls)]},
                 'SKIL': {i: [rec('SKDT', struct.pack('<2i4f', i % 8, i % 3, 0, 0, 0, 0))] for i in range(27)},
                 'ARMO': {'helm': [rec('AODT', helm)], 'shield': [rec('AODT', shield)]}}
        settings = {'fUnarmoredBase1': .1, 'fUnarmoredBase2': .065, 'iBaseArmorSkill': 30, 'fLightMaxMod': .6,
                    'fMedMaxMod': .9, 'iHelmWeight': 5, 'iShieldWeight': 9, 'fNPCbaseMagickaMult': 2}
        for name in ('iCuirassWeight', 'iPauldronWeight', 'iGreavesWeight', 'iBootsWeight', 'iGauntletWeight'):
            settings[name] = 10
        sword = struct.pack('<fihhffh6Bi', 20.0, 50, 1, 900, 1.35, 1.0, 0, 2, 14, 1, 20, 4, 18, 0)
        claymore = struct.pack('<fihhffh6Bi', 30.0, 90, 2, 2100, 1.0, 1.0, 0, 1, 27, 1, 23, 1, 16, 0)
        kinds['WEAP'] = {'sword': [rec('WPDT', sword)], 'claymore': [rec('WPDT', claymore)]}
        preset = {'name': 'Tester', 'race': 'Nord', 'class': 'Monk', 'level': 1, 'skills': {'Block': 77},
                  'attributes': {'agility': 61}, 'loadout': 'fists',
                  'loadouts': {'fists': {'weapon': None, 'armor': ['helm']},
                               'sword_shield': {'weapon': 'sword', 'armor': ['helm', 'shield']}}}
        row, report = prepare_combat.player_sheet(kinds, settings, preset)
        fields = row.split('\t')
        self.assertEqual(fields[:3], ['loadout:fists', 'Tester', '1'])
        skills = [int(v) for v in fields[4].split()]
        self.assertEqual(skills[0], 77)                                  # override
        self.assertEqual(skills[26], 25 + 5 + 10 + 0)                     # major + base + race bonus
        self.assertEqual([int(v) for v in fields[3].split()][3], 61)
        self.assertEqual(fields[7], '0 26 0 0 0 0 0 0 0 0 0')              # fists
        self.assertEqual(fields[10], '0 0 0')
        self.assertGreater(report['armor_rating'], 0)
        row, report = prepare_combat.player_sheet(kinds, settings, preset, 'sword_shield')
        fields = row.split('\t')
        self.assertEqual(fields[7].split()[:8], ['2', '5', '2', '14', '1', '20', '4', '18'])   # long blade one-handed
        self.assertEqual(fields[8].split()[1], '1')                       # shield carried
        self.assertEqual(fields[10], '900 100 0')                         # conditions; 3 kg shield of a 9 kg class: light
        text, reports = prepare_combat.player_file(kinds, settings, preset)
        self.assertTrue(text.startswith('AWAP2\ndefault fists\nloadout:fists\t'))
        self.assertEqual(sorted(reports), ['fists', 'sword_shield'])
        for bad in ({**preset, 'loadouts': {'x': {'weapon': None, 'armor': ['shield']}}, 'loadout': 'x'},      # fists + shield
                    {**preset, 'loadouts': {'x': {'weapon': 'claymore', 'armor': ['shield']}}, 'loadout': 'x'},  # two-handed + shield
                    {**preset, 'loadout': 'nothing'}, {**preset, 'race': 'nobody'}, {**preset, 'level': 0}):
            with self.assertRaises(ValueError):
                prepare_combat.player_sheet(kinds, settings, bad)
        config = json.loads((ROOT / 'config' / 'arena_player.json').read_text(encoding='utf-8'))
        self.assertEqual((config['race'], config['class']), ('nord', 'monk'))

    def test_sounds_become_11025_hz_8_bit_mono(self):
        import prepare_combat
        source = io.BytesIO()
        with wave.open(source, 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes(struct.pack('<%dh' % 2000, *([1000, -1000] * 1000)))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'x.wav'
            seconds = prepare_combat.convert_wav(source.getvalue(), out)
            with wave.open(str(out)) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 1, 11025))
                self.assertEqual(w.getnframes(), 500)
            self.assertAlmostEqual(seconds, 500 / 11025, places=4)

    def test_fighter_frames_fit_the_alias_limit_and_hold_the_hit_key(self):
        import prepare_combat
        from npc_geometry import alias_frame_bytes, ALIAS_FRAME_BYTES
        self.assertLessEqual(alias_frame_bytes(sum(n for _, n in prepare_combat.FRAME_GROUPS), 1999), ALIAS_FRAME_BYTES)

        class Fake:
            events = {'idle: start': 0, 'idle: stop': 2, 'runforward1h: loop start': 10, 'runforward1h: loop stop': 11,
                      'weapononehand: chop start': 20, 'weapononehand: chop large follow stop': 21,
                      'weapononehand: chop hit': 20.8, 'hit1: start': 30, 'hit1: stop': 31,
                      'knockdown: start': 40, 'knockdown: stop': 42, 'death1: start': 50, 'death1: stop': 51}

            def idle_times(self, count):
                import numpy as np
                return np.linspace(0, 2, count, endpoint=False), 2 / count
        groups, hit = prepare_combat.frame_times(Fake(), 'weapononehand')
        self.assertAlmostEqual(hit, .8)
        counts = dict(prepare_combat.FRAME_GROUPS)
        for name, count in counts.items():
            self.assertEqual(len(groups[name][0]), count, name)
        self.assertEqual(groups['death'][0][-1], 51)          # the last frame is the death pose
        self.assertEqual(groups['run'][0][0], 10)
        config = json.loads((ROOT / 'config' / 'arena_fighters.json').read_text(encoding='utf-8'))
        self.assertEqual(config['fighters'][0]['id'], 'mevil molor')   # the default opponent


if __name__ == '__main__':
    unittest.main()
