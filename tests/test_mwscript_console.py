# SPDX-License-Identifier: GPL-3.0-only
"""The original game's console commands (MW-CONSOLE-COMMANDS-62, v0.0.63): the census (config/mwscript-console.json)
gives every original and OpenMW 0.51 console command a state; the aliases are AmiWind's own commands
(engine/aga/src/aw_mwconsole.c), the stat functions run through the MWScript host; a name that is AmiWind's own
top-level command is a collision and stays ours. A native test runs console lines through the parser and table."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
sys.path.insert(0, str(ROOT / 'tools'))

import mwscript_console as C  # noqa: E402

SAME_AS_OURS = {'tcl'}   # AmiWind's own tcl is the same switch (noclip): carried, not a collision


def engine_commands():
    names = set()
    for f in SRC.glob('*.c'):
        names.update(m.lower() for m in re.findall(r'Cmd_AddCommand\s*\(\s*"([^"]+)"', f.read_text(encoding='utf-8', errors='replace')))
    return names


def c_aliases():
    code = (SRC / 'aw_mwconsole.c').read_text(encoding='utf-8')
    table = code[code.index('static const alias_t aliases[]={'):code.index('#define NALIAS')]
    out = set()
    for a, b in re.findall(r'\{"([a-z]+)",(?:"([a-z]+)"|NULL),', table):
        out.add(a)
        if b:
            out.add(b)
    return out


class Census(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        self.rows = self.doc['commands']

    def test_every_command_has_a_state(self):
        self.assertGreater(len(self.rows), 300)
        for r in self.rows:
            self.assertIn(r['state'], C.STATES, r['name'])
            self.assertEqual(r['name'], r['name'].lower())
            if r['state'] in ('alias', 'vm', 'collision', 'not applicable'):
                self.assertTrue(r.get('amiwind'), r['name'])
        self.assertEqual(len({r['name'] for r in self.rows}), len(self.rows))

    def test_the_aliases_are_the_engine_table(self):
        aliases = c_aliases() | {'coe', 'centeronexterior'}
        census = set()
        for r in self.rows:
            if r['state'] == 'alias':
                census.add(r['name'])
                if r.get('short'):
                    census.add(r['short'])
        self.assertEqual(census, aliases)

    def test_a_name_of_ours_is_a_collision(self):
        ours = engine_commands()
        for r in self.rows:
            for n in filter(None, (r['name'], r.get('short'))):
                if n in ours and n not in SAME_AS_OURS:
                    self.assertEqual(r['state'], 'collision', n)
        self.assertEqual({r['name'] for r in self.rows if r['state'] == 'collision'}, {'help', 'say', 'stopsound'})

    def test_the_stat_family_runs_through_the_host(self):
        vm = {r['name'] for r in self.rows if r['state'] == 'vm'}
        stats = {n for n in vm if 'host_actor' in next(r['amiwind'] for r in self.rows if r['name'] == n)}
        # Set/Mod/Get of 8 attributes, 27 skills, 3 dynamic and ModCurrent (the console's own table), and the rest of
        # the compiler's actor calls (Hello, Fight, Flee, Alarm, the level, the disposition, the ratios) by its table
        self.assertGreaterEqual(len(stats), 38 * 3 + 3)
        self.assertIn('setstrength', vm)
        self.assertIn('modcurrenthealth', vm)
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('out=host_actor(k,who,verbs[verb],stat,v);', host)

    def test_the_host_commands_are_the_census(self):
        # the commands run through the host on any target (batch 2): the C table and the census agree
        code = (SRC / 'aw_mwconsole.c').read_text(encoding='utf-8')
        table = code[code.index('static const struct {const char *name;int command,least;} commands[]={'):code.index('#define NCOMMAND')]
        names = set(re.findall(r'\{"([a-z]+)",AW_MWCON_', table))
        self.assertEqual(len(names), 19)
        state = {r['name']: r['state'] for r in self.rows}
        for n in names:
            self.assertEqual(state[n], 'vm', n)
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        body = host[host.index('static int console_command('):host.index('static void console_print(')]
        for call in ('host_item(k,who,', 'host_spell(k,who,', 'host_object(k,who,', 'host_position(k,who,',
                     'host_wander(k,who,', 'AWF_SETPOS', 'AWF_GETANGLE', 'AWF_POSITION', 'AWF_AITRAVEL',
                     'AWF_AIFOLLOW', 'AWF_AIESCORT', 'AW_MwvmScratchEnd(k);'):
            self.assertIn(call, body)
        # the target as the VM's own reference: a scratch instance (AW_MWVM_SELF), never a second lookup
        begin = host[host.index('static int console_begin('):host.index('static int console_stat(')]
        self.assertIn('AW_MwvmScratch((uint32_t)r->_float,NUM_FOR_EDICT(e))', begin)
        self.assertIn('*who=AW_MWVM_SELF;', begin)

    def test_a_placement_without_an_edict_is_a_target(self):
        # WORLD-BUTTONS-62 / MARKS-SUMMON-CARRIERS-NOT-LIVE-63 (v0.0.63 release check round two): the Ghostgate switches
        # and portcullises and the Marks carriers are CHIM placements without an edict; the console finds them by the
        # scripts' object table (an attached instance of that id or its own script, or a scripted mover)
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        begin = host[host.index('static int console_placement('):host.index('static int console_stat(')]
        self.assertIn('AW_MwvmObjectId(k)', begin)
        self.assertIn('(in->flags&AWI_GLOBAL) || !in->reference', begin)      # attached objects only, never a scratch
        self.assertIn('AW_MoverOrigin(r,origin)', begin)                      # a portcullis: where it stands now
        self.assertIn('(*instance=AW_MwvmScratch(ref,-1))<0', begin)
        self.assertIn('AW_MwvmSetOrigin(*instance,at);', begin)
        # the console's Activate is the player's use: the object's own OnActivate script takes it (as E)
        special = host[host.index('static int console_special('):host.index('static int console_table(')]
        self.assertIn('if(in && object_intercept(in->reference)){', special)
        vm = (SRC / 'aw_mwvm.c').read_text(encoding='utf-8')
        self.assertIn('int AW_MwvmObjectId(int k){return ON && k>=0 && k<vm.nobjs?(int)U16(vm.objs+12*k+4):-1;}', vm)
        self.assertIn('int AW_MwvmObjectScript(int k){return ON && k>=0 && k<vm.nobjs?(int)U16(vm.objs+12*k+6):AWM_NONE;}',
                      vm)
        # the OBJS row the builder writes: reference, id string, own script (tools/mwscript/awms.py)
        self.assertIn("struct.pack('>IHHHH', r['reference'], r['id_string'],",
                      (ROOT / 'tools/mwscript/awms.py').read_text(encoding='utf-8'))

    def test_a_placement_no_script_names_is_found_by_its_id(self):
        # WORLD-BUTTONS-62 / MARKS-SUMMON-CARRIERS-NOT-LIVE-63 round three (v0.0.64-dev1 check): the Ghostgate switches
        # and the cursed coins are named by no script, so OBJS has no row for them; BNAM lists every placed scripted
        # reference by its id's hash and the console looks there after OBJS
        from mwscript import awms
        binds = [{'reference': 0x48445, 'id': 'ex_gg_gateswitch_01', 'type': 'ACTI', 'flags': 4},
                 {'reference': 0x48447, 'id': 'EX_GG_GateSwitch_01', 'type': 'ACTI', 'flags': 4},
                 {'reference': 0x40000123, 'id': 'misc_dwrv_cursed_coin00', 'type': 'HELD', 'flags': 8},
                 {'reference': 0x1234, 'id': 'misc_dwrv_cursed_coin00', 'type': 'MISC', 'flags': 2}]
        rows = awms.bound_name_rows(binds)
        self.assertEqual(rows, sorted(rows))
        self.assertIn((awms.fnv1a('ex_gg_gateswitch_01'), 0x48445), rows)
        self.assertIn((awms.fnv1a('ex_gg_gateswitch_01'), 0x48447), rows)   # the id folded: both placements
        self.assertIn((awms.fnv1a('misc_dwrv_cursed_coin00'), 0x1234), rows)
        self.assertEqual(len(rows), 3)                                        # a held item has no place: left out
        self.assertIn('BNAM', awms.ORDER)
        self.assertGreater(awms.ORDER.index('BNAM'), awms.ORDER.index('BIND'))   # on disk, not resident
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('return console_bound(target,ref,origin);', host)
        bound = host[host.index('static int console_bound('):host.index('static int console_placement(')]
        self.assertIn('AW_MwvmSection("BNAM",&off,&rows,&bytes)', bound)
        self.assertIn('in->reference!=r', bound)
        self.assertIn('AW_MoverOrigin(r,origin)', bound)

    def test_the_actor_table_reads_the_whole_directory(self):
        # UNDERWATER-BREATH-62 round three: the engine read at most 32 directory rows of mwscript.awm while the file
        # has more since v0.0.63, so AEFF (every spell's effects), AMGE, AENC and APCS were never found and no game
        # spell could be cast. The engine's limit covers every section the builder writes, with room to grow.
        from mwscript import awms
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        limit = int(re.search(r'#define AW_MWSCRIPT_SECTIONS (\d+)', host).group(1))
        self.assertGreaterEqual(limit, len(awms.ORDER) + 8)
        self.assertNotIn('if(n>32)n=32;', host)
        self.assertIn('static unsigned char head[16+16*AW_MWSCRIPT_SECTIONS];', host)
        self.assertGreater(awms.ORDER.index('AEFF'), 31)   # the section the old cut lost

    def test_the_actor_reader_answers_zero_when_it_read(self):
        # UNDERWATER-BREATH-62 round three: actor_read answers 0 on a good read; the console's id index search tested
        # it the other way round, so player->getspell "argonian breathing" answered 0 for a player holding the spell
        # (and a trap's spell and additem of a known item missed too). Every call site keeps the convention.
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('return fread(out,1,bytes,actor_file)!=bytes;', host)
        calls = re.findall(r'(.{0,4})actor_read\(NULL,', host)
        self.assertTrue(calls)
        for before in calls:
            self.assertFalse(before.endswith('&& ') or before.endswith('&&'), before)   # "&& actor_read" = success taken as failure
        self.assertNotIn('if(!actor_read(', host)
        self.assertIn('if(actor_read(NULL,off+2u*mid,b,2))return -1;', host)

    def test_the_finder_and_the_help(self):
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('Cmd_AddCommand("aw_mw_target",mw_target);', host)
        self.assertIn('s.title="Console target: type to filter (name, id, kind), Enter sets it";', host)
        self.assertIn('static void finder_closed(void *ctx){(void)ctx;if(finder)free(finder);', host)   # only while open
        self.assertIn('Con_DrawTarget (y);', (SRC / 'console.c').read_text(encoding='utf-8'))
        cat = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('UI / CONSOLE|mw target|aw_mw_target|', cat)
        self.assertIn('UI / CONSOLE|mw help|aw_mw_help|', cat)
        con = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        self.assertIn('if(!Q_strcasecmp(word,"mw")){AW_MwConsoleHelp();return;}', con)
        page = con[con.index('static void mwhelp_page(void) {'):con.index('void AW_MwConsoleHelp(void) {')]
        self.assertIn('static char line[256];', page)            # one line kept, the file read a page at a time
        self.assertNotIn('Malloc', page)
        self.assertIn('fclose(f);', page)
        helptext = (ROOT / 'config/mwconsole-help.txt').read_text(encoding='ascii')
        self.assertTrue(helptext.startswith('AWMH1\n'))
        self.assertEqual(helptext, C.help_text(self.doc))
        self.assertIn("('mwconsole-help.txt', b'AWMH1')", (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        cmd = (SRC / 'cmd.c').read_text(encoding='utf-8')
        self.assertIn('if (src == src_command && AW_MwConsoleLine (text))', cmd)
        self.assertIn('aw_mwconsole.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_every_alias_has_its_counterpart_row(self):
        rows = json.loads((ROOT / 'config/mwscript-counterparts.json').read_text(encoding='utf-8'))['console']
        named = {n.lower() for r in rows for n in r['original']}
        for r in self.rows:
            if r['state'] == 'alias':
                self.assertTrue(r['name'] in named or r.get('short') in named, r['name'])
        for r in rows:
            self.assertIn(r['verdict'], ('same', 'partial'))

    def test_the_page_lists_every_command(self):
        page = C.PAGE.read_text(encoding='utf-8')
        self.assertIn('Morrowind:Console', page)
        self.assertIn('## Collisions', page)
        for r in self.rows:
            self.assertIn('| %s |' % r['name'], page)
        c = C.counts(self.doc)
        self.assertIn('%d commands: ' % sum(c.values()), page)
        self.assertIn('CONSOLE_COMMANDS_MORROWIND.md', (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8'))


NATIVE = r'''
#include <stdio.h>
#include <string.h>
#include "aw_mwconsole.h"
static void ex(const char *t){printf("exec %s|\n",t);}
static int st(const char *target,int verb,int stat,float *value){
    printf("stat [%s] %d %d %g\n",target,verb,stat,(double)*value);
    if(!strcmp(target,"nobody"))return 0;
    if(verb==0)*value=42;
    return 1;
}
static void pr(const char *t){printf("print %s",t);}
static int cm(const char *target,int command,const aw_mwcon_line_t *l,char *answer,int capacity){
    int i,least;
    printf("command [%s] %s",target,AW_MwConsoleCommandName(command,&least));
    for(i=0;i<l->args;i++)printf(" <%s>",l->arg[i]);
    printf("\n");
    if(!strcmp(target,"nobody"))return 0;
    snprintf(answer,(size_t)capacity,"answer %d\n",least);
    return 1;
}
int main(int argc,char **argv){
    static const aw_mwcon_host_t h={ex,cm,st,pr};int i;
    for(i=1;i<argc;i++)printf("ran %d\n",AW_MwConsoleRun(argv[i],&h));
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'no C compiler')
class NativeLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-mwcon-'))
        (cls.tmp / 't.c').write_text(NATIVE, encoding='utf-8')
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                '-I', str(SRC), str(cls.tmp / 't.c'), str(SRC / 'aw_mwconsole.c'), '-o',
                                str(cls.tmp / 't')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_lines(self, *lines):
        return subprocess.run([str(self.tmp / 't')] + list(lines), capture_output=True, text=True,
                              check=True).stdout.splitlines()

    def test_aliases_become_our_commands(self):
        out = self.run_lines('tgm', 'ToggleGodMode', 'TCL', 'coc "Seyda Neen"', 'coe -2, -9', 'fixme')
        self.assertEqual([l for l in out if l.startswith('exec')],
                         ['exec dbg god|', 'exec dbg god|', 'exec noclip|', 'exec dbg tp "Seyda Neen"|',
                          'exec dbg tp -12288 -69632|', 'exec dbg unstuck|'])

    def test_the_target_rule(self):
        out = self.run_lines('player->AddItem "iron dagger", 5', 'Fargoth -> removeitem gold_001 100',
                             'additem', 'nobody->GetItemCount x', 'fargoth->setlevel 5')
        self.assertEqual(out[0], 'command [player] additem <iron dagger> <5>')
        self.assertEqual(out[1], 'print answer 1')
        self.assertEqual(out[3], 'command [Fargoth] removeitem <gold_001> <100>')
        self.assertEqual(out[6], 'print additem: 1 argument.')        # the host is not called
        self.assertIn('no such reference here: nobody', out[9])
        self.assertIn('only the player can be the target', out[11])   # setlevel is dbg setlvl: the player's

    def test_the_host_commands(self):
        lines = ('enable', 'x->disable', 'getdisabled', 'position 1 2 3 90', 'positioncell 1 2 3 0 "Seyda Neen"',
                 'setpos x 100', 'getpos z', 'setangle z 90', 'getangle z', 'aiwander 512 0 0', 'aitravel 1 2 3',
                 'aifollow player 0', 'aiescort player 0 1 2 3', 'equip iron_dagger', 'addspell fireball',
                 'removespell fireball')
        out = self.run_lines(*lines)
        cmds = [l.split()[2] for l in out if l.startswith('command')]
        self.assertEqual(cmds, [l.split('->')[-1].split()[0] for l in lines])
        self.assertIn('command [] positioncell <1> <2> <3> <0> <Seyda Neen>', out)
        self.assertIn('command [x] disable', out)

    def test_a_stat_line_runs_through_the_host(self):
        out = self.run_lines('player->SetStrength 50', 'modblock, -5', 'GetHealth', 'ModCurrentFatigue 10',
                             'SetLuck', 'ModCurrentLuck 5', 'fargoth->GetHealth')
        self.assertEqual(out[0], 'stat [player] 1 0 50')
        self.assertEqual(out[2], 'stat [] 2 8 -5')
        self.assertEqual(out[4:6], ['stat [] 0 35 0', 'print gethealth -> 42'])
        self.assertEqual(out[7], 'stat [] 3 37 10')
        self.assertEqual(out[9], 'print setluck: one number.')
        self.assertEqual(out[11], 'ran 0')                        # ModCurrent of an attribute: not a function
        self.assertEqual(out[12], 'stat [fargoth] 0 35 0')        # any actor by id->

    def test_an_unknown_line_is_left_to_the_engine(self):
        self.assertEqual(self.run_lines('frobnicate 1', ''), ['ran 0', 'ran 0'])


TIMING = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
/* MW-CONSOLE-COMMANDS-62: the console's id lookup as the engine reads the file (aw_mwhost.c console_row): per row an
 * AITM row (32 bytes), its string's offset (4) and the string, each a seek and a read through a 1 KB buffer. ROWS
 * items "item_%05d" in a file of AITM rows then STRS; the scan reads every row up to the last id, the index's binary
 * search about log2(ROWS) rows. Prints rows per ms (this host) and the rows each method reads. */
#define ROWS 5000
static FILE *f;static long strs,probes;
static void id_of(int row,char *out){
    unsigned char r[32],o[4];long at;
    probes++;
    fseek(f,32L*row,SEEK_SET);if(fread(r,1,32,f)!=32)exit(2);
    fseek(f,strs+4L*((r[0]<<8)|r[1]),SEEK_SET);if(fread(o,1,4,f)!=4)exit(2);
    at=((long)o[0]<<24)|(o[1]<<16)|(o[2]<<8)|o[3];
    fseek(f,strs+at,SEEK_SET);if(!fgets(out,32,f))exit(2);
}
int main(int argc,char **argv){
    static char buf[1024];char s[32],want[32];int i,lo,hi,found=-1;clock_t t0;double scan_ms,index_ms;long scan_rows;
    (void)argc;
    f=fopen(argv[1],"rb");if(!f)return 1;
    setvbuf(f,buf,_IOFBF,sizeof(buf));
    strs=32L*ROWS;
    sprintf(want,"item_%05d",ROWS-1);
    t0=clock();probes=0;
    for(i=0;i<ROWS && found<0;i++){id_of(i,s);s[strcspn(s,"\n")]=0;if(!strcmp(s,want))found=i;}
    scan_ms=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;scan_rows=probes;
    t0=clock();probes=0;lo=0;hi=ROWS;found=-1;
    while(lo<hi && found<0){int mid=(lo+hi)/2,c;id_of(mid,s);s[strcspn(s,"\n")]=0;c=strcmp(s,want);
        if(!c)found=mid;else if(c<0)lo=mid+1;else hi=mid;}
    index_ms=(double)(clock()-t0)*1000.0/CLOCKS_PER_SEC;
    printf("scan rows %ld ms %.3f rows_per_ms %.0f index rows %ld ms %.4f found %d\n",scan_rows,scan_ms,
           scan_ms>0?scan_rows/scan_ms:0.0,probes,index_ms,found);
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'no C compiler')
class IdLookupTiming(unittest.TestCase):
    def test_the_index_reads_a_few_rows_where_the_scan_reads_them_all(self):
        import struct
        tmp = Path(tempfile.mkdtemp(prefix='aw-mwcon-time-'))
        try:
            rows = 5000
            names = [('item_%05d\n' % i).encode() for i in range(rows)]
            offsets, at = [], 4 * rows
            for n in names:
                offsets.append(at)
                at += len(n)
            body = b''.join(struct.pack('>H', i) + bytes(30) for i in range(rows))
            body += b''.join(struct.pack('>I', o) for o in offsets) + b''.join(names)
            (tmp / 'table.bin').write_bytes(body)
            (tmp / 't.c').write_text(TIMING, encoding='utf-8')
            built = subprocess.run(['cc', '-std=gnu89', '-O1', '-Wall', '-Werror', str(tmp / 't.c'), '-o',
                                    str(tmp / 't')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            out = subprocess.run([str(tmp / 't'), str(tmp / 'table.bin')], capture_output=True, text=True,
                                 check=True).stdout.split()
            print('\nid lookup on this host: scan %s rows in %s ms (%s rows/ms); index %s rows' % (
                out[2], out[4], out[6], out[9]))
            self.assertEqual(int(out[-1]), rows - 1)
            self.assertEqual(int(out[2]), rows)              # the scan reads every row to the last id
            self.assertLessEqual(int(out[9]), 14)            # the sorted index: log2(5000) rows
            self.assertGreater(float(out[6]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_build_writes_the_sorted_index(self):
        actors = (ROOT / 'tools/mwscript/actors.py').read_text(encoding='utf-8')
        self.assertIn("return {'AIDX': by_id(self.item_index), 'ASPX': by_id(self.spell_index),", actors)
        awms = (ROOT / 'tools/mwscript/awms.py').read_text(encoding='utf-8')
        self.assertIn("'AIDX', 'ASPX')", awms)
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('if(AW_MwvmSection(spell?"ASPX":"AIDX",&off,&rows,&bytes) && rows){', host)


class NotYetByCallSites(unittest.TestCase):
    # v0.0.63: the not-yet functions with call sites in the game's scripts, most called first: GetWaterLevel (9),
    # HurtCollidingActor (3), GetCollidingPC (2), GetWeaponType (1), GetStat (1); each carried by the host and in the
    # console's table. SetWaterLevel (3) and ModWaterLevel (1) stay: the room's water is baked into its map
    def test_carried_by_the_host_and_in_the_console(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from mwscript import functions as F
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        table = (ROOT / 'config/mwconsole-functions.txt').read_text(encoding='ascii').split('\n')
        for name in ('getwaterlevel', 'hurtcollidingactor', 'getcollidingpc', 'getweapontype', 'getstat'):
            self.assertIn(name, F.HOST, name)
            self.assertIn('AWF_' + name.upper(), host)
            self.assertTrue(any(l.startswith(name + ' host ') for l in table), name)
        self.assertIn('if(function==AWF_GETSTAT){result->i=0;return AW_MWVM_CALL_READ;}', host)
        self.assertIn('AW_ActorWeaponType(a->base)', host)
        self.assertIn('if(host_player_cell(&x,&y)!=2)', host.replace('!sv.active || !sv_player || ', ''))
        self.assertIn('sv_player->v.absmin[i]>e->v.absmax[i]+1', host)
        self.assertNotIn('setwaterlevel', F.HOST)


class Uncalled(unittest.TestCase):
    # v0.0.63 (MWSCRIPT-GAPS-63): functions no game script calls, carried for the console and add-on content: the
    # magic effect family past the resistances (OpenMW statsextensions.cpp's table) and the reads of uncalled_call
    EFFECTS = {'chameleon': '40', 'waterwalking': '2', 'swimspeed': '1', 'superjump': '9', 'flying': '10',
               'armorbonus': '3', 'castpenalty': '48', 'silence': '46', 'blindness': 'AW_EFFECT_BLIND',
               'paralysis': '45', 'invisible': '39', 'attackbonus': 'AW_EFFECT_FORTIFY_ATTACK',
               'defendbonus': 'AW_EFFECT_SANCTUARY'}
    READS = ('getcurrenttime', 'getmasserphase', 'getsecundaphase', 'getstartingpos', 'getstartingangle',
             'pcget3rdperson', 'pcforce1stperson', 'pcforce3rdperson', 'getpcjumping', 'getspellreadied',
             'getstandingactor', 'getcollidingactor')

    def test_each_carried_by_the_host_and_in_the_console(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from mwscript import functions as F
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        code = (SRC / 'aw_mwcode.h').read_text(encoding='utf-8')
        table = (ROOT / 'config/mwconsole-functions.txt').read_text(encoding='ascii').split('\n')
        for e, number in self.EFFECTS.items():
            row = '{AWF_GET%s,AWF_SET%s,AWF_MOD%s,%s,-1,-1}' % (e.upper(), e.upper(), e.upper(), number)
            self.assertIn(row, host)
            for verb in ('get', 'set', 'mod'):
                name = verb + e
                self.assertIn(name, F.HOST, name)
                self.assertTrue(F.FUNCTIONS[name].run)
                self.assertIn('#define AWF_%s %d\n' % (name.upper(), F.FUNCTION_NUMBERS[name]), code)
                self.assertTrue(any(l.startswith(name + ' host ') for l in table), name)
            self.assertIn('set' + e, F.HOST_EFFECTS)
        for name in self.READS:
            self.assertIn(name, F.HOST, name)
            self.assertIn('#define AWF_%s %d\n' % (name.upper(), F.FUNCTION_NUMBERS[name]), code)
            self.assertIn('AWF_' + name.upper(), host.split('static int uncalled_call(')[1].split('static int gap_call(')[0])
            self.assertTrue(any(l.startswith(name + ' host ') for l in table), name)
        self.assertTrue({'pcforce1stperson', 'pcforce3rdperson'} <= F.HOST_EFFECTS)
        self.assertIn('if(k>=RESIST_PASSIVE_FIRST)', host)
        self.assertIn('{AWF_GETWATERBREATHING,AWF_SETWATERBREATHING,AWF_MODWATERBREATHING,AW_EFFECT_WATER_BREATHING,-1,-1},\n'
                      '    /* v0.0.63', host)   # Water Breathing stays row 10, RESIST_PASSIVE_FIRST

    BATCH2 = ('getpcrunning', 'forcejump', 'clearforcejump', 'forcemovejump', 'clearforcemovejump', 'getforcejump',
              'getforcemovejump', 'getarmortype', 'samefaction', 'getfactionreaction', 'removeeffects',
              'removespelleffects', 'addsoulgem', 'dropsoulgem', 'enablelevelupmenu')

    def test_batch2_carried(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from mwscript import functions as F
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        code = (SRC / 'aw_mwcode.h').read_text(encoding='utf-8')
        body = host.split('static int uncalled_call(')[1].split('static int gap_call(')[0]
        table = (ROOT / 'config/mwconsole-functions.txt').read_text(encoding='ascii').split('\n')
        for name in self.BATCH2:
            self.assertIn(name, F.HOST, name)
            self.assertIn('#define AWF_%s %d\n' % (name.upper(), F.FUNCTION_NUMBERS[name]), code)
            self.assertIn('AWF_' + name.upper(), body)
            if name != 'removespelleffects':   # its argument is the compiler's spell row
                self.assertTrue(any(l.startswith(name + ' host ') for l in table), name)
        move = (SRC / 'aw_move.c').read_text(encoding='utf-8')
        self.assertIn('if(ground_now && (aw_move_force_jump || (aw_move_force_move_jump && last_factor>0)))p->v.button2=1;',
                      move)
        self.assertIn('int AW_DialReaction(const aw_dial_t *d,const char *a,const char *b) {',
                      (SRC / 'aw_dial.c').read_text(encoding='utf-8'))
        # the ones left keep a named reason in the census
        doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        why = {r['name'].casefold(): r.get('why', '') for r in doc['commands'] if r['state'] == 'planned'}
        for name in ('setwaterlevel', 'getwindspeed', 'togglegrid', 'toggleloadfade'):
            if name in why:
                self.assertIn(C.NOT_YET[name], why[name])

    BATCH3 = ('show', 'showvars', 'sv', 'togglescripts', 'toggleai', 'tai', 'resetactors', 'ra', 'outputrefinfo',
              'ori', 'user1', 'user2', 'user3', 'user4', 'togglecollision', 'tcl', 'togglegodmode', 'tgm',
              'togglemenus', 'tm', 'togglevanitymode', 'tvm', 'centeroncell', 'coc', 'centeronexterior', 'coe', 'fixme')

    def test_batch3_console_group_carried(self):
        # v0.0.63 batch 3: the console group as script functions too (aw_mwhost.c console_group_call)
        sys.path.insert(0, str(ROOT / 'tools'))
        from mwscript import functions as F
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        code = (SRC / 'aw_mwcode.h').read_text(encoding='utf-8')
        body = host.split('static int console_group_call(')[1].split('static int gap_call(')[0]
        table = (ROOT / 'config/mwconsole-functions.txt').read_text(encoding='ascii').split('\n')
        for name in self.BATCH3:
            self.assertIn(name, F.HOST, name)
            self.assertIn(name, F.HOST_EFFECTS, name)
            self.assertTrue(F.FUNCTIONS[name].run, name)
            self.assertIn('#define AWF_%s %d\n' % (name.upper(), F.FUNCTION_NUMBERS[name]), code)
            self.assertIn('AWF_' + name.upper(), body)
            self.assertTrue(any(l.startswith(name + ' host ') for l in table), name)
        self.assertIn('if((k=console_group_call(instance,target,function,numbers,count,strings,nstrings,result))!=0)',
                      host)
        amb = (SRC / 'aw_ambient.c').read_text(encoding='utf-8')
        self.assertIn('int AW_AmbientEnabled(void) {return ambient_on;}', amb)
        self.assertIn('int AW_AmbientResetActors(void) {', amb)
        # the aliases keep their AmiWind line: the script form runs the same one
        con = (SRC / 'aw_mwconsole.c').read_text(encoding='utf-8')
        for line in ('"noclip"', '"dbg god"', '"dbg killhud"', '"dbg vanitycam on"', '"dbg unstuck"'):
            self.assertIn(line, con)
            self.assertIn('console_exec(%s)' % line, body)
        doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        state = {r['name'].casefold(): r['state'] for r in doc['commands']}
        for name in ('show', 'showvars', 'togglescripts', 'toggleai', 'resetactors', 'ori', 'outputrefinfo', 'user1'):
            self.assertEqual(state[name], 'vm', name)
        why = {r['name'].casefold(): r.get('why', '') for r in doc['commands'] if r['state'] == 'planned'}
        for name in ('togglesky', 'togglewater', 'toggleworld', 'testcells', 'togglefogofwar'):
            self.assertIn(C.NOT_YET[name], why[name])

    def test_console_only_toggles_mapped(self):
        # the original's console-only toggles with an AmiWind switch: aliases; "toggle CVAR" flips it in console_exec
        con = (SRC / 'aw_mwconsole.c').read_text(encoding='utf-8')
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        for row in ('{"tdt","toggledebugtext","dbg hud",0}', '{"tst","togglestats","dbg fps",0}',
                    '{"tcs","togglecombatstats","toggle aw_combat_readout",0}',
                    '{"tl","togglelights","toggle r_fullbright",0}', '{"repairedonme",NULL,"echo 0",0}'):
            self.assertIn(row, con)
        self.assertIn('if(!strncmp(text,"toggle ",7)){', host)
        self.assertIn('Cvar_SetValue(v->name,v->value?0.0f:1.0f);', host)
        doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        state = {r['name'].casefold(): r['state'] for r in doc['commands']}
        for name in ('toggledebugtext', 'togglestats', 'togglecombatstats', 'togglelights', 'repairedonme'):
            self.assertEqual(state[name], 'alias', name)

    def test_the_census_names_them_vm(self):
        doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        state = {r['name'].casefold(): r['state'] for r in doc['commands']}
        for name in ('getchameleon', 'setinvisible', 'getcurrenttime', 'pcforce3rdperson'):
            if name in state:
                self.assertEqual(state[name], 'vm', name)


class FunctionTable(unittest.TestCase):
    def test_the_table_is_the_compilers(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from mwscript import functions as F
        lines = (ROOT / 'config/mwconsole-functions.txt').read_text(encoding='ascii').splitlines()
        self.assertEqual(lines[0], 'AWMF1')
        self.assertEqual(lines[1:], C.function_rows())
        for line in lines[1:]:
            name, kind = line.split()[:2]
            self.assertIn(name, F.FUNCTIONS)
            if kind == 'host':
                self.assertEqual(int(line.split()[2]), F.FUNCTION_NUMBERS[name])
                self.assertIn(name, F.HOST)
                self.assertNotIn(name, C.COMPILED_ARGUMENTS)
        doc = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        for r in doc['commands']:
            if r['state'] == 'planned':
                self.assertTrue(r.get('why'), r['name'])
        self.assertIn("('mwconsole-functions.txt', b'AWMF1')", (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('got=host_call(k,who,a,numbers,nn,strings,ns,&result);', host)
        self.assertIn('COM_FOpenFile("mwconsole-functions.txt",&f)', host)


if __name__ == '__main__':
    unittest.main()
