# CONVERT-FACE-WINDING-32: Six prison faces are wound opposite to their plane side

## Status: 8 October 2026

Open. Found by the face validator (tools/check_faces.py) over every map of the shipped v0.0.31 image.

## Symptom

Six faces of one brush model in the Seyda Neen prison are wound against their plane side flag
(tilts of 45 to 85 degrees), so the renderer swaps their leading and trailing edges.

## Where

Interior converter output (merged faces).

## How it happened

Plane chosen from vertices that do not match the polygon.

## Why it was not caught

No winding check.

## Reproduction

check_faces.py on the prison map.

## Repair

The shared face builder (one for every path) computes plane and side from the whole polygon
and checks winding; see CONVERT-FACE-PLANE-32.

## Verification

Pending.

## Prevention

Validator gate (plane_side fails).
