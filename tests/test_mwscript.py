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


def cell_exterior(x, y, refs, name='', region=None):
    parts = [sub('NAME', name), sub('DATA', struct.pack('<Iii', 0, x, y))] + ([sub('RGNN', region)] if region else [])
    for number, ident, pos in refs:
        parts += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                  sub('DATA', struct.pack('<6f', pos[0], pos[1], pos[2], 0, 0, 0))]
    return record('CELL', *parts)


def cell_interior(name):
    return record('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0)))


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
AiTravel 100 5 0
AiTravel 100 5 0
End''',
    # the actor record (v0.0.54): stats, items, spells, combat, wander and the dead count reach the host
    'ActorUser': '''Begin ActorUser
short step
if ( step == 0 )
    set step to 1
    SetFight 90
    ModHealth -5
    "chime_obj"->AddItem "Gold_005" 3
    player->RemoveItem "misc_thing" 2
    AddSpell "test spell"
    StartCombat player
    StopCombat
    AIWander 512 5 0 0 10 20 30
endif
if ( GetHealth < 50 )
    set step to 2
endif
if ( OnDeath == 1 )
    set step to 3
endif
if ( GetDeadCount "nobody" == 0 )
    set step to step
endif
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
    # object state (v0.0.51): Disable when not disabled, another object's lock, Lock without a level, Unlock
    'GateScript': '''Begin GateScript
short step
short choice
if ( step == 0 )
    set step to 1
    if ( GetDisabled == 0 )
        Disable
    endif
    "chime_obj"->Lock 50
    Lock
    Unlock
    if ( GetLocked == 0 )
        Enable
    endif
    MessageBox "Gate %.1f of %d" step 2 "Open" "Leave"
endif
; activation (v0.0.51): the player's use comes here; Activate hands it back to the object
if ( OnActivate == 1 )
    Activate
endif
; messages (v0.0.51): the button the player chose, once
set choice to GetButtonPressed
if ( choice == 0 )
    "chime_obj"->Unlock
endif
End''',
    # the original's sound markers start their loop on the run after the cell change (v0.0.54: CellChanged is not
    # VOLATILE; the interpreter runs the script once more after the run that read 1)
    'MarkerZero': '''begin MarkerZero
if ( CellChanged == 0 )
    if ( GetSoundPlaying "Drip" == 0 )
        PlayLoopSound3DVP "Drip" 0.4, 1.0
    endif
endif
end''',
    # the world and cell lookups (v0.0.54): the player's cell by name prefix (a room, an outdoor cell's own name, a
    # region's name), a position, a disease among the player's spells; DontSaveObject and Xbox as OpenMW has them
    'CellUser': '''Begin CellUser
if ( Where == 0 )
    player->PositionCell 4000 8000 -200 90 "Test Room"
    player->PositionCell 100 200 300 0 "Seyda Neen"
    player->PositionCell 1 2 3 0 "Another Room"
    "cell_obj"->PositionCell 1 2 3 0 "Test Room"
endif
if ( GetPCCell "test room" == 1 )
    set Where to 2
elseif ( GetPCCell "Seyda" == 1 )
    set Where to 1
elseif ( GetPCCell "Bitter Coast" == 1 )
    set Where to 3
else
    set Where to 0
endif
set PosX to GetPos x
if ( player->GetCommonDisease == 1 )
    set Where to Where + 10
endif
DontSaveObject
set Where to Where + Xbox
if ( BM_NoSuchVariable == 0 )
    set Where to Where + 100
endif
if ( GetCurrentAIPackage == 0 )
    if ( GetAIPackageDone == 0 )
        if ( "actor_obj"->GetAIPackageDone == 1 )
            set Where to Where + 1000
        endif
    endif
endif
End''',
}


