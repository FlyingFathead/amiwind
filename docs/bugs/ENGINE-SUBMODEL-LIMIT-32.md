# ENGINE-SUBMODEL-LIMIT-32: Map loading does not check the submodel count against MAX_MODELS

## Status: 8 October 2026

Open. Latent; found by the distant shell prototype. The builder's model budget prevents it today.

## Symptom

`SV_SpawnServer` copies every submodel of the map into the model precache (256 entries)
without checking the count, as in stock Quake. A map with more submodels than fit would
write past the precache and the inline-model name table.

## Where

`engine/aga/src/sv_main.c` (`SV_SpawnServer`, `localmodels`).

## How it happened

Inherited from Quake, where maps never came close.

## Why it was not caught

The builder caps models per map, so no map reached it.

## Reproduction

Load a map with more than 255 submodels.

## Repair

Not yet: check `numsubmodels` against the precache size and stop with a clear error; needed
before any change that widens MAX_MODELS (world streamer).

## Verification

Pending.

## Prevention

Engine test with an oversized submodel count.
