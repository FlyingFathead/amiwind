# ANIMKIT-ACTOR-ABI-SITES-35: With the animation kit on, the image step stopped late, one tool at a time, on actor models with more than the previous 8 or 21 frames (guard torch companions last)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | prepare_guard_torches.py, check_actor_ground.py, chim/frame_map.py; fix: tools/actor_frames.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1, v0.0.39-rc1 (last seen) |
| Severity | high: Three default image builds in a row stopped about 10 minutes in, each on the next tool that hard-coded the previous frame counts |
| Family | Actors and NPCs (`actors-npc`) |
| Playtest version | v0.0.35-dev1 MiniWind animkit companion run c2b7a3e |
| From commit | source c2b7a3e, engine c2b7a3e, CHIM world c2b7a3e |
| CHIM engine version | CHIM 0.1.0, engine c2b7a3e, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41-dev5 (16 October 2026)._

<!-- contents start -->
## Contents

- [Recurrence: 13 October 2026](#recurrence-13-october-2026)
- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Sweep](#sweep)
- [Verification](#verification)
- [Prevention](#prevention)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Recurrence: 13 October 2026

The v0.0.39-rc1 image preflight rejected all twenty newly baked player bodies:
the shared reader still limited total model frames to 64. The existing model
writer permits 256 total frames under the unchanged alias byte budget; the
AmiQuake-derived engine's `AW_AnimParse` limits each animation group to 64.
`Mod_LoadAliasModel` and the existing pose table remain unchanged.

The candidate reader distinguishes total frames from frames per group. It
continues to reject undeclared layouts, groups outside the model and groups
larger than the runtime limit. Legacy NPC profiles and first-person hand-sprite
limits are unchanged. Payload regression covers a multi-group model above 64
total frames, the 256 boundary, an oversized group and a missing layout.

Why this escaped: earlier tests exercised the old NPC profiles, all at most
64 total frames, but did not pass expanded player bodies through final payload
preflight. Full-image readback and target gameplay checks remain required;
source tests alone do not establish a shipped repair.

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, for every site at once, before any image shipped with the kit.

## Symptom

A MiniWind build with the animation kit (on by default) passed the payload preflight and stopped in the image
step: "Guard model must retain the original 8/21-frame actor ABI". It was the third image step in a row to stop
on a tool that assumed the previous actor frame counts (after ANIMKIT-GROUND-CHECK-LAYOUT-35 and
ANIMKIT-IMAGE-FORMATS-35), each about 10 minutes into the build.

## Where

`tools/prepare_guard_torches.py` (guard torch companions), and in the same sweep `tools/chim/frame_map.py`
(CHIM frame map actor contact, the next stop), `tools/check_actor_ground.py` (a 32-frame ceiling),
`tools/prepare_hand_sprites.py` (`decode_mdl`, a 32-frame ceiling). Fix: `tools/actor_frames.py`.

## How it happened

The animation kit gives resident models more frames than the two previous actor layouts: 8 idle frames
(residents) and 21 frames (the town actor: idle 0..7, talk 8..11, blink 12, walk 13..20). With the default
react+full profile a standing resident has 17 frames (idle, hit, death) and wears a mover model with up to 64
frames while it moves or fights. Several tools hard-coded the previous counts, each in its own way, and each
was found only when an image build reached it.

## Why it was not caught

The kit was gated with unit tests and a MiniWind build that stopped at the first such tool; nothing listed the
other sites, and the payload preflight did not check actor frame layouts.

## Reproduction

Any image build with the animation kit on and a guard among the residents (Balmora).

## Repair

One helper knows actor frame layouts: `tools/actor_frames.py`. A model's layout is its animation kit layout
(`<model>.anm`, the groups the engine reads in `aw_anim.c`), else explicitly one of the two previous layouts;
any other model is refused, never skipped. Every site asks it:

- guard torch companions: a kit guard gets a companion of its idle group (frames 0..7; the base geometry is
  still reproduced exactly). The engine draws the companion for those frames and the guard's own model for its
  other groups (its existing frame check), so a kit guard holds the torch while it stands; the registry stays at
  8 or 21 frames;
- the actor ground check, the actor placement fitter and the CHIM frame map actor contact check the idle group
  of every layout;
- the frame ceilings of the alias decoders follow the kit's 64-frame maximum.

The payload preflight runs a new `actor-frames` check over the staged payload first (0.1 s on the MiniWind
payload): every placed actor model has a declared layout, every `aw_npc` model's idle group is frames 0..7 (the
QuakeC idle cycle and the guard companions use them), every layout fits its model and its mover, and every item
tag table has one row per model frame. It found ANIMKIT-ITEM-TAG-FRAMES-35 on the failed run's staged files.

## Sweep

Every site that reads an actor model's frame count or frame indices (10 October 2026, v0.0.35 line c2b7a3e):

| Site | Reads | Verdict |
| --- | --- | --- |
| tools/prepare_guard_torches.py `_body` | 8 or 21 frames, else refused | broke: idle-group companion via the helper |
| tools/prepare_guard_torches.py `registry` | companion frames 8 or 21 | OK: companions stay 8 or 21 (helper constants) |
| tools/guard_torch_heap.py `alias_cost` | companion frames 8 or 21 | OK: companions only |
| engine/aga/src/aw_guard_torch.c | registry frames 8 or 21, frame skip past them | OK: kit frames past the idle group draw the guard without the torch |
| tools/check_actor_ground.py `contact_samples`, `resident_frames` | 8, intro 21 | fixed earlier (ANIMKIT-GROUND-CHECK-LAYOUT-35); now the helper |
| tools/check_actor_ground.py `model_frames` | at most 32 frames | broke for 33-64-frame kit models: kit maximum |
| tools/actor_grounding.py `soles` | through check_actor_ground | OK: now passes the layout |
| tools/chim/frame_map.py `actor_contact` | 8 frames, no layout | broke (next stop): reads the layout |
| tools/prepare_hand_sprites.py `decode_mdl` | at most 32 frames | broke for large kit guards: kit maximum |
| tools/prepare_area.py `build_resident` item tags | one row per kit sample | broke: ANIMKIT-ITEM-TAG-FRAMES-35 |
| engine/aga/src/aw_items.c | tag rows equal model frames | broke for movers: ANIMKIT-ITEM-TAG-FRAMES-35 |
| engine/aga/qc/world.qc `aw_npc_idle` | idle frames 0..7 | OK: every kit profile starts with 8 idle frames; the preflight checks it |
| engine/aga/src/aw_anim.c `AW_AnimDefault` | 8 / 21 without a layout | OK: layout first, explicit previous layouts |
| engine/aga/src/aw_combat.c `layout_default` | 8 / 21 without a layout | OK: layout first |
| engine/aga/src/aw_companion.c `frames_of`, `model_source` | 21-frame walk, else mover | OK: kit movers handled |
| engine/aga/src/aw_speech.c `AW_SpeechPose` | 21-frame np_ intro actors only | OK: kit models have no talk frames |
| tools/npc_faces.py, tools/prepare_intro.py, tools/prepare_npcs.py | write the 21 / 8 layouts | OK: producers |
| tools/npc_lod.py | idle-only residents (LOD skips kit models) | OK |
| tools/map_engine_limits.py `model_extras` | layout sounds, tag items, mover | OK; now also the mover's tag items |
| tools/alias_stream_heap.py, tools/audit_gallery_budgets.py | frame count from the header | OK |

## Verification

tests/test_actor_frames.py: a kit model (idle, walk, run) and the previous 8 and 21-frame models through the
helper, the ground check, the guard companion layouts and registry, the item tags and the payload audit; a sweep
test that fails on a new hard-coded actor frame count outside the helper and the sites listed above. On the
failed run's staged files: the guard companion of the kit guard reproduces its base geometry exactly
(17-frame model, 8-frame companion); the MiniWind animkit build finishes its image (merge-queue entry).

## Prevention

One helper for actor frame layouts, a sweep test against new hard-coded counts, and the `actor-frames` payload
preflight check before the image work.

## Exact RC1 evidence, 13 October 2026

The corrected total-frame reader passed normal RC1 finalization and independent package/body readback for all twenty expanded bodies. The 256 total / 64 per ordinary group distinction preserves byte and layer budgets and legacy refusal. This resolves the observed preflight rejection in the exact RC1 image, while broader native motion/memory and final-version binding remain separate.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- ACTOR-ANNOTATE-ROOM-REFERENCE-48 (no report page): The image step stopped on a room corpse: its actor annotation looked up the support class by id alone, but room actors are classified by reference
- [ACTOR-BAKE-CENTRE-SEAM-48](ACTOR-BAKE-CENTRE-SEAM-48.md): Bradil Elarven (Glassworker's Hall) left unbaked: his centre probe falls through the seam of two floor pieces
- ACTOR-GROUND-BAKE-CHIM-ROOMS-48 (no report page): The image step stopped in the actor ground bake: it loaded the batch-room shell maps as classic collision scenes, and its error named no map
- [ACTOR-SPAWN-DROPTOFLOOR-49](ACTOR-SPAWN-DROPTOFLOOR-49.md): The resident spawn grounding as Quake's droptofloor, one rule with the build's room bake
- ACTOR-STORM-POSE-51 (no report page): Requested: characters shield their eyes in ash and blight storms (the idlestorm pose), as all regular NPCs and the player do in the original, often seen in Ald'ruhn
- ACTOR-WANDER-AGGRO-52 (no report page): Requested: NPCs and creatures wander, idle and aggro by their own record variables (AI packages, Fight), as the original game does
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
- CREATURE-DAGOTH-UR-ABSENT-52 (no report page): Dagoth Ur and the Heart of Lorkhan are not in their rooms: the room creature list never named them, so Akulakhan s Chamber has neither
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
- [RESIDENT-ANIM-BYTE-BUDGET-48](RESIDENT-ANIM-BYTE-BUDGET-48.md): A room resident whose animation kit model is over the alias byte budget at every rung stopped the whole room stage (ienas nadus)
- [ROOM-RESIDENTS-NO-FIT-48](ROOM-RESIDENTS-NO-FIT-48.md): 19 batch room residents have no spot their room's collision supports: slopes, a rope bridge's hull, no floor in reach
- SKEL-ANIM-STAGE-52 (no report page): Requested: a MiniWind animation stage where NPCs of Seyda Neen and Balmora run every action from the shared table, nothing baked
- SKEL-BUDGET-SHAPES-52 (no report page): A skeletal resident with many head shapes fits no budget of the ladder: the Vivec town stage stopped on Too many separate shapes for budget
- SKEL-GROUND-SOLES-52 (no report page): Two skeletal residents found no standing spot in their CHIM rooms: the rest frame soles came out unlike the baked idle soles
- SKEL-GROUP-SPAN-52 (no report page): The beast table s spellcast group spanned 200 seconds of other animations: a phased group was cut from its first key to its last
- SKEL-ITEM-TAGS-52 (no report page): Skeletal actors draw no carried weapon, shield or torch: the item tags hold one row per model frame, and a skeletal model has every table frame
- SKEL-READERS-BLOCK-52 (no report page): The builder s readers of actor models refused or misjudged a skeletal model: the ground check stopped the build, the stream estimate called it unstreamable
- SKEL-VERTEX-LIMIT-52 (no report page): A skeletal actor with the full-detail head (about 3,000 vertices) cannot be read: the skeletal block is read only by the alias stream, which takes at most 2,000 vertices

<!-- END GENERATED CATEGORY -->
