# AmiWind v0.0.43-dev1: the builder catches up (in development)

Development snapshot, 17 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.42](RELEASE-v0.0.42.md).

The first v0.0.43 snapshot: the build system fixes found while building v0.0.42, then the next CHIMport batch
(the medium cells, config/chim-weight-classes.json).

## What changed since v0.0.42

- **A stage is no longer starved of workers in silence.** The v0.0.42 final spent about two hours of its CHIM step
  on one worker: the memory guard held it back and never let it grow again. A pooled stage is now checked against
  the memory it needs before it starts, a throttled stage grows back as soon as one more of its units fits under
  80 % of the limit, and a stage held below half its workers for five minutes prints a `[scheduler] ALARM` line
  naming the lease that would let it run at full speed
  ([BUILD-SCHEDULER-MEMORY-STARVED-42](bugs/BUILD-SCHEDULER-MEMORY-STARVED-42.md)).
- **The pools inside a stage follow the build's budget**, not the share the stage got when it started: the CHIM
  stair gate of the final ran on 2 workers while 12 were free
  ([BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42](bugs/BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42.md)).
- **A passed stair walk is reused**, also when a passed build took it from an earlier run: the final walked all
  1,118 frames again ([BUILD-CHIM-STAIR-NO-REUSE-42](bugs/BUILD-CHIM-STAIR-NO-REUSE-42.md)).
- **Seabed cells with no height data can go onto CHIM.** A LAND record without heights is taken as flat seabed at
  the game's default height, as CHIMport already did; the full build refused these 98 cells and named none of them
  ([CHIM-REGION-SEABED-NO-HEIGHTS-42](bugs/CHIM-REGION-SEABED-NO-HEIGHTS-42.md)).
- **Two tree meshes no longer keep 14 cells off CHIM.** Their collision was one long chain even after routing; it
  is now compiled into a compact tree (285 to 29 and 465 to 37 steps deep)
  ([CHIM-HULL-ROUTE-NO-CUT-43](bugs/CHIM-HULL-ROUTE-NO-CUT-43.md)).

## Known in this build

- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): travelling from Seyda Neen to Balmora can
  stop on the Loading screen in the emulator while the host computer is writing heavily to its disk (the emulator's
  hard disk loses a request); restart the emulator if it happens. Not seen on a quiet host.
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the dragon statue in Ebonheart's
  plaza still floats without its pedestal.
- [UI-INVENTORY-FONT-TABS-42](bugs/UI-INVENTORY-FONT-TABS-42.md) and
  [UI-INVENTORY-ORIGINAL-LAYOUT-42](bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory is still work in progress.
- [NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night in the CHIM towns yet.

The rest is as in the [v0.0.42 notes](RELEASE-v0.0.42.md#known-in-this-build); everything else is in the
[bug register](BUGS.md).
