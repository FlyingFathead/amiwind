# CONVERT-COLLISION-FALLBACK-32: Five Balmora meshes fall back to a collision union in qbsp

## Status: 8 October 2026

Open. Found by the CHIM Balmora build; the legacy dev1 conversion shows the same fallbacks.

## Symptom

`ex_hlaalu_b_11`, `_18`, `_21`, `_23` and `ex_velothi_temple_02` fall back to a single collision union in
qbsp, so their collision is coarser than their shape.

Also, since the VIVEC-ARENA-ACTORS-32 fix (8 October 2026): the Vivec canton shells
(`ex_vivec_c_04` refs 466157, 466153, 466160, 466164, 117156 and `ex_vivec_c_02` ref 82613) fall
back 22 times across the Arena regions after a qbsp "non-convex face"; the fallback keeps every
surface plate with its own exact standing bevels.

## Where

Mesh collision conversion (shared by the legacy and CHIM builders).

## How it happened

Unknown.

## Why it was not caught

Fallbacks are logged but not counted or gated.

## Reproduction

Convert Balmora; look for the collision-union fallback lines.

## Repair

Not yet: find why qbsp rejects their pieces; count fallbacks in the build report.

## Verification

Pending.

## Prevention

A fallback count in the build summary with a limit.
