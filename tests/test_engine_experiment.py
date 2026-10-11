# SPDX-License-Identifier: GPL-3.0-only
"""--engine-experiment NAME (docs/EXPERIMENTAL_FLAGS.md): an experimental engine compile switch reaches the engine
stage and the make command only when asked, and is recorded in engine-build.json; a default build's engine command,
make command and receipt are unchanged. widecoord = AW_EXP_WIDECOORD (CHIM-FRAME-COORD-RANGE-33), the spike's switch:
wide coordinates are the default since v0.0.36 (tools/build.py --coord-range, tests/test_coord_range.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class EngineExperimentTests(unittest.TestCase):
    def test_only_an_asked_switch_changes_the_engine_stage(self):
        import build
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        for extra in ([], ['--engine-experiment', 'widecoord']):
            args = build.parser().parse_args(['--hands', 'sprites', *extra])
            args.data_files, args.sdk, args.upstream_archive = Path('/d'), Path('/sdk'), Path('/u.tar.gz')
            engine = [str(part) for part in dict(build.commands(args, tools, Path('/private/run')))['engine']]
            if extra:
                self.assertEqual(engine[engine.index('--engine-experiment') + 1], 'widecoord')
            else:
                self.assertNotIn('--engine-experiment', engine)
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            build.parser().parse_args(['--engine-experiment', 'everything'])

    def test_the_make_command_and_receipt(self):
        import build_aga
        self.assertEqual(build_aga.ENGINE_EXPERIMENTS, {'widecoord': '-DAW_EXP_WIDECOORD'})
        calls = []

        def fake_run(command, cwd=None, env=None, capture=False):
            command = [str(c) for c in command]
            calls.append(command)
            tree = Path(cwd) if cwd else None
            if command[0] == 'make' and 'bench' in command:
                (tree / 'build').mkdir(exist_ok=True)
                (tree / 'build/awbench').write_bytes(b'bench')
            elif command[0] == 'make':
                (tree / 'build').mkdir(exist_ok=True)
                (tree / 'build/AmiQuakeGCC').write_bytes(b'engine')
            elif '-o' in command:
                Path(command[command.index('-o') + 1]).write_bytes(b'hunk')
            return ''
        for asked in (None, 'widecoord'):
            calls.clear()
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'engine'
                argv = ['build_aga.py', 'engine', '--out', str(out), '--sdk', tmp, '--jobs', '1',
                        *(['--engine-experiment', asked] if asked else [])]
                with patch('sys.argv', argv), patch.object(build_aga, 'run', side_effect=fake_run), \
                        patch.object(build_aga, 'check_binary'), \
                        patch.object(build_aga, 'check_engine_fpu', return_value=None), \
                        patch.object(build_aga, 'executable_path', side_effect=lambda p: p), \
                        patch.object(build_aga, 'write_world_coverage'), \
                        patch('sys.stdout'):
                    build_aga.main()
                make = calls[0]
                record = json.loads((out / 'engine-build.json').read_text())
                if asked is None:
                    # wide coordinates are the engine source's default: no define (tests/test_coord_range.py)
                    self.assertFalse([part for part in make if part.startswith('EXTRA_DEFINES=')])
                    self.assertNotIn('engine_experiments', record)
                else:
                    self.assertIn('EXTRA_DEFINES=-DAW_EXP_WIDECOORD', make)
                    self.assertEqual(record['engine_experiments'], ['widecoord'])

    def test_the_makefile_takes_the_switches_for_both_cpu_targets(self):
        text = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('EXTRA_DEFINES ?=', text)
        self.assertEqual(text.count('-DUSE_FAST_RECIPROCAL=1 $(EXTRA_DEFINES)'), 2)


if __name__ == '__main__':
    unittest.main()
