# VIVEC-CANTON-SKY-HOLE-32: Sky shows through a Vivec canton wall seen from below

| | |
| --- | --- |
| Reported by | Harry (owner playtest), release screenshot |
| First noticed | 8 October 2026, v0.0.32-dev3 |
| Where | Vivec Arena preview, a canton wall seen from below; pose not recorded |
| Reproduction | unknown (pose not recorded) |
| Duplicate of | none known |
| Persists in | v0.0.32 (shipped as is) |
| Severity | low (visual, hard to see) |

## Status: 8 October 2026

Open; cause unknown. Owner decision: ship v0.0.32 as is. Found by the owner in v0.0.32-dev3 play
(8 October 2026) in a screenshot taken for the release gallery: "a graphics issue in it, not very
visible but still".

## Symptom

A Vivec canton seen from below in daylight (banners on the right-hand walls, a resident on the
upper walkway): the sky shows through the canton's upper left wall as a jagged, sky-coloured
opening inside the structure where wall should be, and pieces overlap or draw in the wrong order
where the right-hand walls meet. The coordinate overlay was off, so the pose was not recorded.

## Where

The Vivec Arena preview (`config/vivec_arena.json`); the canton pieces converted by
`tools/import_town.py` and the mesh converter. Not known elsewhere.

## How it happened

Unknown. Candidates: a face missing or culled where the frame cuts a neighbouring canton
([VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md)), a gap between converted pieces, or
faces dropped or misordered by the converter (compare
[CONVERT-DEGENERATE-FACES-32](CONVERT-DEGENERATE-FACES-32.md) and
[HORIZON-HOLES-31](HORIZON-HOLES-31.md) for distant buildings).

## Why it was not caught

No visual check of the Arena preview looks up at the canton walls from below; the face validator
reports face defects per map but not holes between pieces.

## Reproduction

Pose not recorded; needs the coordinate overlay next time. Look up at the canton walls from the
lower walkways in daylight. The owner's frame is kept with the private evidence.

## Repair

Not yet. First record the pose, then render the region offline at that pose and check which piece
the opening belongs to.

## Verification

Pending.

## Prevention

Proposed: a set of look-up poses along the Arena walkways in the Arena smoke test.
