# SPDX-License-Identifier: GPL-3.0-only
"""MWScript compiled by the builder (docs/MWSCRIPT_BYTECODE.md): the parser on the language's quirks, the bytecode
and file round trips, the shared opcode table against the engine's header, the engine's interpreter natively
(audio through stubs, branching, globals, journal, timers, the quiet rule, the budget, NOTYET logged once) and the
builder stage on a small synthetic game data set (no game data in the repo)."""
import json
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
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

from mwscript.lexer import tokenize  # noqa: E402
from mwscript.parser import Parser, ParseError, parse  # noqa: E402
from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript.codegen import SCRIPT_VOLATILE, SCRIPT_NOTYET, SCRIPT_HANDWRITTEN, SCRIPT_INERT, fold  # noqa: E402
from mwscript.opcodes import OPCODES, QUERIES  # noqa: E402
from mwscript.media import MediaMap  # noqa: E402
from mwscript import awms  # noqa: E402


# --- a tiny synthetic master (records() reads any sequence of records) ---
def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, flags) + payload


def scpt(name, text):
    head = name.encode('cp1252').ljust(32, b'\0') + struct.pack('<5I', 0, 0, 0, 0, 0)
    return record('SCPT', sub('SCHD', head), sub('SCTX', text.encode('cp1252')))


def glob(name, kind, value):
    return record('GLOB', sub('NAME', name), sub('FNAM', kind.encode('ascii')), sub('FLTV', struct.pack('<f', value)))


def soun(name, file, volume=200, lo=0, hi=0):
    return record('SOUN', sub('NAME', name), sub('FNAM', file), sub('DATA', bytes([volume, lo, hi])))


def acti(name, script):
    return record('ACTI', sub('NAME', name), sub('SCRI', script))


def cell_exterior(x, y, refs):
    parts = [sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y))]
    for number, ident, pos in refs:
        parts += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                  sub('DATA', struct.pack('<6f', pos[0], pos[1], pos[2], 0, 0, 0))]
    return record('CELL', *parts)


SCRIPTS = {
    'AmbientWind': '''Begin AmbientWind
; a sound marker: loops while near, the classic way
if ( CellChanged == 1 )
    PlayLoopSound3DVP, "Cave Wind", 1.0, 1.0
endif
End''',
    'TimerChime': '''begin TimerChime
float timer
short count
set timer to timer + GetSecondsPassed
if ( timer >= 1.0 )
    set timer to 0
    set count to count + 1
    PlaySound3D "Chime"
    if ( count == 3 )
        set QuestFlag to 2
        Journal "QA_Test" 10
    endif
endif
end''',
    'Quiet': '''Begin Quiet
short done
if ( done == 0 )
    set done to 1
    set Counter to Counter + 1
endif
if ( QuestFlag == 2 )
    if ( done == 1 )
        set done to 2
        StreamMusic "Special/Victory.mp3"
    endif
endif
End''',
    'NotYetUser': '''Begin NotYetUser
if ( OnActivate == 1 )
    Activate
    PlaySound "Chime"
endif
AiWander 100 5 0
AiWander 100 5 0
End''',
    'Inert': '''Begin Inert
float t
set t to t + GetSecondsPassed
Rotate Z 30
End''',
    'Looper': '''Begin Looper
short n
while ( n < 100000 )
    set n to n + 1
endwhile
set Counter to Counter
End''',
    'chargenTest': '''Begin chargenTest
PlaySound "Chime"
End''',
}


