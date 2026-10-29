# AmiWind v0.0.56-dev1 (in development)

Development snapshot, 29 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.55](RELEASE-v0.0.55.md).

The first snapshot of v0.0.56, a small one built on v0.0.55: two teleport names fixed and added, a garbage collector
that takes long lists, and new checks and studies in the docs. The game needs 32 MB of Fast RAM, and the emulator
presets of this snapshot have it. What v0.0.55 brought is listed in its [notes](RELEASE-v0.0.55.md).

## New since v0.0.55

- **`dbg tp khuul`**: a new console name for Khuul, on the street outside Thongar's Tradehouse, where that door puts
  you ([console commands](../../AMIWIND_CONSOLE_COMMANDS.md)).
- **`dbg tp suran` lands on a street.** Suran is a hillside town and the old point, the middle of its cell, landed
  among the rocks between its terraces; it is now the street outside the Suran Tradehouse's lower door.
- **The garbage collector takes a list of any length**: `tools/build_gc.py plan ... --delete --items-file FILE`
  deletes exactly the expired items a file lists, for clean-outs too long for `--item` arguments
  ([free disk space](../../BUILD_CACHE.md#free-disk-space)). Old runs are mostly links into the shared pool, so
  deleting them frees little until the next plan expires the pool objects only they used.
- **Two new repository checks in every gate**: no public link may carry a tracking query (`utm_...`, `fbclid` and the
  like), and every bug report page must be in the release file list.
- **Docs**: a [Raspberry Pi with Amiberry](../../REAL_HARDWARE.md#raspberry-pi-with-amiberry) section (what boots,
  the preset, starting straight into the game, and what you need to own); a
  [study of cheap trees with some depth](../../WORLD_TREE_SPRITES.md#study-cheap-trees-with-some-depth-29-october-2026)
  for the trees beside harvest plants and Solstheim's forests; two new bugs from a census of the game's records, the
  gates and levers that do not move yet ([DOOR-MOVERS-NOT-IN-55](../../bugs/DOOR-MOVERS-NOT-IN-55.md)) and the traps
  that never fire ([DOOR-TRAPS-NOT-SPRUNG-55](../../bugs/DOOR-TRAPS-NOT-SPRUNG-55.md)).

## Known in this build

- Mushrooms and other plants growing at the foot of a sprite tree are hard to pick: the flat tree stands in the way
  ([HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](../../bugs/HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md), raised to
  high).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
