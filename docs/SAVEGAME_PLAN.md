# Save/load milestone: compact state and a manageable save list

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

<!-- contents start -->
## Contents

- [The save design in brief](#the-save-design-in-brief)
  - [1. What a save is](#1-what-a-save-is)
  - [2. What must be kept](#2-what-must-be-kept)
  - [3. Item kinds and item instances](#3-item-kinds-and-item-instances)
  - [4. The journal](#4-the-journal)
  - [5. Scripts](#5-scripts)
  - [6. Stable identities](#6-stable-identities)
  - [7. When and how a save is written](#7-when-and-how-a-save-is-written)
  - [8. Memory](#8-memory)
  - [9. The gameplay contract](#9-the-gameplay-contract)
  - [10. Acceptance tests](#10-acceptance-tests)
  - [11. Where v0.0.66-dev2 stands](#11-where-v0066-dev2-stands)
- [First usable save](#first-usable-save)
- [Avoid clutter in files and in the UI](#avoid-clutter-in-files-and-in-the-ui)
- [Format and failure recovery](#format-and-failure-recovery)
- [Sanity check against original saves and OpenMW](#sanity-check-against-original-saves-and-openmw)
- [Planned: importing original and OpenMW saves](#planned-importing-original-and-openmw-saves)
- [Actors in rooms and their packages (v0.0.57)](#actors-in-rooms-and-their-packages-v0057)
- [The world change list (v0.0.59)](#the-world-change-list-v0059)
- [Magic, items and effects in saved games (v0.0.61)](#magic-items-and-effects-in-saved-games-v0061)
- [The actor block, the saved actor rows and the explored map (v0.0.66)](#the-actor-block-the-saved-actor-rows-and-the-explored-map-v0066)
- [Bounds above the game (v0.0.66)](#bounds-above-the-game-v0066)
- [Item instances: two copies of one kind kept apart (v0.0.66)](#item-instances-two-copies-of-one-kind-kept-apart-v0066)
- [References inspected](#references-inspected)

<!-- contents end -->

## The save design in brief

### 1. What a save is

**The restored game is the game's content plus the persistent player and world state.** The content (terrain, buildings,
placements, item and character definitions, dialogue, scripts) comes from the installed game files and is never copied
into a save. The save records what happened in this playthrough.

**Every save is complete and self-contained.** It holds every persistent change relative to the original game data, not
only the changes since the previous save: objects in cells visited long ago, script variables, quest progress,
inventories and timers included. Loading a save never needs an earlier save or a leftover session file. The original
game and the reference engine, OpenMW (GPL-3.0), work this way, and AmiWind follows them.

Two flags are kept apart:

| Flag | Meaning |
| --- | --- |
| Changed from the original | The change stays in every later save. Clearing it would make later saves forget earlier actions: a theft in Seyda Neen must still be known after a second save in Balmora. |
| Changed since the last save | A working flag only, for caches and snapshots. It may be cleared after a save. |

Something never touched costs nothing in the save. Small systems (the player, the globals) may be written whole where
that is simpler than a difference; the large population of placed references is written sparsely. For a changed object
only its latest state is kept: opening and closing a door many times leaves one entry, and a field that returns to its
original value loses its override. Where the game data still contains an object, its removal is written explicitly,
otherwise the next load would recreate it.

### 2. What must be kept

The rule: **keep what would change the continuing game; rebuild what is only implementation.** Forgetting which actor
someone was pursuing, or the fireball about to hit, changes the game; a path search or a particle effect can be built
again.

| Category | Kept |
| --- | --- |
| Player and progression | Name, appearance, race, class, birthsign, attributes, skills, health, magicka, fatigue, level progress, faction standing and ranks, reputation, bounty, place and facing |
| Inventory and equipment | Items with count, condition, charge and soul-gem contents; what is worn or wielded; the selected enchanted item |
| World references | Taken, moved, dropped and deleted objects, enabled state, ownership, locks, traps, doors |
| NPCs and creatures | Changed statistics, death and where the body lies, whether it was cleared, disposition, items, AI packages with their targets and destinations, fights, companions |
| Quests, journal, dialogue | Quest stages, journal entries, topics known, lines heard |
| Scripts | Globals, each object's script variables, running global scripts |
| Magic | Known spells, active effects with their remaining durations and magnitudes, power cooldowns, who cast what |
| World simulation | Time, weather, respawn clocks, projectiles in flight, the random state |
| Made things | Spells, potions and enchantments the player made, with the counter that names the next one |
| Map and controls | The explored map, map markers, quick keys |

### 3. Item kinds and item instances

"Iron longsword" is a kind of item, not one sword. A stack of identical items is saved as a count. When condition,
charge, ownership or script state differ, the copies are separate entries, and equipment points at the entry it uses.
Merely saving a count for a kind cannot tell three swords apart.

### 4. The journal

The current stage of a quest does not say which entries the player received, in what order, or on which day. The
journal is saved as ordered entries. Text that is fixed in the game data is referred to, not copied; text whose
wording depends on the moment it was written (names and numbers filled in) keeps its value from that moment, so an old
entry does not change when the character does.

### 5. Scripts

Script state is saved as data, never as an interpreter's stack: the named variables with their values, whether a global
script is running or stopped, and the identity of the object that owns the variables. A save is made at a defined
point between script runs, so no script is caught half way. A stopped script stays stopped after a load.

### 6. Stable identities

Every placed reference has an identity made from its content file and its reference number, so a save names the same
object whatever the order of loading, the map it is drawn in, a rebuilt world or an added expansion. An object moved to
another place stays the same object, and the move is recorded so that its original placement does not appear again.
Objects created in play are saved with their ids and with the counter that gives the next id, so a new object never
takes an id a restored one holds. A save made with other game data is told apart by what changed: a rebuilt asset that
keeps the identities loads; a reordered table needs mapping; a changed script layout needs migration; removed content
cannot be restored, and the load says what was left out.

### 7. When and how a save is written

A save is captured all at once at a settled point: the current gameplay step and script run are finished first, so no
transfer is caught half way (an item removed from a chest and not yet in the pack would be lost, the other order would
copy it). Capture is checked as complete; a failed export refuses the save. The file is then written to the inactive of
two generations, closed and read back and checked, and only then reported as saved. The checksum shows the bytes are
intact; the completeness check shows the state is all there. Both are needed.

Loading restores the whole state first, and only then do scripts and gameplay events run again, so that a load never
repeats a reward, rolls loot again or fires a pick-up.

Autosaves (`aw_autosaves`, Options > Prefs > Autosave history: 5 kept by default, 0 turns them off) are written after
every map change once the player has been released from the opening, as soon as the player has stood settled for three
seconds (alive, walking, on the ground, out of lava, slime and deep water, no fight, no window or menu, no loading
screen, no photo mode, no voice line playing), and every five minutes of play in between. `dbg save status` shows how
many autosaves the character has, when the next one is due, what holds it back at that moment and how the last save
ended (written, or the part that refused it). The opening journey checks after the release that an autosave is on
disk, so a game that stops writing them fails a test instead of going unnoticed. A save asked for while a script step
runs waits for the step to end; a step that an error ended without finishing (the game's error handling jumped out of
it) is let go at the next frame, with one console line, so it never holds the saves for the rest of the session.

### 8. Memory

The peak extra memory while saving and loading is measured first: the live state, the temporary copies, the encoded
file and the state decoded but not yet applied. If it is a problem, the file is written through a small reusable buffer
(a few KB), with the lengths known beforehand or patched, an incremental checksum and a streamed check of the result.
That keeps the file format and the recovery behaviour. Changes of cells that are not loaded could move to disk if a very
long game ever needs it, copied across at each save; the save still stands on its own.

### 9. The gameplay contract

For every system the question is: what must be true right after loading? Examples:

- A partly burned light keeps its fuel.
- An effect keeps its remaining duration, and a power its cooldown.
- A companion still follows or escorts.
- A dead quest character stays dead.
- A restored stat is not changed again by an effect that is already in it.
- A container keeps the contents it had, not a fresh roll.

Authoritative values are saved together with what is needed to rebuild the derived ones.

### 10. Acceptance tests

| Test | Required result |
| --- | --- |
| Take an object, leave, save twice, load | It is still gone from its original place |
| Move or drop an object into another cell | Exactly one copy, in the right place |
| Change script variables, stop a global script, rebuild with reordered scripts | The same scripts get the same state, or the load says it cannot |
| Save a carried item that has a script | Its variables and one-time behaviour survive |
| Carry two copies with different condition or charge | Each keeps its own values and its worn state |
| Active effects, a cooldown and a companion | Their continuing behaviour survives |
| Export failure, full disk, truncated file | No incomplete save is reported as made; the previous one still loads |
| Load and save an unchanged game again and again | Nothing accumulates: no duplicates, rewards or stat changes |
| Every part at the game's full count (all its NPCs, creatures, quests, topics) | It saves and loads, or the save is refused with a clear message |
| Save, load, save | The two files are the same bytes |

Every change to the save also has to answer one question: what happens when this part fills?

### 11. Where v0.0.66-dev2 stands

What exists: the sparse world change list (the parts below), tagged and versioned sections that older saves still load
through, checksums, two generations with a read-back check, and fingerprints of the content a save was made with. The
engine already refuses a save when the script, change-list, object or actor-block export fails. The saves of the
original game and of OpenMW store the same kinds of state; AmiWind keeps its own format with packed fields (short
reference ids, a field mask, positions in steps) instead of their record layout. A full comparison of the reference
engine's save records with ours follows in a later update.

Known gaps, in the order they are being worked on:

1. An export failure must refuse the save: the engine does so, and tests that inject each failure are being written.
2. Script variables are matched to their script by position inside the script; a layout signature is missing.
3. The script variables of carried items are not kept.
4. Item instances: one condition and one charge are kept per kind in the pack.
5. The fixed limits (`SAVE-STATE-FIXED-CAPS-66` in the [bug register](BUGS.md)): the saved actor rows stop at 256 and
   hold NPCs only, so beyond 256 actors, and for creatures such as companions, the state is not saved; the journal, the
   map markers and the explored map of rooms keep 256 entries each; the explored map shares a 32 KB part with other lists
   and can make the save be refused when it fills. The limits are being measured against the game's real counts. The
   save must hold every change the game makes, with no fixed cap that can refuse a save or silently drop state.

Where each kind of state is kept, for the reference engine's records:

| Reference engine record | Where AmiWind keeps it | State |
| --- | --- | --- |
| Journal and quest state | The change list, fourth part (every quest's stage by its id) | Done; journal entry limit being lifted |
| Dialogue state | The change list: topics known, disposition | Done |
| Cell state: placed objects | The change list, first part (taken, disabled, moved, dropped) | Done |
| Doors | The change list, second part (open, locked) | Done |
| Containers | The change list, third part (difference against the contents) | Done |
| NPC states | The change list, sixth part, and the saved actor rows | Partial (rows stop at 256) |
| Creature states | The same rows | Partial (companions and scripted creatures may not be kept) |
| Globals and script locals | The change list, fourth and fifth parts | Partial (carried items' variables missing) |
| Active spell effects | A block of its own (v0.0.61) | Done |
| The map's fog and markers | The explored map and the markers | Partial (limits above) |
| Stolen items | The change list, second part (by item and owner) | Done |
| Weather, projectiles, random state | Not confirmed in this page | Planned |

The references used are listed at the end of this page, among them the reference engine's save code at
[commit 57e437a](https://github.com/OpenMW/openmw/tree/57e437a85b312f31fb6c110e28e5a6f3ab9f60bc).

**Status:** the post-RC3 checkpoint adds AWS2 dated journal history, retaining
AWS1 decoding without invented history. See [journal schema and limits](WORLD_MAP_AND_JOURNAL.md).
The original AWS1 prototype was implemented for the v0.0.21-dev1 opening slice,
with registration/release eligibility. Character folders, quicksave, four fixed
manual slots, 0–16 autosaves (default 5) and dual validated generations are
implemented. Native filesystem and failure acceptance are recorded with the
playtest evidence. The design below remains the broader target; named manual
saves, general object deltas and controlled original ESS comparisons are pending.
Since v0.0.59-dev4 a world change list keeps taken, dropped, moved, disabled and locked objects (below); since
v0.0.59-dev5 it keeps the actors too, and respawn and saves made with other game data are handled (seventh part).
See [checkpoint limits](releases/notes/RELEASE-v0.0.21-dev1.md). Requested 28 September 2026. Deliver with the next dock/Census milestone once its character
record is authoritative: attributes set and the game saveable/loadable. See [character creation](CHARACTER_CREATION.md) and
[world persistence](PERSISTENCE_AND_STREAMING.md).

## First usable save

Persist name; race, sex, head and hair IDs; class and birthsign IDs; level;
Strength, Intelligence, Willpower, Agility, Speed, Endurance, Personality and
Luck; skills; health/magicka/fatigue; scene, position and facing; inventory;
creation/quest globals, actor/script state and player-control permissions.
Use stable source reference IDs for changed objects. Store attributes as base
values plus applicable modifiers/damage and resources as current/maximum values.
Define which effects survive reload; avoid accidentally applying class/race
bonuses twice. Initial attribute fields alone are a foundation, not a complete
save system, and should be labeled as such during development.

## Avoid clutter in files and in the UI

Proposed defaults, to validate in the first implementation:

- Group saves by character. Show name, location, level and play time.
- Player-adjustable autosave history: retain the last **X snapshots** per
  character. Proposed initial default 3; expose the count in Load/Save options
  with a measured safe range and an explicit off setting. X means save generations,
  not character levels or visited maps. Rotate only after the new snapshot fully
  validates. Changing retention must not discard the only good recovery copy.
- One rotating quicksave with a recovery copy.
  Manual saves are named and deliberately created/overwritten. Never silently
  delete manual saves or another character's saves to meet a quota.
- Show the newest useful entries first; allow explicit expansion of older manual
  saves. Small optional thumbnails; avoid embedding large duplicate artwork.
- Store immutable meshes, textures, sound and base cell data once in content
  packs. Save changed state only, with one canonical entry per object/global.
- Compact superseded deltas only after writing and validating a replacement;
  preserve tombstones for removed/taken objects so they do not respawn on reload.
- Report file size and counts per state category in diagnostics. Repeated
  save/load and unchanged-cell revisits should stabilize rather than accumulate
  duplicate state. Do not promise arbitrary size limits before measurement.

## Format and failure recovery

Use a documented format version, build metadata, content-set fingerprint,
bounded section lengths/counts, explicit byte order and integrity checksum.
Optional future sections must be safely skippable; unsupported required sections
or incompatible content must fail with a readable explanation before replacing
the live session. Never serialize heap addresses, renderer caches, live file
handles, decoded audio buffers or transient preview resources.

Write a new sibling temporary file in bounded chunks. Check every write and
close, validate the result, then promote it with a recoverable old copy. Test the
actual Amiga filesystem's rename/overwrite behavior; do not assume POSIX atomic
replacement. Choose the newest fully validated generation after interruption.
Keep the active session and last good save intact after disk-full, truncated or
failed writes. Compression is optional only after timing and memory measurements.

Original scripts make normal saving available after CharGenState becomes -1.
OpenMW's save-eligibility check also checks completed chargen. Respect that gate
for ordinary play; any temporary developer-only creation checkpoint must be
explicitly separate and restore the entire interrupted state.

## Sanity check against original saves and OpenMW

Bethesda's original engine source/save implementation was not supplied. The
comparison here is with the owned game scripts/records and OpenMW's reader for
original ESS files, plus OpenMW's own save writer. No claim of binary ESS or
OMWSAVE compatibility, or a completed corruption comparison, is made.

OpenMW's ESS importer handles many distinct state categories (including globals,
NPC/reference changes, cells, journal and dialogue). Its writer separately
serializes world, script, journal/dialogue, mechanics, input/UI and profile data.
This is evidence for an explicit state inventory; copying a save header and
player coordinates would omit required behavior. OpenMW stages serialization in
memory to avoid replacing an existing save on serialization failure. For the
Amiga target, use bounded disk staging with measured memory instead of buffering
the whole growing world snapshot.

Before enabling Save/Load:

1. Capture controlled original-game and OpenMW saves before/after one action:
   character choice, moved item, taken item, door change, NPC movement, quest
   update, cell transition and rest. Compare semantic changes, not padding bytes.
2. Verify our state inventory covers each relevant change; document deliberate
   prototype omissions and keep affected menu functions disabled.
3. Round-trip every race/sex and boundary attribute value; class/birthsign
   application, appearance IDs, selected scene and story gates must match.
4. Test duplicate IDs, missing/changed content, invalid versions/counts, NaN or
   out-of-range values, truncated files and checksum errors before state mutation.
5. Inject write/close/rename failures and disk-full conditions. The previous save
   and running game must survive. Repeated load/reload must not grow objects,
   inventory, bonuses or file size without a corresponding gameplay change.
6. Test autosave X=1, the default and maximum, history reduction/increase,
   disabling/re-enabling, rotation after a failed write and per-character isolation.
   Never rotate manual saves. Trigger autosaves only at settled safe states after
   chargen; coalesce simultaneous triggers and test transition/audio interactions.
7. Run on the reference FS-UAE configuration and then WinUAE/physical hardware;
   measure save latency, audio behavior, memory peaks and long-session growth.

## Planned: importing original and OpenMW saves

Planned for v0.0.57 (decided 30 October 2026). A save from the original game (`.ess`) or from OpenMW can be loaded into
AmiWind once and becomes an AmiWind save. Why: the same save opened in OpenMW and in AmiWind puts both in the same
game state (place, quest stage, inventory, time of day), so every comparison between the two (scripts, wandering,
dialogue, weapons, fog) is like for like, with no walking both games to the same spot by hand.

How:

- **Reading is cheap.** Both save formats use the game's own record layout (a record tag, a size, then sub-records).
  The game reads the file once, one record at a time from disk, with a small buffer; the embedded screenshot and map
  image are skipped. Nothing of the foreign format stays in memory, and nothing foreign is read during play.
- **Matching is the work.** A save names the original game's references (the content file and the reference number,
  and record ids). The builder writes a lookup table on disk from those to AmiWind's own placements; the import looks
  each changed reference up in it and writes the change into an AmiWind save.
- **What cannot land is said.** Anything the game cannot place yet (a character AmiWind does not spawn, an item kind it
  does not support) is listed by the import, never silently dropped.
- **In the menu: a save browser.** Load Game shows three tabs, **AmiWind**, **Morrowind** and **OpenMW**. The
  Morrowind and OpenMW tabs list the saves of that kind found in the game's import folder, each with its character
  name, place and level read from its header, before anything is converted. Choosing one imports it (an **Import
  Save** step with a short report of what came over and what could not) and the new save appears under AmiWind,
  ready to load. Keyboard and mouse both work.
- **One way, into AmiWind's own format.** The import only reads the original and OpenMW formats and only writes
  AmiWind's own save; AmiWind never writes a `.ess` or an OpenMW save. It also checks and cleans while it reads:
  every record is validated before anything is written, duplicate and orphaned references are dropped, whole copies
  of cells and containers become only the real changes, and a save too damaged to trust is refused with a readable
  reason (original saves are known to grow and break down over a long game). Only files that start with the
  original game's own save header are taken: Oblivion and Skyrim saves use the same `.ess` name in another format.
- A tool on the PC that does the same conversion stays the fallback.

Order: first the study of what each format keeps and loses, then AmiWind's own complete save (every change to the
world as a compact list against the game's data), then the import. OpenMW's own importer of original saves
(below) is studied for the rules; AmiWind's import is its own code.

## Actors in rooms and their packages (v0.0.57)

The change list keys an actor captured in a room by the room's stable number (worldspawn `_aw_cell_int`) and keeps
its position in the room's own coordinates (flag AW_CHANGE_ROOM); an entry of another room or of the outdoors is not
applied in this one. In a room the actors' state is captured as they stand and applied after a load and when the
room is entered again (rooms have no CHIM window tick, so `AW_ActorsRoomTick` does it). The actors' travel and
follow packages started by the scripts (AITravel, AIFollow) are saved as their own block (AWPK, 26 bytes a package:
the actor, the state, the target point, the followed actor, the hours left) and started again when the actor is in
the map; OpenMW keeps the whole package sequence in the actor's state (components/esm3/aisequence.cpp), here only those
two. Since v0.0.62 the block is version 2 (30 bytes a package, the place an AIFollowCell or AIEscortCell names added)
and holds the escorts too; a version 1 block still loads. Kept by `tests/aga_save_changes_test.c` (a room entry round trip and its refusals).

## The world change list (v0.0.59)

The first part of "every change to the world as a compact list against the game's data" is in (CELL-CHANGES-59,
shipped in v0.0.59-dev4). One sorted list for the whole world, every outdoor cell, room and CHIM frame, holds only
what the player or a script changed on a placed object, for the whole session, and is written into the save as its
own block (feature bit 32 of the AWS4 save). The game data is the base: a row holds only the fields that differ from it,
and no row means "as in the data", the rule of the original's saves and of OpenMW 0.51's cell store.

- **Identity.** The builder gives every placed reference a stable id made from its content file's index and its
  reference number, so a save names the same object whatever the map or the order of loading. A thing the player
  dropped is keyed by its inventory serial.
- **What a row keeps.** Taken, disabled by a script, locked (with the level), stolen from an owner, moved (position and
  facing), and dropped (item, count, position, facing, condition). Taken and disabled are separate marks, so a script's
  Enable never brings back what the player took.
- **Where it lives.** Rows grow in steps in memory up to 32,768 rows (a late original game changes about 7,700
  references), and a second order by place (outdoor cell, room or scene) means a map load reads only its own rows. A
  save is read and checked in full before it replaces anything, and saves made with earlier snapshots still load.
- **Selectable.** `aw_placed ledger off` returns to the earlier fixed tables from the next new game or load.

Checked in game at 32 MB Fast RAM: an item taken in a room stays taken across a map change and a quick load, and an
outdoor drop is kept. Not yet checked: frame to frame, an outdoor take after a load, moved objects and the rows on
disk.

Second part (v0.0.59): a hinged door left open stays open, a lock or unlock by a script, the console or the player's key
is kept, and an owned item taken is recorded as stolen from its owner (by item and owner, so the mark goes with the
item through drops, map changes and saves).

Third part (v0.0.59): container contents and NPC ranks on the same list.

- **Containers.** What the player or a script takes out of or puts into a placed container is kept per container as
  the difference against its game-data contents (one entry per container and item, with a signed count), the rule of
  OpenMW 0.51's container store: a container never touched has no entry and shows the data's contents. The data's
  contents are read from disk only when a container is looked at (the focus table's contents list); nothing of them stays
  in memory. Taking from an owned container is theft and marks the item stolen from whom it belongs to, as for a placed item. A
  script's AddItem, RemoveItem and GetItemCount on a container use the same entries. There is no container window yet:
  `aw_placed container` lists the aimed or nearest container's contents and takes or puts items
  (`aw_placed container take ID [N]`, `put ID [N]`, `all` for every changed container).
- **NPC ranks.** A script's RaiseRank or LowerRank changes the NPC's rank in its own faction (OpenMW 0.51's rule: a rank
  changed before goes on from there, LowerRank stops at 0, nothing on the player or a factionless NPC); the rank is kept
  by the NPC's reference and saved, and the conversation reads it (the speaker's rank in conditions and text).
- **Not yet.** Respawning containers keep what was taken (no restock), and levelled lists inside containers are not
  resolved and cannot be taken; both come with the respawn part.
- **Saved form.** The list's third form is written only when it holds a container change or a rank, so a save without
  them stays readable by the earlier engines; every earlier save loads.

Fourth part (v0.0.59): what scripts and conversations change, on the same list.

- **Journal.** Every quest's stage (Journal, SetJournalIndex, GetJournalIndex) is kept by the quest's id, only when it
  is past the start, for all quests of the game; the fixed table of 32 quests no longer limits what is saved.
- **Globals.** The scripts' globals are kept by the global's id, only those that differ from the game data's start
  value, and set back on a load (globals the save does not name go back to their start value, as in a new game).
- **Topics.** The topics the player knows (AddTopic, a link heard in a conversation) are kept as a set of topic
  names, so a rebuilt topic table in another order still matches them.
- **Disposition.** An NPC's disposition changed by a script (SetDisposition, ModDisposition) or a conversation is kept
  by the NPC's reference, with no limit on how many NPCs; back at the game data's value, the entry goes.
- **The engine's own facts.** Named values of the engine (the clock, the map marker and the like) past the 32 slots of
  the state table go onto the list instead of being refused.
- Ids are matched by a hash of the id folded to lower case (the dialogue table's hash); keys are the game's own record
  ids, so the counts are the game's own: 143 globals, 632 quests, about 2,400 topics, every NPC.
- **Saved form.** The list's fourth form is written only when one of these has an entry; every earlier save loads, and
  an earlier save's quest stages from the table of 32 are taken over on the load.
- **Not yet.** The journal book still lists the quests of the table of 32 (the stages are kept beyond it).

Fifth part (v0.0.59): the scripts' own state, on the same list
([MWSCRIPT-STATE-NOT-SAVED-48](bugs/MWSCRIPT-STATE-NOT-SAVED-48.md)).

- **Script locals.** The local variables (short, long, float) of every object's and every NPC's script are kept by the
  object's reference, only those that differ from their start value (0), the rule of OpenMW 0.51 (a reference's local
  script state is part of its saved state). Within a session they were already kept while the player is away from the
  object's map; the interpreter now holds a whole game's worth (the game places 2,115 objects whose script has locals,
  7,388 values in all; the store held 512 objects before). At a save they go onto the list, and at a load they are
  set back, on the loaded map at once and for every other object when its map is next loaded.
- **Global scripts.** A global script started (StartScript) or stopped (StopScript) is kept with its running state
  when that differs from a new game's (the start scripts running, every other one not), and its locals with it (OpenMW
  0.51's global scripts rule). After a load, a started script runs on and a stopped start script stays stopped.
- **Script identity.** A script is named by the hash of its id, with its row in the compiled scripts as a hint. In
  v0.0.59 a load took the values only when that row still had the same name; since v0.0.66 a script whose row moved in
  a rebuilt file is found by its name (the eighth part below).
- **A load starts from the beginning.** Before the saved values are set, every script value goes back to 0 and only the
  start scripts run, so nothing of the session before the load is carried into it; an earlier save, which has no
  script state, loads with the scripts as in a new game.
- **Saved form.** The list's fifth form is written only when a local or a global script is kept; every earlier save
  loads.
- **Checks on the console.** `dbg mwscript call setlocal VALUE [REF]` and `getlocal [REF]` set and read local 0 of an
  object's script (no REF: the first object on the map whose script has a local); `startscript ROW`, `stopscript ROW`,
  `scriptrunning ROW` and `globallocal ROW [VALUE]` act on the script of that row as a script would.

Checked in game at 32 MB Fast RAM on the Seyda Neen MiniWind: a placed object's script local stays as set across a map
change and across a quicksave, a change and a quickload, and a global script started with StartScript runs on across the
map change and runs again after the quickload although it was stopped after the save.

Sixth part (v0.0.59): the actors, on the same list
([ACTOR-STATE-POOL-LIMITS-54](bugs/ACTOR-STATE-POOL-LIMITS-54.md)).

- **Actor rows.** What happens to an NPC or a creature is kept by its reference, only where it differs from the game
  data (the rule of OpenMW 0.51 and of the original's saves): killed (it is not spawned again; a body a script
  removed is the reference's disabled mark of the first part), where it was left with its health then (outdoors on the
  island, or in a numbered room), hostile to the player, following the player, and a levelled reference's roll. These
  rows replace the fixed list of 2,048 entries the actors had; the list holds up to 8,192 of them (the game's actor
  table has 3,437 entries; the original places 2,673 NPCs).
- **Actor records.** The record of an actor that play or a script changed (stats, health, fatigue and magicka, the behaviour
  ratings, disposition, items and spells added or removed, a fight started by a script) is never dropped any more: the
  pool grows in blocks of 128 while every record in it is changed, up to 8,192 (it refused the 129th before), and each
  actor's item and spell changes grow as needed (12 and 8 before). The changed records go into the save with the list,
  so the actor block no longer meets its 32 KB limit; the block keeps the dead counts.
- **Saved form.** The list's sixth form is written only when an actor row or a changed record is kept; every earlier
  save loads. An earlier save's actor entries and actor records are taken over on the load. The actors alive at the
  moment of the save are written as before, and their state replaces their row at the load.
- **Respawn.** Not changed by this part: a killed actor stays dead (the seventh part, with the respawn rules).
- **Checks on the console.** `chim actors kill`, `chim actors fight` and `chim actors hurt N` act on the nearest
  resident; `aw_mwscript_status` lists the actor rows and the live records.

Checked in game at 32 MB Fast RAM on the Seyda Neen MiniWind: a guard killed and an NPC hurt to 7 health stay dead and
hurt (and hostile) after a trip to the tradehouse and back, and after a quicksave and a quickload.

Seventh part (v0.0.59): respawn, and saves made with other game data. With it the change list is complete for
v0.0.59.

- **Respawning containers.** A container whose record is flagged to respawn gets its game-data contents back (its
  entries on the list go) when its place, an outdoor cell or a room, is entered more than iMonthsToRespawn months
  (4 in Morrowind.esm, 2,880 game hours) after the place's last refill; the first refill comes that long after the
  game's start. The place's time is set at each refill, whether a container needed it or not. This is OpenMW 0.51's
  rule (each cell keeps the time of its last respawn); a container not flagged never refills.
- **Respawning actors.** A dead levelled creature comes back when its cell is next loaded, min(fCorpseRespawnDelay,
  fCorpseClearDelay) game hours (72 in Morrowind.esm) after its death, and its levelled list rolls again; a dead NPC or
  creature whose record is flagged to respawn comes back the same way, as the game data has it (its row and its
  changed record go). Any other dead actor stays dead. The time of death is the first moment the list keeps the actor
  dead (when it leaves the window, at a save, or when its fight slot is reused). The clock is the game's own clock,
  which resting and waiting move.
- **Bodies cleared away (v0.0.66).** A dead actor that does not come back (no Respawn flag, not a levelled list's)
  and whose record is not flagged Persistent loses its body when its cell is next loaded fCorpseClearDelay game hours
  (72 in Morrowind.esm) after its death: the body and what it carried go, and the actor stays dead for good (its row
  keeps the death and a "cleared" mark, saved in the seventh form). A Persistent actor's body stays (OpenMW 0.51
  CellStore::clearCorpse; the builder marks such references in the identity table). As in OpenMW, the respawn and
  the clearing happen only when a cell is loaded; resting or waiting in a cell moves the clock but does not respawn
  anything there.
- **Bodies until then (v0.0.66).** Until its clear time a body lies where the actor fell, and it can be looted, in
  every kind of place: a room, a town's own map and an outdoor cell that joins the view again. Before v0.0.66 a dead
  actor of a joining outdoor cell was not spawned at all, so its body was gone at once on a later visit; that older
  method stays selectable with `chim actors corpses 0` (default 1). A body laid down again from the list is not a new
  death: an essential character's message is not shown a second time.
- **The original data, counted (v0.0.66).** Morrowind.esm: 2,675 NPC records, 61 flagged Respawn (438 placed
  references; the clan lairs' vampires among them), 40 essential, 83 Persistent, none both Respawn and
  Persistent; 260 creature records, 28 flagged Respawn (87 placed references), 2 essential, 17 Persistent; 890
  containers, 91 flagged Respawn; 116 levelled creature lists. GMSTs: fCorpseRespawnDelay 72, fCorpseClearDelay 72,
  iMonthsToRespawn 4. Tribunal.esm: 8 of 159 NPCs and 16 of 97 creatures flagged Respawn. Bloodmoon.esm: 13 of 215
  NPCs and 3 of 75 creatures. So most of the island's people stay dead once killed; the wild creatures come back
  through the levelled lists.
- **Essential characters (v0.0.66).** When an actor whose record is flagged essential dies, by any cause (a fight, a
  spell, a fall or a script), the game's own sKilledEssential text is shown in a message box, once per death (OpenMW
  0.51 mwmechanics/actors.cpp). Play goes on; loading a save is the player's choice.
- **Saves made with other game data.** The save names the content files it was made with, and every reference it
  changed by the game's identity (the content file and the reference number, as in the first part) with a hash of the
  reference's record id. The builder writes a table of every placed reference with its record hash and its respawn flag
  (with the focus table). A save whose game data or build differs now loads: a change whose reference no longer
  exists, whose content file is gone, or whose reference now names another record is dropped and counted, never
  applied to another object (OpenMW 0.51's rule: a saved state is applied only to the reference with the same number
  and the same record id). Levelled rolls are rolled again; the changed actor records and dead counts, which name rows
  of the other build's actor table, are left out. The load says how many changes were left out, by kind, in the console
  and on screen. Without the table (an older image) such a save is refused as before.
- **Saved form.** The list's seventh form is written only when it holds a refill time, a time of death, or the record
  hashes and content files of a list that is saved anyway; every earlier save loads.
- **Checks on the console.** `aw_placed pass HOURS` moves the game clock on as waiting does (nothing else of a rest),
  `aw_placed container` says whether the aimed container respawns, and `aw_mwscript_status` lists the refills, the
  actors back and what the last load of other game data left out.

Checked in game at 32 MB Fast RAM on the Seyda Neen MiniWind: the spore pods taken from a slough fern (flagged to
respawn) are back after 2,900 game hours and a trip to the tradehouse; an imperial guard (flagged to respawn) killed is
back; Fargoth (not flagged) stays dead. The town's levelled creatures are not spawned on that MiniWind (the outdoor
actor table is off by default), so the levelled case is checked by the native tests only.

Not yet: the actor block's other parts (spell effects, soul gems, packages) are taken over as saved. The save import
above builds on this list.

Eighth part (v0.0.66): script values by their variable's name, and the items' script values
([SAVE-SCRIPT-ROW-HINT-ONLY-65](BUGS.md), [SAVE-ITEM-SCRIPT-LOCALS-66](BUGS.md)).

- **Variables by name.** The compiled scripts name every script's variables (a key per variable: a hash of its name
  folded to lower case and its type). Every saved value carries its variable's key, and every script with saved values
  a signature of its variables (their names and types in order). While a script's variables are as saved, a value goes
  back by its slot; when a rebuilt script has a variable inserted, removed, moved or retyped, each value goes to the
  variable of its name, converted between whole numbers and floats as the original engine's rule does (a float made a
  whole number is cut toward zero, a short keeps 16 bits). A value whose variable no longer exists is left out; the load
  says in one line how many went by name and how many were left out (OpenMW 0.51 restores a reference's locals by name
  the same way).
- **Script identity.** A saved script is found by the hash of its name, its saved row only tried first; a script whose
  row moved is found with one read of every row's name hash. Two names that share a hash are never mixed: the builder
  refuses a script file in which two scripts, two globals, two quests or two worn items' ids share one, and two
  variables of one script that share one are saved without a name, so they go back only while the script is unchanged.
- **Items' script values.** The values of an item's script are saved with the item, by its holder (the player, or the
  container, NPC or creature that holds it), its item id and its instance (one instance per item kind until items are
  kept one by one): before v0.0.66 they were not saved at all. An item a container or an actor holds keeps its values
  between visits once its script changed one; an item the player wears keeps its values across map changes (they were
  dropped at every door) and, after a load, runs its script again if it is still carried, so a one-time message or
  effect does not repeat.
- **Saved form.** The list's eighth form is written only when a value keeps a name, a script a signature or an item a
  value; every earlier save loads, its values by their slot as before.

**The settled capture boundary (v0.0.66, [SAVE-INSIDE-SCRIPT-STEP-66](bugs/SAVE-INSIDE-SCRIPT-STEP-66.md)).** A save is
taken only between script steps. While the frame's script tick or a dialogue answer's result script runs, a gameplay
transaction may be half done (an item moving, a reward being given), so a save asked for then (a console command a
script's message box lets through, the save menu) is queued, not taken: the line says so, and the save is written at the
first following frame that is outside a script step and has no load waiting, with the usual Saved line. The autosave
already waited for a settled state; the recorder's starting save and the debug snapshot refuse while a step runs.

**Every part or none (v0.0.66, [SAVE-EXPORT-FAILURE-ACCEPTED-65](BUGS.md)).** A save is written only when every part of
it was kept: the changed actor records, the scripts' values, globals, quest stages and known topics, the references'
identities, the actors' and the objects' changes, the actor block, the dated journal. When one cannot be kept (no
memory, a table at its bound, a name table that cannot be read), or the world change list refuses a row while the save
is taken, the save is refused with one line naming the part: nothing of it is written, the previous save stays as it
was, and the game goes on unchanged. A native test runs the save with each part made to fail in turn. The actor
block's own parts (the spell effects, the things sold, the made spells and items, the soul gems, the faction reactions,
the revealed places, the topic pages, the forced sneak and run, the scripted weather, the crime marks, the werewolf
state, the moved placements, the packages) each name themselves, so the line says which of them could not be kept; a
part that only wanted a bigger block is not a refusal (the block grows first).

## Magic, items and effects in saved games (v0.0.61)

- **Active spell effects** are kept in a block of their own (older saves still load). Every effect applied to an actor
  by reference is kept with its time left; the player's constant-effect items are set again from what is worn after a
  load. In v0.0.61-dev2 the block was read at the wrong size, so a save made with an effect active lost the effects,
  and the made spells, enchanted items, soul gems and the other blocks stored after them, when it was loaded; it is read
  at its real size since v0.0.61-dev3 (`SAVE-EFFECTS-BLOCK-SIZE-61`).
- **Items.** The item table has no fixed number of kinds: it grows in blocks of 32 rows. A save with more than 32 kinds
  sets a feature bit (512) that older versions refuse rather than lose items; saves of the earlier 128-kind table
  (feature bit 256) still load. The player's items keep their condition and charge, and recharge over time; an NPC
  weapon's charge is kept for the session only.
- **Starting spells** are chosen once, when the character is made, and kept with the character.

## The actor block, the saved actor rows and the explored map (v0.0.66)

- **The actor block is a setting.** The block that holds the dead counts, the standing and crime marks, the known
  topics, the spell effects, the made spells and items, soul gems, sold items, the scripts' weather and movers and the
  actors' packages is `aw_save_block_kb` in `config/game.cfg`: 64 KB by default (it was a fixed 32 KB), 32 to 256
  (values outside are clamped, a value that is not a number reads as 64). Its buffer is taken only while a game is
  saved, and a buffer of the loaded block's own size only while a load waits for its scene; before, two fixed 32 KB
  buffers were held for the whole game. A save made with any earlier version (its block at most 32 KB) still loads.
  A block that needs more than the setting refuses the save with a line naming the setting; the previous save stays.
- **The explored map has a section of its own** (feature bit 4096), as long as it needs. Before, the explored land
  was written into the actor block, and a well explored map with a full block refused the whole save. A save never
  cuts the land: every explored cell is written (5 bytes for a fully explored one, 13 for the others); the rooms
  follow. Saves made by the earlier v0.0.66 builds keep it in the actor block and still load. A well explored game
  (1,752 cells, 300 rooms) takes 20,268 bytes.
- **More rooms remembered.** The explored part of 2,048 rooms is kept (it was 256: a room visited after the 256th never
  cleared on the local map, its doors hidden). That covers every room of the base game and both expansions (about
  1,750). A room costs 52 bytes in memory (its name, its 16 x 16 squares and its share of the name index); the local
  map finds a room by its name index once a frame instead of 256 searches of every name.
- **The saved actor rows** hold, for every NPC and creature of every place, what no other part of the save holds: for
  an actor of the game data, its greetings (how often it has greeted the player, and whether it has); its place,
  facing, health and death are in the world change list and the actor records (above). For a role the builder made
  (the intro's), the row also holds its place and health. An actor with nothing to keep has no row, and a row whose
  greetings are back at the game data's goes. The rows are taken when a place is left (a door, a crossing, a
  teleport), when the actor window lets an actor go, and at the save, so a place left long ago is as it was left.
  There is no fixed number any more (it was 256 rows: the 256th row stopped the capture of the rest of that place and
  the save went on without them); the rows grow as needed. A capture that memory refuses says so on the console and
  the save it belongs to is refused.
- **The rows' saved form** (feature bit 8192): per place its save ID and its rows, each row a 3-byte reference, a
  byte saying what follows, then only that (the place in whole units, the facing in 1.4 degree steps, the health,
  the greeting counts). A greeted NPC takes 4 to 6 bytes (5.7 on average with the places counted), a builder's role 11
  to 15, the most a row can take 25; the earlier form took 48 bytes for every row. 2,720 rows (2,700 greeted NPCs and
  20 roles) take 15,541 bytes. Saves of the earlier form still load, and a row in an expansion's room no longer refuses
  the save (the earlier form's place range ended before the expansions' rooms).
- **Memory.** The two fixed 32 KB buffers and the fixed 256-row tables in the five resident copies of the saved game
  held 126,936 bytes for the whole game; they are gone. What is held now: the explored map (12 bytes a cell, 52 a
  room, both in blocks of 64), the saved actor rows (48 bytes a row, in blocks of 64), and while a save is written or a
  load waits, the actor block, the explored map's section and the rows' copy.
- **Sizes measured** (the codec's test, synthetic data): a fresh save 852 bytes; with a full 64 KB actor block and the
  well explored map above, 86,760 bytes.

## Bounds above the game (v0.0.66)

Every fixed count in the save is now a guard above the game's own counts with both expansions, never a cap play can
reach: the world change list's actor rows 32,768 (the game places about 13,800 actor references; was 8,192;
[SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66](bugs/SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66.md)) and saved script locals 65,536 (the
base game declares 7,388; was 8,192; [SAVE-LOCALS-BOUND-UNDER-GAME-66](bugs/SAVE-LOCALS-BOUND-UNDER-GAME-66.md)); made
spells, enchanted items and potions, and filled soul gems 1,024 each (were 64, the 65th refused; the first 255 of each
stay in the blocks older builds read, the rest ride in blocks of their own;
[SAVE-MADE-RECORDS-64-CAP-66](bugs/SAVE-MADE-RECORDS-64-CAP-66.md)); the explored land rows 8,192
(under 1,600 land cells); the map markers' allowance up to 4,096 with 256 the default. The NPCs' crime marks grow from
32 rows by doubling to 1,024 (was 32 fixed: the 33rd witness took a bystander's row, and a save held at most 32;
[SAVE-CRIME-MARKS-32-ROWS-66](bugs/SAVE-CRIME-MARKS-32-ROWS-66.md)), the places a script reveals on the map from 128 to
1,024 (the dialogue results alone call ShowMap 249 times;
[SAVE-REVEALED-PLACES-128-CAP-66](bugs/SAVE-REVEALED-PLACES-128-CAP-66.md)), both with their first 255 in the blocks
older builds read and the rest in blocks of their own; the scripts' region weather rows 32 (was 8, under the three
masters' 16 regions). The actors' travel and follow packages keep their 255 as a guard (128 slots and 64 pending
packages cannot reach it); a package of an actor without a stable reference cannot be found again after a load and is
not saved. Each raise is a declared worst case in the resident registry's budget, with its reason; the rows cost memory
only while kept.

## Item instances: two copies of one kind kept apart (v0.0.66)

The player's items are counted per kind, with one condition and one charge per kind: two iron longswords, one worn down
in a fight and one new, could not be told apart, a copy picked up with a different condition from the carried ones was
refused, and a weapon or shield could be equipped only when exactly one was carried
([SAVE-ITEM-INSTANCES-ONE-PER-KIND-66](bugs/SAVE-ITEM-INSTANCES-ONE-PER-KIND-66.md)). Since v0.0.66 a kind's count stays
one number and ordinary identical copies stay a stack; a copy whose state differs becomes an **instance** of its own:

- An instance is one copy (or several equal copies) of a kind with its own condition or charge, or simply the copy a slot
  wears or the magic selection names. It takes its serial from the same allocator as the dropped items, so a copy dropped
  on the ground is the same thing when picked up again. The sum of a kind's instances never passes its count; a kind that
  loses its last copy loses its instances; an instance whose state equals the plain copies' and that nothing names
  merges back into the stack.
- Equipping a copy of a kind with several copies makes that copy an instance, so a blow lands on the worn copy alone; the
  slot remembers which copy it wears across a save. Spending a selected enchanted item's charge does the same for the
  selected copy; the instances recharge with the rest.
- Dropping takes the plain copies first, then one instance at a time with its condition; picking up a copy whose
  condition differs from the carried plain ones makes it an instance instead of refusing it.
- The save writes the instances, the slots' copies and the selection's copy as their own section (feature bit 16384),
  only when there is one, so a save without instances is byte for byte as before; an older build refuses such a save
  rather than merging the copies. Kept by the two-swords test (`tests/aga_item_instances_test.c`): two swords through a
  blow, a save and a load (the loaded game saves again to the same bytes), a drop and a pickup, merged when alike.
- A scripted copy's own local variables: the carried script runs for the worn copy, so its values are saved under that
  copy's instance serial (0 for a plain copy, and for an item a placed holder holds). After a load the values go back
  only while that copy is still the player's instance of that kind; a copy dropped, merged or given away since does not
  pass its values to another copy. An item's ownership (stolen) stays by kind and owner on the world change list.

## References inspected

- Owned CharGen and CharGenDoorExitCaptain scripts: original completion/save gate.
- [OpenMW ESS importer](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/essimporter/importer.cpp)
- [OpenMW state manager](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwstate/statemanagerimp.cpp)
- [OpenMW creature stats fields](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/esm3/creaturestats.hpp)

Retain original supplied saves as read-only references when collected. No such
controlled ESS comparison pair was supplied in this session; that gate is pending.
