# IMPORT-DOORBANK-CITY-36: The whole-city Vivec frame holds 157 load doors, over the engine's 128-row door bank

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | engine aw_scene.c read_links_for (links[128]); tools/town_interiors.py BANK_ROWS |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | high: The chim-town stage refuses the city's door bank, so the whole-city build fails |
| Family | Town and interior import (`town-import`) |
| Playtest version | offline CHIM world vivec_city (v0.0.36-vivec-b) |
| From commit | source e7a8e82, engine unknown, CHIM world e7a8e82 |
| CHIM engine version | CHIM 0.1.0, engine unknown, world format 0.5 |
| Unknown because | counted on the offline CHIM world, no engine built |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41 (16 October 2026)._

## Status: 11 October 2026

Repaired in source on v0.0.36-vivec-b; verified by the whole-city MiniWind build.

## Symptom

The CHIM town stage of `vivec_city` (all of Vivec in one CHIM frame) refuses its exterior door bank: 157 load
doors against a limit of 128 rows.

## Where

The engine's door bank (`aw_scene.c` `read_links_for`, `links[128]`) and the builder's copy of the limit
(`tools/town_interiors.py` `BANK_ROWS`).

## How it happened

The bank was sized for one town or one canton (the largest district frame held 50 doors). One frame for the whole
city holds 114 doors into Vivec's rooms, 35 Ebonheart doors on its west edge and a few others; 132 of them lie
inside the city's player area.

## Why it was not caught

No frame this large had been built; the limit was checked only when a bank was written.

## Reproduction

Build the `vivec_city` area (`--miniwind-preset vivec-city-chim`) with the old limit.

## Repair

`AW_SCENE_LINKS` 256 in the engine (about 24 KB more static memory) and `BANK_ROWS` 256 in the builder; a test
reads the engine's number so the two never differ.

## Verification

tests/test_town_interiors.py; the whole-city MiniWind build writes its bank of 157 doors.

## Prevention

The builder limit is tested against the engine source.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- [AW-20260928-08](AW-20260928-08.md): Census wall/hanging texture quality or mapping
- [CHIM-TOWN-RECEIPT-MERGED-MASTERS-66](CHIM-TOWN-RECEIPT-MERGED-MASTERS-66.md): With the expansions selected, the CHIM stage stopped while listing a town's receipt files
- [DISTRICT-GATE-ON-CELL-BORDER-67](DISTRICT-GATE-ON-CELL-BORDER-67.md): Godsreach's gate to Plaza Brindisi Dorom cannot be used: it stands on the border of the district's two cells, in the door table of the cell the player does not stand in
- [DISTRICT-PEOPLE-NOT-PLACED-67](DISTRICT-PEOPLE-NOT-PLACED-67.md): The people of Mournhold's five districts are not in the game: 50 of Mournhold's 168 people and 8 of its 244 creatures are not placed
- [DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md): From its arrival point Plaza Brindisi Dorom is not drawn looking south: flat ground to the horizon and a flat grey rectangle in the sky
- [DOOR-CHECK-MODULE-FRAME-MAPS-67](DOOR-CHECK-MODULE-FRAME-MAPS-67.md): The image's door check stopped on the first frame map of Mournhold's districts: its table of neighbouring frames knew only the open-world directory
- [DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67](DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67.md): The image's door tables knew only the Vvardenfell world's frames: with Mournhold's districts as a world of their own, every door into or out of a district would have stayed closed
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- [ROOM-DECAL-ALPHA-62](ROOM-DECAL-ALPHA-62.md): A cobweb compiled into a room is drawn as a solid dark sheet instead of see-through
- [ROOM-TOWER-OF-DUSK-HOLES-67](ROOM-TOWER-OF-DUSK-HOLES-67.md): Ghostgate, Tower of Dusk: the room is drawn with holes, the room's background colour shows through
- [SEYDA-FRAME-DEFERRED-REFS-69](SEYDA-FRAME-DEFERRED-REFS-69.md): Seyda Neen's frame leaves out many of the original's objects of its own cells: lantern hooks, ropes, the inn sign, road signs and chimney smoke are drawn by nothing that names them
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map
- [TOWN-INTERIOR-SAVEID-ORDER-33](TOWN-INTERIOR-SAVEID-ORDER-33.md): Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
