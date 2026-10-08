"""Disk-only command metadata must survive normal image staging."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_aga


class DebugCataloguePackageTests(unittest.TestCase):
    def test_both_runtime_catalogues_are_copied_byte_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            receipt = build_aga.stage_debug_catalogues(target, debug_luma=True)
            self.assertEqual(set(receipt), {'debug-commands.txt', 'shroompicker.txt'})
            for name, record in receipt.items():
                self.assertEqual((target/name).read_bytes(),
                                 (build_aga.ROOT/'config'/name).read_bytes())
                self.assertEqual(record['bytes'], (target/name).stat().st_size)
                self.assertEqual(record['sha256'], build_aga.digest(target/name))

    def test_disabled_keeps_explanatory_routes_but_omits_startup_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            build_aga.stage_debug_catalogues(target)
            build_aga.stage_game_config(target)
            self.assertIn(b'|aw_interiorluma_set|', (target/'debug-commands.txt').read_bytes())
            commands = (target/'default-game.cfg').read_text().splitlines()
            self.assertFalse(any(line.startswith('aw_interiorluma ') for line in commands))
            self.assertFalse(any(line.startswith('aw_exteriorluma ') for line in commands))
            self.assertIn('aw_torch_strength 0.7', commands)
            build_aga.stage_game_config(target, debug_luma=True)
            self.assertEqual((target/'default-game.cfg').read_bytes(), (build_aga.ROOT/'config/game.cfg').read_bytes())
            self.assertIn('aw_interiorluma 1.2', (target/'default-game.cfg').read_text().splitlines())

    def test_engine_cli_flag_reaches_compiler_and_receipt(self):
        for flag, debug in ((None,True),("--disallow-luma-controls",False),("--no-luma-controls",False),("--debug-luma",True),("--interior-brightness",True)):
            with self.subTest(debug=debug), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'out'
                tree = out/'runtime'
                (tree/'build').mkdir(parents=True)
                (tree/'build/AmiQuakeGCC').write_bytes(b'fixture engine')
                (tree/'build/AmiWindCheck').write_bytes(b'fixture checker')
                (tree/'build/awbench').write_bytes(b'fixture benchmark')
                (tree/'build/AmiWindFPU').write_bytes(b'fixture loader')
                argv = ['build_aga.py','engine','--sdk',tmp,'--out',str(out),'--jobs','1']
                if flag:
                    argv.append(flag)
                with patch.object(sys,'argv',argv), patch.object(build_aga,'check_native_versions'), \
                     patch.object(build_aga,'new_output',return_value=out), \
                     patch.object(build_aga,'stage_runtime',return_value=(tree,{})), \
                     patch.object(build_aga,'run') as run, patch.object(build_aga,'check_binary'), \
                     patch.object(build_aga,'check_engine_fpu',return_value={'passed':True}) as fpu, \
                     patch.object(build_aga,'write_world_coverage'), patch.object(build_aga,'executable_path',side_effect=str):
                    build_aga.main()
                fpu.assert_called_once()  # 68040 builds run the FPU check (ENGINE-FPU-UNIMPL-31)
                self.assertEqual(json.loads((out/'engine-build.json').read_text())['fpu_unimplemented_check'], {'passed':True})
                make = run.call_args_list[0].args[0]
                compiler = next(arg for arg in make if arg.startswith('CC='))
                self.assertEqual('-DAMIWIND_DEBUG_LUMA=1' in compiler, debug)
                self.assertIs(json.loads((out/'engine-build.json').read_text())['debug_luma'], debug)
                # The owners' hardware benchmark is built with every engine (docs/HARDWARE-BENCHMARK.md).
                self.assertTrue(any('bench' in call.args[0] for call in run.call_args_list))
                self.assertEqual((out/'awbench').read_bytes(), b'fixture benchmark')
                self.assertIn('hardware_benchmark_sha256', json.loads((out/'engine-build.json').read_text()))

    def test_engine_build_fails_on_compiler_warnings(self):
        warning = 'src/example.c:1:1: warning: example [-Wexample]\n'
        for extra, expect_failure in (([], True), (['--allow-compiler-warnings'], False)):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'out'
                tree = out/'runtime'
                (tree/'build').mkdir(parents=True)
                (tree/'build/AmiQuakeGCC').write_bytes(b'fixture engine')
                (tree/'build/AmiWindCheck').write_bytes(b'fixture checker')
                (tree/'build/awbench').write_bytes(b'fixture benchmark')
                (tree/'build/AmiWindFPU').write_bytes(b'fixture loader')
                argv = ['build_aga.py','engine','--sdk',tmp,'--out',str(out),'--jobs','1',*extra]
                with patch.object(sys,'argv',argv), patch.object(build_aga,'check_native_versions'), \
                     patch.object(build_aga,'new_output',return_value=out), \
                     patch.object(build_aga,'stage_runtime',return_value=(tree,{})), \
                     patch.object(build_aga,'run',return_value=warning), patch.object(build_aga,'check_binary'), \
                     patch.object(build_aga,'check_engine_fpu',return_value={'passed':True}), \
                     patch.object(build_aga,'write_world_coverage'), patch.object(build_aga,'executable_path',side_effect=str):
                    if expect_failure:
                        with self.assertRaises(SystemExit):
                            build_aga.main()
                        self.assertFalse((out/'engine-build.json').exists())
                    else:
                        build_aga.main()
                        self.assertTrue((out/'engine-build.json').exists())

    def test_missing_or_invalid_catalogue_stops_before_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'config').mkdir()
            target = root/'id1'
            target.mkdir()
            (root/'config/debug-commands.txt').write_bytes(b'AWDC1\n')
            with patch.object(build_aga, 'ROOT', root):
                with self.assertRaises(FileNotFoundError):
                    build_aga.stage_debug_catalogues(target)
                self.assertEqual(list(target.iterdir()), [])
                (root/'config/shroompicker.txt').write_bytes(b'OLD\n')
                with self.assertRaisesRegex(ValueError, 'header'):
                    build_aga.stage_debug_catalogues(target)
                self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
