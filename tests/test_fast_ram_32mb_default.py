# SPDX-License-Identifier: GPL-3.0-only
"""32 MB of Fast RAM by default (decided for the project, 27 October 2026: the game needs 32 MB of Fast RAM; every
emulator session runs at 32 MB, more only when a check needs it, never less). Every emulator preset that is not a
frozen record of an earlier release (resources/emulators/AmiWind-vX.Y.Z...: what that release shipped), the current
version's presets (the templates tools/emulator_configs.py fills) and the FS-UAE launcher default to at least 32 MB."""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
EMULATORS = ROOT / 'resources/emulators'
MINIMUM_MIB = 32


def fast_mib(path):
    """The Fast RAM a preset gives (FS-UAE fast_memory + zorro_iii_memory in KB; WinUAE fastmem_size + z3mem_size in
    MB, plus the accelerator board's cpuboardmem1_size)."""
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.fs-uae':
        values = [int(v) for v in re.findall(r'^(?:fast_memory|zorro_iii_memory)\s*=\s*(\d+)', text, re.M)]
        return sum(values) // 1024 if values else None
    values = [int(v) for v in re.findall(r'^(?:fastmem_size|z3mem_size|cpuboardmem1_size)=(\d+)', text, re.M)]
    return sum(values) if values else None


def current_version():
    from project_version import public_version
    return public_version()


class FastRamDefaultTests(unittest.TestCase):
    def presets(self):
        frozen = re.compile(r'AmiWind-v(\d+\.\d+\.\d+.*)-(?:FS-UAE|WinUAE)\.(?:fs-uae|uae)$')
        version = current_version()
        found = []
        for path in sorted(EMULATORS.iterdir()):
            if path.suffix not in ('.fs-uae', '.uae'):
                continue
            match = frozen.match(path.name)
            if match and match.group(1) != version:
                continue          # a frozen record of an earlier release
            found.append(path)
        return found

    def test_every_live_preset_gives_32_mb(self):
        presets = self.presets()
        self.assertGreaterEqual(len(presets), 9)
        low = {path.name: fast_mib(path) for path in presets if (fast_mib(path) or 0) < MINIMUM_MIB}
        self.assertEqual(low, {}, 'presets under %d MB of Fast RAM' % MINIMUM_MIB)

    def test_the_current_version_templates_exist_at_32_mb(self):
        version = current_version()
        for name in ('AmiWind-v%s-FS-UAE.fs-uae' % version, 'AmiWind-v%s-WinUAE.uae' % version):
            self.assertGreaterEqual(fast_mib(EMULATORS / name), MINIMUM_MIB, name)

    def test_the_launcher_defaults_to_32_mb(self):
        spec = importlib.util.spec_from_file_location('aw_launcher_32', ROOT / 'tools/AmiWind-FS-UAE-launcher.py')
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        self.assertEqual(launcher.FAST_RAM_DEFAULT_MIB, MINIMUM_MIB)
        self.assertEqual(launcher.SETTINGS_OPTIONAL['fast_ram_mib'], MINIMUM_MIB)
        self.assertEqual(launcher.FAST_RAM_PRESETS[0][0], MINIMUM_MIB)


if __name__ == '__main__':
    unittest.main()
