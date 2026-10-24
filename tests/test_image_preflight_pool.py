# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-UNDERUSED-32: the image step's payload preflight and room batch install on every core, the same
results as the methods before (kept behind their flags): the engine map limits on the worker pool
(AMIWIND_MAP_LIMITS_POOL=off), the source manifest's frame list parsed by workers (parallel_json.load_list;
AMIWIND_JSON_POOL=ordered), the layout walk by os.walk (AMIWIND_LAYOUT_WALK=pathlib), the room batch files hashed and
copied on threads (AMIWIND_ROOM_INSTALL_THREADS=1), the Python-bound checks in processes and the disk layout beside
them (AMIWIND_PREFLIGHT_METHOD=threads)."""
import hashlib
import json
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

import layout_plan  # noqa: E402
import map_engine_limits as mel  # noqa: E402
import parallel_json  # noqa: E402
import payload_preflight  # noqa: E402
import room_batches  # noqa: E402
from test_map_engine_limits import bsp, world  # noqa: E402


class EngineLimitsPoolTests(unittest.TestCase):
    def test_pooled_audit_equals_the_serial_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            maps = Path(temp) / 'id1/maps'
            maps.mkdir(parents=True)
            room = mel.limits()['entity_room']
            for k in range(40):
                rows = [{'classname': 'light'}] * k + [{'classname': 'func_wall', 'model': '*1'}] * (k % 7)
                (maps / ('vf%04d.bsp' % k)).write_bytes(bsp(world(*rows), 2))
            (maps / 'vf0100.bsp').write_bytes(bsp(world(*[{'classname': 'func_wall'}] * (room + 1))))
            (maps / 'stub.bsp').write_bytes(b'\0bsp stub')
            (Path(temp) / 'id1/harvest-vf0003.txt').write_text('AWH1 0 0 3\n')
            with mock.patch.dict(os.environ, {'AMIWIND_MAP_LIMITS_POOL': 'off'}):
                before = mel.audit_maps(maps, skip={'vf0007.bsp'}, jobs=3)
            now = mel.audit_maps(maps, skip={'vf0007.bsp'}, jobs=3)
            self.assertEqual(json.dumps(now), json.dumps(before))
            self.assertEqual(list(now['per_map']), list(before['per_map']))
            self.assertTrue(now['refused'])
            self.assertEqual(list(now['unreadable']), ['stub'])
            with self.assertRaisesRegex(ValueError, 'vf0100.*MAX_EDICTS'):
                mel.check_maps(maps, jobs=3)


class LoadListTests(unittest.TestCase):
    def test_frames_read_by_workers_equal_the_whole_parse(self):
        doc = {'areas': ['a', 'b'], 'builder': 'chim',
               'frames': [{'cell': [k, -k], 'sprite_entities': [{'n': 'x\n{y', 'k': k}] * (k % 3),
                           'sprite_assets': [{'path': 'p%d' % k, 'bytes': k}], 'big': list(range(k)),
                           'nested': {'frames': [[k, {'a': [1, 2]}]]}} for k in range(97)],
               'world_format': '0.12', 'z': [{'frames': 1}]}
        keep = ('cell', 'sprite_entities', 'sprite_assets')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'chim-source.json'
            path.write_text(parallel_json.dumps(doc, [('frames',)], jobs=2) + '\n', encoding='utf-8')
            want = [{k: f[k] for k in keep if k in f} for f in doc['frames']]
            self.assertEqual(parallel_json.load_list(path, 'frames', keep, jobs=3), want)
            self.assertEqual(parallel_json.load_list(path, 'frames', None, jobs=3), doc['frames'])
            with mock.patch.dict(os.environ, {'AMIWIND_JSON_POOL': 'ordered'}):
                self.assertEqual(parallel_json.load_list(path, 'frames', keep, jobs=3), want)
            self.assertEqual(parallel_json.load_list(path, 'frames', keep, jobs=1), want)
            # another layout (no indent), an empty list, a missing key: parsed whole, as before
            path.write_text(json.dumps(doc), encoding='utf-8')
            self.assertEqual(parallel_json.load_list(path, 'frames', keep, jobs=3), want)
            path.write_text(json.dumps(dict(doc, frames=[]), indent=1, sort_keys=True), encoding='utf-8')
            self.assertEqual(parallel_json.load_list(path, 'frames', keep, jobs=3), [])
            with self.assertRaises(KeyError):
                parallel_json.load_list(path, 'missing', keep, jobs=3)


class LayoutWalkTests(unittest.TestCase):
    def test_os_walk_equals_the_pathlib_walk(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in ('a/b0', 'a-b/x', 'a/b-c', 'a.b', 'A/z', 'a/b/c/d.bin', 'z', 'a-b/y/q', 'm/n/o/p'):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'x' * len(rel))
            (root / 'empty-dir').mkdir()
            with mock.patch.dict(os.environ, {'AMIWIND_LAYOUT_WALK': 'pathlib'}):
                before = layout_plan.walk(root, 'id1/chim/')
            self.assertEqual(layout_plan.walk(root, 'id1/chim/'), before)
            self.assertEqual(len(before), 9)


class RoomInstallTests(unittest.TestCase):
    def stage(self, root, files):
        stage = root / 'stage'
        for rel, data in files.items():
            (stage / 'id1' / rel).parent.mkdir(parents=True, exist_ok=True)
            (stage / 'id1' / rel).write_bytes(data)
        record = {'format': room_batches.STAGE_FORMAT, 'selection': '1-2',
                  'files': {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()},
                  'rooms': [{'room': 'Room A', 'map': 'ra'}]}
        (stage / room_batches.RECORD).write_text(json.dumps(record), encoding='utf-8')
        return stage

    def test_threads_install_the_same_files_and_refuse_the_same_conflicts(self):
        files = {'maps/r%03d.bsp' % k: os.urandom(100 + k) for k in range(150)}
        files.update({'residents/n%d.mdl' % k: b'm' * k for k in range(1, 30)})
        results = {}
        for threads in ('1', '6'):
            with tempfile.TemporaryDirectory() as temp, \
                    mock.patch.dict(os.environ, {'AMIWIND_ROOM_INSTALL_THREADS': threads}):
                root = Path(temp)
                stage = self.stage(root, files)
                id1 = root / 'id1'
                (id1 / 'maps').mkdir(parents=True)
                (id1 / 'maps/r001.bsp').write_bytes(files['maps/r001.bsp'])        # the same bytes: allowed
                out = room_batches.install(stage, id1, jobs=6)
                got = {p.relative_to(id1).as_posix(): p.read_bytes() for p in id1.rglob('*') if p.is_file()}
                # conflicts: one file changed in the stage, one staged in the image with other bytes
                (stage / 'id1/maps/r005.bsp').write_bytes(b'changed')
                (id1 / 'maps/r009.bsp').write_bytes(b'other')
                with self.assertRaises(ValueError) as refused:
                    room_batches.install(stage, id1, jobs=6)
                results[threads] = (out['files'], out['rooms'], got, str(refused.exception))
        self.assertEqual(results['6'], results['1'])
        self.assertEqual(results['6'][2], files)
        self.assertIn('maps/r005.bsp: changed since the stage wrote it', results['6'][3])
        self.assertIn('maps/r009.bsp: staged in the image with other bytes', results['6'][3])


class PreflightMethodTests(unittest.TestCase):
    def test_process_checks_are_the_python_bound_ones(self):
        self.assertEqual(set(payload_preflight.PROCESS_CHECKS),
                         {'payload-names', 'file-formats', 'host-paths', 'actor-frames'})
        with mock.patch.dict(os.environ, {'AMIWIND_PREFLIGHT_METHOD': 'threads'}):
            self.assertEqual(payload_preflight.layout_beside(), 0)
        self.assertEqual(payload_preflight.layout_beside(), 1)

    def test_flags_are_scheduling_only(self):
        import build_cache
        for name in ('AMIWIND_MAP_LIMITS_POOL', 'AMIWIND_LAYOUT_WALK', 'AMIWIND_ROOM_INSTALL_THREADS',
                     'AMIWIND_PREFLIGHT_METHOD', 'AMIWIND_JSON_POOL'):
            self.assertIn(name, build_cache.IGNORED_ENV)


if __name__ == '__main__':
    unittest.main()
