# SPDX-License-Identifier: GPL-3.0-only
"""How the CHIM stages key src/mwad/npc.py (BUILD-STAGE-KEY-NPC-MODULE-53), read only, no build.

The CHIM world stage (chim_build.py) and the interiors stage (chim_interiors.py) reach only the module's import-time
code, never outfit(): a change to how an NPC is dressed keeps their keys. The stages that bake residents (chim_town.py,
chim_rooms.py, chim_room_batches.py) run outfit() for every resident model they write, so the same change rekeys them,
as it must. The v0.0.53 dancers' change rekeyed the CHIM world through other files it changed (engine/aga/qc/world.qc,
engine/aga/src/aw_skel.h and the import-time code of tools/import_town.py and tools/npc_anim.py), not through npc.py.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

NPC = 'src/mwad/npc.py'
WORLD_STAGES = ('chim_build.py', 'chim_interiors.py')
ACTOR_STAGES = ('chim_town.py', 'chim_rooms.py', 'chim_room_batches.py')


class NpcModuleKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def reached(self, script):
        python, _, uncertain = self.index.closure(ROOT / 'tools' / script)
        self.assertFalse(uncertain, script)
        self.assertIn(NPC, python, script)
        return set((self.index.reached_units(ROOT / 'tools' / script) or {}).get(NPC, ()))

    def test_world_stages_reach_no_npc_function(self):
        functions = {u for u in self.index._module_symbols(NPC)['units'] if not u.startswith('<') and not u.isupper()}
        self.assertIn('outfit', functions)
        for script in WORLD_STAGES:
            if not (ROOT / 'tools' / script).is_file():
                continue
            with self.subTest(script=script):
                self.assertEqual(self.reached(script) & functions, set())
                selection, _ = self.index.selection(ROOT / 'tools' / script)
                # keyed by its units (import-time code), not the whole file
                self.assertTrue(selection[NPC].startswith(build_cache.UNIT_PREFIX[build_cache.STAGE_TOP_FORMAT]))

    def test_resident_stages_reach_outfit(self):
        for script in ACTOR_STAGES:
            if (ROOT / 'tools' / script).is_file():
                with self.subTest(script=script):
                    self.assertIn('outfit', self.reached(script))

    def test_an_outfit_change_keeps_the_import_time_key_and_rekeys_its_readers(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / NPC
            target.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / NPC, target)

            def digests():
                index = build_cache.SourceIndex(Path(tmp), top_format=build_cache.STAGE_TOP_FORMAT)
                return index.unit_digest(NPC, {'<top>'}), index.unit_digest(NPC, {'<top>', 'outfit'})

            world, actors = digests()
            text = target.read_text(encoding='utf-8')
            at = text.index('def outfit(')
            body = text.index('\n    return ', at)
            target.write_text(text[:body] + "\n    actor_id = actor_id  # an outfit() change" + text[body:],
                              encoding='utf-8')
            world2, actors2 = digests()
            self.assertEqual(world2, world)        # the CHIM world and interiors keys stay
            self.assertNotEqual(actors2, actors)   # the resident stages rebuild
            # a change to what the world stages do reach (the import-time code) rekeys them
            target.write_text('import os  # an import-time change\n' + target.read_text(encoding='utf-8'),
                              encoding='utf-8')
            self.assertNotEqual(digests()[0], world)


if __name__ == '__main__':
    unittest.main()
