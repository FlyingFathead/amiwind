# CONVERT-DEGENERATE-FACES-32: The converter writes degenerate faces (no area, slivers, repeated vertices)

## Status: 8 October 2026

Open. Found by the face validator (tools/check_faces.py) over every map of the shipped v0.0.31 image.

## Symptom

Shipped maps contain 17 faces with fewer than three distinct vertex positions (10 Seyda Neen
sub-cells), 1,998 zero-area faces, 374 slivers and 25 faces with repeated vertices. They
cost memory and drawing work and can confuse the edge drawer.

## Where

Mesh converter output (brush-entity models); 29 zero-area faces in terrain.

## How it happened

Merged or clipped polygons are not cleaned.

## Why it was not caught

No degenerate-face check.

## Reproduction

check_faces.py over the shipped image.

Related, lower priority (v0.0.32-dev1 build log, 8 October 2026): ericw `qbsp` reported
"CheckFace: Found a non-convex face" while compiling Balmora's collision unions (the fallback to
exact planes) for `ex_hlaalu_b_21` (error size 0.001), `ex_hlaalu_b_11` (2.31 and 9.69) and
`ex_hlaalu_b_23` (10.62). The build continued; the effect on the collision hulls is not measured.

## Repair

The shared face builder drops degenerate faces; the validator then fails on them.

## Verification

Pending.

## Prevention

Validator gate.
