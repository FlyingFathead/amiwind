"""BUILD-STAIR-WALK-UNNAMED-MAP-36: the stair walk checks every map's standing hull before walking and names each map
that has none; the NPC gallery room is skipped by name."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import stair_walk  # noqa: E402
from player_hull import PROFILE  # noqa: E402


def bsp(entities):
    text = entities.encode('cp1252')
    head = struct.pack('<i', 29) + b''.join(struct.pack('<ii', 124, len(text) if i == 0 else 0) for i in range(15))
    return head + text


class HullPreflight(unittest.TestCase):
    def test_names_every_map_without_the_hull(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp, 'good.bsp'); good.write_bytes(bsp('{\n"classname" "worldspawn"\n"aw_hull" "%s"\n}\n' % PROFILE))
            bad = Path(tmp, 'bad.bsp'); bad.write_bytes(bsp('{\n"classname" "worldspawn"\n}\n'))
            stair_walk.hull_preflight([(str(good), None, {})])
            with self.assertRaises(ValueError) as caught:
                stair_walk.hull_preflight([(str(good), None, {}), (str(bad), None, {})])
            self.assertIn('bad.bsp', str(caught.exception))
            self.assertIn('sha256', str(caught.exception))
            self.assertNotIn('good.bsp', str(caught.exception))

    def test_gallery_room_is_not_walked(self):
        self.assertIn('charplane', stair_walk.NOT_WALKED)


if __name__ == '__main__':
    unittest.main()
