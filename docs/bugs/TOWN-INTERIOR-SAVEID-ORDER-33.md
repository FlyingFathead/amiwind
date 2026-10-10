# TOWN-INTERIOR-SAVEID-ORDER-33: Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-dev1 |
| Where | Town table (tools/town_table.py): interior save IDs from AW_TOWN_INTERIOR_BASE |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev1 (last seen) |
| Severity | low: No shipped save can hold a canton room yet; it becomes a save break once a canton ships. |
| Family | Town and interior import (`town-import`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 8f11f40, engine 8f11f40, CHIM world 8f11f40 |
| CHIM engine version | CHIM 0.1.0, engine 8f11f40, world format unknown |
| Unknown because | found in source on the legacy interior converter path; no CHIM world involved |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found while listing the Arena Pit (`vai000`) for IMPORT-TOWN-NO-INTERIORS-32.

## Symptom

`tools/town_table.py` numbers town interiors from `AW_TOWN_INTERIOR_BASE` in save order: towns in
table order, then each town's rooms in list order. The Arena (row 3) had no rooms; listing the Pit
gave it save ID base + 0 and moved all 143 canton rooms (`vqi000` to `voi026`) up by one.

## Where

`tools/town_table.py`, `tools/town_config.py` (`town_interiors`), `engine/aga/src/aw_maps.h`
(`AW_MapId`, `AW_MapName`).

## How it happened

Each town's list is append only, so a room keeps its map name; the save ID is a running index over
all towns, so it is only stable while rooms are appended to the last town that has any.

## Why it was not caught

The cantons and their rooms were added in one change after the Arena, which listed no rooms.

## Reproduction

Append a room to `config/vivec_arena.json` and run `tools/town_table.py --write`: every canton
room's index in `AW_TOWN_INTERIOR_NAMES` moves.

## Repair

Not yet. Harmless today: no canton has shipped, so no save can hold a canton room. Before the first
canton ships, give each town a fixed block of interior save IDs (or pin the IDs in a recorded table).

## Verification

Pending.

## Prevention

`tests/test_town_interiors.py` (`ArenaPit.test_shipped_town_rooms_come_before_unshipped_ones`): the
rooms of shipped towns come before every unshipped town's rooms in save order, so rooms listed for an
unshipped town never renumber a shipped one.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- AW-20260928-08 (no report page): Census wall/hanging texture quality or mapping
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
