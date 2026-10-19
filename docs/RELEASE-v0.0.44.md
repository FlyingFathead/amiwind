# AmiWind v0.0.44: By Azura's Trees!

Released 19 October 2026. Running on CHIM Engine v0.2.1. Previous release: [v0.0.43](RELEASE-v0.0.43.md);
development snapshot [v0.0.44-dev1](RELEASE-v0.0.44-dev1.md).

A patch release for v0.0.43. Its fix for the floating tree crowns on Azura's Coast made the Bitter Coast trees
about 60 % larger, and two Bitter Coast areas no longer fit in memory, so the v0.0.43 image could not be built.
This patch makes those trees 16 to 42 % lighter while every trunk keeps at least 90 % of its height. It also
fixes the player body, the guards' torches and the interior plant sprites found while building its image, gives
the guards in the streets their night torches back, and brings the docs up to date.

## What went wrong and how it was fixed

- **Bitter Coast trees too heavy.** v0.0.43's fix for the floating tree crowns made the Bitter Coast trees about
  60 % larger; two Bitter Coast areas no longer fit in memory and the image could not be built. The trunk shape
  guard now tries lighter copies first: the trees are 16 to 42 % smaller and every trunk keeps at least 90 % of
  its height ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md)).
- **Player bodies and guard torches could not be built.** The new NPC head reducer, which keeps every head's
  outline, left no fitting model for some player bodies and guard torch models. They fall back to the previous
  reducer, and a rebuilt guard model within one rounding step of the original is accepted
  ([NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md)).
- **Interior plant sprites missing outside Vivec.** The plant sprites of converted interiors were installed only
  for the Vivec rooms; every room type installs them now
  ([INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md)).
- **Outdoor guards lost their torches at night.** The guard torch step looked for guards only in the older map
  files, and before the image step writes the CHIM frame maps that hold the towns and regions on CHIM since
  v0.0.36, so only guards indoors got a torch and every guard in the streets walked its night duty without one.
  The step now reads both kinds of map, after the frame maps are written: 19 guard types get their torch instead
  of 13 ([GUARD-TORCH-CHIM-FRAMES-44](bugs/GUARD-TORCH-CHIM-FRAMES-44.md)).
- **The CHIM tracker counted the wrong thing.** It counted the cells that had passed their audits, not what the
  build put on CHIM, and still showed 1,193 of 1,436 cells. It now counts what each build puts on CHIM: all 1,292
  Vvardenfell land cells and 117 sea cells ([TRACKER-CHIM-COUNT-STALE-44](bugs/TRACKER-CHIM-COUNT-STALE-44.md)).

## What changed since v0.0.43

### The world

- **Bitter Coast trees are lighter again.** The trunk shape guard that keeps Azura's Coast tree crowns on their
  trunks now tries a lighter copy first: the Bitter Coast trees are 16 to 42 % smaller than in v0.0.43, every
  trunk keeps at least 90 % of its height, and both Bitter Coast areas fit in memory again
  ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md)).
- **The player body is built again for every race.** The search for the player's own body falls back to the
  previous head reducer when no body fits with the new one, as the NPC heads already do; the image step had
  stopped on the Argonian female body ([NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md)).
- **Guards with torches are built again.** A guard's held-torch model accepts either head reducer, a budget too
  small for the guard is skipped instead of stopping the step, and a rebuild within one rounding step of the
  original model is accepted and recorded ([NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md)).
- **Outdoor guards carry their torches at night again.** The Hlaalu guards in Balmora's streets, the Ordinators
  and Imperial guards outside and the guards of the intro docks walk their night duty with a lit torch again, as
  they did before v0.0.36 ([GUARD-TORCH-CHIM-FRAMES-44](bugs/GUARD-TORCH-CHIM-FRAMES-44.md)).
- **Interior plant sprites reach every room.** The Balmora interiors and the area and harvest rooms copied only
  their maps and left their plant sprites behind; every room now installs its sprites with its map
  ([INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md)).

### Docs

- The FAQ and the CHIM pages are current with v0.0.43.
- The roadmap describes [the road after v0.0.44](ROADMAP.md#the-road-after-v0044-19-october-2026): smoother
  crossings between CHIM cells, every interior of the base game, object and container state, NPC placement and
  compiled MWScript; the [v0.0.45 plan](PLAN-v0.0.45.md) lists the first steps.
- Two new reports from the maintainer are registered:
  [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md) and
  [CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md).

## Known in this build

- [CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): crossing from one CHIM cell to the next can
  stall for a moment, worst at cell corners; the repair is the first step of v0.0.45.
- [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): some rocks do not close up and show open faces.
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

See the [bug register](BUGS.md) for everything else, and the [roadmap](ROADMAP.md) for what comes next.
