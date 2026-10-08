# GATE-NODE-MISSING-31: the local gate never runs the inspector JavaScript tests

## Status: 8 October 2026

Open. Found while adding the inspector's sub-cell cuts.

## Symptom

`tests/test_polycount_markup.js` (the 3D inspector's checks) is skipped in every
local gate run: the Docker build and validation images have no Node.js, so
`tests/test_polycount_preview.py` skips the JavaScript part. The sub-cell cuts
work was checked in a browser shim instead. A full-suite run also showed one
more skip than earlier gates (5 instead of 4), not yet identified.

## Where

The gate images and `tests/test_polycount_preview.py`.

## How it happened

The JavaScript tests were written to run under Node, which the hosted CI may
provide but the local images never did; a skip does not fail the gate.

## Why it was not caught

Skips are counted but not itemised in the gate summary.

## Reproduction

Run the full suite in the build container and list the skipped tests.

## Repair

Not yet: add Node.js to a gate image (offline package), run the JavaScript
tests in the gate, and itemise skips in the gate summary.

## Verification

Pending.

## Prevention

The gate reports every skip by name and fails on an unexpected new skip.
