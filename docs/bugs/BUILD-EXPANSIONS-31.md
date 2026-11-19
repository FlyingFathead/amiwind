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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev
- 2026-10-08: Whole-world measurement findings: Estimating every map of the world with every object placed found silent drops (night lamps in Vivec, static flames), the 220-object interior ceiling, out-of-range interior coordinates, unsupported ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

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

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the user's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSION-INPUTS-UNCHECKED-66](BUILD-EXPANSION-INPUTS-UNCHECKED-66.md): With the expansions selected, the builder neither requires the Tribunal and Bloodmoon files nor checks them against known-good sizes and SHA-256
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses
- [INPUT-TRANSFER-ZIPS-25](INPUT-TRANSFER-ZIPS-25.md): The input preflight refused a game folder with two differently cased transfer ZIPs beside its Video folder
- [MWAD-DELETED-RECORD-35](MWAD-DELETED-RECORD-35.md): Readers disagree on what a deleted record is
- [MWAD-READER-CHECKS-35](MWAD-READER-CHECKS-35.md): Data readers: missing length checks, duplicate FRMR, diverging master lists, lock key
- [MWAD-STRING-DECODE-35](MWAD-STRING-DECODE-35.md): Data readers decode record strings four different ways

Related bugs in other categories:

- [BUILD-GAME-INPUT-KEY-BROAD-64](BUILD-GAME-INPUT-KEY-BROAD-64.md): Every stage that reads the game data was keyed by every game input, so an expansion file being present re-keyed the base world
- [BUILD-LAYER-DATA-MWAD-SHADOWED-64](BUILD-LAYER-DATA-MWAD-SHADOWED-64.md): The Bloodmoon layer data stage stops with mwad is not a package in a MiniWind build
- [CHIM-SEA-BETWEEN-ISLANDS-64](CHIM-SEA-BETWEEN-ISLANDS-64.md): The CHIM cell list holds no sea between Vvardenfell and Solstheim
- [CHIM-SOLSTHEIM-HULL-SURFACE-64](CHIM-SOLSTHEIM-HULL-SURFACE-64.md): The CHIM collision surface check refuses 25 Bloodmoon meshes that are not in its measured table
- [CHIM-SOLSTHEIM-STAIR-CHECK-64](CHIM-SOLSTHEIM-STAIR-CHECK-64.md): The geometric stair check fails on three Bloodmoon meshes
- [CHIM-SOLSTHEIM-TREE-FACES-64](CHIM-SOLSTHEIM-TREE-FACES-64.md): A dense Solstheim forest frame draws about six times the faces of a median Vvardenfell view
- [CHIM-STORE-ONE-AT-A-TIME-64](CHIM-STORE-ONE-AT-A-TIME-64.md): The engine streams one CHIM store at a time, so frames of a second store cannot sit beside the first in the open world
- [CREATURE-EXPANSION-62](CREATURE-EXPANSION-62.md): The creatures of Tribunal and Bloodmoon are not in the game: 136 creature records, their 491 placements and 1,126 levelled creature points
- [HARVEST-EXPANSION-FLORA-62](HARVEST-EXPANSION-FLORA-62.md): The plants placed by the Tribunal and Bloodmoon masters are not harvestable
- [WORLD-REGION-NAMES-VF-ONLY-64](WORLD-REGION-NAMES-VF-ONLY-64.md): The open-world region directory accepts only Vvardenfell region names
- [WORLDMAP-ONE-ISLAND-64](WORLDMAP-ONE-ISLAND-64.md): The in-game world map covers Vvardenfell only

<!-- END GENERATED CATEGORY -->
