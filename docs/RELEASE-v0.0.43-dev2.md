# AmiWind v0.0.43-dev2: the third CHIMport batch (in development)

Development snapshot, 18 October 2026, in development. Running on CHIM Engine v0.2.1. Previous snapshot:
[v0.0.43-dev1](RELEASE-v0.0.43-dev1.md). Previous release: [v0.0.42](RELEASE-v0.0.42.md).

The second v0.0.43 snapshot: the next CHIMport batch, lightest cells first, from the
[cell weight table](chim/CHIMPORT.md).

## What changed since v0.0.43-dev1

- **38 more cells on CHIM** (1,303 to 1,341 cells in the region list), among them Falensarano, Zainab Camp, Vas and
  the whole of Dagoth Ur's surroundings.
- **The 14 cells that were waiting for a hull policy now pass.** They held the two tree meshes fixed in dev1
  ([CHIM-HULL-ROUTE-NO-CUT-43](bugs/CHIM-HULL-ROUTE-NO-CUT-43.md)); the cell tracker now shows 1,189 of 1,436 land
  cells passed, with none pending.
- **The cell tracker and its reference** are republished with these results.
- **The image step's frame maps run on all cores:** the world is read once instead of six times, and the region and
  town frame maps are made on the worker pool, the same image byte for byte (region maps 61 to 35 s, town and region
  phase 99 to 42 s; [BUILD-IMAGE-REGION-MAPS-SERIAL-43](bugs/BUILD-IMAGE-REGION-MAPS-SERIAL-43.md)).
- **The playtest is about 4 % smaller** (1.34 to 1.28 GB): the 38 cells now on CHIM no longer ship their classic maps.
- **Docs:** the [progress tracker](chim/PROGRESS_TRACKER.md) opens with the current state; the FAQ answers whether a
  MiSTer or a Vampire can run AmiWind, and the roadmap names the next steps after the outdoors (an entrance audit
  and an interior tracker) and an RTG display path as a possibility.

## Known in this build

- [CHIM-STAIR-STEPS-SOLID-43](bugs/CHIM-STAIR-STEPS-SOLID-43.md): four cells (Ald-ruhn, Maar Gan, Suran and one
  rope bridge cell) still fail the stair walk and stay off CHIM; the mechanism is measured, the fix is open.
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): travelling from Seyda Neen to Balmora can
  stop on the Loading screen in the emulator while the host computer is writing heavily to its disk; restart the
  emulator if it happens.
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the dragon statue in Ebonheart's
  plaza still floats without its pedestal.
- [UI-INVENTORY-FONT-TABS-42](bugs/UI-INVENTORY-FONT-TABS-42.md) and
  [UI-INVENTORY-ORIGINAL-LAYOUT-42](bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory is still work in progress.
- [NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night in the CHIM towns yet.

The rest is as in the [v0.0.42 notes](RELEASE-v0.0.42.md#known-in-this-build); everything else is in the
[bug register](BUGS.md).
