# SPDX-License-Identifier: GPL-3.0-only
"""A pass is a pass (BUILD-STAIR-PASS-NOT-KEPT-41): a CHIM frame's stair walk that passed is kept with its SHA-256
key, outcome and provenance and reused while the key is unchanged, whatever the rest of the build that walked it
did; a failed walk is not reused as a pass; release candidates and finals keep the check-mark rule. The walker's
code in the key is the walk and the stair rule (chim.collision.STAIR_WALK_CODE), not the collision compilers whose
output the key already holds as the frame's collision lumps: an edit to a compiler, or to the CHIM_VERSION label,
keeps every key; an edit to the walk changes it."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import collision  # noqa: E402

RUN = '2026_10_16_v0.0.42-dev1_full_abc1234'


class PassIsAPass(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        for name in ('AMIWIND_STAIR_WALK_REUSE', 'AMIWIND_RUN_CHIM_VERSION', 'AMIWIND_AW_REQUEST'):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_PASS_CACHE=str(Path(self.tmp.name) / 'cache'), AMIWIND_STAIR_WALK_CACHE='cached',
                          AMIWIND_STAIR_WALK_SAMPLE='0', AMIWIND_RUN_NAME=RUN, AMIWIND_RUN_COMMIT='abc1234',
                          AMIWIND_RUN_VERSION='0.0.42-dev1', AMIWIND_STAIR_WALK_KEY='frame', AMIWIND_STAIR_WALK='all', AMIWIND_STAIR_WATCH='off')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def world(self, name, fill=False):
        from test_chim_stairs import world_of
        out = Path(self.tmp.name) / name
        out.mkdir()
        world_of(out, fill)
        return out

    def gate(self, out):
        from chim.validate import Failures, load_world
        world = load_world(out, Failures())
        collision._STAIR_CACHE.clear()
        return collision.stair_gate(out, world[5], 1, models=world[4])

    def records(self):
        found = []
        for path in (Path(os.environ['AMIWIND_PASS_CACHE']) / 'stair-walk').rglob('*.json'):
            found.append(json.loads(path.read_text(encoding='utf-8'))['row']['record'])
        return found

    def test_a_passed_walk_is_reused_after_its_build_failed(self):
        first = self.gate(self.world('a'))
        self.assertEqual((first['status'], first['pass_cache']['walked']), ('passed', 1))
        # the build failed later (nothing promoted): the next run takes the frame's pass, walking nothing
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked again')):
            again = self.gate(self.world('b'))
        cache = again['pass_cache']
        self.assertEqual((cache['reused'], cache['walked'], cache['reused_passes'], cache['reuse_rule']),
                         (1, 0, 1, 'passes'))
        how = list(cache['frames'].values())[0]
        self.assertTrue(how.startswith('reused pass from %s (0.0.42-dev1, abc1234, ' % RUN), how)
        # the reused pass is listed for the promotion: a passed build of this run marks it (BUILD-CHIM-STAIR-NO-REUSE-42)
        [listed] = cache['reused_records']
        [record] = self.records()
        self.assertEqual(listed['record_sha256'], record['record_sha256'])
        self.assertEqual(first['pass_cache']['reused_records'], [])
        strip = lambda r: {k: v for k, v in r.items() if k != 'pass_cache'}  # noqa: E731
        self.assertEqual(json.dumps(strip(again), sort_keys=True), json.dumps(strip(first), sort_keys=True))

    def test_a_reused_pass_is_still_sampled(self):
        self.gate(self.world('a'))
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '1'
        sampled = self.gate(self.world('b'))
        how = list(sampled['pass_cache']['frames'].values())[0]
        self.assertTrue(how.startswith('walked again: reused pass from '), how)

    def test_a_failed_walk_is_not_reused_as_a_pass(self):
        out = self.world('a', fill=True)
        first = self.gate(out)
        self.assertEqual(first['status'], 'failed')
        [record] = self.records()
        self.assertEqual(record['outcome'], 'failed')
        again = self.gate(out)
        cache = again['pass_cache']
        self.assertEqual((cache['reused'], cache['walked'], cache['unchecked_candidates']), (0, 1, 1))
        self.assertIn('did not pass', list(cache['frames'].values())[0])
        self.assertEqual(again['failures'], first['failures'])

    def test_a_pass_carries_its_key_outcome_and_provenance(self):
        report = self.gate(self.world('a'))
        [record] = self.records()
        import stair_records
        self.assertTrue(stair_records.intact(record))
        self.assertEqual(record['key'], report['pass_cache']['stored'][0]['key'])
        self.assertEqual(len(record['key']), 64)
        self.assertEqual((record['outcome'], record['run'], record['commit'], record['version']),
                         ('passed', RUN, 'abc1234', '0.0.42-dev1'))
        self.assertEqual(record['chim_version'], (ROOT / 'CHIM_VERSION').read_text(encoding='utf-8').strip())
        walked_at = datetime.datetime.fromisoformat(record['walked_at'])
        self.assertIsNotNone(walked_at.utcoffset())
        self.assertEqual(record['walker'], collision.stair_key_sources())

    def test_provenance_from_the_tree_without_the_builder(self):
        import stair_records
        facts = stair_records.walk_facts('passed', environ={'AMIWIND_SOURCE_COMMIT': 'def5678'})
        self.assertEqual(facts['version'], (ROOT / 'VERSION').read_text(encoding='utf-8').strip())
        self.assertEqual(facts['commit'], 'def5678')
        self.assertEqual(stair_records.walk_facts('passed', environ={'AMIWIND_RUN_CHIM_VERSION': '9.9.9'})
                         ['chim_version'], '9.9.9')
        with self.assertRaises(ValueError):
            stair_records.walk_facts('maybe')

    def test_release_builds_reuse_only_checked_walks(self):
        self.gate(self.world('a'))
        os.environ['AMIWIND_RUN_VERSION'] = '0.0.42-rc1'
        release = self.gate(self.world('b'))
        cache = release['pass_cache']
        self.assertEqual((cache['reuse_rule'], cache['reused'], cache['walked']), ('checked', 0, 1))
        self.assertIn('no check mark', list(cache['frames'].values())[0])
        import stair_records
        folder = Path(self.tmp.name) / 'runs' / RUN
        folder.mkdir(parents=True)
        (folder / 'chim-stairs.json').write_text(json.dumps(release), encoding='utf-8')
        self.assertEqual(stair_records.promote(folder, 'req-1')['marked'], 1)
        checked = self.gate(self.world('c'))
        self.assertEqual((checked['pass_cache']['reused'], checked['pass_cache']['walked']), (1, 0))
        self.assertTrue(list(checked['pass_cache']['frames'].values())[0].startswith('reused from '))

    def test_the_reuse_rule(self):
        self.assertEqual(collision.walk_reuse_rule('0.0.42-dev1'), 'passes')
        self.assertEqual(collision.walk_reuse_rule(''), 'passes')
        for version in ('0.0.42-rc1', '0.0.42'):
            self.assertEqual(collision.walk_reuse_rule(version), 'checked')
        os.environ['AMIWIND_STAIR_WALK_REUSE'] = 'checked'
        self.assertEqual(collision.walk_reuse_rule('0.0.42-dev1'), 'checked')
        os.environ['AMIWIND_STAIR_WALK_REUSE'] = 'passes'
        with self.assertRaises(ValueError):
            collision.walk_reuse_rule('0.0.42-rc1')
        os.environ['AMIWIND_STAIR_WALK_REUSE'] = 'sometimes'
        with self.assertRaises(ValueError):
            collision.walk_reuse_rule('0.0.42-dev1')

    def test_the_rule_never_keys_a_stage(self):
        from build_cache import IGNORED_ENV
        self.assertIn(collision.WALK_REUSE_ENV, IGNORED_ENV)


def edited_copy(base, edits):
    """A copy of the source tree (what the key can read) with EDITS: {path: (old text, new text)}."""
    root = Path(base)
    for name in ('tools', 'src', 'config'):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('VERSION', 'CHIM_VERSION'):
        shutil.copy2(ROOT / name, root / name)
    for path, (old, new) in edits.items():
        target = root / path
        text = target.read_text(encoding='utf-8')
        assert old in text, (path, old)
        target.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')
    return root


def walker_key(root):
    code = ('import sys; sys.path[:0] = [%r, %r]; from chim import collision; print(collision.stair_key_sources())'
            % (str(Path(root) / 'src'), str(Path(root) / 'tools')))
    return subprocess.run([sys.executable, '-B', '-c', code], check=True, capture_output=True, text=True,
                          cwd=str(root)).stdout.strip()


class WalkerKeyIsTheWalk(unittest.TestCase):
    """The walker's code key: the walk and the stair rule, not the compilers whose output is in the frame key."""

    def test_compiler_and_label_edits_keep_the_key_walker_edits_change_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            same = {
                # the collision compilers: the walk runs none of them (their output is the frame's lumps)
                'tools/collision_bsp.py': ('def compile_standing_checked(pieces,qbsp,cache,grid=64,check_box=None,patch=True):\n',
                                           'def compile_standing_checked(pieces,qbsp,cache,grid=64,check_box=None,patch=True):\n'
                                           '    _edited = 1\n'),
                'tools/prepare_mesh_bsp.py': ('def standing_planes(points, equations, exact=False):\n',
                                              'def standing_planes(points, equations, exact=False):\n    _edited = 1\n'),
                # the CHIM version label (v0.0.41-dev5 walked 604 unchanged frames again for 0.2.0 -> 0.2.1)
                'CHIM_VERSION': ((ROOT / 'CHIM_VERSION').read_text(encoding='utf-8'), '9.9.9\n'),
            }
            # the flight test (stair_walk.flights): reached through candidates by every frame worker
            walk = {'tools/stair_walk.py': ('def flights(stairs):\n', 'def flights(stairs):\n    _edited = 1\n')}
            base = walker_key(edited_copy(Path(tmp) / 'base', {}))
            self.assertEqual(base, collision.stair_key_sources())
            self.assertEqual(walker_key(edited_copy(Path(tmp) / 'compilers', same)), base)
            self.assertNotEqual(walker_key(edited_copy(Path(tmp) / 'walk', walk)), base)

    def test_loader_edits_keep_the_key_face_edits_change_it(self):
        """BUILD-REUSE-SCHEDULER-TOP-45 part 2: the frame loader is not walk code. The v0.0.45 rewrite of
        chim/validate.py (frames loaded on the worker pool) changed that module's import-time code and every frame was
        walked again; an edit to the loader, its module or the file readers only it uses keeps every key (the worker
        checks the frame it reads against the walk's data key instead), an edit to how the walk reads a brush
        image's faces changes it."""
        with tempfile.TemporaryDirectory() as tmp:
            loader = {
                # import-time code of the loader's module (what v0.0.45 changed)
                'tools/chim/validate.py': ("ROOT = Path(__file__).resolve().parents[2]\n",
                                           "ROOT = Path(__file__).resolve().parents[2]\n_LOADER_POOL = 4\n"),
                # the format's file readers that only the loader runs
                'tools/chim/format.py': ('def read_sector(data):\n', 'def read_sector(data):\n    _edited = 1\n'),
            }
            body = {'tools/chim/validate.py': ("    root = Path(out) / 'chim'\n    _, files, mdir, _ = F.read_index(",
                                               "    root = Path(out) / 'chim'\n    _edited = 1\n"
                                               "    _, files, mdir, _ = F.read_index(")}
            faces = {'tools/chim/faces.py': ('def face_polygons(lumps):\n',
                                             'def face_polygons(lumps):\n    _edited = 1\n')}
            base = walker_key(edited_copy(Path(tmp) / 'base', {}))
            self.assertEqual(walker_key(edited_copy(Path(tmp) / 'loader', loader)), base)
            self.assertEqual(walker_key(edited_copy(Path(tmp) / 'body', body)), base)
            self.assertNotEqual(walker_key(edited_copy(Path(tmp) / 'faces', faces)), base)

    def test_the_key_holds_the_walk_files_and_no_compiler(self):
        selected, uncertain = collision.stair_code_selection()
        self.assertFalse(uncertain)
        self.assertEqual(sorted(selected), sorted(collision.STAIR_WALK_CODE))
        for compiler in ('tools/collision_bsp.py', 'tools/prepare_mesh_bsp.py', 'tools/routed_hull.py',
                         'tools/chim/models.py', 'tools/chim/terrain.py', 'CHIM_VERSION'):
            self.assertNotIn(compiler, selected)

    def test_no_reached_walk_function_uses_a_module_outside_the_list(self):
        """Statically: every function or class of STAIR_WALK_CODE that stair_task reaches imports, and names
        through its module's imports, only modules of the list (or none of the repository's)."""
        import ast
        from build_cache import SourceIndex
        from pass_cache import PASS_KEY_FORM
        index = SourceIndex(ROOT, top_format=PASS_KEY_FORM)
        script = Path(collision.__file__).resolve()
        index.entry_digest(script, 'stair_task')
        reached = index._reached['%s::%s' % (script, 'stair_task')]
        files = set(index.files)

        def repo_module(name, relative, level=0):
            if level:
                base = relative.rsplit('/', 1)[0]
                for _ in range(level - 1):
                    base = base.rsplit('/', 1)[0]
                prefixes = [base + '/']
            else:
                prefixes = ['tools/', 'src/']
            for prefix in prefixes:
                stem = prefix + name.replace('.', '/') if name else prefix.rstrip('/')
                for candidate in (stem + '.py', stem + '/__init__.py'):
                    if candidate in files:
                        return candidate
            return None

        def imported(node, relative):
            """[(bound name, repository module path)] of an import statement."""
            out = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found = repo_module(alias.name, relative)
                    out.append(((alias.asname or alias.name).split('.')[0], found))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    sub = repo_module(((node.module + '.') if node.module else '') + alias.name, relative, node.level)
                    found = sub or repo_module(node.module or '', relative, node.level)
                    out.append((alias.asname or alias.name, found))
            return out
        problems = []
        for relative in collision.STAIR_WALK_CODE:
            tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
            top = {}
            for node in tree.body:
                for name, found in imported(node, relative):
                    top[name] = found
            units = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            for unit in sorted(reached.get(relative, ())):
                node = units.get(unit)
                if node is None:
                    continue
                for inner in ast.walk(node):
                    for name, found in imported(inner, relative):
                        if (found, name) == collision.STAIR_FRAME_LOADER:
                            continue        # the frame loader: its output is checked by content (_stair_frame)
                        if found is not None and found not in collision.STAIR_WALK_CODE:
                            problems.append('%s %s imports %s' % (relative, unit, found))
                    if isinstance(inner, ast.Name) and inner.id in top and top[inner.id] is not None \
                            and top[inner.id] not in collision.STAIR_WALK_CODE:
                        problems.append('%s %s uses %s from %s' % (relative, unit, inner.id, top[inner.id]))
        self.assertEqual(problems, [])

    def test_a_traced_walk_runs_only_the_listed_code(self):
        """Dynamically: every repository function a frame walk calls (stair_task on a flight of stairs) is in a
        file of STAIR_WALK_CODE."""
        from test_chim_stairs import world_of
        import chim.validate  # noqa: F401 (imported before the trace: import-time code is not the walk)
        import stair_walk  # noqa: F401
        root = str(ROOT.resolve())
        called = set()
        functions = set()

        def seen(code):
            path = code.co_filename
            if (os.path.isabs(path) and path.startswith(root) and code.co_name != '<module>'
                    and os.path.isfile(path)):
                relative = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
                called.add(relative)
                functions.add((relative, code.co_name))

        monitoring = getattr(sys, 'monitoring', None)
        if monitoring is None:
            self.skipTest('needs sys.monitoring (Python 3.12)')
        tool = next((t for t in range(1, 6) if monitoring.get_tool(t) is None), None)
        if tool is None:
            self.skipTest('no free sys.monitoring tool id')

        def start(code, offset):
            seen(code)
            return monitoring.DISABLE          # each code object is reported once: the walk runs at full speed
        with tempfile.TemporaryDirectory() as tmp:
            world_of(tmp, False)
            from chim.validate import Failures, load_world
            frames = load_world(tmp, Failures())[5]
            tasks = collision.stair_tasks(tmp, frames)
            collision._STAIR_CACHE.clear()
            rows = []
            monitoring.use_tool_id(tool, 'stair walk code test')
            monitoring.register_callback(tool, monitoring.events.PY_START, start)
            monitoring.set_events(tool, monitoring.events.PY_START)
            try:
                for task in tasks:
                    rows.extend(collision.stair_task(task))
            finally:
                monitoring.set_events(tool, 0)
                monitoring.register_callback(tool, monitoring.events.PY_START, None)
                monitoring.free_tool_id(tool)
        self.assertTrue(any(r['kind'] == 'step' and r.get('flight') for r in rows))
        self.assertLessEqual({'tools/chim/collision.py', 'tools/stair_walk.py', 'tools/audit_walkability.py',
                             'tools/chim/faces.py', 'tools/chim/format.py'}, called)
        # outside the walk's code only the frame loader runs (its output is checked against the walk's data key)
        loader_file, loader = collision.STAIR_FRAME_LOADER
        self.assertEqual(sorted(called - set(collision.STAIR_WALK_CODE) - {loader_file}), [])
        from build_cache import SourceIndex
        loader_units = SourceIndex(ROOT).entry_units(ROOT / loader_file, loader)[3].get(loader_file, set())
        self.assertIn(loader, loader_units)
        import ast
        top_level = {n.name for n in ast.parse((ROOT / loader_file).read_text(encoding='utf-8')).body
                     if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(sorted(name for path, name in functions if path == loader_file
                                and name in top_level and name not in loader_units), [])


class WalkedDataIsKeyedData(unittest.TestCase):
    """BUILD-REUSE-SCHEDULER-TOP-45 part 2, the dangerous direction: with the loader out of the code key, a walk must
    never be stored or reused for data other than what it walked. The data part of the key is the frame as the gate
    read it (frame_stair_key); every walk worker checks the frame it reads against it and walks nothing on a
    mismatch; a frame whose walked data changed gets another key and is walked again."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        for name in ('AMIWIND_STAIR_WALK_REUSE', 'AMIWIND_RUN_CHIM_VERSION', 'AMIWIND_AW_REQUEST'):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_PASS_CACHE=str(Path(self.tmp.name) / 'cache'), AMIWIND_STAIR_WALK_CACHE='cached',
                          AMIWIND_STAIR_WALK_SAMPLE='0', AMIWIND_RUN_NAME=RUN, AMIWIND_RUN_COMMIT='abc1234',
                          AMIWIND_RUN_VERSION='0.0.42-dev1', AMIWIND_STAIR_WALK_KEY='frame', AMIWIND_STAIR_WALK='all', AMIWIND_STAIR_WATCH='off')
        from test_chim_stairs import world_of
        from chim.validate import Failures, load_world
        self.out = Path(self.tmp.name) / 'world'
        self.out.mkdir()
        world_of(self.out, False)
        world = load_world(self.out, Failures())
        self.frames, self.models = world[5], world[4]
        self.clear()

    def tearDown(self):
        self.clear()
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def clear(self):
        collision._STAIR_CACHE.clear()
        collision._STAIR_DIGESTS.clear()

    def unit(self, expect):
        cores = [t[2] for t in collision.stair_tasks(self.out, self.frames) if t[1] == 0]
        return collision.stair_unit((str(self.out), 0, cores, 0, None, expect))

    def changed_load_frame(self):
        """chim.validate.load_frame returning the frame with one placement moved: other data than the world holds."""
        from chim import validate
        real = validate.load_frame

        def moved(out, frame_index):
            row, models = real(out, frame_index)
            path, frame, chunks = row
            chunks = [dict(c, owned=[dict(r, origin=[r['origin'][0] + 64.0] + list(r['origin'][1:]))
                                     for r in c['owned']]) for c in chunks]
            return (path, frame, chunks), models
        return patch.object(validate, 'load_frame', side_effect=moved)

    def test_the_worker_walks_only_the_keyed_frame(self):
        key = collision.frame_stair_key(self.frames[0], self.models)
        _, rows = self.unit(key)
        self.assertTrue(rows)
        self.clear()
        with self.assertRaisesRegex(ValueError, 'other data than the world holds'):
            self.unit('0' * 64)
        self.clear()
        with self.changed_load_frame(), self.assertRaisesRegex(ValueError, 'other data than the world holds'):
            self.unit(key)

    def test_a_gate_whose_loader_reads_other_data_stores_nothing(self):
        with self.changed_load_frame(), self.assertRaisesRegex(ValueError, 'other data than the world holds'):
            collision.stair_gate(self.out, self.frames, 1, models=self.models)
        self.assertEqual(list((Path(os.environ['AMIWIND_PASS_CACHE']) / 'stair-walk').rglob('*.json')), [])

    def test_changed_walked_data_is_walked_again(self):
        first = collision.stair_gate(self.out, self.frames, 1, models=self.models)
        self.assertEqual(first['pass_cache']['walked'], len(self.frames))
        self.clear()
        again = collision.stair_gate(self.out, self.frames, 1, models=self.models)
        self.assertEqual((again['pass_cache']['reused'], again['pass_cache']['walked']), (len(self.frames), 0))
        # the same world with one placement of frame 0 moved: its data key changes, so it is walked, not reused
        path, frame, chunks = self.frames[0]
        moved = [dict(c, owned=[dict(r, origin=[r['origin'][0] + 64.0] + list(r['origin'][1:])) for r in c['owned']])
                 for c in chunks]
        self.assertTrue(any(c['owned'] for c in chunks))
        frames = [(path, frame, moved)] + list(self.frames[1:])
        self.assertNotEqual(collision.frame_stair_key(frames[0], self.models),
                            collision.frame_stair_key(self.frames[0], self.models))
        self.clear()
        # the walk worker reads the files (unchanged): its frame is not the keyed one, so nothing is walked or kept
        with self.assertRaisesRegex(ValueError, 'other data than the world holds'):
            collision.stair_gate(self.out, frames, 1, models=self.models)


if __name__ == '__main__':
    unittest.main()
