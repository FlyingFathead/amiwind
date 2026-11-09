"""The actor library's NPC appearances and creature models are kept in the unit cache the moment each is baked, keyed
on their own inputs, the bake code's reach and the settings it reads (NPC-LIBRARY-NO-UNIT-CACHE-63: the v0.0.63-dev1
build re-baked 418 appearances and 57 creature models because the stage was refused reuse); and the reuse plan marks
a stage planned for reuse whose inputs are rebuilt as at risk."""
import inspect
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def serial_map(function, items, jobs=None, cost=None):
    for item in items:
        yield function(item)


BAKED = []


def fake_standing(task):
    _, _, appearance, _ = task
    BAKED.append(appearance['id'])
    if appearance['id'] == 'broken':
        raise ValueError('no body fits')
    raw = ('model of %s' % '+'.join(appearance['parts'])).encode()
    return raw, 'idle:0:8:0.1000 ~step:fs1.wav', {'fs1.wav': b'RIFF'}, {'bytes': len(raw), 'step': 0.1, 'skin': [8, 8]}


def appearance(ident, *parts):
    return {'id': ident, 'parts': list(parts), 'skeleton': 'meshes/base_anim.nif', 'female': False}


class NpcAppearanceUnits(unittest.TestCase):
    def setUp(self):
        os.environ.pop('AMIWIND_COST_HISTORY', None)
        BAKED.clear()

    def run_stage(self, cache, apps):
        import actor_units
        tasks = [(a['id'] + '-key', 'data', b'palette', a, 'react+full') for a in apps]
        names = {task[0]: task[3]['id'] for task in tasks}
        with mock.patch('build_parallel.completed_map', side_effect=serial_map), \
                mock.patch('npc_library.bake_standing', side_effect=fake_standing):
            return actor_units.bake_appearances(
                tasks, names, 2, cache, lambda task: actor_units.npc_inputs(task[3], task[0], task[4], 'p' * 64),
                log=lambda *a, **k: None)

    def test_stored_units_are_found_and_a_changed_part_rekeys_only_its_appearances(self):
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            cache = pass_cache.UnitCache('npc-appearance', {'game_data': 'g', 'environment': {}}, 'reach', folder)
            apps = [appearance('a', 'p1', 'hair1'), appearance('b', 'p1', 'hair2'), appearance('c', 'p2', 'hair1')]
            done, errors, cached = self.run_stage(cache, apps)
            self.assertEqual((sorted(done), errors, cached), (['a-key', 'b-key', 'c-key'], {}, 0))
            self.assertEqual(sorted(BAKED), ['a', 'b', 'c'])
            BAKED.clear()
            again, _, cached = self.run_stage(cache, apps)
            self.assertEqual((cached, BAKED), (3, []), 'the same inputs must give 3 of 3 from the unit cache')
            self.assertEqual({k: v[0] for k, v in again.items()}, {k: v[0] for k, v in done.items()},
                             'a unit from the cache must equal the baked one')
            changed = [appearance('a', 'p1', 'hair1'), appearance('b', 'p1', 'hair2'), appearance('c', 'p3', 'hair1')]
            _, _, cached = self.run_stage(cache, changed)
            self.assertEqual((cached, BAKED), (2, ['c']))

    def test_a_failed_appearance_is_named_and_the_rest_are_kept(self):
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            cache = pass_cache.UnitCache('npc-appearance', {'game_data': 'g', 'environment': {}}, 'reach', folder)
            done, errors, _ = self.run_stage(cache, [appearance('a', 'p1'), appearance('broken', 'p1')])
            self.assertEqual(sorted(done), ['a-key'])
            self.assertEqual(errors, {'broken-key': 'ValueError: no body fits'})
            BAKED.clear()
            _, _, cached = self.run_stage(cache, [appearance('a', 'p1')])
            self.assertEqual((cached, BAKED), (1, []))

    def test_pack_round_trip(self):
        import actor_units
        result = fake_standing(('d', b'p', appearance('a', 'p1'), 'idle'))
        facts = dict(result[3], _table=('progs/t.skt', b'table'))
        row, files = actor_units.pack_npc(result[:3] + (facts,), 1.234)
        self.assertEqual(actor_units.unpack_npc(row, files), (result[:3] + (facts,), 1.23))


