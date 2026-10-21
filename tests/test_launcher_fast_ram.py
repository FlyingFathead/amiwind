"""Fast RAM choice of the playtest launcher: presets, custom sizes, emulator keys, the 128 MiB default and the
16 MiB baseline still selectable."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SCRIPT = ROOT / 'tools/AmiWind-FS-UAE-launcher.py'
spec = importlib.util.spec_from_file_location('fast_ram_launcher', SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
from emulator_configs import write_configs, VERSION  # noqa: E402

PATH_KEYS = re.compile(r'^(kickstart_file|hard_drive_[0-9]+(?:_type)?) *=')
# Measured in FS-UAE 3.1.66 (JIT on): what each preset must write.
EXPECTED_FS = {
    16: {'zorro_iii_memory': '16384'},
    128: {'zorro_iii_memory': '131072'},
    256: {'zorro_iii_memory': '262144'},
    512: {'zorro_iii_memory': '524288'},
    1024: {'zorro_iii_memory': '1048576'},
    1536: {'zorro_iii_memory': '1048576', 'uae_z3mem2_size': '512'},
}


class FastRamRuleTests(unittest.TestCase):
    def test_presets_are_the_promised_sizes_and_default_first(self):
        self.assertEqual([mib for mib, _ in launcher.FAST_RAM_PRESETS], [128, 16, 256, 512, 1024, 1536])
        self.assertEqual(launcher.FAST_RAM_DEFAULT_MIB, 128)
        self.assertEqual(launcher.FAST_RAM_BASELINE_MIB, 16)
        self.assertEqual(launcher.FAST_RAM_MIN_MIB, 16)
        self.assertEqual(launcher.PROFILE_VALUES['zorro_iii_memory'], '131072')
        self.assertIn('zorro_iii_memory = 131072', launcher.PRESET)

    def test_each_preset_writes_the_right_fs_uae_keys(self):
        for mib, expected in EXPECTED_FS.items():
            self.assertEqual(launcher.fast_ram_fs_uae_values(mib), expected, mib)

    def test_board_rule_powers_of_two_second_not_larger(self):
        for mib in launcher.fast_ram_valid_sizes():
            first, second = launcher.fast_ram_boards(mib)
            self.assertEqual(first & (first - 1), 0)
            self.assertLessEqual(first, 1024)
            self.assertTrue(second == 0 or (second & (second - 1) == 0 and second <= first))
            self.assertEqual(first + second, mib)

    def test_custom_sizes_are_validated(self):
        for text, mib in (('default', 128), ('16', 16), ('128', 128), ('384', 384), ('768 MiB', 768), ('1G', 1024),
                          ('1.5GiB', 1536), ('1280', 1280), (' 24 ', 24)):
            self.assertEqual(launcher.parse_fast_ram(text), mib, text)
        for bad in ('8', '0', '-1', '100', '1000', '1537', '2G', '2048', '4096', 'lots', '1.3G', '128.5'):
            with self.assertRaises(ValueError, msg=bad):
                launcher.parse_fast_ram(bad)
        with self.assertRaisesRegex(ValueError, 'Nearest sizes: 96 or 128 MiB'):
            launcher.parse_fast_ram('100')

    def test_labels_in_plain_words(self):
        self.assertEqual([launcher.fast_ram_label(m) for m in (16, 128, 1024, 1536, 1280)],
                         ['16 MiB', '128 MiB', '1 GiB', '1.5 GiB', '1280 MiB'])

    def test_menu_enter_keeps_presets_and_custom(self):
        cases = ((('',), 16), (('1',), 128), (('2',), 16), (('6',), 1536), (('c', '384'), 384),
                 (('x', '100', '3'), 256), (('512',), 512))
        for answers, expected in cases:
            replies = iter(answers)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.choose_fast_ram(16, ask=lambda _prompt: next(replies)), expected, answers)
        def eof(_prompt):
            raise EOFError
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(launcher.choose_fast_ram(16, ask=eof))


class FastRamConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='amiwind-fast-ram-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.image = self.root / ('AmiWind-v' + VERSION + '.hdf')
        self.image.write_bytes(b'boot fixture')
        (self.root / 'build.json').write_text(json.dumps(dict(
            version=VERSION, hdf_file=self.image.name,
            hdf_files=[dict(file=self.image.name, bytes=12, bootable=True, readback='passed')])), encoding='utf-8')
        self.fs_template = (ROOT / ('resources/emulators/AmiWind-v%s-FS-UAE.fs-uae' % VERSION)).read_text(encoding='utf-8')
        self.win_template = (ROOT / ('resources/emulators/AmiWind-v%s-WinUAE.uae' % VERSION)).read_text(encoding='utf-8')

    def test_default_fs_uae_config_is_the_template_with_128_mib(self):
        out = launcher.configured_text(self.fs_template, self.image, '/rom')
        self.assertEqual(out, launcher.configured_text(self.fs_template, self.image, '/rom', 128))
        self.assertEqual(re.findall(r'(?m)^zorro_iii_memory = (.*)$', out), ['131072'])
        other = re.compile(r'^(kickstart_file|hard_drive_[0-9]+(?:_type)?|zorro_iii_memory) *=')
        keep = [line for line in self.fs_template.splitlines() if not other.match(line)]
        self.assertEqual([line for line in out.splitlines() if not other.match(line)], keep)
        self.assertNotIn('uae_z3mem2_size', out)

    def test_baseline_16_mib_still_written(self):
        out = launcher.configured_text(self.fs_template, self.image, '/rom', 16)
        self.assertEqual(re.findall(r'(?m)^zorro_iii_memory = (.*)$', out), ['16384'])
        win = launcher.fast_ram_winuae_text(self.win_template, 16)
        self.assertEqual(re.findall(r'(?m)^z3mem_size=(.*)$', win), ['16'])

    def test_winuae_profile_already_at_the_size_is_byte_identical(self):
        size = int(re.findall(r'(?m)^z3mem_size=(.*)$', self.win_template)[0])
        self.assertEqual(launcher.fast_ram_winuae_text(self.win_template, size), self.win_template)
        default = launcher.fast_ram_winuae_text(self.win_template, launcher.FAST_RAM_DEFAULT_MIB)
        self.assertEqual(re.findall(r'(?m)^z3mem_size=(.*)$', default), ['128'])
        if size != 128:
            self.assertIn('128MiB Z3 Fast RAM', default)
        self.assertEqual(launcher.fast_ram_winuae_text(default, 128), default)

    def test_fs_uae_presets_and_switching_back_removes_second_board(self):
        for mib, expected in EXPECTED_FS.items():
            out = launcher.configured_text(self.fs_template, self.image, '/rom', mib)
            for key, value in expected.items():
                self.assertEqual(re.findall(r'(?m)^' + key + r' = (.*)$', out), [value], (mib, key))
            if 'uae_z3mem2_size' not in expected:
                self.assertNotIn('uae_z3mem2_size', out)
        big = launcher.configured_text(self.fs_template, self.image, '/rom', 1536)
        self.assertEqual(launcher.configured_text(big, self.image, '/rom', 128),
                         launcher.configured_text(self.fs_template, self.image, '/rom', 128))

    def test_winuae_presets(self):
        for mib, z3, z3b, start in ((256, '256', None, '0x40000000'),
                                    (1024, '1024', None, '0x40000000'),
                                    (1536, '1024', '512', '0x10000000')):
            out = launcher.fast_ram_winuae_text(self.win_template, mib)
            self.assertEqual(re.findall(r'(?m)^z3mem_size=(.*)$', out), [z3])
            self.assertEqual(re.findall(r'(?m)^z3mem2_size=(.*)$', out), [z3b] if z3b else [])
            self.assertEqual(re.findall(r'(?m)^z3mem_start=(.*)$', out), [start])
            self.assertIn(launcher.fast_ram_label(mib).replace(' ', '') + ' Z3 Fast RAM', out)
            self.assertEqual(out.count('\n'), self.win_template.count('\n') + (1 if z3b else 0))

    def test_build_end_configs_take_the_choice(self):
        default = write_configs(self.image)
        before = {n: (self.root / n).read_bytes() for n in default}
        self.assertEqual(write_configs(self.image, fast_ram_mib='default'), default)
        self.assertEqual({n: (self.root / n).read_bytes() for n in default}, before)
        fs, win = [(self.root / n).read_text(encoding='utf-8') for n in default]
        self.assertIn('zorro_iii_memory = 131072', fs)
        self.assertIn('z3mem_size=128', win)
        write_configs(self.image, fast_ram_mib=16)
        fs, win = [(self.root / n).read_text(encoding='utf-8') for n in default]
        self.assertIn('zorro_iii_memory = 16384', fs)
        self.assertIn('z3mem_size=16', win)
        with self.assertRaises(ValueError):
            write_configs(self.image, fast_ram_mib=100)


class FastRamLauncherRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='amiwind-fast-ram-run-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'AmiWind-v0.0.19.hdf').write_bytes(b'synthetic HDF fixture')
        (self.root / 'roms').mkdir()
        (self.root / 'roms/owned.rom').write_bytes(b'R' * 524288)
        self.config = self.root / 'AmiWind-v0.0.19-FS-UAE.fs-uae'
        self.settings = self.root / launcher.SETTINGS_NAME

    def run_main(self, args=(), answers=('',)):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), \
             patch('builtins.input', side_effect=list(answers)):
            status = launcher.main(['--directory', str(self.root)] + list(args))
        return status, output.getvalue()

    def test_default_run_keeps_settings_without_a_fast_ram_entry(self):
        status, output = self.run_main(['--configure-only'])
        self.assertEqual(status, 0, output)
        self.assertNotIn('fast_ram_mib', json.loads(self.settings.read_text()))
        self.assertIn('Fast RAM: 128 MiB (default)', output)
        self.assertIn('zorro_iii_memory = 131072', self.config.read_text())
        self.assertIn('Fast RAM in total:    128 MiB (default)', output)

    def test_baseline_16_mib_is_written_and_remembered(self):
        status, output = self.run_main(['--configure-only', '--fast-ram', '16'])
        self.assertEqual(status, 0, output)
        self.assertIn('zorro_iii_memory = 16384', self.config.read_text())
        self.assertIn('Starting with 16 MiB of Fast RAM', output)
        self.assertEqual(json.loads(self.settings.read_text())['fast_ram_mib'], 16)
        status, output = self.run_main(['--configure-only'])
        self.assertEqual(status, 0, output)
        self.assertIn('Fast RAM: 16 MiB', output)
        self.assertNotIn('(default)', output.split('Fast RAM: 16 MiB', 1)[1].split(chr(10), 1)[0])

    def test_choice_is_written_printed_and_remembered(self):
        status, output = self.run_main(['--configure-only', '--fast-ram', '1536'])
        self.assertEqual(status, 0, output)
        text = self.config.read_text()
        self.assertIn('zorro_iii_memory = 1048576', text)
        self.assertIn('uae_z3mem2_size = 512', text)
        self.assertIn('Z3 Fast RAM board 2:', output)
        self.assertIn('Starting with 1.5 GiB of Fast RAM', output)
        self.assertEqual(json.loads(self.settings.read_text())['fast_ram_mib'], 1536)
        status, output = self.run_main(['--configure-only'])
        self.assertEqual(status, 0, output)
        self.assertIn('Fast RAM: 1.5 GiB', output)
        status, output = self.run_main(['--configure-only', '--fast-ram', 'default'])
        self.assertEqual(status, 0, output)
        self.assertNotIn('uae_z3mem2_size', self.config.read_text())
        self.assertNotIn('fast_ram_mib', json.loads(self.settings.read_text()))

    def test_menu_from_the_launch_prompt(self):
        with patch.object(launcher.shutil, 'which', return_value=None):
            status, output = self.run_main([], answers=('m', '2', 'n'))
        self.assertEqual(status, 0, output)
        self.assertIn('Fast RAM for the emulated Amiga', output)
        self.assertIn('Fast RAM: 16 MiB', output)
        prompts = []
        with patch.object(launcher.shutil, 'which', return_value=None), \
             contextlib.redirect_stdout(io.StringIO()), \
             patch('builtins.input', side_effect=lambda prompt: prompts.append(prompt) or 'n'):
            launcher.main(['--directory', str(self.root)])
        self.assertIn('M = Fast RAM', prompts[0])

    def test_invalid_choice_changes_nothing(self):
        status, output = self.run_main(['--configure-only', '--fast-ram', '100'])
        self.assertEqual(status, 1)
        self.assertIn('Nearest sizes', output)
        self.assertFalse(self.config.exists())
        self.settings.write_text('{"fast_ram_mib": 100}')
        self.assertEqual(self.run_main(['--configure-only'])[0], 1)


if __name__ == '__main__':
    unittest.main()
