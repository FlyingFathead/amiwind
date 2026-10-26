# SPDX-License-Identifier: GPL-3.0-only
"""A resident whose animation kit model does not fit the alias byte budget at any rung of the vertex budget ladder
falls back (RESIDENT-ANIM-BYTE-BUDGET-48): the kit's standing model alone, else the idle-only model; the record and
the stage reports say so. Origin: the v0.0.48-dev2 room stage stopped on 'ienas nadus: Alias byte budget exceeded
with full samples'."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

import npc_anim  # noqa: E402
import npc_library as NL  # noqa: E402
import prepare_area as PA  # noqa: E402

TASK = ('/data', b'\0' * 768, {'id': 'ienas nadus', 'skeleton': 'meshes/base_anim.nif'}, {'text': '', 'voice': ''},
        'ffmpeg')


class Levels(unittest.TestCase):
    def test_order(self):
        self.assertEqual(PA.resident_levels('react+full'),
                         [('kit', 'react+full'), ('standing', 'react'), ('idle', 'idle')])
        self.assertEqual(PA.resident_levels('react'), [('kit', 'react'), ('idle', 'idle')])
        self.assertEqual(PA.resident_levels('idle'), [('kit', 'idle')])
        for name in ('react+full', 'react', 'idle', 'move'):
            self.assertEqual(NL.levels(name), PA.resident_levels(name), name)


def fake_bake(fail):
    """A _bake_resident stand-in: profiles in FAIL raise the budget error, others give a record naming the profile."""
    calls = []

    def bake(task, profile):
        calls.append(profile)
        if profile in fail:
            raise PA.ResidentBudgetError(task[2]['id'] + ': ' + PA.BYTE_BUDGET_ERROR)
        record = {'appearance': task[2], 'frames': {'react+full': 30, 'react': 16, 'idle': 8}[profile]}
        if profile != 'idle':
            record['anim'] = {'profile': profile}
        return task[2]['id'], b'model-' + profile.encode(), b'', record
    return bake, calls


class Fallback(unittest.TestCase):
    def run_with(self, fail):
        bake, calls = fake_bake(fail)
        with patch.dict('os.environ', {'AMIWIND_NPC_ANIM': 'react+full'}), \
                patch.object(PA, '_bake_resident', bake), patch('builtins.print'):
            return PA.build_resident(TASK), calls

    def test_fits_no_fallback(self):
        (identifier, raw, _, record), calls = self.run_with(())
        self.assertEqual(calls, ['react+full'])
        self.assertEqual(raw, b'model-react+full')
        self.assertNotIn('anim_fallback', record)

    def test_standing_model_when_the_kit_does_not_fit(self):
        (identifier, raw, _, record), calls = self.run_with({'react+full'})
        self.assertEqual(calls, ['react+full', 'react'])
        self.assertEqual(raw, b'model-react')
        self.assertEqual(record['anim']['profile'], 'react')
        fb = record['anim_fallback']
        self.assertEqual((fb['profile'], fb['level'], fb['baked']), ('react+full', 'standing', 'react'))
        self.assertIn(PA.BYTE_BUDGET_ERROR, fb['reasons'][0])
        self.assertTrue(PA.json_record(record) == record)    # the unit cache stores it (json_exact)

    def test_idle_when_the_standing_model_does_not_fit_either(self):
        (identifier, raw, _, record), calls = self.run_with({'react+full', 'react'})
        self.assertEqual(calls, ['react+full', 'react', 'idle'])
        self.assertEqual(raw, b'model-idle')
        self.assertNotIn('anim', record)                     # the previous method: no layout, no mover
        self.assertEqual(record['anim_fallback']['level'], 'idle')
        self.assertEqual(len(record['anim_fallback']['reasons']), 2)

    def test_same_inputs_same_outcome(self):
        a, _ = self.run_with({'react+full'})
        b, _ = self.run_with({'react+full'})
        self.assertEqual(a, b)

    def test_other_errors_still_stop(self):
        def bake(task, profile):
            raise ValueError('ienas nadus: Alias vertex budget exceeded')
        with patch.object(PA, '_bake_resident', bake), self.assertRaisesRegex(ValueError, 'vertex budget'):
            PA.build_resident(TASK)

    def test_anim_fallbacks_lists_by_id(self):
        models = {'b': {'anim_fallback': {'profile': 'react+full', 'level': 'idle', 'baked': 'idle', 'reasons': []}},
                  'a': {'anim_fallback': {'profile': 'react+full', 'level': 'standing', 'baked': 'react',
                                          'reasons': []}},
                  'c': {}}
        self.assertEqual([(r['id'], r['level']) for r in PA.anim_fallbacks(models)], [('a', 'standing'), ('b', 'idle')])


class BakeRaises(unittest.TestCase):
    """_bake_resident turns the ladder's last byte-budget error (and fit's) into ResidentBudgetError."""

    def setUp(self):
        groups = [{'name': 'idle', 'base': 0, 'count': 8, 'kind': 'loop', 'step': .1, 'events': []}]
        self.patches = [patch.object(PA, 'Assets', lambda *a: object()), patch.object(PA, 'BSA', lambda *a: None),
                        patch.object(PA, 'child_ci', lambda *a: Path('/x')),
                        patch.object(PA, 'Skeleton', lambda *a: object()),
                        patch.object(npc_anim, 'plan', lambda *a, **k: (object(), groups)),
                        patch.object(npc_anim, 'soun_records', lambda *a: {}),
                        patch.object(PA, 'assemble', lambda *a: ([], [], [])),
                        patch.dict(PA._resident_assets, clear=True), patch.dict(PA._resident_rigs, clear=True),
                        patch.dict(PA._resident_sounds, clear=True),
                        # the baked kit's ladder (--npc-anim-type 1); skeletal actors have no byte budget fallback
                        patch.dict('os.environ', {npc_anim.ANIM_TYPE_ENV: '1'})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def test_byte_budget_at_every_rung(self):
        budgets = []

        def bake(*a, budget, full_frame_budget, **k):
            budgets.append((budget, full_frame_budget))
            raise ValueError(PA.BYTE_BUDGET_ERROR)
        with patch.object(PA, 'bake', bake), self.assertRaises(PA.ResidentBudgetError) as caught:
            PA._bake_resident(TASK, 'react+full')
        self.assertEqual(str(caught.exception), 'ienas nadus: ' + PA.BYTE_BUDGET_ERROR)
        self.assertEqual(budgets, [(b, npc_anim.ACTOR_BYTE_BUDGET) for b in PA.RESIDENT_LADDER])

    def test_32mb_budget_takes_the_full_kit(self):
        """ALIAS-BUDGET-32MB-48: Neloth's and Ienas Nadus's react+full kit (64 samples, 620 faces, 336 skin rows:
        682,312 bytes, measured 23 October 2026) is over the 512 KiB staging limit and within the actors' 32 MB
        budget: the kit level, no fallback; the bake and both fits are given the actors' budget."""
        full = npc_anim.alias_bytes(64, 620 * 3, 620, 512, 336)
        self.assertEqual(full, 682312)
        self.assertGreater(full, npc_anim.ALIAS_BYTE_BUDGET)
        self.assertLessEqual(full, npc_anim.ACTOR_BYTE_BUDGET)
        # the largest kit the vertex ladder allows (666 faces, 64 samples) fits too: no actor is reduced for bytes
        self.assertLessEqual(npc_anim.alias_bytes(64, 666 * 3, 666, 512, 336), npc_anim.ACTOR_BYTE_BUDGET)
        seen = []

        class Skin:
            size = (64, 64)

        def bake(*a, budget, full_frame_budget, **k):
            seen.append(('bake', full_frame_budget))
            return np.zeros((8, 3, 3)), [(0, 1, 2)], None, Skin()

        def fit(*a):
            seen.append(('fit', a[5]))
            raise npc_anim.AliasBudgetError('stop')
        with patch.object(PA, 'bake', bake), patch.object(npc_anim, 'fit', fit), \
                self.assertRaises(PA.ResidentBudgetError):
            PA._bake_resident(TASK, 'react+full')
        self.assertEqual(seen, [('bake', npc_anim.ACTOR_BYTE_BUDGET), ('fit', npc_anim.ACTOR_BYTE_BUDGET)])

    def test_actor_budget_is_the_engine_stream_limit(self):
        """The actors' budget is what the engine streams straight into its cache (model.c AW_ALIAS_STREAM_LIMIT, the
        heap estimate's alias_stream_heap.STREAM_LIMIT); the player's models keep the staging limit."""
        import re
        import alias_stream_heap
        text = (ROOT / 'engine/aga/src/model.c').read_text(encoding='utf-8', errors='replace')
        stream = re.search(r'#define AW_ALIAS_STREAM_LIMIT \((\d+)\*1024\)', text)
        staging = re.search(r'#define AW_ALIAS_STAGING_LIMIT \((\d+)\*1024\)', text)
        self.assertEqual(int(stream.group(1)) * 1024, npc_anim.ACTOR_BYTE_BUDGET)
        self.assertEqual(int(staging.group(1)) * 1024, npc_anim.ALIAS_BYTE_BUDGET)
        self.assertEqual(alias_stream_heap.STREAM_LIMIT, npc_anim.ACTOR_BYTE_BUDGET)
        inc = (ROOT / 'engine/aga/src/model_alias_stream.inc').read_text(encoding='utf-8')
        self.assertNotIn('AW_ALIAS_STAGING_LIMIT', inc)
        # the file size, the decoded size, and the decoded size again with a skeletal block (docs/MODULAR_NPCS.md
        # method C: the AWSB block after the rest frame counts in the same limit)
        self.assertEqual(inc.count('AW_ALIAS_STREAM_LIMIT'), 3)

    def test_vertex_budget_at_the_last_rung_is_not_a_fallback(self):
        def bake(*a, budget, **k):
            raise ValueError('Alias vertex budget exceeded')
        with patch.object(PA, 'bake', bake), self.assertRaises(ValueError) as caught:
            PA._bake_resident(TASK, 'react+full')
        self.assertNotIsInstance(caught.exception, PA.ResidentBudgetError)

    def test_fit_over_budget(self):
        class Skin:
            size = (64, 64)

        def bake(*a, **k):
            return np.zeros((8, 3, 3)), [(0, 1, 2)], None, Skin()

        def fit(*a, **k):
            raise npc_anim.AliasBudgetError('Alias byte budget exceeded even at the smallest frame counts')
        with patch.object(PA, 'bake', bake), patch.object(npc_anim, 'fit', fit), \
                self.assertRaises(PA.ResidentBudgetError):
            PA._bake_resident(TASK, 'react')


