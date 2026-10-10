"""BUILD-POOL-ARG-UNFINGERPRINTED-35: a stage that names the shared storage pool on its command line.

The pool is content-addressed: balmora (and area, balmora-interiors, town-*) read resident NPC bakes from it by
reuse keys made of the inputs their own fingerprint already covers. Hashing the folder made the fingerprint change
with every pooled object, and past 512 MiB balmora was never reusable. The pool now counts as its token; real input
folders keep the size guard; the read trace proves every pool read was a keyed lookup.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cache  # noqa: E402
import build_profile  # noqa: E402
import npc_lod  # noqa: E402
from test_build_cache import make_repository, metadata  # noqa: E402

POSIX = os.name == 'posix'
LIMIT = 64  # bytes: stands in for the 512 MiB guard, so the tests write no large folder


def fill(folder, count, size=40):
    """COUNT pooled objects (and their keys) of SIZE bytes in the pool layout of tools/file_cache.py."""
    for index in range(count):
        digest = f'{index:02x}' + 'a' * 62
        target = folder / 'objects' / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes([index % 256]) * size)
        key = folder / 'keys' / npc_lod.POOL_NAMESPACE / digest[:2] / f'{digest}.json'
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text('{}')


class PoolArgumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'workspace'
        self.run = self.workspace / 'build' / 'run'
        self.run.mkdir(parents=True)
        self.pool = self.workspace / 'cache' / 'asset-pool-v1'
        self.pool.mkdir(parents=True)
        self.data = self.root / 'data'
        self.data.mkdir()
        self.meta = {'data_files': str(self.data)}

    def tearDown(self):
        self.temp.cleanup()

    def command(self, pool=None, stage_script='prepare_balmora.py'):
        return [sys.executable, str(ROOT / 'tools' / stage_script), '--data-files', str(self.data),
                '--scene', str(self.run / 'intro-scene'), '--out', str(self.run / 'balmora'),
                '--npc-model-pool', str(pool or self.pool)]

    def test_balmora_is_reusable_with_a_pool_larger_than_the_folder_limit(self):
        fill(self.pool, 4)
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            first, problems = build_cache.external_inputs('balmora', self.command(), self.run, self.meta)
            self.assertEqual(problems, [])
            self.assertEqual(first, {'--npc-model-pool={WORKSPACE}/cache/asset-pool-v1': build_cache.POOL_CONTENT})
            fill(self.pool, 9)  # more objects pooled by other builds: same fingerprint
            second, problems = build_cache.external_inputs('balmora', self.command(), self.run, self.meta)
        self.assertEqual(problems, [])
        self.assertEqual(first, second)

    def test_every_stage_and_a_pool_named_elsewhere_get_the_same_rule(self):
        elsewhere = self.root / 'shared-pool'
        fill(elsewhere, 4)
        meta = dict(self.meta, storage_pool_dir=str(elsewhere))
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            for stage in ('balmora', 'area', 'balmora-interiors', 'town-vivec_arena'):
                found, problems = build_cache.external_inputs(stage, self.command(elsewhere), self.run, meta)
                self.assertEqual(problems, [], stage)
                self.assertEqual(found, {'--npc-model-pool={WORKSPACE}/cache/asset-pool-v1': build_cache.POOL_CONTENT})
            # A folder inside the pool counts as the pool too.
            found, problems = build_cache.external_inputs('media', [sys.executable, 'x.py', '--other',
                                                                    str(elsewhere / 'objects')], self.run, meta)
        self.assertEqual(problems, [])
        self.assertEqual(list(found.values()), [build_cache.POOL_CONTENT])

    def test_the_media_and_intro_keys_are_unchanged(self):
        for stage in ('media', 'intro'):
            found, _ = build_cache.external_inputs(stage, [sys.executable, 'x.py', '--cache', str(self.pool)], self.run, {})
            self.assertEqual(list(found.values()), ['not hashed (content-addressed cache)'])

    def test_the_folder_guard_still_applies_to_real_input_folders(self):
        recorded = self.root / 'seyda-recorded'
        recorded.mkdir()
        for index in range(4):
            (recorded / f'map{index}.bsp').write_bytes(b'x' * 40)
        command = self.command() + ['--seyda-recorded', str(recorded)]
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            found, problems = build_cache.external_inputs('balmora', command, self.run, self.meta)
        self.assertEqual(len(problems), 1)
        self.assertIn('--seyda-recorded={EXTERNAL}: folder larger than', problems[0])
        self.assertEqual(found['--npc-model-pool={WORKSPACE}/cache/asset-pool-v1'], build_cache.POOL_CONTENT)
        # Under the limit it is hashed by content: a changed file changes the fingerprint.
        small = self.root / 'small'
        small.mkdir()
        (small / 'a.bin').write_bytes(b'one')
        before, _ = build_cache.external_inputs('balmora', self.command() + ['--seyda-recorded', str(small)], self.run, self.meta)
        (small / 'a.bin').write_bytes(b'two')
        after, _ = build_cache.external_inputs('balmora', self.command() + ['--seyda-recorded', str(small)], self.run, self.meta)
        self.assertNotEqual(before, after)

    def test_a_changed_npc_model_still_rebuilds_balmora(self):
        """The models balmora bakes come from the game data (Morrowind.bsa meshes and textures): their hashes
        are in its fingerprint, the pool's growth is not."""
        repository = self.root / 'repo'
        make_repository(repository)
        index = build_cache.SourceIndex(repository)
        steps = [('balmora', [sys.executable, str(repository / 'tools' / 'stage_a.py'), '--data-files', str(self.data),
                              '--npc-model-pool', str(self.pool), '--out', str(self.run / 'balmora')])]
        base = metadata({'Morrowind.esm': 'aa', 'Morrowind.bsa': 'bb'})
        with patch.object(build_cache, 'EXTERNAL_DIRECTORY_LIMIT', LIMIT):
            fill(self.pool, 4)
            first, _, problems, _ = build_cache.fingerprint_steps(steps, self.run, base, index, {'balmora': ()})
            self.assertEqual(problems, {'balmora': []})
            fill(self.pool, 12)
            grown, _, problems, _ = build_cache.fingerprint_steps(steps, self.run, base, index, {'balmora': ()})
            self.assertEqual(problems, {'balmora': []})
            changed, _, _, _ = build_cache.fingerprint_steps(
                steps, self.run, metadata({'Morrowind.esm': 'aa', 'Morrowind.bsa': 'cc'}), index, {'balmora': ()})
        self.assertEqual(first, grown)
        self.assertNotEqual(first, changed)


