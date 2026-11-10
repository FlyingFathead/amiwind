# AmiWind v0.0.64-dev1 (in development)

_Last updated with AmiWind v0.0.64-dev1 (10 November 2026)._

Development snapshot, 10 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

The first snapshot of v0.0.64, "Gone Beyond The Gate". It follows the v0.0.63 release and starts the road to the two
expansion worlds: the builder can now choose which expansions it includes, and the Tribunal and Bloodmoon files are
counted from the game data. No expansion area is built yet. In the game, the console can find and use world objects
that are not characters (the Ghostgate's switches and portcullises, the items whose taking summons a guardian), scripts
can cast spells on other characters, `dbg tp` takes a height as the floor under the feet, and the Argonian's water
breathing is the original's cast spell. 605 of the 1,207 scripts run as scripts and 9 more are carried by AmiWind's own
code (605 and 9 in v0.0.63). The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.63

### The world and the console

- **Activate finds world objects that are not characters.** The console's Activate (and the use of an object by a
  script) now finds the placed objects of the world that are not actors, and acts as the player's use. This is the
  way to reach the Ghostgate's switches and the portcullises they raise, and the items whose taking summons a guardian
  (`WORLD-BUTTONS-62` and `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`, both open until seen in play).
- **A teleport height is the floor under the feet.** `dbg tp X Y Z` and the Position function of scripts read Z as the
  height of the floor the character stands on, as the original does, not as a height above a point in the air. It was
  found while looking at the Red Mountain lava (`LAVA-NO-DAMAGE-63`, to be checked again in play; the entry stays open).
  The console also names placements that have no entity, so they can be found by name.

### Scripts

- **Cast on a character other than the player.** A script can cast a spell on any other character, following OpenMW: the
  cast always succeeds, the effects of range Self land on a character who casts, and those of range Touch and Target
  land on the target. A spell the game does not have compiles to nothing. 27 scripts still wait for a function
  (28 in v0.0.63); the [MWScript tracker](../../MWSCRIPT_FEATURES.md) was measured again for this snapshot.

| State | Scripts |
| --- | ---: |
| Run | 605 of 1,207 (605 in v0.0.63) |
| Carried by AmiWind's own code | 9 |
| Use a function the interpreter lacks | 27 (28 in v0.0.63) |
| Belong to an add-on world not in the image yet | 433 |
| Named by nothing (they never run in the original either) | 133 |

### Water breathing

- **The Argonian's water breathing is the original's cast spell.** In the original game the race does not have a lasting
  water breathing ability: it has the spell "argonian breathing", cast for 120 seconds. The check of the Argonian's
  water breathing now looks for that spell instead of a lasting ability, so it asks for the right thing
  (`UNDERWATER-BREATH-62`, reported twice and still open until seen in play).

### The builder

- **The expansion layers are a choice.** `--dlc tribunal|bloodmoon|both|none` chooses which expansion layers a build
  includes, and `--no-dlc` builds the base game only (`BUILD-EXPANSIONS-31`; both are recorded in the builder's option
  record). The choice is the player's: it is not changed by a debugging option.
- **The base world's keys no longer depend on which expansion files are present.** Every stage that reads the game data
  was keyed by every game input, so an expansion file being on the disk re-keyed stages that never read it. Each stage
  now counts the game inputs it reads (`BUILD-GAME-INPUT-KEY-BROAD-64`, open until a build of this snapshot shows the
  keys unchanged by an expansion file).
- **The cell and room readers take a master list,** so a build can read the cells and rooms of a chosen set of game
  files instead of the three at once.
- **The expansions have their own ranges.** Their rooms get their own room id ranges, and their stores are laid out as
  separate units, so a later build of Mournhold or Solstheim does not move the ids or the storage of the base world.
  No expansion area is built in this snapshot.
- **The census of Tribunal and Bloodmoon.** What each expansion adds, counted from the game files (cells, rooms,
  records, scripts, models and the rest): [expansions census](../../performance/EXPANSIONS-CENSUS-v0.0.64.md).
- **The test sessions examine every stop before a retry.** When a boot or play session ends without the game getting into
  play after a load, the session now examines the stop first: it names the file request that was queued and the handler
  waiting for it, and the emulator's instruction trace is left out of the kept logs. This is the first step of the
  load stall work (`SMOKE-INPLAY-UNSAMPLED-63`, `SMOKE-IDE-TRACE-LOG-63`; both stay open until a stall is caught).
- **An incomplete combat settings file is read once per load.** A settings file that lacks some keys was read again for
  every actor that spawned; it is now read once per load (`COMBAT-SETTINGS-REREAD-63`, to be timed in play).
- **The release kit takes the gate's test suite result** for the same commit instead of running the suite again.

### The register

- The bug register was brought up to date after the v0.0.63 release check: seven fixes were seen in play, the Ghostgate
  buttons were opened again, the race's water breathing was seen failing again, and the findings of the check
  (lava, the guarded items, a stage-key test that fails when run outside the gate's own container, and others) were
  entered.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- The Ghostgate's switches on both sides and their portcullises, with the console's Activate on a switch; the guarded
  coins in Ald Sotha Lower Level (the guardian that appears when a valuable object is taken).
- `dbg tp` with a height in a room and outdoors, then the Red Mountain lava with and without god mode.
- Play an Argonian: the spell "argonian breathing" in the spell list, and swimming under water until the breath bar would
  run out.
- A script that casts at another character (a spell at a guard or at a follower).
- The trip from Seyda Neen to Balmora several times, for the load stall; a run of the standard bench on the Raspberry Pi
  4B and in the emulator.
- Carried over from v0.0.63: Water Breathing after a load and in a New Game, the Ghostgate's portcullises, the
  creatures met late in a long session, the load times with the shared actor shapes.

## Known in this build

- **The race's Water Breathing is not confirmed:** `UNDERWATER-BREATH-62` was reported twice and persists; this
  snapshot's change is checked by tests only.
- The Ghostgate's switches and portcullises, and the items whose taking summons a guardian, can be used from the console
  but have not been seen in play (`WORLD-BUTTONS-62`, `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`). Lava does no damage in the Red
  Mountain pool in the released image; the height change of `dbg tp` is to be checked there (`LAVA-NO-DAMAGE-63`).
- Tribunal and Bloodmoon are not built yet: the switch and the keys are in, and Mournhold and Solstheim come with a later
  snapshot (`BUILD-EXPANSIONS-31`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The end of the main quest in the Heart Chamber cannot play yet: the Heart of Lorkhan is not placed and the chamber's
  collapse is not animated (`ENDGAME-CHAMBER-COLLAPSE-63`), and the chamber's load failure persists
  (`CHIM-ROOM-HEART-CHAMBER-LOAD-50`).
- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- The Pi bench's worst frame from the disk is 72.8 ms (48.1 in the v0.0.61 test image;
  `PI-BENCH-DISK-WORST-FRAME-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- From [v0.0.63](RELEASE-v0.0.63.md): the open entries of its Known list stand, among them pickpocketing and owned
  locks not done. Every other open entry is in the [bug register](../../BUGS.md).
