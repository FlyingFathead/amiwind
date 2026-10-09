# VIVEC-ARENA-FLOATING-NPC-32: A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Vivec Arena preview, Telvanni side, seen from LOCAL 1185 -59 117 |
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

Open; cause unknown. Owner decision: fix later; known in v0.0.32. Reported by the owner while playing
the v0.0.32-dev3 private test (8 October 2026): "that dude there is even floating in the air".

## Symptom

From LOCAL 1185 -59 117 (GLOBAL 41094 -87279 470), heading E 087, pitch -23, time 13:42, location
label "Vivec, Telvanni": a robed resident stands at the end of a stone walkway or arch next to the
Telvanni canton with nothing under him; sky is drawn below his feet. Same edge area as
[VIVEC-ARENA-WATER-FALL-32](VIVEC-ARENA-WATER-FALL-32.md).

## Where

The Vivec Arena frame (`config/vivec_arena.json`, bounds +-1536), the canton pieces kept by
`tools/import_town.py` and the actor placement bake. Resident placement is checked by
`tools/check_actor_ground.py`.

## How it happened

Unknown. Not yet measured: whether the resident's walkway is cut by the frame edge
([VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md)), whether he stands on collision without
drawn faces, or whether the walkway is complete and only the missing sea beyond the canton edge
(VIVEC-ARENA-WATER-FALL-32) makes him look unsupported. The resident's reference is not yet
identified.

## Why it was not caught

The actor ground check passed for every Arena resident in the dev3 build without the private-test
waiver ([VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md)). It tests standing contact against the
map's collision; it does not check that drawn faces lie under the actor, or what the player sees
around the support, so a resident supported by collision at a cut or open edge passes.

## Reproduction

v0.0.32 (or dev3): `dbg tp vivec_arena`, go to LOCAL 1185 -59 117, face E 087, pitch -23.

## Repair

Not yet (owner decision: later). First identify the resident and the piece he stands on, and render
the converted region offline at the pose (visual faces and collision separately).

## Verification

Pending.

## Prevention

Proposed: the actor ground check also reports actors whose support has no drawn face under them, and
actors within a step of a frame cut.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Vivec preview frame and its joins to the world (`vivec-frame-edge`). The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. See [families](README.md#families).

- [TOWN-EDGE-UNBUILT-32](TOWN-EDGE-UNBUILT-32.md): Leaving a town into an unbuilt neighbour drops the player into a bare world map
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-ARENA-HANDOFF-32](VIVEC-ARENA-HANDOFF-32.md): The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view
- [VIVEC-ARENA-WATER-FALL-32](VIVEC-ARENA-WATER-FALL-32.md): The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water
- [VIVEC-CANTON-SKY-HOLE-32](VIVEC-CANTON-SKY-HOLE-32.md): Sky shows through a Vivec canton wall seen from below
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

<!-- END GENERATED CATEGORY -->
