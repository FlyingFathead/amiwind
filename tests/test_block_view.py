# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import os
import re
import shutil
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


class BlockSourceContract(unittest.TestCase):
    def test_composition_uses_existing_68040_safe_math(self):
        source=(ROOT/'engine/aga/src/aw_hand_models.c').read_text(encoding='utf-8')
        source=re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
        self.assertIn('Q_SinCosDeg(',source)
        self.assertIn('Q_atan2(',source)
        self.assertNotRegex(source,r'\b(?:asin|acos|sin|cos|atan|atan2)\s*\(')

    def test_samples_include_the_authored_guard_pose_and_recovery_endpoint(self):
        import prepare_block_view as block
        times, keys = block.block_times({'shield: block start': 2.,
                                        'shield: block hit': 2.3,
                                        'shield: block stop': 3.2})
        self.assertEqual(len(times), 8)
        self.assertEqual(times[2], keys[1])
        self.assertEqual(times[-1], keys[-1])
        raw = block.pack_metadata([('nord', False, 'progs/hands/nord_m_b.mdl')],
                                  times, keys, [[0]*6]*8)
        self.assertEqual(len(raw), 372)
        self.assertEqual(struct.unpack_from('>I', raw, 16+2*28)[0], 300)

    def test_weapon_tag_table_matches_the_engine_contract(self):
        # PLAYER-GEAR-VISUAL-59: AWW1 = 8 header bytes, then stance x 28 frames x 6 big-endian 16.16 values.
        import numpy as np
        import prepare_hand_catalog as catalog
        tags = np.zeros((3, 28, 6))
        tags[2, 27] = [-5, 1.5, 2, 0, 90, -45]
        raw = catalog.pack_weapon_tags(tags)
        self.assertEqual(raw[:8], b'AWW1\x00\x03\x00\x1c')
        self.assertEqual(len(raw), 8 + 3 * 28 * 24)
        self.assertEqual(struct.unpack_from('>6i', raw, 8 + (2 * 28 + 27) * 24),
                         (-5 * 65536, 98304, 131072, 0, 90 * 65536, -45 * 65536))
        for bad in (np.zeros((3, 27, 6)), np.full((1, 28, 6), 129.), np.zeros((7, 28, 6))):
            with self.assertRaises(ValueError):
                catalog.pack_weapon_tags(bad)
        self.assertEqual(catalog.stance_path('dark elf', True, '2w'), 'progs/hands/dark_elf_f_2w.mdl')
        self.assertEqual(catalog.WEAPON_STANCES, ('1h', '2c', '2w'))
        # FIRST-PERSON-WEAPONS-56: six stances tagged (the ranged three without baked arms), as the engine reads them
        self.assertEqual(catalog.WEAPON_TAG_STANCES, ('1h', '2c', '2w', 'bow', 'xb', '1t'))
        self.assertEqual(catalog.pack_weapon_tags(np.zeros((6, 28, 6)))[5], 6)
        with self.assertRaises(ValueError):
            catalog.stance_path('nord', False, 'bow')
        self.assertIn('#define AW_HAND_STANCES 6', (ROOT / 'engine/aga/src/aw_hand_models.h').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            catalog.stance_path('nord', False, 'hh')
        source = (ROOT / 'engine/aga/src/aw_hand_models.c').read_text(encoding='utf-8')
        self.assertIn('"_1h.mdl","_2c.mdl","_2w.mdl","_bw.mdl","_xb.mdl","_1t.mdl"', source)

    def test_armed_stances_keep_the_hand_frame_contract(self):
        import prepare_hands as hands
        counts = [sum(c[3] for c in hands.stance_clips(s)) for s in ('hh', '1h', '2c', '2w')]
        self.assertEqual(counts, [28, 28, 28, 28])

    def test_block_layer_keeps_camera_and_right_hand_outside_the_left_arm_mask(self):
        import numpy as np
        import prepare_block_view as block

        def moved(x):
            m = np.eye(4)
            m[3, 0] = x
            return m

        class Source:
            N = None
            events = {'idle1h: start': 10.}
            parents = {'root': None, 'camera': 'root', 'right hand': 'root',
                       'bip01 l clavicle': 'root', 'shield bone': 'bip01 l clavicle'}
            nodes = parents

            def local(self, name, time):
                return moved(time if name == 'bip01 l clavicle' else 1.)

            def pose(self, time):
                return lambda name: moved({'root': 3., 'camera': 42., 'right hand': 80.}.get(name, time))

        layered = block.BlockSkeleton(Source())
        np.testing.assert_array_equal(layered.pose(.1)('camera'), moved(42))
        np.testing.assert_array_equal(layered.pose(.3)('right hand'), moved(80))
        self.assertAlmostEqual(layered.pose(.1)('shield bone')[3, 0], 4.1)
        self.assertAlmostEqual(layered.pose(.3)('shield bone')[3, 0], 4.3)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class BlockRuntimeNative(unittest.TestCase):
    def compile_fixture(self, fixture, source, defines=()):
        import test_aga_native_source as native
        sources=[ROOT/'engine/aga/src'/source]
        if source=='aw_hand_models.c':sources.append(ROOT/'engine/aga/src/mathlib.c')
        native.NativeSourceTests.compile_run(
            self, fixture, sources, defines=defines,
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_independent_camera_composition_and_metadata_bounds(self):
        self.compile_fixture('aga_block_view_test.c', 'aw_hand_models.c', ['AW_BLOCK_HOST_TEST'])

    def test_actual_equipment_admission_and_once_only_failure(self):
        self.compile_fixture('aga_block_runtime_test.c', 'aw_hand_models.c')

    def test_actual_renderer_state_depth_and_lighting(self):
        self.compile_fixture('aga_block_renderer_test.c', 'r_main.c')


if __name__ == '__main__':
    unittest.main()
