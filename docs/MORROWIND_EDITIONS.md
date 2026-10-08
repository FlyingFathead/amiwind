# Morrowind editions: what the builder reads

AmiWind converts only the master files in `Data Files`: the three ESM masters and
their BSA archives. This page records which editions have been checked against
each other. It lists names, sizes and SHA-256 hashes only; no game files are part of
this repository.

## GOG and Steam Game of the Year editions (checked 8 October 2026)

A file-by-file comparison of an owner's GOG GOTY installation and an owner's Steam
GOTY installation found the six master files **identical**:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `Morrowind.esm` | 79,837,557 | `5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647` |
| `Morrowind.bsa` | 310,459,500 | `3dcd5e6bfa08245521a53374bf733ee5c920df49103898a15aa31144ad64cf48` |
| `Tribunal.esm` | 4,565,686 | `2ace511f23cc2a9ddd5f3aa59c7919789b9378cf4b17c8ae3375dd6b782f3f2b` |
| `Tribunal.bsa` | 64,986,032 | `3901e7a146f7a64a4ae9534c80d5974f7ab15adf5c48c4561d9313c0f7831d69` |
| `Bloodmoon.esm` | 9,631,798 | `bd27090d0e6ad4c1bf1abc83f1a2dac56fcc82cae7bfe8263c413fb301801357` |
| `Bloodmoon.bsa` | 118,425,318 | `7c20956791400d958cb407f0b7c1c19ceaf46719df7eb724d0b450299360bd7c` |

**Both editions are supported**: AmiWind builds from either. The masters are the same,
but the builds are not byte-identical, because the builder reads more than the masters:

- **Fonts.** The GOG edition includes three TrueType fonts in `Data Files/BookArt`
  (`Magic Cards.ttf`, `GOTHIC.TTF`, `daedric_runes.ttf`); the Steam edition does not.
  The builder prefers these fonts for the interface and book text and falls back to
  Bethesda's bitmap fonts (`Data Files/Fonts/*.fnt` with their `.tex` pages, identical
  in both editions). A Steam build therefore has different interface and book lettering.
- **Loose files.** The GOG installation also has about 13,800 loose files next to the
  archives (7,506 meshes, 4,837 textures, 1,441 icons and some sounds and book art).
  Several builder steps let loose files override the archives (NPC models, media, sky
  textures), as the game itself does. Whether these loose files differ from the copies
  inside the archives has not been measured yet; if they do, GOG and Steam builds differ
  there too.
- **Not read by the builder:** the game program and launcher (`Morrowind.exe`,
  `Morrowind Launcher.exe`), `Morrowind.ini`, the official Bethesda plugins (`.esp`)
  in the GOG edition, and any saved games or backups in the folder.

**The GOG Game of the Year edition is the reference edition** for AmiWind's own builds
and releases. **The Steam Game of the Year edition is supported too**: it builds the same
game, with the bitmap fonts and the possible loose-file differences above
(BUILD-EDITION-DIFFERENCES-32). Both editions are part of the from-scratch build checks.

## Fonts: two conversion paths with different glyph indexes

The builder has two ways to make the interface, dialogue and book fonts, chosen
automatically per font family ([paper font options](PAPER_FONT_OPTIONS.md),
[original-font notes](UI_FONT_VARIANTS.md)):

- **TrueType path** (GOG edition: `BookArt/Magic Cards.ttf`, `GOTHIC.TTF`): each of the
  game's 256 character codes is decoded as Windows code page 1252 and the glyph is looked
  up in the font. `Magic Cards.ttf` is a symbol-mapped font. The Daedric font always uses the
  bitmap path, in both editions, because its TrueType glyphs exceed the converter's limits.
- **Bitmap path** (Steam edition, or any installation without those TrueType files): the
  glyphs come from Bethesda's font files, `Fonts/*.fnt` with their `*_0_Lod_A.tex` atlas
  pages (byte-identical in both editions).

The engine draws only Magic Cards (interface, dialogue, books); the Gothic and Daedric
atlases are built but not used yet. It looks each glyph up by the raw game text byte.

**Measured (8 October 2026), neither path is correct yet for characters beyond plain
ASCII:**

- **Bitmap path (Steam):** the `.fnt` files keep their glyphs in a DOS-style order (close to
  code page 437, as OpenMW's font loader also notes), but the converter copies them straight
  across. So 25 codes show the wrong letter (a curly quote shows as an accented o, dashes as
  accented u, the ellipsis as an accented a), other accented letters are blank, and curly
  apostrophes leave a wide gap ([FONT-BITMAP-INDEX-32](bugs/FONT-BITMAP-INDEX-32.md)).
- **TrueType path (GOG):** `Magic Cards.ttf` lacks many characters: accented letters draw a
  missing-glyph box, curly quotes, dashes, apostrophes and the ellipsis vanish, and the
  ASCII brackets draw ornaments (a skull, a mushroom...) instead
  ([FONT-TTF-COVERAGE-32](bugs/FONT-TTF-COVERAGE-32.md)). `GOTHIC.TTF` is complete.
- **Today's playtest text** contains almost none of these characters, so the difference
  hardly shows yet. The game's books (about 3,500 curly quotes each way in Morrowind
  alone), dialogue and journal will need the repair: one shared mapping layer so that both
  editions show the same, correct characters.

To test the bitmap path from a GOG installation, use a separate copy without the
`BookArt` TrueType files; never edit the original installation.

The builder will identify these masters as a known edition when it checks its inputs
(BUILD-INPUTS-UNVERIFIED-32). Other editions (retail CD, other stores, language
versions) can be added when someone reports their sizes and hashes.
