# AmiWind v0.0.60-dev4 (in development)

Development snapshot, 4 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.59](RELEASE-v0.0.59.md). Previous snapshot: [v0.0.60-dev3](RELEASE-v0.0.60-dev3.md).

The fourth snapshot of v0.0.60. It moves the residents' appearance data into the per-area pack, adds a console pick to
kill an actor for testing, and opens a tracker of the base game's systems. The plan for v0.0.60 is the list in the
[roadmap](../../ROADMAP.md); most of it is still open. The game needs 32 MB of Fast RAM, and the emulator presets of
this snapshot have it.

## New since v0.0.60-dev3

- **Residents built from parts read their appearance from the shared per-area pack.** The recipe a resident is built
  from is stored in the same per-area layout as the other resident data, instead of in a file searched while you walk.
  The old files stay in the build behind the switch `aw_npc_tables_areas 0`. The figures are in
  [NPC-RECIPE-TABLES](../../performance/NPC-RECIPE-TABLES.md); the frames in game are not yet measured with it.
- **The game feature tracker.** [GAME_FEATURES](../../GAME_FEATURES.md) lists 48 systems of the base game and how far
  each one is: 10 done, 29 partial, 9 missing.
- **`dbg kill`.** A console command that shows a red crosshair; clicking an NPC or creature kills it, and the body lies
  down and can be searched. `dbg kill REF` kills one actor by reference. It is a testing aid for combat and looting.
- **The essential-death message.** When an essential character dies, the game shows its own message.

## Known in this build

These are the known problems of [v0.0.60-dev3](RELEASE-v0.0.60-dev3.md) that remain in this snapshot.

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

- `dbg kill` and the essential-death message are checked by tests; checking them in game is pending.
- The frame times of the walking residents and of the arrival frame with the per-area tables.
- The rest of the v0.0.60 list; none of it is in this snapshot.
