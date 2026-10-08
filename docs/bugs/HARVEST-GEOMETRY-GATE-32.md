# HARVEST-GEOMETRY-GATE-32: The harvest geometry gate was never re-run on the shipped Seyda Neen maps

## Status: 8 October 2026

Fixed in source on v0.0.32-harvest (not shipped at the time of writing). Found by the builder coverage work (comparing the
v0.0.31 harvest files with their plan).

## Symptom

`reject_existing_geometry` (no baked mushroom left where a harvestable one is placed) was not run again on
the shipped Seyda Neen and intro_docks maps.

## Where

The harvest preparation chain.

## How it happened

Maps changed after the gate ran.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

The image step runs `reject_existing_geometry` on the final map of every map that gets a catalogue,
after the last map change, and stops the build on any failure (BUILD-HARVEST-NOT-BUILT-32). Brush
mushrooms a converter bakes where a harvestable plant goes are removed before the final map passes
(`tools/remove_harvest_geometry.py`), and such a map must then be admitted.

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- The gate passes on all 388 candidate maps, including the 62 Seyda Neen sub-cells and the intro
  docks: the recorded Seyda Neen maps carry no baked harvestable mushroom.
- Without the removal it stops on the 17 Balmora maps that bake mushrooms (134 placements).
- `tests/test_harvest_build.py`: the gate refuses a map with a mushroom bound to a placement and a
  map with scenery at a placement's pose; the removal takes out exactly the bound entity; a map
  whose mushrooms were removed but refused by the heap check stops the build.

## Prevention

Harvest becomes a builder step that rebuilds its catalogues from the maps it ships with, with
the geometry gate in the image step.
