# BUILD-ACTOR-CONTACT-REGRESSION-38: Full dev3 rebuild rejects previously grounded actors

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 12 October 2026, in v0.0.38-dev3 |
| Where | Full build actor-contact stage |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev3 (last seen) |
| Severity | high: Blocks development playtest packaging;116 formerly grounded placements fail. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.38-dev3 full candidate |
| From commit | source 72ddf37, engine 72ddf37, CHIM world 72ddf37 |
| CHIM engine version | CHIM 0.2.0, engine 72ddf37, world format unknown |
| Unknown because | Failure in interior BSP actor-contact stage; CHIM format not material to current finding. |
| Platform or emulator | unknown (Build-time failure before emulator playtest.) |

<!-- END GENERATED FACTS -->

## Symptom
The full development rebuild stops at actor contact: 116 failed contacts and
three explicit exceptions. The dev2 control has116 grounded and the same three
exceptions. The gate prevents packaging this candidate.

## Where
Initial idle actor ground support in rebuilt interior maps, including Addamasartus,
Balmora interiors and the tradehouse.

## How it happened
The first full dev3 rebuild after scenery collision metadata and legacy lava
changes reaches the actor-contact stage and reports blocked sole samples.
Authored nonsolid models received a negative BSP leaf index as their point-hull
root. The empty leaf index was -2, which the collision walker interpreted as
CONTENTS_SOLID everywhere. Broader use of authored NC/NCO metadata exposed this
writer defect in interior maps.

## Why it was not caught
Focused fern/lava diagnostics and synthetic tests did not exercise this complete
rebuild path. The full production actor-contact gate caught it before packaging.

## Reproduction
Build the full current-game recipe from72ddf37 with cached dev2 c2eaa5a inputs.
Compare actor-initial-contact.json:116 grounded controls become failed-contact.

## Repair
Candidate: write a real point node with two empty leaf children for nonsolid
models. This reuses the existing Mod_MakeHull0 leaf-to-contents conversion in
engine/aga/src/model.c; no new engine collision mechanism is introduced.
The standing hull stays empty. The failed build is preserved; no gate waiver.

## Verification
The regression fails against the old writer with a zero-fraction solid hit and
passes against the candidate. All 15 related flora integration tests pass.
Failed full build retained; full rebuilt actor gate, repaired package and native
acceptance remain pending. Evidence recorded 2026-10-12T13:57:14.925186+00:00.

## Prevention
Add a regression for the diagnosed cause and repeat the actual full actor gate
against rebuilt maps. Synthetic tests alone do not close this issue.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
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
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
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

<!-- END GENERATED CATEGORY -->
