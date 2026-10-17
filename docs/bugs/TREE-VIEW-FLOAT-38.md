# TREE-VIEW-FLOAT-38: Direction-dependent floating sprite tree

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Grazelands cell 10,11; global 89029,96069,1369 |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Visible tree placement or projection defect. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| Playtest version | v0.0.38-dev2 (visible screenshot label) |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Version visible; exact installed binary and map hashes not supplied. |
| Platform or emulator | unknown (Emulator not identified.) |

<!-- END GENERATED FACTS -->

## Symptom
The maintainer reports a sprite tree floating above terrain in v0.0.38-dev2,
visible from one general direction. The first image shows the detached trunk.

## Where
Grazelands, cell (10,11), global (89029,96069,1369), heading 234,
pitch 29, game time 09:39. Exact installed map and engine hashes are unknown.

## How it happened
Unknown. Compare placement, sprite bounds/pivot, terrain height and projection.
Do not assume a shared cause with non-unit-scale sprite omissions.

## Why it was not caught
No exact-pose, multi-direction native check is recorded for this placement.

## Reproduction
Compare the two maintainer views from 12 October at 15:34:54 and 15:35:33
(Europe/Helsinki), then circle the same tree in the target engine and OpenMW.
Both screenshots have been visually checked; native reproduction remains pending.

## Repair
Pending diagnosis. Preserve the approved distant-tree silhouettes.

## Verification
Maintainer evidence is a reproduction report, not a repair acceptance result.

## Prevention
Check the same placement from multiple headings and heights before acceptance.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-153454`: SHA-256 `2898758f4d2e52bc0f7d62a138522ce41835ede5b7ca0c52c18e724f8b410064`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-153533`: SHA-256 `e6f32e97ba682f09e244175a4ad2daabc4621618492a36009ec85f716bf8eb90`. Screenshot association checked; no repair or behavioral acceptance inferred.

Second pose: global (88614,96298,1231), cell (10,11), heading 207,
pitch -13, game time 10:02.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

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

<!-- END GENERATED CATEGORY -->
