# NPC-BAKE-VERTEX-32: NPC model bake exceeds the alias vertex budget for two Telvanni residents

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Baking the models of two Telvanni canton residents fails at every reduction step down to 192
vertices, which stopped the whole Telvanni conversion until they were excluded.

## Where

The NPC model baker (`tools/npc_geometry.py`).

## How it happened

Unknown: likely heavy equipment meshes.

## Why it was not caught

First conversion of these residents.

## Reproduction

Import the Telvanni canton without the exclusions.

## Repair

Not yet: find what pushes them over and reduce generically; a failing resident should be
reported and skipped by the importer, not stop the town.

## Verification

Pending.

## Prevention

Importer reports per-resident failures.