def master_bytes(scripts=SCRIPTS):
    out = [record('TES3', sub('HEDR', b'\0' * 300))]
    out += [glob('QuestFlag', 's', 0), glob('Counter', 'l', 0), glob('Fraction', 'f', 1.5), glob('Where', 'l', 0),
            glob('PosX', 'f', 0)]
    out += [record('REGN', sub('NAME', 'Bitter Coast Region'), sub('FNAM', 'Bitter Coast Region'))]
    out += [soun('Cave Wind', 'Fx\\envrn\\cave_wind.wav', 128, 10, 40), soun('Chime', 'Fx\\chime.wav'),
            soun('Drip', 'Fx\\drip.wav')]
    out += [scpt(name, text) for name, text in scripts.items()]
    out += [acti('marker_wind', 'AmbientWind'), acti('chime_obj', 'TimerChime'), acti('quiet_obj', 'Quiet'),
            acti('notyet_obj', 'NotYetUser'), acti('loop_obj', 'Looper'), acti('cg_obj', 'chargenTest'),
            acti('inert_obj', 'Inert'), acti('gate_obj', 'GateScript'), acti('actor_obj', 'ActorUser'),
            acti('cell_obj', 'CellUser'), acti('drip_obj', 'MarkerZero')]
    out.append(cell_exterior(0, 0, [(101, 'marker_wind', (100, 200, 0)), (102, 'chime_obj', (400, 0, 0)),
                                    (103, 'quiet_obj', (0, 0, 0)), (104, 'notyet_obj', (8, 8, 0)),
                                    (105, 'loop_obj', (16, 16, 0)), (106, 'cg_obj', (0, 0, 0)),
                                    (107, 'inert_obj', (0, 0, 0)), (108, 'gate_obj', (0, 0, 0)),
                                    (109, 'actor_obj', (0, 0, 0)), (110, 'cell_obj', (0, 0, 0)),
                                    (111, 'drip_obj', (0, 0, 0))]))
    out += [cell_exterior(-2, -9, [], 'Seyda Neen', 'bitter coast region'),
            cell_exterior(-3, -9, [], '', 'bitter coast region'), cell_interior('Test Room'),
            cell_interior('Another Room')]
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


# the room maps the player's PositionCell may load (a test room list: "Another Room" is in none, so stays not yet)
ROOMS = {'test room': {'map': 'ri0123456789', 'offset': [100, 0, 0]}}


