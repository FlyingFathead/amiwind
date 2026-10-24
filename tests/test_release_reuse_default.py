# SPDX-License-Identifier: GPL-3.0-only
"""The release kind never switches a verified cache off (IMPERATIVE, the maintainer 2026-10-24 02:53 +0300 /
2026-10-23 23:53 UTC: "IF THE WORLD HASN'T CHANGED; WE CAN USE IT CACHED NO MATTER IF IT'S RC1 RC2 RC3 RC1000 or the
FINAL ACTUAL RELEASE"): release candidates and finals reuse like -devN builds by default; --release-from-scratch and
--clean build them from scratch (the reproducibility gate)."""
import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import build  # noqa: E402
import build_cache  # noqa: E402
import pass_cache  # noqa: E402


class ReleaseReuseDefaultTests(unittest.TestCase):
    def resolved(self, *argv):
        args = build.parser().parse_args(list(argv))
        return build_cache.resolve_release_reuse(args)

    def test_release_reuse_is_the_default(self):
        self.assertIs(build.parser().parse_args([]).allow_release_reuse, None)
        self.assertTrue(self.resolved())
        self.assertTrue(self.resolved('--allow-release-reuse'))

    def test_from_scratch_on_request(self):
        self.assertFalse(self.resolved('--release-from-scratch'))

    def test_a_clean_build_is_from_scratch(self):
        args = argparse.Namespace(allow_release_reuse=None, clean=True)
        self.assertFalse(build_cache.resolve_release_reuse(args))

    def test_a_final_takes_the_caches_by_default(self):
        args = argparse.Namespace(allow_release_reuse=None, clean=False)
        allowed = build_cache.resolve_release_reuse(args)
        for version in ('0.0.49-rc1', '0.0.49'):
            self.assertNotEqual(pass_cache.setting(version, '/w', allowed), 'off', version)
            build_cache.require_reuse_allowed(version, allowed)    # no refusal


if __name__ == '__main__':
    unittest.main()
