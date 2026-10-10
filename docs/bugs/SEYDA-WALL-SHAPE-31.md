# SEYDA-WALL-SHAPE-31: dark shape pokes out of a stone wall by the Seyda Neen shore

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev2 |
| Where | Seyda Neen shore stone wall near map sn019 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.28, v0.0.30, v0.0.31-dev2 (last seen) |
| Severity | low: A tree card's dark trunk base is drawn over a stone wall from some headings; cosmetic. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| Playtest version | v0.0.31-dev2 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Owner report from the v0.0.31-dev2 playtest. Likely cause found by a
ray-cast simulation of the reported pose; not yet confirmed with an in-game
capture. No repair yet.

## Symptom

A dark, brown, roughly triangular shape sticks out of the side of a stone wall,
level with the ground, near the shore and the docks. The owner had not seen it
in earlier builds.

## Where

Seyda Neen, global XYZ -10474 -73437 135 (local 197 -439 33), looking
north-east toward the docks; map `sn019` (or an overlapping neighbour with the
same content).

## How it happened

The shape is most likely the trunk base of the Bitter Coast tree
`flora_bc_tree_02` (original reference 483210, scale 1.37), which in the
original stands about 230 units behind the dry-stone wall corner
`ex_drystonewall_c_01` (reference 113892). Trees are drawn as camera-facing
cards (sprite type 2, `tools/prepare_tree_sprites.py`, since v0.0.28), and the
card is depth-tested at the depth of the tree's origin, about 107 units along
the view axis here (AmiQuake `R_SetupAndDrawSprite`). The far end of the wall
is about 126 units deep, behind the card, so where the card's dark trunk base
overlaps the wall's far end, the trunk is drawn over it.

Placement, rotation and scale match the original; nothing between v0.0.30 and
v0.0.31-dev2 changed the sprite, its entity or the sprite code. A ray-cast of
the same pose against the v0.0.30 map shows the same shape (575 sprite pixels
over the wall, 573 in dev2). The card turns with the view, so the artifact
appears only from some headings, which is why it was not seen before.

## Why it was not caught

Billboard depth errors only show where a card's lower part overlaps nearer
geometry from particular angles; no check looks for card pixels drawn in front
of geometry that should hide them.

## Reproduction

v0.0.31-dev2 (or v0.0.30): `dbg tp -10474 -73437`, face north-east (about
052), pitch about +10, look at the stone wall on the left.

## Repair

Not done. Options: push the card's depth back by about the trunk radius (or
clamp it); draw the trunk as a small mesh or crossed quads and keep only the
canopy as a card; or orient the card plane at the tree's position instead of
the view plane. Confirm first with an in-game capture (headlamp off and on)
and an OpenMW reference view of the same pose.

## Verification

Pending.

## Prevention

A capture set of tree cards next to walls from several headings.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
- LAND-HORIZON-GAPS-29 (no report page): Sky visible through gaps in distant resident ground
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars

<!-- END GENERATED CATEGORY -->
