# LOADER-STALL-32: One unexplained stall while loading the Mages Guild with the new loader

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Map loader slice loader (engine model.c), Mages Guild load |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | critical: A load stalled on the Loading screen in 1 of 7 runs; not reproduced since. |
| Family | Loading and disk reads (`disk-loading`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
