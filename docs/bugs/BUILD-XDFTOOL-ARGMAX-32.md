# BUILD-XDFTOOL-ARGMAX-32: the image step fails at the end: xdftool argument list too long

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | image step finalize (tools/build_aga.py, tools/world_volumes.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | critical: The image step failed at its very end after about 30 minutes; no image was produced. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; fix written on the image parallelization branch. Found while profiling the v0.0.32-dev1 image
step on a copy of its inputs.

## Symptom

The image step ends with "Error: [Errno 7] Argument list too long: xdftool" after about 30 minutes of
work. The boot partition is written with ONE xdftool command that lists every boot file: with trees
and grass the boot payload has 15,747 files (about 5,000 flora sprites more than before), about 2 MB of
arguments, over the Linux limit (ARG_MAX 2,097,152).

## Where

`tools/build_aga.py` `finalize_image` (Linux path: one unbatched call); `tools/world_volumes.py`.
The Windows path already batched (`tools/build_windows_xdftool.py`).

## How it happened

The Linux path never had to write this many files: earlier images were patched rather than built, and
flora was opt-in (BUILD-FLORA-OPTIN-32).

## Why it was not caught

No test with a realistic file count; the step fails only at its very end.

## Reproduction

Image step with world flora on the full boot payload.

## Repair

Batch the xdftool operations on every platform (256 KiB of arguments per call, same operation order),
shared by the boot partition and the world volumes.

## Verification

Commit 1f301c4: `tests/test_build_windows_xdftool.py` builds an 18,000-file queue (above 2 MiB),
checks every call stays at or below 256 KiB, keeps the order and creates the image only once; both
packers use the runner. Full suite green on that commit. The dev1 image rebuilt with the fix:
pending.

## Prevention

A test that builds a command list for 20,000 synthetic files and checks every call stays under the limit.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships

<!-- END GENERATED CATEGORY -->
