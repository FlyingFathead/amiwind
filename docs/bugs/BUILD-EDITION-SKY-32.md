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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev
- 2026-10-08: GOG/Steam loose-file A/B findings: The original game data is the same in both editions; AmiWind's builder still makes edition-dependent sky outputs and plugin sounds, and its asset readers ignore the expansion archives.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

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

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the user's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EXPANSION-INPUTS-UNCHECKED-66](BUILD-EXPANSION-INPUTS-UNCHECKED-66.md): With the expansions selected, the builder neither requires the Tribunal and Bloodmoon files nor checks them against known-good sizes and SHA-256
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [INPUT-TRANSFER-ZIPS-25](INPUT-TRANSFER-ZIPS-25.md): The input preflight refused a game folder with two differently cased transfer ZIPs beside its Video folder
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
