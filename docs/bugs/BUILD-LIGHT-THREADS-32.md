# BUILD-LIGHT-THREADS-32: ericw light is not byte-reproducible with more than one thread

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (e77370a), not shipped at the time of writing. Found by the
image-parallel work ([BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md)).

## Symptom

ericw-tools `light` 0.18.1 writes faces and lightmaps in a thread-dependent order: two runs of the
same map with 2-8 threads differ in the faces and lighting lumps. One thread is reproducible; `vis`
is identical for any thread count. Multi-threaded light therefore breaks the file-by-file
comparison of a from-scratch build ([BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md)).

## Where

Every builder step that runs `light -threads N` with N above 1. The Seyda Neen regions and the
Balmora repair already run one light thread per map on the v0.0.32 development line. Still
multi-threaded: `tools/build_gallery.py`, `tools/prepare_census.py`, `tools/prepare_interior.py`,
`tools/prepare_mesh_bsp.py`.

## How it happened

Light threads were set from `--jobs` (or fixed counts) for speed, without a reproducibility check.

## Why it was not caught

No test compared two builds of the same map with different thread counts.

## Reproduction

Light one map twice with `-threads 4` and compare the faces and lighting lumps.

## Repair

In source (e77370a): one shared helper, `tools/vis_options.py` (`LIGHT_THREADS = 1`,
`light_args()`), supplies the thread argument to all 11 light calls in the builder, including the
four tools above; their map-level pools stay parallel. Cost of one thread against 16 is negligible
(Seyda Neen 3.8 s against 3.6 s).

Expected differences: maps that were lit with `--jobs` threads before (the gallery plane, Census,
the prison and the Seyda Neen mesh scene) differ from earlier builds, which were not reproducible
either. The from-scratch comparison against v0.0.31 and dev1 must list these as expected.

## Verification

`tests/test_build_jobs_workers.py` `test_light_compiles_single_threaded`: `LIGHT_THREADS` is 1
and a static scan finds every light call in the builder taking its arguments from `light_args`
(mutation-checked: a call with its own thread count fails it). A from-scratch build is pending.

## Prevention

`tests/test_build_jobs_workers.py` fails when a map light compile becomes multi-threaded; extend it
to the four tools.
