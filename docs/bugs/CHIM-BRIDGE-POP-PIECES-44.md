# CHIM-BRIDGE-POP-PIECES-44: bridges pop into view piece by piece as the player approaches (Balmora)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44 |
| Where | Balmora bridges over the Odai, approaching from a distance |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44 (last seen) |
| Severity | medium: Visible pop-in of a landmark in the best-looking town |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.44_release-try2_c84f8506 |
| From commit | source c84f850, engine c84f850, CHIM world c84f850 |
| CHIM engine version | CHIM 0.2.1, engine c84f850, world format 0.7 |
| Platform or emulator | unknown (maintainer playtest report, emulator not stated) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 19 October 2026

Reported by the maintainer; cause suspected, not checked.

## Symptom

Walking toward Balmora, a bridge over the Odai appears one piece at a time: for a while it is visibly cut, with
gaps between the parts already drawn. The maintainer: a visual glitch that stands out because the rest of Balmora
holds up well at a distance.

## Where

Balmora's bridges, approached from a distance; likely every object built from several placements.

## How it happened

Suspected: each bridge segment is its own placement with its own distance test, so the segments cross the draw
distance one at a time instead of the bridge as a whole.

## Why it was not caught

No check looks at objects made of several placements as they come into view.

## Reproduction

Always, as far as reported: approach a Balmora bridge from outside the draw distance.

## Repair

To do: confirm the cause with the entity inspector on a Balmora bridge. Fix candidates: one distance test for a
group of placements that form one object, or the island cut-out of the
[distant terrain notes](../DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026) standing in
until every piece is drawn.

Plan of 19 October 2026 (maintainer): no distance cut where the fog is still see-through, then a far shell of the
whole island drawn in one fog colour through the engine's existing solid-surface path, with the real world emerging
from it and grouped, overlapping switches so no transition leaves a hole ([distant terrain
notes](../DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026),
[roadmap](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026)).
This bug is fixed on its own as well; the shell does not merely hide it.

## Verification

To do: a short clip of the approach before and after, same route and time of day.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
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

Related bugs in other categories:

- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames

<!-- END GENERATED CATEGORY -->
