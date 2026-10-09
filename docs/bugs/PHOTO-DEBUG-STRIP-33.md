# PHOTO-DEBUG-STRIP-33: Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | photo mode coordinate strip (engine/aga/src/aw_hud.c Sbar_Draw) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The debug coordinate strip left an 88-pixel corner of the view uncovered in photo mode; debug overlay only. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-photomode, not shipped at the time of writing. Present in the
first photo mode commit (45cc1cb) only; no build containing photo mode has shipped.

## Symptom

In photo mode, Ctrl+H (the same as `dbg hud on`) draws the GLOBAL/LOCAL XYZ rows over the
full-screen view on a black strip that starts 88 pixels from the left edge. The bottom-left
88 x 18 pixels of the 3D view stay visible beside the strip. Seen in the first in-game check
of photo mode (FS-UAE, v0.0.32-dev3 image with the photo mode engine, Seyda Neen).

## Where

`engine/aga/src/aw_hud.c` (`Sbar_Draw`). Outside photo mode nothing changes: the strip still
starts beside the health/magicka/fatigue bars.

## How it happened

The coordinate strip was laid out for the normal screen, where the 3D view ends above the
48-row HUD area and the bars occupy its left 88 pixels. Photo mode gives the view the whole
screen and hides the bars, so the strip's left end no longer met anything.

## Why it was not caught

The native HUD test checked the strip only in the normal layout, and the photo mode tests
did not draw the HUD.

## Reproduction

`dbg photomode`, then Ctrl+H, outdoors; look at the bottom-left corner.

## Repair

In photo mode the strip spans the whole width (one black rectangle under both rows, the
cleaner of the two options: the rows stay readable over any scene). The "WASD / F10 console"
hint, drawn when overlays are on and coordinates off, is not drawn over the photo mode view.

## Verification

`tests/aga_hud_test.c`: in photo mode the strip is filled from x=0 across 320 pixels, outside
photo mode from x=88; the hint is drawn only outside photo mode. A source contract in
`tests/test_photo_mode_source.py`. In-game frame with Ctrl+H in photo mode after the fix.

## Prevention

Every overlay drawn in photo mode is checked on the full-screen view, in the native test and
in one in-game frame.

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
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
