# CHIM-TERRAIN-TEXTURE-BLOCKY-43: roads and paths on the ground look blocky

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 20:02 +0300: maintainer: repeats on every path of the game; second spot cell 1,-4 (global 14165 -32687 788): the path edge is jagged, square by square
- Reported with v0.0.43-dev2 at 2026-10-18 20:05 +0300: maintainer: a needless zig-zag along the roads across the map (the stair-step edges of the texture squares)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Ascadian Isles, cell 1,-4 (global 15133 -31424 931): roads and paths island-wide |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | low: a visual roughness on every road and path; no effect on play |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Open. Reported by the maintainer during the v0.0.43-dev2 playtest.

## Symptom

Roads and paths on the ground look blocky: a path breaks into separate squares of texture instead of reading as
one continuous track.

## Where

Every road and path on the island; the reference spot is the Ascadian Isles, cell 1,-4 (global position 15133
-31424 931, local 711 -688 232).

## How it happened

Morrowind paints the ground with a land texture layer of 16 by 16 squares per cell and blends each square into
its neighbours. The terrain here draws one texture per square with hard edges, so a road made of a few squares
shows every square boundary.

## Why it was not caught

The terrain checks compare heights and coverage with the original; nothing compares the look of the texture
layer.

## Reproduction

In v0.0.43-dev2, look along a road or path, for example in the Ascadian Isles at cell 1,-4.

## Repair

Planned, as an A/B measured in memory and frame time on the 68040 preset and compared with OpenMW at the same
pose: (a) baked transition textures for the edge pairs that actually occur, stored once and shared; (b) a dithered
edge band baked into the terrain surfaces, with no extra cost per frame; (c) finer texture squares along roads and
paths only.

## Verification

The reference spot before and after, next to OpenMW at the same pose.

## Prevention

A texture-layer check in the terrain audit: square edges where the original blends.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
- [LAND-HORIZON-GAPS-29](LAND-HORIZON-GAPS-29.md): Sky visible through gaps in distant resident ground
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions
- [WATER-UNDERWATER-SKY-44](WATER-UNDERWATER-SKY-44.md): Under water the distance shows the sky's clouds instead of blue water

<!-- END GENERATED CATEGORY -->
