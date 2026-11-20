# AmiWind v0.0.67-dev1 (in development)

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

Development snapshot, 17 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.66: Forward It Is](RELEASE-v0.0.66.md).

The first snapshot of v0.0.67. It is the v0.0.66 release, labelled for the v0.0.67 line, with the first changes of the
builder and its tools: nothing is new in the game yet. Its emulator presets,
`AmiWind-v0.0.67-dev1-FS-UAE.fs-uae` and `AmiWind-v0.0.67-dev1-WinUAE.uae`, differ from the v0.0.66 ones in the label
only, and both start with 32 MB of Fast RAM, which the game needs. Every change of [v0.0.66](RELEASE-v0.0.66.md) and of
its twelve snapshots is in it; their notes hold the detail. The builder's changes below are checked by the test suite
and the gate of this snapshot; none has been seen on a build of this snapshot yet.

## New since v0.0.66

### The builder and its tools

- **One failure page.** A failed build's `FAILURE.md` is the one page with everything needed to find the cause: besides
  the failed stage, its error lines, the traceback, the last lines of its log and the command that builds again, it says
  what was not completed (the stages not started or cancelled with it, the units refused or left out) and the settings the
  build ran with (its options as given, the recipe with every option's value, the builder and its masters in load order,
  the data folder, and the `AMIWIND_` settings the failed stage read). It names the full build report, and the build's
  last line names the page (`Failure details: RUN/FAILURE.md`); a build that stopped before it made its run folder, or
  with an error of the builder itself, names its build report there instead. `tools/build_failure.py RUN --out DIR`
  writes the page of a run elsewhere and only reads the run. The Toolkit Monitor shows the same page, also for an
  earlier builder's failed run.
- **One list of early checks.** `EARLY_CHECKS` in `tools/build_preflight.py` is the one place for a check of seconds that
  a stage or the image step would otherwise meet hours into a build. The checks of one phase all run and print a line
  each, and the build stops once with every problem. The phase `inputs` runs with the start-up preflight; the phase
  `stored` runs after the reuse plan and before the first stage, on the stored outputs the build reuses, and
  `build.py --check` runs it too and fails with every problem, so the master builder's check stops a build before it
  starts. Its first entry: the room actors' frame check (`tools/image_early_checks.py`), which the image step used to
  meet at the end, runs before the first stage when the room batches are reused and right after them when the build
  makes them (a new phase, `after:STAGE`). The player view stage bakes the player's body parts and first-person arms
  right after the census and stores each part at once, with the parts coverage stop there; the image takes them from the
  unit cache (`BUILD-IMAGE-CHECKS-EARLY-66`).
- **The build report names the machine.** Its top is a short environment summary: the operating system and release,
  whether the build ran in a container and how that was found, the Python version against the recorded reference, the
  cores, the memory (read on Linux, macOS and Windows; "Not available" only where nothing answers) and the free space of
  the workspace and the temporary folder. A failure is classed as **out of memory** or **out of disk** when the build
  shows it (an exit by the kernel's memory killer, a memory error, a full disk or quota), marked proven or likely, with
  the free space and what to do; `FAILURE.md` shows the kind first.
- **CHIMport cells are found again in the unit pool.** A cell's key no longer takes in the id of the request that made
  it, so a cell made once is linked by the next request with the same inputs
  (`CHIMPORT-CELL-KEY-REQUEST-ID-67`). CHIMport also finds its own reader again when run from the tools folder
  (`CHIMPORT-CLI-MWAD-SHADOW-66`).
- **Test sessions never time a warped emulator.** The test tools refuse a timing or bench step in a session that runs
  the emulator in warp mode, and mark every result of a warped run as no timing verdict. Measured on the opening journey:
  warp does not make our test sessions faster ([EMULATOR-WARP.md](../../performance/EMULATOR-WARP.md)).
- **The v0.0.67 line is connected to the v0.0.66 release**: the previous-release pin, the size baseline (the v0.0.66
  release image, 2.88 GiB of payload) and the Toolkit's header.
- **Live numbers from the first second.** The build writes its status folder as soon as its options are read, before the
  free-space check and the build preflight, so its phase, the cores in use against the planned ones and the time since
  the last progress are there from the start; a build that stops in its start-up leaves the status `failed`. The Toolkit
  Monitor's runs list carries a live block (status, phase, elapsed time, cores now and planned, seconds since the last
  progress) for every build of the last hour, so one read of the list follows every build.
