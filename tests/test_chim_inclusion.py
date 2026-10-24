# SPDX-License-Identifier: GPL-3.0-only
"""tools/chim_inclusion.py: the world map's inclusion ledger is written from a build's records, never by hand.

Built by the builder at the end of every CHIM build (the run's toolkit copy), packaged by the packaging step, released
into the repository ledger by the release step; tools/release.py refuses a release the ledger lacks
(TRACKER-INCLUSION-NOT-RUN-SINCE-44-48)."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import chim_inclusion as I  # noqa: E402

SHA_A, SHA_B = 'a' * 64, 'b' * 64


class InclusionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        frames = [{'cell': [1, 2], 'town': 'rcm1_p2'}, {'cell': [-3, -9], 'town': 'seyda'},
                  {'cell': [0, -11], 'town': 'rcm0_m11'}, {'cell': [5, -2], 'town': 'rcp5_m2'}]
        (self.tmp / 'source.json').write_text(json.dumps({'frames': frames}))
        (self.tmp / 'cells.json').write_text(json.dumps({'format': 'aw-chim-cells-1',
                                                         'cells': [[1, 2], [0, -11], [-1, -11]]}))

    def test_entry_lists_region_cells_towns_and_overlaps(self):
        e = I.entry('v9.9.9-dev1', 'packaged', 'abc', self.tmp / 'source.json', self.tmp / 'cells.json',
                    SHA_A, SHA_B, 'readback', now='2026-10-16T00:00:00+00:00')
        self.assertEqual(e['cells'], {'0,-11': {'state': 'included', 'frame': 'rcm0_m11'},
                                      '1,2': {'state': 'included', 'frame': 'rcm1_p2'},
                                      '5,-2': {'state': 'included', 'frame': 'rcp5_m2'}})
        self.assertEqual(e['town_frames'], ['seyda'])
        self.assertEqual(e['partial_town_overlap_cells'], ['-1,-11'])
        self.assertFalse(e['owner_accepted'])
        self.assertIn('Packaging does not certify', e['scope'])

    def test_town_frame_cells_are_included_with_their_town(self):
        frames = [{'cell': [1, 2], 'town': 'rcm1_p2'},
                  {'cell': [3, -10], 'town': 'vivec_city',
                   'frame_ownership': {'core': [8192.0, -90112.0, 24576.0, -73728.0]}}]
        (self.tmp / 'towns.json').write_text(json.dumps({'frames': frames}))
        e = I.entry('v9', 'packaged', 'abc', self.tmp / 'towns.json', self.tmp / 'cells.json', SHA_A, SHA_B,
                    'x', now='2026-10-16T00:00:00+00:00')
        self.assertEqual({k: v['frame'] for k, v in e['cells'].items()},
                         {'1,2': 'rcm1_p2', '1,-11': 'vivec_city', '1,-10': 'vivec_city',
                          '2,-11': 'vivec_city', '2,-10': 'vivec_city'})
        self.assertEqual(e['town_frames'], ['vivec_city'])
        self.assertIn('1 regional whole cells and 4 cells inside town frames (vivec_city)', e['scope'])

    def test_write_replaces_the_same_version_and_keeps_newest_first(self):
        old = {'version': 'v1', 'state': 'released', 'cells': {}, 'generated': '2026-01-01'}
        (self.tmp / 'chim-inclusion.json').write_text(json.dumps({'format': I.FORMAT, 'builds': [old]}))
        new = I.entry('v2', 'packaged', 'abc', self.tmp / 'source.json', self.tmp / 'cells.json', SHA_A,
                      SHA_B, 'x', now='2026-10-16T00:00:00+00:00')
        doc = I.write(self.tmp, new)
        doc = I.write(self.tmp, dict(new, evidence='y'))
        self.assertEqual([b['version'] for b in doc['builds']], ['v2', 'v1'])
        self.assertEqual(doc['builds'][0]['evidence'], 'y')
        js = (self.tmp / 'chim-inclusion.js').read_text(encoding='utf-8')
        self.assertTrue(js.startswith('window.ChimInclusionMetadata = {') and js.endswith('};\n'))
        self.assertEqual(json.loads(js[len('window.ChimInclusionMetadata = '):-2]),
                         json.loads((self.tmp / 'chim-inclusion.json').read_text()))
        self.assertEqual(I.load(self.tmp), doc)
        self.assertEqual(list(self.tmp.glob('*.tmp')), [])

    # -- states: one function decides what each needs ------------------------------------------------------------
    def test_built_needs_no_archive_or_readback_and_says_so(self):
        e = I.entry('v9.9.9-dev1', 'built', 'abc', self.tmp / 'source.json', None, run='RUN', now='t')
        self.assertEqual((e['state'], e['archive_sha256'], e['evidence_sha256'], e['run']), ('built', None, None, 'RUN'))
        self.assertIn('Built, not packaged yet', e['scope'])
        self.assertIn('not packaged yet', e['evidence'])
        self.assertEqual(e['partial_town_overlap_cells'], [])
        with self.assertRaisesRegex(ValueError, 'no archive or readback yet'):
            I.entry('v9', 'built', 'abc', self.tmp / 'source.json', None, archive_sha256=SHA_A)

    def test_packaged_and_released_need_archive_readback_and_evidence(self):
        for state in I.EVIDENCE_STATES:
            for missing in ('archive', 'readback', 'evidence'):
                given = {'archive_sha256': SHA_A, 'readback_sha256': SHA_B, 'evidence': 'x'}
                given[{'archive': 'archive_sha256', 'readback': 'readback_sha256'}.get(missing, missing)] = None
                with self.subTest(state=state, missing=missing), self.assertRaisesRegex(ValueError, missing):
                    I.entry('v9', state, 'abc', self.tmp / 'source.json', None, **given)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            I.entry('v9', 'packaged', 'abc', self.tmp / 'source.json', None, 'nothex', SHA_B, 'x')
        with self.assertRaisesRegex(ValueError, 'one of built, packaged, released'):
            I.with_evidence({'cells': {}, 'town_frames': []}, 'shipped')

    def test_cells_from_the_builders_encoded_list(self):
        e = I.entry('v9', 'built', 'abc', self.tmp / 'source.json', None, cells_text='1,2:l 0,-11:s -1,-11:l 7,7:o')
        self.assertEqual(e['partial_town_overlap_cells'], ['-1,-11', '7,7'])

    def test_the_repository_writer_takes_no_built_entry_and_the_flag_form_needs_evidence(self):
        ledger = self.tmp / 'ledger'
        built = I.entry('v9', 'built', 'abc', self.tmp / 'source.json', None, run='R')
        with self.assertRaisesRegex(ValueError, 'packaged and released builds only'):
            I.write(ledger, built)
        for state in ('built', 'packaged'):
            with self.subTest(state=state), self.assertRaises(SystemExit):
                I.main(['--version', 'v9', '--state', state, '--source-commit', 'abc', '--chim-source',
                        str(self.tmp / 'source.json'), '--ledger', str(ledger)])
        # a built entry already in a repository ledger (by hand) is dropped by the next write
        I.save(ledger, {'format': I.FORMAT, 'builds': [built]})
        doc = I.write(ledger, I.entry('v8', 'packaged', 'abc', self.tmp / 'source.json', None, SHA_A, SHA_B, 'x'))
        self.assertEqual([b['state'] for b in doc['builds']], ['packaged'])

    def test_compact_form_round_trips_and_the_earlier_form_still_loads(self):
        frames = [{'cell': [-19, 14], 'town': 'rcm19_p14'}, {'cell': [22, 0], 'town': 'rcp22_p0'},
                  {'cell': [0, 0], 'town': 'rcm5_p5'},            # a region frame not named after its cell
                  {'cell': [3, -10], 'town': 'vivec_city', 'frame_ownership': {'core': [8192.0, -90112.0, 24576.0, -73728.0]}}]
        (self.tmp / 'mixed.json').write_text(json.dumps({'frames': frames}))
        e = I.entry('v9', 'packaged', 'abc', self.tmp / 'mixed.json', None, SHA_A, SHA_B, 'x', now='t')
        stored = I.compact_entry(e)
        self.assertNotIn('cells', stored)
        self.assertEqual(stored['region_cells'], '-19,14 22,0')
        self.assertEqual(stored['frame_cells'], {'rcm5_p5': '0,0', 'vivec_city': '1,-11 1,-10 2,-11 2,-10'})
        self.assertEqual(I.expand_entry(stored), e)
        ledger = self.tmp / 'ledger'
        I.save(ledger, {'format': I.FORMAT, 'builds': [e]})
        text = (ledger / I.LEDGER_FILE).read_text()
        self.assertEqual(json.loads(text)['builds'][0]['region_cells'], '-19,14 22,0')
        self.assertNotIn('\n ', text)                                   # no indentation
        self.assertEqual(I.load(ledger)['builds'][0], e)
        old = dict(e, state='released')                                 # the earlier per-cell form, indented
        (ledger / I.LEDGER_FILE).write_text(json.dumps({'format': I.FORMAT, 'builds': [old]}, indent=2))
        self.assertEqual(I.load(ledger)['builds'][0], old)
        odd = dict(e, cells=dict(e['cells'], **{'9,9': {'state': 'listed', 'frame': 'rcp9_p9'}}))
        self.assertEqual(I.compact_entry(odd), odd)                     # a non-included cell keeps the per-cell form

    def test_the_repository_ledger_stays_under_its_limit_with_room_for_30_more_full_builds(self):
        import release
        limit = release.text_limit('amiwind-toolkit/chim-inclusion.json')
        doc = I.load(I.LEDGER)
        self.assertEqual([b['version'] for b in doc['builds'] if b.get('state') == 'built'], [])
        self.assertEqual(I.ledger_text(doc), (I.LEDGER / I.LEDGER_FILE).read_text(encoding='utf-8'))
        self.assertEqual(I.script_text(doc), (I.LEDGER / I.SCRIPT_FILE).read_text(encoding='utf-8'))
        size = max((I.LEDGER / name).stat().st_size for name in (I.LEDGER_FILE, I.SCRIPT_FILE))
        # a full-island entry: every Vvardenfell cell of the newest build, in the stored form
        largest = max(len(json.dumps(I.compact_entry(b), separators=(',', ':'))) + 2 for b in doc['builds'])
        self.assertLess(size + 30 * largest, limit, 'ledger %d bytes, full entry %d bytes, limit %d' % (size, largest, limit))

class BuildPackageReleaseTests(unittest.TestCase):
    """The builder's step, packaging and the release step on a synthetic run and repository ledger."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / 'repo-toolkit'
        self.repo.mkdir()
        self.old = {'version': 'v0.0.47', 'state': 'released', 'cells': {'1,2': {'state': 'included', 'frame': 'rcm1_p2'}},
                    'generated': '2026-10-21T00:00:00+00:00', 'archive_sha256': SHA_A, 'evidence_sha256': SHA_B}
        I.save(self.repo, {'format': I.FORMAT, 'builds': [self.old]})
        self.repo_text = (self.repo / I.LEDGER_FILE).read_text()
        self.run = self.tmp / '2026_10_22_v0.0.48-dev2_full_abc1234'
        (self.run / 'chim-world').mkdir(parents=True)
        self.source([{'cell': [1, 2], 'town': 'rcm1_p2'}, {'cell': [5, -2], 'town': 'rcp5_m2'}])
        self.log = []

    def source(self, frames):
        (self.run / 'chim-world' / 'chim-source.json').write_text(json.dumps({'frames': frames}))

    def step(self, **kw):
        return I.build_step(self.run, kw.pop('version', '0.0.48-dev2'), kw.pop('commit', 'abc1234'),
                            kw.pop('cells', '1,2:l 5,-2:l'), ledger=self.repo, log=self.log.append, **kw)

    def mine(self):
        return I.load(self.run / 'toolkit')

    def test_the_build_writes_its_entry_on_top_of_the_repository_ledger(self):
        e = self.step()
        self.assertEqual((e['version'], e['run'], e['state'], e['source_commit']),
                         ('v0.0.48-dev2', self.run.name, 'built', 'abc1234'))
        self.assertEqual(sorted(e['cells']), ['1,2', '5,-2'])
        doc = self.mine()
        self.assertEqual([b['version'] for b in doc['builds']], ['v0.0.48-dev2', 'v0.0.47'])
        js = (self.run / 'toolkit' / I.SCRIPT_FILE).read_text()
        stored = json.loads((self.run / 'toolkit' / I.LEDGER_FILE).read_text())
        self.assertEqual(json.loads(js[len(I.SCRIPT_PREFIX):-2]), stored)
        self.assertEqual((self.repo / I.LEDGER_FILE).read_text(), self.repo_text)    # the repository is never touched

    def test_a_build_entry_sits_on_top_even_when_an_entry_is_newer(self):
        I.save(self.repo, {'format': I.FORMAT, 'builds': [dict(self.old, generated='2999-01-01')]})
        self.step(now='2026-10-22T00:00:00+00:00')
        self.assertEqual(self.mine()['builds'][0]['run'], self.run.name)

    def test_unchanged_inputs_are_reused_and_a_changed_world_is_not(self):
        first = self.step()
        stamp = (self.run / 'toolkit' / I.LEDGER_FILE).stat().st_mtime_ns
        self.assertEqual(self.step(), first)
        self.assertIn('reused', self.log[-1])
        self.assertEqual((self.run / 'toolkit' / I.LEDGER_FILE).stat().st_mtime_ns, stamp)
        self.source([{'cell': [1, 2], 'town': 'rcm1_p2'}])
        second = self.step()
        self.assertEqual(sorted(second['cells']), ['1,2'])
        self.assertNotEqual(second['inputs_sha256'], first['inputs_sha256'])
        for changed in ({'commit': 'def5678'}, {'cells': '1,2:l'}, {'version': '0.0.48-dev3'}):
            with self.subTest(changed=changed):
                self.assertNotIn('reused', (self.step(**changed) and self.log[-1]))

    def test_a_changed_repository_ledger_keeps_the_packaged_entry(self):
        self.step()
        (self.tmp / 'pkg.zip').write_bytes(b'zip')
        (self.tmp / 'readback.json').write_bytes(b'{}')
        I.package(self.run, self.tmp / 'pkg.zip', self.tmp / 'readback.json', 'boot smoke PASS')
        I.save(self.repo, {'format': I.FORMAT, 'builds': [self.old, dict(self.old, version='v0.0.46')]})
        e = self.step()
        self.assertEqual(e['state'], 'packaged')
        self.assertEqual([b['version'] for b in self.mine()['builds']], ['v0.0.48-dev2', 'v0.0.47', 'v0.0.46'])

    def test_no_chim_world_writes_nothing(self):
        shutil.rmtree(self.run / 'chim-world')
        self.assertIsNone(self.step())
        self.assertFalse((self.run / 'toolkit').exists())

    def test_packaging_upgrades_the_runs_entry_with_the_same_function(self):
        self.step()
        (self.tmp / 'pkg.zip').write_bytes(b'zip')
        (self.tmp / 'readback.json').write_bytes(b'{}')
        self.assertEqual(I.main(['package', '--run', str(self.run), '--archive', str(self.tmp / 'pkg.zip'),
                                 '--readback', str(self.tmp / 'readback.json'), '--evidence', 'boot smoke PASS']), 0)
        e = I.run_entry(self.mine(), self.run.name)
        self.assertEqual(e['state'], 'packaged')
        self.assertEqual(e['archive_sha256'], I.sha256(self.tmp / 'pkg.zip'))
        self.assertEqual(e['evidence_sha256'], I.sha256(self.tmp / 'readback.json'))
        self.assertIn('Packaging does not certify', e['scope'])
        self.assertEqual(len(self.mine()['builds']), 2)
        other = self.tmp / 'other-run'
        (other / 'toolkit').mkdir(parents=True)
        I.save(other / 'toolkit', {'format': I.FORMAT, 'builds': []})
        with self.assertRaisesRegex(ValueError, 'no inclusion entry'):
            I.package(other, self.tmp / 'pkg.zip', self.tmp / 'readback.json', 'x')

    def test_the_release_step_needs_a_packaged_entry_and_writes_the_repository_ledger(self):
        self.step(version='0.0.48')
        with self.assertRaisesRegex(ValueError, 'package it first'):
            I.release(self.run, self.repo)
        self.assertEqual(I.release_problems('0.0.48', self.repo)[0].split(':')[0],
                         'the CHIM inclusion ledger (amiwind-toolkit/chim-inclusion.json) lacks v0.0.48')
        (self.tmp / 'pkg.zip').write_bytes(b'zip')
        (self.tmp / 'readback.json').write_bytes(b'{}')
        I.package(self.run, self.tmp / 'pkg.zip', self.tmp / 'readback.json', 'boot smoke PASS')
        I.save(self.repo, {'format': I.FORMAT, 'builds': [self.old, dict(self.old, version='v0.0.48', state='packaged')]})
        self.assertIn('only as packaged', I.release_problems('v0.0.48', self.repo)[0])
        self.assertEqual(I.main(['release', '--run', str(self.run), '--ledger', str(self.repo)]), 0)
        doc = I.load(self.repo)
        released = [b for b in doc['builds'] if b['version'] == 'v0.0.48']
        self.assertEqual(len(released), 1)                         # replaces every entry of that version
        self.assertEqual((released[0]['state'], released[0]['shipped'], released[0]['archive_sha256']),
                         ('released', True, I.sha256(self.tmp / 'pkg.zip')))
        self.assertEqual(I.release_problems('0.0.48', self.repo), [])
        self.assertEqual(I.main(['check-release', '--version', 'v0.0.48', '--ledger', str(self.repo)]), 0)
        self.assertEqual(I.main(['check-release', '--version', 'v0.0.49', '--ledger', str(self.repo)]), 1)

    def test_the_served_ledger_is_the_builds_own_or_the_newest_runs_on_top(self):
        self.assertEqual(I.served_ledger(None, None, self.repo)['builds'][0]['version'], 'v0.0.47')
        self.step()
        doc = I.served_ledger(self.run / 'toolkit', None, self.repo)
        self.assertEqual(doc['builds'][0]['run'], self.run.name)
        builds = self.tmp / 'builds'
        builds.mkdir()
        names = []
        for i in range(3):
            run = builds / ('2026_10_2%d_v0.0.48-dev2_full_abc123%d' % (i, i))
            (run / 'chim-world').mkdir(parents=True)
            shutil.copy(self.run / 'chim-world' / 'chim-source.json', run / 'chim-world')
            I.build_step(run, '0.0.48-dev2', 'abc', ledger=self.repo, log=lambda line: None)
            names.append(run.name)
        (builds / 'not-a-run').mkdir()
        doc = I.served_ledger(None, builds, self.repo, limit=2)
        self.assertEqual([b.get('run') for b in doc['builds']], [names[2], names[1], None])


