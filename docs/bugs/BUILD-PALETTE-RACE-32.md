# BUILD-PALETTE-RACE-32: Census and world flora assets can run together on the same palette file

## Status: 8 October 2026

Open. Found by the build profiler work (source-checked, not observed).

## Symptom

`world-flora-assets` depends only on `intro` and reads `intro-scene/id1/gfx/palette.lmp`; `census` also
runs right after `intro` and rewrites that file in place (truncate, then write). The flora sprites can
therefore be made from the palette before or after Census changes it, or stop on a half-written file.

## Where

`tools/build_parallel.py` stage dependencies; `tools/ui_palette.py` `reserve`.

## How it happened

Dependencies were declared by data flow at the time; Census later started rewriting the palette.

## Why it was not caught

Stages were never profiled or checked for shared outputs.

## Reproduction

Parallel build where both stages overlap; compare sprite hashes between runs.

## Repair

On the v0.0.32 development line (not shipped): `world-flora-assets` and `hand-catalog` (which also
read the scene palette) depend on `census`; `ui_palette` writes the palette, lookups and receipt
whole (temporary file, then rename). Flora sprites are now always made from the Census palette,
so their bytes can differ from builds where flora ran first.

Expected difference (8 October 2026): flora sprite bytes of a from-scratch build can differ from
earlier v0.0.32-dev1 builds in which flora ran before Census. From-scratch comparisons against
those builds list this as an expected difference, not a regression.

## Verification

`tests/test_build_parallel.py`: every stage that reads `intro-scene/id1/gfx/palette.lmp` runs after
Census or before it starts; in-place rewrites leave whole files only.

## Prevention

The profiler's output manifests mark stages that overlap on a path; a test that no two
concurrent stages write or read-while-written the same path.
