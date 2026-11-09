"""The per-model face override list (config/model-face-overrides.json, NPC-BODY-REGRESSION-62)."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import model_face_overrides as mfo  # noqa: E402


def write(entries):
    handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump({'schema': 1, 'entries': entries}, handle)
    handle.close()
    return handle.name


GOOD = {'model': 'Some Actor', 'kind': 'npc', 'extra_faces': 20, 'reason': 'a wrist kept whole',
        'cost': {'before': 480, 'added': 19, 'total': 499}, 'pi_check': 'pending'}


class Overrides(unittest.TestCase):
    def tearDown(self):
        mfo._cache.clear()

    def test_shipped_file_is_valid(self):
        mfo.load()

    def test_entry_read_by_id_and_kind(self):
        path = write([GOOD])
        try:
            self.assertEqual(mfo.extra_faces('some actor', 'npc', path), 20)
            self.assertEqual(mfo.extra_faces('some actor', 'creature', path), 0)
            self.assertEqual(mfo.extra_faces('nobody', 'npc', path), 0)
        finally:
            os.unlink(path)

    def test_bad_entries_refused(self):
        for bad in ({**GOOD, 'extra_faces': 0}, {**GOOD, 'reason': ''}, {**GOOD, 'pi_check': ''},
                    {**GOOD, 'kind': 'static'}, {**GOOD, 'cost': {'before': 480, 'added': 19, 'total': 500}},
                    {**GOOD, 'cost': {'before': 480, 'added': 30, 'total': 510}}):
            path = write([bad])
            try:
                mfo._cache.clear()
                with self.assertRaises(ValueError):
                    mfo.load(path)
            finally:
                os.unlink(path)
        path = write([GOOD, GOOD])
        try:
            with self.assertRaises(ValueError):
                mfo.load(path)
        finally:
            os.unlink(path)

    def test_growth_only_through_an_entry(self):
        """npc_geometry.bake grows a model past today's total only by its extra_faces (grow_to), and the callers
        take extra_faces from this module only."""
        source = (ROOT / 'tools/npc_geometry.py').read_text(encoding='utf-8')
        grows = re.findall(r'grow_to=([^\n]*)', source)
        self.assertTrue(grows)
        for line in grows:
            if line.strip().startswith('None'):
                continue
            self.assertIn('extra_faces', line)
        for path in (ROOT / 'tools').glob('*.py'):
            if path.name in ('npc_geometry.py', 'model_face_overrides.py'):
                continue
            for match in re.finditer(r'extra_faces\s*=\s*([^,)\n]+)', path.read_text(encoding='utf-8')):
                self.assertIn('extra_faces(', match.group(1), '%s passes extra_faces=%s' % (path.name, match.group(1)))


if __name__ == '__main__':
    unittest.main()
