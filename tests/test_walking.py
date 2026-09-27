"""Synthetic terrain conversion checks; these do not benchmark the 68000."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("walk_builder", Path(__file__).resolve().parents[1] / "tools/prepare_walk.py")
walker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(walker)


def fixture():
    return [{"cell": [x, y], "heights": [[16 * ((x + 3) * 64 + ix)
             for ix in range(65)] for _ in range(65)]}
            for y in range(-10, -7) for x in range(-3, 0)]


class WalkingTests(unittest.TestCase):
    def prepare(self, root, grids):
        (root / "terrain-source.json").write_text(json.dumps(grids))
        (root / "converted").mkdir(exist_ok=True)
        return walker.prepare_walk(root, root)

    def test_cell_seams_and_world_scale(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            result = self.prepare(p, fixture())
            vertices = (p / "walking-assets.i").read_text().split("walk_vertices:\n")[1].split("solid_palette:")[0]
            values = [tuple(map(int, line.split("dc.w ")[1].split(","))) for line in vertices.splitlines()]
            self.assertEqual(len(values), 1089)
            self.assertEqual(values[11], (528, 0, 66))  # Beyond first cell seam.
            self.assertEqual(values[-1], (1536, 1536, 192))
            self.assertEqual(result["spacing_world_units"], 768)
            self.assertEqual((p / "converted/walk-hud.planes").stat().st_size, 32000)
            self.assertEqual(result["solid_grid"], [97, 97])

    def test_rejects_duplicate_or_missing_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            for grids in (fixture()[:-1], fixture() + [fixture()[0]]):
                with self.assertRaises(ValueError):
                    self.prepare(Path(tmp), grids)

    def test_sea_clamp_and_unsafe_heights(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            grids = fixture()
            grids[0]["heights"][0][0] = -100
            self.prepare(p, grids)
            self.assertIn("dc.w 0,0,0\n", (p / "walking-assets.i").read_text())
            for height in (float("nan"), 20000):
                grids[0]["heights"][0][0] = height
                with self.assertRaises(ValueError):
                    self.prepare(p, grids)

    def test_fine_grid_range_checked_between_coarse_vertices(self):
        with tempfile.TemporaryDirectory() as tmp:
            grids = fixture()
            grids[0]["heights"][2][2] = 20000  # Absent from the old stride-six lattice.
            with self.assertRaises(ValueError):
                self.prepare(Path(tmp), grids)


if __name__ == "__main__":
    unittest.main()
