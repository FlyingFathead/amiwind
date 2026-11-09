# SPDX-License-Identifier: GPL-3.0-only
"""A stage's temporary work never lands in a folder other stages write (BUILD-STAGE-WRITES-OTHERS-OUTPUT-63).

In the v0.0.62 final the balmora-interiors stage baked its residents in intro-scene/resident-work while
chim-town-vivec_city ran beside it on the same scene; the town stage recorded those files as its outputs, the
interiors stage removed them at its end, and the resume refused the Vivec town ("old output
intro-scene/resident-work/.../a_0885fd279605.anm changed or missing"). prepare_area.populate now bakes in a fresh folder
of its own in the build's scratch (RUN/scratch, private to the run, never in a stage manifest). This test fails when the
resident work folder is inside the scene again, when two calls share it, or when builder code removes or bakes into a
fixed folder directly under a stage's --scene other than the listed persistent ones."""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

# Folders directly under a shared --scene that builder code may name as constants: each is a stage's persistent output
# (read by later stages), never a temporary work folder.
PERSISTENT_SCENE_FOLDERS = {
    'area-work': 'room builds, read by chim_room_batches, balmora interiors, the harvest rooms and the estimates',
    'id1': 'the scene payload itself',
    'opening-barrel-source': 'read by tools/night_lighting.py (the --scene opening barrel directory)',
    'town-flora': 'install_town_flora default only; the image step passes its own work_dir under its output',
    'harvest-source': 'prepare_harvest_room: its own one-room scene',
    'harvest-payload': 'prepare_harvest_room: its own one-room scene',
    'door-delta': 'prepare_harvest_room: its own one-room scene',
    'census-source': 'listed 2026-11-09 when this test was made; its owner not yet checked (BUILD-STAGE-WRITES-OTHERS-'
                     'OUTPUT-63)',
}
SCENE_FOLDER = re.compile(r"\bscene\s*/\s*['\"]([A-Za-z0-9_.-]+)['\"]")


class StageOwnOutputs(unittest.TestCase):
    def test_resident_work_is_in_the_run_scratch_and_never_shared(self):
        import prepare_area
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            scene = run / 'intro-scene'
            scene.mkdir()
            with mock.patch.dict(os.environ, {'AMIWIND_SCRATCH': str(run / 'scratch')}):
                first = prepare_area.resident_work_folder(scene, 'balmora-interiors.json')
                second = prepare_area.resident_work_folder(scene, 'vivec_city-interiors.json')
                third = prepare_area.resident_work_folder(scene)
            for folder in (first, second, third):
                self.assertTrue(folder.is_dir())
                self.assertEqual(folder.parent, run / 'scratch')
                self.assertNotIn(scene, folder.parents)
            self.assertEqual(len({first, second, third}), 3)
            with mock.patch.dict(os.environ, {'AMIWIND_RESIDENT_WORK': 'scene'}):
                self.assertEqual(prepare_area.resident_work_folder(scene), scene / 'resident-work')

    def test_no_fixed_work_folder_under_a_shared_scene(self):
        found = []
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                if 'AMIWIND_RESIDENT_WORK' in line:
                    continue   # the earlier method, selectable on purpose
                for name in SCENE_FOLDER.findall(line):
                    if name not in PERSISTENT_SCENE_FOLDERS and '.' not in name:
                        found.append('%s:%d %s' % (path.relative_to(ROOT).as_posix(), number, name))
        self.assertEqual(found, [], 'a fixed folder under a shared --scene: bake temporary work in tools/build_scratch.py '
                                    'scratch, or list a persistent output in PERSISTENT_SCENE_FOLDERS with its reader')


if __name__ == '__main__':
    unittest.main()
