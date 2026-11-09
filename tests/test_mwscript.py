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


def cell_interior(name, refs=()):
    parts = [sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0))]
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
COE 100 5
COE 100 5
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
SetWaterLevel 0.5
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
    # v0.0.57: the player's standing through the host's call() (functions.HOST); never placed, compiled only
    'StandingUser': '''Begin StandingUser
short r
if ( GetPCCrimeLevel > 1000 )
    ModPCCrimeLevel -50
endif
set r to GetPCRank "Mages Guild"
if ( r < 2 )
    PCRaiseRank "Mages Guild"
endif
if ( player->GetRace "Dark Elf" == 1 )
    ModPCFacRep 5 "Mages Guild"
endif
AddTopic "little secret"
AddTopic "no such topic"
End''',
    # v0.0.57: Cast of a cure on the player is carried out; any other Cast stays not yet
    'CastUser': '''Begin CastUser
short r
Cast "Cure Blight Disease" player
Cast "Fireball" player
Cast "shrine test sp" player
if ( player->GetEffect sEffectFortifyAttribute == 1 )
    set r to 1
endif
End''',
    'StandingReader': '''Begin StandingReader
short r
set r to GetPCRank "Mages Guild"
End''',
    # v0.0.62 (MWSCRIPT-SMALL-FUNCTIONS-62): the small functions through the host's call(); never placed, compiled only
    'SmallUser': '''Begin SmallUser
float a
short r
set a to ( "chime_obj"->GetAngle Z )
SetAngle, X, a
"chime_obj"->Move y 10
MoveWorld z -70
SetPos z 100.5
SetAtStart
Face 10 20 30
if ( GetDetected Player == 1 )
    set r to 1
elseif ( GetLOS "chime_obj" == 1 )
    set r to 2
elseif ( GetInterior )
    set r to 3
elseif ( GetCurrentWeather >= 5 )
    set r to 4
elseif ( OnKnockout == 1 )
    WakeUpPC
endif
RotateWorld z 90
if ( player->GetWeaponDrawn == 1 )
    if ( GetPCSneaking )
        SetDelete 1
    endif
endif
End''',
    'SmallReader': '''Begin SmallReader
short r
set r to GetInterior
End''',
    # CRIME-59 (CRIME-FINE-GOLD-NOT-TAKEN-62): the guards' fine answer, a function call in an explicit reference's count
    'FineUser': '''Begin FineUser
Player->RemoveItem Gold_001 GetPCCrimeLevel
SetPCCrimeLevel 0
PayFine
End''',
    # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): the fades, the forced sneak and the resistances; never placed
    'GapUser': '''Begin GapUser
short r
FadeOut 2
FadeIn 1.5
FadeTo 50 3
"chime_obj"->ForceSneak
set r to ( "chime_obj"->GetForceSneak )
ClearForceSneak
ModResistFire 100
SetResistFrost 40
set r to GetResistShock
set r to ( "chime_obj"->GetResistParalysis )
if ( ( player->HasSoulGem "skink" ) > 0 )
    player->RemoveSoulGem "skink" 2
endif
HurtStandingActor 20
if ( ( "chime_obj"->GetHealth ) < 1 )
    "chime_obj"->Resurrect
endif
End''',
    # v0.0.63 (MWSCRIPT-GAPS-63): the moon's colour, an item the player has equipped, the forced run; never placed
    'GapUser63': '''Begin GapUser63
short r
TurnMoonRed
if ( player->HasItemEquipped "steel longbow_carnius" == 1 )
    TurnMoonWhite
endif
"chime_obj"->ForceRun
set r to ( "chime_obj"->GetForceRun )
player->ClearForceRun
End''',
    # v0.0.63 (MWSCRIPT-GAPS-63, batch 2): a trap's explosion, an attacked actor, a spell's effects, an NPC's gear
    'GapUser63b': '''Begin GapUser63b
short r
if ( GetAttacked == 1 )
    ExplodeSpell "proj_trap_spell"
endif
set r to ( player->GetSpellEffects "proj_trap_spell" )
set r to ( "chime_obj"->HasItemEquipped "iron dagger" )
End''',
    # v0.0.63 (MWSCRIPT-GAPS-63, batch 3): the werewolf set, the travel read and the scale
    'GapUser63c': '''Begin GapUser63c
short r
float s
if ( GetPCTraveling == 0 )
    if ( Player->IsWerewolf == 0 )
        Player->BecomeWerewolf
        Player->SetWerewolfAcrobatics
    endif
endif
if ( GetWerewolfKills > 0 )
    Player->UndoWerewolf
endif
SetScale 1.5
ModScale 0.25
set s to GetScale
End''',
    # CELL-CHANGES-59 slice 5: a global script that starts another one and stops itself (never placed: the harness
    # starts it as a start script); the other one counts its own runs
    'Starter': '''Begin Starter
short phase
set phase to phase + 1
if ( phase == 1 )
    StartScript GlobalCounter
endif
if ( phase >= 3 )
    StopScript Starter
endif
End''',
    'GlobalCounter': '''Begin GlobalCounter
short ticks
set ticks to ticks + 1
set Counter to Counter
End''',
}


# a dialogue result script on the Quiet object (its local done): run through the DRSC row (DIALOGUE-COMPLETE-58)
RESULT_TEXT = 'set done to 7' + chr(13) + chr(10) + 'Choice ' + chr(34) + 'A' + chr(34) + ' 3'


