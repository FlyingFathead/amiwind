# SPDX-License-Identifier: GPL-3.0-only
"""A room's water level as the scripts read it (GETWATERLEVEL-COLUMN-NOT-ROOM-67, v0.0.68).

GetWaterLevel follows OpenMW 0.51 (apps/openmw/mwscript/cellextensions.cpp OpGetWaterLevel, lines 181-199): 0
outdoors, the room's own level in a room whose cell has the water flag, the lowest float in a room without it. The
level of a cell is its record's (components/esm3/loadcell.cpp Cell::loadCell, lines 129-159: INTV or WHGT, the later
winning; a later master's record keeps the earlier level unless it gives one). The builder writes every water room's
level into the script file's WATR section (tools/mwscript/awms.py water_rows) and the engine reads the loaded room's row
(engine/aga/src/aw_water_rules.c, aw_mwhost.c water_room_attach). Before, the engine walked the player's column for
water and read 0 where it found none: Old Mournhold: Temple Sewers West, whose water lies under every placement and is
not in its room map, read 0 for its -1500, and by its scripts' own rules the Black Dart gang's health was set to 0 on
the player's arrival and its lit torches switched to their burned-out form.

Checked here: the rules natively; the wiring of the engine; the builder's rows from small synthetic masters (no game
data in the repo); and a scene with two scripts written for this test (our own words, the same rules as the gang's
arrival script and the torches' scripts of that room), run through our compiler and the script interpreter with a
stub host that answers GetWaterLevel by the engine's own rules from the compiled rows: the gang keeps its health and
the torches stay lit; the column's reading (0) would set the health to 0 and swap the torches.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def water_cell(name, flags, refs=(), whgt=None, intv=None, order=('INTV', 'WHGT')):
    """An interior CELL record with FLAGS and its water height sub-records (in ORDER), then REFS."""
    from test_mwscript import sub, record
    parts = [sub('NAME', name), sub('DATA', struct.pack('<Iii', flags, 0, 0))]
    for tag in order:
        if tag == 'INTV' and intv is not None:
            parts.append(sub('INTV', struct.pack('<i', intv)))
        if tag == 'WHGT' and whgt is not None:
            parts.append(sub('WHGT', struct.pack('<f', whgt)))
    for number, ident, pos in refs:
        parts += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                  sub('DATA', struct.pack('<6f', pos[0], pos[1], pos[2], 0, 0, 0))]
    return record('CELL', *parts)


def addon(cells):
    """Tribunal.esm of CELLS (its master Morrowind.esm)."""
    from test_mwscript import sub, record
    return b''.join([record('TES3', sub('HEDR', b'\0' * 300), sub('MAST', 'Morrowind.esm'), sub('DATA', b'\0' * 8))]
                    + list(cells))


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class WaterRuleTests(unittest.TestCase):
    def test_the_rows_and_the_three_readings(self):
        native.NativeSourceTests().compile_run('aga_water_rules_test.c', [SRC / 'aw_water_rules.c'], cflags=UBSAN)

    def test_the_plane_moves_with_the_level(self):
        # MWSCRIPT-WATER-LEVEL-STATIC-67: the room world's root water plane, hull 0 and the faces' corners
        native.NativeSourceTests().compile_run('aga_water_plane_test.c', [SRC / 'aw_water.c', SRC / 'aw_water_rules.c',
                                                                          SRC / 'world.c', SRC / 'mathlib.c'],
                                               cflags=UBSAN)


class WaterWiringTests(unittest.TestCase):
    def test_the_engine_reads_the_rooms_row(self):
        self.assertIn('aw_water_rules.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        host = code('aw_mwhost.c')
        attach = host[host.index('static void water_room_attach(void){'):]
        attach = attach[:attach.index('\n}\n')]
        self.assertIn('AW_MwvmSection("WATR",&off,&rows,&bytes)', attach)
        self.assertIn('room_water=AW_WaterRow(resident+off,rows,(unsigned long)map_room,&room_water_level);', attach)
        amap = host[host.index('static void attach_map(void){'):]
        amap = amap[:amap.index('if(!AW_MwvmSection("BIND"')]
        self.assertIn('water_room_attach();', amap)            # every map, before its bindings
        body = host[host.index('if(function==AWF_GETWATERLEVEL){'):]
        body = body[:body.index('return AW_MWVM_CALL_READ;\n    }\n')]
        table = body.index('if(water_table){')
        column = body.index('SV_PointContents(p)')
        # the room's own level first; the column walk only for a script file without the rows (an older image)
        self.assertLess(table, column)
        self.assertIn('AW_WaterReading(where==2?AW_WATER_ROOM:where==1?AW_WATER_OUTDOORS:AW_WATER_NOWHERE,room_water,',
                      body[table:column])
        self.assertIn('room water:', host)
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc)\s*\(', code('aw_water_rules.c')))

    def test_the_section_is_resident_and_listed(self):
        from mwscript import awms
        self.assertIn('WATR', awms.RESIDENT)
        self.assertLess(awms.ORDER.index('WATR'), awms.ORDER.index('CODE'))
        header = (SRC / 'aw_water.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_WATER_ROW_BYTES %d' % awms.WATER_ROW.size, header)
        self.assertIn('#define AW_WATER_FLAG %du' % awms.WATER_FLAG, header)
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        for path in ('engine/aga/src/aw_water.h', 'engine/aga/src/aw_water_rules.c', 'tests/aga_water_rules_test.c',
                     'tests/test_water_level.py'):
            self.assertIn('"%s"' % path, files)


class WaterRowTests(unittest.TestCase):
    """The builder's rows from two small masters: the record's level, the flag, the later master's record."""

    @classmethod
    def setUpClass(cls):
        from test_mwscript import master_bytes
        from mwscript.gamedata import GameData
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-water-rows-'))
        cells = [water_cell('Sewer Low', 0x3, whgt=-1500.0), water_cell('Sewer Zero', 0x3, whgt=0.0),
                 water_cell('Old Int', 0x3, intv=-64), water_cell('Flag Only', 0x3),
                 water_cell('Dry Room', 0x1, whgt=100.0), water_cell('Both Fields', 0x3, intv=10, whgt=20.5),
                 water_cell('Both Reversed', 0x3, intv=10, whgt=20.5, order=('WHGT', 'INTV'))]
        (cls.tmp / 'Morrowind.esm').write_bytes(master_bytes(records=cells))
        (cls.tmp / 'Tribunal.esm').write_bytes(addon([
            water_cell('Old Int', 0x3, whgt=12.5),      # the later record's level wins
            water_cell('Flag Only', 0x3),               # gives none: the earlier level (0) is kept
            water_cell('Sewer Zero', 0x1)]))            # the flag taken away: no water room any more
        cls.data = GameData().load(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def level(self, name):
        from mwscript import awms
        number = self.data.interior_numbers[name.casefold()]
        found = [r for r in awms.water_rows(self.data) if r[0] == number]
        return found[0][2] if found else None

    def test_the_levels_by_the_records(self):
        self.assertEqual(self.level('Sewer Low'), -1500.0)
        self.assertEqual(self.level('Old Int'), 12.5)
        self.assertEqual(self.level('Flag Only'), 0.0)
        self.assertEqual(self.level('Both Fields'), 20.5)       # WHGT after INTV
        self.assertEqual(self.level('Both Reversed'), 10.0)     # INTV after WHGT
        self.assertIsNone(self.level('Dry Room'))               # no water flag: no row
        self.assertIsNone(self.level('Sewer Zero'))             # the later record took the flag away
        self.assertIsNone(self.level('Test Room'))

    def test_the_rows_are_ascending_and_written_resident(self):
        from mwscript import awms
        rows = awms.water_rows(self.data)
        self.assertEqual(rows, sorted(rows))
        self.assertTrue(all(f == awms.WATER_FLAG for _, f, _ in rows))
        raw, count = awms.water_section(rows)
        self.assertEqual((len(raw), count), (awms.WATER_ROW.size * len(rows), len(rows)))
        self.assertEqual([awms.WATER_ROW.unpack_from(raw, awms.WATER_ROW.size * i) for i in range(count)],
                         [(n, f, 0, level) for n, f, level in rows])

    def test_a_number_past_16_bits_is_refused(self):
        from mwscript import awms

        class Data:
            interior_numbers = {'big room': 70000}
            interior_water = {'big room': {'water': True, 'level': 1.0}}
        with self.assertRaises(ValueError):
            awms.water_rows(Data())


# The scene's two scripts, our own words with the same rules as the original's (the gang's script at the player's
# arrival; the torches' script that hides a torch under the water and shows it above).
ARRIVAL = '''Begin TestWaterArrival
short checked
if ( checked == 0 )
    if ( CellChanged == 1 )
        set checked to 1
        if ( GetHealth > 1 )
            if ( GetWaterLevel == 0 )
                SetHealth 0
            endif
        endif
    endif
endif
End TestWaterArrival
'''

TORCH = '''Begin TestWaterTorch
short ready
short height
short shown
if ( ready == 0 )
    set ready to 1
    set height to GetPos Z
endif
if ( GetWaterLevel > height )
    if ( shown != 1 )
        Disable
        set shown to 1
    endif
elseif ( shown != 2 )
    Enable
    set shown to 2
endif
End TestWaterTorch
'''

# The stub host: GetWaterLevel is answered by the engine's own rules (aw_water_rules.c) from the compiled WATR rows
# for the room ROOM (COLUMN=1: 0, the column walk's reading in a room whose map holds no water); GetPos Z is each
# instance's bound position; health is kept per instance; every Enable and Disable is printed.
HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
#include "aw_water.h"
static int tick,fn_water,column,found;static float level,health[64],zpos[64];
static void h_sound(int i,int t,int s,int how,float v,float p){}
static int h_playing(int i,int t,int s){return 0;}
static void h_say(int i,int t,int v,int x){}
static int h_saydone(int i,int t){return 1;}
static void h_music(int m){}
static float h_distance(int i,int t){return 100.0f;}
static int h_menu(void){return 0;}
static int32_t h_query(int i,int q,int o){return 0;}
static int32_t h_jget(int t){return 0;}
static void h_jset(int t,int32_t v,int adv){}
static void h_notyet(int n,int s){printf("%d notyet %d\n",tick,n);}
static void h_warn(const char *w,int s){}
static int32_t h_object(int i,int t,int op,int32_t v){printf("%d object %d %d\n",tick,i,op);return 0;}
static void h_message(int i,int t,const float *v,int n,const unsigned char *b,int c){}
static int h_button(int i){return -1;}
static aw_mwcell_t h_actor(int i,int t,int verb,int stat,aw_mwcell_t v){
    aw_mwcell_t out;out.i=0;
    if(i<0 || i>=64 || stat!=35)return out;
    if(verb==0)out.f=health[i];
    else if(verb==1)health[i]=v.f;
    else if(verb==2)health[i]+=v.f;
    return out;
}
static int32_t h_item(int i,int t,int verb,int item,int32_t n){return 0;}
static int32_t h_spell(int i,int t,int verb,int s){return 0;}
static void h_combat(int i,int t,int verb,int o){}
static int32_t h_dead(int a){return 0;}
static void h_wander(int i,int t,const int32_t *v,int n){}
static int h_call(int i,int t,int fn,const aw_mwcell_t *v,int n,const unsigned char *s,int ns,aw_mwcell_t *r){
    if(fn==fn_water){r->f=column?0.0f:AW_WaterReading(AW_WATER_ROOM,found,level);return AW_MWVM_CALL_READ;}
    return 0;
}
static int h_cell(int *x,int *y){*x=0;*y=0;return 2;}
static float h_pos(int i,int t,int axis){return i>=0 && i<64 && axis==2?zpos[i]:0.0f;}
static int h_move(int i,int kind,int map,const float *at,float yaw){return 1;}
static int32_t h_ai(int i,int t,int verb){return 0;}
static const aw_mwvm_host_t host={h_sound,h_playing,h_say,h_saydone,h_music,h_distance,h_menu,h_query,h_jget,h_jset,h_notyet,h_warn,h_object,h_message,h_button,
    h_actor,h_item,h_spell,h_combat,h_dead,h_wander,h_call,h_cell,h_pos,h_move,h_ai};
static unsigned char buf[1<<20];
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;float player[3]={0,0,0};
    unsigned room=(unsigned)atoi(getenv("ROOM"));int ticks=atoi(argv[2]);
    fclose(f);
    fn_water=atoi(getenv("FN_WATER"));column=atoi(getenv("COLUMN"));
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    if(!AW_MwvmSection("WATR",&off,&rows,&bytes)){printf("no WATR\n");return 1;}
    found=AW_WaterRow(buf+off,rows,room,&level);
    printf("room %u found %d level %.1f\n",room,found,level);
    AW_MwvmBeginMap();
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3]={0,0,0};int k;
        unsigned ref=((unsigned)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3];
        int32_t z=(int32_t)(((uint32_t)p[20]<<24)|((uint32_t)p[21]<<16)|((uint32_t)p[22]<<8)|p[23]);
        k=AW_MwvmAttach(ref,(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o);
        if(k>=0 && k<64){zpos[k]=(float)z;health[k]=100;}
        printf("attached %u %d\n",ref,k);
    }
    for(tick=1;tick<=ticks;tick++){
        int i;
        AW_MwvmTick(0.1f,player);
        for(i=0;i<64;i++)printf("%d health %d %.0f\n",tick,i,health[i]);
    }
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class TempleSewersScene(unittest.TestCase):
    """The gang's arrival and the torches in a room whose water lies under every placement (Temple Sewers West's
    record level, -1500), the scripts placed there as the original places theirs: a torch under the floor's height
    (z -26) and one high up (z 514)."""

    @classmethod
    def setUpClass(cls):
        from test_mwscript import master_bytes, SCRIPTS, record, sub, ROOMS
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program, bindings
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript import awms
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-water-scene-'))
        scripts = dict(SCRIPTS, TestWaterArrival=ARRIVAL, TestWaterTorch=TORCH)
        records = [record('CREA', sub('NAME', 'test_gang'), sub('SCRI', 'TestWaterArrival')),
                   record('ACTI', sub('NAME', 'test_torch'), sub('SCRI', 'TestWaterTorch')),
                   water_cell('Test Sewer', 0x3, whgt=-1500.0, refs=[
                       (601, 'test_gang', (-5122.3, 437.8, -786.1)), (602, 'test_torch', (-2608.0, 1536.1, -26.0)),
                       (603, 'test_torch', (-1537.7, 460.8, 514.2))])]
        (cls.tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, records))
        data = GameData().load(cls.tmp)
        prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
        binds = bindings(prog, compiled)
        raw, _ = awms.write(prog, compiled, binds, {'ops_per_run': 500})
        (cls.tmp / 'scene.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        cls.names = {c.name: c for c in compiled}
        cls.binds = binds
        cls.room = data.interior_numbers['test sewer']
        cls.env = {'FN_WATER': str(FUNCTION_NUMBERS['getwaterlevel']), 'ROOM': str(cls.room)}
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(SRC),
                                str(cls.tmp / 'h.c'), str(SRC / 'aw_mwvm.c'), str(SRC / 'aw_ledger.c'),
                                str(SRC / 'aw_water_rules.c'), '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_scene(self, column):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'scene.awm'), '4'], capture_output=True, text=True,
                           env=dict(os.environ, COLUMN='1' if column else '0', **self.env))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = r.stdout.splitlines()
        attached = {int(l.split()[1]): int(l.split()[2]) for l in out if l.startswith('attached ')}
        health = {}
        for l in out:
            w = l.split()
            if w[1:2] == ['health']:
                health[(int(w[0]), int(w[2]))] = float(w[3])
        objects = [(int(w[0]), int(w[2]), int(w[3])) for w in (l.split() for l in out) if w[1:2] == ['object']]
        return out, attached, health, objects

    def test_the_scripts_compile_without_gaps(self):
        for name in ('TestWaterArrival', 'TestWaterTorch'):
            self.assertEqual(self.names[name].notyet, [], name)
        self.assertTrue({601, 602, 603} <= {b['reference'] for b in self.binds})

    def test_the_room_reads_its_own_level(self):
        from mwscript.opcodes import OPCODES
        out, attached, health, objects = self.run_scene(column=False)
        self.assertIn('room %d found 1 level -1500.0' % self.room, out)
        gang, low, high = attached[601], attached[602], attached[603]
        self.assertTrue(min(gang, low, high) >= 0, out)
        self.assertEqual(health[(4, gang)], 100.0)              # the gang keeps its health on arrival
        enable, disable = OPCODES['ENABLE'][0], OPCODES['DISABLE'][0]
        self.assertEqual([op for _, i, op in objects if i == low], [enable])    # the low torch stays lit
        self.assertEqual([op for _, i, op in objects if i == high], [enable])

    def test_the_column_reading_would_flood_the_room(self):
        # the reading before v0.0.68 in this room (its map holds no water): 0, so the same scripts kill the gang and
        # hide the low torch; this is the behaviour the fix removes
        from mwscript.opcodes import OPCODES
        out, attached, health, objects = self.run_scene(column=True)
        gang, low, high = attached[601], attached[602], attached[603]
        self.assertEqual(health[(4, gang)], 0.0)
        self.assertEqual([op for _, i, op in objects if i == low], [OPCODES['DISABLE'][0]])
        self.assertEqual([op for _, i, op in objects if i == high], [OPCODES['ENABLE'][0]])


