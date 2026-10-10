# IMPORT-TOWN-NO-INTERIORS-32: The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Town importer (tools/import_town.py), Vivec Arena doors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1, v0.0.32 (last seen) |
| Severity | high: All 26 Arena doors say Interior unavailable. |
| Family | Town and interior import (`town-import`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Partly repaired in source on v0.0.33-arena-interiors, not shipped at the time of writing. The
importer's interior step exists since the Vivec canton change; the Arena now lists its first room,
"Vivec, Arena Pit" (`vai000`, the combat test spot). Both exterior doors into the Pit and the Pit's
two exits to the Arena are linked; the other 27 of the 29 Arena door rows (Waistworks, Underworks)
stay "Interior unavailable" until those rooms are listed.

8 October 2026: open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1
attempt).

## Symptom

`tools/import_town.py` has no interior step, so all 26 Arena doors have no target and the
engine shows "Interior unavailable".

## Where

`tools/import_town.py`.

## How it happened

The generic importer was built for exteriors first. Its interior step came with the Vivec cantons
(rooms listed per town config, converted with the shared interior converter, door banks both ways),
but the Arena's config was left unchanged so that the v0.0.32 Arena preview kept its payload: it
listed no rooms, so every Arena door kept target "-".

## Why it was not caught

First town with doors through the importer.

## Reproduction

Build with `--extra-town vivec_arena` and use any Arena door.

## Repair

`config/vivec_arena.json` lists "Vivec, Arena Pit" as the Arena's first room (append only: map
`vai000`, save ID base + 0). The builder's town stage (`tools/import_town.py --town vivec_arena`)
converts it with the shared interior converter (every selected placement kept, dressing policy
unchanged), places its four residents (classified as standing in `config/actor_grounding.json`) and
writes the door banks: the Arena's two Pit doors (466158, 466159) lead in; the Pit's canton doors
(466201, 466202) lead out to the Arena frame; its two Waistworks doors stay unavailable. The engine's
town table lists the room (`tools/town_table.py`). On a CHIM build the exits name the town map
(`vivec_arena`), which the engine resolves to the CHIM frame.

## Verification

9 October 2026, owned data, the builder's town stage (3 jobs, 12 min 15 s for the whole Arena town),
the Pit's map identical to a direct interior conversion:

| Check | Result |
| --- | --- |
| Map | `vai000`: 21,992 faces, 37,393 clipnodes, 44 placements (38 models), 3,613,068 B, coordinates within 534 units |
| Stair gate | passed: 44 flight steps, 312 ramps walked; 10 advisory ramp results on the upper stands (92 s with the routed hull, 95 min with the chain) |
| Actor ground gate | passed after the image stage's grounding: the four residents grounded on the upper ledge |
| Heap estimate | pass: 9,381,668 B, clearance 2,152,668 B of 11,534,336 B |
| Heap on the emulator | peak 6,538,912 B of 11,534,336 B after load (FS-UAE, this branch's engine) |
| Combat floor | flat sand floor at one height, about 161,000 square units reachable with the standing box, closed (no fall, no edge); stairs lead to the residents' ledge |
| Visibility | one leaf (the interior converter's sealed box): everything is potentially visible (TOWN-VIS-OCCLUSION-31) |
| OpenMW A/B | five poses, headlamp off and on: geometry, doors, braziers, stairs and residents match |

Not yet: a builder image with the room (the MiniWind preset `vivec-arena-pit`), and the remaining
Arena rooms. Collision cost: INTERIOR-HULL-CHAIN-33 (repaired in source); ROUTED-HULL-NODE-ORDER-33.

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
- [TOWN-INTERIOR-SAVEID-ORDER-33](TOWN-INTERIOR-SAVEID-ORDER-33.md): Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

<!-- END GENERATED CATEGORY -->
