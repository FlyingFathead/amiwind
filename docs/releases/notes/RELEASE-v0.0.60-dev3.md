# AmiWind v0.0.60-dev3 (in development)

Development snapshot, 4 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.59](RELEASE-v0.0.59.md). Previous snapshot: [v0.0.60-dev2](RELEASE-v0.0.60-dev2.md).

The third snapshot of v0.0.60. It adds a fix that was proven in game: the bodies of dead actors can be searched. The
plan for v0.0.60 is the list in the [roadmap](../../ROADMAP.md); most of it is still open. The game needs 32 MB of
Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.60-dev2

- **Searching a body.** A dead actor lying in reach under the crosshair reads "E: Search", and E opens what it carried
  in the container strip; taking from a body is not theft, and what was taken stays taken after leaving and coming back.
  The aim at actors now uses the box of the frame being drawn, not the whole model's bounds, which include the lying
  pose and reached past a standing actor next to a body; a death is recorded at once, so a body killed just before
  leaving a room is still there on return
  ([CORPSE-INVENTORY-NOT-OPENABLE-59](../../bugs/CORPSE-INVENTORY-NOT-OPENABLE-59.md)). Checked in game.

## Known in this build

These are the known problems of [v0.0.60-dev2](RELEASE-v0.0.60-dev2.md) that remain in this snapshot, except the
search of a body, fixed above.

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

- The frame times of the walking residents and of the arrival frame with the per-area tables.
- The rest of the v0.0.60 list; none of it is in this snapshot.
