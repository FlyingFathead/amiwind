"""Sea cells the newest CHIM build holds get their own class on the World Map: "sea, in the game (CHIM)", the sea colour with
diagonal stripes (tools/cell_progress.py mark_sea_in_game, amiwind-toolkit/world-map.html chimCls, chim-head.js, chim-legend.js)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cell_progress as cp  # noqa: E402

KIT = ROOT / 'amiwind-toolkit'


def cell(land, bucket, builds=()):
    return {'land': land, 'chim': {'bucket': bucket, 'on_chim_builds': list(builds)}}


class SeaInGameTests(unittest.TestCase):
    def test_flags_only_sea_cells_the_newest_build_holds(self):
        cells = {
            '-15,-8': cell(False, 'empty_sea', ['v47']),             # sea, in the game
            '1,1': cell(False, 'ocean', ['v47']),                    # open ocean the build carries: in the game too
            '2,2': cell(False, 'empty_sea', []),                     # empty sea not in the game: unchanged
            '3,3': cell(False, 'ocean', ['v46']),                    # held by an older build only
            '4,4': cell(True, 'audits_passed', ['v47']),     # land: never flagged
            '5,5': cell(False, 'converted_failing', ['v47']),        # failing keeps its colour
        }
        self.assertEqual(cp.mark_sea_in_game(cells, 'v47'), 2)
        flagged = sorted(k for k, c in cells.items() if c['chim'].get('sea_in_game'))
        self.assertEqual(flagged, ['-15,-8', '1,1'])
        self.assertEqual(cells['-15,-8']['chim']['bucket'], 'empty_sea')     # buckets and the done figures do not move

    def test_no_build_or_rerun_clears_the_flag(self):
        cells = {'0,0': cell(False, 'empty_sea', ['v47'])}
        cp.mark_sea_in_game(cells, 'v47')
        self.assertTrue(cells['0,0']['chim']['sea_in_game'])
        self.assertEqual(cp.mark_sea_in_game(cells, None), 0)
        self.assertNotIn('sea_in_game', cells['0,0']['chim'])

    def test_page_draws_the_class_and_old_data_keeps_its_colouring(self):
        page = (KIT / 'world-map.html').read_text(encoding='utf-8')
        # grouped data: the cell's state; older data: the sea flag, else the bucket
        self.assertIn("function chimCls(c) { return c.chim.state || (c.chim.sea_in_game ? 'sea_in_game' : c.chim.bucket); }", page)
        self.assertIn("sea_in_game: ['#2f7fa6',", page)
        self.assertIn("'#7dffa6'],", page)                          # the stripe colour (third entry draws the stripes)
        self.assertIn("new Set(['empty_sea', 'ocean', 'sea_in_game'])", page)
        # only the CSV / JSON export reads the data bucket directly
        self.assertEqual(page.count('c.chim.bucket'), 3)         # chimCls, the eligible filter and the export
        head = (KIT / 'chim-head.js').read_text(encoding='utf-8')
        self.assertIn("'sea, in the game (CHIM)'", head)
        self.assertIn('repeating-linear-gradient(135deg,#2f7fa6', head)
        self.assertIn("h.sea_in_game != null", head)                 # older data: no chip
        self.assertIn("'sea_in_game'", (KIT / 'chim-legend.js').read_text(encoding='utf-8'))
        self.assertIn("head['sea_in_game'] = mark_sea_in_game(", (ROOT / 'tools' / 'cell_progress.py').read_text(encoding='utf-8'))


class PaintSeaCellsTests(unittest.TestCase):
    """Paint and the rectangle select reach every cell the tracker knows, sea cells included, and a paint stroke can be
    undone (button and Ctrl+Z) (TOOLKIT-PAINT-SEA-CELLS-48)."""
    def test_paint_uses_the_tracker_cells_and_has_undo(self):
        page = (KIT / 'world-map.html').read_text(encoding='utf-8')
        self.assertIn('chimCells.has(k)', page)
        self.assertIn('if (!paintable(x, y)) return;', page)
        self.assertIn('if (!paintable(i, j)) continue;', page)
        self.assertNotIn('const {x, y, c} = cellAt(e); if (!c) return;', page)
        self.assertIn('<button id="undocells"', page)
        self.assertIn("$('undocells').onclick = paintUndoLast;", page)
        self.assertIn('paintSave(multi); paint = {', page)


if __name__ == '__main__':
    unittest.main()
