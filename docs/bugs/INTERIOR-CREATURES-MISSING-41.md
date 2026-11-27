# INTERIOR-CREATURES-MISSING-41: No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.46 at 2026-10-20 20:09 +0300: Listed under Known in this build in the v0.0.46 release notes (still open at the release).
- Reported with v0.0.54-dev1 at 2026-10-27 15:58 +0200: PERSISTING (partly fixed): rooms carry only the creatures their cell lists name; nothing levelled is placed, 1,270 levelled creature references in 293 rooms. Found in the magic MiniWind of v0.0.54-dev1 and taken today by the creatures worker; fix in progress.
- Reported with v0.0.61 at 2026-11-07 03:54 +0200: PERSISTING: the creature census of the v0.0.61 image places 4 of the 533 creatures that the base master places in rooms; 128 creature records are placed only in rooms (the kwama queens, the Sixth House's Dagoth brothers and corprus creatures, Dwemer centurions, named daedra and dead bodies). The census stops a build on any creature it cannot account for; the rooms are tracked here.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 16 October 2026, in v0.0.41-dev4 |
| Where | tools/prepare_area.py populate (cast filter NPC_ only); every converted interior |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.62-dev1 |
| Severity | high: every interior creature is missing, Vivec in his palace among them; dropped silently without a log line |
| Family | Actors and NPCs (`actors-npc`) |
| Fix commit | `3ca3d610` |
| Fixed on | 2026-11-07 |
| Planning item | `TOMB-NO-CREATURES-61` |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev4_full-rings01234-r3_87f6534 |
| From commit | source 87f6534, engine 87f6534, CHIM world 87f6534 |
| CHIM engine version | CHIM 0.2.0, engine 87f6534, world format 0.7 |
| Platform or emulator | not in game (found in the build records; the room has no actor) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.62-dev1 (3ca3d610) | 2026-11-07 | gate 8240 passed on 3ca3d610 | every creature placed in a converted room gets its table row, its library model and an aw_levelled entity in its room map |
| shipped | a numbered build | v0.0.62-dev1 build 2026_11_07_v0.0.62-dev1_full-v0.0.62-dev1_089421b | 2026-11-07 | the delivered build | the build holds 3ca3d610 and 92231a6d |
| confirmed in play | an end-of-quest session | v0.0.66-dev11 build 2026_11_16_v0.0.66-dev11_full-v0.0.66-dev11_26ed570 | 2026-11-16 | the end of the main quest session, run 3, steps 3 and 4 | Dagoth Ur, a creature placed in a converted interior, is there in his chamber and his script and the Heart's act on him (the steps' checks passed) |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-16: reported in v0.0.41-dev4
- 2026-10-16: INTERIOR-CREATURES-MISSING-41: INTERIOR-CREATURES-MISSING-41: the demigod Vivec is not in his palace.
- 2026-10-20 20:09 +0300: seen again in v0.0.46: Listed under Known in this build in the v0.0.46 release notes (still open at the release).
- 2026-10-27 15:58 +0200: seen again in v0.0.54-dev1: PERSISTING (partly fixed): rooms carry only the creatures their cell lists name; nothing levelled is placed, 1,270 levelled creature references in 293 rooms.
- 2026-11-05: TOMB-NO-CREATURES-60: cause found, the rooms' creatures stop at the room stage: TOMB-NO-CREATURES-60: Samarys Ancestral Tomb has no creature in v0.0.61-dev1.
- 2026-11-07: fixed in source: a gated commit, v0.0.62-dev1 (3ca3d610); gate 8240 passed on 3ca3d610: every creature placed in a converted room gets its table row, its library model and an aw_levelled entity in its room map
- 2026-11-07: shipped: a numbered build, v0.0.62-dev1 build 2026_11_07_v0.0.62-dev1_full-v0.0.62-dev1_089421b; the delivered build: the build holds 3ca3d610 and 92231a6d
- 2026-11-07 03:54 +0200: seen again in v0.0.61: PERSISTING: the creature census of the v0.0.61 image places 4 of the 533 creatures that the base master places in rooms; 128 creature records are placed only in rooms (the kwama queens, the Sixth House's Dagoth brothers and corprus ...
- 2026-11-16: confirmed in play: an end-of-quest session, v0.0.66-dev11 build 2026_11_16_v0.0.66-dev11_full-v0.0.66-dev11_26ed570; the end of the main quest session, run 3, steps 3 and 4: Dagoth Ur, a creature placed in a converted interior, is there in his chamber and his script and the Heart's act on him (the steps' checks passed)

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.46 (21 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Timeline](#timeline)
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

Open. The creature bake this fix added (used by `--interior-creatures all` and by the new creature model library)
was tried read-only on every creature mesh the outdoor world can show: 25 of 39 bake, 14 stop
(CREATURE-BAKE-NIF-UNSUPPORTED-47). The same limits apply indoors, so `all` would leave those creatures out with
their errors.

## Symptom
The Palace of Vivec (room map vpi015) is converted and reachable, but Vivec is not in it. In the original the
demigod floats above the floor, meditating in the lotus position. No other creature is placed in any converted
interior either.

## Where
`tools/prepare_area.py` `populate` (the cast filter keeps only `NPC_` references), called for the CHIM town
rooms by `tools/chim_rooms.py` through `import_town.convert_interiors`. The legacy town path defers every
creature the same way ("creature simulation pending", `tools/import_town.py`).

## How it happened
The resident stage was written for humanoid residents: outfits, body parts, the humanoid skeleton bake and the
`aw_npc` entity. Vivec is a creature record (CREA `vivec_god`) with his own model (`r\LordVivec.NIF`), skeleton
and animations (`XLordVivec`), no race and no body parts, so the filter drops him with every other creature.

## Why it was not caught
The drop is silent: no log line and no "left out" entry names the reference, and the actor checks only see the
actors that were placed. The room's conversion record lists him only as "small item or actor deferred".

## Reproduction
Any full build since the CHIM town rooms: `chim-rooms-vivec_city/scene/vivec_city-interiors.json` has 318
residents and none in vpi015; reference 405515 is in no actor record.

## Repair
In the builder on the v0.0.42 line (not in a build yet): `tools/creature_residents.py`, called by the resident
stage (`tools/prepare_area.py` populate). `--interior-creatures listed` (the default) places the creatures in
`config/interior_creatures.json`, Vivec first; `all` (experimental) every creature the grounding policy
classifies; `off` is the method before. A creature's model is its own NIF on its own skeleton, 8 frames over one
loop of its idle group (Vivec: `idle2`, 4.33 to 7.0 s; his AI_W idle chances give Idle2 60 and his model has no
`idle` group), source origin kept: his posed body runs from 13.9 to 33.1 Quake units above his reference point
(438 triangles, 196,208 bytes). His support state is the policy's `levitating` class (aw_ground_mode 1): the
contact fit, the image-stage ground check and the engine's floor snap leave him where the reference puts him,
0.15 units under the converted dais top. OpenMW 0.51 keeps the actor on the floor (the record has neither Flies
nor a Levitate effect) and the lift is the animation's, which is the same within those 0.15 units. A placed
creature is an idle actor like the placed NPCs: no greeting, dialogue or combat yet. Details:
`docs/NPC_GROUND_CONTACT.md` "Interior creatures and the levitating class".

The island-wide case stays open: the base master places 530 creature references in interiors (178 records,
222 cells); with `all`, 494 have no grounding classification yet and 35 are authored dead (no creature death
pose bake). Every one of them is listed with its reason in the stage report.

## Verification
Regression tests: `tests/test_creature_residents.py` (selection per mode with reasons, the idle range, the
policy class, and a listed creature reaching the room's cast and map with aw_ground_mode 1). OpenMW 0.51 at the
same spot shows him meditating above the dais in the `idle2` loop. Pending: the in-game pair (headlamp off/on)
from the MiniWind preset `vivec-palace`.

## Prevention
Every reference the resident stage leaves out is listed with its reason, as the rooms' geometry pass does.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-AMBIENT-STALE-EDICT-57 (no report page): Teleporting from Seyda Neen to the Ascadian Isles crashes the game: NUM_FOR_EDICT: bad pointer (ambient slots of the old map)
- ACTOR-AMBIENT-WALK-COST-59 (no report page): Walking residents can cost 170 to 300 ms each per think in Seyda Neen
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-ATTACK-ONE-CLOCK-69](ACTOR-ATTACK-ONE-CLOCK-69.md): Every weapon swing, shot and hit reaction of a person is timed by one hand-to-hand clip, so the blow lands off the moment the shown weapon strikes
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- [ACTOR-CHECKS-MISS-PLACED-MODELS-69](ACTOR-CHECKS-MISS-PLACED-MODELS-69.md): The build's actor checks cover 6 of about 3,100 placed actors and can judge a model no map uses: the animation coverage table reads only one kind of map file, and the record audit takes the first model it finds per record
- [ACTOR-CLIP-ABOVE-DRAWN-BODY-69](ACTOR-CLIP-ABOVE-DRAWN-BODY-69.md): Every creature collides in a person-sized box, so a creature lower than a person has collision over its back where nothing is drawn, and a swimming creature's box stands above the water surface
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-GROUNDING-CENSUS-CONFLICTS-67](ACTOR-GROUNDING-CENSUS-CONFLICTS-67.md): The exterior grounding census measures seven people listed as standing on the ground as off the ground, and cannot read five effect models as support
- [ACTOR-HIT-CANCELS-OWN-ATTACK-69](ACTOR-HIT-CANCELS-OWN-ATTACK-69.md): A blow taken in the middle of an actor's own swing or spell cast cancels it
- [ACTOR-LEVELLED-INVENTORY-ONE-PICK-66](ACTOR-LEVELLED-INVENTORY-ONE-PICK-66.md): An actor's levelled inventory is chosen once when the game is built, not when the actor is made
- [ACTOR-LEVELLED-NO-WANDER-56](ACTOR-LEVELLED-NO-WANDER-56.md): Levelled creatures (most wild creatures) never wander or aggro: the Wander table held placed actors only
- [ACTOR-PACK-GUAR-MESH-BROKEN-64](ACTOR-PACK-GUAR-MESH-BROKEN-64.md): The pack guar at Ahemmusa Camp is drawn with its body parts scattered apart
- [ACTOR-PACKAGES-NOT-HELD-66](ACTOR-PACKAGES-NOT-HELD-66.md): Travel, follow and escort packages of the people and creature records are not carried by the build
- [ACTOR-QUEUE-OTHER-MAP-67](ACTOR-QUEUE-OTHER-MAP-67.md): Actors still queued when the map changes spawn in the next map at the old map's coordinates
- [ACTOR-RANGED-COMBAT-MISSING-66](ACTOR-RANGED-COMBAT-MISSING-66.md): People and creatures that carry a bow, crossbow or thrown weapon fight hand to hand or with a melee weapon
- [ACTOR-RESPAWN-CORPSE-RULES-66](ACTOR-RESPAWN-CORPSE-RULES-66.md): Dead bodies are never cleared away; the death rules over time need the original numbers
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- [ACTOR-STATE-NOT-READ-ON-SPAWN-54](ACTOR-STATE-NOT-READ-ON-SPAWN-54.md): A spawned actor never reads its actor record back: a killed NPC respawns alive and lowered health resets on re-entry or load
- [ACTOR-STATE-POOL-LIMITS-54](ACTOR-STATE-POOL-LIMITS-54.md): The actor record drops changes past 128 changed actors, 12 item changes or 8 spell changes per actor; package changes of the behaviour records and NPC positions are not saved
- [ACTOR-STEP-STEEP-CONTACT-REFUSED-69](ACTOR-STEP-STEEP-CONTACT-REFUSED-69.md): A walking resident stops where its box touches a too-steep face (the foot of a rock or wall, the top edge of a crate), although the player walks on there
- [ACTOR-STORM-POSE-51](ACTOR-STORM-POSE-51.md): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- [ACTOR-SWING-STRENGTH-NOT-SHOWN-69](ACTOR-SWING-STRENGTH-NOT-SHOWN-69.md): An actor's swing shows no wind-up by strength: the whole clip plays every time and always ends in the large follow-through
- [ACTOR-TABLE-SAME-MAP-RELOAD-67](ACTOR-TABLE-SAME-MAP-RELOAD-67.md): A reload of the map in play joins none of its actor table cells: no creatures until the next map change
- [ACTOR-WANDER-AGGRO-52](ACTOR-WANDER-AGGRO-52.md): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
- [AMBIENT-RESIDENTS-NOT-VISIBLE-54](AMBIENT-RESIDENTS-NOT-VISIBLE-54.md): From the matched pose OpenMW shows four residents on the Seyda Neen square, AmiWind one far figure
- [AMBIENT-UNSTUCK-FLOOD-61](AMBIENT-UNSTUCK-FLOOD-61.md): Walking residents in Seyda Neen keep falling back to the stuck-movement retry
- [AMBIENT-WALK-STUCK-COLLISION-54](AMBIENT-WALK-STUCK-COLLISION-54.md): Eight of 15 resident walks in the Seyda Neen MiniWind ended stuck: the step trace against the CHIM frame collision blocks most routes
- [ANIMKIT-ACTOR-ABI-SITES-35](ANIMKIT-ACTOR-ABI-SITES-35.md): With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)
- [ANIMKIT-COVERAGE-35](ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player
- [ANIMKIT-GROUND-CHECK-LAYOUT-35](ANIMKIT-GROUND-CHECK-LAYOUT-35.md): With the animation kit on, every image step stopped: the actor ground check refused resident models with more than 8 frames
- [ANIMKIT-IMAGE-FORMATS-35](ANIMKIT-IMAGE-FORMATS-35.md): With the animation kit on, the image step stopped late on the kit's layout files: their format was unknown to the palette overlay
- [ANIMKIT-ITEM-TAG-FRAMES-35](ANIMKIT-ITEM-TAG-FRAMES-35.md): With the animation kit on, residents fought without their weapon and shield: the item tag tables had one row per kit sample, not per model frame, and the mover model had none
- [AW-20260928-05](AW-20260928-05.md): Dock guard misses approach interception
- [AW-20260929-01](AW-20260929-01.md): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [BALMORA-PEOPLE-FLOATING-65](BALMORA-PEOPLE-FLOATING-65.md): In Balmora several people stand in the air above the street, as in early versions
- BARTER-SOLD-ITEM-LOST-58 (no report page): A thing the player sells to a merchant who does not stock it leaves the game instead of going into the merchants stock
- [BLIZZARD-NOT-A-STORM-68](BLIZZARD-NOT-A-STORM-68.md): A blizzard was not treated as a storm: no eye-shielding pose and a fixed drift for its snow
- [BUILD-ACTOR-SPEC-EMPTY-ROOMS-66](BUILD-ACTOR-SPEC-EMPTY-ROOMS-66.md): The image stage stopped on the actor spec check: the check did not read the room batch stage's new list of empty cells, so the one NPC of an empty Tribunal cell counted as missing
- [BUILD-ACTOR-SPEC-UNSPAWNABLE-67](BUILD-ACTOR-SPEC-UNSPAWNABLE-67.md): The actor spec check counted every actor table row outdoors as placed, also rows the game cannot spawn
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- [CENSUS-CAPTAIN-OUT-OF-PLACE-69](CENSUS-CAPTAIN-OUT-OF-PLACE-69.md): Sellus Gravius (chargen captain) stands at a different spot than before in the second Census and Excise Office building
- [CENSUS-GUARD-NO-PATH-TO-THIEF-65](CENSUS-GUARD-NO-PATH-TO-THIEF-65.md): A theft in the census office brings the guard only when he can walk to the player: across the table he cannot
- [CENSUS-NPC-NO-ATTACK-ANIM-65](CENSUS-NPC-NO-ATTACK-ANIM-65.md): The opening's people fight back with no attack animation
- CHARGEN-BIRTHSIGN-REVIEW-58 (no report page): Character creation on the v0.0.58-dev5 image: the birthsign step jumps to the confirm box, the review sheet shows an empty name, and Questions is not greyed out without Morrowind.ini
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48](CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48.md): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- [COMBAT-ACTOR-VS-ACTOR-62](COMBAT-ACTOR-VS-ACTOR-62.md): A dialogue answer that sets two characters against each other does nothing: only fights with the player are carried out
- COMBAT-DEAD-ACTOR-RELOAD-59 (no report page): A killed actor briefly starts combat when its scene loads again
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- [COMBAT-KNOCKDOWN-AFTER-ARMOUR-69](COMBAT-KNOCKDOWN-AFTER-ARMOUR-69.md): A knockdown is decided on the damage left after armour instead of the damage before it
- [COMBAT-OPENING-BLOW-ALWAYS-CRITICAL-69](COMBAT-OPENING-BLOW-ALWAYS-CRITICAL-69.md): The player's first blow on any calm actor counts as a strike on an unaware target: critical damage and no evasion, without sneaking
- [COMBAT-PACK-SLOTS-57](COMBAT-PACK-SLOTS-57.md): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- [COMBAT-PLAYGROUND-CREATURE-HUMANOID-61](COMBAT-PLAYGROUND-CREATURE-HUMANOID-61.md): The combat playground group mode draws a cliff racer as a humanoid figure walking on the ground
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMBAT-SHOT-POOL-FULL-SKIPS-68](COMBAT-SHOT-POOL-FULL-SKIPS-68.md): A ranged fighter's shot is skipped without a count when sixteen shots are already in flight
- [COMBAT-SUMMON-ALLY-62](COMBAT-SUMMON-ALLY-62.md): A summoned creature does not fight for the player: the fight has no side where one actor attacks another
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CORPSE-CLOTHES-NOT-UPDATED-62](CORPSE-CLOTHES-NOT-UPDATED-62.md): Clothing, armour and held items taken from a body or a living actor stay drawn on it
- [CORPSE-NEEDS-FIGHT-SLOT-68](CORPSE-NEEDS-FIGHT-SLOT-68.md): A dead actor's body is not laid down when every fight slot holds a living fighter: the body is missing and cannot be searched
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- [CREATURE-BONES-OVER-MAX-54](CREATURE-BONES-OVER-MAX-54.md): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- [CREATURE-BOX-NOT-OWN-MODEL-69](CREATURE-BOX-NOT-OWN-MODEL-69.md): A creature collides in a box of a person's width, not in the box of its own model, so the player can walk into the drawn flank of a wide creature and combat reads a person's height
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- [CREATURE-COMBAT-FRAMES-MISSING-61](CREATURE-COMBAT-FRAMES-MISSING-61.md): In a fight the ancestor ghost asks its model for frames it does not have: "No such frame" fills the console
- [CREATURE-COMBAT-WEAPON-54](CREATURE-COMBAT-WEAPON-54.md): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- [CREATURE-DUPLICATE-SPAWN-WARP-68](CREATURE-DUPLICATE-SPAWN-WARP-68.md): A wilderness mudcrab turns into several copies that stand inside each other and jump between positions; the combat music keeps playing after they are dead
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points
- [CREATURE-FLOATING-SHALK-64](CREATURE-FLOATING-SHALK-64.md): Shalks on Azura's Coast hang high in the air
- [CREATURE-HIT-CHANCE-STEALTH-VALUE-69](CREATURE-HIT-CHANCE-STEALTH-VALUE-69.md): A creature's chance to hit is worked out from its Stealth value where the original uses its Combat value
- [CREATURE-NETCH-BULL-LEG-REDUCED-58](CREATURE-NETCH-BULL-LEG-REDUCED-58.md): The netch bull's reduced model loses a long stretch of one leg (up to 20 units from the source surface)
- [CREATURE-NIXHOUND-HUMAN-MOVES-67](CREATURE-NIXHOUND-HUMAN-MOVES-67.md): A nix-hound moves like a person and attacks with a weapon swing, and its model looks wrong
- CREATURE-RACER-DRAWN-TINY-57 (no report page): The cliff racer is drawn many times too small: a dark speck the size of a bird while its hit box is a full cliff racer
- [CREATURE-RACER-MESH-SPIKE-58](CREATURE-RACER-MESH-SPIKE-58.md): The cliff racer's model is drawn broken: the wings do not join the body, the parts sit apart, and a long spike runs far below
- [CREATURE-SCALE-KEYS-54](CREATURE-SCALE-KEYS-54.md): The Heart of Lorkhan beats by a scale key, and the skeletal animation table format holds no scale
- [CREATURE-SCALE-NOT-HELD-66](CREATURE-SCALE-NOT-HELD-66.md): A creature record's own size (scale) is not carried by the build
- [CREATURE-SUMMONED-62](CREATURE-SUMMONED-62.md): The 16 creatures that summoning spells call up are not built: a summoning has no creature to show
- [CREATURE-TABLE-ROOT-TRAVEL-67](CREATURE-TABLE-ROOT-TRAVEL-67.md): A creature whose root bone is not named Bip01 keeps its walk and run travel in its own animation table: its drawn poses are coarse and it is drawn away from its place
- [DAGOTH-IDLE-BASE-CHECK-66](DAGOTH-IDLE-BASE-CHECK-66.md): The image stage stopped on Dagoth Ur: its actor-frames check took his idle at frames 30 to 37 for a fault, though his map entity loops exactly that span
- [DAGOTH-UR-NO-ANIMATIONS-65](DAGOTH-UR-NO-ANIMATIONS-65.md): Dagoth Ur in Akulakhan's Chamber has no running and no attack animations
- DANCER-OWN-ANIM-IGNORED-53 (no report page): The Suran dancers only idle: an NPC's own animation file (anim_dancingGirl.nif) was ignored by the skeletal actors
- [DIALOGUE-FIGHT-DISPOSITION-57](DIALOGUE-FIGHT-DISPOSITION-57.md): Requested: disposition drives combat as in the original: a low-disposition NPC turns hostile (effective Fight from disposition), Taunt can start a fight
- [DIALOGUE-TEXT-LINKS-57](DIALOGUE-TEXT-LINKS-57.md): Requested: topic names inside an answer are plain text; the original draws them as blue links that ask about the topic
- [DIALOGUE-WINDOW-LAYOUT-57](DIALOGUE-WINDOW-LAYOUT-57.md): Requested: the dialogue window has no disposition bar, no Persuasion and no service entries, as the original has
- [ESSENTIAL-DEATH-MESSAGE-66](ESSENTIAL-DEATH-MESSAGE-66.md): The essential character death message is shown only for deaths in a fight
- [FARGOTH-STANDING-NO-LAYOUT-66](FARGOTH-STANDING-NO-LAYOUT-66.md): Fargoth's and the opening Imperial guard's standing models carry no animation layout
- [FP-TORCH-OUT-OF-HAND-67](FP-TORCH-OUT-OF-HAND-67.md): In first person a held torch floats away from the left hand: a regression, the torch was held in the hand before
- [GAENOR-ATTACKS-AT-START-67](GAENOR-ATTACKS-AT-START-67.md): Two Gaenors, one of them at level 50, attack a new player in the Temple Courtyard
- [GUARD-WALK-REGRESSION-62](GUARD-WALK-REGRESSION-62.md): The guard at the start turns on the spot on his way to his post beside the door and then stands in the player's route into the Census and Excise Office
- [GUARDS-FIGHT-EACH-OTHER-65](GUARDS-FIGHT-EACH-OTHER-65.md): Two guards who come after the player in Seyda Neen start fighting each other
- [HAIR-CHECK-ACTOR-GROUND-1999-54](HAIR-CHECK-ACTOR-GROUND-1999-54.md): The actor ground check still refused skeletal models past 1,999 vertices
- [HALLOWEEN-SCENE-53](HALLOWEEN-SCENE-53.md): Requested: a Halloween scene by 31 October: the game's skeletons, Desele's dancers and Dagoth Ur dance on the animation stage to a beat
- [HEART-EFFECT-SHELLS-OPAQUE-64](HEART-EFFECT-SHELLS-OPAQUE-64.md): The Heart of Lorkhan is baked with its fire shield and its hidden death glows as opaque skin, so the heart itself is covered and its own texture is not seen
- [HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65](HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65.md): In Akulakhan's Chamber the Heart of Lorkhan leaves its place and follows Dagoth Ur to attack the player
- [HELD-ITEM-TABLE-FULL-69](HELD-ITEM-TABLE-FULL-69.md): After a session has met 64 different armed actor models, the actors met after them draw no weapon, shield or carried torch
- [HELD-MODEL-GAPS-54](HELD-MODEL-GAPS-54.md): 17 of 65 shields have no held model
- [HELD-WEAPON-WRONG-MODEL-62](HELD-WEAPON-WRONG-MODEL-62.md): An actor's held weapon is drawn with another actor's model after the opening is skipped
- [INTRO-DOCK-GUARD-BLOCKS-DOOR-62](INTRO-DOCK-GUARD-BLOCKS-DOOR-62.md): Opening: the dock guard turns on the spot on his way to the Census and Excise Office and stops in the doorway
- INVENTORY-PREVIEW-BAKED-BODY-59 (no report page): Inventory preview draws the race's baked body with its own outfit, not what the player wears
- [MERCHANT-ITEM-CAP-58](MERCHANT-ITEM-CAP-58.md): An actor keeps only 12 item changes, so a merchant refuses the thirteenth kind of item sold to it
- [MOURNHOLD-RESIDENTS-NOT-WALKING-69](MOURNHOLD-RESIDENTS-NOT-WALKING-69.md): Mournhold's district residents with a wander package are not seen walking in the residents' census
- [MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58](MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58.md): With the CHIM cache turned off for one start, the game reports its script instance table full and then freezes with a message box up
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-ATTACK-ANIMS-MISSING-65](NPC-ATTACK-ANIMS-MISSING-65.md): Most creatures play only six baked animation groups: no knockdown, spell cast, second or third attack
- [NPC-BAKE-FALLBACK-62](NPC-BAKE-FALLBACK-62.md): Characters the new seam and floor bake cannot fit in the alias budget are baked a second time with the v0.0.62-dev1 body rules
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-BOW-RIGHT-HAND-69](NPC-BOW-RIGHT-HAND-69.md): A bow carried by a person or creature is placed on the right hand: the original attaches a bow to the left hand's weapon bone
- [NPC-CAST-MAGICKA-NOT-PAID-66](NPC-CAST-MAGICKA-NOT-PAID-66.md): A fighter's spell costs it no magicka: the cast's payment names the wrong stat
- [NPC-CONVERSATION-FACING-23](NPC-CONVERSATION-FACING-23.md): NPCs do not turn to face the player in conversation
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HAIR-BACK-MISSING-53](NPC-HAIR-BACK-MISSING-53.md): Some Suran dancers have no hair at the back of the head
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-HEAD-STARVED-WHOLE-HAIR-54](NPC-HEAD-STARVED-WHOLE-HAIR-54.md): With whole hair some heads got only 28 to 52 triangles: Dark Elf women in robes
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-IDLE-TRACK-PLAYER-67](NPC-IDLE-TRACK-PLAYER-67.md): Requested: an idle character turns its head and body slowly towards the player and follows the player's movements (the dock guard in the opening, the clerk of the Census and Excise Office)
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-NO-SPELLCASTING-65](NPC-NO-SPELLCASTING-65.md): Hostile characters never cast spells in a fight
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-RECIPE-FILES-ROOM-HELD-60](NPC-RECIPE-FILES-ROOM-HELD-60.md): With the earlier recipe files, a room's table stays held outdoors and the town's own cells are not read
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-TALK-MOUTH-STILL-69](NPC-TALK-MOUTH-STILL-69.md): Socucius Ergalla (chargen class) no longer moves his mouth while his voice lines play in the Census and Excise Office
- [NPC-TALK-POSES-ONLY-OPENING-69](NPC-TALK-POSES-ONLY-OPENING-69.md): Only the eight hand-built characters of the opening move their mouths when they speak; every other voiced character, built on the shared body model, has no mouth shapes
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-VOICE-TABLE-ADDONS-54](NPC-VOICE-TABLE-ADDONS-54.md): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WALK-RUBBERBAND-69](NPC-WALK-RUBBERBAND-69.md): Walking residents in Seyda Neen (Indrele Rathryon, Eldafire) move forward and then snap back, again and again
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-GRIP-WRONG-69](NPC-WEAPON-GRIP-WRONG-69.md): NPCs do not hold their weapons in their hands while attacking: the weapon floats beside the body (a battle axe, a knife)
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [NPC-WEREWOLF-FIGHTS-ARMED-68](NPC-WEREWOLF-FIGHTS-ARMED-68.md): A character turned into a werewolf by a script is drawn holding nothing but still uses its own weapon and spells in a fight
- [NPC-WEREWOLF-NO-MODEL-66](NPC-WEREWOLF-NO-MODEL-66.md): The werewolf NPCs of Bloodmoon get no model: their hair part has no attached geometry
- [NPC-WEREWOLF-TALK-OFFERED-68](NPC-WEREWOLF-TALK-OFFERED-68.md): The use key offers to talk to a character that a script has turned into a werewolf
- [OPENING-SHIP-DOCK-ACTORS-ROLE-EXCLUDED-69](OPENING-SHIP-DOCK-ACTORS-ROLE-EXCLUDED-69.md): The five people of the prison ship and the Seyda Neen dock cannot be talked to, show no name, never greet or speak an idle line, and run no behaviour of their own
- [OPENING-SHIP-DOCK-SCRIPTS-HAND-ACTED-69](OPENING-SHIP-DOCK-SCRIPTS-HAND-ACTED-69.md): The prison ship's and the dock's people are acted by hand-written opening code instead of their own scripts: fixed-speed walks with eight frames, lines from separate files, hidden by role instead of the script's Disable
- [OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67](OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67.md): The dead bodies the original places outdoors show only when the player arrives in their cell, never when their cell joins around the player
- [OUTDOOR-CREATURES-HOME-CELL-67](OUTDOOR-CREATURES-HOME-CELL-67.md): The cell the player arrives in has none of its levelled creatures: the window's home frame never joins the actor table
- [OUTDOOR-CREATURES-REGRESSION-66](OUTDOOR-CREATURES-REGRESSION-66.md): Regression: no outdoor creatures spawn, no mudcrabs or slaughterfish, though earlier versions had them
- [OUTDOOR-DEAD-BODY-GONE-66](OUTDOOR-DEAD-BODY-GONE-66.md): An outdoor body is gone at once on a later visit: it cannot be looted after leaving
- PICKUP-E-OWNED-NO-TAKE-58 (no report page): On the v0.0.58-dev5 image the activate key on an aimed owned item (the Census Office Quill Pen, red name, red E: Steal) takes nothing; it is not in the inventory after a save and reload
- [PIER-GUARD-WALKS-INTO-DOOR-65](PIER-GUARD-WALKS-INTO-DOOR-65.md): After the race choice the dock guard walks against the office door for about half a minute before stepping aside
- PLAYER-BODY-THIRD-PERSON-GEAR-59 (no report page): Third-person view: the assembled player body shows no worn clothes or armour, and the shield is not drawn
- [PLAYER-GAIT-RATE-VELOCITY-STEPS-69](PLAYER-GAIT-RATE-VELOCITY-STEPS-69.md): The third-person body's walk, run and sneak play a little too slowly: the body reads the player's speed in steps of 16 units
- [PLAYER-ROBE-RUN-ANIM-67](PLAYER-ROBE-RUN-ANIM-67.md): With a robe on, the player's run animation does not play in third person
- [PLAYER-ROBE-WAIST-SEAM-67](PLAYER-ROBE-WAIST-SEAM-67.md): With a robe on, the third-person player body shows a cut at the waist: the robe's skirt and the upper body do not join
- [PLAYER-SPELL-CAP-58](PLAYER-SPELL-CAP-58.md): The player can hold only 8 spell changes, so a ninth bought spell is refused
- [PLAYER-VANITY-WALK-STUCK-67](PLAYER-VANITY-WALK-STUCK-67.md): After the idle vanity camera starts, the player's walk and run animations stop in third person until the next map load
- [PLAYER-WALK-PLAYS-RUN-GROUP-69](PLAYER-WALK-PLAYS-RUN-GROUP-69.md): A fast walker plays the run animation: the walk or run animation is chosen by the speed, not by whether the character runs
- [PLAZA-FABRICANTS-LIVE-AT-START-67](PLAZA-FABRICANTS-LIVE-AT-START-67.md): Plaza Brindisi Dorom holds the fabricants of a later quest from the start of a new game, one ready to attack on sight
- [RANDOM-SPAWN-IDLE-63](RANDOM-SPAWN-IDLE-63.md): Creatures from the Ghostgate random spawn stand idle next to the player instead of attacking
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-LEVELLED-INTRO-ROOMS-62](ROOM-LEVELLED-INTRO-ROOMS-62.md): Addamasartus and Tharys Ancestral Tomb have no levelled creatures: the intro scene converts their rooms without the levelled creature points
- [ROOM-NPC-DEFERRED-VIVEC-66](ROOM-NPC-DEFERRED-VIVEC-66.md): Two interior NPCs of Vivec are not placed: one in the Telvanni Mage room, one in The Lizard's Head
- [ROOM-PLACED-CORPSES-NOT-SPAWNED-68](ROOM-PLACED-CORPSES-NOT-SPAWNED-68.md): Creatures the game places dead in rooms (skeletons, dead scamps, scribs, centurions, the Hall of Ministry's dead rat) are never spawned, so their bodies are missing
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- [SCRIB-NO-ATTACK-65](SCRIB-NO-ATTACK-65.md): A scrib walks its path but never attacks the player on its own
- [SCRIPT-PLACED-ACTOR-NO-RECORD-PACKAGE-69](SCRIPT-PLACED-ACTOR-NO-RECORD-PACKAGE-69.md): A person or creature a script places, or a spell summons, stands still: it gets no wander behaviour of its record
- [SKEL-ANIM-STAGE-52](SKEL-ANIM-STAGE-52.md): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- [SKEL-POSE-GRID-THINS-LIMBS-68](SKEL-POSE-GRID-THINS-LIMBS-68.md): A skeletal model's rest frame is stored on a byte grid spanning every pose, which thins narrow limbs as drawn
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- [SKEL-TABLE-VIVEC-LAYERED-54](SKEL-TABLE-VIVEC-LAYERED-54.md): Vivec's animation table is layered over the whole humanoid base table: 141 groups, 684 KB
- [SKEL-VERTEX-LIMIT-52](SKEL-VERTEX-LIMIT-52.md): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices
- [SOL-COVENTINA-NO-GROUND-CLASS-68](SOL-COVENTINA-NO-GROUND-CLASS-68.md): A Solstheim cell stops converting because one person placed outdoors there has no grounding class yet
- [SUMMON-SPAWN-FRAME-62](SUMMON-SPAWN-FRAME-62.md): The frame a summoned creature appears in takes about 570 ms: its model files and the actor table are read in that frame
- [SWEEP-SEYDA-EIGHT-FAIL-59](SWEEP-SEYDA-EIGHT-FAIL-59.md): dbg sweep reports 8 failing entities in Seyda Neen on a v0.0.59-dev3 MiniWind with the placed world items; the Census Office map reported 3 in v0.0.58 sessions
- [SWIM-BAKED-CLOTHES-60](SWIM-BAKED-CLOTHES-60.md): Swimming in third-person view shows default clothes instead of the player's own
- [TOMB-NO-CREATURES-60](TOMB-NO-CREATURES-60.md): Samarys Ancestral Tomb has no ghosts, skeletons or other creatures
- [TOWN-EXTERIOR-RESIDENTS-REDUCED-BAKE-69](TOWN-EXTERIOR-RESIDENTS-REDUCED-BAKE-69.md): The street residents of Balmora and Vivec are built by a shorter copy of the resident routine: no handling of people placed dead, ground rules by record only, no part tables
- [WANDER-DOOR-RULE-66](WANDER-DOOR-RULE-66.md): A wandering resident can stop at a destination right by a door and stand there; the original sends an idle wanderer near a door walking
- [WEREWOLF-FIGHT-RULES-LEFT-68](WEREWOLF-FIGHT-RULES-LEFT-68.md): In a fight with a werewolf, silver weapons do no extra damage, the werewolf's own sounds are missing and nobody is readier to attack it
- [WEREWOLF-RACE-SCALE-68](WEREWOLF-RACE-SCALE-68.md): A werewolf is drawn at one size whatever the race of the player or the character turned

Related bugs in other categories:

- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- [BUILD-TORCH-CREATURE-RESIDENT-42](BUILD-TORCH-CREATURE-RESIDENT-42.md): Image step stops in the torch guard on Vivec, an interior creature resident placed as an NPC entity
- [MINIWIND-NO-INTERIOR-SCOPE-42](MINIWIND-NO-INTERIOR-SCOPE-42.md): A MiniWind of one room built the whole town: no scope converted only the start room

<!-- END GENERATED CATEGORY -->