def master_bytes(scripts=SCRIPTS):
    out = [record('TES3', sub('HEDR', b'\0' * 300))]
    out += [glob('QuestFlag', 's', 0), glob('Counter', 'l', 0), glob('Fraction', 'f', 1.5)]
    out += [soun('Cave Wind', 'Fx\\envrn\\cave_wind.wav', 128, 10, 40), soun('Chime', 'Fx\\chime.wav')]
    out += [scpt(name, text) for name, text in scripts.items()]
    out += [acti('marker_wind', 'AmbientWind'), acti('chime_obj', 'TimerChime'), acti('quiet_obj', 'Quiet'),
            acti('notyet_obj', 'NotYetUser'), acti('loop_obj', 'Looper'), acti('cg_obj', 'chargenTest'),
            acti('inert_obj', 'Inert')]
    out.append(cell_exterior(0, 0, [(101, 'marker_wind', (100, 200, 0)), (102, 'chime_obj', (400, 0, 0)),
                                    (103, 'quiet_obj', (0, 0, 0)), (104, 'notyet_obj', (8, 8, 0)),
                                    (105, 'loop_obj', (16, 16, 0)), (106, 'cg_obj', (0, 0, 0)),
                                    (107, 'inert_obj', (0, 0, 0))]))
    return b''.join(out)


def catalogue():
    def row(source, path, frames, category='effects'):
        return {'source': source, 'category': category, 'status': 'included', 'path': path, 'frames': frames}
    return {'format': 'AWMEDIA1', 'excluded': [], 'entries': [
        row('sound/fx/envrn/cave_wind.mp3', 'sound/pool/a00112233445566aa.wav', 22050),
        row('sound/fx/chime.wav', 'sound/pool/a0123456789abcdef.wav', 5512)]}


SOUNDTRACK = {'tracks': [{'file': 'track07.mws', 'source': 'Music/Special/victory.mp3', 'seconds': 30}]}


class SyntheticData:
    def __enter__(self):
        self.dir = Path(tempfile.mkdtemp(prefix='aw-mwscript-'))
        (self.dir / 'Morrowind.esm').write_bytes(master_bytes())
        self.data = GameData().load(self.dir)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)


def program(handwritten=('chargen*',)):
    with SyntheticData() as s:
        media = MediaMap(s.data, catalogue(), SOUNDTRACK)
        prog, compiled = compile_program(s.data, media, handwritten=handwritten)
        return prog, compiled, bindings(prog), s.data


class LexerParserTests(unittest.TestCase):
    def test_tolerances(self):
        warnings = []
        toks = tokenize('PlaySound3DVP, "a b", 1.0: 0.5\nif [ x = 1 ]\nTel-Branora 1stFloor\n"open\n', warnings)
        kinds = [(t.kind, t.value) for t in toks if t.kind != 'nl'][:12]
        self.assertEqual(kinds[:4], [('name', 'PlaySound3DVP'), ('name', 'a b'), ('float', 1.0), ('float', 0.5)])
        self.assertIn(('op', '('), kinds)
        self.assertIn(('op', '=='), kinds)
        self.assertIn(('name', 'Tel-Branora'), kinds)
        self.assertIn(('name', '1stFloor'), kinds)
        self.assertTrue(any('read as ==' in w for w in warnings))
        self.assertTrue(any('unterminated string' in w for w in warnings))

    def test_else_junk_stray_endif_and_unknown_set(self):
        tree, p = parse('Begin t\nshort a\nif ( a == 1 )\nset a to 2\nelse set a to 3\nendif\nendif\n'
                        'set nosuch to 1\nEnd\n')
        body = tree[2]
        self.assertEqual(body[0][0], 'if')
        self.assertEqual(body[0][3], [])                           # the junk after else is skipped (OpenMW)
        self.assertTrue(any('stray endif' in w for w in p.warnings))
        self.assertTrue(any('unknown variable' in w for w in p.warnings))
        self.assertEqual(len(body), 1)

    def test_reference_on_brackets_member_and_cell_first(self):
        tree, p = parse('Begin t\nshort s\nif "ghost"->( OnDeath == 1 )\nset s to "other".count\nendif\n'
                        'PositionCell "Raven Rock, Bar" 1 2 3 0\nEnd\n')
        cond = tree[2][0][2][0][0]
        self.assertEqual(cond[0], 'cmp')
        self.assertEqual(cond[2][1], 'ghost')                      # the call carries the reference
        self.assertEqual(tree[2][0][2][0][1][0][3], ('member', 'other', 'count'))
        self.assertEqual(tree[2][1][2][3][-1], ('str', 'Raven Rock, Bar'))

    def test_unknown_name_in_an_expression_is_an_error(self):
        with self.assertRaises(ParseError):
            parse('Begin t\nif ( NoSuchThing == 0 )\nendif\nEnd\n')

    def test_messagebox_arguments_and_buttons(self):
        tree, p = parse('Begin t\nfloat f\nMessageBox "Value %.0f" f "Ok" "Cancel"\nEnd\n')
        call = tree[2][0][2]
        self.assertEqual(call[2], 'messagebox')
        self.assertEqual(call[4], {'format': 'Value %.0f', 'nargs': 1, 'buttons': ['Ok', 'Cancel']})

    def test_constant_folding(self):
        self.assertEqual(fold(('bin', '*', ('int', 2), ('int', 30))), ('int', 60))
        self.assertEqual(fold(('bin', '/', ('int', 7), ('int', 2))), ('int', 3))
        self.assertEqual(fold(('cmp', '<', ('int', 1), ('float', 2.0))), ('int', 1))


