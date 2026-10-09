# ASSETS-ARCHIVE-ORDER-32: Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | asset readers (tools/npc_geometry.py and scenery readers) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: Readers ignore expansion archives: wrong textures, and on Steam 1,611 meshes cannot be resolved. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the GOG/Steam loose-file A/B (measured on both installations, no repository change).

## Symptom

The game loads Morrowind.bsa, then Tribunal.bsa, then Bloodmoon.bsa (later wins). 47 textures,
2 icons and 1 mesh in Morrowind.bsa are overridden by the expansions. AmiWind's world geometry
readers use Morrowind.bsa only, so 7 textures in world geometry (`tx_velothi_door_01`,
`tx_velothi_doorstrip_01`, `tx_wood_oldwood` and its strip and design, `tx_metal_strip_02`,
`tx_keyhole_04`) are the pre-expansion versions (mean RGB difference about 2 to 3.6).
`npc_geometry.Assets` reads loose files first, then Morrowind.bsa only: on GOG it gets the
expansion version from the loose copy, on Steam the Morrowind.bsa one (for example
`tx_c_robe_comm3_01/02`, `tx_c_ring_expensive_3`, the torch icon), and on Steam it cannot
resolve 1,611 meshes that exist only in the expansion archives. On GOG one texture name can come
from two versions in the same image.

## Where

`tools/npc_geometry.py` (`Assets`) and the Morrowind.bsa-only readers (`prepare_scenery`,
`prepare_quake`, `import_town`, `prepare_doors`, `prepare_harvest_room`, `prepare_tree_sprites`,
`town_interiors`, `night_windows`). `world_estimate_data.MeshSource` already follows all three.

## How it happened

The readers were written for Morrowind.bsa; the expansion archives were never part of the lookup.

## Why it was not caught

No comparison against the game's archive order; GOG loose files hid it for actors.

## Reproduction

Compare the 47 overridden textures in an image with the Bloodmoon/Tribunal copies.

## Repair

Not yet: one shared asset lookup with the game's order (loose files, then archives in
`Morrowind.ini` order, later wins), used by every reader.

## Verification

Pending.

## Prevention

Test that every reader resolves through the shared lookup; edition A/B.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions
- [BUILD-PLUGIN-SOUNDS-32](BUILD-PLUGIN-SOUNDS-32.md): A GOG image includes 8 converted sounds that only an official plugin uses

<!-- END GENERATED CATEGORY -->
