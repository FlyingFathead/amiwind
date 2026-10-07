# SEYDA-WALL-SHAPE-31: dark shape pokes out of a stone wall by the Seyda Neen shore

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
