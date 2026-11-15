# SPDX-License-Identifier: GPL-3.0-only
"""The saved actor rows (SAVE-ACTOR-ROWS-256-66) and the explored map's own save section with the actor block a
setting (MAP-EXPLORED-SAVE-BLOCK-66), through the real writer and loader (tests/aga_save_rows_test.c): NPCs and
creatures changed in two places, both left, a save in a third, New Game, the load, both places as left (301 rows, past
the old 256); the window's release keeps a row; save, load, save the same rows; a full 64 KB block beside a well
explored map; the 32 KB block and 48-byte rows of a save before v0.0.66 load; the heap the same to the byte after
every save and load. Also the wiring the native test cannot reach (the engine's hooks, the shipped setting)."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'Native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class SavedRowsNativeTests(unittest.TestCase):
    def test_rows_of_every_place_the_block_and_the_explored_map_through_a_save_and_a_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / 'saves/p00000002').mkdir(parents=True)
            binary = work / 'save-rows'
            build = subprocess.run(
                ['cc', '-std=gnu99', '-O1', '-g', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                 '-fsanitize=undefined', '-fno-sanitize-recover=all',
                 '-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free', '-I' + str(SRC),
                 str(ROOT / 'tests/aga_save_rows_test.c'),
                 *(str(SRC / n) for n in ('aw_character.c', 'aw_state.c', 'aw_save_codec.c', 'aw_ledger.c',
                                          'aw_jhist.c', 'aw_mapfog.c')),
                 '-lm', '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(binary), str(work)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('rows: 301 over two places kept', run.stdout)
            self.assertIn('old form: a 32 KB block and 101 rows of 48 bytes loaded', run.stdout)
            self.assertIn('unchanged', run.stdout)
            print('\n' + run.stdout)


class SavedRowsWiringTests(unittest.TestCase):
    def test_rows_are_taken_when_a_place_unloads_and_when_the_window_lets_an_actor_go(self):
        # leaving a place (a door, a crossing, a teleport) captures its actors before the next map loads: the rows and
        # every NPC's and creature's change-list row (aw_actors.c AW_ActorsCapture)
        scene = code('aw_scene.c')
        leave = scene[scene.index('static void load_scene('):scene.index('static void load_scene(') + 1600]
        self.assertIn('AW_SaveLeave();', leave)
        self.assertIn('aw_save_actor_leave = AW_ActorsCapture;', code('aw_actors.c'))
        # the actor window's release keeps the row first, before the edict goes
        actors = code('aw_actors.c')
        release = actors[actors.index('static void Release (edict_t *e)'):]
        release = release[:release.index('\n}\n')]
        self.assertLess(release.index('AW_SaveCaptureActor (e);'), release.index('ED_Free (e);'))
        save = code('aw_save.c')
        # NPCs and creatures, no fixed 256 and no silent skip
        self.assertIn('return !strcmp(c,"aw_npc") || !strcmp(c,"aw_creature");', save)
        self.assertNotIn('Save actor limit reached', save)
        self.assertNotIn('AW_SAVE_ACTORS)', save)

    def test_the_block_is_a_setting_and_its_buffers_live_only_while_saving_or_loading(self):
        save = code('aw_save.c')
        self.assertIn('static cvar_t save_block={"aw_save_block_kb","64",true};', save)
        self.assertIn('Cvar_RegisterVariable(&save_block);', save)
        self.assertNotIn('save_actor_block[', save)
        self.assertNotIn('pending_actor_block[', save)
        write = save[save.index('static byte *encode_world('):save.index('int AW_SaveWrite(int slot)')]
        self.assertIn('block=AW_SaveBlockBytes(save_block.value);', write)
        self.assertIn('free(save_changes.actors);', write)
        spawn = save[save.index('void AW_SaveSpawn(void)'):save.index('void AW_SaveReset(void)')]
        imported = spawn.index('aw_save_explored_import(pending_changes.explored_data')
        self.assertLess(spawn.index('aw_save_actors_import(pending_changes.actors'), imported)
        self.assertGreater(spawn.find('AW_SaveChangesFree(&pending_changes);', imported), imported)
        self.assertRegex((ROOT / 'config' / 'game.cfg').read_text(encoding='utf-8'), r'\naw_save_block_kb 64\n')

    def test_the_explored_map_has_its_own_section(self):
        host = code('aw_mwhost.c')
        export = host[host.index('static int actors_export('):host.index('static void actors_import(')]
        self.assertNotIn('AW_MapFogExport(', export)
        self.assertIn('aw_save_explored_encode=explored_encode;aw_save_explored_import=explored_import;', host)
        imp = host[host.index('static void actors_import('):]
        self.assertIn('"AWFG"', imp[:imp.index('\n}\n')])      # a v0.0.66-dev save's block still loads
        codec = code('aw_save_codec.c')
        self.assertIn('(explored?4096U:0U)|(packed?8192U:0U)', codec)


if __name__ == '__main__':
    unittest.main()
