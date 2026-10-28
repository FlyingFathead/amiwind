# CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36: In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | Engine: the client's entity list (cl_main.c CL_RelinkEntities) while the third-person body is drawn |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | high: The opponent disappears from view in a fight |
| Family | Actors and NPCs (`actors-npc`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev5_full-coast-arena-seyda-dev5_6c29a23 (playtest v0.0.36-dev5) |
| Platform or emulator | FS-UAE, JIT (dev5 playtest build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 11 October 2026](#status-11-october-2026)
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

## Status: 11 October 2026

Open, reported by the maintainer on 11 October 2026 after playing the v0.0.36-dev5 playtest build on FS-UAE with JIT. The cause is not known yet. The vivec-b job will investigate on a v0.0.37 branch. Target: v0.0.37.
Open, reported by the maintainer on 11 October 2026 after playing the v0.0.36-dev5 playtest build on FS-UAE with JIT. The cause is not known yet. It is investigated on a v0.0.37 branch. Target: v0.0.37.
Fixed on the v0.0.36 line (branch v0.0.36-thirdperson). The maintainer reported it after playing the v0.0.36-dev5 playtest
build on FS-UAE with JIT, and added later that the switch itself triggers it: Tab into third person hides the enemy,
Tab back to first person brings it back. It is ordered into v0.0.36 rc1.

## Symptom

During a fight, pressing Tab to switch to the third-person camera makes the NPC you are fighting disappear. Switching
back to first person brings it back. The same happened with the idle (vanity) camera and the death camera. Every
other character and moving object disappeared with the opponent; in the Arena the moving parts of the pit went too.

## Where

Engine, the client's entity list: `CL_RelinkEntities` in `cl_main.c`, in the step added for the third-person body
(`aw_view.c`, 10 October 2026).

## How it happened

`CL_RelinkEntities` walks the client's entities with a pointer that the loop itself steps (`i++, ent++`). The
third-person step replaced the view entity with the player's body by writing the body's address into that same
pointer (`ent = aw_view_body (ent)`). From then on the loop stepped through the memory after the body in
`aw_view.c` instead of the entity table, so no entity numbered after the player (every NPC) was put on the list of
things to draw. The loop also wrote into that memory (cleared "models", moved "origins", unlinked "efrags"), so
the same mistake could damage other engine state. That makes it the likely root cause of the vanity-camera crash
[CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md), whose safety net counted a link without a
leaf with the vanity camera running.

## Why it was not caught

The third-person camera was tested in the open and in front of the player's own body; no check counted the drawn
entities with the third-person camera active, and no source check looked for a loop that moves its own cursor.

## Reproduction

Reported by the maintainer in normal play of the dev5 playtest build. Steps to try: start a fight with a hostile NPC, press Tab, and watch the NPC; press Tab again.
Always, from the first frame in third person: start a fight (`dbg arena`), press Tab or start the vanity camera
(`aw_camera vanity now`), and watch the opponent. With `dbg rcount 2` the remote state shows the count: on the
dev5 engine, 39 entities in first person, then 1 (the player's body) in the vanity orbit.

## Repair

The body now has its own pointer (`draw`); the loop's cursor is never reassigned, so every later entity is relinked
and drawn as before. The previous behaviour of every camera is unchanged.

## Verification

Same image (the dev5 build) and the same scripted session on FS-UAE with JIT (`tools/engine_smoke.py --script`:
the Arena fight against Nevil Nolor, first person, Tab, the vanity orbit, back to first person):

| Engine | First person | Vanity orbit | Back in first person |
| --- | --- | --- | --- |
| dev5 (6c29a23) | 39 entities | 1 entity, the opponent and the pit gone | 39 entities |
| fixed | 39 entities | 40 entities (opponent, pit, the player's body) | 39 entities |

Both runs passed the boot smoke. A second scripted run on the fixed engine switches with the Tab key itself (which
also needed [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md)) and with `aw_camera third`.

## Prevention

`tests/test_third_person.py`: the relink loop must hand the body through its own pointer and never assign its
cursor, and a sweep over every engine source fails if any `for` loop that steps a pointer cursor reassigns that
cursor in its body. The scripted Arena-fight smoke is kept with the evidence for repeats.

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
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
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

- [CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md): R_StoreEfrags: Bad entity type 270440 ends the game: a leaf link to an entity whose model is NULL (normal play in Seyda Neen; noclip past the Vivec frame edge)

<!-- END GENERATED CATEGORY -->