def repository_imports(path):
    """Repository modules (tools/X.py, src/PKG/X.py) a file imports, at any level."""
    found = set()
    for node in ast.walk(ast.parse(Path(path).read_text(encoding='utf-8'))):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module]
        for name in names:
            relative = name.replace('.', '/') + '.py'
            if (ROOT / 'tools' / relative).is_file() or (ROOT / 'src' / relative).is_file():
                found.add(name)
    return found


class PoolKeyCoverageTests(unittest.TestCase):
    """The resident bake's pool key covers the code it runs: a stage that reruns never takes an older bake."""

    def test_the_bake_modules_cover_what_the_bake_imports(self):
        self.assertLessEqual(repository_imports(ROOT / 'tools' / 'npc_geometry.py'), set(npc_lod.BAKE_MODULES))
        scenery = repository_imports(ROOT / 'tools' / 'prepare_scenery.py')
        self.assertLessEqual({'mwad.audit', 'mwad.esm', 'nif_common'}, scenery)
        self.assertLessEqual({'mwad.audit', 'mwad.esm', 'nif_common'}, set(npc_lod.BAKE_MODULES))

    def test_an_edit_to_a_bake_module_changes_the_key(self):
        import inspect
        npc_lod._CODE_IDENTITY.clear()
        first = npc_lod.code_identity()
        original = inspect.getsource

        def edited(item):
            text = original(item)
            return text + '\n# edited\n' if getattr(item, '__name__', '') == 'nif_common' else text
        npc_lod._CODE_IDENTITY.clear()
        try:
            with patch.object(inspect, 'getsource', edited):
                second = npc_lod.code_identity()
        finally:
            npc_lod._CODE_IDENTITY.clear()
        self.assertNotEqual(first, second)
        self.assertEqual(first, npc_lod.code_identity())


