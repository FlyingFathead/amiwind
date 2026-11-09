# AmiWind v0.0.63-dev3 (in development)

_Last updated with AmiWind v0.0.63-dev3 (9 November 2026)._

Development snapshot, 9 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.63-dev2](RELEASE-v0.0.63-dev2.md); previous release: [v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

The third snapshot of v0.0.63. It carries creatures that walk, run and attack again wherever they are met, 66 more
functions of the original game's scripting carried out, and a builder that can reuse every earlier run at once and
tells beforehand what it will redo. 605 of the 1,207 scripts run as scripts and 8 more are carried by the game's own
code (the same as in v0.0.63-dev2). The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.63-dev2

### The world

- **Creatures walk, run and attack again everywhere** (`CREATURE-BIPED-ANIMS-62`): the engine kept a fixed number of
  animation layouts (64) and movement models (16) for a whole outdoor session and never freed them, so creatures met
  later glided on idle frames or fought with standing poses. A full table now reuses an entry no live actor needs, and
  holds 64 movement models; the arena's fighters get their movement and worn items (the shield shows). A check confirms
  that every creature whose original animation has walk, run or attack reaches them
  ([animations](../../ANIMATION.md)).

### Scripts and the console

- **66 more functions of the original's scripting are carried out: 433 of 504.** The effect family (Get, Set and Mod
  of Chameleon, WaterWalking, SwimSpeed, SuperJump, Flying, ArmorBonus, CastPenalty, Silence, Blindness, Paralysis,
  Invisible, AttackBonus and DefendBonus), the game hour and the phases of the two moons, the starting position and
  angle of a placed object, the view switches, the player's run and the jump flags, the readied spell, the actors
  standing on or colliding with an object, the armour type, SameFaction and GetFactionReaction, RemoveEffects and
  RemoveSpellEffects, the soul gems (the gem leaves the inventory; it is not laid on the ground yet) and the level-up
  window. Every function and console toggle still left names its reason in the
  [console commands](../../CONSOLE_COMMANDS_MORROWIND.md) page.
- Five console toggles are mapped to the game's own switches: ToggleDebugText, ToggleStats, ToggleCombatStats,
  ToggleLights and RepairedOnMe.
- Placements of an add-on are keyed by the load-order index of their file, and are bound only for the add-on worlds an
  image carries (`MWSCRIPT-ADDON-ATTACH-62`; none is in the image yet).
- The console takes up to 1,000 commands (512 before).

| State | Scripts |
| --- | ---: |
| Run as scripts | 605 of 1,207 (605 in v0.0.63-dev2) |
| Carried by the game's own code | 8 |
| Use a function the interpreter lacks | 28 (29 in v0.0.63-dev2) |
| Belong to an add-on world not in the image yet | 432 (431 in v0.0.63-dev2) |
| Named by nothing (they never run in the original either) | 134 |

One script moved from the ones that lack a function to the ones that belong to an add-on world, because the function
it called is now carried out; the [MWScript tracker](../../MWSCRIPT_FEATURES.md) lists every script with its state.

### The builder and the image

- **`--reuse-all-available`**: the builder reads the finished stages and units of every earlier run through a stage
  index instead of one run, prints a plan for each stage (reused, rebuilt and why) before any stage runs, and stops
  when a stage would redo work that is already stored (`BUILD-UNIT-PREFLIGHT-63`; [BUILD_CACHE](../../BUILD_CACHE.md)).
- **A size report for an image** (`tools/image_size_report.py`): read-only; it counts the bytes of a built image by
  kind, the largest groups of repeated bytes and the distinct 16 x 16 tiles of the actor skins
  (`IMAGE-BIGGER-THAN-ORIGINAL-62`). On the v0.0.63-dev1 image: 3,089 MB, of it 1,675 MB boot payload and 1,123 MB
  world partition.
- **Actor skin tiles, an experimental method that is off by default** (`--skin-tiles on`): the skins of the actor
  models are cut into 16 x 16 tiles stored once, and the engine rebuilds each model byte for byte before it is
  decoded. It would take about 319 MB off the v0.0.63-dev1 payload at about 78 short reads per skin load; it stays off
  until a build with it is measured on the Raspberry Pi 4B and in FS-UAE at 32 MB Fast RAM. Nothing changes for a
  player in this snapshot ([payload sharing](../../PAYLOAD_SHARING.md), [experimental flags](../../EXPERIMENTAL_FLAGS.md)).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Creatures met late in a long outdoor session (an ash slave, a corprus stalker) walk, run and attack;
  a duel in the debug arena with a gallery character shows the shield.
- The console: a few of the new functions on a target, and the five toggles (`dbg help mw`).
- Everything on the [v0.0.63-dev2 checklist](RELEASE-v0.0.63-dev2.md#in-game-checklist-for-this-snapshot).

## Known in this build

- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- Fifty files are still written by two build stages each; they are listed and kept from growing, and each is to be
  written by one stage only (`BUILD-SHARED-WRITES-UNATTRIBUTED-52`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, and the Heart Chamber may not load at
  32 MB Fast RAM.
