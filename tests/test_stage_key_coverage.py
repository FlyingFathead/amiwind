"""Stage keys cover what the stage runs, diagnostics copied along a scene chain are not inputs, and a stage that
inherits pooled (read-only) files can still edit its own copy.

BUILD-CHIM-KEY-UNDERDECLARED-35: the CHIM stage started tools/cell_progress_build.py by a name written in two parts,
so its fingerprint left out the 8 files (and 2 light_sources functions) the tracker ran; only the read trace caught it.
BUILD-POOL-APPLY-READ-MISS-35: in a pool-mode build every reused stage read tools/storage_pool.py (the reuse step)
and was then refused as a reuse source.
BUILD-SCENE-DIAGNOSTIC-COPY-35: npcs/hands/interior/intro copy the previous scene whole (shutil.copytree), logs
included; the trace counted that byte copy as reading another stage's diagnostics and refused reuse.
BUILD-POOL-READONLY-SCENE-WRITE-35: shutil.copytree copied the read-only mode of pooled inputs onto the stage's own
copy, and npcs failed rewriting npc-scene/seyda.bsp ([Errno 13]).
"""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
import build_audit  # noqa: E402
import build_cache  # noqa: E402
import build_profile  # noqa: E402
from mwad.paths import copy_tree  # noqa: E402

POSIX = os.name == 'posix'
NON_ROOT_POSIX = POSIX and hasattr(os, 'geteuid') and os.geteuid() != 0

# The 8 files the CHIM stage's tracker subprocess read in the 2026_10_10 v0.0.35-dev1 run (profile/manifests/chim.json).
CHIM_TRACKER_FILES = ('tools/cell_lava.py', 'tools/cell_lighting.py', 'tools/cell_progress.py', 'tools/cell_progress_build.py',
                      'tools/cell_progress_chim.py', 'tools/cell_progress_order.py', 'tools/cell_progress_release.py',
                      'tools/light_sources.py')


def folded(source):
    return build_cache.folded_string(ast.parse(source, mode='eval').body)


