# ESTIMATE-HEAP-STALE-32: World estimate heap coefficients were fitted to the old loader model

## Status: 8 October 2026

Open. Found by the map loader rework (decoding without staging).

## Symptom

The world estimate's heap coefficients (`config/world-estimate-model.json`) were fitted before
the loader stopped staging lumps, so it now overestimates heap.

## Where

`config/world-estimate-model.json`.

## How it happened

Model change after calibration.

## Why it was not caught

No recalibration step tied to heap model changes.

## Reproduction

Compare estimate and heap check on the calibration maps.

## Repair

Refit on the 1,102-map calibration set with the new heap model.

## Verification

Pending.

## Prevention

A test that the estimate's heap model version matches the heap checker's.
