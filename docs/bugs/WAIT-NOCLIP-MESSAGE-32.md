# WAIT-NOCLIP-MESSAGE-32: Wait refusal names registration, dry ground and speech together instead of the reason that applied

| | |
| --- | --- |
| Reported by | Harry (owner playtest) |
| First noticed | 8 October 2026, v0.0.32-dev3; seen in earlier development builds (first version unknown) |
| Where | Wait dialogue (T) with noclip on, anywhere |
| Reproduction | always |
| Duplicate of | none |
| Persists in | v0.0.32 (shipped as is) |
| Severity | low (message wording) |

## Status: 8 October 2026

Open, low priority (message wording); cause found in source. Owner decision: fix later, no code
change in v0.0.32. Reported by the owner in v0.0.32-dev3 play (8 October 2026); seen many times
before in earlier development builds (first version unknown).

## Symptom

With `noclip` on, pressing T (wait) shows "Wait after registration, on dry ground, when no one is
speaking." although registration is long done and nobody is speaking. The real reason is that the
player is not standing on the ground.

Refusing the wait itself follows the original game, which does not let the player wait or rest while
in the air (levitating, falling) or swimming. The defect is only the message: it lists every
condition at once instead of the one that applied. The original shows its own specific messages;
they are to be checked against OpenMW before any wording is copied.

## Where

`engine/aga/src/aw_wait.c`: `allowed()` and `wait_open()`.

## How it happened

`wait_open()` shows one combined message whenever `allowed()` returns 0. `allowed()` returns 0 when
the game is not a local single-player game, the story restricts waiting, character creation or a
book is open, or speech is playing, and also unless the player edict stands: health above 0,
movetype `MOVETYPE_WALK`, `FL_ONGROUND` set, waterlevel below 2, game not paused. Noclip changes the
movetype to `MOVETYPE_NOCLIP`, so that test fails and the combined registration, dry ground and
speech message is shown.

## Why it was not caught

No test covers the wait refusal reasons, and none covers waiting with noclip on; the message was
written for the opening, where registration is the usual reason.

## Reproduction

Any build with the wait dialogue: after release from the Census office, open the console, type
`noclip`, close the console, press T.

## Repair

Not yet. Let `allowed()` return the reason and show a message for that reason only (in the air or
flying, in water, during speech, before registration), with wording checked against the original
game in OpenMW. Waiting in noclip stays refused unless the owner decides otherwise.

## Verification

Pending.

## Prevention

Proposed: a native test of the wait refusal reasons (one state per reason, including noclip).
