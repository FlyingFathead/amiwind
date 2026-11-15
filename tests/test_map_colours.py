# SPDX-License-Identifier: GPL-3.0-only
"""MAP-ORIGINAL-POI-66 (a): the world map's OpenMW land colours from the cells' WNAM heights (tools/prepare_world_ui.py),
behind AMIWIND_MAP_COLOURS; the default stays the terrain overview."""
import os
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prepare_world_ui as ui  # noqa: E402


def land(x, y, wnam):
    def sub(tag, data):
        return tag.encode() + struct.pack('<I', len(data)) + data
    payload = sub('INTV', struct.pack('<ii', x, y)) + sub('WNAM', struct.pack('<81b', *wnam))
    return b'LAND' + struct.pack('<III', len(payload), 0, 0) + payload


class MapColourTests(unittest.TestCase):
    def test_the_switch_defaults_to_the_terrain_overview(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ui.MAP_COLOURS_VARIABLE, None)
            self.assertEqual(ui.map_colours(), 'terrain')
            self.assertEqual(ui.map_colours('openmw'), 'openmw')
        with mock.patch.dict(os.environ, {ui.MAP_COLOURS_VARIABLE: 'openmw'}):
            self.assertEqual(ui.map_colours(), 'openmw')
        with self.assertRaises(ValueError):
            ui.map_colours('bright')

    def test_the_table_follows_openmws_stops(self):
        self.assertEqual(ui.openmw_map_colour(0), (24, 36, 33))
        self.assertEqual(ui.openmw_map_colour(127), (37, 55, 50))
        self.assertEqual(ui.openmw_map_colour(128), (66, 48, 33))
        self.assertEqual(ui.openmw_map_colour(141), (40, 29, 20))
        self.assertEqual(ui.openmw_map_colour(255), (5, 5, 5))
        land_red = [ui.openmw_map_colour(i)[0] for i in range(128, 256)]
        self.assertEqual(land_red, sorted(land_red, reverse=True))   # higher land is darker
        for bad in (-1, 256):
            with self.assertRaises(ValueError):
                ui.openmw_map_colour(bad)

    def test_wnam_cells_are_painted_north_up_nine_pixels_each(self):
        sea = [-128] * 81
        hill = [0] * 81
        hill[8 * 9 + 0] = 127                     # the cell's north-west texel (last WNAM row is north)
        master = land(0, 0, sea) + land(1, 0, hill) + land(5, 5, hill)
        heights = ui.wnam_heights(master)
        self.assertEqual(sorted(heights), [(0, 0), (1, 0), (5, 5)])
        picture = ui.wnam_picture(heights, (0, 0, 2, 1))
        self.assertEqual(picture.size, (18, 9))
        self.assertEqual(picture.getpixel((4, 4)), ui.openmw_map_colour(0))
        self.assertEqual(picture.getpixel((13, 4)), ui.openmw_map_colour(128))
        self.assertEqual(picture.getpixel((9, 0)), ui.openmw_map_colour(255))   # north-west of cell 1,0 at the top
        self.assertEqual(picture.getpixel((9, 8)), ui.openmw_map_colour(128))
        empty = ui.wnam_picture({}, (0, 0, 1, 1))
        self.assertEqual(empty.getpixel((0, 0)), ui.openmw_map_colour(0))       # no LAND: sea
        with self.assertRaises(ValueError):
            ui.wnam_picture({}, (0, 0, 0, 1))


class MapColourKeyTests(unittest.TestCase):
    def test_flipping_the_switch_changes_the_world_ui_and_image_keys(self):
        """The world-ui stage and the image step (build_aga.py runs prepare_image) read AMIWIND_MAP_COLOURS, so the
        stage environment that keys them changes with it; a cached terrain map is never reused for the OpenMW colours."""
        import build_cache
        root = Path(__file__).resolve().parents[1]
        index = build_cache.SourceIndex()
        for script in ('prepare_world_ui.py', 'build_aga.py'):
            path = root / 'tools' / script
            self.assertIn(ui.MAP_COLOURS_VARIABLE, index.environment_names(path), script)
            with mock.patch.dict(os.environ, {ui.MAP_COLOURS_VARIABLE: 'openmw'}):
                on = build_cache.stage_environment(path, index)
            with mock.patch.dict(os.environ, {ui.MAP_COLOURS_VARIABLE: 'terrain'}):
                self.assertNotEqual(on, build_cache.stage_environment(path, index), script)


if __name__ == '__main__':
    unittest.main()
