# LOADER-STAGING-PEAK-32: Map loading stages most lumps in temporary memory before decoding, raising the heap peak

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan. Not yet measured on its own.

## Symptom

`AW_LoadBrushSection` reads most lumps into `Hunk_TempAlloc` and then decodes them, so the
loader peak holds both copies; faces plus their staged copy are about half the peak in the
Vivec heap failures (VIVEC-HEAP-31).

## Where

`engine/aga/src/model.c` (`AW_LoadBrushSection`).

## How it happened

Simplest loader structure.

## Why it was not caught

The heap check models the peak but nobody tried decoding from small read slices.

## Reproduction

Compare the modelled loader peak with and without the staged copy.

## Repair

Not yet: decode straight from 16 KiB read slices into the final structures (estimated 1-1.5 MB
less peak); re-run the Vivec and world heap checks.

## Verification

Pending.

## Prevention

Heap model and engine stay in step (existing heap tests).
