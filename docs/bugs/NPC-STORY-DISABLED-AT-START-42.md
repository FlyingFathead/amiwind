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

Not yet. The parts it needs, from the original: the references disabled at the start (the Startup script's
`->Disable` lines, read from the data, not a hand list), and for each the condition that enables it (for the
Dreamers `GetJournalIndex A2_2_6thHouse == 50` in the reference's own script; for the others their own quest
scripts). Until AmiWind has the main quest's journal,
the faithful state of a new game is "not placed"; once it has, the engine places them when the journal reaches
that index.

## Verification

Pending the repair.

## Prevention

Pending the repair: a check that every reference the start scripts disable is either left out or placed
disabled, with the reason.

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
- [CHIM-ACTOR-GROUNDING-POLICY-36](CHIM-ACTOR-GROUNDING-POLICY-36.md): A CHIM area outside the shipped towns stops at its chim-town stage: the NPC grounding policy lists only the shipped towns' NPCs, and the check runs 40 minutes into the build
- [COMBAT-RUN-ROOT-DRIFT-33](COMBAT-RUN-ROOT-DRIFT-33.md): Arena fighters' run frames carry the root's forward motion: the body slides ahead and snaps back each cycle
- [COMPANION-NO-RUN-ANIM-33](COMPANION-NO-RUN-ANIM-33.md): The companion slides instead of walking or running, and mimic mode does not mirror the gait
- [INTERIOR-CREATURES-MISSING-41](INTERIOR-CREATURES-MISSING-41.md): No creature is placed in any interior: the resident stage takes NPC records only, so the demigod Vivec is missing from his palace
- [NPC-ANIM-IDLE-ONLY-33](NPC-ANIM-IDLE-ONLY-33.md): NPCs have only an 8-frame idle: walking, running, swimming, hit and death are not animated
- [NPC-ANIMATION-OFFSET-40](NPC-ANIMATION-OFFSET-40.md): Simplified actor vertices keep a fixed offset while limbs rotate
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC resident baking can exceed the alias vertex budget
- [NPC-DAGOTH-BODY-DECIMATION-33](NPC-DAGOTH-BODY-DECIMATION-33.md): Dagoth Ur's body is decimated; his whole model exceeds the alias ceiling
- [NPC-FEMALE-SKELETON-33](NPC-FEMALE-SKELETON-33.md): Female humans are posed on the male skeleton file (base_anim.nif), the original uses base_anim_female.nif
- [NPC-FOLLOW-FLOORS-33](NPC-FOLLOW-FLOORS-33.md): The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds
- [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md): NPC heads decimated into unrecognisable faces
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-NEAR-SKIN-TEXELS-33](NPC-NEAR-SKIN-TEXELS-33.md): Original-head models had blurrier bodies than the budget model
- [NPC-NO-RUN-ANIM-35](NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames
- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance
- [NPC-SPEAR-ATTACK-REGRESSION-39](NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

Related bugs in other categories:

- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting

<!-- END GENERATED CATEGORY -->