class BuilderStepTests(unittest.TestCase):
    """tools/build.py inclusion_step: after a passed build with a CHIM world; never fails the build."""

    def setUp(self):
        import build
        self.build = build
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run = self.tmp / '2026_10_22_v0.0.48-dev2_full_abc1234'
        (self.run / 'chim-world').mkdir(parents=True)
        (self.run / 'chim-world' / 'chim-source.json').write_text(json.dumps({'frames': [{'cell': [1, 2], 'town': 'rcm1_p2'}]}))

    def args(self, **kw):
        return argparse.Namespace(**dict({'stage': 'aga', 'dry_run': False, 'run_name_record': {'commit': 'abc1234'},
                                          'chim_regions_cells': '1,2:l 3,3:s'}, **kw))

    def test_writes_the_runs_entry(self):
        e = self.build.inclusion_step(self.args(), self.run)
        self.assertEqual((e['version'], e['source_commit'], e['partial_town_overlap_cells']),
                         ('v' + self.build.VERSION, 'abc1234', ['3,3']))
        self.assertEqual(I.load(self.run / 'toolkit')['builds'][0]['run'], self.run.name)

    def test_skipped_without_a_chim_world_or_for_a_dry_run(self):
        self.assertIsNone(self.build.inclusion_step(self.args(dry_run=True), self.run))
        self.assertIsNone(self.build.inclusion_step(self.args(stage='setup'), self.run))
        shutil.rmtree(self.run / 'chim-world')
        self.assertIsNone(self.build.inclusion_step(self.args(), self.run))

    def test_a_problem_is_a_warning(self):
        (self.run / 'toolkit').write_text('a file where the folder should be')
        from contextlib import redirect_stdout
        import io
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertIsNone(self.build.inclusion_step(self.args(), self.run))
        self.assertIn('WARNING: the CHIM inclusion entry was not written', out.getvalue())

    def test_it_is_no_stage_and_runs_beside_the_size_ledger(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        main = text[text.index('size_verdict = size_ledger_step(args, run)') - 400:]
        self.assertLess(main.index('inclusion.start()'), main.index('size_verdict = size_ledger_step(args, run)'))
        self.assertLess(main.index('resource_after_build(args, run)'), main.index('inclusion.join()'))
        self.assertLess(main.index('inclusion.join()'), main.index('live.stop()'))
        import build_parallel
        self.assertNotIn('chim-inclusion', build_parallel.DEPENDENCIES)
        # no stage tool reaches it: it keys no stage (the reuse rules, docs/BUILD_CACHE.md)
        for tool in (ROOT / 'tools').glob('*.py'):
            if tool.name not in ('build.py', 'chim_inclusion.py', 'toolkit_serve.py', 'release.py', 'cell_progress_md.py'):
                with self.subTest(tool=tool.name):
                    self.assertNotIn('import chim_inclusion', tool.read_text(encoding='utf-8'))


class ServedAndLiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run = self.tmp / 'run'
        (self.run / 'chim-world').mkdir(parents=True)
        (self.run / 'chim-world' / 'chim-source.json').write_text(json.dumps({'frames': [{'cell': [1, 2], 'town': 'rcm1_p2'}]}))
        I.build_step(self.run, '0.0.48-dev2', 'abc', log=lambda line: None)

    def test_toolkit_serve_answers_the_builds_own_ledger(self):
        import toolkit_serve
        H = toolkit_serve.Handler
        saved = (H.progress_dir, H.builds_dir)
        self.addCleanup(lambda: setattr(H, 'progress_dir', saved[0]) or setattr(H, 'builds_dir', saved[1]))
        H.progress_dir, H.builds_dir = self.run / 'toolkit', None
        server = toolkit_serve.ThreadingHTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = 'http://127.0.0.1:%d/amiwind-toolkit/' % server.server_address[1]
        js = urllib.request.urlopen(base + 'chim-inclusion.js', timeout=10).read().decode('utf-8')
        self.assertEqual(json.loads(js[len(I.SCRIPT_PREFIX):-2])['builds'][0]['run'], 'run')
        doc = json.loads(urllib.request.urlopen(base + 'chim-inclusion.json', timeout=10).read())
        self.assertEqual(doc['builds'][0]['state'], 'built')

    def test_the_live_page_copies_the_runs_ledger(self):
        import live_tracker as lt
        t = lt.LiveTracker(self.run, 'file', total_stages=1, say=lambda line: None)
        (self.run / 'toolkit' / 'cell-progress.json').write_text(json.dumps({'format': 'aw-cell-progress-1'}))
        t._publish({'state': 'running'})
        live = self.run / 'toolkit' / lt.LIVE_FOLDER
        for name in lt.RUN_FILES:
            self.assertEqual((live / name).read_bytes(), (self.run / 'toolkit' / name).read_bytes())


class WorldMapPageTests(unittest.TestCase):
    PAGE = ROOT / 'amiwind-toolkit' / 'world-map.html'

    def helpers(self):
        text = self.PAGE.read_text(encoding='utf-8')
        start = text.index('function inclusionKey(b)')
        end = text.index('function inclusionBuild()')
        return text[start:end]

    def test_states_and_run_keys(self):
        text = self.PAGE.read_text(encoding='utf-8')
        for old in ("(b.state === 'packaged' ? ' - packaged' : ' - pending')", "b.state === 'packaged' && b.cells[key]",
                    'inclusionBuilds = d.builds;'):
            self.assertNotIn(old, text)                                 # released and built are states too
        self.assertIn('inclusionBuilds = d.builds.map(inclusionExpand);', text)
        self.assertIn("value=\"' + escapeHtml(inclusionKey(b))", text)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_helpers_label_and_verify_each_state(self):
        script = self.helpers() + '''
const builds = [{version: 'v0.0.48-dev2', run: 'R', state: 'built'}, {version: 'v0.0.47', state: 'released'},
                {version: 'v0.0.44-dev1', state: 'packaged'}, {version: 'v1', state: 'other'}];
console.log(JSON.stringify(builds.map(b => [inclusionKey(b), inclusionVerified(b), inclusionStateLabel(b)])));'''
        out = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), [['v0.0.48-dev2 R', False, 'built, not packaged'],
                                                  ['v0.0.47', True, 'released'], ['v0.0.44-dev1', True, 'packaged'],
                                                  ['v1', False, 'pending']])

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_page_expands_the_compact_form_like_the_writer(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        frames = [{'cell': [-19, 14], 'town': 'rcm19_p14'}, {'cell': [22, 0], 'town': 'rcp22_p0'},
                  {'cell': [3, -10], 'town': 'vivec_city', 'frame_ownership': {'core': [8192.0, -90112.0, 24576.0, -73728.0]}}]
        (tmp / 'source.json').write_text(json.dumps({'frames': frames}))
        e = I.entry('v9', 'packaged', 'abc', tmp / 'source.json', None, SHA_A, SHA_B, 'x', now='t')
        script = self.helpers() + '''
const stored = %s, old = %s;
console.log(JSON.stringify([inclusionExpand(stored).cells, inclusionExpand(old).cells]));''' % (
            json.dumps(I.compact_entry(e)), json.dumps(e))
        out = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), [e['cells'], e['cells']])

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_page_script_parses(self):
        text = self.PAGE.read_text(encoding='utf-8')
        scripts = [s for s in re.findall(r'<script>(.*?)</script>', text, re.S) if 'inclusionKey' in s]
        self.assertEqual(len(scripts), 1)
        f = Path(tempfile.mkdtemp()) / 'page.js'
        self.addCleanup(shutil.rmtree, f.parent, True)
        f.write_text(scripts[0], encoding='utf-8')
        out = subprocess.run(['node', '--check', str(f)], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == '__main__':
    unittest.main()
