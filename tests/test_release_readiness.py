"""Release readiness block (tools/release_readiness.py, fixlist B17): what a final would refuse, at the start."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import project_version  # noqa: E402
import release_readiness  # noqa: E402


def namespace(**values):
    base = dict(stage='aga', plan=False, check=False, dry_run=False, miniwind=False, readiness_id=[],
                accept_entity_loss=None, accept_known_stair_findings=[], retired_flags_record=[])
    base.update(values)
    return argparse.Namespace(**base)


class ReleaseReadiness(unittest.TestCase):
    def setUp(self):
        project_version.private_test_options.clear()
        self.addCleanup(project_version.private_test_options.clear)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.register = Path(temporary.name) / 'bugs.json'
        self.register.write_text(json.dumps([{'id': 'HARVEST-CHIM-REGION-LOSS-41'}, {'id': 'VIVEC-ARENA-ACTORS-32'},
                                             {'id': 'STAIRS-BALMORA-B01-32'}, {'id': 'PLAYTEST-GALLERY-41'}]))

    def check(self, args, enforced=True):
        return release_readiness.check(args, project_version.private_test_options, enforced, register=self.register)

    def test_clean_build_has_an_empty_block(self):
        record = self.check(namespace())
        self.assertEqual(record['items'], [])
        self.assertTrue(record['ready'])
        self.assertIsNone(release_readiness.refusal(record))
        self.assertIn('none: nothing here stops a release candidate or final', '\n'.join(release_readiness.lines(record)))

    def test_refusals_record_what_they_saw(self):
        # the builder's own refusal logic feeds the block: whatever a final refuses is listed, nothing is copied
        project_version.require_private_test_version('0.0.42-dev1', ['--allow-known-actor-ground-findings'])
        project_version.require_private_test_version('0.0.42-dev1', ['--exclude npc-gallery, video'])
        with self.assertRaises(ValueError):
            project_version.require_private_test_version('0.0.42', ['--skip-census'])
        self.assertEqual(project_version.private_test_options,
                         ['--allow-known-actor-ground-findings', '--exclude npc-gallery, video', '--skip-census'])

    def test_items_list_their_ids(self):
        project_version.require_private_test_version('0.0.42-dev1', ['--allow-known-actor-ground-findings'])
        project_version.require_private_test_version('0.0.42-dev1', ['--accept-known-stair-findings'])
        project_version.require_private_test_version('0.0.42-dev1', ['--exclude npc-gallery'])
        args = namespace(accept_entity_loss='harvest loss on six cells, HARVEST-CHIM-REGION-LOSS-41',
                         accept_known_stair_findings=['STAIRS-BALMORA-B01-32'],
                         readiness_id=['allow-known-actor-ground-findings=VIVEC-ARENA-ACTORS-32',
                                       'no-npc-gallery=PLAYTEST-GALLERY-41'])
        record = self.check(args)
        by_key = {item['key']: item for item in record['items']}
        self.assertEqual(sorted(by_key), ['accept-entity-loss', 'accept-known-stair-findings',
                                          'allow-known-actor-ground-findings', 'exclude-npc-gallery'])
        self.assertEqual(by_key['accept-entity-loss']['ids'], ['HARVEST-CHIM-REGION-LOSS-41'])
        self.assertEqual(by_key['accept-entity-loss']['id_source'], 'reason text')
        self.assertEqual(by_key['accept-known-stair-findings']['ids'], ['STAIRS-BALMORA-B01-32'])
        self.assertEqual(by_key['allow-known-actor-ground-findings']['ids'], ['VIVEC-ARENA-ACTORS-32'])
        # the gallery is named by its older switch: the aliases of a group reach the same item
        self.assertEqual(by_key['exclude-npc-gallery']['ids'], ['PLAYTEST-GALLERY-41'])
        self.assertTrue(all(item['ok'] for item in record['items']))
        self.assertFalse(record['ready'])
        self.assertIsNone(release_readiness.refusal(record))
        text = '\n'.join(release_readiness.lines(record))
        self.assertIn('4 release blocker(s)', text)
        self.assertIn('HARVEST-CHIM-REGION-LOSS-41 (reason text)', text)

    def test_item_without_an_id_stops_the_build(self):
        project_version.require_private_test_version('0.0.42-dev1', ['--exclude npc-gallery'])
        record = self.check(namespace(accept_entity_loss='private checkpoint'))
        self.assertTrue(record['refused'])
        message = release_readiness.refusal(record)
        self.assertIn('--readiness-id exclude-npc-gallery=ID', message)
        self.assertIn('--readiness-id accept-entity-loss=ID', message)
        self.assertIn('NO TRACKER ID', '\n'.join(release_readiness.lines(record)))

    def test_unregistered_id_stops_the_build(self):
        record = self.check(namespace(accept_entity_loss='see MADE-UP-LOSS-41'))
        self.assertEqual(record['items'][0]['unknown_ids'], ['MADE-UP-LOSS-41'])
        self.assertIn('unknown: MADE-UP-LOSS-41', release_readiness.refusal(record))

    def test_area_tests_and_previews_list_without_refusing(self):
        project_version.require_private_test_version('0.0.42-dev1', ['--miniwind'])
        record = self.check(namespace(), enforced=False)
        self.assertEqual([item['key'] for item in record['items']], ['miniwind'])
        self.assertFalse(record['refused'])

    def test_malformed_readiness_id(self):
        for value in ('no-npc-gallery', 'no-npc-gallery=', 'no-npc-gallery=not an id'):
            with self.assertRaisesRegex(ValueError, 'KEY=ID'):
                release_readiness.parse_ids([value])
        self.assertEqual(release_readiness.parse_ids(['--no-npc-gallery=A-B-41,C-D-41']),
                         {'no-npc-gallery': ['A-B-41', 'C-D-41']})

    def test_opt_outs_and_overridden_retired_flags(self):
        args = namespace(no_entity_baseline=True, retired_flags_record=[
            {'name': 'seyda-recorded', 'flag': '--seyda-recorded', 'overridden': True, 'why': 'recorded maps'}],
            readiness_id=['seyda-recorded=VIVEC-ARENA-ACTORS-32'])
        record = self.check(args)
        self.assertEqual([item['key'] for item in record['items']], ['seyda-recorded', 'no-entity-baseline'])
        self.assertEqual([item['ok'] for item in record['items']], [True, False])

    def test_builder_step_prints_records_and_refuses(self):
        import build
        project_version.private_test_options.clear()
        project_version.require_private_test_version('0.0.42-dev1', ['--exclude npc-gallery'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaisesRegex(ValueError, 'release readiness'):
            build.release_readiness_step(namespace())
        self.assertIn('Release readiness', out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            preview = build.release_readiness_step(namespace(plan=True))
            area = build.release_readiness_step(namespace(miniwind=True))
        self.assertFalse(preview['enforced'])
        self.assertIn('MiniWind', area['note'])
        self.assertIsNone(build.release_readiness_step(namespace(stage='terrain')))


if __name__ == '__main__':
    unittest.main()
