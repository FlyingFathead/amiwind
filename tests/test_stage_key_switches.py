# SPDX-License-Identifier: GPL-3.0-only
"""Stage keys leave default-off switch code out, engine header words keep only value items, and a whole stage that
would run again stops the reuse preflight (CHIM-KEYS-TOO-BROAD-62)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build_cache as B          # noqa: E402
import engine_facts as E         # noqa: E402
import reuse_all as RA           # noqa: E402

SWITCH = {'id': 'T', 'flags': ('--twosided',), 'default': 'off', 'setting': 'twosided', 'guard': 'mode_of',
          'definitions': {'tools/m.py': ('MODES', 'mode_of', 'mirror')}, 'modules': ('tools/m.py',)}

BEFORE = '''import x


def build(settings, a):
    out = [a]
    out.append(2)
    return dict({'k': 1},
                **({'grain': a} if a else {}),
                q=1)


def cli(ap):
    ap.add_argument('--grain')
    return ap
'''

AFTER = '''import x


MODES = ('off', 'mirror')


def mode_of(settings):
    return settings.get('twosided', 'off')


def mirror(v):
    return v


def build(settings, a):
    out = [a]
    # the converter route (off by default)
    if mode_of(settings) == 'mirror' and a:
        out = [mirror(a)]
    out.append(2)
    return dict({'k': 1},
                **({'grain': a} if a else {}),
                **({'twosided': a} if a != 'off' else {}),
                q=1)


def cli(ap):
    ap.add_argument('--grain')
    ap.add_argument('--twosided', choices=('off', 'mirror'),
                    default='off')
    return ap
'''


class StripSwitchesTests(unittest.TestCase):
    def test_off_switch_leaves_the_text_as_before(self):
        stripped = B.strip_switches('tools/m.py', AFTER, (SWITCH,))
        # the module's units are what they were (blank lines between top-level items do not count)
        texts = lambda t: {k: v for k, v in B.module_symbols(__import__('ast').parse(t), t, refined=True,
                                                              split=True)['texts'].items()}
        self.assertEqual(texts(stripped), texts(BEFORE))

    def test_other_modules_unchanged(self):
        self.assertIs(B.strip_switches('tools/other.py', BEFORE, (SWITCH,)), BEFORE)

    def test_if_with_else_stays(self):
        text = 'def f(s):\n    if mode_of(s):\n        a = 1\n    else:\n        a = 2\n    return a\n'
        self.assertEqual(B.strip_switches('tools/other.py', text, (SWITCH,)), text)

    def test_switches_on(self):
        self.assertEqual(B.switches_on(['x', '--twosided', 'off'], (SWITCH,)), [])
        self.assertEqual(B.switches_on(['x', '--twosided', 'mirror'], (SWITCH,)), [SWITCH])
        self.assertEqual(B.switches_on(['x', '--twosided=mirror'], (SWITCH,)), [SWITCH])

    def test_registered_switch_modules_exist(self):
        for switch in B.DEFAULT_OFF_SWITCHES:
            for path in list(switch['definitions']) + list(switch['modules']):
                self.assertTrue((ROOT / path).is_file(), path)
            self.assertIn(switch['guard'], (ROOT / next(iter(switch['definitions']))).read_text(encoding='utf-8'))


HEADER = '''#ifndef H
#define H
#define LIMIT 12
extern int mirror;
#if defined(AMIGA) && defined(__m68k__)
void TryFree (void *block);
#define free(block) TryFree (block)
struct sized { int a; };
#endif
#endif
'''


class EngineFactsReadingFiveTests(unittest.TestCase):
    def kept(self, roots=(), words=(), version=5):
        out, _ = E.kept_items({'h.h': HEADER}, set(roots), version, (), set(words))
        return [item['text'] for item in out['h.h']]

    def test_words_keep_only_values(self):
        kept = self.kept(words={'mirror', 'free', 'LIMIT'})
        self.assertIn('#define LIMIT 12', kept)
        self.assertFalse(any('mirror' in t for t in kept))
        self.assertFalse(any(t.startswith('#define free') for t in kept))

    def test_compiled_names_keep_host_items_but_not_target_only_functions(self):
        kept = self.kept(roots={'mirror', 'free', 'sized'})
        self.assertTrue(any('mirror' in t for t in kept))
        self.assertFalse(any(t.startswith('#define free') for t in kept))
        self.assertTrue(any('struct sized' in t for t in kept))

    def test_reading_four_as_before(self):
        kept = self.kept(roots={'mirror', 'free'}, version=4)
        self.assertTrue(any(t.startswith('#define free') for t in kept))


class UnitCacheKeyTests(unittest.TestCase):
    def test_unit_cache_index_leaves_switch_code_out(self):
        self.assertTrue(B.SourceIndex(ROOT, top_format=2).switch_neutral())
        self.assertTrue(B.SourceIndex(ROOT, top_format=B.STAGE_TOP_FORMAT).switch_neutral())
        self.assertFalse(B.SourceIndex(ROOT, top_format=B.STAGE_TOP_FORMAT, engine_facts=4).switch_neutral())

    def test_preflight_sees_the_actor_caches(self):
        names = {row['name'] for row in RA.unit_cache_openers(ROOT) if row['scripts']}
        self.assertIn('room-actor', names)


class WholeStageStopTests(unittest.TestCase):
    STEPS = [('a', []), ('b', [])]

    def test_stops_over_the_limit_and_allows(self):
        problems = RA.strict_problems(self.STEPS, {'a', 'b'}, {}, {}, set(), {}, costs={'a': 13000.0, 'b': 30.0},
                                      reasons={'a': 'changed: sources (x)', 'b': 'changed: sources (y)'})
        self.assertEqual([p[0] for p in problems], ['a'])
        self.assertIn('217 min', problems[0][1])
        self.assertEqual(RA.strict_problems(self.STEPS, {'a'}, {}, {}, set(), {'a': 'why'}, costs={'a': 13000.0},
                                            reasons={'a': 'changed: sources (x)'}), [])

    def test_new_stage_does_not_stop(self):
        self.assertEqual(RA.strict_problems(self.STEPS, {'a'}, {}, {}, set(), {}, costs={'a': 13000.0},
                                            reasons={'a': 'no earlier run holds it'}), [])

    def test_stored_seconds_follows_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp, 'one'), Path(tmp, 'two')
            one.mkdir(), two.mkdir()
            (one / 'build-profile.json').write_text(json.dumps({'stages': [{'name': 'a', 'wall': 900.0}]}))
            (two / 'build-profile.json').write_text(json.dumps(
                {'stages': [{'name': 'a', 'wall': 1.0, 'reused': {'from': str(one)}}]}))
            self.assertEqual(RA.stored_seconds(two, 'a'), 900.0)
            self.assertIsNone(RA.stored_seconds(two, 'missing'))


if __name__ == '__main__':
    unittest.main()
