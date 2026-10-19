# WATER-UNDERWATER-SKY-44: under water the distance shows the sky's clouds instead of blue water

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | the sea, diving under the waves (screenshot 19 October 2026) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | low: a visual break; no effect on play |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 19 October 2026

Reported by the maintainer; not fixed yet.

## Symptom

Diving under the waves, the distant view behind the water shows the sky's cloud layer. In the original game the
view fades to blue under water.

## Where

Anywhere in the sea (the maintainer's screenshot of 19 October 2026).

## How it happened

The horizon and sky are drawn the same way above and below the water surface: no underwater colour replaces them.

## Why it was not caught

No underwater view is part of the visual checks.

## Reproduction

Always: swim under the surface and look toward the horizon.

## Repair

To do, two options measured side by side: an underwater fog colour and horizon fill in blue; or, the maintainer's
idea, the same cloud layers tinted in grades of blue so they read as swirling water, which reuses what is already
drawn. A/B against the original at the same place.

## Verification

To do: stills and a short clip under water, original and AmiWind.

## Prevention

To do: an underwater pose in the visual check set.

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
- [LAND-HORIZON-GAPS-29](LAND-HORIZON-GAPS-29.md): Sky visible through gaps in distant resident ground
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions

<!-- END GENERATED CATEGORY -->
