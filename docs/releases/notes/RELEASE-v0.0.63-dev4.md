# AmiWind v0.0.63-dev4 (in development)

_Last updated with AmiWind v0.0.63-dev4 (9 November 2026)._

Development snapshot, 9 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.63-dev3](RELEASE-v0.0.63-dev3.md); previous release: [v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

v0.0.63-dev3 was not published on its own: everything in it (creatures walking, running and attacking again, 66 more
script functions, the builder's reuse of every earlier run) comes to the main line with this snapshot.

The fourth snapshot of v0.0.63. It fixes four things found in play on v0.0.63-dev3 (health at the start, god mode,
the Argonian's water breathing, Sunder's curse) and carries 27 more functions of the original game's scripting, with the console's
own commands callable from scripts, and a builder that keeps more of its earlier work: its worker pools stay busy, an
engine change to the actor model reader no longer rebuilds the whole world, and the dialogue and voice tables and the
actor ground check come from the unit cache. 605 of the 1,207 scripts run as scripts and 8 more are carried by the
game's own code (the same as in v0.0.63-dev3). The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.63-dev3

### Fixed in play

These four were seen in an emulator session of v0.0.63-dev3 at 32 MB Fast RAM and are fixed here:

- **The player starts with health at its maximum** (`PLAYER-HEALTH-OVER-MAX-63`): a map loaded fresh from the console
  or a restart kept the default spawn health of 100 although the character's maximum (Strength plus Endurance, halved)
  was 40, and restoring the stats only raised values below the maximum. A fresh map now takes the character's health,
  at most its maximum, and restoring the stats sets it to the maximum.
- **God mode keeps the player's health** (`GODMODE-LAVA-DEATH-62`): a script that lowered the player's health
  (ModCurrentHealth) still took it down with god mode on, because the kept value was capped at the maximum the player
  was already above. Health no longer drops under god mode.
- **Argonians breathe under water** (`UNDERWATER-BREATH-62`): the race's Water Breathing ability counted as 0, because
  that effect has no magnitude and the passive sum read its stored magnitude; such an effect now counts once per
  spell, as when it is cast. A race chosen again at character creation is read afresh.
- **Sunder hurts its bearer without Wraithguard** (`MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61`): equipping it from the console
  skipped the step that tells the item's script it was equipped, so its curse never started. Equipping and unequipping
  from the console now run that step as the inventory does, and taking an item off tells its script so, as in the
  original.

### Scripts and the console

- **27 more functions of the original's scripting are carried out: 460 of 504** (433 in v0.0.63-dev3;
  `MWSCRIPT-MISSING-FUNCTIONS-63`). The console group is now callable from scripts too: Show (a global's value),
  ShowVars (the object's script locals by slot number, else every global), ToggleScripts, ToggleAI, ResetActors (actors
  a script moved return to where the map put them, and every walker to its spawn spot), OutputRefInfo (the
  reference's id, number, position, angle, scale and script), User1 to User4 (test hooks that only name themselves) and
  the console's aliases (ToggleCollision, ToggleGodMode, ToggleMenus, ToggleVanityMode, CenterOnCell, CenterOnExterior,
  FixMe and their short forms), which run the same AmiWind line as on the console. No script of the three game files
  calls these, so the number of scripts that run does not change.
- Every console function still left names its reason in the [console commands](../../CONSOLE_COMMANDS_MORROWIND.md)
  page: the drawing switches (sky, water, world), the path grid, collision and border overlays, the fog of war, the
  full help and the cell tests.
- Show and ShowVars cannot name a script's local variables, because the compiler turns a name into a slot number and
  the engine keeps no names (`MWSCRIPT-CONSOLE-LOCAL-NAMES-63`).

| State | Scripts |
| --- | ---: |
| Run as scripts | 605 of 1,207 (605 in v0.0.63-dev3) |
| Carried by the game's own code | 8 |
| Use a function the interpreter lacks | 28 |
| Belong to an add-on world not in the image yet | 432 |
| Named by nothing (they never run in the original either) | 134 |

The 28 scripts that still lack a function all belong to the add-on worlds (placing their own records, moving into
their cells, the water level), which are not in the image yet; the [MWScript tracker](../../MWSCRIPT_FEATURES.md)
lists every script with its state.

### The builder and the image

- **Worker pools start queued units between two results** (`BUILD-IMAGE-QUEUE-STALL-62`): a pool handed a whole batch of
  finished units to its caller before looking at the queue again, so workers stood idle while units waited. It now hands
  back one result at a time and refills freed workers between two. Scheduling only; no key changes
  ([build profile](../../BUILD_PROFILE.md)).
- **The CHIM world key counts only what the loaders reach** (`BUILD-CHIM-HEAP-KEY-LOADER-63`): the key of the world
  stages read every define and declaration of the engine's model file; it now counts only those the brush and edge-cache
  loaders reach, directly or through other counted items. A change that touches only the actor model reader no longer
  rebuilds the whole world ([BUILD_CACHE](../../BUILD_CACHE.md)).
- **The dialogue and voice tables and the actor ground check come from the unit cache**
  (`BUILD-TABLE-UNITS-REBAKE-63`): the tables were keyed on whole files that reach the script compiler's data, so every
  development build baked them again although their bytes had not changed. They are now keyed on the code their bake
  runs, and the actor ground check keeps one unit per placement, stored the moment it settles. Outputs are unchanged.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A new game and a console map load start at full health (the position overlay shows 40/40 for a starting character).
- With god mode on, `ModCurrentHealth -50` and a lava pool take no health.
- An Argonian under water keeps a full breath.
- Sunder equipped without Wraithguard hurts every second; taking it off stops that.
- The console group from a script or the console: `Show` on a global, `ShowVars` on a scripted object, `ToggleAI`,
  `ResetActors` after a script has moved an actor, `OutputRefInfo` on a target (`dbg help mw`).
- Everything on the [v0.0.63-dev3 checklist](RELEASE-v0.0.63-dev3.md#in-game-checklist-for-this-snapshot).

## Known in this build

- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- Show and ShowVars name no script locals (`MWSCRIPT-CONSOLE-LOCAL-NAMES-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- Files that two build stages write each are listed and kept from growing; each is to be written by one stage only
  ([BUILD-SHARED-WRITES-UNATTRIBUTED-52](../../bugs/BUILD-SHARED-WRITES-UNATTRIBUTED-52.md)).
- The image step and the CHIM validation still run on few cores in a full world rebuild
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md),
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md)).
- The new world key and the table units are checked by tests; a build that proves them is still to come
  (`BUILD-CHIM-HEAP-KEY-LOADER-63`, `BUILD-TABLE-UNITS-REBAKE-63`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, and the Heart Chamber may not load at
  32 MB Fast RAM.