class CreatureUnits(unittest.TestCase):
    def setUp(self):
        os.environ.pop('AMIWIND_COST_HISTORY', None)

    def test_models_are_kept_and_found(self):
        import actor_units
        import pass_cache
        calls = []

        def unit(task):
            calls.append(task[3]['mesh'])
            if task[3]['mesh'] == 'bad.nif':
                return 'bad.nif', None, 0.1, 'ValueError: no'
            return task[3]['mesh'], {'files': [('standing', b'mdl', 'progs/c.mdl')], 'record': {'model': 'progs/c.mdl'}}, \
                0.5, None
        tasks = [('kf', 'data', b'pal', {'id': i, 'mesh': m}, False, 1.0) for i, m in (('rat', 'r.nif'), ('x', 'bad.nif'))]
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch('build_parallel.completed_map', side_effect=serial_map), \
                mock.patch('creature_library._unit', side_effect=unit):
            cache = pass_cache.UnitCache('creature-model', {'game_data': 'g', 'environment': {}}, 'reach', folder)
            inputs = lambda task: actor_units.creature_inputs(task, 'p' * 64)  # noqa: E731
            first, cached = actor_units.bake_creatures(tasks, 2, cache, inputs, log=lambda *a, **k: None)
            self.assertEqual(cached, 0)
            self.assertEqual([r[0] for r in first], ['r.nif', 'bad.nif'])
            calls.clear()
            second, cached = actor_units.bake_creatures(tasks, 2, cache, inputs, log=lambda *a, **k: None)
            self.assertEqual((cached, calls), (1, ['bad.nif']), 'the failed model is baked again, the other found')
            self.assertEqual(second[0][1], first[0][1])


class BakeReach(unittest.TestCase):
    def test_the_libraries_key_on_their_bake_code(self):
        import creature_library
        import npc_library
        for function, reach in ((npc_library.build, "(__file__, 'bake_standing')"),
                                (creature_library.bake, "(__file__, '_unit')")):
            source = inspect.getsource(function)
            self.assertIn('pass_cache.source_digest(' + reach + ')', source)
            self.assertIn('actor_units.open_cache(', source)

    def test_an_edit_outside_the_bake_reach_keeps_every_key(self):
        """An edit to build() (how units are run and stored) keeps the bake-reach digest; an edit to the bake re-keys."""
        from build_cache import SourceIndex
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'repo'
            for part in ('tools', 'src', 'config'):
                shutil.copytree(ROOT / part, copy / part, ignore=shutil.ignore_patterns('__pycache__'))
            library = copy / 'tools' / 'npc_library.py'
            text = library.read_text(encoding='utf-8')

            def digest():
                index = SourceIndex(copy)
                return index.entry_digest(library, 'bake_standing', pass_cache.PASS_KEY_NEUTRAL)[0]
            before = digest()
            library.write_text(text.replace("print('NPC library: %d appearances (%d from",
                                            "print('NPC library: %d appearances, (%d from"), encoding='utf-8')
            self.assertEqual(digest(), before, 'an edit in build() re-keyed the appearances')
            library.write_text(text.replace('for budget in (480, 384, 320, 256, 192):',
                                            'for budget in (480, 384, 320, 256, 160):'), encoding='utf-8')
            self.assertNotEqual(digest(), before, 'an edit in the bake kept the key')


