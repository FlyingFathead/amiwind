# DOOR-CHECK-MODULE-FRAME-MAPS-67: The image's door check stopped on the first frame map of Mournhold's districts: its table of neighbouring frames knew only the open-world directory

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 18 November 2026, in v0.0.67-dev2 |
| Where | tools/door_engine_check.py neighbour_walks and job_lines, called by the image step's last part (tools/build_aga.py write_door_check) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev2 (last seen) |
| Severity | high: a build with Mournhold's districts stopped in the image step's last part, 1 h 34 min after it started and 26 min 49 s into the image step, with every stage before it done |
| Family | Town and interior import (`town-import`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 58d5808 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (a builder error in the image step; no image was made) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | developer | v0.0.67-dev2 (tools/door_engine_check.py job_lines, tools/expansion_preflight.py module_frame_maps) | 2026-11-18 14:05 +0200 | a door in a frame outside the walked directory gets a row with its reason; the first-minute check builds the image's last tables from the module's frame map names; tests/test_presented_data_stage.py holds both, and the fault as the build met it | a table the image builds last must be tried on a new kind of map before the stages run |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-18: reported in v0.0.67-dev2
- 2026-11-18 14:05 +0200: fixed in source: developer, v0.0.67-dev2 (tools/door_engine_check.py job_lines, tools/expansion_preflight.py module_frame_maps); a door in a frame outside the walked directory gets a row with its reason; the first-minute check builds the image's last tables from the module's frame map names; tests/test_presented_data_stage.py holds both, and the fault as the build met it: a table the image builds last must be tried on a new kind of map before the stages run
- 2026-11-21 08:13 +0200: seen again in v0.0.68-dev3: Seen again in v0.0.68-dev3: with Solstheim's cells in the image the door audit reports all 95 Solstheim entrances and Mournhold's 28 as not usable, because it runs before the expansions' stores and frame maps are installed and the engine ...

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- [AW-20260928-08](AW-20260928-08.md): Census wall/hanging texture quality or mapping
- [CHIM-TOWN-RECEIPT-MERGED-MASTERS-66](CHIM-TOWN-RECEIPT-MERGED-MASTERS-66.md): With the expansions selected, the CHIM stage stopped while listing a town's receipt files
- [DISTRICT-GATE-ON-CELL-BORDER-67](DISTRICT-GATE-ON-CELL-BORDER-67.md): Godsreach's gate to Plaza Brindisi Dorom cannot be used: it stands on the border of the district's two cells, in the door table of the cell the player does not stand in
- [DISTRICT-PEOPLE-NOT-PLACED-67](DISTRICT-PEOPLE-NOT-PLACED-67.md): The people of Mournhold's five districts are not in the game: 50 of Mournhold's 168 people and 8 of its 244 creatures are not placed
- [DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md): From its arrival point Plaza Brindisi Dorom is not drawn looking south: flat ground to the horizon and a flat grey rectangle in the sky
- [DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67](DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67.md): The image's door tables knew only the Vvardenfell world's frames: with Mournhold's districts as a world of their own, every door into or out of a district would have stayed closed
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

Related bugs in other categories:

- [DOOR-USE-COLLISION-EXPANSIONS-68](DOOR-USE-COLLISION-EXPANSIONS-68.md): 13 exterior entrances of Solstheim and Mournhold cannot be reached in the converted collision: no standing spot at the threshold, or the door out of the use reach

<!-- END GENERATED CATEGORY -->
