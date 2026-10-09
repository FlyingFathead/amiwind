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
    def test_chim_version_file_is_the_one_source(self):
        import chim
        from project_version import chim_version, read_chim_version
        self.assertEqual(chim.CHIM_VERSION, read_chim_version(ROOT/'CHIM_VERSION'))
        self.assertEqual(chim_version(ROOT/'VERSION'), chim.CHIM_VERSION)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'VERSION').write_text('0.0.33\n')
            self.assertIsNone(chim_version(root/'VERSION'))
            generate_native(root/'VERSION', root/'plain')
            self.assertFalse((root/'plain/chim_version.h').exists())
            self.assertIn('AmiWind v0.0.33 hardware preflight', (root/'plain/amiwind_version.i').read_text())
            (root/'CHIM_VERSION').write_text('0.1.0\n')
            generate_native(root/'VERSION', root/'chim')
            self.assertIn('#define CHIM_VERSION "0.1.0"', (root/'chim/chim_version.h').read_text())
            self.assertNotIn('CHIM_VERSION "', (root/'chim/amiwind_version.h').read_text())
            asm = (root/'chim/amiwind_version.i').read_text()
            self.assertIn('AmiWind v0.0.33 / CHIM v0.1.0 hardware preflight', asm)
            self.assertIn('AmiWind v0.0.33 preflight OK.', asm)
            for bad in ('v0.1.0', '0.1', '0.1.0-dev1', '2'):
                (root/'CHIM_VERSION').write_text(bad + '\n')
                with self.assertRaises(ValueError):
                    chim_version(root/'VERSION')

    def test_chim_version_literal_in_engine_sources_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copyfile(ROOT/'VERSION', root/'VERSION')
            for name in ('src/aw_hud.c','src/aw_scene.c','src/sys_amiga.c','boot/bootcheck.asm'):
                p=root/'engine/aga'/name;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/'engine/aga'/name,p)
            check_native_versions(root)
            p=root/'engine/aga/src/chim/chim.h';p.parent.mkdir(parents=True)
            p.write_text('#define CHIM_VERSION\t"0.1.0"\n')
            with self.assertRaisesRegex(ValueError, 'generated chim_version.h'):check_native_versions(root)

    def test_staged_engine_tree_carries_the_chim_version(self):
        text=(ROOT/'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("shutil.copyfile(ROOT/'CHIM_VERSION', tree/'CHIM_VERSION')", text)
        make=(ROOT/'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('$(CHIM_VERSION_FILE)', make)

    def test_preflight_pause_and_dry_run_boot_order(self):
        checker = (ROOT/'engine/aga/boot/bootcheck.asm').read_text()
        self.assertIn('_LVOWaitForChar', checker)
        self.assertIn('_LVORead', checker)
        self.assertIn('#1000000', checker)
        self.assertIn('SPACE or ENTER = start now', checker)
        dry = (ROOT/'tools/build_dry_run.py').read_text()
        self.assertIn('boot / "C/AmiWindCheck"', dry)
        self.assertIn("FailAt 10\\nSYS:C/AmiWindCheck\\nSYS:C/AmiWindDryRun\\n", dry)
