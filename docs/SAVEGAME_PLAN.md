# Save/load milestone: compact state and a manageable save list

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

<!-- contents start -->
## Contents

- [First usable save](#first-usable-save)
- [Avoid clutter in files and in the UI](#avoid-clutter-in-files-and-in-the-ui)
- [Format and failure recovery](#format-and-failure-recovery)
- [Sanity check against original saves and OpenMW](#sanity-check-against-original-saves-and-openmw)
- [Planned: importing original and OpenMW saves](#planned-importing-original-and-openmw-saves)
- [Actors in rooms and their packages (v0.0.57)](#actors-in-rooms-and-their-packages-v0057)
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
two. Kept by `tests/aga_save_changes_test.c` (a room entry round trip and its refusals).

## References inspected

- Owned CharGen and CharGenDoorExitCaptain scripts: original completion/save gate.
- [OpenMW ESS importer](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/essimporter/importer.cpp)
- [OpenMW state manager](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwstate/statemanagerimp.cpp)
- [OpenMW creature stats fields](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/esm3/creaturestats.hpp)

Retain original supplied saves as read-only references when collected. No such
controlled ESS comparison pair was supplied in this session; that gate is pending.
