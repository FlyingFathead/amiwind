# Original map data and private reference layers

14 October 2026. This is a source/format audit and implementation plan, not a map import, rendered comparison or coverage change. The inspected OpenMW reference is revision `a882697616a186ef394ae049df79f96de793d053`; generation details can differ between versions. The original executable's renderer was not inspected.

## What is stored and what is generated

| Layer | Input or storage | Verified meaning |
| --- | --- | --- |
| Original exterior terrain | Master/plugin `LAND` records | `INTV` contains signed cell coordinates; `WNAM` is 81 signed bytes representing a 9 by 9 coarse height grid. `VHGT` stores the detailed terrain height data used for the 65 by 65 grid. These are terrain records, not a finished map image. |
| OpenMW global base | Loaded exterior `CELL`/`LAND` data | `GlobalMap::render` builds the base at runtime. This reference samples `WNAM` and a 256 by 1 OpenMW palette resource, `textures/omw_map_color_palette.dds`. That resource is OpenMW's palette, not evidence of a complete original-world image asset. |
| OpenMW local map | Loaded scene, terrain, objects and simple water | `LocalMap` renders an orthographic view from above. Interiors use scene bounds and the `northmarker` reference rotation. The detailed local image depends on loaded placements, meshes/materials/textures and rendering state. It is separate from the exploration mask. |
| Original Morrowind save map | `.ess` record `FMAP` | OpenMW's original-save importer reads `MAPH` and raw RGB `MAPD` pixels. Its code notes the original default 512 by 512 size; use the stored size rather than assuming every save is identical. A save image is not proof that all areas were visited or that a full set of local map images exists. |
| OpenMW saved global overlay | Save record `GMAP` | `BNDS` gives cell bounds, `DATA` holds an encoded PNG exploration overlay, and repeated `MRK_` entries hold marker cell coordinates. The renderer can regenerate the base separately. |
| OpenMW saved local exploration | Cell save state and fog data | `HFOW` indicates fog state. `FTEX` stores segment coordinates and image bytes; interiors also carry `BOUN`, `ANGL` and `CNTR`. This revision writes PNG and supports older TGA fog images by save-format version. These masks do not replace the rendered local scene. |

