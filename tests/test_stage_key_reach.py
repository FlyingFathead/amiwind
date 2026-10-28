# SPDX-License-Identifier: GPL-3.0-only
"""The stage keys of this repository in form 3 (tools/build_cache.py STAGE_TOP_FORMAT): what the v0.0.48-dev2 builds'
reuse audit found left out, and the class edit that rekeyed the CHIM stages (read only, no build)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

# chim-room-batches read these to key its resident bakes (UnitCache.open(..., __file__) of tools/prepare_area.py);
# the v0.0.48-dev2 try 5 and try 7 records were refused for them (BUILD-ROOM-BATCHES-KEY-UNDERDECLARED-48)
ROOM_BATCH_READS = ('config/surface-flattening.json', 'config/terrain-visual-cull.json', 'config/visual-offsets.json',
                    'tools/chim/seyda.py', 'tools/collision_bsp.py', 'tools/compact_bsp.py', 'tools/exterior_plan.py',
                    'tools/map_files.py', 'tools/planar_merge.py', 'tools/prepare_world_scenery.py', 'tools/routed_hull.py',
                    'tools/surface_flatten.py', 'tools/terrain_visual_cull.py', 'tools/visual_offsets.py',
                    'tools/visual_primitives.py', 'tools/world_payload.py', 'tools/world_scenery.py')


class StageKeyReachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def covered(self, script):
        python, data, uncertain = self.index.closure(ROOT / 'tools' / script)
        self.assertFalse(uncertain, script)
        return set(python) | set(data)

    def test_stage_keys_are_form_3(self):
        # form 3's reach; form 4 (BUILD-KEY-TOP-DEFAULTS-NAME-54) differs only in the import-time text
        self.assertGreaterEqual(build_cache.STAGE_TOP_FORMAT, 3)
        self.assertTrue(build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT).stage_form)

    def test_mwscript_key_covers_the_compiler_files_it_hashes(self):
        # BUILD-MWSCRIPT-KEY-UNDERDECLARED-48: compiler_identity reads every tools/mwscript/*.py
        covered = self.covered('prepare_mwscript.py')
        for path in sorted((ROOT / 'tools' / 'mwscript').glob('*.py')):
            self.assertIn(path.relative_to(ROOT).as_posix(), covered)

    def test_room_batch_key_covers_its_resident_bake_key(self):
        covered = self.covered('chim_room_batches.py')
        self.assertEqual([path for path in ROOM_BATCH_READS if path not in covered], [])

    def test_the_ground_bake_method_keys_no_chim_stage(self):
        # BUILD-STAGE-KEY-WHOLE-CLASS-48: commit 62827968 edited actor_grounding._Fitter._scene (the ground bake of
        # the image step); the CHIM stages never run it, yet "input change: sources (tools/actor_grounding.py)"
        # rekeyed chim, chim-rooms-vivec_city and chim-room-batches
        symbols = self.index._module_symbols('tools/actor_grounding.py')
        self.assertIn('_Fitter', symbols['classes'])
        self.assertNotIn('def _scene', symbols['texts'][build_cache.TOP_TEXT[3]])
        self.assertIn('def _scene', symbols['texts'][build_cache.TOP_TEXT[2]])
        for script in ('chim_build.py', 'chim_rooms.py'):
            if not (ROOT / 'tools' / script).is_file():
                continue
            reached = self.index.reached_units(ROOT / 'tools' / script) or {}
            self.assertNotIn('_Fitter._scene', reached.get('tools/actor_grounding.py', ()), script)


if __name__ == '__main__':
    unittest.main()
