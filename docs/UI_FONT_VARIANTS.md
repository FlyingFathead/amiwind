# Original-font and message-box direction

Owner decisions, 28 September 2026. This is planned UI work, not a shipped feature.

| Variant | Decision |
| --- | --- |
| Magic Cards, 16px, three ink shades plus transparency | Preferred; most legible |
| Magic Cards, 14px, three ink shades plus transparency | Accepted compact alternative |
| Magic Cards, 12px, three ink shades plus transparency | Use only where space requires it |
| Magic Cards, 12px, single ink shade | Rejected; retain historical experiment only |

Keep the original font's character and proportional spacing. Preserve existing
readable/retro/compact fonts and provide a fallback; no replacement by accident.
The private host preview converted the owner's actual bitmap font and atlas,
then rendered a 320x200 mockup with the current palette. It was a font legibility
test, not an approved final panel design. It has not run in the native engine.

## Boxes and layout

Reproduce the original Morrowind UI's black boxes, borders, spacing, text
placement and sizing as closely as the target resolution permits. Inspect the
original assets and behavior before committing to details. Do not adopt a generic
oversized dialogue panel simply because it was convenient for the font preview.
Keep short spoken lines/subtitles, scripted messages and full topic-based dialogue
as distinct UI cases. The owner requests dialogue to enter from below, analogous
to the existing debug console entering from above. Preserve both directions.
Inventory, character, magic, map and journal can use separate tabs/submenus when
the original PC arrangement does not fit at 320x200. Screenshots supplied by the
owner are references, not redistributable public assets.

## Conversion provenance

Original: `Fonts/Magic_Cards_Regular.fnt` plus `Magic_Cards_Regular_0_Lod_A.tex`.
Nominal source size 16px; original atlas 256x256 RGBA. The private study uses
host-side BOX downsampling, proportional metrics, and 1/2-bit packed coverage.
14px coverage data is 5,376 bytes before metrics and color lookup storage.

FNT SHA-256: `d88e86ee724ed5b240376e46dedf1496a303cd9e440a8f79456cf079604ac413`.
TEX SHA-256: `7e1787e08ea9cdce1f29dc98aa4b0878d03e62ac3d051dcc3135b4faf9fe34fc`.

The source-format reference is OpenMW's components/fontloader/fontloader.cpp;
no OpenMW implementation was copied into the native runtime. Extended-character
mapping, native clipping/blitting/wrapping, input routing, voice pacing and target
performance remain to implement and verify. Original and converted font artwork
stays outside this public source tree. The private study preserves its converter,
metrics, preview images, rejected monochrome trial and notes.
