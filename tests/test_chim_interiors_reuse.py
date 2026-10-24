"""CHIM-INTERIORS-REUSE-MISS-48: the CHIM rooms stage names the shared CHIM unit cache.

chim-interiors (tools/chim_interiors.py -> tools/chim/interior.py) passes --unit-cache WORKSPACE/cache/chim-units,
the folder the chim stage fills. Only ('chim', '--unit-cache') was listed as content-addressed, so the rooms stage
hashed the shared folder; past EXTERNAL_DIRECTORY_LIMIT that is a fingerprint problem and the stage was never
reused (a 2026-10-22 rebuild that changed only tools/sky_palette_overlay.py rebuilt it as "(other)"). The folder now
counts by place for every stage that names it.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import build_cache  # noqa: E402

LIMIT = 64  # bytes: stands in for the 512 MiB guard
UNIT_CACHE = 'cache/chim-units'


def fill(folder, count, size=40):
    for index in range(count):
        target = folder / 'mesh' / f'{index:02x}' / f'{index:02x}{"b" * 62}.pickle'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes([index % 256]) * size)


class ChimUnitCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / 'workspace'
        self.run = self.workspace / 'build' / 'run'
        self.run.mkdir(parents=True)
        self.units = self.workspace / UNIT_CACHE
        self.units.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def command(self, script='chim_interiors.py', option='--unit-cache'):
        return [sys.executable, str(ROOT / 'tools' / script), '--rooms-from', str(self.run / 'intro-scene/area-work'),
                '--out', str(self.run / 'chim-interiors'), option, str(self.units)]

    def test_the_rooms_stage_is_reusable_with_a_unit_cache_past_the_folder_limit(self):
        fill(self.units, 4)
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            first, problems = build_cache.external_inputs('chim-interiors', self.command(), self.run, {})
            self.assertEqual(problems, [])
            fill(self.units, 12)  # units other builds added: the same key
            second, problems = build_cache.external_inputs('chim-interiors', self.command(), self.run, {})
        self.assertEqual(problems, [])
        self.assertEqual(first, second)
        self.assertEqual(first, {'--unit-cache={WORKSPACE}/cache/chim-units': 'not hashed (content-addressed cache)'})

    def test_the_chim_stage_key_is_unchanged(self):
        """The chim stage had the rule by name: the same value now, so its fingerprint stays as it was."""
        fill(self.units, 4)
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            found, problems = build_cache.external_inputs('chim', self.command('chim_build.py'), self.run, {})
        self.assertEqual(problems, [])
        self.assertEqual(list(found.values()), ['not hashed (content-addressed cache)'])

    def test_every_planned_stage_that_names_the_unit_cache_gets_the_rule(self):
        """Every stage of the default CHIM build plan that is given the unit cache: never a hashed folder."""
        from test_build_builder import plan
        named = []
        for name, command in plan(['--jobs', '4', '--builder', 'chim']):
            command = [str(part) for part in command]
            for at, part in enumerate(command[:-1]):
                if command[at + 1] == str(Path('/private/ws') / UNIT_CACHE):
                    named.append((name, part, Path(command[1]).name))
        self.assertIn('chim-interiors', [name for name, _, _ in named])
        self.assertIn('chim', [name for name, _, _ in named])
        fill(self.units, 4)
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            for name, option, script in named:
                found, problems = build_cache.external_inputs(name, self.command(script, option), self.run, {})
                self.assertEqual(problems, [], name)
                self.assertEqual(found, {option + '={WORKSPACE}/cache/chim-units':
                                         'not hashed (content-addressed cache)'}, name)

    def test_a_real_input_folder_keeps_the_size_guard(self):
        other = self.workspace / 'cache' / 'something-else'
        other.mkdir(parents=True)
        fill(other, 4)
        command = self.command()[:-1] + [str(self.units), '--rooms', str(other)]
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            _, problems = build_cache.external_inputs('chim-interiors', command, self.run, {})
        self.assertEqual(len(problems), 1)
        self.assertIn('--rooms={WORKSPACE}/cache/something-else: folder larger than', problems[0])


if __name__ == '__main__':
    unittest.main()
