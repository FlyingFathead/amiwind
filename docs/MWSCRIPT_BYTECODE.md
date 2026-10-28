# MWScript compiled by the builder

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [How much MWScript there is (measured 23 October 2026)](#how-much-mwscript-there-is-measured-23-october-2026)
  - [What the scripts need](#what-the-scripts-need)
  - [The functions in use](#the-functions-in-use)
  - [A first real case: the census office door](#a-first-real-case-the-census-office-door)
- [The compiler](#the-compiler)
  - [The quirks it keeps](#the-quirks-it-keeps)
  - [What it squeezes](#what-it-squeezes)
  - [The squeeze, measured (27 October 2026)](#the-squeeze-measured-27-october-2026)
- [The file: id1/mwscript.awm (AWMS1)](#the-file-id1mwscriptawm-awms1)
- [The opcode table](#the-opcode-table)
  - [Shared with the greeting conditions](#shared-with-the-greeting-conditions)
- [Sounds, voices and music by index](#sounds-voices-and-music-by-index)
  - [The original's sound markers](#the-originals-sound-markers)
- [The interpreter](#the-interpreter)
  - [Which objects run scripts](#which-objects-run-scripts)
  - [What runs today, what is "not yet"](#what-runs-today-what-is-not-yet)
  - [The import route: every call kept](#the-import-route-every-call-kept)
- [Sizes and costs](#sizes-and-costs)
- [Builder stage](#builder-stage)
- [Next](#next)
- [Credits](#credits)

<!-- contents end -->

Morrowind's game logic is written in MWScript, the game's own script language: 1,207 scripts in the three masters
(Morrowind, Tribunal and Bloodmoon). The Amiga does not read that text while it plays. The builder parses every
script once and writes compact bytecode for a small interpreter in the engine, as the roadmap decided on
18 October 2026 ([ROADMAP.md step 6](ROADMAP.md)). This page is the design: how much MWScript there is, what the
compiler squeezes out of it, the file, the opcode table (shared with the NPC greeting conditions), what runs today,
what does not yet, and what it costs.

The first target, at the maintainer's request (23 October 2026: "all of the audio is already in the game so we
should start utilizing it as per MWscript"), is audio: the sounds, voice lines and music cues the scripts start.
Status: **EXPERIMENTAL**, compiled in every build, run by the engine only with `dbg mwscript on` (setting
`aw_mwscript`, off by default) until the in-game check. Register entry:
[MWSCRIPT-AUDIO-FIRST-48](bugs/MWSCRIPT-AUDIO-FIRST-48.md).

## How much MWScript there is (measured 23 October 2026)

Every SCPT record of each master, compiled with the master's own records (`python3 -m mwscript.measure`, in the
builder container; the per-script table stays private, these are the totals):

| | Morrowind | Tribunal | Bloodmoon | The game (each id once, the last master wins) |
| --- | ---: | ---: | ---: | ---: |
| Scripts | 632 | 263 | 336 | 1,207 |
| Source text | 514,172 bytes | 214,283 | 252,109 | 942,627 |
| The original editor's compiled form | 216,421 bytes | 94,553 | 106,774 | 400,397 |
| AmiWind bytecode (27 October 2026) | 67,088 bytes | 31,614 | 38,924 | 132,376 (33 % of the original's) |
| Distinct functions used | 207 | 126 | 120 | 251 |
| Function calls | 5,827 | 2,470 | 3,516 | 11,365 |
| Not compiled | 0 | 0 | 0 | 0 |

The 1,207 are 616 Morrowind scripts, 255 Tribunal scripts and all 336 of Bloodmoon (the add-ons replace 24
earlier ones). Every one compiles since v0.0.54. Four Bloodmoon scripts read a name declared nowhere in the game data
(a journal id used as a variable, "if ( BM_BearHunt1 == 0 )"), and one of them also puts the player before a local
("Player->fakeiswere"); until v0.0.54 the compiler refused them. Now it reads them as OpenMW does (the two rules
under [The quirks it keeps](#the-quirks-it-keeps)), with a warning in its report.

Other counts: 143 globals, 318 journal topics, 4 start scripts, 37 locals at most in one script, a stack of 12 cells
at most, 1,476 bytes of bytecode in the longest script, `while` loops in 5 scripts. Placed objects that carry a
script: 8,758 in Morrowind.esm (4,907 of them run something today, see [inert](#which-objects-run-scripts)).

### What the scripts need

| Share of the 1,207 scripts | Scripts |
| --- | ---: |
| Use only the interpreter, audio, the journal and globals | 134 (11 %) |
| Run whole today (everything they call is carried out; 27 October 2026) | 735 (61 %) |
| Touch audio at all | 192 (16 %) |
| Use AI packages (travel, wander, follow, escort, fight/flee settings) | 181 (15 %) |
| Use the inventory (add, remove, count items on others, equip, soul gems) | 194 (16 %) |
| Use combat (start/stop combat, on death, attacked, weapon drawn) | 293 (24 %) |
| Use spells and effects (add/remove spells, cast, diseases, effects) | 140 (12 %) |
| Use positioning (position, place, move, rotate, angles, scale) | 152 (13 %) |
| Use at least one of those five | 668 (55 %) |

"Run whole today" is larger than "audio, journal and globals" because the player's item counts
(`player->GetItemCount`) are game state the engine already keeps. Most of the rest also need object state
(`Enable`, `Disable`, `GetDisabled`, `OnActivate`, locks: roadmap step 4), menus and messages (`MessageBox`), or
stats and dialogue.

### The functions in use

The 40 most used functions over the whole game (calls in the source):

GetJournalIndex 1,364, Disable 830, Journal 600, Enable 498, GetDisabled 434, MessageBox 407, GetDistance 301,
MenuMode 295, OnActivate 280, GetDeadCount 247, OnDeath 245, GetItemCount 241, RemoveItem 239, GetSecondsPassed
235, SetFight 234, CellChanged 208, StartCombat 205, Say 182, AddSpell 173, AddItem 157, Activate 146, StopScript
143, GetPCCell 139, ForceGreeting 134, AIWander 130, GetPos 127, Cast 126, StopCombat 119, PlaySound 108, AddTopic
105, GetAIPackageDone 99, PositionCell 95, GetHealth 94, AITravel 89, HasSoulGem 85, PlayGroup 84, SayDone 79,
RemoveSpell 77, GetButtonPressed 76, SetHello 75.

Per master, the top of the list: Morrowind GetJournalIndex 530, Journal 314, MessageBox 285, Disable 266, MenuMode
183; Tribunal GetJournalIndex 274, Disable 218, Enable 140, GetItemCount 102, Journal 90; Bloodmoon GetJournalIndex
641, Disable 359, GetDisabled 274, Enable 242, Journal 207.

### A first real case: the census office door

The maintainer's first test case (23 October 2026): after the release papers in the census office, the door stays
shut until the papers are taken, and a guard tells the player to step aside. In the original that is not a door
script: the door has none. It is the script of the guard standing by it. Every frame, unless a menu is open: if the
player is within 180 units, and carries the papers, and the guard has finished speaking, he says his "continue
through" line, unlocks the door and plays its lock sound at the door, gives back fighting and magic, and is done;
without the papers he repeats his "no further" line, held back by a timer that resets every 3 seconds and only
speaks when it reads exactly 0 (a quirk the bytecode keeps: the line is heard when a frame lands on the reset).

Compiled: 142 bytes from 1,000 bytes of source, 2 locals. With the compiler and interpreter of this page it runs as
written except three calls: `Unlock` on the door (object state, roadmap step 4), and `EnablePlayerFighting` /
`EnablePlayerMagic` (player controls). Distance, the item count, `Say`, `SayDone`, the timer, `MenuMode` and the
lock sound all run. So the compiled script could replace today's hand-written story rule (`aw_opening.c`) once
those three exist; until then the opening's scripts are on the hand-written list (`config/mwscript.json`
`handwritten`, every script whose name starts with "chargen", 21 scripts), compiled and measured but not run, so
nothing happens twice.

## The compiler

`tools/mwscript/` (Python, run by the builder in its container):

| Module | Does |
| --- | --- |
| `lexer.py` | tokens, with the original editor's tolerances |
| `functions.py` | every function and instruction: return type, arguments, group, whether the engine runs it |
| `parser.py` | statements and expressions to a small tree |
| `codegen.py` | typed stack bytecode, the program's shared tables |
| `compiler.py` | all scripts in two passes (every script's locals first, for member access), bindings |
| `awms.py` | the file: writer, reader, decoder, disassembler |
| `media.py` | script sounds, voices and music to the media catalogue's converted files |
| `opcodes.py` | the opcode table (the engine's copy: `engine/aga/src/aw_mwcode.h`) |
| `measure.py` | the measurement above |

### The quirks it keeps

The language as the game data uses it, learned from OpenMW's compiler (components/compiler) and checked against
all 1,231 SCPT records:

- `,` and `:` are spaces; `[ ]` are brackets; `;` comments to the end of the line;
- names may start with a digit and hold `` ` `` and `'`; a `-` between name characters stays in the name;
- `=` (79 times in the data), `= =` and `<==` are read as the comparison they mean;
- a string that reaches the end of its line ends there;
- `if` and `while` need no brackets; junk after `else` is skipped (8 times: `else set x to 8` does **not** set x,
  as in OpenMW); stray `endif`s are skipped (34 times); a missing `endif` closes at the end;
- `set` of an undeclared variable skips the line, with a warning (a handful of lines in the data, as OpenMW);
- a name in an expression that is no variable, function or global reads as a number: its leading digits, else 0
  (OpenMW's parser does this for old content; four Bloodmoon scripts, v0.0.54);
- a reference before a name that is no function (`Player->fakeiswere`, a local) is dropped and the name read as it
  is (OpenMW: "stray explicit reference"; one Bloodmoon script, v0.0.54);
- `id->( OnDeath == 1 )`: an explicit reference before a bracket applies to the calls inside;
- `"script".var` / `id.var`: another script's or object's variable; an empty member reads 0;
- `PositionCell "cell" x y z r` with the cell first (Bloodmoon) is read in the documented order;
- optional arguments the game ignores (`StopCombat x`, `Disable x`, `Face x y z`) are read and dropped;
- whole-number division stays whole, a short stores 16 bits, a float to a whole number truncates.

### What it squeezes

- Every value is typed at build time: whole numbers and fractions have their own opcodes, conversions only where
  types meet, so whole-number scripts run on integer instructions only.
- Constants are folded (`2 * 30` is stored as 60), branches on a constant are dropped, the last `if` branch with no
  `else` falls through instead of jumping over nothing, each constant takes its smallest push (1, 3 or 5 bytes).
- Names become indexes: globals, journal topics, sounds, voices, music tracks, objects, scripts, strings.
- Each script is marked **VOLATILE** when it reads something outside the game state (time, distance, chance, a
  sound still playing, `SayDone`, an engine query); only those must run every frame.
- A script is **INERT** when nothing it can do today is seen outside its own values (only not-yet calls; no sound,
  global, journal, other object, script start or stop) and no other script reads its values: compiled and counted,
  its placements left out of the file, never run. 119 scripts today (230 before the actor calls of v0.0.54); each
  one comes back by itself when a function it calls is carried out and the file is compiled again.
- A script that reads the actor record (a stat, an item count, a spell, OnDeath, a dead count) is not VOLATILE: it
  is marked ACTOR and runs again when the state it can read changes. A script's own change of an actor moves the
  state generation as a global does, and the engine moves it when a fight changes an actor's health or an actor
  dies, so OnDeath and GetHealth tests run on those events instead of every frame.
- **Compare and branch** (v0.0.54): an `if` or `while` that tests a whole number against a constant from -128 to
  127, the most common test in the game's scripts (`if ( x == 1 )`), is one opcode instead of three: `JNEB` for
  `==`, `JCMPB` for the other comparisons (4 or 5 bytes instead of 6).
- **CellChanged is not VOLATILE** (v0.0.54). It reads 1 only on the run after an object was attached or came into
  range, and the interpreter runs a script then anyway; the run after it also runs (CellChanged reads 0 again, which
  is what the original's sound markers wait for: "if ( CellChanged == 0 ) if ( GetSoundPlaying ... == 0 )
  PlayLoopSound3DVP ..."). `GetSoundPlaying` asks only about the script's own sounds: the script acted when it
  started one, and the engine wakes it when a one-shot sound ends (loops restart by themselves). So a sound marker
  runs twice and then sleeps until its object leaves and comes back, instead of running every frame.

### The squeeze, measured (27 October 2026)

The whole game compiled twice from the same commit, once without compare and branch (the reference) and once with
it; both runs without the media catalogue, so only the code differs:

| | Without | With | Change |
| --- | ---: | ---: | ---: |
| Bytecode (CODE) | 142,480 bytes | 129,862 bytes | -12,618 (-8.9 %) |
| Resident while scripts are on | 176,072 bytes | 163,456 bytes | -12,616 |
| Opcodes in the code | 61,517 | 46,999 | -14,518 |
| Compare-and-branch opcodes | | 7,259 (5,359 `JNEB`, 1,900 `JCMPB`) | |

Opcodes a frame, natively, the method of the table in [Sizes and costs](#sizes-and-costs) (every scripted object of
a 3 by 3 cell block attached, 600 frames of 1/20 s, sounds reported as still playing). Like for like: both runs
attach the same objects and make the same calls; every call to the engine (sounds, voices, journal, object state,
actor calls) and the final globals and locals were written out and the two lists compared: identical in all five
blocks (the same SHA-256 prefix).

| Block | Scripts run a frame | Opcodes a frame, without | With | Change |
| --- | ---: | ---: | ---: | ---: |
| Vivec (3, -10) | 44 | 426 | 240 | -44 % |
| Seyda Neen (-2, -9) | 14 | 162 | 96 | -41 % |
| Cells around (-11, 15) | 15 | 214 | 146 | -32 % |
| Balmora (-3, -2) | 4 | 58 | 36 | -38 % |
| Empty sea (0, 0) | 2 | 46 | 28 | -39 % |

CellChanged without VOLATILE, measured the same way (27 October 2026, the v0.0.54 branch): the whole program
compiled once, a second file made from it with every script that reads CellChanged marked VOLATILE again (142
scripts: the old rule); the same interpreter runs both. Like for like: every call to the engine and the final globals
and locals were written out for each block in three sound cases (sounds always playing; never playing; every sound
ending each 40th frame, the engine then waking the scripts) and compared: identical in all fifteen runs (the same
SHA-256). Opcodes a frame with sounds playing, as the table above:

| Block | Scripts run a frame, before | After | Opcodes a frame, before | After | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vivec (3, -10) | 44 | 3.1 | 240 | 37.4 | -84 % |
| Seyda Neen (-2, -9) | 14 | 7 | 96 | 63.1 | -34 % |
| Cells around (-11, 15) | 15 | 5 | 146 | 98.4 | -33 % |
| Balmora (-3, -2) | 4 | 3 | 36 | 33.1 | -8 % |
| Empty sea (0, 0) | 2 | 1 | 28 | 25.1 | -10 % |

Measured against the integration head before the change (be93bf6c, its own compiler and interpreter, the same
recipe): the same "before" numbers, so the v0.0.54 world lookups below add no work a frame in these blocks. The
host's interpreter time a frame, natively on the build machine (relative only, not the Amiga's): Vivec 1.2 to
0.36 microseconds.

The actor calls themselves (v0.0.54) made the program smaller before the squeeze: CODE 147,531 to 142,480 bytes
(not-yet calls with their names became small opcodes) and the resident part 177,768 to 176,072 bytes although the
actor table's OACT section (1,302 bytes) joined it; they also make the scripts do more (their calls are carried out
instead of logged): Vivec's block 422 to 426 opcodes a frame, the others 4 to 16 more.

## The file: id1/mwscript.awm (AWMS1)

Big-endian. A 16-byte header ("AWMS", version 1, section count, file bytes, resident bytes) and a directory of
sections. The sections up to CODE are the resident part, kept in memory while scripts are on; BIND and STRS stay
on disk.

| Section | Row | Holds | Bytes (the game) |
| --- | --- | --- | ---: |
| CONF | 8 | activation range, opcodes per frame, opcodes per run (from `config/mwscript.json`) | 8 |
| GLOB | 8 | type (short, long, float), name, initial value | 1,144 |
| JRNL | 2 | journal topic name | 636 |
| SNDS | 18 | pool name (8 bytes), length, volume, mapped, near and far hearing distance, name | 1,476 |
| VOIC | 12 | pool name, length, path | 1,584 |
| MUSI | 4 | soundtrack track number, mapped, path | 4 |
| OBJS | 12 | reference (if placed once), id, script, placed count, kind | 1,992 |
| SCRP | 16 | name, locals, stack, flags, code offset and length | 19,312 |
| STRT | 2 | start scripts | 8 |
| PCEL | | the cells each `GetPCCell` name matches (v0.0.54): per name the rooms by stable number and the outdoor cells by grid, made at build time | 1,692 |
| PMOV | 20 | the player's PositionCell moves (v0.0.54): kind (outdoors, into a room), the room map's name, x y z, yaw | 420 |
| CODE | | the bytecode | 132,376 |
| BIND | 24 | placed scripted objects, by reference: script, flags, cell (grid or the room's stable number), position | 117,768 (4,907 rows) |
| STRS | | strings (names for the log, messages, ids of not-yet calls) | 145,333 |
| OACT, ACTB, AINV, AITM, ASPT, ASPL | | the actor table (v0.0.54; OACT resident, the rest on disk): [ACTOR_STATE.md](ACTOR_STATE.md) | 536,338 |
| | | file / resident | 446,316 / 183,212 |

CODE, PCEL and PMOV measured 27 October 2026 (v0.0.54, without the media catalogue: the whole file 1,062,900 bytes
with the actor table, 168,348 resident); the other rows are from earlier measurements.

A pool name is the 8 bytes of a converted file's name in the media catalogue, `sound/pool/a<16 hex>.wav`.

## The opcode table

A stack machine of 32-bit cells; operands follow their opcode, big-endian. `engine/aga/src/aw_mwcode.h` and
`tools/mwscript/opcodes.py` hold the same numbers; `tests/test_mwscript.py` checks that they agree.

| Code | Opcode | Operands | Does |
| --- | --- | --- | --- |
| 00 01 | END, RET | | stop this run |
| 02 03 | JMP, JZ | s16 | jump (JZ pops a whole number, jumps on 0); from the end of the operand |
| 04-07 | PUSHB, PUSHW, PUSHL, PUSHF | s8, s16, s32, f32 | constants |
| 08-0A | GETL, SETL, SETLS | u8 slot | this object's locals (SETLS stores a short) |
| 0B-0D | GETG, SETG, SETGS | u16 global | globals |
| 0E-10 | GETM, SETM, SETMS | u16 object, u8 slot | another object's or script's locals |
| 11 12 13 | GETJ, SETJ, JOURNAL | u16 topic | journal index: read, set (either way), Journal (forward only, adds the entry) |
| 14 15 | I2F, F2I | | conversions (F2I truncates) |
| 16-1A | ADDI SUBI MULI DIVI NEGI | | whole-number arithmetic (division by 0 gives 0) |
| 1B-1F | ADDF SUBF MULF DIVF NEGF | | fraction arithmetic |
| 20-25 | EQI NEI LTI LEI GTI GEI | | whole-number comparisons, push 0 or 1 |
| 26-2B | EQF NEF LTF LEF GTF GEF | | fraction comparisons |
| 2C | POP | | drop a value |
| 2D | REF | u16 object (FFFF the player) | the next call acts on this object |
| 2E | QUERY | u8 query, u16 operand | an engine fact (table below), pushes a whole number |
| 2F | NOTYET | u16 function number, u16 name, u8 flags, u8 strings, u16 per string | a function not carried out yet ([the import route](#the-import-route-every-call-kept)): counted by its number, handed to the engine's `call()` with its numbers and strings, logged once when the engine does not carry it out, its numbers popped, 0 (or the engine's answer) pushed if it has a value (flags: low 5 bits numbers, 80 has a value, 40 a fraction, 20 had a reference) |
| 30-35 | PLAYSOUND, PLAYSOUNDVP, PLAYSOUND3D, PLAYSOUND3DVP, PLAYLOOP3D, PLAYLOOP3DVP | u16 sound | VP forms pop pitch and volume |
| 36 37 | STOPSOUND, SOUNDPLAYING | u16 sound | |
| 38 39 | SAY, SAYDONE | u16 voice, u16 text | |
| 3A | STREAMMUSIC | u16 music | |
| 40-43 | SECONDS, RANDOM, MENUMODE, CELLCHANGED | | GetSecondsPassed (time since this script's last run), Random n, ... |
| 44-46 | STARTSCRIPT, STOPSCRIPT, SCRIPTRUNNING | u16 script | global scripts |
| 47 48 | DISTANCE, SQRT | u16 object / - | GetDistance in game units, GetSquareRoot |
| 49-4E | ENABLE, DISABLE, GETDISABLED, LOCK, UNLOCK, GETLOCKED | - | object state (v0.0.51) on the object REF names, else the script's own; LOCK pops the level (-1: the level it had, as `Lock` without a number); GETDISABLED and GETLOCKED push a whole number |
| 4F 50 | ONACTIVATE, ACTIVATE | - | activation (v0.0.51): ONACTIVATE pushes 1 once after the player used the script's object (the script took the use); ACTIVATE carries out the object's own use |
| 51 | MESSAGEBOX | u16 text, u8 numbers, u8 buttons, u16 per button | a message box (v0.0.51): its numbers popped (each a number with a fraction) and formatted into the text, its buttons by string index |
| 52 | GETBUTTONPRESSED | | pushes the button the player chose, once; -1 until then |
| 53 | ACTOR | u8 verb, u8 stat | the actor record (v0.0.54, [ACTOR_STATE.md](ACTOR_STATE.md)) of REF's object or the script's own: get and ratio push, set, mod and modcurrent pop (a whole number for level, the behaviour ratings, disposition and OnDeath, else a fraction) |
| 54 | ITEM | u8 verb, u16 item | 0 GetItemCount (pushes), 1 AddItem, 2 RemoveItem (pop the count); the item is a row of the actor table's shared items |
| 55 | SPELL | u8 verb, u16 spell | 0 GetSpell (pushes), 1 AddSpell, 2 RemoveSpell, 3 GetCommonDisease and 4 GetBlightDisease (push; any spell of that type in the actor's list, the spell operand unused; v0.0.54) |
| 56 | COMBAT | u8 verb, u16 object | 0 StartCombat against the object (FFFF the player), 1 StopCombat |
| 57 | DEADCOUNT | u16 actor | GetDeadCount of an actor id (FFFF: an id no actor has, 0) |
| 58 | AIWANDER | u8 extra | pops range, duration, time and EXTRA more whole numbers (AIWander's arguments) |
| 59 | JNEB | s8 k, s16 | pops a whole number, jumps when it is not k (the squeeze) |
| 5A | JCMPB | u8 test, s8 k, s16 | pops a whole number, jumps when "number test k" is false (0 ==, 1 !=, 2 <, 3 <=, 4 >, 5 >=) |
| 5B | GETPCCELL | u16 PCEL row | pushes 1 when the player stands in one of the row's cells (v0.0.54) |
| 5C | GETPOS | u8 axis | pushes REF's object's (or the script's own) position on the axis (0 x, 1 y, 2 z), game units (v0.0.54) |
| 5D | PLAYERMOVE | u16 PMOV row | the player's PositionCell, worked out at build time: into a room (its map, the arrival) or outdoors (v0.0.54) |
| 5E | AIPACKAGE | u8 verb | pushes REF's actor's (or the script's own) AI package: 0 GetCurrentAIPackage (-1 none, 0 Wander, ...), 1 GetAIPackageDone (v0.0.54) |

QUERY numbers: 1 the speaker's disposition, 2 PC level, 3 PC sex, 4 PC reputation, 5 PC crime level, 6 PC health
percent, 7 PC rank in a faction (operand: faction string, FFFF the speaker's), 8 PC expelled (same operand), 9 PC
knows a spell, 10 item count on the player (operand: item id string), 11 dead count, 12 PC gold, 13 PC clothing
value, 14 same faction, 15 the speaker's rank, 16 PC werewolf, 17 PC vampire, 18 talked to the PC, 19 PC attribute
(0-7), 20 PC skill (0-26), 21 weather, 22 game hour. Today the engine answers 10; the others read 0.

### Shared with the greeting conditions

The NPC greeting and voice table (branch v0.0.48-npc-greetings) compiles each INFO record's conditions to the same
bytecode, so one interpreter runs both. What that side uses: GETG for a global condition, GETJ for a journal
condition, GETL / GETM for a local or another object's variable, QUERY for disposition and the player's state (the
numbers above; a new fact gets the next free number in both `opcodes.py` and `aw_mwcode.h`), the PUSH opcodes for
the condition's value, the whole-number or fraction comparison by the variable's type, JZ to the next candidate
line, END when a line is chosen. Its strings (faction, item, spell ids) are indexes into the same STRS form. A
condition the engine cannot answer compiles to QUERY with its number and reads 0 (logged once), never to a private
opcode.

## Sounds, voices and music by index

Every sound a script names resolves at build time to the converted file in the media catalogue
(`tools/prepare_media_assets.py`): no audio is copied, the file holds the converted file's pool name.

- `PlaySound*`, `PlayLoopSound*`, `StopSound`, `GetSoundPlaying` name a SOUN record: its file, volume and hearing
  distances (the record's min and max times the game settings fAudioMinDistanceMult and fAudioMaxDistanceMult, the
  defaults when both are 0; rule from OpenMW's sound code, values from the game data);
- `Say` names a voice file under Sound; `StreamMusic` a file under Music, which becomes the soundtrack's own
  track number (`music/trackNN.mws`).

What each does follows OpenMW's script sound rules (apps/openmw/mwscript/soundextensions.cpp): the 2D forms play on
the listener, the 3D forms on the reference, a loop until `StopSound`, `GetSoundPlaying` asks about that reference's
sound, `Say` plays the voice file on the actor with its text only as a subtitle, `SayDone` reads the actor's say
finished. The dialogue's own voice lines (greetings, combat taunts, hit and flee lines) go through OpenMW's
DialogueManager::say instead (apps/openmw/mwdialogue/dialoguemanagerimp.cpp), which also refuses an actor that is
already speaking, an NPC under water and a knocked-down actor; AmiWind's greeting and combat tables carry that rule
([NPC_VOICE_TABLE.md](NPC_VOICE_TABLE.md)), not a script's `Say`. The pool file of a sound is the same one the voice
table names (the media pool, `sound/pool/a<16 hex>.wav`); one shared row table for both is being agreed (v0.0.54).

Measured on the v0.0.48-dev2 media catalogue: **82 sounds, 81 mapped**; **132 voice files, 131 mapped**; **1 music
file, 0 mapped**. 71 voice names ask for a `.wav` where the data has the `.mp3` (the game plays the `.mp3`): mapped,
with that note. Not mapped, each with its reason: one sound whose file is missing from the game data (a test sound),
one voice file missing from the game data (one of the 7 missing voice sources the catalogue already reports), and
one music file that is not in the soundtrack (a developer's test door). The stage prints every unmapped name with its
reason (`[warning: unmapped ...]`) and writes them to `mwscript-report.json`.

### The original's sound markers

Morrowind places invisible editor markers whose scripts play a looping or 3D sound when the player is near: water
under the Khuul pier, creaking under bridges and boats, cave wind and drips, spirit voices in tombs, Dwemer
machinery. The converters already keep them as invisible deferred placements with their role
(`tools/editor_markers.py`, the "nonvisual source marker" records of CHIMport), never drawn. Their scripts now
compile like every other: each marker keeps its reference number, and the bindings the engine reads at a map change
place its script at the marker's spot; nothing is added to the maps.

Measured 23 October 2026 (`tools/editor_markers.py census` against the compiled file):

| | Sound markers | Cells |
| --- | ---: | ---: |
| Morrowind, outdoors | 187 | 78 |
| Morrowind, rooms | 1,976 | 434 |
| Tribunal (rooms) / Bloodmoon (13 outdoors, 106 in rooms) | 283 / 119 | not in the image yet |
| All | 2,565 | 613 |

All 2,163 Morrowind markers are bound in the file with their sound mapped to a converted file. The most placed
sounds: Cave Wind 523, Cave Drip 444, Spirit Ambient Voices 301, Boat Creak 254, Haunted 241, Ambient Factory Ruins
121, Dock Creak 68, Lava Layer 52, Daedric Chant 52. The busiest outdoor cell is Khuul's (-11, 15) with 9; Seyda
Neen's (-2, -9) has 5. Each plays with its SOUN record's volume and hearing distances; pitch is not available in
Quake's mixer. Besides the markers, 2,112 other placed objects (activators, containers, NPCs) have scripts that
play a 3D sound. The built world draws none of the markers: `editor_markers.py check-built` on the v0.0.48-dev2
Balmora MiniWind run found 0 problems in 54 scenery indexes. Register:
[SOUND-MARKERS-SILENT-48](BUGS.md).

## The interpreter

`engine/aga/src/aw_mwvm.c`: a switch on opcodes, no engine headers, everything from the game through a host table
(`aw_mwhost.c` in the engine, stubs in the native tests). Every script's code is checked once at load (opcodes,
operands, table indexes, jump targets), so the loop does no bounds checks. Its tables (65,716 bytes) are taken once
when the scripts are switched on; nothing is allocated while scripts run.

- A script runs only while its object is **active**: within the activation range of the player (12,288 game
  units, one and a half exterior cells; the original runs the 3 by 3 cells around the player), or in the loaded room.
- A script that is not VOLATILE and whose last run changed nothing and called nothing runs again only after the state
  it can read has changed (a global, a journal index, another object's variable, a script started or stopped).
- An opcode budget per frame (4,000) is shared round robin; a script left over waits at the head of the next frame.
  One run stops after 2,000 opcodes (an endless loop), logged once.
- NOTYET calls are logged once per function name, never a crash.

### Which objects run scripts

At each map change (`aw_mwhost.c`): every edict whose original reference (`aw_ref`) has a script in the file's
bindings (NPCs, creatures and the objects the maps keep as edicts), and on an outdoor map every scripted placement
inside the map (sound markers and other activators the CHIM frames keep without an edict, placed by their position
in the game data), and in a room every scripted placement of that room (the room map's stable interior number,
worldspawn `_aw_cell_int`, matches the binding's; room maps are the game positions at a quarter scale, and a
recentred room's shift is taken from one of its edicts). The bindings are read from disk at the map change and not
kept. Not attached: the hand-written list, inert scripts, and more than 256 edict-less placements in one room. An
object's values are kept while its map is not loaded (512 objects, 4,096 values). Room placements are not
checked in game yet ([MWSCRIPT-INTERIOR-PLACEMENTS-48](BUGS.md)).

### What runs today, what is "not yet"

Runs: variables, `if`/`elseif`/`else`, `while`, `set`, arithmetic and comparisons, globals, another object's
variables, `GetJournalIndex`, `SetJournalIndex`, `Journal`, `GetSecondsPassed`, `Random`, `MenuMode`,
`CellChanged`, `StartScript`, `StopScript`, `ScriptRunning`, `GetDistance`, `GetSquareRoot`, `player->GetItemCount`,
and audio: `PlaySound`, `PlaySoundVP`, `PlaySound3D`, `PlaySound3DVP`, `PlayLoopSound3D`, `PlayLoopSound3DVP`,
`StopSound`, `GetSoundPlaying`, `Say`, `SayDone`, `StreamMusic`. Loops repeat when their sample ends and stop when
their object leaves the range. Quake's mixer has no pitch, so the VP forms keep their volume only; voices play on
the speaker without lip movement yet.

Object state (v0.0.51): `Enable`, `Disable`, `GetDisabled`, `Lock`, `Unlock`, `GetLocked`, on the script's own
object or the one named before `->`. A disabled object with an entity is hidden and not solid until `Enable`, also
after a map change (its new entity is hidden again); `Lock` without a number takes the level the object had last
(100 when it never had one). Both are kept in saved games, by the object's reference, in the same change list as the
actors' state (an object's entry carries "disabled" and "lock set, level"). An actor the CHIM world spawns as its
cell joins is not spawned while disabled; after `Enable` it comes with its cell's next join. Not yet: CHIM scenery
without an entity keeps showing when disabled (its collision is part of the CHIM chunk, so hiding it alone would
leave an invisible wall). Doors that turn in place
(hinged doors) follow a script's lock: the opening's own locks come first, then the script's, then the game data's;
`GetLocked` on a door no script has touched reads the game data's lock. Load doors into rooms read no lock at all
yet ([DOOR-LOAD-LOCKS-MISSING-51](BUGS.md), waiting for a way to open a lock: keys, lockpicks, the Security skill).

Activation (v0.0.51): `OnActivate` and `Activate` run, with the original's rule. A script that reads `OnActivate`
takes over its object's use: when the player uses the object, it does nothing by itself, and `OnActivate` reads 1
once on the script's next run; the script's `Activate` then carries out the object's own use (a door opens, locks
kept). Today the use is taken over for doors (hinged doors and load doors); other objects' own use (items,
containers, actors) is not yet. A script the engine carries by hand (the census office's) is never attached, so its
door keeps the engine's own rules. The `aw_mwscript_status` command counts the uses the scripts took and their
`Activate` calls.

Messages (v0.0.51): `MessageBox` and `GetButtonPressed` run, as OpenMW shows them. The text takes its numbers
(`%d`, `%f`, `%g` and `%e` with a precision, `%%`; a `%s` is kept as written, the compiler passes no strings). A box
without buttons is a notice in the message line for its length times 0.1 s (3 to 10 s). A box with buttons stops
the world until the player chooses (Left/Right or A/D move, Enter, Space, E or the mouse choose, 1-9 choose that
button); a new box replaces a shown one, and `GetButtonPressed` reads the choice once, -1 until then
(`engine/aga/src/aw_msgbox_rules.c`, `aw_msgbox.c`).

The actor record (v0.0.54, [ACTOR_STATE.md](ACTOR_STATE.md)): every attribute's, skill's and dynamic stat's Get,
Set and Mod, `ModCurrent` and the `GetRatio` forms, `GetLevel`, `SetLevel`, the behaviour ratings' Get, Set and
Mod (`SetFight`, `SetHello` and the rest), `GetDisposition`, `SetDisposition`, `ModDisposition`, `OnDeath`,
`GetDeadCount`, `AddItem`, `RemoveItem` and `GetItemCount` on any actor (the player's own items are the game state
the engine keeps), `AddSpell`, `RemoveSpell`, `GetSpell`, `StartCombat` (with the player), `StopCombat` (through the
combat layer's per-actor end when it is in the build), and `AIWander` (handed to the ambient tables' wander when
they are in the build). 87 functions moved from "not yet" to running; the scripts that use them, by function (a
script counted once per function): OnDeath 221, StartCombat 106, GetDeadCount 105, RemoveItem 81, AddItem 77,
SetFight 73, AIWander 73, GetHealth 69, AddSpell 52, StopCombat 40, SetHealth 33, SetHello 30. Scripts that run whole
(everything they call carried out): 390 before, 635 after (of 1,207).

The world and cell lookups (v0.0.54): `GetPCCell` compares the player's cell with the cells its name matches
(every cell whose name starts with it, without case: a room's name, an outdoor cell's own name, else its region's
name, else the game setting sDefaultCellname; rule from OpenMW's cellextensions.cpp). The builder turns each name
into a row of rooms (stable numbers) and outdoor cells (grid) once, so the engine compares numbers and never text,
and the engine moves the state generation when the player's cell changes, so the scripts that ask are not run every
frame. `GetPos` reads the position of the script's object or the one named before `->` in game units (OpenMW's
transformationextensions.cpp). `GetCommonDisease` and `GetBlightDisease` look for a spell of that type in the
actor's spell list and its changes (OpenMW's hasCommonDisease and hasBlightDisease); the player catches no disease
from creatures yet, so on the player they read 1 only after a script gave one. `DontSaveObject` compiles to nothing
and `Xbox` to 0, as OpenMW has them. 6 functions moved from "not yet" to running: scripts that run whole 635 before,
697 after (of 1,207; GetPCCell alone was the last missing call of 25 of them).

`PositionCell` of the player (v0.0.54; rule from OpenMW's transformationextensions.cpp OpPositionCell): the builder
works each such move out once (the PMOV section, 20 bytes a move), when its numbers are constants. Into a room: the
room's map name and the arrival in the map's own units, by the doors' rule (the room lists of the repo: a town or scene
list's map name, else the batch room's; a recentred room's offset first; a quarter scale and the feet lifted; the
player's rotation is in degrees), loaded the way a door loads it. Outdoors, and for a cell that is no interior (as
OpenMW does): the coordinate teleport of `dbg tp X Y Z`, the view keeping its direction. A room whose map is not on
the disk (a batch room the build did not convert), a pending load or the story's hold: nothing happens, counted in
`aw_mwscript_status`. Measured 27 October 2026: 22 of the game's PositionCell calls are the player's and carried out
(21 moves, 19 of them into rooms); 74 stay "not yet": moving an NPC or a creature into another cell waits for the
object state's table of moved actors (roadmap step 4), and a few of the player's go into rooms no repo list names yet
(Tribunal and Bloodmoon). Scripts that run whole: 715 of 1,207.

`GetCurrentAIPackage` and `GetAIPackageDone` (v0.0.54; rules from OpenMW's aiextensions.cpp): the actor's package as
the ambient tables run it (`AW_AmbientAiPackage`, through the engine's `aw_mwscript_ai_package`), with OpenMW's
numbers (-1 none, 0 Wander; Travel, Escort, Follow and Activate come with those packages), -1 for a dead actor, and
"done" once a wander that does not repeat has run out. The ambient tables move the state generation when a package
starts or ends, so these scripts are not run every frame. Without the ambient tables in the build both read -1 and
0. Scripts that run whole: 735 of 1,207.

Not yet (124 functions; by the number of scripts using them): ForceGreeting 98, PositionCell (other actors) 57, Cast 53,
PlayGroup 29, GetPCRank 26, AITravel 24, PlaceItem 24, GetPCCrimeLevel 23, Rotate 21, GetEffect 21, AddTopic 20. The
most called: ForceGreeting 134, Cast 126, AddTopic 105, AITravel 89, HasSoulGem 85, PlayGroup 84, PositionCell 74.
They wait for the dialogue window, moving actors between cells, spells and effects, the other AI packages, a crime
level and animation. The scripts' own values are not in saved games
yet ([MWSCRIPT-STATE-NOT-SAVED-48](BUGS.md)).

### The import route: every call kept

Every script of the game is in the file and every call in it is compiled, also the ones the engine does not carry
out yet (v0.0.54, the maintainer's "the stuff that is in there would exist in some form, even if it's not plugged
in yet"). Such a call is a NOTYET instruction that keeps all of it: the function's number (its place in the
compiler's table, `tools/mwscript/functions.py`, the names in alphabetical order), its name, its numeric arguments
(computed by the script's own code and handed over in order) and its string arguments (ids, cell names, animation
groups, by string index; a reference's id first). The interpreter counts every such call by function number and hands
it to the engine's `call()`: when the engine carries a function out by its number, the scripts use it with no new
opcode and no change of the file's format (the stage compiles the program again in a few seconds, so a script that
was left out as [inert](#what-it-squeezes) comes back). Until then the call is logged once and reads 0.
`aw_mwscript_status` lists the not-yet functions this session called most, with their counts. A function used
very often gets its own opcode later, as the actor calls did, when that is faster.

## Sizes and costs

| | |
| --- | ---: |
| `id1/mwscript.awm` | 446,316 bytes (183,212 resident while on) |
| Interpreter code (68040, -O1) | 9,720 bytes |
| Engine side code / data | 5,876 / 10,960 bytes |
| Interpreter tables (taken when switched on) | 65,716 bytes, plus 3,840 for the import route's counters (v0.0.54) |
| Journal names (taken when switched on) | 318 topics, 22,896 bytes |
| Compile time, the whole game | 2.5 s, one unit, reused from the pool when unchanged |

Interpreter work per frame, measured natively on the real file: every scripted object of a 3 by 3 cell block attached
and in range, 600 frames of 1/20 s, sounds reported as still playing (so the ambient loops ask every frame; the worst
case for work):

| Block | Objects | Global scripts | Scripts run a frame | Opcodes a frame (first frame) |
| --- | ---: | ---: | ---: | ---: |
| Vivec (3, -10) | 52 | 3 | 54 | 514 (393) |
| Seyda Neen (-2, -9) | 11 | 3 | 10 | 121 (218) |
| Cells around (-11, 15) | 14 | 3 | 16 | 190 (224) |
| Balmora (-3, -2) | 1 | 3 | 3 | 47 (130) |
| Empty sea (0, 0) | 0 | 3 | 2 | 42 (141) |

Before inert scripts were left out and NOTYET values stopped counting as VOLATILE, Vivec's block ran 107 scripts and
2,242 opcodes a frame. With the squeeze and CellChanged without VOLATILE (27 October 2026, the tables in
[The squeeze, measured](#the-squeeze-measured-27-october-2026)): Vivec 3.1 scripts and 37.4 opcodes a frame, Seyda
Neen 7 and 63.1, the cells around (-11, 15) 5 and 98.4, Balmora 3 and 33.1, the empty sea 1 and 25.1.

**Estimate, not a measurement on the machine:** the 68040 code of the loop is a fetch, a two-range jump table and
the opcode's body, about 25 to 45 cycles an opcode; at 25 MHz about 1.2 to 1.6 microseconds. Vivec's 514 opcodes
were then about 0.6 to 0.8 ms a frame (37 since v0.0.54: about 0.05 ms); N active scripts cost about N times 15 microseconds (about 9.5 opcodes a run
here, plus the activation test); the budget caps the interpreter at about 5 ms a frame. To be measured in game
(`dbg mwscript status`, the frame profile) before any default.

## Builder stage

`mwscript` (`tools/prepare_mwscript.py`), CHIM builder, default on, after media and music: one unit keyed by the
SHA-256 of the masters, the media catalogue, the soundtrack, `config/mwscript.json` and the compiler's source;
reused from the shared pool when unchanged. Writes `mwscript/id1/mwscript.awm`, `mwscript-report.json` (counts,
sizes, every unmapped sound with its reason) and `mwscript-receipt.json`. The image step checks the file against the
receipt's SHA-256, reads it back, and links it into the payload. The legacy builder's plan is unchanged.

## Next

1. In-game check in a MiniWind sandbox (Seyda Neen docks and Vivec's water spouts): sounds, loops, ranges, frame
   time with and without; then the default. The session that decides it: the Seyda Neen and Vivec MiniWinds on
   the slow preset, the same scripted walk twice (scripts off, then `dbg mwscript on`), the frame profile and
   `aw_mwscript_status` every 10 s; it passes when the sound markers start and stop with their range, nothing the
   scripts do shows twice next to a hand-written rule, no run reaches the opcode limit, the not-yet list holds no
   surprise, and the frame time grows by less than 1 ms.
2. Object state (roadmap step 4): `Enable`, `Disable`, `GetDisabled`, `Lock`, `Unlock` and `GetLocked` run since
   v0.0.51 and are saved; next: the doors read a script's lock, `OnActivate` and `Activate` (the census door),
   Disable on CHIM scenery and on actors the CHIM world spawns, and the interpreter's own values in saved games.
3. Room placements checked in game: the stable room number and the quarter-scale positions, a recentred room's
   shift.
4. The greeting conditions on the same interpreter (`MessageBox` runs since v0.0.51).

## Credits

The rules of the language (argument kinds, the scanner's tolerances, how `else` junk and unknown variables are
treated, the sound distance rule) were learned by reading OpenMW 0.51's script compiler and sound code (GPL-3.0,
components/compiler and apps/openmw); AmiWind's compiler and interpreter are its own code, nothing copied
([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
