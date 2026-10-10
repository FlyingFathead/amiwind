# MWAD-DELETED-RECORD-35: Readers disagree on what a deleted record is

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

Header flag 0x20 and the DELE subrecord were each tested by only some readers; an empty DELE subrecord was missed by a truthiness test.

## Where

The Morrowind data readers in src/mwad and the input and closure tools.

## How it happened

The readers grew separately, each with its own copy of the small helpers.

## Why it was not caught

Owner data is well formed, so the differences never showed; found by code review.

## Reproduction

Feed the reader a synthetic record with the unusual form (see the test).

## Repair

One mwad.esm.is_deleted(flags, subrecords) (flag OR DELE; cell header only for cells) used by audit, interior, vicinity, npc and content_closure.

## Verification

tests/test_mwad_shared.py DeletedTests; stage outputs on the owner data compared by hash tree against the reuse source.

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
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
