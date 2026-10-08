# BUILD-HAND-CATALOG-SERIAL-32: The hand-catalog stage bakes every race and sex one after another

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (63ab202), not shipped at the time of writing. Found by the
image-parallel work.

## Symptom

The `hand-catalog` builder stage loops over every playable race and sex pair in one process with no
worker pool, although each pair is independent.

## Where

`tools/prepare_hand_catalog.py` (race/sex loop), `hand-catalog` stage in `tools/build.py`.

## How it happened

The stage was added after the shared worker pool, without one.

## Why it was not caught

No test checked that the new stage receives `--jobs` and uses the pool.

## Reproduction

Run the stage and watch its CPU use: one busy core.

## Repair

In source (63ab202): the race/sex pairs bake in the shared worker pool with `--jobs`, results in
serial order, the catalogue written once after every pair succeeded.

## Verification

135 s at one job, 42 s at 16 (busy host), identical output.
`tests/test_hand_catalog_normals.py` `test_race_pairs_bake_in_the_pool_with_serial_bytes`.

## Prevention

`tests/test_build_jobs_workers.py` covers the stage once it takes `--jobs`.
