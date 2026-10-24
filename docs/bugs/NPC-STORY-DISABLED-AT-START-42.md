# NPC-STORY-DISABLED-AT-START-42: Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | resident placement: Startup script disables and journal re-enables not applied |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | medium: Sixth House servants appear long before the main quest sends them |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | 2026_10_17_v0.0.42-dev1_full-dev1-proof_5e043ad |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

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

## Verification

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

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
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
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [CREATURE-BAKE-NIF-UNSUPPORTED-47](CREATURE-BAKE-NIF-UNSUPPORTED-47.md): The creature bake refuses 14 of the 39 creature meshes the outdoor world can show, the cliff racer, the rat, the guar and the nix-hound among them
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach

Related bugs in other categories:

- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting

<!-- END GENERATED CATEGORY -->
