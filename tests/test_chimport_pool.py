"""The CHIMporter on the shared storage pool (CHIMPORT-NO-SHARED-POOL-35): units and whole cells stored once and
linked, keys that change with every input, defaults that change nothing, one writer per run folder, --region, and
--storage-pool-dir for the builder and the CHIMporter (one pool, a copy fallback across file systems)."""
import argparse
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import chimport as C  # noqa: E402
import storage_pool  # noqa: E402
from chim.units import PooledUnitCache, UnitCache, run_units  # noqa: E402

LINKS = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0
FAKE_CELL = (Path(__file__).resolve().parent / 'test_chimport.py')


class Temp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pool = self.root / 'pool'
        env = {k: v for k, v in os.environ.items() if k != storage_pool.ENV}
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        for here, directories, names in os.walk(self.root):
            for name in directories + names:
                path = Path(here) / name
                if not path.is_symlink():
                    os.chmod(path, 0o755)
        self.temp.cleanup()


class PooledUnits(Temp):
    def build(self, folder, link=True, calls=None):
        cache = PooledUnitCache(folder, self.pool, link=link)

        def worker(task):
            calls.append(task)
            return {'mesh': task, 'faces': list(range(500))}
        with contextlib.redirect_stdout(io.StringIO()):
            got = run_units('mesh', [('ab' + '1' * 62, 'rock'), ('cd' + '2' * 62, 'tree')], worker, 1, cache)
        return cache, got

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_a_unit_in_the_pool_is_linked_not_recomputed_and_byte_identical(self):
        calls = []
        first, a = self.build(self.root / 'run1' / 'units', calls=calls)
        self.assertEqual(len(calls), 2)
        self.assertEqual(first.pool_stats['stored_units'], 2)
        calls.clear()
        second, b = self.build(self.root / 'run2' / 'units', calls=calls)
        self.assertEqual(calls, [])                                  # nothing built again
        self.assertEqual(a, b)
        self.assertEqual(second.pool_stats['reused_units'], 2)
        self.assertEqual(second.stats['mesh']['reused'], 2)
        for fp in ('ab' + '1' * 62, 'cd' + '2' * 62):
            one = first._path('mesh', fp)
            two = second._path('mesh', fp)
            self.assertEqual(one.read_bytes(), two.read_bytes())    # byte-identical
            self.assertEqual(os.stat(one).st_ino, os.stat(two).st_ino)  # one inode: stored once, linked
            self.assertFalse(os.stat(two).st_mode & 0o222)          # shared files are read-only

    def test_copy_mode_reuses_by_verified_copy(self):
        calls = []
        self.build(self.root / 'run1' / 'units', link=False, calls=calls)
        calls.clear()
        second, b = self.build(self.root / 'run2' / 'units', link=False, calls=calls)
        self.assertEqual(calls, [])
        self.assertEqual(second.pool_stats['reused_units'], 2)

    def test_a_plain_unit_cache_never_touches_the_pool(self):
        cache = UnitCache(self.root / 'run1' / 'units')
        run_units('mesh', [('ef' + '3' * 62, 'x')], lambda t: t, 1, cache)
        self.assertFalse(self.pool.exists())


