# SPDX-License-Identifier: GPL-3.0-only
"""An engine source edit rekeys only the stages that read that file (BUILD-ENGINE-SOURCE-KEY-BROAD-36).

The v0.0.50 final rebuilt the CHIM world for an edit of engine/aga/src/aw_scene.c (the `dbg tp` named places): three
builder modules name the engine folder (tools/engine_limits.py SOURCE, tools/chim/zone_sim.py SRC and the include
folders of check_world_map_heap's target ABI probe), and a folder named in reached code counts whole, so every CHIM
world stage keyed all 331 files of engine/aga/src. In those modules (build_cache.C_HEADER_READERS) the folder now
counts as the engine files the reach names and their #include closure. This gate test fails when a stage started by
tools/build.py keys an engine C file outside ENGINE_C_INPUTS (read only, no build)."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

# Engine C files a stage may key, each read by a builder check whose result is in the stage's output:
# - engine_limits / map_engine_limits defines and cvar defaults: aw_combat.c, chim/chim_statics.c, chim/chim_world.c,
#   sys_amiga.c (the entity, zone and heap budgets of the CHIM gates);
# - the zone walk gate compiles chim/chim_zone.c (zone_sim);
# - check_world_map_heap hashes the loaders into its receipt and checks their policies: model.c, r_efrag.c, cl_main.c,
#   host.c, zone.c, aw_harvest*.c, aw_section.c (harvest and section budgets), r_draw.c (edge_cache_heap's pins);
# - chim/chim_chunks.c: the chunk link budget.
ENGINE_C_INPUTS = frozenset('engine/aga/src/' + name for name in (
    'aw_combat.c', 'aw_harvest.c', 'aw_harvest_proxy.c', 'aw_harvest_runtime.c', 'aw_section.c', 'chim/chim_chunks.c',
    'chim/chim_statics.c', 'chim/chim_world.c', 'chim/chim_zone.c', 'cl_main.c', 'host.c', 'model.c', 'r_draw.c',
    'r_efrag.c', 'sys_amiga.c', 'zone.c'))
# Engine files no builder check reads: an edit of one must rebuild only the engine and the image
ENGINE_ONLY = ('engine/aga/src/aw_scene.c', 'engine/aga/src/r_main.c', 'engine/aga/src/sv_main.c')
CHIM_STAGES = ('chim_build.py', 'chim_rooms.py', 'chim_room_batches.py', 'chim_interiors.py', 'chim_town.py')


def stage_scripts():
    """Every tools/*.py script tools/build.py starts as a stage (its tool('NAME.py', ...) calls)."""
    text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
    return sorted(name for name in set(re.findall(r"tool\(\s*'([A-Za-z0-9_]+\.py)'", text))
                  if (ROOT / 'tools' / name).is_file())


class RepositoryEngineKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        cls.engine = [path for path in cls.index.files if path.startswith('engine/aga/src/')]

    def engine_files(self, script):
        selected, uncertain = self.index.selection(ROOT / 'tools' / script)
        self.assertFalse(uncertain, script)
        return {path for path in selected if path.startswith('engine/')}

    def test_the_engine_only_files_exist(self):
        for path in ENGINE_ONLY:
            self.assertIn(path, self.index.files)

    def test_no_stage_keys_an_engine_c_file_it_does_not_read(self):
        for script in stage_scripts():
            extra = sorted(path for path in self.engine_files(script)
                           if path.endswith('.c') and path not in ENGINE_C_INPUTS)
            self.assertEqual(extra, [], '%s: an edit of these engine files would rebuild the stage' % script)

    def test_an_engine_only_edit_rebuilds_no_stage(self):
        for script in stage_scripts():
            self.assertFalse(self.engine_files(script) & set(ENGINE_ONLY), script)

    def test_the_chim_world_keys_far_less_than_the_engine_folder(self):
        for script in CHIM_STAGES:
            if (ROOT / 'tools' / script).is_file():
                self.assertLess(len(self.engine_files(script)), len(self.engine) // 2, script)

    def test_the_chim_stage_still_keys_what_the_zone_gate_compiles(self):
        files = self.engine_files('chim_build.py')
        self.assertIn('engine/aga/src/chim/chim_zone.c', files)
        self.assertIn('engine/aga/src/chim/chim_zone.h', files)
        self.assertIn('engine/aga/src/quakedef.h', files)


READER = '''
from pathlib import Path
SOURCE = Path(__file__).resolve().parents[1] / 'engine/aga/src'
def define(header, source=SOURCE):
    return (Path(source) / header).read_text()
'''
STAGE = '''
import engine_limits
print(engine_limits.define('limits.c'))
'''
STAGE_WHOLE = '''
from pathlib import Path
print(sorted((Path(__file__).resolve().parents[1] / 'engine/aga/src').iterdir()))
'''


class HeaderRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        files = {'tools/engine_limits.py': READER, 'tools/stage.py': STAGE, 'tools/stage_whole.py': STAGE_WHOLE,
                 'engine/aga/src/limits.c': '#include "quakedef.h"\n#include <stdio.h>\nint x;\n',
                 'engine/aga/src/quakedef.h': '#include "chim/zone.h"\n#include "generated_version.h"\n',
                 'engine/aga/src/chim/zone.h': '  #  include "../common.h"\n',
                 'engine/aga/src/common.h': '/* no includes */\n',
                 'engine/aga/src/scene.c': '#include "quakedef.h"\nint scene;\n'}
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def selected(self, script, top_format=build_cache.STAGE_TOP_FORMAT, **options):
        index = build_cache.SourceIndex(self.root, top_format=top_format, **options)
        selected, uncertain = index.selection(self.root / 'tools' / script)
        self.assertFalse(uncertain)
        return {path for path in selected if path.startswith('engine/')}

    def test_a_reader_keys_the_named_file_and_its_includes(self):
        self.assertEqual(self.selected('stage.py'), {
            'engine/aga/src/limits.c', 'engine/aga/src/quakedef.h', 'engine/aga/src/chim/zone.h',
            'engine/aga/src/common.h'})

    def test_the_folder_named_elsewhere_still_counts_whole(self):
        self.assertIn('engine/aga/src/scene.c', self.selected('stage_whole.py'))

    def test_the_unit_caches_keep_their_reach(self):
        self.assertIn('engine/aga/src/scene.c', self.selected('stage.py', top_format=1))
        self.assertIn('engine/aga/src/scene.c', self.selected('stage.py', narrow_headers=False))

    def test_the_companion_follows_the_stage_index(self):
        index = build_cache.SourceIndex(self.root, top_format=build_cache.STAGE_TOP_FORMAT)
        self.assertTrue(index.companion().narrow_headers)


if __name__ == '__main__':
    unittest.main()
