"""Real alias raster depth versus wider arithmetic; synthetic geometry only."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(os.environ.get('AMIWIND_TEST_ROOT',Path(__file__).resolve().parents[1]))
SOURCE=ROOT/'engine/aga/src'


def wide_reference(source):
    """Keep scan conversion intact, but widen every depth value and operation.

    This oracle does not wrap intermediate depth. It checks that every active
    pixel is representable before comparing exact framebuffer and depth bytes.
    It deliberately changes the private span layout; it is never a target build.
    """
    source=re.sub(r'int\s+sfrac, tfrac, light, zi;',
                  'int sfrac, tfrac, light; long long zi;',source)
    source=re.sub(r'int\s+r_zistepx, r_zistepy;','long long r_zistepx, r_zistepy;',source)
    source=re.sub(r'int\s+d_sfrac, d_tfrac, d_light, d_zi;',
                  'int d_sfrac, d_tfrac, d_light; long long d_zi;',source)
    source=re.sub(r'int\s+d_ziextrastep, d_zibasestep;','long long d_ziextrastep, d_zibasestep;',source)
    source=re.sub(r'int\s+lzi;','long long lzi;',source)
    source=source.replace('r_zistepx = AW_AliasDepthStep(','r_zistepx = (long long)(')
    source=source.replace('r_zistepy = AW_AliasDepthStep(','r_zistepy = (long long)(')
    source='\n'.join(line.replace('(unsigned int)','')
                     if any(name in line for name in ('d_zi','r_zistep','lzi =')) else line
                     for line in source.splitlines())+'\n'
    source=source.replace('if ((lzi >> 16) >= *lpz)',
                          'if(lzi<0 || lzi>2147483647LL) abort();\n\t\t\t\tif ((lzi >> 16) >= *lpz)')
    return source


@unittest.skipIf(os.name=='nt','native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'),'requires C compiler')
class AliasDepthTests(unittest.TestCase):
    def test_skinny_and_near_clipped_triangles_match_wide_pixel_depth(self):
        span=Path(os.environ.get('AMIWIND_DEPTH_SOURCE',SOURCE/'d_polyse.c'))
        fixture=Path(os.environ.get('AMIWIND_DEPTH_FIXTURE',ROOT/'tests/aga_alias_depth_test.c'))
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder);wide=tmp/'wide.c';wide.write_text(wide_reference(span.read_text()))
            outputs=[]
            for label,path in [('target-arithmetic',span),('wide-reference',wide)]:
                exe=tmp/label
                command=['cc','-std=gnu89','-fsanitize=address,undefined,float-cast-overflow',
                         '-fno-sanitize=alignment','-fno-sanitize-recover=all',
                         '-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
                         '-I'+str(SOURCE),str(fixture),str(path),str(SOURCE/'r_aclip.c'),
                         str(SOURCE/'mathlib.c'),'-lm','-o',str(exe)]
                built=subprocess.run(command,capture_output=True)
                self.assertEqual(built.returncode,0,built.stderr.decode(errors='replace'))
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
                self.assertFalse(result.stderr,result.stderr.decode(errors='replace'))
                self.assertEqual(len(result.stdout),168*320*200*3)
                outputs.append(result.stdout)
            self.assertEqual(outputs[0],outputs[1])
