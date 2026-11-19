# CHIM-STAR-TREES-POP-64: Star trees (crossed-plane crowns) pop in and out of view while the camera moves

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 November 2026, in v0.0.64-dev3 |
| Where | tools/chim_tree_star.py (the star tree copies); the engine brush model passes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.64-dev3 (last seen) |
| Severity | medium: a test-only tree method; it decides against this method |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | MiniWind v0.0.64-dev3 |
| From commit | source caa123b, engine caa123b, CHIM world caa123b |
| CHIM engine version | CHIM 0.2.2, engine caa123b, world format 0.11 |
| Platform or emulator | FS-UAE 32 MB Fast, 68040 JIT preset |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- [HORIZON-POP-29](HORIZON-POP-29.md): Ashlands horizon pops or breaks up while turning
- [LAND-HORIZON-GAPS-29](LAND-HORIZON-GAPS-29.md): Sky visible through gaps in distant resident ground
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- [SKY-FOG-OFF-BACKGROUND-25](SKY-FOG-OFF-BACKGROUND-25.md): With fog off, far pixels outdoors that no surface covered showed a pale solid background instead of the sky
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- [SKY-STARS-28](SKY-STARS-28.md): Enlarged stars cover original night artwork
- [SKY-VISUAL-01](SKY-VISUAL-01.md): Sky-only day/night remap clashed with gray distance fog
- [TREE-PILLAR-28](TREE-PILLAR-28.md): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions
- [WATER-UNDERWATER-SKY-44](WATER-UNDERWATER-SKY-44.md): Under water the distance shows the sky's clouds instead of blue water

Related bugs in other categories:

- [CHIM-SOLSTHEIM-TREE-FACES-64](CHIM-SOLSTHEIM-TREE-FACES-64.md): A dense Solstheim forest frame draws about six times the faces of a median Vvardenfell view

<!-- END GENERATED CATEGORY -->
