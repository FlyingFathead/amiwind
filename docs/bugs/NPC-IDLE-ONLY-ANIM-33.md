# NPC-IDLE-ONLY-ANIM-33: NPCs play only their idle animation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | NPC model bake (base_anim idle frames only) and QuakeC aw_npc_idle |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Moving NPCs (the companion, chasing or fleeing actors) glide in their idle pose |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.33-dev1 MiniWind #3 |
| From commit | source c4e14ab, engine c4e14ab, CHIM world c4e14ab |
| CHIM engine version | CHIM 0.1.0, engine c4e14ab, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Planned for the next release as the animation kit.

## Symptom

The owner, playing the companion test in a MiniWind build: the companion follows well but has no walking
animation; it glides in its idle pose. Every NPC is the same.

## Where

The NPC model bake samples only the idle group of the original animation files into vertex frames
(see [Modular NPCs](../MODULAR_NPCS.md)), and the game logic plays those idle frames only.

## How it happened

The first NPC bake targeted standing residents; moving NPCs (companions, chasing and fleeing actors) came
later.

## Why it was not caught

Residents stand still in every earlier test scene.

## Reproduction

`dbg companion test` in Balmora and walk: the companion moves without walking.

## Repair

Planned: sample every animation group (walk, run, turn, swim, fight, die, idle) for every character type
(male, female, beast races, special NPCs, creatures) once per shared body part, with the sounds the game
ties to them, and let the game logic choose the group and playback rate from the movement, the way the
original game does (checked against the game data and OpenMW).

## Verification

Pending.

## Prevention

The animation kit's tests cover every character type and animation group.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