- **The strict reuse stop counts what one build looks up.** The units a cache holds are counted as the largest group
  under one key, bounded by the most units one build stored under one key (every unit now records the build that stored
  it). A table that a build looks up once, such as the voice table, keeps one unit for each set of game files its key
  saw, stored by other builds; those are no longer counted as work the build would redo. This stopped the engine and image
  stages of the v0.0.66 release build's check ("would bake again 6 of the 7 units"); on the real caches and the release's
  keys the voice table goes from 1 of 7 to 1 of 1 and the other tables keep their counts
  ([REUSE-STOP-OLD-GROUPS-67](../../bugs/REUSE-STOP-OLD-GROUPS-67.md)).
- **The performance database goes on past a changed file.** A changed file in a folder of runs or results is reported as
  a conflict and the rest of the folder is still read; the command exits 1 (`PERF-DB-FOLDER-CONFLICT-67`).
- **The bug register of the v0.0.66 release.** Its findings and closing steps are recorded: the three builder failure
  report entries and the image partition write (the partitions in 25.4 s against 110 s on the dev12 build) are closed
  with their steps, and new entries are added for the reuse stop, the guard torch step, the frame memory report's
  numbering, a resumed delivery, and two faults of `aw chimport-region`.

## What the v0.0.67 line works on

- **Tribunal and Bloodmoon in the game.** In order: the expansions' files checked; every change they make to
  Vvardenfell working end to end (the boat at Khuul, Louis Beauchamp in Ald'ruhn, Asciene Rane in Ebonheart and the way to
  Mournhold and back, the Dark Brotherhood); Solstheim built like the island; Mournhold's five districts as one exterior
  of their own; the expansions' scripts and dialogue; the save with their counts; the Toolkit's views of both; and
  playtests. Each expansion is accepted in four steps, each on a measured run and each before the next starts: the player
  can get there (reach), one quest plays from start to end (play), a save and a load in the middle of it carry on
  (continue), and then the rest of its quests and places, one at a time (broaden). The order is in the
  [roadmap](../../ROADMAP.md).
- **A builder that fails fast and says why.** Begun in this snapshot (above): the live numbers from the first second, the
  list of early checks with its first entry, the one failure page, the environment summary and the failure kind, and the
  reuse stop that counts what one build looks up. Still to come: a check that every stage read the game files the build
  selected.
- **The build times recorded again.** Every build records its stage times in the performance database, and build
  estimates come from it; the folder ingest's fix is in this snapshot, the rest follows.
- **The bug register brought up to date.** The findings and the closing steps of the v0.0.66 release are recorded (above);
  the long-open entries that were deferred to this version are still to be taken up.

