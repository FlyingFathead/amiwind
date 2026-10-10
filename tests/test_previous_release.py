"""Release ancestry check (RELEASE-PREVIOUS-FIXES-MISSING-33): rc and final heads contain the previous release."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import previous_release as pr

PINNED = 'a' * 40
OTHER = 'b' * 40


def fake_git(present=(PINNED,), ancestors=(PINNED,), repo=True):
    def git(*args):
        if args[0] == 'rev-parse':
            return 0 if repo else 128
        if args[0] == 'cat-file':
            return 0 if args[2].split('^')[0] in present else 1
        if args[0] == 'merge-base':
            return 0 if args[2] in ancestors else 1
        raise AssertionError(args)
    return git


class PinTests(unittest.TestCase):
    def test_repository_pin_names_a_version_and_commits(self):
        pin = pr.load_pin(ROOT)
        self.assertTrue(pin['version'])
        self.assertTrue(pin['commits'])

    def test_image_builds_run_the_check_before_any_work(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertIn('require_previous_release(ROOT, VERSION)', text)
        check = text.index('require_previous_release(ROOT, VERSION)')
        self.assertLess(text.index('        if args.host_plan:\n'), check)  # a host plan runs no tools
        self.assertLess(check, text.index("        if getattr(args, 'accept_known_stair_findings', None):\n"))

    def test_release_versions(self):
        for v in ('0.0.34', '0.0.34-rc1', '0.0.34-rc2'):
            self.assertTrue(pr.is_release_version(v), v)
        for v in ('0.0.34-dev', '0.0.34-dev3'):
            self.assertFalse(pr.is_release_version(v), v)


class AncestryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'tools').mkdir()
        (self.root / pr.PIN).write_text(json.dumps({'version': '0.0.33', 'commits': [PINNED]}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_release_with_the_previous_release_passes(self):
        self.assertIsNone(pr.require_previous_release(self.root, '0.0.34-rc1', fake_git()))

    def test_release_without_the_previous_release_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'does not contain the previous release v0.0.33'):
            pr.require_previous_release(self.root, '0.0.34-rc1', fake_git(ancestors=()))
        with self.assertRaisesRegex(ValueError, 'release candidate or final'):
            pr.require_previous_release(self.root, '0.0.34', fake_git(ancestors=()))

    def test_release_with_an_unknown_pin_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'exists in this repository'):
            pr.require_previous_release(self.root, '0.0.34', fake_git(present=()))

    def test_any_pinned_commit_counts(self):
        (self.root / pr.PIN).write_text(json.dumps({'version': '0.0.33', 'commits': [OTHER, PINNED]}),
                                        encoding='utf-8')
        self.assertIsNone(pr.require_previous_release(self.root, '0.0.34', fake_git(present=(OTHER, PINNED))))

    def test_development_version_only_notes(self):
        note = pr.require_previous_release(self.root, '0.0.34-dev2', fake_git(ancestors=()))
        self.assertIn('not refused', note)

    def test_source_tree_without_git_notes(self):
        note = pr.require_previous_release(self.root, '0.0.34', fake_git(repo=False))
        self.assertIn('no git history', note)

    def test_bad_pin_is_refused(self):
        (self.root / pr.PIN).write_text(json.dumps({'version': '0.0.33', 'commits': ['HEAD']}), encoding='utf-8')
        with self.assertRaises(ValueError):
            pr.load_pin(self.root)


class PublishedCommitTests(unittest.TestCase):
    """The published (tagged) release commit is required; a same-tree private commit alone is refused with the fix."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        (self.root / 'tools' / 'previous-release.json').write_text(json.dumps(
            {'version': '0.0.34', 'published': OTHER, 'commits': [OTHER, PINNED]}), encoding='utf-8')

    def test_published_commit_passes(self):
        git = fake_git(present=(OTHER, PINNED), ancestors=(OTHER, PINNED))
        self.assertIsNone(pr.require_previous_release(self.root, '0.0.35', git))

    def test_private_commit_alone_is_refused_with_the_ours_merge(self):
        git = fake_git(present=(OTHER, PINNED), ancestors=(PINNED,))
        with self.assertRaisesRegex(ValueError, 'git merge -s ours --no-edit bbbbbbb'):
            pr.require_previous_release(self.root, '0.0.35-rc1', git)

    def test_neither_is_refused_with_a_real_merge(self):
        git = fake_git(present=(OTHER, PINNED), ancestors=())
        with self.assertRaisesRegex(ValueError, r'fix: git merge bbbbbbb'):
            pr.require_previous_release(self.root, '0.0.35', git)

    def test_published_commit_not_fetched(self):
        git = fake_git(present=(PINNED,), ancestors=(PINNED,))
        with self.assertRaisesRegex(ValueError, 'git fetch origin tag v0.0.34'):
            pr.require_previous_release(self.root, '0.0.35', git)

    def test_repository_pin_requires_the_published_commit(self):
        pin = pr.load_pin(ROOT)
        self.assertIn(pin['published'], pin['commits'])


if __name__ == '__main__':
    unittest.main()