class CellKey(Temp):
    def setUp(self):
        super().setUp()
        self.palette = self.root / 'palette.lmp'
        self.palette.write_bytes(bytes(768))
        self.qbsp = self.root / 'qbsp'
        self.qbsp.write_bytes(b'qbsp 1')
        self.lock = self.root / 'inputs.lock'
        self.files = {str(self.root / 'data' / 'Morrowind.esm'): {'sha256': 'a' * 64, 'bytes': 1, 'mtime_ns': 1},
                      str(self.root / 'data' / 'meshes' / 'x.nif'): {'sha256': 'b' * 64, 'bytes': 1, 'mtime_ns': 1}}
        self.write_lock()
        from known_inputs import LOCK_ENV
        os.environ[LOCK_ENV] = str(self.lock)

    def write_lock(self):
        self.lock.write_text(json.dumps({'files': self.files}))

    def key(self, **kw):
        a = dict(cell=(3, -2), data_files=self.root / 'data', palette=self.palette, qbsp=self.qbsp,
                 abi_sizes={'edict': 120}, missing_land='flat')
        a.update(kw)
        return C.cell_key(**a)[0]

    def test_the_key_changes_when_any_input_changes(self):
        base = self.key()
        self.assertIsNotNone(base)
        self.assertEqual(base, self.key())                           # deterministic
        changed = {
            'cell': self.key(cell=(3, -1)),
            'missing land': self.key(missing_land='refuse'),
            'abi sizes': self.key(abi_sizes={'edict': 124}),
            'no qbsp': self.key(qbsp=None),
        }
        self.palette.write_bytes(bytes(767) + b'\1')
        changed['palette'] = self.key()
        self.palette.write_bytes(bytes(768))
        self.qbsp.write_bytes(b'qbsp 2')
        changed['qbsp binary'] = self.key()
        self.qbsp.write_bytes(b'qbsp 1')
        name = str(self.root / 'data' / 'meshes' / 'x.nif')
        self.files[name]['sha256'] = 'c' * 64
        self.write_lock()
        changed['game input content'] = self.key()
        self.files[name]['sha256'] = 'b' * 64
        self.files[str(self.root / 'data' / 'meshes' / 'y.nif')] = self.files.pop(name)
        self.write_lock()
        changed['game input name'] = self.key()
        self.files[name] = self.files.pop(str(self.root / 'data' / 'meshes' / 'y.nif'))
        self.write_lock()
        with patch.dict(os.environ, {'AMIWIND_MODEL_HULL': 'routed'}):
            changed['switch'] = self.key()
        with patch.object(C, 'code_identity', lambda: 'other code'):
            changed['code'] = self.key()
        for what, value in changed.items():
            self.assertNotEqual(value, base, what)
        self.assertEqual(self.key(), base)                           # back to the same inputs: the same key
        with patch.dict(os.environ, {storage_pool.ENV: str(self.root / 'elsewhere')}):
            self.assertEqual(self.key(), base)                       # where the pool is: not an input

    def test_no_lock_means_no_cell_key(self):
        from known_inputs import LOCK_ENV
        del os.environ[LOCK_ENV]
        key, why = C.cell_key((0, 0), self.root / 'data', self.palette)
        self.assertIsNone(key)
        self.assertIn('input lock', why)

    def test_code_identity_covers_the_converter(self):
        C._CODE.clear()
        first = C.code_identity()
        self.assertRegex(first, '^[0-9a-f]{64}$')
        self.assertEqual(first, C.code_identity())


FAKE_OUTPUT = {'chim/world.cwi': b'I' * 70000, 'chim/frames/x+03/y-02/s00.ccs': b'S' * 1000,
               'far/0_0.far': b'F' * 300, 'chim-receipt.json': b'{"r": 1}\n'}


def fake_convert(calls):
    def convert(cell, data_files, palette, out, qbsp=None, unit_cache=None, jobs=1, missing_land='flat',
                abi_sizes=None):
        calls.append(cell)
        for rel, data in FAKE_OUTPUT.items():
            (Path(out) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(out) / rel).write_bytes(data)
        (Path(out) / 'work' / 'c1').mkdir(parents=True, exist_ok=True)
        (Path(out) / 'work' / 'c1' / 'scenery.mwpak').write_bytes(b'W' * 100)
        res = {'cell': list(cell), 'converted': True, 'errors': [], 'wall_s': 5.0, 'cpu_s': 4.0, 'status': 'passed'}
        C.write_json(Path(out) / 'result.json', res)
        return res
    return convert


