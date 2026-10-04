# SPDX-License-Identifier: GPL-3.0-only
import tempfile
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from cull_bsp_hidden import cull_bsp
from test_cull_bsp_hidden import fixture
from compact_bsp import entities
from player_hull import lumps, pack_lumps
from replace_bsp_world import rows
from exterior_sky_build import transform, configure_staged_maps, sky_pixels


def sky_fixture():
    data = lumps(fixture())
    blob = struct.pack('<16s6I', b'sky', 256, 128, 40, 32808, 41000, 43048) + bytes([17]) * 43520
    old = bytes(data[2][8:])
    data[2] = bytearray(struct.pack('<iii', 2, 12, 12 + len(old)) + old + blob)
    data[6] += struct.pack('<8f2i', 1, 0, 0, 0, 0, 1, 0, 0, 1, 0)
    # World and pool sky faces; opaque static shell remains untouched.
    struct.pack_into('<h', data[7], 10, 1)
    struct.pack_into('<h', data[7], 7 * 20 + 10, 1)
    data[5] = bytearray(struct.pack('<i2h6h2H', 0, -1, -1, 0, 0, 0, 5, 5, 5, 0, 8))
    return pack_lumps(data)


class ExteriorSkyTests(unittest.TestCase):
    def test_normal_build_options_reach_image_command(self):
        import build
        for extra, expected in (([], 'false'), (['--local-skybox', 'true', '--shared-sky-source', '/owned/sky.lmp'], 'true')):
            args = build.parser().parse_args(extra)
            args.data_files = Path('/owned')
            args.sdk = Path('/sdk')
            tools = {k: '/tools/' + k for k in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
            steps = dict(build.commands(args, tools, Path('/private/run')))
            image = steps['image']
            self.assertEqual(image[image.index('--local-skybox') + 1], expected)
            if extra:
                self.assertEqual(image[image.index('--shared-sky-source') + 1], str(args.shared_sky_source.resolve()))
            self.assertNotIn('--local-skybox', steps['engine'])

    def test_direct_image_parser_preserves_defaults_and_override(self):
        import build_aga
        required = ['--sdk', '/sdk', '--data-files', '/owned', '--no-npc-gallery', '--world-scenery', '/scenery']
        for key in ('scene', 'music', 'engine', 'out', 'qcc', 'qbsp', 'vis', 'light', 'xdftool', 'rdbtool'):
            required += ['--' + key, '/' + key]
        for extra, expected in (([], 'false'), (['--local-skybox', 'true'], 'true')):
            with patch('sys.argv', ['build_aga.py', 'image', *required, *extra]), patch.object(build_aga, 'image') as image:
                build_aga.main()
                self.assertEqual(image.call_args.args[0].local_skybox, expected)

    def test_catalogue_interior_classification_does_not_guess_unknown(self):
        from build_aga import staged_interior_map_names, staged_exterior_map_names
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'maps').mkdir()
            for name in ('prison', 'seyda', 'unknown'):
                (root / 'maps' / (name + '.bsp')).write_bytes(b'fixture')
            self.assertEqual(staged_interior_map_names(root), {'prison'})
            self.assertEqual(staged_exterior_map_names(root), {'seyda'})

    def test_remove_world_and_inline_sky_and_remap_pool(self):
        raw = sky_fixture()
        output, receipt = transform(raw, scene_kind='exterior')
        self.assertEqual(receipt['removed_face_ids'], [0, 7])
        self.assertEqual(receipt['stored_faces_after'], 6)
        before, after = lumps(raw), lumps(output)
        for i in (1, 2, 3, 4, 6, 8, 9, 12, 13):
            self.assertEqual(before[i], after[i])
        self.assertEqual(after[7], before[7][20:140])
        self.assertEqual(rows(after)[5][0][9:11], [0, 6])
        self.assertEqual(rows(after)[14][3][15], 0)
        self.assertEqual(rows(after)[10][0][9], 0)
        es = entities(after[0])
        self.assertEqual(es[0]['_aw_sky_mode'], 'exterior')
        self.assertTrue(all('aw_render_ranges' not in e for e in es))

    def test_debug_keeps_faces_shared_metadata(self):
        raw = sky_fixture()
        out, receipt = transform(raw, scene_kind='exterior', local_skybox=True)
        self.assertEqual(lumps(out)[7], lumps(raw)[7])
        self.assertEqual(receipt['removed_sky_faces'], 0)
        self.assertEqual(entities(lumps(out)[0])[0]['_aw_sky_mode'], 'exterior')

    def test_interior_keeps_geometry_and_disables_background(self):
        raw = sky_fixture()
        out, receipt = transform(raw, scene_kind='interior')
        self.assertEqual(lumps(out)[7], lumps(raw)[7])
        self.assertEqual(entities(lumps(out)[0])[0]['_aw_sky_mode'], 'interior')

    def test_resource_pixels_and_unknown_maps(self):
        raw = sky_fixture()
        self.assertEqual(sky_pixels(raw), [bytes([17]) * 32768])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maps = root / 'id1' / 'maps'
            maps.mkdir(parents=True)
            for name in ('outside', 'inside', 'unknown'):
                (maps / (name + '.bsp')).write_bytes(raw)
            receipt = configure_staged_maps(root / 'id1', exterior_maps=['outside'], interior_maps=['inside'], work_dir=root / 'work')
            self.assertEqual(receipt['removed_sky_faces'], 2)
            self.assertEqual(receipt['unknown_maps_preserved'], ['unknown'])
            self.assertEqual((maps / 'unknown.bsp').read_bytes(), raw)
            self.assertEqual((root / 'id1/gfx/aw_shared_sky.lmp').read_bytes(), bytes([17]) * 32768)
            self.assertEqual((root / 'work/originals/outside.bsp').read_bytes(), raw)

    def test_conflicting_resources_fail_before_staging_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maps = root / 'id1/maps'
            maps.mkdir(parents=True)
            raw = sky_fixture()
            other = raw.replace(bytes([17]) * 43520, bytes([18]) * 43520)
            (maps / 'a.bsp').write_bytes(raw)
            (maps / 'b.bsp').write_bytes(other)
            with self.assertRaises(ValueError):
                configure_staged_maps(root / 'id1', exterior_maps=['a', 'b'], work_dir=root / 'work')
            self.assertEqual((maps / 'a.bsp').read_bytes(), raw)
            self.assertFalse((root / 'work').exists())

    def test_invalid_settings_and_ranges_reject(self):
        raw = sky_fixture()
        for kwargs in ({'scene_kind': 'unknown'}, {'scene_kind': 'exterior', 'local_skybox': 'yes'}):
            with self.assertRaises(ValueError):
                transform(raw, **kwargs)
        data = lumps(raw)
        data[0] = bytearray(bytes(data[0]).replace(b'0:1', b'0:2'))
        with self.assertRaises(ValueError):
            transform(pack_lumps(data), scene_kind='exterior')


if __name__ == '__main__':
    unittest.main()
