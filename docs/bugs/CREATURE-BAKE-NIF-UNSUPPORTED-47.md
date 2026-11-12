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
- ACTOR-AMBIENT-WALK-COST-59 (no report page): Walking residents can cost 170 to 300 ms each per think in Seyda Neen
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-LEVELLED-NO-WANDER-56](ACTOR-LEVELLED-NO-WANDER-56.md): Levelled creatures (most wild creatures) never wander or aggro: the Wander table held placed actors only
- ACTOR-PACK-GUAR-MESH-BROKEN-64 (no report page): The pack guar at Ahemmusa Camp is drawn with its body parts scattered apart
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STATE-NOT-READ-ON-SPAWN-54 (no report page): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- [ACTOR-STATE-POOL-LIMITS-54](ACTOR-STATE-POOL-LIMITS-54.md): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- [ACTOR-WANDER-AGGRO-52](ACTOR-WANDER-AGGRO-52.md): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
- AMBIENT-RESIDENTS-NOT-VISIBLE-54 (no report page): From the matched pose OpenMW shows four residents on the Seyda Neen square, AmiWind one far figure
- [AMBIENT-UNSTUCK-FLOOD-61](AMBIENT-UNSTUCK-FLOOD-61.md): Walking residents in Seyda Neen keep falling back to the stuck-movement retry
- AMBIENT-WALK-STUCK-COLLISION-54 (no report page): Eight of 15 resident walks in the Seyda Neen MiniWind ended stuck: the step trace against the CHIM frame collision blocks most routes
- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- BARTER-SOLD-ITEM-LOST-58 (no report page): A thing the player sells to a merchant who does not stock it leaves the game instead of going into the merchants stock
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- CENSUS-NPC-NO-ATTACK-ANIM-65 (no report page): The opening's people fight back with no attack animation
- CHARGEN-BIRTHSIGN-REVIEW-58 (no report page): Character creation on the v0.0.58-dev5 image: the birthsign step jumps to the confirm box, the review sheet shows an empty name, and Questions is not greyed out without Morrowind.ini
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48 (no report page): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- COMBAT-ACTOR-VS-ACTOR-62 (no report page): A dialogue answer that sets two characters against each other does nothing: only fights with the player are carried out
- COMBAT-DEAD-ACTOR-RELOAD-59 (no report page): A killed actor briefly starts combat when its scene loads again
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- COMBAT-PACK-SLOTS-57 (no report page): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- COMBAT-PLAYGROUND-CREATURE-HUMANOID-61 (no report page): The combat playground group mode draws a cliff racer as a humanoid figure walking on the ground
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- COMBAT-SUMMON-ALLY-62 (no report page): A summoned creature does not fight for the player: the fight has no side where one actor attacks another
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- CORPSE-CLOTHES-NOT-UPDATED-62 (no report page): Clothing, armour and held items taken from a body or a living actor stay drawn on it
- CREATURE-BONES-OVER-MAX-54 (no report page): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- [CREATURE-COMBAT-FRAMES-MISSING-61](CREATURE-COMBAT-FRAMES-MISSING-61.md): In a fight the ancestor ghost asks its model for frames it does not have: "No such frame" fills the console
- CREATURE-COMBAT-WEAPON-54 (no report page): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points
- CREATURE-FLOATING-SHALK-64 (no report page): Shalks on Azura's Coast hang high in the air
- CREATURE-NETCH-BULL-LEG-REDUCED-58 (no report page): The netch bull's reduced model loses a long stretch of one leg (up to 20 units from the source surface)
- CREATURE-RACER-DRAWN-TINY-57 (no report page): The cliff racer is drawn many times too small: a dark speck the size of a bird while its hit box is a full cliff racer
- CREATURE-RACER-MESH-SPIKE-58 (no report page): The cliff racer's model is drawn broken: the wings do not join the body, the parts sit apart, and a long spike runs far below
- CREATURE-SCALE-KEYS-54 (no report page): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- [CREATURE-SUMMONED-62](CREATURE-SUMMONED-62.md): The 16 creatures that summoning spells call up are not built: a summoning has no creature to show
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- DIALOGUE-FIGHT-DISPOSITION-57 (no report page): Requested: disposition drives combat as in the original: a low-disposition NPC turns hostile (effective Fight from disposition), Taunt can start a fight
- [DIALOGUE-TEXT-LINKS-57](DIALOGUE-TEXT-LINKS-57.md): Requested: topic names inside an answer are plain text; the original draws them as blue links that ask about the topic
- DIALOGUE-WINDOW-LAYOUT-57 (no report page): Requested: the dialogue window has no disposition bar, no Persuasion and no service entries, as the original has
- [GUARD-WALK-REGRESSION-62](GUARD-WALK-REGRESSION-62.md): The guard at the start turns on the spot on his way to his post beside the door and then stands in the player's route into the Census and Excise Office
- HAIR-CHECK-ACTOR-GROUND-1999-54 (no report page): The actor ground check still refused skeletal models past 1,999 vertices
- HALLOWEEN-SCENE-53 (no report page): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- HEART-EFFECT-SHELLS-OPAQUE-64 (no report page): The Heart of Lorkhan is baked with its fire shield and its hidden death glows as opaque skin, so the heart itself is covered and its own texture is not seen
- HELD-MODEL-GAPS-54 (no report page): 17 of 65 shields have no held model
- [HELD-WEAPON-WRONG-MODEL-62](HELD-WEAPON-WRONG-MODEL-62.md): An actor's held weapon is drawn with another actor's model after the opening is skipped
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- INTRO-DOCK-GUARD-BLOCKS-DOOR-62 (no report page): Opening: the dock guard turns on the spot on his way to the Census and Excise Office and stops in the doorway
- INVENTORY-PREVIEW-BAKED-BODY-59 (no report page): Inventory preview draws the race's baked body with its own outfit, not what the player wears
- MERCHANT-ITEM-CAP-58 (no report page): An actor keeps only 12 item changes, so a merchant refuses the thirteenth kind of item sold to it
- MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58 (no report page): With the CHIM cache turned off for one start, the game reports its script instance table full and then freezes with a message box up
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- NPC-BAKE-FALLBACK-62 (no report page): Characters the new seam and floor bake cannot fit in the alias budget are baked a second time with the v0.0.62-dev1 body rules
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
- [NPC-RECIPE-FILES-ROOM-HELD-60](NPC-RECIPE-FILES-ROOM-HELD-60.md): With the earlier recipe files, a room's table stays held outdoors and the town's own cells are not read
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- NPC-VOICE-TABLE-ADDONS-54 (no report page): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- PICKUP-E-OWNED-NO-TAKE-58 (no report page): On the v0.0.58-dev5 image the activate key on an aimed owned item (the Census Office Quill Pen, red name, red E: Steal) takes nothing; it is not in the inventory after a save and reload
- PIER-GUARD-WALKS-INTO-DOOR-65 (no report page): After the race choice the dock guard walks against the office door for about half a minute before stepping aside
- PLAYER-BODY-THIRD-PERSON-GEAR-59 (no report page): Third-person view: the assembled player body shows no worn clothes or armour, and the shield is not drawn
- PLAYER-SPELL-CAP-58 (no report page): The player can hold only 8 spell changes, so a ninth bought spell is refused
- RANDOM-SPAWN-IDLE-63 (no report page): Creatures from the Ghostgate random spawn stand idle next to the player instead of attacking
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-LEVELLED-INTRO-ROOMS-62](ROOM-LEVELLED-INTRO-ROOMS-62.md): Addamasartus and Tharys Ancestral Tomb have no levelled creatures: the intro scene converts their rooms without the levelled creature points
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- SKEL-ANIM-STAGE-52 (no report page): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- SKEL-TABLE-VIVEC-LAYERED-54 (no report page): Vivec's animation table is layered over the whole humanoid base table: 141 groups, 684 KB
- SKEL-VERTEX-LIMIT-52 (no report page): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices
- SUMMON-SPAWN-FRAME-62 (no report page): The frame a summoned creature appears in takes about 570 ms: its model files and the actor table are read in that frame
- SWEEP-SEYDA-EIGHT-FAIL-59 (no report page): dbg sweep reports 8 failing entities in Seyda Neen on a v0.0.59-dev3 MiniWind with the placed world items; the Census Office map reported 3 in v0.0.58 sessions
- SWIM-BAKED-CLOTHES-60 (no report page): Swimming in third-person view shows default clothes instead of the player's own
- TOMB-NO-CREATURES-60 (no report page): Samarys Ancestral Tomb has no ghosts, skeletons or other creatures

Related bugs in other categories:

- [CHIM-EXTERIOR-ACTORS-MISSING-46](CHIM-EXTERIOR-ACTORS-MISSING-46.md): Most outdoor NPCs and every outdoor creature are missing: region frames place no actors (93 of 566 exterior NPC references, 0 of 5,415 creature references)

<!-- END GENERATED CATEGORY -->