class PoolReadTraceTests(unittest.TestCase):
    def test_keyed_lookups_and_objects_are_covered(self):
        lines = ['%keys/npc-resident-v2/ab/abcd.json', '%objects/ab/abcdef', '%keys/chim-unit/mesh/0f/0f12.json',
                 'tools/npc_lod.py']
        problems, summary = build_cache.pool_read_problems(lines)
        self.assertEqual(problems, [])
        self.assertEqual(summary, {'objects': 1, 'keys': {'chim-unit/mesh': 1, 'npc-resident-v2': 1}})

    def test_other_pool_reads_are_uncovered(self):
        problems, _ = build_cache.pool_read_problems(['%index.json', '%objects/ab/cd', '%keys/x.json'])
        self.assertEqual(problems, ['index.json', 'keys/x.json', 'objects/ab/cd'])

    def test_an_uncovered_pool_read_makes_the_stage_not_reusable(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = build_cache.Recorder.__new__(build_cache.Recorder)
            recorder.run = Path(temp)
            recorder.traced = True
            recorder.closures = {'root': str(ROOT), 'stages': {'balmora': []}, 'files': []}
            recorder.cache = {}
            trace = Path(temp) / 'reads.txt'
            trace.write_text('%keys/npc-resident-v2/ab/ab12.json\n%objects/ab/ab34\n')
            reasons, summary = recorder.check_trace('balmora', trace)
            self.assertEqual(reasons, [])
            self.assertEqual(summary['pool_reads'], {'objects': 1, 'keys': {'npc-resident-v2': 1}})
            trace.write_text('%keys/npc-resident-v2/ab/ab12.json\n%manifest.json\n')
            reasons, _ = recorder.check_trace('balmora', trace)
        self.assertEqual(len(reasons), 1)
        self.assertIn('storage pool files outside its keyed lookups', reasons[0])

    @unittest.skipUnless(POSIX, 'the read trace runs with the stage wrapper on POSIX')
    def test_the_trace_hook_lists_pool_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'workspace' / 'build' / 'run'
            (run / 'profile').mkdir(parents=True)
            pool = Path(temp) / 'workspace' / 'cache' / 'asset-pool-v1'
            fill(pool, 1)
            (pool / 'stray.txt').write_text('x')
            roots = [str(path) for path in build_cache.storage_pool_roots(run, {})]
            self.assertTrue(build_cache.write_trace_hook(run, ROOT, roots))
            target = run / 'profile' / build_profile.READS_FOLDER / 'stage.txt'
            code = ("import os\nfrom pathlib import Path\np = Path(os.environ['P'])\n"
                    "for f in sorted(p.rglob('*')):\n    f.is_file() and f.read_bytes()\n")
            env = dict(os.environ, P=str(pool), PYTHONPATH=str(run / 'profile' / build_profile.TRACE_HOOK_FOLDER),
                       **{build_profile.TRACE_ENV: str(target)})
            env.pop('AMIWIND_CACHE_FALLBACK', None)
            subprocess.run([sys.executable, '-c', code], env=env, check=True)
            lines = target.read_text().splitlines()
        problems, summary = build_cache.pool_read_problems(lines)
        self.assertEqual(problems, ['stray.txt'])
        self.assertEqual(summary, {'objects': 1, 'keys': {npc_lod.POOL_NAMESPACE: 1}})


if __name__ == '__main__':
    unittest.main()
