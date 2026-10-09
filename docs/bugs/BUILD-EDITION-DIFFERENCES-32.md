# BUILD-EDITION-DIFFERENCES-32: GOG and Steam editions produce different builds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Builder inputs (BookArt fonts, loose-file overrides) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Steam lacks the TTF fonts and GOG loose files override archives, so builds differ by edition. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Fonts confirmed; loose-file differences not yet measured.

## Symptom

The six master files are identical in the GOG and Steam Game of the Year editions, but
builds differ: the Steam edition lacks the three TrueType fonts in `BookArt`, so the
builder falls back to Bethesda's bitmap fonts for interface and book text; and the GOG
installation has about 13,800 loose files that override archive copies in several
builder steps.

## Where

`tools/prepare_ui.py` (`bake_family`: TTF first, bitmap fallback), `tools/prepare_reading.py`,
and the steps that let loose files override archives (`npc_geometry.py`,
`prepare_media_assets.py`, `prepare_shared_sky_assets.py`, `build_night_sky.py`).

## How it happened

The builder was developed against the GOG installation and follows the game's rule that
loose files override archives.

## Why it was not caught

Only one edition was ever built.

## Reproduction

Build from a Steam installation and compare the interface fonts and the files above with
a GOG build.

Measured (8 October 2026): 5,949 of the GOG loose files shadow a path in `Morrowind.bsa`
(5,895 meshes, 52 textures, 2 icons). Whether their contents differ from the archive copies
is still to be compared.

Compared by the loose-file A/B (8 October 2026): all three archives and all three masters are
byte-identical between GOG and Steam. Of 21,039 loose GOG files, 8,592 equal their winning archive
copy, 1 differs (`meshes/r/iceminion.nif`, a case-only node name), and 12,446 are loose-only:
mostly the original `.tga`/`.bmp` art behind archived `.dds` files (the game reads `.dds`), plus
the official plugins' files and 8 plugin sounds. So the original game shows the same world in
both editions; AmiWind's builder does not yet (BUILD-EDITION-SKY-32, BUILD-PLUGIN-SOUNDS-32,
ASSETS-ARCHIVE-ORDER-32).

## Repair

Not yet: measure whether GOG's loose files differ from the archive copies; make the
builder report which font source and which loose overrides it used (in the known-inputs
check and the build summary), so builds say which edition-specific inputs they used.
GOG stays the reference edition.

## Verification

Pending.

## Prevention

The known-inputs check identifies the edition and reports edition-specific inputs.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses

<!-- END GENERATED CATEGORY -->
