# HARVEST-PILOT-SHIPPING-32: 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue

## Status: 8 October 2026

Fixed in source on v0.0.32-harvest (not shipped at the time of writing). Found by the builder coverage work (comparing the
v0.0.31 harvest files with their plan).

## Symptom

24 Seyda Neen maps ship the dev4 pilot catalogue (six plants) and 3 pilot models instead of the full
catalogue.

## Where

v0.0.31 harvest files for those maps.

## How it happened

The pilot was never replaced. The standalone chain also could not make the whole set in one run:
`prepare_harvest_alias.convert_plan` caps the entire run at 8 shared models ("External model
registry exceeds 8 shared models"), while the master has 8 non-pilot models and v0.0.31 shipped 11
including the pilot ones, so the shipped set was assembled from three separate runs, and the
pilot run's results stayed in.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

The harvest step generates every catalogue with the same settings (256 plants per map, the runtime
bound) and converts the models once (BUILD-HARVEST-NOT-BUILT-32); nothing is carried forward, so no
pilot catalogue or pilot model can ship. The new step (commit 0331f76) checks the runtime limit of 8
models per map instead of per run (`tools/harvest_build.py`: a map over the plant or model limit is
refused), so one run makes every catalogue.

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- 8 shared models, byte-identical to v0.0.31's 8 non-pilot models; the 3 pilot models are gone.
- Every catalogue is a generated AWH4 catalogue of its map's full placement set; the Seyda Neen
  results are in HARVEST-SEYDA-STALE-32.

## Prevention

Harvest becomes a builder step that rebuilds its catalogues from the maps it ships with, with
the geometry gate in the image step.
