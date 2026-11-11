# AmiWind v0.0.64-dev4 (in development)

_Last updated with AmiWind v0.0.64-dev4 (10 November 2026)._

Development snapshot, 10 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.64-dev3](RELEASE-v0.0.64-dev3.md). Previous release: [v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

The fourth snapshot of v0.0.64, "Gone Beyond The Gate". Cobwebs, hanging moss and leaves are drawn with their
see-through parts instead of solid rectangles, and that is now on by default. Spell and trap damage meets the target's
resistances and weaknesses, the stats page lists the player's factions, the journal adds an ending entry it would have
skipped, the groundwork for Solstheim's map rows and HUD region names is in place, and a room load gives back the cached tables of the area left before it
grows. No expansion area is part of the game image yet. The game needs 32 MB of Fast RAM, and the emulator presets of
this snapshot have it.

This snapshot carries v0.0.64-dev1, v0.0.64-dev2 and v0.0.64-dev3 as well: for anyone who did not take dev3, their
changes are in [the dev3 notes](RELEASE-v0.0.64-dev3.md) (which also list dev1 and dev2) and arrive together with these.

## Checked in play on a test build

- **Race resistances on spell and trap damage** were seen in play on a test build of the branch before the merge.

These are checks on a test build, not on this snapshot's image; the in-game checklist below asks for them again.

## Checked by tests, not yet in play

Every other change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet. The register keeps an entry open until its change is seen on an image.

## New since v0.0.64-dev3

### The renderer

- **See-through materials are on by default.** Cobwebs, hanging moss and leaves are drawn with their see-through parts
  instead of solid rectangles (the pass added in dev3 was off by default; a visible fix ships on). The console setting
  is `aw_seethrough_material` (`dbg seethrough`): `0` draws them as solid rectangles as before, `1` is the default, `2`
  also draws them from behind. Typed without a value it prints the current value and the list. Its cost is not yet
  measured on a full build; this snapshot's bench measures it (`ROOM-DECAL-ALPHA-62`, open until seen on an image). A second way to draw them from behind, a
  mirrored copy of each such face, is a build option (`--chim-fence-twosided-faces mirror`) and stays off until measured.

### Spells and traps

- **Spell and trap damage meets the target's resistances and weaknesses.** An effect that can be resisted (the elements,
  poison, paralysis, the drains, damages and absorbs, the mind effects, disintegration) is weighed against the target's
  resist, elemental shield and weakness magnitudes, from its active effects and the always-on abilities of its race,
  birthsign and spells, with its Willpower and Luck roll. A full resistance stops the effect, a partial one scales it, a
  weakness raises it; a Nord's frost immunity now stops a frost trap (`RACE-RESIST-NOT-ON-SPELL-DAMAGE-64`).

### The journal and the factions

- **A quest ending is no longer skipped.** A journal entry at or below the quest's current index is still added once,
  with its finished or restart mark and the journal-updated notice, so an ending reached that way finishes the quest; an
  entry already heard does nothing (`JOURNAL-LOWER-INDEX-ENTRY-64`).
- **The stats page lists the player's factions:** each faction's rank, what the next rank needs, the reputation and the
  bounty (`FACTION-STATS-PAGE-64`). The expulsion message of a faction came in dev3.

### Groundwork for Solstheim

