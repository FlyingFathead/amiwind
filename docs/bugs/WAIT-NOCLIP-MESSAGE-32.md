# WAIT-NOCLIP-MESSAGE-32: Wait refusal names registration, dry ground and speech together instead of the reason that applied

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Wait dialogue (T) with noclip on, anywhere |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | low: Message wording. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- HUD-STATS-29 (no report page): Health uses fixed 100; other bars hardcoded full
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar

<!-- END GENERATED CATEGORY -->
