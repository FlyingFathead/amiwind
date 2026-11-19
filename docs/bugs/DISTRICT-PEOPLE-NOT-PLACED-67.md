# DISTRICT-PEOPLE-NOT-PLACED-67: The people of Mournhold's five districts are not in the game: 50 of Mournhold's 168 people and 8 of its 244 creatures are not placed

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 18 November 2026, in v0.0.67-dev2 |
| Where | the image step's actor tables for the districts' outdoor frames (Godsreach, the Great Bazaar, Plaza Brindisi Dorom, the Royal Palace courtyard, the Temple courtyard) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev2 (last seen) |
| Severity | high: the districts are empty streets: no merchants of the bazaar, no guards, none of the people the city's quests start with |
| Family | Town and interior import (`town-import`) |
| Playtest version | 2026_11_18_v0.0.67-dev2_full-mournhold-module-test3_104174c |
| From commit | source and engine 104174c |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (read from the image's own record of the expansions' actors) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-18: reported in v0.0.67-dev2
- 2026-11-18 18:05 +0200: v0.0.67-dev2: Counted from the districts' own presented game data: 57 actor references in the districts' cells (49 people, 8 creatures; 38 with a script), none of them in a frame map: a district's frame map held its worldspawn, its start and its flames.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- [AW-20260928-08](AW-20260928-08.md): Census wall/hanging texture quality or mapping
- [CHIM-TOWN-RECEIPT-MERGED-MASTERS-66](CHIM-TOWN-RECEIPT-MERGED-MASTERS-66.md): With the expansions selected, the CHIM stage stopped while listing a town's receipt files
- [DISTRICT-GATE-ON-CELL-BORDER-67](DISTRICT-GATE-ON-CELL-BORDER-67.md): Godsreach's gate to Plaza Brindisi Dorom cannot be used: it stands on the border of the district's two cells, in the door table of the cell the player does not stand in
- [DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md): From its arrival point Plaza Brindisi Dorom is not drawn looking south: flat ground to the horizon and a flat grey rectangle in the sky
- [DOOR-CHECK-MODULE-FRAME-MAPS-67](DOOR-CHECK-MODULE-FRAME-MAPS-67.md): The image's door check stopped on the first frame map of Mournhold's districts: its table of neighbouring frames knew only the open-world directory
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

- [DISTRICT-PLACED-THINGS-NO-ROW-67](DISTRICT-PLACED-THINGS-NO-ROW-67.md): In Mournhold's districts no container, item, activator or door sign can be aimed at: their rows are keyed as a room's, and the game outdoors asks for the cells around the player

<!-- END GENERATED CATEGORY -->
