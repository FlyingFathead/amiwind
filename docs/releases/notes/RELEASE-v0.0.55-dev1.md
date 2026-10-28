# AmiWind v0.0.55-dev1 (in development)

Development snapshot, 28 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.54](RELEASE-v0.0.54.md).

The first snapshot of v0.0.55, a builder fix first: a build on a machine that runs short of memory now slows down and
says so, instead of crawling for hours and then failing. The game itself is the v0.0.54 game with the DemoWind test
effects and one HUD fix; it needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.54

- **Builds survive memory pressure on any machine.** A tester's full build on a Linux machine without a container ran
  its CHIM stage for 38 hours on less than half a core and then stopped when the system ended one of its workers for
  lack of memory. The builder's memory guard, its warnings and the memory limits of its worker pools read only a
  container's limit, so on a plain machine they saw nothing; they now read the machine's own memory when there is no
  container ([BUILD-GUARD-BLIND-NO-CGROUP-55](../../BUGS.md)). A worker lost to memory now costs a retry, not
  the build: its unfinished work goes out again with half as many units at once, at most twice, each time with one
  `[pool] WARNING: RAM exhausted?` line ([BUILD-OOM-DEGRADE-NOT-DIE-54](../../BUGS.md)). The CHIM stage's early
  frame checks, where that build stopped, run on the stage's own workers under the same limits
  ([BUILD-CHIM-EARLY-CHECK-POOL-55](../../BUGS.md)).
- **Memory in the build log and the Toolkit monitor.** The monitor shows `RAM: used, available` above the core squares
  (orange under 20 % available, red under 10 %), the peak and the stages that ran then, and the memory as a second
  curve beside the cores on the stage timeline. The build log gets a `[memory]` line at each new peak above 75 % and a
  warning every 5 minutes while less than 10 % is available ([TOOLKIT-MONITOR-NO-MEMORY-55](../../BUGS.md),
  [BUILD_PROFILE.md](../../BUILD_PROFILE.md), [AmiWind Toolkit](../../AMIWIND_TOOLKIT.md#monitor)).
- **Toolkit.** A reload keeps the open tab instead of going back to World
  ([TOOLKIT-RELOAD-WORLD-55](../../BUGS.md)), and a magnifier on a row of Recent builds and gates opens that
  build in the monitor ([TOOLKIT-RESULTS-NO-OPEN-55](../../BUGS.md)).
- **DemoWind** (`dbg demowind`): cheap effects shown one at a time in place of the world, with their cost on screen;
  the first is the Red Mountain sky in eight steps from Seyda Neen to the crater, in the colours of the game's own
  blight and ash storm weather ([DEMOWIND.md](../../DEMOWIND.md)). A test of the effect, not yet in the game's sky.
- **The debug HUD** writes `GLOBAL XYZ: N/A (interior)` indoors, so the clock fits again
  ([HUD-INTERIOR-CLOCK-CUT-54](../../BUGS.md)).
- **The docs are organised.** Release notes, patches and one-off records have folders of their own, and
  [docs/README.md](../../README.md) is a generated index of every document; nothing was deleted, every old path is
  listed in [MOVES.json](../../history/MOVES.json).
- **Room and resident units keyed per mesh (first part).** A new row of a per-mesh measured table now changes only
  the cached units of that mesh instead of every room and resident unit; the stages that read the tables still
  run again when a row changes, and no build has proven the fix with a new row yet, so the bug stays open
  ([BUILD-KEY-MESH-TABLE-WHOLE-54](../../BUGS.md)).

## Known in this build

- The CHIM stage's main process still holds a lot of memory of its own, which keeps its workers few on a small
  machine ([BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
