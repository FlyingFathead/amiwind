# VIVEC-DISTANT-BRIDGES-32: Distant bridges between the Vivec cantons are not drawn

| | |
| --- | --- |
| Reported by | Harry (owner playtest), release screenshot |
| First noticed | 8 October 2026, v0.0.32-dev3 |
| Where | Vivec Arena preview, from a canton top; pose not recorded |
| Reproduction | unknown (pose not recorded) |
| Duplicate of | none known (related: VIVEC-ARENA-FRAME-EDGE-32, HORIZON-HOLES-31) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | low (visual) |

## Status: 8 October 2026

Open; cause unknown. Owner decision: ship v0.0.32 as is; known in v0.0.32. Found by the owner in
v0.0.32-dev3 play (8 October 2026) in a screenshot taken for the release gallery: "distant bridges
not rendering".

## Symptom

From a Vivec canton top in daytime (an armoured guard nearby, the Arena dome in the distance, low
sun), the bridges between the cantons in the distance are not drawn: the gaps between the canton
bodies are empty. The coordinate overlay was off, so the pose was not recorded.

## Where

The Vivec Arena preview (`config/vivec_arena.json`: bounds +-1536, draw distance 540) and the
region maps written by `tools/import_town.py`.

## How it happened

Unknown. Candidates: the bridges lie outside the frame and are cut by it
([VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md)); they are beyond the 540-unit draw
and fog distance while the larger canton bodies are kept, the same far culling that breaks up
distant buildings ([HORIZON-HOLES-31](HORIZON-HOLES-31.md)); or brush model distance culling drops
the thinner pieces first.

## Why it was not caught

No visual check of the Arena preview looks across to the other cantons from a canton top.

## Reproduction

Pose not recorded; needs the coordinate overlay next time. Stand on a canton top in the Arena
preview in daylight and look across towards the other cantons. The owner's frame is kept with the
private evidence.

## Repair

Not yet. First record the pose, then check whether the missing bridges are in the frame's maps at
all, and at what distance they are culled.

## Verification

Pending.

## Prevention

Proposed: a look-across pose from each reachable canton top in the Arena smoke test, compared with
the original game in OpenMW.
