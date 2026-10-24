# MESH-VIVEC-CAP-GAP-38: Vivec giant mushroom cap opening

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): RC1: three inspected views in cell 2,-10 show torn mushroom cap seams. Prior cell 5,-10 report retained; exact models and closure repair pending.
- Reported with v0.0.42-dev1 at 2026-10-17 11:49 +0300: maintainer on TG with a frame at cell 1,-10: the mushrooms at Vivec are still open

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in an unknown version |
| Where | Vivec exterior cell 5,-10, global 46983,-81758,835 |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.39-rc1, v0.0.42-dev1 (last seen) |
| Severity | high: Repeated maintainer-visible failure in RC1; exact repair remains unverified. |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [RC1 maintainer evidence, 13 October 2026](#rc1-maintainer-evidence-13-october-2026)
- [Location confirmed, 16 October 2026](#location-confirmed-16-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Maintainer screenshot shows a bright opening along a giant mushroom cap in Vivec. The maintainer suspects mesh reduction; cause is unconfirmed.

## Where

HUD: exterior cell 5,-10; global 46983,-81758,835; local 3553,2600,208; heading 071, pitch -27; time 08:36. Rounded HUD readings. Exact installed build, model and reference unknown.

## How it happened

Cause found 17 October 2026 (v0.0.42-dev2 line). The mushrooms the maintainer pinned in v0.0.42-dev1 are
`flora_emp_parasol_03` (references 172013, cell 2,-10, and 172126, cell 2,-12; read from the Vivec city frame's
scenery index at the three pinned hit points). There is no separate banner model: the "banners" are the mesh's own
hanging vine quads. The cap is several materials (`Tx_emperor_parasol_01/02/03`) joined at their rims. The
original has no two-sided draw flag (no NiStencilProperty) and no submesh is dropped.

Every CHIM area except Seyda Neen (Vivec, Balmora, the region cells) converts its scenery through the town model
profile (`tools/chim/build.py` `prepare_area` -> `town_regions.town_model_profile` -> `visual_profile`). That profile
gives every `flora_` mesh a target of 120 triangles and the default reducer, which reduces each material on its own
and also collapses rim edges, so each cap material pulled back from its neighbour: the same mechanism as GEO-01 and
MESH-LOD-OPEN-SEAMS-33. The open-world and Seyda path (`prepare_world_scenery.scenery_profile`) keeps the shared
seams, which is why the mushrooms there were closed; its docstring wrongly said the town frames used it too. So it
was never only Vivec: before the fix, the seam audit measured torn seams or rims on 1,317 placements of 14 mushroom
models in the town/CHIM-area space (parasol 01/02/03 191 + 238 + 271, the Telvanni mushrooms 48 + 76, the shelf
fungus 11, Bitter Coast mushrooms 01-05 482). The audit already listed the five worst as "known" under
MESH-LOD-TORN-MESHES-33, so the gate let them pass.

## Why it was not caught

Unknown until exact payload and audit receipts are bound. Conversion success does not establish closure from this native view.

## Reproduction

Load the reported location and look up at the cap with the recorded heading and pitch. Bind engine, world and reference identity first. Repeatability and normal movement state unverified.

## Repair

17 October 2026, at the shared layer: `town_regions.visual_profile` reduces every mushroom cap mesh
(`flora_emp_parasol_`, `flora_t_mushroom_`, `flora_bc_mushroom_`, `flora_t_shelffungus_`; `MUSHROOM_CAP_PREFIXES`) with
the boundary-locked reducer (`lock_boundaries`: rims and seams stay exactly where the source has them, only inside
edges collapse). That one profile serves the legacy town builder, the CHIM model builder and the seam audit. Cost:
parasol 01/02/03 135/132/138 -> 160/163/170 triangles, the others +0 to +9; about half of what the open-world
seam-keeping profile costs (283-328). The seam gate now treats these models as closed in the town space
(`config/seam-audit-known.json` "closed" rows with a space): any torn seam or rim fails the build.

Island-wide seam audit with the fix (all 3,775 placed meshes, 666 reduced mesh/path pairs): 0 failures; every
mushroom model 0 % torn seam and 0 % torn rim in the town space (before: 1,317 placements on torn variants, after: 0).
The open-world profile of the parasols still tears free rims (0.22-0.60) without tearing seams; it is the Seyda and
legacy path and was left as it is.

Earlier, ruled out 16 October 2026: Vivec's detail budget (`vivec-deep`,
`config/chim-detail-budgets.json`) lists no mushroom or banner mesh, so its unaudited reductions
(CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36) are not the cause. Leading suspect now: the cap and the draped banner as
separate materials whose vertices are not shared along their edge. Next (v0.0.42 plan 2.3): the exact mesh and
placement identified, the seam audit run on its converted variants, compared with the original at the same pose. Inspect original and converted geometry before choosing a repair. Read existing AmiQuake rendering machinery before any renderer change.

## Verification

Original maintainer screenshot inspected and preserved. Matched OpenMW/native captures and topology comparison pending. The pinned full-game build predates this report and contains no repair for it.

## Prevention

Cover the identified model's material seams and reported viewing direction, retaining exact packaged-model and original-game comparison evidence.



Mesh checklist for Vivec giant mushrooms (maintainer follow-up, 12 October):

- [ ] Inventory every large-mushroom model and placement in Vivec, including town-specific variants.
- [ ] Bind the two reported views in cell 5,-10 to exact source and packaged model identities.
- [ ] Compare material boundaries and shared rims before and after reduction; check winding and cap closure.
- [ ] Check every actual conversion profile used by the Vivec and regional build routes.
- [ ] Capture matched OpenMW/native views from above, beside and below the caps.
- [ ] Verify the repaired models in the extracted playtest package, with memory and frame-time measurements.

Second screenshot: global 47007,-81794,835, heading 069, pitch -38, time 09:44, same cell. It shows the same opening from another angle. The HUD shows the v0.0.38 series; exact suffix and binary hashes remain unverified. The maintainer's explanation that a Vivec-specific variant escaped the earlier island repair remains a hypothesis until model binding.


12 October diagnostic: nearest mushroom candidate is reference 171483, flora_emp_parasol_01, scale 1.49, in cell 5,-10. Its position agrees with the reported viewing direction, but exact installed-payload binding remains pending. The preserved dev2 CHIM model has 123 faces and 38,248 bytes at this scale. Using the retained town scenery and unchanged diagnostic helpers, the town profile reduces 428 source triangles to 135 and fails sampled material-boundary matching. A boundary-lock trial yields 160 triangles and passes that sampled check. This is not a repair acceptance or a native performance result. The legacy world scenery explicitly preserves mushroom shared seams; the town profile tested here does not. The model is already listed in the town seam audit under MESH-LOD-TORN-MESHES-33.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-191710`: SHA-256 `ba11a8c78d05dc88dfb17459ec15729916a8adb882ad79553e527efb22d99839`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-191925`: SHA-256 `70c2351f5d3d94f81b68192544c981323be3596ad8f9fd779197fd4168919688`. Screenshot association checked; no repair or behavioral acceptance inferred.

## RC1 maintainer evidence, 13 October 2026

The original images remain private. Rounded HUD readings are location aids,
not exact source/package bindings or proof of motion.

- `OWNER-20261013-214618`, SHA-256 `b4c3b49b91d1d9cb2d9131b78b59c1b18aadcdbaf560b647dbd23a62cf3ea3f3`: Large mushroom cap has an open band along its rim. HUD RC1, cell 2,-10; global 21519,-78784,184; local -2812,3343,46; heading120, pitch-35, game time11:04.
- `OWNER-20261013-214647`, SHA-256 `26fdc285e6b41b67d57c523b76d7375dfb96478a6a91016f26a63a347a98f0f5`: Two large mushroom caps show open seams. HUD RC1, cell2,-10; global20788,-78832,173; local-2994,3331,43; heading356, pitch-49, time11:31.
- `OWNER-20261013-214728`, SHA-256 `f120705fd04455c475ec9d974dca1840f6e38f3520c52991e92d980596ec68de`: Large cap has a broad opening along its top/rim. HUD RC1, cell2,-10; global19845,-77331,425; local-3230,3707,106; heading136, pitch-27, time11:50.

## Location confirmed, 16 October 2026

The generic giant mushroom caps were repaired long ago. This report is about two specific giant mushrooms near
Vivec's entrance (cell 2,-10, the 13 October views) that have banners draped from them; those two still show open
bands. No change to the giant mushroom profile of towns: the next step is to bind the placements at the reported
poses to their exact models (the banner may be part of a Vivec-specific mesh or a separate static), compare with
the original game at the same poses, and repair only those meshes.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
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
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

<!-- END GENERATED CATEGORY -->
