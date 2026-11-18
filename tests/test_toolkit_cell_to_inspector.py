# SPDX-License-Identifier: GPL-3.0-only
"""The World Map opens a cell of the CHIM open world in the 3D Inspector (TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67).

On a cell the newest build holds on CHIM, the Local view offers the frame that holds it (the tracker's memory audit names
it; a town frame holds its neighbours; a sea cell without the audit is found by its cell), and Show in 3D opens that frame
of the served build's world in the inspector; on a cell with nothing to open the button says why when clicked; served
without island-cells.json, the Local view shows the tracker's record instead of asking for a file by hand. The Toolkit page
hands such a link to its 3D Inspector tab. The page scripts run under Node.js with inert DOM stubs, on synthetic data."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'amiwind-toolkit'


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable; the page checks need an existing interpreter')
class CellToInspectorTests(unittest.TestCase):
    def test_the_world_map_opens_a_cell_in_3d(self):
        r = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / 'test_toolkit_cell_to_inspector.js'), str(KIT)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('cell to inspector ok', r.stdout)


class CellToInspectorSourceTests(unittest.TestCase):
    def test_the_inspector_takes_a_link_and_a_cell(self):
        page = (KIT / 'map-inspector.html').read_text(encoding='utf-8')
        self.assertIn("e.data.type==='amiwind-open-link'", page)
        self.assertIn("q.get('cell')", page)
        self.assertIn('R.frameHolding(chim.world', page)

    def test_the_files_ship_in_the_release(self):
        import json
        listed = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for name in ('tests/test_toolkit_cell_to_inspector.py', 'tests/test_toolkit_cell_to_inspector.js'):
            self.assertIn(name, listed)


if __name__ == '__main__':
    unittest.main()
