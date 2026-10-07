# AmiWind v0.0.30 - The Temple

AmiWind brings Morrowind's landscapes and interiors to the Amiga through a
GPL-licensed conversion pipeline and native engine. This source release includes
project code and documentation; it does not include Morrowind game files.

v0.0.30 collects the development builds since v0.0.29
([dev3](RELEASE-v0.0.30-dev3.md), [dev4](RELEASE-v0.0.30-dev4.md),
[dev5](RELEASE-v0.0.30-dev5.md), [rc1](RELEASE-v0.0.30-rc1.md)). The release
candidate was playtested in WinUAE on 7 October 2026: the Balmora Temple,
Census office, Balmora, torches and roadside mushroom picking work; WinUAE
music crackles at some transitions remain (see Known issues).

## Changes

- **Fixed in rc1: misplaced objects in the Census and Excise Office.** dev5's
  lighting rebuild of the Census map paired the new geometry with an older
  object list in which one object was missing, so 67 of 140 objects used their
  neighbour's model: an upright rug poking through the upper floor (seen as a
  black hole in the ceiling below) and a tapestry inside a bookshelf. rc1 uses
  the correct object list with the same flames; owner-accepted in the rc1
  playtest.
  ([CENSUS-ENTITIES-30](BUG_JOURNAL.md#census-entities-30-misplaced-objects-in-the-census-and-excise-office-7-october-2026))
- **The Balmora Temple is whole again.** The scene converter applied the
  rotation stored on some meshes' NIF root node; Morrowind ignores it and keeps
  only the root's position and scale. The lower-level Velothi walls were turned
  a quarter turn, which left missing and edge-on walls, see-through holes and
  floating objects. The same fix repairs Tharys Ancestral Tomb and the Nord
  fireplaces in five Seyda Neen interiors, which faced away from the room.
  ([BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md),
  [CONVERTER-ROOT-ROTATION-30](bugs/CONVERTER-ROOT-ROTATION-30.md))
- **Crash fix:** a `NUM_FOR_EDICT: bad pointer` crash on a Seyda Neen region
  change. The opening sequence kept actor pointers across a map reload.
  ([INTRO-ROLES-30](bugs/INTRO-ROLES-30.md))
- **Options > Controls:** rebind gameplay actions from the menu. Greyed rows
  show planned actions (inventory, quick keys, magic). Arrow keys now move like
  W/A/S/D. See [keymaps](KEYMAPS.md).
- **NPC lighting:** NPCs standing on converted floors take that floor's light
  instead of ambient only, so they no longer appear as dark silhouettes in
  interiors (`aw_actor_brush_light`).
- **Glow and flames:** glowing materials such as lantern glass, Dwemer lights,
  mushrooms and lava are lit by their own glow (`dbg emissive`), and placed
  fires and candles show a flame (`aw_static_flames`). Both need a map rebuild
  to appear; in this release that is the Temple's lantern and the Census and
  Excise Office's fireplace and candles. See
  [lanterns and torch lighting](LANTERNS_AND_TORCH_LIGHTING.md).
- **Faster Seyda Neen crossings:** converted NPC models are read once instead of
  twice while a region loads; the heavier crossings read about 15 % less
  (`aw_alias_single_pass`). See [Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md).
- **Less music crackle in WinUAE:** a v0.0.30-dev5 playtest on 7 October 2026
  reports much less music crackle in WinUAE than v0.0.29. It still crackles
  during some map changes, such as going from the prison ship's hold to the
  deck. No audio code changed in this cycle; lighter loading is the likely
  reason, not yet measured.
- **Warning-free engine:** the Amiga engine builds without compiler warnings and
  the build fails on any new one. The cleanup removed an unreachable, broken
  16-bit surface drawer, bounds all path formatting and moves a 15 KB sprite
  buffer off the stack. See [AGA build](AGA_BUILD.md).
- **Tools:** `tools/analyze_subcell_redundancy.py`
  ([sub-cell redundancy](SUBCELL_REDUNDANCY.md)),
  `tools/poi_checklist.py` ([points of interest](POI_CHECKLIST.md)) and
  `build_aga.py image --canonical-land-source` for the Seyda Neen partition.

Every new lighting and loading change has a console switch, so it can be
compared in place or turned off if something looks wrong.

## Known issues

- **Seyda Neen crossings** still pause for about 1.0-1.5 s per sub-cell load
  in the emulator. The sub-cell maps are large (up to about 5 MB) and fill the
  heap, so cached models are dropped on each crossing. A lighter rebuild of the
  Seyda Neen maps is in progress for the next version.
- **Load freeze (SEYDA-LOAD-HANG-30):** in about 5 of 70 automated FS-UAE runs
  of a Seyda Neen route, the game stopped during a region load. The game was
  waiting for a disk read that never completed; the cause is open. See the
  [journal](BUG_JOURNAL.md).
- **Seyda Neen maps cannot yet be regenerated** from the public tools
  ([BUILD-SEYDA-REGEN-30](BUG_JOURNAL.md)).
- **Glow and flames** reach other maps only as they are rebuilt; the prison
  ship's cabin lantern is still unlit. The flame look is still being tuned.
- One Balmora exterior placement (`furn_pathspear_03`) still has the root
  rotation; it uses a separate exterior pipeline.
- From v0.0.29: the Bitter Coast mushroom report, WinUAE music pauses and
  crackle during some map changes (reduced, not gone), the idle-to-punch hand transition, 44
  modeled memory reserve warnings, and incomplete world, quest and interior
  coverage. See the [tracker](BUGS.md) and [v0.0.29 notes](RELEASE-v0.0.29.md).
