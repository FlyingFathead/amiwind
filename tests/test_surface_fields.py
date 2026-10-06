# SPDX-License-Identifier: GPL-3.0-only
import unittest
import test_aga_native_source as native

class SurfaceFieldsTests(unittest.TestCase):
    def test_actual_face_decoder_bounds_and_exact_generated_flags(self):
        native.NativeSourceTests().compile_run('aga_surface_fields_test.c',[],
            cflags=['-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all'])

if __name__=='__main__':unittest.main()
