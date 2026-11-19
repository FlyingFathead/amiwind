# SKY-VISUAL-01: Sky-only day/night remap clashed with gray distance fog

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 4 October 2026, in v0.0.28-rc1 |
| Where | Day/night sky remap against gray distance fog |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.28-rc1 (last seen) |
| Severity | medium: Contrasting distant silhouettes and moire; visual fault. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-04: reported in v0.0.28-rc1
- 2026-10-04: EFRAG-01: static foliage leaf links exhausted in image004: Recorded 4 October 2026 from the 06:26:57 EEST final verification.
- 2026-10-04: SKY-VISUAL-01: sky-only day/night remap conflicts with gray fog: Recorded 4 October 2026 during the bounded native route for the earlier v0.0.28-rc1 candidate.
- 2026-10-04: HDF-WRITER-01: private image005 refresh left owned blocks free: Filesystem evidence and scope: both the 07:27:36 EEST post-exit and 07:30:07 EEST post-reboot checks passed: 8,788 original files checked, none missing or unexpectedly ...

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- [CHIM-STAR-TREES-POP-64](CHIM-STAR-TREES-POP-64.md): Star trees (crossed-plane crowns) pop in and out of view while the camera moves
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
- [TREE-PILLAR-28](TREE-PILLAR-28.md): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions
- [WATER-UNDERWATER-SKY-44](WATER-UNDERWATER-SKY-44.md): Under water the distance shows the sky's clouds instead of blue water

<!-- END GENERATED CATEGORY -->
