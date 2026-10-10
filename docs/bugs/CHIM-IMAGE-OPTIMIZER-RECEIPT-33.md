# CHIM-IMAGE-OPTIMIZER-RECEIPT-33: A pure CHIM image stops at the final heap gate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/build_aga.py image step, tools/optimize_world_maps.py receipt binding |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: Every pure CHIM image build (--builder chim, since 4b15583) would fail in the image step after about 20 minutes of work. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 0a98597, engine 0a98597, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0a98597, world format 0.5 |
| Unknown because | found in source on the CHIM branch; no CHIM world build |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open: found by reading the code; no build has reached this point yet. Repaired in source on the
CHIM no-legacy branch; not yet in a build.

## Symptom

A pure CHIM image (`--builder chim`) would stop in the image step with "Final heap audit does not
describe optimized map outputs", after the frame maps are written and the CHIM towns' legacy maps are
removed.

## Where

`tools/build_aga.py` image step; `tools/optimize_world_maps.py` (`bind_heap_report`,
`verify_optimized_maps`).

## How it happened

The map optimizer writes a receipt of every staged map, and the final heap audit and a later check
bind to exactly that set. Since the pure CHIM image (4b15583) the image step writes the CHIM frame
maps and removes the legacy exterior maps after the optimizer, so the staged map set no longer
matches the receipt.

## Why it was not caught

The unit tests cover the frame maps, the removal and the receipt binding separately. The only
complete image build that used CHIM was made before 4b15583 (frame maps written after the heap gate,
nothing removed).

## Reproduction

Build an image with `--builder chim`: the image step stops at the final heap gate.

## Repair

`optimize_world_maps.rebind_chim_maps`: right after the frame maps and the removal, the receipt drops
the removed maps, adds the frame maps unchanged (`not_optimized: CHIM frame map`), records the change
under `chim_rebind` and is verified against the staged maps. Any other new or missing map stops the
image. The stair and heap gates then run on the shipped set.

## Verification

`tests/test_chim_no_legacy.py` `OptimizerRebindTests`: the old receipt fails against the CHIM map set;
the rebound receipt passes `verify_optimized_maps`; a stray map or a missing map stops it. A source
order test pins the rebind before the stair and heap gates.

## Prevention

Those tests. The pass 2 build (pure CHIM Balmora and Seyda Neen) is the first complete run through
this path.

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
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built

<!-- END GENERATED CATEGORY -->
