# HARVEST-SEYDA-HEAP-REFUSED-32: Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:heap |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Seyda Neen sub-cells sn018 sn019 sn020 sn021 sn026 sn035 sn055 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Six sub-cells lose harvest they had in v0.0.31. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. A player-visible regression against v0.0.31. Found by the builder harvest step
(BUILD-HARVEST-NOT-BUILT-32, commit 0331f76); related to
[HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md).

## Symptom

The image step's heap admission refuses harvest catalogues for sn018, sn019, sn020, sn021, sn026,
sn035 and sn055, so those sub-cells ship without harvestable mushrooms. v0.0.31 shipped catalogues
for six of them (sn018, sn019, sn020, sn021, sn026, sn035); in those six, mushrooms that could be
picked in v0.0.31 can no longer be picked. sn055 had none in v0.0.31.

## Where

Seyda Neen sub-cells (the recorded v0.0.31 maps under the BUILD-SEYDA-REGEN-30 exception);
`tools/harvest_build.py` admission through `tools/check_world_map_heap.py`.

## How it happened

v0.0.31's catalogues were made outside the builder and never passed the current heap model. The
builder now admits a catalogue only if the map clears the modeled heap allowance with it installed:

- sn019 (-238,180 bytes), sn026 (-104,356) and sn035 (-12,148) fail even without a catalogue, so an
  image with the strict budget policy fails on them anyway (HEAP-SEYDA-OVERLAP-32);
- sn018 (+7,212), sn020 (+92,652), sn021 (+26,540) and sn055 (+86,364) pass without a catalogue and
  fail only because of the harvest charge.

## Why it was not caught

Harvest data was carried forward in patched images (BUILD-HARVEST-NOT-BUILT-32), and the heap
allowance was raised after these maps shipped (HEAP-SEYDA-OVERLAP-32).

## Reproduction

The image step's receipt `harvest-staging.json` (refused maps), or the repository heap check on the
Seyda Neen maps with and without their catalogues.

## Repair

Not yet. Options: measure the real harvest and guard overlap in the emulator and set the allowance
from it (HEAP-SEYDA-OVERLAP-32); a smaller catalogue for the four maps that fail only on the harvest
charge; Seyda Neen rebuilt by CHIM. Until then the v0.0.32 notes list these sub-cells as having no
harvest.

## Verification

Pending.

## Prevention

The harvest step reports refused maps against the previous release's catalogues; a map that loses
harvest it had in the last release is listed in the build summary.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
