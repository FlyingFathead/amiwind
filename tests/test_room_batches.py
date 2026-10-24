# SPDX-License-Identifier: GPL-3.0-only
"""Interior rooms by batch (tools/room_batches.py, tools/chim_room_batches.py; docs/chim/DOOR_GRAPH.md "Rooms by batch
in the builder"): the repo's room list, the batch selection, the door links both ways on a synthetic graph, the reuse
of finished room units, and the build plan's stage."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import room_batches as R  # noqa: E402


def doc_of(batches):
    """A room list of {batch: [room names]}."""
    out, next_id = [], 0
    for n, names in batches.items():
        rows = []
        for order, name in enumerate(names, 1):
            rows.append({'room': name, 'map': R.room_map(name), 'id': next_id, 'order': order, 'entrance': '0,0',
                         'doors_from': ['0,0'], 'depth': 1})
            next_id += 1
        out.append({'batch': n, 'kind': 'town', 'groups': ['T'], 'part': 0, 'rooms': rows})
    return {'format': R.FORMAT, 'next_id': next_id, 'batches': out}


class RepoList(unittest.TestCase):
    def test_the_repo_list_is_sound_and_public(self):
        doc = R.load()
        self.assertIsNotNone(doc, 'config/room-batches.json')
        self.assertEqual(R.check(doc), [])
        rows = R.rows(doc)
        self.assertGreater(len(rows), 800)
        allowed = {'room', 'map', 'id', 'order', 'entrance', 'doors_from', 'depth', 'state', 'batch'}
        for row in rows:
            self.assertLessEqual(set(row), allowed, row['room'])   # names, numbers and cells only, no positions
        self.assertEqual(R.dumps(doc), (ROOT / 'config' / R.CONFIG).read_text(encoding='utf-8'))

    def test_the_list_is_not_read_as_rooms_in_the_game(self):
        import cell_progress
        ours = cell_progress.our_maps(ROOT / 'config')
        maps = {row['map'] for row in R.rows(R.load())}
        self.assertFalse(maps & set(ours.values()))

    def test_map_names_fit_the_engine(self):
        for name in ('Balmora, Guild of Mages', "ken's test hole"):
            m = R.room_map(name)
            self.assertRegex(m, R.MAP_NAME)
            self.assertLessEqual(len(m), 15)        # aw_scene.c %15s
            self.assertEqual(m, R.room_map(name.upper()))

    def test_the_engine_table_is_current(self):
        import town_table
        self.assertTrue(town_table.check(), 'run tools/town_table.py --write')
        header = town_table.HEADER.read_text(encoding='ascii')
        self.assertIn('#define AW_ROOM_BATCH_COUNT %d' % len(R.engine_rows()), header)

    def test_ids_never_move(self):
        old = doc_of({1: ['A', 'B'], 2: ['C']})
        ids, nxt = R.assign_ids(['C', 'D', 'A'], old)
        self.assertEqual(ids, {'c': 2, 'd': 3, 'a': 0})
        self.assertEqual(nxt, 4)
        old['next_id'] = 10      # an id once given is never given again
        self.assertEqual(R.assign_ids(['E'], old)[0], {'e': 10})

    def test_check_refuses_the_scene_list_key(self):
        doc = doc_of({1: ['A']})
        doc['batches'][0]['rooms'][0]['cell'] = 'A'
        self.assertTrue(any('"cell"' in p for p in R.check(doc)))


class Selection(unittest.TestCase):
    def setUp(self):
        self.doc = doc_of({1: ['A'], 2: ['B'], 3: ['C'], 5: ['D']})

    def test_values(self):
        self.assertEqual(R.parse_selection('none', self.doc), [])
        self.assertEqual(R.parse_selection(None, self.doc), [])          # the shipped default
        self.assertEqual(R.parse_selection('all', self.doc), [1, 2, 3, 5])
        self.assertEqual(R.parse_selection('2', self.doc), [2])
        self.assertEqual(R.parse_selection('1-3', self.doc), [1, 2, 3])
        self.assertEqual(R.parse_selection('1,3, 5', self.doc), [1, 3, 5])
        self.assertEqual(R.selection_text([1, 2, 3, 5]), '1-3, 5')

    def test_refusals(self):
        for bad in ('4', '1-4', 'x', '3-1', '0'):
            with self.assertRaises(ValueError, msg=bad):
                R.parse_selection(bad, self.doc)

    def test_rooms_another_stage_converts_are_left_to_it(self):
        doc = R.load()
        convert, held, refused = R.plan(doc, [1], ['balmora-interiors'])
        self.assertEqual(convert, [])
        self.assertEqual(len(held), len(doc['batches'][0]['rooms']))
        self.assertEqual(set(held.values()), {'balmora-interiors'})
        # without Balmora's stage the batch stage converts them, under their fixed names (save IDs kept)
        convert, held, _ = R.plan(doc, [1], [])
        self.assertEqual(held, {})
        self.assertTrue(all(row['build_map'].startswith('bm') for row in convert))

    def test_build_refusals(self):
        import build
        args = type('A', (), {'room_batches': 'all', 'miniwind': True, 'interior_format': 'chim'})()
        with self.assertRaises(ValueError):
            build.room_batch_selection(args)
        args = type('A', (), {'room_batches': '1', 'miniwind': False, 'interior_format': 'bsp'})()
        with self.assertRaises(ValueError):
            build.room_batch_selection(args)
        args = type('A', (), {'room_batches': '1', 'miniwind': False, 'interior_format': 'bsp'})()
        with self.assertRaises(ValueError):            # an explicit selection with bsp rooms is refused ...
            build.room_batch_selection(args)
        every = [b['batch'] for b in R.load()['batches']]
        # ... the default (not given) is all for a full build with CHIM rooms (the maintainer's decision of 23 October
        # 2026), and none for a MiniWind and for --interior-format bsp: the default never errors
        self.assertEqual(build.ROOM_BATCHES_DEFAULT, 'all')
        args = type('A', (), {'room_batches': None, 'miniwind': False, 'interior_format': 'chim'})()
        self.assertEqual(build.room_batch_selection(args), every)
        args = type('A', (), {'room_batches': None, 'miniwind': False, 'interior_format': 'bsp'})()
        self.assertEqual(build.room_batch_selection(args), [])
        args = type('A', (), {'room_batches': None, 'miniwind': True, 'interior_format': 'chim'})()
        self.assertEqual(build.room_batch_selection(args), [])
        args = type('A', (), {'room_batches': '2', 'miniwind': True, 'interior_format': 'chim'})()
        self.assertEqual(build.room_batch_selection(args), [2])      # a MiniWind takes numbers
        args = type('A', (), {'room_batches': 'none', 'miniwind': False, 'interior_format': 'chim'})()
        self.assertEqual(build.room_batch_selection(args), [])

    def test_bsp_default_plan_builds(self):
        """A full build with --interior-format bsp and the default plans without error and without the stage."""
        from test_build_defaults import steps
        names = [n for n, _ in steps('--interior-format', 'bsp')]
        self.assertNotIn('chim-room-batches', names)
        self.assertIn('chim-room-batches', [n for n, _ in steps()])
        self.assertNotIn('chim-room-batches', [n for n, _ in steps('--room-batches', 'none')])


def door(number, source, dest, position, interior_source, rot=0.0):
    return {'number': number, 'source_cell': source, 'source_interior': interior_source,
            'destination_cell': dest or '', 'destination_interior': bool(dest),
            'destination': {'position': list(position), 'rotation_radians': [0.0, 0.0, rot]}}


class DoorLinks(unittest.TestCase):
    """A synthetic graph: exterior cell 1,2 (a CHIM region frame) -> Room A <-> Room B -> Room C (not converted);
    Room A -> back outside; a town room T -> Room B."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.id1 = Path(tmp.name)
        self.a, self.b, self.c = R.room_map('Room A'), R.room_map('Room B'), R.room_map('Room C')
        blank = '0.00000 0.00000 0.00000 1.00000 1.00000 1.00000'
        self.banks = {
            # the region frame of cell 1,2 (chim.frame_map.door_bank_text: a space before the label)
            'doors-vf0001.txt': ['vf0001 - 10 %s 0.00000 0.00000 0.00000 0.00000 Room A' % blank],
            # the batch rooms' own banks (chim_room_batches.room_banks: a tab before the label)
            'doors-%s.txt' % self.a: ['%s - 20 %s 0 0 0 0\tExterior world' % (self.a, blank),
                                      '%s - 21 %s 0 0 0 0\tRoom B' % (self.a, blank)],
            'doors-%s.txt' % self.b: ['%s - 30 %s 0 0 0 0\tRoom A' % (self.b, blank),
                                      '%s - 31 %s 0 0 0 0\tRoom C' % (self.b, blank)],
            # a town room's bank into Room B, and a row of another kind that must stay as it is
            'doors-town1.txt': ['town1 - 40 %s 0 0 0 0\tRoom B' % blank,
                                'town1 - 41 %s 0 0 0 0\tSomewhere Else' % blank],
        }
        for name, rows in self.banks.items():
            (self.id1 / name).write_text('\n'.join(['AWD3', *rows]) + '\n', encoding='cp1252')
        self.doors = [
            door(10, '', 'Room A', (100, 200, 300), False),
            door(20, 'Room A', None, (8192 + 400, 16384 + 800, 1200), True, rot=0.5),
            door(21, 'Room A', 'Room B', (40, 80, 120), True),
            door(30, 'Room B', 'Room A', (4, 8, 12), True),
            door(31, 'Room B', 'Room C', (1, 1, 1), True),
            door(40, 'Town Room', 'Room B', (400, 800, 1200), True),
            door(41, 'Town Room', 'Somewhere Else', (0, 0, 0), True),
        ]
        self.batch = {'room a': self.a, 'room b': self.b}
        self.present = dict(self.batch, **{'town room': 'town1'})
        self.frames = {'towns': [], 'regions': {(1, 2): ('vf0001', [8192 * .25, 16384 * .25, 10.0])}}

    def rows(self, name):
        return [R.parse_row(line) for line in (self.id1 / name).read_text(encoding='cp1252').splitlines()[1:]]

    def test_links_both_ways(self):
        receipt = R.link_banks(self.id1, self.batch, self.present, self.doors, self.frames,
                               listed={'room a', 'room b', 'room c'})
        self.assertEqual(receipt['linked'], {'exterior_to_room': 1, 'room_to_exterior': 1, 'room_to_room': 3})
        # outside -> Room A at its arrival (room units: x 0.25, feet lifted)
        fields, sep, label = self.rows('doors-vf0001.txt')[0]
        self.assertEqual((fields[1], sep, label), (self.a, ' ', 'Room A'))
        self.assertEqual([float(v) for v in fields[4:7]], [25.0, 50.0, 75.0 + R.FEET])
        # Room A -> back outside, in the region frame's own units
        fields, sep, label = self.rows('doors-%s.txt' % self.a)[0]
        self.assertEqual((fields[1], sep, label), ('vf0001', '\t', 'Exterior world'))
        self.assertEqual([float(v) for v in fields[4:7]], [100.0, 200.0, 300.0 - 10.0 + R.FEET])
        # Room A <-> Room B
        self.assertEqual(self.rows('doors-%s.txt' % self.a)[1][0][1], self.b)
        self.assertEqual(self.rows('doors-%s.txt' % self.b)[0][0][1], self.a)
        # a town room into a batch room
        self.assertEqual(self.rows('doors-town1.txt')[0][0][1], self.b)

    def test_rooms_not_converted_stay_inert_and_are_listed(self):
        receipt = R.link_banks(self.id1, self.batch, self.present, self.doors, self.frames,
                               listed={'room a', 'room b', 'room c'})
        self.assertEqual(self.rows('doors-%s.txt' % self.b)[1][0][1], '-')
        self.assertEqual(self.rows('doors-town1.txt')[1][0][1], '-')       # not ours: untouched, not listed
        self.assertEqual([(u['reference'], u['reason']) for u in receipt['unlinked']],
                         [(31, 'room not converted in this build')])

    def test_an_exit_with_no_frame_stays_inert(self):
        receipt = R.link_banks(self.id1, self.batch, self.present, self.doors, {'towns': [], 'regions': {}})
        self.assertEqual(self.rows('doors-%s.txt' % self.a)[0][0][1], '-')
        self.assertIn('no town or CHIM region frame', receipt['unlinked'][0]['reason'])

    def test_a_second_pass_changes_nothing(self):
        R.link_banks(self.id1, self.batch, self.present, self.doors, self.frames)
        before = {p.name: p.read_bytes() for p in self.id1.iterdir()}
        receipt = R.link_banks(self.id1, self.batch, self.present, self.doors, self.frames)
        self.assertEqual(receipt['banks_changed'], {})
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.id1.iterdir()})


