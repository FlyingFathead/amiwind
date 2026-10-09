# PHOTO-GALLERY-TEXT-33: Photo mode leaves test-room and gallery instruction text over the view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | photo mode in debug rooms (engine/aga/src/screen.c, AW_GalleryDraw) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Debug-room instruction text stayed over the photo mode view; test rooms only. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-photomode, not shipped at the time of writing. Present in the
photo mode commits 45cc1cb and 1e12e07 only; no build containing photo mode has shipped.

## Symptom

In `dbg torchtest`, photo mode hid the HUD, hands and crosshair, but the room's three
instruction lines ("Torch test - dark enclosed room", "Empty room", "V: torch  F: hands ...")
stayed at the top of the view. Seen in the second in-game check of photo mode (FS-UAE,
v0.0.32-dev3 image with the photo mode engine).

## Where

`engine/aga/src/screen.c` (`SCR_UpdateScreen`) calls `AW_GalleryDraw`, which draws the
instruction text of the torch test, combat test and character model gallery. The light
gallery strip (`dbg lightgallery`) is a separate interactive tool and is left visible.

## How it happened

Photo mode gated the scene prompts and the message box, but not the debug rooms' own text.

## Why it was not caught

The first in-game check was outdoors in Seyda Neen, where no gallery text is drawn.

## Reproduction

`dbg torchtest`, then `dbg photomode`.

## Repair

`AW_GalleryDraw` is not called while photo mode is on.

## Verification

Source contract in `tests/test_photo_mode_source.py`; in-game frame in the torch test room.

## Prevention

Photo mode is checked in-game in a debug room as well as outdoors.

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
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