class NamedInPartsTests(unittest.TestCase):
    def test_strings_built_from_literals_are_folded(self):
        self.assertEqual(folded("'cell_progress' + '_build.py'"), 'cell_progress_build.py')
        self.assertEqual(folded("'a' + 'b' + 'c.py'"), 'abc.py')
        self.assertEqual(folded("f'{\"tool\"}_x.py'"), 'tool_x.py')
        self.assertIsNone(folded("name + '.py'"))
        self.assertIsNone(folded("f'{name}.py'"))
        self.assertIsNone(folded("'a' * 2"))

    def test_a_script_named_in_parts_is_in_the_fingerprint(self):
        stage = ("import subprocess, sys\nfrom pathlib import Path\n"
                 "def main():\n"
                 "    script = Path(__file__).with_name('hid' + 'den_tool.py')\n"
                 "    other = Path(__file__).with_name(f'{\"second\"}_tool.py')\n"
                 "    subprocess.run([sys.executable, str(script)]); subprocess.run([sys.executable, str(other)])\n"
                 "if __name__ == '__main__':\n    main()\n")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tools').mkdir()
            (root / 'tools' / 'stage.py').write_text(stage)
            (root / 'tools' / 'hidden_tool.py').write_text('from deep import f\nif __name__ == "__main__":\n    f()\n')
            (root / 'tools' / 'second_tool.py').write_text('X = 1\n')
            (root / 'tools' / 'deep.py').write_text('def f():\n    return 1\n')
            for scope in build_cache.SCOPES:
                python, _, uncertain = build_cache.SourceIndex(root, scope=scope).closure(root / 'tools' / 'stage.py')
                self.assertFalse(uncertain, scope)
                self.assertLessEqual({'tools/hidden_tool.py', 'tools/second_tool.py', 'tools/deep.py'}, python, scope)

    def test_the_tracker_has_its_own_stage_key_and_the_chim_key_is_exact(self):
        """The CHIM stage no longer runs the tracker (so neither its code nor the docs it can read key the CHIM world);
        the cell-progress stage's key covers every file and function the tracker ran in the dev1 run."""
        index = build_cache.SourceIndex(ROOT)
        chim, chim_data, uncertain = index.closure(ROOT / 'tools' / 'chim_build.py')
        self.assertFalse(uncertain)
        self.assertEqual(sorted(set(CHIM_TRACKER_FILES[:-1]) & chim), [])  # light_sources: CHIM lighting uses it
        self.assertEqual(sorted(path for path in chim_data if path.startswith('docs/')), [])
        script = ROOT / 'tools' / 'cell_progress_build.py'
        tracker, _, uncertain = index.closure(script)
        self.assertFalse(uncertain)
        self.assertEqual([path for path in CHIM_TRACKER_FILES if path not in tracker], [])
        # BUILD-CELL-PROGRESS-KEY-BUGS-35: no documentation (the bug register least of all) keys the tracker stage.
        _, tracker_data, _ = index.closure(script)
        self.assertEqual(sorted(path for path in tracker_data if path.startswith('docs/')), [])
        if index.scope == 'units':
            reached = index.reached_units(script).get('tools/light_sources.py', set())
            self.assertLessEqual({'classify', 'quake_style'}, set(reached))

    def test_no_repository_code_names_a_python_script_the_scan_cannot_follow(self):
        """Island-wide half: a '.py' name built at run time ('x' + suffix, f'{name}.py') would hide a script a stage
        runs from every fingerprint. None may exist outside the reviewed uses below (none names a stage's code)."""
        reviewed = {  # path: why the computed name is not code a stage runs
            'tools/build_cache.py': 'the fingerprint scanner itself',
        }
        found = []
        for base in ('tools', 'src'):
            for path in sorted((ROOT / base).rglob('*.py')):
                relative = path.relative_to(ROOT).as_posix()
                if relative in reviewed:
                    continue
                try:
                    tree = ast.parse(path.read_text(encoding='utf-8'))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    tail = None
                    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                        tail = node.right
                    elif isinstance(node, ast.JoinedStr) and node.values:
                        tail = node.values[-1]
                    if not (isinstance(tail, ast.Constant) and isinstance(tail.value, str) and tail.value.endswith('.py')
                            and not any(ch.isspace() for ch in tail.value)):  # a message naming a file is no script name
                        continue
                    if build_cache.folded_string(node) is None:
                        found.append(f'{relative}:{node.lineno}')
        self.assertEqual(found, [])


