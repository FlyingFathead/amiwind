"""Real renderer cache arena regression, including eviction and map teardown."""
import os
from pathlib import Path
import shutil
import unittest
import test_aga_native_source as native

@unittest.skipIf(os.name == 'nt', 'runtime fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
class SurfaceCacheListTests(unittest.TestCase):
    def test_cache_ownership_and_rendered_pixels(self):
        native.NativeSourceTests.compile_run(self, 'aga_surface_cache_list_test.c',
            [Path(native.SOURCE)/'src/d_surf.c'], standard='gnu99',
            cflags=['-O2', '-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_cache_flush_precedes_map_hunk_release(self):
        text=(Path(native.SOURCE)/'src/host.c').read_text()
        body=text[text.index('void Host_ClearMemory (void)'):]
        self.assertLess(body.index('D_FlushCaches ();'),body.index('Mod_ClearAll ();'))
        self.assertLess(body.index('D_FlushCaches ();'),body.index('Hunk_FreeToLowMark (host_hunklevel)'))

if __name__ == '__main__':unittest.main()
