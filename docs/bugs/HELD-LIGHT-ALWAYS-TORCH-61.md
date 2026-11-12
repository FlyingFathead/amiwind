# HELD-LIGHT-ALWAYS-TORCH-61: Any carried light held in the hand is drawn and lit as the torch

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 6 November 2026, in v0.0.61-dev2 |
| Where | engine held light (torch and hand models) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.61 |
| Severity | medium: every held light other than a torch looks and lights wrong; nothing breaks |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine afa644d |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (found by reading the engine code; to be seen on the dev2 image) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev2 (6 November 2026)._

## Status: 6 November 2026

Open, repaired on the v0.0.61 line (tracker HELD-LIGHT-OWN-MODEL-61) and seen working in a MiniWind of the repair;
fixed once a numbered build carries it.

## Symptom

Equipping a candle, a candlestick or a lantern from the inventory puts it in the left hand as in the original, but
the hand shows the torch, in first and third person, with the torch's flame and the torch's light radius. A candle
lights as far as a torch; a three-candle holder shows one torch flame; a paper lantern, which has no flame, shows one.

## How it happened

The carried torch came first (one model, one flame, one light). When the item catalogue learned every carried light
(their weight, value, burn time, radius and colour), equipping any of them was tied to the torch's switch, so the
torch's model, flame and light stood in for all of them. The radius and colour read from the record were not used.

## Why it was not caught

The in-game checks equipped the debug torch, which is the torch.

## Records

Measured from the game data (LHDT): torch radius 256. Candle (light_de_candle_03) 128; Pewter and Silver Candlesticks
(light_com_candle_09, light_com_candle_10, three flames each) 256; Travel Lantern (light_com_lantern_01), Glass Lantern
(light_de_lantern_02, blue) and Paper Lantern (light_de_lantern_01, no flame, steady light) 256. Of the 165 carriable
light records the radius runs from 16 to 512 (median 128); two are above the torch's.

## Repair

- The builder writes beside each carried light's item model a small text file (`tools/held_lights.py`: the model's
  place on the left hand's Shield Bone, the original's carried-light turn about its BoneOffset, and up to four flame
  emitters with the same numbers a placed copy's flame has) and puts the record's flicker and fire flags into the item
  catalogue (byte 511). Nothing new is converted: the light's model is the one the item model table already holds. The
  torch's own mesh gets no such file and keeps its own hand, flame and light.
- First person: the arms from parts gain a light stance in the first-person table (the bare hands with the left arm on
  the original's first-person torch group); the light's model rides their shield bone, its flames are drawn over the
  view as the torch's are.
- Third person: the assembled body's left arm takes the table's torch group (as a skeletal guard holds his torch), the
  light's model hangs on the shield bone and its flames are drawn as the placed copy's.
- The dynamic light reaches the torch's current reach times the record's radius over the torch's (256), never further,
  and flickers only when the record flickers or pulses.

Not yet: the light's colour (the dynamic lights are one shade), the burn time counting down (no light burns down yet,
TORCH-FUEL-29), the light in the inventory picture, and the baked body (`aw_player_body_parts 0`), which still shows
the torch. Lanterns hang below the hand, so in first person only their handle shows at the bottom of the view.

## Verification

Native tests: the held light file read once per item, the reach (192 for a 256 record, 96 for the candle's 128 at
the torch's default 192), steady against flickering, the torch back on unequip, the catalogue's byte 511, the
first-person light stance. In game (MiniWind of Seyda Neen, Arrille's Tradehouse, FS-UAE at 32 MB Fast, JIT): the
torch as before; the candle, both three-candle holders (three flames each), the glass, paper and travel lanterns in
first and third person; the console reports each light's reach (candle 96, the rest 192, the paper lantern steady).

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
- [TORCH-INVENTORY-PICTURE-64](TORCH-INVENTORY-PICTURE-64.md): Unequipping the torch in the inventory still shows a torch in the hand

<!-- END GENERATED CATEGORY -->
