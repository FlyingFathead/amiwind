# What are rocks? — terrain coverage and conversion workflow

Findings from the owned base master and NIFs, 29 September 2026, v0.0.23-dev3.

<!-- contents start -->
## Contents

- [LAND is only one part of the landscape](#land-is-only-one-part-of-the-landscape)
- [Silt Strider case: inclusion was correct, orientation was wrong](#silt-strider-case-inclusion-was-correct-orientation-was-wrong)
- [Low-poly policy](#low-poly-policy)
- [Required workflow](#required-workflow)
- [Native evidence](#native-evidence)
- [dev4 follow-up](#dev4-follow-up)
- [v0.0.27-rc2: Rocks and Mushrooms](#v0027-rc2-rocks-and-mushrooms)
- [v0.0.38 investigation: repeated shoreline rock gaps](#v0038-investigation-repeated-shoreline-rock-gaps)

<!-- contents end -->

## LAND is only one part of the landscape

Morrowind LAND records provide a height field and its ground materials. They do
not contain the entire visible landscape. CELL references place separate NIF
meshes over and into that ground: boulders, outcrops, cliffs, building foundations,
platforms and other structural scenery. Those meshes can cover a coarse slope or
hide a join. A correct heightmap alone does not guarantee an intact-looking hill.
Never seal a reported opening with invented terrain until the source placements,
transforms, render visibility and collision have been inspected.

In this export the rock base objects are **STAT** records, placed through CELL
references with position, rotation and scale. There is no separate ROCK record
category. The base ID and MODL filename identify useful families, but matching a
name is a conversion policy, not proof that an object is decorative or removable.

| Identified family | Examples in this area | Observed source triangles per mesh |
| --- | --- | ---: |
| Terrain rocks | `terrain_rock_bc_*`, `terrain_rock_ai_*`, `terrain_rock_rm_*`; `meshes/f/Terrain_rock_*.nif` | 70–180 |
| Nordic rock/foundation pieces | `ex_nord_rock_01/02`; `meshes/x/Ex_nord_rock_*.nif` | 30–35 |

Directory `f/` alone is not a foliage classifier. Terrain rocks there must not be
removed by a broad vegetation filter. Deleted references remain excluded; keep
the original scale and all three rotation components.

## Silt Strider case: inclusion was correct, orientation was wrong

The reported camera is local `XYZ 263 463 19`, yaw 352, pitch -17. The large rock
covering this part of the port hillside is `terrain_rock_bc_18`, reference 251560,
from exterior cell (-2,-9). Its original placement is approximately
(-8536.042, -69810.516, 417.597), scale 2. Its local origin is
(681.990, 467.371, 104.399); rotations are approximately
(5.783185, 6.083185, 5.016813) radians. It was already in both the exported scenery
and final BSP: simply adding more rock references would not repair this defect.

The converter composed rotations as Rz × Ry × Rx. TES3 placement here requires
Rx(-x) × Ry(-y) × Rz(-z) for column vectors, the same convention already corrected
for the intro collision boxes. A yaw-only test cannot catch this error. The wrong
order tilted the rock above the LAND surface like a floating roof, exposing the
background underneath. With entities hidden, native captures showed the intact
underlying LAND slope; with the corrected rock transform, the gap closed.

Runtime still applies entity yaw. The host now bakes the inverse of that yaw
against the full authored transform, so the composed result is correct. Tilted
placements with different yaws no longer incorrectly share a bake. Geometry,
texture coordinates, collision pieces and selection bounds use the same transform.
No hand-positioned filler and no increased draw distance were required.

## Low-poly policy

Terrain rocks now use a host-side **64 visual-triangle target per source mesh**,
retaining originals when already below it. Reduction respects separate material
components, so the target is not an unconditional hard cap. Tiny disconnected
pieces may need extra triangles. Textures remain 64×64; original geometry still
supplies the approximate collision conversion. Small Nordic pieces remain at
30–35 source triangles. This is a static bake, with no runtime LOD switching.

The rebuilt exterior has 49 distinct terrain-rock bakes: 3,119 BSP faces versus
5,179 before reduction. The port rock drops from 174 source triangles to 64 visual
triangles. Individual reduced rock bakes use 63–65 BSP faces (UV/material splits
can differ from triangle counts).

Rock coverage is structural. Inspect the reduced silhouette and the LAND overlap
at the source placement, especially for large scaled rocks. If a reduction exposes
a seam, preserve the needed boundary or use a documented per-model exception;
do not hide it by increasing fog. Count final BSP surfaces/edges as well as input
triangles: UV splitting may create additional rasterizer work. Native visibility,
walkability, memory and frame-cost checks decide whether the reduced asset ships.

## Required workflow

1. Record camera XYZ, yaw, pitch, current map and version; retain a native capture.
2. Inspect source LAND and nearby CELL references, including meshes whose bounds
   intersect the area even when their origins are outside it.
3. Resolve STAT/ACTI/DOOR model paths and verify source → exported reference → BSP
   presence. Inspect separate visual and authored collision geometry.
4. Compare a terrain-only view, full scene, fog-off and culling diagnostics. A
   disappearing wall is not automatically a missing mesh or missing ground.
5. Validate compound rotation, scale, winding and material coordinates before
   simplification. Rebuild geometry and collider/bounds together.
6. Apply the low-poly budget and repeat the original camera plus nearby angles;
   walk the route and check collision independently. Record measured counts,
   exceptions, evidence and remaining uncertainty in the checkpoint.

The separate Vodunius-house hole was a renderer ordering defect: far-culled world
leaves could still supply stale order keys to clipped brush fragments. The fix
makes world, brush-fragment and entity-split traversal agree on the far plane.
It did not require changing the house mesh, disabling culling or importing rocks.

## Native evidence

| Before: wrong compound rotation | After: corrected, 64-triangle visual rock |
| --- | --- |
| ![Rock lifted above the LAND slope](images/amiwind-v0.0.23-dev3-rock-before.png) | ![Rock covers the slope at the original placement](images/amiwind-v0.0.23-dev3-rock-after.png) |

FS-UAE captures at the reported port position, cropped only to the game viewport.
The displayed repair is verified at these views. Full port walking/collision
acceptance and other rock seams still require inspection; a visual closure does
not certify every collider.

## dev4 follow-up

The owner confirms the port rock fix in dev3. The later missing rider was an
entity spawn-order problem: actor floor traces ran before the platform brushes
were linked. The cut-off town tree was a signed sprite-depth comparison against
the background. Neither required changing the accepted rock mesh or terrain.
See [dev3 feedback trials](FEEDBACK-v0.0.23-dev3.md) for the discarded culling
experiment and the final fixes. Preserve structural rocks when optimizing LAND.

## v0.0.27-rc2: Rocks and Mushrooms

The world overlay uses the existing topomap and authored exterior placements:
37,960 rocks and 816 giant mushrooms, covered across 2,526 retained regions.
Town sub-cell maps remain deliberate frame-cost controls. Small collectible
mushrooms are excluded. See [candidate scope](RELEASE-v0.0.27-rc2.md).

The giant-mushroom playtest exposed another structural reduction problem.
Original cap sections use different materials but share joining positions.
Simplifying those sections independently moved or removed rim vertices, opening
visible gaps. All five giant-mushroom models were checked. Rc2 preserves joined
sections and their original UVs; rock reduction is unchanged. This conservative
exception increases mushroom triangles while retaining the source silhouette.
Final BSP budgets passed; corrected-image visual and frame-cost acceptance is
still required. Boundary-constrained reduction is a future optimization, not a
reason to ship open caps. See GEO-01 in the [bug journal](BUG_JOURNAL.md).

## v0.0.38 investigation: repeated shoreline rock gaps

On 12 October 2026 the owner reported recurring open rock sections in
v0.0.38-dev2, across Ashlands and Sheogorad shoreline cells. The owner reports
that this predates dev2; the first affected version remains unknown. See
[WORLD-SHORE-OPEN-GEOMETRY-38](bugs/WORLD-SHORE-OPEN-GEOMETRY-38.md).
Repeated shapes suggest a shared conversion problem rather than an isolated
missing placement, but exact model/view matching is still required.

The legacy world-scenery profile sets a 64-triangle target and preserves shared
seams for giant mushrooms, but not rocks. Its default reducer simplifies
material components independently. This is the same class of risk described in
[MESH-LOD-OPEN-SEAMS-33](bugs/MESH-LOD-OPEN-SEAMS-33.md); that report's Silt
Strider repair does not establish acceptance for all rocks.

A read-only diagnostic over 153 rock-named models in the current world-scenery
packet found that 129 lost at least one original material-rim vertex under the
production profile. The existing boundary-locked reducer retained every measured
rim vertex in all 153 models. Total visual triangles rose from 9,584 to 10,208
in this model inventory; these are not final map faces, memory or frame timings.
The two nearby Ashlands models `terrain_ashland_rock_02` and
`terrain_ashland_rock_05` changed from 63 triangles each to 90 and 82 respectively.
Production behavior has not been changed by this diagnostic.

Rim-vertex loss alone does not prove an open surface: a removed vertex can lie
on an unchanged edge. The next check must compare the authored joining curves
and converted boundaries, including material and UV splits. Preserve intentional
source openings; do not require every original mesh to be a closed solid or add
invented filler. Account for every rock type, with explicit exceptions rather
than silently testing only passing models. Match the affected reference,
transform and view in OpenMW and the native game, then check final map budgets,
collision and measured performance before accepting a repair. The existing
AmiQuake brush-model renderer uses plane-side/backface tests; disabling those
tests is not an established repair for changed geometry.

A subsequent reusable diagnostic compares material-boundary curves in model
space, sampling edge endpoints and midpoints in both directions. Its regression
cases distinguish a removed collinear vertex from a displaced boundary, detect
a missing material part and retain intentional open source geometry. Applied
to the same 153-model inventory, 129 production reductions have sampled boundary
drift; boundary locking has none at the measured samples. This is stronger than
vertex retention alone, but does not exhaustively test surface interiors, winding,
UVs or final BSP/native output. It remains an offline diagnostic, not an accepted
universal repair.

CPU and RAM efficiency remain acceptance requirements. The model inventory's
triangle increase cannot predict the cost of repeated placements in a visible
scene. Measure the same native view before and after a proposed repair, including
normal-speed frame time, map storage and resident memory. Reuse the existing
renderer and cache; preserving seams does not justify an unmeasured extra pass.

The nearby cracked-ground appearance is a separate texture question. The legacy
terrain converter already imports original LAND materials as 32 by 32 indexed
textures. Trace the original material, UV scale and downsampling before adding
an overlay. Four mip levels contain 1,360 texel bytes at 32 by 32 and 5,440 at
64 by 64, excluding headers and surface-cache storage. AmiQuake's existing
`D_CacheSurface` caches lit surfaces by mip level; source texture bytes alone do
not establish runtime cost. No texture-size change or added terrain layer has
been accepted by this investigation.
