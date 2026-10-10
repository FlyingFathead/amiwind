# Disk image size: what is in the game image, and where it is going

This page explains the size of the AmiWind disk images, file group by file group, and how the CHIM engine
brings the whole game down to a single partition.

Figures are measured from the v0.0.34 release build (its image read back file by file, 2026-10-10).

## v0.0.34 today

The game ships as two hard-disk images:

| Image | Size | Partitions |
|---|---|---|
| `AmiWind-v0.0.34.hdf` | 3.75 GiB | DH0 (system, game data) 1.50 GiB, DW0 (world) 1.50 GiB |
| `AmiWind-v0.0.34-world-01.hdf` | 1.75 GiB | DW1 (world) 1.24 GiB, DW2 (world) 0.03 GiB |

Together they hold 18,392 files, 4.26 GiB of content. Identical files stored twice account for only 0.01 GiB, so
the size does not come from copied files. It comes from how the open world is built.

### What the content is

| Group | Files | Size | Share | What it is |
|---|---|---|---|---|
| Open-world region maps (`maps/vf*.bsp`) | 2,532 | 3,531 MB | 83 % | The island outside the towns, built with the legacy world method |
| NPC gallery (`gallery/`) | 7,106 | 219 MB | 5 % | Prerendered NPC heads and figures |
| Sounds and voices (`sound/`) | 7,352 | 195 MB | 5 % | Effects, creature sounds, dialogue voices |
| Intro (`intro/`) | 43 | 131 MB | 3 % | The opening sequence |
| Video (`media/`) | 1 | 61 MB | 1 % | |
| Music (`music/`) | 21 | 54 MB | 1 % | |
| Game logic (`progs/`) | 316 | 47 MB | 1 % | Compiled QuakeC |
| Interiors and towns (other `maps/`) | ~60 | ~89 MB | 2 % | Balmora, its interiors, Seyda Neen, the Temple, ... |
| CHIM world (`chim/` + CHIM frame maps) | ~124 | ~28 MB | < 1 % | Seyda Neen and Balmora on the CHIM engine |
| Character, interface, graphics, engine | ~800 | ~12 MB | | |

### What is on CHIM today

The towns: Seyda Neen (its square, the docks and the census office courtyard) and Balmora are CHIM frame maps,
converted from your own game data. The open land outside the towns, including the coast around Seyda Neen, is still
built with the legacy world method below. CHIMport replaces it cell by cell, starting at the coast.

### Why the open world is so large

The legacy world method cuts the island into overlapping region maps. Each region map contains its own core area
plus a wide overlap on every side, so it can be loaded on its own. As a result, every object outside the towns is stored
in about ten region maps (measured: 9.8 copies per object). The 2,532 region maps are 83 % of the image.

## Roadmap horizon: one partition with CHIM

This is a goal on the roadmap horizon, not a feature of this release: the image stays as it is above until the whole
island runs on CHIM.

The CHIM engine ("Chunks and Heaps In Memory") stores every mesh, texture and piece of terrain once and places it by
reference, cell by cell, and streams it as you move. There is no overlap and no copy per region.

CHIMport converts the island to CHIM cell by cell, starting at the coast and moving inland. Measured so far: the
combined CHIM world of all cells converted up to each ring, where every shared mesh and texture is stored once
(cumulative, each ring adds the next band of cells inland; MiB):

| Cells converted | Combined CHIM world |
|---|---|
| 171 (coast) | 66 MiB |
| 331 | 242 MiB |
| ~480 | 506 MiB |
| ~742 | 1,011 MiB |

Summing each cell's own files without sharing gives 2.6 GB for the whole island (all 1,292 cells): an upper
bound, since a combined world stores shared assets once. The gap grows inland as more assets are shared (at about
742 cells: 1,011 MiB combined against 1,388 MB summed per cell).

The island has 1,292 exterior cells, and the cells get denser inland, so the size per cell grows. A projection from
the combined rings, not yet measured, puts the whole island at about 1.8-2.2 GB. That is at the edge of one
partition, and it is not yet proven to fit.

The plan, on the roadmap horizon:

1. Build the whole island on CHIM and measure it.
2. Squeeze it below 2 GiB: one copy of each texture and mesh variant, compressed visibility data, less per-cell file
   overhead.
3. A builder gate fails any build whose world does not fit one partition.
4. The legacy region maps (3.5 GB) leave the image.

The rest of the game (sounds, gallery, intro, music, video, game logic, interiors) is about 0.75 GB. The horizon goal:
with the island on CHIM, the whole game on ONE disk image, with the world in a single partition.

## Amiga limits this has to respect

- Every partition is smaller than 2 GiB and starts below 2 GiB on its drive (Kickstart 3.1 cannot mount one that starts
  past it).
- Every file is well under 2 GiB (PAKs below about 1 GiB, sharded).
- Every disk image is smaller than 4 GiB.

The builder's disk-layout gate enforces all of these for every image type.
