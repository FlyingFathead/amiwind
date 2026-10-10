# TOWN-FRAME-CEILING-32: ground above the town frame ceiling leaks the map

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Town converter terrain frame ceiling (tools/import_town.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: 320 regions with high ground leak the map and stop vis. |
| Family | Town and interior import (`town-import`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the public world estimate's sample conversions.

## Symptom

The town converter seals each frame with a sky box whose top is at 2,048 units. Where
the ground is higher, the spawn point ends up above the box, qbsp reports a leak and vis
stops ("couldn't read terrain.prt"). Seen converting exterior region w+00+11 022 (ground
at 3,120); 320 Vvardenfell regions have ground above 2,048.

## Where

`tools/import_town.py` (`terrain_map`, the frame's floor and ceiling).

## How it happened

The ceiling was chosen for the towns converted so far, all of them low.

## Why it was not caught

No high region was converted until the whole-world sample.

## Reproduction

Convert region w+00+11 022 with the town converter.

## Repair

Not yet: set each frame's ceiling from its highest ground plus headroom (within the
coordinate range), or shift the frame's local origin down.

## Verification

Pending.

## Prevention

The world estimate checks ground height against the frame ceiling (new column).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- AW-20260928-08 (no report page): Census wall/hanging texture quality or mapping
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-INTERIOR-SAVEID-ORDER-33](TOWN-INTERIOR-SAVEID-ORDER-33.md): Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
