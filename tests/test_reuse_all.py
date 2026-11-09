"""--reuse-all-available (BUILD-UNIT-PREFLIGHT-63): every earlier run of the workspace is a reuse source. The stopped
v0.0.63-dev1 run had 26 passed stages that could not be combined with the v0.0.62 release run's stages, because
--reuse-from takes exactly one run. Here: the stage index, the newest-match choice, the combination of several runs'
plans, the minute-one lines, the strict stop and the gate check on per-item bakes with no cache."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import reuse_all as RA  # noqa: E402


def write_run(workspace, name, started, stages, failed=()):
    run = Path(workspace) / 'build' / name
    run.mkdir(parents=True, exist_ok=True)
    steps = [{'name': stage, 'status': 'passed'} for stage in stages] + [{'name': s, 'status': 'failed'} for s in failed]
    fingerprints = dict(stages, **{s: 'f-' + s for s in failed})
    (run / 'build-state.json').write_text(json.dumps({
        'build_started_at': started, 'status': 'passed' if not failed else 'failed', 'steps': steps,
        'stage_cache': {'schema': 'amiwind-stage-cache-v2', 'fingerprints': fingerprints}}))
    return run


def plan(run, files=None, links=None, skipped=None, hazards=None):
    return {'from': str(run), 'fingerprint': 'x', 'files': files or {}, 'links': links or {}, 'skipped': skipped or {},
            'rebuild_hazard_stages': hazards or {}, 'rebuild_hazard': ['p'] if hazards else []}


class StageIndex(unittest.TestCase):
    def test_index_rows_newest_match_and_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_run(tmp, 'old', '2026-11-08T10:00:00+00:00', {'a': 'A', 'b': 'B'})
            write_run(tmp, 'new', '2026-11-09T10:00:00+00:00', {'a': 'A', 'b': 'B2'}, failed=('c',))
            index = RA.update_index(tmp)
            self.assertTrue(RA.index_path(tmp).is_file())
            self.assertEqual(sorted(index['runs']['new']['stages']), ['a', 'b'])       # the failed stage is left out
            found = RA.matches(index, {'a': 'A', 'b': 'B', 'c': 'f-c'})
            self.assertEqual(found['a'], ['new', 'old'])                                  # newest first
            self.assertEqual(found['b'], ['old'])
            self.assertNotIn('c', found)
            self.assertEqual(RA.candidate_runs(index, {'a': 'A', 'b': 'B'}), ['new', 'old'])
            self.assertEqual(RA.candidate_runs(index, {'a': 'A'}, exclude={'new'}), ['old'])
            self.assertEqual(RA.candidate_runs(index, {'a': 'A', 'b': 'B'}, preferred='old')[0], 'old')
            # a run that changed is read again; a removed run leaves the index
            write_run(tmp, 'new', '2026-11-09T10:00:00+00:00', {'a': 'A', 'b': 'B'})
            import shutil
            shutil.rmtree(Path(tmp) / 'build' / 'old')
            index = RA.update_index(tmp)
            self.assertEqual(sorted(index['runs']), ['new'])
            self.assertEqual(RA.matches(index, {'b': 'B'})['b'], ['new'])

    def test_rows_and_record_never_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_run(tmp, 'r', '2026-11-09T10:00:00+00:00', {'a': 'A'})
            RA.record_run(Path(tmp) / 'build' / 'r', tmp)
            self.assertEqual(RA.rows(json.loads(RA.index_path(tmp).read_text())), [('r', 'a', 'A', '2026-11-09T10:00:00+00:00')])
            RA.record_run(Path(tmp) / 'nowhere' / 'x', Path(tmp) / 'nowhere')     # nothing there: no exception


class Combine(unittest.TestCase):
    def test_newest_option_kept_when_consistent(self):
        deps = {'a': [], 'b': ['a']}
        options = {'a': [('N', plan('N')), ('O', plan('O'))], 'b': [('O', plan('O'))]}
        taken, over = RA.combine(['a', 'b'], deps, options, lambda s, x, y: True)
        self.assertEqual({k: v[0] for k, v in taken.items()}, {'a': 'N', 'b': 'O'})
        self.assertEqual(over, {})

    def test_dependency_with_other_outputs_passes_over(self):
        deps = {'a': [], 'b': ['a']}
        options = {'a': [('N', plan('N'))], 'b': [('O', plan('O')), ('N', plan('N'))]}
        taken, over = RA.combine(['a', 'b'], deps, options, lambda s, x, y: False)
        self.assertEqual(taken['b'][0], 'N')                     # same run as its dependency
        self.assertIn('other outputs', over['b'][0])
        taken, over = RA.combine(['a', 'b'], deps, {'a': options['a'], 'b': [('O', plan('O'))]},
                                 lambda s, x, y: False)
        self.assertNotIn('b', taken)                             # no consistent source: rebuilt

    def test_file_left_to_a_later_stage(self):
        deps = {'a': [], 'b': ['a']}
        a_old = plan('O', skipped={'out/x': 'b'})
        # b rebuilt: a cannot leave x to it
        taken, over = RA.combine(['a', 'b'], deps, {'a': [('O', a_old)]}, lambda s, x, y: True)
        self.assertNotIn('a', taken)
        # b from another run that delivers x: fine; without x: passed over
        with_x = {'a': [('O', a_old)], 'b': [('N', plan('N', files={'out/x': {'sha256': 'h', 'size': 1}}))]}
        self.assertIn('a', RA.combine(['a', 'b'], deps, with_x, lambda s, x, y: True)[0])
        without = {'a': [('O', a_old)], 'b': [('N', plan('N'))]}
        self.assertNotIn('a', RA.combine(['a', 'b'], deps, without, lambda s, x, y: True)[0])

    def test_finish_plans_recomputes_conditions_and_hazards(self):
        deps = {'a': [], 'b': ['a'], 'c': ['b']}
        taken = {'b': ('O', plan('O', hazards={'x': 3})), 'c': ('N', plan('N', hazards={'b': 2}))}
        plans = RA.finish_plans(taken, deps)
        self.assertEqual(plans['b']['rebuilt_ancestors'], ['a'])
        self.assertTrue(plans['c']['conditional'])
        self.assertEqual(plans['b']['rebuild_hazard_count'], 0)      # x is not taken from O
        self.assertEqual(plans['c']['rebuild_hazard_count'], 0)      # b comes from O, not N
        self.assertNotIn('skipped', plans['b'])


class MinuteOneAndStrict(unittest.TestCase):
    STEPS = [('a', []), ('b', []), ('c', [])]

    def test_lines(self):
        lines = RA.minute_one_lines(self.STEPS, {'a': {'from': '/w/build/R1', 'rebuilt_ancestors': []}},
                                    {'b': 'changed: sources'}, {'b': [('resident-bake', 1700, 1769)]})
        self.assertEqual(lines[0].strip(), 'a: reused from R1')
        self.assertIn('rebuild: changed: sources', lines[1])
        self.assertIn('resident-bake: 1700 of 1769 units from the cache', lines[1])
        self.assertIn('no earlier run holds it', lines[2])

    def test_strict_stop_and_allow(self):
        rows = {'b': [('resident-bake', 0, 1769)], 'c': [('interior-room', 930, 935)]}
        closures = {'a': ['tools/npc_library.py'], 'b': [], 'c': []}
        uncached = {('tools/npc_library.py', 'bake_standing')}
        problems = RA.strict_problems(self.STEPS, {'a', 'b', 'c'}, rows, closures, uncached, {})
        stages = sorted(stage for stage, _ in problems)
        self.assertEqual(stages, ['a', 'b'])                        # c: 5 of 935 is under 5 %
        allowed = RA.parse_allowed(['a:the standing models move to the gallery cache', 'b:new resident code'])
        self.assertEqual(RA.strict_problems(self.STEPS, {'a', 'b', 'c'}, rows, closures, uncached, allowed), [])
        # reached functions known: a module in the closure whose bake the stage never reaches does not count
        units = {'a': {'tools/npc_library.py': ['other']}}
        self.assertEqual(RA.strict_problems(self.STEPS, {'a'}, {}, closures, uncached, {}, units=units), [])
        self.assertEqual(RA.strict_problems(self.STEPS, set(), rows, closures, uncached, {}), [])   # all reused

    def test_allow_needs_a_reason(self):
        for bad in ('a', 'a:', ':why'):
            with self.assertRaises(ValueError):
                RA.parse_allowed([bad])

    def test_unit_counts(self):
        groups = {'new': {'u1', 'u2'}, 'old': {'u1', 'u2', 'u3', 'u4'}}
        self.assertEqual(RA.unit_counts(groups, ('new',)), (2, 4))
        self.assertEqual(RA.unit_counts(groups, ('new', 'old')), (4, 4))
        self.assertEqual(RA.unit_counts({}, ('x',)), (0, 0))

    def test_census_reads_new_entries_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / 'image-passes'
            for key, sources, unit in (('aa1', 'S1', 'u1'), ('aa2', 'S1', 'u2'), ('bb3', 'S2', 'u1')):
                folder = cache / 'resident-bake' / key[:2]
                folder.mkdir(parents=True, exist_ok=True)
                (folder / f'{key}.json').write_text(json.dumps({'provenance': {
                    'fields': {'sources_sha256': sources}, 'input_manifest': {'unit': unit}}}))
            groups = RA.census(cache, 'resident-bake', tmp)
            self.assertEqual(groups, {'S1': {'u1', 'u2'}, 'S2': {'u1'}})
            self.assertTrue((Path(tmp) / 'cache' / RA.CENSUS_FOLDER / 'resident-bake.json').is_file())
            self.assertEqual(RA.census(cache, 'resident-bake', tmp), groups)


class UnitCacheOpeners(unittest.TestCase):
    def test_openers_name_their_key_code(self):
        found = {(row['module'], row['name']): row for row in RA.unit_cache_openers(ROOT)}
        resident = found[('tools/prepare_area.py', 'resident-bake')]
        self.assertEqual([s[1] for s in resident['scripts']], ['build_resident', 'publish_resident'])
        self.assertIn(('tools/chim_room_batches.py', 'interior-room-chim'), found)


class UncachedBakes(unittest.TestCase):
    def test_no_new_uncached_bake_path(self):
        """The gate check: a per-item bake with no cache that is not on the known list fails here. A known path that
        has gained a cache drops out of the scan; take it off KNOWN_UNCACHED_BAKES then."""
        found = RA.uncached_bakes(ROOT)
        new = sorted(found - set(RA.KNOWN_UNCACHED_BAKES))
        self.assertEqual(new, [], 'per-item bakes with no cache (give them a unit cache, or list them with the '
                                  'item that closes them in tools/reuse_all.py KNOWN_UNCACHED_BAKES): %s' % new)

    def test_scan_finds_a_pooled_bake(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'tools').mkdir()
            (Path(tmp) / 'tools' / 'x.py').write_text(
                'def bake_item(t):\n    return t\n\ndef run(pool, items):\n    return list(pool.map(bake_item, items))\n')
            (Path(tmp) / 'tools' / 'y.py').write_text(
                'from pass_cache import UnitCache\n\ndef bake_item(t):\n    return t\n\n'
                'def run(pool, items):\n    return list(pool.map(bake_item, items))\n')
            self.assertEqual(RA.uncached_bakes(tmp), {('tools/x.py', 'bake_item')})


if __name__ == '__main__':
    unittest.main()
