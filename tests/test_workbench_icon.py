"""Workbench icon: the classic icon writer (tools/amiga_icon.py) and the boot volume's icon (tools/workbench_launcher.py).

The writer's output is read back field by field at fixed offsets of the 78-byte DiskObject header and through the
reader, which refuses anything it does not know. The launcher tests cover each --workbench-icon value, the default
command list (off adds nothing) and the FFS name limit of the label "AmiWind v<VERSION>"."""
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import amiga_icon
import build
import layout_plan
import workbench_launcher
from project_version import VERSION

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}


def picture(width, height, fill=None):
    return width, height, [fill(x, y) if fill else (x + y) % 4 for y in range(height) for x in range(width)]


class WriterTests(unittest.TestCase):
    def test_header_fields_at_their_offsets(self):
        data = amiga_icon.disk_object('project', picture(20, 3), picture(20, 3, lambda x, y: 3 - (x + y) % 4),
                                      default_tool='C:IconX', tool_types=['WINDOW=NIL:', 'DONOTWAIT'], stack=8192)
        magic, version = struct.unpack_from('>HH', data, 0)
        self.assertEqual((magic, version), (0xE310, 1))
        self.assertEqual(struct.unpack_from('>I', data, 4)[0], 0)                       # NextGadget
        self.assertEqual(struct.unpack_from('>hhhh', data, 8), (0, 0, 20, 3))           # gadget box = picture
        self.assertEqual(struct.unpack_from('>HHH', data, 16), (0x0006, 0x0003, 0x0001))
        render, select, text = struct.unpack_from('>III', data, 22)
        self.assertTrue(render and select)
        self.assertEqual(text, 0)
        self.assertEqual(struct.unpack_from('>I', data, 44)[0], 1)                      # UserData: 2.x+ icon
        self.assertEqual(data[48], 4)                                                     # WBPROJECT
        tool, types = struct.unpack_from('>II', data, 50)
        self.assertTrue(tool and types)
        self.assertEqual(struct.unpack_from('>II', data, 58), (0x80000000, 0x80000000))  # NO_ICON_POSITION
        self.assertEqual(struct.unpack_from('>II', data, 66), (0, 0))                   # no drawer, no tool window
        self.assertEqual(struct.unpack_from('>i', data, 74)[0], 8192)
        # first Image right after the header: 20x3, 2 planes, PlanePick 3
        self.assertEqual(struct.unpack_from('>hhhhh', data, 78), (0, 0, 20, 3, 2))
        self.assertEqual(data[78 + 14:78 + 16], b'\x03\x00')
        info = amiga_icon.parse(data)
        self.assertEqual(info['type'], 'project')
        self.assertEqual(info['default_tool'], 'C:IconX')
        self.assertEqual(info['tool_types'], ['WINDOW=NIL:', 'DONOTWAIT'])
        self.assertEqual(info['stack'], 8192)
        self.assertEqual(info['normal']['pixels'], picture(20, 3)[2])
        self.assertEqual(info['selected']['pixels'], picture(20, 3, lambda x, y: 3 - (x + y) % 4)[2])
        # length-prefixed strings at the end: the tool types' count field is (n+1)*4
        tail = data[-(4 + len(b'DONOTWAIT\0')):]
        self.assertEqual(tail, struct.pack('>I', 10) + b'DONOTWAIT\0')

    def test_plane_layout_rows_padded_to_16_bits(self):
        # 17 pixels wide -> 4 bytes per row; pixel 0 = 1 (plane 0), pixel 16 = 2 (plane 1)
        pixels = [0] * 17
        pixels[0], pixels[16] = 1, 2
        planes = amiga_icon.to_planes(pixels, 17, 1, 2)
        self.assertEqual(planes, b'\x80\x00\x00\x00' + b'\x00\x00\x80\x00')
        self.assertEqual(amiga_icon.from_planes(planes, 17, 1, 2), pixels)

    def test_deterministic_and_complement_without_second_picture(self):
        a = amiga_icon.disk_object('tool', picture(8, 2), stack=300000)
        self.assertEqual(a, amiga_icon.disk_object('tool', picture(8, 2), stack=300000))
        info = amiga_icon.parse(a)
        self.assertEqual(info['gadget']['flags'], 0x0004)                                # complemented when selected
        self.assertIsNone(info['selected'])
        self.assertIsNone(info['default_tool'])

    def test_disk_icon_carries_drawer_data(self):
        data = amiga_icon.disk_object('disk', picture(16, 4), picture(16, 4))
        info = amiga_icon.parse(data)
        self.assertEqual(info['type'], 'disk')
        self.assertEqual((info['drawer']['left'], info['drawer']['width']), (50, 400))
        self.assertEqual((info['drawer']['flags'], info['drawer']['view_modes']), (0, 0))
        self.assertEqual(data[48], 1)
        self.assertEqual(len(data), 78 + 56 + 2 * (20 + 2 * 4 * 2) + 6)

    def test_refusals(self):
        good = amiga_icon.disk_object('project', picture(8, 2), default_tool='C:IconX')
        with self.assertRaisesRegex(ValueError, 'trailing'):
            amiga_icon.parse(good + b'\0')
        with self.assertRaisesRegex(ValueError, 'truncated'):
            amiga_icon.parse(good[:-1])
        with self.assertRaisesRegex(ValueError, 'magic'):
            amiga_icon.parse(b'\xe3\x11' + good[2:])
        with self.assertRaisesRegex(ValueError, 'does not fit'):
            amiga_icon.disk_object('tool', (2, 1, [0, 4]))
        with self.assertRaisesRegex(ValueError, 'unknown icon type'):
            amiga_icon.disk_object('kick', picture(8, 2))
        with self.assertRaisesRegex(ValueError, 'line breaks'):
            amiga_icon.disk_object('tool', picture(8, 2), tool_types=['A=1\nB=2'])
        with self.assertRaisesRegex(ValueError, 'size of the normal'):
            amiga_icon.disk_object('tool', picture(8, 2), picture(8, 3))

    def test_png_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / 'p.png'
            amiga_icon.save_png(png, picture(12, 5))
            self.assertEqual(amiga_icon.load_png(png), picture(12, 5))
            out = Path(tmp) / 'x.info'
            data = amiga_icon.write_icon(out, png, 'tool', stack=4096)
            self.assertEqual(out.read_bytes(), data)
            amiga_icon.save_png(png, (2, 1, [0, 7]), palette=[(0, 0, 0)] * 8)
            with self.assertRaisesRegex(ValueError, 'colour index 7'):
                amiga_icon.load_png(png)


