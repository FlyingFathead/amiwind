# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-FINALIZE-UNDERUSED-48: the image step after the player view, on more cores, with the same outputs.

- The harvest source's master context is worked out once per process (it was asked for up to six times, about 4 s
  each): later calls get an equal, independent copy; another source receipt or master is worked out again.
- The actor table's master part is worked out beside the finalize checks (chim.actors.master_tables in a spawned
  worker): the table is byte for byte the one written in one go.
- The actor library's files are copied side by side: the same files, the same count.
- The world UI runs in a spawned worker beside the player view as its own timed phase, joined before its check.
- The untimed steps are timed phases (build_profile.PHASES; tests/test_build_profile.py checks every target exists).
Synthetic data only.
"""
import ast
import contextlib
import io
import json
import pickle
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class HarvestPlacementsTests(unittest.TestCase):
    def setUp(self):
        import harvest_build as H
        self.H = H
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.source, self.data = root / 'harvest', root / 'data'
        (self.source / 'source').mkdir(parents=True)
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(b'master one')
        (self.data / 'Morrowind.bsa').write_bytes(b'archive')   # resolve_data_files wants both
        (self.source / 'source/scenery-index.json').write_text('{"references": []}')
        (self.source / 'source/scenery.mwpak').write_bytes(b'pak')
        self.receipt = {'master': H.pin(b'master one'), 'settings': {'max_plants': 24, 'intern_root_spans': True},
                        'global_catalogue_sha256': 'c', 'global_slots': 2}
        (self.source / H.SOURCE_RECEIPT).write_text(json.dumps(self.receipt))
        self.calls = []
        patch.dict(H._PLACEMENTS, clear=True).start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.temp.cleanup()

    def context(self, master, **settings):
        self.calls.append(master)
        return {'catalogue': 'c', 'indices': [1, 2], 'full': {'references': [{'n': 1, 'pose': (1.0, 2.0)}]}}

    def run_placements(self):
        import prepare_harvest
        import prepare_harvest_alias
        with patch.object(self.H, 'load_source', lambda source: json.loads((Path(source) / self.H.SOURCE_RECEIPT)
                                                                          .read_text())), \
                patch.object(prepare_harvest, 'source_context', self.context), \
                patch.object(prepare_harvest_alias, 'validate_references',
                             lambda context, index, archive: [{'number': 7, 'bounds': [[0, 0, 0], [1, 1, 1]]}]):
            return self.H.held_placements(self.source, self.data)

    def test_worked_out_once_and_every_caller_gets_its_own_copy(self):
        first = self.run_placements()
        first[1]['full']['references'].append('changed by a caller')
        first[2][0]['number'] = 99
        second = self.run_placements()
        self.assertEqual(self.calls, [b'master one'])
        self.assertEqual(second[1], {'catalogue': 'c', 'indices': [1, 2],
                                     'full': {'references': [{'n': 1, 'pose': (1.0, 2.0)}]}})
        self.assertEqual(second[2], [{'number': 7, 'bounds': [[0, 0, 0], [1, 1, 1]]}])
        self.assertEqual(second[0], self.receipt)
        third = self.run_placements()
        self.assertIsNot(third[1], second[1])
        self.assertEqual(third[1:], second[1:])

    def test_another_receipt_or_master_is_worked_out_again(self):
        self.run_placements()
        self.receipt['settings']['max_plants'] = 25
        (self.source / self.H.SOURCE_RECEIPT).write_text(json.dumps(self.receipt))
        self.run_placements()
        self.assertEqual(len(self.calls), 2)
        (self.data / 'Morrowind.esm').write_bytes(b'master two')
        with self.assertRaisesRegex(ValueError, 'another master'):
            self.run_placements()
        self.receipt['master'] = self.H.pin(b'master two')
        (self.source / self.H.SOURCE_RECEIPT).write_text(json.dumps(self.receipt))
        self.run_placements()
        self.assertEqual(self.calls[-1], b'master two')
        self.assertEqual(len(self.calls), 3)


class ActorTableTests(unittest.TestCase):
    def test_the_table_from_worked_out_master_tables_is_the_same(self):
        from build_parallel import Background
        from chim import actors as A
        from test_chim_actor_table import ROWS, frame_map
        from test_chim_levelled import MASTER
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            master, maps = temp / 'Morrowind.esm', temp / 'maps'
            master.write_bytes(MASTER)
            maps.mkdir()
            frame_map(maps / 'town-chim.chim', ROWS)
            whole = A.write_table(temp / 'one.cca', master, maps)
            # in a spawned worker, as the image step does: the tables come back through pickle
            tables = Background(A.master_tables, master, jobs=2).result()
            split = A.write_table(temp / 'two.cca', master, maps, tables=tables)
            self.assertEqual((temp / 'one.cca').read_bytes(), (temp / 'two.cca').read_bytes())
            self.assertEqual(whole, split)
            self.assertEqual(pickle.loads(pickle.dumps(A.master_tables(master))), A.master_tables(master))


class ActorLibraryInstallTests(unittest.TestCase):
    def test_every_file_copied_side_by_side(self):
        import actor_library as AL
        with tempfile.TemporaryDirectory() as temp:
            lib, id1 = Path(temp) / 'lib', Path(temp) / 'id1'
            files = {'progs/c_%02d.mdl' % i: bytes([i]) * (i + 1) for i in range(40)}
            files.update({'sound/fx/a/step%d.wav' % i: b'w%d' % i for i in range(5)})
            for rel, raw in files.items():
                (lib / 'id1' / rel).parent.mkdir(parents=True, exist_ok=True)
                (lib / 'id1' / rel).write_bytes(raw)
            (id1 / 'progs').mkdir(parents=True)
            with patch('creature_library.base_texts', lambda path: {}), patch('npc_library.base_texts', lambda path: {}):
                texts, copied = AL.install(lib, id1)
            self.assertEqual(copied, len(files))
            self.assertEqual({p.relative_to(id1).as_posix(): p.read_bytes() for p in id1.rglob('*') if p.is_file()},
                             files)


class WorldUiTests(unittest.TestCase):
    def test_world_ui_is_its_own_phase_with_the_same_call(self):
        import prepare_world_ui
        calls = []
        out = io.StringIO()
        with patch.object(prepare_world_ui, 'prepare', lambda *a: calls.append(a) or {'format': 'x'}), \
                contextlib.redirect_stdout(out):
            self.assertEqual(prepare_world_ui.prepare_image('/data', '/boot'), {'format': 'x'})
        self.assertEqual(calls, [('/data', None, '/boot')])
        self.assertIn('Image: world UI: started', out.getvalue())

    def test_image_starts_it_before_the_player_view_and_joins_it_before_its_check(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        image = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'image')
        text = ast.get_source_segment(source, image)
        start = text.index('Background(prepare_world_ui_image')
        self.assertLess(start, text.index('prepare_combat(args.data_files'))
        self.assertLess(start, text.index('Background(prepare_player_view_image'))
        self.assertLess(text.index('world_ui.result()'), text.index("validate_world_ui(boot/'id1')"))
        self.assertNotIn('prepare_world_ui(args.data_files', text)

    def test_image_runs_the_torch_and_the_player_view_beside_the_steps_that_never_touch_their_files(self):
        # BUILD-IMAGE-FINALIZE-UNDERUSED-48 (v0.0.54-dev1 magic MiniWind: torch 6.3 s and player view 8.4 s, each on
        # one core, one after the other): the torch beside the gallery and the torch test map, the player view beside
        # the combat data; each joined before its report is written and before anything that reads its files
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        image = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'image')
        text = ast.get_source_segment(source, image)
        torch = text.index('Background(prepare_torch_image')
        self.assertLess(torch, text.index('stage_required(args.gallery'))
        self.assertLess(torch, text.index('build_torchtest('))
        self.assertLess(text.index('build_torchtest('), text.index('torch_report=torch_job.result()'))
        self.assertLess(text.index('torch_report=torch_job.result()'), text.index("'torch-conversion.json'"))
        view = text.index('Background(prepare_player_view_image')
        self.assertLess(view, text.index('prepare_combat(args.data_files'))
        self.assertLess(text.index('prepare_combat(args.data_files'), text.index('view_report=view_job.result()'))
        self.assertLess(text.index('view_report=view_job.result()'), text.index("'player-view.json'"))
        self.assertLess(text.index('view_report=view_job.result()'), text.index('prepare_inventory(args.data_files'))
        self.assertNotIn('prepare_torch(args.data_files', text)

    def test_the_workers_time_themselves(self):
        import prepare_player_view
        import prepare_torch
        for module, label, call in ((prepare_torch, 'Image: torch', ('/data', '/id1')),
                                    (prepare_player_view, 'Image: player view', ('/data', '/id1', 4, False))):
            calls, out = [], io.StringIO()
            with patch.object(module, 'prepare', lambda *a, **k: calls.append((a, k)) or {'format': 'x'}), \
                    contextlib.redirect_stdout(out):
                self.assertEqual(module.prepare_image(*call), {'format': 'x'})
            self.assertIn(label + ': started', out.getvalue())
        self.assertEqual(calls[-1], (('/data', '/id1'), {'jobs': 4, 'bodies': False}))


if __name__ == '__main__':
    unittest.main()