Source: [terrain format](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/components/esm3/loadland.hpp), [global rendering](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwrender/globalmap.cpp), [local rendering](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/openmw/mwrender/localmap.cpp), [original-save conversion](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/apps/essimporter/converter.cpp), [global serialization](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/components/esm3/globalmap.cpp), [fog serialization](https://github.com/OpenMW/openmw/blob/a882697616a186ef394ae049df79f96de793d053/components/esm3/fogstate.cpp).

The original-save importer also consumes `CELL` `NAM8` exploration data. It reads 32 bytes, or an interior form with an extra four-byte prefix; its comments interpret this as a 16 by 16 one-bit mask and leave some semantics unresolved. Crucially, this importer discards the local fog data rather than transferring it to the converted save. It uses exterior exploration information while constructing the global overlay. Do not promise complete local exploration restoration from that importer.

This audit does not claim an exhaustive inventory of original map-related artwork. Paper, icons and other UI art may be separate assets; that is different from the terrain, runtime scene map and save-state image/mask layers above. Loading additional plugins can change terrain, placements and the resulting map.

## What AmiWind already provides

[world_progress_background.py](../tools/world_progress_background.py) already generates local-use backgrounds from the owner's master: `topo` uses detailed terrain heights, `world` uses `LAND.WNAM` with the established dark-map palette, and `cells` writes terrain plus original placement metadata. The output image sidecar contains `bounds`, `pixels_per_cell` and `style` in a common north-up cell frame.

The toolkit's [Island (local) loader](../amiwind-toolkit/world-map.html) accepts PNG and JSON selected by the user, using local file reads and image blob URLs. The documented [local layer workflow](AMIWIND_TOOLKIT.md#your-data) already supports these owner-derived files. Reuse it before adding another loader or map generator.

The toolkit's current Local close-up is terrain shading plus placement dots. It is not a textured OpenMW local-map render. Likewise, a WNAM-derived background is not an original-save RGB image and is not proof of exact rendered palette parity. Keep those labels distinct.

## Load an owner-supplied reference background

The existing server and file picker support this already; no additional image loader is required.

Keep a matching `island-world.png` and `island-world.json` together in your private map-data directory. The JSON sidecar uses inclusive exterior-cell bounds in west, south, east, north order:

```json
{"bounds": [-1, -2, 2, 3], "pixels_per_cell": 9, "style": "world"}
```

This synthetic example describes a 36 by 54 pixel image. Keep north at the top; the upper-left cell is west/north. Do not infer bounds from pixel dimensions or stretch an uncalibrated image to fit.

For a local server, point `--data` at that private directory and `--progress` at the separate current CHIM tracker directory:

```sh
python3 tools/toolkit_serve.py --data PRIVATE_MAP_DIRECTORY --progress TRACKER_DIRECTORY
```

Use the address printed by the server, open World Map, and select **Bottom layer > Game world map**. Its page URL carries `?served=1`; it requests `/data/island-world.png` and `/data/island-world.json`. The `--progress` directory supplies conversion status independently. If both topographic and world images are present, Topo remains the initial bottom layer; choose Game world map explicitly.

If a running server already points at the correct directories, replacing its private map files and reloading the page rereads them; these routes send `Cache-Control: no-store`. If the server is offline or points at another directory, metadata registration alone does not make an image visible. Confirm the running binding before claiming a served overlay.

Without a server, open the Toolkit locally and select both files with **Island (local)**. Keep `world` in the PNG filename and `"style": "world"` in the JSON so the existing picker associates them. A PNG alone does not supply geographic bounds.

Validation used synthetic data through the real local HTTP handler: exact image/sidecar responses and content types, uncached rereads, independent progress binding, missing files, unlisted game files and traversal refusal. The page loader was checked as a source contract. These checks establish routing support; browser rendering, image calibration and landmark alignment remain separate acceptance checks. No original image bytes are included in the tests.

## Bounded implementation plan

1. Keep original assets, original/save-derived images, extracted exploration masks and detailed placement JSON outside public source and public exports. Publish only code, schemas and sanitized findings. The existing background generator already states that its game-derived outputs must not be committed or published.
2. Start with the existing private `world` PNG and its matching bounds sidecar. For an owner-supplied PNG, supply a calibrated sidecar in the same format; confirm the loader's chosen style and image orientation. Do not infer world bounds just from image dimensions.
3. Record private input hashes, content/plugin identity, bounds, resolution, source type and whether exploration is baked into the image. Preserve original pixels. Apply the coordinate transform in the viewer rather than repainting evidence. One exterior cell is 8192 original units; the current converted scale is 0.25. Test corners, the origin and at least two known landmarks, including the image's top-down Y orientation.
4. Keep the reference background, exploration mask, town/subcell footprints and converted/audited/native/packaged status as separate layers. Showing an original area on the reference map must never increase conversion or acceptance counts. Existing partial-cell coverage diagrams remain separate project-generated evidence.
5. If an exact saved original map is needed, add a small private `.ess` FMAP reader/export step after validating the stored RGB size and bounds. This is not implemented here. Do not import local fog by claiming the existing OpenMW importer preserves it.
6. If a true local reference render is needed, request the matching cell, content set, pose/bounds/north direction and rendering settings in the established headless OpenMW workflow. Compare it as reference evidence. No new render, map conversion or native session was run for this audit.

Next acceptance is a private overlay load with exact input/sidecar hashes and coordinate/landmark checks, followed by a public-export inspection proving the game-derived files and private bindings are absent. This introduces no new coverage or gameplay acceptance claim.

## Requested original World/Local navigation, 14 October 2026

Extend the existing tracker World/Local navigation with locally supplied
original world and detailed local reference layers. Keep the current
terrain/placement schematic explicitly labelled. Calibrate bounds, north,
selected cell and landmarks, preserving original reference pixels privately.
Keep converted, audited, native-checked, packaged and failed/held/excluded
overlays independent. Original imagery never increases coverage. The current
loader support above does not establish detailed original local imagery,
calibration or visual acceptance; those remain planned.
