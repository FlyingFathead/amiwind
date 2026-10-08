"""No silent drops in the mesh converter (BUILD-DRESSING-EXCLUDED-32).

v0.0.32-dev1's Census and Excise Office lost a lantern hook that v0.0.31 shipped:
append_meshes skipped dressing meshes (lantern hooks, ropes, ...) without a word
in the conversion receipt. Every placement handed to the converter must now be
placed (an entity carrying its aw_ref) or listed in the result's "omitted" with
the rule that removed it.
"""
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from player_hull import pack_lumps  # noqa: E402


def assemble(root, sources, retain_dressing=False):
    """One small face per model through append_meshes; one reference per model."""
    from prepare_mesh_bsp import append_meshes
    polygon = np.array([[0., 0., 0.], [32., 0., 0.], [32., 32., 0.], [0., 32., 0.]])
    axes = np.array([[1/64, 0], [0, 1/64], [0, 0.]])
    data = (np.column_stack((polygon * 4, np.zeros((4, 2)))), np.array([[0, 1, 3, 0]]),
            [(polygon, 0, axes, np.array([0., 0.]), np.array([0., 0, 1]))], [], {})
    models = [dict(source=s, triangles=2, materials=[dict(texture_index=None, diffuse=[1, 1, 1])]) for s in sources]
    refs = [dict(number=i + 1, id='ref%d' % (i + 1), model_index=i, scale=1, position=[i * 64, 0, 0],
                 rotation_radians=[0, 0, 0]) for i in range(len(sources))]
    (root/'scenery-index.json').write_text(json.dumps(dict(cell='Synthetic interior', models=models,
                                                           textures=[], references=refs)))
    (root/'scenery.mwpak').write_bytes(b'')
    (root/'palette.lmp').write_bytes(bytes(range(256)) * 3)
    sections = [b''] * 15
    sections[0] = b'{\n"classname" "worldspawn"\n}\n\0'
    sections[2] = struct.pack('<i', 0)
    sections[10] = struct.pack('<i', -1) + bytes(24)
    sections[14] = bytes(64)
    (root/'base.bsp').write_bytes(pack_lumps(sections))
    lighting = dict(ambient=[40, 40, 40], lights=[])
    result = append_meshes(root/'base.bsp', root/'out.bsp', root, root/'palette.lmp', centre=(0, 0),
                           lighting=lighting, jobs=1, references=[r['number'] for r in refs],
                           prepared_models={i: data for i in range(len(sources))}, retain_dressing=retain_dressing)
    raw = (root/'out.bsp').read_bytes()
    offset, size = struct.unpack_from('<ii', raw, 4)
    placed = {int(n) for n in re.findall(rb'"aw_ref" "([0-9]+)"', raw[offset:offset + size])}
    return result, placed


class MeshOmissionReceiptTests(unittest.TestCase):
    SOURCES = ['meshes/i/in_c_plain_room_side.nif', 'meshes/f/furn_com_lantern_hook.nif',
               'meshes/f/furn_de_rope_01.nif']

    def test_every_reference_is_placed_or_receipted(self):
        with tempfile.TemporaryDirectory() as directory:
            result, placed = assemble(Path(directory), self.SOURCES)
        omitted = {row['reference']: row for row in result['omitted']}
        self.assertEqual(placed, {1})
        self.assertEqual(set(omitted), {2, 3})
        self.assertEqual(placed | set(omitted), {1, 2, 3})
        self.assertIn('lantern_hook', omitted[2]['reason'])
        self.assertIn('furn_de_rope', omitted[3]['reason'])
        self.assertEqual(omitted[2]['model'], self.SOURCES[1])

    def test_retained_dressing_is_placed_and_nothing_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            result, placed = assemble(Path(directory), self.SOURCES, retain_dressing=True)
        self.assertEqual(placed, {1, 2, 3})
        self.assertEqual(result['omitted'], [])

    def test_interior_rule_keeps_dressing_but_not_markers_and_tracks_it(self):
        import prepare_mesh_bsp as m
        sources = self.SOURCES + ['meshes/f/flora_bc_fern_02.nif', 'meshes/m/marker_north.nif']
        with tempfile.TemporaryDirectory() as directory:
            result, placed = assemble(Path(directory), sources, retain_dressing=m.INTERIOR_DRESSING)
        self.assertEqual(placed, {1, 2, 3, 4})
        self.assertEqual([(r['reference'], r['reason']) for r in result['omitted']],
                         [(5, 'dressing excluded by the mesh converter (marker_)')])
        self.assertEqual([(r['reference'], r['rule']) for r in result['dressing_retained']],
                         [(2, 'lantern_hook'), (3, 'furn_de_rope'), (4, 'flora_')])

    def test_interior_default_keeps_dressing_and_skip_option_restores_the_earlier_rule(self):
        import argparse
        import prepare_mesh_bsp as m
        parser = argparse.ArgumentParser(); m.add_dressing_option(parser)
        try:
            m.apply_dressing_option(parser.parse_args([]))
            self.assertEqual(m.interior_dressing(), m.INTERIOR_DRESSING)
            self.assertNotIn('marker_', m.INTERIOR_DRESSING)
            m.apply_dressing_option(parser.parse_args(['--skip-dressing']))
            self.assertEqual(m.interior_dressing(), ())
            with tempfile.TemporaryDirectory() as directory:
                result, placed = assemble(Path(directory), self.SOURCES, retain_dressing=m.interior_dressing())
            self.assertEqual(placed, {1})
        finally:
            m.apply_dressing_option(parser.parse_args([]))

    def test_guided_build_passes_skip_dressing_to_the_interior_steps_only(self):
        import build
        tools = {n: '/opt/' + n for n in ('qbsp', 'vis', 'light', 'qcc', 'xdftool', 'rdbtool', 'ffmpeg')}
        base = ['--data-files', '/data', '--workspace', '/ws', '--name', 'r', '--sdk', '/sdk', '--jobs', '2']
        plain = dict(build.commands(build.parser().parse_args(base), tools, Path('/run')))
        skip = dict(build.commands(build.parser().parse_args(base + ['--skip-dressing']), tools, Path('/run')))
        for name in plain:
            extra = [a for a in skip[name] if a not in plain[name]]
            self.assertEqual(extra, ['--skip-dressing'] if name in ('interior', 'census', 'area') else [], name)
        self.assertTrue(all('--skip-dressing' not in c for c in plain.values()))

    def test_interior_converters_merge_the_converter_omissions(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('prepare_census.py', 'prepare_interior.py', 'prepare_area.py'):
            source = (root/'tools'/name).read_text(encoding='utf-8')
            self.assertIn("omitted+report['omitted']", source.replace(' ', '').replace('"', "'"), name)


if __name__ == '__main__':
    unittest.main()
