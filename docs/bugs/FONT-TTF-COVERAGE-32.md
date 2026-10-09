# FONT-TTF-COVERAGE-32: Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | tools/prepare_ui.py, Magic Cards TrueType font (GOG edition) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Missing glyphs and ornaments replace characters and brackets. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the font A/B (TrueType path from the GOG edition, bitmap path from the Steam edition). Affects the GOG reference build.

## Symptom

`Magic Cards.ttf` (a symbol-mapped font) lacks 53 Windows-1252 characters, which draw a
missing-glyph box (all of é, ä, ö, ü and their capitals among them), and 67 more map to empty
zero-width glyphs, so curly quotes, dashes, apostrophes and the ellipsis vanish. ASCII
`[ \ ] _ { | }` draw ornaments (skull, swirl, mushroom, disc, drop, star) instead, for example
around "[Ranged]" in spell names. The converter's coverage check (at least 8 distinct Latin
glyphs) does not catch this.

## Where

`tools/prepare_ui.py` (`pack_truetype`, coverage check).

## How it happened

The font is decorative and incomplete; coverage was checked only roughly.

## Why it was not caught

Today's shipped text uses almost none of these characters.

## Reproduction

Render "protégé", curly quotes and "[Ranged]" with the GOG build's font.

## Repair

Not yet. One shared build-time mapping layer in `tools/prepare_ui.py`: atlas slot b always
means Windows-1252 byte b (the engine stays unchanged). Per byte, use the TrueType glyph only
if the font really has an outline for it (not a missing-glyph box, an empty zero-width glyph or
an ornament); otherwise the bitmap `.fnt` glyph through a verified per-font table from its
DOS-style (code page 437-like) order; otherwise a substitute as Morrowind and OpenMW use
(curly quotes to straight, dashes to a hyphen, the ellipsis to a full stop, accented capitals to
their base letter). Both editions then show the same characters. Decide the soft hyphen.

## Verification

Pending.

## Prevention

Tests: bracket codes are never ornaments; every displayed byte has a real glyph or a substitute.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
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
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
