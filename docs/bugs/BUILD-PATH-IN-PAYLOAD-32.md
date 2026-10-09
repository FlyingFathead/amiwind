# BUILD-PATH-IN-PAYLOAD-32: A shipped sky file contains the folder the build ran in

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:payload-diff |
| First noticed | 8 October 2026, in v0.0.32 |
| Where | id1/gfx/sky-palette-bank.json (tools/prepare_shared_sky_assets.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | low: Harmless in play; breaks byte-identical rebuilds across workspaces and ships a build folder path. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.32 |
| From commit | source and engine 0f467e4 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-dev, not shipped at the time of writing. Present in the v0.0.32 payload.

## Symptom

`id1/gfx/sky-palette-bank.json` in the v0.0.32 payload has a field `shared_sky_source` holding the
absolute path of the build's work folder (`.../sky-asset-preparation/owned-cloud-sky.lmp`). Two
builds of the same source in different folders therefore differ in this file, and a build folder
path ships in the public payload. No effect on play: the game does not read the field.

## Where

`tools/prepare_shared_sky_assets.py` (`prepare_staged_sky`), which writes the marker into the
staged `id1/gfx/` during the image step.

## How it happened

The marker was written from the same report the builder uses internally, and that report needs the
real path of the prepared sky file (the exterior sky step reads it next).

## Why it was not caught

Nothing compared a payload built in one folder with one built in another, and no check looked for
build paths in payload files.

## Reproduction

Build the image twice in two different work folders and compare `id1/gfx/sky-palette-bank.json`;
or search the v0.0.32 payload's text files for the build folder. Found by the v0.0.32 release image
payload diff against the dev3 image: the only differing file.

## Repair

The shipped marker names the sky source relative to the build work folder
(`sky-asset-preparation/owned-cloud-sky.lmp`); the sky itself stays identified by `sky_sha256`.
The builder's own report keeps the usable path. The image step now refuses any payload text file
that contains the build output folder path (`tools/amiga_fs.py` `check_payload_host_paths`, run
before the world volumes are packed).

## Verification

`tests/test_prepare_shared_sky_assets.py` (the marker holds no temporary build path; fails on the
v0.0.32 code), `tests/test_amiga_fs.py` (the payload check finds the path in native, POSIX and
JSON-escaped forms, ignores binary files and short roots, and runs in the image step before
packing). An image build from v0.0.33-dev has not been run yet.

## Prevention

The payload path check is part of every image build; release payload comparisons across
workspaces stay part of the from-scratch check.

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
