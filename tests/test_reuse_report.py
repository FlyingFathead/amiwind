# SPDX-License-Identifier: GPL-3.0-only
"""Reuse audit (tools/reuse_report.py): every stage a --reuse-from run did not reuse, EXPECTED or UNEXPECTED."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402
import reuse_report  # noqa: E402


def manifest(folder, stage, files, reusable=True, reasons=(), mode=420):
    target = folder / 'profile' / 'manifests'
    target.mkdir(parents=True, exist_ok=True)
    (target / f'{stage}.json').write_text(json.dumps({
        'schema': build_cache.MANIFEST_SCHEMA, 'stage': stage, 'status': 'complete', 'reusable': reusable,
        'reasons': list(reasons), 'files': {k: {'size': 1, 'sha256': v, 'mode': mode} for k, v in files.items()},
        'links': {}, 'deleted': [], 'directories': [], 'deleted_directories': []}))


def state(run, old, steps, reused, not_reused):
    run.mkdir(parents=True, exist_ok=True)
    (run / 'build-state.json').write_text(json.dumps({
        'steps': [{'name': name} for name in steps],
        'stage_cache': {'reuse_from': str(old), 'reused': reused, 'not_reused': not_reused}}))


def details(folder, stages):
    (folder / 'profile').mkdir(parents=True, exist_ok=True)
    (folder / 'profile' / 'fingerprints.json').write_text(json.dumps(stages))


class ReuseReportTests(unittest.TestCase):
    def audit(self, run):
        with contextlib.redirect_stdout(io.StringIO()) as text:
            code = reuse_report.main([str(run)])
        return code, text.getvalue()

    def test_real_input_changes_and_policy_are_expected(self):
        with tempfile.TemporaryDirectory() as temp:
            run, old = Path(temp) / 'new', Path(temp) / 'old'
            details(old, {'scenery': {'sources': {'by_file': {'tools/prepare_scenery.py': 'a'}}}})
            details(run, {'scenery': {'sources': {'by_file': {'tools/prepare_scenery.py': 'b'}}}})
            state(run, old, ['setup', 'scenery', 'engine', 'image'], {'setup': {}},
                  {'scenery': 'changed: sources (tools/prepare_scenery.py)', 'engine': build_cache.NON_REUSABLE['engine'],
                   'image': build_cache.NON_REUSABLE['image']})
            code, text = self.audit(run)
            self.assertEqual(code, 0, text)
            self.assertIn('Reuse audit: 1 of 4 stages reused', text)
            self.assertIn('0 unexpected', text)

    def test_a_key_that_changed_only_with_the_release_file_list_is_unexpected(self):
        with tempfile.TemporaryDirectory() as temp:
            run, old = Path(temp) / 'new', Path(temp) / 'old'
            state(run, old, ['harvest'], {}, {'harvest': 'changed: sources (tools/release-files.json)'})
            code, text = self.audit(run)
            self.assertEqual(code, 1)
            self.assertIn('over-broad key', text)

    def test_refused_records_and_differing_outputs_are_unexpected_and_named(self):
        with tempfile.TemporaryDirectory() as temp:
            run, old = Path(temp) / 'new', Path(temp) / 'old'
            manifest(old, 'census', {'scene/census.txt': 'a' * 64})
            manifest(run, 'census', {'scene/census.txt': 'b' * 64})
            state(run, old, ['balmora', 'census', 'character'],
                  {'character': {'refused': 'an earlier stage it depends on ran again and its outputs differ from '
                                            'the old run: census'}},
                  {'balmora': 'old outputs not reusable: created run-folder entries outside every declared stage path: '
                              'scratch',
                   'census': "its output scene/x was replaced later in old by balmora, which is rebuilt"})
            result = reuse_report.report(run)
            rows = {row['stage']: row for row in result['rows']}
            self.assertEqual(rows['balmora']['class'], 'UNEXPECTED')
            self.assertEqual(rows['census']['class'], 'UNEXPECTED')       # follows the unexpected balmora rebuild
            self.assertEqual(rows['character']['class'], 'UNEXPECTED')
            self.assertIn('census: 1 units differ (scene/census.txt changed)', rows['character']['detail'])
            self.assertEqual(result['reused'], 0)

    def test_dependants_of_a_real_change_are_expected_and_of_identical_outputs_unexpected(self):
        """The upstream stage is compared again by content: one that really changed after an expected rebuild makes
        its dependants' rebuild EXPECTED; one whose outputs are identical (a read-only reused copy, 0o444 against
        0o644: BUILD-REUSE-CUTOFF-MODE-36) makes it UNEXPECTED, named."""
        refused = 'an earlier stage it depends on ran again and its outputs differ from the old run: '
        with tempfile.TemporaryDirectory() as temp:
            run, old = Path(temp) / 'new', Path(temp) / 'old'
            details(old, {'intro': {'sources': {'by_file': {'tools/intro.py': 'a'}}}})
            details(run, {'intro': {'sources': {'by_file': {'tools/intro.py': 'b'}}}})
            manifest(old, 'intro', {'intro-scene/video.awv': 'a' * 64})
            manifest(run, 'intro', {'intro-scene/video.awv': 'b' * 64})
            manifest(old, 'bsp', {'bsp-scene/maps/a.bsp': 'c' * 64}, mode=0o444)
            manifest(run, 'bsp', {'bsp-scene/maps/a.bsp': 'c' * 64}, mode=0o644)
            state(run, old, ['intro', 'bsp', 'character', 'hands'],
                  {'character': {'refused': refused + 'intro, bsp'}, 'hands': {'refused': refused + 'bsp'}},
                  {'intro': 'changed: sources (tools/intro.py)', 'bsp': 'changed: sources (tools/collision_bsp.py)'})
            rows = {row['stage']: row for row in reuse_report.report(run)['rows']}
        self.assertEqual((rows['character']['class'], rows['character']['cause']), ('EXPECTED', 'upstream changed'))
        self.assertIn('changed by content: intro (identical by content: bsp)', rows['character']['detail'])
        self.assertEqual((rows['hands']['class'], rows['hands']['cause']),
                         ('UNEXPECTED', 'refused with identical outputs'))

    def test_preflight_names_the_changed_files_and_flags_keys_the_diff_does_not_explain(self):
        """BUILD-REUSE-KEYS-TOO-BROAD-35: the reuse preflight explains every rebuild by the source diff against the
        reuse source's recorded tree, or by a real input change; a source key that changed with no file changed is
        UNEXPECTED (a key too broad), and a dev1-like full rebuild is loud."""
        old_sources = {'tools/a.py': '1', 'tools/b.py': '2', 'src/mwad/esm.py': '3'}
        files = {'tools/a.py': '1', 'tools/b.py': '2', 'src/mwad/esm.py': '4'}
        old = {'setup': {'sources': {'by_file': {'src/mwad/esm.py': 'u1'}}},
               'music': {'sources': {'by_file': {'tools/b.py': 'u1'}}, 'game_inputs': 'x'},
               'media': {'sources': {'by_file': {'tools/a.py': 'u1'}}}}
        new = {'setup': {'sources': {'by_file': {'src/mwad/esm.py': 'u2'}}},
               'music': {'sources': {'by_file': {'tools/b.py': 'u1'}}, 'game_inputs': 'y'},
               'media': {'sources': {'by_file': {'tools/a.py': 'u2'}}}}
        reasons = {'setup': 'changed: sources (src/mwad/esm.py)', 'music': 'changed: game_inputs',
                   'media': 'changed: sources (tools/a.py)', 'engine': build_cache.NON_REUSABLE['engine']}
        order = ['setup', 'music', 'media', 'engine']
        result = reuse_report.preflight(order, reasons, new, old, old_sources, files)
        rows = {row['stage']: row for row in result['rows']}
        self.assertEqual(result['source_diff']['changed'], ['src/mwad/esm.py'])
        self.assertEqual((rows['setup']['class'], rows['setup']['diff_files']), ('EXPECTED', ['src/mwad/esm.py']))
        self.assertEqual(rows['music']['class'], 'EXPECTED')          # a real input change, no source file needed
        self.assertEqual((rows['media']['class'], rows['media']['cause']), ('UNEXPECTED', 'not in the source diff'))
        self.assertEqual((result['reused'], result['unexpected'], result['policy']), (0, 1, 1))
        self.assertEqual(result['too_broad'], ['media'])
        with contextlib.redirect_stdout(io.StringIO()) as text:
            reuse_report.print_preflight(result)
        self.assertIn('NONE of the 3 reusable stages is reused', text.getvalue())
        self.assertIn('stopping before any stage runs', text.getvalue())
        self.assertIn('changed files: src/mwad/esm.py', text.getvalue())
        # A file the reuse source did not record cannot be proven unchanged: it explains the rebuild.
        result = reuse_report.preflight(order, reasons, new, old, {'src/mwad/esm.py': '3'}, files)
        self.assertEqual(result['unexpected'], 0)

    def test_a_stage_the_old_run_reused_without_a_replaced_file_follows_the_stage_that_replaced_it(self):
        """BUILD-REUSE-AUDIT-WITHOUT-REASON-36: the BUILD-REUSE-REDUCED-RECORD-36 reason was classed 'other',
        UNEXPECTED. It is an explained rebuild: EXPECTED unless a stage that replaced the file was itself rebuilt
        UNEXPECTED; the recorded reason is kept as the detail."""
        old_name = '2026_10_10_v0.0.36-dev3_full-coast-chim-regions-270-resume_e8f03ea'
        # The reason exactly as the v0.0.36-dev3 resume2 preflight printed it.
        unrecorded = (f'{old_name} reused it without intro-scene/asset-name-map.json (replaced there by a stage no '
                      'longer recorded), which this build runs again')
        named = (f'{old_name} reused it without intro-scene/asset-name-map.json (replaced there by harvest, '
                 'balmora), which this build runs again')
        self.assertEqual(reuse_report.followed_stages(named), ['harvest', 'balmora'])
        self.assertEqual(reuse_report.followed_stages(unrecorded), [])
        with tempfile.TemporaryDirectory() as temp:
            run, old = Path(temp) / 'new', Path(temp) / 'old'
            state(run, old, ['intro', 'scenery', 'harvest', 'balmora'], {'scenery': {}},
                  {'intro': unrecorded, 'harvest': 'changed: sources (tools/prepare_harvest.py)',
                   'balmora': f'{old_name} reused it without scene/b.txt (replaced there by harvest), which this '
                              'build runs again'})
            result = reuse_report.report(run)
            rows = {row['stage']: row for row in result['rows']}
            self.assertEqual((rows['intro']['class'], rows['intro']['cause']), ('EXPECTED', 'reduced record'))
            self.assertEqual(rows['intro']['detail'], unrecorded)
            self.assertEqual(rows['balmora']['class'], 'EXPECTED')
            self.assertEqual(result['unexpected'], 0)
            code, text = self.audit(run)
            self.assertEqual(code, 0, text)
            self.assertIn('reduced record: ' + unrecorded[:80], text)
            # The stage that replaced the file was rebuilt for an over-broad key: the follower is unexpected too.
            state(run, old, ['intro', 'harvest'], {},
                  {'intro': named, 'harvest': 'changed: sources (tools/release-files.json)'})
            rows = {row['stage']: row for row in reuse_report.report(run)['rows']}
            self.assertEqual((rows['harvest']['class'], rows['intro']['class']), ('UNEXPECTED', 'UNEXPECTED'))
        # The reuse preflight classes it the same way.
        result = reuse_report.preflight(['intro', 'engine'], {'intro': unrecorded,
                                                              'engine': build_cache.NON_REUSABLE['engine']},
                                        {}, {}, {}, {})
        self.assertEqual(([row['class'] for row in result['rows']], result['unexpected']), (['EXPECTED', 'EXPECTED'], 0))

    def test_not_a_reuse_run(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            run.mkdir()
            (run / 'build-state.json').write_text(json.dumps({'steps': [], 'stage_cache': {}}))
            self.assertEqual(self.audit(run)[0], 2)


if __name__ == '__main__':
    unittest.main()
