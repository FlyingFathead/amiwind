"""Synthetic real-renderer torch checks. Native fixture execution stays Linux-only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class TorchLightDistanceTests(unittest.TestCase):
    def run_fixture(self, name, sources):
        with tempfile.TemporaryDirectory() as scratch:
            executable = Path(scratch) / 'torch-light-check'
            command = ['cc', '-std=gnu89', '-fsanitize=undefined,float-cast-overflow',
                       '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
                       '-Wl,--gc-sections', '-I'+str(SOURCE), str(ROOT/'tests'/name),
                       *[str(SOURCE/source) for source in (*sources, 'aw_format.c')], '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout+compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_same_world_sample_keeps_falloff_across_material_uv_density_and_skew(self):
        self.run_fixture('aga_torch_light_distance_test.c', ['r_surf.c', 'r_light.c'])

    def test_guard_diagnostics_distinguish_flames_from_admitted_lights(self):
        self.run_fixture('aga_guard_light_diagnostic_test.c', ['aw_guard_torch.c', 'mathlib.c'])
