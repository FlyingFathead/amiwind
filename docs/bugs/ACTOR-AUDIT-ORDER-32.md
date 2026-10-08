# ACTOR-AUDIT-ORDER-32: The actor audit lists "Canonical owner omits" errors in set order

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (d776653), not shipped at the time of writing. Present before
v0.0.32. Found by the image-parallel work (byte-identical audit checks).

## Symptom

The "Canonical owner omits its actor placement" errors come from iterating a set, so their order
can differ between processes and the audit report is not byte-identical across runs. Only builds
that have such errors are affected.

## Where

`tools/check_actor_ground.py` (canonical owner check).

## How it happened

The missing placements are collected in a set and reported in iteration order.

## Why it was not caught

The audits compared so far had no such errors.

## Reproduction

An audit with at least two such errors, run under two `PYTHONHASHSEED` values.

## Repair

In source (d776653): the errors are written sorted by owner and reference.

## Verification

`tests/test_actor_ground.py` `test_owner_omission_errors_are_sorted_in_every_process` (the same
audit under four hash seeds gives the same bytes).

## Prevention

A test that writes the audit with such errors under several hash seeds and compares the bytes.
