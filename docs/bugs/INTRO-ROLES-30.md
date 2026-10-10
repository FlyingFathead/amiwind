# INTRO-ROLES-30: crash after a region change while intro roles are held

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 October 2026, in v0.0.30-dev3 |
| Where | opening sequence roles on Seyda Neen region change (aw_intro.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.30-dev4 |
| Severity | critical: Engine stopped with NUM_FOR_EDICT bad pointer on a region change. |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | v0.0.30-dev3 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- TRANSITION-EQUIPMENT-29 (no report page): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- VIEW-AUTOCENTER-29 (no report page): Reported viewport/yaw resets while walking or crossing cells

<!-- END GENERATED CATEGORY -->
