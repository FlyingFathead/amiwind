# SPDX-License-Identifier: GPL-3.0-only
"""B5 (v0.0.42): the CHIM stage's world conversion keeps its workers busy without changing a byte.

The source stage remembers its repeated reads per process (chim.source_memo, mwad.audit share_master,
import_town receipt files); the towns are prepared beside the region frames; the visibility rows of small
frames run whole on the workers. Each new path is checked against the method before v0.0.42. Synthetic data only.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def tree_bytes(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}


class SharedMasterTests(unittest.TestCase):
    """mwad.audit: one master parse per process, each audit with its own land table."""

    def setUp(self):
        from test_workflow import synthetic_install
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'Data Files'
        synthetic_install(self.data)

    def tearDown(self):
        from mwad import audit
        audit.share_master(False)
        self.tmp.cleanup()

    def run_audit(self, name, radius=0, missing_land=None):
        from mwad.audit import audit
        out = Path(self.tmp.name) / name
        with contextlib.redirect_stdout(io.StringIO()):
            audit(self.data, out, [0, 0], radius, 2, missing_land=missing_land)
        return tree_bytes(out)

    def test_shared_parse_writes_the_same_files(self):
        from mwad import audit
        plain = self.run_audit('plain', 1, 'flat')
        audit.share_master(True)
        hits, parses = audit.shared_master_stats()
        first = self.run_audit('first', 1, 'flat')
        again = self.run_audit('again', 1, 'flat')
        self.assertEqual(first, plain)
        self.assertEqual(again, plain)
        self.assertEqual(audit.shared_master_stats(), [hits + 1, parses + 1])

    def test_a_flat_audit_never_fills_the_next_audits_land(self):
        from mwad import audit
        audit.share_master(True)
        self.run_audit('flat', 1, 'flat')
        with self.assertRaises(ValueError):
            self.run_audit('strict', 1, None)

    def test_a_changed_master_is_parsed_again(self):
        from mwad import audit
        audit.share_master(True)
        self.run_audit('one')
        master = self.data / 'morrowind.esm'
        st = master.stat()
        os.utime(master, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
        parses = audit.shared_master_stats()[1]
        self.run_audit('two')
        self.assertEqual(audit.shared_master_stats()[1], parses + 1)


class ModelMemoTests(unittest.TestCase):
    """chim.source_memo: a model read is remembered by the model's bytes and handed out as a fresh copy."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name) / 'models.bsa'
        self.archive.write_bytes(b'0123456789abcdef' * 4)
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def fake_read(self, task):
        name, path, extent, collision = task
        self.calls.append(name)
        with open(path, 'rb') as f:
            f.seek(extent['offset'])
            raw = f.read(extent['bytes'])
        return name, raw, (([raw[:2]], [{'texture_source': 'x'}], [0, 1], []), []), None, None

    def test_second_read_of_the_same_bytes_is_remembered_and_copied(self):
        from chim import source_memo
        with mock.patch.dict(source_memo._STATE['originals'], {'read_model': self.fake_read}), \
                mock.patch.object(source_memo, '_MODELS', source_memo._Memory()):
            task = ('meshes/a.nif', str(self.archive), {'offset': 16, 'bytes': 8}, None)
            first = source_memo.read_model(task)
            first[2][0][1][0]['texture_index'] = 7      # the writer marks materials in place
            second = source_memo.read_model(task)
            self.assertEqual(self.calls, ['meshes/a.nif'])
            self.assertEqual(second, self.fake_read(task))
            self.assertNotIn('texture_index', second[2][0][1][0])

    def test_other_bytes_or_settings_are_read_again(self):
        from chim import source_memo
        with mock.patch.dict(source_memo._STATE['originals'], {'read_model': self.fake_read}), \
                mock.patch.object(source_memo, '_MODELS', source_memo._Memory()):
            source_memo.read_model(('meshes/a.nif', str(self.archive), {'offset': 0, 'bytes': 8}, None))
            source_memo.read_model(('meshes/a.nif', str(self.archive), {'offset': 8, 'bytes': 8}, None))
            source_memo.read_model(('meshes/a.nif', str(self.archive), {'offset': 8, 'bytes': 8}, 'root_node'))
            with mock.patch.dict(os.environ, {'AMIWIND_NO_FLAMES': '1'}):
                source_memo.read_model(('meshes/a.nif', str(self.archive), {'offset': 8, 'bytes': 8}, 'root_node'))
            self.assertEqual(len(self.calls), 4)

    def test_off_reads_every_time(self):
        from chim import source_memo
        with mock.patch.dict(source_memo._STATE['originals'], {'read_model': self.fake_read}), \
                mock.patch.object(source_memo, '_MODELS', source_memo._Memory()), \
                mock.patch.dict(os.environ, {source_memo.ENV: 'off'}):
            task = ('meshes/a.nif', str(self.archive), {'offset': 0, 'bytes': 8}, None)
            source_memo.read_model(task)
            source_memo.read_model(task)
            self.assertEqual(len(self.calls), 2)

    def test_memory_stays_within_its_limit(self):
        from chim import source_memo
        memory = source_memo._Memory()
        with mock.patch.dict(os.environ, {source_memo.LIMIT_ENV: '1'}):
            for i in range(40):
                memory.put(i, b'x' * 100_000)
            self.assertLessEqual(memory.size, 1024 * 1024)
            self.assertIsNone(memory.get(0))
            self.assertEqual(memory.get(39), b'x' * 100_000)

    def test_only_the_chim_stage_installs_it(self):
        uses = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'tools').rglob('*.py')
                if 'source_memo.install()' in p.read_text(encoding='utf-8', errors='replace')]
        self.assertEqual(uses, ['tools/chim/build.py'])


