"""vis threads from --jobs and the --vis fast/full builder option.

Default command lines must stay exactly as before (outputs unchanged until
structural occluders exist); full mode and the thread budget must reach the
vis invocation of every converter.
"""
import ast
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from vis_options import map_threads, vis_args, vis_kwargs  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
VIS_STEPS = {'bsp', 'interior', 'census', 'area', 'balmora', 'balmora-interiors', 'actor-contact', 'world-terrain', 'image'}


class Stop(Exception):
    pass


class VisArguments(unittest.TestCase):
    def test_default_matches_historical_command_lines(self):
        # Historical literals of prepare_balmora/prepare_area/prepare_world_regions,
        # prepare_census and rebuild_balmora_region, and prepare_bounded_world.
        self.assertEqual(vis_args('terrain.bsp', 1), ['-threads', '1', '-fast', 'terrain.bsp'])
        self.assertEqual(vis_args('room.bsp', 1), ['-threads', '1', '-fast', 'room.bsp'])
        self.assertEqual(vis_args('census.bsp', 12), ['-threads', '12', '-fast', 'census.bsp'])
        self.assertEqual(vis_args('base.bsp', 8, fast_first=True), ['-fast', '-threads', '8', 'base.bsp'])
        self.assertEqual(vis_kwargs('fast'), {})

    def test_full_mode_and_thread_budget(self):
        self.assertEqual(vis_args('terrain.bsp', 24, 'full'), ['-threads', '24', 'terrain.bsp'])
        self.assertEqual(vis_args('base.bsp', 8, 'full', fast_first=True), ['-threads', '8', 'base.bsp'])
        self.assertEqual(vis_kwargs('full'), {'vis_mode': 'full'})
        self.assertEqual([map_threads(24), map_threads(24, 24), map_threads(24, 5), map_threads(1, 8)], [24, 1, 4, 1])
        for bad in (lambda: vis_args('x.bsp', 1, 'fastest'), lambda: vis_kwargs('slow'), lambda: map_threads(0)):
            with self.assertRaises(ValueError):
                bad()

    def test_no_converter_hard_codes_a_vis_pass(self):
        """Every vis call goes through vis_args or an explicit vis_mode choice."""
        allowed = {'vis_options.py': 2, 'prepare_interior.py': 1, 'prepare_mesh_bsp.py': 1}
        for path in sorted((ROOT / 'tools').glob('*.py')):
            count = len(re.findall(r"""['"]-fast['"]""", path.read_text(encoding='utf-8')))
            with self.subTest(path=path.name):
                self.assertEqual(count, allowed.get(path.name, 0))
        for name in ('prepare_interior.py', 'prepare_mesh_bsp.py'):
            text = (ROOT / 'tools' / name).read_text(encoding='utf-8')
            self.assertRegex(text, r"\['-fast'[^\]]*\] if vis_mode=='fast' else \[")
        for name in ('import_town.py', 'prepare_area.py', 'prepare_census.py', 'prepare_world_regions.py',
                     'prepare_bounded_world.py', 'rebuild_balmora_region.py'):
            self.assertIn('vis_args(', (ROOT / 'tools' / name).read_text(encoding='utf-8'), name)

    def test_converter_clis_accept_vis_mode(self):
        for name in ('import_town.py', 'prepare_area.py', 'prepare_balmora_interiors.py',
                     'prepare_census.py', 'prepare_interior.py', 'prepare_mesh_bsp.py', 'prepare_world_regions.py',
                     'prepare_seyda_regions.py', 'build_aga.py'):
            tree = ast.parse((ROOT / 'tools' / name).read_text(encoding='utf-8'))
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'add_vis_option']
            self.assertTrue(calls, name + ' lacks --vis-mode')


class BuilderOption(unittest.TestCase):
    def steps(self, extra=()):
        import build
        args = build.parser().parse_args(list(extra))
        args.data_files = Path('/owned/Data Files'); args.sdk = Path('/sdk')
        # Automatic --jobs follows live free memory; pin it for stable comparisons.
        with patch('build_jobs.auto_jobs', return_value=4):
            return build.commands(args, TOOLS, Path('/private/run'))

    def test_default_command_lines_unchanged(self):
        default = self.steps()
        self.assertEqual(default, self.steps(['--vis', 'fast']))
        self.assertEqual(default, self.steps(['--vis-mode', 'fast']))
        for name, command in default:
            self.assertNotIn('--vis-mode', command, name)
        balmora = dict(default)['balmora']
        self.assertTrue(balmora[1].endswith('prepare_balmora.py'))
        # The only town imports of a default build are the shipped towns (BUILD-EXTRA-TOWN-OPTIN-32).
        from town_config import shipped_extra_towns
        self.assertEqual([name for name, _ in default if name.startswith('town-')],
                         ['town-' + town for town in shipped_extra_towns()])

    def test_full_reaches_every_map_converter(self):
        for name, command in self.steps(['--vis', 'full', '--extra-town', 'vivec_arena']):
            with self.subTest(step=name):
                expected = name in VIS_STEPS or name.startswith('town-')
                self.assertEqual(command.count('--vis-mode'), int(expected))
                if expected:
                    self.assertEqual(command[command.index('--vis-mode') + 1], 'full')

    def test_extra_town_joins_the_scene_chain(self):
        from build_parallel import stage_dependencies
        steps = self.steps(['--extra-town', 'vivec_arena', '--extra-town', 'vivec_arena'])
        names = [name for name, _ in steps]
        self.assertEqual(names.count('town-vivec_arena'), 1)
        self.assertEqual(names.index('town-vivec_arena'), names.index('balmora-interiors') + 1)
        command = dict(steps)['town-vivec_arena']
        self.assertTrue(command[1].endswith('import_town.py'))
        self.assertEqual(command[command.index('--town') + 1], 'vivec_arena')
        self.assertEqual(Path(command[command.index('--scene') + 1]), Path('/private/run/intro-scene'))
        deps = stage_dependencies(steps)
        self.assertEqual(deps['town-vivec_arena'], ('balmora-interiors',))
        self.assertEqual(deps['door-audio'], ('town-vivec_arena',))
        self.assertEqual(stage_dependencies(self.steps())['door-audio'], ('town-vivec_arena',))
        self.assertEqual(stage_dependencies(self.steps(['--only-core-towns']))['door-audio'], ('balmora-interiors',))
        with self.assertRaises(SystemExit):
            self.steps(['--extra-town', 'balmora'])
        # Towns blocked in config/towns.json are not offered.
        from town_config import load_registry
        for town in [t['id'] for t in load_registry()['towns'] if t.get('blocked')]:
            with self.subTest(town=town), self.assertRaises(SystemExit):
                self.steps(['--extra-town', town])


