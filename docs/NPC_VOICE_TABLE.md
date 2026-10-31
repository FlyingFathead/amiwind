# NPC voice table (AWGL1)

_Last updated with AmiWind v0.0.56 (30 October 2026)._

<!-- contents start -->
## Contents

- [Status: how far the voices are (23 October 2026)](#status-how-far-the-voices-are-23-october-2026)
- [What it holds](#what-it-holds)
- [How a line is chosen](#how-a-line-is-chosen)
- [Engine](#engine)
- [Cost](#cost)
- [File format](#file-format)
- [Size and the build](#size-and-the-build)

<!-- contents end -->

Every NPC record's voice lines and conversation greeting in one file the engine looks up by record:
`id1/npc-voices.lut`. The maintainer asked for it on 23 October 2026: the NPC greetings should be as they are per
NPC, which needs a really fast lookup table; then for the whole voice vocabulary, since the audio files are already
in the game; and for the run-time conditions as bytecode, so that they are not slow
([NPC-GREETINGS-LIBRARY-MUTE-48](bugs/NPC-GREETINGS-LIBRARY-MUTE-48.md)).

## Status: how far the voices are (23 October 2026)

**Done, in the v0.0.48 line's source:**
- The table holds 2,673 NPC records, every voice topic and 4,224 voice files.
- It is built from the full game data in under 30 s and read back.
- The images gain only the table itself (757 KB): it points at voices the image already ships.

**Checked against the data, NPC by NPC.** Each NPC speaks with the voice of its own race and sex, plus its own lines:

| NPC | Voice | Example |
| --- | --- | --- |
| Fargoth | Wood Elf male | 138 hello lines |
| Caius Cosades | Imperial male | |
| Habasi, Ajira | Khajiit female | |
| Hlaalu guards | Dark Elf male | the Ordinator "What are you doing? Get out!" for intruders |
| Ordinators | Dark Elf male | their own idle lines, "Submit to the Three, the Spirits, and Thy Lords." |
| The census office officer | Breton male | thief line "What do you think you're doing?!" |
| The census office captain | his own recording | "Your papers, please." |

**Not done yet:**
- **No in-game check.** Nobody has listened in a build yet; the first build with the table is v0.0.48-dev2.
- **Two NPCs left out.** Two Orc NPCs have accented letters in their record ids and stay silent
  ([NPC-VOICE-NONASCII-IDS-48](bugs/NPC-VOICE-NONASCII-IDS-48.md)).
- **Lines with no recording.** Conversation greetings are text in the original (only a few have a recording, like the
  captain's), so most greetings show as text.
- **Sounds tied to a place.** The original's sound markers (water under the Khuul pier, creaking under bridges, the
  silt striders) are script audio, not NPC voices. They come with the compiled scripts, audio first.

## What it holds

- Every NPC record of `Morrowind.esm` (2,673 of 2,675; two ids with non-ASCII letters are left out with the reason).
- Every Voice topic of the data: Hello, Idle, Intruder, Thief, Hit, Attack, Flee and Alarm (no NPC can say the
  data's one Alarm line), and the conversation greeting (the Greeting 0 to 9 topics in turn, OpenMW's order).
- Per NPC: its hello distance (the NPC's Hello setting times `iGreetDistanceMultiplier`, in Quake units), its base
  disposition, its faction rank, and the names its lines' text defines need (class, race, faction, rank, home
  cell). The greet reset distance and duration (`fGreetDistanceReset`, `iGreetDuration`) are in the header.
- Sounds are the converted voice files the media stage already ships (`sound/pool/a<16 hex>.wav`, the media
  catalogue's own names): the table stores the 8-byte hash once per file and converts nothing.

## How a line is chosen

The rule is the original's, as OpenMW 0.51 implements it (`mwdialogue/filter.cpp` Filter::search,
`dialoguemanagerimp.cpp` say and startDialogue): a topic's INFO records in order, the first one that passes is
said. The builder (`tools/greeting_lut.py`) compiles each INFO for each NPC with the same filter the town residents'
conversation greeting uses (`src/mwad/dialogue.py` Context.compile):

- **Decided at build time** (they only read the speaker's record): actor id, race, class, faction and rank, sex,
  NotId, NotRace, NotClass, NotFaction, the speaker's level, reputation and Hello/Fight/Flee/Alarm settings, whether its script
  declares a local, Choice, and the cell when the NPC is placed in one cell only (an NPC placed in several cells or
  in none matches no cell test). An INFO that fails one is never a candidate for that NPC.
- **Left for the game** (compiled into condition records): globals, Random100, the journal, items, the dead,
  script locals' values, the player's faction and rank, the player's state (health, level, crime, clothing ...),
  TalkedToPc, the speaker's health and disposition.

The entries of a topic that the same NPCs can say form one list, in the original's order, cut after its first
entry with no run-time condition (nothing after it can ever be said). An NPC's candidates for a topic are the
merge of the few lists whose audience holds it; the engine walks that merge in order and stops at the first entry
whose conditions all hold. With `aw_npc_voice_pick 1` it picks at random among those that hold (an AmiWind option).

## Engine

`engine/aga/src/aw_glut.c`:

- **Load:** once, at the first NPC spawn. The part before the texts (450,216 bytes for the game data) is one
  allocation outside the Quake heap; a line's text (306,989 bytes in all) is read from the file when it is said.
- **Lookup:** by the entity's `aw_source_id` (its NPC record), a binary search over the sorted ids (12 compares for
  2,673 records), cached per edict. No allocation and no string parsing at greet time.
- **Hello:** an NPC placed without a greeting of its own (`aw_voice` empty, hello distance 0: the actor library's
  NPCs, `tools/npc_library.py`, such as the outdoor region actors) takes its hello distance from the table at spawn
  (QC `aw_glut_prep`, #84);
  when the player comes near, the QC greeting rule says the table's Hello (`aw_glut_say`, #85; `aw_glut_text`,
  #86): the line in the centre print, the voice on channel 2. A voice file the build lacks: the line is shown and
  nothing plays. Town residents keep their own per-placement hello.
- **Conversation greeting:** a talk with an NPC that has no `aw_greeting` of its own opens with the table's
  (`aw_converse`), its defines filled: the speaker's from the NPC row (%Name is the entity's name), the player's by
  the dialogue reader.
- **Barks:** Idle, Hit, Attack and Flee (`aw_anim.c` AW_VoiceSay, the original's odds) come from the table for every
  NPC whose record is in it, town residents too, so every NPC has its full vocabulary. Creatures keep their
  models' lines.
- `aw_npc_voice_lut 0` (saved): the previous method, each model's own bark lines and no table greeting.

Not wired yet (no engine event): Intruder and Thief (crime witnesses), Alarm. Functions the engine does not know
yet fail their condition (as the build-time greeting passes over them): PcGender, SameSex, SameRace, Weather,
PcMagicka, PcFatigue, the player's attributes and skills, the player's gold. Disposition is the NPC's base value
(no modifiers yet); globals keep their start value until scripts run; journal, locals and dead counts read 0.

## Cost

Measured on the game data (23 October 2026):

| Topic | Candidates per NPC (average / most) | Lists merged (most) | Condition records (average / most) |
| --- | --- | --- | --- |
| Hello | 141 / 188 | 6 | 267 / 350 |
| Idle | 8.4 / 11 | 3 | 8 / 10 |
| Hit | 17.8 / 20 | 2 | 28 / 33 |
| Attack | 16.9 / 21 | 2 | 20 / 28 |
| Flee | 4.9 / 6 | 3 | 4 / 5 |
| Conversation greeting | 93 / 173 | 21 | 176 / 385 |

Those are the whole walks; a pick stops at the first entry that holds. One condition record is one switch case, a
few byte loads and a compare (about 30 to 40 instructions); taking the next entry of the merge is one compare per
list. The worst Hello walk is about 21,000 instructions and the worst conversation greeting about 37,000: on a
25 MHz 68040 roughly 1 to 2 ms and 2 to 3 ms, once per greeting, never per frame. Idle, Hit, Attack and Flee are
under 2,000 instructions. The id lookup (once per actor) is 12 string compares.

## File format

Big-endian, every table 4-byte aligned. `tools/greeting_lut.py` writes and reads it; `aw_glut.c` checks every count,
offset and index once at load, so a pick never reads past the data.

| Part | Bytes | Fields |
| --- | --- | --- |
| Header | 80 | `AWGL`, u16 version 2, u16 topics, u32 counts (NPCs, sets, list sets, list set items, lists, list items, entries, conditions, sounds, globals, names, string bytes, text bytes), u16 reset distance, u16 greet seconds, u16 functions, u16 0, u16 creature rows, u16 named slots, u32 SOUN rows, u32 0 |
| Topics | 4 each | u32 string offset of the topic's name (`greeting` last) |
| Fixture | 4 per function, then a bit map | i32 start-of-game value of each SCVR function; bit set = known |
| NPC rows | 24 each, sorted by id | u32 id, u16 hello distance, u8 disposition, i8 rank (-1 none), u16 set, 5 x u16 define names (class, race, faction, rank, cell; 0xFFFF none), 2 x u16 0 |
| Sets | 2 per topic | u16 list set of each topic (0xFFFF none) |
| List sets, items | 8; 2 | u32 first item, u16 count, u16 0; u16 list |
| Lists, items | 8; 2 | u32 first item, u16 count, u16 0; u16 entry (ascending: the original's order) |
| Entries | 12 | u32 text offset (0xFFFFFFFF none), u32 first condition, u16 sound (0xFFFF none), u8 conditions, u8 flags (1: no run-time condition, its list ends) |
| Conditions | 8 | u8 opcode, u8 comparison, u16 operand, i32 or f32 value |
| Sounds | 12 | the pool file's 16 hex digits as 8 bytes, u16 length (1/100 s, 0 unknown), u16 flags (1: the build has the file) |
| Globals | 8 | u32 name, f32 start value |
| Names | 4 | u32 string offset |
| Creature rows (version 2) | 20 each, sorted by id | u32 id, 8 x u16 sound (left foot, right foot, swim left, swim right, moan, roar, scream, land; 0xFFFF none) |
| Named slots (version 2) | 2 each, padded to 4 | u16 sound of each sound the engine plays by name, in `aw_glut.h` AW_SLOT_* order |
| SOUN rows (version 2) | 16 each | one per SOUN record of the three masters, sorted by folded id: the pool file's 8 bytes (zero when not converted), u16 length, u8 volume, u8 flags (1 mapped), u16 near, u16 far (the record's distances times `fAudioMinDistanceMult` and `fAudioMaxDistanceMult`) |
| Strings | | ids, names, topic names (NUL-terminated cp1252), padded to 4 |
| Texts | | the lines' texts, last (not kept in memory) |

### Condition records

Comparison byte: 0 `==`, 1 `!=`, 2 `>`, 3 `>=`, 4 `<`, 5 `<=` (the SCVR order); bit 7 set: the value is an IEEE
single, else a 32-bit integer. The operand classes are meant for the compiled scripts of the roadmap's MWScript step
to reuse: a global by its index in the globals table, a journal, item, dead, local, cell or faction id by its index
in the names table, a function by the original's SCVR function number.

| Opcode | Name | Operand | Tests |
| --- | --- | --- | --- |
| 1 | FUNC | SCVR function number (0 .. 74) | the function's value: live for Health_Percent, PcHealthPercent, PcHealth, TalkedToPc and FactionRankDifference; the start-of-game fixture for the rest; unknown fails |
| 2 | GLOBAL | global index | the global's value (its start value until scripts run) |
| 3 | LOCAL | name index | the speaker's script local (0 until scripts run) |
| 4 | NOTLOCAL | name index | not (the local compared) |
| 5 | JOURNAL | name index | the journal index (0 until the journal exists) |
| 6 | ITEM | name index | the player's count of the item (0; gold not known: fails) |
| 7 | DEAD | name index | how many of that id are dead (0) |
| 8 | CELL | name index | value 1: the NPC's home cell starts with the name; 0: it does not (NotCell) |
| 9 | DISP | none | the disposition, compared with the value |
| 10 | PCFACTION | name index (0xFFFF: the speaker's faction) | the player's rank in the faction (no faction yet: fails) |
| 11 | RANDOM100 | none | Random100, rolled 0 .. 100 per pick |

### The sound table (version 2, 27 October 2026)

The same file also holds every creature's sound generators and the sounds the engine plays by name (a swing, a
miss, the armour and hand-to-hand hits, health damage, bow and crossbow, landing, body falls, footsteps, swimming,
each item kind's pick-up and put-down), as indexes into the Sounds table above. There is one table for these sounds; the combat
sheets keep no list of their own. The creature rows come from all three masters, and the builder resolves the
original's fallback (own generator, the original's, one of a creature with the same model, the generic one).
Every Sounds row also carries the converted file's length and whether the build has it, and one SOUN row per sound
record carries what the compiled scripts' PlaySound and its kin need (file, length, volume, hearing distances), so
the scripts read the same table instead of keeping their own copy. Engine calls: `AW_GlutCreatureFind`,
`AW_GlutCreatureSound`, `AW_GlutSlotSound`, `AW_GlutPoolPath`, `AW_GlutSoundLength`, `AW_GlutSoundMapped`,
`AW_GlutSoun` (`aw_glut.h`; an index is the pool file `sound/pool/a<16 hex>.wav`). The rules and the counts are in
[NPC_DEFAULTS.md](NPC_DEFAULTS.md#how-the-game-names-its-sounds). On the game data with the v0.0.53 media stage:
396 creature rows (1,321 moments from the creature's own or its original's generators, 1,760 from the generic
ones, none empty), 73 named slots, all found, and 601 SOUN rows, 599 of them converted; the file grows from
757,205 to 801,393 bytes, the part kept in memory from 450,216 to 494,404.

## Size and the build

On the game data: 757,205 bytes (450,216 kept in memory, 306,989 of texts): 2,673 NPC rows, 1,553 sets, 1,759 list
sets, 1,078 lists, 7,247 entries, 12,025 condition records, 4,224 sounds, 15 globals, 1,620 names.

The image step writes it (`tools/build_aga.py` finalize_image, `greeting_lut.image_step`): one unit in the image pass
cache (`npc-voice-table`), keyed by the SHA-256 of `Morrowind.esm`, the sound sources the data offers and the
module's sources; its report is `npc-voice-table.json` beside the image. Built from nothing it took 10 seconds on 6
workers (the NPC records in 25 units); with unchanged inputs the unit is taken from the cache.

The voices it names: 4,224 files, 108.4 MB as converted, 4,223 of them in a full build's voice payload (6,447 voices,
186.0 MB in the v0.0.47 builds). The one missing is `vo\d\f\Hit_DF007.mp3`, one of the media catalogue's 7 voice
sources the data does not have. So the image grows by the table file only. A MiniWind build keeps only the voices
its reference closure's actors can say (4,158 in the Balmora room builds); the table's lines of other NPCs are then
shown without a voice.