class RepositoryPictureTests(unittest.TestCase):
    def test_pictures_are_four_colour_and_the_same_size(self):
        normal = amiga_icon.load_png(workbench_launcher.PICTURE)
        selected = amiga_icon.load_png(workbench_launcher.SELECTED)
        self.assertEqual(normal[:2], (192, 36))
        self.assertEqual(selected[:2], (192, 36))
        self.assertLessEqual(max(normal[2]), 3)
        self.assertNotEqual(normal[2], selected[2])


class LauncherTests(unittest.TestCase):
    def test_label_and_ffs_name_limit(self):
        self.assertEqual(workbench_launcher.label('0.0.46'), 'AmiWind v0.0.46')
        for version in ('0.0.46-dev1', '0.0.46-rc1', '0.0.100-dev10', VERSION):
            self.assertLessEqual(len(workbench_launcher.label(version) + '.info'), 30)
        with self.assertRaisesRegex(ValueError, 'FFS allows 30'):
            workbench_launcher.label('100.100.100-preview12')
        for bad in ('0.0.46 ', '0.0.46"', 'v0.0.46', '0.0.46-dev1;x'):
            with self.assertRaises(ValueError):
                workbench_launcher.label(bad)

    def test_requester_script_is_one_short_line_with_ok(self):
        for version in ('0.0.46', '0.0.100-dev10'):
            script = workbench_launcher.requester_script(version)
            commands = [line for line in script.splitlines() if not line.startswith(';')]
            self.assertEqual(len(commands), 1)
            self.assertTrue(commands[0].startswith('C:RequestChoice >NIL: "AmiWind v%s" "' % version))
            self.assertTrue(commands[0].endswith('" "OK"'))
            self.assertLessEqual(len(commands[0]), workbench_launcher.LINE_LIMIT)
            self.assertIn('booting', commands[0])
            self.assertIn('AMIWIND', commands[0])

    def test_launch_script_follows_the_startup_sequence(self):
        single = workbench_launcher.launch_script('0.0.46')
        self.assertEqual([l for l in single.splitlines() if not l.startswith(';')],
                         ['FailAt 10', 'AMIWIND:AmiWindCheck', 'Stack 300000', 'AMIWIND:AmiWind'])
        pair = workbench_launcher.launch_script('0.0.46', pair=True, fpu=True)
        body = [l for l in pair.splitlines() if not l.startswith(';')]
        self.assertEqual(body[:3], ['FailAt 10', 'AMIWIND:AmiWindFPU', 'AMIWIND:AmiWindCPU'])
        self.assertIn('  AMIWIND:AmiWind060', body)
        self.assertNotIn('SYS:', '\n'.join(body))
        self.assertEqual(body.count('  Stack 300000'), 2)

    def test_install_each_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(workbench_launcher.install(tmp, 'off', '0.0.46'))
            self.assertEqual(list(Path(tmp).iterdir()), [])
            for mode, window in (('requester', workbench_launcher.REQUESTER_WINDOW),
                                 ('launch', workbench_launcher.LAUNCH_WINDOW)):
                receipt = workbench_launcher.install(tmp, mode, '0.0.46', pair=True)
                self.assertEqual(receipt['name'], 'AmiWind v0.0.46')
                self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),
                                 ['AmiWind v0.0.46', 'AmiWind v0.0.46.info'])
                info = amiga_icon.parse((Path(tmp) / 'AmiWind v0.0.46.info').read_bytes())
                self.assertEqual(info['type'], 'project')
                self.assertEqual(info['default_tool'], 'C:IconX')
                self.assertEqual(info['tool_types'], [window])
                self.assertEqual((info['normal']['width'], info['normal']['height']), (192, 36))
                self.assertIsNotNone(info['selected'])
                script = (Path(tmp) / 'AmiWind v0.0.46').read_bytes()
                self.assertNotIn(b'\r', script)
                self.assertIn(b'RequestChoice' if mode == 'requester' else b'Stack 300000', script)
            with self.assertRaises(ValueError):
                workbench_launcher.install(tmp, 'on', '0.0.46')

    def test_boot_volume_name_matches_the_layout(self):
        self.assertIn("Part('DH0', '%s', 'boot'" % workbench_launcher.BOOT_VOLUME,
                      (ROOT / 'tools/layout_plan.py').read_text(encoding='utf-8'))
        self.assertTrue(hasattr(layout_plan, 'resolve'))

    def test_option_reaches_only_the_image_step_and_default_adds_nothing(self):
        plain = build.parser().parse_args([])
        self.assertIsNone(plain.workbench_icon)  # not given = the image step's default
        plain.data_files, plain.sdk = Path('/owned/Data Files'), Path('/sdk')
        self.assertFalse(any('--workbench-icon' in c for _, c in build.commands(plain, TOOLS, Path('/private/run'))))
        for mode in ('off', 'requester', 'launch'):
            args = build.parser().parse_args(['--workbench-icon', mode])
            args.data_files, args.sdk = Path('/owned/Data Files'), Path('/sdk')
            steps = dict(build.commands(args, TOOLS, Path('/private/run')))
            image = steps['image']
            self.assertEqual(image[image.index('--workbench-icon') + 1], mode)
            for name, command in steps.items():
                if name != 'image':
                    self.assertNotIn('--workbench-icon', command)
        with self.assertRaises(SystemExit):
            build.parser().parse_args(['--workbench-icon', 'on'])

    def test_image_step_accepts_the_option(self):
        out = subprocess.run([sys.executable, str(ROOT / 'tools/build_aga.py'), 'image', '--help'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('--workbench-icon {off,requester,launch}', out)
        self.assertIn('launch (default', ' '.join(out.split()))
        self.assertEqual(workbench_launcher.DEFAULT, 'launch')


if __name__ == '__main__':
    unittest.main()
