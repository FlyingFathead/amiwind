# BUILD-SEYDA-REPORT-HOST-PATHS-35: The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:payload-preflight |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/prepare_seyda_regions.py convert: the seyda-regions.json it writes into id1 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: Every default CHIM build (converted Seyda Neen) stopped at the image step's host-paths check; the file named the build folder. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.35-dev1 clean build (source 7ec5c03) |
| From commit | source 7ec5c03, engine 7ec5c03, CHIM world 7ec5c03 |
| CHIM engine version | CHIM 0.1.0, engine 7ec5c03, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Repair in v0.0.35 development (not shipped).

## Symptom

A clean v0.0.35 development build with the BUILD-SEYDA-CONVERTED-NOT-STAGED-35 repair (source 7ec5c03, the
default CHIM build that converts Seyda Neen) got past the chim-inputs check. The image step's later payload
preflight then stopped it:

```
host-paths: Payload files contain the build workspace path (BUILD-PATH-IN-PAYLOAD-32): id1/seyda-regions.json
```

## Where

`tools/prepare_seyda_regions.py`, `convert()`: it writes its conversion report as `id1/seyda-regions.json`,
which ships in the payload. The report named its inputs and candidates by absolute path: the source map, the
preserved source town, the palette and each region's candidate BSP (330 path strings, all under the image
folder).

## How it happened

Until v0.0.34 every release build used `--seyda-recorded`, which ships the recorded v0.0.31 file instead. That
file has the same schema; its paths name the folder the v0.0.31 image was assembled in, not the current build
folder, so the host-paths check (BUILD-PATH-IN-PAYLOAD-32) never matched it. Converting Seyda Neen became the
default on the v0.0.35 line (BUILD-SEYDA-REGEN-30), so the converted report reached the payload for the first
time.

## Why it was not caught

The converted path had never reached the end of a full image: the early preflight stopped it first
(BUILD-SEYDA-CONVERTED-NOT-STAGED-35). No test checked the converted report for build paths.

## Reproduction

A default full build (CHIM with Seyda Neen, no `--seyda-recorded`) on source 7ec5c03: the image step stops at
the host-paths check.

## Repair

The check is unchanged. `convert()` writes the shipped `id1/seyda-regions.json` with every absolute path under
the image folder made relative to it (`neutral_paths`: `seyda.map`, `bounded-seyda/source-town.bsp`,
`boot/id1/gfx/palette.lmp`, `bounded-seyda/sn000/candidate.bsp`): the same schema, hashes and names as the
recorded file, without a host root. The full report with absolute paths stays in the build folder as
`bounded-seyda/seyda-regions-full.json` and is still returned to the caller. The image step and the town
flora install read only the region entries (name, core, coverage), which are unchanged.

## Verification

- The failed run's own `seyda-regions.json`, rewritten by `neutral_paths` into a scratch folder: the host-paths
  check passes; the file as written by 7ec5c03 is refused with the message above.
- `tests/test_seyda_pending_preflight.py` (`SeydaReportPathTests`): no absolute path left in the written form,
  the host-paths check refuses the absolute form and passes the written form, and `convert()` writes the
  neutral form and keeps the full report in the work folder.

## Prevention

Every report a converter writes into `id1/` names files relative to the build, never by absolute path; the
host-paths check stays in the payload preflight.

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
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step

<!-- END GENERATED CATEGORY -->
