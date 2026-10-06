# CENSUS-DOOR-STUCK-29: opening the hall door can trap the player

## 6 October 2026 activation guard candidate

The proposed overlap guard is now implemented in the next source candidate.
Actual RC1 map hulls plus actual `AW_OpeningUse` verify refusal for the player
and a solid NPC, unchanged actor pose/closed yaw/story flag, no false sound or
relink, and successful opening once both bodies are clear. Five focused existing
checks pass in Linux Docker. The open door remains SOLID_BSP.

This checks the final pose of the existing instant rotation. Saved-open restore,
already-trapped saves, native passage acceptance and packaged integration remain
pending. First shipped fixed version remains **none**.

Updated 2026-10-06T13:34:07+00:00. Status: **cause reproduced in actual collision code; repair
in progress; no shipped fix yet**.

| Field | Recorded value |
| --- | --- |
| Reported version | v0.0.29-rc1 private playtest, WinUAE |
| Reported date / game clock | 6 October 2026 / 10:16 |
| Area | Census and Excise Office interior, hall door |
| Displayed local XYZ | 65, 52, 65; interior global coordinate unavailable |
| Displayed direction / pitch | N 008 / 20; compass heading is not raw engine yaw |
| Fixed | N |
| First shipped fixed version | None |
| Intended fix checkpoint | Next candidate after published RC1; exact release designation pending |
| Owner | Collision/runtime maintenance |
| Release gate | Safe passage after opening, with original collision and save behavior preserved |

## Report and expected behavior

After opening the hall door, the playtester could no longer move normally at
the captured position. Opening a door must not place its solid hull inside the
player. Keep the closed/open door collision; do not hide this with noclip,
coordinate-specific teleportation, or removing architectural collision.

## Reproduction and cause

The read-only replay used the exact shipped census BSP, SHA-256
`2145d7a0abf0be4a49218d62b11a5ab8f114910f308c185184edb248eac71d7d`,
the RC1 model decoder and actual `SV_ClipMoveToEntity`/math routines compiled
inside Linux Docker. This was a geometry replay, not a new emulator run.

The HUD truncates position to integers. Replaying Z=65 literally also contacts
a floor brush, so it is not the complete standing pose. An actual downward
hull trace finds **(65,52,65.549949646)**, which displays the reported integers.
At that position the closed scene has no overlapping world/inline brush. The
existing open action changes door reference **172860**, inline model ***2**,
from yaw **-180** to **-90**, then relinks it without checking the player.
The open scene gains exactly one overlap: that hall door.

All 64 sampled positions within [65,66) x [52,53) x [65,66) are outside the
closed door hull and inside its open hull. This sampling tests the door-specific
result; floor validity is established separately by the standing-pose trace.
The direct replay therefore reproduces rotation of the door onto the player.

## Repair and acceptance

The repair in progress checks whether the proposed open pose overlaps the
player or a solid actor before committing it. If blocked, keep the existing
closed angle and story flag, avoid a false opening sound, and provide a brief
step-aside message. A clear approach must still open normally. The check must
not alter unrelated movement/collision code or change the original door mesh.

Saved-open restoration is a separate ordering case: the open door can be
restored before the saved player pose. An activation guard alone must not be
reported as repairing an already-trapped save. Test that case explicitly.

Required regression evidence:

- Actual shipped hull at the valid reported standing position: closed clear,
  proposed opening obstructed, rejected opening leaves pose/state unchanged.
- A clear player position opens once, emits its opening cue once, and permits
  travel through the doorway in both directions.
- Nearby solid actor and already-open cases retain correct behavior.
- Save/reload in valid closed/open states preserves geometry, actor position
  and story progression; document handling of existing trapped saves separately.
- Target playtest with ordinary controls confirms passage and no renewed trap.

When shipped and verified, update the fixed flag, exact first fixed version,
package identity and target evidence together. Source tests alone do not close it.

See [the issue index](../BUGS.md) and [RC1 issues](../BUGS-v0.0.29-RC1.md).
