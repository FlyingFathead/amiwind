"""Bounded section core + actual scene/reset/hand/audio transition fixtures."""
import unittest
import os
import shutil
from pathlib import Path
import test_aga_native_source as native
SOURCE=native.SOURCE

@unittest.skipIf(os.name == 'nt', 'native helper fixtures run inside Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class InteriorSectionTests(unittest.TestCase):
    def test_physical_ids_hysteresis_parser_and_legacy(self):
        native.NativeSourceTests().compile_run('aga_section_test.c',[Path(SOURCE)/'src/aw_section.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_actual_scene_section_handoff(self):
        native.NativeSourceTests().compile_run('aga_scene_test.c',[Path(SOURCE)/'src'/n for n in
            ('aw_scene.c','aw_region.c','aw_story.c','aw_state.c','mathlib.c','cl_main.c','view.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

if __name__=='__main__': unittest.main()
