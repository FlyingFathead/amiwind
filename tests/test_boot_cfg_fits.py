"""The boot configs against the engine's command buffer (CFG-OVER-COMMAND-BUFFER-68).

The v0.0.68-dev8 image's default-game.cfg (8511 bytes) did not fit Quake's 8192-byte command buffer, so the engine
dropped the whole file and ran none of the game's defaults (no actor table: no outdoor creature at Seyda Neen). The
first test fails on that engine (cmd.c's 8192 against the builder's 32768); the others pin the image step's check.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import boot_cfg_fit  # noqa: E402


class BootCfgFitTests(unittest.TestCase):
    def test_builder_buffer_is_the_engine_buffer(self):
        self.assertEqual(boot_cfg_fit.engine_buffer(), boot_cfg_fit.ENGINE_CMD_BUFFER)

    def test_engine_buffer_holds_the_dev8_default_config_twice(self):
        # the default-game.cfg that was dropped: 8511 bytes; the buffer must hold it with room for what queues beside it
        self.assertGreaterEqual(boot_cfg_fit.engine_buffer(), 2 * 8511)

    def test_check_refuses_a_config_over_half_the_buffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'default-game.cfg').write_bytes(b'x' * (boot_cfg_fit.ENGINE_CMD_BUFFER // 2))
            (Path(tmp) / 'default.cfg').write_bytes(b'bind w +forward\n')
            with self.assertRaises(ValueError) as caught:
                boot_cfg_fit.check(tmp)
            self.assertIn('default-game.cfg', str(caught.exception))
            self.assertNotIn('default.cfg 16', str(caught.exception))

    def test_check_refuses_the_dev8_config_with_the_old_buffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'default-game.cfg').write_bytes(b'x' * 8511)
            with self.assertRaises(ValueError):
                boot_cfg_fit.check(tmp, buffer=8192)

    def test_check_passes_and_reports_configs_that_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'default-game.cfg').write_bytes(b'x' * 8511)
            (Path(tmp) / 'autoexec.cfg').write_bytes(b'')
            self.assertEqual(boot_cfg_fit.check(tmp), {'autoexec.cfg': 0, 'default-game.cfg': 8511})

    def test_repo_game_config_leaves_room_for_the_builder_lines(self):
        # config/game.cfg becomes default-game.cfg, and the image step appends its own default lines (about 1 KB
        # in v0.0.68-dev8): the repo's file must leave at least 4 KB under the check's half of the buffer
        size = (ROOT / 'config/game.cfg').stat().st_size
        self.assertLess(size, boot_cfg_fit.ENGINE_CMD_BUFFER // 2 - 4096)

    def test_image_step_calls_the_check(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("from boot_cfg_fit import check as check_boot_cfgs", text)
        self.assertIn("check_boot_cfgs(boot/'id1')", text)

    def test_finalize_checks_the_configs_before_it_writes(self):
        # the shared image tail (finalize_image, also run on a continued image) checks the configs again, right after
        # its read-only payload preflight and before its first write
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        body = text[text.index('def finalize_image(args):'):]
        body = body[:body.index('\ndef ')]
        preflight = body.index('payload_preflight(args, out, excluded, jobs)')
        check = body.index("check_boot_cfgs(boot/'id1')")
        self.assertLess(preflight, check)
        self.assertLess(check, body.index('write_text('))


if __name__ == '__main__':
    unittest.main()
