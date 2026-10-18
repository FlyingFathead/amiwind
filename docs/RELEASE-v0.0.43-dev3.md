# AmiWind v0.0.43-dev3: every exterior cell on CHIM (in development)

Development snapshot, 18 October 2026, in development. Running on CHIM Engine v0.2.1. Previous snapshot:
[v0.0.43-dev2](RELEASE-v0.0.43-dev2.md). Previous release: [v0.0.42](RELEASE-v0.0.42.md).

The first build with every exterior cell of Vvardenfell on CHIM: no classic region maps are left outdoors.

## What changed since v0.0.43-dev2

- **The stair walk passes everywhere.** Three meshes carried collision that did not match their visible steps:
  a ramp over the Redoran stairs, a slope invented over a Hlaalu canal walkway and a solid layer over a rope bridge.
  The shared converter now checks collision over every visible flight and replaces what blocks it, so the 39 cells
  around Ald-ruhn, Buckmoth, Maar Gan and Suran come onto CHIM
  ([CHIM-STAIR-STEPS-SOLID-43](bugs/CHIM-STAIR-STEPS-SOLID-43.md)).
- **Balmora's border cells are whole CHIM cells** instead of narrow classic strips around the town
  ([CHIM-BALMORA-INSET-SLIVERS-43](bugs/CHIM-BALMORA-INSET-SLIVERS-43.md)).
- **Fourteen open-sea cells off the west coast** join as ocean cells
  ([CHIM-OCEAN-CELL-RECORD-CLASSIC-43](bugs/CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md)).
- **Docs:** the FAQ answers whether AmiWind is a decompilation of Morrowind (it is not); the bug journal's older
  entries moved to a dated archive.

## Known in this build

- [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the walkway at the Vivec Hlaalu canton dock
  cannot be climbed; the player sinks into it and gets stuck. The cause is found, the fix comes in a later snapshot.
- [CHIM-RED-MOUNTAIN-SOLID-SKY-43](bugs/CHIM-RED-MOUNTAIN-SOLID-SKY-43.md): on the Red Mountain summit the player can
  end up inside solid ground with only the sky drawn. The cause is found, the fix comes in a later snapshot.
- [BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): the build's stair walk used only about
  half of its cores; the image is not affected, the build is slower than it should be.
- [CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43](bugs/CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43.md): stair plates of most meshes
  still get an approximate collision hull; the meshes the stair fix changed are handled.
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