class CellReuse(CellKey):
    def go(self, out, calls, reuse_mode='pool'):
        with patch.object(C, 'convert_cell', fake_convert(calls)), contextlib.redirect_stdout(io.StringIO()):
            return C.convert_cell_pooled((3, -2), self.root / 'data', self.palette, out, self.qbsp,
                                         self.root / 'units', 1, 'flat', {'edict': 120}, self.pool, 'option', reuse_mode)

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_a_cell_in_the_pool_is_linked_not_converted_again(self):
        calls = []
        first = self.go(self.root / 'run1' / 'cell', calls)
        self.assertEqual(first['pool']['cell'], 'computed')
        self.assertEqual(first['pool']['stored_bytes'], sum(len(v) for v in FAKE_OUTPUT.values()))
        self.assertIsNotNone(first['pool']['manifest'])
        second = self.go(self.root / 'run2' / 'cell', calls)
        self.assertEqual(len(calls), 1)                              # converted once
        self.assertEqual(second['pool']['cell'], 'reused')
        self.assertEqual(second['converted'], True)
        self.assertEqual(second['original_wall_s'], 5.0)
        for rel, data in FAKE_OUTPUT.items():
            one, two = self.root / 'run1' / 'cell' / rel, self.root / 'run2' / 'cell' / rel
            self.assertEqual(two.read_bytes(), data)                 # byte-identical
            self.assertEqual(os.stat(one).st_ino, os.stat(two).st_ino)
        self.assertFalse((self.root / 'run2' / 'cell' / 'work').exists())   # the source stage is never shared
        third = self.go(self.root / 'run3' / 'cell', calls)          # a third run on the same pool: linked
        self.assertEqual(third['pool']['cell'], 'reused')
        # A changed input is converted again; rerunning in a folder holding read-only links works.
        self.palette.write_bytes(bytes(767) + b'\2')
        again = self.go(self.root / 'run1' / 'cell', calls)
        self.assertEqual(len(calls), 2)
        self.assertEqual(again['pool']['cell'], 'computed')
        self.assertEqual(again['pool']['stored_bytes'], 0)           # same bytes: linked to the pooled objects
        self.assertEqual(again['pool']['linked_bytes'], sum(len(v) for v in FAKE_OUTPUT.values()))

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_the_collector_keeps_objects_a_cell_manifest_names(self):
        import build_gc
        calls = []
        self.go(self.root / 'run1' / 'cell', calls)
        import shutil
        for here, directories, names in os.walk(self.root / 'run1'):
            for name in directories + names:
                os.chmod(Path(here) / name, 0o755)
        shutil.rmtree(self.root / 'run1')                            # the run is gone: only the pool holds them
        result = build_gc.plan([], workspaces=[self.root / 'nows'], extra_pools=[self.pool])
        expired = [row for row in result['items'] if row['kind'] == 'pool-object' and row['decision'] == 'expire']
        self.assertEqual(expired, [])

    def test_pool_off_is_exactly_convert_cell(self):
        seen = []

        def convert(*a):
            seen.append(a)
            return {'cell': [0, 0]}
        out = self.root / 'cell'
        with patch.object(C, 'convert_cell', convert):
            res = C.convert_cell_pooled((0, 0), 'D', 'P', out, 'Q', 'U', 2, 'flat', {'s': 1})
        self.assertEqual(seen, [((0, 0), 'D', 'P', out, 'Q', 'U', 2, 'flat', {'s': 1})])
        self.assertNotIn('pool', res)


