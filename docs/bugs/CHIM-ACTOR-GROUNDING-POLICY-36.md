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

_Last updated with AmiWind v0.0.42-dev2 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

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

### The seven candidates (decided for the project, 17 October 2026)

The CHIMport run of 17 October 2026 stopped four cells on four of the seven candidates: (-7,9) Lucan Ostorius,
(5,-8) Paur Maston, (-3,5) Viatrix Petilia and (7,-7) Umbra. Their feet stand 137 to 264 units above the support
under them (the land; no static there), none levitates or swims. Decided for the project, 17 October 2026: these
four and the other two placed above the ground (dreamer_talker07, Fjol) are `ground`. The rule comes from OpenMW:
every actor that neither flies nor swims is dropped onto the first surface below on its first update after its
cell loads (`apps/openmw/mwworld/worldimp.cpp` World::adjustPosition, called from
`apps/openmw/mwmechanics/actors.cpp`), so in the game they stand where it drops them. Hentus Yansurnummu stands
in the water (feet below sea level) and is `swimming`, as OpenMW decides from the water level
(World::isSwimming). Recorded in `config/actor_grounding.json` (`decisions`, and the exception's source).

## Verification

- The census on the maintainer's data: 559 of 566 exterior placements measure as ground. All nine missing
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

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STATE-NOT-READ-ON-SPAWN-54 (no report page): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- ACTOR-STATE-POOL-LIMITS-54 (no report page): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- ACTOR-WANDER-AGGRO-52 (no report page): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
- AMBIENT-RESIDENTS-NOT-VISIBLE-54 (no report page): From the matched pose OpenMW shows four residents on the Seyda Neen square, AmiWind one far figure
- AMBIENT-WALK-STUCK-COLLISION-54 (no report page): Eight of 15 resident walks in the Seyda Neen MiniWind ended stuck: the step trace against the CHIM frame collision blocks most routes
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
- CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48 (no report page): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- CREATURE-BONES-OVER-MAX-54 (no report page): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- CREATURE-COMBAT-WEAPON-54 (no report page): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- CREATURE-SCALE-KEYS-54 (no report page): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- HAIR-CHECK-ACTOR-GROUND-1999-54 (no report page): The actor ground check still refused skeletal models past 1,999 vertices
- HALLOWEEN-SCENE-53 (no report page): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- HELD-MODEL-GAPS-54 (no report page): 17 of 65 shields have no held model
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HAIR-BACK-MISSING-53](NPC-HAIR-BACK-MISSING-53.md): Some Suran dancers have no hair at the back of the head
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-HEAD-STARVED-WHOLE-HAIR-54](NPC-HEAD-STARVED-WHOLE-HAIR-54.md): With whole hair some heads got only 28 to 52 triangles: Dark Elf women in robes
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- NPC-VOICE-TABLE-ADDONS-54 (no report page): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- SKEL-ANIM-STAGE-52 (no report page): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- SKEL-TABLE-VIVEC-LAYERED-54 (no report page): Vivec's animation table is layered over the whole humanoid base table: 141 groups, 684 KB
- SKEL-VERTEX-LIMIT-52 (no report page): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices

Related bugs in other categories:

- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground

<!-- END GENERATED CATEGORY -->
