# SPDX-License-Identifier: GPL-3.0-only
"""The image step's stair gate accepts known stair findings (--accept-known-stair-findings) for
private -devN tests only: recorded, never dropped, every other failure still gates; refused for
release candidates and finals."""
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

import stair_walk  # noqa: E402
from chim.known import known_stair_findings  # noqa: E402


def row(ref, name='bm020'):
    return {'kind': 'step', 'flight': True, 'result': 'failed', 'ref': ref, 'map': name, 'point': [0, 0, 0],
            'rise': 8.0, 'detail': {'status': 'start in solid'}}


def report(*rows):
    return {'status': 'failed', 'failures': list(rows), 'exempt_failures': [], 'advisory_failures': [], 'rows': list(rows)}


class ImageStairAcceptanceTests(unittest.TestCase):
    def test_accepted_failures_move_and_others_still_gate(self):
        accepted = known_stair_findings(['STAIRS-BALMORA-B01-32'])
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stair_walk, 'check', return_value=report(row(41499), row(7))):
            out = Path(tmp) / 'stair-walk.json'
            with self.assertRaisesRegex(ValueError, 'ref 7'):
                stair_walk.require(tmp, out, accepted=accepted)
            saved = json.loads(out.read_text())
            self.assertEqual([(r['ref'], r['finding']) for r in saved['accepted_known_findings']],
                             [(41499, 'STAIRS-BALMORA-B01-32')])
            self.assertEqual([r['ref'] for r in saved['failures']], [7])

    def test_only_accepted_failures_pass_and_are_recorded(self):
        accepted = known_stair_findings(['STAIRS-BALMORA-B01-32', 'STAIRS-ADDAMASARTUS-32'])
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stair_walk, 'check', return_value=report(row(41499), row(89756, 'addamasartus'))):
            out = Path(tmp) / 'stair-walk.json'
            result = stair_walk.require(tmp, out, accepted=accepted)
            self.assertEqual(result['status'], 'passed with accepted known findings')
            self.assertEqual(result['accepted_ids'], ['STAIRS-ADDAMASARTUS-32', 'STAIRS-BALMORA-B01-32'])
            self.assertEqual(len(json.loads(out.read_text())['accepted_known_findings']), 2)

    def test_without_acceptance_the_gate_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stair_walk, 'check', return_value=report(row(41499))):
            with self.assertRaisesRegex(ValueError, 'ref 41499'):
                stair_walk.require(tmp, Path(tmp) / 'stair-walk.json')

    def test_image_step_refuses_it_for_release_candidates_and_finals(self):
        import build_aga
        args = build_aga.argparse.Namespace(accept_known_stair_findings=['STAIRS-BALMORA-B01-32'])
        self.assertIn('--accept-known-stair-findings', build_aga.image_waivers(args))
        from project_version import require_private_test_version
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'refused'):
                require_private_test_version(version, build_aga.image_waivers(args))
        require_private_test_version('0.0.33-dev1', build_aga.image_waivers(args))
        self.assertEqual(build_aga.image_waivers(build_aga.argparse.Namespace()), [])

    def test_the_build_plan_passes_it_to_the_image_step(self):
        import build
        import build_font_options as options
        args = build.parser().parse_args(['--jobs', '4', '--accept-known-stair-findings', 'STAIRS-BALMORA-WESTSOUTH-32'])
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        args.builder_options = options.resolve_builder(args)
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        command = [str(p) for p in dict(build.commands(args, tools, Path('/private/run')))['image']]
        self.assertEqual(command[command.index('--accept-known-stair-findings') + 1], 'STAIRS-BALMORA-WESTSOUTH-32')

    def test_every_known_finding_is_a_tracker_entry_with_its_placements(self):
        table = json.loads((ROOT / 'config/known-stair-findings.json').read_text(encoding='utf-8'))['findings']
        bugs = {e['id']: e for e in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for fid, entry in table.items():
            with self.subTest(fid=fid):
                self.assertIn(fid, bugs)
                self.assertTrue(entry['refs'])
                page = (ROOT / 'docs' / bugs[fid]['report']).read_text(encoding='utf-8')
                for ref in entry['refs']:
                    self.assertIn('ref %d' % ref, page)


if __name__ == '__main__':
    unittest.main()
