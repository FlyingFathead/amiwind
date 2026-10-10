"""Stage fingerprints and --reuse-from: exact invalidation, byte-identical reuse, refusals."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_cache  # noqa: E402
import build_profile  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

MANIFESTS = os.name == 'posix'

STAGE_A = '''
import sys
from pathlib import Path
def main():
    from helper import payload
    out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
    (out / 'a.txt').write_text(payload('a'))
    (out / 'deep').mkdir()
    (out / 'deep' / 'blob.bin').write_bytes(bytes(range(256)) * 512)
    (out / 'scratch.tmp').write_text('removed by stage c')
main()
'''
STAGE_B = '''
import sys
from pathlib import Path
from helper import payload
scene = Path(sys.argv[sys.argv.index('--scene') + 1]); out = Path(sys.argv[sys.argv.index('--out') + 1])
out.mkdir(parents=True)
(out / 'b.txt').write_text(payload('b') + (scene / 'a.txt').read_text())
'''
STAGE_C = '''
import sys
from pathlib import Path
scene = Path(sys.argv[sys.argv.index('--scene') + 1]); other = Path(sys.argv[sys.argv.index('--other') + 1])
(scene / 'c.txt').write_text('c:' + (other / 'b.txt').read_text())
(scene / 'scratch.tmp').unlink()
'''
STAGE_D = '''
import sys
from pathlib import Path
other = Path(sys.argv[sys.argv.index('--other') + 1]); out = Path(sys.argv[sys.argv.index('--out') + 1])
out.mkdir(parents=True)
(out / 'd.txt').write_text('d:' + (other / 'b.txt').read_text())
'''
HELPER = '''
import json
def payload(name):
    settings = json.loads(open(__file__.replace('tools/helper.py', 'config/settings.json')).read())
    return name + ':' + settings['value'] + '\\n'
CONFIG = 'config/settings.json'
def unused():
    import heavy
    return heavy.VALUE
'''
STAIR = '''
import os
VARIABLE = 'AMIWIND_STAIR_MITIGATION'
def mode():
    return os.environ.get(VARIABLE, 'on')
'''
STAGE_E = '''
import sys
from pathlib import Path
from stair import mode
out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
(out / 'e.txt').write_text(mode())
'''
DYNAMIC = '''
import os
def option(name):
    return os.environ.get(f'AMIWIND_{name}')
'''
STAGE_F = '''
import sys
from dynamic import option
print(option('ANY'))
'''
# Reads a repository file through a path no static scan can see: the read trace must catch it.
STAGE_HIDDEN = '''
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
name = ''.join(['hid', 'den.json'])  # built at run time: no static scan sees it (literal parts are folded)
out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
(out / 'h.txt').write_text((root / ''.join(['con', 'fig']) / name).read_text())
'''

# A town registry: config/registry.json rows name the town files (BUILD-CACHE-OVERBROAD-33).
TOWNS = '''
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = 'registry.json'
def load():
    rows = json.loads((ROOT / 'config' / REGISTRY).read_text())
    return [json.loads((ROOT / 'config' / row['config']).read_text())['name'] for row in rows]
'''
STAGE_G = '''
import sys
from pathlib import Path
from towns import load
out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
(out / 'g.txt').write_text(','.join(load()))
'''
# Runs helper.unused() through a name no static scan can see: the call trace must catch it.
STAGE_CALL = '''
import sys
from pathlib import Path
helper = __import__('helper')
out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
(out / 'u.txt').write_text(str(getattr(helper, 'un' + 'used')()))
'''


def make_repository(root):
    (root / 'tools').mkdir(parents=True)
    (root / 'config').mkdir()
    (root / 'engine').mkdir()
    (root / 'docs').mkdir()
    for name, text in (('stage_a.py', STAGE_A), ('stage_b.py', STAGE_B), ('stage_c.py', STAGE_C), ('stage_d.py', STAGE_D),
                       ('helper.py', HELPER), ('unrelated.py', 'VALUE = 1\n'), ('heavy.py', 'VALUE = 1\n'),
                       ('stair.py', STAIR), ('stage_e.py', STAGE_E), ('dynamic.py', DYNAMIC), ('stage_f.py', STAGE_F),
                       ('stage_hidden.py', STAGE_HIDDEN), ('towns.py', TOWNS), ('stage_g.py', STAGE_G),
                       ('stage_call.py', STAGE_CALL)):
        (root / 'tools' / name).write_text(text)
    (root / 'config' / 'settings.json').write_text('{"value": "one"}')
    (root / 'config' / 'registry.json').write_text('[{"id": "a", "config": "town_a.json"}]')
    (root / 'config' / 'town_a.json').write_text('{"name": "Balmora"}')
    (root / 'config' / 'town_b.json').write_text('{"name": "Vivec"}')
    (root / 'config' / 'release.json').write_text('{"features": []}')
    (root / 'config' / 'hidden.json').write_text('hidden')
    (root / 'engine' / 'engine.c').write_text('int main(void) { return 0; }\n')
    (root / 'docs' / 'NOTES.md').write_text('# Notes\n')
    return build_cache.SourceIndex(root)


def steps_for(repository, run, data, jobs=2):
    tools = repository / 'tools'
    return [('alpha', [sys.executable, str(tools / 'stage_a.py'), '--data-files', str(data), '--out', str(run / 'alpha'),
                       '--jobs', str(jobs)]),
            ('beta', [sys.executable, str(tools / 'stage_b.py'), '--scene', str(run / 'alpha'), '--out', str(run / 'beta')]),
            ('gamma', [sys.executable, str(tools / 'stage_c.py'), '--scene', str(run / 'alpha'), '--other', str(run / 'beta')]),
            ('delta', [sys.executable, str(tools / 'stage_d.py'), '--other', str(run / 'beta'), '--out', str(run / 'delta')])]


def metadata(inputs=None):
    return {'compiler_jobs': 1, 'input_sha256': inputs or {'Morrowind.esm': 'aa'}, 'tools': {}, 'tool_sha256': {},
            'version_comparison': []}


def tree(run):
    return {p.relative_to(run).as_posix(): p.read_bytes() for p in sorted(Path(run).rglob('*'))
            if p.is_file() and p.relative_to(run).parts[0] in ('alpha', 'beta', 'delta')}


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / 'repo'
        self.data = self.root / 'data'
        self.data.mkdir()
        make_repository(self.repository)

    def tearDown(self):
        self.temp.cleanup()

    def fingerprints(self, run='run', jobs=2, inputs=None, env=None, steps=None, scope=build_cache.DEFAULT_SCOPE):
        index = build_cache.SourceIndex(self.repository, scope=scope)
        steps = steps or steps_for(self.repository, self.root / run, self.data, jobs)
        with patch.dict(os.environ, env or {}):
            return build_cache.fingerprint_steps(steps, self.root / run, metadata(inputs), index)[0]

    def test_unchanged_inputs_give_the_same_fingerprint(self):
        first = self.fingerprints()
        self.assertEqual(first, self.fingerprints())
        self.assertEqual(first, self.fingerprints(run='another-run'))   # run folder normalized
        self.assertEqual(first, self.fingerprints(jobs=16))              # worker count normalized
        (self.repository / 'tools' / 'unrelated.py').write_text('VALUE = 2\n')
        (self.repository / 'engine' / 'engine.c').write_text('int main(void) { return 1; }\n')
        (self.repository / 'docs' / 'NOTES.md').write_text('# Changed notes\n')
        self.assertEqual(first, self.fingerprints(env={'UNRELATED': 'x', 'AMIWIND_BUILD_JOBS': '7'}))

    def test_any_input_tool_source_or_argument_changes_it(self):
        first = self.fingerprints()
        changed = self.fingerprints(inputs={'Morrowind.esm': 'bb'})
        self.assertNotEqual(first['alpha'], changed['alpha'])            # game input (alpha reads --data-files)
        self.assertNotEqual(first['gamma'], changed['gamma'])            # ... and everything after it
        (self.repository / 'tools' / 'helper.py').write_text(HELPER + 'EDITED = 1\n')
        helper = self.fingerprints()
        self.assertNotEqual(first['alpha'], helper['alpha'])             # imported inside a function
        self.assertNotEqual(first['beta'], helper['beta'])
        (self.repository / 'tools' / 'helper.py').write_text(HELPER)
        self.assertEqual(first, self.fingerprints())
        (self.repository / 'config' / 'settings.json').write_text('{"value": "two"}')
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])  # data folder named in the code
        (self.repository / 'config' / 'settings.json').write_text('{"value": "one"}')
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C + 'EDITED = 1\n')
        edited = self.fingerprints()
        self.assertEqual(first['alpha'], edited['alpha'])
        self.assertEqual(first['beta'], edited['beta'])
        self.assertNotEqual(first['gamma'], edited['gamma'])
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C)
        steps = steps_for(self.repository, self.root / 'run', self.data)
        steps[1][1].append('--extra')
        argument = self.fingerprints(steps=steps)
        self.assertEqual(first['alpha'], argument['alpha'])
        self.assertNotEqual(first['beta'], argument['beta'])
        self.assertNotEqual(first['gamma'], argument['gamma'])           # through its dependency
        # Environment: only the variables a stage's code names count (BUILD-ENV-FINGERPRINT-GLOBAL-33).
        self.assertEqual(first['alpha'], self.fingerprints(env={'AMIWIND_SCENERY_REDUCE': '0.5'})['alpha'])
        external = self.root / 'captions.json'
        external.write_text('[1]')
        steps = steps_for(self.repository, self.root / 'run', self.data)
        steps[0] = (steps[0][0], steps[0][1] + ['--intro-captions', str(external)])
        with_file = self.fingerprints(steps=steps)
        external.write_text('[2]')
        self.assertNotEqual(with_file['alpha'], self.fingerprints(steps=steps)['alpha'])

    def extra_steps(self, run='run', root=None):
        tools = (root or self.repository) / 'tools'
        run = self.root / run
        return [('alpha', [sys.executable, str(tools / 'stage_a.py'), '--data-files', str(self.data), '--out', str(run / 'alpha')]),
                ('epsilon', [sys.executable, str(tools / 'stage_e.py'), '--out', str(run / 'epsilon')]),
                ('zeta', [sys.executable, str(tools / 'stage_f.py'), '--out', str(run / 'zeta')]),
                ('eta', [sys.executable, str(tools / 'stage_d.py'), '--other', str(run / 'epsilon'), '--out', str(run / 'eta')])]

    def test_stair_rule_reaches_only_the_stages_that_read_it(self):
        """BUILD-ENV-FINGERPRINT-GLOBAL-33: a build-wide setting invalidates only its readers."""
        dependencies = {'alpha': (), 'epsilon': (), 'zeta': (), 'eta': ('epsilon',)}
        index = build_cache.SourceIndex(self.repository)
        run = self.root / 'run'

        def prints(env):
            with patch.dict(os.environ, env):
                return build_cache.fingerprint_steps(self.extra_steps(), run, metadata(), index, dependencies)[0]
        on, off = prints({'AMIWIND_STAIR_MITIGATION': 'on'}), prints({'AMIWIND_STAIR_MITIGATION': 'off'})
        self.assertEqual(on['alpha'], off['alpha'])          # never reads it
        self.assertNotEqual(on['epsilon'], off['epsilon'])   # reads it (through a module constant)
        self.assertNotEqual(on['eta'], off['eta'])           # depends on a stage that reads it
        self.assertNotEqual(on['zeta'], off['zeta'])         # builds AMIWIND_ names at run time: every variable
        self.assertEqual(index.environment_names(self.repository / 'tools' / 'stage_e.py'), {'AMIWIND_STAIR_MITIGATION'})
        self.assertEqual(index.environment_names(self.repository / 'tools' / 'stage_f.py'), {build_cache.ENV_ANY})
        self.assertEqual(index.environment_names(self.repository / 'tools' / 'stage_a.py'), set())
        # Bookkeeping and worker-count variables never count.
        self.assertEqual(on, prints({'AMIWIND_STAIR_MITIGATION': 'on', 'AMIWIND_BUILD_BUDGET': '3',
                                     'AMIWIND_ACTIVE_ENV': '/somewhere/venv', 'AMIWIND_STAGE_TRACE': '/x'}))

    def test_real_stages_read_the_stair_rule_only_where_it_is_used(self):
        index = build_cache.SourceIndex()
        variable = 'AMIWIND_STAIR_MITIGATION'
        for script in ('prepare_media_assets.py', 'prepare_music.py', 'prepare_dialogue_lookup.py', 'mwad.py',
                       'world_scenery.py', 'prepare_tree_sprites.py'):
            names = index.environment_names(ROOT / 'tools' / script)
            self.assertNotIn(variable, names, script)
            self.assertNotIn(build_cache.ENV_ANY, names, script)
        for script in ('prepare_mesh_bsp.py', 'prepare_interior.py', 'import_town.py', 'build_aga.py'):
            self.assertIn(variable, index.environment_names(ROOT / 'tools' / script), script)
        with patch.dict(os.environ, {variable: 'on'}):
            media_on = build_cache.stage_environment(ROOT / 'tools' / 'prepare_media_assets.py', index)
            bsp_on = build_cache.stage_environment(ROOT / 'tools' / 'prepare_mesh_bsp.py', index)
        with patch.dict(os.environ, {variable: 'off'}):
            self.assertEqual(media_on, build_cache.stage_environment(ROOT / 'tools' / 'prepare_media_assets.py', index))
            self.assertNotEqual(bsp_on, build_cache.stage_environment(ROOT / 'tools' / 'prepare_mesh_bsp.py', index))

    def test_unrelated_code_does_not_count(self):
        """BUILD-CACHE-CLOSURE-WIDE-33: a module imported only by code the stage never reaches is not an input."""
        first = self.fingerprints()
        (self.repository / 'tools' / 'heavy.py').write_text('VALUE = 2\n')
        self.assertEqual(first, self.fingerprints())
        python, _, _ = build_cache.SourceIndex(self.repository).closure(self.repository / 'tools' / 'stage_a.py')
        self.assertNotIn('tools/heavy.py', python)
        # The earlier method stays selectable and still counts it.
        python, _, _ = build_cache.SourceIndex(self.repository, scope='modules').closure(self.repository / 'tools' / 'stage_a.py')
        self.assertIn('tools/heavy.py', python)
        # Once the stage reaches the function, the module counts.
        (self.repository / 'tools' / 'stage_a.py').write_text(STAGE_A + 'from helper import unused\nunused()\n')
        reached = self.fingerprints()
        (self.repository / 'tools' / 'heavy.py').write_text('VALUE = 3\n')
        self.assertNotEqual(reached['alpha'], self.fingerprints()['alpha'])

    def test_instrumentation_modules_never_count(self):
        """Profiler/progress edits keep reuse; a converter edit does not (explicit, reviewed list)."""
        self.assertEqual(build_cache.INSTRUMENTATION_MODULES,
                         {'tools/build_profile.py', 'tools/build_progress.py', 'tools/build_cache.py',
                          'tools/unit_tree.py'})
        tools = self.repository / 'tools'
        (tools / 'build_progress.py').write_text('def show(text):\n    print(text)\n')
        (tools / 'build_profile.py').write_text('from build_progress import show\ndef instrument(stage):\n    show(stage)\n')
        (tools / 'stage_a.py').write_text(STAGE_A.replace('def main():', 'import build_profile\nbuild_profile.instrument("a")\n'
                                                          'def main():'))
        first = self.fingerprints()
        python, _, _ = build_cache.SourceIndex(self.repository).closure(tools / 'stage_a.py')
        self.assertFalse(python & build_cache.INSTRUMENTATION_MODULES)
        (tools / 'build_progress.py').write_text('def show(text):\n    print("[progress]", text)\n')
        (tools / 'build_profile.py').write_text('from build_progress import show\nimport unrelated\ndef instrument(stage):\n'
                                                '    show(stage)\n')
        self.assertEqual(first, self.fingerprints())
        (tools / 'helper.py').write_text(HELPER + 'CONVERTER_EDIT = 1\n')
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])
        # On this repository: a profiler edit keeps every converter's fingerprint.
        index = build_cache.SourceIndex()
        scripts = [ROOT / 'tools' / name for name in ('prepare_world_regions.py', 'prepare_mesh_bsp.py', 'prepare_music.py')]
        before = [index.digest(script) for script in scripts]
        for module in build_cache.INSTRUMENTATION_MODULES:
            if module in index.files:
                index.files[module] = 'edited'
        self.assertEqual(before, [index.digest(script) for script in scripts])

    def test_real_closures_leave_unrelated_tools_out(self):
        """Editing a tool a stage cannot reach keeps its fingerprint (measured on this repository)."""
        index = build_cache.SourceIndex(scope='symbols')  # whole files: an edit is a changed hash
        media = ROOT / 'tools' / 'prepare_media_assets.py'
        python, data, uncertain = index.closure(media)
        self.assertFalse(uncertain)
        for unrelated in ('tools/build_aga.py', 'tools/prepare_world_regions.py', 'tools/mesh_geometry.py',
                          'tools/stair_walk.py', 'tools/project_version.py'):
            self.assertNotIn(unrelated, python)
        self.assertFalse([path for path in data if path.startswith(('engine/', 'docs/', 'config/'))], data)
        before = index.digest(media)
        index.files['tools/build_aga.py'] = 'edited'
        index.files['tools/mesh_geometry.py'] = 'edited'
        self.assertEqual(before, index.digest(media))
        self.assertNotEqual(index.digest(ROOT / 'tools' / 'prepare_mesh_bsp.py'),
                            build_cache.SourceIndex(scope='symbols').digest(ROOT / 'tools' / 'prepare_mesh_bsp.py'))

    def test_moved_workspace_and_checkout_keep_fingerprints(self):
        """BUILD-CACHE-ABSOLUTE-PATHS-33: fingerprints hold content, not locations."""
        def prints(base, captions_text='[1]'):
            repository, data = base / 'repo', base / 'data'
            if not repository.exists():
                shutil.copytree(self.repository, repository)
                data.mkdir()
                (base / 'bin').mkdir()
                (base / 'bin' / 'qbsp').write_text('tool')
            (base / 'captions.json').write_text(captions_text)
            run = base / 'workspace' / 'build' / 'dev-a'
            steps = steps_for(repository, run, data)
            steps[0] = (steps[0][0], steps[0][1] + ['--qbsp', str(base / 'bin' / 'qbsp'), '--bindir', str(base / 'bin'),
                                                    '--cache', str(base / 'workspace' / 'cache' / 'models'),
                                                    '--intro-captions', str(base / 'captions.json')])
            meta = dict(metadata(), data_files=str(data), tools={'qbsp': str(base / 'bin' / 'qbsp')},
                        tool_sha256={'qbsp': 'same'})
            (base / 'workspace' / 'cache' / 'models').mkdir(parents=True, exist_ok=True)
            return build_cache.fingerprint_steps(steps, run, meta, build_cache.SourceIndex(repository))[:2]
        first, components = prints(self.root / 'one')
        second, _ = prints(self.root / 'elsewhere' / 'two')
        self.assertEqual(first, second)
        command = components['alpha']['command']
        self.assertIn('{REPO}/tools/stage_a.py', command)
        self.assertIn('{DATA}', command)
        self.assertIn('{TOOL:qbsp}', command)
        self.assertIn('{TOOLDIR:qbsp}', command)
        self.assertIn('{WORKSPACE}/cache/models', command)
        self.assertIn('{EXTERNAL}', command)
        self.assertFalse([part for part in json.dumps(components) .split('"') if str(self.root) in part])
        # Content still counts.
        self.assertNotEqual(first['alpha'], prints(self.root / 'one', '[2]')[0]['alpha'])

    def test_functions_a_stage_never_reaches_do_not_count(self):
        """BUILD-CACHE-OVERBROAD-33: scope 'units' hashes a module's import-time code and the functions a stage
        reaches; an edit elsewhere in a module every stage imports keeps every fingerprint."""
        helper = self.repository / 'tools' / 'helper.py'
        first, whole = self.fingerprints(), self.fingerprints(scope='symbols')
        helper.write_text(HELPER.replace('return heavy.VALUE', 'return heavy.VALUE + 1'))
        self.assertEqual(first, self.fingerprints())                       # unused() is never reached
        self.assertNotEqual(whole['alpha'], self.fingerprints(scope='symbols')['alpha'])  # whole files: still selectable
        helper.write_text(HELPER.replace("name + ':'", "name + '='"))
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])  # payload() is reached
        self.assertNotEqual(first['beta'], self.fingerprints()['beta'])
        helper.write_text(HELPER + 'EXTRA = 1\n')
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])  # import-time code always counts
        helper.write_text(HELPER.replace('def unused():', 'def unused(value=print(1)):'))
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])  # default values run on import
        helper.write_text(HELPER)
        self.assertEqual(first, self.fingerprints())
        index = build_cache.SourceIndex(self.repository)
        reached = index.reached_units(self.repository / 'tools' / 'stage_a.py')['tools/helper.py']
        self.assertIn('payload', reached)
        self.assertNotIn('unused', reached)
        # explain names the file that changed
        steps = steps_for(self.repository, self.root / 'run', self.data)
        _, before, _, _ = build_cache.fingerprint_steps(steps, self.root / 'run', metadata(), index)
        helper.write_text(HELPER.replace("name + ':'", "name + '='"))
        _, after, _, _ = build_cache.fingerprint_steps(steps, self.root / 'run', metadata(),
                                                       build_cache.SourceIndex(self.repository))
        self.assertEqual(build_cache.explain(before['alpha'], after['alpha']), ['sources (tools/helper.py)'])

    def test_registry_named_files_and_whole_path_chains(self):
        """BUILD-CACHE-OVERBROAD-33: ROOT / 'config' / row['config'] counts the files the registry rows name,
        and ROOT / 'config' / NAME one file, not the whole config folder."""
        index = build_cache.SourceIndex(self.repository)
        stage = self.repository / 'tools' / 'stage_g.py'
        _, data, uncertain = index.closure(stage)
        self.assertFalse(uncertain)
        self.assertEqual(data, {'config/registry.json', 'config/town_a.json'})
        _, wide, _ = build_cache.SourceIndex(self.repository, scope='symbols').closure(stage)
        self.assertIn('config/release.json', wide)                     # the earlier rule: the whole folder
        steps = [('gee', [sys.executable, str(stage), '--out', str(self.root / 'run' / 'gee')])]
        first = self.fingerprints(steps=steps)
        (self.repository / 'config' / 'release.json').write_text('{"features": [1]}')
        (self.repository / 'config' / 'town_b.json').write_text('{"name": "Vivec!"}')
        self.assertEqual(first, self.fingerprints(steps=steps))        # files no row names
        (self.repository / 'config' / 'town_a.json').write_text('{"name": "Balmora!"}')
        self.assertNotEqual(first, self.fingerprints(steps=steps))     # a named town file
        (self.repository / 'config' / 'town_a.json').write_text('{"name": "Balmora"}')
        (self.repository / 'config' / 'registry.json').write_text('[{"config": "town_a.json"}, {"config": "town_b.json"}]')
        second = self.fingerprints(steps=steps)
        self.assertNotEqual(first, second)                             # the registry itself
        _, data, _ = build_cache.SourceIndex(self.repository).closure(stage)
        self.assertIn('config/town_b.json', data)                      # ... and the file it now names
        (self.repository / 'config' / 'town_b.json').write_text('{"name": "Vivec"}')
        self.assertNotEqual(second, self.fingerprints(steps=steps))

    def test_closure_and_explanations(self):
        index = build_cache.SourceIndex(self.repository)
        python, data, uncertain = index.closure(self.repository / 'tools' / 'stage_a.py')
        self.assertEqual(python, {'tools/stage_a.py', 'tools/helper.py'})
        self.assertEqual(data, {'config/settings.json'})
        self.assertFalse(uncertain)
        self.assertNotIn('docs/NOTES.md', index.files)
        old = {'command': ['x'], 'sources': {'digest': '1'}, 'dependencies': {'a': '1', 'b': '2'}}
        new = {'command': ['x'], 'sources': {'digest': '2'}, 'dependencies': {'a': '1', 'b': '3'}}
        self.assertEqual(build_cache.explain(old, new), ['dependency b', 'sources'])

    def test_real_stage_closures_leave_engine_sources_to_the_engine_and_image(self):
        """An engine C edit must not invalidate the conversion stages (measured on this repository)."""
        index = build_cache.SourceIndex()
        for script in ('prepare_world_scenery.py', 'prepare_world_regions.py', 'prepare_scenery.py', 'prepare_music.py'):
            python, data, uncertain = index.closure(ROOT / 'tools' / script)
            self.assertFalse(uncertain, script)
            self.assertIn('tools/' + script, python)
            self.assertFalse([path for path in data if path.startswith('engine/aga/src/')], script)
        python, data, _ = index.closure(ROOT / 'tools' / 'build_aga.py')
        self.assertTrue([path for path in data if path.startswith('engine/aga/src/')])
        self.assertIn('tools/optimize_world_maps.py', python)   # imported inside a function


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / 'repo'
        self.data = self.root / 'data'
        self.data.mkdir()
        make_repository(self.repository)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, name, reuse_from=None, parallel=False, mode='copy', pool=None, forced=()):
        run = self.root / 'workspace' / name
        index = build_cache.SourceIndex(self.repository)
        meta = metadata()
        meta['compiler_jobs'] = 2 if parallel else 1
        meta['runtime_version'] = '0.0.0-dev1'
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            steps = build_cache.prepare(steps_for(self.repository, run, self.data), run, meta, reuse_from, mode, index,
                                        pool=pool, forced=forced)
            if parallel:
                execute_parallel(steps, run, meta, self.repository)
            else:
                build.execute(steps, run, meta)
        state = json.loads((run / 'build-state.json').read_text())
        return run, state, output.getvalue()

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_a_forced_stage_runs_again_and_the_stages_after_it_follow_their_keys(self):
        # --rebuild-stage (docs/BUILD_CACHE.md): the forced stage writes the same outputs, so the stages after it
        # are reused; nothing else runs.
        first, _, _ = self.build('first')
        second, state, _ = self.build('second', reuse_from=first, forced=['alpha'])
        cache = state['stage_cache']
        self.assertEqual(cache['forced'], ['alpha'])
        self.assertEqual(cache['not_reused']['alpha'], build_cache.FORCED_REASON)
        reused = sorted(name for name, row in cache['reused'].items() if not row.get('refused'))
        self.assertEqual(reused, ['beta', 'delta', 'gamma'])
        for name in ('beta', 'gamma', 'delta'):
            self.assertEqual(build_cache.load_manifest(second, name)['files'],
                             build_cache.load_manifest(first, name)['files'])

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_reused_outputs_are_byte_identical_to_a_fresh_build(self):
        first, state, _ = self.build('first')
        self.assertEqual(state['status'], 'passed')
        manifest = build_cache.load_manifest(first, 'alpha')
        self.assertEqual(set(manifest['files']), {'alpha/a.txt', 'alpha/deep/blob.bin', 'alpha/scratch.tmp'})
        self.assertEqual(build_cache.load_manifest(first, 'gamma')['deleted'], ['alpha/scratch.tmp'])
        second, state, printed = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
        for entry in state['steps']:
            self.assertTrue(entry['reused'].startswith('reused (fingerprint '), entry)
            self.assertIn('build_cache.py', ' '.join(entry['command']))
        self.assertIn('reused  alpha', printed)
        self.assertIn('Reused stage alpha from', (second / 'logs' / '01-alpha.log').read_text())
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        self.assertEqual(tree(second), tree(first))
        self.assertFalse((second / 'alpha' / 'scratch.tmp').exists())
        self.assertEqual((second / 'alpha' / 'c.txt').read_text(), (fresh / 'alpha' / 'c.txt').read_text())
        profile = json.loads((second / 'build-profile.json').read_text())
        self.assertEqual([row['reused']['from'] for row in profile['stages']], [str(first)] * 4)
        # A reused run is itself a reuse source, also for the parallel scheduler.
        third, state, _ = self.build('third', reuse_from=second, parallel=True)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
        self.assertEqual(tree(third), tree(fresh))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_changed_stage_and_its_dependents_rebuild(self):
        first, _, _ = self.build('first')
        (self.repository / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        second, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'gamma'])
        self.assertIn('changed: sources', state['stage_cache']['not_reused']['delta'])
        self.assertEqual((second / 'delta' / 'd.txt').read_text(), 'D:b:one\na:one\n')
        # gamma deletes alpha's scratch file in place: when gamma rebuilds, alpha's version is
        # needed but no longer exists in the old run, so alpha rebuilds too; beta is reused once
        # alpha has written the same files again (BUILD-CACHE-NO-CUTOFF-33).
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C.replace("'c:'", "'C:'"))
        second, state, _ = self.build('second-c', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['beta'])
        reasons = state['stage_cache']['not_reused']
        self.assertIn('changed: ', reasons['gamma'])
        self.assertIn('alpha/scratch.tmp was replaced later', reasons['alpha'])
        self.assertFalse((second / 'profile' / 'reuse-fallback').exists())
        self.assertTrue((second / 'alpha' / 'c.txt').read_text().startswith('C:'))
        (self.repository / 'tools' / 'helper.py').write_text(HELPER.replace("':'", "'='"))
        third, state, _ = self.build('third', reuse_from=first)
        self.assertEqual(state['stage_cache']['reused'], {})
        self.assertIn('changed: sources', state['stage_cache']['not_reused']['alpha'])
        self.assertEqual((third / 'beta' / 'b.txt').read_text(), 'b=one\na=one\n')

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_damaged_old_outputs_are_never_copied(self):
        first, _, _ = self.build('first')
        (first / 'delta' / 'd.txt').write_text('tampered')
        second, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'gamma'])
        self.assertIn('old output delta/d.txt changed or missing', state['stage_cache']['not_reused']['delta'])
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        self.assertFalse(list(second.rglob('*' + build_cache.TEMPORARY_SUFFIX)))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_damage_found_while_copying_rebuilds_or_stops(self):
        first, _, _ = self.build('first')
        run = self.root / 'workspace' / 'manual'
        (run / 'profile').mkdir(parents=True)
        index = build_cache.SourceIndex(self.repository)
        steps = steps_for(self.repository, run, self.data)
        fingerprints, components, problems, dependencies = build_cache.fingerprint_steps(steps, run, metadata(), index)
        plans, _ = build_cache.plan_reuse(steps, fingerprints, dependencies, components, problems, first)
        self.assertEqual(plans['gamma']['rebuild_hazard'], ['alpha/scratch.tmp'])
        self.assertEqual(plans['delta']['rebuild_hazard_count'], 0)
        (run / 'profile' / build_cache.PLAN_NAME).write_text(json.dumps(plans))
        # The old run is damaged after planning: delta can still rebuild itself ...
        (first / 'delta' / 'd.txt').write_text('tampered')
        (run / 'beta').mkdir()
        (run / 'beta' / 'b.txt').write_text('b:one\na:one\n')
        target = run / 'delta'
        rebuild = [sys.executable, '-c',
                   'import sys; from pathlib import Path; p = Path(sys.argv[1]); p.mkdir(); (p / "d.txt").write_text("rebuilt")',
                   str(target)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_cache.apply_stage(run, 'delta', rebuild), 0)
        self.assertEqual((run / 'delta' / 'd.txt').read_text(), 'rebuilt')
        self.assertIn('SHA-256', (run / 'profile' / 'reuse-fallback' / 'delta.txt').read_text())
        self.assertFalse(list(run.rglob('*' + build_cache.TEMPORARY_SUFFIX)))
        # ... but gamma, whose replaced file alpha left out, must stop the build instead.
        (run / 'alpha').mkdir()
        (first / 'alpha' / 'c.txt').write_text('tampered')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(build_cache.apply_stage(run, 'gamma', ['false']), 1)
        self.assertIn('cannot be rebuilt in this run either', output.getvalue())

    @unittest.skipUnless(MANIFESTS and hasattr(os, 'geteuid') and os.geteuid() != 0, 'hard links need a non-root POSIX user')
    def test_hard_links_are_verified_and_read_only(self):
        first, _, _ = self.build('first')
        second, state, _ = self.build('second', reuse_from=first, mode='hardlink')
        self.assertEqual(state['stage_cache']['reuse_mode'], 'hardlink')
        blob = second / 'alpha' / 'deep' / 'blob.bin'
        self.assertEqual(os.stat(blob).st_ino, os.stat(first / 'alpha' / 'deep' / 'blob.bin').st_ino)
        with self.assertRaises(PermissionError):
            blob.open('r+b')

    @unittest.skipUnless(MANIFESTS and hasattr(os, 'geteuid') and os.geteuid() != 0, 'hard links need a non-root POSIX user')
    def test_pool_mode_links_reused_files_to_one_pooled_object(self):
        import storage_pool
        pool = self.root / 'workspace' / 'pool'
        first, _, _ = self.build('first')
        second, state, _ = self.build('second', reuse_from=first, mode='pool', pool=pool)
        third, third_state, _ = self.build('third', reuse_from=second, mode='pool', pool=pool)
        self.assertEqual(state['stage_cache']['reuse_mode'], 'pool')
        relative = Path('alpha') / 'deep' / 'blob.bin'
        digest = build_cache.sha256_file(first / relative)
        blob = storage_pool.object_path(pool, digest)
        inodes = {os.stat(path).st_ino for path in (first / relative, second / relative, third / relative, blob)}
        self.assertEqual(len(inodes), 1, [(str(path), os.stat(path).st_ino, os.stat(path).st_nlink, os.stat(path).st_dev,
                                          oct(os.stat(path).st_mode)) for path in (first / relative, second / relative,
                                                                                 third / relative, blob)]
                         + [third_state['stage_cache'].get('not_reused')])  # stored once, never copied
        self.assertIn('links to the storage pool', (second / 'logs' / '01-alpha.log').read_text())
        with self.assertRaises(PermissionError):
            (third / relative).open('r+b')
        fresh, _, _ = self.build('fresh')
        self.assertEqual(build_cache.sha256_file(third / relative), build_cache.sha256_file(fresh / relative))

    def test_pool_mode_needs_a_pool_folder(self):
        with self.assertRaises(ValueError):
            build_cache.prepare([], self.root / 'workspace' / 'nopool', metadata(), self.root / 'other', 'pool',
                                build_cache.SourceIndex(self.repository))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_concurrent_stages_touching_one_path_are_never_reused(self):
        run = self.root / 'workspace' / 'parallel'
        shared = 'import sys, time\nfrom pathlib import Path\np = Path(sys.argv[1]); p.mkdir(exist_ok=True)\n' \
                 'time.sleep(.3); (p / sys.argv[2]).write_text(sys.argv[2]); (p / "shared.txt").write_text(sys.argv[2])\ntime.sleep(.3)\n'
        steps = [('media', [sys.executable, '-c', shared, str(run / 'together'), 'media']),
                 ('music', [sys.executable, '-c', shared, str(run / 'together'), 'music']),
                 ('world-survey', [sys.executable, '-c', shared, str(run / 'alone'), 'survey'])]
        meta = metadata()
        meta['compiler_jobs'] = 3
        with contextlib.redirect_stdout(io.StringIO()):
            steps = build_cache.prepare(steps, run, meta, index=build_cache.SourceIndex(self.repository))
            execute_parallel(steps, run, meta, self.repository)
        index = json.loads((run / 'profile' / 'manifests' / 'index.json').read_text())
        self.assertFalse(index['media']['reusable'])
        self.assertFalse(index['music']['reusable'])
        self.assertIn('while', index['media']['reasons'][0])
        self.assertTrue(index['world-survey']['reusable'])

    def test_reuse_temporaries_of_declared_roots_are_not_undeclared_outputs(self):
        # BUILD-REUSE-TMP-UNDECLARED-33: a reused stage's copy (voice-lookup.json + TEMPORARY_SUFFIX) appeared in
        # the run folder while setup ran, and setup became non-reusable.
        run = self.root / 'workspace' / 'recorder'
        run.mkdir(parents=True)
        steps = [('setup', [sys.executable, 'tools/x.py', str(run / 'setup.json')]),
                 ('dialogue-lookup', [sys.executable, 'tools/y.py', str(run / 'voice-lookup.json')])]
        recorder = build_cache.Recorder(run, steps, {})
        recorder.before('setup', steps[0][1])
        (run / 'setup.json').write_text('{}')
        (run / ('voice-lookup.json' + build_cache.TEMPORARY_SUFFIX)).write_text('partial copy')
        self.assertTrue(recorder.after('setup', {})['reusable'])
        recorder.before('setup', steps[0][1])
        (run / 'stray.txt').write_text('x')
        (run / ('stray.txt' + build_cache.TEMPORARY_SUFFIX)).write_text('x')
        manifest = recorder.after('setup', {})
        self.assertFalse(manifest['reusable'])
        self.assertIn('stray.txt', manifest['reasons'][0])

    def test_the_builder_scratch_folder_is_not_an_undeclared_output(self):
        # BUILD-REUSE-SCRATCH-UNDECLARED-33: RUN/scratch (AMIWIND_SCRATCH for every stage) appeared while the first
        # stages ran; they became non-reusable and the rc1c rerun reused 1 of 33 stages.
        from build_scratch import ENV as SCRATCH_ENV, stage_environment
        run = self.root / 'workspace' / 'scratch-run'
        run.mkdir(parents=True)
        with patch.dict(os.environ, {SCRATCH_ENV: ''}):
            os.environ.pop(SCRATCH_ENV)
            scratch = Path(stage_environment(run)[SCRATCH_ENV])
        self.assertEqual(scratch.parent, run)
        self.assertIn(scratch.name, build_cache.RUN_PRIVATE)
        steps = [('terrain', [sys.executable, 'tools/x.py', str(run / 'terrain.json')])]
        recorder = build_cache.Recorder(run, steps, {})
        recorder.before('terrain', steps[0][1])
        (run / 'terrain.json').write_text('{}')
        (scratch / 'scratch-1234').mkdir(parents=True)
        manifest = recorder.after('terrain', {})
        self.assertTrue(manifest['reusable'], manifest['reasons'])
        self.assertEqual(list(manifest['files']), ['terrain.json'])

    def test_old_records_refused_only_for_scratch_are_reusable(self):
        # Runs recorded before the fix (rc1c, rc1d) marked stages non-reusable only for RUN/scratch: requalified
        # when read; any other reason still refuses.
        run = self.root / 'workspace' / 'old-record'
        folder = run / 'profile' / 'manifests'
        folder.mkdir(parents=True)
        base = {'schema': build_cache.MANIFEST_SCHEMA, 'stage': 'terrain', 'status': 'complete', 'fingerprint': 'f',
                'files': {'terrain.json': {'size': 2, 'sha256': 'a' * 64, 'mode': 420}}, 'links': {}, 'deleted': []}
        cases = {'scratch-only': ([build_cache.SCRATCH_ONLY_REASON], True),
                 'scratch-and-more': (['created run-folder entries outside every declared stage path: scratch, stray'],
                                      False),
                 'two-reasons': ([build_cache.SCRATCH_ONLY_REASON, 'ran 1 Python files from outside the checkout'],
                                 False),
                 'other': (['changed x (and 0 more) while y ran; outputs cannot be attributed'], False)}
        for name, (reasons, expected) in cases.items():
            (folder / f'{name}.json').write_text(json.dumps(dict(base, stage=name, reusable=False, reasons=reasons)))
            manifest = build_cache.load_manifest(run, name)
            self.assertIs(manifest['reusable'], expected, name)
            self.assertEqual(manifest['files'], base['files'])
        (folder / 'fresh.json').write_text(json.dumps(dict(base, reusable=True, reasons=[])))
        self.assertNotIn('requalified', build_cache.load_manifest(run, 'fresh'))

    @unittest.skipUnless(MANIFESTS, 'the read trace runs with the stage wrapper on POSIX')
    def test_read_trace_catches_an_input_the_fingerprint_missed(self):
        first, state, _ = self.build('first')
        reads = build_cache.load_manifest(first, 'alpha')['reads']
        self.assertTrue(reads['traced'])
        self.assertEqual((reads['misses'], reads['uncovered'], reads['outside']), ([], [], []))
        self.assertIn('config/settings.json', (first / 'profile' / 'reads' / '01-alpha.txt').read_text().split())
        run = self.root / 'workspace' / 'hidden'
        steps = [('hidden', [sys.executable, str(self.repository / 'tools' / 'stage_hidden.py'), '--out', str(run / 'hidden')])]
        _, data, _ = build_cache.SourceIndex(self.repository).closure(self.repository / 'tools' / 'stage_hidden.py')
        self.assertNotIn('config/hidden.json', data)  # invisible to the static scan ...
        meta = metadata()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            steps = build_cache.prepare(steps, run, meta, index=build_cache.SourceIndex(self.repository))
            build.execute(steps, run, meta)
        manifest = build_cache.load_manifest(run, 'hidden')
        self.assertFalse(manifest['reusable'])            # ... so the run is never a reuse source for it
        self.assertEqual(manifest['reads']['misses'], ['config/hidden.json'])
        self.assertIn('left out', manifest['reasons'][0])
        self.assertIn('register a bug', output.getvalue())
        with patch.dict(os.environ, {build_cache.TRACE_ENV: 'off'}), contextlib.redirect_stdout(io.StringIO()):
            off = self.root / 'workspace' / 'untraced'
            steps = build_cache.prepare([('hidden', [sys.executable, str(self.repository / 'tools' / 'stage_hidden.py'),
                                                     '--out', str(off / 'hidden')])], off, meta,
                                        index=build_cache.SourceIndex(self.repository))
            build.execute(steps, off, meta)
        self.assertIsNone(build_cache.load_manifest(off, 'hidden')['reads'])

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_unreached_edit_reuses_every_stage_byte_identically(self):
        """BUILD-CACHE-OVERBROAD-33 (d): an edit outside every stage's reached code reuses all stages, and the
        reused outputs equal a fresh build's byte for byte; a reached edit still rebuilds (c)."""
        first, _, _ = self.build('first')
        (self.repository / 'tools' / 'helper.py').write_text(HELPER.replace('return heavy.VALUE', 'return 2'))
        second, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        (self.repository / 'tools' / 'helper.py').write_text(HELPER.replace("name + ':'", "name + '='"))
        third, state, _ = self.build('third', reuse_from=second)
        self.assertFalse({'alpha', 'beta'} & set(state['stage_cache']['reused']))
        self.assertIn('changed: sources (tools/helper.py)', state['stage_cache']['not_reused']['alpha'])
        # gamma's own parts are unchanged: planned as reused, run because beta's output changed.
        self.assertTrue((third / 'profile' / 'reuse-fallback' / 'gamma.txt').is_file())
        self.assertEqual((third / 'beta' / 'b.txt').read_text(), 'b=one\na=one\n')

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_rebuilt_stage_with_unchanged_outputs_keeps_later_stages(self):
        """BUILD-CACHE-NO-CUTOFF-33: a stage whose code changed but whose outputs come out the same no longer
        rebuilds every stage after it; outputs that do change still do."""
        first, _, _ = self.build('first')
        stage_a = self.repository / 'tools' / 'stage_a.py'
        stage_a.write_text(STAGE_A.replace("    out = Path(", "    # same outputs, new code\n    out = Path("))
        second, state, printed = self.build('second', reuse_from=first)
        cache = state['stage_cache']
        self.assertIn('changed: sources', cache['not_reused']['alpha'])
        self.assertEqual(sorted(cache['reused']), ['beta', 'delta', 'gamma'])
        plan = json.loads((second / 'profile' / build_cache.PLAN_NAME).read_text())
        self.assertTrue(plan['beta']['conditional'])
        self.assertEqual(plan['gamma']['rebuilt_ancestors'], ['alpha'])
        self.assertFalse((second / 'profile' / 'reuse-fallback').exists())
        self.assertIn('ran again with outputs identical', (second / 'logs' / '02-beta.log').read_text())
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        self.assertEqual((second / 'alpha' / 'c.txt').read_text(), (fresh / 'alpha' / 'c.txt').read_text())
        self.assertFalse((second / 'alpha' / 'scratch.tmp').exists())
        # The reused run is a source again, and a real output change rebuilds what follows.
        stage_a.write_text(STAGE_A.replace("payload('a')", "payload('A')"))
        third, state, _ = self.build('third', reuse_from=second)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['beta', 'delta', 'gamma'])
        fallback = third / 'profile' / 'reuse-fallback'
        self.assertEqual(sorted(path.stem for path in fallback.glob('*.txt')), ['beta', 'delta', 'gamma'])
        self.assertIn('outputs differ', (fallback / 'beta.txt').read_text())
        self.assertEqual((third / 'beta' / 'b.txt').read_text(), 'b:one\nA:one\n')
        self.assertEqual((third / 'alpha' / 'c.txt').read_text(), 'c:b:one\nA:one\n')
        clean, _, _ = self.build('clean')
        self.assertEqual(tree(third), tree(clean))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_reuse_preflight_stops_an_unexplained_rebuild_before_any_stage_runs(self):
        """BUILD-REUSE-KEYS-TOO-BROAD-35: with --reuse-from, a stage rebuilt for a source key change that no changed
        file explains stops the build before any stage runs, unless --accept-rebuild; --reuse-plan says the same,
        read only. A real edit is explained and named."""
        first, _, _ = self.build('first')
        index = build_cache.SourceIndex(self.repository)
        state_path = first / 'build-state.json'
        state = json.loads(state_path.read_text())
        state['source_sha256'] = {path: index.files[path] for path in index.files}
        details_path = first / 'profile' / 'fingerprints.json'
        details = json.loads(details_path.read_text())
        # A key that changed with no file changed: the recorded per-file part of alpha differs from today's.
        details['alpha']['sources']['by_file']['tools/stage_a.py'] = 'units:recorded-differently'
        state['stage_cache']['fingerprints']['alpha'] = build_cache.digest_json(details['alpha'])
        state_path.write_text(json.dumps(state))
        details_path.write_text(json.dumps(details))
        with self.assertRaisesRegex(ValueError, 'Reuse preflight: 1 stage'):
            with contextlib.redirect_stdout(io.StringIO()):
                build_cache.prepare(steps_for(self.repository, self.root / 'workspace' / 'refused', self.data),
                                    self.root / 'workspace' / 'refused', metadata(), first, 'copy', index)
        self.assertFalse((self.root / 'workspace' / 'refused').exists())
        result = build_cache.predict_preflight(first, root=self.repository)
        self.assertEqual([row['stage'] for row in result['rows'] if row['class'] == 'UNEXPECTED'], ['alpha'])
        run = self.root / 'workspace' / 'accepted'
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            build_cache.prepare(steps_for(self.repository, run, self.data), run, metadata(), first, 'copy', index,
                                accept_rebuild=True)
        self.assertIn('accepted with --accept-rebuild', output.getvalue())
        # A real edit: explained by the source diff, which names the file; the stages after it stay reusable.
        details['alpha']['sources']['by_file']['tools/stage_a.py'] = index.selection(
            self.repository / 'tools' / 'stage_a.py')[0]['tools/stage_a.py']
        state['stage_cache']['fingerprints']['alpha'] = build_cache.digest_json(details['alpha'])
        state_path.write_text(json.dumps(state))
        details_path.write_text(json.dumps(details))
        (self.repository / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        result = build_cache.predict_preflight(first, root=self.repository)
        self.assertEqual(result['unexpected'], 0)
        self.assertEqual([(row['stage'], row['diff_files']) for row in result['rows']], [('delta', ['tools/stage_d.py'])])
        self.assertEqual(result['reused'], 3)

    @unittest.skipUnless(MANIFESTS and hasattr(sys, 'monitoring'), 'the call trace needs POSIX and Python 3.12+')
    def test_call_trace_catches_a_function_the_fingerprint_missed(self):
        """Scope 'units': a function that ran although no static scan reached it makes the outputs not reusable."""
        first, _, _ = self.build('first')
        reads = build_cache.load_manifest(first, 'alpha')['reads']
        self.assertEqual(reads['call_misses'], [])
        self.assertGreater(reads['calls'], 0)
        self.assertIn('@tools/helper.py\tpayload', (first / 'profile' / 'reads' / '01-alpha.txt').read_text().splitlines())
        run = self.root / 'workspace' / 'calls'
        stage = self.repository / 'tools' / 'stage_call.py'
        self.assertNotIn('unused', build_cache.SourceIndex(self.repository).reached_units(stage).get('tools/helper.py', ()))
        meta = metadata()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            steps = build_cache.prepare([('calls', [sys.executable, str(stage), '--out', str(run / 'calls')])], run, meta,
                                        index=build_cache.SourceIndex(self.repository))
            build.execute(steps, run, meta)
        manifest = build_cache.load_manifest(run, 'calls')
        self.assertFalse(manifest['reusable'])
        self.assertEqual(manifest['reads']['call_misses'], ['tools/helper.py:unused'])
        self.assertIn('functions its fingerprint left out', ' '.join(manifest['reasons']))
        self.assertIn('register a bug', output.getvalue())
        self.assertEqual(build_cache.check_calls(['@tools/helper.py\tunused', '@tools/helper.py\t<module>',
                                                  '@tools/helper.py\tpayload', '@out/run/x.py\tf'],
                                                 {'tools/helper.py': ['<top>', 'payload']},
                                                 {'tools/helper.py': ['payload', 'unused']}, 'out/run'),
                         ['tools/helper.py:unused'])

    @unittest.skipUnless(MANIFESTS, 'the read trace runs with the stage wrapper on POSIX')
    def test_reuse_chain_with_another_checkout_on_pythonpath(self):
        """Gate 450: with PYTHONPATH naming another checkout (as the gate and the builder image do),
        `build_cache.py apply` of a reused stage loads the builder's instrumentation from there;
        that must not stop the reused run from being a reuse source. Stage code from outside the
        checkout still must."""
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'extlib.py').write_text('VALUE = "x"\n')
        with patch.dict(os.environ, {'PYTHONPATH': os.pathsep.join([str(ROOT / 'src'), str(ROOT / 'tools'), str(outside)])}):
            first, _, _ = self.build('first')
            second, state, _ = self.build('second', reuse_from=first)
            self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
            third, state, _ = self.build('third', reuse_from=second, parallel=True)
            self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
            self.assertEqual(tree(third), tree(first))
            (self.repository / 'tools' / 'stage_d.py').write_text('import extlib\n' + STAGE_D)
            fourth, state, _ = self.build('fourth', reuse_from=first)
        manifest = build_cache.load_manifest(fourth, 'delta')
        self.assertFalse(manifest['reusable'])
        self.assertEqual([Path(path).name for path in manifest['reads']['outside']], ['extlib.py'])

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_old_schema_runs_and_predict(self):
        first, _, _ = self.build('first')
        self.assertEqual(build_cache.predict(first, root=self.repository), {name: None for name in ('alpha', 'beta', 'gamma', 'delta')})
        (self.repository / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        predicted = build_cache.predict(first, root=self.repository)
        self.assertEqual([name for name, reason in predicted.items() if reason is None], ['alpha', 'beta', 'gamma'])
        self.assertIn('changed: sources', predicted['delta'])
        state = json.loads((first / 'build-state.json').read_text())
        state['stage_cache']['schema'] = 'amiwind-stage-cache-v1'
        (first / 'build-state.json').write_text(json.dumps(state))
        _, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(state['stage_cache']['reused'], {})
        self.assertIn('amiwind-stage-cache-v1 fingerprints', state['stage_cache']['not_reused']['alpha'])

    def test_release_versions_refuse_reuse(self):
        with patch.dict(os.environ):  # build.main sets AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
            self._release_versions_refuse_reuse()

    def _release_versions_refuse_reuse(self):
        for version in ('0.0.32', '0.0.32-rc1', '1.0.0', '0.0.33'):
            with self.assertRaisesRegex(ValueError, 'from scratch'):
                build_cache.require_reuse_allowed(version)
            build_cache.require_reuse_allowed(version, allow_release=True)
        build_cache.require_reuse_allowed('0.0.32-dev1')
        with patch.object(build, 'VERSION', '0.0.32-rc1'), contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stop:
            build.main(['--stage', 'terrain', '--data-files', str(self.data), '--reuse-from', str(self.root),
                        '--workspace', str(self.root / 'workspace')])
        self.assertEqual(stop.exception.code, 1)
        with contextlib.redirect_stderr(io.StringIO()) as error, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit):
            build.main(['--dry-run', '--reuse-from', str(self.root)])
        self.assertIn('--reuse-from needs', error.getvalue())

    def test_unknown_or_unfinished_old_runs(self):
        with self.assertRaisesRegex(ValueError, 'no build-state.json'):
            self.build('first', reuse_from=self.root / 'missing')
        if not MANIFESTS:
            return
        first, _, _ = self.build('first-real')
        state = json.loads((first / 'build-state.json').read_text())
        state['steps'][1]['status'] = 'failed'
        (first / 'build-state.json').write_text(json.dumps(state))
        (first / 'profile' / 'manifests' / 'alpha.json').unlink()
        _, state, _ = self.build('second', reuse_from=first)
        self.assertFalse({'alpha', 'beta'} & set(state['stage_cache']['reused']))
        self.assertIn('no output manifest', state['stage_cache']['not_reused']['alpha'])
        self.assertIn('not passed', state['stage_cache']['not_reused']['beta'])

    def test_engine_and_image_always_run(self):
        self.assertEqual(set(build_cache.NON_REUSABLE), {'engine', 'image', 'dry-run-image'})
        roots = build_cache.output_roots(['python', '/w/run/a/x.bin', '/w/run/a', '/w/run/logs/1.log', '/w/run/b/c'], Path('/w/run'))
        self.assertEqual(roots, ['a', 'b/c'])
        self.assertEqual(build_cache.normalize_command(['p', '--out', '/w/run/x', '--jobs', '12'], Path('/w/run')),
                         ['p', '--out', '{RUN}/x', '--jobs', '{JOBS}'])


