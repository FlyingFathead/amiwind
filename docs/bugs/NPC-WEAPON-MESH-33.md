# NPC-WEAPON-MESH-33: NPCs hold no weapons or shields; combat uses them unseen

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/prepare_area.py and mwad/npc.py outfit (shields and weapons skipped), every converted NPC |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Fights look bare-handed: an Arena fighter swings an invisible mace and blocks with an invisible shield; rules unaffected. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found while building the Vivec Arena minigame (docs/COMBAT.md). The combat rules use each
NPC's best melee weapon and shield from its record; the converted models show neither.

## Symptom

In `dbgmode arenapit` Mevil Molor swings a steel mace and blocks with a chitin shield that are not
drawn: the attack frames move an empty hand, a block shows nothing.

## Where

`src/mwad/npc.py` `outfit` skips shields ("not drawn in this unarmed idle study") and never looks at
weapons; `tools/prepare_area.py`, `tools/prepare_gallery.py` and `tools/prepare_combat.py` bake what
`outfit` returns. Every converted NPC is affected.

## How it happened

The NPC conversion started as an unarmed idle study. Weapons and shields attach to the skeleton's
Weapon Bone and Shield Bone with their own offsets (the carried torch already needed this bone
math), which nobody needed before combat existed.

## Why it was not caught

Until combat, no NPC held anything in play, so nothing looked wrong.

## Reproduction

Always: `dbgmode arenapit mevil molor`, watch his attack.

## Repair

Not yet. Attach the record's equipped weapon and shield meshes to the Weapon Bone and Shield Bone
in the shared assembly (`npc_geometry.assemble`, the torch's `rigid_attachment` convention), for
every NPC at once; measured weapon meshes are small (steel mace 390 triangles, steel longsword 276,
ebony longsword 212, steel shardblade 145), so the bake budget decides how much survives.

## Verification

None yet. A regression test should bake one armed NPC and check that the weapon's triangles follow
the hand in the attack frames.

## Prevention

Combat-visible equipment belongs to the shared NPC assembly, not to a per-scene path.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups

<!-- END GENERATED CATEGORY -->
