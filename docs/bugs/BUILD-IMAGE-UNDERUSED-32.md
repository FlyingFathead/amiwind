# BUILD-IMAGE-UNDERUSED-32: Parts of the image step still run serially or leave most CPUs idle

## Status: 8 October 2026

Open; tagged performance. Found by the image-parallel work after the
[BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md) repair.

## Symptom

One image pass on the dev1 inputs (16-CPU container, `--jobs 16`) still spends:

| Work | Time | CPU use |
| --- | --- | --- |
| Guard torches | 60 s | serial |
| Shared sky | 53 s | serial |
| DH0 readback | 41 s | about 1 busy CPU |
| Night lighting | 23 s | serial |
| Balmora's three rebuilds | 78 s | about 2 busy CPUs |
| Hidden-surface cull | 190 s | about 6 of 16 CPUs |

Update (8 October 2026, 517d548, not shipped at the time of writing): the hidden-surface cull's imbalance came from
the parent process rewriting a 4 MB progress receipt after every map, which starved the workers;
it now writes at most every 2 s, and the cull went from 186.5 s to 83.1 s (busy host). Drive
readback is now parallel (in slices). Still open: guard torch conversion stays serial (60 s)
because its receipt records assets in first-read order, so per-entry asset recording is needed
before it can run in parallel; shared sky, night lighting and the Balmora rebuilds are not yet
re-measured.

## Where

`tools/build_aga.py` image step.

## How it happened

Guard torch and shared sky conversion write one shared asset archive and were kept serial; the
rest was not yet split into independent pieces.

## Why it was not caught

Per-pass CPU use was first measured by the build profiler.

## Reproduction

The build profile of an image pass (per-pass time and busy CPUs).

## Repair

Not yet: split the shared-archive passes into parallel conversion plus one ordered write, read the
boot drive back in parallel, and find what keeps the cull and the Balmora rebuilds below their
share.

## Verification

`tests/test_hidden_surface_build.py` `test_progress_receipt_writes_are_throttled_and_final_receipt_complete`,
`tests/test_world_volumes_readback.py` `test_sliced_parallel_readback_equals_serial`. Remaining
passes pending; outputs must stay byte-identical to the serial code.

## Prevention

Idle-core warnings in the build profile ([BUILD_PROFILE.md](../BUILD_PROFILE.md)).
