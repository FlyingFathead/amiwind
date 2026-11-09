"""The NPC bake's release fallback (AMIWIND_NPC_BAKE_FALLBACK=dev1): a model the new seam and floor method cannot bake
is baked once more with the v0.0.62-dev1 body rules; off by default; other errors still stop; the environment is put
back after the retry."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import npc_geometry as g  # noqa: E402


class BakeFallback(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        for k in list(g.DEV1_BODY_RULES) + ['AMIWIND_NPC_BAKE_FALLBACK']:
            os.environ.pop(k, None)

    def tearDown(self):
        self.env.stop()

    def test_the_signature_shows_through(self):
        import inspect
        self.assertIn('head_detail', inspect.signature(g.bake).parameters)   # npc_lod reads it

    def test_off_by_default_the_error_stops(self):
        with mock.patch.object(g, '_bake_once', side_effect=g.AliasOverflow('Alias vertex budget exceeded', 3)):
            with self.assertRaises(g.AliasOverflow):
                g.bake([], [], [], None, model='imperial guard')

    def test_overflow_retries_with_the_dev1_rules(self):
        seen = []

        def once(*a, **k):
            seen.append({key: os.environ.get(key) for key in g.DEV1_BODY_RULES})
            if len(seen) == 1:
                raise g.AliasOverflow('Alias vertex budget exceeded', 3)
            return 'baked'

        os.environ['AMIWIND_NPC_BAKE_FALLBACK'] = 'dev1'
        with mock.patch.object(g, '_bake_once', side_effect=once):
            self.assertEqual(g.bake([], [], [], None, model='imperial guard'), 'baked')
        self.assertEqual(seen[0], {k: None for k in g.DEV1_BODY_RULES})
        self.assertEqual(seen[1], g.DEV1_BODY_RULES)
        for k in g.DEV1_BODY_RULES:
            self.assertNotIn(k, os.environ)

    def test_no_split_retries_other_errors_stop(self):
        os.environ['AMIWIND_NPC_BAKE_FALLBACK'] = 'dev1'
        calls = []

        def once(*a, **k):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError('Too many separate shapes for budget')
            return 'baked'

        with mock.patch.object(g, '_bake_once', side_effect=once):
            self.assertEqual(g.bake([], [], [], None), 'baked')
        with mock.patch.object(g, '_bake_once', side_effect=ValueError('something else')):
            with self.assertRaises(ValueError):
                g.bake([], [], [], None)

    def test_a_failing_retry_stops(self):
        os.environ['AMIWIND_NPC_BAKE_FALLBACK'] = 'dev1'
        with mock.patch.object(g, '_bake_once', side_effect=g.AliasOverflow('Alias vertex budget exceeded', 9)):
            with self.assertRaises(g.AliasOverflow):
                g.bake([], [], [], None)


if __name__ == '__main__':
    unittest.main()