class CompilerTests(unittest.TestCase):
    def test_program_compiles_and_round_trips(self):
        prog, compiled, binds, data = program()
        names = {c.name: c for c in compiled}
        self.assertEqual({c.name for c in compiled if c.error}, set())
        self.assertTrue(names['TimerChime'].flags & SCRIPT_VOLATILE)
        self.assertFalse(names['Quiet'].flags & SCRIPT_VOLATILE)
        self.assertTrue(names['NotYetUser'].flags & SCRIPT_NOTYET)
        self.assertTrue(names['chargenTest'].flags & SCRIPT_HANDWRITTEN)
        raw, sizes = awms.write(prog, compiled, binds)
        f = awms.read(raw)
        self.assertEqual(f['resident'], sizes['resident'])
        rows = awms.scripts(f)
        for row, c in zip(rows, compiled):
            self.assertEqual(row['code'], c.code)
            decoded = awms.decode(row['code'])
            again = bytearray()
            for _, name, args in decoded:     # re-encode every instruction: byte-identical
                code, layout = OPCODES[name]
                again.append(code)
                if layout == 'N':
                    again += struct.pack('>HBB', *args[:3]) + b''.join(struct.pack('>H', s) for s in args[3:])
                else:
                    for letter, value in zip(layout, args):
                        again += struct.pack({'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter], value)
            self.assertEqual(bytes(again), row['code'])
        strings = awms.strings(f)
        self.assertIn('AmbientWind', strings)
        self.assertEqual(len(binds), 7)
        self.assertTrue(names['Inert'].flags & SCRIPT_INERT)
        self.assertNotIn(107, [b['reference'] for b in bindings(prog, compiled)])   # inert: left out of the file
        self.assertFalse(names['NotYetUser'].flags & SCRIPT_INERT)
        self.assertFalse(names['Looper'].flags & SCRIPT_INERT)   # it writes a global (after its loop)
        self.assertFalse(names['TimerChime'].flags & SCRIPT_INERT)
        self.assertEqual([b['reference'] for b in binds], sorted(b['reference'] for b in binds))

    def test_media_map_by_index_with_repairs(self):
        prog, compiled, binds, data = program()
        wind = prog.sounds.rows[prog.sounds.index['cave wind']]
        self.assertTrue(wind['resolved'])
        self.assertEqual(wind['path_pool'], 'sound/pool/a00112233445566aa.wav')
        self.assertIn('.mp3', wind['note'])                       # requested .wav, the data has the .mp3
        music = prog.music.rows[0]
        self.assertEqual((music['resolved'], music['track']), (True, 7))
        with SyntheticData() as s:
            m = MediaMap(s.data, {'entries': []}, None)
            self.assertEqual(m.sound('Chime')['reason'], 'missing source')
            self.assertEqual(m.sound('No Such')['reason'], 'no SOUN record')
            c = catalogue(); c['entries'][1]['status'] = 'missing_output'
            self.assertEqual(MediaMap(s.data, c, None).sound('Chime')['reason'], 'not converted')
            self.assertEqual(MediaMap(s.data, catalogue(), None).sound('chime  ')['resolved'], True)

    def test_shared_opcode_table_matches_the_engine_header(self):
        header = (ROOT / 'engine/aga/src/aw_mwcode.h').read_text(encoding='utf-8')
        defined = {m.group(1): int(m.group(2), 0) for m in re.finditer(r'#define AWM_(\w+) (0x[0-9A-Fa-f]+)', header)}
        for name, (code, _) in OPCODES.items():
            self.assertEqual(defined.get(name), code, name)
        self.assertEqual(set(defined) - {'NONE'}, set(OPCODES))
        queries = {m.group(1): int(m.group(2)) for m in re.finditer(r'#define AWQ_(\w+) (\d+)', header)}
        for name, number in QUERIES.items():
            self.assertEqual(queries.get(name), number, name)
        self.assertEqual(queries['COUNT'], max(QUERIES.values()) + 1)


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
static int tick;static int journal[64];
static void h_sound(int i,int t,int s,int how,float v,float p){printf("%d sound %d %d %d %d %.2f\n",tick,i,t,s,how,v);}
static int h_playing(int i,int t,int s){return 0;}
static void h_say(int i,int t,int v,int x){printf("%d say %d %d\n",tick,i,v);}
static int h_saydone(int i,int t){return 1;}
static void h_music(int m){printf("%d music %d\n",tick,AW_MwvmMusic(m));}
static float h_distance(int i,int t){return 100.0f;}
static int h_menu(void){return 0;}
static int32_t h_query(int i,int q,int o){return 0;}
static int32_t h_jget(int t){return journal[t];}
static void h_jset(int t,int32_t v,int adv){if(!adv || v>journal[t])journal[t]=v;printf("%d journal %d %d\n",tick,t,v);}
static void h_notyet(int n,int s){printf("%d notyet %d\n",tick,n);}
static void h_warn(const char *w,int s){printf("%d warn %s\n",tick,w);}
static const aw_mwvm_host_t host={h_sound,h_playing,h_say,h_saydone,h_music,h_distance,h_menu,h_query,h_jget,h_jset,h_notyet,h_warn};
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");static unsigned char buf[1<<20];long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;
    int ticks=atoi(argv[2]),i;float player[3]={0,0,0},dt=(float)atof(argv[3]);
    fclose(f);
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    AW_MwvmBeginMap();
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3];
        for(i=0;i<3;i++)o[i]=(float)(int32_t)(((uint32_t)p[12+4*i]<<24)|((uint32_t)p[13+4*i]<<16)|((uint32_t)p[14+4*i]<<8)|p[15+4*i])*0.25f;
        printf("attach %u %d\n",(unsigned)((p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3]),
               AW_MwvmAttach(((uint32_t)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3],(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o));
    }
    for(tick=1;tick<=ticks;tick++)AW_MwvmTick(dt,player);
    {const aw_mwvm_stats_t *s=AW_MwvmStats();
     printf("stats runs %lu quiet %lu far %lu deferred %lu aborted %lu notyet %lu\n",s->runs,s->skipped_quiet,s->skipped_far,s->deferred,s->aborted,s->notyet_calls);}
    for(i=0;i<AW_MwvmGlobalCount();i++)printf("global %d %d %f\n",i,AW_MwvmGlobalInt(i),AW_MwvmGlobalFloat(i));
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InterpreterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-'))
        cls.prog, cls.compiled, binds, _ = program()
        raw, _ = awms.write(cls.prog, cls.compiled, binds, {'ops_per_run': 500})
        (cls.tmp / 'test.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_mwvm.c'), '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_vm(self, ticks, dt='0.25'):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'test.awm'), str(ticks), dt],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.splitlines()

    def index(self, table, key):
        return getattr(self.prog, table).index[key]

    def test_audio_timers_globals_journal_music(self):
        out = self.run_vm(16)
        wind, chime = self.index('sounds', 'cave wind'), self.index('sounds', 'chime')
        loops = [l for l in out if ' sound ' in l and l.split()[4] == str(wind)]
        self.assertEqual(len(loops), 1, out)                      # CellChanged: once, on the first run
        self.assertTrue(loops[0].startswith('1 ') and loops[0].split()[5] == '2')
        chimes = [int(l.split()[0]) for l in out if ' sound ' in l and l.split()[4] == str(chime)]
        self.assertEqual(chimes, [4, 8, 12, 16])                  # every second of 0.25 s frames
        self.assertIn('12 journal %d 10' % self.index('journal', 'qa_test'), out)
        # the quiet script wakes on the global change: the same frame or the next (round robin order)
        self.assertEqual(len([l for l in out if re.fullmatch(r'1[23] music 7', l)]), 1, out)
        g = {l.split()[1]: l.split() for l in out if l.startswith('global')}
        self.assertEqual(g[str(self.index('globals', 'questflag'))][2], '2')
        self.assertEqual(g[str(self.index('globals', 'counter'))][2], '1')
        self.assertFalse([l for l in out if ' sound ' in l and l.split()[4] == str(chime) and l.split()[0] == '0'])

    def test_handwritten_scripts_do_not_attach(self):
        out = self.run_vm(1)
        self.assertIn('attach 106 -1', out)
        self.assertIn('attach 107 -1', out)                       # inert today: not attached

    def test_quiet_rule_notyet_once_and_the_loop_guard(self):
        out = self.run_vm(16)
        stats = next(l for l in out if l.startswith('stats')).split()
        self.assertGreater(int(stats[4]), 0)                       # quiet skips happened
        notyet = [l for l in out if l.split()[1:2] == ['notyet']]
        # OnActivate and AiWander once each; Activate never runs (the not-yet OnActivate reads 0)
        self.assertEqual(len(notyet), 2, notyet)
        self.assertTrue(all(int(l.split()[0]) <= 2 for l in notyet), notyet)   # on its first run (budget order)
        self.assertGreaterEqual(int(stats[10]), 1)                 # the endless loop was stopped
        self.assertTrue(any('opcode limit' in l for l in out))


class BuilderStageTests(unittest.TestCase):
    def test_stage_writes_reads_back_and_reuses(self):
        import prepare_mwscript
        with SyntheticData() as s:
            media = s.dir / 'media'; media.mkdir()
            (media / 'media-coverage.json').write_text(json.dumps(catalogue()))
            music = s.dir / 'music'; music.mkdir()
            (music / 'soundtrack.json').write_text(json.dumps(SOUNDTRACK))
            pool = s.dir / 'pool'
            for attempt in ('miss', 'hit'):
                out = s.dir / ('out-' + attempt)
                self.assertEqual(prepare_mwscript.main(['--data-files', str(s.dir), '--media', str(media),
                                                        '--music', str(music), '--out', str(out),
                                                        '--cache', str(pool)]), 0)
                receipt = json.loads((out / 'mwscript-receipt.json').read_text())
                self.assertEqual(receipt['cache'], attempt)
                raw = (out / 'id1/mwscript.awm').read_bytes()
                f = awms.read(raw)
                self.assertEqual(f['SCRP_rows'], len(SCRIPTS))
                report = json.loads((out / 'mwscript-report.json').read_text())
                self.assertEqual(report['media']['sounds']['mapped'], 2)
                self.assertEqual(report['media']['music']['mapped'], 1)
            self.assertEqual((s.dir / 'out-miss/id1/mwscript.awm').read_bytes(),
                             (s.dir / 'out-hit/id1/mwscript.awm').read_bytes())


if __name__ == '__main__':
    unittest.main()
