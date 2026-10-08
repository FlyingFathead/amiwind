# FONT-BITMAP-INDEX-32: Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)

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
