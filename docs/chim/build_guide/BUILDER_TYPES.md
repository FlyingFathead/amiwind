# Builder types

## How CHIM builds relate to the legacy chain today

A build is `--builder chim` (the default from v0.0.33: the CHIM areas Balmora and Seyda Neen from
`config/build-defaults.json`, or the towns named with one or more `--chim-area TOWN`, as a CHIM world)
or `--builder legacy` (every exterior as region maps, as in v0.0.32; selectable and tested). A CHIM
build with Seyda Neen also needs `--seyda-recorded DIR` (BUILD-SEYDA-REGEN-30); asset-free dry runs
and terrain-only builds do not. The legacy builder's plan
and outputs are unchanged by CHIM; the CHIM builder is the legacy plan plus the `chim` stage, with
the image step deciding what ships.

### What still runs, and why

A CHIM plan still runs these legacy stages, because a later step reads their output
(`tools/chim/plan.py`; every CHIM build records the list in `build-state.json` `chim_plan`):

1. The CHIM towns' region conversion (`balmora`; Seyda Neen's region maps are made in the image step
   or taken from the recorded maps): the CHIM frame maps copy their actors, player starts and point
   entities from the town's final region maps and check every static both ways.
2. The open-world chain (`world-terrain`, `world-scenery-assets`, `world-scenery`): the image step
   installs the open-world overlay, and the open world is not on CHIM yet.
3. World flora (`world-flora`): the image installs the Seyda Neen and Balmora town flora from it;
   the CHIM world adds the same flora as meshes, and the frame-map check needs both sides.
4. The shared converter stages (scene chain, scenery, census palette, world survey, harvest, flora
   assets): the CHIM stage reads them (`tools/chim_build.py --legacy-run`), and the interiors are
   built from the same chain.
5. Extra towns (`town-<id>`, only when one is shipped or named with `--extra-town`; the Vivec Arena is
   withdrawn from v0.0.33 default builds): `import_town` runs in the scene chain, which later stages copy;
   its output is left out of a CHIM image (below).

### What ships

- The CHIM towns as a CHIM world (one more world volume) with their frame maps
  (`maps/<town>-chim.bsp`; for Seyda Neen also `intro_docks-chim.bsp` and `sncourt-chim.bsp`).
- Interiors as Quake maps, built as before.
- The open world with the legacy builder's maps, as "not yet CHIM".
- No Vivec Arena: a CHIM build leaves extra towns that are not CHIM areas out whole (exterior maps,
  region and door tables, harvest catalogues), each file recorded in `build.json`
  `chim_world.removed_legacy` with the reason "not on CHIM yet". The engine finds no such
  destination until the CHIM Arena lands.
- Seyda Neen on CHIM needs the recorded v0.0.31 Seyda Neen maps from your own v0.0.31 image
  (`--seyda-recorded DIR`); the frame maps are checked against them.

### The safety net

The image step removes the CHIM towns' legacy exterior maps (`chim.frame_map.remove_legacy_areas`)
and the towns not on CHIM (`chim.frame_map.remove_towns_not_on_chim`), lets the map optimizer's
receipt follow the new map set, and right before the volumes are packed fails the build if any
legacy exterior map of a CHIM area, or any file of a town left out, is in the payload
(`chim.frame_map.require_no_legacy_areas`, recorded as `build.json` `chim_world.legacy_check`).

### What comes next

Tracked as CHIM-LEGACY-CHAIN-33, in this order:

1. Frame maps from the converter's entity list instead of the compiled region maps.
2. Town flora for CHIM towns from the flora assets alone (no open-world terrain).
3. The image step without the open-world overlay when no open-world area is built, with the entity
   tracker scoped to the areas built; then the open-world stages leave the CHIM plan.
4. The stages of extra towns not on CHIM out of the CHIM plan; interiors of a town without its
   exterior.

## Disk layout limits (every builder type)

Legacy and CHIM images go through the same disk-layout gate in the image step: partition start and
size below 2 GiB, files below 1 GiB, drive images below 4 GiB, measured layout in `build.json`
(`disk_layout`). Details: [Linux build](../../LINUX_BUILD.md#disk-layout-limits).
