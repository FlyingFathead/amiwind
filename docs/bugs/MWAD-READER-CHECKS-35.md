# MWAD-READER-CHECKS-35: Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | Morrowind data readers (src/mwad, tools/known_inputs.py, tools/content_closure.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | low: Readers could accept or misread unusual data silently; the owner base-game data is unaffected (outputs byte-identical). |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |
| Playtest version | none |
| From commit | source and engine 6979d4f |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-mwad-fixes, not shipped at the time of writing.

## Symptom

Several fixed-size reads unpacked without a length check (struct.error), a duplicate original FRMR was accepted, the TES3 header walk truncated on an overrun, Tribunal/Bloodmoon were not game inputs in the path rules, game files were found by an ad-hoc scan, and the input-lock key ignored symlinks and case.

## Where

The Morrowind data readers in src/mwad and the input and closure tools.

## How it happened

The readers grew separately, each with its own copy of the small helpers.

## Why it was not caught

Owner data is well formed, so the differences never showed; found by code review.

## Reproduction

Feed the reader a synthetic record with the unusual form (see the test).

## Repair

mwad.esm.unpack (FormatError naming the field), duplicate FRMR refused, one subrecord walk that raises on overrun (an invalid verdict, not a crash), one GAME_MASTERS/GAME_ARCHIVES list for paths, input check, known inputs and the closure, child_ci for game files (ambiguous case is an error), lock key normcase(realpath), read_text with encoding, one SHA-256 file digest and BSA asset read.

## Verification

tests/test_mwad_shared.py; stage outputs on the owner data compared by hash tree against the reuse source.

## Prevention

One shared module for these helpers; new readers import it. The writer scan test refuses new unpinned writers.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
