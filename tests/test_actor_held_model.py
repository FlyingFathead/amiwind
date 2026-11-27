# SPDX-License-Identifier: GPL-3.0-only
"""ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69: the actor table names the model each weapon and shield is held with.

What an actor holds was fixed per actor MODEL when the game was built (the item tag beside the model), so actors
sharing one model could not hold different weapons and a creature held none. The item rows of the actor table (AITM,
tools/mwscript/actors.py) now carry, in the two bytes that were written as 0, the string of the item's held model:
the item model of its mesh, the one the player holds and the world shows (tools/prepare_item_models.py). A weapon and
a shield have one; every other item has none. On a small synthetic game data set; no game data in the repo."""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import test_actorstate as base  # noqa: E402
from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms  # noqa: E402
from mwscript import actors  # noqa: E402

NONE = 0xFFFF
SWORD_MESH = 'w\\W_Test_Sword.NIF'
SHIELD_MESH = 'a\\A_Test_Shield.nif'


def master_bytes():
    sub, record, npco = base.sub, base.record, base.npco
    wpdt = struct.pack('<fihhffh6Bi', 20.0, 100, 1, 500, 1.25, 1.5, 0, 2, 10, 3, 12, 4, 14, 0)
    bow = struct.pack('<fihhffh6Bi', 8.0, 100, 9, 300, 1.0, 1.0, 0, 1, 20, 0, 0, 0, 0, 0)
    out = [base.master_bytes(),
           record('WEAP', sub('NAME', 'held_sword'), sub('MODL', SWORD_MESH), sub('WPDT', wpdt)),
           record('WEAP', sub('NAME', 'held_sword_twin'), sub('MODL', SWORD_MESH.upper()), sub('WPDT', wpdt)),
           record('WEAP', sub('NAME', 'held_bow'), sub('MODL', 'w\\w_test_bow.nif'), sub('WPDT', bow)),
           record('ARMO', sub('NAME', 'held_shield'), sub('MODL', SHIELD_MESH),
                  sub('AODT', struct.pack('<ifiiii', 8, 15.0, 50, 400, 0, 20))),
           record('ARMO', sub('NAME', 'worn_cuirass'), sub('MODL', 'a\\a_test_cuirass.nif'),
                  sub('AODT', struct.pack('<ifiiii', 1, 30.0, 50, 400, 0, 20))),
           record('MISC', sub('NAME', 'held_nothing'), sub('MODL', 'm\\misc_test.nif')),
           record('NPC_', sub('NAME', 'held_npc'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                  sub('NPDT', struct.pack('<h8B27BB3HBBbBi', 5, *range(50, 58), *range(10, 37), 0, 50, 20, 100, 40,
                                          1, 2, 0, 30)), sub('FLAG', struct.pack('<I', 0)),
                  npco(1, 'held_sword'), npco(1, 'held_sword_twin'), npco(1, 'held_bow'), npco(1, 'held_shield'),
                  npco(1, 'worn_cuirass'), npco(1, 'held_nothing'))]
    return b''.join(out)


def build():
    tmp = Path(tempfile.mkdtemp(prefix='aw-held-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master_bytes())
        data = GameData().load(tmp)
        prog, compiled = compile_program(data, handwritten=())
        raw, _sizes = awms.write(prog, compiled, bindings(prog, compiled))
        return prog, raw
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class HeldModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.raw = build()
        cls.f = awms.read(cls.raw)
        cls.names = awms.strings(cls.f)
        cls.t = cls.prog.actors

    def held(self, ident):
        """The string of the item's last two AITM bytes, None for 0xFFFF."""
        index = struct.unpack_from('>H', self.f['AITM'], 32 * self.t.item_index[ident] + 30)[0]
        return None if index == NONE else self.names[index]

    def test_the_path_is_the_item_model_tables_own(self):
        # the formula repeated in actors.py equals the item model table's, so the path is a model the image holds
        import prepare_inventory
        import prepare_item_models
        for mesh in (SWORD_MESH, SHIELD_MESH, 'W\\W_IRON_DAGGER.NIF', ' w/w_spear.nif '):
            self.assertEqual(actors.held_model(mesh),
                             prepare_item_models.model_path(prepare_inventory.mesh_key(mesh)))
        self.assertEqual(actors.held_model(''), '')
        self.assertLess(len(actors.held_model(SWORD_MESH)), 64)      # the engine's item path length

    def test_a_weapon_and_a_shield_name_their_held_model(self):
        # BEFORE: these two bytes were 0 for every item
        self.assertEqual(self.held('held_sword'), actors.held_model(SWORD_MESH))
        self.assertEqual(self.held('held_bow'), actors.held_model('w\\w_test_bow.nif'))     # ranged weapons too
        self.assertEqual(self.held('held_shield'), actors.held_model(SHIELD_MESH))
        self.assertTrue(self.held('held_sword').startswith('progs/items/m'))
        self.assertTrue(self.held('held_sword').endswith('.mdl'))
        # two records with one mesh (whatever its letter case) share one model and one string
        self.assertEqual(self.held('held_sword_twin'), self.held('held_sword'))

    def test_every_other_item_names_none(self):
        for ident in ('worn_cuirass', 'held_nothing', 'test_ring', 'test_sword', 'test_cuirass'):
            self.assertIsNone(self.held(ident), ident)      # test_sword: a weapon record without a mesh
        self.assertEqual(struct.unpack_from('>H', self.f['AITM'], 30)[0], NONE)     # row 0, the gold item
        self.assertEqual(self.t.report['held_models'], 3)

    def test_the_rows_keep_their_size_and_their_other_fields(self):
        self.assertEqual(len(self.f['AITM']), 32 * self.f['AITM_rows'])
        row = 32 * self.t.item_index['held_sword']
        kind, typ, health = struct.unpack_from('>BBH', self.f['AITM'], row + 2)
        self.assertEqual((kind, typ, health), (actors.ITEM_WEAPON, 1, 500))
        self.assertEqual(struct.unpack_from('>H', self.f['AITM'], row + 28)[0], NONE)      # its enchantment: none


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_actorstate.h"
static unsigned char *file;static long size;
static int rd(void *c,uint32_t off,void *out,uint32_t n){(void)c;if(off+n>(uint32_t)size)return 1;memcpy(out,file+off,n);return 0;}
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");aw_actorstate_io_t io={rd,NULL};int i,got;
    char weapon[AW_ACTOR_HELD_PATH],shield[AW_ACTOR_HELD_PATH];
    fseek(f,0,SEEK_END);size=ftell(f);fseek(f,0,SEEK_SET);file=malloc(size);if(fread(file,1,size,f)!=(size_t)size)return 2;fclose(f);
    if(!AW_ActorStateOpen(file,(uint32_t)size,&io))return 3;
    for(i=2;i<argc;i++){
        got=AW_ActorHeldModels(AW_ActorFind(argv[i]),weapon,shield);
        printf("%s %d [%s] [%s]\n",argv[i],got,weapon,shield);
    }
    got=AW_ActorHeldModels(-1,weapon,shield);printf("norow %d [%s] [%s]\n",got,weapon,shield);
    got=AW_ActorHeldModels(AW_ActorCount(),weapon,shield);printf("pastend %d\n",got);
    AW_ActorStateClose();
    got=AW_ActorHeldModels(0,weapon,shield);printf("closed %d\n",got);
    return 0;
}
'''
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    import re
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class EngineReaderTests(unittest.TestCase):
    """aw_actorstate.c AW_ActorHeldModels on the table above, and on the same table as it was written before the
    field (the two bytes 0)."""

    @classmethod
    def setUpClass(cls):
        cls.prog, raw = build()
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-held-native-'))
        (cls.tmp / 'new.awm').write_bytes(raw)
        # the table of a build before the field: the same file with bytes 30-31 of every item row 0
        f = awms.read(raw)
        at = raw.index(f['AITM'])
        old = bytearray(raw)
        for row in range(f['AITM_rows']):
            old[at + 32 * row + 30:at + 32 * row + 32] = b'\0\0'
        (cls.tmp / 'old.awm').write_bytes(bytes(old))
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(SRC),
                                str(cls.tmp / 'h.c'), str(SRC / 'aw_actorstate.c'), '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        cls.out = {}
        for name in ('new', 'old'):
            r = subprocess.run([str(cls.tmp / 'h'), str(cls.tmp / (name + '.awm')), 'held_npc', 'fixed_npc',
                                'test_rat', 'auto_npc'], capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            cls.out[name] = dict(line.split(' ', 1) for line in r.stdout.splitlines())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_an_actor_holds_what_its_record_has_equipped(self):
        # held_npc: the build's weapon choice for it and its shield unless that weapon takes both hands
        t = self.prog.actors
        row = actors.read_actor(awms.read((self.tmp / 'new.awm').read_bytes())['ACTB'], t.actor('held_npc'))
        inv = t.inventory[row['inv_first']:row['inv_first'] + row['inv_count']]
        weapon = t.items[inv[row['weapon']][0]]
        shield_worn = any(fl & actors.INV_EQUIPPED and t.items[i]['held'] == actors.held_model(SHIELD_MESH)
                          for i, _c, fl in inv)
        want = '%d [%s] [%s]' % (1 | (2 if shield_worn else 0), weapon['held'],
                                 actors.held_model(SHIELD_MESH) if shield_worn else '')
        self.assertTrue(weapon['held'])
        self.assertEqual(self.out['new']['held_npc'], want)

    def test_no_weapon_mesh_and_no_weapon_are_nothing_not_unknown(self):
        # fixed_npc wields test_sword, a record without a mesh, and wears a cuirass: it holds nothing (0), and that is
        # an answer; the rat and the unarmed NPC likewise
        self.assertEqual(self.out['new']['fixed_npc'], '0 [] []')
        self.assertEqual(self.out['new']['test_rat'], '0 [] []')
        self.assertEqual(self.out['new']['auto_npc'], '0 [] []')

    def test_a_table_before_the_field_and_a_missing_row_cannot_say(self):
        # -1: the caller keeps the items of the model's tag (an older image with a newer engine)
        self.assertEqual(self.out['old']['held_npc'], '-1 [] []')
        for name in ('new', 'old'):
            self.assertEqual(self.out[name]['norow'], '-1 [] []')
            self.assertEqual(self.out[name]['pastend'], '-1')
            self.assertEqual(self.out[name]['closed'], '-1')


class EngineWiringTests(unittest.TestCase):
    def setUp(self):
        self.items = code('aw_items.c')

    def test_the_actors_own_items_are_asked_at_its_spawn(self):
        prep = body(self.items, 'void AW_ItemsPrep(edict_t *actor) {')
        # the edict's last actor's items never stay; asked only for a model with a table; the record's models are
        # loaded, the tag's own only for an actor whose record cannot say
        self.assertLess(prep.index('own_known[n]=0;'), prep.index('sv.state!=ss_loading)return;'))
        self.assertIn('if(lazy && (t>=0 || tm>=0)){', prep)
        self.assertIn('(held=aw_items_held(actor,own[0],own[1]))>=0', prep)
        self.assertIn('(held&(1<<k)) && AW_ItemsIsItemPath(own[k])?precache(own[k]):0', prep)
        self.assertIn('}else{tag_items(t);tag_items(tm);own_tag_actors++;}', prep)
        self.assertIn('prep(m,m->name,m->numframes,!lazy);', prep)
        host = code('aw_mwhost.c')
        self.assertIn('aw_items_held=items_held;', host)
        self.assertIn('return AW_ActorHeldModels(row,weapon,shield);', body(host, 'static int items_held('))

    def test_the_drawn_item_is_the_actors_own_when_its_record_said(self):
        show = body(self.items, 'int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {')
        self.assertIn('int i=own?own_item[own][k]:table[t].item[k];', show)
        self.assertIn('own?!AW_ItemsIsItemPath(sv.model_precache[i]) || (table[t].skel && table[t].bone[k]<0):', show)
        kinds = body(self.items, 'int AW_ItemsKinds(edict_t *actor) {')
        self.assertIn('own?own_item[own][k]>0:table[t].item[k]', kinds)

    def test_a_tag_keeps_its_entry_for_its_bones_alone(self):
        # a tag whose items are not loaded, or that names none (a creature's), still gives the bones and the scale
        prep = body(self.items, 'static void prep(model_t *m,const char *name,int numframes,int load) {')
        self.assertIn('if(!load && bones[k]>=0){any=1;if(items[k][0])fresh.unloaded=1;}', prep)
        self.assertIn('fresh.item[k]=load && items[k][0] && bones[k]>=0?precache(items[k]):0;', prep)
        tag = body(self.items, 'static void tag_items(int t) {')
        self.assertIn('if(t<0 || !table[t].unloaded)return;', tag)

    def test_the_item_names_cover_every_weapon_and_shield_and_start_clean(self):
        import re
        names = int(re.search(r'#define NAMES (\d+)', self.items).group(1))
        self.assertGreaterEqual(names, 235)         # the game data's weapon and shield meshes
        self.assertIn('if(named>=NAMES){', body(self.items, 'static int precache(const char *path) {'))
        for head in ('void AW_ItemsSceneReset(void) {', 'static void level_check(void) {'):
            self.assertIn('memset(own_known,0,sizeof(own_known));', body(self.items, head))
        self.assertIn('int counts[11],info[3];', code('aw_animkit.c'))


if __name__ == '__main__':
    unittest.main()
