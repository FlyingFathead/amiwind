# VIVEC-ROOMS-UNREACHABLE-32: Excluded Vivec hub rooms leave converted rooms unreachable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Vivec canton interior import (door links) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Converted rooms behind excluded hub rooms cannot be reached. |
| Family | Town and interior import (`town-import`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Where a hub room (for example a Waistworks level) is excluded for its limits, converted rooms
behind it cannot be reached: 5 of 18 in the Foreign Quarter, 5 of 14 in Redoran, 12 of 15 in
Telvanni.

## Where

Town interior import (door links).

## How it happened

Rooms are converted independently of reachability.

## Why it was not caught

First multi-room canton import.

## Reproduction

Import the cantons with the current exclusions.

## Repair

Not yet: report reachability per room in the import; fix the hubs (220-model limit, heap)
first.

## Verification

Pending.

## Prevention

Import report lists unreachable rooms.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- AW-20260928-08 (no report page): Census wall/hanging texture quality or mapping
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map

<!-- END GENERATED CATEGORY -->