def master_bytes(scripts=SCRIPTS, records=(), room_refs=()):
    """RECORDS: more records before the cells; ROOM_REFS: references placed in Test Room."""
    out = [record('TES3', sub('HEDR', b'\0' * 300))]
    out += [glob('QuestFlag', 's', 0), glob('Counter', 'l', 0), glob('Fraction', 'f', 1.5), glob('Where', 'l', 0),
            glob('PosX', 'f', 0)]
    out += [record('REGN', sub('NAME', 'Bitter Coast Region'), sub('FNAM', 'Bitter Coast Region'))]
    out += [soun('Cave Wind', 'Fx\\envrn\\cave_wind.wav', 128, 10, 40), soun('Chime', 'Fx\\chime.wav'),
            soun('Drip', 'Fx\\drip.wav')]
    # a shrine blessing: Fortify Strength 10 for 60 s, Restore Health 5-15 at once (ENAM: effect, skill, attribute,
    # range, area, duration, low, high)
    out += [record('SPEL', sub('NAME', 'shrine test sp'), sub('SPDT', struct.pack('<3i', 0, 0, 0)),
                   sub('ENAM', struct.pack('<hbbiiiii', 79, -1, 0, 0, 0, 60, 10, 10)),
                   sub('ENAM', struct.pack('<hbbiiiii', 75, -1, -1, 0, 0, 0, 5, 15)),
                   sub('ENAM', struct.pack('<hbbiiiii', 69, -1, -1, 0, 0, 0, 0, 0)),
                   sub('ENAM', struct.pack('<hbbiiiii', 27, -1, -1, 0, 0, 3, 2, 2)))]
    out += [record('DIAL', sub('NAME', 'Little Secret'), sub('DATA', b'\0')),
            record('INFO', sub('INAM', '1'), sub('ONAM', 'quiet_obj'), sub('NAME', 'A secret.'),
                   sub('BNAM', RESULT_TEXT)),
            record('DIAL', sub('NAME', 'background'), sub('DATA', b'\0')),
            record('DIAL', sub('NAME', 'A Journal'), sub('DATA', b'\x04'))]
    out += [scpt(name, text) for name, text in scripts.items()]
    out += [acti('marker_wind', 'AmbientWind'), acti('chime_obj', 'TimerChime'), acti('quiet_obj', 'Quiet'),
            acti('notyet_obj', 'NotYetUser'), acti('loop_obj', 'Looper'), acti('cg_obj', 'chargenTest'),
            acti('inert_obj', 'Inert'), acti('gate_obj', 'GateScript'), acti('actor_obj', 'ActorUser'),
            acti('cell_obj', 'CellUser'), acti('drip_obj', 'MarkerZero')]
    out += list(records)
    out.append(cell_exterior(0, 0, [(101, 'marker_wind', (100, 200, 0)), (102, 'chime_obj', (400, 0, 0)),
                                    (103, 'quiet_obj', (0, 0, 0)), (104, 'notyet_obj', (8, 8, 0)),
                                    (105, 'loop_obj', (16, 16, 0)), (106, 'cg_obj', (0, 0, 0)),
                                    (107, 'inert_obj', (0, 0, 0)), (108, 'gate_obj', (0, 0, 0)),
                                    (109, 'actor_obj', (0, 0, 0)), (110, 'cell_obj', (0, 0, 0)),
                                    (111, 'drip_obj', (0, 0, 0))]))
    out += [cell_exterior(-2, -9, [], 'Seyda Neen', 'bitter coast region'),
            cell_exterior(-3, -9, [], '', 'bitter coast region'), cell_interior('Test Room', room_refs),
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


class SeenScriptTests(unittest.TestCase):
    """MWSCRIPT-INERT-SEEN-62: a script whose only effect is a message box, its object's use taken over (OnActivate),
    or a local the speaker's dialogue filters read is seen in the game, so it is not inert and its object binds."""

    def test_message_box_activation_and_dialogue_locals_are_seen(self):
        scripts = dict(SCRIPTS,
                       BoxOnUse='Begin BoxOnUse\nif ( OnActivate == 1 )\n    MessageBox "This door is blocked."\n'
                                'endif\nEnd BoxOnUse\n',
                       KeepUse='Begin KeepUse\nif ( OnActivate == 1 )\n    return\nendif\nEnd KeepUse\n',
                       DeedFlag='Begin DeedFlag\nshort hasDeed\nshort noLore\n'
                                'if ( GetItemCount "plain_misc" > 0 )\n    set hasDeed to 1\nendif\nEnd DeedFlag\n',
                       QuietFlag='Begin QuietFlag\nshort unread\nset unread to 1\nEnd QuietFlag\n',
                       OnlyLocals='Begin OnlyLocals\nshort noLore\nEnd OnlyLocals\n')
        records = [record('MISC', sub('NAME', 'plain_misc')),
                   record('DOOR', sub('NAME', 'box_door'), sub('SCRI', 'BoxOnUse')),
                   record('MISC', sub('NAME', 'keep_misc'), sub('SCRI', 'KeepUse')),
                   record('NPC_', sub('NAME', 'deed_npc'), sub('SCRI', 'DeedFlag')),
                   record('NPC_', sub('NAME', 'quiet_npc'), sub('SCRI', 'QuietFlag')),
                   record('NPC_', sub('NAME', 'lore_npc'), sub('SCRI', 'OnlyLocals')),
                   # the dialogue filter Local hasDeed == 1 and NotLocal noLore (SCVR: index, type, function, op)
                   record('DIAL', sub('NAME', 'land deed'), sub('DATA', b'\0')),
                   record('INFO', sub('INAM', '7'), sub('NAME', 'You have the deed.'),
                          sub('SCVR', '03X00hasDeed'), sub('INTV', struct.pack('<i', 1)),
                          sub('SCVR', '1CX00noLore'), sub('INTV', struct.pack('<i', 0)))]
        d = Path(tempfile.mkdtemp(prefix='aw-mwscript-seen-'))
        try:
            (d / 'Morrowind.esm').write_bytes(master_bytes(scripts, records, room_refs=[
                (401, 'box_door', (0, 0, 0)), (402, 'keep_misc', (0, 0, 0)), (403, 'deed_npc', (0, 0, 0)),
                (404, 'quiet_npc', (0, 0, 0)), (405, 'lore_npc', (0, 0, 0))]))
            data = GameData().load(d)
            prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
            binds = bindings(prog, compiled)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(data.dialogue_locals, {'hasdeed', 'nolore'})
        names = {c.name: c for c in compiled}
        for seen in ('BoxOnUse', 'KeepUse', 'DeedFlag'):
            self.assertFalse(names[seen].flags & SCRIPT_INERT, seen)
        for unseen in ('QuietFlag', 'OnlyLocals'):      # a local nothing reads; a declaration alone sets nothing
            self.assertTrue(names[unseen].flags & SCRIPT_INERT, unseen)
        bound = {b['reference'] for b in binds}
        self.assertTrue({401, 402, 403} <= bound)
        self.assertFalse({404, 405} & bound)


class WeatherCallTests(unittest.TestCase):
    """MWSCRIPT-COMPLETE-LANDMARK: ChangeWeather and ModRegion go to the host with the region's catalogue index (the
    sorted Morrowind.esm region ids) first; a region the image has not is no code (OpenMW finds no such region)."""

    def test_the_region_is_worked_out_at_build_time(self):
        from mwscript.awms import decode
        from mwscript.functions import FUNCTION_NUMBERS, HOST, HOST_EFFECTS
        text = ('Begin WeatherEnd\nModRegion "Bitter Coast Region" 50 50 0 0 0 0 0 0\n'
                'ChangeWeather "bitter coast region" 0\nChangeWeather "Mournhold Region" 1\n'
                'ModRegion "Mournhold Region" 100 0 0 0 0 0 0 0\nStopScript WeatherEnd\nEnd WeatherEnd\n')
        records = [record('REGN', sub('NAME', 'Ascadian Isles Region'), sub('FNAM', 'Ascadian Isles Region'))]
        d = Path(tempfile.mkdtemp(prefix='aw-mwscript-weather-'))
        try:
            (d / 'Morrowind.esm').write_bytes(master_bytes(dict(SCRIPTS, WeatherEnd=text), records))
            data = GameData().load(d)
            prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(data.base_regions, {'ascadian isles region', 'bitter coast region'})
        self.assertTrue({'changeweather', 'modregion'} <= HOST & HOST_EFFECTS)
        c = next(c for c in compiled if c.name == 'WeatherEnd')
        self.assertEqual(c.notyet, [])
        ops = list(decode(c.code))
        calls = [(i, a) for i, (_, n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual([a[0] for _, a in calls], [FUNCTION_NUMBERS['modregion'], FUNCTION_NUMBERS['changeweather']])
        (m, mod), (k, change) = calls
        self.assertEqual(mod[2] & 0x1F, 9)             # the region's index and eight chances
        self.assertEqual(change[2] & 0x1F, 2)          # the region's index and the weather
        pushes = [(n, a) for _, n, a in ops[m - 9:m]]
        self.assertEqual(pushes[0], ('PUSHB', [1]))    # bitter coast region: second of the sorted ids
        self.assertEqual(ops[k - 2][1:], ('PUSHB', [1]))
        self.assertTrue(any('a region the image has not' in w for w in c.warnings))
        self.assertEqual(len(calls), 2)                # Mournhold's calls: no code


class HeldItemBindingTests(unittest.TestCase):
    """MWSCRIPT-INVENTORY-HITONME-62: the scripts of items a placed container holds (OpenMW 0.51 localscripts.cpp
    addCell: the active cells' containers' and actors' items run their scripts) are BIND_HELD rows at the holder."""

    def test_a_container_s_scripted_items_bind_at_the_container(self):
        from mwscript.compiler import BIND_HELD, BIND_INTERIOR, BIND_EDICT, HELD_BIT, held_key
        held = ('Begin HeldItem\nshort OnPCEquip\nif ( OnPCEquip == 1 )\n    set QuestFlag to 1\nendif\n'
                'End HeldItem\n')
        other = 'Begin HeldOther\nset Counter to 2\nEnd HeldOther\n'

        def npco(count, ident):
            return sub('NPCO', struct.pack('<i', count) + ident.encode('cp1252').ljust(32, b'\0'))
        records = [record('MISC', sub('NAME', 'held_misc'), sub('SCRI', 'HeldItem')),
                   record('MISC', sub('NAME', 'held_two'), sub('SCRI', 'HeldOther')),
                   record('MISC', sub('NAME', 'plain_misc')),
                   record('CONT', sub('NAME', 'test_chest'), npco(2, 'held_misc'), npco(1, 'plain_misc'),
                          npco(1, 'held_misc'), npco(1, 'held_two')),
                   record('CONT', sub('NAME', 'empty_chest'))]
        d = Path(tempfile.mkdtemp(prefix='aw-mwscript-held-'))
        try:
            (d / 'Morrowind.esm').write_bytes(master_bytes(dict(SCRIPTS, HeldItem=held, HeldOther=other), records,
                                                           room_refs=[(301, 'test_chest', (40, 80, 0)),
                                                                      (302, 'empty_chest', (0, 0, 0))]))
            data = GameData().load(d)
            self.assertEqual(data.holdings['test_chest'], ['held_misc', 'plain_misc', 'held_misc', 'held_two'])
            prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
            binds = bindings(prog, compiled)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        rows = [b for b in binds if b['flags'] & BIND_HELD]
        self.assertEqual([b['reference'] for b in rows], [held_key(301, 0), held_key(301, 1)])
        self.assertEqual(held_key(301, 1), HELD_BIT | (1 << 24) | 301)
        self.assertEqual([prog.scripts.rows[b['script']]['name'] for b in rows], ['HeldItem', 'HeldOther'])
        for b in rows:
            self.assertEqual(b['flags'], BIND_HELD | BIND_INTERIOR | BIND_EDICT)
            self.assertEqual((b['holder'], b['position']), (301, [40, 80, 0]))
        self.assertEqual([b['reference'] for b in binds], sorted(b['reference'] for b in binds))
        self.assertGreater(binds[-1]['reference'], 0xFFFFFF)          # after every placed reference
        f = awms.read(awms.write(prog, compiled, binds)[0])
        self.assertEqual(f['BIND_rows'], len(binds))
        self.assertEqual(struct.unpack_from('>I', f['BIND'], 24 * (len(binds) - 1))[0], held_key(301, 1))
        with self.assertRaises(ValueError):
            held_key(0x1000000, 0)

    def test_the_engine_attaches_held_rows_at_the_holder_while_it_has_the_item(self):
        from mwscript.compiler import BIND_HELD, HELD_BIT
        src = ROOT / 'engine/aga/src'
        header = (src / 'aw_mwcode.h').read_text(encoding='utf-8')
        self.assertIn('#define AWB_HELD %d' % BIND_HELD, header)
        self.assertIn('#define AWB_HELD_BIT 0x%08xu' % HELD_BIT, header)
        host = (src / 'aw_mwhost.c').read_text(encoding='utf-8')
        attach = host[host.index('static void attach_map(void){'):]
        attach = attach[:attach.index('\n}\n')]
        self.assertIn('entity=entity_of_reference(AWB_HELD_HOLDER(ref));', attach)
        self.assertEqual(attach.count('held_attach('), 3)            # an edict holder, outdoors, a room's spot
        self.assertIn('if(held_attached_now>=HELD_MAX){held_over++;return -1;}', host)
        self.assertIn('held_recheck(script);', host[host.index('static void pcadd_flush(void){'):])
        self.assertIn('if(!global && AWB_HELD_KEY(reference))return;', host)
        vm = (src / 'aw_mwvm.c').read_text(encoding='utf-8')
        self.assertIn('if(AWB_HELD_KEY(in->reference)){in->flags=0;continue;}', vm)
        self.assertIn('if(!AWB_HELD_KEY(reference) && (p=park_slot(', vm)


class ResultKeyTests(unittest.TestCase):
    def test_two_texts_with_one_key_stop_the_build(self):
        # the engine tells result scripts apart by (hash, length): two different texts with one key are refused
        from mwscript.codegen import check_result_keys, CompileError
        same = [{'hash': 1, 'length': 3, 'text': b'abc'}, {'hash': 1, 'length': 3, 'text': b'abc'}]
        check_result_keys(same)                                    # one text twice (two speakers): fine
        with self.assertRaises(CompileError) as caught:
            check_result_keys([{'hash': 1, 'length': 3, 'text': b'abc'}, {'hash': 1, 'length': 3, 'text': b'xyz'}])
        self.assertIn("b'abc'", str(caught.exception))
        self.assertIn("b'xyz'", str(caught.exception))


class EngineLimitTests(unittest.TestCase):
    def test_builder_limits_are_the_engines(self):
        # MWSCRIPT-REFUSED-SCRIPT-COUNT-58: the builder refuses what the interpreter would refuse
        vm = (ROOT / 'engine/aga/src/aw_mwvm.c').read_text(encoding='utf-8')
        self.assertEqual(int(re.search(r'#define MAX_SCRIPTS (\d+)', vm).group(1)), awms.ENGINE_MAX_SCRIPTS)
        self.assertEqual(int(re.search(r'#define MAX_GLOBALS (\d+)', vm).group(1)), awms.ENGINE_MAX_GLOBALS)
        self.assertGreaterEqual(awms.ENGINE_MAX_SCRIPTS, 8618)    # v0.0.58-dev5's file with its dialogue scripts


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
    def test_dungeon_ambience_sounds_are_flagged(self):
        """TOMB-MUSIC-OVER-AMBIENT-60: a sound marker's loop of a dungeon ambience (here Cave Wind) carries SNDS flag 2
        beside the mapped flag; other sounds (Chime, Drip) do not. The engine rests the exploration music on it."""
        prog, compiled, binds, data = program()
        raw, _ = awms.write(prog, compiled, binds)
        sections = struct.unpack_from('>H', raw, 6)[0]
        table = {raw[16 + 16 * i:20 + 16 * i]: struct.unpack_from('>III', raw, 20 + 16 * i) for i in range(sections)}
        offset, rows, size = table[b'SNDS']
        self.assertEqual(size, 18 * rows)
        flags = {name: raw[offset + 18 * i + 11] for name, i in prog.sounds.index.items()}
        self.assertEqual(flags['cave wind'] & awms.SOUND_AMBIENCE, awms.SOUND_AMBIENCE)
        self.assertFalse(flags['chime'] & awms.SOUND_AMBIENCE or flags['drip'] & awms.SOUND_AMBIENCE)
        self.assertEqual(awms.AMBIENCE_SOUNDS, {'haunted', 'spirit ambient voices', 'cave drip', 'cave wind'})
        vm = (ROOT / 'engine/aga/src/aw_mwvm.c').read_text(encoding='utf-8')
        self.assertIn('(vm.snds[18*k+11]&3)==3', vm)   # mapped and an ambience

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
        self.assertEqual(calls[0][0], FUNCTION_NUMBERS['coe'])     # v0.0.62: FadeTo is carried out now
        self.assertEqual(prog.strings.rows[calls[0][1]], 'coe')
        self.assertEqual(calls[0][2] & 0x1F, 2)                    # two numbers: 100 5
        cell = names['CellUser']
        # PositionCell: the player's moves are worked out here; the player's into a room no list names stays not yet;
        # another object's goes to the host (v0.0.62): the same NOTYET form, not counted as not yet
        self.assertEqual([prog.strings.rows[a[1]] for _, n, a in awms.decode(cell.code) if n == 'NOTYET'],
                         ['positioncell', 'positioncell'])
        self.assertEqual(cell.notyet, ['positioncell'])
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

    def test_position_cell_of_an_actor(self):
        # v0.0.62 (MWSCRIPT-POSITIONCELL-ACTORS-62; OpenMW transformationextensions.cpp OpPositionCell): anything but
        # the player goes to the host with x, y, z in the destination's units (a room: its map's own, a recentred
        # room's offset first), Quake's yaw from the rotation in minutes of arc, the kind and the room's number; a
        # cell the game has not is no code (OpenMW does nothing); each actor a move may bring into a room is a VISI
        # row with its home room's map (the self form: the script's bearers)
        from mwscript.functions import FUNCTION_NUMBERS
        scripts = dict(SCRIPTS, MoverScript='''Begin MoverScript
"mover_npc"->PositionCell 4100 8000 -200 5400 "Test Room"
"mover_npc"->PositionCell 0 0 0 0 "No Such Place"
"mover_npc"->PositionCell 100 200 300 0 "Seyda Neen"
End''', SelfMover='''Begin SelfMover
PositionCell 8 8 8 60 "Another Room"
End''')
        extra = (record('NPC_', sub('NAME', 'mover_npc')), record('NPC_', sub('NAME', 'self_npc'), sub('SCRI', 'SelfMover')))
        tmp = Path(tempfile.mkdtemp(prefix='aw-mwscript-pc-'))
        try:
            (tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, extra, [(201, 'mover_npc', (0, 0, 0)),
                                                                              (202, 'self_npc', (0, 0, 0))]))
            data = GameData().load(tmp)
            prog, compiled = compile_program(data, MediaMap(data, catalogue(), SOUNDTRACK), rooms=ROOMS)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        names = {c.name: c for c in compiled}
        mover = names['MoverScript']
        self.assertEqual(mover.notyet, [])
        self.assertFalse(mover.flags & SCRIPT_NOTYET)
        self.assertTrue(any('No Such Place' in w for w in mover.warnings))
        ops = [(n, a) for _, n, a in awms.decode(mover.code)]
        calls = [k for k, (n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual(len(calls), 2)
        for k in calls:
            self.assertEqual(ops[k][1][0], FUNCTION_NUMBERS['positioncell'])
            self.assertEqual(ops[k][1][2] & 0x1F, 6)               # x, y, z, yaw, kind, number
            self.assertEqual(ops[k][1][3], 1)                      # the cell's name
        room = data.interior_numbers['test room']

        def pushed(k):
            out = []
            for n, a in ops[k - 6:k]:
                out.append(a[0])
            return out
        first = pushed(calls[0])
        self.assertEqual(first[:4], [1000.0, 2000.0, -50.0, 270.0])   # (x - 100) / 4, y / 4, z / 4; -90 degrees
        self.assertEqual(first[4:], [2, room])
        self.assertEqual(pushed(calls[1]), [100.0, 200.0, 300.0, 0.0, 1, 0])   # outdoors: the original's units
        self.assertEqual(ops[calls[0] - 7][0], 'REF')
        other = data.interior_numbers['another room']
        self.assertEqual(prog.visitors, {(room, 201): prog.strings.index['ri0123456789'],
                                         (other, 202): prog.strings.index['ri0123456789']})
        f = awms.read(awms.write(prog, compiled, bindings(prog))[0])
        self.assertEqual(f['VISI_rows'], 2)
        self.assertEqual(struct.unpack_from('>IIHH', f['VISI'], 0)[:2], tuple(sorted([(room, 201), (other, 202)])[0]))
        self.assertIn('VISI', awms.RESIDENT)
        self.assertEqual(names['SelfMover'].notyet, [])

    def test_the_placing_family(self):
        # v0.0.62 (MWSCRIPT-PLACE-OBJECTS-62; OpenMW transformationextensions.cpp OpPlaceAt, OpPlaceItem,
        # OpPlaceItemCell): an NPC or creature with a placed reference, or a carried item, goes to the host with its
        # PLAC row as the last number; a creature placed nowhere and an activator stay not yet; PlaceItemCell works
        # its cell out here (a room: the room map's units for an actor); the PLAC rows are every id a Place call
        # names, sorted, with the template (a room's reference first) and the record's script
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript.codegen import PLACE_KINDS
        scripts = dict(SCRIPTS, PlacerScript='''Begin PlacerScript
PlaceAtPC "summon_npc" 1 128 1
PlaceAtPC "lone_rat", 1, 256, 0
"cell_obj"->PlaceAtMe "summon_npc" 2 64 3
PlaceItem "shiny_coin" 100 200 300 90
PlaceItem "magic_glow" 1 2 3 0
PlaceItemCell "summon_npc" "Test Room" 4100 8000 -200 90
PlaceItemCell "summon_npc" "No Such Place" 0 0 0 0
"cell_obj"->Drop "shiny_coin" 2
Drop "magic_glow" 1
End''', SummonedScript='''Begin SummonedScript
short done
set done to 1
End''', EquipNote='''Begin EquipNote
short OnPCEquip
short PCSkipEquip
short button
short asked
if ( OnPCEquip == 1 )
    if ( asked == 0 )
        MessageBox "Wear it?" "Cancel" "OK"
        set asked to 1
    endif
    set button to GetButtonPressed
    if ( button == 1 )
        set OnPCEquip to 0
        set asked to 0
    endif
endif
End''')
        extra = (record('NPC_', sub('NAME', 'summon_npc'), sub('SCRI', 'SummonedScript')),
                 record('CREA', sub('NAME', 'lone_rat')), record('MISC', sub('NAME', 'shiny_coin')),
                 acti('magic_glow', ''), record('WEAP', sub('NAME', 'note_dagger'), sub('SCRI', 'EquipNote')))
        tmp = Path(tempfile.mkdtemp(prefix='aw-mwscript-place-'))
        try:
            (tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, extra, [(301, 'summon_npc', (0, 0, 0))]))
            data = GameData().load(tmp)
            prog, compiled = compile_program(data, MediaMap(data, catalogue(), SOUNDTRACK), rooms=ROOMS)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        names = {c.name: c for c in compiled}
        placer = names['PlacerScript']
        # v0.0.62: the rat placed nowhere is made from its actor table base (MWSCRIPT-GAP-FUNCTIONS-62); the activator
        # with no placed reference (no template) stays not yet, placed and dropped
        self.assertEqual(sorted(placer.notyet), ['drop', 'placeitem'])
        self.assertTrue(any('No Such Place' in w for w in placer.warnings))
        rows = prog.place_rows()
        self.assertEqual([r['key'] for r in rows], ['lone_rat', 'magic_glow', 'shiny_coin', 'summon_npc'])
        npc = rows[3]
        self.assertEqual((npc['kind'], npc['template'], npc['carried']), (PLACE_KINDS['actor'], 301, True))
        self.assertEqual(npc['home'], prog.strings.index['ri0123456789'])
        self.assertEqual(npc['script'], prog.scripts.index['summonedscript'])
        self.assertEqual((rows[0]['carried'], rows[1]['kind'], rows[1]['carried'], rows[2]['kind']),
                         (True, PLACE_KINDS['other'], False, PLACE_KINDS['item']))
        ops = [(n, a) for _, n, a in awms.decode(placer.code)]
        calls = [(k, a) for k, (n, a) in enumerate(ops) if n == 'NOTYET' and
                 a[0] in (FUNCTION_NUMBERS['placeatpc'], FUNCTION_NUMBERS['placeatme'], FUNCTION_NUMBERS['placeitem'],
                          FUNCTION_NUMBERS['placeitemcell'])]

        def pushed(k, count):
            # the constants pushed before op K (conversions between them skipped)
            out = []
            while len(out) < count:
                k -= 1
                if ops[k][0].startswith('PUSH'):
                    out.insert(0, ops[k][1][0])
            return out

        def before(k):
            # the nearest REF or NOTYET before op K
            while ops[k - 1][0] not in ('REF', 'NOTYET'):
                k -= 1
            return ops[k - 1][0]
        by_fn = {}
        for k, a in calls:
            by_fn.setdefault(a[0], []).append((k, a))
        at_pc = by_fn[FUNCTION_NUMBERS['placeatpc']]
        self.assertEqual(at_pc[0][1][2] & 0x1F, 4)                 # count, distance, direction, row
        self.assertEqual(pushed(at_pc[0][0], 4), [1, 128.0, 1, 3])
        self.assertEqual(at_pc[1][1][2] & 0x1F, 4)                 # the rat: from its base, with its row (v0.0.62)
        self.assertEqual(pushed(at_pc[1][0], 4), [1, 256.0, 0, 0])
        at_me = by_fn[FUNCTION_NUMBERS['placeatme']][0]
        self.assertEqual(pushed(at_me[0], 4), [2, 64.0, 3, 3])
        self.assertEqual(before(at_me[0]), 'REF')
        item = [c for c in by_fn[FUNCTION_NUMBERS['placeitem']] if c[1][2] & 0x1F == 5]
        self.assertEqual(pushed(item[0][0], 5), [100.0, 200.0, 300.0, 90.0, 2])
        cell = by_fn[FUNCTION_NUMBERS['placeitemcell']][0]
        self.assertEqual(cell[1][2] & 0x1F, 7)
        room = data.interior_numbers['test room']
        self.assertEqual(pushed(cell[0], 7), [1000.0, 2000.0, -50.0, 270.0, 2, room, 3])
        # v0.0.62: Drop of the coin on the object REF names: count, its AITM row, its PLAC row (2); the activator's
        # Drop stays not yet (its own number only)
        drops = [(k, a) for k, (n, a) in enumerate(ops) if n == 'NOTYET' and a[0] == FUNCTION_NUMBERS['drop']]
        self.assertEqual([a[2] & 0x1F for _, a in drops], [3, 1])
        self.assertEqual(pushed(drops[0][0], 3), [2, prog.actors.item('shiny_coin'), 2])
        self.assertEqual(before(drops[0][0]), 'REF')
        f = awms.read(awms.write(prog, compiled, bindings(prog))[0])
        self.assertEqual(f['PLAC_rows'], 4)
        self.assertEqual(struct.unpack_from('>HHIHBB', f['PLAC'], 36),
                         (npc['id'], npc['home'], 301, npc['script'], 0, 1))
        self.assertIn('PLAC', awms.RESIDENT)
        # the placed record's own script is compiled (it runs on the placed actor's instance)
        self.assertIn('SummonedScript', names)
        # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): the dagger whose script declares OnPCEquip and PCSkipEquip is an EQUP
        # row (its script, the two slots: 0 and 1); its message box with buttons and GetButtonPressed run whole
        equips = prog.equip_rows()
        self.assertEqual([(r[0], r[2], r[3], r[4]) for r in equips],
                         [('note_dagger', prog.scripts.index['equipnote'], 0, 1)])
        self.assertEqual(names['EquipNote'].notyet, [])
        self.assertEqual(f['EQUP_rows'], 1)
        self.assertEqual(struct.unpack('>HHBBH', f['EQUP']), (prog.string('note_dagger'),
                                                             prog.scripts.index['equipnote'], 0, 1, 0))
        self.assertIn('EQUP', awms.RESIDENT)

    def test_ai_follow_cell_and_escort(self):
        # v0.0.62 (MWSCRIPT-POSITIONCELL-ACTORS-62; OpenMW aiextensions.cpp OpAiFollowCell, OpAiEscort, OpAiEscortCell):
        # the host gets duration, x, y, z (a room: its map's own units, as PositionCell's), the kind and the room's
        # number, the target and the cell; the reset argument is not passed; an AIEscortCell into a cell the game has
        # not is no code; a follower of the player is a VISI row of any room (0xFFFFFFFF) with its home room's map
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript.codegen import VISI_ANY
        scripts = dict(SCRIPTS, EscortScript='''Begin EscortScript
"guide_npc"->AIFollowCell Player "Test Room" 0 4100 8000 -200 0
"guide_npc"->AIEscortCell Player "Seyda Neen" 2 100 200 300
"guide_npc"->AIEscortCell Player "No Such Place" 0 1 2 3
"guide_npc"->AIEscort Player 0 10 20 30 0
AIFollowCell, Player, "Nowhere At All", 0, 1, 2, 3, 0
End''')
        extra = (record('NPC_', sub('NAME', 'guide_npc'), sub('SCRI', 'EscortScript')),)
        tmp = Path(tempfile.mkdtemp(prefix='aw-mwscript-ai-'))
        try:
            (tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, extra, [(301, 'guide_npc', (0, 0, 0))]))
            data = GameData().load(tmp)
            prog, compiled = compile_program(data, MediaMap(data, catalogue(), SOUNDTRACK), rooms=ROOMS)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        c = {x.name: x for x in compiled}['EscortScript']
        self.assertEqual(c.notyet, [])
        self.assertTrue(any('No Such Place' in w for w in c.warnings))
        ops = [(n, a) for _, n, a in awms.decode(c.code)]
        calls = [k for k, (n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual([ops[k][1][0] for k in calls], [FUNCTION_NUMBERS['aifollowcell'], FUNCTION_NUMBERS['aiescortcell'],
                                                         FUNCTION_NUMBERS['aiescort'], FUNCTION_NUMBERS['aifollowcell']])
        room = data.interior_numbers['test room']

        def pushed(k, n):
            return [a[0] for _, a in ops[k - n:k]]
        self.assertEqual(ops[calls[0]][1][2] & 0x1F, 6)
        self.assertEqual(ops[calls[0]][1][3], 2)                      # the target and the cell
        self.assertEqual(pushed(calls[0], 6), [0.0, 1000.0, 2000.0, -50.0, 2, room])
        self.assertEqual(pushed(calls[1], 6), [2.0, 100.0, 200.0, 300.0, 1, 0])   # outdoors: the original's units
        self.assertEqual(ops[calls[2]][1][2] & 0x1F, 5)               # AIEscort: duration x y z and the reset
        self.assertEqual(pushed(calls[3], 6), [0.0, 1.0, 2.0, 3.0, 1, 0])   # a cell the game has not: never done
        self.assertEqual(prog.visitors, {(VISI_ANY, 301): prog.strings.index['ri0123456789']})
        f = awms.read(awms.write(prog, compiled, bindings(prog))[0])
        self.assertEqual(struct.unpack_from('>IIHH', f['VISI'], 0)[:2], (VISI_ANY, 301))

    def test_the_players_standing_goes_through_the_host_call(self):
        # v0.0.57 (functions.HOST): crime level, faction rank, faction reputation and GetRace keep the import route's
        # form (no new opcode) but the script is not "not yet"; a reference becomes a REF before the call, the
        # numbers arrive as the function declares them (ModPCCrimeLevel a fraction, ModPCFacRep a whole number)
        from mwscript.functions import FUNCTION_NUMBERS, HOST
        prog, compiled, _, _ = program()
        names = {c.name: c for c in compiled}
        user = names['StandingUser']
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertFalse(user.flags & SCRIPT_VOLATILE)
        self.assertFalse(user.flags & SCRIPT_INERT)              # it changes the standing
        self.assertEqual(user.notyet, [])
        self.assertTrue(names['StandingReader'].flags & SCRIPT_INERT)   # a read alone is seen nowhere
        ops = [(n, a) for _, n, a in awms.decode(user.code)]
        calls = [a for n, a in ops if n == 'NOTYET']
        self.assertEqual([a[0] for a in calls], [FUNCTION_NUMBERS[n] for n in (
            'getpccrimelevel', 'modpccrimelevel', 'getpcrank', 'pcraiserank', 'getrace', 'modpcfacrep', 'addtopic')])
        # AddTopic: the topic's TOPC row (sorted: background 0, little secret 1) as its number; an unknown topic
        # compiles to nothing, with a warning; the journal DIAL is no topic
        i = next(k for k, (n, a) in enumerate(ops) if n == 'NOTYET' and a[0] == FUNCTION_NUMBERS['addtopic'])
        self.assertEqual(ops[i - 1], ('PUSHB', [1]))
        self.assertTrue(any('unknown topic' in w for w in user.warnings))
        f = awms.read(awms.write(prog, compiled, bindings(prog))[0])
        self.assertEqual(f['TOPC_rows'], 2)
        self.assertEqual([prog.strings.rows[struct.unpack_from('>H', f['TOPC'], 2 * k)[0]] for k in range(2)],
                         ['background', 'Little Secret'])
        i = next(k for k, (n, a) in enumerate(ops) if n == 'NOTYET' and a[0] == FUNCTION_NUMBERS['getrace'])
        self.assertEqual(ops[i - 1], ('REF', [0xFFFF]))          # player->GetRace: the player as the target
        self.assertEqual(prog.strings.rows[calls[4][4]], 'Dark Elf')
        self.assertEqual(calls[4][3], 1)                          # one string, no reference id among them
        before = ops[[k for k, (n, a) in enumerate(ops) if n == 'NOTYET'][1] - 1]
        self.assertIn(before[0], ('PUSHF', 'I2F'))                # -50 as a fraction
        cast = names['CastUser']
        self.assertEqual(cast.notyet, ['cast'])                   # Fireball waits; the cure and the blessing run
        self.assertEqual(len([a for _, n, a in awms.decode(cast.code) if n == 'NOTYET']), 4)
        ge = [(n, a) for _, n, a in awms.decode(cast.code)]
        k = next(i for i, (n, a) in enumerate(ge) if n == 'NOTYET' and a[0] == FUNCTION_NUMBERS['geteffect'])
        self.assertEqual(ge[k - 1], ('PUSHB', [79]))               # sEffectFortifyAttribute: effect 79
        self.assertEqual(ge[k - 2], ('REF', [0xFFFF]))
        # with a cure (kind 4, common disease) and Poison landing as Damage Health
        self.assertEqual(prog.spfx.rows[0]['effects'], [(3, 0, 60, 10, 10), (2, 35, 0, 5, 15), (4, 3, 0, 0, 0),
                                                        (1, 35, 3, 2, 2)])
        f = awms.read(awms.write(prog, compiled, bindings(prog))[0])
        self.assertEqual(f['SPFX_rows'], 1)
        self.assertEqual(len(f['SPFX']), 4 + 32)
        self.assertIn('SPFX', awms.RESIDENT)
        header = (ROOT / 'engine/aga/src/aw_mwcode.h').read_text(encoding='utf-8')
        found = {m.group(1).lower(): int(m.group(2)) for m in re.finditer(r'#define AWF_(\w+) (\d+)', header)}
        self.assertEqual(found, {n: FUNCTION_NUMBERS[n] for n in HOST})

    def test_a_blessing_of_passive_effects_is_carried(self):
        # MWSCRIPT-UNPLACED-ATTACH-62 (the shrines): Shield, a resistance, Levitate and Fortify Attack land by their
        # effect number (SPFX kind 5); a spell with an action effect (Mark) stays "not yet"
        prog, _, _, _ = program()
        spel = prog.data.records['SPEL']

        def enam(number, duration, low, high):
            return ('ENAM', struct.pack('<hbbiiiii', number, -1, -1, 0, 0, duration, low, high))
        spel['blessing test sp'] = [enam(3, 2880, 10, 10), enam(92, 2880, 20, 20), enam(10, 1440, 100, 100),
                                    enam(117, 2880, 5, 5)]
        spel['mark test sp'] = [enam(3, 60, 5, 5), enam(60, 0, 0, 0)]
        row = prog.spell_effects('Blessing Test SP')
        self.assertIsNotNone(row)
        self.assertEqual(prog.spfx.rows[row]['effects'], [(5, 3, 2880, 10, 10), (5, 92, 2880, 20, 20),
                                                          (5, 10, 1440, 100, 100), (5, 117, 2880, 5, 5)])
        self.assertIsNone(prog.spell_effects('mark test sp'))
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('if(x[0]==5)', host)                        # the engine lands kind 5 by its number

    def test_a_call_in_a_referenced_count_keeps_the_reference(self):
        # CRIME-FINE-GOLD-NOT-TAKEN-62: "Player->RemoveItem Gold_001 GetPCCrimeLevel": the count's call (which resets
        # the target) comes first, then the player as the target, then the item change; PayFine is carried out
        prog, compiled, _, _ = program()
        user = {c.name: c for c in compiled}['FineUser']
        ops = [(n, a) for _, n, a in awms.decode(user.code)]
        names = [n for n, _ in ops]
        k = names.index('ITEM')
        self.assertEqual(ops[k - 1], ('REF', [0xFFFF]))            # the player, right before the change
        self.assertIn('NOTYET', names[:k - 1])                     # GetPCCrimeLevel before the reference
        self.assertEqual(user.notyet, [])

    def test_fades_forced_sneak_and_resistances_go_through_the_host_call(self):
        # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): carried out by the host (not "not yet"), in order, with their numbers;
        # the resistances' reads make the script VOLATILE (an effect lands or ends without the state generation)
        from mwscript.functions import FUNCTION_NUMBERS
        prog, compiled, _, _ = program()
        user = {c.name: c for c in compiled}['GapUser']
        self.assertEqual(user.notyet, [])
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertTrue(user.flags & SCRIPT_VOLATILE)
        self.assertFalse(user.flags & SCRIPT_INERT)
        calls = [a for _, n, a in awms.decode(user.code) if n == 'NOTYET']
        self.assertEqual([a[0] for a in calls], [FUNCTION_NUMBERS[n] for n in (
            'fadeout', 'fadein', 'fadeto', 'forcesneak', 'getforcesneak', 'clearforcesneak', 'modresistfire',
            'setresistfrost', 'getresistshock', 'getresistparalysis', 'hassoulgem', 'removesoulgem', 'hurtstandingactor', 'resurrect')])

    def test_moon_equipped_and_forced_run_go_through_the_host_call(self):
        # v0.0.63 (MWSCRIPT-GAPS-63): TurnMoonRed / TurnMoonWhite, HasItemEquipped and the forced run are carried out
        # by the host (not "not yet"), in order; HasItemEquipped's read makes the script VOLATILE (equipping does not
        # move the state generation); the engine has a case for each and keeps the run in the AWRN save block
        from mwscript.functions import FUNCTION_NUMBERS
        prog, compiled, _, _ = program()
        user = {c.name: c for c in compiled}['GapUser63']
        self.assertEqual(user.notyet, [])
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertTrue(user.flags & SCRIPT_VOLATILE)
        self.assertFalse(user.flags & SCRIPT_INERT)
        ops = [(n, a) for _, n, a in awms.decode(user.code)]
        calls = [(k, a) for k, (n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual([a[0] for _, a in calls], [FUNCTION_NUMBERS[n] for n in (
            'turnmoonred', 'hasitemequipped', 'turnmoonwhite', 'forcerun', 'getforcerun', 'clearforcerun')])
        self.assertIn(('REF', [0xFFFF]), ops[calls[0][0] + 1:calls[1][0]])   # player->HasItemEquipped (then its row)
        self.assertEqual([prog.strings.rows[s] for s in calls[1][1][4:]], ['steel longbow_carnius'])
        self.assertEqual(ops[calls[5][0] - 1], ('REF', [0xFFFF]))   # player->ClearForceRun
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        for case in ('AWF_TURNMOONRED', 'AWF_HASITEMEQUIPPED', 'AWF_FORCERUN', '"AWRN"'):
            self.assertIn(case, host)
        self.assertIn('sky_moon_red', (ROOT / 'engine/aga/src/r_sky.c').read_text(encoding='utf-8'))
        self.assertIn('aw_ambient_forced_run', (ROOT / 'engine/aga/src/aw_ambient.c').read_text(encoding='utf-8'))

    def test_explode_attacked_and_spell_effects_go_through_the_host_call(self):
        # v0.0.63 (MWSCRIPT-GAPS-63, batch 2): ExplodeSpell and GetSpellEffects hand the spell's ASPT row, HasItemEquipped
        # the item's AITM row (an NPC's worn list) after its id; GetAttacked reads the combat layer's list
        from mwscript.functions import FUNCTION_NUMBERS
        prog, compiled, _, _ = program()
        user = {c.name: c for c in compiled}['GapUser63b']
        self.assertEqual(user.notyet, [])
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertTrue(user.flags & SCRIPT_VOLATILE)
        self.assertFalse(user.flags & SCRIPT_INERT)
        ops = [(n, a) for _, n, a in awms.decode(user.code)]
        calls = [(k, a) for k, (n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual([a[0] for _, a in calls], [FUNCTION_NUMBERS[n] for n in (
            'getattacked', 'explodespell', 'getspelleffects', 'hasitemequipped')])
        row = prog.spell('proj_trap_spell')
        self.assertEqual(calls[1][1][2] & 0x1F, 1)                  # ExplodeSpell: one number, the row
        self.assertEqual(calls[2][1][2] & 0x1F, 1)
        self.assertIn(row, [a[0] for n, a in ops[:calls[1][0]] if n.startswith('PUSH')])
        self.assertIn(('REF', [0xFFFF]), ops[calls[1][0] + 1:calls[2][0]])   # player->GetSpellEffects
        self.assertEqual([prog.strings.rows[s] for s in calls[3][1][4:]], ['iron dagger'])
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        for case in ('AWF_EXPLODESPELL', 'AWF_GETATTACKED', 'AWF_GETSPELLEFFECTS', 'AW_ActorWearsItem'):
            self.assertIn(case, host)
        self.assertIn('int AW_CastExplode(', (ROOT / 'engine/aga/src/aw_cast.c').read_text(encoding='utf-8'))
        self.assertIn('aw_combat_attacked(t)', (ROOT / 'engine/aga/src/aw_combat.c').read_text(encoding='utf-8'))

    def test_werewolf_set_and_scale_go_through_the_host_call(self):
        # v0.0.63 (MWSCRIPT-GAPS-63, batch 3): BecomeWerewolf hands the werewolf's 35 stats four to a number (9
        # numbers, 255 where the data has no setting), SetWerewolfAcrobatics its one value; the rest by number
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript.codegen import Program
        prog, compiled, _, _ = program()
        user = {c.name: c for c in compiled}['GapUser63c']
        self.assertEqual(user.notyet, [])
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertFalse(user.flags & SCRIPT_INERT)
        calls = [a for _, n, a in awms.decode(user.code) if n == 'NOTYET']
        self.assertEqual([a[0] for a in calls], [FUNCTION_NUMBERS[n] for n in (
            'getpctraveling', 'iswerewolf', 'becomewerewolf', 'setwerewolfacrobatics', 'getwerewolfkills',
            'undowerewolf', 'setscale', 'modscale', 'getscale')])
        self.assertEqual(calls[2][2] & 0x1F, 9)
        self.assertEqual(calls[3][2] & 0x1F, 1)
        self.assertEqual(calls[8][2] & 0xC0, 0xC0)                 # GetScale: a value, a fraction
        # the packing: four bytes to a number, high byte first, signed
        prog.data.records.setdefault('GMST', {})['fwerewolfstrength'] = [('FLTV', struct.pack('<f', 150.0))]
        words = Program.werewolf_settings(prog, True)
        self.assertEqual(len(words), 9)
        self.assertEqual((words[0] >> 24) & 255, 150)
        self.assertEqual(words[0] & 0xFFFFFF, 0xFFFFFF)
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        for case in ('AWF_BECOMEWEREWOLF', 'AWF_SETWEREWOLFACROBATICS', 'AWF_GETWEREWOLFKILLS', 'AWF_SETSCALE', '"AWWF"'):
            self.assertIn(case, host)

    def test_the_small_functions_go_through_the_host_call(self):
        # v0.0.62 (MWSCRIPT-SMALL-FUNCTIONS-62): angles, moves, SetAtStart, Face, detection, the line of sight, the
        # interior, the weather, a knockdown and WakeUpPC keep the import route's form and are carried out (the script
        # is not "not yet"); the reads that change without the state generation make it VOLATILE, GetInterior does not
        # (the player's cell moves it); the changes keep it attached (not INERT)
        from mwscript.functions import FUNCTION_NUMBERS
        prog, compiled, _, _ = program()
        names = {c.name: c for c in compiled}
        user = names['SmallUser']
        self.assertEqual(user.notyet, [])
        self.assertFalse(user.flags & SCRIPT_NOTYET)
        self.assertTrue(user.flags & SCRIPT_VOLATILE)
        self.assertFalse(user.flags & SCRIPT_INERT)
        reader = names['SmallReader']
        self.assertFalse(reader.flags & (SCRIPT_VOLATILE | SCRIPT_NOTYET))
        self.assertTrue(reader.flags & SCRIPT_INERT)              # a read alone is seen nowhere
        ops = [(n, a) for _, n, a in awms.decode(user.code)]
        calls = [(k, a) for k, (n, a) in enumerate(ops) if n == 'NOTYET']
        self.assertEqual([a[0] for _, a in calls], [FUNCTION_NUMBERS[n] for n in (
            'getangle', 'setangle', 'move', 'moveworld', 'setpos', 'setatstart', 'face', 'getdetected', 'getlos',
            'getinterior', 'getcurrentweather', 'onknockout', 'wakeuppc', 'rotateworld', 'getweapondrawn',
            'getpcsneaking', 'setdelete')])
        k = calls[14][0]
        self.assertEqual(ops[k - 1], ('REF', [0xFFFF]))          # player->GetWeaponDrawn: the player as the target
        chime = prog.objects.index['chime_obj']
        k, angle = calls[0]
        self.assertEqual(ops[k - 1], ('REF', [chime]))            # "chime_obj"->GetAngle: the object as the target
        self.assertEqual(angle[2], 0x80 | 0x40)                   # a value, a fraction, no numbers
        self.assertEqual([prog.strings.rows[s] for s in angle[4:]], ['Z'])
        self.assertEqual(calls[1][1][2] & 0x1F, 1)                # SetAngle: one number, after its axis
        self.assertIn(('REF', [chime]), ops[calls[1][0] + 1:calls[2][0]])   # "chime_obj"->Move: the object
        self.assertEqual(calls[6][1][2] & 0x1F, 2)                # Face X Y (the ignored third number dropped)
        self.assertEqual(calls[7][1][2], 0x80)                    # GetDetected: a whole number
        self.assertEqual([prog.strings.rows[s] for s in calls[7][1][4:]], ['Player'])


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
#include "aw_ledger.h"
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
static unsigned char buf[1<<20];static long nbuf;
static int read_mem(void *u,uint32_t off,void *out,uint32_t n){(void)u;if((long)off+(long)n>nbuf)return 0;memcpy(out,buf+off,n);return 1;}
/* CELL-CHANGES-59 slice 5: the scripts' state through the world change list as the engine's host keeps it
 * (aw_mwhost.c locals_export / locals_import): a script's name hash here is the hash of "s<row>" */
static uint32_t name_hash(int script){char s[16];sprintf(s,"s%d",script);return AW_LedgerNameHash(s);}
static void put(void *user,uint32_t ref,int script,int global,int running,const aw_mwcell_t *cells,int count){
    aw_ledger_t *l=(aw_ledger_t *)user;int i;uint32_t h=name_hash(script);
    if(global && running!=AW_MwvmStartsAtLoad(script) && !AW_LedgerScriptSet(l,h,script,running))printf("refused script\n");
    for(i=0;i<count;i++)if(cells[i].i && !AW_LedgerLocalSet(l,global,global?h:ref,h,script,i,cells[i].i))printf("refused local\n");
}
static void import(const aw_ledger_t *l){
    int i,dropped=0;
    AW_MwvmLocalsReset();
    for(i=0;i<l->script_count;i++)
        if(name_hash(l->script[i].hint)!=l->script[i].script || !AW_MwvmGlobalScriptSet(l->script[i].hint,l->script[i].running))dropped++;
    for(i=0;i<l->local_count;i++){
        const aw_ledger_local_t *x=&l->local[i];
        if(name_hash(x->hint)!=x->script || !(x->global?AW_MwvmGlobalScriptLocal(x->hint,x->slot,(uint32_t)x->value):
                                             AW_MwvmLocalSet(x->key,x->hint,x->slot,(uint32_t)x->value)))dropped++;
    }
    printf("import dropped %d\n",dropped);
}
static void attach_all(void){
    uint32_t off,rows,bytes,r;int i;
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3];
        for(i=0;i<3;i++)o[i]=(float)(int32_t)(((uint32_t)p[12+4*i]<<24)|((uint32_t)p[13+4*i]<<16)|((uint32_t)p[14+4*i]<<8)|p[15+4*i])*0.25f;
        AW_MwvmAttach(((uint32_t)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3],(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o);
    }
}
/* what the test reads: references 102 (TimerChime: timer, count) and 103 (Quiet: done), the global scripts */
static void show(const char *when,int starter,int counter){
    int s;aw_mwcell_t v,c;
    printf("%s",when);
    if(AW_MwvmLocalGet(103,0,&s,&v))printf(" done %d",(int)v.i);else printf(" done -");
    if(AW_MwvmLocalGet(102,0,&s,&v) && AW_MwvmLocalGet(102,1,&s,&c))printf(" timer %.2f count %d",v.f,(int)c.i);
    else printf(" timer - count -");
    printf(" starter %d counter %d",AW_MwvmScriptRunning(starter),AW_MwvmScriptRunning(counter));
    for(s=0;s<AW_MwvmInstanceCount();s++){aw_mwvm_instance_t *in=AW_MwvmInstance(s);
        if(in && (in->flags&AWI_GLOBAL) && (int)in->script==counter)printf(" ticks %d",(int)AW_MwvmLocal(s,0).i);}
    printf("\n");
}
static int locals_test(float dt,int starter,int counter){
    static aw_ledger_t saved,read_back;static unsigned char bytes[1<<18];int n,i;float player[3]={0,0,0};
    AW_MwvmStartScript(starter);     /* as a start script: it starts COUNTER with StartScript, then stops itself */    for(tick=1;tick<=6;tick++)AW_MwvmTick(dt,player);
    show("before",starter,counter);
    AW_MwvmBeginMap();               /* a map with none of these objects: their values are parked */
    for(i=0;i<2;i++,tick++)AW_MwvmTick(dt,player);
    show("away",starter,counter);
    AW_MwvmBeginMap();attach_all();  /* back: the values come back from the parking store */
    show("back",starter,counter);
    AW_MwvmLocalsEach(put,&saved);   /* the save */
    n=AW_LedgerEncode(&saved,bytes,sizeof(bytes));
    printf("saved %d locals %d scripts %d bytes %.4s\n",saved.local_count,saved.script_count,n,(const char *)bytes);
    if(n<=0 || !AW_LedgerDecode(bytes,n,&read_back))return 1;
    { int s;aw_mwcell_t v;           /* changed after the save */
      if(AW_MwvmLocalGet(103,0,&s,&v))AW_MwvmLocalSet(103,s,0,99u);
      AW_MwvmGlobalScriptSet(counter,0);AW_MwvmGlobalScriptSet(starter,1);
      for(i=0;i<3;i++,tick++)AW_MwvmTick(dt,player); }
    show("changed",starter,counter);
    AW_MwvmBeginMap();import(&read_back);attach_all();   /* the load: the saved values, then the map */
    show("loaded",starter,counter);
    for(i=0;i<2;i++,tick++)AW_MwvmTick(dt,player);
    show("running",starter,counter);
    AW_MwvmLocalsReset();show("reset",starter,counter);   /* a new game: the start */
    AW_LedgerClear(&saved);AW_LedgerClear(&read_back);
    return 0;
}
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;
    int ticks=atoi(argv[2]),i;float player[3]={0,0,0},dt=(float)atof(argv[3]);
    unsigned used=argc>4?(unsigned)atoi(argv[4]):0;   /* the player uses this reference's object at tick 3 */
    fclose(f);nbuf=n;
    if(getenv("ROOM"))room=atoi(getenv("ROOM"));
    if(getenv("CALLS"))answer=atoi(getenv("CALLS"));
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    AW_MwvmBeginMap();
    if(getenv("HOLD")){   /* CENSUS-INTRO-SCRIPTS-62: a held script is not attached; released, it is */
        int s=atoi(getenv("HOLD")),done=AW_MwvmScriptHold(s,1);
        printf("hold %d held %d\n",done,AW_MwvmScriptHeld(s));
        if(getenv("RELEASE")){done=AW_MwvmScriptHold(s,0);printf("release %d held %d\n",done,AW_MwvmScriptHeld(s));}
    }
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3];
        for(i=0;i<3;i++)o[i]=(float)(int32_t)(((uint32_t)p[12+4*i]<<24)|((uint32_t)p[13+4*i]<<16)|((uint32_t)p[14+4*i]<<8)|p[15+4*i])*0.25f;
        printf("attach %u %d\n",(unsigned)((p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3]),
               AW_MwvmAttach(((uint32_t)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3],(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o));
    }
    if(getenv("NEWGAME"))printf("newgame %d\n",AW_MwvmNewGame());   /* NPC-STORY-DISABLED-AT-START-42 */
    if(getenv("HELD")){   /* SCRIPTED-EVENT-FALLING-MAGE-61: the HELD rows and the lookup by actor */
        uint32_t a,s;float at[3];int k;
        for(k=0;AW_MwvmHeld(k,&a,&s,at);k++)printf("held %u %u %.1f %.1f %.1f find %d\n",(unsigned)a,(unsigned)s,
                                                   at[0],at[1],at[2],AW_MwvmHeldFind(a));
        printf("held rows %d find-none %d\n",AW_MwvmHeldCount(),AW_MwvmHeldFind(1));
        return 0;
    }
    if(getenv("PCADD")){   /* CENSUS-INTRO-SCRIPTS-62: OnPCAdd on the taken placement 103, then a carried instance */
        int s=atoi(getenv("PCADD")),ps,k,running=0;aw_mwcell_t pv;
        printf("pcadd placed %d\n",AW_MwvmPcAdd(103,s,0));
        if(AW_MwvmLocalGet(103,0,&ps,&pv))printf("placed local %d\n",(int)pv.i);
        printf("pcadd carried %d\n",AW_MwvmPcAdd(0,s,0));
        for(k=0;k<AW_MwvmInstanceCount();k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);
            if(in && (in->flags&AWI_GLOBAL) && (int)in->script==s && (in->flags&AWI_RUNNING))running=(int)AW_MwvmLocal(k,0).i;}
        printf("carried local %d\n",running);
        printf("pcadd slot %d held %d\n",AW_MwvmPcAdd(0,s,999),(AW_MwvmScriptHold(s,1),AW_MwvmPcAdd(0,s,0)));
        printf("pcadd row %d\n",AW_MwvmPcAddRow(0x12345678u,&ps,&k));
        return 0;
    }
    if(getenv("CARRIED")){   /* MWSCRIPT-UNPLACED-ATTACH-62: an item's script runs while carried, stops with the last */
        int s=atoi(getenv("CARRIED")),k,running=0,value=-1,ls=-1;
        int a,b,c;   /* each call its own statement: the order of a call's arguments is not defined */
        a=AW_MwvmPcAdd(0,s,AW_MWVM_NO_SLOT);b=AW_MwvmPcAdd(0,s,AW_MWVM_NO_SLOT);
        printf("carried start %d again %d\n",a,b);
        for(k=0;k<AW_MwvmInstanceCount();k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);
            if(in && (in->flags&AWI_GLOBAL) && (int)in->script==s){running=(in->flags&AWI_RUNNING)!=0;value=(int)AW_MwvmLocal(k,0).i;}}
        printf("carried running %d local %d\n",running,value);
        printf("carried placed %d\n",AW_MwvmPcAdd(103,s,AW_MWVM_NO_SLOT));
        a=AW_MwvmCarriedStop(s);b=AW_MwvmCarriedStop(s);c=AW_MwvmScriptRunning(s);
        printf("carried stop %d again %d running %d\n",a,b,c);
        printf("attached %d none %d\n",AW_MwvmScriptAttached(s),AW_MwvmScriptAttached(AW_MwvmScriptCount()-1));
        a=AW_MwvmLevelledScript((uint32_t)strtoul(getenv("LEVELLED"),NULL,10),&ls);
        printf("levelled %d script %d\n",a,ls);
        ls=-1;a=AW_MwvmLevelledScript(0x12345678u,&ls);
        printf("levelled none %d script %d\n",a,ls);
        return 0;
    }
    if(getenv("LOCALS"))return locals_test(dt,atoi(getenv("LOCALS")),atoi(getenv("COUNTER")));
    if(getenv("DETACH")){   /* v0.0.62: reference 103 leaves the map (PositionCell), its values parked, then back */
        int s,k,attached=0,first,again;aw_mwcell_t v;
        for(tick=1;tick<=2;tick++)AW_MwvmTick(dt,player);
        first=AW_MwvmDetach(103);again=AW_MwvmDetach(103);
        printf("detach %d again %d\n",first,again);
        for(k=0;k<AW_MwvmInstanceCount();k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);
            if(in && (in->flags&AWI_USED) && in->reference==103)attached++;}
        printf("attached %d parked %d\n",attached,AW_MwvmLocalGet(103,0,&s,&v)?(int)v.i:-1);
        k=AW_MwvmAttach(103,s,0,-1,player);
        printf("back %d done %d\n",k>=0,k>=0?(int)AW_MwvmLocal(k,0).i:-1);
        return 0;
    }
    if(getenv("BLOCK")){    /* v0.0.62: an entity block by its reference in a map's entity text */
        static const char text[]="{\n\"classname\" \"worldspawn\"\n\"message\" \"a } in a value\"\n}\n"
            "{\n\"classname\" \"aw_npc\"\n\"aw_ref\"  \"12\"\n\"netname\" \"Twelve\"\n}\n"
            "{\n\"classname\" \"aw_npc\"\n\"netname\" \"aw_ref\"\n\"aw_ref\" \"123\"\n}\n";
        static const uint32_t refs[]={12,123,1,0};unsigned long length=0;
        for(i=0;i<4;i++){const char *b=AW_MwvmEntityBlock(text,sizeof(text)-1,refs[i],&length);
            printf("block %u %ld %.*s|\n",(unsigned)refs[i],b?(long)(b-text):-1L,b?(int)length:0,b?b:"");}
        return 0;
    }
    if(getenv("DIALOGUE")){   /* a result text run on reference 103 (the Quiet object) through its DRSC row */
        const char *text=getenv("DIALOGUE");int speaker=-1,row_speaker,broken,script,k,ps;aw_mwcell_t pv;
        if(getenv("DETACHED"))printf("detached %d\n",AW_MwvmDetach(103));   /* the speaker's script not attached */
        for(k=0;k<AW_MwvmInstanceCount();k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);
            if(in && (in->flags&AWI_USED) && in->reference==103)speaker=in->script;}
        script=AW_MwvmFindDialogue(read_mem,NULL,AW_MwvmTextHash(text,(int)strlen(text)),(int)strlen(text),speaker,&row_speaker,&broken);
        printf("dialogue %d speaker %d row %d broken %d ran %d\n",script,speaker,row_speaker,broken,
               script>=0?AW_MwvmRunDialogue(script,103,row_speaker):0);
        for(k=0;k<AW_MwvmInstanceCount();k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);
            if(in && (in->flags&AWI_USED) && in->reference==103)printf("done %d\n",(int)AW_MwvmLocal(k,0).i);}
        printf("parked %d\n",AW_MwvmLocalGet(103,0,&ps,&pv)?(int)pv.i:-1);
        printf("missing %d\n",AW_MwvmFindDialogue(read_mem,NULL,AW_MwvmTextHash("nothing",7),7,speaker,&row_speaker,&broken));
        return 0;
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
        # MWSCRIPT-UNPLACED-ATTACH-62: a creature record with the Quiet script that a levelled list names (LACT row)
        cls.prog.data.bases['lev_crea'] = ('CREA', 'quiet')
        cls.prog.data.levelled_lists = {'lev_test': ['lev_crea']}
        raw, _ = awms.write(cls.prog, cls.compiled, binds, {'ops_per_run': 500})
        (cls.tmp / 'test.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_mwvm.c'), str(src / 'aw_ledger.c'),
                                '-o', str(cls.tmp / 'h')],
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

    def test_dialogue_result_runs_on_the_speaker_through_its_row(self):
        # DIALOGUE-COMPLETE-58: the result text's row is found by hash and length, compiled with the Quiet script's
        # locals; run on reference 103 it sets that instance's local done to 7 and calls Choice (host call 22)
        from mwscript.codegen import SCRIPT_DIALOGUE
        out = self.run_vm(0, env={'DIALOGUE': RESULT_TEXT, 'CALLS': '-1'})
        line = next(l for l in out if l.startswith('dialogue')).split()
        quiet = str(self.index('scripts', 'quiet'))
        self.assertEqual(line[3], quiet)                          # the speaker's attached script
        self.assertEqual(line[5], quiet)                          # the row compiled with its locals
        self.assertEqual((line[7], line[9]), ('0', '1'))          # compiled, ran
        self.assertTrue(self.compiled[int(line[1])].flags & SCRIPT_DIALOGUE)
        self.assertIn('done 7', out)
        self.assertTrue(any(l.split()[1:3] == ['call', '22'] for l in out), out)
        self.assertIn('missing -1', out)

    def test_dialogue_result_keeps_a_detached_speakers_locals(self):
        # CENSUS-INTRO-SCRIPTS-62: a result run while the speaker's script is not attached (Sellus Gravius's Greeting 1,
        # "set state to -1") writes his parked locals, and AW_MwvmLocalGet (the dialogue's Local condition, aw_mwhost.c
        # live_local) reads them back: the next greeting sees state -1
        out = self.run_vm(0, env={'DIALOGUE': RESULT_TEXT, 'CALLS': '-1', 'DETACHED': '1'})
        self.assertIn('detached 1', out)
        line = next(l for l in out if l.startswith('dialogue')).split()
        quiet = str(self.index('scripts', 'quiet'))
        self.assertEqual(line[3], '-1')                           # no attached speaker
        self.assertEqual(line[5], quiet)                          # the row still runs with his locals
        self.assertEqual(line[9], '1')
        self.assertNotIn('done 7', out)                           # nothing attached
        self.assertIn('parked 7', out)                            # kept where the condition reads it

    def test_a_held_script_is_not_attached(self):
        # CENSUS-INTRO-SCRIPTS-62: with the old opening chosen (aw_census_legacy 1) the census office's scripts are
        # held: reference 103's script is not attached while held, and is once released
        quiet = self.index('scripts', 'quiet')
        held = self.run_vm(0, env={'HOLD': str(quiet), 'DIALOGUE': RESULT_TEXT, 'CALLS': '-1'})
        self.assertIn('hold 1 held 1', held)
        self.assertIn('attach 103 -1', held)
        self.assertEqual(next(l for l in held if l.startswith('dialogue')).split()[3], '-1')
        free = self.run_vm(0, env={'HOLD': str(quiet), 'RELEASE': '1', 'DIALOGUE': RESULT_TEXT, 'CALLS': '-1'})
        self.assertIn('release 1 held 0', free)
        self.assertNotIn('attach 103 -1', free)
        self.assertEqual(next(l for l in free if l.startswith('dialogue')).split()[3], str(quiet))

    def test_onpcadd_reaches_the_taken_placement_or_the_carried_instance(self):
        # CENSUS-INTRO-SCRIPTS-62: OnPCAdd 1 on the placement the player took (its own values go on), else on the
        # item's carried instance (started); a slot out of range or a held script: nothing; an unknown item: no row
        quiet = self.index('scripts', 'quiet')
        out = self.run_vm(0, env={'PCADD': str(quiet)})
        self.assertIn('pcadd placed 1', out)
        self.assertIn('placed local 1', out)
        self.assertIn('pcadd carried 2', out)
        self.assertIn('carried local 1', out)
        self.assertIn('pcadd slot 0 held 0', out)
        self.assertIn('pcadd row 0', out)

    def test_a_carried_items_script_runs_and_stops_with_the_last_one(self):
        # MWSCRIPT-UNPLACED-ATTACH-62: a carried item whose script has no OnPCAdd: its carried instance starts (no
        # local set), a second start changes nothing, the taken placement keeps its own; the last one leaving stops it
        # (once); the LACT row of the levelled creature names its script, an unknown record none
        from mwscript.awms import fnv1a
        quiet = self.index('scripts', 'quiet')
        out = self.run_vm(0, env={'CARRIED': str(quiet), 'LEVELLED': str(fnv1a('lev_crea'))})
        self.assertIn('carried start 2 again 2', out)
        self.assertIn('carried running 1 local 0', out)
        self.assertIn('carried placed 1', out)
        self.assertIn('carried stop 1 again 0 running 0', out)
        self.assertIn('attached 1 none 0', out)
        self.assertIn('levelled 1 script %d' % quiet, out)
        self.assertIn('levelled none 0 script -1', out)

    def test_pcadd_rows_name_each_carried_items_onpcadd_slot(self):
        # PADD: a carryable record whose script declares OnPCAdd gives one row (hash of the folded id, script, slot);
        # a container's script or a script without the local gives none
        from mwscript.awms import pcadd_rows, fnv1a

        class Index:
            def __init__(self, names):
                self.index = {n: i for i, n in enumerate(names)}

        class Data:
            bases = {'ring_keley': ('CLOT', 'chargen_ring_keley'), 'chargen statssheet': ('BOOK', 'chargenstatssheet'),
                     'barrel': ('CONT', 'chargen_ring_keley'), 'plain': ('MISC', 'noadd')}

        class P:
            data = Data()
            scripts = Index(['chargen_ring_keley', 'chargenstatssheet', 'noadd'])
            script_locals = {'chargen_ring_keley': {'state': ('s', 0), 'onpcadd': ('s', 1)},
                             'chargenstatssheet': {'state': ('s', 0), 'onpcadd': ('s', 1)}, 'noadd': {'x': ('s', 0)}}
        rows = pcadd_rows(P())
        # MWSCRIPT-UNPLACED-ATTACH-62: an item whose script has no OnPCAdd gives a row too (NO_SLOT: it runs carried)
        self.assertEqual(rows, sorted([(fnv1a('ring_keley'), 0, 1), (fnv1a('chargen statssheet'), 1, 1),
                                       (fnv1a('plain'), 2, awms.NO_SLOT)]))
        self.assertEqual(fnv1a('A'), fnv1a('a'))

    def test_levelled_actor_rows_name_the_scripted_actors_a_list_gives(self):
        # LACT (MWSCRIPT-UNPLACED-ATTACH-62): a scripted creature or NPC record a levelled list names gives one row
        # (hash of the folded id, script); an item, an actor with no script or a record no list names gives none
        from mwscript.awms import levelled_actor_rows, fnv1a

        class Index:
            def __init__(self, names):
                self.index = {n: i for i, n in enumerate(names)}

        class Data:
            bases = {'kagouti_diseased': ('CREA', 'diseaseyellowtick'), 'cattle_arg_f01': ('NPC_', 'cattlescript'),
                     'mudcrab': ('CREA', ''), 'sunder': ('WEAP', 'ouch_sunder'), 'placed_only': ('CREA', 'cattlescript')}
            levelled_actors = ['kagouti_diseased', 'cattle_arg_f01', 'mudcrab', 'sunder', 'nobody']

        class P:
            data = Data()
            scripts = Index(['diseaseyellowtick', 'cattlescript', 'ouch_sunder'])
        self.assertEqual(levelled_actor_rows(P()), sorted([(fnv1a('kagouti_diseased'), 0),
                                                            (fnv1a('cattle_arg_f01'), 1)]))

    def test_gamedata_reads_the_levelled_creature_lists(self):
        # MWSCRIPT-UNPLACED-ATTACH-62: every actor a LEVC record names (the last master's record wins)
        lev = record('LEVC', sub('NAME', 'lev_test'), sub('DATA', struct.pack('<i', 0)), sub('NNAM', b'\0'),
                     sub('INDX', struct.pack('<i', 2)), sub('CNAM', 'Lev_Crea'), sub('INTV', struct.pack('<h', 1)),
                     sub('CNAM', 'other_crea'), sub('INTV', struct.pack('<h', 5)))
        d = Path(tempfile.mkdtemp(prefix='aw-mwscript-lev-'))
        try:
            (d / 'Morrowind.esm').write_bytes(master_bytes(records=[lev]))
            data = GameData().load(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(data.levelled_lists, {'lev_test': ['lev_crea', 'other_crea']})
        self.assertEqual(data.levelled_actors, ['lev_crea', 'other_crea'])

    def test_a_file_with_the_dialogue_scripts_loads(self):
        # MWSCRIPT-REFUSED-SCRIPT-COUNT-58: the dialogue result scripts made v0.0.58-dev5's file 8,618 scripts and the
        # interpreter refused every file over 2,048, so no script ran. A file of 9,000 one-opcode scripts loads; one
        # over the engine's limit is refused there and by the builder first.
        def awm(count):
            code = bytes([OPCODES['END'][0]])
            sections = {'CONF': (struct.pack('>IHH', 12288, 4000, 2000), 1),
                        'SCRP': (struct.pack('>HBBHHII', 0, 0, 0, 0, 0, 0, 1) * count, count), 'CODE': (code, count)}
            tags = ('CONF', 'GLOB', 'JRNL', 'SNDS', 'VOIC', 'MUSI', 'OBJS', 'SCRP', 'STRT', 'CODE', 'BIND')
            head = 16 + 16 * len(tags)
            directory, body = b'', b''
            for tag in tags:
                data, rows = sections.get(tag, (b'', 0))
                directory += tag.encode() + struct.pack('>III', head + len(body), rows, len(data))
                body += data + b'\0' * (-len(data) % 4)
            return b'AWMS' + struct.pack('>HHII', 1, len(tags), head + len(body), head + len(body)) + directory + body
        for count, loads in ((9000, True), (awms.ENGINE_MAX_SCRIPTS + 1, False)):
            path = self.tmp / ('many-%d.awm' % count)
            path.write_bytes(awm(count))
            r = subprocess.run([str(self.tmp / 'h'), str(path), '0', '0.25'], capture_output=True, text=True)
            self.assertEqual(r.returncode == 0, loads, r.stdout + r.stderr)
        with self.assertRaises(ValueError):
            awms.check_limits(awms.ENGINE_MAX_SCRIPTS + 1, 0)
        awms.check_limits(awms.ENGINE_MAX_SCRIPTS, awms.ENGINE_MAX_GLOBALS)

    def test_locals_and_global_scripts_kept_across_a_cell_change_and_a_load(self):
        # CELL-CHANGES-59 slice 5 (OpenMW 0.51: a reference's locals are part of its saved state; a global script is
        # saved with its running state and its locals): through the world change list's saved form and back
        starter, counter = self.index('scripts', 'starter'), self.index('scripts', 'globalcounter')
        out = self.run_vm(0, env={'LOCALS': str(starter), 'COUNTER': str(counter)})
        rows = {l.split()[0]: l.split()[1:] for l in out if l.split()[:1] and l.split()[0] in
                ('before', 'away', 'back', 'changed', 'loaded', 'running', 'reset')}

        def field(when, name):
            r = rows[when]
            return r[r.index(name) + 1]
        # StartScript ran from the started script; it stopped itself with StopScript
        self.assertEqual((field('before', 'starter'), field('before', 'counter')), ('0', '1'), out)
        ticks = int(field('before', 'ticks'))
        self.assertGreaterEqual(ticks, 5)
        self.assertEqual(field('before', 'done'), '1')            # Quiet set its own local on its first run
        # a cell change: the objects' values parked (kept, not running), the global script runs on, the values come back
        self.assertEqual(rows['away'][:6], rows['before'][:6])
        self.assertEqual(int(field('away', 'ticks')), ticks + 2)
        self.assertEqual(rows['back'][:6], rows['before'][:6])
        # the save carries the values (the fifth form) and the running script; after the load they are the saved ones
        saved = next(l for l in out if l.startswith('saved')).split()
        self.assertEqual(saved[-1], 'AWL5')
        self.assertGreaterEqual(int(saved[1]), 4)                 # done, timer, count, phase, ticks (non-zero ones)
        self.assertEqual(saved[3], '1')                           # one global script whose running state differs
        self.assertEqual(field('changed', 'done'), '99')
        self.assertEqual((field('changed', 'counter'), field('changed', 'starter')), ('0', '0'))
        self.assertEqual(rows['loaded'][:6], rows['back'][:6])
        self.assertEqual((field('loaded', 'starter'), field('loaded', 'counter'), field('loaded', 'ticks')),
                         ('0', '1', str(ticks + 2)))
        self.assertIn('import dropped 0', out)
        self.assertEqual(int(field('running', 'ticks')), ticks + 4)  # still running after the load
        # a new game: every value at 0, no global script running but the start scripts (none here)
        self.assertEqual((field('reset', 'done'), field('reset', 'counter'), field('reset', 'ticks')), ('0', '0', '0'))
        self.assertFalse([l for l in out if l.startswith('refused')], out)

    def test_an_object_that_left_the_map_keeps_its_values(self):
        # v0.0.62 (PositionCell to another place): the instance is parked as a map change parks it, runs no more,
        # and has its values again when attached where it arrives
        out = self.run_vm(0, env={'DETACH': '1'})
        self.assertIn('detach 1 again 0', out)
        self.assertIn('attached 0 parked 1', out)                 # Quiet's done (1 after its first run), kept
        self.assertIn('back 1 done 1', out)

    def test_an_entity_block_by_its_reference(self):
        # v0.0.62: the actor's entity in a map's entity text by its "aw_ref" key: a quoted brace or a value that reads
        # "aw_ref" is no match; a reference no entity has is none
        text = '\n'.join(self.run_vm(0, env={'BLOCK': '1'}))
        found = dict(re.findall(r'block (\d+) (-?\d+) ', text))
        self.assertEqual((found['1'], found['0']), ('-1', '-1'))
        self.assertNotEqual(found['12'], '-1')
        self.assertIn('"aw_ref"  "12"\n"netname" "Twelve"\n}|', text)
        self.assertIn('"netname" "aw_ref"\n"aw_ref" "123"\n}|', text)
        self.assertLess(int(found['12']), int(found['123']))

    def test_handwritten_scripts_do_not_attach(self):
        out = self.run_vm(1)
        self.assertIn('attach 106 -1', out)
        self.assertIn('attach 107 -1', out)                       # inert today: not attached

    def test_quiet_rule_notyet_once_and_the_loop_guard(self):
        out = self.run_vm(16)
        stats = next(l for l in out if l.startswith('stats')).split()
        self.assertGreater(int(stats[4]), 0)                       # quiet skips happened
        notyet = [l for l in out if l.split()[1:2] == ['notyet']]
        # COE and PositionCell (the player's into a room no list names; the stub host carries out no call, so the
        # other object's goes the same way), once each (OnActivate and Activate run since v0.0.51; never used here,
        # OnActivate reads 0; AIWander runs since v0.0.54)
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
        travel = FUNCTION_NUMBERS['coe']
        out = self.run_vm(4)
        calls = [l.split()[1:] for l in out if l.split()[1:3] == ['call', str(travel)]]
        self.assertTrue(calls, out)
        self.assertEqual(calls[0], ['call', str(travel), '2', '100', '5', 'strings', '0'])
        counted = {int(l.split()[1]): l.split() for l in out if l.startswith('function')}
        self.assertEqual(int(counted[travel][2]), len(calls))
        self.assertEqual(int(counted[travel][3]), self.prog.strings.index['coe'])
        travel_line = str(self.prog.strings.index['coe'])
        self.assertEqual(len([l for l in out if l.split()[1:3] == ['notyet', travel_line]]), 1)    # logged once
        # carried out by number (the host answers): no log, the host count instead
        out = self.run_vm(4, env={'CALLS': str(travel)})
        self.assertFalse([l for l in out if l.split()[1:3] == ['notyet', travel_line]], out)
        stats = next(l for l in out if l.startswith('stats')).split()
        self.assertEqual(int(stats[14]), len(calls))


STANDING_HARNESS = r'''
#include <stdio.h>
#include "aw_pcstanding.h"
int main(void){
    int i;char name[16];
    AW_StandingReset();
    printf("%d %d\n",AW_StandingRank("Mages Guild"),AW_StandingCrime());
    AW_StandingModCrime(-5);printf("crime %d\n",AW_StandingCrime());           /* never below 0 */
    AW_StandingSetCrime(1500);AW_StandingModCrime(-50);printf("crime %d\n",AW_StandingCrime());
    AW_StandingSetReputation(300);printf("rep %d\n",AW_StandingReputation());   /* capped at 255 */
    AW_StandingLower("Mages Guild");printf("rank %d\n",AW_StandingRank("mages guild"));   /* not a member: -1 */
    AW_StandingRaise("Mages Guild");printf("rank %d\n",AW_StandingRank("MAGES GUILD"));   /* joins: 0 */
    for(i=0;i<12;i++){AW_StandingRaise("mages guild");}
    printf("rank %d\n",AW_StandingRank("Mages Guild"));    /* 9 */
    AW_StandingJoin("Mages Guild");printf("rank %d\n",AW_StandingRank("Mages Guild"));    /* join keeps the rank */
    AW_StandingSetExpelled("Fighters Guild",1);printf("expelled %d %d\n",AW_StandingExpelled("fighters guild"),
        AW_StandingRank("Fighters Guild"));
    AW_StandingJoin("Fighters Guild");AW_StandingLower("Fighters Guild");
    printf("left %d %d\n",AW_StandingRank("Fighters Guild"),AW_StandingExpelled("Fighters Guild"));
    AW_StandingSetFactionReputation("Temple",3);AW_StandingSetFactionReputation("temple",AW_StandingFactionReputation("TEMPLE")+4);
    printf("facrep %d %d\n",AW_StandingFactionReputation("Temple"),AW_StandingFactionReputation("Imperial Cult"));
    for(i=0;i<40;i++){sprintf(name,"f%d",i);AW_StandingJoin(name);}

    printf("full %d %d\n",AW_StandingFull(),AW_StandingRank("f39"));
    {static unsigned char block[2048];int n;
     AW_StandingReset();AW_StandingSetCrime(70000);AW_StandingSetReputation(12);AW_StandingRaise("Temple");
     AW_StandingRaise("temple");AW_StandingSetExpelled("Thieves Guild",1);AW_StandingSetFactionReputation("Temple",-3);
     n=AW_StandingExport(block,sizeof(block));AW_StandingReset();
     i=AW_StandingImport(block,n);
     printf("saved %d %d %d %d %d %d %d\n",n,i,AW_StandingCrime(),AW_StandingReputation(),
            AW_StandingRank("TEMPLE"),AW_StandingExpelled("thieves guild"),AW_StandingFactionReputation("Temple"));
     i=AW_StandingImport(block,n-1);
     printf("bad %d %d\n",i,AW_StandingRank("Temple"));
     /* v0.0.62 (CRIME-59): the crimes' numbers (a new one, the last paid), saved (AWPS2) */
     AW_StandingReset();printf("none %d\n",AW_StandingCrimeLast());
     AW_StandingCrimeNew();AW_StandingCrimeNew();AW_StandingCrimePaid();AW_StandingCrimeNew();
     n=AW_StandingExport(block,sizeof(block));AW_StandingReset();i=AW_StandingImport(block,n);
     printf("crimes %d %d %d %d\n",n,i,AW_StandingCrimeLast(),AW_StandingCrimeNew());
     /* a block saved before v0.0.62 (AWPS1: no crimes' numbers) still loads */
     AW_StandingReset();AW_StandingSetCrime(5);n=AW_StandingExport(block,sizeof(block));block[4]=1;
     AW_StandingReset();i=AW_StandingImport(block,n-8);
     printf("v1 %d %d %d\n",i,AW_StandingCrime(),AW_StandingCrimeLast());}
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class StandingTests(unittest.TestCase):
    """v0.0.57: the player's standing (aw_pcstanding.c) natively, with OpenMW's rules (npcstats.cpp)."""

    def test_crime_reputation_ranks_expelled(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-standing-'))
        try:
            (tmp / 'h.c').write_text(STANDING_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_pcstanding.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(out, ['-1 0', 'crime 0', 'crime 1450', 'rep 255', 'rank -1', 'rank 0', 'rank 9', 'rank 9',
                               'expelled 1 -1', 'left -1 0', 'facrep 7 0', 'full 1 -1',
                               'saved 96 1 70000 12 1 1 -3', 'bad 0 -1', 'none -1', 'crimes 20 1 1 3',
                               'v1 1 5 -1'])


EFFECT_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t a;static unsigned char block[512];int i,n,ok;
#ifdef AW_ACTOR_SKILL_PARTS
    static aw_actor_skills_t skills;
#endif
    memset(&a,0,sizeof(a));a.reference=AW_ACTOR_PLAYER_REF;a.dyn_base[0]=a.dyn_cur[0]=50;
#ifdef AW_ACTOR_SKILL_PARTS
    AW_ActorAttachSkills(&a,&skills);
#endif
    a.dyn_base[1]=a.dyn_cur[1]=40;a.attr_base[0]=40;
    AW_EffectsReset();
    AW_EffectsAdd(&a,AW_FX_FORTIFY,AWA_ATTRIBUTE+0,10,5);
    AW_EffectsAdd(&a,AW_FX_DAMAGE,AWA_HEALTH,2,3);
    AW_EffectsAdd(&a,AW_FX_DRAIN,AWA_MAGICKA,15,4);
    AW_EffectsAdd(&a,AW_FX_FORTIFY,AWA_HEALTH,20,10);
    printf("start %d %.1f %.1f %.1f %.1f\n",a.attr_mod[0],a.dyn_cur[0],a.dyn_base[0],a.dyn_cur[1],a.dyn_base[1]);
    printf("has %d %d %d %d\n",AW_EffectsHas(79),AW_EffectsHas(80),AW_EffectsHas(19),AW_EffectsHas(14));
    for(i=0;i<6;i++)AW_EffectsTick(&a,1.0f);
    printf("after6 %d %.1f %.1f %.1f %d\n",a.attr_mod[0],a.dyn_cur[0],a.dyn_base[0],a.dyn_cur[1],AW_EffectsCount());
    n=AW_EffectsExport(block,sizeof(block));ok=AW_EffectsImport(block,n);
    printf("saved %d %d %d\n",n,ok,AW_EffectsCount());
    AW_EffectsAdd(&a,AW_FX_RESTORE,AWA_HEALTH,100,0);
    printf("restore %.1f\n",a.dyn_cur[0]);
    for(i=0;i<5;i++)AW_EffectsTick(&a,1.0f);
    printf("end %.1f %.1f %d\n",a.dyn_cur[0],a.dyn_base[0],AW_EffectsCount());
    for(i=0;i<40;i++)AW_EffectsAdd(&a,AW_FX_FORTIFY,AWA_SKILL+3,1,60);
    printf("full %d %lu\n",AW_EffectsCount(),AW_EffectsRefused());
    ok=AW_EffectsImport(block,n-1);
    printf("bad %d %d\n",ok,AW_EffectsCount());
    return 0;
}
'''

# v0.0.61 (SPELL-EFFECTS-57): any effect number on any actor by its reference, the effects that only add their
# magnitude (Light, Levitate), the per-second elements, the NPCs' share of the pool, forgetting, the v2 save and a
# v0.0.57 (version 1) block still loading.
EFFECT_ACTORS_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t p,npc,other;static unsigned char block[2048];int i,n,ok,group;uint32_t owners[8];
    static const unsigned char v1[16]={'A','W','E','F',1,1,3,0,0x41,0x20,0,0,0x40,0xa0,0,0};   /* Fortify Strength 10, 5 s */
    memset(&p,0,sizeof(p));memset(&npc,0,sizeof(npc));memset(&other,0,sizeof(other));
    p.reference=AW_ACTOR_PLAYER_REF;p.dyn_base[0]=p.dyn_cur[0]=50;
    npc.reference=0x1234;npc.dyn_base[0]=npc.dyn_cur[0]=40;npc.attr_base[2]=50;
    other.reference=0x99;other.dyn_base[0]=other.dyn_cur[0]=30;
    AW_EffectsReset();
    {int k1=AW_EffectKind(14,&group),g1=group,k2=AW_EffectKind(41,&group),k3=AW_EffectKind(89,&group),g3=group;
     printf("kinds %d %d %d %d %d\n",k1,g1,k2,k3,g3);}
    printf("persec %d %d %d %d\n",AW_EffectPerSecond(14),AW_EffectPerSecond(41),AW_EffectPerSecond(79),AW_EffectPerSecond(75));
    printf("harmful %d %d %d %d %d %d\n",AW_EffectHarmful(14),AW_EffectHarmful(86),AW_EffectHarmful(41),AW_EffectHarmful(75),
           AW_EffectHarmful(7),AW_EffectHarmful(8));
    ok=AW_EffectsLand(&p,AW_EFFECT_LIGHT,AW_EFFECT_NO_ARG,20,30,7);
    ok+=AW_EffectsLand(&p,AW_EFFECT_LEVITATE,AW_EFFECT_NO_ARG,10,15,8);
    ok+=AW_EffectsLand(&npc,AW_EFFECT_FIRE_DAMAGE,AW_EFFECT_NO_ARG,5,4,9);
    ok+=AW_EffectsLand(&npc,AW_EFFECT_FROST_DAMAGE,AW_EFFECT_NO_ARG,12,0,9);       /* no duration: at once */
    ok+=AW_EffectsLand(&npc,17,2,10,6,9);                                          /* Drain Intelligence (attribute 2) */
    ok+=AW_EffectsLand(&npc,17,AW_EFFECT_NO_ARG,10,6,9);                           /* refused: no attribute */
    ok+=AW_EffectsLand(&other,AW_EFFECT_SHIELD,AW_EFFECT_NO_ARG,15,10,3);
    printf("landed %d count %d %d %d %d\n",ok,AW_EffectsCount(),AW_EffectsCountOn(AW_ACTOR_PLAYER_REF),AW_EffectsCountOn(0x1234),
           AW_EffectsCountOn(0x99));
    printf("npc %.1f %d light %.1f lev %.1f has %d %d %d\n",npc.dyn_cur[0],npc.attr_mod[2],
           AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_LIGHT,AW_EFFECT_NO_ARG),
           AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_LEVITATE,AW_EFFECT_NO_ARG),
           AW_EffectsHas(AW_EFFECT_LIGHT),AW_EffectsHasOn(0x1234,AW_EFFECT_FIRE_DAMAGE),AW_EffectsHas(AW_EFFECT_FIRE_DAMAGE));
    n=AW_EffectsOwners(owners,8);
    printf("owners %d %x %x\n",n,(unsigned)owners[0],(unsigned)owners[1]);
    for(i=0;i<5;i++){AW_EffectsTick(&npc,1.0f);AW_EffectsTick(&p,1.0f);}           /* "other" is not loaded: it does not tick */
    printf("after5 npc %.1f %d count %d other %d\n",npc.dyn_cur[0],npc.attr_mod[2],AW_EffectsCount(),AW_EffectsCountOn(0x99));
    n=AW_EffectsExport(block,sizeof(block));ok=AW_EffectsImport(block,n);
    printf("saved %d %d %d %.1f\n",n,ok,AW_EffectsCount(),AW_EffectsMagnitude(0x99,AW_EFFECT_SHIELD,AW_EFFECT_NO_ARG));
    n=AW_EffectsForget(0x99);printf("forget %d %d\n",n,AW_EffectsCount());
    for(i=0;i<40;i++)AW_EffectsLand(&npc,AW_EFFECT_SHIELD,AW_EFFECT_NO_ARG,1,60,3);
    printf("npcfull %d %d %lu\n",AW_EffectsCount(),AW_EffectsCountOn(0x1234),AW_EffectsRefused());
    ok=AW_EffectsImport(v1,sizeof(v1));
    {aw_effect_info_t e;int got=AW_EffectsAt(0,&e);
     printf("v1 %d %d %d %d %x %.1f %.1f\n",ok,AW_EffectsCount(),got,e.effect,(unsigned)e.owner,e.magnitude,e.left);}
    return 0;
}
'''


# RESIST-NORMAL-WEAPONS-61: the combat layer reads Resist Normal Weapons (98) and Weakness to Normal Weapons (36) as
# the summed magnitude on the actor now (aw_mwhost.c effect_magnitude_of); two sources add, one ending takes its part.
EFFECT_RESIST_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t npc;int i;
    memset(&npc,0,sizeof(npc));npc.reference=0x42;npc.dyn_base[0]=npc.dyn_cur[0]=60;
    AW_EffectsReset();
    AW_EffectsLand(&npc,98,AW_EFFECT_NO_ARG,25,10,1);
    AW_EffectsLand(&npc,98,AW_EFFECT_NO_ARG,15,3,2);
    AW_EffectsLand(&npc,36,AW_EFFECT_NO_ARG,20,5,3);
    printf("now %.1f %.1f %.1f\n",AW_EffectsMagnitude(0x42,98,AW_EFFECT_NO_ARG),AW_EffectsMagnitude(0x42,36,AW_EFFECT_NO_ARG),
           AW_EffectsMagnitude(0x43,98,AW_EFFECT_NO_ARG));
    for(i=0;i<4;i++)AW_EffectsTick(&npc,1.0f);
    printf("after4 %.1f %.1f health %.1f\n",AW_EffectsMagnitude(0x42,98,AW_EFFECT_NO_ARG),
           AW_EffectsMagnitude(0x42,36,AW_EFFECT_NO_ARG),npc.dyn_cur[0]);
    {   /* a creature: Fortify Skill (83, Long Blade 5) changes nothing, Fortify Attribute (79, Strength) does */
        static aw_actor_t c;
        memset(&c,0,sizeof(c));c.reference=0x77;c.kind=1;
        AW_EffectsLand(&c,83,5,10,5,4);AW_EffectsLand(&c,79,0,10,5,4);
        printf("creature %d %d\n",c.skill_mod[5],c.attr_mod[0]);
        for(i=0;i<6;i++)AW_EffectsTick(&c,1.0f);
        printf("creature after %d %d\n",c.skill_mod[5],c.attr_mod[0]);
    }
    return 0;
}
'''


