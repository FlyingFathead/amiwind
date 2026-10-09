# BUILD-HEAP-RECEIPT-TUPLES-32: The image step refuses its own final heap receipt (tuples against lists)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | image step final heap receipt (tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev2 (last seen) |
| Severity | critical: The image step refuses its own heap receipt after about 20 minutes, so no image is made. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (2ca08b5), not shipped at the time of writing. Found by the
v0.0.32-dev2 image build.

## Symptom

The dev2 image step stopped at the very end, after about 20 minutes, with "Saved final heap
receipt differs from the supplied audit".

## Where

`tools/build_aga.py` (`audit_world_map_heap_with_receipt`, `bind_heap_report`),
`tools/compact_harvest_heap.py`.

## How it happened

Since the harvest builder step (BUILD-HARVEST-NOT-BUILT-32), the heap audit's
`harvest_external_profile.fingerprint_entries` held Python tuples (made by
`compact_harvest_heap`). Saved as JSON they come back as lists. `bind_heap_report` compares the
audit held in memory with the saved receipt, so every tuple counted as a difference and the
binding refused. dev1 had no harvest catalogues, so the list was empty and nothing tripped.

## Why it was not caught

The harvest tests used synthetic data and never ran the final heap binding with a non-empty
harvest profile.

## Reproduction

On the real dev2 maps: 389 differences between the in-memory audit and the saved receipt, all
tuple against list.

## Repair

In source (2ca08b5): `audit_world_map_heap_with_receipt` returns exactly the saved JSON, and the
fingerprint entries are built as lists.

## Verification

`tests/test_heap_receipt_roundtrip.py` (`test_returned_audit_equals_saved_receipt_with_tuples`,
`test_compact_harvest_fingerprint_entries_are_lists`). A finished dev2 image is pending.

## Prevention

The round-trip test; the finalize stages bind to the saved receipts, not to in-memory objects.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
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

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
