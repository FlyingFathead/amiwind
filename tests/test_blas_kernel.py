"""One BLAS kernel family for builds and tests (TESTS-HEAD-REDUCER-BYTES-CI-45): OpenBLAS picks its kernels by the
processor, and kernel families round the NPC bake's matrix work differently, which changed baked skin bytes from
one processor to the next. The builder and the test runner pin the family before NumPy loads; caches key on it."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import blas_kernel  # noqa: E402


class BlasKernelTests(unittest.TestCase):
    def test_pin_sets_the_family_on_a_capable_processor(self):
        environ = {}
        with patch.object(blas_kernel, 'cpu_supports_pinned', return_value=True):
            self.assertEqual(blas_kernel.pin(environ), 'Haswell')
        self.assertEqual(environ, {'OPENBLAS_CORETYPE': 'Haswell'})

    def test_an_explicit_choice_wins(self):
        environ = {'OPENBLAS_CORETYPE': 'SkylakeX'}
        with patch.object(blas_kernel, 'cpu_supports_pinned', return_value=True):
            self.assertEqual(blas_kernel.pin(environ), 'SkylakeX')
        self.assertEqual(environ['OPENBLAS_CORETYPE'], 'SkylakeX')

    def test_an_incapable_processor_stays_unpinned_and_says_why(self):
        environ = {}
        with patch.object(blas_kernel, 'cpu_supports_pinned', return_value=False):
            self.assertIsNone(blas_kernel.pin(environ))
            with self.assertRaisesRegex(ValueError, 'AVX2'):
                blas_kernel.pinned_environment({})
        self.assertEqual(environ, {})

    def test_key_names_the_kernel(self):
        with patch.dict(os.environ, {'OPENBLAS_CORETYPE': 'Haswell'}):
            pinned = blas_kernel.key()
        with patch.dict(os.environ, {'OPENBLAS_CORETYPE': 'SkylakeX'}):
            other = blas_kernel.key()
        self.assertIn('OPENBLAS_CORETYPE=Haswell', pinned)
        self.assertNotEqual(pinned, other)

    def test_builder_pins_before_its_first_import(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertLess(text.index('blas_kernel.pin()'), text.index('\nimport '))

    def test_test_runner_pins_for_its_workers(self):
        text = (ROOT / 'tools/run_tests.py').read_text(encoding='utf-8')
        main = text.index('def main(')
        self.assertLess(text.index('blas_kernel.pin()', main), text.index("'--worker'", main))

    def test_bake_caches_key_on_the_kernel(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        import gallery_cache
        with patch.dict(os.environ, {'OPENBLAS_CORETYPE': 'Haswell'}):
            pinned = gallery_cache.environment()
        with patch.dict(os.environ, {'OPENBLAS_CORETYPE': 'SkylakeX'}):
            other = gallery_cache.environment()
        self.assertNotEqual(pinned['blas'], other['blas'])
        source = (ROOT / 'tools/npc_lod.py').read_text(encoding='utf-8')
        self.assertIn('blas_kernel.key()', source[source.index('def code_identity'):])


if __name__ == '__main__':
    unittest.main()