class Library(unittest.TestCase):
    def test_library_falls_back_the_same_way(self):
        calls = []

        def bake(task):
            calls.append(task[3])
            if task[3] == 'react+full':
                raise NL.BudgetError('ienas nadus: ' + NL.BYTE_BUDGET_ERROR)
            return b'm', '', {}, {'bytes': 1, 'frames': 16}
        app = {'id': 'ienas nadus'}
        with patch.object(NL, '_bake_standing', bake), patch('builtins.print'):
            raw, layout, sounds, facts = NL.bake_standing(('/data', b'', app, 'react+full'))
        self.assertEqual(calls, ['react+full', 'react'])
        self.assertEqual(facts['anim_fallback']['level'], 'standing')


class StageCount(unittest.TestCase):
    def test_summary_line(self):
        import build_summary as S
        from room_batches import RECORD
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(S.read_resident_fallback(tmp))
            (Path(tmp) / 'chim-room-batches').mkdir()
            fb = {'count': 2, 'by_level': {'idle': 1, 'standing': 1}, 'ids': {'idle': ['x'], 'standing': ['ienas nadus']}}
            (Path(tmp) / 'chim-room-batches' / RECORD).write_text(json.dumps({'residents': {'anim_fallback': fb}}))
            line = S.resident_fallback_line(S.read_resident_fallback(tmp))
        self.assertIn('2 (idle 1: x; standing 1: ienas nadus)', line)
        self.assertIn('none', S.resident_fallback_line({'count': 0, 'by_level': {}, 'ids': {}}))


if __name__ == '__main__':
    unittest.main()
