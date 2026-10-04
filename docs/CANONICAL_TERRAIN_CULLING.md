# Canonical exterior terrain culling

The host pass consumes the owner's local, authored LAND NPZ directly. No assets
are shipped with these tools. Water is never an occlusion receiver. Negative
LAND heights are the actual seabed; there is no invented bottom cutoff.

Standalone diagnostic:

```text
python tools/cull_bsp_terrain.py original.bsp --out fresh/candidate.bsp --canonical-land-source terrain-source.npz --canonical-origin X Y Z
```

The coordinate contract is `compiled XYZ = source XYZ * 0.25 - origin XYZ`.
An explicit origin is required. Source cell adjacency and array validity are
checked before clipping. Missing LAND coverage raises an error. The original
input is not overwritten, and an existing render-pool candidate cannot be reused
as the unculled seed.

Seyda region conversion accepts `--canonical-land-source`. Its origin is derived
from `config/seyda_area.json`: source centre multiplied by source scale, with Z
origin zero. Enabled conversion validates the source before creating a build.
It never substitutes local compiled brushes for the required source NPZ.

Existing boolean and overlap precedence remains: explicit CLI force, BSP,
subcell, cell, global default. Overlap is finite and nonnegative, in compiled
units; the default is 0.5. `--terrain-visual-cull false` retains the original byte
path without requiring canonical data.

Static geometry is transformed per placement before clipping. Identical kept
fragments are shared through one auxiliary render pool; each original entity
binds relative `aw_render_ranges`. Worldspawn identifies the model using
`aw_render_pool`. Original entity transforms and collision hulls remain intact.
Crossing lightmapped fragments crop each original style's 16-unit sample grid.
Float32 zero-area fragments are removed before references are remapped.
World sky render faces are omitted; their initialization texture resource is
retained until the shared-sky resource path supplies it independently.

## Current acceptance gate

The coherent 049/050 Seyda batch passes bounded host validation, and the assembled
V3 image is undergoing independent native testing. All 64 maps passed a strict
serialized second cut covering 2,129,800 placed polygons, with zero further
changes or winding-preservation failures. Preservation alone did not check the
renderer convention: the subsequent native test exposed reversed LAND edges.
The 051 repair reverses 442,861 LAND loops and changes only signed surfedge
ordering. Other BSP lumps, collision, materials and file sizes remain unchanged.
A matched-camera diagnostic and initial combined-engine town replay restore
brown textured ground. These bounded views do not certify all maps or routes. Twelve distinct NPCs pass identity/support
checks; 1,696 standing probes over the actual town cores plus a 32-unit guard
pass, with maximum measured height error 0.00015736 compiled units.

Seven maps required a float32 serialization correction: 13 replacement faces
add 1,776 bytes. Actual serialized coordinates are re-clipped with the same
0.5 overlap and 0.00002 boundary tolerance; no tolerance or coverage expansion
is used. Collision, PVS, actors and unchanged faces remain preserved. The 35
focused host checks pass. The 29 older probes outside mapped town coverage remain
historical diagnostics; they do not demonstrate a current defect or certify a
native route. Wider-world coverage and native appearance/ground/NPC traversal
remain open. This is bounded experimental source work, not global certification.

Use the Polycount Inspector to examine the serialized BSP with all hiding and
terrain preview disabled. Its auxiliary render-pool support displays the stored
candidate, rather than pretending that viewer filtering constitutes a bake.


### Historical canonical render/collision repair experiments

The first exact surface reconstruction used a separate diagnostic render model
while retaining coarse world collision. This does not repair physical terrain:
rendering and collision must consume the same authoritative canonical planes.
The new `canonical_terrain_brushes` helper generates those planes directly from
authored LAND and coalesces only connected convex regions with identical affine
plane and material. It rejects missing coverage and never uses water as ground.

A bounded structural-world trial produced 19,136 world faces and 38,425 stock
clipnodes from 8,192 authored triangle prisms; VIS rejected a leaf with too many
portals. Exact coalescing reduced this to 5,081 prisms but still produced 19,082
world faces and 38,333 clipnodes, with the same VIS failure. Compiling solid-detail
terrain allowed VIS and matched point collision at sampled canonical contacts,
but the subsequent composed candidate exceeded the hard static leaf-link limit.
These attempts are rejected, not shipped terrain repairs or measured savings.

The subsequent bounded experiment separates canonical terrain into one supported
inline brush model with matching collision and surface graphics, using a small
structural visibility world. This changes the original visibility representation;
native scene submission and edge/surface capacity remain acceptance gates. No
whole-world terrain acceptance follows from one map.

### Historical candidate034 measurement — 4 October 2026

Candidate034 passed an actual second cut of **45,368 serialized placed polygons**
with zero changed polygons, zero winding failures and zero measured area loss.
The final source snapshot passed 46 focused host tests. Those checks include
float32 shoreline grid/diagonal constraints and the bounded atomic-triangle
fallback. The serialized geometry audit found no invalid, zero-area or sky render
faces. It retained 472 original inline collision hulls exactly; 289 canonical
standing probes had a maximum absolute error of 0.000109 compiled units.

An independent water comparison checked the final polygons against unmerged
canonical pieces. Both water sides preserve 2,153,767.8355856 square units of
visible water to within 0.000001 square units, with no missing visible polygon.
Water height, UV vectors and source winding remain unchanged. Float32 shoreline
adjustments affect only the submerged contact margin; their net area change is
about 0.010167 square units per side. Repeat stability alone is not permission to
erode visible water.