class Reuse(unittest.TestCase):
    """A second run of the room units converts nothing: every unit comes from the unit cache."""

    def test_second_run_converts_nothing(self):
        import chim_room_batches as S
        made = []

        def fake_build(task, jobs=1):
            data, scene, entry, timings, cell = task
            made.append(entry['map'])
            root = Path(scene) / 'area-work' / entry['map']
            root.mkdir(parents=True)
            (root / 'room.bsp').write_bytes(b'shell ' + entry['map'].encode())
            (root / 'placements.json').write_text('[1, 2]')
            return {'map': entry['map'], 'placements': 2}, {'name': entry['cell'], 'refs': []}

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lock = tmp / 'inputs.json'
            lock.write_text(json.dumps({'schema': __import__('known_inputs').LOCK_SCHEMA,
                                        'files': {'Morrowind.esm': {'sha256': '0' * 64}}}))
            entries = [{'map': R.room_map(n), 'cell': n, 'interior': True, 'area': 'balmora'} for n in ('A', 'B', 'C')]
            env = {'AMIWIND_PASS_CACHE': str(tmp / 'cache'), __import__('known_inputs').LOCK_ENV: str(lock)}
            with patch.dict(os.environ, env), patch.object(S, 'build_shell', fake_build):
                for run in ('one', 'two'):
                    scene = tmp / run
                    (scene / 'id1/gfx').mkdir(parents=True)
                    (scene / 'id1/gfx/palette.lmp').write_bytes(b'p' * 768)
                    results = S.convert('data', scene, entries, '', 1,
                                        refresh=lambda todo: {e['map']: {'refs': [0]} for e in todo})
                    self.assertEqual(sorted(k for k, v in results.items() if v[0] == 'ok'),
                                     sorted(e['map'] for e in entries))
                    if run == 'one':
                        self.assertEqual(sorted(made), sorted(e['map'] for e in entries))
                        self.assertTrue(all(v[2] for v in results.values()))
                        made.clear()
                    else:
                        self.assertEqual(made, [])                         # nothing converted again
                        self.assertFalse(any(v[2] for v in results.values()))
                        for e in entries:                                   # restored as made
                            self.assertEqual((scene / 'area-work' / e['map'] / 'room.bsp').read_bytes(),
                                             b'shell ' + e['map'].encode())


