# Shared models for harvestable mushrooms

`tools/prepare_harvest_alias.py` is a bounded, opt-in conversion path for
harvestable mushrooms. It leaves the retained BSP files byte-identical and
stores shared one-frame MDL models separately. AWH4 catalogues bind original
placements to those models. Existing AWH3 brush catalogues can coexist with
AWH4 when they use the same original placement index.

<!-- contents start -->
## Contents

- [Builder step](#builder-step)
- [Inputs and identity](#inputs-and-identity)
- [Conversion and staging](#conversion-and-staging)
- [Memory and admission](#memory-and-admission)
- [Current limits](#current-limits)

<!-- contents end -->

This path requires the corresponding AWH4 runtime. A generated payload is
diagnostic evidence, not proof of native appearance, memory headroom or
production admission. It does not activate mushrooms across the whole world.

## Builder step

Since BUILD-HARVEST-NOT-BUILT-32 the builder makes the harvest data by default;
no plan is supplied by hand. `tools/harvest_build.py` uses the functions below
with the settings the shipped catalogues were made with (at most 256 plants per
map, the runtime bound; interned root spans; per-map model registries):

1. Builder step `harvest` (`harvest_build.py prepare --data-files ... --palette
   <intro scene palette> --out <run>/harvest --jobs N`, after the census): every
   exterior original small-mushroom placement of the master is checked with the
   catalogue graph rules, exported as one packet (`prepare_scenery.export_refs`,
   32-pixel materials) and each model converted once against the runtime palette
   (`prepare_hand_catalog.runtime_palette`: the image's final palette). Writes
   `harvest-source.json`, the packet and `payload/progs/harvest/*.mdl`.
2. Image step, before the final map passes (`clear_baked`): on every shipped
   exterior map, brush entities bound to a harvestable placement in that map's
   coverage are removed with `tools/remove_harvest_geometry.py` (exact reference
   and pose; every surviving surface and hull verified). Only Balmora's
   converter bakes mushrooms today. Receipt `image/harvest/harvest-baked-removal.json`.
3. Image step, after the last map change and before the entity tracker, heap
   audit and content fingerprint (`install`): the plan comes from the region
   directories the image ships (world maps from `world/regions.awr`, Seyda Neen
   and Balmora sub-cells from `seyda-regions.txt` and `balmora-regions.txt`, the
   intro docks from its fixed route bounds); a map's placements are those whose
   transformed bounds touch its coverage. The geometry gate
   (`reject_existing_geometry`) runs on every candidate's final map and stops the
   build on failure. Every candidate catalogue is staged, the repository heap
   check (`check_world_map_heap.inspect_maps`, target ABI sizes) runs on those
   maps, and maps that fail keep no catalogue; models no admitted map uses are
   dropped. A map whose baked mushrooms were removed must be admitted, or the
   build stops. Receipts: `image/harvest/harvest-plan.json` (this format, with
   the final map pins) and `harvest-staging.json` (admitted and refused maps,
   plants, models, heap clearance).

The models must have been converted with the stage's final palette, and the
master must be the one the step read; otherwise the image stops. Output is
byte-identical for every `--jobs` value. `--no-harvest` (debugging only) skips
all of it.

## Inputs and identity

The converter consumes a standalone original master, a bounded scenery packet
and index, the game palette, and an explicit retained-map plan. It verifies
SHA-256 and byte counts for every input. The packet's original NIF source
digest is recorded provenance; this step reopens the packet geometry, not the
original NIF archive. Packet generation must therefore have its own verified
source receipt.

For every selected placement, original master/cell/FRMR identity, CONT model,
position, rotation, scale, container flags, contents and scripts are checked.
Original ingredient and container display names are retained. Unsupported
ownership, scripts, restocking or item types fail conversion. Missing source
items retain the existing explicit missing-node behavior.

Map membership is recomputed from transformed original model bounds and each
map's coverage. The plan's expected placement keys must agree. Existing source
reference bindings and scenery at the exact source pose are rejected to avoid
duplicate geometry. Anonymous baked geometry cannot be identified from an
entity list alone; the retained BSP provenance must separately establish that
the selected original models are absent.

The persistent key remains the original placement identity. Model IDs,
catalogue representation and transient rendering residency never become save
identity. Empty or picked placements remain absent, and changing subcells does
not reroll their resolved contents.

## Conversion and staging

Run conversion and its tests inside the documented Docker development setup.
Use private input/output directories for original assets and converted files.

```sh
python3 tools/prepare_harvest_alias.py convert \
  --plan inputs/harvest-plan.json --master inputs/base.esm \
  --index inputs/scenery-index.json --packet inputs/scenery.mwpak \
  --palette inputs/palette.lmp --base-root inputs/retained-maps \
  --legacy-root inputs/legacy-overlay --budget inputs/heap-bindings.json \
  --media-payload inputs/media-payload --out output/harvest-candidate
```

The plan format is `AmiWind external harvest plan 1`. Its `inputs` dictionary
contains `{sha256, bytes}` pins for `master`, `index`, `packet` and `palette`.
`global_slots` and `global_catalogue_sha256` bind the full original placement
index. Each `maps` row supplies `name`, relative BSP `path`, its hash and size,
map `origin`, two-dimensional `coverage`, and expected full placement `keys`.
Optional `legacy` rows bind the BSP, original conversion report and AWH3
catalogue by relative path/hash/size. Legacy catalogues are regenerated from
the original records and their actual brush entities and must match exactly.

The converter emits shared MDLs, AWH4 catalogues, verified optional pickup
audio and an exact `external-harvest-manifest.json`. It records retained BSP
dependencies without copying large map files during a source-only check.
Missing pickup audio remains a visible warning in the manifest.

The separate `stage` command builds only a **fresh directory** and rechecks
every copied byte against the manifest. It cannot edit an HDF, overwrite an
existing installation, or waive failed heap admission:

```sh
python3 tools/prepare_harvest_alias.py stage \
  --payload output/harvest-candidate --base-root inputs/retained-maps \
  --legacy-root inputs/legacy-overlay --out output/new-map-payload
```

## Memory and admission

An unchanged BSP does not mean the external models cost no memory. The budget
must include all unique model caches, the worst source-file plus decoded-model
hunk fallback, and the measured target static storage delta. Host structure
sizes are not a substitute for the target ABI. The receipt binds the measured
target result and each baseline map hash. The conservative surcharge also
applies to included legacy maps rather than assuming caches vanish immediately.

The budget input supplies `target_struct_sizes_bytes`,
`target_measurement_sha256`, `target_static_delta_bytes`, `heap_budget_bytes`
and one baseline row per included map (`map`, `bsp_sha256`, `bsp_bytes`,
`estimated_total_bytes`). These are reviewed target measurement inputs, not
values to tune until admission passes. Failed inherited allowances remain
failed; an unchanged number of failing maps does not demonstrate acceptance.
Missing budget evidence is **unknown**, not a pass. Native headroom and model
admission must still be measured with the exact candidate.

## Current limits

- At most 24 original placements per bounded batch and map by default (the
  builder step uses the runtime bound, 256), and 8 shared models per map.
- Original surfaces are retained and split at repeated-UV boundaries; the
  shared quantizer preserves coincident material seam positions.
- Opaque models with 1–3 materials use 32-pixel source material tiles.
- One MDL frame is used, with original placement rotation and scale applied by
  the runtime. There is no pickup animation or per-frame geometry allocation.
- MDL position quantization and integer UV coordinates have recorded errors.
- The current exporter writes vertex normal index zero. Alias lighting differs
  from brush lighting, so native appearance must be reviewed explicitly.
- Proximity unloading, global model admission and the larger placement-capacity
  experiment are separate work; this converter does not silently enable them.

The gameplay fingerprint includes each AWH4 catalogue and each distinct model's
actual bytes. Model changes therefore cannot silently reuse an incompatible
save namespace. Existing no-catalogue behavior and AWH3 conversion remain
unchanged.