# v0.0.62 (SUMMONED-CREATURES-62): the summoning effects by number, and one effect ended at once (a summoned creature
# died) while another of its owner's and the same effect of another owner stay; a Fortify ended so is undone.
EFFECT_SUMMON_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t p;int e,n=0;
    for(e=0;e<AW_EFFECT_COUNT;e++)n+=AW_EffectSummon(e);
    printf("summons %d %d %d %d %d\n",n,AW_EffectSummon(102),AW_EffectSummon(116),AW_EffectSummon(134),AW_EffectSummon(117));
    memset(&p,0,sizeof(p));p.reference=AW_ACTOR_PLAYER_REF;p.attr_mod[0]=0;
    AW_EffectsReset();
    AW_EffectsLand(&p,102,AW_EFFECT_NO_ARG,1,60,1);AW_EffectsLand(&p,79,0,10,60,1);
    {static aw_actor_t q;memset(&q,0,sizeof(q));q.reference=0x42;AW_EffectsLand(&q,102,AW_EFFECT_NO_ARG,1,60,2);}
    n=AW_EffectsEnd(NULL,AW_ACTOR_PLAYER_REF,102);
    printf("ended %d %d %d %d\n",n,AW_EffectsHas(102),AW_EffectsHasOn(0x42,102),AW_EffectsCount());
    e=p.attr_mod[0];n=AW_EffectsEnd(&p,AW_ACTOR_PLAYER_REF,79);
    printf("fortify %d %d %d\n",e,n,p.attr_mod[0]);
    return 0;
}
'''


# v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): a script's base modifier (ModResistFire / SetResistFire): it adds to the
# magnitude, may go below 0, is not an active spell (GetEffect), survives the clock and the save, and goes at 0;
# a stat effect (Fortify Strength, 79) refused
EFFECT_BASE_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t npc;static unsigned char block[2048];int n,i;
    memset(&npc,0,sizeof(npc));npc.reference=0x42;
    AW_EffectsReset();
    AW_EffectsLand(&npc,90,AW_EFFECT_NO_ARG,25,5,1);
    printf("mod %d %d %d\n",AW_EffectsBaseModify(0x42,90,100),AW_EffectsBaseModify(0x42,28,-30),
           AW_EffectsBaseModify(0x42,79,5));
    printf("now %.1f %.1f has %d %d\n",AW_EffectsMagnitude(0x42,90,AW_EFFECT_NO_ARG),
           AW_EffectsMagnitude(0x42,28,AW_EFFECT_NO_ARG),AW_EffectsHasOn(0x42,90),AW_EffectsHasOn(0x42,28));
    for(i=0;i<6;i++)AW_EffectsTick(&npc,1.0f);
    printf("after6 %.1f count %d\n",AW_EffectsMagnitude(0x42,90,AW_EFFECT_NO_ARG),AW_EffectsCountOn(0x42));
    n=AW_EffectsExport(block,sizeof(block));
    printf("saved %d %d %.1f %.1f\n",n,AW_EffectsImport(block,n),AW_EffectsMagnitude(0x42,90,AW_EFFECT_NO_ARG),
           AW_EffectsMagnitude(0x42,28,AW_EFFECT_NO_ARG));
    AW_EffectsBaseModify(0x42,90,-100);
    printf("back %.1f count %d\n",AW_EffectsMagnitude(0x42,90,AW_EFFECT_NO_ARG),AW_EffectsCountOn(0x42));
    return 0;
}
'''


