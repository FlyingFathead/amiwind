# BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43: the first all-CHIM build stops in the image preflight

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 18 October 2026, in v0.0.43-dev3 |
| Where | tools/payload_preflight.py disk-layout check and tools/world_volumes.py partition_batches |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev3 (last seen) |
| Severity | high: blocks every all-CHIM image; the milestone build cannot be packaged until fixed |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev3_full-batch5_ef7e464 |
| From commit | source ef7e464, engine ef7e464, CHIM world ef7e464 |
| CHIM engine version | CHIM 0.2.1, engine ef7e464, world format 0.7 |
| Platform or emulator | Docker build (Linux) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Fixed in the builder on 18 October 2026 (v0.0.43-dev3 line); the dev3 image step resumes from its failed run.
Found by the v0.0.43-dev3 build.

## Symptom

The first full build with every exterior cell on CHIM converted everything, then stopped at the start of the
image step: "disk-layout: Invalid or oversized boot payload". The message names neither a file nor a limit.

## Where

The payload preflight's disk-layout check (`tools/payload_preflight.py`) and the partition planner it calls
(`tools/world_volumes.py`, `partition_batches`).

## How it happened

The preflight plans the world partitions from the classic world maps that are already on disk. CHIM region frame
maps are written later in the same image step, so they are left out of the plan. As long as some cells were
classic, the plan had maps to work with. With every exterior cell on CHIM the list is empty, and the planner
refuses an empty list with the same message it uses for an oversized boot payload.

Cause confirmed on the dev3 run's own staged files: the region directory names 2,526 open-world maps; none of them
is on disk (every cell belongs to a CHIM region frame, 1,348 frame maps under their primary names, the rest are
alias rows of divided cells or omitted maps), so the planned map list was empty. The boot payload itself was
well inside its budget (336,282,253 bytes of 1,610,612,736). The real packing step (`world_volumes.pack`) runs
after the frame maps are written, so it would have found them; only the preflight refused.

## Why it was not caught

No test ran the preflight on a world with no classic maps left; that state first existed in this build.

## Reproduction

Run the image step of a build in which every exterior cell is on CHIM.

## Repair

- The preflight puts every CHIM region frame map the image step will write into its partition plan, under its
  open-world map name (`world_volumes.PlannedMap`), so the plan has the same maps as the packing step. A frame
  map's size is a recorded upper bound (1,024 bytes plus 512 per recipe sprite row; v0.0.43-dev2's 1,295 region
  frame maps measured 808 to 9,996 bytes). Their far terrain sidecars and recipe sprites go into the boot plan
  with their exact sizes from the CHIM world. A classic map an earlier stage still made for a CHIM cell is not
  counted: the frame map replaces it. Zero classic maps is a valid world.
- `partition_batches` refuses each case with its own message and numbers: no maps to partition (with the boot
  payload size), a boot payload over the budget (its bytes, the limit and the excess; the packing step adds the
  largest boot files), a single map over the budget (its name and bytes).
- The disk-layout result in `payload-preflight.json` now records the plan: each drive and partition with its
  size, start, file count, payload and largest file.

## Verification

The preflight on the v0.0.43-dev3 run's own staged files (read only): 12 checks, 0 errors, 19.8 s. Its plan:
one drive of 2,281,734,144 bytes; DH0 (boot) 512 MiB at 32 KiB, 336,282,253 bytes in 2,815 files, largest
37,434,738 bytes; DW0 128 MiB at 512 MiB + 32 KiB, the 1,348 frame maps (1,485,312 bytes planned, largest
20,992); DW1 (the CHIM world) 1.5 GiB at 640 MiB + 32 KiB, 1,261,414,804 bytes in 35,658 files, largest
4,454,864 bytes. Every partition is below 2 GiB and starts below 2 GiB, every file is far below 1 GiB, the
drive is below 4 GiB. Tests: `tests/test_all_chim_preflight.py` (an all-CHIM world passes and partitions;
planned maps partition exactly like files of the same size; each refusal names its unit). The resumed dev3
image step is the end check.

## Prevention

`tests/test_all_chim_preflight.py` keeps an all-CHIM world in the suite. Before a milestone build, the
preflight runs on a test world already in the milestone state.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [IMAGE-ONE-HDF-TARGET-36](IMAGE-ONE-HDF-TARGET-36.md): The game ships on two drive images and three world partitions; the project target is the whole game on one HDF
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