class Cores(unittest.TestCase):
    """ROOM-BATCH-CORES-49: the unit cache opened once per stage (the same keys as one open per room), and the tail's
    free cores offered to the rooms still to start, never more cores in flight than the stage holds."""

    def test_one_open_same_keys(self):
        import chim_room_batches as S
        import pass_cache
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lock = tmp / 'inputs.json'
            lock.write_text(json.dumps({'schema': __import__('known_inputs').LOCK_SCHEMA,
                                        'files': {'Morrowind.esm': {'sha256': '1' * 64}}}))
            (tmp / 'scene/id1/gfx').mkdir(parents=True)
            (tmp / 'scene/id1/gfx/palette.lmp').write_bytes(b'q' * 768)
            env = {'AMIWIND_PASS_CACHE': str(tmp / 'cache'), __import__('known_inputs').LOCK_ENV: str(lock)}
            entries = [{'map': R.room_map(n), 'cell': n, 'interior': True, 'area': 'balmora'} for n in 'ABCD']
            with patch.dict(os.environ, env):
                single = [pass_cache.input_digest(S.unit_inputs(e, tmp / 'scene', 't')[1]) for e in entries]
                opened = S.open_units(tmp / 'scene', 't')
                shared = [pass_cache.input_digest(S.unit_inputs(e, tmp / 'scene', 't', opened)[1]) for e in entries]
                self.assertEqual(single, shared)
                self.assertEqual(len(set(shared)), len(entries))
                calls = []
                real = pass_cache.UnitCache.open
                with patch.object(pass_cache.UnitCache, 'open', lambda *a: calls.append(a) or real(*a)), \
                        patch.object(S, 'build_shell', lambda task, jobs=1: (_ for _ in ()).throw(ValueError('x'))):
                    S.convert('data', tmp / 'scene', entries, 't', 1,
                              refresh=lambda todo: {e['map']: {'refs': [0]} for e in todo})
                self.assertEqual(len(calls), 1)

    def test_tail_cores(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        import build_parallel
        lock, state = threading.Lock(), {'now': 0, 'peak': 0}

        def work(task):
            item, cores = task
            with lock:
                state['now'] += cores
                state['peak'] = max(state['peak'], state['now'])
            import time
            time.sleep(0.02 + item / 2000.0)
            with lock:
                state['now'] -= cores
            return item, cores

        spread = lambda item, offered: ((item, min(offered, max(1, item // 20))), min(offered, max(1, item // 20)))
        env = {k: v for k, v in os.environ.items() if k not in (build_parallel.ALLOWANCE_ENV, 'AMIWIND_BUILD_JOBS')}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(build_parallel, 'process_pool', lambda n: ThreadPoolExecutor(n)):
            # many units: one core each until fewer are left to start than cores are free
            items = list(range(1, 41)) * 3
            got = list(build_parallel.spread_map(work, items, 4, cost=lambda i: i, spread=spread))
            self.assertEqual(sorted(i for i, _ in got), sorted(items))
            self.assertLessEqual(state['peak'], 4)
            first = [c for i, c in got if i == 40]
            self.assertEqual(first[:2], [1, 1])               # the largest started when the pool was full
            # fewer units than cores: the free cores go to them, the largest the most
            state['peak'] = 0
            got = dict(build_parallel.spread_map(work, [100, 60, 20], 8, cost=lambda i: i, spread=spread))
            self.assertLessEqual(state['peak'], 8)
            self.assertGreater(got[100], 1)
            self.assertGreaterEqual(got[100], got[60])
            self.assertEqual(got[20], 1)
            # serial: one core each, the same results
            self.assertEqual(sorted(build_parallel.spread_map(work, [3, 1, 2], 1, cost=lambda i: i, spread=spread)),
                             [(1, 1), (2, 1), (3, 1)])


class BuildPlan(unittest.TestCase):
    def test_the_stage_sits_before_the_chim_interiors_and_names_the_held_stages(self):
        import build
        steps = [('census', ['c']), ('balmora-interiors', ['b']), ('chim-rooms-vivec_city', ['v']),
                 ('chim-interiors', ['ci']), ('image', ['im'])]
        args = type('A', (), {'room_batches': '1-2', 'miniwind': False, 'interior_format': 'chim',
                              'data_files': Path('/data')})()
        tool = lambda name, *items: [name, *map(str, items)]
        with patch.object(build, 'npc_lod_arguments', lambda *a: []):
            out = build.room_batch_commands(args, steps, tool, Path('/run'), {'ffmpeg': 'ff'}, 8)
        names = [n for n, _ in out]
        self.assertEqual(names, ['census', 'balmora-interiors', 'chim-rooms-vivec_city', 'chim-room-batches',
                                 'chim-interiors', 'image'])
        command = dict(out)['chim-room-batches']
        self.assertEqual(command[command.index('--batches') + 1], '1-2')
        held = [command[i + 1] for i, p in enumerate(command) if p == '--held-by']
        self.assertEqual(held, ['balmora-interiors', 'chim-rooms-vivec_city'])
        self.assertIn(str(Path('/run/chim-room-batches/scene/area-work')), dict(out)['chim-interiors'])
        self.assertIn('--chim-room-batches', dict(out)['image'])

    def test_no_selection_leaves_the_plan_as_it_was(self):
        import build
        steps = [('chim-interiors', ['ci']), ('image', ['im'])]
        args = type('A', (), {'room_batches': 'none'})()
        self.assertEqual(build.room_batch_commands(args, steps, None, Path('/run'), {}, 8), steps)
        # the default on a plan without the CHIM interiors stage (the legacy builder): nothing, no error
        args = type('A', (), {'room_batches': build.RoomBatchesDefault('all'), 'miniwind': False,
                              'interior_format': 'chim'})()
        self.assertEqual(build.room_batch_commands(args, steps[1:], None, Path('/run'), {}, 8), steps[1:])

    def test_stage_dependencies(self):
        from build_parallel import DEPENDENCIES, stage_dependencies
        names = [n for n in DEPENDENCIES if n not in ('image', 'dry-run-image')]
        names += [d for n in names for d in DEPENDENCIES[n] if d not in names]
        steps = [(n, [n]) for n in dict.fromkeys(names)] + [
            ('chim-room-batches', ['r']), ('chim-interiors', ['ci']), ('image', ['im'])]
        deps = stage_dependencies(steps)
        # the rooms read the census palette and the hands report, no scene map (BUILD-SEYDA-BSP-CARRIER-48): they wait
        # for the census alone, not for the stages that rewrite seyda.bsp (BUILD-ROOM-BATCHES-SCENE-RACE-48)
        self.assertEqual(deps['chim-room-batches'], ('census',))
        self.assertIn('chim-room-batches', deps['chim-interiors'])
        self.assertIn('chim-room-batches', deps['image'])


class WaterPlane(unittest.TestCase):
    """ROOM-BATCH-WATER-OUTSIDE-48: a cell's water under or over everything the room places is no refusal."""

    def test_inside_under_over(self):
        import chim_room_batches as S
        self.assertEqual(S.water_plane(None, -100.0, 200.0), (None, 200.0, None))
        self.assertEqual(S.water_plane(40.0, -100.0, 200.0), (40.0, 200.0, None))          # 10 Quake units: inside
        water, top, note = S.water_plane(-4000.0, -100.0, 200.0)                            # far under the room
        self.assertEqual((water, top), (None, 200.0))
        self.assertIn('no water plane', note)
        water, top, note = S.water_plane(1000.0, -100.0, 200.0)                             # 250: over the room
        self.assertEqual((water, top), (1000.0, 250.0 + S.EDGE))
        self.assertIn('under water', note)


class GroundingPreflight(unittest.TestCase):
    def test_unclassified_residents_are_listed_before_any_unit(self):
        import chim_room_batches as S
        cells = {'ria': {'refs': [{'type': 'NPC_', 'id': 'nobody we know xyz'}, {'type': 'STAT', 'id': 'wall'},
                                  {'type': 'NPC_', 'id': 'gone', 'deleted': True}]}}
        with patch.object(S, 'read_cells', lambda data, rooms: cells):
            problems, got = S.unclassified_residents('data', [{'map': 'ria', 'cell': 'Room A'}])
        self.assertEqual(problems, {'Room A': ['nobody we know xyz']})
        self.assertIs(got, cells)


class StartsAsAStage(unittest.TestCase):
    def test_the_tools_start_with_the_builders_module_path(self):
        """The builder runs stages with PYTHONPATH=src:tools; tools/mwad.py must not shadow the mwad package
        (DOOR-GRAPH-MWAD-SHADOW-48)."""
        import subprocess
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / 'src'), str(ROOT / 'tools')]))
        for tool in ('chim_room_batches.py', 'door_graph.py'):
            run = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / tool), '--help'], env=env,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, tool + ': ' + run.stderr[-400:])


