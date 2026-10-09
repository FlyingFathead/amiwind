# PLACE-NAMES-INTERIOR-31: location label has no place name inside interiors

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev3 |
| Where | HUD location label in interiors (aw_hud.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev3 (last seen) |
| Severity | low: Interiors show no town or building name in the title. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.31-dev3 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Owner report from the v0.0.31-dev3 playtest; cause read in source.

## Symptom

Outdoors the debug title names the town ("Vvardenfell / Bitter Coast Region /
Seyda Neen"), but inside the prison ship, the Census and Excise Office and its
courtyard it does not say Seyda Neen or the building.

## Where

`engine/aga/src/aw_hud.c` (`Sbar_Draw`): interiors have no exterior cell, so
the title falls back to the map's own message (for example "AmiWind / Prison
Ship"); the place-name table (`world/region-names.awn`) covers exterior cells
only.

## How it happened

The place names were added for exterior cells (ARN2); interiors were not part
of that change.

## Why it was not caught

The change was checked outdoors only.

## Reproduction

v0.0.31-dev3: the prison ship, the Census and Excise Office, its courtyard.

## Repair

Not done: give each interior map its original cell name (for example "Seyda
Neen, Census and Excise Office") and show it as "Vvardenfell / Bitter Coast
Region / Seyda Neen / Census and Excise Office"; the prison ship as the Imperial
Prison Ship off Seyda Neen.

## Verification

Pending.

## Prevention

Interior views in the place-name checks.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- HUD-STATS-29 (no report page): Health uses fixed 100; other bars hardcoded full
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