class Defaults(Temp):
    def parse(self, *extra):
        argv = ['run', '--data-files', 'D', '--palette', 'P', '--out', str(self.root / 'run')] + list(extra)
        seen = {}
        with patch.object(C, 'run', lambda a: seen.setdefault('a', a) and 0):
            C.main(argv)
        return seen['a']

    def test_default_flags_change_nothing(self):
        a = self.parse()
        self.assertEqual((a.storage_pool, a.reuse_mode, a.storage_pool_dir, a.region), ('off', 'copy', None, None))
        os.environ[storage_pool.ENV] = str(self.pool)               # even with the variable set: off stays off
        self.assertEqual(C.pool_choice(a), (None, 'environment'))
        a.pool_dir = None
        row = {'x': -6, 'y': 25}
        legacy = [sys.executable, str(Path(C.__file__).resolve()), 'cell', '--data-files', 'D', '--palette', 'P',
                  '--cell=-6,25', '--out', str(a.out / 'cells' / C.cell_dir((-6, 25))), '--unit-cache',
                  str(a.out / 'units'), '--jobs', '2']
        self.assertEqual(C.cell_command(a, row), legacy)

    def test_pool_options_reach_the_cell_process(self):
        a = self.parse('--storage-pool', 'on', '--storage-pool-dir', str(self.pool), '--reuse-mode', 'pool')
        a.pool_dir, origin = C.pool_choice(a)
        self.assertEqual((a.pool_dir, origin), (self.pool.absolute(), 'option'))
        cmd = C.cell_command(a, {'x': 1, 'y': 2})
        self.assertEqual(cmd[cmd.index('--storage-pool-dir') + 1], str(self.pool.absolute()))
        self.assertEqual(cmd[cmd.index('--reuse-mode') + 1], 'pool')

    def test_auto_follows_a_named_pool_and_link_modes_need_the_pool(self):
        a = self.parse('--storage-pool', 'auto')
        self.assertEqual(C.pool_choice(a)[0], None)
        os.environ[storage_pool.ENV] = str(self.pool)
        self.assertEqual(C.pool_choice(a)[0], self.pool.absolute())
        b = self.parse('--reuse-mode', 'pool')
        with self.assertRaises(ValueError):
            C.pool_choice(b)
        del os.environ[storage_pool.ENV]
        with self.assertRaises(ValueError):
            C.pool_choice(self.parse('--storage-pool', 'on'))
        w = self.parse('--storage-pool', 'on', '--workspace', str(self.root / 'ws'))
        self.assertEqual(C.pool_choice(w)[0], self.root / 'ws' / 'cache' / 'asset-pool-v1')


class LockAndRegion(Temp):
    def setUp(self):
        super().setUp()
        self.run_dir = self.root / 'run'
        self.run_dir.mkdir()
        rows = []
        for i, (x, y, region) in enumerate([(0, 0, 'Bitter Coast Region'), (1, 0, 'Bitter Coast Region'),
                                            (2, 0, 'West Gash Region'), (3, 0, "Azura's Coast Region")], 1):
            rows.append(dict(x=x, y=y, ring=1, order=i, land=True, refs=1, name='', region=region,
                             categories={'statics': 1}))
        self.plan = {'format': C.PLAN_FORMAT, 'cells': rows}
        C.write_json(self.run_dir / 'plan.json', self.plan)

    def args(self, **kw):
        a = dict(out=self.run_dir, data_files=Path('/none'), palette=Path('/none'), qbsp=None, sdk=None, workers=2,
                 jobs=1, rings=None, cells=None, retry_failed=False, timeout=60, dry_run=False, no_world=True,
                 world_timeout=60, world_every=1, tracker=None, tracker_tool=None, tracker_ingest='', feed_every=0)
        a.update(kw)
        return SimpleNamespace(**a)

    def go(self, **kw):
        fake = self.root / 'fake_cell.py'
        src = FAKE_CELL.read_text(encoding='utf-8')
        fake.write_text(src.split("FAKE_CELL = r'''", 1)[1].split("'''", 1)[0])

        def command(args, row):
            return [sys.executable, str(fake), '--cell', '%d,%d' % (row['x'], row['y']),
                    '--out', str(args.out / 'cells' / C.cell_dir((row['x'], row['y'])))]
        with patch.object(C, 'cell_command', command), patch.object(C, 'inputs_lock', lambda *a: None), \
                contextlib.redirect_stdout(io.StringIO()):
            return C.run(self.args(**kw))

    def test_a_second_writer_is_refused(self):
        with C.RunLock(self.run_dir):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(self.go(), 3)
            self.assertIn('another run is already writing', err.getvalue())
            self.assertFalse((self.run_dir / 'state.json').exists())
        self.assertEqual(self.go(), 0)                               # released: the next run goes ahead
        self.assertEqual(len(C.read_json(self.run_dir / 'state.json')['cells']), 4)

    def test_region_selects_the_cells_of_that_region(self):
        rows = C.select(self.plan, regions=['bitter coast'])
        self.assertEqual([(r['x'], r['y']) for r in rows], [(0, 0), (1, 0)])
        rows = C.select(self.plan, regions=["Azura's Coast Region", 'West Gash'])
        self.assertEqual([(r['x'], r['y']) for r in rows], [(2, 0), (3, 0)])
        with self.assertRaises(ValueError) as caught:
            C.select(self.plan, regions=['Solstheim'])
        self.assertIn('Bitter Coast Region', str(caught.exception))
        self.go(region=['Bitter Coast'])
        self.assertEqual(set(C.read_json(self.run_dir / 'state.json')['cells']), {'0,0', '1,0'})


