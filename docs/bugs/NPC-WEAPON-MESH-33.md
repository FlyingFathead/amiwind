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

Repaired in source for the combat fighters (v0.0.33-arena-combat). `mwad/npc.py` `carried_parts`
adds the wielded weapon and the carried shield as rigid parts, the way the original engine does
(OpenMW `npcanimation.cpp` showWeapons and showCarriedLeft, `actoranimation.cpp` getShieldMesh): a
weapon is its own model on "Weapon Bone"; a shield is its armour's Shield body part (the female one
for women when the record gives one), otherwise its ground model, on "Shield Bone".
`outfit(..., carried=...)` takes the items from the caller, and the fighter bake
(`prepare_combat.bake_fighter`) passes the rules' own pick (`equipment()`: best melee weapon, the
shield unless the weapon is two-handed), so the drawn items are always the ones the rules use. The
shared assembly (`npc_geometry.assemble`) now skips `RootCollisionNode` subtrees, which the original
never draws (weapons and shields carry them). Measured weapon meshes are small (steel mace 390
triangles, steel longsword 276, ebony longsword 212, steel shardblade 145); the bake budget decides
how much survives.

Town residents (repaired in source, part 2): they hold their items only while fighting, through one
shared mechanism. `tools/npc_items.py` bakes each weapon or shield mesh once as a one-frame item
model (`items/<hash>.mdl`) and writes, beside each resident model with carried items, a tag table
(`<model>.tag`: per model frame, the Weapon Bone and Shield Bone origin and Quake angles in the
model's space), for both animation methods (idle-only and the animation kit). The engine
(`engine/aga/src/aw_items.c`) reads the table and precaches the items at spawn, shows the items as
their own entities when the resident engages, places them every frame from the tag of the actor's
current frame (the actor's yaw added) and removes them when the fight ends. Measured on the owner's
data: the weapon rebuilt from the item model and the tag matches the directly attached weapon within
0.001 units for a Hlaalu guard (steel longsword, Hlaalu tower shield); for an Imperial guard the
item keeps its own size, up to 3.3 units off at the blade tip, because the original also stretches
attached items with the actor's race width and height. Item models are about 146 KB each (once per
mesh); a tag table is 736 bytes for an 8-frame resident.

## Verification

Unit test (tests/test_combat.py `test_carried_weapon_and_shield_parts`): weapon and shield parts,
bones, the female shield part, the ground-model fallback, unknown items refused, the fighter bake
passing the rules' pick and the collision-node skip; `test_item_tags_angles_and_file` (Quake angles
round trip, tag rows, tag file, wiring); native `aga_items_test.c` (tag parsing, refusals, item pose
at yaw 0 and 90); the combat fixture checks items are shown at engage and hidden at every release
(it caught a leak on re-engage, fixed before commit). Real data: Mevil Molor (steel mace, chitin
shield) and Ultis Salam (steel longsword) baked from the owner's data, the weapon rigid on the hand
in every attack frame. Pending: an in-game frame (the evidence MiniWind, after the builder hold).

## Prevention

Combat-visible equipment belongs to the shared NPC assembly, not to a per-scene path.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames

<!-- END GENERATED CATEGORY -->
