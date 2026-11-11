"""Solstheim in the one open-world region table (WORLD-REGION-NAMES-VF-ONLY-64): the engine knows its frame maps
"slNNNN" (terrain IDs from AW_SOLSTHEIM_TERRAIN_BASE, the island Solstheim), and the test image's rows and region
names (tools/chim/sol_test.py) keep every base index while the frame -23,20 reports Solstheim and its region."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
from chim import sol_test  # noqa: E402

COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
PROBE = r'''
#include <stdio.h>
#include <string.h>
#include "aw_maps.h"
int main(void){
    char name[8];int t;
    if(AW_TerrainId("vf0000")!=0 || AW_TerrainId("vf1234")!=1234)return 1;
    if(AW_TerrainId("sl0000")!=AW_SOLSTHEIM_TERRAIN_BASE || AW_TerrainId("sl0007")!=AW_SOLSTHEIM_TERRAIN_BASE+7)return 2;
    if(AW_TerrainId("vf4096")>=0 || AW_TerrainId("sl4096")>=0 || AW_TerrainId("sx0001")>=0)return 3;
    t=AW_TerrainId("sl0007");AW_TerrainName(t,name);if(strcmp(name,"sl0007"))return 4;
    AW_TerrainName(42,name);if(strcmp(name,"vf0042"))return 5;
    if(strcmp(AW_IslandOf("sl0003"),"Solstheim") || strcmp(AW_IslandOf("vf0003"),"Vvardenfell") ||
       strcmp(AW_IslandOf("balmora"),"Vvardenfell"))return 6;
    if(strcmp(AW_MapName(AW_MapId("sl0002")),"sl0002") || strcmp(AW_MapTitle(AW_MapId("sl0002")),"Solstheim") ||
       strcmp(AW_MapTitle(AW_MapId("vf0002")),"Vvardenfell"))return 7;
    /* the HUD's region part: the land's name is not repeated (any land) */
    if(strcmp(AW_RegionInLand("Solstheim","Solstheim, Brodir Grove Region"),"Brodir Grove Region") ||
       strcmp(AW_RegionInLand("Vvardenfell","Vvardenfell, Somewhere Region"),"Somewhere Region") ||
       strcmp(AW_RegionInLand("Solstheim","Ascadian Isles Region"),"Ascadian Isles Region") ||
       strcmp(AW_RegionInLand("Solstheim","Solstheimish Region"),"Solstheimish Region") ||
       strcmp(AW_RegionInLand("Solstheim","Solstheim, "),"Solstheim, ") || AW_RegionInLand("Solstheim",NULL))return 8;
    puts("ok");return 0;
}
'''


def arn2(names, places, cells):
    return (b'ARN2' + struct.pack('<III', len(names), len(places), len(cells))
            + b''.join(n.ljust(64, b'\0') for n in names) + b''.join(p.ljust(64, b'\0') for p in places)
            + b''.join(struct.pack('<iiII', x, y, r, q) for (x, y), (r, q) in sorted(cells.items())))


class EngineNames(unittest.TestCase):
    @unittest.skipUnless(COMPILER, 'no C compiler')
    def test_terrain_ids_and_islands(self):
        with tempfile.TemporaryDirectory() as d:
            src, exe = Path(d) / 'probe.c', Path(d) / 'probe'
            src.write_text(PROBE)
            subprocess.run([COMPILER, '-std=gnu99', '-I', str(ROOT / 'engine/aga/src'), str(src), '-o', str(exe)],
                           check=True)
            out = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual((out.returncode, out.stdout.strip()), (0, 'ok'))


class ImageRows(unittest.TestCase):
    FRAME = {'id': 'rcm23_p20', 'cell': [-23, 20], 'origin': [-46080.0, 41984.0, 0.0],
             'core': [[-1024, -1024], [1024, 1024]]}

    def test_directory_rows(self):
        raw = sol_test.directory_rows([self.FRAME])
        self.assertEqual(raw[:4], b'AWS1')
        self.assertEqual(struct.unpack_from('<I', raw, 4)[0], 1)
        self.assertEqual(len(raw), 8 + 52)
        row = raw[8:]
        self.assertEqual(row[:8], b'sl0000\0\0')
        v = struct.unpack_from('<11f', row, 8)
        self.assertEqual(v[:3], (-46080.0, 41984.0, 0.0))
        self.assertEqual(v[3:7], (-1024.0, -1024.0, 1024.0, 1024.0))
        self.assertEqual(v[7:], (-1920.0, -1920.0, 1920.0, 1920.0))       # the cover the engine requires (896 wider)
        self.assertEqual(sol_test.map_name(0), 'sl0000')

    def test_the_frame_reports_its_region_and_base_indices_stay(self):
        none = 0xFFFFFFFF
        base = arn2([b'Ascadian Isles Region', b'West Gash Region'], [b'Balmora'],
                    {(-3, -2): (1, 0), (5, -3): (0, none)})
        layer = arn2([b'Ascadian Isles Region', b'Brodir Grove Region', b'West Gash Region'], [b'Balmora', b'Thirsk'],
                     {(-3, -2): (2, 0), (5, -3): (0, none), (-23, 20): (1, none), (-21, 21): (1, 1)})
        names, places, cells = sol_test.read_region_names(sol_test.merged_region_names(base, layer))
        self.assertEqual(names[:2], [b'Ascadian Isles Region', b'West Gash Region'])   # base indices unchanged
        self.assertEqual(names[cells[-23, 20][0]], b'Brodir Grove Region')
        self.assertEqual(cells[-23, 20][1], none)
        self.assertEqual((names[cells[-21, 21][0]], places[cells[-21, 21][1]]), (b'Brodir Grove Region', b'Thirsk'))
        self.assertEqual(cells[-3, -2], (1, 0))                                            # base rows unchanged


if __name__ == '__main__':
    unittest.main()