class StageKeyCoverageTests(unittest.TestCase):
    """BUILD-KEY-OVERBROAD-33: an import search path entry (sys.path.insert(0, str(ROOT / 'tools'))) named
    every non-Python file under tools/, so a new bug page (tools/release-files.json) rebuilt interior,
    census, harvest, chim and chim-town. The key stays complete: a computed read under tools/ still counts."""

    IDIOMS = (
        "import sys\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n"
        "sys.path.insert(0, str(ROOT / 'tools'))\n"
        "sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]\n"
        "for p in (ROOT / 'tools', ROOT / 'src'):\n"
        "    while str(p) in sys.path:\n"
        "        sys.path.remove(str(p))\n"
        "    sys.path.insert(0, str(p))\n"
        "def main():\n    return 1\n"
        "main()\n")

    def repository(self, root, extra=''):
        (root / 'tools').mkdir(parents=True)
        (root / 'src').mkdir()
        (root / 'tools' / 'stage.py').write_text(self.IDIOMS + extra)
        (root / 'tools' / 'release-files.json').write_text('[]\n')
        (root / 'tools' / 'table.json').write_text('{}\n')
        (root / 'src' / 'notes.json').write_text('{}\n')
        return build_cache.SourceIndex(root)

    def test_import_search_paths_are_not_data_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            index = self.repository(Path(temp))
            _, data, uncertain = index.closure(Path(temp) / 'tools' / 'stage.py')
            self.assertFalse(uncertain)
            self.assertEqual(data, set())

    def test_a_computed_read_under_tools_still_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            extra = "def load(name):\n    return (ROOT / 'tools' / name).read_text()\nload('table.json')\n"
            index = self.repository(Path(temp), extra)
            _, data, _ = index.closure(Path(temp) / 'tools' / 'stage.py')
            self.assertIn('tools/table.json', data)
            self.assertIn('tools/release-files.json', data)   # an open-ended read of the folder: all of it

    def test_no_builder_stage_keys_the_release_file_list_or_the_tracker(self):
        """Editing tools/release-files.json or adding a bug page rebuilds no stage (the real repository)."""
        import re
        scripts = sorted(set(re.findall(r"tool\([\"']([a-z_]+\.py)", (ROOT / 'tools' / 'build.py').read_text())))
        self.assertIn('prepare_interior.py', scripts)
        index = build_cache.SourceIndex(ROOT)
        for script in scripts:
            if script == 'build_aga.py':
                continue  # engine (never reused: BUILD-ENGINE-KEY-SDK-33) and image (always assembled)
            _, data, _ = index.closure(ROOT / 'tools' / script)
            tracker = sorted(path for path in data if path == 'tools/release-files.json' or path.startswith('docs/bugs/')
                             or path in ('docs/BUGS.md', 'docs/BUG_JOURNAL.md'))
            self.assertEqual(tracker, [], script)


