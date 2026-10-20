# PLAYER-TORCH-THIRDPERSON-38: Player torch and holding pose disappear in third person while light remains

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 9 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Maintainer repeat: F unsheathes fists successfully; V after F produces world light but no third-person carried torch pose or animation.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Original human/beast and common first-person torch groups confirmed. Player companion/pose remains unwired; guard overlay has layout limits. No torch/native acceptance.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Maintainer now requires third-person torch holding in RC2. Source integration IN PROGRESS; exact bake/tests/native/package/maintainer acceptance pending. Swimming scope unchanged.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): RC2 torch source candidate implemented. All 20 companion bake/readbacks, 35 converter and 36 runtime checks pass. Exact target/native, matched original, package/maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-14 (time not recorded): Scoped native Nord F-then-V hold/movement/off and first-person control observed; original game/audio clip retained. Exact full package/reference and maintainer acceptance pending.
- Reported with v0.0.43-dev2 at 2026-10-18 16:41 +0300: maintainer: the inventory character display does not show the equipped torch either; it should hold it
- Reported with v0.0.44-dev1 at 2026-10-19 15:56 +0300: maintainer, vanity camera: the player shows the raised-arm torch pose but no torch in the hand
- Reported with v0.0.44-dev1 at 2026-10-19 15:57 +0300: maintainer: every third-person camera, not only the vanity camera; the raised-arm pose shows, the torch model is missing
- Reported with v0.0.45 at 2026-10-20 02:22 +0300: source diagnosis: held torch alias never reloaded after a cache eviction (aw_view.c view_held) and never drawn in the inventory picture; fix in code with regression tests, needs gate and in-game check

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Third-person player body and equipment |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2, v0.0.39-rc1, v0.0.43-dev2, v0.0.44-dev1 (last seen) |
| Severity | medium: Visible player equipment and ready-state feedback are missing. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM 0.2.0, engine c2eaa5a, world format unknown |
| Unknown because | World format not transcribed into this report. |
| Platform or emulator | unknown (Maintainer did not specify emulator.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 9 times; something has to be done](#persisting-reported-9-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Underwater torch follow-up, 12 October 2026](#underwater-torch-follow-up-12-october-2026)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [RC1 repeated equipment report, 13 October 2026](#rc1-repeated-equipment-report-13-october-2026)
- [Original torch-group availability, 13 October 2026](#original-torch-group-availability-13-october-2026)
- [Required RC2 scope, 13 October 2026](#required-rc2-scope-13-october-2026)
- [Implemented RC2 torch candidate, 13 October 2026](#implemented-rc2-torch-candidate-13-october-2026)
- [Native candidate findings, 14 October 2026](#native-candidate-findings-14-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Cause of the missing torch, 20 October 2026](#cause-of-the-missing-torch-20-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Maintainer reports a regression in v0.0.38-dev2: equip a torch and switch to third person; illumination remains, but the torch model, torch animation and raised holding pose are absent.

## Where

Third-person player body and its equipment animation in v0.0.38-dev2.

## How it happened

Source diagnosis, 13 October 2026: aw_view.c renders a race/sex body without an
equipment companion or torch pose. AW_TorchDraw explicitly returns when the
chase camera is active; the first-person flame is therefore hidden, while the
independent dynamic light can remain. The existing guard-torch converter overlays
the original left clavicle and attaches equipment to Shield Bone, but its kit
companions only cover idle frames. Its old 8/21-frame phase convention cannot be
reused unchanged for the player's variable animation layout.

## Why it was not caught

No exact-package third-person equipment transition check is attached. General
camera or NPC animation checks do not establish player equipment behavior.

## Reproduction

Repeat the maintainer scenario above in dev2, recording race, equipment, view changes,
idle and movement. Independent native reproduction remains pending.

## Repair

RC2 source candidate integrates an original torch-pose player body, held mesh and frame-aligned emitter following the maintainer's explicit requirement. Reuse the existing player-body and animation machinery, check
the original/OpenMW equipment poses and transitions, and preserve working light
and first-person behavior. The torch regression history needs comparison with
an earlier exact package before identifying a first-bad build.

## Verification

Fix in code (20 October 2026, see "Cause of the missing torch" below); it needs
the engine gate and an in-game check: third person at night on a Balmora street,
torch equipped (F then V and V alone), idle, walk and run, the vanity camera, the
inventory picture, headlamp off and on, with a clip. No maintainer acceptance yet.

## Prevention

Exact-package checks must cover equipment meshes and poses independently of
lighting, in both first and third person, at idle and while moving.


## Underwater torch follow-up, 12 October 2026

The maintainer also reports that the torch can be lit underwater and asks to keep
this in the same torch report. Verify the original Morrowind/OpenMW rules for
lighting, extinguishing, equipping and swimming before implementing the state
gate. This behavior is reported, not yet independently reproduced. Test initial
water entry, lighting while submerged, surfacing, fuel and save/load separately.

Source review, 13 October 2026: aw_torch.c checks living player, assets and hand
state in AW_TorchEquipped and the toggle command, but does not reject swimming
or submersion. The world.qc hand update has no water restriction either. This
corroborates the missing equipment gate; it is not an independent native replay.
OpenMW 0.48 removes the held light when swimming and plays a torch-out sound
for the player. This is an equipment transition, not just hiding the flame.
See the original [equipped-light rules](https://raw.githubusercontent.com/OpenMW/openmw/openmw-0.48.0/apps/openmw/mwmechanics/actors.cpp).
Calibrate the swimming threshold through the [water gameplay audit](WATER-GAMEPLAY-PARITY-38.md)
before implementing the transition. Preserve first-person lighting and fuel
controls on dry land; verify inventory and save/load effects separately.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-152017`: SHA-256 `e53bd537e39bdae534cd1a83ca7e5c3d3093ef284a94a760eaa18654becaea8e`. Underwater view shows a torch. Still frame cannot establish swimming animation.

## RC1 repeated equipment report, 13 October 2026

The maintainer confirms that F unsheathes the fists in third person. Pressing V after F lights the world, but the third-person torch model, holding pose and animation are still absent. Preserve this as a repeat of the carried-torch issue, independent of bare-hand draw/lower and punch work. No repaired torch candidate or acceptance follows from the light turning on. Reproduce the F then V sequence in both views, stationary and moving, and compare the equipped mesh and pose with the original.

## Original torch-group availability, 13 October 2026

Read-only inspection of the original human and beast skeletons confirms an authored torch group; the common first-person skeleton also contains it. The female third-person override contains locomotion overrides without torch keys and uses the shared base for absent groups. The female and beast first-person overrides do not contain torch keys; the shared first-person source supplies the group. X/KF counterparts agree with the corresponding source key sets. This records group availability only; no original game files or animation data are exported here.

The missing third-person torch is an integration gap: the player has no carried torch companion/pose, AW_TorchDraw hides the first-person flame in chase view, and dynamic lighting can continue independently. Existing guard-torch code overlays the authored left clavicle and attaches the mesh, but its idle/old8-or21-frame phase convention cannot be reused unchanged for variable player gait/action layouts. Preserve this limitation and the dry-land first-person behavior. Reuse the original pose through bounded offline sampling only after equipment/state, idle/moving, water and budget checks; this audit introduces no torch implementation into RC2.

## Required RC2 scope, 13 October 2026

The latest maintainer instruction requires the carried third-person torch and authored holding animation to be repaired for RC2; this supersedes its earlier v0.0.40 deferral. Source integration is in progress. The confirmed original torch keys and existing guard/player equipment machinery are inputs, not a completed repair receipt.

Integrate the player mesh, left-arm pose and emitter with variable idle/moving/action layouts while preserving working first-person presentation, independent light behavior, budgets and character/view/state transitions. Exact source implementation and automated/bake receipts must be supplied before pinning, followed by native idle/walk/run/view-toggle/F-then-V controls and matched original-game comparison. No native, complete RC2 image/package or maintainer acceptance is claimed. Swimming/diving and wider underwater gameplay remain separate open work; this instruction does not expand them into the current repair scope.

## Implemented RC2 torch candidate, 13 October 2026

The converter now bakes an alternative player body with the original left-arm
torch hold over the ordinary movement poses, a held equipment mesh and aligned
emitter points. Runtime selects these companions in third person when equipped,
copies the displayed body frame/transform for held equipment and reuses the
existing bounded torch/guard light machinery. Equipment and attack layers remain
separate; preserve first-person behavior and state/view/character transitions.
This reuses AmiQuake alias rendering/cache mechanisms and the existing original
guard-torch overlay rather than assuming its old idle frame convention applies.

The isolated Nord male probe passes: 56 frames, 376,608-byte torch body and
239,504-byte held mesh preserving 238 source torch triangles. The completed
all-appearance run passes 20/20 companion sets with exact bake/readback records;
base 20 body model/layout files remain unchanged. Thirty-five converter and
36 runtime focused checks pass against their respective source snapshots,
including the actual torch-light fixture. These are source/automated/bake facts.

Fresh target compilation, complete image/package readback and matched native
first/third-person idle/walk/run/F-then-V/view/state controls remain required.
No visual repair or maintainer acceptance is established by these checks. Leg seams,
swimming/diving and wider original water/equipment parity retain their existing
open requirements. The prior in-progress scope entry remains historical.

## Native candidate findings, 14 October 2026

Target compilation and scoped Nord native F-then-V, hold/walk/run, torch-off and first-person control pass; an unaltered game/audio clip shows the carried mesh and raised arm. All 20 companions pass bake/readback. Matched original, complete image/package and maintainer acceptance remain pending.

## Post-pin RC2 package observation, 14 October 2026

The independently extracted RC2 package shows a raised left arm and carried torch on Nord, then torch-off and water/land model selection. Full disk readback verifies all 20 body/held-torch companions. Scoped native evidence is not all-appearance or matched-original visual acceptance; maintainer acceptance remains pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

## Cause of the missing torch, 20 October 2026

The v0.0.44-dev1 reports narrow the symptom: in every third-person camera the
raised-arm torch pose shows but the torch itself does not, and the inventory
picture shows no torch either. The raised arm only exists in the torch body, so
the torch body and its held torch were both admitted; the held torch was then
not drawn. Two causes in the engine:

1. The held torch never came back after a cache eviction (engine/aga/src/aw_view.c,
   view_held). The torch body and the held torch are two optional alias models in
   Quake's model cache. Any later load (an NPC, a guard torch pair, a map chunk, the
   inventory pose model) can evict either one. The body survives that: the alias
   renderer reloads its own entity through Mod_Extradata. The held torch was drawn
   only while Cache_Check still found it, and nothing ever loaded it again, so after
   one eviction the arm stayed raised and the torch was gone for the rest of the
   area (the light stayed: it is the player's own light, separate from the model).
   The RC2 check of 14 October was a short scoped run in a small scene where nothing
   evicted it; v0.0.43 and v0.0.44 load far more into the cache (whole-island CHIM,
   guard torches at night, inventory pictures), which is why the report came back.
2. The inventory picture never drew the held torch (aw_view.c
   AW_ViewInventoryEquipment draws only a right-hand weapon and a shield): the torch
   pose was shown without its torch.

Rule from OpenMW npcanimation.cpp (showCarriedLeft) and characterpreview.cpp
(InventoryPreview::update): the carried-left light is a part of the character that
is always attached while it is shown, in the world and in the inventory doll, where
the torch group plays on the left arm. Our own implementation, nothing copied:

- held_ready() in aw_view.c: an evicted held torch is loaded again in the same slot,
  under its first admission's rule (2 MiB free hunk), at most once a second
  (AW_ViewHeldRetry in aw_view_rules.c), and only with the torch body's frame count.
  The held draw no longer requires the body to be in the cache that frame (the
  renderer reloads the body; the torch only copies its frame and placement).
- AW_ViewInventoryHeld in aw_view.c, drawn by AW_InventoryPreviewDraw in aw_head.c:
  the held torch at the torch body's frame and placement in the inventory picture.

Why the earlier attempts did not hold: they built and checked the assets (20 of 20
torch body and held torch pairs baked and read back) and one short native run;
nothing tested the held torch after the cache had to make room, and the inventory
picture was out of their scope. Regression checks: tests/aga_view_test.c (retry
rule), tests/aga_inventory_pose_test.c (eviction and reload through the real
aw_view.c), tests/aga_inventory_preview_test.c (the torch drawn in the inventory
picture) and tests/test_third_person.py (the draw path uses the re-admission). All
four fail on the code before the fix.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

Related bugs in other categories:

- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

<!-- END GENERATED CATEGORY -->
