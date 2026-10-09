# SPDX-License-Identifier: GPL-3.0-only
"""--jobs N becomes N workers end to end (BUILD-IMAGE-SERIAL-32).

Runs in the public source check without game data or map compilers:
(a) build.commands(): every stage whose tool has a worker pool receives exactly
    --jobs N (no hard-coded or silent count); the image and actor-contact stages
    are among them.
(b) the image step's per-map passes hand N to the shared pool factory
    (build_parallel.process_pool), and their results are byte-identical to the
    serial path (jobs=1) with real spawned workers.
(c) resolve_jobs keeps an explicit N unchanged even above the CPU count; the
    one warning appears only when N exceeds the usable CPU threads.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_jobs  # noqa: E402
import build_parallel  # noqa: E402

TOOLS = {k: '/tools/' + k for k in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
# Stages whose tool has no worker pool: one process each, budgeted as one slot.
SERIAL_BY_DESIGN = {'setup', 'terrain', 'npcs', 'hands', 'dialogue-lookup', 'door-audio',
                    'reading', 'opening-references', 'world-ui'}
# Independent per-item loops not yet in the pool (tracked; remove when pooled).
SERIAL_NOT_YET_POOLED = set()


def stage_commands(jobs, extra=()):
    args = build.parser().parse_args(['--jobs', str(jobs), '--tree-sprites', *extra])
    args.data_files = Path('/owned'); args.sdk = Path('/sdk')
    return build.commands(args, TOOLS, Path('/private/run'))


def tool_has_jobs_option(command):
    text = Path(command[1]).read_text(encoding='utf-8')
    return 'add_jobs(' in text or "'--jobs'" in text or '"--jobs"' in text


@contextlib.contextmanager
def recorded_pools():
    """Replace the pool factory by thread pools that record their size."""
    sizes = []

    def factory(count):
        sizes.append(count)
        return ThreadPoolExecutor(max_workers=count)
    with patch.object(build_parallel, 'process_pool', side_effect=factory):
        yield sizes


class StageJobsTests(unittest.TestCase):
    def test_every_pooled_stage_receives_exactly_n(self):
        for jobs in (3, 16, 100):
            steps = stage_commands(jobs)
            names = [name for name, _ in steps]
            self.assertIn('image', names)
            for name, command in steps:
                text = [str(part) for part in command]
                with self.subTest(jobs=jobs, stage=name):
                    if '--jobs' in text:
                        self.assertEqual(text[text.index('--jobs') + 1], str(jobs))
                        self.assertEqual(text.count('--jobs'), 1)
                    else:
                        self.assertIn(name, SERIAL_BY_DESIGN | SERIAL_NOT_YET_POOLED, 'stage without --jobs: ' + name)
                        self.assertFalse(tool_has_jobs_option(text), name + ' tool accepts --jobs but gets none')
                    self.assertNotIn('-threads', text)
            for name in ('image', 'actor-contact', 'world-flora', 'world-terrain'):
                command = [str(part) for part in dict(steps)[name]]
                self.assertEqual(command[command.index('--jobs') + 1], str(jobs), name)

    def test_automatic_jobs_resolve_once_per_plan(self):
        # BUILD-JOBS-RESOLVE-PER-STAGE-32: free memory changes between calls.
        import itertools
        counter = itertools.count(20)
        with patch.dict(os.environ), patch.object(build_jobs, 'auto_jobs', side_effect=lambda: next(counter)):
            os.environ.pop('AMIWIND_BUILD_JOBS', None)
            args = build.parser().parse_args(['--tree-sprites'])
            args.data_files = Path('/owned'); args.sdk = Path('/sdk')
            values = {str(command[command.index('--jobs') + 1]) for _, command in
                      build.commands(args, TOOLS, Path('/private/run')) if '--jobs' in command}
        self.assertEqual(len(values), 1, values)

    def test_image_parser_accepts_jobs(self):
        import build_aga
        required = ['--sdk', '/sdk', '--data-files', '/owned', '--no-npc-gallery', '--world-scenery', '/scenery']
        for key in ('scene', 'music', 'media', 'engine', 'out', 'qcc', 'qbsp', 'vis', 'light', 'xdftool', 'rdbtool'):
            required += ['--' + key, '/' + key]
        for extra, expected in (([], None), (['--jobs', '7'], 7), (['--jobs', '100'], 100)):
            with patch('sys.argv', ['build_aga.py', 'image', *required, *extra]), \
                    patch.object(build_aga, 'image') as image:
                build_aga.main()
                self.assertEqual(image.call_args.args[0].jobs, expected)

    def test_image_jobs_is_exact_and_reaches_nested_defaults(self):
        import argparse
        import build_aga
        with patch.dict(os.environ, {'AMIWIND_BUILD_JOBS': '1'}):
            self.assertEqual(build_aga.image_jobs(argparse.Namespace(jobs=100)), 100)
            self.assertEqual(os.environ['AMIWIND_BUILD_JOBS'], '100')
            self.assertEqual(build_jobs.resolve_jobs(None), 100)

    def test_scheduled_stage_alone_gets_whole_budget(self):
        script = ('import json, os, sys; print(json.dumps([sys.argv[-1], os.environ["AMIWIND_BUILD_JOBS"]]))')
        steps = [('first', [sys.executable, '-c', 'pass']),
                 ('last', [sys.executable, '-c', script, '--jobs', '1'])]
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            run = Path(temp) / 'run'
            build_parallel.execute_parallel(steps, run, {'compiler_jobs': 5}, ROOT)
            state = json.loads((run / 'build-state.json').read_text())
            last = next(step for step in state['steps'] if step['name'] == 'last')
            self.assertEqual(last['jobs'], 5)
            self.assertEqual(json.loads((run / 'logs' / '02-last.log').read_text()), ['5', '5'])


class ImageCallSiteTests(unittest.TestCase):
    """Static: every per-map pass of the image step gets the image job count."""
    PASSES = {'configure_staged_maps', 'cull_staged_maps', 'stamp_staged_hands', 'optimize_maps',
              'require_actor_ground', 'verify_optimized_maps', 'audit_world_map_heap_with_receipt',
              'write_content_fingerprint', 'convert_builder_scene', 'entity_gate', 'pack_world_volumes',
              'assemble_drives', 'annotate', 'bake_ground', 'install_world_scenery', 'install_world_flora'}

    def calls(self, function):
        tree = ast.parse((ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
        return [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]

    def test_every_per_map_pass_receives_jobs(self):
        seen = set()
        for function in ('image', 'finalize_image'):
            for call in self.calls(function):
                keywords = {k.arg: k.value for k in call.keywords}
                if call.func.id in self.PASSES:
                    seen.add(call.func.id)
                    self.assertIn('jobs', keywords, call.func.id)
                    self.assertIsInstance(keywords['jobs'], ast.Name, call.func.id)
                    self.assertEqual(keywords['jobs'].id, 'jobs', call.func.id)
                if call.func.id == 'repair_balmora_maps':
                    self.assertEqual(keywords['threads'].id, 'jobs')
        self.assertEqual(seen, self.PASSES)

    def test_no_hard_coded_worker_counts_in_the_builder(self):
        pattern = re.compile(r'\b(?:jobs|threads|max_workers|workers)\s*=\s*(?:[2-9]|\d{2,})\b|optimizer_jobs')
        for path in sorted((ROOT / 'tools').glob('*.py')):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if pattern.search(line.split('#')[0]):
                    self.fail(f'{path.name}:{number}: hard-coded worker count: {line.strip()}')

    def test_light_compiles_single_threaded(self):
        # ericw light 0.18.1 writes faces/lighting in thread order: not reproducible.
        # Every light invocation takes its arguments from vis_options.light_args.
        from vis_options import LIGHT_THREADS, light_args
        self.assertEqual(LIGHT_THREADS, 1)
        self.assertEqual(light_args('-minlight', 24, 'x.bsp'), ['-threads', '1', '-minlight', '24', 'x.bsp'])
        # A light executable followed by its argument list.
        call = re.compile(r"""(\(\s*light|\(\s*['"]light['"]|quake\[['"]light['"]\]|Path\(light\)\.resolve\(\)\))\s*,\s*[\[*]?\s*(\[|light_args|['"]-)""")
        found = 0
        for path in sorted((ROOT / 'tools').glob('*.py')):
            if path.name == 'vis_options.py':
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if call.search(line) and not line.lstrip().startswith('def '):
                    found += 1
                    self.assertIn('light_args(', line, f'{path.name}:{number}: light without light_args')
                if 'light' in line and '-threads' in line and 'light_args' not in line and 'vis' not in line:
                    self.fail(f'{path.name}:{number}: light thread count outside light_args: {line.strip()}')
        self.assertGreaterEqual(found, 11)


def sky_maps(root, count):
    from test_exterior_sky_build import sky_fixture
    maps = root / 'id1' / 'maps'; maps.mkdir(parents=True)
    raw = sky_fixture()
    for index in range(count):
        (maps / f'm{index:02d}.bsp').write_bytes(raw)
    return [f'm{index:02d}' for index in range(count)]


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(Path(root).rglob('*')) if p.is_file()}


class ImagePoolTests(unittest.TestCase):
    """Each pass hands N (or N capped by its item count) to the pool factory."""
    JOBS = 3

    def test_exterior_sky_uses_pool(self):
        from exterior_sky_build import configure_staged_maps
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes, \
                contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp); names = sky_maps(root, 8)
            configure_staged_maps(root / 'id1', exterior_maps=names[:5], interior_maps=names[5:],
                                  work_dir=root / 'work', jobs=self.JOBS)
        self.assertTrue(sizes)
        self.assertEqual(set(sizes), {self.JOBS})

    def test_hidden_surface_cull_uses_pool(self):
        from hidden_surface_build import cull_staged_maps
        from test_hidden_surface_build import fixture, parallel_fixture_processor
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes, \
                contextlib.redirect_stdout(io.StringIO()):
            base = Path(temp); maps = base / 'maps'; maps.mkdir()
            for index in range(6):
                (maps / f'm{index}.bsp').write_bytes(fixture())
            cull_staged_maps(maps, base / 'proof', {'m0', 'm1'}, processor=parallel_fixture_processor, jobs=self.JOBS)
        self.assertEqual(sizes, [self.JOBS] * 4)  # the cull, then three hash checks

    def test_optimizer_uses_pool_for_preparation_and_hashing(self):
        from optimize_world_maps import optimize_maps, verify_optimized_maps
        from test_share_bsp_geometry import repeated_geometry
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes, \
                contextlib.redirect_stdout(io.StringIO()):
            maps = Path(temp) / 'maps'; maps.mkdir()
            for index in range(5):
                (maps / f'm{index}.bsp').write_bytes(repeated_geometry())
            report = optimize_maps(maps, Path(temp) / 'receipt.json', jobs=self.JOBS)
            verify_optimized_maps(maps, report, jobs=self.JOBS)
        self.assertGreaterEqual(len(sizes), 3)
        self.assertEqual(set(sizes), {self.JOBS})

    def test_hand_metadata_uses_pool(self):
        from hand_metadata import stamp_staged_hands
        from test_hand_metadata import HandMetadata
        fixture = HandMetadata()
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes:
            id1 = Path(temp); (id1 / 'maps').mkdir(); (id1 / 'progs').mkdir()
            (id1 / 'progs/v_nord.mdl').write_bytes(fixture.model())
            for index in range(5):
                (id1 / 'maps' / f'm{index}.bsp').write_bytes(fixture.map_bytes())
            result = stamp_staged_hands(id1, fixture.report(), jobs=self.JOBS)
        self.assertEqual(len(result['changed_maps']), 5)
        self.assertEqual(set(sizes), {self.JOBS})

    def test_actor_audit_uses_pool(self):
        from check_actor_ground import audit
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes:
            maps = actor_world(Path(temp))
            audit(maps, jobs=self.JOBS)
        self.assertEqual(sizes, [self.JOBS, self.JOBS])

    def test_heap_audit_uses_pool(self):
        import check_world_map_heap as heap
        from test_check_world_map_heap import SIZES, make_bsp
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes:
            maps = Path(temp)
            for index in range(9):
                (maps / f'sn{index:03d}.bsp').write_bytes(make_bsp())
            heap.inspect_maps(maps, SIZES, jobs=self.JOBS)
        self.assertEqual(sizes, [self.JOBS])

    def test_explicit_n_above_cpu_count_is_not_capped(self):
        with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes, \
                patch.object(build_jobs, 'usable_cpus', return_value=2):
            paths = []
            for index in range(40):
                path = Path(temp) / f'{index}.bin'; path.write_bytes(bytes([index]))
                paths.append(path)
            digests = build_parallel.hash_files(paths, 32)
        self.assertEqual(sizes, [32])
        self.assertEqual(digests, [hashlib.sha256(bytes([i])).hexdigest() for i in range(40)])


def actor_world(root, bad_model=True):
    """Several maps: grounded, failed, invalid, overlap copies, a bad model."""
    from test_actor_ground import actor, alias, bsp
    id1 = root; maps = id1 / 'maps'; maps.mkdir()
    (id1 / 'progs').mkdir(); (id1 / 'progs/test.mdl').write_bytes(alias())
    (id1 / 'progs/low.mdl').write_bytes(alias(4))
    (id1 / 'balmora-regions.txt').write_text('AWBR1\nbm000 -10 -10 10 10 -20 -20 20 20\n')
    (maps / 'bm000.bsp').write_bytes(bsp(actor(10.25, ref='1') + actor(40, 'agronian guy', 1, ref='2'), 10))
    (maps / 'balmora.bsp').write_bytes(bsp(actor(10.25, ref='1'), 0))
    (maps / 'room.bsp').write_bytes(bsp(actor(2, ref='3') + actor(.25, ref='4') +
                                        actor(identifier='unknown-new-actor', ref='5'), 0))
    missing = actor(.25, ref='7').replace('progs/test.mdl', 'progs/missing.mdl') if bad_model else ''
    (maps / 'cell.bsp').write_bytes(bsp(actor(.25, ref='6').replace('progs/test.mdl', 'progs/low.mdl') + missing, 0))
    for index in range(4):
        (maps / f'vf{index:04d}.bsp').write_bytes(bsp('', 0))
    return maps


class SerialParallelIdentityTests(unittest.TestCase):
    """Real spawned workers produce the bytes of the serial path."""

    def setUp(self):
        # Spawned workers inherit sys.path. Test modules put tools/ (which holds
        # the mwad.py command) first; the builder puts src/ (the mwad package)
        # first, as here.
        src = str(ROOT / 'src')
        order = patch.object(sys, 'path', [src] + [p for p in sys.path if p != src])
        order.start()
        self.addCleanup(order.stop)

    def test_actor_audit_equals_reference_and_serial(self):
        from check_actor_ground import audit
        with tempfile.TemporaryDirectory() as temp:
            maps = actor_world(Path(temp))
            serial = json.dumps(audit(maps, jobs=1), indent=2)
            parallel = json.dumps(audit(maps, jobs=3), indent=2)
            reference = json.dumps(reference_audit(maps), indent=2)
        self.assertEqual(parallel, serial)
        self.assertEqual(serial, reference)
        report = json.loads(serial)
        self.assertEqual({row['status'] for row in report['rows']},
                         {'grounded', 'failed-contact', 'invalid', 'explicit-exception'})

    def test_exterior_sky_hand_and_heap_passes_equal_serial(self):
        from exterior_sky_build import configure_staged_maps
        import check_world_map_heap as heap
        from test_check_world_map_heap import SIZES, make_bsp
        results = []
        for jobs in (1, 3):
            with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as log:
                root = Path(temp); names = sky_maps(root, 7)
                configure_staged_maps(root / 'id1', exterior_maps=names[:4], interior_maps=names[4:6],
                                      work_dir=root / 'work', jobs=jobs)
                maps = root / 'heap'; maps.mkdir()
                for index in range(6):
                    (maps / f'sn{index:03d}.bsp').write_bytes(make_bsp())
                estimate = json.dumps(heap.inspect_maps(maps, SIZES, jobs=jobs), indent=2).replace(str(root), '<root>')
                results.append((tree_bytes(root / 'id1'), tree_bytes(root / 'work'), estimate, log.getvalue()))
        self.assertEqual(results[0], results[1])

    def test_annotate_and_bake_ground_equal_serial(self):
        from actor_grounding import annotate, bake_ground
        identities = {1: 'heddvild', 2: 'agronian guy', 3: 'heddvild', 4: 'heddvild', 5: 'heddvild', 6: 'heddvild'}
        results = []
        for jobs in (1, 3):
            with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as log, \
                    patch('actor_grounding.records', return_value=[('CELL', 0, b'')]), \
                    patch('actor_grounding.subrecords', return_value=[]), \
                    patch('actor_grounding.cell_data', return_value={'refs': [
                        {'number': n, 'id': i} for n, i in identities.items()]}):
                root = Path(temp); maps = actor_world(root, bad_model=False)
                (root / 'master.esm').write_bytes(b'')
                annotated = annotate(maps, root / 'master.esm', jobs=jobs)
                baked = bake_ground(maps, jobs=jobs)
                results.append((annotated, baked, tree_bytes(maps), log.getvalue()))
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0][1])
        self.assertIn('Actor support:', results[0][3])

    def test_sliced_support_search_equals_one_search(self):
        import actor_grounding
        from test_actor_ground import actor, alias, bsp
        results = []
        for jobs, slice_size in ((1, len(actor_grounding.OFFSETS)), (1, 7), (3, 7), (3, 64)):
            with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                    patch.object(actor_grounding, 'SEARCH_SLICE', slice_size):
                root = Path(temp); maps = root / 'maps'; maps.mkdir(); (root / 'progs').mkdir()
                (root / 'progs/test.mdl').write_bytes(alias(4))
                (maps / 'room.bsp').write_bytes(bsp(actor(ref='1') + actor(80, ref='2'), 0))
                (maps / 'hall.bsp').write_bytes(bsp(actor(ref='3'), 0))
                report = actor_grounding.bake_ground(maps, jobs=jobs)
                results.append((report, tree_bytes(maps)))
        self.assertEqual({r[0][0].get('mesh_contact') for r in results}, {'fitted'})
        for other in results[1:]:
            self.assertEqual(other, results[0])

    def test_backups_are_links_and_survive_replacement(self):
        # dev3-r2 profile: sky, cull and optimizer wrote a full copy of every map
        # they change before replacing it; a hard link keeps the same bytes.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); live = root / 'm.bsp'; live.write_bytes(b'original')
            build_parallel.keep_original(live, root / 'backup.bsp', b'original')
            if os.name == 'posix':
                self.assertEqual(os.stat(live).st_ino, os.stat(root / 'backup.bsp').st_ino)
            (root / 'candidate.bsp').write_bytes(b'changed')
            (root / 'candidate.bsp').replace(live)
            self.assertEqual((root / 'backup.bsp').read_bytes(), b'original')
            self.assertEqual(live.read_bytes(), b'changed')
            with patch.object(build_parallel.os, 'link', side_effect=OSError('cross-device')):
                build_parallel.keep_original(live, root / 'copy.bsp', b'changed')
            self.assertEqual((root / 'copy.bsp').read_bytes(), b'changed')

    def test_support_fitting_uses_one_pool_for_heads_and_all_slices(self):
        # dev3-r2 profile: the round-by-round search started a pool per round and
        # waited for each round's slowest slice (2.7 of 24 cores for 95 s).
        import actor_grounding
        from test_actor_ground import actor, alias, bsp
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                patch.object(actor_grounding, 'SEARCH_SLICE', 3), recorded_pools() as sizes:
            root = Path(temp); maps = root / 'maps'; maps.mkdir(); (root / 'progs').mkdir()
            (root / 'progs/test.mdl').write_bytes(alias(4))
            (maps / 'room.bsp').write_bytes(bsp(actor(ref='1') + actor(ref='4'), 0))
            (maps / 'hall.bsp').write_bytes(bsp(actor(ref='3'), 0))
            report = actor_grounding.bake_ground(maps, jobs=4)
        self.assertEqual([row.get('mesh_contact') for row in report], ['fitted'] * 3)
        self.assertEqual(sizes, [2, 4, 2])  # map scan, fitting (heads and every slice), map writes

    def test_support_fitting_takes_the_stage_share_not_its_start_value(self):
        # BUILD-IDLE-STAGES-33: actor-contact started with --jobs 1 beside other
        # stages and fitted every placement serially while holding 12 workers.
        import actor_grounding
        from test_actor_ground import actor, alias, bsp
        reports = {}
        for label, allowance in (('serial', None), ('share', '4')):
            with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                    patch.object(actor_grounding, 'SEARCH_SLICE', 3), recorded_pools() as sizes:
                root = Path(temp); maps = root / 'maps'; maps.mkdir(); (root / 'progs').mkdir()
                (root / 'progs/test.mdl').write_bytes(alias(4))
                (maps / 'room.bsp').write_bytes(bsp(actor(ref='1') + actor(ref='4'), 0))
                (maps / 'hall.bsp').write_bytes(bsp(actor(ref='3'), 0))
                env = {} if allowance is None else {'AMIWIND_BUILD_JOBS_FILE': str(root / 'allowance')}
                if allowance is not None:
                    (root / 'allowance').write_text(allowance + chr(10))
                with patch.dict(os.environ, env):
                    reports[label] = (actor_grounding.bake_ground(maps, jobs=1),
                                      tree_bytes(maps), list(sizes))
        self.assertEqual(reports['serial'][2], [])           # jobs 1 alone: serial, no pool
        self.assertIn(4, reports['share'][2])                 # the held share fits in a pool
        self.assertEqual(reports['serial'][:2], reports['share'][:2])  # same report, same map bytes

    def test_live_jobs_reads_the_allowance(self):
        from build_parallel import live_jobs
        with tempfile.TemporaryDirectory() as temp:
            allowance = Path(temp) / 'allowance'
            allowance.write_text('6' + chr(10))
            with patch.dict(os.environ, AMIWIND_BUILD_JOBS_FILE=str(allowance)):
                self.assertEqual(live_jobs(1), 6)
            with patch.dict(os.environ, AMIWIND_BUILD_JOBS_FILE=str(Path(temp) / 'missing')):
                self.assertEqual(live_jobs(3), 3)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_BUILD_JOBS_FILE', None)
            self.assertEqual(live_jobs(2), 2)

    def test_fingerprint_hashing_equals_serial(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = []
            for index in range(12):
                path = Path(temp) / f'{index}.bin'; path.write_bytes(os.urandom(1000 + index))
                paths.append(path)
            self.assertEqual(build_parallel.hash_files(paths, 1), build_parallel.hash_files(paths, 4))


class ResolveJobsTests(unittest.TestCase):
    def test_explicit_n_is_returned_unchanged(self):
        with patch.object(build_jobs, 'usable_cpus', return_value=4):
            for value in (1, 4, 5, 100):
                self.assertEqual(build_jobs.resolve_jobs(value), value)

    def test_auto_uses_auto_jobs_and_inherited_budget(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_BUILD_JOBS', None)
            with patch.object(build_jobs, 'auto_jobs', return_value=11):
                self.assertEqual(build_jobs.resolve_jobs(None), 11)
            os.environ['AMIWIND_BUILD_JOBS'] = '6'
            self.assertEqual(build_jobs.resolve_jobs(None), 6)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            build.parser().parse_args(['--jobs', '0'])

    def test_warning_only_above_usable_cpu_threads_regardless_of_memory(self):
        with patch.object(build_jobs, 'usable_cpus', return_value=24), \
                patch.object(build_jobs, 'available_memory', return_value=64 * 1024 ** 2):
            self.assertIsNone(build_jobs.jobs_warning(None))
            self.assertIsNone(build_jobs.jobs_warning(24))
            self.assertIsNone(build_jobs.jobs_warning(1))
            text = build_jobs.jobs_warning(100)
        self.assertEqual(text, 'WARNING: --jobs 100 exceeds 24 usable CPU threads; running 100 workers '
                               'as requested (expect contention and higher temperatures)')

    def test_usable_cpus_ignores_memory(self):
        with patch('build_jobs.os.cpu_count', return_value=8), \
                patch('build_jobs.os.sched_getaffinity', return_value=set(range(8)), create=True), \
                patch.object(Path, 'read_text', side_effect=OSError), \
                patch.object(build_jobs, 'available_memory', return_value=64 * 1024 ** 2):
            self.assertEqual(build_jobs.usable_cpus(), 8)
            self.assertEqual(build_jobs.auto_jobs(), 1)

    def run_build(self, root, jobs):
        args = ['--dry-run', '--workspace', str(root), '--name', 'fixture', '--jobs', str(jobs)]

        def commands(options, run):
            output = run / 'image' / f'AmiWind-v{build.VERSION}-dry-run.hdf'
            script = f'from pathlib import Path; p=Path({str(output)!r}); p.parent.mkdir(); p.write_bytes(b"x")'
            return [('engine', [sys.executable, '-c', script])]
        captured = io.StringIO()
        with patch('setup_build.use_environment'), \
                patch.object(build, 'dry_run_prerequisites', return_value={}), \
                patch.object(build, 'provenance', return_value={'compiler_jobs': 1, 'tools': {}}), \
                patch.object(build, 'dry_run_commands', side_effect=commands), \
                patch.object(build_jobs, 'usable_cpus', return_value=4), \
                contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            self.assertEqual(build.main(args), 0)
        run = root / 'build/fixture'
        return (captured.getvalue(), json.loads((run / 'build-state.json').read_text()),
                json.loads((run / 'build-summary.json').read_text()))

    def test_build_warns_once_and_records_it(self):
        with tempfile.TemporaryDirectory() as temp:
            text, state, summary = self.run_build(Path(temp), 100)
        warning = 'WARNING: --jobs 100 exceeds 4 usable CPU threads'
        self.assertEqual(text.count(warning), 1)
        self.assertEqual(text.count(warning + '; running 100 workers as requested'), 1)
        self.assertTrue(state['jobs_warning'].startswith(warning))
        self.assertTrue(summary['build_environment']['jobs_warning'].startswith(warning))
        with tempfile.TemporaryDirectory() as temp:
            text, state, summary = self.run_build(Path(temp), 4)
        self.assertNotIn('WARNING: --jobs', text)
        self.assertIsNone(state['jobs_warning'])


# The serial audit as it was before the worker pool (tools/check_actor_ground.py
# at v0.0.32-dev 887c566), kept as the byte-identity reference.
def reference_audit(maps):
    from collections import Counter
    from functools import lru_cache
    import math
    import struct
    from actor_grounding import initial_state
    from audit_walkability import Scene
    from check_actor_ground import contact_samples, entities, model_frames, owner
    maps=Path(maps);rows=[];placements={};errors=[];hashes={};copies=0;owner_seen=set()
    @lru_cache(maxsize=3)
    def scene(name):return Scene((maps/(name+'.bsp')).read_bytes(),hull=0)
    @lru_cache(maxsize=128)
    def poses(name):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe actor model path')
        raw=(maps.parent/p).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest()
        return model_frames(raw)
    for path in sorted(maps.glob('*.bsp')):
        map_seen=set()
        raw=path.read_bytes();hashes['maps/'+path.name]=hashlib.sha256(raw).hexdigest()
        for e in entities(raw):
            if e.get('classname') not in ('aw_npc','aw_corpse'):continue
            copies+=1
            row=dict(map=path.stem,reference=e.get('aw_ref'),source_id=e.get('aw_source_id'),
                     name=e.get('netname'),model=e.get('model'))
            try:
                if not row['source_id']:raise ValueError('Missing original actor identity')
                state=initial_state(row['source_id']);row['initial_state']=state
                if int(e.get('aw_ground_mode',-1))!=int(state!='ground'):
                    raise ValueError('Entity support mode disagrees with classified source')
                if (e['classname']=='aw_corpse')!=(state=='authored_dead'):
                    raise ValueError('Death pose/classification mismatch')
                point=tuple(map(float,e['origin'].split()));angles=tuple(map(float,e.get('angles','0 0 0').split()))
                if len(point)!=3 or len(angles)!=3 or not all(map(math.isfinite,point+angles)):
                    raise ValueError('Invalid actor transform')
                target=owner(maps,path.stem,point);row['owner']=target
                identity=e.get('aw_ref') or ('intro:'+e.get('aw_intro_role',''))
                key=(target,identity)
                if identity in map_seen:raise ValueError('Duplicate placed reference inside one scene')
                map_seen.add(identity)
                if path.stem==target:owner_seen.add(key)
                signature=(row['source_id'],row['model'],point,angles,state)
                if key in placements:
                    if signature!=placements[key]:raise ValueError('Overlap copy differs from canonical placement')
                    continue
                placements[key]=signature;row['position']=point
                if state!='ground':row['status']='explicit-exception';rows.append(row);continue
                samples=contact_samples(poses(row['model']),angles,bool(float(e.get('aw_intro_role',0))))
                measured=[];failures=[]
                for local,frames in samples.items():
                    foot=tuple(point[k]+local[k] for k in range(3))
                    hit=scene(target).floor((foot[0],foot[1],foot[2]+2),6)
                    sample=dict(foot=foot,frames=sorted(set(frames)),support_status=hit['status'])
                    if hit['status']=='supported':
                        sample.update(gap=foot[2]-hit['height'],support_reference=hit['reference'])
                        if sample['gap']<-.5 or sample['gap']>1.0:failures.append(sample)
                    else:failures.append(sample)
                    measured.append(sample)
                gaps=[m['gap'] for m in measured if 'gap' in m]
                row.update(status='failed-contact' if failures else 'grounded',sample_count=len(measured),
                           minimum_gap=min(gaps) if gaps else None,maximum_gap=max(gaps) if gaps else None,
                           failures=failures)
                if failures:errors.append(dict(**{k:row[k] for k in ('map','reference','source_id')},error='Initial mesh contact outside support tolerance'))
            except (ValueError,KeyError,OSError,struct.error) as exc:
                row.update(status='invalid',error=str(exc));errors.append(row.copy())
            rows.append(row)
    if not copies:errors.append(dict(error='No actor placements found'))
    for key in placements.keys()-owner_seen:
        errors.append(dict(owner=key[0],reference=key[1],error='Canonical owner omits its actor placement'))
    return dict(format=1,status='failed' if errors else 'passed',placement_copies=copies,
                distinct_placements=len(placements),summary=dict(Counter(r['status'] for r in rows)),
                tolerance={'minimum_gap':-.5,'maximum_gap':1.0,'sole_band':.5},
                scope='Initial ground-resident idle poses, packaged point collision, explicit source classification; no moving platforms, footsteps, IK or future animation proof.',
                rows=rows,errors=errors,payload_sha256=hashes)



def tree_bytes(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(Path(root).rglob('*')) if path.is_file()}


class StageParallelTests(unittest.TestCase):
    """Scene-chain stages on the shared pool give the serial path's bytes (BUILD-IDLE-STAGES-33)."""

    def setUp(self):
        src = str(ROOT / 'src')
        order = patch.object(sys, 'path', [src] + [p for p in sys.path if p != src])
        order.start()
        self.addCleanup(order.stop)

    def town_regions(self, root, jobs, model_budget=99):
        """Run import_town.compile_regions with the map tools replaced by deterministic fakes."""
        import import_town

        def tool(command, cwd, **_):
            name = Path(command[0]).name
            target = Path(cwd) / 'terrain.bsp'
            target.write_bytes((target.read_bytes() if target.exists() else b'') + name.encode())

        def hull(base, map_path, qbsp):
            base.write_bytes(base.read_bytes() + b'+hull' + map_path.read_bytes()[:8])

        def meshes(base, out, scenery, palette, centre, jobs, references, prepared_models, **_):
            out.write_bytes(base.read_bytes() + json.dumps([references, sorted(prepared_models)]).encode())
            return {'unique_models': len(references), 'instances': len(references), 'clipnodes': 7}
        root.mkdir(parents=True, exist_ok=True)
        entries = [{'name': 'r%02d' % n, 'core': [[n, 0], [n + 1, 1]], 'coverage': n} for n in range(7)]
        context = {'entries': entries, 'index': {'refs': 3}, 'settings': {'entity_budget': 99, 'model_budget': model_budget,
                   'centre': [0, 0]}, 'grids': {}, 'terrain_wad': b'WAD', 'timings': '', 'arrival': [0, 0, 0],
                   'prepared': {1: 'a', 2: 'b'}, 'out': root, 'scene': root, 'qbsp': '/t/qbsp', 'vis': '/t/vis',
                   'light': '/t/light', 'vis_mode': 'fast', 'dry_run': False}
        with recorded_pools() as sizes, \
                patch.object(build_parallel, 'captured', lambda function, *args: (function(*args), '')), \
                patch.object(import_town.subprocess, 'run', side_effect=tool), \
                patch.object(import_town, 'select_references', lambda index, entry, settings: list(range(int(entry['name'][1:]) % 4))), \
                patch.object(import_town, 'terrain_at', lambda *a: (5,)), \
                patch.object(import_town, 'terrain_map', lambda entry, grids, settings, spawn, timings: 'map %s %s' % (entry['name'], spawn)), \
                patch.object(import_town, 'owner', lambda point, entries: 3), \
                patch.object(import_town, 'collision_coverage', lambda entry, settings: None), \
                patch.object(import_town, 'rebuild_world_hull', side_effect=hull), \
                patch.object(import_town, 'append_meshes', side_effect=meshes), \
                patch.object(import_town, 'bound_visuals', lambda raw, coverage: (raw + bytes([coverage]), {'c': coverage})):
            import_town._REGION_CONTEXT.clear()
            rows = [(entry['name'], report, messages) for entry, report, messages in import_town.compile_regions(context, jobs)]
        return rows, sizes

    def test_town_regions_compile_side_by_side_and_equal_serial(self):
        with tempfile.TemporaryDirectory() as temp:
            serial, serial_pools = self.town_regions(Path(temp) / 'a', 1)
            parallel, pools = self.town_regions(Path(temp) / 'b', 3)
            self.assertEqual(tree_bytes(Path(temp) / 'a'), tree_bytes(Path(temp) / 'b'))
        self.assertEqual(serial, parallel)
        self.assertEqual([name for name, _, _ in parallel], ['r%02d' % n for n in range(7)])
        self.assertIn(3, pools)

    def test_media_sounds_and_videos_on_one_pool_equal_serial(self):
        import prepare_media_assets as media
        import prepare_video
        assets = {f'sound/fx/s{n:02}.wav': {'source': f'sound/fx/s{n:02}.wav', 'file': f'/data/s{n:02}.wav'}
                  for n in range(9)}
        assets.update({'video/' + source: {'source': 'video/' + source, 'file': '/data/' + source}
                       for _, _, source in prepare_video.VIDEO_CATALOG[:3]})
        assets['video/extra.bik'] = {'source': 'video/extra.bik', 'file': '/data/extra.bik'}

        def sound(task):
            record, output, ffmpeg = task
            time.sleep(.01 * (hash(record['source']) % 3))
            return {'source': record['source'], 'category': 'effects', 'status': 'included',
                    'path': media.sound_output(record['source'])}

        def video(task):
            row, source, relative, lookup, output, ffmpeg = task
            if source is None:
                return row
            target = Path(output) / 'id1' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.encode())
            return dict(row, status='included', path=relative, sha256='0' * 64, bytes=len(source), source_sha256='1' * 64,
                        **({'lookup': lookup} if lookup else {}))
        outputs = {}
        for jobs in (1, 4):
            with tempfile.TemporaryDirectory() as temp, recorded_pools() as sizes, \
                    contextlib.redirect_stdout(io.StringIO()) as log, \
                    patch.object(media, 'resolve_data_files', lambda data: Path(data)), \
                    patch.object(media, 'discover', lambda data: (assets, [], [])), \
                    patch.object(media, 'lookups', lambda data, found: {'sounds': [], 'voiced_dialogue': []}), \
                    patch.object(media, 'convert_sound', side_effect=sound), \
                    patch.object(media, 'convert_video', side_effect=video):
                media.prepare(temp, Path(temp) / 'media', jobs=jobs)
                outputs[jobs] = (tree_bytes(Path(temp) / 'media'), log.getvalue(), list(sizes))
        self.assertEqual(outputs[1][:2], outputs[4][:2])
        self.assertEqual(outputs[1][2], [])
        self.assertIn(4, outputs[4][2])

    def test_gallery_dependency_prefetch_equals_serial_identities(self):
        # The gallery's start parsed every source mesh serially (about 125 s on the
        # critical path); the pool fills the same caches, so identities are unchanged.
        import build_gallery
        import gallery_cache

        class FakeDependencies(gallery_cache.Dependencies):
            files = {'meshes/b/skel.nif': ['textures/a.dds', 'textures/a.tga'], 'meshes/head.nif': ['textures/h.tga'],
                     'meshes/crea.nif': ['textures/c.dds']}
            present = {'textures/a.tga': b'a', 'textures/h.tga': b'h', 'textures/c.dds': b'c',
                       'meshes/b/skel.nif': b's', 'meshes/head.nif': b'hd', 'meshes/crea.nif': b'cr'}

            def __init__(self, data):
                self.hashes, self.meshes = {}, {}

            def read(self, name):
                return self.present.get(name)

            def mesh(self, name):
                if name not in self.meshes:
                    if name not in self.files:
                        raise ValueError('Missing gallery source mesh: ' + name)
                    self.hashes[name] = gallery_cache.digest(self.present[name])
                    self.meshes[name] = sorted({name, *self.files[name]})
                return self.meshes[name]
        specs = [{'kind': 'NPC_', 'appearance': {'skeleton': 'meshes/b/skel.nif', 'parts': [{'mesh': 'head.nif'}]}},
                 {'kind': 'CREA', 'mesh': 'crea.nif'}, {'kind': 'CREA', 'mesh': 'crea.nif'}]
        with patch.object(gallery_cache, 'Dependencies', FakeDependencies), recorded_pools() as sizes:
            build_gallery._DEPENDENCIES.clear()
            serial = FakeDependencies('/data')
            expected = [serial.for_spec(spec) for spec in specs]
            pooled = FakeDependencies('/data')
            build_gallery.prefetch_dependencies(pooled, '/data', specs, 3)
            self.assertEqual(sorted(pooled.meshes), sorted(FakeDependencies.files))  # all parsed by the pool
            self.assertEqual([pooled.for_spec(spec) for spec in specs], expected)
            self.assertEqual(pooled.hashes, serial.hashes)
        self.assertIn(3, sizes)

    def test_town_region_limit_stops_at_the_first_region_in_order(self):
        for jobs in (1, 3):
            with self.subTest(jobs=jobs), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, 'r02: inline model budget exceeded'):
                    self.town_regions(Path(temp), jobs, model_budget=1)


if __name__ == '__main__':
    unittest.main()
