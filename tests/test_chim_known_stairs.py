# SPDX-License-Identifier: GPL-3.0-only
"""Accepted known stair findings (--accept-known-stair-findings): private -devN tests only, recorded,
never dropped; refused for release candidates and finals; unknown IDs refused."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.known import known_stair_findings  # noqa: E402


class KnownStairFindingTests(unittest.TestCase):
    def test_ids_map_to_their_placements_and_unknown_ids_are_refused(self):
        self.assertEqual(known_stair_findings(['STAIRS-BALMORA-B01-32']), {41499: 'STAIRS-BALMORA-B01-32'})
        with self.assertRaisesRegex(ValueError, 'Unknown stair finding'):
            known_stair_findings(['STAIRS-NOWHERE-99'])

    def test_every_listed_finding_is_a_tracker_entry(self):
        table = json.loads((ROOT / 'config/known-stair-findings.json').read_text(encoding='utf-8'))['findings']
        ids = {e['id'] for e in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        self.assertLessEqual(set(table), ids)

    def test_accepted_failures_are_recorded_not_dropped(self):
        from chim import collision
        failing = {'kind': 'step', 'flight': True, 'result': 'failed', 'ref': 41499, 'map': 'f', 'point': [0, 0, 0],
                   'detail': {'status': 'start in solid'}}
        other = dict(failing, ref=7)
        report = {'status': 'failed', 'failures': [failing, other], 'tested': 2}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch('mesh_geometry_env.stair_mode', return_value='on'), \
                mock.patch('chim.validate.load_world', return_value=(None,) * 5 + ([],)), \
                mock.patch.object(collision, 'stair_gate', return_value=dict(report, failures=[failing, other])):
            with self.assertRaisesRegex(ValueError, 'ref 7'):
                collision.require_stairs(tmp, 1, accepted=['STAIRS-BALMORA-B01-32'])
            saved = json.loads((Path(tmp) / 'chim-stairs.json').read_text())
            self.assertEqual([r['finding'] for r in saved['accepted_known_findings']], ['STAIRS-BALMORA-B01-32'])
            self.assertEqual([r['ref'] for r in saved['failures']], [7])
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch('mesh_geometry_env.stair_mode', return_value='on'), \
                mock.patch('chim.validate.load_world', return_value=(None,) * 5 + ([],)), \
                mock.patch.object(collision, 'stair_gate', return_value=dict(report, failures=[failing])):
            r = collision.require_stairs(tmp, 1, accepted=['STAIRS-BALMORA-B01-32'])
            self.assertEqual(r['status'], 'passed with accepted known findings')

    def test_refused_for_release_candidates_and_finals(self):
        import chim_build
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), mock.patch('project_version.public_version', return_value=version), \
                    mock.patch('chim.build.build_areas') as run, contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as stop:
                chim_build.main(['--area', 'balmora', '--data-files', '/none', '--palette', '/none', '--out', '/none',
                                 '--accept-known-stair-findings', 'STAIRS-BALMORA-B01-32'])
            self.assertEqual(stop.exception.code, 1)
            run.assert_not_called()

    def test_the_build_plan_passes_it_to_the_chim_stage(self):
        import build
        import build_font_options as options
        args = build.parser().parse_args(['--jobs', '4', '--builder', 'chim',
                                          '--accept-known-stair-findings', 'STAIRS-BALMORA-B01-32'])
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        args.builder_options = options.resolve_builder(args)
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        command = [str(p) for p in dict(build.commands(args, tools, Path('/private/run')))['chim']]
        self.assertEqual(command[command.index('--accept-known-stair-findings') + 1], 'STAIRS-BALMORA-B01-32')


if __name__ == '__main__':
    unittest.main()
