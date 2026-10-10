# SERVER-FRAME-ARRIVAL-33: The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine Host_ServerFrame at Balmora camera 3 (legacy and CHIM alike) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: About 20 percent of the frame at the Balmora arrival point at 49.7 MHz (relative); 12 ms at camera 4. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open, cause unknown. Found while splitting the slow-CPU frame time (CHIM-SLOWCPU-FRAMETIME-33).

## Symptom

On the slow accelerator preset (FS-UAE cycle-exact 68040 at 49.7 MHz, relative numbers) the
engine's own walk profile (`server_us`, the time of `Host_ServerFrame`) reads 226 ms per frame at
Balmora camera 3 (`dbg tp -21800 -12300`, the arrival point) on CHIM and 228 ms on the legacy
region map, but 12 ms at camera 4. The player stands still.

## Where

`Host_ServerFrame` (physics, QuakeC, client messages). Not QuakeC instructions: the QuakeC
profiler counts about 750 instructions per frame there (`aw_npc_idle` most). `pause` did not
lower the host_speeds server share, so either `pause` does not stop the world there or the time
is outside `SV_Physics` (client messages, entity visibility).

## How it happened

Unknown.

## Why it was not caught

The JIT preset hides it (a few milliseconds a frame); the counters have no server timer.

## Reproduction

Slow preset, camera 3, read `server_us` in `walk-profile.csv` or `host_speeds 1`.

## Repair

Pending: time `SV_Physics`, `SV_SendClientMessages` and the collision traces separately.

## Verification

Pending.

## Prevention

A server timer in the renderer counters line.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

Related bugs in other categories:

- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)

<!-- END GENERATED CATEGORY -->