# MWSCRIPT-WATER-LEVEL-STATIC-67: three scripts written for this test (our own words, the same rules as the original's
# crank of the Forgotten Sewer, its blocked trap door, and the lever of Temple Sewers West)
CRANK = '''Begin TestWaterCrank
short moving
short ready
float low
float high
float target
float now
float step
if ( ready == 0 )
    set low to -550
    set high to 400
    set ready to 1
endif
set now to GetWaterLevel
if ( OnActivate == 1 )
    if ( moving == 0 )
        if ( now >= high )
            set target to low
        else
            set target to high
        endif
        set moving to 1
    endif
endif
if ( moving == 0 )
    return
endif
set step to ( 50 * GetSecondsPassed )
if ( target > now )
    set now to ( now + step )
    if ( now > target )
        set now to target
    endif
else
    set now to ( now - step )
    if ( now < target )
        set now to target
    endif
endif
SetWaterLevel now
if ( now == target )
    set moving to 0
endif
End TestWaterCrank
'''

DOOR = '''Begin TestWaterDoor
short ready
float start
float rose
if ( ready == 0 )
    set start to GetWaterLevel
    set ready to 1
endif
if ( OnActivate == 1 )
    set rose to ( GetWaterLevel - start )
    if ( rose > 10 )
        Activate
    else
        MessageBox "The way is blocked."
    endif
endif
End TestWaterDoor
'''