# v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): the AWFS save block of the forced sneak and the fade
FORCED_HARNESS = r'''
#include <stdio.h>
#include "aw_forced_rules.h"
int main(void){
    unsigned char b[64];uint32_t in[2]={0x01020304u,0xA0B0C0D0u},out[4];int n,player=9,count=9;float fade=-1;
    n=AW_ForcedPack(b,sizeof(b),1,in,2,0.5f);
    printf("pack %d %c%c%c%c %d %d %d small %d\n",n,b[0],b[1],b[2],b[3],b[4],b[5],b[6],AW_ForcedPack(b,18,1,in,2,0));
    {int k=AW_ForcedUnpack(b,n,&player,out,4,&count,&fade);
     printf("unpack %d %d %d %08x %08x %.2f\n",k,player,count,(unsigned)out[0],(unsigned)out[1],fade);}
    {int cut=AW_ForcedUnpack(b,n-1,&player,out,4,&count,&fade),many=AW_ForcedUnpack(b,n,&player,out,1,&count,&fade),tag;
     b[0]='X';tag=AW_ForcedUnpack(b,n,&player,out,4,&count,&fade);
     printf("refused %d %d %d\n",cut,many,tag);}
    n=AW_ForcedPack(b,sizeof(b),0,in,0,2.0f);
    printf("badfade %d %d\n",n,AW_ForcedUnpack(b,n,&player,out,4,&count,&fade));
    /* v0.0.63 (MWSCRIPT-GAPS-63): the AWRN block of the forced run */
    n=AW_ForcedRunPack(b,sizeof(b),1,in,2);
    printf("run %d %c%c%c%c %d %d %d small %d\n",n,b[0],b[1],b[2],b[3],b[4],b[5],b[6],AW_ForcedRunPack(b,14,1,in,2));
    {int k=AW_ForcedRunUnpack(b,n,&player,out,4,&count);
     printf("rununpack %d %d %d %08x %08x\n",k,player,count,(unsigned)out[0],(unsigned)out[1]);
     printf("runrefused %d %d\n",AW_ForcedRunUnpack(b,n-1,&player,out,4,&count),AW_ForcedRunUnpack(b,n,&player,out,1,&count));}
    /* v0.0.63 (MWSCRIPT-GAPS-63): the AWWF block of the werewolf state */
    {unsigned char wb[128];aw_were_t w,r;int i,k;
     w.player=1;w.kept=1;w.kills=300;
     for(i=0;i<8;i++)w.attr[i]=(short)(40+i);
     for(i=0;i<27;i++)w.skill[i]=(short)(5+i);
     w.skill[3]=-2;
     n=AW_WerePack(wb,sizeof(wb),&w,in,2);
     k=AW_WereUnpack(wb,n,&r,out,4,&count);
     printf("were %d %d %d %d %d %d %d %d %08x small %d cut %d\n",n,k,r.player,r.kept,r.kills,r.attr[7],r.skill[26],
            r.skill[3],(unsigned)out[1],AW_WerePack(wb,82,&w,in,2),AW_WereUnpack(wb,n-1,&r,out,4,&count));}
    return 0;
}
'''


