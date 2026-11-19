# SPDX-License-Identifier: GPL-3.0-only
"""The shared-sky check of the CHIM frame maps (tools/frame_sky_check.py): every frame map the image step writes names
the shared exterior sky as open_world_worldspawn (tools/chim/frame_map.py) writes it, checked the moment the image step
has passed (tools/build_preflight.py EARLY_CHECKS, phase after:image). Fixture maps only: a BSP29 header and its entity
lump, the part of a map the check reads."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build_preflight  # noqa: E402
import frame_sky_check as S  # noqa: E402
from chim.frame_map import entity_text, open_world_worldspawn  # noqa: E402

SKY = {'_aw_sky_mode': 'exterior', '_aw_sky_asset': 'gfx/aw_shared_sky.lmp'}


def bsp(rows):
    """A BSP29 file holding only its header and entity lump (lump 0 right after the 15-lump directory)."""
    lump = entity_text(rows)
    return struct.pack('<i', 29) + struct.pack('<ii', 124, len(lump)) + bytes(14 * 8) + lump


def frame(cell='-23 20', **keys):
    return dict(open_world_worldspawn({}), _chim_frame=cell, **keys)


class FrameMapsWithoutSky(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lines = []

    def maps(self, folder, files):
        folder.mkdir(parents=True, exist_ok=True)
        for name, row in files.items():
            (folder / name).write_bytes(bsp([row, {'classname': 'info_player_start', 'origin': '0 0 24'}]))
        return folder

    def test_the_keys_checked_are_the_ones_open_world_worldspawn_writes(self):
        self.assertEqual(S.wanted_keys(), SKY)

    def test_a_frame_map_without_either_key_or_with_another_value_is_named(self):
        bare = {k: v for k, v in frame().items() if k not in SKY}
        folder = self.maps(self.root / 'maps', {
            'vf1637.chim': frame(),                                         # a region frame map as written
            'sl0000.chim': dict(frame('-23 20'), message='Solstheim', _chim_world='chimsol', _chim_edge='closed'),
            'sl0001.chim': dict(bare, _chim_world='chimsol'),               # neither key
            'sl0002.chim': dict(frame(), _aw_sky_mode='interior'),          # the interior black
            'sl0003.chim': {k: v for k, v in frame().items() if k != '_aw_sky_asset'},
            'vf1638.bsp': {'classname': 'worldspawn', 'message': 'Vvardenfell'},   # not a frame map: not read
            'room.chim': {'classname': 'worldspawn', '_chim_room': 'r0001'},       # a room map: not read
        })
        self.assertEqual(S.frame_maps_without_sky(folder), [
            ('sl0001.chim', ['_aw_sky_mode missing', '_aw_sky_asset missing']),
            ('sl0002.chim', ['_aw_sky_mode is "interior", not "exterior"']),
            ('sl0003.chim', ['_aw_sky_asset missing'])])
        self.assertEqual(S.frame_maps_without_sky(self.root / 'none'), [])
        self.assertEqual(S.main([str(folder)]), 1)

    def test_the_check_after_the_image_step_reads_its_frame_maps(self):
        run = self.root / 'run'
        context = build_preflight.EarlyContext('after:image', run=run, steps=['image'], log=self.lines.append)
        self.assertEqual(S.frame_map_sky_after(context), [])                 # no maps folder: nothing to check
        folder = self.maps(run / 'image' / 'boot' / 'id1' / 'maps', {'vf1637.chim': frame()})
        self.assertEqual(S.frame_map_sky_after(context), [])
        self.assertIn('names the shared exterior sky', self.lines[-1])
        self.maps(folder, {'sl0001.chim': {k: v for k, v in frame().items() if k != '_aw_sky_mode'}})
        problems = S.frame_map_sky_after(context)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith('1 CHIM frame map in image/boot/id1/maps does not name the shared '
                                               'exterior sky'), problems[0])
        self.assertIn('sl0001.chim (_aw_sky_mode missing)', problems[0])

    def test_a_long_list_is_cut_with_a_count(self):
        found = [('m%02d.chim' % i, ['_aw_sky_mode missing']) for i in range(S.SHOWN + 3)]
        text = S.problem_text(found, 'maps')
        self.assertTrue(text.startswith('%d CHIM frame maps in maps do not name' % (S.SHOWN + 3)), text)
        self.assertTrue(text.endswith('; and 3 more'), text)

    def test_it_is_registered_after_the_image_step(self):
        self.assertIn(('frame-map-sky', 'after:image', 'frame_sky_check:frame_map_sky_after'),
                      build_preflight.EARLY_CHECKS)
        run = self.root / 'run'
        self.maps(run / 'image' / 'boot' / 'id1' / 'maps', {'sl0001.chim': dict(frame(), _aw_sky_asset='gfx/x.lmp')})
        problems = build_preflight.after_stage_problems('image', run, log=self.lines.append)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith('frame-map-sky: 1 CHIM frame map'), problems[0])
        self.assertIn('_aw_sky_asset is "gfx/x.lmp", not "gfx/aw_shared_sky.lmp"', problems[0])


if __name__ == '__main__':
    unittest.main()
