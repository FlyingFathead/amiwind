# SPDX-License-Identifier: GPL-3.0-only
"""Builder stage entries accept what tools/build.py passes them, and run.

BUILD-ACTOR-CONTACT-CALL-32: the actor-contact stage called the Seyda region
conversion with a signature two releases old; only a from-scratch build with
the owner's data reached it. These tests reach every stage entry without data:
each stage script parses the exact command line the builder generates, and the
actor-contact stage runs end to end on a synthetic scene with only the heavy
calls replaced by signature-checked stand-ins.
"""
import argparse
import ast
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
VARIANTS = ([], ['--extra-town', 'vivec_foreign', '--vis', 'full', '--tree-sprites'],
            ['--no-npc-gallery', '--no-tree-sprites', '--only-core-towns'])


def builder_steps(run, data, extra=()):
    import build
    args = build.parser().parse_args(list(extra))
    args.data_files = Path(data)
    args.sdk = Path('/sdk')
    return build.commands(args, TOOLS, Path(run))


class Parsed(Exception):
    pass


def parse_only(script, argv):
    """Run a stage script as __main__ up to its argument parsing; return the result."""
    parse_args = argparse.ArgumentParser.parse_args
    parse_known = argparse.ArgumentParser.parse_known_args
    depth = [0]

    def outer_parse(self, args=None, namespace=None):
        depth[0] += 1
        try:
            result = parse_args(self, args, namespace)
        finally:
            depth[0] -= 1
        raise Parsed(result)

    def outer_known(self, args=None, namespace=None):
        if depth[0]:
            return parse_known(self, args, namespace)
        depth[0] += 1
        try:
            result = parse_known(self, args, namespace)
        finally:
            depth[0] -= 1
        raise Parsed(result)

    with patch.object(sys, 'argv', [str(script), *map(str, argv)]), \
         patch.object(argparse.ArgumentParser, 'parse_args', outer_parse), \
         patch.object(argparse.ArgumentParser, 'parse_known_args', outer_known):
        try:
            runpy.run_path(str(script), run_name='__main__')
        except Parsed as parsed:
            return parsed.args[0]
        except SystemExit as exc:
            raise AssertionError(f'{script.name} rejected the builder command line (exit {exc.code})') from None
    raise AssertionError(f'{script.name} finished without parsing its command line')


class StageCommandLines(unittest.TestCase):
    def test_every_stage_parses_its_builder_command_line(self):
        seen = set()
        for extra in VARIANTS:
            for name, command in builder_steps('/private/run', '/owned/Data Files', extra):
                script = Path(command[1])
                self.assertEqual(script.parent, ROOT / 'tools', name)
                with self.subTest(stage=name, variant=' '.join(extra)):
                    parse_only(script, command[2:])
                seen.add(name)
        for required in ('bsp', 'actor-contact', 'image', 'town-vivec_arena', 'town-vivec_foreign', 'world-flora'):
            self.assertIn(required, seen)


class ActorContactStage(unittest.TestCase):
    def test_stage_entry_runs_on_a_synthetic_scene(self):
        import check_scene_actors
        import prepare_seyda_regions
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run, data = tmp / 'run', tmp / 'Data Files'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(b'')
            scene = run / 'intro-scene'
            for folder in ('progs', 'maps', 'gfx'):
                (scene / 'id1' / folder).mkdir(parents=True)
            (scene / 'id1/progs/player.mdl').write_bytes(b'mdl')
            (scene / 'id1/maps/sncourt.bsp').write_bytes(b'room')
            (scene / 'id1/maps/vf0001.bsp').write_bytes(b'world tile')
            (scene / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
            (scene / 'seyda.bsp').write_bytes(b'town')
            (scene / 'seyda.map').write_text('{\n"classname" "worldspawn"\n}\n', newline='\n')
            command = dict(builder_steps(run, data))['actor-contact']
            self.assertEqual(Path(command[1]).name, 'check_scene_actors.py')
            # autospec: a call that no longer matches a signature fails here.
            with patch.object(prepare_seyda_regions, 'convert', autospec=True, return_value={}) as convert, \
                 patch.object(check_scene_actors, 'annotate', autospec=True, return_value={}), \
                 patch.object(check_scene_actors, 'bake_ground', autospec=True, return_value={}), \
                 patch.object(check_scene_actors, 'require', autospec=True,
                              return_value={'acceptance': {'actors': 0}}) as require, \
                 patch.object(sys, 'argv', [command[1], *command[2:]]):
                check_scene_actors.main()
            out = run / 'actor-contact'
            convert.assert_called_once()
            args, kwargs = convert.call_args
            self.assertEqual(args, (out / 'id1/maps/seyda.bsp', out / 'id1/maps'))
            self.assertEqual(kwargs['source_map'], scene / 'seyda.map')
            self.assertEqual(kwargs['palette'], scene / 'id1/gfx/palette.lmp')
            self.assertEqual(kwargs['ericw_bin'], Path(TOOLS['qbsp']).parent)
            self.assertEqual(kwargs['canonical_land_source'], run / 'world-survey/terrain-source.npz')
            self.assertEqual(kwargs['vis_mode'], 'fast')
            require.assert_called_once()
            self.assertTrue((out / 'id1/maps/sncourt.bsp').is_file())
            self.assertFalse((out / 'id1/maps/vf0001.bsp').exists())
            self.assertEqual((out / 'actor-ground-acceptance.json').read_text(), '{\n  "actors": 0\n}\n')

    def test_image_and_actor_contact_share_one_region_call(self):
        for name in ('build_aga.py', 'check_scene_actors.py'):
            tree = ast.parse((ROOT / 'tools' / name).read_text(encoding='utf-8'))
            imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                        and node.module == 'prepare_seyda_regions' for alias in node.names}
            with self.subTest(tool=name):
                self.assertIn('convert_builder_scene', imported)
                self.assertNotIn('convert', imported)

    def test_shared_region_call_forwards_to_convert(self):
        import prepare_seyda_regions
        with patch.object(prepare_seyda_regions, 'convert', autospec=True, return_value={'ok': 1}) as convert:
            result = prepare_seyda_regions.convert_builder_scene(
                Path('/m'), scene_map=Path('/s.map'), palette=Path('/p.lmp'), ericw_bin=Path('/e'),
                work_dir=Path('/w'), canonical_land_source=Path('/t.npz'), vis_mode='full')
        self.assertEqual(result, {'ok': 1})
        convert.assert_called_once_with(Path('/m/seyda.bsp'), Path('/m'), source_map=Path('/s.map'),
                                        palette=Path('/p.lmp'), ericw_bin=Path('/e'),
                                        jobs=None, work_dir=Path('/w'),
                                        vis_mode='full', canonical_land_source=Path('/t.npz'))


if __name__ == '__main__':
    unittest.main()
