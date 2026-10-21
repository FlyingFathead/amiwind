"""No new *.bsp-only map listing in tools/ (GUARD-TORCH-CHIM-FRAMES-44).

CHIM frame maps are maps/<name>.chim since v0.0.36 (tools/map_files.py). A tool that lists a maps folder with
its own glob('*.bsp') misses every town and region frame without a word. Tools list maps with
map_files.map_files (or frame_maps where only frames count). The listings below are the deliberate *.bsp-only
ones, each with its reason; any other, or one more in the same file, fails here.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# a glob/rglob whose pattern literal ends in .bsp, or a suffix compared with '.bsp'
LISTING = re.compile(r"""\.r?glob\([^)\n]*\.bsp['"]|\.suffix(?:\.lower\(\))?\s*==\s*['"]\.bsp['"]""")

ALLOWED = {
    'tools/actor_grounding.py': (2, 'annotates and fits actors on legacy map collision; a frame map is an empty '
                                    'world, its residents are fitted on the CHIM frame by the chim-town stage'),
    'tools/analyze_subcell_redundancy.py': (1, 'measures legacy sub-cell maps (sn/bm prefix) only'),
    'tools/asset_census.py': (1, 'bakes: lightmaps of interior maps; frame maps are exterior and hold no faces'),
    'tools/build_aga.py': (1, 'empty MiniWind evidence: proves no legacy map but torchtest is staged'),
    'tools/check_actor_ground.py': (1, 'frame residents are judged by their town stage fit (chim_frames, '
                                       'BUILD-ACTOR-GATE-CHIM-FRAMES-36), not on the empty frame world'),
    'tools/check_scene_actors.py': (1, 'the scene stage (before the image) holds legacy maps only'),
    'tools/chim/frame_map.py': (1, "a town's legacy region maps (<prefix>NNN), the frame map's sources"),
    'tools/chim_town.py': (1, "a town's legacy region maps (<prefix>NNN), the frame map's sources"),
    'tools/exterior_sky_build.py': (1, 'frame maps get their sky keys when written (frame_exterior, '
                                       'chim_town_rows); rewriting them here would break the optimizer receipt'),
    'tools/harvest_build.py': (1, 'interior_rows: interior rooms are BSP maps; a CHIM frame map (.chim) is an exterior '
                                  'frame and holds no interior placement (HARVEST-INTERIOR-PICK-47)'),
    'tools/hand_metadata.py': (1, "frame maps get the hand fields when written (hand_metadata's worldspawn_fields)"),
    'tools/hidden_surface_build.py': (1, 'frame maps hold no render faces (their geometry is the CHIM world)'),
    'tools/miniwind.py': (2, "prunes the scene's legacy maps; the frame maps are written after it"),
    'tools/night_windows.py': (1, 'CLI: classifies the glass faces of town map geometry; frame maps hold none '
                                  '(NIGHT-WINDOWS-LOST-CHIM-36)'),
    'tools/optimize_world_maps.py': (2, 'optimizes legacy BSPs; frame maps join unoptimized (rebind_chim_maps)'),
    'tools/repair_terrain_material.py': (1, 'one-off repair of the legacy Balmora maps (balmora, bmNNN)'),
    'tools/world_estimate_sample.py': (1, 'its own freshly compiled sample maps'),
    # pending: fixed on the release line (map_files); this entry goes when that fix is merged here
}


def listings():
    """{tools-relative path: number of *.bsp-only listings} over every Python file under tools/."""
    found = {}
    for path in sorted((ROOT / 'tools').rglob('*.py')):
        count = len(LISTING.findall(path.read_text(encoding='utf-8', errors='replace')))
        if count:
            found[path.relative_to(ROOT).as_posix()] = count
    return found


class MapListingGuard(unittest.TestCase):
    def test_no_new_bsp_only_listing(self):
        new = {name: count for name, count in listings().items() if count > ALLOWED.get(name, (0, ''))[0]}
        self.assertEqual(new, {}, 'a *.bsp-only map listing misses the CHIM frame maps (x.chim): list maps with '
                                  'map_files.map_files (tools/map_files.py), or add the file to ALLOWED with '
                                  'the reason frame maps must not be read there')

    def test_every_allowance_has_a_reason_and_a_file(self):
        for name, (count, reason) in ALLOWED.items():
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertGreater(count, 0, name)
            self.assertTrue(reason.strip(), name)

    def test_the_pattern_catches_the_known_forms(self):
        for text in ("sorted(maps.glob('*.bsp'))", 'p.glob("*.bsp")', "game.glob('maps/*.bsp')",
                     "(id1 / 'maps').glob(row['prefix'] + '[0-9][0-9][0-9].bsp')", "p.rglob('*.bsp')",
                     "p.suffix.lower() == '.bsp'"):
            self.assertTrue(LISTING.search(text), text)
        for text in ("map_files(maps)", "glob('*.chim')", "name.endswith('.bsp')"):
            self.assertFalse(LISTING.search(text), text)


if __name__ == '__main__':
    unittest.main()
