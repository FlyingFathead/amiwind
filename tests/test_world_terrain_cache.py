"""Per-map world terrain cache: verified hits, misses on any input change, release builds without it."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import prepare_world_regions as regions  # noqa: E402

BSP = b'BSP29 fake map ' * 64


class FakeTools:
    """qbsp writes terrain.bsp; vis and light do nothing. Counts calls."""

    def __init__(self):
        self.calls = 0

    def run(self, command, cwd, **_):
        self.calls += 1
        if Path(command[0]).name == 'qbsp':
            (Path(cwd) / 'terrain.bsp').write_bytes(BSP)


class UnitCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.cache = self.base / 'cache'
        self.tools = FakeTools()
        patches = [patch.object(regions, 'map_text', lambda entry, terrain: 'map ' + entry['shape']),
                   patch.object(regions.subprocess, 'run', self.tools.run),
                   patch.object(regions, 'rebuild_world_hull', lambda *a, **k: None),
                   patch.object(regions, 'deduplicate', lambda raw: (raw, {'shared': 0})),
                   patch.object(regions, 'lumps', lambda raw: [bytearray(40)] * 15),
                   patch.object(regions, '_terrain', object())]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        self.temp.cleanup()

    def convert(self, run, name='vf001', shape='a', identity='code-1'):
        out = self.base / run
        out.mkdir(exist_ok=True)
        (out / 'terrain.wad').write_bytes(b'wad')
        entry = {'name': name, 'shape': shape, 'origin': [0, 0, 0]}
        return regions.compile_region((self.base, out, entry, self.base / 'bin', 1, 'fast', str(self.cache), identity)), out

    def test_hit_is_verified_and_identical(self):
        first, out = self.convert('one')
        self.assertEqual(first.pop('_unit_cache'), 'miss')
        self.assertEqual(self.tools.calls, 3)
        second, again = self.convert('two')
        self.assertEqual(second.pop('_unit_cache'), 'hit')
        self.assertEqual(self.tools.calls, 3)                     # no map tool ran
        self.assertEqual(first, second)
        self.assertEqual((out / 'vf001' / 'scene.bsp').read_bytes(), (again / 'vf001' / 'scene.bsp').read_bytes())
        self.assertEqual(json.loads((again / 'vf001' / 'conversion.json').read_text()), second)
        # Same map text under another name: the cached map, this entry's name.
        third, _ = self.convert('three', name='vf002')
        self.assertEqual((third.pop('_unit_cache'), third['name']), ('hit', 'vf002'))

    def test_any_input_change_misses(self):
        self.convert('one')
        for run, options in (('shape', {'shape': 'b'}), ('code', {'identity': 'code-2'})):
            result, _ = self.convert(run, **options)
            self.assertEqual(result['_unit_cache'], 'miss', run)
        out = self.base / 'wad'
        out.mkdir()
        (out / 'terrain.wad').write_bytes(b'another wad')
        entry = {'name': 'vf001', 'shape': 'a', 'origin': [0, 0, 0]}
        result = regions.compile_region((self.base, out, entry, self.base / 'bin', 1, 'fast', str(self.cache), 'code-1'))
        self.assertEqual(result['_unit_cache'], 'miss')

    def test_damaged_entry_is_rebuilt(self):
        self.convert('one')
        (cached,) = list(self.cache.glob('*/*/scene.bsp'))
        cached.write_bytes(b'damaged')
        calls = self.tools.calls
        result, out = self.convert('two')
        self.assertEqual(result['_unit_cache'], 'miss')
        self.assertGreater(self.tools.calls, calls)
        self.assertEqual((out / 'vf001' / 'scene.bsp').read_bytes(), BSP)

    def test_identity_follows_code_and_tools(self):
        bindir = self.base / 'bin'
        bindir.mkdir()
        for name in ('qbsp', 'vis', 'light'):
            (bindir / name).write_bytes(name.encode())
        first = regions.unit_cache_identity(bindir)
        self.assertEqual(first, regions.unit_cache_identity(bindir))
        (bindir / 'light').write_bytes(b'light 2')
        self.assertNotEqual(first, regions.unit_cache_identity(bindir))


class BuilderTests(unittest.TestCase):
    def test_only_development_builds_use_the_cache(self):
        args = build.parser().parse_args(['--workspace', '/w'])
        with patch.object(build, 'VERSION', '0.0.33-dev2'):
            self.assertEqual(build.world_terrain_cache(args), ['--cache', Path('/w/cache/world-terrain-v1')])
            args.no_unit_cache = True
            self.assertEqual(build.world_terrain_cache(args), [])
            args.no_unit_cache = False
        for version in ('0.0.33', '0.0.33-rc1'):
            with patch.object(build, 'VERSION', version):
                self.assertEqual(build.world_terrain_cache(args), [], version)
                args.allow_release_reuse = True
                self.assertEqual(len(build.world_terrain_cache(args)), 2, version)
                args.allow_release_reuse = False


if __name__ == '__main__':
    unittest.main()
