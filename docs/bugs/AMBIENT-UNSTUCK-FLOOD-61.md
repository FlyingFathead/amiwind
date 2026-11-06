# AMBIENT-UNSTUCK-FLOOD-61: Walking residents in Seyda Neen keep falling back to the stuck-movement retry

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 6 November 2026, in v0.0.61-dev2 |
| Where | walking residents: a failed step inside solid (aw_walk.c AW_ActorStep, sv_phys.c SV_CheckStuck) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61-dev2 (last seen) |
| Severity | low: console spam with developer messages on and possibly frame time on the slow machine |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.61-dev2 |
| From commit | source afa644d, engine afa644d, CHIM world afa644d |
| CHIM engine version | CHIM 0.2.2, engine afa644d, world format unknown |
| Unknown because | the CHIM format number of the dev2 image was not read for this entry |
| Platform or emulator | Amiberry on Raspberry Pi 4B, 128 MB Fast; FS-UAE 3.1.66, JIT, A1200 68040, 32 MB Fast |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev2 (6 November 2026)._

<!-- contents start -->
## Contents

- [Status: 6 November 2026](#status-6-november-2026)
- [Symptom](#symptom)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 6 November 2026

Open, repaired on the v0.0.61 line. Fixed once a numbered build with the repair is checked in game.

## Symptom

During the standard benchmark of v0.0.61-dev2 on the Raspberry Pi 4B, in the live Seyda Neen scene with developer
messages on, the console filled with "Unstuck." lines until the benchmark's result line scrolled away; with the
walking residents switched off (`chim actors ambient off`) the result line stayed readable. The same lines appear on
FS-UAE at 32 MB Fast.

## How it happened

"Unstuck." is the developer message of Quake's stuck search (`sv_phys.c` `SV_CheckStuck`), which the player's walk
runs first in every frame. The walking residents step with the player's walk (`aw_walk.c` `AW_ActorStep` calls
`AW_WalkPlayer`), so every resident step runs it too: one position test when the standing box is clear, and up to 164
when it starts inside solid.

In Seyda Neen one resident did nearly all of it: Indrele Rathryon, at the foot of a steep world face on her route (a
face whose normal points 0.26 up, far steeper than walkable). Her box, snapped onto ground that touches that face,
tests as inside solid there (Quake's plane precision at such joins). Each step then searched for a clear spot, the
step into the face failed (no walkable floor under it), and the failed step put her back where she stood, inside, so
the next step searched again: ten searches per walk, until ten failed steps end the walk and the next one leads her
back to the same face. In a 60 s window at the Seyda Neen start, 20 of the 22 searches were hers. The two Imperial
Guards and other residents meet the same face, but their boxes do not start inside.

## Why it was not caught

The resident walk counted steps, failed steps and traces, but not the searches; the message is shown only with
developer messages on, and the Pi bench is the first check that runs with them on in a live town scene.

## Repair

A failed step that started inside solid now settles the walker once on the clear spot the search finds (one unit
aside or a few units up at most, `aw_walk.c` `AW_ActorSettle`), so its next steps start clear. It is the setting
`chim actors ambient settle on`, the default written into `id1/default-game.cfg`; `chim actors ambient settle off` gives the old
behaviour back for comparison. The fix is in the residents' walk, so it applies to every walking resident of the
game, not only Seyda Neen. `chim actors ambient` now prints the searches of the residents' steps (and per second), how
many were settled, their position tests, and the searches of every body; `chim actors ambient list` prints each
resident's own count. A native test (`tests/aga_unstuck_test.c`) runs the engine's own walk, step and search against
a synthetic ground with a 76-degree face: ten searches in ten steps the old way, two with the settle.

## Verification

FS-UAE 3.1.66, A1200 68040 with FPU, JIT, 32 MB Fast, the delivered v0.0.61-dev2 image with the repaired engine. The
two residents put at the spots where they had started inside solid and walked on into the face, nine tries each way:
106 searches and 1,758 position tests the old way, one search per try with every one settled (9 of 9) and 336 tests
with the repair. In Balmora, Vivec and Suran no search repeated. Details in
[docs/performance/FRAME-WAITS.md](../performance/FRAME-WAITS.md), "Walking residents' stuck searches".

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-AMBIENT-STALE-EDICT-57 (no report page): Teleporting from Seyda Neen to the Ascadian Isles crashes the game: NUM_FOR_EDICT: bad pointer (ambient slots of the old map)
- ACTOR-AMBIENT-WALK-COST-59 (no report page): Walking residents can cost 170 to 300 ms each per think in Seyda Neen
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-LEVELLED-NO-WANDER-56](ACTOR-LEVELLED-NO-WANDER-56.md): Levelled creatures (most wild creatures) never wander or aggro: the Wander table held placed actors only
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STATE-NOT-READ-ON-SPAWN-54 (no report page): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- [ACTOR-STATE-POOL-LIMITS-54](ACTOR-STATE-POOL-LIMITS-54.md): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
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
- BARTER-SOLD-ITEM-LOST-58 (no report page): A thing the player sells to a merchant who does not stock it leaves the game instead of going into the merchants stock
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- CHARGEN-BIRTHSIGN-REVIEW-58 (no report page): Character creation on the v0.0.58-dev5 image: the birthsign step jumps to the confirm box, the review sheet shows an empty name, and Questions is not greyed out without Morrowind.ini
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48 (no report page): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- COMBAT-DEAD-ACTOR-RELOAD-59 (no report page): A killed actor briefly starts combat when its scene loads again
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- COMBAT-PACK-SLOTS-57 (no report page): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- COMBAT-PLAYGROUND-CREATURE-HUMANOID-61 (no report page): The combat playground group mode draws a cliff racer as a humanoid figure walking on the ground
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- CREATURE-BONES-OVER-MAX-54 (no report page): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- [CREATURE-COMBAT-FRAMES-MISSING-61](CREATURE-COMBAT-FRAMES-MISSING-61.md): In a fight the ancestor ghost asks its model for frames it does not have: "No such frame" fills the console
- CREATURE-COMBAT-WEAPON-54 (no report page): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- CREATURE-NETCH-BULL-LEG-REDUCED-58 (no report page): The netch bull's reduced model loses a long stretch of one leg (up to 20 units from the source surface)
- CREATURE-RACER-DRAWN-TINY-57 (no report page): The cliff racer is drawn many times too small: a dark speck the size of a bird while its hit box is a full cliff racer
- CREATURE-RACER-MESH-SPIKE-58 (no report page): The cliff racer's model is drawn broken: the wings do not join the body, the parts sit apart, and a long spike runs far below
- CREATURE-SCALE-KEYS-54 (no report page): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- DIALOGUE-FIGHT-DISPOSITION-57 (no report page): Requested: disposition drives combat as in the original: a low-disposition NPC turns hostile (effective Fight from disposition), Taunt can start a fight
- DIALOGUE-TEXT-LINKS-57 (no report page): Requested: topic names inside an answer are plain text; the original draws them as blue links that ask about the topic
- DIALOGUE-WINDOW-LAYOUT-57 (no report page): Requested: the dialogue window has no disposition bar, no Persuasion and no service entries, as the original has
- HAIR-CHECK-ACTOR-GROUND-1999-54 (no report page): The actor ground check still refused skeletal models past 1,999 vertices
- HALLOWEEN-SCENE-53 (no report page): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- HELD-MODEL-GAPS-54 (no report page): 17 of 65 shields have no held model
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- INVENTORY-PREVIEW-BAKED-BODY-59 (no report page): Inventory preview draws the race's baked body with its own outfit, not what the player wears
- MERCHANT-ITEM-CAP-58 (no report page): An actor keeps only 12 item changes, so a merchant refuses the thirteenth kind of item sold to it
- MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58 (no report page): With the CHIM cache turned off for one start, the game reports its script instance table full and then freezes with a message box up
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
- [NPC-RECIPE-FILES-ROOM-HELD-60](NPC-RECIPE-FILES-ROOM-HELD-60.md): With the earlier recipe files, a room's table stays held outdoors and the town's own cells are not read
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- NPC-VOICE-TABLE-ADDONS-54 (no report page): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- PICKUP-E-OWNED-NO-TAKE-58 (no report page): On the v0.0.58-dev5 image the activate key on an aimed owned item (the Census Office Quill Pen, red name, red E: Steal) takes nothing; it is not in the inventory after a save and reload
- PLAYER-BODY-THIRD-PERSON-GEAR-59 (no report page): Third-person view: the assembled player body shows no worn clothes or armour, and the shield is not drawn
- PLAYER-SPELL-CAP-58 (no report page): The player can hold only 8 spell changes, so a ninth bought spell is refused
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
- SWEEP-SEYDA-EIGHT-FAIL-59 (no report page): dbg sweep reports 8 failing entities in Seyda Neen on a v0.0.59-dev3 MiniWind with the placed world items; the Census Office map reported 3 in v0.0.58 sessions
- SWIM-BAKED-CLOTHES-60 (no report page): Swimming in third-person view shows default clothes instead of the player's own
- TOMB-NO-CREATURES-60 (no report page): Samarys Ancestral Tomb has no ghosts, skeletons or other creatures

<!-- END GENERATED CATEGORY -->
