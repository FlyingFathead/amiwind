# SEYDA-REGIONS-PIN-33: The recorded Seyda Neen region table differs from what the region layout writes

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | Seyda Neen region layout (prepare_seyda_regions.py) vs the recorded v0.0.31 stage |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The recorded maps ship with their own pinned table; only comparisons against the current layout differ. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the CHIM builder (milestone M2, Seyda Neen on CHIM) while preparing the recorded
v0.0.31 Seyda Neen maps as the parity reference. The owner's copy of the recorded table is preserved
privately, with a SHA-256 manifest; it is never shipped with the source.

## Symptom

`seyda-regions.txt` written from the repository's region layout
(`prepare_seyda_regions.directory_text(regions())`) does not match the recorded v0.0.31 table that
`config/seyda-recorded-v0.0.31.json` pins. The region names, cores, default point, hysteresis and
draw distance are equal. The coverage boxes differ: the recorded table reaches 700 units past each
core, the current layout 896 (`OVERLAP`).

## Where

`config/seyda-bounded-regions.json` and `tools/prepare_seyda_regions.py` (`OVERLAP`,
`directory_text`), against the recorded stage (BUILD-SEYDA-REGEN-30).

## How it happened

The overlap was raised after v0.0.31 was recorded. The recorded maps were cut with the old overlap,
so the pinned table and the maps agree with each other but not with the current layout. Before
this change the recorded table existed in one copy only, inside a build volume.

## Why it was not caught

Recorded-stage builds install the pinned table and maps byte for byte. Nothing compared the table
with the current layout.

## Reproduction

Write `directory_text(regions())` and compare it with the pinned `seyda-regions.txt`
(SHA-256 `a927b673...`).

## Repair

None needed for v0.0.32: the recorded maps and their own table ship together. The CHIM frame map
reads only the cores and the default point, which are equal in both tables. Seyda Neen on CHIM
(M2) replaces both.

## Verification

The CHIM Seyda frame map is checked against the recorded maps with the pinned table.

## Prevention

Keep every recorded input in the owner's private archive with a manifest, not only in a build
volume.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)

<!-- END GENERATED CATEGORY -->
