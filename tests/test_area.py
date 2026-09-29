"""Starting-area boundaries, stable save IDs and BSP29 index pressure."""
import json
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from area_config import SCENES, inside
from prepare_mesh_bsp import order_face_planes


class AreaTests(unittest.TestCase):
    def test_map_registry_matches_native_save_order(self):
        header=(ROOT/'engine/aga/src/aw_maps.h').read_text()
        arrays=re.findall(r'names\[AW_MAP_COUNT\] = \{([^}]+)\}',header)
        expected=[s['map'] for s in SCENES]
        self.assertEqual(len(expected),len(set(expected)))
        self.assertEqual(expected[:3],['prison','seyda','census'])
        for array in arrays:self.assertEqual(re.findall(r'"([^"]+)"',array),expected)
        self.assertEqual([s['id'] for s in SCENES],list(range(len(SCENES))))
        self.assertTrue(all(re.fullmatch('[a-z]+',v) and len(v)<16 for v in expected))

    def test_port_and_cave_approach_are_inside_playable_rectangle(self):
        self.assertTrue(inside([-8800,-70530,0]))
        self.assertTrue(inside([-6735,-67063,0]))
        self.assertFalse(inside([-19517,-67530,0]))

    def test_visible_planes_reordered_before_wide_collision_indices(self):
        lumps=[bytearray() for _ in range(15)]
        lumps[1]=bytearray(b''.join(struct.pack('<4fi',1,0,0,i,0) for i in range(70000)))
        lumps[7]=bytearray(40)
        lumps[5]=bytearray(struct.pack('<ihh6h2H',69999,-1,-1,0,0,0,1,1,1,0,0))
        lumps[9]=bytearray(struct.pack('<iHH',3,40000,65534))
        order_face_planes(lumps,[69999,32768])
        self.assertEqual(struct.unpack_from('<H',lumps[7],0)[0],0)
        self.assertEqual(struct.unpack_from('<H',lumps[7],20)[0],1)
        self.assertEqual(struct.unpack_from('<f',lumps[1],12)[0],69999)
        self.assertEqual(struct.unpack_from('<i',lumps[5])[0],0)
        plane,left,right=struct.unpack('<iHH',lumps[9])
        self.assertEqual((left,right),(40000,65534))
        self.assertEqual(struct.unpack_from('<f',lumps[1],plane*20+12)[0],3)
