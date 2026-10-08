# VIVEC-ARENA-WATER-FALL-32: The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water

| | |
| --- | --- |
| Reported by | Harry (owner playtest) |
| First noticed | 8 October 2026, v0.0.32-dev3 |
| Where | Vivec Arena preview, east of the Arena canton: LOCAL 1374 165 -212 and LOCAL 1076 -150 65 |
| Reproduction | always at those poses (steps on the page) |
| Duplicate of | none (related: VIVEC-ARENA-FRAME-EDGE-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | medium (the player can fall out of the area) |

## Status: 8 October 2026

Open; cause unknown. Owner decision: fix later, not a v0.0.32 blocker; known in v0.0.32. Reported by
the owner while playing the v0.0.32-dev3 private test (8 October 2026). Present in every build with the
Vivec Arena preview (v0.0.32-dev1 to dev3, v0.0.32).

## Symptom

Two owner reports from the same area, east of the Arena canton towards the Telvanni canton:

1. Going into the water near the Telvanni canton: "the water connects nowhere and you fall off the
   area". Underwater blue tint; HUD GLOBAL 41849 -86377 -848, LOCAL 1374 165 -212 (inside the
   +-1536 frame), heading E 093, pitch -24, time 13:09; location label "Vivec, Telvanni".
2. Standing under an arch at the canton edge: LOCAL 1076 -150 65 (GLOBAL 40658 -87640 260),
   heading NE 044, pitch -14, time 13:31, label "Vivec, Arena". The water surface stops a short
   way out; sky and cloud texture are drawn below the horizon where open sea should be, with the
   underside of the canton structure overhead.

Both are one defect: past the canton edge there is no sea surface drawn and nothing to stand on or
swim in, so the view shows sky below the horizon and the player falls out of the area.

## Where

The Vivec Arena frame (`config/vivec_arena.json`, bounds +-1536 local units, draw distance 540), its
region maps `va*.bsp` written by `tools/import_town.py`, and the water and terrain the frame is
given. Seyda Neen, Balmora and the open world are not known to be affected.

## How it happened

Unknown. Candidates to measure: the frame has no sea bed or water volume (or no terrain under the
water) in part of the frame; the water surface is clipped to the converted canton pieces instead of
covering the frame; the bottom of the frame is open, so a swimming player sinks out of the map.

## Why it was not caught

The Arena checks covered the canton top, the stairs, the residents and the arrival point. Nothing
checks that the water surface and a sea bed cover the whole frame, and no test swims or looks out
from the canton edges.

## Reproduction

v0.0.32 (or dev3): `dbg tp vivec_arena`, walk east to the Telvanni side of the Arena canton.

- Pose 1: LOCAL 1374 165 -212, heading E 093, pitch -24: enter the water and keep swimming down
  or east.
- Pose 2: LOCAL 1076 -150 65, heading NE 044, pitch -14: look out under the arch.

## Repair

Not yet (owner decision: later). First measure what the frame map holds at both poses (water
brushes, terrain, sea bed, map bounds). Related:
[VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md) (the visual cut where neighbouring canton
bodies end at the frame edge), [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md) (the
earlier arrival under the water) and [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md)
(a resident at a walkway end with sky below him, same area).

## Verification

Pending.

## Prevention

Proposed: a frame check in the town import report that the water surface and a floor under it cover
every point of the frame below the water line, plus a swim and a look-out pose at each canton edge in
the Arena smoke test.
