# TOOLKIT-TEST-POINTERLOCK-31: inspector test left pointer lock set

## Status: 8 October 2026

Fixed in source on v0.0.32-dev, with the sub-cell cuts work.

## Symptom

Earlier checks in `tests/test_polycount_markup.js` leave
`document.pointerLockElement` set, so a later drag check behaves as if the mouse
were captured.

## Where

`tests/test_polycount_markup.js`.

## How it happened

The tests share one page state and the pointer-lock state was never reset.

## Why it was not caught

The JavaScript tests do not run in the local gate
([GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md)).

## Reproduction

Run the markup tests with a drag check after a pointer-lock check.

## Repair

The drag check clears the pointer-lock state first.

## Verification

All 16 milestones pass in a browser run.

## Prevention

Run the JavaScript tests in the gate (GATE-NODE-MISSING-31).
