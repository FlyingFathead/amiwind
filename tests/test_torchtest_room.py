# SPDX-License-Identifier: GPL-3.0-only
"""Compile the actual procedural room; check its lightmaps and collision hull."""
import os
from pathlib import Path
import struct
import tempfile
import unittest

from build_torchtest import build, validate
from player_hull import lumps, pack_lumps

TOOLS = Path(os.environ['ERICW_BIN']) if os.environ.get('ERICW_BIN') else None


@unittest.skipIf(os.name == 'nt', 'compiler checks run in Linux Docker')
@unittest.skipUnless(TOOLS and all((TOOLS/name).is_file() for name in ('qbsp','vis','light')),
                     'set ERICW_BIN to the cached BSP tools')
class TorchTestRoomTests(unittest.TestCase):
    def test_compiled_enclosed_room_has_zero_samples_and_source_sized_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);palette=root/'palette.lmp'
            palette.write_bytes(bytes(v for i in range(256) for v in (i,i,i)))
            output=root/'id1/maps/torchtest.bsp'
            report=build(palette,output,root/'work',*(TOOLS/name for name in ('qbsp','vis','light')))
            data=lumps(output.read_bytes())
            self.assertGreaterEqual(report['faces'],6)
            self.assertGreater(report['lighting_bytes'],0)
            self.assertFalse(any(data[8]))
            self.assertLess(len(output.read_bytes()),65536)
            # Actual generated clipnodes/planes, not invented room dimensions.
            planes=list(struct.iter_unpack('<4fi',data[1]))
            nodes=list(struct.iter_unpack('<ihh',data[9]))
            head=struct.unpack_from('<i',data[14],40)[0]
            def contents(point):
                node=head;seen=set()
                while node>=0:
                    self.assertNotIn(node,seen);seen.add(node)
                    pi,front,back=nodes[node];plane=planes[pi]
                    distance=sum(point[i]*plane[i] for i in range(3))-plane[3]
                    node=front if distance>=0 else back
                return node
            for point in ((64,0,17),(0,0,64),(120,0,17),(0,0,110)):
                self.assertEqual(contents(point),-1,point)
            for point in ((64,0,16),(122,0,17),(-122,0,17),(0,90,17),(0,-90,17),(0,0,112)):
                self.assertEqual(contents(point),-2,point)
            # Refuse the two common false-darkness cases and invalid offsets.
            original=bytearray(data[8]);data[8]=bytearray()
            with self.assertRaisesRegex(ValueError,'nonempty'):validate(pack_lumps(data))
            data[8]=original;data[8][0]=1
            with self.assertRaisesRegex(ValueError,'all-zero'):validate(pack_lumps(data))
            data[8][0]=0;struct.pack_into('<i',data[7],16,-1)
            with self.assertRaisesRegex(ValueError,'light samples'):validate(pack_lumps(data))
