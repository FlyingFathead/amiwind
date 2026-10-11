"""The console's version lines (owner, 11 October 2026): "AmiWind vX / CHIM vY", then the AmiQuake line, then
'Type: "dbg help" for help.' - at start-up, with the version command and in the server info on a map load."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
import project_version  # noqa: E402

LINES = ('AMIWIND_TITLE', 'AMIQUAKE_VERSION_LINE_OF (VERSION)', 'AW_CONSOLE_HELP_LINE')


def body(path, start):
    text = (SRC / path).read_text(encoding='utf-8')
    i = text.index(start)
    return text[i:text.index('\n}', i)]


class ConsoleVersionLines(unittest.TestCase):
    def test_title_comes_from_the_boot_check_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_version.generate_native(ROOT / 'VERSION', tmp)
            header = (Path(tmp) / 'amiwind_version.h').read_text(encoding='utf-8')
            boot = (Path(tmp) / 'amiwind_version.i').read_text(encoding='utf-8')
        value = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        chim = (ROOT / 'CHIM_VERSION').read_text(encoding='utf-8').strip()
        title = 'AmiWind v%s / CHIM v%s' % (value, chim)
        self.assertIn('#define AMIWIND_TITLE "%s"' % title, header)
        self.assertIn(title, boot)

    def test_lines_and_their_order(self):
        quake = (SRC / 'quakedef.h').read_text(encoding='utf-8')
        self.assertRegex(quake, r'#define\s+AMIQUAKE_VERSION_LINE_OF\(v\)\s+"AmiQuake: VERSION " AW_STRINGIFY \(v\)')
        self.assertRegex(quake, r'#define\s+AW_CONSOLE_HELP_LINE\s+"Type: \\"dbg help\\" for help\."')
        for path, start in (('host.c', 'void Host_Init ('), ('host_cmd.c', 'void Host_Version_f'),
                            ('sv_main.c', 'void SV_SendServerinfo')):
            text = body(path, start)
            at = [text.find(x) for x in LINES]
            self.assertTrue(all(a >= 0 for a in at), '%s: all three lines' % path)
            self.assertEqual(at, sorted(at), '%s: title, AmiQuake line, help line' % path)
            self.assertNotIn('%4.2f', text, '%s: no float formatting (ENGINE-FPU-UNIMPL-31)' % path)
        self.assertIn('SERVER (%ld CRC)', body('sv_main.c', 'void SV_SendServerinfo'))

    def test_console_page_shows_them(self):
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        for line in ('AmiWind v<version> / CHIM v<CHIM version>', 'AmiQuake: VERSION 1.09',
                     'Type: "dbg help" for help.'):
            self.assertIn(line, page)
        self.assertTrue(re.search(r'#define\s+VERSION\s+1\.09\b', (SRC / 'quakedef.h').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
