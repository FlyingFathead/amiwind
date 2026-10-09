# VIVEC-DISTANT-BRIDGES-32: Distant bridges between the Vivec cantons are not drawn

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Vivec Arena preview, from a canton top; pose not recorded |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | low: Visual. |
| Family | Vivec preview frame and its joins to the world (`vivec-frame-edge`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Vivec preview frame and its joins to the world (`vivec-frame-edge`). The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. See [families](README.md#families).

- [TOWN-EDGE-UNBUILT-32](TOWN-EDGE-UNBUILT-32.md): Leaving a town into an unbuilt neighbour drops the player into a bare world map
- [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md): A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-ARENA-HANDOFF-32](VIVEC-ARENA-HANDOFF-32.md): The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view
- [VIVEC-ARENA-WATER-FALL-32](VIVEC-ARENA-WATER-FALL-32.md): The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water
- [VIVEC-CANTON-SKY-HOLE-32](VIVEC-CANTON-SKY-HOLE-32.md): Sky shows through a Vivec canton wall seen from below

Related bugs in other categories:

- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky

<!-- END GENERATED CATEGORY -->
