# AmiWind v0.0.45: CHIM Streaming Improved, Guard Torches Are Back

Released 20 October 2026. Running on CHIM Engine v0.2.1. Previous release: [v0.0.44](RELEASE-v0.0.44.md).

Crossing from one CHIM cell to the next uses spare Fast RAM now: the frames around the player are read ahead into
memory while you walk, and the engine's heap grows with the RAM the machine has instead of staying at the built
11 MiB. On a 128 MiB machine a crossing takes about a third of the v0.0.44 time (light areas about 290-370 ms down to
about 120 ms, Balmora about 650-820 ms down to about 200-220 ms); a 16 MiB machine keeps today's sizes and is only
1-7 % faster. (Corrected 20 October 2026: first published as "about half as long", from one measurement; the
figures here are from a fixed route, [CROSSING_BASELINE](performance/CROSSING_BASELINE.md).) The guards in the streets carry their torches at night again. More
improvements to cell-to-cell streaming are on the way: the largest remaining part of a crossing is the engine
restarting the game for every new frame, and the next step replaces that with a switch in place.

## What changed since v0.0.44

### Streaming

- **Frames read ahead into spare Fast RAM.** While the player walks, the frames around the current one are read
  into memory beyond the 16 MiB baseline, so a crossing finds most of what it needs already loaded. Measured over a
  fixed route on a 128 MiB setup: about a third of the v0.0.44 time (light areas 293-367 ms down to 117-123 ms,
  Balmora 650-822 ms down to 201-223 ms); with 16 MiB, 1-7 % faster
  ([CROSSING_BASELINE](performance/CROSSING_BASELINE.md), [CHIM-CROSSING-SYNC-LOAD-43](bugs/CHIM-CROSSING-SYNC-LOAD-43.md)).
- **A heap sized from the free Fast RAM.** At start the engine sizes its heap from the largest free Fast RAM
  block, less a margin for the system and sound: 24 MiB and an 82 MiB CHIM cache on a 128 MiB setup, the built
  11 MiB on a 16 MiB one. The start option `-heapmb` still overrides it
  ([ENGINE-HEAP-FIXED-SIZE-43](bugs/ENGINE-HEAP-FIXED-SIZE-43.md)).
- **What is left of a crossing.** A crossing measured on the v0.0.44 data spends about 220 to 260 ms restarting
  the game for the next frame, the same with 16 or 128 MiB, so more RAM cannot shorten that part. The next step
  keeps the game running and switches the frame in place; today's method stays selectable
  ([CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md), [the v0.0.45 plan](PLAN-v0.0.45.md)).

### The world

- **Guard torches at night.** The guard torch step looked for guards only in the older map files, and before
  the image step writes the CHIM frames that hold the towns and regions, so only guards indoors got a torch. It
  reads both kinds of map now and runs after the frames are written: 19 guard types get their torch instead of 13
  ([GUARD-TORCH-CHIM-FRAMES-44](bugs/GUARD-TORCH-CHIM-FRAMES-44.md)).

### The builder

- **The CHIM stage on every core.** Its sections that ran on one core while the other units waited (visibility
  rows, the stair gate, validation) run on the worker pool, with the same output byte for byte
  ([BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md)).
- **Scheduling changes no longer rebuild everything.** The code that decides how many units run at once no
  longer counts as an input of the stages and the NPC gallery, so a change to it keeps their finished work
  reusable; the stair walks still walk again after a change to the world loader and follow in the next version
  ([BUILD-REUSE-SCHEDULER-TOP-45](bugs/BUILD-REUSE-SCHEDULER-TOP-45.md)).
- **Every map listing sees the CHIM frames.** The tools that read the staged maps list both kinds of map file, and
  a test refuses a new listing that sees only the older kind.
- **A rock audit.** A check over every rock mesh compares the converted rocks with the original's faces, winding
  and rotation; it found the converter keeps them as the original has them
  ([CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md)).

### Docs

- The CHIM progress tracker explains every number it counts in one table, and the README's v0.0.43 count is
  completed: 1,409 cells on CHIM, the 61 cells of the town frames included.
- The roadmap and the v0.0.45 plan describe the distant views without pop-in, a HUD outside the per-frame screen
  conversion, and Mournhold's open districts with their sky and weather.

## Known in this build

- [CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): a crossing still pauses for a moment, mostly while
  the game restarts for the next frame; the switch in place is the next step.
- [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): some rocks still show open faces in game; the
  converter is ruled out, the in-game cause is still to be found.
- [CHIM-BRIDGE-POP-PIECES-44](bugs/CHIM-BRIDGE-POP-PIECES-44.md) and [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md):
  bridges appear piece by piece and the sky can show through distant geometry.
- [PLAYER-TORCH-THIRDPERSON-38](bugs/PLAYER-TORCH-THIRDPERSON-38.md): in third person the player's torch is not
  shown.
- [AW-20260928-10](bugs/AW-20260928-10.md): interior doors do not open or close.
- [SKY-REDMOUNTAIN-BLUE-44](bugs/SKY-REDMOUNTAIN-BLUE-44.md): Red Mountain has a clear blue sky instead of its red
  weather.
- [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the player sinks into the Vivec dock walkways
  and can get stuck there.
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
- [BUILD-BODY-BAKE-SLOWER-44](bugs/BUILD-BODY-BAKE-SLOWER-44.md): the build's player body bake is slower than its
  baseline; the image is not affected.

See the [bug register](BUGS.md) for everything else, and the [roadmap](ROADMAP.md) for what comes next.
