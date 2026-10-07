# INTRO-ROLES-30: crash after a region change while intro roles are held

## Status: 7 October 2026

Cause identified and repaired in `engine/aga/src/aw_intro.c`. Present in
v0.0.29 and v0.0.30-dev3; first fixed build: v0.0.30-dev4 (development build,
not owner-accepted).

## Symptom

`NUM_FOR_EDICT: bad pointer` crash during a region change in Seyda Neen, for
example on the first sub-cell load after reaching the town. The crash text is
shown in the AmigaDOS window and written to `ERROR.TXT`.

## Cause

The opening sequence keeps direct pointers to its role actors (the guards,
Jiub and others) in a fixed `roles[]` table. A region change is a full map
load: the entity list is rebuilt and may hold fewer entries. A pointer kept
from the previous map can then point past the last live entity (one recorded
case: entity 203 of 202). Reading it through `NUM_FOR_EDICT` triggers the
engine's bounds check, which stops the game.

## Repair

`validate_roles()` checks every stored role pointer against the current entity
list (inside the list, index in range, entity not freed) and clears stale
entries. It runs before a role is used by dialogue (`say`), by `AW_IntroRole`
and on each `AW_IntroTick`. A cleared role behaves as an absent actor.

## Verification

Same scripted Seyda Neen route in headless FS-UAE (A1200/AGA, 68040, fresh
disk copy each run), console `+forward` walking through six planned sub-cell
crossings:

| Build | Runs | Result |
| --- | --- | --- |
| v0.0.30-dev3 | 2 | Crash on the first sub-cell load, both runs |
| Repaired engine | 3 | No crash; all six planned crossings plus four open-world region loads |

Not yet covered: the full opening sequence played through to the town with a
region change at every stage, and owner playtest.
