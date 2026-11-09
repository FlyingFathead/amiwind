# SPDX-License-Identifier: GPL-3.0-only
"""Risky stages first (BUILD-RISKY-STAGES-FIRST-63): the v0.0.62 final build stopped after 5 h in its last step on a
player body, a bake that needs nothing of the world.

Checked: the default plan has the player-view stage (tools/player_view_stage.py) right after the census, waiting for
no world stage, and the image waits for it; every risky stage that needs no world stage is placed before every world
stage and the scheduler starts it first among the stages ready with it; --player-body off has no such stage; the
pre-flight checks every stored model against the engine's limits, names every model over one and stops before any
bake; its limits are the engine headers' own. Synthetic data only.
"""
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def steps(*extra):
    import build
    from test_build_defaults import TOOLS, RUN
    args = build.parser().parse_args(list(extra))
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, TOOLS, RUN)


def reaches(deps, name):
    """Every stage NAME waits for, directly or not."""
    seen, todo = set(), list(deps[name])
    while todo:
        d = todo.pop()
        if d not in seen:
            seen.add(d)
            todo.extend(deps.get(d, ()))
    return seen


class RiskyStagesFirst(unittest.TestCase):

    def test_player_view_stage_after_the_census_beside_the_world(self):
        from build_parallel import stage_dependencies
        plan = steps()
        names = [n for n, _ in plan]
        self.assertIn('player-view', names)
        self.assertLess(names.index('census'), names.index('player-view'))
        deps = stage_dependencies(plan)
        # inserting it changed no other stage's dependencies
        without = stage_dependencies([s for s in plan if s[0] != 'player-view'])
        self.assertEqual({k: tuple(d for d in v if d != 'player-view') for k, v in deps.items() if k != 'player-view'},
                         without)
        self.assertEqual(deps['player-view'], ('census',))
        self.assertIn('player-view', deps['image'])
        command = [str(x) for x in dict(plan)['player-view']]
        self.assertIn('player_view_stage.py', command[1])
        self.assertIn('intro-scene/id1/gfx/palette.lmp', ' '.join(command))

    def test_no_stage_with_the_player_body_off(self):
        self.assertNotIn('player-view', [n for n, _ in steps('--player-body', 'off')])

    def test_a_world_independent_risky_stage_is_never_scheduled_after_a_world_stage(self):
        from build_parallel import RISK_FIRST, risk_first, stage_dependencies, world_stage
        plan = steps()
        names = [n for n, _ in plan]
        deps = stage_dependencies(plan)
        worlds = [n for n in names if world_stage(n)]
        self.assertTrue(worlds)
        independent = [n for n in RISK_FIRST if n in names and not any(world_stage(d) for d in reaches(deps, n))]
        self.assertIn('player-view', independent)
        for name in independent:
            # it waits for no world stage, so it is ready no later than any of them
            self.assertFalse(any(world_stage(d) for d in reaches(deps, name)), name)
            # and is started first among the stages ready with it
            ready = [(i, step) for i, step in enumerate(plan, 1) if step[0] in (name, *worlds)]
            self.assertEqual(risk_first(list(reversed(ready)))[0][1][0], name)

    def test_risk_first_keeps_plan_order_otherwise(self):
        from build_parallel import risk_first
        ready = [(3, ('b', [])), (1, ('a', [])), (5, ('player-view', [])), (2, ('actor-library', []))]
        self.assertEqual([s[0] for _, s in risk_first(ready)], ['actor-library', 'player-view', 'a', 'b'])


class PreFlight(unittest.TestCase):

    def test_limits_are_the_engine_headers(self):
        import npc_anim
        from player_view_stage import LIMITS
        local = (ROOT / 'engine/aga/src/r_local.h').read_text(encoding='latin-1')
        model = (ROOT / 'engine/aga/src/gl_model.h').read_text(encoding='latin-1')
        self.assertEqual(LIMITS['vertices'], int(re.search(r'#define\s+MAXALIASVERTS\s+(\d+)', local).group(1)))
        self.assertEqual(LIMITS['triangles'], int(re.search(r'#define\s+MAXALIASTRIS\s+(\d+)', model).group(1)))
        self.assertEqual(LIMITS['frames'], int(re.search(r'#define\s+MAXALIASFRAMES\s+(\d+)', model).group(1)))
        self.assertEqual(LIMITS['bytes'], npc_anim.ALIAS_BYTE_BUDGET)

    def test_every_model_over_a_limit_is_named_before_any_bake(self):
        import prepare_player_view as view
        from player_view_stage import preflight
        tasks = [('data', b'\1' * 768, race, female) for race in ('nord', 'orc') for female in (False, True)]
        swim = [t + ({'model': view.body_path(t[2], t[3])},) for t in tasks]

        class Cache:
            def load_unit(self, inputs):
                name = inputs['entry']['name']
                if name == 'body orc female':
                    return None                                       # still to bake
                row = {'bytes': 1000, 'frames': 40, 'vertices': 400, 'triangles': 700, 'model': 'm', 'groups': {}}
                if name == 'body nord male':
                    row['vertices'] = 4000
                if name == 'swim orc male':
                    row['bytes'] = 600 * 1024
                return {'parts': [{'value': 'p'}, {'value': row}]}, {}
        lines = []
        checked, missing, problems = preflight(tasks, swim, Cache(), log=lambda *a, **k: lines.append(a[0]))
        self.assertEqual(missing, 2)                                  # the orc woman's body and her torch body
        self.assertEqual(checked, 4 + 4 + 4 - 1 + 3)
        self.assertEqual(sorted(p.split(':')[0] for p in problems), ['body nord male', 'swim orc male'])
        self.assertTrue(any('OVER: body nord male: vertices 4000 over its limit 3072' in line for line in lines))

    def test_no_cache_checks_nothing(self):
        from player_view_stage import preflight
        tasks = [('data', b'\1' * 768, 'nord', False)]
        self.assertEqual(preflight(tasks, [t + ({'model': 'm'},) for t in tasks], None, log=lambda *a, **k: None),
                         (0, 4, []))


if __name__ == '__main__':
    unittest.main()
