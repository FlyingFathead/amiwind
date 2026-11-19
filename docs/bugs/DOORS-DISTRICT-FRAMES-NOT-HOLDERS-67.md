# DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67: The image's door tables knew only the Vvardenfell world's frames: with Mournhold's districts as a world of their own, every door into or out of a district would have stayed closed

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 18 November 2026, in v0.0.67-dev2 |
| Where | tools/build_aga.py write_world_doors and write_room_batch_links (the frames that hold an exterior door or arrival) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev2 (last seen) |
| Severity | high: the 40 doors into a district and the 28 out of one, and the jail's release marker, would have been held back in an image that holds the districts; found by reading the image step before any build ran it |
| Family | Town and interior import (`town-import`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine c534a39 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (found in the source of the image step while moving the districts into a build module of their own; no image with the districts exists yet) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- [AW-20260928-08](AW-20260928-08.md): Census wall/hanging texture quality or mapping
- [CHIM-TOWN-RECEIPT-MERGED-MASTERS-66](CHIM-TOWN-RECEIPT-MERGED-MASTERS-66.md): With the expansions selected, the CHIM stage stopped while listing a town's receipt files
- [DISTRICT-GATE-ON-CELL-BORDER-67](DISTRICT-GATE-ON-CELL-BORDER-67.md): Godsreach's gate to Plaza Brindisi Dorom cannot be used: it stands on the border of the district's two cells, in the door table of the cell the player does not stand in
- [DISTRICT-PEOPLE-NOT-PLACED-67](DISTRICT-PEOPLE-NOT-PLACED-67.md): The people of Mournhold's five districts are not in the game: 50 of Mournhold's 168 people and 8 of its 244 creatures are not placed
- [DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md): From its arrival point Plaza Brindisi Dorom is not drawn looking south: flat ground to the horizon and a flat grey rectangle in the sky
- [DOOR-CHECK-MODULE-FRAME-MAPS-67](DOOR-CHECK-MODULE-FRAME-MAPS-67.md): The image's door check stopped on the first frame map of Mournhold's districts: its table of neighbouring frames knew only the open-world directory
- [IMPORT-DOORBANK-CITY-36](IMPORT-DOORBANK-CITY-36.md): The whole-city Vivec frame holds 157 load doors, over the engine's 128-row door bank
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- [ROOM-DECAL-ALPHA-62](ROOM-DECAL-ALPHA-62.md): A cobweb compiled into a room is drawn as a solid dark sheet instead of see-through
- [ROOM-TOWER-OF-DUSK-HOLES-67](ROOM-TOWER-OF-DUSK-HOLES-67.md): Ghostgate, Tower of Dusk: the room is drawn with holes, the room's background colour shows through
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map
- [TOWN-INTERIOR-SAVEID-ORDER-33](TOWN-INTERIOR-SAVEID-ORDER-33.md): Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
