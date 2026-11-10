# AmiWind v0.0.64-dev2 (in development)

_Last updated with AmiWind v0.0.64-dev2 (10 November 2026)._

Development snapshot, 10 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.64-dev1](RELEASE-v0.0.64-dev1.md). Previous release: [v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

The second snapshot of v0.0.64, "Gone Beyond The Gate". Trapped doors and containers now spring their trap on the player,
as the original does. The engine has a load trace and a memory line per load, both meant for the stall on the trip from
Seyda Neen to Balmora. The Toolkit's CHIM Progress Tracker has a view for each expansion, and the first Solstheim frame
was built and measured as a test build. No expansion area is part of the game image yet. 605 of the 1,207 scripts run
as scripts and 9 more are carried by AmiWind's own code, as in v0.0.64-dev1. The game needs 32 MB of Fast RAM, and the
emulator presets of this snapshot have it.

This snapshot carries v0.0.64-dev1 as well. The first snapshot was not published on its own, so its changes (listed in
[its notes](RELEASE-v0.0.64-dev1.md)) arrive together with these.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.64-dev1

### Traps

- **Opening a trapped door or container springs its trap.** A placed door (hinged or load door) or container whose
  reference names a trap spell casts that spell on the player who opens it, instead of opening, as the original game
  does (`DOOR-TRAPS-NOT-SPRUNG-55`, open until seen in play). The trap is used up when it springs and stays used up in
  saved games; a new game clears it. The key that opens the lock also disarms the trap.
- **How many there are.** Morrowind.esm places 457 trapped references with 85 trap spells; with Tribunal and Bloodmoon
  there are 468 (290 containers, 167 hinged doors and 11 load doors).
- **The census of world mechanisms.** [World mechanisms](../../WORLD_MECHANISMS.md) lists the 54 activators of the three
  game files that move, turn, enable, disable, lock, unlock or activate another object (the Ghostgate's switches, the
  Dwemer cranks, the shrine statues), with their cells, what they act on and how many of their scripts run, and counts the
  trapped doors and containers.
- **Not done yet:** a trap does not spring on a failed lock pick or from a probe, the trap sounds and the tooltip line
  are missing, and the traps of the expansions come with their worlds.

### The load stall

- **A load trace, off by default.** `dbg loadtrace on`, `off` and `dump` (the console variable `aw_loadtrace`) keep every
  file call of a load (open, read, seek, close, with the file, the bytes, the times and the load stage) in a fixed ring in
  memory, and nothing is written during the load. When the scene is ready, the last calls and every call that did not
  finish are printed and the whole ring is written to a file; `dbg loadtrace dump` does the same at any time. Off, each
  file call costs one test. It is for `CHIM-SEYDA-BALMORA-LOAD-HANG-43`, which stays open until a stall is caught with it.
- **One memory line per load.** After the actors are placed, after a restored save and when the scene is ready, the
  console prints the hunk, the zone, the cache, and the Fast and Chip RAM free and largest, so the memory taken outside
  the hunk is measured for every load. It costs four memory queries per load and none per frame.
- **The boot smoke can turn the trace on** (`--load-trace`, off by default); when a session stalls, the examination reads
  the ring from the stopped emulator, names the calls that never finished and keeps the ring with the logs.

### The Toolkit

- **Expansion views on the CHIM Progress Tracker.** Solstheim is on the main map view beside Vvardenfell; Mournhold,
  which has no exterior, has a map screen of its own (its districts and rooms) behind a view switch above the map. Each
  view shows its done, partial and missing counts, and the completion of Bloodmoon and Tribunal shows beside the base
  game's. A build without an expansion shows no view and no figure for it
  ([CHIM Progress Tracker](../../chim/PROGRESS_TRACKER.md), [the Toolkit](../../AMIWIND_TOOLKIT.md)).

### The builder

- **The first Solstheim frame, as a test build.** `--chim-sol-test CELLS` (test builds only, off by default) builds
  Bloodmoon's cells as CHIM frames from a layered copy of the game data (`tools/chim_layer_data.py`), keyed by Bloodmoon's
  files; the image does not take it. It was measured on the densest forest cell: the frame fits the memory budget at 32 MB
  Fast RAM (61 % of the zone's ring budget), but its views draw 45,964 faces at the median against 7,562 on Vvardenfell,
  and the trees are 87 % of them. The trees need the cheaper method before Solstheim ships
  (`CHIM-SOLSTHEIM-TREE-FACES-64`, open). The numbers are in
  [the first Solstheim frame, measured](../../performance/SOLSTHEIM-FIRST-FRAME-v0.0.64.md).
- **The Bloodmoon meshes the first frame stopped on are covered.** The 25 Bloodmoon meshes the collision surface check
  did not know are in the collision hull table, and three meshes are on the known list of the stair check (collision
  method 0). The first Solstheim test frame now builds with the shipped defaults
  (`CHIM-SOLSTHEIM-HULL-SURFACE-64` and `CHIM-SOLSTHEIM-STAIR-CHECK-64`, fixed in v0.0.64-dev2).
- **The base world's key leaves out the expansion rows,** so a Vvardenfell build is not re-keyed by them; the tests prove it.
- **The start-up plan of a build can be wrong in a cascade.** The plan counts a stage whose reuse is at risk as reused, so
  a rebuild after a change to an early stage runs much longer than the plan says (`BUILD-PLAN-AT-RISK-CASCADE-64`, found
  and measured on the build of the previous snapshot, open).
- **The image step still scans maps on about one core** and runs the actor ground check under half its cores; it was seen
  again on the build of the previous snapshot (`BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52`, open).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A trapped chest or door (for example a locked, trapped chest in a ruin or a shop): the first use springs the trap on
  the player and does not open; the second use opens it. Save and load after the trap sprang and use it again: it must
  stay used up. Open another trapped chest with its key: the trap must not spring.
- After a load, `dbg loadtrace dump` (with `dbg loadtrace on` before the load): the file written and the calls it names;
  the memory line printed after each load.
- The trip from Seyda Neen to Balmora several times with the trace on, for the load stall.
- The Toolkit's CHIM Progress Tracker with a build that holds an expansion: the view switch, the Mournhold screen and the
  completion figure beside the base game's.
- Carried over from v0.0.64-dev1: the Ghostgate's switches and portcullises, `dbg tp` with a height, the Red Mountain
  lava, an Argonian swimming under water, and a script that casts at another character.

## Known in this build

- **Trapped doors and containers spring their trap** by the test suite only, not in play (`DOOR-TRAPS-NOT-SPRUNG-55`).
- **The race's Water Breathing is not confirmed:** `UNDERWATER-BREATH-62` was reported twice and persists; the change of
  the previous snapshot is checked by tests only.
- The Ghostgate's switches and portcullises, and the items whose taking summons a guardian, can be used from the console
  but have not been seen in play (`WORLD-BUTTONS-62`, `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`). Lava does no damage in the Red
  Mountain pool in the released image; the height change of `dbg tp` is to be checked there (`LAVA-NO-DAMAGE-63`).
- Tribunal and Bloodmoon are not built into the image yet: the switch, the keys and a test-only Solstheim frame are in,
  and Mournhold and Solstheim come with a later snapshot (`BUILD-EXPANSIONS-31`). A Solstheim forest draws about six
  times the faces of a median Vvardenfell view (`CHIM-SOLSTHEIM-TREE-FACES-64`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); the load trace is the tool for it.
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