# v0.0.61 (PLAYER-CASTING-59): a worn item's Constant Effect: Fortify Strength (79) applied at once and held whatever
# the clock does, a Restore Health (75) acting each second it is worn, both through a save; taken off (its source
# removed) the fortify is undone; a constant effect needs an item source; the generation moves with a load.
EFFECT_CONSTANT_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_effects.h"
int main(void){
    static aw_actor_t p;unsigned char block[1100];int n,ok,i;unsigned long g0,g1;
    memset(&p,0,sizeof(p));p.reference=AW_ACTOR_PLAYER_REF;p.dyn_base[0]=100;p.dyn_cur[0]=50;
    AW_EffectsReset();g0=AW_EffectsGeneration();
    ok=AW_EffectsLand(&p,79,0,10,AW_EFFECT_CONSTANT,AW_EFFECT_SOURCE_CONSTANT+1);
    ok+=AW_EffectsLand(&p,75,AW_EFFECT_NO_ARG,2,AW_EFFECT_CONSTANT,AW_EFFECT_SOURCE_CONSTANT+1);
    ok+=AW_EffectsLand(&p,79,0,10,AW_EFFECT_CONSTANT,7);                       /* refused: a spell's source */
    ok+=AW_EffectsLand(&p,41,AW_EFFECT_NO_ARG,5,3,AW_EFFECT_SOURCE_ITEM);      /* a used item's Light, 3 s */
    printf("landed %d str %d health %.1f count %d\n",ok,p.attr_mod[0],p.dyn_cur[0],AW_EffectsCount());
    for(i=0;i<5;i++)AW_EffectsTick(&p,1.0f);
    printf("after5 str %d health %.1f count %d light %.1f\n",p.attr_mod[0],p.dyn_cur[0],AW_EffectsCount(),
           AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,41,AW_EFFECT_NO_ARG));
    n=AW_EffectsExport(block,sizeof(block));
    /* SAVE-EFFECTS-BLOCK-SIZE-61: the reader's size of the block, by its version; a cut one refused */
    {int whole=AW_EffectsBlockBytes(block,(unsigned long)n+40),cut=AW_EffectsBlockBytes(block,(unsigned long)n-1),v1;
     block[4]=1;v1=AW_EffectsBlockBytes(block,1000);block[4]=2;
     printf("block %d cut %d v1 %d\n",whole,cut,v1);}
    ok=AW_EffectsImport(block,n);g1=AW_EffectsGeneration();
    printf("saved %d %d count %d moved %d\n",n,ok,AW_EffectsCount(),g1!=g0);
    AW_EffectsTick(&p,1e8f);
    printf("long str %d count %d\n",p.attr_mod[0],AW_EffectsCount());
    n=AW_EffectsRemoveSource(&p,AW_EFFECT_SOURCE_CONSTANT+1);
    printf("off %d str %d count %d none %d\n",n,p.attr_mod[0],AW_EffectsCount(),AW_EffectsRemoveSource(&p,AW_EFFECT_SOURCE_CONSTANT+1));
    return 0;
}
'''


CAST_RULES_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_cast.h"
int main(void){
    aw_spell_effect_t e[2];aw_mgef_t m[2];float skill[27];int school,i;float base,ft;
    memset(e,0,sizeof(e));memset(m,0,sizeof(m));
    for(i=0;i<27;i++)skill[i]=5;
    skill[10]=30;skill[11]=20;                         /* Destruction 30, Alteration 20 */
    e[0].effect=14;e[0].range=AW_RANGE_TOUCH;e[0].duration=1;e[0].magnitude_min=2;e[0].magnitude_max=8;
    m[0].base_cost=5;m[0].school=2;                    /* Fire Damage, destruction */
    e[1].effect=41;e[1].range=AW_RANGE_SELF;e[1].duration=20;e[1].magnitude_min=10;e[1].magnitude_max=10;
    m[1].base_cost=1;m[1].school=0;                    /* Light, alteration */
    base=AW_CastBaseChance(e,m,2,skill,50,40,12,0.5f,&school);
    ft=AW_CastFatigueTerm(1.25f,0.5f,50,100);
    printf("base %.2f school %d ft %.2f\n",base,school,ft);
    printf("chance %.2f %.2f %.2f %.2f %.2f %.2f\n",AW_CastChance(base,0,0,0,0,5,ft,100,12,1),
           AW_CastChance(base,0,0,0,0,5,ft,10,12,1),AW_CastChance(base,0,0,1,0,0,ft,100,12,1),
           AW_CastChance(base,5,1,0,0,0,ft,0,12,1),AW_CastChance(base,5,0,0,0,0,ft,0,12,1),
           AW_CastChance(base,0,0,0,3,0,ft,100,12,1));
    printf("cap %.2f %.2f ft0 %.2f\n",AW_CastChance(500,0,0,0,0,0,1,100,1,1),AW_CastChance(-20,0,0,0,0,0,1,100,1,1),
           AW_CastFatigueTerm(1.25f,0.5f,0,0));
    printf("mag %.0f %.0f %.0f %.0f\n",AW_CastMagnitude(2,8,0),AW_CastMagnitude(2,8,0.999f),AW_CastMagnitude(2,8,0.5f),
           AW_CastMagnitude(5,3,0.7f));
    printf("schools %d %d ranges %d dur %.0f\n",AW_CastSchoolSkill(2),AW_CastSchoolSkill(5),AW_CastRanges(e,2),
           AW_CastDuration(&e[0],&m[0]));
    m[0].flags=AW_MGEF_NO_DURATION;
    printf("nodur %.0f\n",AW_CastDuration(&e[0],&m[0]));
    return 0;
}
'''


