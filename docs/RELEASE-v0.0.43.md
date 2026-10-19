# AmiWind v0.0.43: Let There Be CHIM: Vvardenfell's Outdoors, All of It

Released 18 October 2026. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.42](RELEASE-v0.0.42.md); development snapshots [v0.0.43-dev1](RELEASE-v0.0.43-dev1.md),
[v0.0.43-dev2](RELEASE-v0.0.43-dev2.md), [v0.0.43-dev3](RELEASE-v0.0.43-dev3.md) and
[v0.0.43-dev4](RELEASE-v0.0.43-dev4.md).

Every exterior cell of Vvardenfell is on CHIM: no classic region maps are left outdoors. With it come the fixes
from the maintainer's v0.0.43-dev2 playtest and a builder that keeps its cores busy.

## What changed since v0.0.42

### The world

- **All of Vvardenfell's outdoors on CHIM.** The 227 cells that stayed classic in v0.0.42 joined in three CHIMport
  batches, lightest cells first, from the [cell weight table](chim/CHIMPORT.md): the medium cells, then
  Falensarano, Zainab Camp, Vas and the whole of Dagoth Ur's surroundings, then the towns that waited for their
  heaviest cell (Ald-ruhn, Maar Gan, Suran, Buckmoth) and Balmora's border cells, now whole CHIM cells instead of
  narrow classic strips ([CHIM-BALMORA-INSET-SLIVERS-43](bugs/CHIM-BALMORA-INSET-SLIVERS-43.md)).
- **The sea floor and the open sea:** the 98 sea floor cells whose land records carry no heights are taken as flat
  seabed, as the original game does ([CHIM-REGION-SEABED-NO-HEIGHTS-42](bugs/CHIM-REGION-SEABED-NO-HEIGHTS-42.md)),
  and fourteen open-sea cells off the west coast join as ocean cells
  ([CHIM-OCEAN-CELL-RECORD-CLASSIC-43](bugs/CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md)).
- **The stair walk passes everywhere.** Three meshes carried collision that did not match their visible steps: a
  ramp over the Redoran stairs, a slope over a Hlaalu canal walkway and a solid layer over a rope bridge. The
  shared converter now checks collision over every visible flight and replaces what blocks it
  ([CHIM-STAIR-STEPS-SOLID-43](bugs/CHIM-STAIR-STEPS-SOLID-43.md)).
- **Two tree meshes no longer keep 14 cells off CHIM:** their collision is compiled into a compact tree
  ([CHIM-HULL-ROUTE-NO-CUT-43](bugs/CHIM-HULL-ROUTE-NO-CUT-43.md)).
- **Red Mountain's summit** no longer meets a solid sky ceiling
  ([CHIM-RED-MOUNTAIN-SOLID-SKY-43](bugs/CHIM-RED-MOUNTAIN-SOLID-SKY-43.md)).
- **Editor markers** (bridge, boat and town markers) are no longer drawn or solid; they stay as invisible objects
  for later sound and effect use ([COLLISION-NC-FLAGS-32](bugs/COLLISION-NC-FLAGS-32.md)).
- **Floating plants on Azura's Coast** sit on their trunks again
  ([CHIM-AZURA-FLOATING-FLORA-43](bugs/CHIM-AZURA-FLOATING-FLORA-43.md)).
- **Interior plants and trees are sprites by default, and NPC heads keep their outline**
  ([INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md),
  [NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md)).
- **The sea reaches the horizon at Vivec**
  ([VIVEC-ARENA-WATER-FALL-32](bugs/VIVEC-ARENA-WATER-FALL-32.md)).
- **The playtest is smaller:** cells on CHIM no longer ship their classic maps.

### The build tools

- **No stage starves in silence:** a pooled stage is checked against the memory it needs before it starts, grows
  back as soon as one more unit fits, and prints an alarm when it is held below half its workers
  ([BUILD-SCHEDULER-MEMORY-STARVED-42](bugs/BUILD-SCHEDULER-MEMORY-STARVED-42.md),
  [BUILD-STAGE-ALLOWANCE-STUCK-43](bugs/BUILD-STAGE-ALLOWANCE-STUCK-43.md)).
- **Pools inside a stage follow the build's budget**, and a passed stair walk is reused
  ([BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42](bugs/BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42.md),
  [BUILD-CHIM-STAIR-NO-REUSE-42](bugs/BUILD-CHIM-STAIR-NO-REUSE-42.md)).
- **The image step's frame maps run on all cores**, the same image byte for byte
  ([BUILD-IMAGE-REGION-MAPS-SERIAL-43](bugs/BUILD-IMAGE-REGION-MAPS-SERIAL-43.md)), and the image step accepts a
  world with every cell on CHIM ([BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43](bugs/BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43.md)).

### Docs

- The [progress tracker](chim/PROGRESS_TRACKER.md) opens with the current state; the FAQ answers whether a MiSTer
  or a Vampire can run AmiWind and whether AmiWind is a decompilation of Morrowind (it is not); the roadmap names
  the next steps after the outdoors (an entrance audit and an interior tracker).

## Known in this build

- [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the player sinks into the Vivec dock walkways
  and can get stuck there.
- [BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): the build's stair walk uses only about
  half of its cores; the image is not affected, the build is slower than it should be.
- [CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43](bugs/CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43.md): stair plates of most meshes
  still get an approximate collision hull.
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](bugs/CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): ruin pillars near Azura's Coast can
  look like shapes hanging in the air.
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): travelling from Seyda Neen to Balmora
  can stop on the Loading screen in the emulator while the host computer is writing heavily to its disk; restart
  the emulator if it happens.
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the dragon statue in Ebonheart's
  plaza floats without its pedestal.
- [UI-INVENTORY-FONT-TABS-42](bugs/UI-INVENTORY-FONT-TABS-42.md) and
  [UI-INVENTORY-ORIGINAL-LAYOUT-42](bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory is still work in progress.
- [NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night in the CHIM towns yet.
- [VIVEC-ROOM-PRECACHE-LIMIT-42](bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): Vivec, Telvanni Tower is left out.
- [INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md): only listed creatures are placed in
  interiors.

See the [bug register](BUGS.md) for everything else.
