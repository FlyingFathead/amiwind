# CHIM-VIEW-FACES-33: Model faces dominate each Balmora view: the streamer alone does not fix frame rate

## Status: 8 October 2026

Open. Found by the first CHIM world-format build of Balmora (branch v0.0.33-chim-format, format 0.1).

## Symptom

13,535 faces per view (median), up to 54,406; terrain is only 2.2 % of them. CHIM fixes disk and heap
use, not drawing cost.

## Where

Balmora placements in CHIM format.

## How it happened

Same models as today; only the storage changes.

## Why it was not caught

First measurement.

## Reproduction

The CHIM validator's per-view face counts.

Which models (format 0.3 statistics, 8 October 2026): a few models dominate. The heaviest single
model is the siltstrider (3,266 faces); by placed faces summed over the frame, flora_tree_wg_01
7,310, hlaalu_loaddoor_02 6,328, light_de_streetlight_01 5,587, ex_hlaalu_buttress_03 4,092 and
dsteps_03 3,854. Candidate owners: distance detail and model simplification for these heavy models;
the 160 placements over 16 leaves are in [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md).

First FS-UAE comparison, Balmora under CHIM against the legacy maps (8 October 2026; the five
benchmark cameras; JIT profile on a busy host, so relative numbers only):

| Counter (per frame) | Legacy -> CHIM, range over the cameras |
| --- | --- |
| World faces | 654 -> 97 ... 498 -> 46 |
| Clip nodes | 233,867 -> 39,126 ... |
| Frame time | 92.5 -> 46.9 ms ... 51.2 -> 28.0 ms |
| Frames per second x10 | 108 -> 213 ... 195 -> 357 |

Doors in and out of the town pass under CHIM. Placed-model faces remain the main work per view, as
above; the session's cache thrashing is [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md) and
its texture specks [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md).

## Repair

Not yet: distance detail (simpler distant shapes, the mold shells) and occlusion; measured with
the renderer counters in FS-UAE.

## Verification

Pending.

## Prevention

Face counts per view in the report; frame budget in the design.
