# TOOLKIT-TEXT-ENCODING-38: Toolkit labels contain corrupted Unicode characters

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | Toolkit World map status and Local view button |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | low: Corrupted labels reduce readability; geometry and map data are unchanged. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 68c2863 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Toolkit browser UI.) |

<!-- END GENERATED FACTS -->

## Symptom

Status separators displayed as mojibake, and the Local view button displayed a broken arrow before its label.

## Where

Toolkit World map status strip and both Local view button variants (2D + 3D and 2D only).

## How it happened

A text-editing step decoded UTF-8 source using the Windows default encoding and wrote the misdecoded text back as UTF-8.

## Why it was not caught

The initial repair checked the status separators but missed the differently corrupted triangle in the Local view button.

## Reproduction

Open the affected Toolkit source, select an exterior cell, and inspect the status strip and Local view button.

## Repair

Read and write source explicitly as UTF-8. Restore damaged punctuation and encode the JavaScript button arrow as a Unicode escape, preserving its displayed character.

## Verification

The earlier separator repair was verified in the live browser. Both button strings were corrected in all maintained Toolkit copies. A scan of Toolkit HTML, JavaScript, CSS, JSON and Markdown found no remaining instances of the observed mojibake patterns or replacement characters. Release packaging remains unverified.

## Prevention

Use explicit UTF-8 for source editing and inspect every affected label, including alternate button states, after encoding repairs.

13 October 2026 recurrence in release documentation: a locale-decoded text edit damaged historical README punctuation and a heading anchor. The anchor gate detected it before packaging. Historical content was restored from the previous commit using explicit UTF-8 byte decoding; all 1,008 document checks pass. This is a source-editing workflow failure, not a game-runtime change.

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
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
