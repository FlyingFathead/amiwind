# VIVEC-ARENA-FRAME-EDGE-32: Neighbouring canton bodies end at the Arena frame edge, in view

## Status: 8 October 2026

Open (design limit of the one-frame Arena preview). Found while checking the owner's dev1 reports
for [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md).

## Symptom

Since the VIVEC-ARENA-ACTORS-32 fix the Arena frame keeps the Redoran, Telvanni, St. Delyn,
St. Olms and Foreign Quarter canton bodies whose footprints reach into it. Region visuals and
collision are clipped to the frame (local +-1536), so these bodies end in a straight cut. From
places the player can reach inside the frame, for example the St. Delyn walkway at local
-1211 -962 87, the cut at x -1536 is 325 units away, inside the 540-unit fog distance. Beyond it
there is only sea and sky. In dev1 the bodies were missing altogether.

## Where

`config/vivec_arena.json` (bounds +-1536, draw distance 540) and the region clipping in
`tools/import_town.py` / `tools/bound_balmora_visuals.py`.

## How it happened

The frame was sized so that its edge stays beyond fog range from every point of the Arena canton.
The bridges and the parts of neighbouring cantons inside the frame are reachable too, and from
them the edge is in view.

## Why it was not caught

The first Arena checks looked from the Arena canton only.

## Reproduction

Converted Arena, local -1211 -962 87, heading west: the canton slab ends at x -1536 (offline
render of the fixed `va000`).

## Repair

Not yet; owner decision. Measured options:

- Whole cantons in the Arena frame: their footprints need bounds of about +-3072, which is 64
  regions (the region cap) and takes in the Temple and Ministry regions. The canton frames of the
  same area already exceed the loader heap with today's regions (St. Delyn 5 of 25 regions, St.
  Olms 6 of 25, Temple 8 of 36; [VIVEC-HEAP-31](VIVEC-HEAP-31.md)), so this does not fit.
- The planned per-canton towns (`config/vivec_*.json`) and the world streamer replace the cut with
  the neighbouring canton's own frame.
- A shorter fog distance near the frame edge (location fog) would hide the cut without new data.

## Verification

Pending.

## Prevention

A frame-edge view check from every reachable point (fog distance against the frame edge) in the
town import report.
