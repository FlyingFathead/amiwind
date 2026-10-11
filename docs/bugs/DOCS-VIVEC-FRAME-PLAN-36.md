# DOCS-VIVEC-FRAME-PLAN-36: The docs contradict each other on how Vivec goes onto CHIM (one frame vs eight district frames vs the coordinate range)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.36-dev3 |
| Where | docs/chim WORLD_FORMAT, README, FEATURES and OPEN_WORLD_FRAMES (M3 stage B) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | medium: the Vivec plan cannot be followed as written; blocks M3 stage B decisions |
| Family | Vivec preview frame and its joins to the world (`vivec-frame-edge`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b5e7a9 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Open. Found in a review of the CHIM format docs. Needs one plan; the frame plan is an owner decision.

## Symptom

The docs give four statements about Vivec's CHIM milestone M3, stage B, that cannot all be true:

1. [README.md](../chim/README.md) milestones and [FEATURES.md](../chim/FEATURES.md): stage B is "all of Vivec in one
   frame", designed (format 0.6).
2. [WORLD_FORMAT.md](../chim/WORLD_FORMAT.md) "Stage B: all of Vivec, as one frame" itself says the district cores span
   8,192 by 9,216 units while positions wrap past about 4,096 ([CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md)),
   so one frame cannot hold them; it also says "nine" district frames in one place and "eight" in another.
3. [OPEN_WORLD_FRAMES.md](../chim/OPEN_WORLD_FRAMES.md): Vivec keeps its eight district frames until the open-world
   frames (M4) span edges.
4. WORLD_FORMAT.md's own rule refuses overlapping frames in one world, and the eight district frames overlap by design,
   so they cannot ship together as they are.

## Count from the game data (10 October 2026)

Counted from the exterior cell names in the base master file: Vivec has **eight named districts on 12 exterior
cells**: Foreign Quarter (2 cells), Arena, Hlaalu, Redoran, St. Delyn, St. Olms, Telvanni (1 each) and the Temple (4 cells),
plus 3 cells named only "Vivec" (the water and edges around the cantons): 15 cells named Vivec in all, nine distinct names,
which is probably where "nine" came from; the districts are eight. The eight district frames together touch 36 cells
(x 1..6, y -14..-9): the 15 Vivec cells, 2 Ebonheart cells and 19 unnamed water and shore cells.

## Where

docs/chim/README.md (milestones), docs/chim/FEATURES.md (Vivec on CHIM, M3), docs/chim/WORLD_FORMAT.md (stage B),
docs/chim/OPEN_WORLD_FRAMES.md (Vivec).

## How it happened

Each document was written at a different stage of the M3 design; the coordinate-range finding and the district-frame
decision came later and were not carried back into the earlier pages.

## Why it was not caught

No check compares design statements across documents.

## Reproduction

Always: read the four places above.

## Repair

One plan, written once and linked from the other pages, after the owner decides between: (1) widening the coordinate
protocol (one change to how positions are sent, plus an audit of every 4,096-unit assumption), (2) two city frames
with distant levels across their edge, (3) waiting for the M4 open-world frames. Until then every page says "frame
plan: decision pending" and links here. "Nine" is corrected to eight.

## Verification

To do: the four pages agree and name the decided plan.

## Prevention

Design decisions live in one place per milestone; other pages link to it instead of restating it.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Vivec preview frame and its joins to the world (`vivec-frame-edge`). The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. See [families](README.md#families).

- [TOWN-EDGE-UNBUILT-32](TOWN-EDGE-UNBUILT-32.md): Leaving a town into an unbuilt neighbour drops the player into a bare world map
- [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md): A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-ARENA-HANDOFF-32](VIVEC-ARENA-HANDOFF-32.md): The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view
- [VIVEC-ARENA-WATER-FALL-32](VIVEC-ARENA-WATER-FALL-32.md): The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water
- [VIVEC-CANTON-SKY-HOLE-32](VIVEC-CANTON-SKY-HOLE-32.md): Sky shows through a Vivec canton wall seen from below
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

Related bugs in other categories:

- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)

<!-- END GENERATED CATEGORY -->
