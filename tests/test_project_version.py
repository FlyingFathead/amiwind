import shutil
import tempfile
import unittest
from pathlib import Path
from project_version import ROOT, VERSION, check_native_versions, public_version, python_version, generate_native


class ProjectVersion(unittest.TestCase):
    def test_runtime_and_metadata_agree(self):
        self.assertEqual(check_native_versions(), VERSION)

    def test_release_versions_refuse_private_test_waivers(self):
        # VIVEC-ARENA-ACTORS-32: a waived image can only be a -devN private test.
        from project_version import require_private_test_version
        require_private_test_version('0.0.32-dev1', ['--allow-known-actor-ground-findings'])
        for version in ('0.0.32-rc1', '0.0.32'):
            require_private_test_version(version, [])
            with self.assertRaisesRegex(ValueError, 'waivers .* are refused'):
                require_private_test_version(version, ['--map-budget-policy warning'])

    def test_image_step_lists_waivers(self):
        import argparse
        from build_aga import image_waivers
        self.assertEqual(image_waivers(argparse.Namespace(map_budget_policy='strict')), [])
        both = argparse.Namespace(allow_known_actor_ground_findings='a.json', map_budget_policy='warning')
        self.assertEqual(len(image_waivers(both)), 2)

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
            asm = (root/'generated/amiwind_version.i').read_text()
            self.assertIn('AmiWind v0.0.17-dev1 hardware preflight', asm)
            self.assertIn('AmiWind v0.0.17-dev1 preflight OK.', asm)
            self.assertIn('AmiWind v0.0.17-dev1 was not loaded', asm)
            self.assertIn('$VER: AmiWindCheck 0.0.17-dev1', asm)
    def test_preflight_pause_and_dry_run_boot_order(self):
        checker = (ROOT/'engine/aga/boot/bootcheck.asm').read_text()
        self.assertIn('_LVOWaitForChar', checker)
        self.assertIn('_LVORead', checker)
        self.assertIn('#1000000', checker)
        self.assertIn('SPACE or ENTER = start now', checker)
        dry = (ROOT/'tools/build_dry_run.py').read_text()
        self.assertIn('boot / "C/AmiWindCheck"', dry)
        self.assertIn("FailAt 10\\nSYS:C/AmiWindCheck\\nSYS:C/AmiWindDryRun\\n", dry)
