# FONT-BITMAP-INDEX-32: Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | bitmap font path (tools/prepare_ui.py, aw_ui.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Wrong characters on the Steam bitmap font path; little visible in shipped text. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the font A/B (TrueType path from the GOG edition, bitmap path from the Steam edition). Affects Steam builds now; little visible in today's shipped text.

## Symptom

Bethesda's `.fnt` fonts store their glyphs in a DOS-style (code page 437-like) order, but the
converter copies the slots straight into the atlas and the engine looks glyphs up by the raw
Windows-1252 game byte. On the bitmap path 25 codes show the wrong letter (for example a
curly quote shows as ô or ö, dashes as û or ù, the ellipsis as à), other accented letters are
blank, and the curly apostrophes are blank but leave a wide gap.

## Where

`tools/prepare_ui.py` (`OriginalFont`, `pack_font`), `engine/aga/src/aw_ui.c` (`AW_UIText`).

## How it happened

The order inside the `.fnt` was never mapped; the conversion record also claims "CP1252
game strings" for the bitmap path.

## Why it was not caught

Only the GOG edition (TrueType path) was built, and today's shipped text has almost no
high characters.

## Reproduction

Build from the Steam edition and show text with curly quotes or accented letters.

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

Tests: the .fnt slot holding e-acute lands in atlas slot 0xE9; quotes are never blank.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
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
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