The expansions' work and the rest of the list are not in this snapshot: the later snapshots of the line add them, and
their notes say what changed.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The same as for [v0.0.66](RELEASE-v0.0.66.md#what-to-check-in-play), since the game is the same: a fight with people and
creatures that cast spells or shoot bows, a kill and a save and load, the map and its markers, readied magic, leaving the
census office by its street door while a resident stands near it, and a map with many scripted objects.

## Known in this build

The game is the v0.0.66 release, so its list stands. The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of
the game's scripts run: of the 1,074 scripts the original uses, 611 run and 9 more are carried by AmiWind's own code; 433
belong to Mournhold and Solstheim and wait for them. The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how
far each land and part has come.

- **Mournhold and Solstheim are not playable yet.** Their rooms are in the image, but not their outdoors, the way there
  or their quests. Corrected for v0.0.67: the way to Mournhold works (see [the v0.0.67
  notes](RELEASE-v0.0.67.md#known-in-this-build)); its quests and much of its play are not ready.
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **A resident can still stand in front of a door**
  ([WANDER-DOOR-RULE-66](../../bugs/WANDER-DOOR-RULE-66.md), open): on the v0.0.66 journey Fargoth stood in front of the
  census office's street door again.
- **Coming back out of a door onto a resident standing on its arrival point**
  ([DOOR-ARRIVAL-INSIDE-ACTOR-66](../../bugs/DOOR-ARRIVAL-INSIDE-ACTOR-66.md)): fixed in source and covered by tests, still
  to be seen in play.
- **One of the three dreamer workers stays alive after EndGame's `SetHealth 0`**
  ([MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66](../../bugs/MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66.md)).
- **Outdoor creatures and most outdoor residents**
  ([CHIM-EXTERIOR-ACTORS-MISSING-46](../../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md), open for a long time): the town cells'
  mudcrabs and slaughterfish are placed again in v0.0.66, still to be seen in play, and the register's entry stays open
  until then (`OUTDOOR-CREATURES-REGRESSION-66`).
- **Buttons and levers that should act**: the Ghostgate switches have no in-game check on a v0.0.64 or later build
  (`WORLD-BUTTONS-62`, in the [bug tracker](../../BUGS.md)).
- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): an interrupt request lost in the
  drive that serves the test sessions' remote-console folder; players have no such drive. The game also stops with its
  clock frozen after a frame of several seconds in test sessions
  ([SESSION-STALL-AFTER-LONG-FRAME-62](../../bugs/SESSION-STALL-AFTER-LONG-FRAME-62.md)).
- **The save's whole round trip is not proven in play** (`SAVE-STATE-FIXED-CAPS-66`).
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
- **Bloodmoon's werewolves have no model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`, `NPC-WEREWOLF-NO-MODEL-66`).
- **The shores and pond edges still run in saw-tooth steps**; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- **In the builder, deferred from v0.0.66 to this version**: the image step's player view remakes all its player bodies in
  every build ([BUILD-PLAYER-VIEW-UNDERUSED-48](../../bugs/BUILD-PLAYER-VIEW-UNDERUSED-48.md)); the actor library's
  appearance bakes have no unit cache
  ([NPC-LIBRARY-NO-UNIT-CACHE-63](../../bugs/NPC-LIBRARY-NO-UNIT-CACHE-63.md)); and the gameplay journey's door aim
  changes with its eye position (`JOURNEY-AIM-RETRY-YAW-66`, in the [bug tracker](../../BUGS.md)).
- **Open in the builder since the v0.0.66 release build**: the guard torch step bakes the six boat guard models one at a
  time from scratch only to skip them all
  ([GUARD-TORCH-SCRATCH-SERIAL-67](../../bugs/GUARD-TORCH-SCRATCH-SERIAL-67.md)); the frame memory report numbers its peak
  model lists differently in a build from scratch and in one that reuses
  ([FRAME-HEAP-PEAK-MODELS-NUMBERING-67](../../bugs/FRAME-HEAP-PEAK-MODELS-NUMBERING-67.md)); a resumed delivery stops on
  the package outputs of its own failed try
  ([DELIVER-RESUME-OWN-OUTPUT-66](../../bugs/DELIVER-RESUME-OWN-OUTPUT-66.md)); and `aw chimport-region` passes a palette,
  qbsp and SDK the builder image does not hold and reports passed when every cell failed
  (`AW-CHIMPORT-REGION-NO-PALETTE-66`, `AW-CHIMPORT-REGION-PASSED-ALL-FAILED-66`). The reuse stop's fix
  ([REUSE-STOP-OLD-GROUPS-67](../../bugs/REUSE-STOP-OLD-GROUPS-67.md)), the live numbers (`BUILD-NO-STALL-ALERT-66`), the
  early check list and the performance database's folder ingest (`PERF-DB-FOLDER-CONFLICT-67`) are fixed in source and
  covered by tests; their entries stay open until a build of this line confirms them.
- **The builder's other open entries of v0.0.66 stand**: the image and room batch stages use too few cores
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md),
  [BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52](../../bugs/BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52.md),
  [BUILD-ROOM-BATCHES-UNDERUSED-54](../../bugs/BUILD-ROOM-BATCHES-UNDERUSED-54.md)); the memory leases can deadlock a
  build (`AW-LEASE-MEMORY-DEADLOCK-36`); the gate's smoke test has no remote control
  ([GATE-SMOKE-NO-REMOTE-CONTROL-60](../../bugs/GATE-SMOKE-NO-REMOTE-CONTROL-60.md)); unit keys change with settings they
  never read (`BUILD-UNIT-KEYS-REACH-64`) and the reuse check stops stages whose key changed only in code they never ran
  (`BUILD-REUSE-NEVER-READ-STOPS-66`); the performance guard judges the partition write by the number of partitions
  (`PERF-GUARD-BASIS-BY-COUNT-66`); `tools/mwad.py` has the name of the `src/mwad` package (`MWAD-NAME-CLASH-66`); the
  image step's room resident step takes about two minutes on one core when every room is cached
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`); and checks in the development container can fail on a file read with
  "Cannot allocate memory" ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md)).
- From [v0.0.66](RELEASE-v0.0.66.md): its Known list stands. Every other open entry is in the
  [bug register](../../BUGS.md).
