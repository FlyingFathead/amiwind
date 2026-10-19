# LAND-HORIZON-GAPS-29: Sky visible through distant ground

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 5 October 2026, in v0.0.29-dev2 |
| Where | Bitter Coast, distant resident ground beyond the forward-distance gate |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29-dev2 (last seen) |
| Severity | medium: Sky shows through gaps in distant ground; opt-in pass restores it, default stays off. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

Historical reports describe gaps in resident distant LAND. The maintainer supplies
two v0.0.38-dev2 screenshots showing an incomplete jagged mountain silhouette
and asks that distant/topographic terrain occlude the sky. This follow-up is
linked provisionally; the exact current cause is not independently reproduced.

## Where

Grazelands cell 12,6, displayed global 101239,52173,525. The screenshots show
the same displayed position with differing heading (165 versus 130) and clock
(17:08 versus 17:21); they are not a controlled single-variable comparison.

## How it happened

Historical source investigation implicated a forward-distance node gate that
omitted resident LAND. An opt-in aw_terrain_horizon pass was recorded with native
and cost gates pending. Do not assume this proves the current package cause.
Inspect AmiQuake BSP visibility, distance clipping and existing horizon machinery
before choosing a repair. Preserve global topomap alignment and current sky.

## Why it was not caught

Historical optional repair lacked completed native OFF/ON acceptance. Current
package has no attached matched-view reproduction for these supplied poses.

## Reproduction

Use the reported cell and position, sweep heading at a fixed clock and camera
mode, then move while retaining heading. Bind exact package, map format, renderer
settings and terrain coverage. Compare matched original/OpenMW views.

## Repair

Pending current diagnosis. Distant ground should provide continuous appropriate
occlusion without changing unrelated sky rendering. Measure baseline cost.

## Verification

Maintainer evidence preserved; no new repair or native acceptance established.

## Prevention

Keep matched horizon sweeps and boundary traversal controls for legacy and CHIM
terrain. Verify coverage and occlusion separately from optional cloud styling.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
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
