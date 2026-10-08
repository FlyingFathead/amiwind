# BUILD-SCHEDULER-JOBSHARE-32: The stage scheduler fixes a stage's worker share when it starts

## Status: 8 October 2026

Open. Found by the build profiler work (synthetic build, measured).

## Symptom

A stage that becomes ready while another holds most of the `--jobs` budget gets one worker and keeps it:
in the synthetic build `scenery` ran 48 s on 1 of 16 cores while the serial image step held 14 jobs
on one core.

## Where

`tools/build_parallel.py`.

## How it happened

Budgets are assigned at start and never rebalanced.

## Why it was not caught

Stages were never profiled or checked for shared outputs.

## Reproduction

The profiler's synthetic build; idle-core warnings.

## Repair

On the v0.0.32 development line (not shipped): a serial stage holds one worker; running pooled
stages share the rest evenly and are rebalanced every scheduler round, leaving one worker for each
ready stage that waits. Each pooled stage gets an allowance file (`AMIWIND_BUILD_JOBS_FILE`); its
worker pools (`ordered_map`, `completed_map`) never run more tasks than the allowance and grow up
to the build budget when it rises. Map tool threads (`vis -threads`) keep the value the stage
started with.

Remaining limit (8 October 2026, image-parallel work): Python pools follow the new allowance, but
map tool threads keep the start value, so a stage whose share shrinks can briefly run more threads
than its share until its running map tools finish. Open.

## Verification

`tests/test_build_parallel.py`: a long pooled stage starts with 7 of 8 workers, shrinks to 4 when a
late stage starts, the late stage grows from its start share to 4 and to 8 when the first ends; the
workers held never exceed the budget. Not yet measured on a full build.

## Prevention

Idle-core warnings in every build profile; a scheduler test with uneven stages.