class ConverterInvocation(unittest.TestCase):
    def run_world_region(self, task_tail):
        import prepare_world_regions as world
        calls = []
        def fake_run(command, **kwargs):
            calls.append(command)
            if Path(command[0]).name == 'light':
                raise Stop
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp); (out / 'terrain.wad').write_bytes(b'wad')
            with patch.object(world, '_terrain', object()), patch.object(world, 'map_text', return_value='{}\n'), \
                 patch.object(world.subprocess, 'run', side_effect=fake_run):
                with self.assertRaises(Stop):
                    world.compile_region((out, out, {'name': 'vf0000'}, Path('/bin'), *task_tail))
        return next(c[1:] for c in calls if Path(c[0]).name == 'vis')

    def test_world_regions_vis_command(self):
        self.assertEqual(self.run_world_region(()), ['-threads', '1', '-fast', 'terrain.bsp'])
        self.assertEqual(self.run_world_region((1, 'fast')), ['-threads', '1', '-fast', 'terrain.bsp'])
        self.assertEqual(self.run_world_region((6, 'full')), ['-threads', '6', 'terrain.bsp'])

    def test_balmora_repair_passes_full_mode_only_when_requested(self):
        from test_balmora_layout_repair import LayoutTests
        import repair_balmora_maps
        for mode, expected in (('fast', {}), ('full', {'vis_mode': 'full'})):
            seen = []
            def rebuilt(cache, source, palette, entry, settings, out, bin, threads=4, **kwargs):
                seen.append(kwargs)
                out.mkdir(); p = out / (entry['name'] + '.bsp'); p.write_bytes(b'new')
                return {'candidate_path': str(p)}
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); maps, cache = LayoutTests.fixture(None, root)
                with patch.object(repair_balmora_maps, 'rebuild_cached_region', side_effect=rebuilt), \
                     patch.object(repair_balmora_maps, 'bound_visuals', side_effect=lambda raw, bounds: (raw, {})):
                    repair_balmora_maps.repair(maps, cache=cache, palette=root / 'palette', ericw_bin=root,
                                               work_dir=root / 'work', vis_mode=mode)
            self.assertTrue(seen)
            self.assertTrue(all(k == expected for k in seen), mode)

    def test_room_tasks_carry_divided_threads(self):
        import prepare_area
        captured = {}
        def fake_map(function, tasks, workers):
            captured['tasks'] = tasks; captured['workers'] = workers
            return []
        with tempfile.TemporaryDirectory() as tmp:
            scene = Path(tmp) / 'scene'; (scene / 'id1/maps').mkdir(parents=True)
            (scene / 'id1/gfx').mkdir(); (scene / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
            from player_hull import pack_lumps
            (scene / 'id1/maps/seyda.bsp').write_bytes(pack_lumps([b'{\n"aw_eye_height" "22"\n}\n\0'] + [b''] * 14))
            with patch.object(prepare_area, 'resolve_data_files', side_effect=lambda p: Path(p)), \
                 patch.object(prepare_area, 'ordered_map', side_effect=fake_map), \
                 patch.object(prepare_area, 'populate', return_value={}):
                prepare_area.prepare(tmp, scene, 'q', 'v', 'l', jobs=24, vis_mode='full')
        tasks = captured['tasks']
        self.assertTrue(tasks)
        workers = min(24, len(tasks))
        self.assertEqual(captured['workers'], workers)
        self.assertTrue(all(t[7:9] == (24 // workers, 'full') for t in tasks))
        # 10th field: the Seyda Neen rooms keep their dressing (BUILD-DRESSING-EXCLUDED-32).
        from prepare_mesh_bsp import INTERIOR_DRESSING
        self.assertTrue(all(t[9] == INTERIOR_DRESSING for t in tasks))


if __name__ == '__main__':
    unittest.main()
