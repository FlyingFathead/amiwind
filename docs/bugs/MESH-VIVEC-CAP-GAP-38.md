# MESH-VIVEC-CAP-GAP-38: Vivec giant mushroom cap opening

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in an unknown version |
| Where | Vivec exterior cell 5,-10, global 46983,-81758,835 |
| Reproduction | once |
| Duplicate of | no |
| Persists in | unknown |
| Severity | medium: Visible opening in scenery; extent across placements unknown |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

## Symptom

Owner screenshot shows a bright opening along a giant mushroom cap in Vivec. The owner suspects mesh reduction; cause is unconfirmed.

## Where

HUD: exterior cell 5,-10; global 46983,-81758,835; local 3553,2600,208; heading 071, pitch -27; time 08:36. Rounded HUD readings. Exact installed build, model and reference unknown.

## How it happened

Unknown. Inspect source mesh, material seams, reduction, winding and packaged identity. GEO-01 is a similar historical repair, not proof of a shared cause.

## Why it was not caught

Unknown until exact payload and audit receipts are bound. Conversion success does not establish closure from this native view.

## Reproduction

Load the reported location and look up at the cap with the recorded heading and pitch. Bind engine, world and reference identity first. Repeatability and normal movement state unverified.

## Repair

None established. Inspect original and converted geometry before choosing a repair. Read existing AmiQuake rendering machinery before any renderer change.

## Verification

Original owner screenshot inspected and preserved. Matched OpenMW/native captures and topology comparison pending. The pinned full-game build predates this report and contains no repair for it.

## Prevention

Cover the identified model's material seams and reported viewing direction, retaining exact packaged-model and original-game comparison evidence.



Mesh checklist for Vivec giant mushrooms (owner follow-up, 12 October):

- [ ] Inventory every large-mushroom model and placement in Vivec, including town-specific variants.
- [ ] Bind the two reported views in cell 5,-10 to exact source and packaged model identities.
- [ ] Compare material boundaries and shared rims before and after reduction; check winding and cap closure.
- [ ] Check every actual conversion profile used by the Vivec and regional build routes.
- [ ] Capture matched OpenMW/native views from above, beside and below the caps.
- [ ] Verify the repaired models in the extracted playtest package, with memory and frame-time measurements.

Second screenshot: global 47007,-81794,835, heading 069, pitch -38, time 09:44, same cell. It shows the same opening from another angle. The HUD shows the v0.0.38 series; exact suffix and binary hashes remain unverified. The owner's explanation that a Vivec-specific variant escaped the earlier island repair remains a hypothesis until model binding.


12 October diagnostic: nearest mushroom candidate is reference 171483, flora_emp_parasol_01, scale 1.49, in cell 5,-10. Its position agrees with the reported viewing direction, but exact installed-payload binding remains pending. The preserved dev2 CHIM model has 123 faces and 38,248 bytes at this scale. Using the retained town scenery and unchanged diagnostic helpers, the town profile reduces 428 source triangles to 135 and fails sampled material-boundary matching. A boundary-lock trial yields 160 triangles and passes that sampled check. This is not a repair acceptance or a native performance result. The legacy world scenery explicitly preserves mushroom shared seams; the town profile tested here does not. The model is already listed in the town seam audit under MESH-LOD-TORN-MESHES-33.


## Owner evidence reconciliation, 13 October 2026

The following owner screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-191710`: SHA-256 `ba11a8c78d05dc88dfb17459ec15729916a8adb882ad79553e527efb22d99839`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-191925`: SHA-256 `70c2351f5d3d94f81b68192544c981323be3596ad8f9fd779197fd4168919688`. Screenshot association checked; no repair or behavioral acceptance inferred.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [CHIM-STRIDER-SCALED-SEAMS-36](CHIM-STRIDER-SCALED-SEAMS-36.md): Seyda Neen's silt strider (scale 0.89 variant) still shows open seams; Balmora's (scale 1.0) is closed
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
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

<!-- END GENERATED CATEGORY -->