def program(handwritten=('chargen*',)):
    with SyntheticData() as s:
        media = MediaMap(s.data, catalogue(), SOUNDTRACK)
        prog, compiled = compile_program(s.data, media, handwritten=handwritten, rooms=ROOMS)
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

    def test_unknown_name_in_an_expression_reads_as_a_number(self):
        # OpenMW's rule for legacy content (exprparser.cpp parseName): its leading digits, else 0 (four Bloodmoon
        # scripts test a journal id this way)
        tree, p = parse('Begin t\nshort a\nif ( BM_BearHunt1 == 0 )\nset a to 12abc\nendif\nEnd\n')
        cond = tree[2][0][2][0][0]
        self.assertEqual(cond, ('cmp', '==', ('float', 0.0), ('int', 0)))
        self.assertEqual(tree[2][0][2][0][1][0][3], ('float', 12.0))
        self.assertTrue(any('read as a number' in w for w in p.warnings))
        # a reference before a name that is no function is dropped, the name read as it is (OpenMW)
        tree, p = parse('Begin t\nshort fakeiswere\nif ( Player->fakeiswere == 0 )\nendif\nEnd\n')
        self.assertEqual(tree[2][0][2][0][0][2], ('local', 'fakeiswere'))
        with self.assertRaises(ParseError):
            parse('Begin t\nif ( == 0 )\nendif\nEnd\n')

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
                elif layout == 'F':
                    again += struct.pack('>HHBB', *args[:4]) + b''.join(struct.pack('>H', s) for s in args[4:])
                else:
                    for letter, value in zip(layout, args):
                        again += struct.pack({'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter], value)
            self.assertEqual(bytes(again), row['code'])
        strings = awms.strings(f)
        self.assertIn('AmbientWind', strings)
        self.assertEqual(len(binds), 11)                          # GateScript, ActorUser, CellUser, MarkerZero too
        self.assertFalse(names['MarkerZero'].flags & SCRIPT_VOLATILE)   # CellChanged and GetSoundPlaying only
        self.assertFalse(names['AmbientWind'].flags & SCRIPT_VOLATILE)
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
        # the import route: every function has a number the engine counts (AWM_FUNCTIONS of them)
        from mwscript.functions import FUNCTIONS, FUNCTION_NUMBERS
        from mwscript.opcodes import FUNCTIONS_MAX, SPELL_VERBS
        self.assertIn('#define AWM_FUNCTIONS %d ' % FUNCTIONS_MAX, header)
        self.assertLessEqual(len(FUNCTIONS), FUNCTIONS_MAX)
        self.assertEqual(sorted(FUNCTION_NUMBERS.values()), list(range(len(FUNCTIONS))))
        self.assertIn('#define AWM_SPELL_COMMON_DISEASE %d' % SPELL_VERBS['common_disease'], header)
        self.assertIn('#define AWM_SPELL_BLIGHT_DISEASE %d' % SPELL_VERBS['blight_disease'], header)

    def test_every_call_is_kept_and_the_cell_table(self):
        # the import route: a not-yet call keeps its function's number, its name and its arguments (numbers on the
        # stack, strings by index); GetPCCell names become rows of cells (rooms by number, outdoor cells by grid)
        from mwscript.functions import FUNCTION_NUMBERS
        prog, compiled, binds, data = program()
        names = {c.name: c for c in compiled}
        calls = [a for _, n, a in awms.decode(names['NotYetUser'].code) if n == 'NOTYET']
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], FUNCTION_NUMBERS['aitravel'])
        self.assertEqual(prog.strings.rows[calls[0][1]], 'aitravel')
        self.assertEqual(calls[0][2] & 0x1F, 3)                    # three numbers: 100 5 0
        cell = names['CellUser']
        # PositionCell: the player's moves are worked out here; a room no list names and another object stay not yet
        self.assertEqual([prog.strings.rows[a[1]] for _, n, a in awms.decode(cell.code) if n == 'NOTYET'],
                         ['positioncell', 'positioncell'])
        moves = [a[0] for _, n, a in awms.decode(cell.code) if n == 'PLAYERMOVE']
        self.assertEqual(len(moves), 2)
        room, outdoors = (prog.moves.rows[m] for m in moves)
        self.assertEqual((room['kind'], prog.strings.rows[room['map']]), (2, 'ri0123456789'))
        self.assertEqual(room['at'], (975.0, 2000.0, -50 + 16.875))      # (x - 100) / 4, y / 4, z / 4 + the feet
        self.assertEqual(room['yaw'], 0)                                  # 90 degrees: the door rule's yaw 0
        self.assertEqual((outdoors['kind'], outdoors['at'], outdoors['yaw']), (1, (100.0, 200.0, 300.0), 0.0))
        self.assertTrue(any('read as a number' in w for w in cell.warnings))
        rows = {r['name'].casefold(): r for r in prog.pccells.rows}
        room = data.interior_numbers['test room']
        self.assertEqual((rows['test room']['rooms'], rows['test room']['outside']), ([room], []))
        self.assertEqual(rows['seyda']['outside'], [(-2, -9)])
        self.assertEqual(rows['bitter coast']['outside'], [(-3, -9)])  # (-2, -9) has a name of its own
        f = awms.read(awms.write(prog, compiled, binds)[0])
        self.assertEqual(f['PCEL_rows'], 3)
        self.assertIn('PCEL', awms.RESIDENT)


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
static int disabled,locked;
static int32_t h_object(int i,int t,int op,int32_t v){
    printf("%d object %d %d %d %d\n",tick,i,t,op,(int)v);
    if(op==AWM_DISABLE)disabled=1;
    if(op==AWM_ENABLE)disabled=0;
    if(op==AWM_LOCK && t==AW_MWVM_SELF)locked=v<0?100:v;
    if(op==AWM_UNLOCK && t==AW_MWVM_SELF)locked=0;
    return op==AWM_GETDISABLED?disabled:op==AWM_GETLOCKED?locked>0:0;
}
static void h_message(int i,int t,const float *v,int n,const unsigned char *b,int c){
    int k;printf("%d message %d %d %d",tick,i,t,n);
    for(k=0;k<n;k++)printf(" %.2f",v[k]);
    printf(" buttons %d",c);
    for(k=0;k<c;k++)printf(" %d",(b[2*k]<<8)|b[2*k+1]);
    printf("\n");
}
static int h_button(int i){return tick==5?0:-1;}   /* the player chooses the first button at tick 5 */
static float health=60;
static aw_mwcell_t h_actor(int i,int t,int verb,int stat,aw_mwcell_t v){
    aw_mwcell_t out;out.i=0;
    printf("%d actor %d %d %d %d %d %.2f\n",tick,i,t,verb,stat,v.i,verb?v.f:0.0f);
    if(stat==35 && verb==2)health+=v.f;
    if(stat==35 && verb==0)out.f=health;
    return out;
}
static int32_t h_item(int i,int t,int verb,int item,int32_t n){printf("%d item %d %d %d %d %d\n",tick,i,t,verb,item,(int)n);return 0;}
static int32_t h_spell(int i,int t,int verb,int s){printf("%d spell %d %d %d %d\n",tick,i,t,verb,s);return verb==3;}
static void h_combat(int i,int t,int verb,int o){printf("%d combat %d %d %d %d\n",tick,i,t,verb,o);}
static int32_t h_dead(int a){printf("%d dead %d\n",tick,a);return 0;}
static void h_wander(int i,int t,const int32_t *v,int n){int k;printf("%d wander %d %d",tick,i,t);for(k=0;k<n;k++)printf(" %d",(int)v[k]);printf("\n");}
/* the import route: every NOTYET call with its number and arguments; carried out (answer 7) when CALLS asks */
static int answer=-1;
static int h_call(int i,int t,int fn,const aw_mwcell_t *v,int n,const unsigned char *s,int ns,aw_mwcell_t *r){
    int k;printf("%d call %d %d",tick,fn,n);for(k=0;k<n;k++)printf(" %d",(int)v[k].i);printf(" strings %d\n",ns);
    if(fn!=answer)return 0;
    r->i=7;return 1;
}
/* the player stands outdoors in (-2, -9) for two frames, then in the room ROOM (when set) */
static int room;
static int h_cell(int *x,int *y){if(tick<=2 || !room){*x=-2;*y=-9;return 1;}*x=room;*y=0;return 2;}
static float h_pos(int i,int t,int axis){printf("%d pos %d %d %d\n",tick,i,t,axis);return 123.5f;}
static int h_move(int i,int kind,int map,const float *at,float yaw){
    printf("%d move %d %d %.3f %.3f %.3f %.1f\n",tick,kind,map,at[0],at[1],at[2],yaw);return 1;}
