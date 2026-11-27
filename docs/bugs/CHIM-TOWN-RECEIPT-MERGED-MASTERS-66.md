# CHIM-TOWN-RECEIPT-MERGED-MASTERS-66: With the expansions selected, the CHIM stage stopped while listing a town's receipt files

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 14 November 2026, in v0.0.66-dev2 |
| Where | The CHIM stage: the town import's receipt of the files it read |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev2 |
| Severity | high: it stopped every build with the expansions selected (the default) in the CHIM stage |
| Family | Town and interior import (`town-import`) |
| Fix commit | `796d8043` |
| Fixed on | 2026-11-14 |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source ec3a18c, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | found in the source: the build stopped in the CHIM stage before its world and engine were made |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.66-dev2 (796d8043) | 2026-11-14 | gate 10744 passed on 796d8043 | a file outside the game data folder (the merged master) is listed in the receipt by its name |
| shipped | a numbered build | v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e | 2026-11-14 | the delivered build | the build holds 796d8043 |
| confirmed by a build | a numbered build | v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e | 2026-11-14 | the dev2 line's build log (the CHIM world of the run of 796d8043, taken by the dev2 build) | the CHIM world's source and receipt step completed with the expansions selected, where the run of ec3a18cd had stopped in it; a builder fix, no play check applies |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-14: reported in v0.0.66-dev2
- 2026-11-14: fixed in source: a gated commit, v0.0.66-dev2 (796d8043); gate 10744 passed on 796d8043: a file outside the game data folder (the merged master) is listed in the receipt by its name
- 2026-11-14: shipped: a numbered build, v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e; the delivered build: the build holds 796d8043
- 2026-11-14: confirmed by a build: a numbered build, v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e; the dev2 line's build log (the CHIM world of the run of 796d8043, taken by the dev2 build): the CHIM world's source and receipt step completed with the expansions selected, where the run of ec3a18cd had stopped in it; a builder fix, no play check applies

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- [AW-20260928-08](AW-20260928-08.md): Census wall/hanging texture quality or mapping
- [DISTRICT-GATE-ON-CELL-BORDER-67](DISTRICT-GATE-ON-CELL-BORDER-67.md): Godsreach's gate to Plaza Brindisi Dorom cannot be used: it stands on the border of the district's two cells, in the door table of the cell the player does not stand in
- [DISTRICT-PEOPLE-NOT-PLACED-67](DISTRICT-PEOPLE-NOT-PLACED-67.md): The people of Mournhold's five districts are not in the game: 50 of Mournhold's 168 people and 8 of its 244 creatures are not placed
- [DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67](DISTRICT-PLAZA-NOT-DRAWN-FROM-ARRIVAL-67.md): From its arrival point Plaza Brindisi Dorom is not drawn looking south: flat ground to the horizon and a flat grey rectangle in the sky
- [DOOR-CHECK-MODULE-FRAME-MAPS-67](DOOR-CHECK-MODULE-FRAME-MAPS-67.md): The image's door check stopped on the first frame map of Mournhold's districts: its table of neighbouring frames knew only the open-world directory
- [DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67](DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67.md): The image's door tables knew only the Vvardenfell world's frames: with Mournhold's districts as a world of their own, every door into or out of a district would have stayed closed
- [IMPORT-DOORBANK-CITY-36](IMPORT-DOORBANK-CITY-36.md): The whole-city Vivec frame holds 157 load doors, over the engine's 128-row door bank
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

Related bugs in other categories:

- [EXPANSION-ARCHIVE-READERS-66](EXPANSION-ARCHIVE-READERS-66.md): With the expansions selected, 24 builder stages that read the merged game data opened the base game archive alone, so a model or texture only an expansion archive holds was missing

<!-- END GENERATED CATEGORY -->
