"""Size ledger (tools/size_ledger.py, docs/BUILD_OUTPUT.md "Size ledger"): payload per folder in GiB, compared
like-for-like only, and the size guard."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import size_ledger  # noqa: E402

GIB = size_ledger.GIB
MIB = 1024 ** 2


def make_run(folder, boot_files, world_files=(), chim_bytes=0, gallery=True, excluded=(), build_type=None,
             version='0.0.42', receipt_dh0=None):
    """A fake finished run: image/boot files, a world partition list, a CHIM volume and the image receipt."""
    run = Path(folder) / 'run'
    boot = run / 'image' / 'boot'
    for path, size in boot_files.items():
        target = boot / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'x' * size)
    dh0 = sum(boot_files.values())
    partitions = [{'partition': 'DH0', 'payload_bytes': dh0 if receipt_dh0 is None else receipt_dh0,
                   'files': len(boot_files), 'hdf_file': 'AmiWind.hdf'}]
    if world_files:
        partitions.append({'partition': 'DW0', 'payload_bytes': sum(world_files.values()),
                           'files': len(world_files), 'hdf_file': 'AmiWind.hdf'})
        (run / 'image' / 'world-partitions.json').write_text(json.dumps({'partitions': [
            {'partition': 'DW0', 'files': [{'path': p, 'bytes': n} for p, n in world_files.items()]}]}))
    if chim_bytes:
        partitions.append({'partition': 'DW1', 'payload_bytes': chim_bytes, 'files': 3, 'hdf_file': 'world-01.hdf'})
    record = {'version': version, 'partitions': partitions,
              'payload_bytes': sum(p['payload_bytes'] for p in partitions),
              'hdf_files': [{'file': 'AmiWind.hdf', 'bytes': 4 * GIB - 1}, {'file': 'world-01.hdf', 'bytes': GIB}],
              'chim_world': {'partition': 'DW1'} if chim_bytes else {'status': 'not_requested'},
              'npc_gallery': {'status': 'passed'} if gallery else {'status': 'disabled'},
              'excluded_content': {'groups': list(excluded)}}
    if build_type:
        record['build_type'] = build_type
    (run / 'image' / 'build.json').write_text(json.dumps(record))
    return run


BOOT = {'AmiWind': 100, 'S/startup-sequence': 10, 'id1/maps/a.bsp': 1000, 'id1/maps/f.chim': 200,
        'id1/maps/f.far': 20, 'id1/gallery/n.mdl': 300, 'id1/sound/pool/s.wav': 40, 'id1/music/t.mws': 50,
        'id1/intro/mw.awv': 60, 'id1/progs/p.mdl': 70, 'id1/media/catalogue.json': 5, 'id1/default.cfg': 1}


class GroupingTests(unittest.TestCase):
    def test_paths_fall_into_their_folders(self):
        cases = {'id1/maps/vf0001.bsp': 'classic-maps', 'id1/maps/vf2563.chim': 'chim-world',
                 'id1/maps/seyda-chim.far': 'chim-world', 'id1/chim/frames/x-09/y+18/s07.ccs': 'chim-world',
                 'id1/gallery/a.mdl': 'npc-gallery', 'id1/sound/npc/x.wav': 'sound', 'id1/music/track08.mws': 'music',
                 'id1/intro/amiwind.awv': 'video', 'id1/other/clip.awv': 'video', 'id1/progs/body/x.mdl': 'progs',
                 'id1/media/catalogue.json': 'other', 'AmiWind': 'other', 'S/startup-sequence': 'other',
                 'id1/doors.txt': 'other'}
        for path, group in cases.items():
            self.assertEqual(size_ledger.group_of(path), group, path)

    def test_run_is_grouped_and_checked_against_the_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            run = make_run(folder, BOOT, world_files={'id1/maps/w.bsp': 500, 'id1/maps/w.chim': 30}, chim_bytes=900)
            ledger = size_ledger.collect(run)
        self.assertEqual(ledger['status'], 'complete', ledger['checks'])
        groups = {name: row['bytes'] for name, row in ledger['groups'].items()}
        self.assertEqual(groups, {'classic-maps': 1500, 'chim-world': 200 + 20 + 30 + 900, 'npc-gallery': 300,
                                  'sound': 40, 'music': 50, 'video': 60, 'progs': 70, 'other': 116})
        self.assertEqual(ledger['payload_bytes'], sum(BOOT.values()) + 530 + 900)
        self.assertEqual(ledger['payload_bytes'], ledger['receipt_payload_bytes'])
        self.assertEqual(ledger['drive_bytes'], 5 * GIB - 1)

    def test_a_partition_that_does_not_add_up_makes_the_ledger_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            run = make_run(folder, BOOT, receipt_dh0=sum(BOOT.values()) + 7)
            ledger = size_ledger.collect(run)
        self.assertEqual(ledger['status'], 'partial')
        self.assertIn('DH0', ledger['checks'][0])

    def test_no_image_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                size_ledger.collect(Path(folder))


class FormatTests(unittest.TestCase):
    def test_gib_has_two_decimals_and_no_negative_zero(self):
        self.assertEqual(size_ledger.gib(4089367880), '3.81')
        self.assertEqual(size_ledger.gib(228011160), '0.21')
        self.assertEqual(size_ledger.gib(-MIB), '0.00')
        self.assertEqual(size_ledger.signed_gib(228011160), '+0.21')
        self.assertEqual(size_ledger.signed_gib(-228011160), '-0.21')
        self.assertEqual(size_ledger.signed_gib(MIB), '0.00')

    def test_the_committed_release_baseline_is_a_complete_record(self):
        record = size_ledger.load_record(size_ledger.RELEASE_BASELINE)
        self.assertEqual(record['version'], '0.0.41')
        self.assertEqual(record['status'], 'complete')
        self.assertEqual(record['labels'], [])
        self.assertEqual(sum(row['bytes'] for row in record['groups'].values()), record['payload_bytes'])
        self.assertEqual(size_ledger.gib(record['payload_bytes']), '3.81')
        self.assertEqual(size_ledger.gib(record['groups']['npc-gallery']['bytes']), '0.21')


class ComparabilityTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(size_ledger.labels({'npc_gallery': True, 'partial_area': None, 'excluded': []}), [])
        self.assertEqual(size_ledger.labels({'npc_gallery': False, 'partial_area': 'MiniWind balmora (exterior)',
                                             'excluded': ['video']}),
                         ['gallery off', 'partial area: MiniWind balmora (exterior)', 'video excluded'])

    def test_profile_reads_gallery_partial_area_and_exclusions(self):
        content = size_ledger.profile({'npc_gallery': {'status': 'disabled'},
                                       'excluded_content': {'groups': ['video', 'npc-gallery']},
                                       'build_type': {'town': 'balmora', 'scope': 'exterior'}})
        self.assertEqual(content, {'npc_gallery': False, 'partial_area': 'MiniWind balmora (exterior)',
                                   'excluded': ['video']})

    def baseline(self, folder, **kwargs):
        with tempfile.TemporaryDirectory() as other:
            record = size_ledger.collect(make_run(other, BOOT, **kwargs))
        path = Path(folder) / ('base-%d.json' % len(list(Path(folder).glob('base-*'))))
        path.write_text(json.dumps(record))
        return path

    def test_gallery_off_is_never_like_for_like_and_not_judged(self):
        with tempfile.TemporaryDirectory() as folder:
            base = self.baseline(folder)
            run = make_run(folder, {k: v for k, v in BOOT.items() if 'gallery' not in k}, gallery=False)
            ledger = size_ledger.build_ledger(run, '0.0.42', [], 'fail', release_baseline=base)
        row = ledger['comparisons'][0]
        self.assertFalse(row['like_for_like'])
        self.assertIn('gallery off', ' '.join(row['not_comparable_because']))
        self.assertEqual(ledger['guard']['verdict'], 'not-comparable')
        self.assertIn('NOT like-for-like', '\n'.join(size_ledger.table_lines(ledger)))

    def test_partial_area_and_excluded_video_are_not_like_for_like(self):
        with tempfile.TemporaryDirectory() as folder:
            base = self.baseline(folder)
            cases = ({'build_type': {'town': 'balmora', 'scope': 'exterior'}}, {'excluded': ['video']})
            for index, kwargs in enumerate(cases):
                run = make_run(Path(folder) / str(index), BOOT, **kwargs)
                ledger = size_ledger.build_ledger(run, '0.0.42', [], 'fail', release_baseline=base)
                self.assertFalse(ledger['comparisons'][0]['like_for_like'], kwargs)
                self.assertEqual(ledger['guard']['verdict'], 'not-comparable')


class GuardTests(unittest.TestCase):
    def grown(self, folder, version, mode, reason=None, extra=GIB // 10, margin=0.05):
        base_dir = Path(folder) / 'base'
        base = base_dir / 'record.json'
        base_dir.mkdir()
        base.write_text(json.dumps(size_ledger.collect(make_run(base_dir, BOOT))))
        boot = dict(BOOT, **{'id1/maps/big.bsp': extra})
        run = make_run(Path(folder) / 'now', boot)
        return size_ledger.build_ledger(run, version, [base], mode, margin, reason, release_baseline=None)

    def test_growth_within_the_margin_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.grown(folder, '0.0.42', 'fail', extra=GIB // 100)
        self.assertEqual(ledger['guard']['verdict'], 'passed')

    def test_growth_over_the_margin_fails_a_release_build(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.grown(folder, '0.0.42', 'auto')
        self.assertEqual(ledger['guard']['mode'], 'fail')
        self.assertEqual(ledger['guard']['verdict'], 'failed')
        self.assertEqual(ledger['guard']['grown'][0]['group'], 'classic-maps')
        self.assertIn('FAILED', size_ledger.guard_line(ledger['guard']))

    def test_growth_over_the_margin_only_warns_a_dev_build(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.grown(folder, '0.0.42-dev1', 'auto')
        self.assertEqual(ledger['guard']['verdict'], 'warned')

    def test_rc_is_judged_like_a_release(self):
        self.assertEqual(size_ledger.guard_mode('auto', '0.0.42-rc1'), 'fail')
        self.assertEqual(size_ledger.guard_mode('fail', '0.0.42-dev2'), 'fail')

    def test_a_named_reason_lets_growth_pass_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.grown(folder, '0.0.42', 'fail', reason='Vivec interiors added')
        self.assertEqual(ledger['guard']['verdict'], 'named')
        self.assertEqual(ledger['guard']['reason'], 'Vivec interiors added')

    def test_off_never_judges(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.grown(folder, '0.0.42', 'off')
        self.assertEqual(ledger['guard']['verdict'], 'off')

    def test_step_writes_the_ledger_skips_without_an_image_and_an_unreadable_receipt_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            run = make_run(folder, BOOT)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                verdict = size_ledger.step(run, '0.0.42', mode='fail')
            self.assertEqual(verdict, 'passed')
            written = size_ledger.read(run)
            self.assertEqual(written['schema'], size_ledger.SCHEMA)
            self.assertEqual(written['comparisons'][0]['role'], 'release')
            empty = Path(folder) / 'empty'
            (empty / 'image').mkdir(parents=True)
            with contextlib.redirect_stdout(out):
                self.assertEqual(size_ledger.step(empty, '0.0.42', mode='fail'), 'skipped')
            self.assertIsNone(size_ledger.read(empty))
            (empty / 'image' / 'build.json').write_text('not json')
            with contextlib.redirect_stdout(out):
                self.assertEqual(size_ledger.step(empty, '0.0.42', mode='fail'), 'failed')
                self.assertEqual(size_ledger.step(empty, '0.0.42-dev1', mode='auto'), 'warned')
            self.assertEqual(size_ledger.read(empty)['guard']['verdict'], 'error')


if __name__ == '__main__':
    unittest.main()
