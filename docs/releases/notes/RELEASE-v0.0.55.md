# AmiWind v0.0.55: Sky Is Turning Red (Among Other Things)

Released 29 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.54](RELEASE-v0.0.54.md); development
snapshots [v0.0.55-dev1](RELEASE-v0.0.55-dev1.md) and [v0.0.55-dev2](RELEASE-v0.0.55-dev2.md).

Nearer Red Mountain the sky turns red before you reach the mountain's own region, its clouds race and the crater sky
is darker still. Builds survive memory pressure on any machine, the build monitor shows the memory, the build disk and
every warning of a build, old build runs no longer pile up for ever, and the docs are organised. The game needs 32 MB
of Fast RAM; the emulator presets have it.

This release is the v0.0.55 development line with the version changed: the world of the v0.0.55-dev2 build, with only
the engine and the image built again. It was not also built from scratch this time; that check moves to v0.0.56.

## What changed since v0.0.54

- **The sky turns red nearer Red Mountain.** DemoWind's Red Mountain sky is in the game: the nearer the mountain, the
  more the sky, the light on the land and, at half strength, the distance fog take the game's own Blight weather
  colours, before the Red Mountain region begins; the clouds speed up toward Blight's cloud speed without jumping, and
  in the crater the sky is a quarter darker still. Ald'ruhn keeps its own weather; the change starts just outside the
  Ghostfence. `aw_redmountain 0` keeps the region weather alone, and `dbg weather` shows how strong the pull is where
  you stand ([DAY_NIGHT_AND_SKY.md](../../DAY_NIGHT_AND_SKY.md#region-weather-20-october-2026),
  [RED-MOUNTAIN-MENACE-54](../../BUGS.md)). Checked in game at 32 MB Fast at Ald'ruhn and outside the Ghostfence
  during development.
- **Builds survive memory pressure on any machine.** The memory guard, its warnings and the worker pools' limits read
  the machine's own memory when there is no container ([BUILD-GUARD-BLIND-NO-CGROUP-55](../../BUGS.md)); a worker lost
  to memory costs a retry with fewer units at once, not the build ([BUILD-OOM-DEGRADE-NOT-DIE-54](../../BUGS.md)); the
  CHIM stage's early frame checks run under the same limits ([BUILD-CHIM-EARLY-CHECK-POOL-55](../../BUGS.md)).
- **The build monitor shows memory, the disk and every warning.** `RAM: used, available` and `Disk: free of total`
  above the core squares (orange, then red as either runs out), the memory curve beside the cores on the timeline,
  and a yellow `Warnings: N [view]` row with every warning line of the stage logs. The build log gets `[memory]` and
  `[disk]` warnings while either is nearly gone ([TOOLKIT-MONITOR-NO-MEMORY-55](../../BUGS.md),
  [MONITOR-WARNINGS-ROW-54](../../BUGS.md), [AmiWind Toolkit](../../AMIWIND_TOOLKIT.md#monitor),
  [BUILD_PROFILE.md](../../BUILD_PROFILE.md)).
- **Old build runs no longer pile up.** The garbage collector (`tools/build_gc.py`) lets the runs of release series
  older than the newest three expire (a pinned or running build always stays), every build warns before the first
  stage when its disk is 80 % full and names the collector's command, and nothing is deleted without `--delete`
  ([free disk space](../../BUILD_CACHE.md#free-disk-space)).
- **Toolkit.** A reload keeps the open tab ([TOOLKIT-RELOAD-WORLD-55](../../BUGS.md)), and a magnifier on a row of
  Recent builds and gates opens that build in the monitor ([TOOLKIT-RESULTS-NO-OPEN-55](../../BUGS.md)).
- **DemoWind** (`dbg demowind`): cheap effects shown one at a time in place of the world, with their cost on screen
  ([DEMOWIND.md](../../DEMOWIND.md)).
- **The docs are organised.** Release notes, patches and one-off records have folders of their own, and
  [docs/README.md](../../README.md) is a generated index of every document; nothing was deleted, every old path is in
  [MOVES.json](../../history/MOVES.json).
- **The debug HUD** writes `GLOBAL XYZ: N/A (interior)` indoors, so the clock fits again
  ([HUD-INTERIOR-CLOCK-CUT-54](../../BUGS.md)); the bug register writes its pages' contents lists itself.

## Known in this build

- Inside the Red Mountain region the sky is the game's Blight weather as before; the red pull only adds the darker
  crater there. The silhouettes of far hills carry a thin bright rim against the reddened sky.
- The build cache's own entries (CHIM units, image passes, the pool's keys) are still kept whole; only old runs age
  out so far (BUILD-CACHE-NO-RETENTION-55 in the [bug register](../../BUGS.md)). A new bug report page is not yet added to the release
  file list by itself ([REGISTER-ADD-NO-RELEASE-ROW-48](../../BUGS.md)).
- The CHIM stage's main process still holds a lot of memory of its own, which keeps its workers few on a small
  machine ([BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Moved to v0.0.56: the build from scratch of the release line, the stale-docs pass, weather by region with its
  storm poses, the Ghostfence's own animation, the merged arena mode, first-person weapons, the QuakeC frame share,
  and characters that wander and attack by their own records ([roadmap](../../ROADMAP.md)).
- Everything else is in the [bug register](../../BUGS.md).