LEVER = '''Begin TestWaterLever
short pulled
float rise
if ( OnActivate == 1 )
    if ( pulled == 0 )
        set pulled to 1
    endif
endif
if ( pulled != 1 )
    return
endif
set rise to ( 200 * GetSecondsPassed )
ModWaterLevel rise
if ( GetWaterLevel >= 850 )
    SetWaterLevel 850
    set pulled to 2
endif
End TestWaterLever
'''

# The stub host: the room ROOM's level from the compiled WATR rows, moved by SetWaterLevel and ModWaterLevel by the
# engine's own rules (aw_water_rules.c, as aw_mwhost.c calls them); only that room's bindings attached; USE "ref:tick,..."
# the player's uses; each change of the level, each object operation and each message box printed.
MOVING = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
#include "aw_water.h"
static int tick,fn_get,fn_set,fn_mod,found;static float level;
static void h_sound(int i,int t,int s,int how,float v,float p){}
static int h_playing(int i,int t,int s){return 0;}
static void h_say(int i,int t,int v,int x){}
static int h_saydone(int i,int t){return 1;}
static void h_music(int m){}
static float h_distance(int i,int t){return 100.0f;}
static int h_menu(void){return 0;}
static int32_t h_query(int i,int q,int o){return 0;}
static int32_t h_jget(int t){return 0;}
static void h_jset(int t,int32_t v,int adv){}
static void h_notyet(int n,int s){printf("%d notyet %d\n",tick,n);}
static void h_warn(const char *w,int s){}
static int32_t h_object(int i,int t,int op,int32_t v){printf("%d object %d %d\n",tick,i,op);return 0;}
static void h_message(int i,int t,const float *v,int n,const unsigned char *b,int c){printf("%d message %d\n",tick,i);}
static int h_button(int i){return -1;}
static aw_mwcell_t h_actor(int i,int t,int verb,int stat,aw_mwcell_t v){aw_mwcell_t out;out.i=0;return out;}
static int32_t h_item(int i,int t,int verb,int item,int32_t n){return 0;}
static int32_t h_spell(int i,int t,int verb,int s){return 0;}
static void h_combat(int i,int t,int verb,int o){}
static int32_t h_dead(int a){return 0;}
static void h_wander(int i,int t,const int32_t *v,int n){}
static int h_call(int i,int t,int fn,const aw_mwcell_t *v,int n,const unsigned char *s,int ns,aw_mwcell_t *r){
    if(fn==fn_get){r->f=AW_WaterReading(AW_WATER_ROOM,found,level);return AW_MWVM_CALL_READ;}
    if((fn==fn_set || fn==fn_mod) && n>=1){
        float now;
        if(!AW_WaterCallChanges(AW_WATER_ROOM,found)){printf("%d refused\n",tick);return 1;}
        now=AW_WaterLevelAfter(fn==fn_mod,level,v[0].f);
        if(now!=level){level=now;printf("%d level %.2f\n",tick,level);AW_MwvmStateChanged();}
        return 1;
    }
    return 0;
}
static int h_cell(int *x,int *y){*x=0;*y=0;return 2;}
static float h_pos(int i,int t,int axis){return 0.0f;}
static int h_move(int i,int kind,int map,const float *at,float yaw){return 1;}
static int32_t h_ai(int i,int t,int verb){return 0;}
static const aw_mwvm_host_t host={h_sound,h_playing,h_say,h_saydone,h_music,h_distance,h_menu,h_query,h_jget,h_jset,h_notyet,h_warn,h_object,h_message,h_button,
    h_actor,h_item,h_spell,h_combat,h_dead,h_wander,h_call,h_cell,h_pos,h_move,h_ai};
