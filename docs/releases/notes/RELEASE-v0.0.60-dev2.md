# AmiWind v0.0.60-dev2 (in development)

Development snapshot, 4 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.59](RELEASE-v0.0.59.md). Previous snapshot: [v0.0.60-dev1](RELEASE-v0.0.60-dev1.md).

The second snapshot of v0.0.60. It carries the walking residents' per-area tables and the build fixes of dev1, and adds
two fixes that were proven in game: the builder now rebuilds the compiled scripts whenever their compiler changes, and
containers whose contents are levelled lists show their items. The plan for v0.0.60 is the list in the
[roadmap](../../ROADMAP.md); most of it is still open. The game needs 32 MB of Fast RAM, and the emulator presets of
this snapshot have it.

## New since v0.0.59

The notes of [dev1](RELEASE-v0.0.60-dev1.md) listed nothing as finished, although its build already carried the first
four lines below. They are listed here so that this page is complete against v0.0.59.

### In dev1, not listed in its notes

- **The walking residents' data per area.** The packages of the walking residents are split by each placement's own
  cell and kept in memory per area, searched there instead of in files while you walk. How much it saves in the
  emulator is not yet measured (see the end of these notes).
- **The boot check waits for the game.** The check that boots the finished image in the emulator sends no key until the
  game's own remote state file appears, so a key typed during the start-up memory notice can no longer turn the CHIM
  cache off and fail the check.
- **Release tooling.** A build that grows past the size margin now says early that a final will stop there and records
  it ([BUILD-SIZE-GUARD-LATE-48](../../bugs/BUILD-SIZE-GUARD-LATE-48.md)); the delivery checks its output names at the
  start, before the boot check; the reuse check runs its preflight once instead of twice (143 s instead of 286 s on a
  busy host, same result); padded disk images are copied onto the J: drive in a way the drive accepts.
- **Compiled scripts of the correct compiler.** v0.0.59 shipped compiled scripts made by an older compiler than the
  one in its source (7,339 bindings instead of 8,566), so beds gave no rest window and two rank raises did nothing. The
  dev1 build was made with the scripts rebuilt.

### New in dev2

- **The builder sees compiler changes.** The compiled-scripts stage is rebuilt whenever the script compiler changes,
  not only when a function it ran changes: the compiler's identity, the table of calls the engine provides and the files
  it hashes whole are part of the stage's key, and the image step refuses compiled scripts made by another compiler.
  Placed beds open the rest window again and the two rank raises happen, in every build made from here on, not only in
  the one where the scripts were rebuilt by hand.
- **Levelled container contents.** Containers whose contents are levelled lists roll their items by the original's
  rules the first time they are opened, and keep them across saves
  ([CONTAINER-LEVELLED-CONTENTS-EMPTY-59](../../bugs/CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md)). Checked in game.
- **Searching a body in code.** A dead actor's body is found by the container strip and opened as E opens a container.
  This is not yet checked in game.

## Known in this build

These are the known problems of [v0.0.59](RELEASE-v0.0.59.md) that remain in this snapshot.

- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames; the per-area tables for the walking residents are in this build, and the frames are not
  yet measured with them.
- A build's performance check can fail on the resident bake of the Vivec town, which costs about three and a half
  times its earlier CPU per unit
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Looting the bodies of dead actors.
- The frame times of the walking residents and of the arrival frame with the per-area tables.
- The rest of the v0.0.60 list; none of it is in this snapshot.
