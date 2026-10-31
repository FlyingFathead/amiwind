# CREATURE-BAKE-NIF-UNSUPPORTED-47: The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 21 October 2026, in v0.0.46 |
| Where | creature pose code: tools/npc_geometry.py, tools/creature_residents.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.47 |
| Severity | high: the most common outdoor creatures cannot get a model, so they cannot be placed even once the actor table spawns creatures |
| Family | Actors and NPCs (`actors-npc`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.47-actor-models branch (no build) |
| From commit | source 1db6550, engine 1db6550, CHIM world 1db6550 |
| CHIM engine version | CHIM unknown, engine 1db6550, world format unknown |
| Unknown because | found by a read-only bake of the game data, no image |
| Platform or emulator | not in game (found by a read-only bake, no image) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (21 October 2026)._

<!-- contents start -->
## Contents

- [Status: 21 October 2026](#status-21-october-2026)
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

## Status: 21 October 2026

Open. Later the same day: the creature library is part of the actor library stage, which a build runs only with
`--chim-actor-table on` (not built yet). The meshes that differed from the previous bake were checked against the
files: the plain and animated models hold the same shapes, vertices, triangles and skin, and both pose paths give
the same node transforms; the new method had sampled a looping idle from its start to its stop instead of between
its loop markers (fixed: now 21 of the 25 meshes both methods bake give byte-identical idle models, the kwama
forager among them); the other four (netch bull, netch betty, least kagouti, minescrib) have TCB position keys,
which the previous bake holds still between two equal key values and the new method follows as the curve the file
describes (OpenMW reads them the same way), so the new side is the one that matches the file.

Earlier: repaired in the source behind the creature model library (experimental, not in any build): its new `kf`
method bakes all 39 exterior creature meshes and their 17 scaled variants on the game data (read only), with walk,
run, attack, hit and death frames; not seen in game. The resident stage's own creature bake is unchanged (its
models byte for byte the same).

Found the same day by a read-only bake of every creature mesh the exterior can show (no build). Nothing ships with these
models yet: no build bakes exterior creatures (CHIM-EXTERIOR-ACTORS-MISSING-46).

## Symptom

The resident stage's creature bake (`tools/creature_residents.py`, the pose code of `tools/npc_geometry.py`) bakes 25
of the 39 creature meshes that the exterior references and its levelled creature lists can show, and stops on the
other 14 with one of three errors:

- "Duplicate skeleton node": 7 meshes (the frost and storm atronachs, both guars, the rust rat, the shalk, the
  winged twilight). Their NIFs repeat a node name; the pose code keys its skeleton by node name.
- "Nonlinear key interval needs its authored interpolation": 4 meshes (the cliff racer, the dreugh, the kwama
  worker, the nix-hound). Their idle keys use curve interpolation between keys, which the pose code samples only
  at the keys themselves.
- "no idle animation range in the model's text keys": 3 meshes (the dremora, the golden saint, the skeleton). These
  creatures walk on two legs; their animation is not in their own mesh file.

The three most used exterior lists hold only cliff racers (1,216 references, each with a 75 % chance of none).

## Where

`tools/npc_geometry.py` (Skeleton: node names; the key sampler: interpolation) and `tools/creature_residents.py`
(idle range from the mesh's own text keys), as used by the resident stage for interior creatures and by
`tools/creature_library.py`.

## How it happened

The creature bake was written for one listed interior creature (Vivec, INTERIOR-CREATURES-MISSING-41) and checked on
it; the other creature meshes were not tried. Humanoid NPCs use the shared skeleton file, which has unique node names
and linear keys.

## Why it was not caught

No build bakes the island's creatures; the `all` mode of `--interior-creatures` lists a failing model as left out
with its error, and no build ran it.

## Reproduction

Bake every creature mesh the exterior can show with `tools/creature_library.py` on the maintainer's game data
(read only, models in a scratch folder): 25 baked, 14 left out with the errors above.

## Repair

In the source, experimental (21 October 2026): `tools/creature_pose.py`, used only by the creature model library
(`tools/creature_library.py`, method `kf`, its default). It reads a creature as the original does (behaviour read
from OpenMW 0.51, our own implementation): the animated model is the mesh with an "x" before its name when that
version has its keyframe file; the animation comes from keyframe files (a two-legged creature first takes the shared
`xbase_anim.kf`, then its own); keyframes bind to the first node of a name, so a repeated node name keeps its own
transform instead of stopping the bake; curve keys (quadratic, and TCB with tangents made from tension, continuity
and bias) are sampled as curves; quaternion keys of every type are slerped. The NPC, gallery and resident bakes keep
their own code (`tools/npc_geometry.py`, `tools/creature_residents.py` unchanged): their models are byte for byte the
same (a sample of 16 gallery models and 3 resident creatures hashed with and without the change).

Measured on the game data (read only, models in a scratch folder): 39 of 39 meshes; standing models (16 frames)
238-316 KB, median 246 KB, 9.7 MB together; mover models (38 frames) 354-472 KB, median 371 KB, 14.6 MB together;
78 s on 10 cores (681 CPU s). For the 25 meshes both methods bake, the idle frames agree with the previous bake
within 0.33 units (the largest vertex distance) on 19 meshes; the babelfish (0.58), least kagouti (0.62) and
slaughterfish (1.3; 95 % of its vertices within 0.2) differ a little more; the netch bull, netch betty and kwama
forager differ more (another vertex order or count from the animated model, a 3.6-unit offset). Resolved later
the same day (see the status): the idle loop markers (fixed) and the TCB curves (the new method follows the
file).

## Verification

Bake every exterior creature mesh again: 39 of 39, with an in-game look at each in a MiniWind sandbox (headlamp off
and on, a short clip).

## Prevention

The creature library run reports every mesh it leaves out with its error; a creature mesh census in the tests of the
pose code.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-AMBIENT-STALE-EDICT-57 (no report page): Teleporting from Seyda Neen to the Ascadian Isles crashes the game: NUM_FOR_EDICT: bad pointer (ambient slots of the old map)
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-LEVELLED-NO-WANDER-56](ACTOR-LEVELLED-NO-WANDER-56.md): Levelled creatures (most wild creatures) never wander or aggro: the Wander table held placed actors only
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STATE-NOT-READ-ON-SPAWN-54 (no report page): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- ACTOR-STATE-POOL-LIMITS-54 (no report page): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- [ACTOR-WANDER-AGGRO-52](ACTOR-WANDER-AGGRO-52.md): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
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
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48 (no report page): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- COMBAT-PACK-SLOTS-57 (no report page): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- CREATURE-BONES-OVER-MAX-54 (no report page): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- CREATURE-COMBAT-WEAPON-54 (no report page): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- CREATURE-RACER-DRAWN-TINY-57 (no report page): The cliff racer is drawn many times too small: a dark speck the size of a bird while its hit box is a full cliff racer
- CREATURE-SCALE-KEYS-54 (no report page): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- DIALOGUE-FIGHT-DISPOSITION-57 (no report page): Requested: disposition drives combat as in the original: a low-disposition NPC turns hostile (effective Fight from disposition), Taunt can start a fight
- DIALOGUE-TEXT-LINKS-57 (no report page): Requested: topic names inside an answer are plain text; the original draws them as blue links that ask about the topic
- DIALOGUE-WINDOW-LAYOUT-57 (no report page): Requested: the dialogue window has no disposition bar, no Persuasion and no service entries, as the original has
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

- [CHIM-EXTERIOR-ACTORS-MISSING-46](CHIM-EXTERIOR-ACTORS-MISSING-46.md): Most outdoor NPCs and every outdoor creature are missing: region frames place no actors (93 of 566 exterior NPC references, 0 of 5,415 creature references)

<!-- END GENERATED CATEGORY -->
