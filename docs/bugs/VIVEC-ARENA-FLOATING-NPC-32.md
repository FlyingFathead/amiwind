# VIVEC-ARENA-FLOATING-NPC-32: A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet

| | |
| --- | --- |
| Reported by | Harry (owner playtest) |
| First noticed | 8 October 2026, v0.0.32-dev3 |
| Where | Vivec Arena preview, Telvanni side, seen from LOCAL 1185 -59 117 |
| Reproduction | unknown (seen once; pose on the page) |
| Duplicate of | none known (related: VIVEC-ARENA-WATER-FALL-32) |
| Persists in | v0.0.32 (shipped as is) |
| Severity | low (visual) |

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
