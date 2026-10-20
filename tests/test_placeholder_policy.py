"""Stand-in assets stop the build unless a test build names them or an open bug is the known gap
(SKY-FLAT-PALETTE-DRIFT-41). Synthetic files only."""
import contextlib
import json
import hashlib
import io
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import placeholder_policy as P


class PolicyTests(unittest.TestCase):
    def test_refusal_names_placeholder_unit_input_hash_and_opt_out(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'palette.lmp'; path.write_bytes(b'x' * 768)
            with self.assertRaises(P.PlaceholderRefused) as caught:
                P.check('shared-sky', 'not prepared', (), unit='gfx/aw_shared_sky.lmp', inputs=[path, Path(folder) / 'gone'])
            text = str(caught.exception)
            for word in ('shared-sky', 'gfx/aw_shared_sky.lmp', hashlib.sha256(b'x' * 768).hexdigest(),
                         'gone missing', '--allow-placeholder shared-sky', 'refused for release candidates'):
                self.assertIn(word, text)

    def test_allowed_placeholder_is_loud_and_recorded(self):
        records, out = [], io.StringIO()
        with contextlib.redirect_stdout(out):
            record = P.check('intro-video', 'not staged', {'intro-video'}, unit='intro/mw_intro.awv', records=records)
        self.assertEqual(records, [record])
        self.assertIn('[PLACEHOLDER ALLOWED] intro-video', out.getvalue())

    def test_known_gap_ships_loud_and_recorded_with_its_bug(self):
        # The default build must not stop on a stand-in an open bug already explains (every build ships an
        # empty night-windows table today); it is named on stdout and in the receipt with that bug.
        records, out = [], io.StringIO()
        with contextlib.redirect_stdout(out):
            record = P.check('night-windows', 'empty table', (), unit='world/night-windows.txt', records=records)
        self.assertEqual(records, [record])
        self.assertEqual(record['known_gap'], 'NIGHT-WINDOWS-LOST-CHIM-36')
        self.assertIn('[PLACEHOLDER KNOWN GAP] night-windows', out.getvalue())
        self.assertIn('NIGHT-WINDOWS-LOST-CHIM-36', out.getvalue())

    def test_known_gaps_are_open_bugs(self):
        # Fixing the bug removes the entry, so the stand-in stops the build again.
        rows = {row['id']: row for row in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for name, bug in P.KNOWN_GAPS.items():
            self.assertIn(name, P.NAMES)
            self.assertIn(bug, rows, name)
            self.assertEqual(rows[bug]['state'], 'open',
                             '%s is no longer open: remove %s from placeholder_policy.KNOWN_GAPS' % (bug, name))

    def test_parse_accepts_known_names_only(self):
        self.assertEqual(P.parse(['shared-sky,night-sky', 'ui-font']), {'shared-sky', 'night-sky', 'ui-font'})
        with self.assertRaisesRegex(ValueError, 'unknown placeholder'):
            P.parse(['clouds'])

    def test_every_name_has_a_check_site(self):
        sources = ''.join((ROOT / 'tools' / name).read_text(encoding='utf-8')
                          for name in ('build_aga.py', 'prepare_shared_sky_assets.py'))
        for name in P.NAMES:
            self.assertRegex(sources, r"(placeholder\(args, ?|check\()'%s'" % re.escape(name), name)

    def test_builder_option_is_a_private_test_waiver(self):
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('"--allow-placeholder"', source)
        self.assertIn("require_private_test_version(VERSION, [placeholder_policy.OPTION", source)
        self.assertIn("image_options += ['--allow-placeholder', name]", source)
