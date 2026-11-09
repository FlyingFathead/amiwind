# SPDX-License-Identifier: GPL-3.0-only
"""Breath and drowning under water (UNDERWATER-BREATH-62), god mode against every world damage
(GODMODE-LAVA-DEATH-62) and the effect layers CHIM leaves out (BLIGHT-CLOUD-HIDE-62): the rules natively, the
engine's wiring, the builder's settings and the scripts' Water Breathing calls."""
import json
import os
import re
import shutil
import sys
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
class BreathRuleTests(unittest.TestCase):
    def test_breath_falls_fills_and_drowns(self):
        native.NativeSourceTests().compile_run('aga_breath_rules_test.c', [SRC / 'aw_breath_rules.c'], cflags=UBSAN)


class BreathWiringTests(unittest.TestCase):
    def test_after_the_lava_through_the_one_damage_check(self):
        self.assertIn('AW_SPIKE_STAGE (AW_SP_LAVA, (AW_LavaPhysics (), AW_BreathPhysics ()));', code('sv_phys.c'))
        self.assertIn('AW_LavaInit();AW_BreathInit();', code('aw_debug.c'))
        self.assertIn('aw_breath_rules.c aw_breath.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        breath = code('aw_breath.c')
        self.assertIn('AW_CombatHurtPlayer(loss,"drowning");', breath)
        self.assertIn('aw_combat_effect_magnitude(p,AW_EFFECT_WATER_BREATHING)', breath)   # abilities and effects
        self.assertIn('AW_ResetRegister("breath (drowning)",reset_breath,digest_breath);', breath)
        self.assertIn('Cmd_AddCommand("aw_breath",breath_command);', breath)
        self.assertIn('if(strncmp(line,"breath ",7))continue;', breath)
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', breath))
        ui = code('aw_ui.c')
        self.assertIn('int (*aw_breath_bar)(float *fraction,int *flashing);', ui)
        self.assertIn('aw_breath_bar(&fraction,&flashing)', ui)

    def test_settings_and_sound_come_from_the_master(self):
        import prepare_combat
        self.assertEqual(prepare_combat.BREATH_SETTINGS, ('fHoldBreathTime', 'fSuffocationDamage'))
        self.assertEqual(prepare_combat.BREATH_SOUND, ('drown', 'drown'))
        text = (ROOT / 'tools' / 'prepare_combat.py').read_text(encoding='utf-8')
        self.assertIn("lines += [f'breath {name} {settings[name]:.6g}' for name in BREATH_SETTINGS]", text)
        self.assertIn("lines.append(f'breath sound combat/{key}.wav {seconds:.3f}')", text)
        header = (SRC / 'aw_breath.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_BREATH_SETTING_COUNT %d' % len(prepare_combat.BREATH_SETTINGS), header)
        rules = code('aw_breath_rules.c')
        for name in prepare_combat.BREATH_SETTINGS:
            self.assertIn('"%s"' % name, rules)

    def test_the_command_is_listed(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'\n[A-Z /]+\|breath\|aw_breath\|')
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg breath`', page)


class GodModeTests(unittest.TestCase):
    def test_every_world_damage_and_every_script_loss_asks_god_mode(self):
        combat = code('aw_combat.c')
        body = combat[combat.index('int AW_CombatHurtPlayer(float damage,const char *cause) {'):]
        body = body[:body.index('\n}\n')]
        self.assertIn('AW_CombatGodWorldDamage((int)p->v.flags&FL_GODMODE,damage,&world_god_damage)', body)
        host = code('aw_mwhost.c')
        store = host[host.index('static void player_store(const aw_actor_t *a){'):]
        store = store[:store.index('\n}\n')]
        self.assertIn('AW_CombatGodHealth(((int)sv_player->v.flags&FL_GODMODE)!=0,sv_player->v.health,', store)
        self.assertIn('God mode is on: no death', code('aw_view.c'))
        # the lava volume and the lava script both reach the player through the one check
        self.assertIn('AW_CombatHurtPlayer(AW_LavaDamage(lava_dps.value,dt),"lava")', code('aw_lava.c'))
        self.assertIn('AW_CombatHurtPlayer(hurt,"lava")', host)


class WaterBreathingScriptTests(unittest.TestCase):
    def test_get_set_and_mod_go_through_the_host(self):
        from mwscript.functions import FUNCTION_NUMBERS, HOST, HOST_EFFECTS
        names = ('getwaterbreathing', 'setwaterbreathing', 'modwaterbreathing')
        self.assertTrue(set(names) <= HOST)
        self.assertTrue({'setwaterbreathing', 'modwaterbreathing'} <= HOST_EFFECTS)
        header = (SRC / 'aw_mwcode.h').read_text(encoding='utf-8')
        for name in names:
            self.assertIn('#define AWF_%s %d' % (name.upper(), FUNCTION_NUMBERS[name]), header)
        self.assertIn('{AWF_GETWATERBREATHING,AWF_SETWATERBREATHING,AWF_MODWATERBREATHING,AW_EFFECT_WATER_BREATHING,-1,-1}',
                      code('aw_mwhost.c'))


class EffectLayerTests(unittest.TestCase):
    def test_the_blight_cloud_is_left_out_and_recorded(self):
        from chim.build import effect_layer_models, effect_layer_references
        models = effect_layer_models()
        self.assertIn('f/active_blight_large.nif', models)
        self.assertEqual(models['f/active_blight_large.nif']['bug'], 'CHIM-DAGOTH-UR-RUIN-CYLINDER-44')
        refs = [{'number': 7, 'model': 'f\\Active_Blight_Large.NIF', 'id': 'blight cloud'},
                {'number': 3, 'model': 'x\\ex_dwrv_ruin20.nif'},
                {'number': 5, 'model': 'meshes/f/active_blight_large.nif'}]
        kept, removed = effect_layer_references(refs, models)
        self.assertEqual([r['number'] for r in kept], [3])
        self.assertEqual(removed, [5, 7])
        self.assertEqual(effect_layer_references(refs[1:2], models), (refs[1:2], []))
        config = json.loads((ROOT / 'config' / 'chim-effect-layers.json').read_text(encoding='utf-8'))
        for entry in config['models'].values():
            self.assertTrue(entry['reason'] and entry['bug'])
        build = (ROOT / 'tools' / 'chim' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("parity['effect_layers_removed'] = effect_removed", build)
        self.assertLess(build.index("parity['harvest_removed'] = sorted(removed)"),
                        build.index('selected, effect_removed = effect_layer_references(selected)'))


if __name__ == '__main__':
    unittest.main()