class ReceiptFilesTests(unittest.TestCase):
    """import_town source receipts: the game files listed and hashed once per process, the same receipt."""

    def test_same_files_and_hashes(self):
        import import_town
        from known_inputs import input_sha256
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'
            for rel in ('Morrowind.esm', 'Morrowind.bsa', 'Meshes/a.nif', 'meshes/x/b.nif', 'Textures/t.dds', 'Sound/s.wav'):
                (data / rel).parent.mkdir(parents=True, exist_ok=True)
                (data / rel).write_bytes(rel.encode())
            expected = {p.relative_to(data).as_posix(): input_sha256(p) for p in sorted(
                [data / 'Morrowind.esm', data / 'Morrowind.bsa'] + [p for p in data.rglob('*') if p.is_file()
                 and p.relative_to(data).parts[0].casefold() in ('meshes', 'textures')])}
            with mock.patch.dict(import_town._RECEIPT_LISTING, clear=True), \
                    mock.patch.dict(import_town._RECEIPT_HASHES, clear=True):
                self.assertEqual(import_town._receipt_files(data), expected)
                self.assertEqual(list(import_town._receipt_files(data)), list(expected))
                (data / 'Meshes/a.nif').write_bytes(b'changed, longer')
                again = import_town._receipt_files(data)
                self.assertEqual(again['Meshes/a.nif'], input_sha256(data / 'Meshes/a.nif'))


class TownsBesideTests(unittest.TestCase):
    """chim.build: towns go to the workers first, beside many region frames; otherwise after them."""

    def test_threshold_and_modes(self):
        import chim.build as B
        self.assertTrue(B.towns_beside(723, 24))
        self.assertFalse(B.towns_beside(20, 24))
        self.assertFalse(B.towns_beside(723, 1))
        with mock.patch.dict(os.environ, {B.TOWN_PREP_ENV: 'after'}):
            self.assertFalse(B.towns_beside(723, 24))
        with mock.patch.dict(os.environ, {B.TOWN_PREP_ENV: 'sideways'}):
            with self.assertRaises(ValueError):
                B.towns_beside(723, 24)

    def test_towns_first_and_seyda_from_its_legacy_run(self):
        import chim.build as B
        calls = []

        def area(town, *args):
            calls.append(('area', town, args[4]))
            return {'frame': {}}, {'town': town}, {}, 1

        def seyda_area(legacy, *args):
            calls.append(('seyda', legacy, args[4]))
            return {'frame': {}}, {'town': 'seyda'}, {}, 1

        def serial(function, items, jobs=None, **kw):
            return map(function, items)
        generated = {t: {'town': {'id': t}} for t in ('rcp1_p1', 'rcp2_p1')}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(B, 'prepare_area', area), \
                mock.patch('chim.seyda.prepare_area', seyda_area), mock.patch('build_parallel.ordered_map', serial), \
                mock.patch('town_config.register_generated', lambda rows: None), \
                mock.patch('chim.validate.early_frame_failures', lambda *a: []), \
                mock.patch('chim.source_memo.install', lambda: False):
            result = B.prepare_areas_parallel(['seyda', 'balmora', 'rcp1_p1', 'rcp2_p1'], generated, None,
                                              Path(tmp), b'', None, 4, B.UnitCache(None), B.Timer(), None, (), True,
                                              set(), None, legacy_run='/run')
        self.assertEqual(list(result), ['seyda', 'balmora', 'rcp1_p1', 'rcp2_p1'])
        self.assertEqual(calls[0], ('seyda', '/run', 1))
        self.assertEqual([c[1] for c in calls[1:]], ['balmora', 'rcp1_p1', 'rcp2_p1'])
        self.assertTrue(all(c[2] == 1 for c in calls))


