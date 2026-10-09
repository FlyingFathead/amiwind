# BUILD-EXPANSIONS-31: Tribunal and Bloodmoon cannot be converted with today's tools

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | ESM and BSA readers in the converters (Tribunal, Bloodmoon) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: 1,112 expansion maps cannot be converted; outside the current scope. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps).

## Symptom

The ESM loader rejects plugins, interiors read Morrowind.esm only and mesh export opens
Morrowind.bsa only: 1,112 expansion maps are out of reach. Measured anyway: Tribunal 95 maps
(34 over a limit), Bloodmoon 1,017 (126 over; 10 Solstheim regions exceed 600 edicts even
today, Lake Fjalding up to 989; 79 snow-forest regions over texinfo).

## Where

The ESM/BSA readers in the converters.

## How it happened

Only the base game was in scope.

## Why it was not caught

Not a goal until the whole-world plan.

## Reproduction

Point the converters at Tribunal.esm.

Related: the Toolkit's town labels come from Morrowind.esm only, so Solstheim cells have no
labels on the map metrics layer.

## Repair

Not yet: load plugins in order with record overrides; read every BSA.

## Verification

Pending.

## Prevention

Builder test with a synthetic plugin.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses

<!-- END GENERATED CATEGORY -->