class WriteAttributionTests(unittest.TestCase):
    """BUILD-REUSE-ATTRIBUTION-33: two stages ran at the same time (character and chim-town); both saw
    intro-scene/id1/character/*.awh change and both were refused. The read trace now records each stage's
    writes into the run folder, and a file only one of them wrote is that stage's output."""

    def run_pair(self, run, character_writes, town_writes):
        steps = [('character', [sys.executable, 'tools/x.py', '--scene', str(run / 'scene')]),
                 ('town', [sys.executable, 'tools/y.py', '--scene', str(run / 'scene'), '--out', str(run / 'town')])]
        (run / 'scene').mkdir(parents=True)
        recorder = build_cache.Recorder(run, steps, {})
        recorder.traced = True
        recorder.before('character', steps[0][1])
        recorder.before('town', steps[1][1])
        import time
        time.sleep(0.01)  # windows are kept in milliseconds: make the two runs overlap on a fast host
        (run / 'scene' / 'h106.awh').write_bytes(b'head')
        (run / 'town').mkdir()
        (run / 'town' / 'entities.json').write_text('{}')
        traces = {}
        for name, writes in (('character', character_writes), ('town', town_writes)):
            if writes is None:
                traces[name] = None
                continue
            traces[name] = run.parent / f'{name}.txt'
            traces[name].write_text(''.join('>' + path + '\n' for path in writes) + 'tools/x.py\n')
        recorder.after('town', {}, traces['town'])
        recorder.after('character', {}, traces['character'])
        recorder.close({'status': 'passed'})
        return build_cache.load_manifest(run, 'character'), build_cache.load_manifest(run, 'town')

    def test_the_traced_writer_owns_the_file(self):
        with tempfile.TemporaryDirectory() as temp:
            character, town = self.run_pair(Path(temp) / 'run', ['scene/h106.awh'], ['town/entities.json'])
            self.assertTrue(character['reusable'], character['reasons'])
            self.assertTrue(town['reusable'], town['reasons'])
            self.assertIn('scene/h106.awh', character['files'])
            self.assertNotIn('scene/h106.awh', town['files'])
            self.assertIn('town/entities.json', town['files'])
            self.assertEqual(town['attributed'][0]['stage'], 'character')

    def test_unknown_or_shared_writers_still_refuse_both(self):
        for character_writes, town_writes in ((None, ['town/entities.json']),            # not traced
                                              ([], ['town/entities.json']),              # a native tool wrote it
                                              (['scene/h106.awh'], ['scene/h106.awh'])):  # both wrote it
            with tempfile.TemporaryDirectory() as temp:
                character, town = self.run_pair(Path(temp) / 'run', character_writes, town_writes)
                self.assertFalse(character['reusable'])
                self.assertFalse(town['reusable'])
                self.assertIn('outputs cannot be attributed', town['reasons'][-1])

    @unittest.skipUnless(MANIFESTS, 'the read trace runs with the stage wrapper on POSIX')
    def test_the_trace_hook_records_run_folder_writes(self):
        """The generated hook, run in a child process, lists opens for writing, renames and removals in the run."""
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            (run / 'profile').mkdir(parents=True)
            self.assertTrue(build_cache.write_trace_hook(run, ROOT))
            target = run / 'profile' / build_profile.READS_FOLDER / 'stage.txt'
            code = ("import os\nfrom pathlib import Path\nr = Path(os.environ['R'])\n"
                    "(r / 'a.txt').write_text('x')\nopen(r / 'b.tmp', 'wb').close()\nos.replace(r / 'b.tmp', r / 'b.txt')\n"
                    "(r / 'a.txt').read_text()\nos.remove(r / 'a.txt')\n"
                    "(r / 'x.log').write_text('t')\n(r / 'x.log').read_text()\n")
            env = dict(os.environ, R=str(run), PYTHONPATH=str(run / 'profile' / build_profile.TRACE_HOOK_FOLDER),
                       **{build_profile.TRACE_ENV: str(target)})
            subprocess.run([sys.executable, '-c', code], env=env, check=True)
            recorder = build_cache.Recorder.__new__(build_cache.Recorder)
            recorder.traced = True
            self.assertEqual(recorder.traced_writes(target), {'a.txt', 'b.tmp', 'b.txt', 'x.log'})
            self.assertEqual(recorder.diagnostic_reads(target), ['x.log'])


