# AmiWind v0.0.68-dev1 (in development)

_Last updated with AmiWind v0.0.68-dev1 (20 November 2026)._

Development snapshot, 20 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The first snapshot of v0.0.68. The version has no title yet. This snapshot is not Solstheim yet: that is the work of
the line, in progress on its own branches (see [the roadmap](../../ROADMAP.md)). It is a small snapshot of what was
mended since the v0.0.67 release: a build that stops now ends with a plain block that says why, that the finished work
is kept and the command that continues it; the progress tracker counts the two opening rooms as ready; the automated
playthroughs wait for the game instead of for a fixed number of seconds; and the private word lists left the public
tree. Its emulator presets, `AmiWind-v0.0.68-dev1-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev1-WinUAE.uae`, both start with
32 MB of Fast RAM, which the game needs. The game itself is the one of v0.0.67: nothing in this snapshot changes how
the game plays. The changes below are checked by the test suite and the gate of this snapshot; none of them is a change
of the game in play, so none was seen in play.

## New since v0.0.67

### Fixed

- **The progress tracker counts the two opening rooms as ready.** The Imperial Prison Ship and Seyda Neen, Census and
  Excise Office are in the game as room maps of their own, and they are now counted as ready and listed as special
  interiors, named under the land's count, instead of being listed as not ready
  ([TRACKER-ROOM-MAPS-NOT-READY-67](../../bugs/TRACKER-ROOM-MAPS-NOT-READY-67.md)). Vvardenfell's rooms are 1,131 of
  1,131, Solstheim's 101 of 101 and Mournhold's 91 of 91 on the tracker's data; the Toolkit's completion panel and the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) show the same numbers. Solstheim's open terrain, 0 of 144,
  is what is left of its count. The tracker data of this snapshot was counted again by the same rule and is still the
  data of the v0.0.67 build.

### Builder and tools

- **A build that stops ends with a plain block for the player.** When a build stops, for memory or for any other reason,
  its last lines say why it stopped, that the finished work is kept, the exact command that continues from the same
  build folder, and what to try for that cause (fewer workers where the workers hold the memory, swap or more memory
  where one process holds it). The same block opens the build report and the failure page, and a build cancelled with
  Ctrl+C ends with the command that continues it. Where an earlier build measured a stage's memory the block uses it,
  else the reference figures of `config/build-memory.json`, measured in the v0.0.66 from-scratch build of the whole
  game (BUILD-OOM-HELP-AND-TIP-68).