This ledger compares the original uncropped BSP, the **current007** shared-sky
baseline and candidate034. Current007 is not the earlier CONTROL002 experiment.
The storage total includes the BSP and exactly one external 32,768-byte shared
sky resource where applicable. The original's embedded resources are already
inside its BSP. Other assets and whole-game storage are outside this comparison.

| Version of sn045 | BSP bytes | External sky bytes | Included storage bytes | Stored faces | Modeled peak map bytes |
|---|---:|---:|---:|---:|---:|
| Original before culling | 4,550,392 | 0 | 4,550,392 | 26,190 | 6,487,584 |
| Current007 shared-sky baseline | 4,496,556 | 32,768 | 4,529,324 | 26,021 | 6,424,480 |
| Candidate034 canonical terrain | 5,474,876 | 32,768 | 5,507,644 | 32,500 | 7,426,528 |
| Candidate035 | pending | pending | pending | pending | pending |

Candidate034 is **not a net optimization**. It adds 957,252 included storage
bytes and 6,310 stored faces against the original, or 978,320 bytes and 6,479
faces against current007. Its modeled map peak also rises by 938,944 bytes
against the original and 1,002,048 bytes against current007. Disk bytes, stored
faces and modeled heap allocations are separate measurements.

These rows use the ABI of engine
`f19ea3089bfb73b3bea801334f51a76a722c54316f471d8d1271807347f3d2d2`.
An actual normalized-source compile matched that executable byte for byte and
bound all 205 engine source files. Candidate034 includes the exact 11,536-byte
charge for 145 separately allocated render-range records containing 383 ranges.
Its static placements require 140 leaf links within the existing 8,192-link
base, whereas the original and current007 require 8,612 links and one overflow
page. The peak estimate leaves 962,080 bytes after the 3 MiB baseline in the
11 MiB heap, so it exceeds the additional 2 MiB safety allowance by 1,135,072
bytes. That remains a private-test warning needing adjustment; actual allocation
failures remain errors. It is not a measured runtime free-memory result.

The BSP identities are SHA-256:

| Input/output | SHA-256 |
|---|---|
| Original | `19454bba203ddc0d3fd3a2c521a4d34dc63b51c7da4206b55d52f5649fb92480` |
| Current007 | `83f4f3d3300ef66ba8572fa9697053897fc9b377bfc56f5784b8d51b94776d44` |
| Candidate034 | `083040730dcd41112f3015e2c8604b08eb588dad33138b30bab80596c33dbd5d` |

The private receipts bind those bytes, canonical input identity, imported culling
source hashes, tests and ABI accounting. They retain the failed earlier attempts
and distinguish each diagnostic image from its terrain candidate.

**Historical status: candidate034 was not accepted; candidate035 was then pending.** Native008, which
contained the earlier candidate030, exposed actor-support problems after terrain
collision was replaced following actor placement/support baking. Direct
`map sn045` entry also bypasses the normal region ownership catalogue. These
findings cannot be turned into a candidate034 gameplay pass by its host checks
or by a successful filesystem readback.

Resident overlap copies in sn045 belong to other owner cores. The existing
support fitter uses each actor's owner BSP and requires identical overlap
placements; independently moving a copy in this one diagnostic map would break
that contract. The next historical candidate was required to establish support on the intended entry path
while retaining actor identities and consistent owner placement. Erene
Llenim remains owned by sn011 and present in the overlap catalogue. Her position
is outside this bounded sn045 terrain trial; keeping her does not require
expanding this trial's coverage or relocating her. Final actor contact, ordinary
region entry, terrain traversal, workload and appearance remain native gates.

### Historical regional blocker in candidate034 — 4 October 2026

Candidate034 cannot be promoted as an isolated sn045 replacement. Its owner
core spans `(240, 241.125)` to `(352, 318.75)`. Comparing canonical point-hull
ground against the unchanged neighboring maps at 33 samples per edge found:

| Neighbor | Join | Maximum absolute height mismatch, compiled units |
|---|---|---:|
| sn044 | west | 4.39447 |
| sn046 | east | 2.92365 |
| sn040 | south | 4.05001 |
| sn049 | north | 0.0000126 |

The first three joins were blocking geometry/collision inconsistencies in that isolated candidate. Owner
cores and overlap copies must use coherent canonical terrain and actor support;
the five affected resident copies in sn045 belong to sn020, sn032, sn035 and
sn054. Local movement of only those copies would violate the existing shared
placement contract. Erene's sn011 ownership remains intact and does not require
expanding this bounded trial.

A feasibility compile of the largest affected owner, sn054, produced 43,907
final point-hull nodes against the 32,767 limit. Exact deduplication still left
36,972, so that representation does not fit. A private compact exact-heightfield
prototype has since measured 17,450 nodes and 6,969 planes, with zero mismatches
in 106,896 comparisons against the compiled source's solid contents. Those
point comparisons do not establish a serialized combined BSP, standing collision,
matching-ABI memory or native acceptance; those gates remain pending.
Reducing terrain quality, changing canonical heights or eroding visible water
is not an accepted way around the limit. The bounded native009 clock/sky/runtime
pass does not waive these regional blockers; current coherent host results supersede this isolated-map diagnostic, while native acceptance remains pending.
