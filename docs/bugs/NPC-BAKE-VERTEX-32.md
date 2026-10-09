# NPC-BAKE-VERTEX-32: NPC model bake exceeds the alias vertex budget for two Telvanni residents

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | NPC model baker (tools/npc_geometry.py), Telvanni residents |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Two residents exceed the vertex budget and stopped a town conversion. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

Related bugs in other categories:

- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
