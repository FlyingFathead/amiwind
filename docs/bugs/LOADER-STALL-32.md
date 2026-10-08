# LOADER-STALL-32: One unexplained stall while loading the Mages Guild with the new loader

## Status: 8 October 2026

Open. Found by the map loader rework (decoding without staging). Not reproduced since.

## Symptom

In 1 of 7 emulator runs of the new loader the Mages Guild load stalled after "before-bsp" with no
error file; the screen stayed on "Loading...". It did not recur in later runs or a 24-load stress
run; old-engine runs were clean. Another emulator and two heavy jobs were running at the time.

## Where

`engine/aga/src/model.c` slice loader (suspected), or host load.

## How it happened

Unknown.

## Why it was not caught

Rare; needs repeated runs.

## Reproduction

Repeated Mages Guild loads with the new engine under host load.

## Repair

Not yet: more stress runs with the debugger attached on stall.

## Verification

Pending.

## Prevention

Stress loads in the loader tests.
