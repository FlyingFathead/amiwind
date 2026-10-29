"""The Pi boot image tool (tools/pi_image, docs/PI_BOOT_IMAGE.md): the lessons of the first stick stay in it, it
checks every download and never writes to a disk."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/pi_image/make_pi_image.sh'
PRESET = ROOT / 'tools/pi_image/amiwind.uae'


def preset():
    return dict(line.split('=', 1) for line in PRESET.read_text(encoding='utf-8').splitlines()
                if '=' in line and not line.startswith('#'))


class PiImageTests(unittest.TestCase):
    def test_script_is_valid_bash(self):
        if not shutil.which('bash'):
            self.skipTest('no bash here')
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_preset_keeps_the_jit_on(self):
        p = preset()
        # cycle-exact switches the JIT off; above 16384 Amiberry reads 0 (JIT off); indirect is 26x slower on FPU code
        for key in ('cycle_exact', 'cpu_cycle_exact', 'cpu_memory_cycle_exact', 'blitter_cycle_exact', 'cpu_compatible'):
            self.assertEqual(p[key], 'false', key)
        self.assertEqual(p['cachesize'], '16384')
        self.assertEqual(p['compfpu'], 'true')
        for key in ('comp_trustbyte', 'comp_trustword', 'comp_trustlong', 'comp_trustnaddr'):
            self.assertEqual(p[key], 'direct', key)

    def test_preset_stays_safe(self):
        p = preset()
        self.assertEqual(p['cpu_threaded'], 'false')  # SPRITE-BAD-TYPE-THREADED-56
        self.assertGreaterEqual(int(p['z3mem_size']), 32)  # 32 MB Fast RAM is the minimum
        self.assertIn('/opt/amiwind/current.hdf', p['hardfile2'])
        self.assertEqual(p['kickstart_rom_file'], '/opt/amiwind/data/kick.rom')

    def test_downloads_are_checked_and_no_disk_is_written(self):
        s = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('set -euo pipefail', s)
        self.assertIn('.sha256', s)             # Raspberry Pi OS against its published sum
        self.assertIn('SHA256SUMS', s)          # Amiberry against its release's sums
        self.assertNotIn('of=/dev', s)          # never dd to a device
        self.assertNotIn('force_turbo=1', s)
        for lesson in ('libegl1', 'libegl-mesa0', 'libgles2', 'video=HDMI-A-1:', 'RuntimeWatchdogSec',
                       'getty@tty2', 'id -u amiwind', 'sort -V'):
            self.assertIn(lesson, s, lesson)

    def test_doc_warns_about_the_overclock(self):
        d = (ROOT / 'docs/PI_BOOT_IMAGE.md').read_text(encoding='utf-8')
        self.assertIn('⚠️ **AmiWind is measured on a Pi 4 at 2.0 GHz, and the image runs a Pi 4 at 2.0 GHz by default.**', d)
        s = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('OVERCLOCK=1', s)       # the maintainer: the 2.0 GHz setting is the Pi 4 default
        self.assertIn('[pi4]', s)              # only a Pi 4 takes it
        self.assertIn('heatsink **and** a fan', d)
        self.assertIn('never share it', d)


if __name__ == '__main__':
    unittest.main()
