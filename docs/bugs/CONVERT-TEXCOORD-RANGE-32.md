# CONVERT-TEXCOORD-RANGE-32: Converter does not check the 16-bit texture-coordinate range

## Status: 8 October 2026

Open. Found by the texture-mapping snapping test.

## Symptom

The converter checks surface extents but not that texture coordinates stay within the
engine's 16-bit range; only the later map optimizer catches it ("Surface short overflow
unsupported"). Today's converter does not trigger it on the tested maps.

## Where

`tools/prepare_mesh_bsp.py` surface checks.

## How it happened

Only extents were checked.

## Why it was not caught

No converted map came close until a snapping experiment did.

## Reproduction

Convert with texture offsets near the 16-bit edge.

## Repair

One repair for all three (owner, 8 October 2026: no path-specific patches): a single
face builder used by every converter path (plane from the whole polygon, refit after
merging, the engine's extent rule, texture-coordinate range, lightmap size from stored
values), and a face validator run on every map as a builder gate. The validator runs
first over the shipped maps to measure how many faces are wrong today. The snap-mode
plane fix is removed once the shared builder is in.

## Verification

Pending.

## Prevention

Converter test at the range edge.
