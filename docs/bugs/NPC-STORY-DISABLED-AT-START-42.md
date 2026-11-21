# NPC-STORY-DISABLED-AT-START-42: Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.61 at 2026-11-07 02:34 +0200: Dreamers stand on the roads from the start of a new game (the maintainer's play); cause: the global script Main never ran, so its run-once Startup never disabled them
- Reported with v0.0.67-dev2 at 2026-11-18 (time not recorded): Seen again with the v0.0.67-dev2 engine (8aa02cf3) on the v0.0.67-dev1 image: after a teleport inside Seyda Neen (the scene spawns again), the actor sweep names two Dreamers (`Dreamer_Talker04`, `Dreamer_Talker05`) and the Argonian of the opening (`agronian guy`) as disabled by a script but drawn. After the first spawn, the test character preset and a save loaded in place, the sweep finds no such actor.
- Reported with v0.0.67 at 2026-11-20 13:57 +0200: Seen in play on the respin image 1246c42 on 19 November 2026: people a script keeps out of the world stay hidden after a load of the map in play.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | resident placement: Startup script disables and journal re-enables not applied |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1, v0.0.61 (last seen) |
| Severity | medium: Sixth House servants appear long before the main quest sends them |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | 2026_10_17_v0.0.42-dev1_full-dev1-proof_5e043ad |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.62-dev1 (b998cb2d) | 2026-11-07 | gate 7722 passed on 4aee681c, which holds it | a new game runs the run-once start scripts, so Startup disables its 102 story references |
| shipped | a numbered build | v0.0.62-dev1 build 2026_11_07_v0.0.62-dev1_full-v0.0.62-dev1_089421b | 2026-11-07 | the delivered build | the build holds b998cb2d |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-17: reported in v0.0.42-dev1
- 2026-10-17: NPC-STORY-DISABLED-AT-START-42: NPC-STORY-DISABLED-AT-START-42: registered: the original's Startup script disables 58 NPCs (the twelve town Dreamers and the Dreamer Prophet among them) and 20 creatures at a new game, and the Dreamers ...
- 2026-11-07: fixed in source: a gated commit, v0.0.62-dev1 (b998cb2d); gate 7722 passed on 4aee681c, which holds it: a new game runs the run-once start scripts, so Startup disables its 102 story references
- 2026-11-07: shipped: a numbered build, v0.0.62-dev1 build 2026_11_07_v0.0.62-dev1_full-v0.0.62-dev1_089421b; the delivered build: the build holds b998cb2d
- 2026-11-07 02:34 +0200: seen again in v0.0.61: Dreamers stand on the roads from the start of a new game (the maintainer's play); cause: the global script Main never ran, so its run-once Startup never disabled them
- 2026-11-18: seen again in v0.0.67-dev2: Seen again with the v0.0.67-dev2 engine (8aa02cf3) on the v0.0.67-dev1 image: after a teleport inside Seyda Neen (the scene spawns again), the actor sweep names two Dreamers (`Dreamer_Talker04`, `Dreamer_Talker05`) and the Argonian of the ...
- 2026-11-20 13:57 +0200: seen again in v0.0.67: Seen in play on the respin image 1246c42 on 19 November 2026: people a script keeps out of the world stay hidden after a load of the map in play.

<!-- END GENERATED TIMELINE -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Timeline](#timeline)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
  - [The runtime route (v0.0.62)](#the-runtime-route-v0062)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The maintainer, 17 October 2026: there are several Dreamers, and they start to appear only after the main
quest has moved on. In AmiWind they stand in their places (Hla Oad, Gnaar Mok, Suran, Ald-ruhn, the roads)
from the start of a new game.

## Where

Resident placement: `tools/import_town.py` (`residents`, towns and CHIM towns) and `tools/prepare_area.py`
(`populate`, rooms and Seyda Neen) place every NPC reference of their cells. Nothing reads which references the
original disables.

## How it happened

The original mechanism (base master records):

- The global script **Main** (which OpenMW always starts, `apps/openmw/mwscript/globalscripts.cpp`
  `GlobalScripts::addStartup`) starts **Startup**, the original's run-once script. Among its 102 `->Disable`
  lines are 58 NPC and 20 creature IDs; the NPCs include `Dreamer Prophet` and `Dreamer_Talker01` to
  `Dreamer_Talker12`, and also quest characters such as Hannat Zainsubani, Wulf and the Cavern of the Incarnate
  ghosts.
- `Dreamer_Talker01` to `12` carry the script **dreamer_talkerEnable**: while the reference is disabled, when
  the journal `A2_2_6thHouse` stands at 50 it enables itself.
- Placements in the base master: `dreamer_talker01` exterior -2,-3, `02` Ald-ruhn, Gindrala Hleran's House,
  `03` Buckmoth Legion Fort, `04` exterior 0,-9, `05` exterior -2,-8, `06` Gnaar Mok, `07` Hla Oad, `08` exterior
  -4,12, `09` exterior -12,11, `10` exterior -8,16, `11` exterior 4,-9, `12` Suran; the Prophet in Vivec,
  Foreign Quarter Underworks.

OpenMW (0.51) runs the start scripts at a new game, and `World::disable`
(`apps/openmw/mwworld/worldimp.cpp`) only takes the reference out of the scene: its local script keeps running,
which is how `dreamer_talkerEnable` can enable it later.

AmiWind has neither the start-script disables nor the journal stages that enable them, so every one of these
references (where a built area contains it) is placed as a normal resident.

## Why it was not caught

Resident placement has always placed what the cell lists; scripted enable state was never part of it.

## Reproduction

Start a new game and go to Hla Oad: the Dreamer stands there.

## Repair

21 October 2026, branch v0.0.47-story-npc (not yet in a build), off by default:

- `tools/start_disabled.py` reads the list from the game data, never a hand list: the scripts the global script
  Main starts (its `StartScript` lines: Startup, VampireCheck, CharGen), their `->Disable` lines outside any `if`
  block (a line inside one is reported as conditional, not applied), and for every disabled reference its type, its
  placements and how it is enabled again: its own script when that script is the simple journal template (a
  journal index read, a guard that returns, one `Enable` under one journal comparison), every other script or
  dialogue result that names `ID->Enable`, otherwise "unknown, needs the script compiler".
- With `--start-disabled original`, the resident stages (`tools/import_town.py` residents for towns and CHIM
  towns, `tools/prepare_area.py` populate for rooms and Seyda Neen) leave the disabled actors (NPC and creature
  records) out of a new game and list each with its map, reference, the start script line and its enable rule
  (`residents.json` `start_disabled`, the area report's `left_out` and `start_disabled`).
- Builder option `--start-disabled placed|original` (environment `AMIWIND_START_DISABLED`, part of the resident
  stages' keys): `placed` is the default (every actor placed, as before; the variable is not set, the reports
  are as before); `original` is the faithful mode, off by default because nothing enables a left-out actor
  during play yet: it would remove the Dreamer Prophet and the quest characters for good. It becomes the default
  once the runtime enable exists (the world state's "disabled at start" records).

What the table holds (Morrowind.esm): 102 disabled references, 78 actors (58 NPCs, 20 creatures), every one with a
single placement. Enable rules: 12 journal (the twelve Dreamers: their script `dreamer_talkerEnable`, journal
`A2_2_6thHouse` == 50), 22 with no script of their own (enabled by a quest script or a dialogue result, e.g. the
Dreamer Prophet by a dialogue result), 9 whose own script never enables them (enabled elsewhere), 35 unknown until
the script compiler exists.

Not done: nothing enables a held actor during play. AmiWind's journal state exists, but no quest stage advances
`A2_2_6thHouse` yet; the table is the input for the world state's "disabled at start" records and the actor
layer. Objects the start script disables (scaffolding, notes, keys, a bucket) are listed but still placed. The
terrain detail tiles of a CHIM town (`tools/chim/build.py`) still count a held resident's spot (only keeps the
original ground samples there).

### The runtime route (v0.0.62)

Reported again with v0.0.61 (7 November 2026): Dreamers stood on the roads from the start of a new game. By then the
runtime pieces existed: the compiled scripts carry out `Disable` and `Enable` on any placed reference, the object
state keeps them in saved games, the CHIM world spawns no disabled actor, and a room hides a disabled actor's entity.
What was missing was the start: the engine never ran the global script Main, so Startup never ran.

- The builder reads the scripts Main starts under `if ( CharGenState == 1 )` (`tools/mwscript/gamedata.py`
  `new_game_scripts`) and writes them as the NEWG section of `id1/mwscript.awm`: Startup and VampireCheck run, the
  character creation script stays with the engine's hand-written opening.
- The engine starts each once when a new game begins, by any opening (`aw_save.c` `AW_SaveReset`, the scripts on
  their next tick: `aw_mwhost.c`, `aw_mwvm.c` `AW_MwvmNewGame`). Startup then disables its 102 references through
  the object state; each Dreamer's own script keeps running while it is disabled and enables it at the main quest's
  stage, as in the original.
- The build check (`tools/mwscript/newgame.py`, in the mwscript stage) stops the build when a new game would start
  nothing, or when a reference placed once that those scripts disable is not bound to its reference number. On the
  game data: 102 disabled references, 78 actors, 101 placed once and bound, 1 placed twice (a plate).
- The builder option `--start-disabled` (above) stays as it was: `placed` is still right, because the game now holds
  the actors back itself and can bring them back.

Not yet seen in game: a new game in a build with this change, then the road north of Seyda Neen (the Dreamer at
cell -2,-8 and the falling mage at -3,-8). A save made before v0.0.62 keeps the world it had.

## Verification

- Unit tests `tests/test_mwscript_new_game.py` (v0.0.62, synthetic master): the reader of Main's new-game block and
  of the unconditional disables, the NEWG section, the build check passing and refusing, `Fall` compiled to nothing,
  and natively the interpreter: a new game runs Startup's disables once, without a new game nothing is disabled.
- Unit tests `tests/test_start_disabled.py` (synthetic script text and a synthetic master, no game data): the
  `->Disable` reader (quoted, bare, comments, conditional lines), the scripts Main starts, the journal template in
  both forms and its refusals, the enable callers, the table, the filter in both modes, the builder option and the
  town resident stage's record.
- Read-only counts against the v0.0.46 release run (2026_10_20_v0.0.46_release_a3fb9b74) and the game data:
  `original` would leave out 11 placed references: around Seyda Neen Dreamer_Talker04, Dreamer_Talker05 and agronian
  guy; Balmora Dreamer_Talker01; Vivec Dreamer_Talker11 and tarvyn faren; Vivec rooms the Dreamer Prophet (Foreign
  Quarter Underworks), drarel andus and frelene acques; Balmora rooms balyn omavel-DEAD and itermerel. None of the
  20 creatures is placed in that build.
- Not yet seen in game: needs a build with the branch and `--start-disabled original` (Hla Oad, Gnaar Mok and the roads are outside the built town
  frames; Seyda Neen, Balmora and Vivec are where the change shows).

## Prevention

The disabled-at-start list comes from the data, and every held actor is written into the stage's report with its
reason and enable rule, so the actor layer (world state "disabled at start") reads the same table. A test fails if
the builder stops exporting the mode to the resident stages.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-AMBIENT-STALE-EDICT-57 (no report page): Teleporting from Seyda Neen to the Ascadian Isles crashes the game: NUM_FOR_EDICT: bad pointer (ambient slots of the old map)
- ACTOR-AMBIENT-WALK-COST-59 (no report page): Walking residents can cost 170 to 300 ms each per think in Seyda Neen
- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-GROUNDING-CENSUS-CONFLICTS-67](ACTOR-GROUNDING-CENSUS-CONFLICTS-67.md): The exterior grounding census measures seven people listed as standing on the ground as off the ground, and cannot read five effect models as support
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
- [ACTOR-STORM-POSE-51](ACTOR-STORM-POSE-51.md): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
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
- [BUILD-ACTOR-SPEC-EMPTY-ROOMS-66](BUILD-ACTOR-SPEC-EMPTY-ROOMS-66.md): The image stage stopped on the actor spec check: the check did not read the room batch stage's new list of empty cells, so the one NPC of an empty Tribunal cell counted as missing
- [BUILD-ACTOR-SPEC-UNSPAWNABLE-67](BUILD-ACTOR-SPEC-UNSPAWNABLE-67.md): The actor spec check counted every actor table row outdoors as placed, also rows the game cannot spawn
- [CAMERA-POV-TAP-LOST-36](CAMERA-POV-TAP-LOST-36.md): A Toggle POV (Tab) tap released before the next frame did not switch the view
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md): In combat, switching to third person (Tab) hides the NPC you are fighting; it reappears back in first person
- [CENSUS-GUARD-NO-PATH-TO-THIEF-65](CENSUS-GUARD-NO-PATH-TO-THIEF-65.md): A theft in the census office brings the guard only when he can walk to the player: across the table he cannot
- [CENSUS-NPC-NO-ATTACK-ANIM-65](CENSUS-NPC-NO-ATTACK-ANIM-65.md): The opening's people fight back with no attack animation
- CHARGEN-BIRTHSIGN-REVIEW-58 (no report page): Character creation on the v0.0.58-dev5 image: the birthsign step jumps to the confirm box, the review sheet shows an empty name, and Questions is not greyed out without Morrowind.ini
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48](CHIM-ACTOR-TABLE-BEFORE-FRAME-MAPS-48.md): The CHIM actor table was written before any frame map existed, so even town residents in it carry no frame-map position (built_rows_used 0)
- [COMBAT-ACTOR-VS-ACTOR-62](COMBAT-ACTOR-VS-ACTOR-62.md): A dialogue answer that sets two characters against each other does nothing: only fights with the player are carried out
- COMBAT-DEAD-ACTOR-RELOAD-59 (no report page): A killed actor briefly starts combat when its scene loads again
- COMBAT-FLYER-FLEES-57 (no report page): A cliff racer that turns hostile cannot reach the player and flees instead of diving to attack
- [COMBAT-PACK-SLOTS-57](COMBAT-PACK-SLOTS-57.md): In a pack of more than four hostiles the fifth never attacks: fallen fighters keep their combat slots
- [COMBAT-PLAYGROUND-CREATURE-HUMANOID-61](COMBAT-PLAYGROUND-CREATURE-HUMANOID-61.md): The combat playground group mode draws a cliff racer as a humanoid figure walking on the ground
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMBAT-SUMMON-ALLY-62](COMBAT-SUMMON-ALLY-62.md): A summoned creature does not fight for the player: the fight has no side where one actor attacks another
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CORPSE-CLOTHES-NOT-UPDATED-62](CORPSE-CLOTHES-NOT-UPDATED-62.md): Clothing, armour and held items taken from a body or a living actor stay drawn on it
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- [CREATURE-BONES-OVER-MAX-54](CREATURE-BONES-OVER-MAX-54.md): Four creature meshes have more bones than AW_SKEL_MAX_BONES (64): 67, 84, 69 and 74
- CREATURE-COMBAT-ANIM-GROUPS-54 (no report page): A creature does not use its own animation groups in a fight
- [CREATURE-COMBAT-FRAMES-MISSING-61](CREATURE-COMBAT-FRAMES-MISSING-61.md): In a fight the ancestor ghost asks its model for frames it does not have: "No such frame" fills the console
- [CREATURE-COMBAT-WEAPON-54](CREATURE-COMBAT-WEAPON-54.md): A creature's carried weapon is not drawn in combat
- [CREATURE-DAGOTH-UR-ABSENT-52](CREATURE-DAGOTH-UR-ABSENT-52.md): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
- [CREATURE-DUPLICATE-SPAWN-WARP-68](CREATURE-DUPLICATE-SPAWN-WARP-68.md): A wilderness mudcrab turns into several copies that stand inside each other and jump between positions; the combat music keeps playing after they are dead
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points
- [CREATURE-FLOATING-SHALK-64](CREATURE-FLOATING-SHALK-64.md): Shalks on Azura's Coast hang high in the air
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
- [HELD-MODEL-GAPS-54](HELD-MODEL-GAPS-54.md): 17 of 65 shields have no held model
- [HELD-WEAPON-WRONG-MODEL-62](HELD-WEAPON-WRONG-MODEL-62.md): An actor's held weapon is drawn with another actor's model after the opening is skipped
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [INTRO-DOCK-GUARD-BLOCKS-DOOR-62](INTRO-DOCK-GUARD-BLOCKS-DOOR-62.md): Opening: the dock guard turns on the spot on his way to the Census and Excise Office and stops in the doorway
- INVENTORY-PREVIEW-BAKED-BODY-59 (no report page): Inventory preview draws the race's baked body with its own outfit, not what the player wears
- [MERCHANT-ITEM-CAP-58](MERCHANT-ITEM-CAP-58.md): An actor keeps only 12 item changes, so a merchant refuses the thirteenth kind of item sold to it
- [MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58](MWSCRIPT-INSTANCE-TABLE-FULL-CACHE-OFF-58.md): With the CHIM cache turned off for one start, the game reports its script instance table full and then freezes with a message box up
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-ATTACK-ANIMS-MISSING-65](NPC-ATTACK-ANIMS-MISSING-65.md): Most creatures play only six baked animation groups: no knockdown, spell cast, second or third attack
- [NPC-BAKE-FALLBACK-62](NPC-BAKE-FALLBACK-62.md): Characters the new seam and floor bake cannot fit in the alias budget are baked a second time with the v0.0.62-dev1 body rules
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
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
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-VOICE-TABLE-ADDONS-54](NPC-VOICE-TABLE-ADDONS-54.md): The 368 Tribunal and Bloodmoon NPCs have no voices
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [NPC-WEREWOLF-NO-MODEL-66](NPC-WEREWOLF-NO-MODEL-66.md): The werewolf NPCs of Bloodmoon get no model: their hair part has no attached geometry
- [OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67](OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67.md): The dead bodies the original places outdoors show only when the player arrives in their cell, never when their cell joins around the player
- [OUTDOOR-CREATURES-HOME-CELL-67](OUTDOOR-CREATURES-HOME-CELL-67.md): The cell the player arrives in has none of its levelled creatures: the window's home frame never joins the actor table
- [OUTDOOR-CREATURES-REGRESSION-66](OUTDOOR-CREATURES-REGRESSION-66.md): Regression: no outdoor creatures spawn, no mudcrabs or slaughterfish, though earlier versions had them
- [OUTDOOR-DEAD-BODY-GONE-66](OUTDOOR-DEAD-BODY-GONE-66.md): An outdoor body is gone at once on a later visit: it cannot be looted after leaving
- PICKUP-E-OWNED-NO-TAKE-58 (no report page): On the v0.0.58-dev5 image the activate key on an aimed owned item (the Census Office Quill Pen, red name, red E: Steal) takes nothing; it is not in the inventory after a save and reload
- [PIER-GUARD-WALKS-INTO-DOOR-65](PIER-GUARD-WALKS-INTO-DOOR-65.md): After the race choice the dock guard walks against the office door for about half a minute before stepping aside
- PLAYER-BODY-THIRD-PERSON-GEAR-59 (no report page): Third-person view: the assembled player body shows no worn clothes or armour, and the shield is not drawn
- [PLAYER-ROBE-RUN-ANIM-67](PLAYER-ROBE-RUN-ANIM-67.md): With a robe on, the player's run animation does not play in third person
- [PLAYER-ROBE-WAIST-SEAM-67](PLAYER-ROBE-WAIST-SEAM-67.md): With a robe on, the third-person player body shows a cut at the waist: the robe's skirt and the upper body do not join
- [PLAYER-SPELL-CAP-58](PLAYER-SPELL-CAP-58.md): The player can hold only 8 spell changes, so a ninth bought spell is refused
- [PLAYER-VANITY-WALK-STUCK-67](PLAYER-VANITY-WALK-STUCK-67.md): After the idle vanity camera starts, the player's walk and run animations stop in third person until the next map load
- [PLAZA-FABRICANTS-LIVE-AT-START-67](PLAZA-FABRICANTS-LIVE-AT-START-67.md): Plaza Brindisi Dorom holds the fabricants of a later quest from the start of a new game, one ready to attack on sight
- [RANDOM-SPAWN-IDLE-63](RANDOM-SPAWN-IDLE-63.md): Creatures from the Ghostgate random spawn stand idle next to the player instead of attacking
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-LEVELLED-INTRO-ROOMS-62](ROOM-LEVELLED-INTRO-ROOMS-62.md): Addamasartus and Tharys Ancestral Tomb have no levelled creatures: the intro scene converts their rooms without the levelled creature points
- [ROOM-NPC-DEFERRED-VIVEC-66](ROOM-NPC-DEFERRED-VIVEC-66.md): Two interior NPCs of Vivec are not placed: one in the Telvanni Mage room, one in The Lizard's Head
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- [SCRIB-NO-ATTACK-65](SCRIB-NO-ATTACK-65.md): A scrib walks its path but never attacks the player on its own
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
- [WANDER-DOOR-RULE-66](WANDER-DOOR-RULE-66.md): A wandering resident can stop at a destination right by a door and stand there; the original sends an idle wanderer near a door walking

Related bugs in other categories:

- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- [SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62](SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62.md): An actor a script enables in a loaded area is not drawn: the falling mage near Seyda Neen falls and dies unseen, his body searchable but invisible
- [SCRIPTED-EVENT-FALLING-MAGE-61](SCRIPTED-EVENT-FALLING-MAGE-61.md): The falling mage north of Seyda Neen does not fall: he is in the world from the start and his scripted fall does not run

<!-- END GENERATED CATEGORY -->
