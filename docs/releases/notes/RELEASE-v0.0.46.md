# AmiWind v0.0.46: Red Mountain Getting Red: A Whole Heap Of Fixes

Released 20 October 2026. Running on CHIM Engine v0.2.1. Previous release: [v0.0.45](RELEASE-v0.0.45.md).

Red Mountain is red again: every region now chooses its weather the way the original game does, and the mountain
draws its blight sky. The Ebonheart dragon statue is back on its pedestal, the torch shows in third person, the
Vivec dock walkways hold the player up, and the Dreamers greet you. Under the hood, the collision pieces of the
whole island now keep only the surface you walk on, so every frame fits its memory again, and the build monitor
shows each stage's status and the machine's cores at a glance.

## What changed since v0.0.45

### The world

- **Red Mountain is red.** Every region drew the clear sky, because nothing ever chose a weather. Each region now
  picks its weather from its own chances, as the original game does, and draws that weather's sky, horizon and
  fog colours; Red Mountain gets its blight sky ([SKY-REDMOUNTAIN-BLUE-44](../../bugs/SKY-REDMOUNTAIN-BLUE-44.md)).
  Weather clouds, rain and ash, storm sounds and storm light are not in yet.
- **The Ebonheart dragon statue stands on its pedestal.** The converter kept an offset that the game throws away,
  so the statue floated over the plaza. The rule now matches the game for every model: 25 models move, among them
  the Daedric ruins and the anvils
  ([MESH-EBONHEART-DRAGON-PEDESTAL-42](../../bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md)).
- **The torch shows in third person and in the inventory picture.** The held torch was dropped from memory and never
  loaded again ([PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md)).
- **Vivec dock walkways.** The player no longer sinks into the planks
  ([CHIM-VIVEC-DOCK-WALKWAY-43](../../bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md)).
- **The Dreamers greet you.** A talk opens with the NPC's conversation greeting, and the story NPCs are active from
  the start ([NPC-DREAMER-GREETING-DEFAULT-42](../../bugs/NPC-DREAMER-GREETING-DEFAULT-42.md)).
- **Collision that keeps what you stand on.** The walkway fix gave every collision piece on the island the hull of
  all its points, which added about 55 MB of stored collision and pushed six frames over their memory. Pieces now
  keep their walkable surface exactly and give the sides a cheaper hull; one skewed Daedric ruin uses a looser
  tolerance. Kelp and grass that have no collision are rounded to the nearest 0.1 of scale, so copies share one model
  (at most 5 % of their drawn size; `--scale-snap off` keeps every scale as placed)
  ([CHIM-HULL-SURFACE-HEAP-46](../../bugs/CHIM-HULL-SURFACE-HEAP-46.md)).
- **Walkways no longer split in the distance (test switches).** Two new far-detail switches, both off by default:
  no cut before the fog is opaque, and the pieces of one structure cut together
  ([CHIM-BRIDGE-POP-PIECES-44](../../bugs/CHIM-BRIDGE-POP-PIECES-44.md)).

### The builder

- **Rebuilds reuse more.** Stair walks are keyed by the data they walk, the reuse check refuses rebuilds explained
  only by scheduling, the version or docs, and its standalone form says the same as the build
  ([BUILD-REUSE-SCHEDULER-TOP-45](../../bugs/BUILD-REUSE-SCHEDULER-TOP-45.md),
  [BUILD-REUSE-PLAN-ENV-36](../../bugs/BUILD-REUSE-PLAN-ENV-36.md)). The size guard compares with the previous release's own
  record ([BUILD-SIZE-GUARD-OLD-BASELINE-45](../../bugs/BUILD-SIZE-GUARD-OLD-BASELINE-45.md)).
- **No stand-ins.** A stand-in sky, font or video now stops the build instead of shipping
  ([SKY-FLAT-PALETTE-DRIFT-41](../../bugs/SKY-FLAT-PALETTE-DRIFT-41.md)).
- **A heap check before a converter change merges.** `tools/chim_heaviest_frames.py` lists the frames closest to their
  memory limit, for a quick build of just those.
- **Reproducible NPC bytes.** Every build and test uses one numerical kernel family, so the NPC heads come out
  byte-identical on every processor; this is the cause of the test that failed on the first CI attempt of the last
  releases. Repaired; the CI run of this release is its proof
  ([TESTS-HEAD-REDUCER-BYTES-CI-45](../../bugs/TESTS-HEAD-REDUCER-BYTES-CI-45.md)).
- **Times with their zone.** The build's finish time is printed in UTC and in local time
  ([BUILD-ETA-CLOCK-UTC-ONLY-46](../../bugs/BUILD-ETA-CLOCK-UTC-ONLY-46.md)).

### The Toolkit

- **Monitor.** Each stage now opens with a status mark that differs by shape as well as colour (built, reused,
  running, pending, failed, cancelled); time left and the finish time have rows of their own, the finish time in
  local time and UTC; and a square of one box per core shows the cores in use, green, amber under half, red once
  the build has stayed low for a while ([Toolkit: Monitor](../../AMIWIND_TOOLKIT.md#monitor)).

### Docs

- **Cell crossings measured over a fixed route.** With 128 MB a crossing takes about a third of the v0.0.44 time;
  with 16 MB it is only slightly faster ([CROSSING_BASELINE](../../performance/CROSSING_BASELINE.md)). The v0.0.45 notes,
  which said "about half", are corrected, and the v0.0.43 and v0.0.45 notes now carry their publish dates.
- **The bug register was audited** and its archives are split by version range.
- **Roadmap:** collision built from what the game already knows (its movement rules), so stair walks can leave the
  regular build ([roadmap](../../ROADMAP.md)).

## Known in this build

- [CHIM-CROSSING-SLUGGISH-43](../../bugs/CHIM-CROSSING-SLUGGISH-43.md): crossings with 16 MB still pause; the streamed
  crossing is in development.
- [CHIM-HULL-SURFACE-HEAP-46](../../bugs/CHIM-HULL-SURFACE-HEAP-46.md): after the collision fix a few frames have little
  memory to spare (20 to 40 KB).
- [CHIM-ROCKS-OPEN-SHELLS-43](../../bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): some rocks still show open faces in game.
- [HORIZON-HOLES-31](../../bugs/HORIZON-HOLES-31.md): the sky can show through distant geometry.
- [AW-20260928-10](../../bugs/AW-20260928-10.md): interior doors do not open or close.
- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): travelling from Seyda Neen to Balmora
  can stop on the Loading screen in the emulator while the host computer is writing heavily to its disk; restart
  the emulator if it happens.
- [UI-INVENTORY-FONT-TABS-42](../../bugs/UI-INVENTORY-FONT-TABS-42.md) and
  [UI-INVENTORY-ORIGINAL-LAYOUT-42](../../bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory is still work in progress.
- [NIGHT-WINDOWS-LOST-CHIM-36](../../bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night in the CHIM towns yet.
- [VIVEC-ROOM-PRECACHE-LIMIT-42](../../bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): Vivec, Telvanni Tower is left out.
- [INTERIOR-CREATURES-MISSING-41](../../bugs/INTERIOR-CREATURES-MISSING-41.md): only listed creatures are placed in
  interiors.
- [BUILD-STAIR-WALK-BRUTE-FORCE-46](../../bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md): the build still walks every staircase
  again whenever collision changes; this release's test build spent about 13 minutes on it (9 in the
  CHIM stage, the rest in the image step).

See the [bug register](../../BUGS.md) for everything else, and the [roadmap](../../ROADMAP.md) for what comes next.
