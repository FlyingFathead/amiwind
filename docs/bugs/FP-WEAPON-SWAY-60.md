# FP-WEAPON-SWAY-60: The weapon in first-person view moves more while walking than in the original

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.61-dev1 at 2026-11-05 21:32 +0200: Decision of the maintainer after playing v0.0.61-dev1: the held weapon's sway in first person is kept as it is; with a melee weapon it reads as a deliberately lively, slightly cartoonish style rather than a fault. The original keeps the hands still and moves them only on an attack. A switch for a still-hands view is planned: a debug command, a saved setting and a row in the Options menu, with the sway on by default. The sway's cost per frame on a 68040 is to be measured; if it proves heavy on slower machines, the still-hands view also serves as the lighter choice.
- Reported with v0.0.61-dev1 at 2026-11-05 22:37 +0200: Decided: the held weapon's sway becomes a setting with two styles, chosen in the Options menu, the debug menu and the console and kept with the settings. Style 1, AmiWind groove, is today's sway and the default; style 2, Morrowind stiff, keeps the hands still and moves them only on an attack, as the original does. The sway costs a few sine and cosine calculations per frame and no extra drawing; its cost on a 68040 is to be measured.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 5 November 2026, in v0.0.61-dev1 |
| Where | Engine: first-person weapon bob |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.61-dev2 |
| Severity | low: a visual difference from the original; nothing breaks |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.61-dev1 |
| From commit | source 374d59b, engine 374d59b, CHIM world 374d59b |
| CHIM engine version | CHIM 0.2.2, engine 374d59b, world format unknown |
| Unknown because | a playtest report on the delivered dev build |
| Platform or emulator | the delivered v0.0.61-dev1 image (playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev1 (5 November 2026)._

## Status: 5 November 2026

Open, kept by decision and becoming a setting. Present in v0.0.61-dev1.

## Symptom

In first-person view, a held weapon such as a club or a mace swings and bobs noticeably while the player walks,
more than in the original game, where the hands stay still and move only on an attack. Seen by the maintainer while
playing v0.0.61-dev1.

## Where

The first-person view: the engine's view bob and idle sway (view.c, V_CalcBob and the idle sway), applied to the held
weapon. The third-person body and the actors are not affected.

## How it happened

The engine keeps its own view bob and idle sway from its Quake origins. The held weapon follows them, so it moves with
every step. The original game has no such sway.

## Why it was not caught

The first-person view was checked for the weapon being shown and drawn correctly, not for how it moves compared with
the original.

## Reproduction

Equip any melee weapon, switch to first-person view and walk: the weapon swings with each step.

## Repair

After playing it, the maintainer decided to keep the sway as a style of its own. It becomes a setting with two styles,
chosen in the Options menu, the debug menu and the console, and kept with the settings:

- Style 1, AmiWind groove: today's sway, and the default.
- Style 2, Morrowind stiff: the hands stay still and move only on an attack, as in the original.

The sway costs one square root and a few table-based sine lookups per frame and no extra drawing. Its time per frame
on a 68040 is to be measured.

## Verification

To check on the next development build: both styles in first-person view while walking and attacking, and the setting
kept after a restart.

## Prevention

The first-person view is compared with the original for movement as well as for the drawn weapon.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- FIRST-PERSON-WEAPON-SETS-MISSING-54 (no report page): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- FP-FOREARMS-BELOW-VIEW-61 (no report page): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- PLAYER-EQUIPMENT-NOT-WORN-54 (no report page): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- PLAYER-PARTS-BAKE-REFUSED-59 (no report page): Two body part meshes are refused by the assembled player body's parts library
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

<!-- END GENERATED CATEGORY -->