- **Groundwork for Solstheim's map rows and HUD region names.** The region table has rows for the island's frame maps,
  its name and its region names, and the HUD rule names the land first, then the region ("Solstheim / Brodir Grove
  Region"); the debug teleport and the marks read those rows (`WORLD-REGION-NAMES-VF-ONLY-64`). Solstheim is not
  playable in this build yet: its frames exist only in test images.

### Memory

- **A room load gives back the area cache first.** Before a room sizes its growth from the free Fast RAM, every cached
  table of the area left is given back and read again from disk when it is needed; the place's own areas and the list of
  world changes are kept (`ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64`).
- **A memory census by owner** (`aw_memcensus`, off by default, switched on by the console) lists the engine's live blocks
  of 4 KiB or more by the code that asked for them.

### The builder

- **Narrower flora cache keys.** The world flora and world scenery region units are keyed on the part of the tool that
  converts a region, not on the whole tool file, so an unrelated edit no longer rebakes them (`UNIT-KEY-WHOLE-FILE-63`).
- **The collision census.** Every model of a build is ranked by its collision bytes against its drawn faces; the size
  ledger and the build summary list the 20 worst, and a model far above the rest prints a warning that does not stop the
  build.
- **Animation tables carry scale keys:** the engine scales a bone and its children.
- **A Raspberry Pi 4B drive image.** The builder can make a ready-to-write Raspberry Pi 4B drive image (no ROMs, no
  personal settings) for test deliveries.
- **A MiniWind of the Heart Chamber alone** (`akulakhan-chamber`) for the chamber's load work.

### The Toolkit

- **The tracker headline shows one row per land** (Vvardenfell, Solstheim, Mournhold) and one for the build; its version
  fields are taken from the version of the build, and a check fails when the data or the pages fall behind it
  (`TOOLKIT-ELIGIBLE-RELEASE-STALE-64`).
- **Pages reload themselves** when the served data changes.
- **The 3D Map Inspector opens CHIM rooms** and shows, per placed model, its faces, drawing bytes and collision bytes and
  the collision to drawing ratio, with a heat view by visual density, collision bytes or the ratio
  ([the Toolkit](../../AMIWIND_TOOLKIT.md)).

### The register

- New entries: `BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64` (the reuse report counts a stage's whole stored unit group as
  rebuilt when the stage makes no units), `TOOLKIT-WORLD-FORMAT-STALE-64`, `CHIM-STAR-TREES-POP-64`,
  `CHIM-SOLSTHEIM-STAR-HITCHES-64`, `CHIM-SOLSTHEIM-CROWNS-NOT-DRAWN-64`, `STORE-MODELS-VIS-PLANES-BLOAT-64`,
  `JOURNAL-LOWER-INDEX-ENTRY-64`, `BUILD-DIRECT-START-CELL-CHIM-64`, `BUILD-LAYER-DATA-MWAD-SHADOWED-64`,
  `BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64` and `TEST-SAVED-EQUIPMENT-NATIVE-FLAKY-64`; sightings on
  `COLLISION-HULL-CHAINS-33`, `UNIT-KEY-WHOLE-FILE-63`, `PERF-GUARD-RESIDENT-BUSY-HOST-57`,
  `GATE-SMOKE-NO-REMOTE-CONTROL-60` and `AKULAKHAN-CHAMBER-32MB-STALL-53`; `ROOM-LOAD-FAIL-LEAKS-FAST-RAM-64` closed (the
  Fast RAM a failed load leaves is no leak).

## Carried from v0.0.64-dev3, dev2 and dev1

See [the dev3 notes](RELEASE-v0.0.64-dev3.md): game spells, powers and enchantments taking effect again, Activate by id
for the Ghostgate's switches, lava that kills, god mode across map changes, the journal's quest endings and the
expulsion message, the Solstheim star-tree test option, trapped doors and containers, the load trace, the Toolkit's
expansion panes and the builder's expansion switch.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A cobweb in a tomb: see-through by default; `dbg seethrough 0` makes it a solid rectangle, `2` shows it from behind.
- A frost spell or frost trap on a Nord: no damage; a fire spell on a Nord: full damage.
- The stats page after joining a guild: the faction, its rank, the next rank's needs, reputation and bounty.
- A quest with two endings: it moves to the finished list at its ending.
- Carried over from v0.0.64-dev3: a game spell, a power and an enchantment, Argonian Breathing, the Ghostgate's switches,
  lava with god mode across a load.

## Known in this build

- **The Heart Chamber still does not load at 32 MB Fast RAM;** the work is in progress (`AKULAKHAN-CHAMBER-32MB-STALL-53`),
  and the end of the main quest cannot play yet (`ENDGAME-CHAMBER-COLLAPSE-63`, `CHIM-ROOM-HEART-CHAMBER-LOAD-50`).
- **The tree methods are not settled and are test-only:** the star trees exist only in test images, their crowns pop in
  and out while the camera moves and a flight over them has single-frame hitches (`CHIM-SOLSTHEIM-TREE-FACES-64`,
  `CHIM-STAR-TREES-POP-64`, `CHIM-SOLSTHEIM-STAR-HITCHES-64`).
- **Solstheim is not playable in this build yet;** its frames exist only in test images.
- **The see-through materials' cost** is not yet measured on a full build (`ROOM-DECAL-ALPHA-62`).
- **The reuse report** can count a stage that made no units as fully rebuilt (`BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64`).
- Tribunal and Bloodmoon are not built into the image yet (`BUILD-EXPANSIONS-31`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- From [v0.0.64-dev3](RELEASE-v0.0.64-dev3.md) and [v0.0.63](RELEASE-v0.0.63.md): the open entries of their Known lists
  stand. Every other open entry is in the [bug register](../../BUGS.md).
