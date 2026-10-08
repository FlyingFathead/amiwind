# RENDER-SURFCACHE-THRASH-32: Seyda Neen views rebuild the surface cache every frame at a fixed camera

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

With the camera standing still, Seyda Neen 1 allocates 914 surface cache blocks per frame
(812 KB, 0.76 million texels drawn), Seyda Neen 3 625. Balmora allocates 0 at its cameras.
The cache is smaller than these views need, so lit surfaces are rebuilt every frame.

## Where

Engine surface cache (`d_surf.c`, cache size set at start-up).

## How it happened

Unknown: likely many distinct lit brush-model surfaces in view at once.

## Why it was not caught

No per-frame cache counters before this work.

## Reproduction

`dbg rcount 1` at the Seyda Neen cameras in `docs/HARDWARE-BENCHMARK.md`.

## Repair

Not yet: measure cache size needed per view; compare with the memory budget.

## Verification

Pending.

## Prevention

Counters in the benchmark route.
