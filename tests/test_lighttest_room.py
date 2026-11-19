# SPDX-License-Identifier: GPL-3.0-only
"""The light test corridor (LIGHTTEST-MAP-67, tools/build_lighttest.py): compiled as the image step does, a long dark
corridor with nothing in it but the player's start, every light sample zero (only the held light lights it), long
enough for the 20-second walk; the torch test room beside it stays as it was; and the engine enters it, starts a
waiting walk or the item tester there, and leaves it."""
import os
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
TOOLS = Path(os.environ['ERICW_BIN']) if os.environ.get('ERICW_BIN') else None
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='latin-1'), flags=re.S)


class Wiring(unittest.TestCase):
    def test_the_image_step_builds_it_beside_the_torch_room(self):
        build = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertLess(build.index('build_torchtest('), build.index('build_lighttest('))
        self.assertIn("boot/'id1/maps/torchtest.bsp'", build)              # the torch room is kept
        self.assertIn("boot/'id1/maps/lighttest.bsp'", build)
        self.assertIn("'light_test':lighttest_report", build)
        self.assertNotIn('itemtest', build)

    def test_the_engine_start_is_the_maps_start(self):
        from build_lighttest import HALF_LENGTH, START
        header = (SRC / 'aw_cycleitems.h').read_text(encoding='latin-1')
        self.assertIn('#define AW_LIGHTTEST_START_X %d' % START[0], header)
        self.assertLess(-HALF_LENGTH, START[0])
        # the 20 s walk stays inside even at a run of 150 units a second
        self.assertGreater(HALF_LENGTH - START[0], 20 * 150)

    def test_the_engine_enters_runs_and_leaves_the_corridor(self):
        gallery = code('aw_gallery.c')
        self.assertIn('light_test?"map lighttest\\n"', gallery)
        self.assertIn('if(light_test){light_center(p);combat_pose(p,1);AW_LightTestReady();return;}', gallery)
        self.assertIn('int AW_LightTestActive(void){return light_test && session && sv.active && '
                      '!strcmp(sv.name,"lighttest");}', gallery)
        self.assertIn('if(light_test)return;', gallery)                    # no actor, nothing else spawned
        tester = code('aw_cycleitems.c')
        self.assertIn('AW_GalleryLightTestEnter()', tester)
        self.assertIn('AW_GalleryLightTestLeave();', tester)
        # a carried light is lit in the corridor (the gallery otherwise turns the torch off)
        self.assertIn('!AW_LightTestActive()', code('aw_torch.c'))
        self.assertIn('!strcmp(sv.name,"lighttest")', code('aw_scene.c'))
        # dark like the torch room: no gameplay light scaling
        self.assertIn('strcmp(name,"lighttest")', (SRC / 'aw_interior_light_policy.h').read_text(encoding='latin-1'))


@unittest.skipIf(os.name == 'nt', 'compiler checks run in Linux Docker')
@unittest.skipUnless(TOOLS and all((TOOLS/name).is_file() for name in ('qbsp', 'vis', 'light')),
                     'set ERICW_BIN to the cached BSP tools')
class Corridor(unittest.TestCase):
    def test_compiled_dark_empty_corridor_to_walk(self):
        from build_lighttest import HALF_LENGTH, HALF_WIDTH, HEIGHT, START, build, validate
        from player_hull import lumps, pack_lumps
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            palette = root/'palette.lmp'
            palette.write_bytes(bytes(v for i in range(256) for v in (i, i, i)))
            output = root/'id1/maps/lighttest.bsp'
            report = build(palette, output, root/'work', *(TOOLS/name for name in ('qbsp', 'vis', 'light')))
            raw = output.read_bytes()
            data = lumps(raw)
            self.assertGreaterEqual(report['faces'], 6)
            self.assertTrue(data[8] and not any(data[8]))                  # dark: every sample zero
            self.assertLess(len(raw), 262144)
            entities = bytes(data[0])
            self.assertEqual(entities.count(b'"classname"'), 2)            # worldspawn and the player start only
            self.assertIn(b'"_minlight" "0"', entities)
            planes = list(struct.iter_unpack('<4fi', data[1]))
            nodes = list(struct.iter_unpack('<ihh', data[9]))
            head = struct.unpack_from('<i', data[14], 40)[0]

            def contents(point):
                node, seen = head, set()
                while node >= 0:
                    self.assertNotIn(node, seen)
                    seen.add(node)
                    pi, front, back = nodes[node]
                    plane = planes[pi]
                    node = front if sum(point[i]*plane[i] for i in range(3)) - plane[3] >= 0 else back
                return node
            for point in (START, (0, 0, 17), (HALF_LENGTH-24, 0, 17), (0, HALF_WIDTH-24, 17), (0, 0, HEIGHT-20)):
                self.assertEqual(contents(point), -1, point)
            for point in ((0, 0, -2), (HALF_LENGTH+8, 0, 17), (-HALF_LENGTH-8, 0, 17), (0, -HALF_WIDTH-8, 17),
                          (0, 0, HEIGHT+8)):
                self.assertEqual(contents(point), -2, point)
            data[8] = bytearray(b'\x01') + data[8][1:]
            with self.assertRaisesRegex(ValueError, 'all-zero'):
                validate(pack_lumps(data))


if __name__ == '__main__':
    unittest.main()