class SkeletalSeed(unittest.TestCase):
    """The v0.0.63-dev1 build baked its NPCs as skeletal models (--npc-anim-type 2): the seed imports them with their
    shared animation table, made again as the bake makes it and equal to the stage folder's file."""

    def make_run(self, folder, table=b'TABLE'):
        import json
        run = Path(folder) / 'run'
        lib = run / 'actor-library' / 'id1'
        (lib / 'progs').mkdir(parents=True)
        (lib / 'sound').mkdir()
        (run / 'intro-scene' / 'id1' / 'gfx').mkdir(parents=True)
        (run / 'intro-scene' / 'id1' / 'gfx' / 'palette.lmp').write_bytes(b'pal')
        raw = b'skeletal model'
        (lib / 'progs' / 'n_k1.mdl').write_bytes(raw)
        (lib / 'progs' / 'n_k1.anm').write_text('idle:0:8:0.1 ~step:fs1.wav:fs2.wav\n', encoding='ascii')
        (lib / 'sound' / 'fs1.wav').write_bytes(b'RIFF1')
        (lib / 'progs' / 'human.skt').write_bytes(table)
        import hashlib
        manifest = {'format': 'AmiWind NPC standing library 1', 'profile': 'react+full',
                    'models': {'k1': {'model': 'progs/n_k1.mdl', 'seconds': 3.0, 'type': 2, 'table': 'progs/human.skt',
                                      'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}},
                    'npcs': {'b': {'key': 'k1'}, 'a': {'key': 'k1'}}, 'left_out': {}}
        (run / 'actor-library' / 'npc-library.json').write_text(json.dumps(manifest), encoding='utf-8')
        return run

    def run_seed(self, run, cache, table=(b'TABLE', 'progs/human.skt'), lookup_only=False):
        import actor_units_seed as S
        with mock.patch('pass_cache.source_digest', return_value=S.SEED_REACH['dc356e39']), \
                mock.patch('actor_units.open_cache', return_value=cache), \
                mock.patch('npc_library.standing_profile', return_value='react+full'), \
                mock.patch('npc_library.appearances', return_value=({'a': appearance('a', 'p1')}, {})), \
                mock.patch('npc_library.appearance_key', return_value='k1'), \
                mock.patch('mwad.npc.load_master', return_value=({}, None, None)), \
                mock.patch('mwad.paths.child_ci', return_value=Path('x')), \
                mock.patch('actor_units_seed.skeletal_table', return_value=table):
            return S.seed(run, 'data', lookup_only, log=lambda *a, **k: None)

    def test_a_skeletal_appearance_is_imported_with_its_table_and_found(self):
        import actor_units
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            run = self.make_run(folder)
            cache = pass_cache.UnitCache('npc-appearance', {'game_data': 'g', 'environment': {}}, 'r', folder + '/c')
            counts = self.run_seed(run, cache)
            self.assertEqual((counts['imported'], counts['skipped']), (1, {}))
            self.assertEqual(self.run_seed(run, cache, lookup_only=True)['found'], 1)
            inputs = actor_units.npc_inputs(appearance('a', 'p1'), 'k1', 'react+full',
                                            actor_units.palette_digest(b'pal'))
            (raw, layout, sounds, facts), seconds = actor_units.unpack_npc(*cache.load_unit(inputs))
            self.assertEqual((raw, layout, sounds, seconds), (b'skeletal model', 'idle:0:8:0.1 ~step:fs1.wav:fs2.wav',
                                                               {'fs1.wav': b'RIFF1'}, 3.0))
            self.assertEqual(facts['_table'], ('progs/human.skt', b'TABLE'))

    def test_a_table_that_differs_is_not_imported(self):
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            run = self.make_run(folder, table=b'OTHER')
            cache = pass_cache.UnitCache('npc-appearance', {'game_data': 'g', 'environment': {}}, 'r', folder + '/c')
            counts = self.run_seed(run, cache)
            self.assertEqual(counts['imported'], 0)
            self.assertIn('animation table', counts['skipped']['k1'])


class FighterUnits(unittest.TestCase):
    def test_fighters_are_kept_and_found(self):
        import actor_units
        import pass_cache
        os.environ.pop('AMIWIND_COST_HISTORY', None)
        calls = []

        def fighter(task):
            calls.append(task[2])
            return task[2], b'mdl ' + task[2].encode(), {'name': task[2], 'layout': 'idle:0:8:0.1', 'bytes': 3}
        tasks = [('data', b'pal', 'ken', 'handtohand'), ('data', b'pal', 'ryu', 'weapononehand')]
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch('build_parallel.completed_map', side_effect=serial_map), \
                mock.patch('prepare_combat.bake_fighter', side_effect=fighter):
            cache = pass_cache.UnitCache('arena-fighter', {'game_data': 'g', 'environment': {}}, 'reach', folder)
            first, cached = actor_units.bake_fighters(tasks, 2, cache, actor_units.fighter_inputs,
                                                      log=lambda *a, **k: None)
            self.assertEqual((cached, calls), (0, ['ken', 'ryu']))
            calls.clear()
            second, cached = actor_units.bake_fighters(tasks, 2, cache, actor_units.fighter_inputs,
                                                       log=lambda *a, **k: None)
            self.assertEqual((cached, calls, second), (2, [], first))


class StoreErrorsLoud(unittest.TestCase):
    """UNIT-CACHE-STORE-ERRORS-SILENT-63: a store into a folder the build cannot write is found by reading it back;
    run_each prints it and fails the stage; the build's preflight names unwritable cache folders."""

    def test_stored_reads_the_entry_back(self):
        import pass_cache
        import unit_store
        with tempfile.TemporaryDirectory() as folder:
            cache = pass_cache.UnitCache('t', {}, 'r', folder)
            self.assertTrue(unit_store.stored(cache, {'entry': {'name': 'a'}}, {'x': 1}, {'0': b'bytes'}))
            with mock.patch.object(pass_cache.UnitCache, 'store_files', lambda *a: None):
                self.assertFalse(unit_store.stored(cache, {'entry': {'name': 'b'}}, {'x': 1}, {'0': b'other'}))

    def test_a_failed_store_fails_the_stage_after_the_map(self):
        import unit_store
        os.environ.pop('AMIWIND_COST_HISTORY', None)
        lines, kept = [], []

        def keep(index, result):
            kept.append(index)
            return index != 1
        with mock.patch('build_parallel.completed_map', side_effect=serial_map):
            with self.assertRaisesRegex(RuntimeError, '1 stores FAILED'):
                unit_store.run_each('t', lambda task: task, [(0, 'a'), (1, 'b'), (2, 'c')], ['a', 'b', 'c'], 1, keep,
                                    label='X', log=lambda text, flush=False: lines.append(text))
        self.assertEqual(kept, [0, 1, 2], 'every unit is still kept before the stage fails')
        self.assertTrue(any(line.startswith('!! X: STORE FAILED: b') for line in lines))
        self.assertIn('!! X: 1 stores FAILED (b)', lines)

    @unittest.skipIf(not hasattr(os, 'geteuid') or os.geteuid() == 0, 'root writes everywhere')
    def test_unwritable_cache_folders_are_named(self):
        import unit_store
        with tempfile.TemporaryDirectory() as folder:
            locked = Path(folder) / 'npc-appearance' / 'ab'
            locked.mkdir(parents=True)
            (Path(folder) / 'player-view').mkdir()
            self.assertEqual(unit_store.unwritable_folders(folder), [])
            locked.chmod(0o555)
            try:
                self.assertEqual(unit_store.unwritable_folders(folder), [str(locked)])
            finally:
                locked.chmod(0o755)


class RoomActorUnits(unittest.TestCase):
    def test_placements_are_kept_as_they_settle_and_found(self):
        import actor_units
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            maps = Path(folder) / 'id1' / 'maps'
            (maps.parent / 'progs').mkdir(parents=True)
            maps.mkdir()
            (maps / 'room_a.chim').write_bytes(b'room a')
            (maps.parent / 'progs' / 'n.mdl').write_bytes(b'model')
            tasks = [('tok', str(maps), 'room_a', {'aw_ref': str(n), 'model': 'progs/n.mdl', 'origin': '0 0 %d' % n},
                      [0.0, 0.0, float(n)], (0.0, 0.0, 0.0)) for n in range(3)]
            fitted = []

            def fit_all(todo, jobs, keep):
                for j, task in enumerate(todo):
                    fitted.append(task[3]['aw_ref'])
                    keep(j, {'placed_origin': (0.0, 0.0, task[4][2] + 0.25), 'status': 'supported'})
            cache = pass_cache.UnitCache('room-actor', {'environment': {}}, 'r', folder + '/c')
            with mock.patch('chim.interior.installed_room', side_effect=ValueError('no room record')):
                first = actor_units.fit_room_actors(tasks, 2, cache, maps, fit_all, log=lambda *a, **k: None)
                self.assertEqual(fitted, ['0', '1', '2'])
                fitted.clear()
                again = actor_units.fit_room_actors(tasks, 2, cache, maps, fit_all, log=lambda *a, **k: None)
                self.assertEqual((fitted, again), ([], first))
                self.assertEqual(first[1]['placed_origin'], [0.0, 0.0, 1.25])
                (maps / 'room_a.chim').write_bytes(b'room a, other collision')
                actor_units.fit_room_actors(tasks, 2, cache, maps, fit_all, log=lambda *a, **k: None)
                self.assertEqual(fitted, ['0', '1', '2'], 'a changed room map re-keys its placements')

    def test_the_fit_keeps_each_placement_once_in_the_serial_path(self):
        import room_actor_bake as R
        heads = {'a': ({'r': 'a'}, None), 'b': ({'r': 'b'}, [0, 0, 0])}
        tasks = [('t', 'm', 'room', {'aw_ref': k}, [0, 0, 0], (0, 0, 0)) for k in 'ab']
        kept = []
        with mock.patch.object(R, '_fit_head', side_effect=lambda task: heads[task[3]['aw_ref']]), \
                mock.patch.object(R, '_fit_search', return_value=None), \
                mock.patch.object(R, 'search_offsets', return_value=[0] * 40), \
                mock.patch.object(R, 'finish', side_effect=lambda result, best: dict(result, finished=True)):
            R._fit_all(tasks, 1, keep=lambda index, result: kept.append((index, result)))
        self.assertEqual(kept, [(0, {'r': 'a'}), (1, {'r': 'b', 'finished': True})])


class GuardSkips(unittest.TestCase):
    def test_a_skip_verdict_is_kept_and_not_tried_again(self):
        import actor_units
        import pass_cache
        with tempfile.TemporaryDirectory() as folder:
            id1 = Path(folder) / 'id1'
            (id1 / 'progs').mkdir(parents=True)
            (id1 / 'progs' / 'g.mdl').write_bytes(b'guard')
            task = ('data', str(id1), {'source_id': 'guard', 'base_model': 'progs/g.mdl'}, {'class': 'Guard'},
                    'torch.nif', b'p' * 768, None)
            cache = pass_cache.UnitCache('guard-torch-skip', {'environment': {}}, 'r', folder + '/c')
            layout = lambda task: 'idle:0:8:0.1'  # noqa: E731
            self.assertEqual(actor_units.known_guard_skips([task], cache, layout), ({}, [0]))
            actor_units.keep_guard_skip(cache, task, {'skipped': 'does not reproduce'}, layout)
            self.assertEqual(actor_units.known_guard_skips([task], cache, layout),
                             ({0: {'skipped': 'does not reproduce', 'reused': True}}, []))


class ReusePlanAtRisk(unittest.TestCase):
    def test_a_reused_stage_reading_a_rebuilt_stage_is_at_risk(self):
        import reuse_report
        order = ['census', 'chim-town-balmora', 'actor-library', 'image', 'music']
        details = {'actor-library': {'dependencies': {'census': 'x', 'chim-town-balmora': 'y'}},
                   'image': {'dependencies': {'actor-library': 'z'}}, 'music': {'dependencies': {}}}
        reasons = {'chim-town-balmora': 'sources changed'}
        risky = reuse_report.reuse_at_risk(order, reasons, details, {'census', 'actor-library', 'image', 'music'})
        self.assertEqual(risky, {'actor-library': ['chim-town-balmora'], 'image': ['actor-library']})
        lines = reuse_report.at_risk_lines({'at_risk': risky, 'rows': [{'stage': 'chim-town-balmora'}]})
        self.assertEqual(lines[0], 'actor-library: reuse at risk: reads chim-town-balmora (rebuilt); reused only if '
                                   'they write the same outputs again')
        self.assertIn('reads actor-library (at risk)', lines[1])


if __name__ == '__main__':
    unittest.main()
