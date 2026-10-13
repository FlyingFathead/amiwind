# PLAYER-TORCH-THIRDPERSON-38: Player torch and holding pose disappear in third person while light remains

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Third-person player body and equipment |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Visible player equipment and ready-state feedback are missing. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM 0.2.0, engine c2eaa5a, world format unknown |
| Unknown because | World format not transcribed into this report. |
| Platform or emulator | unknown (Owner did not specify emulator.) |

<!-- END GENERATED FACTS -->

## Symptom

Owner reports a regression in v0.0.38-dev2: equip a torch and switch to third person; illumination remains, but the torch model, torch animation and raised holding pose are absent.

## Where

Third-person player body and its equipment animation in v0.0.38-dev2.

## How it happened

Cause unknown. Inspect the existing AmiQuake chase/player-body path in aw_view.c,
animation state selection and the packaged body/equipment assets. Do not assume
a working light proves the torch mesh and animation were included.

## Why it was not caught

No exact-package third-person equipment transition check is attached. General
camera or NPC animation checks do not establish player equipment behavior.

## Reproduction

Repeat the owner scenario above in dev2, recording race, equipment, view changes,
idle and movement. Independent native reproduction remains pending.

## Repair

Pending diagnosis. Reuse the existing player-body and animation machinery, check
the original/OpenMW equipment poses and transitions, and preserve working light
and first-person behavior. The torch regression history needs comparison with
an earlier exact package before identifying a first-bad build.

## Verification

Open, needs fixing. Owner report recorded; no fix or repaired-package acceptance.

## Prevention

Exact-package checks must cover equipment meshes and poses independently of
lighting, in both first and third person, at idle and while moving.


## Underwater torch follow-up, 12 October 2026

The owner also reports that the torch can be lit underwater and asks to keep
this in the same torch report. Verify the original Morrowind/OpenMW rules for
lighting, extinguishing, equipping and swimming before implementing the state
gate. This behavior is reported, not yet independently reproduced. Test initial
water entry, lighting while submerged, surfacing, fuel and save/load separately.


## Owner evidence reconciliation, 13 October 2026

The following owner screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-152017`: SHA-256 `e53bd537e39bdae534cd1a83ca7e5c3d3093ef284a94a760eaa18654becaea8e`. Underwater view shows a torch. Still frame cannot establish swimming animation.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
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
