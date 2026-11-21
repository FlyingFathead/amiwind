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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| shipped | a development build | v0.0.61-dev2 | 2026-11-06 | the bug journal entry of 2026-11-06: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered | Set fixed in v0.0.61-dev2: CHARGEN-INVENTORY-LOCKED-60, CHARGEN-NO-STARTING-CLOTHES-60, SERVICE-REFUSAL-UNCLOTHED-60, FP-WEAPON-SWAY-60, HELD-BLADE-EDGE-ON-61, CARRIED-RECORDS-SEARCH-PER-KIND-61, INVENTORY-OPEN-COST-MANY-KINDS-61, TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61, MUSIC-DEATH-TRACK-RANDOM-60, BLANK-PAPER-READ-60, COLLECT-CAPACITY-REJECTED-60 and TOMB-MUSIC-OVER-AMBIENT-60. |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-05: reported in v0.0.61-dev1
- 2026-11-05 21:32 +0200: seen again in v0.0.61-dev1: Decision of the maintainer after playing v0.0.61-dev1: the held weapon's sway in first person is kept as it is; with a melee weapon it reads as a deliberately lively, slightly cartoonish style rather than a fault.
- 2026-11-05 22:37 +0200: seen again in v0.0.61-dev1: Decided: the held weapon's sway becomes a setting with two styles, chosen in the Options menu, the debug menu and the console and kept with the settings.
- 2026-11-06: v0.0.61-dev2: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered: The points the v0.0.61-dev2 release notes list as not yet seen in game were played on that image at 32 MB Fast in ...
- 2026-11-06: shipped: a development build, v0.0.61-dev2; the bug journal entry of 2026-11-06: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered: Set fixed in v0.0.61-dev2: CHARGEN-INVENTORY-LOCKED-60, CHARGEN-NO-STARTING-CLOTHES-60, SERVICE-REFUSAL-UNCLOTHED-60, FP-WEAPON-SWAY-60, HELD-BLADE-EDGE-ON-61, CARRIED-RECORDS-SEARCH-PER-KIND-61, INVENTORY-OPEN-COST-MANY-KINDS-61 ...

<!-- END GENERATED TIMELINE -->

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

- [AW-20260928-18](AW-20260928-18.md): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- [DEBUG-TORCH-64](DEBUG-TORCH-64.md): The debug torch no longer lights with V: the console says no light is equipped
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- [FIRST-PERSON-WEAPON-SETS-MISSING-54](FIRST-PERSON-WEAPON-SETS-MISSING-54.md): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- [FP-ARMS-CUT-62](FP-ARMS-CUT-62.md): In first person, looking down shows the forearms ending in mid-air, with no upper arms or shoulders behind them
- [FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67](FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67.md): On a test build of the per-race first-person hands, the first-person arms, the held lantern and its light are not drawn at all, looking ahead or down; the same walk on the earlier build showed the arm, the lantern and its light
- [FP-ARMS-NO-MODEL-SLOT-67](FP-ARMS-NO-MODEL-SLOT-67.md): After the race or sex is changed several times in one place, the first-person arms turn into an old hand model with holes and the held lantern is not drawn
- [FP-BARE-HAND-OTHER-SKIN-67](FP-BARE-HAND-OTHER-SKIN-67.md): In first person the bare hand of some races has another race's skin and looks gloved, unlike the arm
- [FP-FISTS-LUMP-67](FP-FISTS-LUMP-67.md): Drawing the fists in first person shows a lump in the top left corner of the view instead of the fists
- [FP-FOREARMS-BELOW-VIEW-61](FP-FOREARMS-BELOW-VIEW-61.md): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- [FP-HANDS-PER-RACE-67](FP-HANDS-PER-RACE-67.md): In first person the Nord man, the Imperial woman and the Dark Elf and Redguard men show another race's or sex's hand, as the game's records name it, and the skin steps at the wrist
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- [HAND-PUNCH-TRANSITION-29](HAND-PUNCH-TRANSITION-29.md): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- [HELD-LIGHT-NOT-IN-HAND-65](HELD-LIGHT-NOT-IN-HAND-65.md): An equipped candlestick is not held in the hand; readying shows only the fists
- [LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67](LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67.md): With a light and a one-handed weapon equipped together, the two held items replace each other and the light shines from no visible model
- [PLAYER-3P-HELD-ITEM-STALE-65](PLAYER-3P-HELD-ITEM-STALE-65.md): After a new weapon is given and readied, the third-person body still holds the light that was equipped before
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-EQUIPMENT-NOT-WORN-54](PLAYER-EQUIPMENT-NOT-WORN-54.md): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PARTS-BAKE-REFUSED-59](PLAYER-PARTS-BAKE-REFUSED-59.md): Two body part meshes are refused by the assembled player body's parts library
- [PLAYER-PARTS-HAIR-FALSE-STOP-67](PLAYER-PARTS-HAIR-FALSE-STOP-67.md): The player-view stage stops on two of Tribunal's own Dark Elf hairs, calling them another race's part: their mesh names write the race without its space
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- [TORCH-ACTIVATE-CRASH-25](TORCH-ACTIVATE-CRASH-25.md): Raising the fists and pressing V crashed the game: a dynamic light was marked through a negative collision root
- [TORCH-FLAME-VISIBILITY-29](TORCH-FLAME-VISIBILITY-29.md): Torch flame not visible after changing styles
- [TORCH-FUEL-29](TORCH-FUEL-29.md): Torch never burns out; no unlit or fuel state
- [TORCH-HAND-NORD-29](TORCH-HAND-NORD-29.md): Detached-looking left grip fragment in dev4
- [TORCH-HAND-SEPARATION-29](TORCH-HAND-SEPARATION-29.md): Torch grip and hand appear to break during idle and running
- [TORCH-HAND-TO-HAND-64](TORCH-HAND-TO-HAND-64.md): With a torch equipped the fists cannot fight, raising them brings the torch back and V cannot put it away
- [TORCH-INPUT-29](TORCH-INPUT-29.md): F cannot raise hands; V only prints torch state
- [TORCH-INVENTORY-PICTURE-64](TORCH-INVENTORY-PICTURE-64.md): Unequipping the torch in the inventory still shows a torch in the hand

<!-- END GENERATED CATEGORY -->
