# Original-font and message-box direction

Owner decisions, 28 September 2026. In v0.0.21-dev1, 14 px is the default
and Options cycles through 16, 14, 12 px and fallback. All existing atlases are
preserved. The main-menu panel follows font metrics and sits lower to expose
the Morrowind title. Independent dialogue/book size settings remain planned.

| Variant | Decision |
| --- | --- |
| Magic Cards, 16px, three ink shades plus transparency | Retained larger option |
| Magic Cards, 14px, three ink shades plus transparency | Current playtest default |
| Magic Cards, 12px, three ink shades plus transparency | Use only where space requires it |
| Magic Cards, 12px, single ink shade | Rejected; retain historical experiment only |

Keep the original font's character and proportional spacing. Preserve existing
readable/retro/compact fonts and provide a fallback; no replacement by accident.
The private host preview converted the owner's actual bitmap font and atlas,
then rendered a 320x200 mockup with the current palette. It was a font legibility
test, not an approved final panel design. The study itself was a mockup. Native integration followed in v0.0.18-dev1;
see RELEASE-v0.0.18-dev1.md.

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
no OpenMW implementation was copied into the native runtime. Native clipping/blitting/wrapping and font selection are implemented and tested
in v0.0.18-dev1. Extended-character locale mapping, full dialogue input routing,
voice pacing and physical-target performance remain open. Original and converted font artwork
stays outside this public source tree. The private study preserves its converter,
metrics, preview images, rejected monochrome trial and notes.

## v0.0.18-dev2 palette and optional frame

Unused duplicate-sky palette slots 225..253 are audited across world/alias/UI
pixels, packed hands and light/fog tables before assigning original bar colors.
The console font and existing world pixels remain unchanged. Gold outer frame
is available in Options and defaults off; dialogue borders remain enabled.
