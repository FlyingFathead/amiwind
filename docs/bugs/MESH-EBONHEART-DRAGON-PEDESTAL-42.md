# MESH-EBONHEART-DRAGON-PEDESTAL-42: Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.42-dev1 at 2026-10-17 12:02 +0300: maintainer: statue floating in the air, no pedestal drawn
- Reported with v0.0.43-dev1 at 2026-10-18 07:50 +0300: maintainer: the after image (test engine with the popping fix) still has the statue floating in the air
- Reported with v0.0.45 at 2026-10-20 02:50 +0300: same converter rule in v0.0.45; cause: the root NiNode translation (z 327.1) kept, the game drops it; fixed on branch v0.0.46-sky-pedestal, needs a world build

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | Ebonheart plaza, ex_imp_dragonstatue (vivec_city frame, cell 2,-13) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.46 |
| Severity | medium: A landmark statue hangs in the air over the plaza in every build since at least v0.0.41 |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | v0.0.42-dev1 (full-dev1-proof) |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | unknown (the maintainer's own emulator session; reproduced the same day in FS-UAE 3.1.66 (JIT) with the dev1 and v0.0.41 images) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 20 October 2026](#status-20-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Island-wide sweep](#island-wide-sweep)
- [Repair](#repair)
- [Reproduction](#reproduction)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 20 October 2026

Fixed in v0.0.46. The maintainer checked the v0.0.46-dev1 playtest on the evening of 20 October 2026: "ebonheart's statue pedestal is at least confirmed fixed, just checked it out".
The text below is the state before that build.

Cause found: the converter applied the translation of the model's root node, which the game drops. Repaired in
the source on branch v0.0.46-sky-pedestal for every model at once (25 models, 723 placements island-wide), not
yet in a build. Still present in v0.0.45 (same converter rule). Needs a world rebuild and an in-game look.

## Symptom

The maintainer, v0.0.42-dev1, 17 October 2026: in the Ebonheart plaza the dragon statue hangs in the air,
"no pedestal drawn in". Its round base is drawn; below it there is sky down to the plaza.

## Where

The converted model `x/ex_imp_dragonstatue@s1` (CHIM model 4447 of the dev1 world, vivec_city frame, cell
2,-13).

## How it happened

Found 20 October 2026: nothing is missing; the whole model is drawn 327 units too high. In
`ex_imp_dragonstatue.nif` the root is a NiNode (`Ex_imp_statue_base`, the file's first record) with a
translation of z 327.1; the base (`Tri Ex_imp_statue_base 0-2`), the column and the dragon are its children. The
game drops the whole transform of such a root (rule from OpenMW file components/nif/node.cpp, NiNode::read: a
Morrowind NIF's root NiNode, record 0, any name but Bip01, gets the identity transform). The converter
(`tools/prepare_scenery.py` `model_geometry`, rule `nif_common.root_local` 'morrowind', since
BALMORA-TEMPLE-GEOMETRY-29) dropped only the root's rotation and kept its translation and scale. With the game's
rule the model spans z -92 to 1,060 around its origin: placed at z 416, its base starts at z 324, 20 units into
the plaza's top (z 344), as a statue on its plinth; with the converter's it started at z 652, 308 units above the
plaza, which reads as a statue without its pedestal.

The Temple repair kept the root translation because `contain_crate_01` (root offset z -32) rests on the floor only
with it: that crate's root is the NiTriShape itself, not a NiNode, and the game keeps the whole transform of such a
root, so the crate is unchanged by this repair.

Measured on 17 October 2026:

- The original data place one `ex_imp_dragonstatue` at 18577, -101915, z 416 and the plaza
  (`ex_imp_plaza`) at z 48; no other object stands under the statue (every reference of cell 2,-13 within
  700 units). So the column is part of the statue's own model or of the plaza model.
- The converted statue's vertices span z 59 to 347 engine units above its origin (236 to 1,388 original
  units): nothing below 236. Its base therefore starts at about z 652, while the plaza's converted tiles reach
  at most 296 units above their origin (z 344).
- It is not a streaming fault (it was first reported beside CHIM-ZONE-RELEASE-FLICKER-42): the statue floats
  the same in v0.0.41, in v0.0.42-dev1 and with the zone repairs, where every chunk of the ring at that pose
  is loaded.

## Why it was not caught

No check compares a converted model's vertical extent with its original mesh, and the plaza was not looked at
in game before. The Temple repair took the crate as proof that root translations are kept, without telling a
NiTriShape root from a NiNode root.

## Island-wide sweep

`tools/nif_root_audit.py --data-files DIR` (20 October 2026, Morrowind.esm, 3,679 placed models): 25 models whose
root the game's rule and the converter's earlier rule treat differently, with 54 exterior and 669 interior
placements. The shift is how far every earlier build moved them (the earlier rule's origin minus the game's, in
original units):

| Model | Shift (x, y, z) | Exterior | Interior |
| --- | --- | --- | --- |
| x/ex_dae_ruin_01 | 0, 0, -1,018 (sunk) | 41 | 2 |
| x/ex_dae_mehrunesdagon | -3, 30, +421 | 0 | 10 |
| x/ex_imp_dragonstatue | 0, 0, +327 | 1 | 0 |
| x/ex_dae_malacath_attack | 0, 3, +316 | 2 | 9 |
| i/in_dagoth_bridge00 | 7, -138, +29 | 0 | 1 |
| i/in_de_shipwreckul_lg | 5, 37, +92 | 0 | 5 |
| f/furn_bone_stake00 | 0, 0, +61 | 0 | 514 |
| f/furn_anvil00 | 0, 0, +32 | 6 | 21 |
| m/misc_bellows10 | 0, 0, +8 | 0 | 15 |
| f/furn_6th_ashaltar | 0, 0, -4 | 0 | 24 |
| x/ex_common_house_addon | 0, 3, 0 | 4 | 0 |
| d/door_dwrv_loadup00 | 0, -3, +2 (and its root rotation) | 0 | 11 |
| 13 ground robes (c/c_m_robe_*_gnd) | under 1 unit | 0 | 57 |

Checked against the land: with the game's rule the six exterior anvils rest on the terrain (bottom at land height
within 0 to 8 units; with the earlier rule all 32 above it) and the Malacath statue at 45508, 178361 touches the
land within 0.1 unit (earlier rule: 316 above). The 41 exterior Daedric ruins (`ex_dae_ruin_01`) were drawn 1,018
units too low by every build so far. No model with a non-NiNode root has a rotation (the one case where the earlier
rule dropped a transform the game keeps); no creature model changes; NPC body parts do not use this converter path.

## Repair

`nif_common.scenery_root_local` (default rule 'node'): a root NiNode that is the file's first record and not named
Bip01 loses its whole transform; any other root keeps its whole transform. `prepare_scenery.model_geometry` (every
scenery, CHIM, door, interior and creature model, visual and collision) and `model_flames` use it. The earlier rules
stay selectable (`model_geometry(..., root_rule='morrowind')` and `'legacy'`). `tools/nif_root_audit.py` lists every
placed model the rule moves. The CHIM model, tile and cut unit keys now include `tools/nif_common.py` (they read
geometry through it but were not keyed on it).

Rebuild cost: every CHIM variant, tile and cut unit and every scenery stage that reaches `prepare_scenery.py` is
recomputed once (the converter changed); the NPC gallery and NPC level bakes are rekeyed by the same file
although no creature or body model changes.

## Reproduction

`dbg tp 19705 -101510`, `aw_aim 211 -13`: the statue hangs above the tower roofs to the right of the crosshair.

## Verification

Done (source, 20 October 2026): `tests/test_scenery_root_transform.py`: a root NiNode's translation (the statue's
z 327.1) and scale are dropped (both fail on the earlier converter), a NiTriShape root keeps its offset (the
crate), Bip01 and later-record roots keep theirs, the earlier rules stay selectable, the audit lists the moved
models, the CHIM unit keys include the rule's file. The real `ex_imp_dragonstatue.nif` converts to z -92 to 1,060
(was 236 to 1,388).

To do: a world build, then at the reproduction pose (and in a headless OpenMW view of it) the statue on its
plinth on the plaza, headlamp off and on; the same for one Daedric ruin (`ex_dae_ruin_01`, e.g. the pair at
-119173, 115206), an exterior anvil and an interior with bone stakes.

## Prevention

`tools/nif_root_audit.py` names every placed model whose root the rule changes; the test pins the rule on
fictional meshes. Still open: a converter check that a model's converted bounds match the original mesh's bounds
as the game composes it (per mesh, island wide).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- BALMORA-GROUND-DENTS-51 (no report page): Sharp V-shaped dents in Balmora s ground beside the canal wall (cell -3,-2); the maintainer: they are back
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- CHIM-COLLISION-ROOM-FILLED-54 (no report page): One convex collision piece fills the room above a floor of the same mesh: seven trapdoors and a Redoran hut door cannot be used
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- CHIM-DOOR-TERRAIN-COARSE-54 (no report page): The 128-unit terrain tiles bridge the dip a door sits in: two Dwemer doors have ground 170 to 190 units above the threshold
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
- CHIM-ROOM-LAVA-TOP-ROUNDING-48 (no report page): A lava room was kept as a room map: the pool top compared rounded (record -66.55, brush -66.56)
- [CHIM-STRIDER-SCALED-SEAMS-36](CHIM-STRIDER-SCALED-SEAMS-36.md): Seyda Neen's silt strider (scale 0.89 variant) still shows open seams; Balmora's (scale 1.0) is closed
- [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md): Terrain triangle diagonals differ from the OpenMW 0.48 reference
- [CONVERT-COLLISION-FALLBACK-32](CONVERT-COLLISION-FALLBACK-32.md): Five Balmora meshes fall back to a collision union in qbsp
- [CONVERT-DEGENERATE-FACES-32](CONVERT-DEGENERATE-FACES-32.md): The converter writes degenerate faces (no area, slivers, repeated vertices)
- [CONVERT-FACE-PLANE-32](CONVERT-FACE-PLANE-32.md): Converter takes a merged face's plane from its first three vertices
- [CONVERT-FACE-WINDING-32](CONVERT-FACE-WINDING-32.md): Six prison faces are wound opposite to their plane side
- [CONVERT-MERGE-NONPLANAR-32](CONVERT-MERGE-NONPLANAR-32.md): Merged polygons can be slightly non-planar (up to about 0.05 units)
- [CONVERT-QHULL-FLAT-32](CONVERT-QHULL-FLAT-32.md): Collision building fails on a flat mesh (chitin shortbow)
- [CONVERT-TEXCOORD-RANGE-32](CONVERT-TEXCOORD-RANGE-32.md): Converter does not check the 16-bit texture-coordinate range
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- [GHOSTFENCE-NO-ANIMATION-46](GHOSTFENCE-NO-ANIMATION-46.md): The Ghostfence's shimmering curtain does not move: its texture scroll is dropped by the converter
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SEAM-AUDIT-IGNORES-RIM-TEARS-54 (no report page): The seam audit reports meshes with torn rims as ok
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames

<!-- END GENERATED CATEGORY -->
