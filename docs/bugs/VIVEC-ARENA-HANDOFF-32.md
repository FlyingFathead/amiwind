# VIVEC-ARENA-HANDOFF-32: The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Arena frame handoff core (config/vivec_arena.json), Redoran east exit |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Handoff arrives about 205 units from the frame edge, so the edge is in view. |
| Family | Vivec preview frame and its joins to the world (`vivec-frame-edge`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

The Arena's default handoff core covers strips of Redoran, the Foreign Quarter, St. Olms and
Telvanni. Being earlier in the town table, the Arena takes over there, but its frame edge is only
96 units beyond its core: arriving from the Redoran Plaza east exit lands about 205 units from
the edge, so the edge is in view.

## Where

`config/vivec_arena.json` (no explicit `handoff_core`), `engine/aga/src/aw_world.c` handoff.

## How it happened

The Arena was configured alone, before neighbouring cantons existed.

## Why it was not caught

No neighbouring towns until now.

## Reproduction

Exit Redoran Plaza east with the Arena and cantons installed.

## Repair

Not yet: give the Arena a `handoff_core` of cell 4,-11 and widen its bounds (after dev1).

## Verification

Pending.

## Prevention

Importer check that every frame edge stays beyond draw distance from its handoff core.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Vivec preview frame and its joins to the world (`vivec-frame-edge`). The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. See [families](README.md#families).

- [TOWN-EDGE-UNBUILT-32](TOWN-EDGE-UNBUILT-32.md): Leaving a town into an unbuilt neighbour drops the player into a bare world map
- [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md): A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-ARENA-WATER-FALL-32](VIVEC-ARENA-WATER-FALL-32.md): The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water
- [VIVEC-CANTON-SKY-HOLE-32](VIVEC-CANTON-SKY-HOLE-32.md): Sky shows through a Vivec canton wall seen from below
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

<!-- END GENERATED CATEGORY -->
