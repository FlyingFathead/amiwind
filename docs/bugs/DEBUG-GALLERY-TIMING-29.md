# DEBUG-GALLERY-TIMING-29: hands unavailable in combat and torch test rooms

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 6 October 2026, in v0.0.29-dev |
| Where | combat and torch test rooms (dbg combattest, torchtest) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.29-rc2 |
| Severity | low: Debug test rooms only; hands were unavailable there. |
| Family | First-person hands and torch (`torch-hands`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-06: reported in v0.0.29-dev
- 2026-10-06: RC1 follow-up evidence: Combined repair candidate: 1,047 tests, zero failures/errors, four documented skips; Amiga build passed.
- 2026-10-06: Current RC1 regression checkpoint: Delivered playtest remains v0.0.29-rc1.
- 2026-10-06: Post-RC1 combined gate: The next candidate passes 1,046 Linux Docker checks, zero failures/errors, and four documented skips: three Windows-only checks and the JavaScript inspector check requiring Node.js.
- 2026-10-06: RC1 follow-up: building brightness and isolated inspection scenes: Recorded 2026-10-06T14:29:39+00:00; next candidate after v0.0.29-rc1, not in the published RC1.
- 2026-10-06: Follow-up validation checkpoint: The post-RC1 repair candidate passes the full 1,047-test suite with zero failures or errors and four documented skips, plus the Amiga build.
- 2026-10-06: Current RC1 regression checkpoint: Consolidated RC1 reports, coordinates and scoped positive observations: RC1 playtest ledger (docs/history/feedback/RC1_PLAYTEST_LEDGER.md).

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.39 (14 October 2026)._

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

**Update, 7 October 2026:** first delivered in v0.0.29-rc2; a later native run
showed punch, torch off/on/off after appearance choice and return to the
ordinary state ([RC2 checkpoint](../history/checkpoints/RC2_ISSUE_CHECKPOINT.md)). The darkness
issue below (TORCHTEST-DARKNESS-29) remains open.

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-TORCH-64](DEBUG-TORCH-64.md): The debug torch no longer lights with V: the console says no light is equipped
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- FIRST-PERSON-WEAPON-SETS-MISSING-54 (no report page): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- [FP-ARMS-CUT-62](FP-ARMS-CUT-62.md): In first person, looking down shows the forearms ending in mid-air, with no upper arms or shoulders behind them
- FP-FISTS-LUMP-67 (no report page): Drawing the fists in first person shows a lump in the top left corner of the view instead of the fists
- FP-FOREARMS-BELOW-VIEW-61 (no report page): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- [FP-WEAPON-SWAY-60](FP-WEAPON-SWAY-60.md): The weapon in first-person view moves more while walking than in the original
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- HELD-LIGHT-NOT-IN-HAND-65 (no report page): An equipped candlestick is not held in the hand; readying shows only the fists
- PLAYER-3P-HELD-ITEM-STALE-65 (no report page): After a new weapon is given and readied, the third-person body still holds the light that was equipped before
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- PLAYER-EQUIPMENT-NOT-WORN-54 (no report page): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- PLAYER-PARTS-BAKE-REFUSED-59 (no report page): Two body part meshes are refused by the assembled player body's parts library
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- [TORCH-ACTIVATE-CRASH-25](TORCH-ACTIVATE-CRASH-25.md): Raising the fists and pressing V crashed the game: a dynamic light was marked through a negative collision root
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- [TORCH-HAND-TO-HAND-64](TORCH-HAND-TO-HAND-64.md): With a torch equipped the fists cannot fight, raising them brings the torch back and V cannot put it away
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state
- [TORCH-INVENTORY-PICTURE-64](TORCH-INVENTORY-PICTURE-64.md): Unequipping the torch in the inventory still shows a torch in the hand

Related bugs in other categories:

- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
