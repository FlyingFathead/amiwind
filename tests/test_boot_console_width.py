# SPDX-License-Identifier: GPL-3.0-only
"""Every boot checklist line fits the 64-column boot console on one row
(BOOT-CONSOLE-WIDTH-32): the countdown overwrites itself with a carriage return, which
only works when the line does not wrap."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine' / 'aga' / 'boot' / 'bootcheck.asm'
COLUMNS = 63  # the boot console is 64 columns; the last column would wrap
WIDTHS = {'%ld': 6, '%s': 27}  # widest values the checklist prints (KiB counts, names)


def visible_width(literal):
    text = re.sub(r'%-?(\d+)s', lambda m: ' ' * int(m.group(1)), literal)
    for token, width in WIDTHS.items():
        text = text.replace(token, 'x' * width)
    return len(text)


class BootConsoleWidthTests(unittest.TestCase):
    def test_every_line_fits_one_row(self):
        lines = re.findall(r'dc\.b\s+(?:13,)?"([^"]*)"', SOURCE.read_text(encoding='utf-8'))
        self.assertGreater(len(lines), 20)
        for literal in lines:
            with self.subTest(line=literal):
                self.assertLessEqual(visible_width(literal), COLUMNS)

    def test_countdown_overwrites_one_row(self):
        text = SOURCE.read_text(encoding='utf-8')
        countdown = re.search(r'countdown_format:\s*dc\.b\s+13,"([^"]*)"', text).group(1)
        done = re.search(r'countdown_done:\s*dc\.b\s+13,"([^"]*)"', text).group(1)
        self.assertLessEqual(visible_width(countdown), COLUMNS)
        self.assertGreaterEqual(len(done), len(countdown.replace('%ld', '0')))


if __name__ == '__main__':
    unittest.main()