class PoolDir(Temp):
    def test_order_option_config_environment_default(self):
        ws = self.root / 'ws'
        self.assertEqual(storage_pool.resolve_dir(ws), (ws / 'cache' / 'asset-pool-v1', 'workspace default'))
        os.environ[storage_pool.ENV] = str(self.root / 'env')
        self.assertEqual(storage_pool.resolve_dir(ws), ((self.root / 'env').absolute(), 'environment'))
        self.assertEqual(storage_pool.resolve_dir(ws, config='p', config_base=self.root),
                         ((self.root / 'p').absolute(), 'build config'))
        self.assertEqual(storage_pool.resolve_dir(ws, cli=self.root / 'cli', config='p', config_base=self.root),
                         ((self.root / 'cli').absolute(), 'option'))

    def builder_args(self, **kw):
        a = argparse.Namespace(workspace=self.root / 'ws', storage_pool='on', dry_run=False, build_config=None,
                               storage_pool_dir=None)
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def test_builder_default_is_unchanged_and_the_custom_dir_is_used(self):
        import build
        self.assertEqual(build.storage_pool_dir(self.builder_args()), self.root / 'ws' / 'cache' / 'asset-pool-v1')
        self.assertIsNone(build.parser().parse_args([]).storage_pool_dir)
        self.assertEqual(build.storage_pool_dir(self.builder_args(storage_pool_dir=self.pool)), self.pool.absolute())
        config = self.root / 'build.json'
        config.write_text(json.dumps({'storage_pool_dir': 'shared-pool'}))
        self.assertEqual(build.storage_pool_dir(self.builder_args(build_config=config)),
                         (self.root / 'shared-pool').absolute())
        self.assertIn('--storage-pool-dir', build.parser().format_help())

    def test_a_custom_dir_keeps_the_stage_keys(self):
        import build_cache
        run = self.root / 'ws' / 'build' / 'r1'
        default = build_cache.normalize_command(['x.py', '--cache', str(self.root / 'ws/cache/asset-pool-v1')], run, {})
        custom = build_cache.normalize_command(['x.py', '--cache', str(self.pool)], run,
                                               {'storage_pool_dir': str(self.pool)})
        self.assertEqual(default, custom)

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_a_pool_on_another_file_system_falls_back_to_copies_with_one_warning(self):
        import build
        real = os.link

        def cross(src, dst, *a, **k):
            if '.pool-link-probe.' in str(dst):
                raise OSError(errno.EXDEV, 'Invalid cross-device link')
            return real(src, dst, *a, **k)
        run = self.root / 'ws' / 'build' / 'r1'
        (run / 'chim').mkdir(parents=True)
        world = run / 'chim' / 'world.pak'
        world.write_bytes(b'w' * 100000)
        out = io.StringIO()
        with patch.object(os, 'link', cross), contextlib.redirect_stdout(out):
            summary = build.pool_outputs(self.builder_args(storage_pool_dir=self.pool), run)
        self.assertFalse(summary['pool']['links'])
        self.assertIn('another file system', summary['pool']['warning'])
        self.assertEqual(out.getvalue().count('STORAGE POOL WITHOUT HARD LINKS'), 1)
        self.assertEqual(os.stat(world).st_nlink, 1)                 # nothing pooled: no extra copy
        self.assertTrue((run / 'profile' / 'storage-pool.json').is_file())
        record = storage_pool.setting(self.pool, 'option', run, log=lambda line: None)
        self.assertTrue(record['links'])                            # without the fault the same folders link


if __name__ == '__main__':
    unittest.main()