static unsigned char buf[1<<20];
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;float player[3]={0,0,0};
    unsigned room=(unsigned)atoi(getenv("ROOM"));int ticks=atoi(argv[2]);const char *use=getenv("USE");
    unsigned uses_ref[16];int uses_tick[16],nuse=0,u;
    fclose(f);
    fn_get=atoi(getenv("FN_GET"));fn_set=atoi(getenv("FN_SET"));fn_mod=atoi(getenv("FN_MOD"));
    while(use && *use && nuse<16){const char *c=strchr(use,':');if(!c)break;uses_ref[nuse]=(unsigned)atoi(use);
        uses_tick[nuse++]=atoi(c+1);use=strchr(c,',');if(use)use++;}
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    if(!AW_MwvmSection("WATR",&off,&rows,&bytes)){printf("no WATR\n");return 1;}
    found=AW_WaterRow(buf+off,rows,room,&level);
    printf("room %u found %d level %.2f\n",room,found,level);
    AW_MwvmBeginMap();
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3]={0,0,0};
        unsigned ref=((unsigned)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3];
        int flags=(p[6]<<8)|p[7],cell=(p[8]<<8)|p[9];
        if(!(flags&AWB_INTERIOR) || (unsigned)cell!=room)continue;
        printf("attached %u %d\n",ref,AW_MwvmAttach(ref,(p[4]<<8)|p[5],flags,-1,o));
    }
    for(tick=1;tick<=ticks;tick++){
        for(u=0;u<nuse;u++)if(uses_tick[u]==tick)printf("%d use %u %d\n",tick,uses_ref[u],AW_MwvmUse(uses_ref[u]));
        AW_MwvmTick(0.1f,player);
    }
    printf("end level %.2f\n",level);
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class MovingWaterScene(unittest.TestCase):
    """The crank and the trap door in a room whose record level is 0 (the Forgotten Sewer's), the lever in a room whose
    record level is -1500 (Temple Sewers West's), and the lever in a room without water: the level each frame, the door
    that opens only once the water has risen, the lever stopping at 850, nothing in the dry room."""

    @classmethod
    def setUpClass(cls):
        from test_mwscript import master_bytes, SCRIPTS, record, sub, ROOMS
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program, bindings
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript import awms
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-water-moving-'))
        scripts = dict(SCRIPTS, TestWaterCrank=CRANK, TestWaterDoor=DOOR, TestWaterLever=LEVER)
        records = [record('ACTI', sub('NAME', 'test_crank'), sub('SCRI', 'TestWaterCrank')),
                   record('DOOR', sub('NAME', 'test_trapdoor'), sub('SCRI', 'TestWaterDoor')),
                   record('ACTI', sub('NAME', 'test_lever'), sub('SCRI', 'TestWaterLever')),
                   water_cell('Test Sewer Zero', 0x3, whgt=0.0, refs=[(701, 'test_crank', (362.2, 4451.8, 572.4)),
                                                                     (702, 'test_trapdoor', (0.3, 3087.3, -30.0))]),
                   water_cell('Test Sewer Low', 0x3, whgt=-1500.0, refs=[(703, 'test_lever', (-48.3, -197.2, -89.7))]),
                   water_cell('Test Dry Room', 0x1, refs=[(704, 'test_lever', (0, 0, 0))])]
        (cls.tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, records))
        data = GameData().load(cls.tmp)
        prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
        binds = bindings(prog, compiled)
        raw, _ = awms.write(prog, compiled, binds, {'ops_per_run': 500})
        (cls.tmp / 'scene.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(MOVING, encoding='utf-8')
        cls.names = {c.name: c for c in compiled}
        cls.rooms = {name: data.interior_numbers[name] for name in ('test sewer zero', 'test sewer low', 'test dry room')}
        cls.env = {'FN_GET': str(FUNCTION_NUMBERS['getwaterlevel']), 'FN_SET': str(FUNCTION_NUMBERS['setwaterlevel']),
                   'FN_MOD': str(FUNCTION_NUMBERS['modwaterlevel'])}
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(SRC),
                                str(cls.tmp / 'h.c'), str(SRC / 'aw_mwvm.c'), str(SRC / 'aw_ledger.c'),
                                str(SRC / 'aw_water_rules.c'), '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_scene(self, room, ticks, use):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'scene.awm'), str(ticks)], capture_output=True,
                           text=True, env=dict(os.environ, ROOM=str(self.rooms[room]), USE=use, **self.env))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = r.stdout.splitlines()
        levels = [(int(w[0]), float(w[2])) for w in (l.split() for l in out) if w[1:2] == ['level'] and w[0].isdigit()]
        return out, levels

    def test_the_scripts_compile_without_gaps(self):
        for name in ('TestWaterCrank', 'TestWaterDoor', 'TestWaterLever'):
            self.assertEqual(self.names[name].notyet, [], name)

    def test_the_crank_raises_and_lowers_the_water_and_the_door_waits_for_it(self):
        from mwscript.opcodes import OPCODES
        # (a use is taken by a script that has read OnActivate once: from the second frame on) the door tried at 3
        # (blocked), the crank used at 5 (up), the door at 95 (open), the crank at 100 (down)
        out, levels = self.run_scene('test sewer zero', 300, '702:3,701:5,702:95,701:100')
        self.assertIn('room %d found 1 level 0.00' % self.rooms['test sewer zero'], out)
        up = [lv for t, lv in levels if t < 100]
        self.assertEqual(up[0], 5.0)                               # 50 units a second, a tenth of a second a frame
        self.assertEqual(up[-1], 400.0)
        self.assertEqual(len(up), 80)                              # 8 s up
        down = [lv for t, lv in levels if t >= 100]
        self.assertEqual(down[-1], -550.0)
        self.assertEqual(len(down), 190)                           # 19 s down
        door = [w for w in (l.split() for l in out)]
        message = [int(w[0]) for w in door if w[1:2] == ['message']]
        activated = [int(w[0]) for w in door if w[1:2] == ['object'] and int(w[3]) == OPCODES['ACTIVATE'][0]]
        self.assertEqual(message, [3])                             # blocked before the water rose
        self.assertEqual(activated, [95])                          # opens once it rose more than 10
        self.assertIn('end level -550.00', out)

    def test_the_lever_floods_the_room_to_850(self):
        out, levels = self.run_scene('test sewer low', 200, '703:2')
        self.assertIn('room %d found 1 level -1500.00' % self.rooms['test sewer low'], out)
        self.assertEqual(levels[0], (2, -1480.0))                  # 200 units a second
        self.assertEqual(levels[-1][1], 850.0)
        self.assertLess(levels[-1][0], 125)                        # about 11.8 s
        self.assertEqual(len([1 for _, lv in levels if lv > 850]), 1)   # one frame past it, then set to 850
        self.assertIn('end level 850.00', out)

    def test_a_room_without_water_keeps_none(self):
        out, levels = self.run_scene('test dry room', 20, '704:2')
        self.assertIn('room %d found 0' % self.rooms['test dry room'], ' '.join(out))
        self.assertEqual(levels, [])
        self.assertTrue(any(l.split()[1:2] == ['refused'] for l in out))


