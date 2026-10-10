# Builder types

## How CHIM builds relate to the legacy chain today

A build is `--builder chim` (the default from v0.0.33: the CHIM areas Balmora and Seyda Neen from
`config/build-defaults.json`, or the towns named with one or more `--chim-area TOWN`, as a CHIM world)
or `--builder legacy` (every exterior as region maps, as in v0.0.32; selectable and tested). From
v0.0.35 a CHIM build with Seyda Neen needs no recorded input: Seyda Neen is converted from your data
(`--seyda-recorded DIR`, the legacy recorded v0.0.31 maps, is optional and NOT RECOMMENDED since v0.0.31;
BUILD-SEYDA-REGEN-30). The legacy builder's plan
and outputs are unchanged by CHIM; the CHIM builder is the legacy plan plus the `chim` stage, with
the image step deciding what ships.

See [Which Seyda Neen is in my build?](../../LINUX_BUILD.md#which-seyda-neen-is-in-my-build) for which Seyda Neen an image holds.

### CHIM-native towns (EXPERIMENTAL, `--chim-native-towns on`)

With `--chim-native-towns on` (off by default in v0.0.35), builds have one Balmora: the
CHIM one. A CHIM town other than Seyda Neen has no legacy region maps
([CHIM-LEGACY-CHAIN-33](../../bugs/CHIM-LEGACY-CHAIN-33.md)):

- its legacy chain stage (`balmora`, or `town-<id>`) is not in the plan;
- the stage `chim-town-<town>` (`tools/chim_town.py`, after the CHIM world) makes what the frame map
  and the image need from the game data: the residents (models and greeting voices, baked as the
  legacy chain bakes them), the frame map's entities (worldspawn, the player start at the town
  arrival, one actor per resident with its support fitted on the CHIM frame's own collision), the
  region table and the exterior door bank. It reads the CHIM world's own source stage, so nothing
  is converted twice;
- the image step installs those files, writes the frame map from those entities, plans the town's
  harvest catalogues from its region table (the engine loads them by region on the CHIM frame),
  checks the arrival and the actors on the frame's collision and counts the town's CHIM placements
  in the entity tracker. The Balmora layout repair, the legacy town flora and every per-map pass
  on Balmora region maps are gone with the maps.

Checked against a legacy-chain build (the v0.0.33-dev1 MiniWind image): the same region table,
player start, worldspawn and resident files byte for byte, the same 18 actors, 17 of them identical
and one 0.003 units lower (its support fitted on the CHIM frame's collision instead of the legacy
region map's).

The legacy chain stays selectable: `--legacy-area balmora` (debugging and legacy comparisons only;
the build warns) builds Balmora's region maps in a CHIM build and the frame map copies its entities
from them, as before; `--builder legacy` builds no CHIM world at all.

### What still runs, and why

A CHIM plan still runs these legacy stages, because a later step reads their output
(`tools/chim/plan.py`; every CHIM build records the list in `build-state.json` `chim_plan`):

1. Seyda Neen's region maps when Seyda Neen is a CHIM area (made in the image step or taken from the
   recorded maps): its frame maps copy their actors, player starts and point entities from them and
   check every static both ways. Other CHIM towns have no region conversion (above), unless
   `--legacy-area TOWN` asks for it.
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
- Seyda Neen on CHIM: the frame maps are checked against the Seyda Neen region maps the builder
  converts from your data (without the terrain visual cull; those maps never ship). A legacy build
  with Seyda Neen still needs `--seyda-recorded DIR` (BUILD-SEYDA-CULL-STABLE-32). Optional, NOT RECOMMENDED since v0.0.31: `--seyda-recorded DIR` (the legacy recorded v0.0.31 maps from your own
  v0.0.31 image) uses those as the reference instead, kept byte for byte (v0.0.33 required it).

### The safety net

The image step removes the CHIM towns' legacy exterior maps (`chim.frame_map.remove_legacy_areas`)
and the towns not on CHIM (`chim.frame_map.remove_towns_not_on_chim`), lets the map optimizer's
receipt follow the new map set, and right before the volumes are packed fails the build if any
legacy exterior map of a CHIM area, or any file of a town left out, is in the payload
(`chim.frame_map.require_no_legacy_areas`, recorded as `build.json` `chim_world.legacy_check`).

### What comes next

Tracked as CHIM-LEGACY-CHAIN-33, in this order:

1. Frame maps from the converter's entity list instead of the compiled region maps: done for every
   CHIM town except Seyda Neen (`chim-town-<town>`).
2. Town flora for CHIM towns from the flora assets alone (no open-world terrain).
3. The image step without the open-world overlay when no open-world area is built, with the entity
   tracker scoped to the areas built; then the open-world stages leave the CHIM plan.
4. The stages of extra towns not on CHIM out of the CHIM plan; interiors of a town without its
   exterior.

## Disk layout limits (every builder type)

Legacy and CHIM images go through the same disk-layout gate in the image step: partition start and
size below 2 GiB, files below 1 GiB, drive images below 4 GiB, measured layout in `build.json`
(`disk_layout`). Details: [Linux build](../../LINUX_BUILD.md#disk-layout-limits).

## CHIM lighting type

`--chim-lighting-type TYPE` (config key `chim_lighting_type` in `config/build-defaults.json` or a `--build-config`
file) chooses how a CHIM world is lit. The default is `hybrid`.

| Type | What it does |
| --- | --- |
| `none` | No light sources: constant terrain light, models without lightmaps, an empty night lamp table |
| `lamps` | The v0.0.33 lighting: the night lamp table of lamps, lanterns, torches, fires and candles |
| `hybrid` | The default: terrain lightmaps, a light level per placed model, the nearest light sources of every class as dynamic lights, per-plant glow. The parts land step by step; the CHIM receipt records which are in |
| `baked-e` | Reserved, refused: per-placement lightmaps where a light reaches, for an increased-memory version of the game |
| `full` | Reserved, refused: per-placement lightmaps for every placed model, for an increased-memory version of the game |

Details, measurements and the plan: [CHIM lighting](../LIGHTING.md) and the [CHIM lights roadmap](../LIGHTING_ROADMAP.md).
