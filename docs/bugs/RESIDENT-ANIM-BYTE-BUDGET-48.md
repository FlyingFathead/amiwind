# RESIDENT-ANIM-BYTE-BUDGET-48: a room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/prepare_area.py build_resident, tools/npc_library.py bake_standing (budget ladder) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48-dev2 |
| Severity | high: one NPC over the byte budget stopped the room batches stage of the v0.0.48-dev2 release build (935 rooms, about 23 minutes lost) |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try4_277bb8c2 |
| From commit | source 277bb8c, engine 277bb8c, CHIM world 277bb8c |
| CHIM engine version | CHIM 0.2.1, engine 277bb8c, world format 0.12 |
| Platform or emulator | not in game (the build stopped in the room batches stage; nothing was built into an image) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Why](#why)
- [Fix](#fix)
- [Measured](#measured)
- [Regression tests](#regression-tests)
- [Since ALIAS-BUDGET-32MB-48 (v0.0.48)](#since-alias-budget-32mb-48-v0048)
- [Open](#open)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Fixed in the resident bake and the actor library (branch v0.0.48-resident-budget). Measured on the game data for
all 40 room batches with the build's settings: 2 of 1,769 room residents fall back, both to the standing model.
Not yet seen in a build or in the game.

## Symptom

The v0.0.48-dev2 build (`2026_10_23_v0.0.48-dev2_dev2-try4_277bb8c2`) stopped in the room batches stage
(`chim-room-batches`, 935 rooms) after about 23 minutes, in its resident step:

```
Error: ienas nadus: Alias byte budget exceeded with full samples
```

One NPC stopped every room of the stage.

## Why

The room stage bakes every resident with the animation kit (`--anim-kit on`, profile `react+full`: a standing
model and a mover model from one bake of all the kit's samples). The bake tries a ladder of vertex budgets (480,
384, 320, 256, 192); with the kit, a model whose topology keeps every disconnected panel is checked against the
alias stream's 512 KiB staging limit with all its samples (`npc_geometry.bake`, `full_frame_budget`). For Ienas
Nadus (and Neloth) even budget 192 is over that limit with all the `full` profile's samples, and the last rung's error
stopped the stage. The town stages never had such an NPC; the 1,134 rooms bring heavier outfits (robes, layered
clothing).

## Fix

`prepare_area.build_resident` tries animation levels in order (`resident_levels`) and takes the first that fits:

1. **kit**: the build's profile (`react+full`: the standing model and its mover);
2. **standing**: the kit's standing profile alone (`react`: idle, hit, death; no mover), baked again from that
   profile's own samples, so its shapes, frames and layout match it;
3. **idle**: the idle-only model, the previous method (8 idle frames, no layout).

Only the byte budget moves a resident down a level (the last rung's byte-budget error, or `npc_anim.fit` at the
smallest frame counts); any other bake error still stops the stage. The record says what happened
(`anim_fallback`: the build's profile, the level and profile baked, the reasons), the log prints one line per
resident, the resident report lists them, the room batches stage record counts them by level with their ids
(`residents.anim_fallback`), and the build summary prints the line. The same appearance always takes the same
level, so the same inputs give the same bytes; the unit cache key is unchanged (its inputs).

`npc_library.bake_standing` (the region actor library) has the same ladder and the same fallback; its manifest and
the actor library summary list the appearances that fell back.

The engine plays all three levels: a layout without a mover never swaps models, and a model without a layout plays
its idle frames (`aw_anim.c`; `tests/aga_anim_test.c` parses a layout with no mover token; the town residents had
idle-only models before the kit).

## Measured

23 October 2026, run `/vol/ws8/build/2026_10_23_v0.0.48-dev2_resident-budget-measure_f6671a33`: every resident of
batches 1-40 (935 rooms, 1,769 NPC records) baked with the failed build's stage environment (`react+full`, budget
heads, locked reducer, root rule legacy), 16 cores, 388 s:

| Resident | Level | Profile | Frames | Triangles | Bytes |
| --- | --- | --- | --- | --- | --- |
| ienas nadus | standing | react | 16 | 619 | 323,604 |
| neloth | standing | react | 16 | 620 | 323,848 |

No resident needed the idle level; no other error.

## Regression tests

`tests/test_resident_anim_fallback.py`: the level order; the kit, standing and idle outcomes and their records; the
same outcome for the same inputs; other errors still stop; the ladder's byte error at every rung and `npc_anim.fit`'s
error become the fallback error, a vertex error at the last rung does not; the actor library falls back the same
way; the build summary line.

## Since ALIAS-BUDGET-32MB-48 (v0.0.48)

The byte budget was the 16 MB era's 512 KiB staging limit. The actors' budget is now 768 KiB, sized for 32 MB of
Fast RAM (`npc_anim.ACTOR_BYTE_BUDGET`, the engine's direct alias stream limit `AW_ALIAS_STREAM_LIMIT`, which also
loads such a model on 16 MB). Measured again on the same 1,769 room residents (23 October 2026, read only): none
falls back. Ienas Nadus and Neloth bake the full `react+full` kit: 619 and 620 triangles, standing models of 331,060
and 331,316 bytes, movers of 681,492 and 682,312 bytes. The fallback stays for any kit still over the budget.

## Open

- Ienas Nadus and Neloth in the game with their full kit (walk, run, fight); to check in a room.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
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
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute
- [NPC-VOICE-NONASCII-IDS-48](NPC-VOICE-NONASCII-IDS-48.md): Two Orc NPCs with accented letters in their record ids are left out of the voice table and stay silent
- [NPC-WANDER-NOT-EXECUTED-35](NPC-WANDER-NOT-EXECUTED-35.md): Residents stand still: the original's Wander AI packages (radius, duration, idles) are decoded but not executed
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach

Related bugs in other categories:

- ALIAS-BUDGET-32MB-48 (no report page): The alias model budget is still the 16 MB era's 512 KiB: two NPCs fall back to standing-only animations

<!-- END GENERATED CATEGORY -->
