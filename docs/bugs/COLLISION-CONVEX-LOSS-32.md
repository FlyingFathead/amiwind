# COLLISION-CONVEX-LOSS-32: Convex collision proxies lose and invent authored surfaces

## Status: 8 October 2026

Open. Found while tracing [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md). Present in every
release that converts meshes with `collision_parts` (towns, open-world scenery).

## Symptom

The convex collision proxy of a mesh can be far from the authored collision surface in both
directions:

- **Lost surface:** each hull is built from at most 14 extreme points (one per sample
  direction), so authored triangles can lie outside it. Measured as the largest distance of a
  source vertex or triangle centre outside its own hull: `ex_vivec_c_02` 106.9 units,
  `ex_vivec_c_04` 97.1 (the Redoran canton top under Ordinator 241614 had no collision),
  Balmora `ex_velothi_temple_01` 31.9, `ex_hlaalu_buttress_05` 17.0, rocks up to 24.3, trees up
  to 23.2.
- **Invented solid:** groups of four or fewer triangles are accepted whatever their error, so
  hulls can close authored space. Deepest closed space: `ex_vivec_c_04` 34.7, Balmora rocks up to
  18.0 (`terrain_rock_wg_13`), trees up to 8.1.

## Where

`tools/mesh_geometry.py` `collision_parts` (14-direction support samples; split only above four
triangles and below depth 8). The module docstring calls this "can miss small details"; the
measured misses are not small.

Unaffected: meshes on surface collision (Balmora's hand-made architecture list, interiors except
rocks, and since VIVEC-ARENA-ACTORS-32 every exterior architecture mesh whose proxy closes more
than a step).

## How it happened

The proxy trades fidelity for clip-node count; the error test only measures triangle centres
inside the hull (invented solid), never surface left outside it, and small groups skip it.

## Why it was not caught

No check compares the proxy with the source surface. The actor gate and the walkability scans
measure the converted collision only.

## Reproduction

For each model of a town's scenery index, run `collision_parts` on its collision mesh and
measure, per hull, the largest distance of its source points outside the hull (lost) and the
`error` value (closed). Measured on the dev1 Balmora and Arena work directories.

## Repair

Not yet. The exterior-architecture part that blocked the Arena residents is repaired by the
surface rule of VIVEC-ARENA-ACTORS-32 (closed space deeper than the step height). Lost surfaces
and organic props (rocks, trees) are unchanged: a general change would alter Balmora and every
open-world map in the last release on the legacy engine. Candidates: build hulls from all points
of a group, split small groups that exceed the tolerance, and add lost surface to the error test,
then re-measure clip-node and heap budgets (the CHIM world format is the natural place).

## Verification

Pending.

## Prevention

Pending: a per-model fidelity report (closed and lost distance) in the conversion reports, with
a limit for architecture.
