"""Real save/write/restore with synthetic catalogues and VM model rebinding."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipIf(os.name == 'nt', 'Native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class SavedEquipmentTests(unittest.TestCase):
    def test_actual_save_write_restore_and_corrupt_intent(self):
        src=ROOT/'engine/aga/src'
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            (work/'saves/p00000002').mkdir(parents=True)
            binary=work/'saved-equipment'
            subprocess.run(['cc','-std=gnu99','-O1','-g','-ffunction-sections','-fdata-sections',
                '-Wl,--gc-sections','-fsanitize=address,undefined','-fno-sanitize-recover=all',
                '-I'+str(src),str(ROOT/'tests/aga_saved_equipment_test.c'),
                *(str(src/n) for n in ('aw_character.c','aw_state.c','aw_save_codec.c')),
                '-lm','-o',str(binary)],check=True,capture_output=True,text=True)
            run=subprocess.run([str(binary),str(work)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__ == '__main__': unittest.main()
