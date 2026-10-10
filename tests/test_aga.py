"""Host checks for the native display conversion; no game data required."""
import ctypes
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DisplayTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_native_c2p_against_pixel_oracle(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'exec').mkdir();(p/'graphics').mkdir()
            (p/'exec/types.h').write_text('#include <stdint.h>\ntypedef uint32_t ULONG; typedef uint8_t UBYTE; typedef uint16_t UWORD;\n')
            (p/'graphics/gfx.h').write_text('struct BitMap {UWORD BytesPerRow; UWORD Rows; UBYTE Flags, Depth; UWORD pad; unsigned char *Planes[8];};\n')
            so=p/'c2p.so'
            subprocess.run(['cc','-shared','-fPIC','-O2','-I'+str(p),str(ROOT/'engine/aga/src/aw_c2p.c'),'-o',str(so)],check=True)
            lib=ctypes.CDLL(str(so))
            class Bitmap(ctypes.Structure):
                _fields_=[('bytes_per_row',ctypes.c_uint16),('rows',ctypes.c_uint16),('flags',ctypes.c_uint8),
                          ('depth',ctypes.c_uint8),('pad',ctypes.c_uint16),('planes',ctypes.POINTER(ctypes.c_uint8)*8)]
            rng=random.Random(3100)
            # Unpadded rows (stride = width/8) and rows padded for the fetch
            # mode (ENGINE-C2P-ROWSTRIDE-35): padding bytes stay untouched.
            for width,rows,stride in ((256,33,32),(360,20,48),(320,7,64)):
                pixels=bytes(range(256))[:width]+bytes(rng.randrange(256) for _ in range(width*rows-min(width,256)))
                src=(ctypes.c_uint8*len(pixels)).from_buffer_copy(pixels)
                planes=[(ctypes.c_uint8*(stride*rows))(*([0xA5]*(stride*rows))) for _ in range(8)]
                bm=Bitmap(stride,rows,0,8,0,(ctypes.POINTER(ctypes.c_uint8)*8)(*planes))
                lib.aw_c2p(None,ctypes.byref(bm),src,ctypes.c_uint32(width),ctypes.c_uint32(rows))
                for plane in range(8):
                    expected=b''.join(
                        bytes(sum(((pixels[r*width+n+j]>>plane)&1)<<(7-j) for j in range(8)) for n in range(0,width,8))
                        +bytes([0xa5])*(stride-width//8) for r in range(rows))
                    self.assertEqual(bytes(planes[plane]),expected,(width,stride,plane))

class PerformanceGateTests(unittest.TestCase):
    def setUp(self):
        import sys,copy
        sys.path.insert(0,str(ROOT/'tools'))
        import profile_aga
        self.mod=profile_aga
        self.baseline={'context':{k:'same' for k in profile_aga.MATCH_FIELDS},
                       'sampled_p95_frame_us':20000,'frame':{'worst_frame_us':30000,'heap_used_bytes':4000000,'audio_late_updates':1,'missed_audio_frames':100},
                       'music':{'read_errors':0},'adjacent_track_repeats':0,'average_fps':50}
        self.candidate=copy.deepcopy(self.baseline)

    def test_refuses_mismatched_machine(self):
        self.candidate['context']['effective_machine']='different'
        with self.assertRaisesRegex(ValueError,'effective_machine'):self.mod.compare(self.baseline,self.candidate)

    def test_catches_pacing_and_audio_regression(self):
        self.candidate['sampled_p95_frame_us']=25000
        self.candidate['frame']['missed_audio_frames']=200
        r=self.mod.compare(self.baseline,self.candidate)
        self.assertFalse(r['passed']);self.assertEqual(set(r['regressions']),{'sampled_p95_frame_us','missed_audio_frames'})

    def test_accepts_identical_baseline(self):
        self.assertTrue(self.mod.compare(self.baseline,self.candidate)['passed'])

    def test_rejects_missing_geometry_even_if_frame_rate_improves(self):
        self.candidate['average_fps']=100
        self.candidate['frame']['surface_overflow_frames']=1
        result=self.mod.compare(self.baseline,self.candidate)
        self.assertFalse(result['passed'])
        self.assertIn('surface_overflow_frames',result['regressions'])

class StartupDependencyTests(unittest.TestCase):
    def setUp(self):
        import sys
        sys.path.insert(0, str(ROOT/'tools'))
        from check_aga_binary import check_binary
        self.check = check_binary
        self.header = bytes.fromhex('000003f3')

    def test_rejects_old_icon_autoload(self):
        with self.assertRaisesRegex(ValueError, 'icon.library'):
            self.check(self.header + b'\0icon.library\0graphics.library\0')

    def test_rejects_workbench_autoload(self):
        with self.assertRaisesRegex(ValueError, 'workbench.library'):
            self.check(self.header + b'\0Workbench.Library\0')

    def test_accepts_core_libraries(self):
        self.assertEqual(self.check(self.header + b'dos.library\0graphics.library\0')['desktop_library_check'], 'passed')
