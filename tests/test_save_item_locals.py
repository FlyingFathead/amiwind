# SPDX-License-Identifier: GPL-3.0-only
"""The scripts' values by name and the items' script values in a save (SAVE-SCRIPT-ROW-HINT-ONLY-65,
SAVE-ITEM-SCRIPT-LOCALS-66, v0.0.66).

The compiled file names every script's variables (LOCN: a key per variable, the folded name's hash and its type), the
items placed holders hold (HITM) and every script row's name hash (SCRH); it refuses names that share a hash (their
saved values would mix). The interpreter parks a held item's values and a worn item's once they hold one, so they
live on across map changes and reach the save. The engine's restore by name is aw_ledger.c AW_LedgerLocalSlot
(tests/aga_world_ledger_test.c "script locals by name"). Synthetic master only (no game data); the native part runs
in the Linux gate."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms  # noqa: E402
from test_mwscript import record, sub, scpt  # noqa: E402

# the script as saved, and the same script rebuilt: a variable inserted before the others, two swapped, one retyped
ITEM_A = '''begin ItemScript
short done
long count
float timer
if ( done == 0 )
\tset done to 1
\tMessageBox "Once"
endif
set count to count + 1
end'''
ITEM_B = '''begin ItemScript
short greeted
float timer
float count
short done
if ( done == 0 )
\tset done to 1
\tMessageBox "Once"
endif
set count to count + 1
end'''


def compiled(item_text):
    tmp = Path(tempfile.mkdtemp(prefix='aw-saveitems-'))
    try:
        out = [record('TES3', sub('HEDR', b'\0' * 300)), scpt('ItemScript', item_text),
               scpt('Plain', 'begin Plain\nDisable\nend'),
               record('MISC', sub('NAME', 'ring_once'), sub('SCRI', 'ItemScript'))]
        (tmp / 'Morrowind.esm').write_bytes(b''.join(out))
        data = GameData().load(tmp)
        prog, comp = compile_program(data, None, handwritten=(), rooms={})
        return prog, comp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def locn(f):
    """{script row: (keys, flags)} of a file's LOCN section."""
    raw, rows, out = f['LOCN'], f['LOCN_rows'], {}
    for i in range(rows):
        script, n, flags, first = struct.unpack_from('>HBBI', raw, 8 * i)
        out[script] = ([struct.unpack_from('>I', raw, 8 * rows + 4 * (first + k))[0] for k in range(n)], flags)
    return out


