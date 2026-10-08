# BUILD-NO-OVERLAY-32: The builder has no engine-overlay command; dev measurements used a private script

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

Measuring a new engine on the shipped image needed the private `overlay_multi.py`; the
repository builder cannot put a new engine onto an existing image.

## Where

`tools/build_aga.py`.

## How it happened

Overlay was done privately before the one-builder rule.

## Why it was not caught

No rule until 8 October 2026.

## Reproduction

Try to test a new engine on the v0.0.31 image with the repository builder only.

## Repair

Not yet: an `overlay` command with tests (part of the builder config/versions work).

## Verification

Pending.

## Prevention

One builder for every build we make.
