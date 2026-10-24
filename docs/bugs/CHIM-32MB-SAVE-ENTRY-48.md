# CHIM-32MB-SAVE-ENTRY-48: a save, a start or a console jump into a place marked for 32 MB of Fast RAM was not refused on 16 MB

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | aw_save.c AW_SaveRead, aw_scene.c load_scene / quick_go, host_cmd.c map / changelevel / load |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | high: loading a save made in a marked room or frame on a 16 MB start loads a place the zone does not fit |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 7f5d043, engine 7f5d043, CHIM world 7f5d043 |
| CHIM engine version | CHIM 0.2.1, engine 7f5d043, world format 0.12 |
| Platform or emulator | not in game (found by reading the engine's entry paths; engine tests only) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48 (23 October 2026)._

## Status: 23 October 2026

Fixed in v0.0.48 (branch v0.0.48-fix-32mb-saves, 23 October 2026). Engine tests pass; not yet seen in a build or in
the game.

## Symptom

The builder marks the CHIM rooms and region frames that need 32 MB of Fast RAM (`"_chim_room_fast_mb" "32"`,
`"_chim_frame_fast_mb" "32"` in the map's worldspawn; CHIM-ROOM-16MB-REFUSAL-48 and CHIM-FRAME-16MB-REFUSAL-48 in
the [register](../BUGS.md)). On 16 MB (or with Options > Video > Extra RAM off) the
engine refused only the two walking ways in: the door of a marked room and the crossing into a marked frame. Every
other way loaded the place anyway, with the zone the marked place does not fit:

- loading a save made inside a marked room or frame (the Load game menu, the quick load, "Load your last save" on
  the death screen);
- a start that lands in one (a quick start, a direct-start build's start line);
- the console: `dbg tp <name>`, `dbg tp X Y [Z]`, the camera marks, the silt strider, a door out of a room into a
  marked frame, and a raw `map`, `changelevel` or Quake `load`.

## Where

`engine/aga/src/aw_save.c` AW_SaveRead, `engine/aga/src/aw_scene.c` (load_scene, quick_go),
`engine/aga/src/host_cmd.c` (Host_Map_f, Host_Changelevel_f, Host_Loadgame_f). The builder marks are unchanged.

## How it happened

The room check (AW_SceneRoomRefuse) was placed at the door, and the frame check (AW_SceneFrameRefuse) at the
crossing in AW_SceneTick. The save load and the other scene changes issue their own `map` command and never asked
either check.

## Why it was not caught

The engine tests covered the door and the crossing only; the frame entry's status already named the gap ("a start
or a saved game inside a marked frame is not refused").

## Reproduction

On a 16 MB start (or Extra RAM off), save inside a marked room on a 32 MB machine, then load that save; or type
`dbg tp <marked room>`: the place loads.

## Repair

One check for every entry, AW_SceneEntryRefuse (aw_scene.c): the room mark or the frame mark of the target map,
and for a save also the frame that holds the saved position when it lies past the scene's own core (a save written
after a streamed crossing). On less Fast RAM nothing is left or loaded; the same screen as at a door says why
("Sorry, but this interior cannot be run with 16MB of Fast RAM." / "this area" for a frame, "Press ENTER to
return.") over the loading art. ENTER returns to:

- the main menu for a save load or a start (AW_SaveRead returns 2: refused and handled, so the Load game menu and
  the death screen close; there is no previous place to return to, or it is the death screen);
- the game where the player stood for a console jump during play (dbg tp, the strider, a door, a raw `map`); the
  main menu when no game runs.

Callers: AW_SaveRead through the hook `aw_save_entry_refuse` (bound in aw_debug.c), load_scene (every scene change
except a region crossing, which the tick checks), quick_go, and AW_SceneMapRefuse in Host_Map_f,
Host_Changelevel_f and Host_Loadgame_f before the running game is left (a scene change this file started itself
passes, as it was checked already).

## Verification

`tests/aga_scene_test.c` (a save in a marked room and in a marked frame, Extra RAM off, dbg tp to a marked room
during play, a raw map during play and from the main menu, a quick start refused and the same start going on with
32 MB, the pending start's own map command passing), `tests/aga_chim_save_test.c` (the load asks the check with
the saved scene and position before anything is queued; refused: 2, no map command, nothing pending), and
`tests/test_chim_room_fast_ram.py` (every entry asks the check before it leaves the game). In-game check on a
16 MB start pending.

## Prevention

The source test pins the check in each entry path; a new entry path that issues `map` itself still meets the check
in Host_Map_f.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- DOOR-HALL-SWING-DIRECTION-48 (no report page): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
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

- CHIM-FRAME-16MB-REFUSAL-48 (no report page): Five CHIM region frames are over or within 64 KiB of the 16 MB heap budget: on 16 MB of Fast RAM (or with Extra RAM off) their rings may not fit the zone
- CHIM-ROOM-16MB-REFUSAL-48 (no report page): On 16 MB of Fast RAM (or with Extra RAM off) a CHIM room larger than the zone ended the game with a host error at its door

<!-- END GENERATED CATEGORY -->
