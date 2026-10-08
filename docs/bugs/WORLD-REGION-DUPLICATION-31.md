# WORLD-REGION-DUPLICATION-31: every exterior object is stored about ten times on disk

## Status: 8 October 2026

Open. Intended to be mitigated after initial tests are done. Measured by the whole-world estimate;
disk use of the shipped towns follows the same pattern. The world streamer (CHIM) stores every object once;
on the first converted town it needs about an eighth of the region maps' disk space.

## Symptom

The v0.0.31 disks hold 4.79 GB of game files for two towns, their interiors and
the terrain; the whole island would need about 20 GB of maps. Across all exterior
regions, the objects placed add up to 1,403,340 against 143,147 exterior objects
in the game: each object is stored about 9.8 times, with its faces, collision and
lightmaps. Textures (about 1 GB) and lightmaps (about 1 GB) are a small part of
the 18 GB of exterior maps; the rest is repeated geometry.

Already measured per face on 7 October 2026 by the sub-cell redundancy tool
([SUBCELL_REDUNDANCY.md](../SUBCELL_REDUNDANCY.md)): Seyda Neen's 64 maps store each
face 24.1 times on average, Balmora's 7.3 times. The whole-world estimate shows the
same pattern for every exterior region (9.8 times per object).

## Where

`tools/town_regions.py`: each region is a 768-unit core plus an overlap of at
least `sqrt(2) x draw distance + hysteresis + 32` (896 units) on every side, so
a region map covers about 2,560 units across, about eleven times its core area.

## How it happened

Every region is a self-contained Quake map, so everything visible from its core,
out to the draw distance, has to be inside it in full detail.

## Why it was not caught

It was measured for Seyda Neen and Balmora on 7 October 2026 but recorded only as
a diagnosis, not as a bug, so it never reached the register or the plan.

## Reproduction

Sum the placed objects over all regions in the world estimate and divide by the
game's exterior object count.

## Repair

Not yet. Candidates, to be measured: full detail only in the core and a short
margin, with the overlap band carrying distant shells (see the distant shell
prototype) instead of full geometry and collision; larger cores once the
overlap is cheap; textures shared between maps instead of stored in each map.

## Verification

Pending.

## Prevention

Every build reports the duplication factor (objects placed over objects in the
game) and total bytes per covered cell.