class MovingWaterWiringTests(unittest.TestCase):
    def test_the_host_moves_the_level_saves_it_and_moves_the_plane(self):
        from mwscript import functions as F
        for name in ('setwaterlevel', 'modwaterlevel'):
            self.assertIn(name, F.HOST)
            self.assertIn(name, F.HOST_EFFECTS)
        host = code('aw_mwhost.c')
        call = host[host.index('if(function==AWF_SETWATERLEVEL || function==AWF_MODWATERLEVEL){'):]
        call = call[:call.index('if(function==AWF_HASSOULGEM)')]
        for text in ('AW_WaterCallChanges(where==2?AW_WATER_ROOM:AW_WATER_OUTDOORS,room_water)',
                     'level=AW_WaterLevelAfter(function==AWF_MODWATERLEVEL,room_water_level,numbers[0].f);',
                     'AW_WaterFactId(id,(unsigned long)map_room);',
                     'AW_LedgerFactSet(&aw_ledger,id,(int32_t)AW_WaterFactValue(level))',
                     'AW_WaterPlaneSet(level*0.25f+room_shift[2]);', 'AW_MwvmStateChanged();'):
            self.assertIn(text, call)
        attach = host[host.index('static void water_room_attach(void){'):]
        attach = attach[:attach.index('\n}\n')]
        self.assertIn('if(AW_LedgerFact(&aw_ledger,id,&kept)){room_water_level=AW_WaterFactLevel((long)kept);', attach)
        self.assertIn('attach_map();water_plane_apply();', host)     # after the map's shift is known
        apply = host[host.index('static void water_plane_apply(void){'):]
        apply = apply[:apply.index('\n}\n')]
        self.assertIn('AW_WaterPlaneFind();', apply)                # every attach: the old map's plane forgotten
        self.assertIn('AW_WaterPlaneSet(room_water_level*0.25f+room_shift[2]);', apply)
        init = host[host.index('void AW_MwscriptInit(void){'):]
        self.assertIn('AW_WaterInit();', init[:init.index('\n}\n')])
        self.assertIn('AW_WaterPlaneStatus();', host)
        water = code('aw_water.c')
        self.assertIn('AW_ResetRegister("water plane",reset_water_plane,NULL);', water)
        self.assertIn('Cvar_RegisterVariable(&aw_water_movable);', water)
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', water))
        self.assertIn('aw_water.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        for path in ('engine/aga/src/aw_water.c', 'tests/aga_water_plane_test.c'):
            self.assertIn('"%s"' % path, files)
        # the census no longer lists them as not yet; the console runs them as script lines
        import mwscript_console as C
        self.assertNotIn('setwaterlevel', C.NOT_YET)
        self.assertNotIn('modwaterlevel', C.NOT_YET)

    def test_the_image_ships_the_moving_water_on(self):
        """The shipped default: the image's game settings say aw_water_movable 1 (the engine's default too), the image
        record names it, and the line before says how to keep the water as built (the A/B switch)."""
        import tempfile
        import build_aga
        self.assertIn('{"aw_water_movable", "1"}', code('aw_water.c'))
        self.assertTrue(build_aga.WATER_PLANE_LINES.endswith(b'\naw_water_movable 1\n'))
        self.assertIn(b'"aw_water_movable 0" in the console', build_aga.WATER_PLANE_LINES)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'default-game.cfg').write_bytes(b'aw_mwscript 1')
            record = build_aga.stage_water_plane_config(tmp)
            text = (Path(tmp) / 'default-game.cfg').read_bytes()
        self.assertEqual(text, b'aw_mwscript 1\n' + build_aga.WATER_PLANE_LINES)
        self.assertEqual(record, {'on': True, 'config': 'id1/default-game.cfg', 'line': 'aw_water_movable 1'})
        image = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("args.image_water_plane_config=stage_water_plane_config(boot/'id1')", image)
        self.assertIn("build_json['water_plane'] = args.image_water_plane_config", image)


if __name__ == '__main__':
    unittest.main()
