# BUILD-EXPANSION-INPUTS-UNCHECKED-66: with the expansions selected, the builder neither requires the Tribunal and Bloodmoon files nor checks them against known-good sizes and SHA-256

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 November 2026, in v0.0.66-dev2 |
| Where | src/mwad/input_check.py (only Morrowind.esm and Morrowind.bsa are required) and config/input-reference (no expansion entries) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev2 |
| Severity | high: The expansions are on by default: a missing expansion file is skipped without a message and a different one only warns, so a build can run on wrong or missing game data. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.66-dev2 |
| From commit | source 1d5d76a, engine 1d5d76a, CHIM world 1d5d76a |
| CHIM engine version | CHIM 0.2.2, engine 1d5d76a, world format unknown |
| Unknown because | the build stopped before the image |
| Platform or emulator | not in game (build time) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.66-dev2 (13 November 2026)._

## Status: 13 November 2026

Fixed in v0.0.66-dev2.

## Symptom

The builder has built both expansions by default since v0.0.66-dev2, but its reference input check (the one that
compares the base `Morrowind.esm` and `Morrowind.bsa` by size and SHA-256) required only the base pair. A missing
Tribunal or Bloodmoon master or archive was skipped without a line, a different one counted only as an optional
difference, and `config/input-reference/` held no entry for the expansion files at all.

## Cause

`src/mwad/input_check.py` treated Tribunal and Bloodmoon as optional game inputs, and the expansion selection
(`--dlc`, `--no-dlc`) was not passed to the check.

## Fix

`config/input-reference/reference.json` now holds an `expansions` section with the size and SHA-256 of
`Tribunal.esm`, `Tribunal.bsa`, `Bloodmoon.esm` and `Bloodmoon.bsa` (the Game of the Year files, the same values as
`config/known-inputs.json`). The input check receives the build's expansion selection: every file of a selected
expansion is required; a missing one, or one whose size or SHA-256 differs, stops the check with the file named and
the expected size and SHA-256 (a difference becomes a warning only with `--allow-data-differences`, as for the base
files). An expansion that is left out is not required. The check runs at the start of the build and in
`--check-inputs`, before any stage, and hashes each file once through the build's input lock. With the base game
alone the check is unchanged. Tests: `tests/test_expansion_input_check.py`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the user's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
