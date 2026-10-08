# BUILD-JOBS-RESOLVE-PER-STAGE-32: With automatic jobs, stages of one build plan can get different worker counts

## Status: 8 October 2026

Open. Found by the parallel test runner work.

## Symptom

`tools/build.py` `commands()` resolves the automatic job count again for each stage, from current free memory,
so one plan can give stages different `--jobs` values (23 vs 22 observed). Two tests failed
nondeterministically under load because of it.

## Where

`tools/build.py` `commands()`, `tools/build_jobs.py`.

## How it happened

Each stage calls `resolve_jobs()` itself.

## Why it was not caught

Free memory was stable on quiet hosts.

## Reproduction

Plan a build twice while memory use changes.

## Repair

On the v0.0.32 development line (not shipped): `tools/build.py` resolves the worker count once
(an explicit `--jobs N` exactly, automatic once) in `main` and once per plan in `commands()`;
provenance, the scheduler and every stage use that value.

## Verification

`tests/test_build_jobs_workers.py`: with an automatic count that changes on every call, all
stages of one plan get the same value.

## Prevention

A test that every stage of one plan gets the same resolved value.
