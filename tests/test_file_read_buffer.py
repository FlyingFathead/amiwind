# SPDX-License-Identifier: GPL-3.0-only
"""Loose game files are read through a 16 KiB stdio buffer (SEYDA-READ-SLOW-31).

The C library's default is 1 KiB, one AmigaDOS call per KiB; measured in
FS-UAE, 16 KiB halves Seyda Neen map read time and 64 KiB gains nothing overall.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / 'engine' / 'aga' / 'src' / 'common.c'


class FileReadBufferTest(unittest.TestCase):
    def test_loose_files_get_a_16k_full_buffer_right_after_open(self):
        source = COMMON.read_text(encoding='utf-8')
        opened = list(re.finditer(r'\*file = fopen \(netpath, "rb"\);', source))
        # two opens: the single open of a FILE without a cache folder (ARRIVAL-LONG-FRAME-DEV6-59: the open is the
        # existence check) and the original path after the cache folder's copy
        self.assertEqual(len(opened), 2)
        self.assertRegex(source, r'(?m)^extern int com_fopen_buffer;')
        for match in opened:
            after = source[match.end():match.end() + 600]
            # 16 KiB unless a caller asks for a small buffer around its open (com_fopen_buffer: a binary search on
            # focus.awf refilled 16 KiB per step, TRADEHOUSE-LONG-FRAME-59)
            self.assertRegex(after, r'setvbuf \(\*file, NULL, _IOFBF, com_fopen_buffer > 0 \? com_fopen_buffer : 16384\);')
            # Nothing else may run between the open and the buffer setup (setvbuf
            # must precede the first read on the stream).
            between = after[:after.index('setvbuf')]
            self.assertNotRegex(re.sub(r'/\*.*?\*/', '', between, flags=re.S), r'\b(fread|fseek|ftell|getc|fgets)\b')


if __name__ == '__main__':
    unittest.main()