class CompiledTableTests(unittest.TestCase):
    def test_each_variable_named_in_slot_order(self):
        for text, declared in ((ITEM_A, [('done', 's'), ('count', 'l'), ('timer', 'f')]),
                               (ITEM_B, [('greeted', 's'), ('timer', 'f'), ('count', 'f'), ('done', 's')])):
            prog, comp = compiled(text)
            raw, sizes = awms.write(prog, comp, bindings(prog, comp))
            f = awms.read(raw)
            index = prog.scripts.index['itemscript']
            self.assertEqual(locn(f)[index], ([awms.local_key(n, t) for n, t in declared], 0))
            self.assertNotIn(prog.scripts.index['plain'], locn(f))          # no variables: no row
            self.assertEqual(prog.local_names_report['collided'], [])
            # on disk, after the bindings (never resident)
            for tag in ('LOCN', 'HITM', 'SCRH'):
                self.assertGreater(awms.ORDER.index(tag), awms.ORDER.index('BIND'))
            # every script row's name hash, as the engine's AW_LedgerNameHash of its name
            self.assertEqual([struct.unpack_from('>I', f['SCRH'], 4 * i)[0] for i in range(f['SCRH_rows'])],
                             [awms.name_hash(r['name']) for r in prog.scripts.rows])
        # the key: the folded name's hash in bits 0-29, the type above; the same name keeps its name bits
        self.assertEqual(awms.local_key('Done', 's'), awms.local_key('done', 's'))
        self.assertEqual(awms.local_key('count', 'f') & 0x3FFFFFFF, awms.local_key('count', 'l') & 0x3FFFFFFF)
        self.assertEqual(awms.local_key('count', 'f') >> 30, 2)

    def test_two_names_of_one_hash_are_never_mixed(self):
        prog, comp = compiled(ITEM_A)
        real = awms.name_hash
        # 'count' and 'timer' made to share a hash: both written without a name, the script flagged, the report says so
        fake = lambda s: real('count') if s.casefold() in ('count', 'timer') else real(s)  # noqa: E731
        with mock.patch.object(awms, 'name_hash', fake):
            rows, report = awms.local_rows(prog, comp)
        keys, flags = {r[0]: (r[1], r[2]) for r in rows}[prog.scripts.index['itemscript']]
        self.assertEqual((keys[1], keys[2], flags), (0, 0, awms.LOCN_COLLIDED))
        self.assertEqual(keys[0], awms.local_key('done', 's'))
        self.assertEqual(report['collided'], [{'script': 'ItemScript', 'names': ['count', 'timer']}])
        # two scripts (or globals, quests, worn items) of one hash: the builder refuses the file
        with self.assertRaises(ValueError) as caught:
            awms.check_name_hashes('scripts', ['a', 'b'], 0)
        self.assertIn('share the name hash', str(caught.exception))
        awms.check_name_hashes('scripts', ['ItemScript', 'itemscript', 'Plain'])   # one name in two cases: one name
        with mock.patch.object(awms, 'name_hash', lambda s: 5):
            with self.assertRaises(ValueError):
                awms.write(prog, comp, bindings(prog, comp))


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
static aw_mwvm_host_t host;
static void each(void *user,uint32_t reference,int script,int global,int running,const aw_mwcell_t *cells,int count){
    int i;(void)user;(void)running;
    if(global)return;
    printf("each %08lx %d",(unsigned long)reference,script);
    for(i=0;i<count;i++)printf(" %ld",(long)cells[i].i);
    printf("\n");
}
static long get(uint32_t ref,int slot){int s;aw_mwcell_t v;return AW_MwvmLocalGet(ref,slot,&s,&v)?(long)v.i:-99;}
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");long size;unsigned char *file;int script=atoi(argv[2]),k;float o[3]={0,0,0};
    uint32_t held=0x40000000u|301u,quiet=0x41000000u|301u,worn=0x3F000000u|0x123456u;
    if(!f)return 2;
    fseek(f,0,SEEK_END);size=ftell(f);fseek(f,0,SEEK_SET);file=malloc((size_t)size);
    if(fread(file,1,(size_t)size,f)!=(size_t)size)return 3;
    fclose(f);
    if(!AW_MwvmLoad(file,(unsigned long)size,&host))return 4;
    /* a held item (a chest's), another held one that never changes, and a worn item's carried instance */
    if(AW_MwvmAttach(held,script,AWB_HELD,-1,o)<0 || AW_MwvmAttach(quiet,script,AWB_HELD,-1,o)<0 ||
       AW_MwvmAttach(worn,script,0,-1,o)<0)return 5;
    AW_MwvmLocalSet(held,script,0,1);AW_MwvmLocalSet(held,script,1,7);AW_MwvmLocalSet(worn,script,0,1);
    AW_MwvmBeginMap();   /* the player walks through a door */
    printf("after the map change held %ld %ld quiet %ld worn %ld\n",get(held,0),get(held,1),get(quiet,0),get(worn,0));
    AW_MwvmLocalsEach(each,NULL);
    /* back at the chest: its item's values are there again (its one-time behaviour does not repeat) */
    if((k=AW_MwvmAttach(held,script,AWB_HELD,-1,o))<0)return 6;
    printf("attached again held %ld %ld\n",(long)AW_MwvmLocal(k,0).i,(long)AW_MwvmLocal(k,1).i);
    /* a detach parks it the same way */
    AW_MwvmLocalSet(held,script,1,9);AW_MwvmDetach(held);
    printf("detached held %ld\n",get(held,1));
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InterpreterParkingTests(unittest.TestCase):
    def test_item_values_live_on_across_map_changes(self):
        prog, comp = compiled(ITEM_A)
        raw, _ = awms.write(prog, comp, bindings(prog, comp))
        src = ROOT / 'engine/aga/src'
        with tempfile.TemporaryDirectory(prefix='aw-saveitems-vm-') as tmp:
            tmp = Path(tmp)
            (tmp / 'test.awm').write_bytes(raw)
            (tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter',
                                    '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                    str(tmp / 'h.c'), str(src / 'aw_mwvm.c'), str(src / 'aw_ledger.c'),
                                    '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(tmp / 'h'), str(tmp / 'test.awm'), str(prog.scripts.index['itemscript'])],
                                 capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        out = run.stdout.splitlines()
        script = prog.scripts.index['itemscript']
        # the held item's values and the worn item's are parked (they were dropped: the worn item's key had the held
        # bit); the held item that never changed takes no room in the parking store
        self.assertIn('after the map change held 1 7 quiet -99 worn 1', out)
        self.assertIn('each 4000012d %d 1 7 0' % script, out)        # 301 = 0x12d
        self.assertIn('each 3f123456 %d 1 0 0' % script, out)
        self.assertFalse([line for line in out if line.startswith('each 4100012d')], out)
        self.assertIn('attached again held 1 7', out)
        self.assertIn('detached held 9', out)


class EngineWiringTests(unittest.TestCase):
    def test_the_save_keeps_items_by_holder_and_item(self):
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        # the worn item's key no longer has the held bit (bit 30)
        self.assertIn('#define CARRIED_KEY 0x3F000000u', host)
        self.assertEqual(0x3F000000 & 0x40000000, 0)
        # an item's values by (holder, item, serial): the player's worn one (holder 0) or a placed holder's
        put = host[host.index('static void locals_put('):]
        put = put[:put.index('\n}\n')]
        # SAVE-ITEM-INSTANCES-ONE-PER-KIND-66: the player's worn copy's values go under that copy's instance serial (0 for
        # a plain copy and for a placed holder's item)
        self.assertIn('AW_LedgerItemLocalSet(l,holder,item,holder?0:worn_serial(item),h,script,i,', put)
        self.assertIn('if(is_item && !item_of(reference,&holder,&item)){locals_unnamed++;locals_refused++;return;}', put)
        worn = host[host.index('static uint32_t worn_serial(uint32_t item){'):]
        worn = worn[:worn.index('\n}\n')]
        self.assertIn('aw_state.inventory.equipped_serial[k] && AW_LedgerNameHash(id)==item)return aw_state.inventory.equipped_serial[k];',
                      worn)
        imp = host[host.index('static void locals_import(const aw_ledger_t *l){'):]
        imp = imp[:imp.index('\n}\n')]
        self.assertIn('!(key=item_key(x->holder,x->item,s))', imp)
        # a value under a serial is kept only while that copy is still the player's instance of that kind
        self.assertIn('if((x->serial && (x->holder || !serial_carried(x->serial,x->item))) || (s=script_row(x->script,x->hint))<0 ||',
                      imp)
        carried = host[host.index('static int serial_carried(uint32_t serial,uint32_t item){'):]
        carried = carried[:carried.index('\n}\n')]
        self.assertIn('int j=AW_ItemInstFind(&aw_state,serial);', carried)
        self.assertIn('return AW_LedgerNameHash(AW_ITEM_ID(&aw_state,x->row))==item;', carried)
        # a worn item still carried after the load runs its script again
        key = host[host.index('static uint32_t item_key('):]
        self.assertIn('carried_add(id,s);', key[:key.index('\n}\n')])


if __name__ == '__main__':
    unittest.main()