class FrameVisibilityTests(unittest.TestCase):
    """chim.world.frame_visibility: small frames whole on the workers give the same world files as the
    method before v0.0.42 (each frame in turn)."""

    def build(self, name, mode, jobs):
        from chim.world import build_frames
        from test_chim_frames import frame_specs
        a, b, _ = frame_specs(Path(self.tmp.name) / ('specs-' + name))
        out = Path(self.tmp.name) / name
        with mock.patch.dict(os.environ, {'AMIWIND_CHIM_VIS_ROWS': mode}),                 mock.patch('chim.world.FRAME_VIS_CHUNKS', 10 ** 6):
            receipt = build_frames(out, [a, b], {'grain': 256, 'sector_chunks': 2}, jobs=jobs)
        return tree_bytes(out), receipt

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_frames_on_workers_match_serial_byte_for_byte(self):
        serial, serial_receipt = self.build('serial', 'serial', 1)
        pooled, pooled_receipt = self.build('frames', 'frames', 2)
        self.assertEqual(sorted(pooled), sorted(serial))
        self.assertEqual(pooled, serial)
        self.assertEqual(pooled_receipt['visibility'], serial_receipt['visibility'])

    def test_layouts_on_workers_match_every_earlier_method(self):
        # BUILD-CHIM-SERIAL-SECTIONS-44: layouts and rows made together on the workers (frames, the default), the
        # v0.0.43 method (layouts in the parent while the pool works, frames-parent) and the serial method write the
        # same bytes; the parent itself never makes a layout in the default method
        import chim.world as W
        serial, serial_receipt = self.build('serial', 'serial', 1)
        parent, _ = self.build('parent', 'frames-parent', 2)

        def refuse(*args, **kwargs):
            raise AssertionError('frame_layout ran in the parent')
        with mock.patch.object(W, 'frame_layout', refuse):
            pooled, pooled_receipt = self.build('pooled', 'frames', 2)
        self.assertEqual(parent, serial)
        self.assertEqual(pooled, serial)
        self.assertEqual(pooled_receipt['visibility'], serial_receipt['visibility'])

    def test_large_frames_take_their_layout_from_the_workers(self):
        # every frame over FRAME_VIS_CHUNKS: layouts on the workers, rows in blocks over the pool; same bytes
        from chim.world import build_frames
        from test_chim_frames import frame_specs
        results = {}
        for mode, jobs in (('serial', 1), ('frames', 2)):
            a, b, _ = frame_specs(Path(self.tmp.name) / ('large-specs-' + mode))
            out = Path(self.tmp.name) / ('large-' + mode)
            with mock.patch.dict(os.environ, {'AMIWIND_CHIM_VIS_ROWS': mode}), \
                    mock.patch('chim.world.FRAME_VIS_CHUNKS', 0):
                build_frames(out, [a, b], {'grain': 256, 'sector_chunks': 2}, jobs=jobs)
            results[mode] = tree_bytes(out)
        self.assertEqual(results['frames'], results['serial'])

    def test_mixed_variant_keys_are_ordered(self):
        # dev1 proof build 2026-10-17: model numbers beside ('tile', ...) terrain tile variants
        from types import SimpleNamespace
        from chim.world import _visibility_inputs
        world = SimpleNamespace(order=[(0, 0)])
        part = {'_pid': 1, '_box': (0, 0, 0, 1, 1, 1), 'origin': (0, 0, 0), 'yaw': 0}
        owned = [dict(part, variant=3), dict(part, variant=('tile', 1, 0, 0))]
        layout = (world, {(0, 0): {'owned': owned, 'reach': []}}, None, None, None)
        spec = {'frame': 'f', 'terrain': {(0, 0): {'info': {'zmax': 1}}},
                'variants': {3: {'occluders': []}, ('tile', 1, 0, 0): {'occluders': [], 'occluder_grid': [1]}}}
        variants = _visibility_inputs(spec, layout, {})[4]
        self.assertEqual(set(variants), {3, ('tile', 1, 0, 0)})
        self.assertEqual(variants[('tile', 1, 0, 0)], {'occluders': [], 'occluder_grid': [1]})

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            self.build('bad', 'sometimes', 2)


if __name__ == '__main__':
    unittest.main()