/* the AI package: the script's own actor wanders (0) and its package is not done; another object's is done */
static int32_t h_ai(int i,int t,int verb){printf("%d ai %d %d %d\n",tick,i,t,verb);return verb?t!=AW_MWVM_SELF:0;}
static const aw_mwvm_host_t host={h_sound,h_playing,h_say,h_saydone,h_music,h_distance,h_menu,h_query,h_jget,h_jset,h_notyet,h_warn,h_object,h_message,h_button,
    h_actor,h_item,h_spell,h_combat,h_dead,h_wander,h_call,h_cell,h_pos,h_move,h_ai};
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");static unsigned char buf[1<<20];long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;
    int ticks=atoi(argv[2]),i;float player[3]={0,0,0},dt=(float)atof(argv[3]);
    unsigned used=argc>4?(unsigned)atoi(argv[4]):0;   /* the player uses this reference's object at tick 3 */
    fclose(f);
    if(getenv("ROOM"))room=atoi(getenv("ROOM"));
    if(getenv("CALLS"))answer=atoi(getenv("CALLS"));
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    AW_MwvmBeginMap();
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3];
        for(i=0;i<3;i++)o[i]=(float)(int32_t)(((uint32_t)p[12+4*i]<<24)|((uint32_t)p[13+4*i]<<16)|((uint32_t)p[14+4*i]<<8)|p[15+4*i])*0.25f;
        printf("attach %u %d\n",(unsigned)((p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3]),
               AW_MwvmAttach(((uint32_t)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3],(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o));
    }
    for(tick=1;tick<=ticks;tick++){
        if(used && tick==3)
            for(i=0;i<AW_MwvmInstanceCount();i++){
                aw_mwvm_instance_t *in=AW_MwvmInstance(i);
                if(in && (in->flags&AWI_USED) && in->reference==used &&
                   (AW_MwvmScriptFlags(in->script)&AWS_ONACTIVATE)){in->flags|=AWI_ACTIVATED;printf("%d used %d\n",tick,i);}
            }
        AW_MwvmTick(dt,player);
    }
    {const aw_mwvm_stats_t *s=AW_MwvmStats();
     printf("stats runs %lu quiet %lu far %lu deferred %lu aborted %lu notyet %lu host %lu\n",s->runs,s->skipped_quiet,s->skipped_far,s->deferred,s->aborted,s->notyet_calls,s->host_calls);}
    for(i=0;i<AWM_FUNCTIONS;i++)if(AW_MwvmFunctionCalls(i))printf("function %d %lu %d\n",i,AW_MwvmFunctionCalls(i),AW_MwvmFunctionName(i));
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

    def run_vm(self, ticks, dt='0.25', used=None, env=None):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'test.awm'), str(ticks), dt]
                           + ([str(used)] if used else []), capture_output=True, text=True,
                           env=dict(os.environ, **(env or {})))
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
        # AiTravel and PositionCell (of another object, into a room no list names), once each (OnActivate and
        # Activate run since v0.0.51; never used here, OnActivate reads 0; AIWander runs since v0.0.54)
        self.assertEqual(len(notyet), 2, notyet)
        self.assertTrue(all(int(l.split()[0]) <= 2 for l in notyet), notyet)   # on its first run (budget order)
        self.assertGreaterEqual(int(stats[10]), 1)                 # the endless loop was stopped
        self.assertTrue(any('opcode limit' in l for l in out))


    def test_object_state_calls_reach_the_host(self):
        # v0.0.51: Disable/Enable/GetDisabled/Lock/Unlock/GetLocked run (no longer "not yet"); in order, on the
        # object REF names (the chime object for the second Lock) or the script's own (-2)
        out = self.run_vm(4)
        calls = [l.split()[2:] for l in out if l.split()[1:2] == ['object']]
        chime = str(self.index('objects', 'chime_obj'))
        codes = {name: str(code) for name, (code, _) in OPCODES.items()}
        self.assertEqual([c[1:] for c in calls], [
            ['-2', codes['GETDISABLED'], '0'], ['-2', codes['DISABLE'], '0'], [chime, codes['LOCK'], '50'],
            ['-2', codes['LOCK'], '-1'], ['-2', codes['UNLOCK'], '0'], ['-2', codes['GETLOCKED'], '0'],
            ['-2', codes['ENABLE'], '0']], out)
        self.assertEqual(len({c[0] for c in calls}), 1)          # one instance, on its first run only

    def test_onactivate_takes_the_use_and_activate_hands_it_back(self):
        # v0.0.51: the script reads OnActivate (flag ONACTIVATE): the player's use at tick 3 reads 1 once there,
        # and its Activate reaches the host on that run only
        out = self.run_vm(6, used=108)
        self.assertTrue(any(l.split()[1:2] == ['used'] for l in out), out)
        activates = [l.split()[0] for l in out if l.split()[1:2] == ['object'] and l.split()[4] == str(OPCODES['ACTIVATE'][0])]
        self.assertEqual(activates, ['3'], out)
        self.assertNotIn(str(OPCODES['ACTIVATE'][0]), [l.split()[4] for l in self.run_vm(6) if l.split()[1:2] == ['object']])

    def test_messagebox_reaches_the_host_and_getbuttonpressed_reads_the_choice(self):
        # v0.0.51: MessageBox carries its text, its numbers (step 1, the constant 2, as numbers with a fraction) and
        # its buttons by string index; the choice of the first button (tick 5) is read once: the Unlock follows
        out = self.run_vm(7)
        messages = [l.split() for l in out if l.split()[1:2] == ['message']]
        self.assertEqual(len(messages), 1, out)
        m = messages[0]
        self.assertEqual(m[0], '1')
        self.assertEqual(m[4:7], ['2', '1.00', '2.00'])
        self.assertEqual(m[7:9], ['buttons', '2'])
        strings = self.prog.strings.index
        self.assertEqual(m[3], str(strings['Gate %.1f of %d']))
        self.assertEqual(m[9:], [str(strings['Open']), str(strings['Leave'])])
        chime = str(self.index('objects', 'chime_obj'))
        unlocks = [l.split()[0] for l in out if l.split()[1:2] == ['object'] and l.split()[3] == chime
                   and l.split()[4] == str(OPCODES['UNLOCK'][0])]
        self.assertEqual(unlocks, ['5'], out)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class ActorCallTests(unittest.TestCase):
    """The actor record's calls (v0.0.54, docs/ACTOR_STATE.md) compile to their opcodes and reach the host."""
    setUpClass = classmethod(InterpreterTests.setUpClass.__func__)
    tearDownClass = classmethod(InterpreterTests.tearDownClass.__func__)
    run_vm = InterpreterTests.run_vm
    index = InterpreterTests.index

    def test_actor_calls_reach_the_host(self):
        from mwscript.opcodes import ACTOR_STATS, VERBS
        out = self.run_vm(4)
        first = [l.split()[1:] for l in out if l.split()[0] == '1' and l.split()[1] in
                 ('actor', 'item', 'spell', 'combat', 'wander', 'dead')]
        kinds = [r[0] for r in first]
        self.assertEqual(kinds[:7], ['actor', 'actor', 'item', 'item', 'spell', 'combat', 'combat'], first)
        self.assertEqual(first[0][3:6], [str(VERBS['set']), str(ACTOR_STATS['fight']), '90'])   # whole number
        self.assertEqual(first[1][3:5], [str(VERBS['mod']), str(ACTOR_STATS['health'])])
        self.assertEqual(first[1][6], '-5.00')                                                    # a fraction
        gold = self.prog.actors.item_index['gold_001']
        self.assertEqual(first[2][2:], [str(self.index('objects', 'chime_obj')), '1', str(gold), '3'])  # gold_005: gold
        self.assertEqual(first[3][2:4], ['-1', '2'])                                              # the player
        self.assertEqual(first[5][2:], ['-2', '0', '-1'])                                         # StartCombat player
        wander = next(r for r in first if r[0] == 'wander')
        self.assertEqual(wander[3:], ['512', '5', '0', '0', '10', '20', '30'])
        # GetDeadCount of an id no actor has: DEADCOUNT 0xFFFF reads 0 without asking the host
        self.assertFalse(any(r[0] == 'dead' for r in first))
        code = next(c for c in self.compiled if c.name == 'ActorUser').code
        self.assertIn(('DEADCOUNT', [0xFFFF]), [(n, a) for _, n, a in awms.decode(code)])

    def test_actor_reads_are_not_volatile(self):
        from mwscript.codegen import SCRIPT_ACTOR
        c = next(c for c in self.compiled if c.name == 'ActorUser')
        self.assertFalse(c.flags & SCRIPT_VOLATILE)
        self.assertTrue(c.flags & SCRIPT_ACTOR)
        self.assertFalse(c.flags & SCRIPT_NOTYET)

    def test_stats_agree_with_the_engine(self):
        from mwscript.opcodes import ACTOR_STATS, VERBS
        header = (ROOT / 'engine/aga/src/aw_actorstate.h').read_text(encoding='utf-8')
        found = {m.group(1).lower(): int(m.group(2)) for m in re.finditer(r'AWA_([A-Z]+)=(\d+)', header)}
        for name, number in ACTOR_STATS.items():
            self.assertEqual(found.get(name), number, name)
        verbs = {m.group(1).lower(): int(m.group(2)) for m in re.finditer(r'AWV_([A-Z]+)=(\d+)', header)}
        self.assertEqual(verbs, VERBS)
        code = (ROOT / 'engine/aga/src/aw_mwcode.h').read_text(encoding='utf-8')
        for name, number in VERBS.items():
            self.assertIn('#define AWM_VERB_%s %d' % (name.upper(), number), code)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class ImportRouteTests(unittest.TestCase):
    """v0.0.54: every not-yet call counted by its function number and handed to the host with its arguments; the
    world and cell lookups (GetPCCell, GetPos, the diseases) and OpenMW's constants."""
    setUpClass = classmethod(InterpreterTests.setUpClass.__func__)
    tearDownClass = classmethod(InterpreterTests.tearDownClass.__func__)
    run_vm = InterpreterTests.run_vm
    index = InterpreterTests.index

    def globals_of(self, out):
        return {l.split()[1]: l.split() for l in out if l.startswith('global')}

    def test_cell_position_disease_and_constants(self):
        where, posx = str(self.index('globals', 'where')), str(self.index('globals', 'posx'))
        # outdoors in (-2, -9), named Seyda Neen: 1; the player's common disease: +10; Xbox 0; the unknown name 0: +100;
        # its own actor wanders, not done, the other actor's package done: +1000
        out = self.run_vm(4)
        g = self.globals_of(out)
        self.assertEqual(g[where][2], '1111')
        self.assertIn('1 ai', ' '.join(l for l in out if l.split()[1:2] == ['ai']))
        self.assertEqual(float(g[posx][3]), 123.5)
        # from the third frame in the room "Test Room": the cell changed, so the script reads 2 (+10 +100)
        room = self.prog.data.interior_numbers['test room']
        g = self.globals_of(self.run_vm(4, env={'ROOM': str(room)}))
        self.assertEqual(g[where][2], '1112')

    def test_the_players_position_cell_reaches_the_host(self):
        moves = [l.split() for l in self.run_vm(4) if l.split()[1:2] == ['move']]
        room = str(self.prog.strings.index['ri0123456789'])
        self.assertEqual(moves, [['1', 'move', '2', room, '975.000', '2000.000', '-33.125', '0.0'],
                                 ['1', 'move', '1', '65535', '100.000', '200.000', '300.000', '0.0']])

    def test_cell_changed_scripts_run_once_more_after_the_change(self):
        # "if ( CellChanged == 0 )": the marker's loop starts on the run after the one that read 1 (the harness
        # reports no sound playing, so it asks again on every run after that: it acted)
        drip = str(self.index('sounds', 'drip'))
        starts = [int(l.split()[0]) for l in self.run_vm(4) if l.split()[1:2] == ['sound'] and l.split()[4] == drip]
        self.assertEqual(starts, [2, 3, 4])

    def test_not_yet_calls_are_counted_and_handed_to_the_host(self):
        from mwscript.functions import FUNCTION_NUMBERS
        travel = FUNCTION_NUMBERS['aitravel']
        out = self.run_vm(4)
        calls = [l.split()[1:] for l in out if l.split()[1:3] == ['call', str(travel)]]
        self.assertTrue(calls, out)
        self.assertEqual(calls[0], ['call', str(travel), '3', '100', '5', '0', 'strings', '0'])
        counted = {int(l.split()[1]): l.split() for l in out if l.startswith('function')}
        self.assertEqual(int(counted[travel][2]), len(calls))
        self.assertEqual(int(counted[travel][3]), self.prog.strings.index['aitravel'])
        travel_line = str(self.prog.strings.index['aitravel'])
        self.assertEqual(len([l for l in out if l.split()[1:3] == ['notyet', travel_line]]), 1)    # logged once
        # carried out by number (the host answers): no log, the host count instead
        out = self.run_vm(4, env={'CALLS': str(travel)})
        self.assertFalse([l for l in out if l.split()[1:3] == ['notyet', travel_line]], out)
        stats = next(l for l in out if l.startswith('stats')).split()
        self.assertEqual(int(stats[14]), len(calls))


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
