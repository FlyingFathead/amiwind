# MWScript compiled by the builder

_Last updated with AmiWind v0.0.68-dev5 (22 November 2026)._

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
  - [Held actors and falls](#held-actors-and-falls)
  - [What runs today, what is "not yet"](#what-runs-today-what-is-not-yet)
  - [The import route: every call kept](#the-import-route-every-call-kept)
- [Spell effects: the design (SPELL-EFFECTS-57)](#spell-effects-the-design-spell-effects-57)
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

The first target, at the maintainer's request (23 October 2026: the audio is already in the game, so it should now be
used as the scripts direct), is audio: the sounds, voice lines and music cues the scripts start.
Status: compiled in every build and **on by default since v0.0.57** (setting `aw_mwscript`, default 1, saved;
the builder also states `aw_mwscript 1` in the game's default settings). `dbg mwscript off` switches the scripts
off and stops their sounds; `dbg mwscript` alone, `on` and `off` answer in the console what the scripts do,
whether `id1/mwscript.awm` was loaded (format, bytes on disk, scripts, bytes kept) and the
`aw_mwscript_status` counts ([DBG-MWSCRIPT-SILENT-56](BUGS.md)). The in-game check is still the open item (Next 1).
Register entry:
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
| Run whole today (everything they call is carried out; 30 October 2026) | 957 (79 %) |
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
| `newgame.py` | the scripts a new game starts once and their build check (v0.0.62) |
| `events.py` | the actors held on an object a script disables, and the census of distance-triggered world events (v0.0.62) |

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
  one comes back by itself when a function it calls is carried out and the file is compiled again. Seen, so never
  inert (v0.0.62, MWSCRIPT-INERT-SEEN-62): a message box; reading OnActivate (the object's use goes to the script, so
  a blocked door stays shut and an item the script keeps cannot be taken); and setting a local that a dialogue filter
  reads (an INFO's Local or NotLocal condition reads the speaker's attached script at run time), for a script an NPC
  or a creature record carries. 15 scripts of the masters came back by this (blockedDoor, DoorBarricaded, noPickUp,
  templeStewards and others; 25 more bindings).
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
| CONF | 20 | activation range, opcodes per frame, opcodes per run (from `config/mwscript.json`); then the script engine's table sizes counted from the whole game (v0.0.66-dev12, `tools/mwscript/plan.py`): attached instances, their local values, parked objects, parked values. The engine allocates exactly these at load; an older file's 8-byte CONF gives it the earlier constants (256, 4,096, 2,816, 9,216). The three masters: 791 instances, 1,475 values, 5,478 parked objects, 12,811 parked values | 20 |
| GLOB | 8 | type (short, long, float), name, initial value | 1,144 |
| JRNL | 2 | journal topic name | 636 |
| SNDS | 18 | pool name (8 bytes), length, volume, mapped, near and far hearing distance, name | 1,476 |
| VOIC | 12 | pool name, length, path | 1,584 |
| MUSI | 4 | soundtrack track number, mapped, path | 4 |
| OBJS | 12 | u32 reference (if placed once), u16 id, u16 script, u16 placed count, u16 kind (1: the id names a script, its global instance); the engine reads the row through one set of readers, and a script's read or write of another object's variable finds that object's script there (up to v0.0.66-dev10 it took the id for the script, so every such read gave 0 and every write was lost) | 1,992 |
| SCRP | 16 | name, locals, stack, flags, code offset and length | 19,312 |
| STRT | 2 | start scripts | 8 |
| NEWG | 2 | the scripts a new game starts once (v0.0.62): Main's new-game block, [below](#which-objects-run-scripts) | 6 |
| HELD | 20 | an actor standing on an object a script disables (v0.0.62): the actor's and the object's references, the actor's placed position, [below](#held-actors-and-falls) | 20 (1 row) |
| PCEL | | the cells each `GetPCCell` name matches (v0.0.54): per name the rooms by stable number and the outdoor cells by grid, made at build time | 1,692 |
| PMOV | 20 | the player's PositionCell moves (v0.0.54): kind (outdoors, into a room), the room map's name, x y z, yaw | 420 |
| VISI | 12 | the actors a PositionCell may bring into a room (v0.0.62), sorted: the room's stable number, the actor's reference, its home room map's name (none: outdoors or a room the build lacks) | 12 a row |
| PADD | 8 | every carryable item record that names a script (v0.0.62), sorted by the FNV-1a of its folded id: the hash, the script, the slot of its OnPCAdd local (0xFF: none). The item's script runs while the player carries one (OpenMW 0.51's rule): its carried instance starts when the item arrives and at every map change while it is carried, and stops when the last one leaves the inventory. A script with OnPCAdd gets that local set to 1 on arrival: on the placement the player took (its own values go on), else on the carried instance. The game's masters give 186 rows, 3 of them with OnPCAdd (the census papers and the courtyard ring among them) | 1,488 (186 rows) |
| LACT | 8 | every NPC or creature record a levelled creature list names that has a script (v0.0.62), sorted by the FNV-1a of its folded id (the actor table's base hash): the hash, the script, 0. The actor a levelled list gives runs its record's script under the list's reference from its spawn (OpenMW 0.51's rule); its values are kept as any placed actor's | 656 (82 rows) |
| PLAC | 12 | every object a Place call names (v0.0.62), sorted by id: the id, a template reference of the same record and its home room map's name, the record's script, the kind (NPC or creature, carried item, other) and whether the engine can make it, [below](#what-runs-today-what-is-not-yet) | 492 (41 rows) |
| WATR | 8 | every room whose cell has the water flag (v0.0.68), sorted by the room's stable number: the number, the flag, the room's water level in the original's units (its record's INTV or WHGT, a later master's record winning; the flag alone: 0). `GetWaterLevel` reads the loaded room's row: 0 outdoors, the room's own level in a room with water, the lowest float in a room without (OpenMW 0.51's rule). Before, the engine looked for water in the player's column and read 0 where it found none, which a room whose water lies under every placement (its map holds no water) read for its own level | 1,896 (237 rows by the three masters' records) |
| CODE | | the bytecode | 132,376 |
| BIND | 24 | placed scripted objects, by reference: script, flags, cell (grid or the room's stable number), position | 117,768 (4,907 rows) |
| STRS | | strings (names for the log, messages, ids of not-yet calls) | 145,333 |
| TOPC | 2 | the game's dialogue topics, sorted (v0.0.57): name; on disk, AddTopic hands the row | 4,196 |
| OACT, ACTB, AINV, AITM, ASPT, ASPL | | the actor table (v0.0.54; OACT resident, the rest on disk): [ACTOR_STATE.md](ACTOR_STATE.md) | 536,338 |
| LOCN | 8 + 4 a variable | the scripts' variables by name (v0.0.66, on disk, read only while a game is saved or loaded): per script with variables that is not a dialogue result script, its row, variable count, flags and first key; then a key per variable (the folded name's hash and its type). Saved values carry their variable's key, so a rebuilt script gets each value back in the variable of its name ([SAVEGAME_PLAN.md](SAVEGAME_PLAN.md), eighth part) | 16,208 (811 scripts, 2,430 variables) |
| HITM | 8 | the items placed holders hold (v0.0.66, on disk): a held item's reference and the hash of its item id, so a save keeps its script values by holder and item | 3,928 (491 rows) |
| SCRH | 4 | every script row's name hash (v0.0.66, on disk): a saved script whose row moved is found with one read | 34,472 (8,618 rows) |
| RGNS | 2 | the region catalogue's ids in its order (v0.0.68, on disk): the id as the region's record writes it; row N is the region index a compiled `ChangeWeather` or `ModRegion` hands the engine. The console's `ChangeWeather` and `ModRegion` find a typed id here (a few small reads a line, never in a frame of play) and `dbg weather` names the region it shows. An older file has none: the console then names no region | 32 (16 rows: the three game files' regions; 18 with the base game alone) |
| WERE | 4 | the werewolf's game settings as a compiled `BecomeWerewolf` and `SetWerewolfAcrobatics` hand them to the engine (v0.0.68, on disk): nine rows of the eight attributes and 27 skills from the `fWereWolf` settings, a byte each, four to a row (255: no setting), then the Acrobatics value. The console's `BecomeWerewolf` and `SetWerewolfAcrobatics` read them (ten small reads a line); an older file has none and the console's player forms refuse | 40 (10 rows) |
| EFFN | 2 | the magic effects' game setting ids without `sEffect`, in the game's numbering (v0.0.68, on disk): row N is the number a compiled `GetEffect` hands the engine. The console's `GetEffect` finds a typed id here (one read of the section, then the names up to the match, never in a frame of play); an older file has none and the console takes a number only | 286 (143 rows) |
| CELN | 24 | the cells a console line can name (v0.0.68, on disk): every interior cell (its stable number, its room map's name and recentring), every exterior cell name, every district the build presents as exterior cells (its move), sorted by the 32-bit FNV-1a of the name with A-Z lowered. The console's `PositionCell`, `PlaceItemCell`, `AIFollowCell` and `AIEscortCell` find a typed cell here by a binary search (about a dozen reads of 24 bytes, then the name) and work it out as the compiler does; its `GetPCCell` reads a room's name by its number. Rows of one hash are each checked by their own name (the three game files have no two names of one hash). An older file has none: the console's cell forms refuse | about 34,000 (1,423 rows: 1,328 interiors and 95 exterior names of the three game files) |
| CELG | 4 | every exterior grid cell by the name OpenMW gives it (v0.0.68, on disk): its own name, else its region's, else `sDefaultCellname`; a presented district's block cells by the district's name. The console's `GetPCCell` outdoors reads the player's cell here (a binary search) | about 6,300 (1,559 grid cells of the three game files and the presented blocks) |
| | | file / resident | 446,316 / 183,212 |

CODE, PCEL and PMOV measured 27 October 2026 (v0.0.54, without the media catalogue: the whole file 1,062,900 bytes
with the actor table, 168,348 resident); LOCN, HITM and SCRH computed 14 November 2026 from the v0.0.66-dev2 file (both
expansions); the other rows are from earlier measurements. The builder refuses a file in which two scripts, two
globals, two quests or two worn items share the name hash a save keeps them by.

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
operands, table indexes, jump targets), so the loop does no bounds checks. Its tables are taken once when the
scripts are switched on, in one block; nothing is allocated while scripts run.

**The tables are sized by the build** (v0.0.66-dev12: fixed in source and covered by tests, not yet seen in a session,
`EXPANSION-SCRIPT-LIMITS-66`; one limit stays: 4 live copies per scripted Place row in one map, a fifth is refused with a
console line and counted, `MWVM-PLACE-COPIES-FOUR-66`; up to dev11 they were constants: 256 attached instances, 4,096
local values, 2,816 parked objects, 9,216 parked values, so a map with more scripted placements left the rest without
their scripts, and a long game lost values once the store was full). The builder counts the whole game, both expansions
included, whether or not the image binds their worlds (`tools/mwscript/plan.py`): the busiest loaded map (a 3 by 3
block of exterior cells or one interior: Raven Rock's block has 350 scripted placements, Mournhold's Temple Courtyard
213) with its held items and the levelled-list placements that can give a scripted actor, every global script that can
have an instance at once (the start scripts, every script a StartScript names, the new game's run-once scripts, the
carried items' scripts: 251), the copies the scripts' Place calls can make and the two scratch instances; for the
parking store every object whose script has a local value (3,496 of the 11,423 bound, with 10,499 values), the carried
items' scripts, the levelled placements and the copies. The counts go into the file's CONF and the engine allocates
exactly that (about 180 KB of tables for the three masters, 97 KB with the old constants); a table running out is told
to the engine every time and counted (`dbg mwscript status` shows the plan against the session's peaks): at a map change
that is a clear stop with the numbers (the plan was wrong), elsewhere (a console's StartScript) the one action is
refused in the console. An object whose script has no local value is not parked: there is nothing to keep. OpenMW keeps
a reference's locals with the reference (`apps/openmw/mwworld/refdata.hpp`, `setLocals`) and its local scripts in a list
with no bound (`mwworld/localscripts.cpp` `add`, `addCell`); the counted plan is this engine's way to the same result
without a heap that grows in play. A script-made copy (a trap's projectile, a summoned creature) that is deleted or whose
key is given back is forgotten: its values go with it, so the store does not fill with gone copies.

**A member operation is one step** (`"object".variable`, v0.0.66-dev12): each object row remembers its attached
instance, and the parked store is hashed by reference, so a read or write of another object's variable never walks the
instance table or the store (the 99 every-frame object scripts of the masters hold 307 such operations; up to dev11 each
walked up to 256 instances and 2,816 parked objects).

- A script runs only while its object is **active**: within the activation range of the player (12,288 game
  units, one and a half exterior cells; the original runs the 3 by 3 cells around the player), or in the loaded room.
- A script that is not VOLATILE and whose last run changed nothing and called nothing runs again only after the state
  it can read has changed (a global, a journal index, another object's variable, a script started or stopped). A
  script whose variables another script reads is SHARED (the compiler's whole-program pass): its own change of such a
  variable moves the state too, so the reader wakes and sees it on the next frame instead of sleeping through it
  (v0.0.66-dev12; 44 scripts of the masters are read by others, 9 of their readers had been quiet).
- An opcode budget per frame (4,000) is shared round robin; a script left over waits at the head of the next frame.
  One run stops after 2,000 opcodes (an endless loop), logged once.
- NOTYET calls are logged once per function name, never a crash.

### Which objects run scripts

At each map change (`aw_mwhost.c`): every edict whose original reference (`aw_ref`) has a script in the file's
bindings (NPCs, creatures and the objects the maps keep as edicts), and on an outdoor map every scripted placement
inside the map (sound markers and other activators the CHIM frames keep without an edict, placed by their position
in the game data), and in a room every scripted placement of that room (the room map's stable interior number,
worldspawn `_aw_cell_int`, matches the binding's; room maps are the game positions at a quarter scale, and a
recentred room's shift is taken from one of its edicts). A placement in one of Mournhold's districts, which the game
data keeps as an interior cell and the build presents as outdoor frames, is bound with flag 16 (presented) at the
place the presented world gives it: it keeps the room flag (every script of the district runs while it is loaded, as
in the original's interior cell) and is placed on the district's frame when it has no edict (v0.0.68; until then none
of the five districts' 366 scripted objects ran: the ambient sounds, the Temple courtyard's living and dead trees,
the Plaza's attack rubble, Azura's statue outside the Temple). The bindings are read from disk at the map change and not
kept. Not attached: the hand-written list, inert scripts, and placements past the build's planned instance count (refused
and counted; see [the interpreter](#the-interpreter)). An
object's values are kept while its map is not loaded, in the parking store the build sized for every object of the
game whose script has values ([above](#the-interpreter)). Room placements are not checked in game yet
([MWSCRIPT-INTERIOR-PLACEMENTS-48](BUGS.md)).

Global scripts: the game data's start script records (Tribunal's and Bloodmoon's) start when the file loads and again
at every load of a save. The original also always runs its global script Main (OpenMW 0.51 globalscripts.cpp adds it
before the start script records), and a new game sets CharGenState to 1 (OpenMW worldimp.cpp), so Main's block under
that test starts the new game's run-once scripts: Startup and VampireCheck (and the character creation script, which
the engine carries by hand). Startup's `->Disable` lines take 102 references out of the world until a quest brings
them back: the twelve Dreamers on the roads and in the towns, the Dreamer Prophet, the falling mage north of Seyda
Neen, quest characters, creatures and a few objects. Until v0.0.62 nothing started Main, so all of them stood in the
world from the first minute ([NPC-STORY-DISABLED-AT-START-42](bugs/NPC-STORY-DISABLED-AT-START-42.md)). Since
v0.0.62 the builder reads the scripts Main starts in that block and writes them as the NEWG section (2 bytes a
script, resident); the engine starts each once when a new game begins, by any opening (the ship, a quick start, a
test scene), and then Startup disables them through the object state, which saved games keep. A disabled reference's
own script keeps running, as in OpenMW (World::disable keeps the local script), so a Dreamer's script enables it when
the main quest reaches its stage. The build check (`tools/mwscript/newgame.py`, run by the stage) refuses a file whose
new game would start nothing, or one where a reference placed once that these scripts disable is not bound to its
reference number; the stage report lists the counts (`new_game` in `mwscript-report.json`). Measured on the game data,
7 November 2026: 3 scripts in the block (2 run, the character creation script is carried by hand), 102 disabled
references, 78 of them actors, 101 placed once and every one bound, 1 placed twice (a plate, left as it is).
`aw_mwscript_status` counts the new games and the scripts started. A save made before v0.0.62 keeps the world it had.

### Held actors and falls

v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61. The falling mage north of Seyda Neen is not scripted to fall. He stands on
an invisible platform high above the road; his journal's script enables him when the player comes within 2,000 units,
disables the platform two seconds later, and plays two screams through the player (`"player"->Say`, two seconds and
four more after). The game's physics does the rest: with the platform gone he falls, and the fall damage on landing
kills him (OpenMW 0.51: the platform's collision leaves with `Disable`, mwphysics/movementsolver.cpp drops the actor,
mwmechanics/character.cpp charges the landing). AmiWind has no collision for an invisible marker box, so the same
thing is built as a general mechanism, by a rule on the data, not by name:

- **The builder** (`tools/mwscript/events.py`, run by the mwscript stage) finds every NPC or creature that stands on
  a placed activator, static, container or door that some script disables (an `ID->Disable` in any script or dialogue
  result, or the object's own script calling `Disable`) and that is placed once: its feet at most 32 game units
  sideways from the object and up to 128 above it. Each pair is a HELD row: the actor's reference, the object's and
  the actor's placed position. Measured on the game data, 7 November 2026: 1 row, the mage on his platform (his feet
  50 units above it, 15 sideways); 7 other actors stand near such an object but beside or below it (the stage report
  lists them with the reason).
- **The engine** (`engine/aga/src/aw_fall.c`) holds a HELD actor at its placed position while its object is there: the
  floor snap at spawn (`aw_scene.c AW_NPCFloor`) leaves it, and a ground point baked by a frame or the actor table is
  replaced by the row's position. Once a script disables the object (or the player takes it), the actor falls: OpenMW's
  gravity (8.96 m/s squared, 627 game units/s squared) in steps of 1/60 s, every drop counted as the fall height, until
  its hull meets the ground or water. The fall starts only when something collidable is under it (the streamed ground
  may not be ready yet). The landing costs the fall damage of the next section, taken from the actor record's health
  with the game's Health Damage sound; under 1 health it dies as by a blow, so `OnDeath` reads 1 (the journal's script stops) and
  the body lies where it landed and can be searched. `aw_mwscript_status` shows the rows, the actors tracked and their
  state (held, waiting for ground, falling, landed), the falls and the last fall's height and loss.

**Fall damage** (the player and every actor; `aw_move_rules.c`, rules from OpenMW 0.51 written independently): below
the game setting fFallDamageDistanceMin (400) nothing; above it the height less 400, less 1.5 times Acrobatics and the
Jump magnitude (not below 0), times fFallDistanceMult (0.07) plus fFallDistanceBase (0), times fFallAcroBase (0.25)
plus fFallAcroMult (0.01) times (100 minus Acrobatics). The health lost is that times 1 minus a quarter of the fatigue
term. Nothing landing in water, nothing in god mode. The fall height grows only while the actor is in the air and
starts again on the ground, under water, while levitating and while any Slowfall is on, so a Slowfall landing never
hurts (OpenMW mtphysics.cpp). The five settings are read from the game data with the movement settings
(`combat/settings.txt`). For the mage: about 2,460 units, Acrobatics around 15: 157 damage, 108 health at full fatigue,
where he has 5.

**Slowfall** (OpenMW physicssystem.cpp and movementsolver.cpp): the factor 1 minus the magnitude times 0.005 (0 to 1)
multiplies the falling speed once each 1/60 s, so a Slowfall settles at a slow, steady descent. On an actor (a Slowfall
spell cast on the mage before the platform goes) and on the player alike. The player still falls with the engine's own
gravity, several times the original's ([PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md)); the fall height,
and so the damage, does not depend on the speed.

Not yet: a hard landing's knockdown (the damage over Acrobatics times the fatigue term; the combat layer's knockdown
starts only in a fight) and an NPC's landing sound (DefaultLand); [FALL-LANDING-KNOCKDOWN-62](BUGS.md).

**Seen in game** (7 November 2026, Seyda Neen MiniWinds at 32 MB Fast): held until the trigger, enabled by his journal's
script (his hidden edict shown again with its model and solidity, his disabled row cleared and the platform's added),
drawn standing on the platform and in the air on the last part of his fall, the fall of 2,468 units, 117.9 health
lost, dead, the body drawn where it landed and searchable with the original loot. Both screams start (`Say: 2
started, 0 not started`, on the player). His only greeting ("Greeting 0") has the result `Goodbye`, and
`dbg mwscript result "Greeting 0" "agronian guy"` runs it to the Goodbye. What the player does not
see is the draw distance: the trigger is 500 map units from his journal and he stands 617 above the ground, past the
default draw distance of 300, so from the road the fall is out of sight until near its end
([SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62](BUGS.md)). `aw_mwscript_status` counts the scripts' `Say` calls (started, not
started for want of an actor, a voice row or a sample, the last one's actor and length): the two screams of the event.
`dbg sweep` counts the actors a script disabled (and those the opening hides) apart, not as "without a model", and
fails a disabled actor that is still drawn.

**The census of distance-triggered events.** The stage report (`distance_events` in `mwscript-report.json`) lists
every script that tests the player's distance and then changes the world (enables, disables, attacks, places, moves,
makes an actor fall), with the object each is placed on. Game data, 7 November 2026: 90 scripts, 92 rows; 25 scripts
placed in Vvardenfell, 65 without a placement there (placed in the add-ons' worlds, which the image does not hold yet,
or on records the game spawns while it runs). What they do: disable 59, enable 44, attack 33, greet 32, place 14,
speak 13, walk 13, follow 9, move 7, play a sound 7, fall 1.
Among them: the slave hunters at Khuul, four fighters who attack in exterior cell 11, 20, Dagoth Ur's chamber and Azura's end, the
Moon and Star's cavern, Hannat Zainsubani, Ragash gra-Shuzgub, the white guar, and in the add-ons the Raven Rock colony, the
werewolf and hunter events and Almalexia's and Sotha Sil's ends.

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
after a map change (its new entity is hidden again). Since v0.0.67 that holds for every load of a map, the map already
in play included: a teleport inside the place or a reload of it attaches the map again, so the Plaza Brindisi Dorom's
fabricants and the Dreamers Startup disabled in Seyda Neen stay hidden; before, such a load drew them, because the
engine told a new map by its file and name alone and a `Disable` of a reference already disabled did nothing
([PLAZA-FABRICANTS-LIVE-AT-START-67](bugs/PLAZA-FABRICANTS-LIVE-AT-START-67.md)). A `Disable` of a disabled reference
whose entity is still drawn hides it as well (counted in `dbg mwscript status`, "map attach"); `Lock` without a number takes the level the object had last
(100 when it never had one). Both are kept in saved games, by the object's reference, in the same change list as the
actors' state (an object's entry carries "disabled" and "lock set, level"). An actor the CHIM world spawns as its
cell joins is not spawned while disabled; since v0.0.62 its entity text is kept while its cell stays in the window (16
at most, a few hundred bytes each), and an `Enable` spawns it on the next tick, as the original shows an enabled
actor at once; before, it came only with its cell's next join (SCRIPTED-EVENT-FALLING-MAGE-61). Not yet: CHIM scenery
without an entity keeps showing when disabled (its collision is part of the CHIM chunk, so hiding it alone would
leave an invisible wall). Doors that turn in place
(hinged doors) follow a script's lock: the opening's own locks come first, then the script's, then the game data's;
`GetLocked` on a door no script has touched reads the game data's lock. Load doors into rooms read no lock at all
yet ([DOOR-LOAD-LOCKS-MISSING-51](BUGS.md), waiting for a way to open a lock: keys, lockpicks, the Security skill).

Activation (v0.0.51): `OnActivate` and `Activate` run, with the original's rule. A script that reads `OnActivate`
takes over its object's use: when the player uses the object, it does nothing by itself, and `OnActivate` reads 1
once on the script's next run; the script's `Activate` then carries out the object's own use (a door opens, locks
kept). Since v0.0.66 the use is the script's only while the script reads `OnActivate`: reading it takes the
next use, the object's `Activate` gives it back, and a script that returns before its `OnActivate` line after that
leaves the object its own use (OpenMW 0.51 keeps the same rule, `mwworld/refdata.cpp`). The census office's two
scripted doors are built that way: once opened, their script marks itself done and returns before `OnActivate`, so
the doors open as plain doors every time after, also when the player comes back into the room. Before, a script
that merely contained `OnActivate` took every use, and those doors opened only once
([CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66](BUGS.md)). Before a script's first run on a newly loaded map the object
has its own use. Today the use is taken over for doors (hinged doors and load doors); other objects' own use (items,
containers) is not yet. Since v0.0.57 actors too: E on an actor whose script reads `OnActivate` talks to nobody and
the script's `OnActivate` reads 1 (`pr_cmds.c`, the same intercept as the doors'); the script's `Activate` on an
actor does nothing yet (OpenMW would open the talk or the corpse's inventory). Measured 30 October 2026: 258 scripts
read OnActivate; placed on activators 71 scripts (1,525 placements), books 11, doors 6, NPCs 8 (8 placements),
items and containers the rest. Activators too (v0.0.57): E with no actor under the crosshair goes to the scripted
placement that reads OnActivate nearest the line of view, within the original's activation distance (iMaxActivateDist,
192 game units) and a narrow cone, also when the CHIM world keeps it without an entity (the script's instance has its
position); that covers the 71 activator scripts (1,525 placements) and the books, items and containers whose scripts
read OnActivate. Their own use without a script (picking an item up, opening a container) is not yet. A script the engine carries by hand (the census office's) is never attached, so its
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
from creatures yet, so on the player they read 1 only after a script gave one. `DontSaveObject` and `Fall` compile
to nothing and `Xbox` to 0, as OpenMW has them (`Fall` since v0.0.62: the falling mage's script calls it, and his fall
is the physics after his invisible platform is disabled). 6 functions moved from "not yet" to running: scripts that run whole 635 before,
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

`PositionCell` of anything but the player (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62; rules from OpenMW's
transformationextensions.cpp OpPositionCell, our own code). The builder works the destination out once: an interior
cell by its name (its stable number, and x, y, z in that room map's own units: a recentred room's offset first, then a
quarter scale, as the builder places a resident), else an exterior cell by its name (the original's units); the
rotation of anything but the player is in minutes of arc (60 a degree), turned into Quake's yaw; a cell the game does
not have compiles to nothing, as OpenMW does nothing then. The call goes to the engine through the import route (x, y,
z, yaw, the kind, the room's number, the cell's name; no new opcode). Each actor such a move may bring into a room is a
row of the VISI section (the room, the actor's reference, its home room's map), 12 bytes a row, resident. In the
engine (aw_mwhost.c `position_cell`, aw_actors.c):

- into the place loaded now, the actor loaded: it is put there and turned; its row of the world change list keeps
  where it stands (CELL-CHANGES-59), so it stays there after leaving and coming back and after a save and a load;
- into another place: the actor's row says where it is now (the room's number and its position there, or outdoors
  its island position); a loaded actor leaves this map at the end of the frame, not while a conversation or a menu is
  open (its own script's values parked as a map change parks them), and its entity is kept for the session;
- its home leaves it out from then on: a room or a town map frees it when its actors take their rows, a joining CHIM
  frame does not spawn it;
- a room spawns its arrivals when it loads: for each VISI row of the room whose actor's row puts it there, its
  entity from this session's copy, else from its home room's map (one file open, the map's header and its entity
  lump in one read each), spawned as a joining frame's actor is, its own script attached again;
- into the room loaded now, the actor not loaded: it arrives at once the same way.

Not carried yet, counted in `aw_mwscript_status` ("PositionCell: ..."): an actor that arrives outdoors while its home
frame is not in the window stands there once its home frame joins (no outdoor arrival table yet); an object that is no
actor moved to another place; the player's own PositionCell into a room the build lacks (still "not yet": the
Tribunal and Bloodmoon rooms). Measured 7 November 2026 with the feature tracker (MWSCRIPT_FEATURES.md): scripts that
run whole 409 before, 433 after (of 1,207); 26 of the 30 scripts PositionCell alone held moved (24 run, 2 are placed
only in an add-on world); the 4 left are the player's into rooms the build lacks; every dialogue result that calls it
(14) now runs, 7,366 of 7,411 results whole.

Cost (the budget sheet): resident, the VISI rows (12 bytes each; the game's moves give a few dozen) and at most 8
kept entity blocks of 16 KB at most each, made only when an actor leaves a loaded map; per call a few comparisons and
one row of the change list (a binary search), no disk; leaving a map, one search of the map's entity text (in
memory); an arrival whose home is not loaded, one file open and two reads (the map header's 12 bytes, then the home
room's entity lump), behind the room's loading screen, then the spawn every joining actor costs. Measured on the
v0.0.61 build's room maps (7 November 2026) for seven home rooms the game's moves name: entity lumps 721 to 9,169
bytes (under 5 ms at 2 MB/s, plus the open), an actor's block 483 to 775 bytes (median 616). Nothing per frame while
no move happens.

`AIFollowCell`, `AIEscort` and `AIEscortCell` (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62; rules from OpenMW's
aiextensions.cpp OpAiFollowCell, OpAiEscort and OpAiEscortCell, aifollow.cpp, aiescort.cpp and actionteleport.cpp,
our own code). The builder works the cell out once, as PositionCell's: an interior cell's stable number and the point
in that room map's own units; the outdoors and a cell the game does not have get the number 0. An AIEscortCell into
a cell the game does not have compiles to nothing (OpenMW starts no package then); the reset argument is not passed
(OpenMW ignores its value). The call goes to the engine through the import route (duration, x, y, z, the kind, the
room's number; the target and the cell). On the ambient tables (aw_ambient.c `AW_AmbientPackage`):

- the follow (GetCurrentAIPackage 3) is AIFollow's, done when the actor is within the follow distance of the point in
  the room the call names; with a cell that is no room it is never done by its position, as OpenMW has it; a duration
  in game hours ends it too;
- the escort (GetCurrentAIPackage 2) walks straight to the destination while the escorted actor keeps up (450
  original units at the start, then the actor's half extent + 450 while near) and stands once it falls behind (the
  half extent + 250 then); outside the place an AIEscortCell names it waits; done within 64 units of the destination;
- the player's followers go along through a door, a travel or a region map's load (OpenMW's getFollowers: those
  within 800 original units, not fighting): the package is kept, the follower's entity block is kept for the session
  (from the loaded map, or for an outdoor actor from the CHIM frame map it was joined from: one open and two reads,
  behind the loading screen), and once the player stands in the new place the follower is spawned beside the player
  there, its row of the world change list saying so, its own script attached again. A coordinate teleport takes no
  follower along. Escorts never go through a door (OpenMW: the player brings them back);
- every AIFollow and AIFollowCell of the player compiles a VISI row of any room (room 0xFFFFFFFF) for the follower,
  so a room it was left in, or a saved game made there, spawns it there again;
- the packages are kept in saved games (the AWPK block, version 2: 30 bytes a package, the place added; a version 1
  block still loads).

Counted in `aw_mwscript_status` and `chim actors ambient`. Not carried yet: a follower whose home is outdoors, after a
saved game is loaded in a room, comes back only once its home frame loads (its entity is read from its home room's map
for an indoor home; MWSCRIPT-POSITIONCELL-OUTDOOR-62). Measured 7 November 2026 with the feature tracker: scripts that
run whole 434 before, 435 after (of 1,207; two of the escort scripts are placed only in an add-on world); every
dialogue result that calls AIFollowCell (19) runs, 7,385 of 7,411 results whole. Cost: per call one slot change and a
few comparisons; per think of an escort or a follower one distance test and the walk step; at a door, per follower a
search of the loaded map's entity text in memory or one frame map read; resident, at most 8 kept entity blocks (shared
with PositionCell) and 32 joined frame names (2 KB). The game's masters compile to 228 VISI rows (2,736 bytes,
resident): 28 of PositionCell's rooms and 200 followers of any room; a room's load reads them once (a binary search of
the change list for each follower row).

The player's control switches (v0.0.62, MWSCRIPT-PLAYER-CONTROL-62; rules from OpenMW 0.51 controlextensions.cpp,
mwinput/controlswitch.cpp, the input scripts playercontrols.lua and camera.lua, miscextensions.cpp OpEnableTeleporting
and OpEnableLevitation; our own code): `DisablePlayerControls` and `EnablePlayerControls`, the same pair for
`PlayerFighting`, `PlayerJumping`, `PlayerLooking`, `PlayerMagic`, `PlayerViewSwitch` and `VanityMode`, the seven
`Get...Disabled` readers, and `Disable`/`EnableTeleporting` and `Disable`/`EnableLevitation`. They go through the import
route (no new opcode, no change of the file's format). What each one stops while it is off:

| Switch | Off means |
| --- | --- |
| PlayerControls | no walking, jumping, attacking or readying, no use key, and the inventory, map, journal and wait windows do not open from their keys |
| PlayerFighting | no attack and the hands are not readied |
| PlayerJumping | no jump |
| PlayerLooking | the mouse and the turn keys do not turn the player; switching it off faces the player to rotation 0, as OpenMW does |
| PlayerMagic | kept and read; the player cannot ready a spell yet, so nothing else changes |
| PlayerViewSwitch | the first and third person key does nothing; the view stays as it is |
| VanityMode | no idle orbit; a running one ends |
| Teleporting, Levitation | kept and saved for the effects that will read them (Mark, Recall and the Interventions; Levitate) |

A switch a script turns off is independent of the opening's own rule (`aw_story.c`): a control works only when both allow
it, so the registration on the ship and in the census office behaves as before, and the opening's scripts stay on the
hand-written list. The disabled switches are one bit mask in the saved named facts, so a saved game keeps them, an
older save loads with every switch on, and a new game starts with every switch on (OpenMW InputManager::clear,
World::startNewGame). A script that calls the same switch every frame changes nothing and wakes no other script.
`aw_mwscript_status` names the switches that are off; `dbg mwscript call disableplayercontrols` (any of the 25 names)
carries one out by the script's route. Measured 7 November 2026 with the feature tracker: scripts that run whole 435
before, 437 after (of 1,207); the 15 scripts that call DisablePlayerControls no longer have it among their gaps. Cost:
per call one search of the 32 global rows and, on a change, one row written; in play, a few such searches a frame for
the input (the same search the opening's CharGenState test already makes); nothing resident but the one row.

The small functions (v0.0.62, MWSCRIPT-SMALL-FUNCTIONS-62; rules from OpenMW 0.51, our own code): the functions
that alone kept the most scripts from running whole, cheapest first, ranked on the feature tracker. All go through the
import route (no new opcode, no change of the file's format):

| Function | What it does here | OpenMW 0.51 |
| --- | --- | --- |
| `GetAngle`, `SetAngle` | an object's rotation in degrees on x, y or z (u, v, w the same axes); z is minus Quake's yaw, as the converter places objects; an actor's angle within -180 to 180 (x within -90 to 90); SetAngle on the player turns the view | transformationextensions.cpp OpGetAngle, OpSetAngle; worldimp.cpp rotateObject |
| `Move`, `MoveWorld` | units a second along the object's own axes (x forward, y left, z up) or the world's; the player standing on it goes along | OpMove, OpMoveWorld, moveStandingActors |
| `RotateWorld` | degrees a second about the world's z (x and y as Quake's pitch and roll, for an object standing upright); an actor only about z | OpRotateWorld |
| `SetPos` | the position on one axis, the original's units | OpSetPos |
| `SetAtStart` | back where the map put it: a script's first change of an object's place or angles keeps that start, until the next map | OpSetAtStart |
| `Face` | an actor (not the player) turns to the point at once (the original turns it at its turning speed) | aiextensions.cpp OpFace |
| `GetDetected` | an NPC sees the actor (a line of sight through the world, actors not in the way) and its awareness roll, kept 5 seconds, reaches the crime rules' target (a player who does not sneak is always noticed); any other observer: any NPC within 7,168 units that does | aiextensions.cpp OpGetDetected; actors.cpp isActorDetected; mechanicsmanagerimp.cpp awarenessCheck; creaturestats.cpp getAwarenessRoll |
| `GetLOS`, `GetLineOfSight` | both actors, enabled, eye to eye through the world | OpGetLineOfSight, World::getLOS |
| `GetInterior` | 1 while the player is in a room map | cellextensions.cpp OpGetInterior |
| `GetCurrentWeather` | the weather in effect (0 clear to 9 blizzard, the one being left while a change runs) | skyextensions.cpp OpGetCurrentWeather |
| `GetPCSneaking` | the player sneaks | controlextensions.cpp OpGetPcSneaking |
| `GetWeaponDrawn` | the player's hands readied without a torch; an actor while it fights | miscextensions.cpp OpGetWeaponDrawn |
| `OnKnockout` | 1 in the frame a script first sees the actor knocked down (a blow's or fatigue's) | statsextensions.cpp OpOnKnockout; actors.cpp |
| `SetDelete` | 1 deletes the object for good, as an item the player took: it leaves the world, Enable does not bring it back, its local script stops after the frame and no map binds it again; 0 undeletes it (its script binds at the next map load); kept in saved games | miscextensions.cpp OpSetDelete, worldimp.cpp deleteObject / undeleteObject |
| `GetPCSleep` | 1 while the hours of a rest pass (over the frames since v0.0.67, so every rest gives the scripts at least one frame asleep), 0 while the window only offers the rest, during a wait and in play; a whole number (before v0.0.67 the host wrote it as a fraction, so a script's `GetPCSleep == 1` never held) | miscextensions.cpp OpGetPcSleep; waitdialog.hpp getSleeping; timeadvancer.cpp |
| `WakeUpPC` | the hours of a rest or wait stop where they are (the hours passed count, no level-up; a planned wilderness interruption still comes) and the window closes, also when it only offers the rest | miscextensions.cpp OpWakeUpPC; waitdialog.cpp wakeUp |

Angles and moves act on an object with an entity; CHIM scenery without one cannot turn or move yet (counted in
`aw_mwscript_status`, as Rotate's). The reads that change without the state generation moving (the angles, detection,
the line of sight, a knockdown, the weather, sneaking, a weapon out) make their script VOLATILE, as GetPos does;
GetInterior does not (the player's cell moves it). Measured 7 November 2026 with the feature tracker: scripts that run
whole 437 before, 468 after (of 1,207); 277 of 504 functions carried out (259 before). GetDetected alone held 9 attached
scripts (the slave owners, guards and the prison guards), SetAtStart 4, SetAngle 3. Cost (the budget sheet): resident,
32 starting places (36 bytes each) and 16 knockdown and 16 awareness rows (16 bytes each), 1,664 bytes; per call a few comparisons
and at most one entity link; GetDetected and GetLOS one world trace each (their scripts ask every frame: a handful of
NPCs near the player); no disk, nothing per frame while no script asks.

Not carried in this batch, with the reason: `Cast` of other spells (the spell effects on other actors, SPELL-EFFECTS-57),
`PlaceAtPC`, `PlaceItem`, `PlaceAtMe`, `Drop` (the object spawner, above), `BecomeWerewolf`, `IsWerewolf`,
`UndoWerewolf` (werewolves), `OnMurder` (the murder crime: the crime rules know thefts only, CRIME-59), `PlayBink` (the
videos are not in the image), `HurtStandingActor` (the engine's own lava rule hurts the player already; the script form
would hurt twice), `GotoJail` and `PayFine` (jail), `Resurrect`, `HitOnMe` (the last weapon to hit an actor was not
kept then; it is since v0.0.62, below), `HasSoulGem` (souls in soul gems are not kept yet). `OnMurder`, `GotoJail` and `PayFine` followed with the crimes
(below).

The crimes (v0.0.62, CRIME-59; rules from OpenMW 0.51, our own code, docs/GAME_FORMULAS.md "Crime, sneaking, locks and
detection"): the functions the guards' arrest and the murder scripts call, through the import route (no new opcode, no
change of the file's format):

| Function | What it does here | OpenMW 0.51 |
| --- | --- | --- |
| `OnMurder` | 1 once after the actor's murder by the player was reported to the crime rules (a killing that was a crime: it was not fair to attack, or it had reacted to one of the player's crimes) | statsextensions.cpp OpOnMurder; mechanicsmanagerimp.cpp actorKilled, reportCrime |
| `PayFine` | the bounty to 0, the stolen goods the player carries go into the nearest prison's evidence chest, and every NPC that reacted to the crimes paid for calms down (its fight and pursuit end, its Fight and disposition come back) | miscextensions.cpp OpPayFine; worldimp.cpp confiscateStolenItems; actors.cpp |
| `PayFineThief` | the bounty to 0 and the calm, the goods kept (the thieves' fixers) | OpPayFineThief |
| `GotoJail` | the bounty to 0, the goods taken, the calm; when the conversation has closed, max(1, bounty / iDaysinPrisonMod) days pass as a rest, a random skill a day falls by one (Security and Sneak rise), and the player is let out at the nearest prison marker with the game's release line | OpGoToJail; worldimp.cpp goToJail; jailscreen.cpp; playerskillhandlers.lua jailTimeServed |
| `GetPCInJail` | 1 from GotoJail until the release | OpGetPcInJail |

A conversation's answer runs with its speaker's reference but no entity of its own; since v0.0.62 its calls on the
speaker find the speaker by that reference, so an answer's `StartCombat` starts the fight at once (the guard's "Resist
Arrest.", GUARD-RESIST-ARREST-NOTHING-61), and an answer's `SetFight` takes effect when the talk closes: the speaker
whose Fight, with the disposition and distance biases, reaches 100 attacks (OpenMW 0.51 actors.cpp; a robber's refused
demand "SetFight 100 / Goodbye", DIALOGUE-AGGRO-62). The three masters hold 343 answers whose result starts combat (138
distinct result texts, all compiled whole).

The dialogue's `Alarmed` condition reads the speaker's mark from the crime rules (an alarmed guard), and the crime gold
globals (PCHasCrimeGold, PCHasGoldDiscount, CrimeGoldDiscount, CrimeGoldTurnIn, PCHasTurnIn) are set when a
conversation opens (OpenMW updateDialogueGlobals). Measured 7 November 2026 with the feature tracker: scripts that run
whole 479 before, 485 after (of 1,207; OnMurder alone held the 5 placed scripts of the Redoran councillors, Athyn
Sarethi, Bolvyn Venim, Alvis Teri and Ondres Nerano); dialogue results that run whole 7,390 before, 7,404 after (the 14
answers of the guards and the thieves' fixers that pay the fine or go to jail); 324 of 504 functions carried out (319
before). Cost
(the budget sheet): resident, the NPC rows (24 bytes each, 32 at first and doubled as the marked NPCs grow, up to
1,024) and the jail's state (about 700 bytes, its release line); a call
is a table lookup, PayFine and GotoJail a pass over the stolen pairs and the rows; GotoJail reads the prison markers
(a file of six lines) once.

A test aid for result scripts: `dbg mwscript result TOPIC NPC [N]` runs the result script of the answer the loaded NPC
gives on TOPIC now (or its N-th answer on the topic, from 1, whatever its conditions say) the way the dialogue window
runs it, without opening the window, and prints the script and whether it ran. An in-game check of a PositionCell,
AIFollowCell or control switch answer needs no conversation then. Its cost is one conversation read, at the command only.

`GetCurrentAIPackage` and `GetAIPackageDone` (v0.0.54; rules from OpenMW's aiextensions.cpp): the actor's package as
the ambient tables run it (`AW_AmbientAiPackage`, through the engine's `aw_mwscript_ai_package`), with OpenMW's
numbers (-1 none, 0 Wander; Travel, Escort, Follow and Activate come with those packages), -1 for a dead actor, and
"done" once a wander that does not repeat has run out. The ambient tables move the state generation when a package
starts or ends, so these scripts are not run every frame. Without the ambient tables in the build both read -1 and
0. Scripts that run whole: 735 of 1,207.

The stats themselves (attributes, skills, health, magicka and fatigue with Get, Set, Mod, ModCurrent and the ratio,
level, the behaviour ratings, disposition) run since v0.0.54 on every actor and on the player (above). The player's
standing runs since v0.0.57 (rules from OpenMW's statsextensions.cpp and dialogueextensions.cpp; the engine's
`aw_pcstanding.c`): `GetPCCrimeLevel`, `SetPCCrimeLevel`, `ModPCCrimeLevel` (the bounty, never below 0 by Mod);
`GetReputation`, `SetReputation`, `ModReputation` of the player (0 to 255, as the original caps it; an NPC's reads
its record, changing an NPC's is not yet); per faction `GetPCRank` (-1 when not a member), `PCJoinFaction`,
`PCRaiseRank` (joins when not a member, then one rank up to the record's last rank slot), `PCLowerRank` (below rank 0
leaves the faction and clears the expelled mark), `PCExpelled`, `PCExpell`, `PCClearExpelled`, `GetPCFacRep`,
`SetPCFacRep`, `ModPCFacRep`; without a faction named, the speaker's own (a factionless one reads -1 and changes
nothing); and `GetRace` of the player or an NPC. These use the import route below: the call keeps its form and the
engine answers it by its number (no new opcode, no change of the file's format); a read does not keep its script
awake, a change wakes the scripts that read the standing. Kept in saved games since the AddTopic change below
([MWSCRIPT-STANDING-NOT-SAVED-57](BUGS.md)). Measured 30 October 2026 over the game's data: scripts that run whole
735 before, 765 after (of 1,207); Morrowind.esm alone 376 before, 403 after (of 632). Cost: 71 bytes more
bytecode, 72 bytes more resident file, 1,300 bytes of engine table (32 factions), nothing read from disk but the
faction names (the 16-entry id cache).

`PlayGroup` and `LoopGroup` (v0.0.57; rule from OpenMW's animationextensions.cpp and character.cpp playGroup): the
named group of the actor's skeletal table plays once (LoopGroup: once plus the count) over what its state plays, the
way a cast plays (`aw_animkit.c`), then the state's own group again; a hit, a fall or a death ends it. On an actor
without a skeletal table, or a group its table lacks, nothing happens (counted in `aw_mwscript_status`). Scripts that
run whole: 765 before, 783 after (of 1,207).

`AddTopic` (v0.0.57; rule from OpenMW's dialogueextensions.cpp OpAddTopic): the topic joins the player's known
topics, which the dialogue window will list (DIALOGUE-57). The builder writes the game's 2,098 dialogue topics (DIAL
records of the topic type, sorted) as the TOPC section, on disk (4,196 bytes, a name index each); a script's AddTopic
becomes the topic's row number, so the engine keeps one bit per topic (263 bytes) and compares no text. An AddTopic
of a name no topic has compiles to nothing, with a warning. The known topics and the player's standing are kept in
saved games, after the actor records (a save of an earlier version loads as before, with none known). Scripts that run
whole: 783 before, 799 after (of 1,207); Morrowind.esm 418 of 632.

`Cast` of the cures (v0.0.57; OpenMW miscextensions.cpp OpCast, the effects from spelleffects.cpp): a Cast on the
player of Cure Common Disease removes every common disease from the player's spells, Cure Blight Disease every
blight; Cure Poison changes nothing, because no poison state exists yet. The caster plays its cast. These are the
shrines' cure blessings (16 shrine scripts, 48 casts); the same scripts also cast their own shrine blessing, which
waits for the spell effects (SPELL-EFFECTS-57: an effect table on disk, active effects per actor, saved), so they
do not run whole yet and the count of scripts that run whole stays 799. Every other Cast compiles as "not yet".

`Cast` on anything but the player (v0.0.64; OpenMW 0.53 miscextensions.cpp OpCast, spellcasting.cpp CastSpell::cast):
the call hands the spell's ASPT row and the target's object row. A caster other than the player casts the spell on the
target and it always succeeds: its Self effects land on the caster when the caster is an actor, its Touch and Target
effects on the target, at once (no bolt flies). A target placed more than once, or made by a script, is found by its
id among the loaded actors. A spell the game has not compiles to nothing, with a warning (OpenMW reports it and does
nothing). The player as the caster (OpenMW only selects the spell then) stays "not yet".

`ForceGreeting` (v0.0.57; OpenMW dialogueextensions.cpp OpForceGreeting: the actor opens the dialogue with its
greeting): the actor plays the greeting the engine plays when the player talks to it (the voice table and its hello
line, QC `aw_greet`), by the same talk rule (alive, not hostile, not knocked down, something to say). The dialogue
window itself is DIALOGUE-57; until it exists the greeting is what talking does. An actor that is not loaded, or
cannot talk, does nothing (counted in `aw_mwscript_status`). Cost: one QC call when a script asks, nothing resident.
Scripts that run whole: 834 before, 899 after (of 1,207).

`Rotate` (v0.0.57; OpenMW transformationextensions.cpp OpRotate: the given degrees a second times the frame's
duration, the player only around z) turns an object that has an entity; CHIM scenery without one cannot turn yet
(counted). `GetTarget` (OpenMW aiextensions.cpp OpGetTarget): the combat layer here fights the player only, so it
reads 1 for the player while the actor fights and lives, else 0; a fight starts without the state generation moving,
so a script that asks runs every frame. Scripts that run whole: 899 before, 919 after (of 1,207).

`AITravel` (v0.0.57; OpenMW aiextensions.cpp OpAiTravel, aitravel.cpp): the actor walks to the point on the
ambient tables' routes (docs/NPC_PATHFINDING.md "Travel packages, from the scripts"); `GetCurrentAIPackage` reads 1
and `GetAIPackageDone` 1 once it arrived. Scripts that run whole: 919 before, 930 after. `AIFollow` (OpenMW
aifollow.cpp) on the same module (docs/NPC_PATHFINDING.md); `GetStandingPC` (OpenMW World::getPlayerStandingOn)
reads 1 while the player stands on an object that has an entity (CHIM scenery without one reads 0 yet). Scripts that
run whole: 930 before, 950 after. `GetDetected` runs since v0.0.62 (the small functions, above). `Position` (OpenMW
transformationextensions.cpp OpPosition): the player goes to the outdoor point by the coordinate teleport (as the
original, the player always lands outdoors); any other object with an entity moves within the map it is in; the
rotation is not applied yet. Scripts that run whole: 950 before, 957 after.

**Placing objects** (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62; rules from OpenMW 0.51 transformationextensions.cpp
OpPlaceAt, OpPlaceItem, OpPlaceItemCell and worldimp.cpp safePlaceObject, our own code). `PlaceAtPC` and `PlaceAtMe`
make COUNT copies at DISTANCE game units in the DIRECTION 0 front, 1 back, 2 left, 3 right of the player or the
reference, facing as it faces; an NPC or creature takes the next direction (in OpenMW's order) while the way from the
spot back to the reference is blocked (OpenMW's ray from 30 units up to the reference 20 units up), and stands on the
ground under the spot. `PlaceItem` places at X Y Z of the player's cell with a rotation in degrees; `PlaceItemCell` in
a named cell, which the builder works out as PositionCell's (a cell the game has not compiles to nothing: OpenMW
reports it and does nothing).

- **The builder** reads every object id a Place call of the game names (the scripts and the dialogue results) and
  writes the PLAC section, sorted by id (12 bytes a row, resident): its kind, for an NPC or creature a template (a
  reference of the same record placed in Morrowind.esm, a room's first, with that room's map name) and the record's
  own script. A call goes to the engine through the import route with the row's number as its last number (no new
  opcode). It is carried out for an NPC or creature that has a placed reference in Vvardenfell (the build has its
  converted model) and for a carried item; any other stays "not yet" (below).
- **An NPC or creature** is a new reference: its key is in a block no game file uses (content file index 15: `F00000`
  plus the PLAC row times 4,096 plus a serial). Its entity is the template's (the loaded map's text, this session's
  copy, else the template's home room map: one open and two reads), else the actor table's base of the record, with
  the new reference; it is spawned as a joining frame's actor is and its own script is attached. Its row of the world
  change list (place and position, then health and death as every actor's) keeps it: leaving the area releases it as
  any outdoor actor, a room's map change takes it with the map, and once a second the engine spawns every placed actor
  whose row puts it here (this room; outdoors a cell the window holds) and that does not live. A save keeps the row; a
  dead one stays dead. A load of a save made with other game data drops these rows with the other changes it cannot
  place.
- **A carried item** is a drop row of the world change list (the next drop serial, the item's id, the place and
  position), shown at once when its place is loaded and taken as any drop (CELL-CHANGES-59).

- **A levelled creature list** (v0.0.67, [MWSCRIPT-PLACE-OTHER-KINDS-62](BUGS.md); OpenMW 0.51
  mwclass/creaturelevlist.cpp: a placed list gives one creature of it at the player's level) is an actor row with the
  levelled flag (PLAC flags 4): the engine rolls one creature of the list of that id in the actor table for the new
  reference at the player's level, keeps the pick under it (a return or a load gives the same creature), and spawns it
  as above, its record's script attached. The builder puts every list a Place call names, and every region's sleep
  list, in the actor table with a base of its own (tools/chim/actors.py named_lists). Tribunal's fab_cent_fight_watch
  places two of in_dwe_all_tribunal's centurions in Bamz-Amschend this way.
- **A scripted object no map places** (v0.0.67; an activator whose record has a script: Tribunal's trapProjectile,
  Bloodmoon's transformation effects) is a point row (PLAC flags 2): an entity of its own where the call puts it, not
  drawn (no map converted its model), not solid, under its new reference, so its record's script runs on it: the mine's
  projectile moves to the player (SetPos), casts its spell (ExplodeSpell), disables and deletes itself. An object with
  neither a placed reference nor a script stays "not yet": it would show nothing and run nothing.
- **A deleted script-made reference leaves for good** (v0.0.67; OpenMW mwworld/cellstore.cpp writeReferences keeps no
  deleted reference that no content file made): after the frame's run, SetDelete 1 on a reference of the `F00000`
  block frees its edict and drops its rows of both change lists, so it is not spawned again on a return or a load, not
  saved, and its key is free again; a projectile the mine fires every few seconds no longer leaves a row behind.

Not carried yet, kept as "not yet" and counted in the feature tracker: an NPC or creature whose record no reference
in Vvardenfell places (Ranes Ienith, Rerlas Mon's rats, the Dark Brotherhood attackers of Tribunal and most of
Bloodmoon's: no converted model, [MWSCRIPT-PLACE-NO-MODEL-62](BUGS.md)), and an object with neither a placed reference
nor a script. Game data, 7 November 2026: 41 objects named (21 NPCs, 9 creatures, 4 items, 7 others), 11 of them made
by the engine. Measured 19 November 2026 (0.0.67, the feature tracker): every PlaceItem call of the game is carried out
(24 scripts, 37 uses; it was missing in 19 scripts before), the scripts with a function missing went from 21 to 2 (the two
water levers of Old Mournhold, [MWSCRIPT-WATER-LEVEL-STATIC-67](BUGS.md)), the scripts that run from 611 to 617.
Measured with the feature tracker (MWSCRIPT_FEATURES.md, 7 November 2026, against the integration line with
AIFollowCell, AIEscort, the player's control switches and the small functions): scripts that run whole 468 before,
472 after (of 1,207); scripts with a function missing 149 before, 139 after (6 more are whole but placed only in an
add-on world); dialogue results whole 7,385 before, 7,386 after.

Cost (the budget sheet): resident, the PLAC rows (492 bytes for the game) and a change list row per placed actor (48
bytes); per call a few traces (the ray back to the reference, the ground), one template read when the template is not
in the loaded map (one open and two reads of its room map's header and entity lump, 1 to 9 KB), then the spawn every
joining actor costs (its model's first load when it is not cached); once a second a binary search in the change list
and a look at the placed rows; nothing per frame. `aw_mwscript_status` counts the calls made, refused and kept for
another place, the spawns and the placed actors kept.

A test route in the console: `aw_mwscript_status call FUNCTION [number] [faction]` carries out one of the
standing calls or `addtopic ROW` on the player through the same host route a script takes, and answers with the
crime level, the reputation and the number of known topics; `aw_mwscript_status` shows the same counts. A named
faction is found by a scan of the file's strings on disk, which takes several seconds on the Amiga: a test route,
never a script's path (scripts carry the faction's string number). Checked in game on 30 October 2026 (Seyda Neen
MiniWind, 32 MB Fast): crime level 1450, reputation 12, a Mages Guild rank and one known topic set, a quicksave, all
changed, a quickload: the crime level, the reputation and the topic came back.

The interpreter's own opcodes typed on the console (v0.0.68): `MenuMode`, `OnActivate`, `CellChanged`,
`GetSecondsPassed`, `Random`, `XBox`, `GetButtonPressed`, `DontSaveObject`, `Fall` and `GetSquareRoot` answer what the
opcode would read on that line's target (OpenMW 0.51's rules). The console is a menu, so `MenuMode` reads 1 while it is
open. `Random N` is the next roll of the one generator the scripts use. `GetSecondsPassed` is the interpreter's last
frame. `GetButtonPressed` takes the message box's answer, as a script's read does. `CellChanged` and `OnActivate` read
the target's own attached script, and a target without one reads 0. As in the original, `OnActivate` read on an
object passes the object's next use to its script; the object's `Activate` gives it back. `DontSaveObject` and `Fall`
do nothing, and `XBox` reads 0.

The cell commands typed on the console (v0.0.68): `PositionCell`, `PlaceItemCell`, `AIFollowCell`, `AIEscortCell` and
`GetPCCell` find the cell by its name in the CELN and CELG sections, and the console works out the move with the
compiler's own rules. The player is moved into the room's map at the given point, as a door arrival would put him, or
outdoors. Another actor moves to the room's map units or outdoors; a cell the game does not have does nothing, as in
OpenMW. A presented district moves by its own offset. The line then makes the same call a compiled line makes.
`GetPCCell` compares the name of the player's cell with the typed text from its start, in any case: a room's name, or
an exterior cell's name as OpenMW gives it. The two sections and their names cost about 103 KB in the file on disk
(34 KB of rows, 6 KB of grid cells, about 63 KB of names in STRS) and nothing in memory.

Not yet (111 functions the game's scripts call, 124 before v0.0.57). The ones that stop the most scripts, measured 30 October 2026 (`python3 -m mwscript.measure`,
"blockers": the scripts for which the function is the only call not carried out, of the scripts using it):
ForceGreeting 64 of 98, Cast 29 of 53, PositionCell (other actors) 25 of 37,
AITravel 10 of 24, BecomeWerewolf 10 of 18, GetTarget 8 of 15, GetStandingPC 8 of 13, PlaceAtPC 7 of 15, Position 7
of 14, Rotate 6 of 21, GetDetected 6 of 10. Carried out in that order (each step the function that frees the most
further scripts), ForceGreeting alone brings 63 more scripts to run whole, with Cast 91, with PositionCell 117. The
most called: ForceGreeting 134, Cast 126, AddTopic 105, AITravel 89, HasSoulGem 85, PlayGroup 84, PositionCell 74.
They wait for the dialogue window, moving actors between cells, spells and effects, the other AI packages and
animation. The scripts' own values are not in saved games
yet ([MWSCRIPT-STATE-NOT-SAVED-48](BUGS.md)).

A room's water (v0.0.68). `GetWaterLevel` reads the room's own level from the WATR rows: 0 outdoors, the room's level
in a room with the water flag, the lowest float in a room without it (OpenMW 0.51's rule). `SetWaterLevel` and
`ModWaterLevel` set and move the level of the player's room; outdoors (where OpenMW stops the script) and in a room
without water they change nothing. The level is kept as a named fact of the room in the world change list, so a
save holds it and New Game clears it, and it comes back whenever the room is loaded again. The surface follows: a CHIM
room's world holds its water as one level plane at its root (the open air above, the water below, the two water faces
on it), and the engine moves that plane and its faces' corners, so swimming, the breath and the view under water follow
the new level by themselves (engine/aga/src/aw_water.c). A level outside the room's box puts the plane at the box's
edge. A room with lava carved beside its water keeps the water where it was built (four rooms of the game have both;
no script moves their water). The setting `aw_water_movable 0` leaves every plane where it was built. Not yet: a room
whose water lies under every placement has no plane in its map (Old Mournhold: Temple Sewers West, where the lever
raises it), and the placements the surface passes are not yet drawn on their new side of it
([MWSCRIPT-WATER-LEVEL-STATIC-67](bugs/MWSCRIPT-WATER-LEVEL-STATIC-67.md)).

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

## Spell effects: the design (SPELL-EFFECTS-57)

**The first slice runs since v0.0.57** (`engine/aga/src/aw_effects.c`): a `Cast` on the player of a spell whose
every effect is a Fortify, Drain, Damage or Restore of an attribute, a skill, health, magicka or fatigue lands those
effects (the magnitude rolled once between the record's low and high), ticks them on the game clock, undoes Fortify
and Drain when they end and keeps the active ones in saved games. The builder writes only the spells a Cast names
(SPFX, resident: 1,096 bytes for the game); the player's pool holds 16 effects (a full pool refuses one, counted in
`aw_mwscript_status`). Measured 30 October 2026: scripts that run whole 799 before, 816 after (of 1,207); the shrines'
blessings of these kinds now run. `GetEffect` (v0.0.57; OpenMW miscextensions.cpp OpGetEffect) reads the active
list: the builder turns the effect's name ("sEffectPoison") into the game's effect number, and the engine answers 1
when an effect of that number is active on the player. Effects of other kinds cannot be active yet, and no other
actor carries effects yet, so 0 is the true answer there; the scripts ask mostly about Poison, Fire Damage,
Invisibility and Chameleon. Since v0.0.68 the builder knows all 143 effects by their game setting ids in the game's
order (OpenMW components/esm3/loadmgef.cpp sGmstEffectIds; Tribunal's and Bloodmoon's summons last), or by a whole
number as the effect's own number; before, it knew 84 and three of them by another word, so a `GetEffect` of
sEffectDrainSpellpoints or of a summon read 0. Scripts that run whole: 816 before, 830 after. Then the effects the remaining Casts named most: the cures
inside a blessing (Cure Common Disease and Cure Blight Disease remove those spells, Cure Poison changes nothing yet)
and Fire, Frost and Shock Damage and Poison, which hurt health like Damage Health (no resistances exist here yet, so
the full magnitude lands): 830 before, 834 after. Still waiting: the effects of other kinds (Shield, Water
Breathing, Swift Swim, Levitate and the like; 13 scripts wait only for a Cast of them), Casts on other actors, effects on other actors, the effect table of every spell and
enchantment.

**The shrines' own blessings (v0.0.62).** A spell may now also hold effects with no attribute or skill that only
stand on the actor for their duration with a magnitude: Water Breathing to Slow Fall, the weaknesses, Invisibility to
Night Eye, the detections, Spell Absorption, Reflect, Fortify Maximum Magicka, the resistances and Fortify Attack
(SPFX kind 5: the effect by its number). The engine lands them with their magnitude rolled once, as any other effect
of the active list (OpenMW 0.51 keeps them in the actor's active effects, which its systems read). Spells with an
action effect (Lock, Open, Mark, Recall, the interventions, Dispel, the summons, the bound items, Calm, Frenzy,
Command) still wait. Measured 8 November 2026 with the MWScript tracker: scripts that run 541 before, 551 after (the
10 Vvardenfell shrines that waited only for their blessing: Aldsotha, Delyn, Ghostgate, Kummu, Meris, Olms, the Puzzle
Canal, Seryn, Stop Moon, Vivec's Fury); scripts that use a function the interpreter lacks 94 before, 82 after.

`PlayBink` (v0.0.62; OpenMW 0.51 miscextensions.cpp OpPlayBink: the video plays over the game, which goes on after
it): the converted video of the same catalogue name (the file name less ".bik", `intro/videos.awl`) plays over the
scene as `debug playvid` plays it, and the scene and its input come back when it ends or Esc skips it; a build without
videos says so once and the script goes on. Scripts that run: 551 before, 553 after (AzuraEnd's ending video and
MoonAndStar's cavern video).

`HitOnMe WEAPON` (v0.0.62; OpenMW 0.51 miscextensions.cpp OpHitOnMe, Creature/Npc::onHit: the weapon of every
successful blow becomes the victim's last hit object; HitOnMe reads 1 when it is that weapon and then clears it):
each weapon blow of the player that lands (a hit or a blocked blow, the killing one too; a miss and fists keep nothing)
keeps the right-hand weapon's record id for its victim, at the same two points as the strike enchantment
(`aw_combat.c`, the hook `aw_combat_weapon_hit`); the host compares the call's id and clears it on a match. Eight
rows of victim reference and id hash, 64 bytes resident; a new victim past them takes the oldest row; New Game and a
save load empty them. An NPC's or a creature's weapon has no record id in its fight sheet yet, so its blows on the
player are counted, not kept. The Heart of Lorkhan's script (LorkhanHeart: Sunder, then Keening) needed only this.
Scripts that run: 553 before, 554 after; scripts that use a function the interpreter lacks 79 before, 77 after
(ValbrandrDraugr, the other script that calls it, waits for Solstheim).

`ChangeWeather REGION WEATHER` and `ModRegion REGION CHANCES...` (v0.0.62; OpenMW 0.51 skyextensions.cpp
OpChangeWeather, OpModRegion; weather.cpp WeatherManager::changeWeather, modRegion, RegionWeather::setChances): the
compiler works the region out (its index among the sorted region ids of the build's game files, the order of the
weather table `world/region-weather.aww`, which the world UI stage writes from the same merged files) and hands it
first; a region those files lack is no code, as OpenMW finds no such region. Until v0.0.68 the compiler counted the
base game's nine regions alone while an image with the expansions orders its table over all sixteen, so EndGame's
Red Mountain lines changed the Grazelands (REGION-INDEX-BASE-ONLY-68). ChangeWeather sets the region's weather until its next weather change (here the end of
its period of "Hours Between Weather Changes"); ModRegion replaces the region's chances for the rest of the game (the
ones given, each 0 to 100, and none for the weathers past them, as OpenMW's OpModRegion builds the list: since v0.0.68;
before, the weathers past the given ones kept the region's own), and a weather the new chances still allow stays
until that change, else the new chances choose. Both also work typed on the console since v0.0.68 (the region by its
id, from RGNS above). The player in
that region moves to the new weather as to any other (a transition). One row per changed region, 8 at most (148 bytes
resident), saved in the scripts' block (AWWR) and emptied by New Game and every save load. Once the Red Mountain
region's chances have neither ash nor blight, the Red Mountain sky pull stops. The end of the main quest (EndGame:
"Red Mountain Region" 50 clear, 50 cloudy, then clear) needed only these; scripts that run 569 before, 570 after;
scripts that use a function the interpreter lacks 77 before, 73 after (three Mournhold scripts wait for Mournhold).

**Items held by containers and other actors (v0.0.62).** OpenMW 0.51 runs the script of every item in the
containers, NPCs and creatures of the active cells, each on its own item (mwworld/localscripts.cpp addCell). The
builder writes one BIND row per placed container, NPC or creature of Morrowind.esm and each distinct carryable item of
its record that names a compiled script (`compiler.held_bindings`, flag 8): its reference is the holder's with bit 30
and the item's number among the holder's scripted items in bits 24-29, so the rows sort after every placed reference,
and its cell and position are the holder's. The engine reads them with the map's other bindings (no resident table)
and attaches each while the holder's area is loaded and the holder still has an item of that script (a container by
its contents now, an actor by its live record), at most 32 a map; when the player gains such an item (taken from the
container or a body) the held instances of that script are checked again. A held item's values are neither parked nor
saved: each visit starts them again. Measured 8 November 2026: 491 rows over 14 scripts (OrdinatorUniform 284 and
LegionUniform 164 on the guards' armour, ashStatueTopic 32, the rest one each: Sunder on Dagoth Vemyn, the Darksun
shield and Light of Day on Ano Vando, the treasury orders, the Mark amulets, books in chests); BIND 8,568 rows before,
9,059 after (11,784 bytes more on disk, read at each map change). The tracker counts no state change from them: those
scripts already ran while the player carries their items.

**Any effect on any actor (v0.0.61).** The active list now holds any of the game's 143 magic effects, by its
effect number and its attribute or skill, on any actor record by its reference (the player and the NPCs and
creatures a spell lands on): 64 entries of 20 bytes (1,280 bytes resident), at most 32 of them on the player. The
effects that act while they last (the elements, poison, sun damage, Damage and Restore, Absorb Health, Magicka and
Fatigue, the disintegrations, the cures) act each second, their magnitude a second; every other effect is applied
once and undone when it ends (Fortify, Drain, Absorb Attribute and Skill), or only adds its magnitude to the actor's
effect magnitudes, which the engine's systems read (Light, Levitate, Shield, Feather and the like). Which effects act
each second follows OpenMW 0.51 (components/esm3/loadmgef.cpp, the effects without the applied-once flag). Effects
on an actor whose record is not loaded do not tick, as OpenMW updates only the actors in the active cells. Saved
games carry the list as a version 2 block (16 bytes an effect, with the actor and the spell); v0.0.57's version 1
blocks still load. Not yet: resistances and weaknesses, reflection, the caster's half of Absorb.

The design, as it was written first (the rest of it is still to build). What the shrines' blessings, the traps, `Cast`, `GetEffect` and the effect Get/Set/Mod calls
wait for. The rules are OpenMW 0.51's (apps/openmw/mwmechanics/activespells.cpp for the active list and its ticking,
spelleffects.cpp for what each effect does, spellcasting.cpp for casting), written independently.

- **The effect table, on disk.** The builder writes the game's SPEL and ENCH records' effect lists (ENAM: effect
  number, skill or attribute, range, area, duration, magnitude low and high) and the MGEF flags the engine needs (the
  effect's school, whether it has a duration or a magnitude) as one section of `id1/mwscript.awm`: a row per spell
  pointing at its effects, 12 bytes an effect. Only an index (the spell's row by its STRS number, 4 bytes a spell)
  stays resident when the scripts are on; the effects are read when a spell is cast. The size goes into the
  resident registry against the 32 MB Fast machine; the builder report states it.
- **The active list, per actor.** A fixed pool of active effects (effect, stat, magnitude, seconds left, the caster's
  spell), 16 bytes each, about 64 for the whole loaded world plus 16 for the player, so at most about 1.3 KB; a full
  pool refuses a new effect (counted, logged once), it never allocates.
- **Ticking.** Durations count down on the game's own time, the same clock the scripts' `GetSecondsPassed` reads,
  not the frame; a magnitude is rolled once when the spell lands (between low and high, as OpenMW). When an effect
  ends, what it did is undone by OpenMW's rule for its kind: a Fortify takes its bonus back, a Drain gives its loss
  back, a Damage and a Restore are instant (no duration of their own: a Damage with a duration hurts each second).
- **The stats.** The actor record already holds attributes and skills as base plus a modifier and the dynamic stats
  as current and base (docs/ACTOR_STATE.md); Fortify and Drain move the modifier (dynamic: the base and the current),
  Damage moves the current down, Restore moves it up to the base. These are the existing calls with OpenMW's caps.
- **Saved games.** The active list goes into the save beside the actor records and the player's standing (the same
  trailer, a new tagged block); an older save loads with nothing active.
- **The first slice.** Fortify, Drain, Damage and Restore of the attributes and of health, magicka and fatigue, with
  durations, applied by `Cast` on the player and by the shrine blessings (their spells are of those kinds); then
  measure how many scripts run whole. `GetEffect` reads the active list.

## Sizes and costs

| | |
| --- | ---: |
| `id1/mwscript.awm` | 446,316 bytes (183,212 resident while on) |
| Interpreter code (68040, -O1) | 9,720 bytes |
| Engine side code / data | 5,876 / 10,960 bytes |
| Interpreter tables (taken when switched on) | sized by the build since v0.0.66-dev12 (fixed in source and covered by tests, not yet seen in a session, `EXPANSION-SCRIPT-LIMITS-66`; 4 live copies per scripted Place row in one map stay the limit, `MWVM-PLACE-COPIES-FOUR-66`): for the three masters 791 instances (38 KB), 1,475 values (6 KB), 5,478 parked objects (66 KB), 12,811 parked values (51 KB), a 16 KB hash and 3 KB of row tables, about 180 KB; 60 KB fixed beside them (the runnable and global-instance tables, the globals, the code marks, the import route's counters). The old constants took 97 KB |
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

The stage keys the compiler's files whole: it names them in its read trace, so a reused build takes the stage's
earlier output only while every one of them is unchanged, tables such as the host function list included
(`tools/mwscript/ident.py`). When it installs the file, the image step compares the receipt's compiler hash with
this source's and stops on a difference
(BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59: v0.0.59 was built with compiled scripts of an older compiler, so the
1,225 placed beds and two RaiseRank scripts had no compiled behaviour).

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
5. The next blockers by the scripts they stop (measured 30 October 2026, "Not yet" above): ForceGreeting (64
   scripts wait only for it: it needs the dialogue window of DIALOGUE-57, which opens on the actor and lists the
   known topics this page's AddTopic keeps), Cast (spells on actors). PositionCell of other actors runs since
   v0.0.62 (above), and so do AIFollowCell, AIEscort and AIEscortCell with the followers going through doors; next
   for them: the outdoor arrivals (an actor moved to an exterior cell stands there while its home frame is not in the
   window) and the in-game check of both.
   Then the scripts' own values in saved games.

## Credits

The rules of the language (argument kinds, the scanner's tolerances, how `else` junk and unknown variables are
treated, the sound distance rule) were learned by reading OpenMW 0.51's script compiler and sound code (GPL-3.0,
components/compiler and apps/openmw); AmiWind's compiler and interpreter are its own code, nothing copied
([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