ITEM_RULES_HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "aw_cast.h"
static void spell(aw_start_spell_t *s,int row,int cost,int flags,int effect,int range,int school,float base,int lo,int hi,
                  int duration,unsigned mflags){
    memset(s,0,sizeof(*s));s->row=row;s->cost=cost;s->flags=flags;s->n=1;
    s->e[0].effect=(short)effect;s->e[0].range=(unsigned char)range;s->e[0].skill=5;s->e[0].attribute=-1;
    s->e[0].magnitude_min=(unsigned short)lo;s->e[0].magnitude_max=(unsigned short)hi;s->e[0].duration=(unsigned short)duration;
    s->m[0].school=school;s->m[0].base_cost=base;s->m[0].flags=mflags;
}
int main(void){
    aw_start_spell_t s[5];aw_start_settings_t set;float sk[27],at[8];int out[8],n,i,race[1]={12};
    printf("cost %d %d %d %d\n",AW_CastItemCost(40,10),AW_CastItemCost(40,60),AW_CastItemCost(40,110),AW_CastItemCost(5,5));
    printf("charge %.1f %.1f %.1f\n",AW_CastItemCharge(30,20),AW_CastItemCharge(20,20),AW_CastItemCharge(19.5f,20));
    for(i=0;i<27;i++)sk[i]=30;
    for(i=0;i<8;i++)at[i]=40;
    spell(&s[0],10,5,2,14,AW_RANGE_TARGET,2,5,2,4,1,0);      /* fire on target, destruction */
    spell(&s[1],11,8,2,41,AW_RANGE_SELF,0,1,5,5,10,0);       /* light on self, alteration */
    spell(&s[2],12,3,6,14,AW_RANGE_TOUCH,2,5,1,1,1,0);       /* always succeeds; the race's own */
    spell(&s[3],13,2,2,83,AW_RANGE_SELF,0,1,5,5,10,1);       /* names skill 5 (30 < 70): refused */
    spell(&s[4],14,9,2,41,AW_RANGE_SELF,0,1,5,5,10,0);
    set.magicka_mult=1;set.chance=50;set.max=100;set.skill_min=70;set.cost_mult=0.5f;
    printf("chance %.2f %.2f %.2f\n",AW_CastStartChance(&s[0],sk,at,0.5f),AW_CastStartChance(&s[1],sk,at,0.5f),
           AW_CastStartChance(&s[2],sk,at,0.5f));
    n=AW_CastStartSpells(s,5,&set,sk,at,race,1,out,8);printf("all %d",n);for(i=0;i<n;i++)printf(" %d",out[i]);printf("\n");
    set.max=2;n=AW_CastStartSpells(s,5,&set,sk,at,race,1,out,8);printf("max2 %d",n);for(i=0;i<n;i++)printf(" %d",out[i]);printf("\n");
    at[1]=6;set.max=100;n=AW_CastStartSpells(s,5,&set,sk,at,NULL,0,out,8);printf("int6 %d",n);for(i=0;i<n;i++)printf(" %d",out[i]);printf("\n");
    at[1]=40;sk[10]=5;n=AW_CastStartSpells(s,5,&set,sk,at,NULL,0,out,8);printf("weak %d",n);for(i=0;i<n;i++)printf(" %d",out[i]);printf("\n");
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class ItemAndStartSpellRuleTests(unittest.TestCase):
    """v0.0.61 (PLAYER-CASTING-59, PLAYER-START-SPELLS-NOT-KNOWN-61): a magic item's charge per use by the Enchant
    skill (OpenMW 0.51 spellutil.cpp getEffectiveEnchantmentCastCost) and the starting spells of a new character
    (autocalcspell.cpp autoCalcPlayerSpells), natively."""

    def test_item_cost_and_starting_spells(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-items-'))
        try:
            (tmp / 'h.c').write_text(ITEM_RULES_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_cast_rules.c'), str(src / 'aw_effects.c'), '-lm', '-o', str(tmp / 'h')],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # cost 40 at Enchant 10, 60 (half off), 110 (none left: at least 1), 5 at Enchant 5 (5.25: a little more);
        # a charge of 20 pays a 20 use, 19.5 does not
        # the fire bolt: 2 x 30 - 5 + 0.2 x 40 + 0.1 x 40 = 67; the light 64; always succeeds 100
        # all: the race's own and the one naming a skill under 70 left out; past 2 the cheapest (fire, 5) gives way to
        # the next one dearer than it; with Intelligence 6 only the spells of cost 6 or less (fire 5; the always one 3
        # now that no race excludes it); Destruction 5: the fire bolt's chance is 17, under 50
        self.assertEqual(out, ['cost 40 20 1 5', 'charge 10.0 0.0 -1.0', 'chance 67.00 64.00 100.00',
                               'all 3 10 11 14', 'max2 2 11 14', 'int6 2 10 12', 'weak 3 11 12 14'])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class CastRuleTests(unittest.TestCase):
    """v0.0.61 (PLAYER-CASTING-59): the casting chance by OpenMW 0.51's rules (spellutil.cpp), natively."""

    def test_chance_fatigue_magnitude(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-cast-'))
        try:
            (tmp / 'h.c').write_text(CAST_RULES_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_cast_rules.c'), str(src / 'aw_effects.c'), '-lm', '-o', str(tmp / 'h')],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # Fire Damage on touch: term 1 x 0.5 x 5 x 0.5 = 1.25 against 2 x 30; Light on self: 20 x 0.1 x 10 x 0.5 = 10
        # against 2 x 20 = 40, the lower: skill 40 (alteration); 40 - 12 + 0.2 x 50 + 0.1 x 40 = 42; fatigue at half
        # 1.25 - 0.5 x 0.5 = 1.0; Sound 5 takes 5; too little magicka, a used power or Silence give 0
        self.assertEqual(out, ['base 42.00 school 0 ft 1.00',
                               'chance 37.00 0.00 100.00 100.00 0.00 0.00',
                               'cap 100.00 0.00 ft0 1.25',
                               'mag 2 8 5 5',
                               'schools 10 15 ranges 3 dur 1',
                               'nodur 1'])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class EffectTests(unittest.TestCase):
    """v0.0.57 (SPELL-EFFECTS-57): Fortify, Drain, Damage and Restore on the player's record, natively."""

    def test_fortify_drain_damage_restore_and_the_save(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # Fortify Strength +10 and Fortify Health +20 at once, Drain Magicka -15; Damage Health 2 a second for 3 s;
        # after 6 s the Fortify Strength and the Drain have ended and are undone, the Fortify Health still holds
        # v0.0.61: the save block is version 2 (16 bytes an effect); the player holds up to 32 of the 64 entries
        self.assertEqual(out, ['start 10 70.0 70.0 25.0 40.0', 'has 1 1 1 0', 'after6 0 64.0 70.0 40.0 1', 'saved 22 1 1',
                               'restore 70.0', 'end 50.0 50.0 0', 'full 32 8', 'bad 0 0'])

    def test_weapon_resistance_magnitudes(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects3-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_RESIST_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # 25 + 15 while both last; the 3-second one ends; the weakness holds 5 s; neither touches health
        # a creature has no skills: Fortify Skill on it changes nothing, nor undoes anything at its end
        self.assertEqual(out, ['now 40.0 20.0 0.0', 'after4 25.0 20.0 health 60.0', 'creature 0 10', 'creature after 0 0'])

    def test_the_forced_sneak_and_fade_save_block(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-forced-'))
        try:
            (tmp / 'h.c').write_text(FORCED_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_forced_rules.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # 11 + 2 x 4 bytes, round trip; a cut block, too many references, a wrong tag and a fade past 1 refused
        self.assertEqual(out, ['pack 19 AWFS 1 1 2 small -1', 'unpack 19 1 2 01020304 a0b0c0d0 0.50',
                               'refused -1 -1 -1', 'badfade 11 -1',
                               # v0.0.63: the forced run, 7 + 2 x 4 bytes, round trip; cut and too many refused
                               'run 15 AWRN 1 1 2 small -1', 'rununpack 15 1 2 01020304 a0b0c0d0', 'runrefused -1 -1',
                               # the werewolf state, 79 + 2 x 4 bytes, round trip (a negative skill kept); small, cut
                               'were 87 87 1 1 300 47 31 -2 a0b0c0d0 small -1 cut -1'])

    def test_summoning_effects_and_one_effect_ended(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects5-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_SUMMON_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # 15 of the base game (102-116), the centurion sphere (134) and the expansions' 6 (137-142)
        self.assertEqual(out, ['summons 22 1 1 1 0', 'ended 1 0 1 2', 'fortify 10 1 0'])

    def test_a_scripts_base_modifier(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects6-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_BASE_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # Resist Fire 25 for 5 s from a spell plus the script's 100; Weakness to Fire's base at -30; Fortify Strength
        # refused; the spell's ends, the base holds (two entries, saved as 6 + 2 x 16); back to 0, it goes
        self.assertEqual(out, ['mod 1 1 0', 'now 125.0 -30.0 has 1 0', 'after6 100.0 count 2', 'saved 38 1 100.0 -30.0',
                               'back 0.0 count 1'])

    def test_constant_effects_of_worn_items(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects4-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_CONSTANT_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # three land (the spell-sourced constant refused); Restore Health 2 a second while worn (50 -> 60 in 5 s), the
        # Light of a used item ends at 3 s; the save keeps the constants (6 + 2 x 16) and the load moves the
        # generation; no clock ends them; taken off, the fortify is undone
        # SAVE-EFFECTS-BLOCK-SIZE-61: the block's size by its version (2 x 16 here; the same count read as version 1
        # would be 2 x 10), a cut block refused
        self.assertEqual(out, ['landed 3 str 10 health 50.0 count 3', 'after5 str 10 health 60.0 count 2 light 0.0',
                               'block 38 cut -1 v1 26', 'saved 38 1 count 2 moved 1', 'long str 10 count 2',
                               'off 2 str 0 count 0 none 0'])

    def test_any_effect_on_any_actor(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-effects2-'))
        try:
            (tmp / 'h.c').write_text(EFFECT_ACTORS_HARNESS, encoding='utf-8')
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(src), str(tmp / 'h.c'),
                                    str(src / 'aw_effects.c'), '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            out = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, check=True).stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # Fire Damage 5 a second for 4 s and Frost Damage 12 at once on the NPC (40 -> 28, then -20 over 4 s);
        # Drain Intelligence 10 for 6 s holds past 5 s; Light and Levitate add their magnitudes on the player and end
        # at 30 and 15 s; the Shield on an actor whose record is not loaded does not tick and survives the save
        # harmful: Fire Damage, Absorb Health, Burden yes; Light, Restore Health, Feather no
        self.assertEqual(out, ['kinds 1 1 -1 0 4', 'persec 1 0 0 1', 'harmful 1 1 0 0 1 0',
                               'landed 6 count 5 2 2 1',
                               'npc 28.0 -10 light 20.0 lev 10.0 has 1 1 0',
                               'owners 2 1234 99',
                               'after5 npc 8.0 -10 count 4 other 1',
                               'saved 70 1 4 15.0',
                               'forget 1 3',
                               'npcfull 34 32 9',
                               'v1 1 1 1 79 ffffffff 10.0 5.0'])


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
                self.assertEqual(f['SCRP_rows'], len(SCRIPTS) + 1)      # and the one dialogue result script (_dlg_0)
                report = json.loads((out / 'mwscript-report.json').read_text())
                self.assertEqual(report['media']['sounds']['mapped'], 2)
                self.assertEqual(report['media']['music']['mapped'], 1)
            self.assertEqual((s.dir / 'out-miss/id1/mwscript.awm').read_bytes(),
                             (s.dir / 'out-hit/id1/mwscript.awm').read_bytes())

    def test_the_image_refuses_scripts_of_another_compiler(self):
        """BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59: v0.0.59 shipped bytecode of an older compiler (a reused
        stage); the image step compares the receipt's compiler with this source's when it installs the file."""
        import build_aga
        import prepare_mwscript
        with SyntheticData() as s:
            media = s.dir / 'media'; media.mkdir()
            (media / 'media-coverage.json').write_text(json.dumps(catalogue()))
            out = s.dir / 'out'
            self.assertEqual(prepare_mwscript.main(['--data-files', str(s.dir), '--media', str(media),
                                                    '--out', str(out)]), 0)
            checked = prepare_mwscript.check_compiler(out)
            self.assertEqual(checked['compiler'], prepare_mwscript.compiler_identity())
            id1 = s.dir / 'image-id1'; id1.mkdir()
            self.assertEqual(build_aga.install_mwscript(out, id1)['source_compiler'], checked['compiler'])
            receipt = json.loads((out / 'mwscript-receipt.json').read_text())
            receipt['inputs']['compiler'] = '9d6be54a' + '0' * 56
            (out / 'mwscript-receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'another compiler'):
                prepare_mwscript.check_compiler(out)
            with self.assertRaisesRegex(ValueError, 'another compiler'):
                build_aga.install_mwscript(out, id1)

    def test_the_stage_keys_its_compiler_whole_in_its_trace(self):
        """The '=' lines the stage writes into its trace name every compiler file (note_compiler_read)."""
        import prepare_mwscript
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / 'trace.txt'
            from unittest import mock
            with mock.patch.dict(os.environ, {'AMIWIND_STAGE_TRACE': str(trace)}):
                prepare_mwscript.note_compiler_read()
            lines = set(trace.read_text().splitlines())
        self.assertIn('=tools/mwscript/functions.py', lines)
        self.assertIn('=tools/mwscript/ident.py', lines)
        self.assertIn('=tools/prepare_mwscript.py', lines)
        self.assertIn('=tools/prepare_combat.py', lines)
        self.assertEqual(len(lines), len(prepare_mwscript.compiler_files()))


if __name__ == '__main__':
    unittest.main()
