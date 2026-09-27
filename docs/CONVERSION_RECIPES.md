# Reusable conversion recipes

AmiWind is a host conversion pipeline plus an Amiga runtime. The goal is to
repeat a documented build from user-provided inputs, not to repair each scene
manually after export. Owned input, generated intermediate files, images and
performance evidence stay outside the source repository.

## Reproducible stages

`build.sh` records a versioned build receipt with the recipe ID, hand mode,
commands, input/source/tool SHA-256 checksums, tool paths, stage logs and timings
under the external workspace. Each named run is immutable; failures preserve
completed earlier stages. The AGA path now includes the prison interior after
terrain, scenery, NPCs and hands, before compiling the runtime and HDF.

| Stage | Reusable work | Current bounded recipe |
| --- | --- | --- |
| Read | ESM cells/references, BSA meshes and textures | Base Morrowind; fixed Seyda Neen coverage |
| Resolve | Object IDs, transforms, materials, complete assemblies | Arrival ship assembly explicitly configured |
| Geometry | Same-plane merging, optional component/material LOD, UV patches | Selected ship hull LOD; ordinary scenery retained |
| Collision | Standing hull profile, convex proxies, hollow surface prisms | Hollow collision selected for the prison shell |
| Lighting | Offline scalar ambient and bounded lamp falloff | Prison AMBI/LIGH; no shadows, flicker or coloured lights |
| Actors | Body-part assembly, clothing, sampled animation | Three town NPCs and Nord unarmed first person |
| First person | Same poses to MDL and optional opaque sprite spans | `--hands 3d` default; `--hands sprites` experiment |
| Links | Authored door source/destination coordinates | Prison ship and exterior hatch only |
| Pack | Bounded BSP/data formats, music blocks, RDB/FFS HDF | One resident scene; continuous music identity |
| Verify | Synthetic tests, binary/filesystem checks, native recordings | Pinned emulator/ROM/config and versioned evidence |

## Generalise through recipes, not silent guesses

Keep source cell coordinates (8192-unit exterior cells) separate from smaller
runtime chunks and the current 0.25 world scale. A future scene recipe should
name its source cells, included assemblies, spawn, links, lighting policy,
geometry/collision variants and hard budgets. The host reader and exporters
already accept reusable inputs; the full guided build remains a **two-scene
prototype**, not an arbitrary-cell conversion promise.

New recipes must report included and omitted object IDs with reasons. Unknown
records should be visible in the report. Do not silently replace interactive
objects with decoration. Limits such as 16-bit BSP node references, runtime
model slots, visible edges/surfaces and resident heap must fail the conversion
with an actionable report, rather than producing a broken image.

## Controlled comparisons

Keep the current conversion as variant A. Write variant B to a different output
directory and record both recipes and input hashes. Use identical position,
heading (`DEG`), pitch, draw distance, hardware settings and scripted route.
Compare appearance, collision, loading time, steady frame time, RAM and audio
underruns. Record failures and rejected experiments too.

Planned comparisons: separate planks versus a textured joined deck; 3D hands
versus complete first-person sprite sets; distant building geometry versus
baked backdrops. These are experiments, not permission to flatten the whole map.
A sprite set must cover the selected race/body, equipment and required motions;
missing coverage keeps the 3D path. Race may be stable during play, but equipment
and animation change. Cache/invalidation must use the complete appearance key.

## Lessons captured so far

- A connected hollow collision shell can become a solid room when enclosed by
  convex proxies. Preserve its wall/floor surfaces as thin prisms instead.
- Long same-side collision-tree chains consumed task stack. The runtime now
  descends those chains iteratively; a 24,000-node synthetic test uses a 256 KiB
  host stack. Segment splits still recurse and need bounded input topology.
- Degenerate/constant UVs cannot be inverted for lightmap positions. Bake a
  face-centre value for those surfaces; reject oversized lightmaps.
- A source door destination may place the standing head through its hatch.
  Search downward over a bounded distance for the receiving floor; never assume
  copied coordinates alone are a safe spawn.
- Collision size and camera eye height are separate. Base humanoid collision
  dimensions do not establish first-person eye position or race height.
- Testing only initial load missed transition/input-state failures. Test repeated
  entry/exit and clean shutdown, and retain unsuccessful runs as failures.

See [optimization history](OPTIMIZATION_HISTORY.md),
[implementation journal](IMPLEMENTATION_JOURNAL.md),
[player movement](PLAYER_MOVEMENT.md) and [roadmap](ROADMAP.md).

## Receipt and future recipe boundary

`amiwind-build-receipt-v1` names `seyda-neen-prison-v1` for the current AGA route.
Every installed input file is hashed once before conversion, including loose
files. Inputs are not embedded in the public recipe. The commands and source
hashes identify the current procedural recipe; there is not yet an arbitrary
JSON scene importer or automatic incremental cache. Tool hashes identify direct
executables, not every shared library or SDK file. Preserve the SDK/environment
with the private build evidence for deeper reproduction. HDF timestamps can differ.

Next: lift cell/assembly/spawn/budget choices out of stage code into a validated
recipe schema; then select another exterior or interior without editing converter
logic. Reuse this path for other games only after implementing a source-format
adapter, unit/axis mapping and equivalent behavioral tests. Generality must grow
from proven recipes; it must not hide per-game assumptions.
