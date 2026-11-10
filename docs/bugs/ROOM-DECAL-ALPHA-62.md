# ROOM-DECAL-ALPHA-62: A cobweb compiled into a room is drawn as a solid dark sheet instead of see-through

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 7 November 2026, in v0.0.61 |
| Where | Room conversion: see-through textures of meshes built into rooms (Andrano Ancestral Tomb) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61 (last seen) |
| Severity | medium: cobwebs and other see-through surfaces look wrong in rooms; the rest of the room works |
| Family | Town and interior import (`town-import`) |
| Playtest version | v0.0.61 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format unknown |
| Unknown because | a playtest report on the delivered release image; the commit of the running build was not read back |
| Platform or emulator | the delivered v0.0.61 release image (playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

## Status: 7 November 2026

Open. Seen on the v0.0.61 release image. No earlier register entry names see-through surfaces in rooms.

## Symptom

In the Andrano Ancestral Tomb a cobweb that is built into the room is drawn as a solid dark sheet. In the original it is see-through. Other surfaces with a see-through texture (leaves, banners, grates) that are built into rooms may show the same.

## Where

The conversion of meshes into room geometry: the texture of such a surface loses its transparency on the way.

## How it happened

Not known yet. The places to look at are the material flags of the converter, the room bake and the texture palette.

## Why it was not caught

No check counts the see-through surfaces of the game that end up drawn opaque.

## Reproduction

Enter the Andrano Ancestral Tomb and look at a cobweb.

## Repair

None yet. Every see-through surface of the game is to keep its transparency in rooms.

## Verification

Not verified yet. Pictures of this cobweb and two others are the proof.

## Prevention

A build-time count of see-through surfaces drawn opaque, which must be zero.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Town and interior import (`town-import`). The town importer converts every town and interior within engine limits; doors lead somewhere. See [families](README.md#families).

- AW-20260928-08 (no report page): Census wall/hanging texture quality or mapping
- [IMPORT-DOORBANK-CITY-36](IMPORT-DOORBANK-CITY-36.md): The whole-city Vivec frame holds 157 load doors, over the engine's 128-row door bank
- [IMPORT-TEST-CELLS-31](IMPORT-TEST-CELLS-31.md): Development test cells would be imported with the world
- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"
- TOWN-ARRIVAL-002 (no report page): Town flora fallback picked the wrong Balmora region
- TOWN-FLORA-BINDING-003 (no report page): Town flora staging rejected a valid legacy sprite binding
- [TOWN-FRAME-CEILING-32](TOWN-FRAME-CEILING-32.md): Ground above the town frame ceiling (2,048 units) leaks the map
- [TOWN-INTERIOR-SAVEID-ORDER-33](TOWN-INTERIOR-SAVEID-ORDER-33.md): Town interior save IDs are numbered across towns: listing a room for an earlier town renumbers every later town's rooms
- [VIVEC-ROOMS-UNREACHABLE-32](VIVEC-ROOMS-UNREACHABLE-32.md): Excluded Vivec hub rooms leave converted rooms unreachable

Related bugs in other categories:

- CHIM-FENCE-WRONG-ARCHIVE-64 (no report page): The see-through texture check read a texture from the wrong archive and stopped the CHIM stage
- CHIM-MODEL-FENCE-FACES-64 (no report page): CHIM model faces cannot be alpha-tested, so crossed tree panels cannot be drawn as model variants

<!-- END GENERATED CATEGORY -->
