# AmiWind v0.0.60: Work With What You've Got

Release, 4 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.59](RELEASE-v0.0.59.md).

v0.0.60, "Work With What You've Got", is a smaller release that finishes what v0.0.59 left open: beds and two rank
raises work again, containers with levelled contents show their items, the bodies of the dead can be searched, the
walking residents and the residents built from parts read small per-area tables instead of searching files, and the
base game has a tracker of its systems. The game needs 32 MB of Fast RAM, and the emulator presets of this release have
it. This release is the fourth development snapshot of v0.0.60 (dev4) with its final version number; the combat work
and the larger data and dialogue items move, openly, to v0.0.61.

## Checked in game

Two of the changes below were checked in game on a Seyda Neen sandbox at 32 MB Fast RAM: levelled container contents
(Arrille's Tradehouse baskets and a crate rolled their items and kept them on reopening) and searching a body (E opens
what the body carried; what was taken stayed taken after leaving and coming back). The other changes are checked by
tests or by the build; what is not yet checked in game is listed at the end of these notes.

## New since v0.0.59

- **Beds and the two rank raises work again.** v0.0.59 shipped compiled scripts made by an older compiler than the one
  in its source (7,339 bindings instead of 8,566), so placed beds gave no rest window and two rank raises did nothing.
  The scripts stage is rebuilt whenever the script compiler changes, not only when a function it ran changes: the
  compiler's identity, the table of calls the engine provides and the files it hashes whole are part of the stage's
  key, and the image step refuses compiled scripts made by another compiler.
- **Levelled container contents.** Containers whose contents are levelled lists roll their items by the original's
  rules the first time they are opened, and keep them across saves
  ([CONTAINER-LEVELLED-CONTENTS-EMPTY-59](../../bugs/CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md)).
- **Searching a body.** A dead actor lying in reach under the crosshair reads "E: Search", and E opens what it carried
  in the container strip; taking from a body is not theft, and what was taken stays taken after leaving and coming
  back. The aim at actors uses the box of the frame being drawn, not the whole model's bounds, which include the lying
  pose and reached past a standing actor next to a body; a death is recorded at once, so a body killed just before
  leaving a room is still there on return
  ([CORPSE-INVENTORY-NOT-OPENABLE-59](../../bugs/CORPSE-INVENTORY-NOT-OPENABLE-59.md)).
- **The walking residents' data per area.** The packages of the walking residents are split by each placement's own
  cell and kept in memory per area, searched there instead of in files while you walk. How much it saves in the
  emulator is not yet measured.
- **The residents' appearance pack.** The recipe a resident built from parts is drawn from is stored in the same
  per-area layout as the other resident data, instead of in a file searched while you walk. The old files stay in the
  build behind the switch `aw_npc_tables_areas 0`. The figures are in
  [NPC-RECIPE-TABLES](../../performance/NPC-RECIPE-TABLES.md).
- **The game feature tracker.** [GAME_FEATURES](../../GAME_FEATURES.md) lists 48 systems of the base game and how far
  each one is: 10 done, 29 partial, 9 missing.
- **`dbg kill`.** A console command that shows a red crosshair; clicking an NPC or creature kills it, and the body lies
  down and can be searched. `dbg kill REF` kills one actor by reference. It is a testing aid for combat and looting.
- **The essential-death message.** When an essential character dies, the game shows its own message.
- **The builder and the release tooling.** A build that grows past the size margin says early that a final will stop
  there and records it ([BUILD-SIZE-GUARD-LATE-48](../../bugs/BUILD-SIZE-GUARD-LATE-48.md)); the delivery checks its
  output names at the start, before the boot check; the reuse check runs its preflight once instead of twice (143
  seconds instead of 286 on a busy host, same result); padded disk images are copied onto the J: drive in a way the
  drive accepts; and the check that boots the finished image in the emulator sends no key until the game's own remote
  state file appears, so a key typed during the start-up memory notice can no longer turn the CHIM cache off and fail
  the check.

## Known in this build

- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames; the per-area tables for the walking residents are in this build, and the frames are not
  yet measured with them.
- A build's performance check can fail on the resident bake of the Vivec town, which costs about three and a half
  times its earlier CPU per unit
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- With the earlier recipe files (the switch set to 0), a room's table stays held outdoors
  (NPC-RECIPE-FILES-ROOM-HELD-60).
- The boot check of a build sometimes gets no remote control from the emulator and passes on a rerun
  ([GATE-SMOKE-NO-REMOTE-CONTROL-60](../../bugs/GATE-SMOKE-NO-REMOTE-CONTROL-60.md)); one native test
  (TEST-SKEL-NATIVE-FLAKY-UNDER-LOAD-60) failed once under host load; the builder script `tools/build_aga.py` is 7 bytes
  under the release text size limit (BUILD-AGA-AT-TEXT-LIMIT-60).

## Not yet checked in game

- `dbg kill` and the essential-death message are checked by tests; checking them in game is pending.
- The frame times of the walking residents and of the arrival frame with the per-area tables.
- The in-game checks carried over from v0.0.59 (items in their places and dropping every kind of item, the container
  strip, the world change list, resting and waiting, the coordinate conversion on the streamed towns, what the player
  wears and wields); they are in the v0.0.61 list of the [roadmap](../../ROADMAP.md).
- The rest of the v0.0.61 list, none of which is in this release.
