# TORCH-INVENTORY-PICTURE-64

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 November 2026, in v0.0.64 |
| Where | Inventory picture and first person after an unequip (aw_torch.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.64 (last seen) |
| Severity | medium: The picture contradicts the equipment; the torch seems still held. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.64 release (ffdf7d97) |
| From commit | source ffdf7d9, engine ffdf7d9, CHIM world ffdf7d9 |
| CHIM engine version | CHIM 0.2.2, engine ffdf7d9, world format 0.11 |
| Platform or emulator | the v0.0.64 release image |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.64 (11 November 2026)._

## What happens

Unequipping the torch in the inventory leaves a torch in the hand in the inventory's picture.

## Cause

The lit flag of the carried torch was cleared on the next torch update, while the inventory's picture re-rendered on the unequip at once and drew the old torch.

## Fix

With no light in the left hand nothing is lit, at once (the torch test room keeps its own flag). The hands-and-torch test unequips and checks the torch gone before any update.

## Status

Fix on the v0.0.65 line; open until it is seen in the game.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- [DEBUG-TORCH-64](DEBUG-TORCH-64.md): The debug torch no longer lights with V: the console says no light is equipped
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- FIRST-PERSON-WEAPON-SETS-MISSING-54 (no report page): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- [FP-ARMS-CUT-62](FP-ARMS-CUT-62.md): In first person, looking down shows the forearms ending in mid-air, with no upper arms or shoulders behind them
- FP-FOREARMS-BELOW-VIEW-61 (no report page): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- [FP-WEAPON-SWAY-60](FP-WEAPON-SWAY-60.md): The weapon in first-person view moves more while walking than in the original
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- HELD-LIGHT-NOT-IN-HAND-65 (no report page): An equipped candlestick is not held in the hand; readying shows only the fists
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
- [TORCH-HAND-TO-HAND-64](TORCH-HAND-TO-HAND-64.md): With a torch equipped the fists cannot fight, raising them brings the torch back and V cannot put it away
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

<!-- END GENERATED CATEGORY -->
