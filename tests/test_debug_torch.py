"""The debug torch (test only): the maintainer's preview-stage request of 17 October 2026.

The player leaves the census office with the original torch that never burns out, while the builder's game
config says aw_debug_torch 1 (on for every build until the final game). Native rules: tests/aga_inventory_test.c
(given once, never when off, unlimited burn time) and tests/aga_inventory_metadata_test.c (the catalogue row);
the catalogue row from the original record: tests/test_inventory_assets.py.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
sys.path.insert(0, str(ROOT / 'tools'))


def code(name):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


class DebugTorchTests(unittest.TestCase):
    def test_game_config_turns_it_on_until_the_final_game(self):
        lines = (ROOT / 'config/game.cfg').read_text(encoding='utf-8').splitlines()
        self.assertEqual([l for l in lines if l.startswith('aw_debug_torch')], ['aw_debug_torch 1'])

    def test_receipt_record_follows_the_staged_switch(self):
        from build_aga import debug_torch_record, stage_game_config
        with tempfile.TemporaryDirectory() as tmp:
            stage_game_config(tmp)
            record = debug_torch_record(tmp)
            self.assertTrue(record['on'])
            self.assertEqual(record['item'], 'Debug torch (test only)')
            self.assertEqual(record['line'], 'aw_debug_torch 1')
            cfg = Path(tmp) / 'default-game.cfg'
            cfg.write_text(cfg.read_text(encoding='utf-8').replace('aw_debug_torch 1', 'aw_debug_torch 0'),
                           encoding='utf-8', newline='\n')
            record = debug_torch_record(tmp)
            self.assertFalse(record['on'])
            self.assertEqual(record['note'], 'not given')
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("build_json['debug_torch'] = args.image_debug_torch_record", source)

    def test_given_only_at_the_census_exit_and_never_saved_as_a_setting(self):
        scene = code('aw_scene.c')
        self.assertIn('if(AW_StoryRestricted() && links[i].reference==119659 && AW_StoryTransition(AW_STAGE_RELEASED) '
                      '&& aw_scene_census_exit)', scene)
        self.assertEqual(scene.count('aw_scene_census_exit()'), 1)
        torch = code('aw_debug_torch.c')
        # Not archived (no saved config.cfg value can override the image's game config); off without it.
        self.assertIn('static cvar_t aw_debug_torch={"aw_debug_torch","0"};', torch)
        self.assertIn('if(!aw_debug_torch.value)return;', torch)
        self.assertIn('AW_DebugTorchGrant(&aw_state,1)', torch)
        self.assertIn('aw_scene_census_exit=census_exit;aw_torch_item_lit=item_lit;', torch)
        self.assertIn('AW_DebugTorchInit();', code('aw_debug.c'))
        self.assertIn('aw_debug_torch.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_equipped_light_lights_the_carried_torch(self):
        torch = code('aw_torch.c')
        self.assertIn('int (*aw_torch_item_lit)(void);', torch)
        update = torch[torch.index('void AW_TorchUpdate(void)'):]
        self.assertLess(update.index('item_torch();'), update.index('torch=AW_TorchEquipped();'))
        self.assertIn('if(v){if(lit && raised)v->_float=1;else if(!lit && was_lit)v->_float=0;}', torch)


if __name__ == '__main__':
    unittest.main()
