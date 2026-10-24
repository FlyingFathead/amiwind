"""The collapsible control blocks of the Toolkit pages World Map and Monitor (amiwind-toolkit/panel-fold.js): both pages
carry the toggles, the Collapse all control and the summary line outside the foldable group, and storage access is guarded."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'amiwind-toolkit'


def page(name):
    return (KIT / name).read_text(encoding='utf-8')


class FoldTests(unittest.TestCase):
    def test_helper_is_shipped_and_loaded_by_both_pages(self):
        self.assertIn('amiwind-toolkit/panel-fold.js', json.loads((ROOT / 'tools' / 'release-files.json').read_text()))
        for name in ('world-map.html', 'monitor.html'):
            self.assertIn('<script src="panel-fold.js"></script>', page(name), name)
            self.assertIn('window.AmiWindFold.init(', page(name), name)

    def test_helper_source(self):
        src = page('panel-fold.js')
        self.assertIn("OPEN = '" + chr(0x25BE) + "'", src)           # open triangle
        self.assertIn("CLOSED = '" + chr(0x25B8) + "'", src)         # closed triangle
        self.assertIn("'aria-expanded'", src)
        self.assertIn("doc.createElement('button')", src)
        self.assertIn("'Collapse all' : 'Expand all'", src)
        # every localStorage access is inside a try that has its own catch
        self.assertEqual(src.count('root.localStorage'), src.count('catch (_)'))
        for m in re.finditer(r'root\.localStorage', src):
            line_start = src.rfind('\n', 0, m.start()) + 1
            self.assertIn('try {', src[line_start:m.start()], 'unguarded storage access')

    def test_world_page_blocks_and_summary(self):
        html = page('world-map.html')
        for block in ('legendblock', 'filesblock', 'layers', 'metricsbar', 'chimbar'):
            self.assertIn("el: $('%s')" % block, html, block)
        self.assertIn('id="foldall"', html)
        self.assertIn("'amiwind-map-folds-1'", html)
        # the summary line (chimhead) and its rule come before the collapsible group, and are not inside it
        self.assertLess(html.index('id="chimhead"'), html.index('id="summaryrule"'))
        self.assertLess(html.index('id="summaryrule"'), html.index('<div id="controls">'))
        self.assertLess(html.index('id="summaryrule"'), html.index('id="legendblock"'))
        self.assertNotIn('id="chimfold"', html)                       # one toggle style: the shared triangle button
        self.assertIn("n.classList.contains('chimtitle')", html)     # the headline title stays; the chips move to the legend

    def test_monitor_page_blocks_and_summary(self):
        html = page('monitor.html')
        for block in ('runblock', 'logbar', 'tlbar'):
            self.assertIn("document.getElementById('%s')" % block, html, block)
        self.assertIn('id="foldall"', html)
        self.assertIn("'amiwind-monitor-folds-1'", html)
        self.assertLess(html.index('id="status"'), html.index('<hr class="foldrule">'))
        self.assertLess(html.index('<hr class="foldrule">'), html.index('id="runblock"'))
        self.assertLess(html.index('<hr class="foldrule">'), html.index('<main>'))

    def test_toolkit_version_line(self):
        # the tree's own version, not a literal (a literal went stale at the v0.0.49 release)
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertIn('Last updated with AmiWind v' + version, page('header.js'))

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_helper_runs_with_blocked_storage(self):
        out = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / 'test_toolkit_fold.js'), str(KIT / 'panel-fold.js')],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('fold ok', out.stdout)


if __name__ == '__main__':
    unittest.main()
