# INPUT-TRANSFER-ZIPS-25: The input preflight refused a game folder with two differently cased transfer ZIPs beside its Video folder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 1 October 2026, in v0.0.25-rc1 |
| Where | builder: the game input scan and preflight |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.25-rc1 (last seen) |
| Severity | high: the builder refused a usable game installation |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-01: reported in v0.0.25-rc1
- 2026-10-01: v0.0.25-rc1: Input preflight rejects personal transfer ZIPs — v0.0.25-rc1: Reproduction: put Morrowind_Video.zip and Morrowind_video.zip beside the normal Data Files/Video directory.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66 (16 November 2026)._

## Status: 16 November 2026

Open. Repaired in source on the v0.0.25-rc1 line: Morrowind.esm and Morrowind.bsa are selected by name and supported asset types inside known game folders before the path checks, inventory and build hashes; unrelated folders, root files and transfer archives are ignored; a synthetic regression covers both cased ZIPs, a loose video, archive-free receipts and a real video conflict. The build that shipped it is not recorded. Recorded as an entry from the bug journal on 16 November 2026.

## Symptom

With Morrowind_Video.zip and Morrowind_video.zip beside Data Files/Video, the scanner rejected the case-folded ZIP collision before telling game assets apart.

## Where

Builder: the game input scan and preflight.

## How it happened

As recorded in the bug journal: see the dated history in the timeline below.

## Why it was not caught

Not recorded.

## Reproduction

As in the symptom; reproduction: always.

## Repair

The game inputs are selected positively by name and asset type; transfer archives are ignored.

## Verification

See the status and the timeline below.

## Prevention

Not recorded.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the user's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSION-INPUTS-UNCHECKED-66](BUILD-EXPANSION-INPUTS-UNCHECKED-66.md): With the expansions selected, the builder neither requires the Tribunal and Bloodmoon files nor checks them against known-good sizes and SHA-256
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
