import shutil
import tempfile
import unittest
from pathlib import Path
from project_version import ROOT, VERSION, check_native_versions, public_version, python_version, generate_native


class ProjectVersion(unittest.TestCase):
    def test_runtime_and_metadata_agree(self):
        self.assertEqual(check_native_versions(), VERSION)

    def test_drift_stops_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copyfile(ROOT/'VERSION', root/'VERSION')
            for name in ('src/aw_hud.c','src/aw_scene.c','src/sys_amiga.c','boot/bootcheck.asm'):
                p=root/'engine/aga'/name;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/'engine/aga'/name,p)
            p=root/'engine/aga/boot/bootcheck.asm'
            p.write_text(p.read_text().replace('include "amiwind_version.i"', 'banner: dc.b "AmiWind v0.0.1",0'))
            with self.assertRaises(ValueError):check_native_versions(root)

    def test_python_prerelease_maps_to_public_spelling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'VERSION').write_text('0.0.17-dev1\n')
            self.assertEqual(public_version(root),'0.0.17-dev1')
            self.assertEqual(python_version(root),'0.0.17.dev1')
            generate_native(root/'VERSION', root/'generated')
            self.assertIn('"0.0.17-dev1"', (root/'generated/amiwind_version.h').read_text())
            self.assertIn('Loading AmiWind v0.0.17-dev1', (root/'generated/amiwind_version.i').read_text())