- **The build guide has a section for it.** [The build stopped or ran out of memory: what now?](../../LINUX_BUILD.md#the-build-stopped-or-ran-out-of-memory-what-now)
  says what to do, shows the block of a stop in the CHIM world stage, gives the swap and container settings, and lists
  the memory each large stage reached in the v0.0.66 from-scratch build (43.7 GiB at its peak, with the CHIM world
  stage and the room batches side by side). [Building and playing](../../BUILDING_AND_PLAYING.md) and the README point
  to it.
- **The build report gains the swap and the memory peaks**: the machine's swap (on Linux, macOS and Windows, and a
  container's own swap limit), the build's memory peak beside the memory it had, and the failed stage's peak with its
  largest process. The machine block (cores, memory, swap, free space) is printed at the start of every build, so a
  build that is ended without a report still shows what it started with.
- **The session language waits by condition.** `until map`, `until screen`, `until server`, `until loaded` and
  `until journal` wait for the game's own state, each with a limit in seconds, instead of a fixed number of seconds
  that is too long on a quiet machine and too short on a loaded one; the opening journey uses them
  ([FS-UAE development access](../../FS-UAE-DEVELOPMENT.md), [the game recorder](../../GAME_RECORDER.md);
  ACCELERATED-PLAYTHROUGH-66).
- **The private word lists left the public tree.** The lists of words, instruction files and channels that the privacy
  checks read are kept by the maintainer's own tooling, not in the repository; the public-text tests no longer hold
  them and their own comments no longer name the words they forbid
  ([PUBLIC-GUARD-SPELLS-TOOL-NAMES-67](../../bugs/PUBLIC-GUARD-SPELLS-TOOL-NAMES-67.md)).
- **The bug tracker** records the new faults, sightings and fixes of 20 November (see Known in this build).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island, the expansions'
  remaining scripts and dialogue, the save with their counts and the playtests.
- **The build's memory plan.** A build that fits a 32 GB machine: a plan from the measured stage peaks in its first
  minute, stages that do not fit side by side run one after another, every reduction written as a warning in the log,
  the work of the long stages stored as it finishes, and the CHIM world stage's main process split. This snapshot adds
  only the advice after a stop; the plan is in work (BUILD-TESTER-32GB-OOM-67).
- **The debug arena's custom play mode and the debug teleport's water note**, and **the early studies of the docs in
  their own folder, marked as historical**: planned, not in this snapshot (see the roadmap).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The game of this snapshot is the game of v0.0.67, so the
[checklist of the v0.0.67 snapshots](RELEASE-v0.0.67-dev3.md#in-game-checklist-for-this-snapshot) stands. What this
snapshot changes is in the builder and the tools: run a build that is stopped on purpose and read its last lines, and
open the Toolkit's completion panel for the special interiors.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run; the
[CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **A build can still run out of memory on a 32 GB machine.** The CHIM world stage holds the whole world in its main
  process (about 24 GiB in the v0.0.66 measurement) and the room batches run beside it; this snapshot only says what to
  do after a stop. The plan that avoids the stop, and the work stored inside the long stages as it finishes, are in
  work ([BUILD-TESTER-32GB-OOM-67](../../bugs/BUILD-TESTER-32GB-OOM-67.md),
  [BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md), open). Some steps of the CHIM world stage run
  again in full after a stop.
- **Old Mournhold's sewers:** the water levers do not move the water
  ([MWSCRIPT-WATER-LEVEL-STATIC-67](../../bugs/MWSCRIPT-WATER-LEVEL-STATIC-67.md)); `GetWaterLevel` reads the water in
  the player's column, so it reads 0 in Old Mournhold: Temple Sewers West
  ([GETWATERLEVEL-COLUMN-NOT-ROOM-67](../../bugs/GETWATERLEVEL-COLUMN-NOT-ROOM-67.md)); people and creatures under
  water never drown, only the player does
  ([ACTOR-DROWNING-NOT-CARRIED-67](../../bugs/ACTOR-DROWNING-NOT-CARRIED-67.md)); all open.
- **In the tools:** the progress tracker's ingest steps write their data without an error when a remembered input
  cannot be read ([CELL-PROGRESS-SOURCE-UNREADABLE-SILENT-67](../../bugs/CELL-PROGRESS-SOURCE-UNREADABLE-SILENT-67.md));
  the performance database records the CHIM import runs without their times
  ([PERF-DB-CHIMPORT-NO-WALL-67](../../bugs/PERF-DB-CHIMPORT-NO-WALL-67.md)); the release route's upload step is
  refused when the release was published first
  ([ROUTE-UPLOAD-AFTER-PUSH-67](../../bugs/ROUTE-UPLOAD-AFTER-PUSH-67.md)); the register tool stops now and then with an
  error while it writes, after it has saved the entry
  ([REGISTER-WRITE-EINVAL-67](../../bugs/REGISTER-WRITE-EINVAL-67.md)), and two register writes at the same time in one
  checkout can lose an entry ([REGISTER-CONCURRENT-WRITE-LOST-67](../../bugs/REGISTER-CONCURRENT-WRITE-LOST-67.md)); all
  open.
- **Fixed in source, and open in the bug tracker until a build records them:** TRACKER-ROOM-MAPS-NOT-READY-67 and
  PUBLIC-GUARD-SPELLS-TOOL-NAMES-67 above, and the arrival in a flooded room
  ([ROOM-ARRIVAL-FLOODED-ON-ROOF-67](../../bugs/ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md)), which shipped in v0.0.67 and was
  seen in play there: the scripted teleport into Sotha Sil, Outer Flooded Halls lands in the hall's water.
- From [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not
  named here, among them Mournhold's and Solstheim's unfinished play. Every other open entry is in the
  [bug tracker](../../BUGS.md).
