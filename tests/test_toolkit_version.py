"""The Toolkit's "Last updated with AmiWind vX" line names the release a Toolkit change ships in (tools/toolkit_version.py)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolkit_version as tv  # noqa: E402

PUBLISHED = 'a' * 40


def world_map(version):
    return "<script>\nconst TOOLKIT = {name: 'AmiWind Toolkit · World Map', version: '%s'};\n</script>\n" % version


def fake_git(changed=(), git=True, published=True, history=True, previous_own='0.1.0'):
    """git -C ROOT ... answers for changed_files(): rev-parse, cat-file, diff."""
    def run(*args):
        if args[0] == 'rev-parse' and args[1] == '--git-dir':
            code, out = (0 if git else 128), ''
        elif args[0] == 'cat-file':
            code, out = (0 if published else 1), ''
        elif args[0] == 'rev-parse':
            code, out = (0 if history else 1), ''
        elif args[0] == 'diff':
            code, out = 0, ''.join(name + '\n' for name in changed)
        elif args[0] == 'show':
            code, out = 0, world_map(previous_own)
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, code, out, '')
    return run


class ToolkitVersionTests(unittest.TestCase):
    def tree(self, version='0.0.36-dev1', named='0.0.35', index_named=None, own='0.1.0'):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / 'tools').mkdir()
        (root / 'amiwind-toolkit').mkdir()
        (root / 'VERSION').write_text(version + '\n')
        (root / 'tools/previous-release.json').write_text(json.dumps(
            {'version': '0.0.35', 'published': PUBLISHED, 'commits': [PUBLISHED]}))
        (root / tv.HEADER).write_text("  const VERSION_TEXT = 'Last updated with AmiWind v%s';  // by hand\n" % named)
        (root / tv.INDEX).write_text('<h1>Toolkit<small id="toolkit-version" title="t">Last updated with AmiWind '
                                     'v%s</small></h1>\n' % (index_named or named))
        (root / tv.WORLD_MAP).write_text(world_map(own), encoding='utf-8')
        return root

    def test_changed_toolkit_with_a_stale_line_fails_with_the_fix(self):
        root = self.tree(own='0.1.1')     # own version already raised: the line alone is stale
        with self.assertRaisesRegex(ValueError, r'still says "Last updated with AmiWind v0\.0\.35".*v0\.0\.36.*bump'):
            tv.check(root, fake_git(['amiwind-toolkit/world-map.html']))

    def test_bump_writes_the_release_version_into_both_files(self):
        root = self.tree()
        run = fake_git(['amiwind-toolkit/world-map.html'])
        self.assertIn('v0.0.36', tv.bump(root, run))
        self.assertEqual(tv.named_versions(root), ('0.0.36', '0.0.36'))
        self.assertIn('// by hand', (root / tv.HEADER).read_text())  # the rest of the line is kept
        self.assertEqual(tv.own_version((root / tv.WORLD_MAP).read_text(encoding='utf-8')), '0.1.1')
        self.assertIn('Toolkit 0.1.1, version line: v0.0.36 (1 Toolkit files changed', tv.check(root, run))

    def test_changed_toolkit_raises_its_own_version_by_at_least_one_patch(self):
        root = self.tree(named='0.0.36', own='0.1.0')
        run = fake_git(['amiwind-toolkit/world-map.html'])
        with self.assertRaisesRegex(ValueError, r'own version is 0\.1\.0, not above the previous release.s 0\.1\.0'):
            tv.check(root, run)
        self.assertIn('own version 0.1.0 -> 0.1.1', tv.bump(root, run))
        tv.check(root, run)
        root = self.tree(named='0.0.36', own='0.2.0')     # a bigger hand-made step is kept as is
        self.assertNotIn('own version', tv.bump(root, run))
        tv.check(root, run)

    def test_unchanged_toolkit_keeps_its_older_line(self):
        root = self.tree()
        self.assertIn('Toolkit unchanged', tv.check(root, fake_git([])))
        self.assertIn('left as is', tv.bump(root, fake_git([])))
        self.assertEqual(tv.named_versions(root), ('0.0.35', '0.0.35'))

    def test_header_and_index_must_agree(self):
        root = self.tree(named='0.0.36', index_named='0.0.35')
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            tv.check(root, fake_git([]))

    def test_trees_without_history_are_skipped_not_failed(self):
        root = self.tree()
        self.assertIn('no-git', tv.check(root, fake_git(['amiwind-toolkit/x.html'], git=False)))
        self.assertIn('shallow', tv.check(root, fake_git(['amiwind-toolkit/x.html'], published=False, history=False)))
        def no_git_program(*args):
            raise FileNotFoundError('git')
        self.assertIn('no-git', tv.check(root, no_git_program))
        with self.assertRaisesRegex(ValueError, 'not in this clone'):
            tv.check(root, fake_git([], published=False, history=True))

    def test_the_shipped_files_carry_a_matching_line(self):
        header, index = tv.named_versions(ROOT)
        self.assertEqual(header, index)
        self.assertTrue(tv.own_version((ROOT / tv.WORLD_MAP).read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
