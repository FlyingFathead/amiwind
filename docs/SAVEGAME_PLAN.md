# Save/load milestone: compact state and a manageable save list

**Status:** the post-RC3 checkpoint adds AWS2 dated journal history, retaining
AWS1 decoding without invented history. See [journal schema and limits](WORLD_MAP_AND_JOURNAL.md).
The original AWS1 prototype was implemented for the v0.0.21-dev1 opening slice,
with registration/release eligibility. Character folders, quicksave, four fixed
manual slots, 0–16 autosaves (default 3) and dual validated generations are
implemented. Native filesystem and failure acceptance are recorded with the
playtest evidence. The design below remains the broader target; named manual
saves, general object deltas and controlled original ESS comparisons are pending.
See [checkpoint limits](RELEASE-v0.0.21-dev1.md). Requested 28 September 2026. Deliver with the next dock/Census milestone once its character
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

## References inspected

- Owned CharGen and CharGenDoorExitCaptain scripts: original completion/save gate.
- [OpenMW ESS importer](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/essimporter/importer.cpp)
- [OpenMW state manager](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwstate/statemanagerimp.cpp)
- [OpenMW creature stats fields](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/esm3/creaturestats.hpp)

Retain original supplied saves as read-only references when collected. No such
controlled ESS comparison pair was supplied in this session; that gate is pending.
