# Save/load milestone: compact state and a manageable save list

_Last updated with AmiWind v0.0.62-dev1 (2026-11-07)._

<!-- contents start -->
## Contents

- [First usable save](#first-usable-save)
- [Avoid clutter in files and in the UI](#avoid-clutter-in-files-and-in-the-ui)
- [Format and failure recovery](#format-and-failure-recovery)
- [Sanity check against original saves and OpenMW](#sanity-check-against-original-saves-and-openmw)
- [Planned: importing original and OpenMW saves](#planned-importing-original-and-openmw-saves)
- [Actors in rooms and their packages (v0.0.57)](#actors-in-rooms-and-their-packages-v0057)
- [The world change list (v0.0.59)](#the-world-change-list-v0059)
- [Magic, items and effects in saved games (v0.0.61)](#magic-items-and-effects-in-saved-games-v0061)
- [References inspected](#references-inspected)

<!-- contents end -->

**Status:** the post-RC3 checkpoint adds AWS2 dated journal history, retaining
AWS1 decoding without invented history. See [journal schema and limits](WORLD_MAP_AND_JOURNAL.md).
The original AWS1 prototype was implemented for the v0.0.21-dev1 opening slice,
with registration/release eligibility. Character folders, quicksave, four fixed
manual slots, 0–16 autosaves (default 3) and dual validated generations are
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
- **Script identity.** A script is named by the hash of its id, with its row in the compiled scripts as a hint; a load
  takes the values only when that row still has the same name (a rebuilt script file in another order drops them, and
  the drop is counted in `aw_mwscript_status`). The names are read from disk once per script per session.
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

Not yet: corpses are not cleared away after fCorpseClearDelay (a body stays until it respawns or a script removes
it), and the actor block's other parts (spell effects, soul gems, packages) are taken over as saved. The save import
above builds on this list.

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

## References inspected

- Owned CharGen and CharGenDoorExitCaptain scripts: original completion/save gate.
- [OpenMW ESS importer](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/essimporter/importer.cpp)
- [OpenMW state manager](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwstate/statemanagerimp.cpp)
- [OpenMW creature stats fields](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/esm3/creaturestats.hpp)

Retain original supplied saves as read-only references when collected. No such
controlled ESS comparison pair was supplied in this session; that gate is pending.
