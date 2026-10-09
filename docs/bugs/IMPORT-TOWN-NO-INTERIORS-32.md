# IMPORT-TOWN-NO-INTERIORS-32: The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Town importer (tools/import_town.py), Vivec Arena doors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | high: All 26 Arena doors say Interior unavailable. |
| Family | Town and interior import (`town-import`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt).

## Symptom

`tools/import_town.py` has no interior step, so all 26 Arena doors have no target and the
engine shows "Interior unavailable".

## Where

`tools/import_town.py`.

## How it happened

The generic importer was built for exteriors first.

## Why it was not caught

First town with doors through the importer.

## Reproduction

Build with `--extra-town vivec_arena` and use any Arena door.

## Repair

Not yet: an interior step in the importer using the interior converter, linking door targets.

## Verification

Pending.

## Prevention

Importer test with a synthetic interior behind a door.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- AW-20260928-08 (no report page): Census wall/hanging texture quality or mapping
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
