# BUILD-SEYDA-CULL-STABLE-32: From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)

## Status: 8 October 2026

Open. Found by the from-scratch build after the builder fixes. Part of the Seyda Neen regeneration gap (BUILD-SEYDA-REGEN-30); covered by the recorded exception for v0.0.32.

## Symptom

The actor-contact stage fails on region sn000 in `canonical_bsp_cull._stable_local_parts`:
"Serialized placement fragment is not repeat-stable". This is the first time a from-scratch
build reached it; the stage crashed earlier before (BUILD-ACTOR-CONTACT-CALL-32).

## Where

`tools/canonical_bsp_cull.py` (Seyda Neen canonical terrain cull).

## How it happened

Unknown.

## Why it was not caught

The stage never ran from scratch since v0.0.27.

## Reproduction

Run the builder from scratch with your own data.

## Repair

Not yet; Seyda Neen is rebuilt by the CHIM streamer, so this is handled by the recorded
exception until then.

## Verification

Pending.

## Prevention

From-scratch builds before every release.
