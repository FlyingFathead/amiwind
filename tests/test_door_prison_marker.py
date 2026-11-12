# SPDX-License-Identifier: GPL-3.0-only
"""DOOR-PRISON-MARKER-65: a prison marker is never a door.

The original stores the jail's destination as a door record (PrisonMarker); the world door table keeps it out of its
door tables (tools/world_doors.py, MARKER_IDS), but the opening's Seyda Neen door table listed reference 474482 as a door
labelled Census and Excise Office, and using it put the player on the jail spot under the census office floor. The
engine refuses any door table row whose reference is one of the image's prison markers (prison-markers.txt)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


class PrisonMarkerNeverADoorTests(unittest.TestCase):
    def test_the_door_table_reader_skips_a_prison_marker(self):
        scene = code('aw_scene.c')
        self.assertIn('int (*aw_door_is_marker)(unsigned long ref);', scene)
        reader = scene[scene.index('static void read_links_for(const char *map) {'):]
        reader = reader[:reader.index('r.bounds=1;links[count++]=r;')]
        self.assertIn('if(version==3 && aw_door_is_marker && aw_door_is_marker(r.reference)){', reader)

    def test_the_crime_layer_knows_the_markers_from_the_image(self):
        crime = code('aw_crime.c')
        self.assertIn('static int prison_marker(unsigned long ref){', crime)
        self.assertIn('if(n<0)n=markers_read(m,MARKERS);', crime)
        self.assertIn('aw_door_is_marker=prison_marker;', crime)

    def test_the_world_door_table_keeps_markers_out_of_its_door_tables(self):
        import world_doors
        self.assertIn('prisonmarker', world_doors.MARKER_IDS)
        self.assertEqual(world_doors.kind({'id': 'PrisonMarker'}), 'marker')
        self.assertEqual(world_doors.kind({'id': 'chargen exit door'}), 'door')


if __name__ == '__main__':
    unittest.main()
