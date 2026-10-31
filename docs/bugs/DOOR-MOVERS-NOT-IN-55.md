# DOOR-MOVERS-NOT-IN-55: gates, trapdoors and bar counter flaps do not move: only doors that turn on a vertical hinge open

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.55 |
| Where | Gates, trapdoors, hatches and tavern, inn and club counter flaps, island-wide |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.55 (last seen) |
| Severity | medium: a lot of the game's moving parts stand still; a gameplay and look loss, with a way round for most |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | 2026_10_29_v0.0.55_full-final_9a672fd |
| From commit | source 9a672fd, engine 9a672fd, CHIM world 9a672fd |
| CHIM engine version | CHIM 0.2.2, engine 9a672fd, world format 0.11 |
| Platform or emulator | unknown (the maintainer's report from playing in general, no session named) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56 (30 October 2026)._

## Status: 29 October 2026

Open. Cause not pinned. Registered from the maintainer's report: the game has many different gates and trapdoors, and
also the opening hinges of tavern, inn and club bar counters, that are still not in. On the counters: the bar
counters with a hinge at the side so that the way through is for staff only, a lid-kind of hinge, the kind German
beer halls have, and many bars besides. He added that he saw the counter flaps in someone's playthrough and is not
sure of them: such a playthrough may run mods, so whether the base game (Morrowind.esm, Tribunal, Bloodmoon) has
counter flaps at all is for the census to show. Gates and trapdoors are in the base game, and so are some lids (the
maintainer, same day; one is the swinging lid of the prison ship's hatch, `docs/DOOR_MAPPING.md`). His caution for
the census, on how uniformly the data does these: the original's data may not be consistent about it, so each kind
is read from the records, never assumed from the model's look. Traps on doors are their own bug,
[DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md).

## Census: 29 October 2026

From the three masters (Morrowind.esm, Tribunal.esm, Bloodmoon.esm), read in a container with the builder's own
record reader (`src/mwad/esm.py`); the DOOR and ACTI records whose id or model reads as a gate, trapdoor, hatch,
lid, counter flap, portcullis, grate, lever or cage: 75 records, 338 placed references.

| Kind | Records | Placed | Examples | What it needs |
| --- | --- | --- | --- | --- |
| DOOR, no script | 24 | 285 | `ex_h_trapdoor_01`, `Ex_De_SN_Gate`, `CharGen_ship_trapdoor` | nothing new: a load door, or a hinged door that already turns about its vertical axis as every door does in the original and OpenMW |
| DOOR with a script that moves nothing | 9 | 9 | `BM_mazegate_01..03`, `ex_co_ship_trapdoor` | the script's other work (MWScript) |
| ACTI moved by its script (Move, MoveWorld, PlayGroup) | 30 | 32 | 26 Dwemer levers `act_dwe_lever_*`, the Ghostgate switches `ex_gg_gateswitch_01/02`, `Act_Rockslide01` | the MWScript work: the script moves the part |
| ACTI with a script that moves nothing | 6 | 8 | the Ghostgate portcullises `ex_gg_portcullis_01/02` (moved by the switches' scripts) | the same |
| ACTI, no script | 6 | 4 | signs and colliders | nothing |

No record of the three masters has "counter" or "flap" in its id or model: the hinged bar counters are most likely
from a mod, as the maintainer guessed. So the gap is not a hinge mode: the parts that move in the original move by
their scripts (levers, the Ghostgate), and come with the MWScript work.

## Symptom

Moving parts of the world that are not ordinary doors stand still: gates, trapdoors and hatches, and the hinged
flap in a tavern, inn or club bar counter that lifts like a lid to let the staff through.

## Where

Island-wide: the taverns, inns and clubs with a counter flap, the gates of strongholds and towns, the trapdoors and
hatches of houses, towers and ships. No cell or reference is pinned yet.

## How it happened

Since v0.0.48-dev2 the engine opens ordinary hinged doors (`docs/DOOR_MAPPING.md`, `aw_hinged_door.c`): every
placed DOOR without a destination, 1,026 in Morrowind.esm, turns 90 degrees about its vertical hinge. Anything that
moves another way has no code: a flap or hatch turns about a horizontal axis, a portcullis slides. In the original
many of these are probably moved by their own scripts, which AmiWind does not run yet; that is a guess until the
census below.

## Why it was not caught

The door work covered load doors and doors turning on a vertical hinge; nothing listed the other moving parts.

## Reproduction

Always, for every such part: walk up to a bar counter flap, a gate or a hatch and use it.

## Repair

None yet. First a census from the game's own records, in a container: every DOOR and activator whose model or name
reads as a gate, trapdoor, hatch, counter flap or portcullis; for each, how it moves in the original (vertical
hinge, horizontal hinge, slide, scripted), whether a script moves it, and where it is placed. Then per kind: a
horizontal-hinge mode for the hinged door code (flaps and hatches), a slide mode (portcullises), and the scripted
ones with the MWScript work.

## Verification

None yet. In game at 32 MB Fast: a counter flap in a tavern, a hatch and a gate each move by the original's rule,
with their sounds, and never close on the player.

## Prevention

The census becomes a builder check: every moving part of the game data has a kind the engine handles, or is listed
as not handled yet.

## Related

[AW-20260928-12](AW-20260928-12.md), DOOR-HALL-SWING-DIRECTION-48,
[DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md), CHIM-COLLISION-ROOM-FILLED-54.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ACTOR-FRAME-FIT-MARGINAL-53 (no report page): The v0.0.53-dev3 image stopped in the actor placement gate: Mivul Urvon (Vivec frame, reference 135239) no longer fits, after the shared table grew by the dancers groups
- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CHIM-32MB-SAVE-ENTRY-48](CHIM-32MB-SAVE-ENTRY-48.md): A save, a start or a console jump into a place marked for 32 MB of Fast RAM was not refused on 16 MB
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- [DOOR-BANK-STREAMED-FRAME-51](DOOR-BANK-STREAMED-FRAME-51.md): After a streamed crossing into another region frame, that frame s doors cannot be used: the engine reads only the start frame s door bank (830 of 1,102 entrances)
- DOOR-HALL-SWING-DIRECTION-48 (no report page): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
- DOOR-USE-BLOCKED-53 (no report page): 50 region-frame entrances cannot be used from where a player can stand: the use ray meets the entrance structure or the ground before the door, or there is no standing spot at it
- [DOOR-USE-COLLISION-FILLED-53](DOOR-USE-COLLISION-FILLED-53.md): 35 region-frame entrances cannot be reached through their converted collision: 24 Daedric shrine steps the player slides off, raised trapdoors under their tower hulls, Dwemer doors inside the terrain chunk
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTERIOR-SPAWN-UNDERWATER-41](INTERIOR-SPAWN-UNDERWATER-41.md): Vivec underworks rooms spawn under their water
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- TRANSITION-EQUIPMENT-29 (no report page): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- VIEW-AUTOCENTER-29 (no report page): Reported viewport/yaw resets while walking or crossing cells

Related bugs in other categories:

- CHIM-COLLISION-ROOM-FILLED-54 (no report page): One convex collision piece fills the room above a floor of the same mesh: seven trapdoors and a Redoran hut door cannot be used
- [DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md): Trapped doors and containers open without their trap

<!-- END GENERATED CATEGORY -->
