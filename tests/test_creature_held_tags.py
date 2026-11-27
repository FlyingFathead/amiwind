# SPDX-License-Identifier: GPL-3.0-only
"""CREATURE-COMBAT-WEAPON-54: an armed creature's model gets an item tag, so it can hold its weapon and shield.

No creature model had a tag (the bones a held item hangs on), so no creature drew a weapon or shield. The actor
library now writes one beside the model of every creature mesh a "weapon and shield" record uses when its table is
the shared humanoid one (tools/creature_held_tags.py): the table frames, the two bones and the model's scale, and no
item, since one model serves records with different weapons and each actor's own record names what it holds. A
creature on a table of its own has no such bones and is listed. On made-up files; no game data in the repo."""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))
sys.path.insert(2, str(ROOT / 'tests'))

import actor_frames  # noqa: E402
import creature_held_tags  # noqa: E402
import creature_tables  # noqa: E402
import skeletal_actor  # noqa: E402

BONES = ['bip01', 'bip01 l hand', 'shield bone', 'bip01 r hand', 'weapon bone']
FRAMES = 3207


def skeletal_model(frames):
    """The smallest file actor_frames.skeletal_frames reads as a skeletal model of FRAMES table frames."""
    head = bytearray(84)
    head[:4] = b'IDPO'
    struct.pack_into('<i', head, 4, 6)       # an alias model, version 6
    struct.pack_into('<i', head, 60, 1)      # one vertex
    struct.pack_into('<i', head, 68, 1)      # one stored frame
    block = bytearray(76)
    block[:4] = b'AWSB'
    struct.pack_into('>I', block, 48, frames)
    return bytes(head) + bytes(block) + bytes(16)


def plain_table():
    return b'AWSK' + struct.pack('>H', 2) + bytes(18) + b'frames'


class HeldTagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='aw-creature-tags-'))
        progs = self.tmp / 'progs'
        progs.mkdir()
        appended = creature_tables.to_appended(plain_table(), creature_tables.HUMANOID_TABLE)
        self.models = {}
        for name, table in (('skeleton', appended), ('saint', appended), ('riekling', plain_table()),
                            ('rat', appended), ('baked', None)):
            model = 'progs/c_%s_k.mdl' % name
            (self.tmp / model).write_bytes(skeletal_model(FRAMES))
            record = {'model': model, 'method': 'skeletal' if table else 'kf'}
            if table:
                record['table'] = 'progs/k_%s.awsk' % name
                (self.tmp / record['table']).write_bytes(table)
            self.models['r/%s.nif' % name] = record
        flag = creature_held_tags.WEAPON_AND_SHIELD
        self.planned = {'bases': {'skeleton': {'flags': flag | 1}, 'skeleton archer': {'flags': flag},
                                  'skeleton_plain': {'flags': 1}, 'golden saint': {'flags': flag},
                                  'bm_riekling': {'flags': flag}, 'rat': {'flags': 0x48},
                                  'baked thing': {'flags': flag}, 'unbuilt': {'flags': flag}}}
        self.meshes = {'r/skeleton.nif': ['skeleton', 'skeleton archer', 'skeleton_plain'],
                       'r/saint.nif': ['golden saint'], 'r/riekling.nif': ['bm_riekling'], 'r/rat.nif': ['rat'],
                       'r/baked.nif': ['baked thing'], 'r/unbuilt.nif': ['unbuilt']}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self):
        return creature_held_tags.write(None, self.planned, self.meshes, self.models, self.tmp, humanoid_bones=BONES)

    def test_only_meshes_of_flagged_records(self):
        flagged = creature_held_tags.flagged_meshes(self.planned, self.meshes)
        self.assertEqual(flagged['r/skeleton.nif'], ['skeleton', 'skeleton archer'])
        self.assertNotIn('r/rat.nif', flagged)

    def test_a_creature_on_the_humanoid_table_gets_its_bones(self):
        # BEFORE: no creature model had a tag file at all
        self.assertFalse(list(self.tmp.rglob('*.tag')))
        written, left = self.write()
        self.assertEqual(sorted(written), ['r/saint.nif', 'r/skeleton.nif'])
        text = (self.tmp / 'progs/c_skeleton_k.tag').read_text(encoding='ascii')
        self.assertEqual(text, 'AWTS1 %d\nweapon -\nshield -\nbones 4 2\nscale 0.250000 0.250000 0.250000\n' % FRAMES)
        tag = skeletal_actor.read_skeletal_tag(text)
        self.assertEqual((tag['frames'], tag['bones'], tag['paths']), (FRAMES, [4, 2], {'weapon': None, 'shield': None}))
        self.assertEqual(written['r/skeleton.nif']['records'], ['skeleton', 'skeleton archer'])
        self.assertEqual(written['r/skeleton.nif']['bones'], [4, 2])
        # the image's own check of every tag: one row count per model frame (tools/actor_frames.py check)
        raw = (self.tmp / 'progs/c_skeleton_k.mdl').read_bytes()
        self.assertEqual(actor_frames.tag_frames(text, skeletal=True), actor_frames.skeletal_frames(raw))

    def test_the_others_get_none_and_are_listed(self):
        written, left = self.write()
        self.assertEqual(sorted(p.name for p in self.tmp.rglob('*.tag')), ['c_saint_k.tag', 'c_skeleton_k.tag'])
        self.assertIn('a table of its own', left['r/riekling.nif'])
        self.assertIn('not a skeletal model', left['r/baked.nif'])
        self.assertIn('no model', left['r/unbuilt.nif'])
        self.assertNotIn('r/rat.nif', left)             # not armed: nothing to say

    def test_a_humanoid_table_without_the_bones_stops(self):
        with self.assertRaises(ValueError):
            creature_held_tags.write(None, self.planned, self.meshes, self.models, self.tmp,
                                     humanoid_bones=['bip01', 'bip01 r hand'])

    def test_the_actor_library_writes_them_beside_the_bake(self):
        source = (ROOT / 'tools' / 'actor_library.py').read_text(encoding='utf-8')
        main = source[source.index('def main(argv=None):'):source.index('def install(')]
        call = main.index('creature_held_tags.write(a.data_files, planned, meshes, models, id1)')
        self.assertLess(main.index('models.update(more)'), call)        # after every creature model is made
        self.assertLess(call, main.index("'creature-library.json'"))
        self.assertIn("'creature_item_tags'", main)
        # outside the creature units: the bake module does not name it, so no unit's code reaches it
        self.assertNotIn('creature_held_tags', (ROOT / 'tools' / 'creature_library.py').read_text(encoding='utf-8'))
        self.assertNotIn('creature_held_tags', (ROOT / 'tools' / 'creature_tables.py').read_text(encoding='utf-8'))


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EngineReadsTheTagTests(unittest.TestCase):
    def test_the_engine_parses_a_tag_that_names_no_item(self):
        import test_aga_native_source as native
        tmp = Path(tempfile.mkdtemp(prefix='aw-creature-tag-native-'))
        try:
            path = tmp / 'c.tag'
            path.write_text(creature_held_tags.tag_text(FRAMES, BONES), encoding='ascii', newline='\n')
            native.NativeSourceTests().compile_run(
                'aga_items_bare_tag_test.c', [SRC / 'aw_items.c'], defines=('AW_ITEMS_HOST_TEST',),
                cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'], arguments=(str(path), str(FRAMES), '4', '2'))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
