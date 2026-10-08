# SPDX-License-Identifier: GPL-3.0-only
"""follow_original_stair_rules: Morrowind's stair/slope collision rules are ON by default (owner decision
2026-10-08); a build config or the CLI can turn them off for debugging, and the choice is resolved once."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from build_font_options import add_font_options, resolve_font_options  # noqa: E402


def parse(argv):
    p = argparse.ArgumentParser()
    add_font_options(p)
    return p.parse_args(argv)


class StairRulesOptionTests(unittest.TestCase):
    def test_shipped_default_is_true(self):
        self.assertIs(json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))['follow_original_stair_rules'], True)
        o = resolve_font_options(parse([]))
        self.assertIs(o['follow_original_stair_rules'], True)
        self.assertEqual(o['follow_original_stair_rules_selected_by'], 'shipped default')

    def test_cli_off_and_on(self):
        self.assertIs(resolve_font_options(parse(['--no-follow-original-stair-rules']))['follow_original_stair_rules'], False)
        o = resolve_font_options(parse(['--follow-original-stair-rules']))
        self.assertIs(o['follow_original_stair_rules'], True)
        self.assertEqual(o['follow_original_stair_rules_selected_by'], 'CLI override')

    def test_build_config_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'b.json'
            cfg.write_text('{"follow_original_stair_rules": false}', encoding='utf-8')
            o = resolve_font_options(parse(['--build-config', str(cfg)]))
            self.assertIs(o['follow_original_stair_rules'], False)
            self.assertEqual(o['follow_original_stair_rules_selected_by'], 'build config')
            cfg.write_text('{"follow_original_stair_rules": "yes"}', encoding='utf-8')
            with self.assertRaises(ValueError):
                resolve_font_options(parse(['--build-config', str(cfg)]))

    def test_cli_flags_are_exclusive(self):
        with self.assertRaises(SystemExit):
            parse(['--follow-original-stair-rules', '--no-follow-original-stair-rules'])


if __name__ == '__main__':
    unittest.main()
