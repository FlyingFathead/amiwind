"""Stage fingerprints on a copy of this repository: what a real change set rebuilds (BUILD-CACHE-OVERBROAD-33).

Its own module: the copied repository is shared by the class (setUpClass), so the test runner keeps
it in one task, apart from tests/test_build_cache.py.
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

# The stages of an AmiWind "MiniWind" Playtester Build (v0.0.33-dev1 mw-033c) and their scripts.
MINIWIND_STAGES = {
    'setup': 'mwad.py', 'dialogue-lookup': 'prepare_dialogue_lookup.py', 'media': 'prepare_media_assets.py',
    'music': 'prepare_music.py', 'engine': 'build_aga.py', 'scenery': 'prepare_scenery.py', 'scene': 'prepare_quake.py',
    'bsp': 'prepare_mesh_bsp.py', 'npcs': 'prepare_npcs.py', 'hands': 'prepare_hands.py', 'interior': 'prepare_interior.py',
    'intro': 'prepare_intro.py', 'census': 'prepare_census.py', 'balmora': 'prepare_balmora.py',
    'harvest': 'harvest_build.py', 'hand-catalog': 'prepare_hand_catalog.py', 'chim': 'chim_build.py',
    'balmora-interiors': 'prepare_balmora_interiors.py', 'door-audio': 'prepare_door_audio.py',
    'character': 'prepare_character.py', 'reading': 'prepare_reading.py', 'opening-references': 'prepare_opening_refs.py',
    # the tracker data stage (BUILD-CELL-PROGRESS-KEY-BUGS-35: a bug registration rebuilt it and stopped builds)
    'cell-progress': 'cell_progress_build.py',
}
SCENE_CHAIN = ('scenery', 'scene', 'bsp', 'npcs', 'hands', 'interior', 'census', 'balmora', 'balmora-interiors',
               'character', 'reading', 'opening-references', 'door-audio', 'hand-catalog', 'harvest')


class RepositoryReuseTests(unittest.TestCase):
    """BUILD-CACHE-OVERBROAD-33, measured on a copy of this repository with the MiniWind stage list."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.repository = Path(cls.temp.name) / 'repo'
        shutil.copytree(ROOT, cls.repository, ignore=shutil.ignore_patterns('.git', '__pycache__', 'out', 'images', '*.pyc'))
        cls.index = build_cache.SourceIndex(cls.repository)
        cls.first = cls.digests()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def digests(cls, edited=()):
        cls.index.refresh(list(edited))
        return {stage: cls.index.digest(cls.repository / 'tools' / script) for stage, script in MINIWIND_STAGES.items()}

    def edit(self, relative, old=None, new='\n'):
        path = self.repository / relative
        original = path.read_bytes()
        self.addCleanup(lambda: (path.write_bytes(original), self.index.refresh([relative])))
        text = original.decode('utf-8')
        if old is None:
            path.write_bytes((text + new).encode('utf-8'))
        else:
            self.assertEqual(text.count(old), 1, (relative, old))
            path.write_bytes(text.replace(old, new).encode('utf-8'))
        return relative

    def changed(self, *edited):
        now = self.digests(edited)
        return {stage for stage in MINIWIND_STAGES if now[stage] != self.first[stage]}

    def test_no_stage_is_uncertain(self):
        self.assertEqual([stage for stage, (_, _, uncertain) in self.first.items() if uncertain], [])

    def test_docs_and_tracker_edits_reuse_every_stage(self):
        """(a) docs/tracker-only change."""
        edited = [self.edit('docs/bugs/bugs.json', new=' '), self.edit('docs/BUGS.md'), self.edit('docs/BUG_JOURNAL.md'),
                  self.edit('docs/bugs/BUILD-CACHE-OVERBROAD-33.md'), self.edit('docs/BUILD_PROFILE.md')]
        self.assertEqual(self.changed(*edited), set())
        for stage, script in MINIWIND_STAGES.items():
            python, data, _ = self.index.closure(self.repository / 'tools' / script)
            docs = sorted(path for path in python | data if path.startswith('docs/'))
            # The image builder (engine/image script) reads the owner's walked-cells list.
            self.assertEqual(docs, ['docs/trackers/checked.json'] if stage == 'engine' else [], stage)

    def test_engine_edits_reuse_every_stage_that_does_not_compile_it(self):
        """(b) engine-only change: only the engine/image script and the CHIM stage's heap gate (it compiles
        the engine's structures to measure them) count engine sources."""
        edited = [self.edit('engine/aga/src/aw_scene.c'), self.edit('engine/aga/src/chim/chim_chunks.c'),
                  self.edit('engine/aga/src/r_main.c')]
        self.assertEqual(self.changed(*edited), {'engine', 'chim'})

    def test_builder_scheduler_edit_reuses_every_stage(self):
        """The measured mw-033a -> mw-033c case: the build plan's dependency code (tools/build_parallel.py
        stage_dependencies) changed; every stage imports the module for its worker pool."""
        edited = self.edit('tools/build_parallel.py', 'def stage_dependencies(steps, skipped=()):\n',
                           'def stage_dependencies(steps, skipped=()):\n    steps = list(steps)\n')
        self.assertEqual(self.changed(edited), set())
        whole = build_cache.SourceIndex(self.repository, scope='symbols')
        self.assertIn('tools/build_parallel.py', whole.closure(self.repository / 'tools' / 'prepare_scenery.py')[0])

    def test_scheduler_table_row_reuses_stages_that_do_not_read_it(self):
        """BUILD-SCHEDULER-TABLE-KEY-35: a new row in the scheduler's DEPENDENCIES table (tools/build_parallel.py)
        changes only the stages whose code reads the table, never media, music or the scene chain."""
        readers = {stage for stage, script in MINIWIND_STAGES.items()
                   if 'DEPENDENCIES' in (self.index.reached_units(self.repository / 'tools' / script) or {})
                   .get('tools/build_parallel.py', ())}
        edited = self.edit('tools/build_parallel.py', "    'dry-run-image': ('engine',),\n",
                           "    'dry-run-image': ('engine',),\n    'new-audit': ('census',),\n")
        changed = self.changed(edited)
        self.assertEqual(changed, readers)
        self.assertFalse({'media', 'music', 'setup', *SCENE_CHAIN} & changed, changed)

    def test_literal_tables_are_their_own_units(self):
        import ast
        tree = ast.parse("A = {'x': (1, 2)}\nB = [f()]\nC = (1,)\nC = (2,)\n__all__ = ['A']\n"
                         "def f():\n    return A\n")
        self.assertEqual(sorted(build_cache.lazy_tables(tree).values()), ['A'])  # B calls, C is bound twice
        units = build_cache.module_symbols(tree, "A = {'x': (1, 2)}\n", refined=True)['units']
        self.assertIn('A', units)
        self.assertIn('A', units['f']['names'])

    def test_real_converter_and_pool_edits_still_rebuild(self):
        """(c) no false reuse: the worker pool function the converters run changes exactly their fingerprints."""
        users = {stage for stage, script in MINIWIND_STAGES.items()
                 if 'ordered_map' in (self.index.reached_units(self.repository / 'tools' / script) or {})
                 .get('tools/build_parallel.py', ())}
        self.assertTrue({'scenery', 'bsp', 'interior', 'census', 'balmora'} <= users, users)
        signature = 'def ordered_map(function, items, jobs=None, cost=None, timings=None):\n'
        edited = self.edit('tools/build_parallel.py', signature, signature + '    items = list(items)\n')
        self.assertEqual(self.changed(edited), users)

    def test_collision_converter_edit_rebuilds_its_readers(self):
        edited = self.edit('tools/collision_bsp.py', 'def compile_standing(', 'def compile_standing(  ')
        changed = self.changed(edited)
        self.assertTrue({'bsp', 'interior', 'census', 'balmora', 'balmora-interiors'} <= changed, changed)
        self.assertFalse({'media', 'music', 'setup', 'dialogue-lookup'} & changed, changed)

    def test_registry_config_edit_reuses_the_scene_chain(self):
        """config/release-features.json (the release coverage table) is no town file: the town code reads
        config/<row['config']> of config/towns.json rows, not the whole folder."""
        edited = self.edit('config/release-features.json', new=' ')
        self.assertFalse(set(SCENE_CHAIN) & self.changed(edited), self.changed(edited))
        towns = self.edit('config/balmora.json', new=' ')
        self.assertIn('balmora', self.changed(edited, towns))


if __name__ == '__main__':
    unittest.main()