class ShellRoomMap(unittest.TestCase):
    def test_a_shell_room_map_takes_its_placements_from_the_record(self):
        from chim.interior import room_map, room_record
        from chim import placed as P
        import chim_room_batches as S
        shell = S.shell_map([-10, -10, -10], [10, 10, 10], [
            '{\n"classname" "worldspawn"\n"message" "Room A"\n"%s" "1"\n}' % S.SHELL_KEY,
            '{\n"classname" "info_player_start"\n"origin" "0 0 0"\n"angle" "0"\n}'])
        rec = P.placement(0, 77, 0, (1.0, 2.0, 3.0), (0.0, 0.0, 0.0), 0, 0, 0, ((0, 0, 0), (1, 1, 1)), 1, False)
        record = room_record(((-10, -10, -10), (10, 10, 10)), [0], [rec])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'room.bsp'
            path.write_bytes(shell)
            data, report = room_map(path, R.room_map('Room A'), record, ((-10, -10, -10), (10, 10, 10)))
        self.assertEqual(report['placements_checked'], 1)
        from chim.frame_map import entities
        world = entities(data)[0]
        self.assertNotIn(S.SHELL_KEY, world)
        self.assertEqual(world['_chim_room'], R.room_map('Room A'))


if __name__ == '__main__':
    unittest.main()
