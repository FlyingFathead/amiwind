# AmiWind v0.0.61-dev1 (in development)

Development snapshot, 5 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.60](RELEASE-v0.0.60.md).

The first snapshot of v0.0.61. It opens the version and carries no game changes: it adds two pages to the
documentation. The plan for v0.0.61 is the list in the [roadmap](../../ROADMAP.md); none of it is in this snapshot.
The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.60

- **The gameplay recorder, planned.** [GAME_RECORDER](../../GAME_RECORDER.md) describes a recorder for testing: it
  records a session (a save at the start plus the player's inputs, about 1 MB an hour), plays it back exactly, shows
  where a replay differs, and measures frame times over marked segments. Recordings are meant to become gameplay tests
  and benchmarks in the boot smoke and the delivery checks. Nothing of it is in the game yet.
- **The emulator disk stall: hypotheses and a test plan.** The
  [bug page](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md) now lists what is known, three suspected causes (a lost
  completion signal inside the emulator, the remote-console folder, and the smoke's own stall label, which is inferred
  and not checked), and how each will be tested. The shipped presets are unchanged.
- The roadmap lists both under v0.0.61.

## Known in this build

These are the known problems of [v0.0.60](RELEASE-v0.0.60.md) that remain in this snapshot.

- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames; the frames are not yet measured with the per-area tables.
- A build's performance check can fail on the resident bake of the Vivec town, which costs about three and a half
  times its earlier CPU per unit
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- `dbg kill` and the essential-death message of v0.0.60 are checked by tests; checking them in game is pending.
- The frame times of the walking residents and of the arrival frame with the per-area tables.
- All of the v0.0.61 list.
