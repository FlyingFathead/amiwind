# BUILD-FINALIZE-SCENE-31: Image finalisation stops on an undefined name before media staging

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | image step (tools/build_aga.py, finalize_image) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29-dev4, v0.0.32-dev (last seen) |
| Severity | critical: finalize_image stops with a NameError, so no disk image is produced. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Repaired in source (one line); not yet exercised by a full image build.
Present since v0.0.29-dev4.

## Symptom

`tools/build_aga.py image` (and so every guided AGA build) stops with a
Python `NameError: name 'scene' is not defined` in `finalize_image`, after
the map, actor and heap gates and before the music and media are staged. No
HDF is made. Not yet seen in a build log; found reading the source.

## Where

`tools/build_aga.py`, `finalize_image`: the media step reads
`scene/'intro-conversion.json'`, but `scene` is a local of `image()`, not of
`finalize_image`.

## How it happened

v0.0.29-dev4 added the intro conversion receipt to media staging inside
`finalize_image`, using the name `scene` from `image()`. `finalize_image` only
has `args.scene`.

## Why it was not caught

No test runs `finalize_image` to the media step (it needs a complete stage),
the existing tests only check the order of its steps in the source text, and
the toolchain has no undefined-name check. The playtest disks since then were
assembled by adding files to earlier images, which does not run this code.

## Reproduction

In Docker: `symtable` on `tools/build_aga.py` shows `scene` in
`finalize_image` as an unbound global, and the module binds no `scene`.

## Repair

Read the receipt from `Path(args.scene)/'intro-conversion.json'`.

## Verification

The same `symtable` check after the change finds no use of `scene` in
`finalize_image`; full suite in Docker. Pending: a full image build.

## Prevention

A full image build (or a test that runs `finalize_image` on a complete
synthetic stage) before the next release; consider an undefined-name check in
the source gate.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
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
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

<!-- END GENERATED CATEGORY -->