class EveryStageAuditTests(unittest.TestCase):
    """build_audit wakes on any stage (not only chim) whose trace holds code its fingerprint left out."""

    def test_every_stage_with_an_uncovered_read_or_call_is_a_wake_finding(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            folder = run / 'profile' / 'manifests'
            folder.mkdir(parents=True)
            for name, reads in (('chim', {'traced': True, 'misses': ['tools/cell_lava.py'],
                                          'call_misses': ['tools/light_sources.py:classify']}),
                                ('npcs', {'traced': True, 'misses': [], 'call_misses': ['tools/x.py:f']}),
                                ('setup', {'traced': True, 'misses': [], 'call_misses': []}),
                                ('engine', None)):
                (folder / f'{name}.json').write_text(json.dumps({'stage': name, 'reads': reads}))
            found = build_audit.key_coverage(run)
            self.assertEqual([(f['stage'], f['severity']) for f in found], [('chim', 'wake'), ('npcs', 'wake')])
            self.assertEqual(found[0]['missed'], ['tools/cell_lava.py', 'tools/light_sources.py:classify'])


def recorder_for(run, name, files, reused):
    recorder = build_cache.Recorder.__new__(build_cache.Recorder)
    recorder.run = Path(run)
    recorder.traced = True
    recorder.closures = {'root': str(ROOT), 'stages': {name: []}, 'files': files,
                         'units': {name: {}}, 'module_units': {'tools/storage_pool.py': ['place']}}
    recorder.cache = {'reused': {name: {'from': 'old'}}} if reused else {}
    return recorder


class ApplyStepTests(unittest.TestCase):
    def test_a_reused_stage_reading_the_pool_module_stays_reusable(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / 'reads.txt'
            trace.write_text('tools/storage_pool.py\n@tools/storage_pool.py\tplace\ntools/converter.py\n')
            files = ['tools/storage_pool.py', 'tools/converter.py']
            reasons, summary = recorder_for(temp, 'setup', files, reused=True).check_trace('setup', trace)
            self.assertEqual(summary['misses'], ['tools/converter.py'])  # any other uncovered read still counts
            self.assertEqual(summary['call_misses'], [])
            trace.write_text('tools/storage_pool.py\n@tools/storage_pool.py\tplace\n')
            reasons, _ = recorder_for(temp, 'setup', files, reused=True).check_trace('setup', trace)
            self.assertEqual(reasons, [])
            # A stage that really ran and read it without its key covering it is still refused.
            reasons, summary = recorder_for(temp, 'setup', files, reused=False).check_trace('setup', trace)
            self.assertEqual(summary['misses'], ['tools/storage_pool.py'])
            self.assertEqual(summary['call_misses'], ['tools/storage_pool.py:place'])


@unittest.skipUnless(POSIX, 'the read trace runs on POSIX')
class DiagnosticCopyTests(unittest.TestCase):
    def test_a_diagnostic_copied_into_a_diagnostic_is_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            (run / 'profile').mkdir(parents=True)
            (run / 'bsp-scene').mkdir()
            for name in ('light.log', 'seyda.log', 'seyda.bsp'):
                (run / 'bsp-scene' / name).write_text(name)
            (run / 'other').mkdir()
            (run / 'other' / 'compile.log').write_text('read for real')
            (run / 'other' / 'kept.log').write_text('copied into a compared output')
            self.assertTrue(build_cache.write_trace_hook(run, ROOT))
            target = run / 'profile' / build_profile.READS_FOLDER / 'stage.txt'
            code = ("import os, shutil, sys\nfrom pathlib import Path\nsys.path.insert(0, os.environ['SRC'])\n"
                    "from mwad.paths import copy_tree\nr = Path(os.environ['R'])\n"
                    "copy_tree(r / 'bsp-scene', r / 'npc-scene')\n"
                    "shutil.copytree(r / 'bsp-scene', r / 'plain-copy')\n"
                    "(r / 'other' / 'compile.log').read_text()\n"
                    "shutil.copyfile(r / 'other' / 'kept.log', r / 'npc-scene' / 'kept.txt')\n")
            env = dict(os.environ, R=str(run), SRC=str(ROOT / 'src'),
                       PYTHONPATH=str(run / 'profile' / build_profile.TRACE_HOOK_FOLDER),
                       **{build_profile.TRACE_ENV: str(target)})
            subprocess.run([sys.executable, '-c', code], env=env, check=True)
            recorder = build_cache.Recorder.__new__(build_cache.Recorder)
            recorder.traced = True
            self.assertEqual(recorder.diagnostic_reads(target), ['other/compile.log', 'other/kept.log'])

    def test_a_scene_chain_stage_is_reusable_after_copying_the_scene(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            steps = [('npcs', [sys.executable, 'tools/x.py', '--scene', str(run / 'bsp-scene'), '--out', str(run / 'npc-scene')])]
            (run / 'bsp-scene').mkdir(parents=True)
            recorder = build_cache.Recorder(run, steps, {})
            recorder.traced = True
            recorder.before('npcs', steps[0][1])
            (run / 'npc-scene').mkdir()
            (run / 'npc-scene' / 'light.log').write_text('copied')
            trace = Path(temp) / 'reads.txt'
            trace.write_text('>npc-scene/light.log\n')  # the copy's read of bsp-scene/light.log is not listed
            manifest = recorder.after('npcs', {}, trace)
            self.assertTrue(manifest['reusable'], manifest['reasons'])


STAGE_BASE = '''
import sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
(out / 'seyda.bsp').write_bytes(bytes(range(256)) * 64)
'''
# Like prepare_npcs: copy the inherited scene, then rewrite one of its files in place.
STAGE_CHAIN = '''
import sys
from pathlib import Path
sys.path.insert(0, SRC)
from mwad.paths import copy_tree
scene = Path(sys.argv[sys.argv.index('--scene') + 1]); out = Path(sys.argv[sys.argv.index('--out') + 1])
copy_tree(scene, out)
raw = (out / 'seyda.bsp').read_bytes()
(out / 'seyda.bsp').write_bytes(raw + b'entities')
'''


@unittest.skipUnless(NON_ROOT_POSIX, 'pooled hard links are read-only only for a non-root POSIX user')
class PoolSceneWriteTests(unittest.TestCase):
    def test_copy_tree_of_pooled_files_is_writable_and_leaves_the_pool_unchanged(self):
        import storage_pool
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pool, scene = root / 'pool', root / 'bsp-scene'
            scene.mkdir()
            (scene / 'seyda.bsp').write_bytes(b'x' * 4096)
            digest = build_cache.sha256_file(scene / 'seyda.bsp')
            storage_pool.put(pool, scene / 'seyda.bsp', digest)
            blob = storage_pool.object_path(pool, digest)
            self.assertEqual(os.stat(blob).st_ino, os.stat(scene / 'seyda.bsp').st_ino)
            self.assertFalse(os.stat(blob).st_mode & 0o222)
            shutil.copytree(scene, root / 'old-way')
            with self.assertRaises(PermissionError):  # the bug: the copy kept the pool's read-only mode
                (root / 'old-way' / 'seyda.bsp').write_bytes(b'y')
            copy_tree(scene, root / 'npc-scene')
            (root / 'npc-scene' / 'seyda.bsp').write_bytes(b'rewritten')
            self.assertEqual(build_cache.sha256_file(blob), digest)
            self.assertFalse(os.stat(blob).st_mode & 0o222)
            self.assertNotEqual(os.stat(root / 'npc-scene' / 'seyda.bsp').st_ino, os.stat(blob).st_ino)

    def test_a_pool_mode_resume_reruns_a_scene_chain_stage(self):
        """A pool-mode resume where the scene-chain stage reruns on reused (pooled, read-only) inputs succeeds,
        and the pooled object keeps its bytes."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repository, pool = root / 'repo', root / 'workspace' / 'pool'
            (repository / 'tools').mkdir(parents=True)
            (repository / 'tools' / 'stage_base.py').write_text(STAGE_BASE)
            chain = repository / 'tools' / 'stage_chain.py'
            chain.write_text(STAGE_CHAIN.replace('SRC', repr(str(ROOT / 'src'))))

            def run_build(name, reuse_from=None, mode='copy'):
                run = root / 'workspace' / name
                steps = [('base', [sys.executable, str(repository / 'tools' / 'stage_base.py'), '--out', str(run / 'scene')]),
                         ('chain', [sys.executable, str(chain), '--scene', str(run / 'scene'), '--out', str(run / 'chain')])]
                meta = {'compiler_jobs': 1, 'input_sha256': {'Morrowind.esm': 'aa'}, 'tools': {}, 'tool_sha256': {},
                        'version_comparison': [], 'runtime_version': '0.0.0-dev1'}
                with contextlib.redirect_stdout(io.StringIO()):
                    steps = build_cache.prepare(steps, run, meta, reuse_from, mode, build_cache.SourceIndex(repository),
                                                pool=pool if mode == 'pool' else None)
                    build.execute(steps, run, meta)
                return run, json.loads((run / 'build-state.json').read_text())

            first, _ = run_build('first')
            chain.write_text(chain.read_text() + '# the chain stage changed: it runs again\n')
            second, state = run_build('second', reuse_from=first, mode='pool')
            self.assertEqual(state['status'], 'passed')
            self.assertIn('base', state['stage_cache']['reused'])
            self.assertNotIn('chain', state['stage_cache']['reused'])
            digest = build_cache.sha256_file(first / 'scene' / 'seyda.bsp')
            blob = __import__('storage_pool').object_path(pool, digest)
            self.assertEqual(os.stat(blob).st_ino, os.stat(second / 'scene' / 'seyda.bsp').st_ino)
            self.assertEqual(build_cache.sha256_file(blob), digest)
            self.assertEqual((second / 'chain' / 'seyda.bsp').read_bytes(),
                             (first / 'scene' / 'seyda.bsp').read_bytes() + b'entities')


class CopyModeSweepTests(unittest.TestCase):
    def test_no_repository_code_copies_a_tree_with_its_read_only_modes(self):
        """Island-wide half of BUILD-POOL-READONLY-SCENE-WRITE-35: every folder copy goes through
        mwad.paths.copy_tree (copies writable, the pooled source untouched)."""
        found = []
        for base in ('tools', 'src'):
            for path in sorted((ROOT / base).rglob('*.py')):
                relative = path.relative_to(ROOT).as_posix()
                if relative == 'src/mwad/paths.py':
                    continue
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                    if 'shutil.copytree(' in line:
                        found.append(f'{relative}:{number}')
        self.assertEqual(found, [])


class ResumeTests(unittest.TestCase):
    """2026_10_10 v0.0.35 resumes: reruns of npcs/hands/interior/intro were byte-identical apart from logs, yet
    every stage after them was refused ('outputs differ') and area failed on a static rebuild hazard."""

    def manifests(self, run, old, new_extra, old_extra, new_reasons, old_reasons):
        same = {'npc-scene/seyda.bsp': 'a' * 64}
        for folder, extra, reasons in ((run, new_extra, new_reasons), (old, old_extra, old_reasons)):
            target = folder / 'profile' / 'manifests'
            target.mkdir(parents=True)
            (folder / 'build-state.json').write_text('{}')
            files = dict(same, **extra)
            (target / 'npcs.json').write_text(json.dumps({
                'schema': build_cache.MANIFEST_SCHEMA, 'stage': 'npcs', 'status': 'complete', 'reusable': not reasons,
                'reasons': reasons, 'files': {k: {'size': 1, 'sha256': v, 'mode': 420} for k, v in files.items()},
                'links': {}, 'deleted': [], 'directories': [], 'deleted_directories': []}))

    def test_outputs_of_a_trace_refused_record_are_compared(self):
        """BUILD-RESUME-OUTPUTS-DIFFER-35: a record refused only for what it read still records what it wrote."""
        diagnostics = ['read build diagnostics written by other stages, which are not stage inputs: bsp-scene/light.log']
        code = ['read 8 repository files its fingerprint left out (first: tools/cell_lava.py)']
        attributed = ['changed npc-scene/seyda.bsp (and 0 more) while hands ran; outputs cannot be attributed']
        cases = (({'npc-scene/light.log': 'b' * 64}, {'npc-scene/light.log': 'c' * 64}, diagnostics, diagnostics, True),
                 ({}, {}, code, [], True),
                 ({'npc-scene/x.bsp': 'b' * 64}, {'npc-scene/x.bsp': 'c' * 64}, diagnostics, diagnostics, False),
                 ({}, {}, attributed, [], False),
                 ({}, {}, [], ['created run-folder entries outside every declared stage path: junk'], False))
        for new_extra, old_extra, new_reasons, old_reasons, expected in cases:
            with tempfile.TemporaryDirectory() as temp:
                run, old = Path(temp) / 'new', Path(temp) / 'old'
                self.manifests(run, old, new_extra, old_extra, new_reasons, old_reasons)
                self.assertIs(build_cache.same_outputs(run, old, 'npcs'), expected, (new_reasons, old_reasons))

    def test_a_skipping_stage_that_ran_after_all_is_no_rebuild_hazard(self):
        """BUILD-RESUME-HAZARD-STATIC-35: census (planned as reused) left out 8 files area replaces; when census
        runs after all it writes them, so area can be rebuilt."""
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            plan = {'rebuild_hazard_count': 9, 'rebuild_hazard_stages': {'census': 8, 'npc-gallery': 1},
                    'rebuilt_ancestors': []}
            self.assertEqual(build_cache.live_hazard(plan, run), {'census': 8, 'npc-gallery': 1})
            (run / 'profile' / 'reuse-fallback').mkdir(parents=True)
            (run / 'profile' / 'reuse-fallback' / 'census.txt').write_text('outputs differ')
            self.assertEqual(build_cache.live_hazard(plan, run), {'npc-gallery': 1})
            plan['rebuilt_ancestors'] = ['npc-gallery']
            self.assertEqual(build_cache.live_hazard(plan, run), {})
            self.assertEqual(build_cache.live_hazard({'rebuild_hazard_count': 3}, run), {'earlier reused stages': 3})
            self.assertEqual(build_cache.live_hazard({}, run), {})


class GalleryBytesTests(unittest.TestCase):
    def test_a_cached_and_a_fresh_gallery_result_write_the_same_bytes(self):
        """BUILD-GALLERY-JSON-KEY-ORDER-35: 3,460 gallery model receipts differed between two builds only in key
        order (cache entries are stored with sorted keys, fresh results are not)."""
        import gallery_cache
        fresh = {'status': 'ready', 'key': 'm1', 'vertices': 3, 'sha256': 'a' * 64, 'atlas_profile': 'face8-v1'}
        cached = json.loads(json.dumps(fresh, sort_keys=True))
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'a').mkdir()
            (Path(temp) / 'b').mkdir()
            gallery_cache.materialize(Path(temp) / 'a', 'm1', b'mdl', fresh)
            gallery_cache.materialize(Path(temp) / 'b', 'm1', b'mdl', cached)
            self.assertEqual((Path(temp) / 'a' / 'm1.json').read_bytes(), (Path(temp) / 'b' / 'm1.json').read_bytes())

    def test_every_gallery_json_writer_sorts_its_keys(self):
        for relative in ('tools/prepare_gallery.py', 'tools/gallery_cache.py'):
            for number, line in enumerate((ROOT / relative).read_text(encoding='utf-8').splitlines(), 1):
                if 'json.dumps(' in line and ('write_text(' in line or 'atomic_write(' in line):
                    self.assertIn('sort_keys=True', line, f'{relative}:{number}')


class SelfNamingTests(unittest.TestCase):
    """BUILD-CELL-PROGRESS-KEY-BUGS-35: tools/cell_progress.py writes 'generator': 'tools/cell_progress.py' into its
    output. The scan took that label for a run of the module's command line, reached its main() and, through it,
    all of docs/ (the bug register too), so every bug registration rebuilt cell-progress and stopped builds."""

    STAGE = 'from lib import ingest\nif __name__ == "__main__":\n    ingest()\n'
    MAIN = ("def main():\n    return (Path(__file__).parents[1] / 'docs' / 'register.json').read_text()\n"
            "if __name__ == '__main__':\n    main()\n")

    def closure(self, library):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tools').mkdir()
            (root / 'docs').mkdir()
            (root / 'docs' / 'register.json').write_text('[]')
            (root / 'tools' / 'stage.py').write_text(self.STAGE)
            (root / 'tools' / 'lib.py').write_text(library)
            _, data, _ = build_cache.SourceIndex(root).closure(root / 'tools' / 'stage.py')
            return data

    def test_a_module_naming_itself_does_not_reach_its_main(self):
        library = ("from pathlib import Path\n"
                   "def ingest():\n    return {'generator': 'tools/lib.py'}\n" + self.MAIN)
        self.assertNotIn('docs/register.json', self.closure(library))

    def test_a_module_that_runs_itself_is_still_followed(self):
        library = ("import subprocess, sys\nfrom pathlib import Path\n"
                   "def ingest():\n    subprocess.run([sys.executable, 'tools/lib.py'])\n" + self.MAIN)
        self.assertIn('docs/register.json', self.closure(library))

    def test_an_advisory_stage_never_stops_the_build(self):
        steps = [('chim', ['python3', 'tools/chim_build.py']),
                 ('cell-progress', ['python3', 'tools/cell_progress_build.py', '--never-fail']),
                 ('needed', ['python3', 'tools/x.py', '--never-fail']), ('image', ['python3', 'tools/build_aga.py'])]
        dependencies = {'chim': (), 'cell-progress': ('chim',), 'needed': (), 'image': ('chim', 'needed')}
        self.assertEqual(build_cache.advisory_stages(steps, dependencies), {'cell-progress'})


if __name__ == '__main__':
    unittest.main()
