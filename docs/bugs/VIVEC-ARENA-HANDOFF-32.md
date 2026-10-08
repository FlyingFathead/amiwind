# VIVEC-ARENA-HANDOFF-32: The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view

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