class DiagnosticOutputTests(unittest.TestCase):
    """BUILD-OUTPUTS-NOT-REPRODUCIBLE-33: tool logs ("0.306 seconds elapsed") and timing reports made a rerun
    stage's outputs differ, which refused every stage after it. They are diagnostics: not compared, and no stage
    may read one."""

    def manifests(self, run, old, new_files, old_files):
        for folder, files in ((run, new_files), (old, old_files)):
            target = folder / 'profile' / 'manifests'
            target.mkdir(parents=True)
            (folder / 'build-state.json').write_text('{}')
            (target / 'census.json').write_text(json.dumps({
                'schema': build_cache.MANIFEST_SCHEMA, 'stage': 'census', 'status': 'complete', 'reusable': True,
                'reasons': [], 'files': {k: {'size': 1, 'sha256': v, 'mode': 420} for k, v in files.items()},
                'links': {}, 'deleted': [], 'directories': [], 'deleted_directories': []}))

    def test_outputs_that_differ_only_in_diagnostics_are_the_same(self):
        same = {'scene/census.txt': 'a' * 64}
        cases = (({'scene/light.log': 'b' * 64}, {'scene/light.log': 'c' * 64}, True),
                 ({'chim-world/chim-stats.json': 'b' * 64}, {'chim-world/chim-stats.json': 'c' * 64}, True),
                 ({'scene/light.log': 'b' * 64}, {}, True),
                 ({'scene/table.json': 'b' * 64}, {'scene/table.json': 'c' * 64}, False))
        for new_extra, old_extra, expected in cases:
            with tempfile.TemporaryDirectory() as temp:
                run, old = Path(temp) / 'new', Path(temp) / 'old'
                self.manifests(run, old, dict(same, **new_extra), dict(same, **old_extra))
                self.assertIs(build_cache.same_outputs(run, old, 'census'), expected, new_extra)

    def test_a_stage_that_reads_another_stages_diagnostic_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            steps = [('reader', [sys.executable, 'tools/x.py', '--scene', str(run / 'scene')])]
            (run / 'scene').mkdir(parents=True)
            recorder = build_cache.Recorder(run, steps, {})
            recorder.traced = True
            recorder.before('reader', steps[0][1])
            (run / 'scene' / 'out.txt').write_text('x')
            trace = Path(temp) / 'reads.txt'
            trace.write_text('>scene/out.txt\n<scene/own.log\n<other/compile.log\n')
            (run / 'scene' / 'own.log').write_text('mine')
            manifest = recorder.after('reader', {}, trace)
            self.assertFalse(manifest['reusable'])
            self.assertIn('read build diagnostics written by other stages', manifest['reasons'][-1])
            self.assertIn('other/compile.log', manifest['reasons'][-1])
            self.assertNotIn('own.log', manifest['reasons'][-1])

    def test_no_repository_code_reads_a_log_file(self):
        """Static half of the rule (the stage trace is the run-time half): every '.log' literal in tools/ is in a
        write, a removal, a message, or one of the reviewed uses below (none reads a stage's log)."""
        import re
        writes = re.compile(r"""open\([^)]*['"](w|a|ab|wb|w\+|x)['"]|\.open\(['"](w|a|ab|wb)['"]|write_text|write_bytes|"""
                            r"""stdout=|stderr=|unlink|help=|print\(|^\s*#|Error\(""")
        reviewed = {  # path: why it is not a stage reading another stage's log
            'tools/build.py': 'the builder names its own per-stage log under RUN/logs (run-private)',
            'tools/build_parallel.py': 'the scheduler names its own per-stage log under RUN/logs (run-private)',
            'tools/build_summary.py': 'the summary reads the engine log under RUN/logs (run-private) for warnings',
            'tools/build_cache.py': 'the diagnostic rule itself',
            'tools/build_aga.py': 'names the engine runtime log on the Amiga disk',
            'tools/prepare_world_regions.py': 'a region unit cache copy of its own logs',
            'tools/build_docker.py': 'host-side image build log', 'tools/run_docker.py': 'host-side logs',
            'tools/fsuae_headless_probe.py': 'emulator probe logs', 'tools/package_opening.py': 'opening package',
            'tools/profile_demo.py': 'demo profiler', 'tools/capture_opening.py': 'opening capture',
            'tools/run_tests.py': 'test runner log', 'tools/world_estimate_sample.py': 'estimate sample tool logs',
            'tools/chimport.py': 'the island conversion tool (not a builder stage) quotes a failed cell process log'}
        found = []
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            relative = path.relative_to(ROOT).as_posix()
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if re.search(r"""\.log['"]""", line) and not writes.search(line) and relative not in reviewed:
                    found.append(f'{relative}:{number}: {line.strip()}')
        self.assertEqual(found, [])


class ApplyTraceTests(unittest.TestCase):
    def test_storage_pool_loaded_by_the_reuse_step_is_not_outside_code(self):
        """The pool-mode reuse step loads tools/storage_pool.py; a third run must still reuse the second."""
        _, _, outside = build_cache.check_reads(['!/elsewhere/tools/storage_pool.py',
                                                 '!/elsewhere/tools/__pycache__/storage_pool.cpython-312.pyc',
                                                 '!/elsewhere/tools/converter.py'], None, set(), '/repo')
        self.assertEqual(sorted(outside), ['/elsewhere/tools/converter.py'])


if __name__ == '__main__':
    unittest.main()
