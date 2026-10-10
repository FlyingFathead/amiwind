# BUILD-INPUTS-UNVERIFIED-32: the builder does not check user inputs against known versions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Builder input handling (tools/build.py, tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Modified or damaged Morrowind data converted without warning. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Repair in progress (one shared known-inputs check).

## Symptom

The builder converts whatever Morrowind data files it is given without telling the user
whether they match a known edition (for example the GOG Game of the Year release). A
patched, modded or damaged `Morrowind.esm` or `.bsa` is converted as-is. The same holds
for the optional Amiga FPU support libraries.

Correction (8 October 2026): this page first said the game data was never checked. That was
wrong: `config/input-reference/` (7,197 records) with `src/mwad/input_check.py` already stopped
a build on a different `Morrowind.esm` or `.bsa` unless `--allow-data-differences` was given.
What was missing: Tribunal and Bloodmoon, naming the edition, the Amiga libraries, and one
shared hash path. Some steps (`prepare_doors`, `prepare_guard_torches`, `prepare_harvest`,
`mwad.audit`) still hash `Morrowind.esm` themselves instead of reading the inputs lock.

## Where

`tools/build.py` and `tools/build_aga.py` input handling; `tools/fpu_support.py`.

## How it happened

Only cache consistency was checked: the receipts record `Morrowind.esm`'s SHA-256 and the
town importer refuses a cache made from a different file. The Kickstart ROM and downloaded
tools are checked against known hashes; the game data never was.

## Why it was not caught

Builds always used the same owner copy.

## Reproduction

Build with a modified `Morrowind.esm`: no warning.

## Repair

Fixed in source (v0.0.32-dev): `tools/known_inputs.py` identifies every input (TES3 masters,
BSA archives, Kickstart ROM, Amiga libraries) against `config/known-inputs.json`, reports
known / unknown / invalid with warn, fail or require-known policies, and keeps the inputs
lock `amiwind-inputs.lock` (`--check-hashes core|full|auto|off`, default core). The existing
reference check now reads the lock.

## Verification

Suite 1,371 tests passing; on the GOG data all six masters and archives are known, the
edition reads "Game of the Year edition (GOG, reference)". Core hashing takes 0.3 s on the
host and 2.7 s through the Docker bind mount.

## Prevention

The verifier runs on every build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

<!-- END GENERATED CATEGORY -->
