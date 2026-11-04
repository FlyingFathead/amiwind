# AmiWind v0.0.60-dev1 (in development)

Development snapshot, 4 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.59](RELEASE-v0.0.59.md).

The first snapshot of v0.0.60. It opens the development line: the version number moves to v0.0.60-dev1, and the plan
for v0.0.60 is the list in the [roadmap](../../ROADMAP.md). No item of that list is finished in this snapshot; the game
is the v0.0.59 release. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.59

- Nothing is finished yet. The items of v0.0.60 are listed in the [roadmap](../../ROADMAP.md) and are added here as
  each one is done and checked.

## Known in this build

These are the known problems of [v0.0.59](RELEASE-v0.0.59.md), which this snapshot carries unchanged.

- Containers whose contents are levelled lists open empty
  ([CONTAINER-LEVELLED-CONTENTS-EMPTY-59](../../bugs/CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md)).
- Bodies of dead actors cannot be looted yet
  ([CORPSE-INVENTORY-NOT-OPENABLE-59](../../bugs/CORPSE-INVENTORY-NOT-OPENABLE-59.md)).
- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames.
- A build's performance check can fail on the resident bake of the Vivec town, which costs about three and a half
  times its earlier CPU per unit
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Everything in the v0.0.60 list; nothing of it is in this snapshot.
