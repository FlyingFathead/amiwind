# CHIM-ACTOR-GROUNDING-POLICY-36: A new CHIM area's residents stop the build: the grounding policy only knows the shipped towns

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.36-dev1 |
| Where | tools/actor_grounding.py initial_state; config/actor_grounding.json; chim-town stage |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36-dev1 |
| Severity | high: Every new CHIM area with residents (every CHIMport region) stops the build; found only after the expensive stages |
| Family | Actors and NPCs (`actors-npc`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_10_v0.0.36-dev1_full-bcoast-chimtest_9e195a7 |
| From commit | source 9e195a7, engine 9e195a7, CHIM world 9e195a7 |
| CHIM engine version | CHIM 0.1.0, engine 9e195a7, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in v0.0.36-dev1. Every NPC placed in an exterior cell of the base master is now classified by
measurement, and the build preflight refuses an unclassified resident of a CHIM area in seconds, before any
stage runs. Seven measured candidates (none in a shipped town or in the test area) wait for a sourced decision.

## Symptom

The build stops at the area's chim-town stage, after about 40 minutes of earlier stages:
`Error: Unclassified initial support state: vala herennius`. The stage had already prepared the area's ten
residents from the game data.

## Where

`tools/actor_grounding.py` `initial_state()`, reading `config/actor_grounding.json`, called by the chim-town stage
(`tools/chim_town.py`) for every resident of a CHIM-native area.

## How it happened

The grounding policy is an explicit list: every NPC must be classified as standing on the ground or as a
documented exception (scripted airborne, flying, levitating, swimming, placed dead), and an unclassified NPC is an
error by design, so no behaviour is guessed. The list was written town by town: 454 ground NPCs and 8 exceptions,
all from the towns shipped so far (Seyda Neen, Balmora, Vivec). The first area outside them brought NPCs the list
has never seen: 9 of the block's 10 residents are missing.

## Why it was not caught

No build had a CHIM area outside the shipped towns before. The policy is only read when a stage places actors, so
the gap shows 40 minutes into a build instead of in the preflight, which checks game data, caches and free space
but not the actor policy.

## Reproduction

Always: build a CHIM-native area whose residents are not in `config/actor_grounding.json`
(`build.py --chim-area bcoast_x7y2 --extra-town bcoast_x7y2 --chim-native-towns on`).

## Repair

Two parts, both at the shared layer:

1. `tools/actor_grounding_census.py` measures every NPC placement in the island's exterior cells (566
   placements of 488 NPCs). The feet (the reference position) are compared with the highest support under
   them, sampled at the centre and on a 16-unit foot circle: the land surface (the converter's own triangle
   split) or a triangle of a static object in the same or a neighbouring cell (statics, activators, doors,
   containers and lights, visible and collision triangles, placed as the scenery converter places them). The
   tolerance is what the build itself can fit: the support fitter looks from 32 units inside a support down to
   128 units above it (8 and 40 Quake units at the world scale of 0.25). The original data places most actors
   a little above their support and the engine settles them onto it (OpenMW's actor placement lifts an actor
   that is neither flying nor swimming slightly and traces it down onto the first collision below).
   An NPC is ground only when every exterior placement of it measures within the tolerance, its feet are not
   below sea level and its record carries no Levitate ability. A record that places the NPC dead (health 0)
   gives a documented `authored_dead` exception with that source. Everything else is listed as a candidate with
   its numbers; flying, levitating, swimming or scripted states are never assigned automatically.
   `--write` merges the result into `config/actor_grounding.json`: every existing entry and exception is
   kept; 432 ground NPCs and 5 `authored_dead` exceptions were added (886 ground NPCs, 13 exceptions).
2. The build preflight (`tools/build_preflight.py` `grounding_problems`, run by `tools/build.py` for every
   image build before any stage) lists the NPC residents of every CHIM area of the build from the master's
   exterior cells (the area's frame, minus its documented resident exclusions) and refuses the build with the
   missing IDs. It takes about 2 seconds.

## Verification

- The census on the owner's data: 559 of 566 exterior placements measure as ground. All nine missing
  residents of the test area (Gnaar Mok block) are ground; every CHIM area (Seyda Neen, Balmora, the Vivec
  districts and the test area) passes the preflight.
- Before the policy update the preflight refused the test area with exactly the nine missing IDs, in 2 seconds.
- Regression tests (`tests/test_actor_grounding_census.py`): the frame filter, the refusal with the missing ID,
  the preflight placed before any stage in `tools/build.py`, the tolerance equal to the fitter's search, the
  record facts (placed dead, Levitate ability), a candidate is never classified, and the nine residents
  classify as ground.
- Still to do: the test area's build passing its chim-town stage (the next build of that area).

## Prevention

The policy check runs in the preflight, so a missing classification costs seconds, not a build. A new region
is classified by rerunning the census; its candidates are decided from a cited source (the NPC and script
records, the OpenMW source, the private reference corpus), never guessed.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
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
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

Related bugs in other categories:

- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground

<!-- END GENERATED CATEGORY -->
