# BUILD-EDITION-SKY-32: Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Sky builders (build_night_sky.py, shared sky assets) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Night sky and sky palette outputs differ by edition because loose .tga is read before the archive. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the GOG/Steam loose-file A/B (measured on both installations, no repository change).

## Symptom

`build_night_sky.py` reads loose `.tga` before the archive `.dds`: GOG uses 22 loose star and moon
images, Steam the `Morrowind.bsa` copies. `gfx/aw_night_sky.lmp` differs in 1,956 of 27,664 bytes
and `gfx/night-sky.json` records the different hash. `prepare_shared_sky_assets.py` does the same
for clouds: the pixels are identical, but `gfx/sky-palette-bank.json` names and hashes a different
source file.

## Where

`tools/build_night_sky.py` (`owned_images`), `tools/prepare_shared_sky_assets.py` (`owned_clouds`).

## How it happened

The loose originals were preferred when only GOG data was used.

## Why it was not caught

Only one edition was ever built.

## Reproduction

Build the sky assets from a GOG and a Steam installation and compare `gfx/`.

## Repair

Not yet: read what the game reads (archive `.dds` first, in archive order), or record the
choice per edition; markers name the logical asset, not the edition's file.

## Verification

Pending.

## Prevention

Edition A/B of the builder outputs in the from-scratch check.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses

<!-- END GENERATED CATEGORY -->
