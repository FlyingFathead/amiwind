# FONT-TTF-COVERAGE-32: Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments

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
