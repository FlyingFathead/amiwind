# BUILD-DIAGNOSTIC-PALETTE-38: Diagnostic palette stages mixed

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 12 October 2026, in v0.0.38-dev |
| Where | Isolated legacy lava diagnostic, flora integration |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38-dev (last seen) |
| Severity | medium: Colour evidence and cached asset compatibility are unreliable until palette stages match |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | Isolated lava diagnostic |
| From commit | source and engine c2eaa5a |
| CHIM engine version | none: legacy engine |
| Build note | Converter changes pinned separately by diagnostic source manifest; not a committed release world |

<!-- END GENERATED FACTS -->

## Symptom
A flora integration guard rejects a diagnostic scenery palette mismatch.
Earlier diagnostic colour captures do not establish correct palette parity.

## Where
The isolated legacy lava diagnostic used the final image palette during terrain
and scenery conversion, while cached flora used the pre-sky conversion palette.

## How it happened
The diagnostic selected the packaged palette as a convenient input, bypassing
the production ordering: convert with the original palette, then remap indexed
pixels when reserving the sky bank. The sealed development package is unchanged.

## Why it was not caught
Terrain and scenery agreed with each other. The independent flora palette
fingerprint check caught the inconsistency before flora conversion proceeded.

## Reproduction
Combine the earlier diagnostic scenery with cached flora; compare their palette
hashes. The flora guard refuses the mismatch.

## Repair
Rebuilt all three diagnostic layers with the original conversion palette.
Applied the existing sky_palette_overlay pixel mapping and verified that its
banked palette equals the packaged palette. No engine mechanism changed.

## Verification
The rebuilt map retains geometry, collision and entities across pixel remapping.
All nine required sprite payloads match exact disk readback. The rebuilt
map loads natively with scenery, flora, the correct world identity and exterior
classification. This is a scoped diagnostic, not final package acceptance. Prior geometry/contact evidence is retained;
prior colour comparisons are not accepted as palette parity.

## Prevention
Bind conversion and runtime palette hashes separately. Use production remapping
and reject mixed-palette layer inputs before diagnostic captures.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells

<!-- END GENERATED CATEGORY -->
