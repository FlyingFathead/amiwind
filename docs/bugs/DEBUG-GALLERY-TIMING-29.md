# DEBUG-GALLERY-TIMING-29: hands unavailable in combat and torch test rooms

## Explicit test-room input restriction, 2026-10-06T18:59:52+03:00

Native follow-up identified a separate control failure: after appearance
selection returns to the pre-Census story stage, normal fighting restrictions
also mask combat-test attack and torch-test impulse202. The female capture
shows idle hands, not a successful punch. The default post-demo punch check
remains valid. This is unrelated to the torch-room gray lighting floor.

The narrow source repair grants input only during a captured, active explicit
combat/torch test session on its matching map. Character-modal blocking stays;
ordinary NPC gallery, raw test-map loads and normal story restrictions remain.
Permission ends immediately when return begins, without changing story state.
The actual gallery/story regression fails before repair; five focused Docker
checks pass after repair with no skips. Full combined gates and new native
pre-Census punch/torch/exit acceptance are pending. No shipped fixed version.

## Native follow-up: 2026-10-06T18:49:45+03:00

The combined repaired source passes 1,047 tests with zero failures/errors and
four documented skips, plus the Amiga build. A bounded FS-UAE session showed
valid combat hands, actual punching, and return to the ordinary town map.
The torch test room also displayed valid hands and returned successfully.
However, pressing V did not equip/light a torch in this run. This is an open
control failure requiring binding/state diagnosis, not successful torch
acceptance. The session returned to AmigaDOS and closed cleanly at
2026-10-06T18:47:31+03:00. First delivered fixed version remains none.

Updated 2026-10-06T15:03:42+00:00. **Open in the post-RC1 candidate; not part of delivered RC1.**

| Field | Evidence |
| --- | --- |
| First reproduced | 6 October 2026, FS-UAE in Docker, combined candidate after RC1 |
| Reproduction | Enter an ordinary playable map with valid current-character hands. Run `dbg torchtest`, press F to raise hands and V to equip torch. Also enter `dbg combattest` and try punching. |
| Coordinates | Procedural test scene entry; no world coordinates required. Preserve current scene/pose before entering for return checks. |
| Actual | Rooms load, but hands state/frame remain zero. Console reports invalid animation timings and asks to rebuild converted maps. Torch cannot equip; off/on world pixels do not change. |
| Expected | Current-character timing/hand metadata transfers before server activation; draw, punch and torch controls work. |
| Confirmed cause | `SV_SpawnServer` invokes `AW_GalleryEntities` before `sv.active=true`. The hook called `AW_GalleryActive`, which required `sv.active`; therefore timing transfer was skipped. Earlier isolated fixture incorrectly supplied an already active server. |
| Candidate repair | Use explicit captured session/map identity in the pre-activation entity hook. Preserve the active-server requirement on ordinary runtime APIs and server spawn order. |
| Regression | Exercise the real inactive callback lifecycle. Unfixed source fails the timing assertion. Six fixed-source checks pass with no skips, including the actual room compiler/hull test. |
| Fixed in source / delivered version | Narrow source repair passes focused validation; full build/native acceptance pending. First delivered fixed version **none**. |
| Closure requirement | Combined gates plus fresh native combat/torch draw, punch, equip/light and exit checks, preserving pose, equipment and fullbright state. |

## Separate issue: TORCHTEST-DARKNESS-29

The room has valid nonempty all-zero light samples, ambient zero and exemption
from building brightness. Nevertheless its actual-palette floor remains dim gray.
The palette generator uses `max(.15, 1-level/63)`, retaining a 15% minimum.
This is separate from the missing-hands lifecycle failure. Global darkening is
not an accepted fix: scope any change to the test room, check off/on world
pixels and an NPC, then verify normal interiors/exteriors remain unchanged.
Status open; no darkness repair or first fixed version yet.
