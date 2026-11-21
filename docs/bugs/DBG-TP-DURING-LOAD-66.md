# DBG-TP-DURING-LOAD-66: A dbg tp typed while a load is still running is lost: a town name does nothing, a place says no map holds the point, a room prints its name and stays

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 November 2026, in v0.0.66-dev2 |
| Where | dbg tp (aw_teleport) and dbg scene (aw_scene) in engine/aga/src/aw_scene.c, typed while a map load is pending or the client is not yet in play |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.66-dev2 (last seen) |
| Severity | medium: debug teleports and scripted sessions only, but it made the release smoke hops wrong both ways: a lost Arena Pit hop passed on v0.0.66-dev1, three hops failed on v0.0.66-dev2 |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.66-dev2 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.66-dev3 (c139d3f8) | 2026-11-14 | gate 10818 passed on c0ab8f11, which holds it | a dbg tp or dbg scene typed during a load is held and runs once the load has arrived |
| shipped | a numbered build | v0.0.66-dev3 build 2026_11_15_v0.0.66-dev3_full-v0.0.66-dev3_c0ab8f1 | 2026-11-15 | the delivered build | the first build that holds c139d3f8 |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-14: fixed in source: a gated commit, v0.0.66-dev3 (c139d3f8); gate 10818 passed on c0ab8f11, which holds it: a dbg tp or dbg scene typed during a load is held and runs once the load has arrived
- 2026-11-15: reported in v0.0.66-dev2
- 2026-11-15: shipped: a numbered build, v0.0.66-dev3 build 2026_11_15_v0.0.66-dev3_full-v0.0.66-dev3_c0ab8f1; the delivered build: the first build that holds c139d3f8

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev2 (15 November 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 15 November 2026](#status-15-november-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 15 November 2026

Fixed in source on the v0.0.66-dev2 line (engine only). Pending the next v0.0.66-dev2 image's smoke hops in game.

## Symptom

The release smoke hops type one `dbg tp` after another with a fixed wait between them. On the v0.0.66-dev2 image
three of them were typed while the area before was still loading, and each was lost in its own way:

- `dbg tp balmora`, typed in the last frame of the Seyda Neen load: no load and no console line. The player stayed in
  Seyda Neen.
- `dbg tp arenapit`, typed during the Vivec load: the console printed "Vivec, Arena Pit" and nothing loaded.
- `dbg tp aldruhn`, typed during the same load: "Ald'ruhn: no map on this disk holds that point; player state
  unchanged." Ald'ruhn is on the disk: the same command loaded its map (vf0877) on the v0.0.66-dev1 image.

The Arena Pit hop was lost the same way on v0.0.66-dev1: typed during the Vivec load, it printed its name and the
player stayed at the Vivec arrival. The hop check passed it, because the reading before it had been taken in the
middle of that load.

## Where

The console commands `dbg tp` (aw_teleport) and `dbg scene` (aw_scene) in `engine/aga/src/aw_scene.c`.

## How it happened

A scene load sets a pending flag when it starts and clears it when the player arrives. `load_scene` returns at once
while the flag is set, and the coordinate route (`map_teleport`) refuses while a load is pending or the client is not
yet in play. None of the callers said why:

- a town name fell through to its town route, whose `load_scene` did nothing;
- a place of `teleport-names.txt` printed the message meant for a point outside every map;
- a room printed its name before its `load_scene`.

## Why it was not caught

A command typed by hand comes after the arrival. The smoke hops type theirs after a fixed wait, and loads on
v0.0.66-dev2 take longer than that wait (IMAGE-LOADS-SLOWER-66). The hop check counts a reading taken in the middle of
a load as a change of place.

## Repair

A `dbg tp` or `dbg scene` typed while a load runs (the load pending, or the client not yet in play) is held:

- One command is held. A newer one replaces it and the console says so. An argument with a quote, a semicolon or a
  line break is refused instead of held.
- The held command runs as soon as the load has arrived and the player is in play, from the scene tick, with a
  console line.
- A failed load and New Game drop it, with a console line.

The console lines:

- `dbg tp: a load is in progress (MAP); aw_teleport "balmora" runs when it has arrived.`
- `dbg tp: aw_teleport "vivec" replaces the held aw_teleport "balmora".`
- `dbg tp: the load has arrived; aw_teleport "vivec" runs now.`
- `dbg tp: the held aw_teleport "vivec" is dropped: the load failed.` (or `a new game starts`, `no game is running`)

## Verification

`tests/aga_scene_test.c` (run by `tests/test_aga_native_source.py`: the scene links test and the strider test) types
`dbg tp` during a pending load on the real scene code and checks:

- it is held and nothing loads;
- it does not run while the client is still signing on, and runs once after the arrival;
- a newer one replaces it, and `dbg scene` is held the same way;
- coordinates keep their words;
- New Game and a game that is gone drop it.

In game: pending the smoke hops of the next v0.0.66-dev2 image.

## Prevention

The hop check should take each hop's own arrival (its map loaded and the player in play), not only a reading that
differs from the one before.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- [AW-20260928-14](AW-20260928-14.md): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-CENSUS-MISSES-FUNCTIONS-68](CONSOLE-CENSUS-MISSES-FUNCTIONS-68.md): The table of the original game's console commands leaves out 110 functions of the script language, most of which already work when typed
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66](CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66.md): The original's console Equip on the player wears the item without its script's OnPCEquip: Wraithguard equipped with player->equip leaves wraithguardEquipped at 0
- [CONSOLE-GETPOS-SCRATCH-ORIGIN-66](CONSOLE-GETPOS-SCRATCH-ORIGIN-66.md): The console's GetPos on an actor answers a point near 0 instead of where the actor stands (dagoth_ur_2->getpos y read -0.43 while he stood at y 3700)
- [CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66](CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66.md): The console's ShowVars on a reference prints the console's own empty instance, not the reference's script (heart_akulakhan->sv: script 0, 0 locals)
- [CONSOLE-TP-ROOM-NAME-63](CONSOLE-TP-ROOM-NAME-63.md): The console teleport to a room map name stays in the current town instead of entering the room
- [DBG-CONTAINER-AIM-NO-SPOT-59](DBG-CONTAINER-AIM-NO-SPOT-59.md): aw_placed container aim finds no standing spot the room collision accepts in Arrille's Tradehouse
- [DBG-CONTAINER-AIM-OUT-OF-REACH-67](DBG-CONTAINER-AIM-OUT-OF-REACH-67.md): aw_placed container aim stands the player 40 units from the container, past the reach for a container on the floor, and aims above a small one
- [DBG-DBATTACK-ASLEEP-COUNT-67](DBG-DBATTACK-ASLEEP-COUNT-67.md): dbg dbattack reports no sleeping frame and a dead assassin when the attack wakes the player in the rest's first frame
- [DBG-DOOR-GO-AIM-CHIM-59](DBG-DOOR-GO-AIM-CHIM-59.md): aw_hinged_door go does not bring the door under the crosshair in a CHIM room
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- [DBG-PLACED-LOOK-VIEW-NOT-TURNED-61](DBG-PLACED-LOOK-VIEW-NOT-TURNED-61.md): The test commands aw_placed look and aw_view set the view angles but the view does not turn
- [DBG-QUOTED-ID-REFUSED-62](DBG-QUOTED-ID-REFUSED-62.md): A debug command with a quoted record ID holding a space is refused as an unknown debug command (dbg npcs talk "agronian guy")
- [DBG-SPAWN-CELL-ZERO-67](DBG-SPAWN-CELL-ZERO-67.md): An actor placed by the debug spawn command is booked in cell 0,0 instead of the player's cell: the focus names it under the crosshair, but nothing is drawn there
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- [DBG-TP-BEINGS-66](DBG-TP-BEINGS-66.md): Requested: the dbg tp list chooses All, Exteriors, Interiors or Beings and reaches any person or creature by name
- [DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63](DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63.md): dbg tp into a room reached through a door list prints no arrival line
- [DBG-TP-NO-FLOOR-FALLBACK-63](DBG-TP-NO-FLOOR-FALLBACK-63.md): dbg tp to a spot with no floor under it falls back to the frame centre
- [DBG-TP-ROOM-NAME-COMMA-67](DBG-TP-ROOM-NAME-COMMA-67.md): dbg tp with a room name as the place list shows it, a comma in it, is refused as an unknown debug command
- DBG-TP-SAME-MAP-54 (no report page): dbg tp X Y finds no map for a point on a MiniWind CHIM frame
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-GOD-LOCKED-DOORS-51](DEBUG-GOD-LOCKED-DOORS-51.md): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- [DEBUG-POSE-AFTER-RELOAD-52](DEBUG-POSE-AFTER-RELOAD-52.md): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [DEBUG-VIEW-PITCH-DRIFT-54](DEBUG-VIEW-PITCH-DRIFT-54.md): aw_view alone lets the pitch drift, and the greeting camera takes the view during scripted sessions
- DEV2-REGION-LOAD-CRASH-57 (no report page): v0.0.57-dev1 dev2 image crashes with NUM_FOR_EDICT: bad pointer when a teleport loads another region (dev1 did not)
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [GAME-RECORDER-FIGHT-SEED-61](GAME-RECORDER-FIGHT-SEED-61.md): A recording made while an NPC fights the player does not replay the same: the fight takes a seed of its own on the replay's load
- [GAME-RECORDER-HOTKEY-DIALOGUE-61](GAME-RECORDER-HOTKEY-DIALOGUE-61.md): While a recording runs, Ctrl+R does not stop it when the dialogue window is open: the key goes into the dialogue search field
- [GAME-RECORDER-MISSING-61](GAME-RECORDER-MISSING-61.md): Requested: a gameplay recorder that records a play session and plays it back in another game instance
- [GODMODE-LOST-ON-MAP-CHANGE-64](GODMODE-LOST-ON-MAP-CHANGE-64.md): God mode switched on before a teleport, a door or a load is off again after the map change
- HORS-FROM-MENU-58 (no report page): dbg aw hors cannot be started from the main menu
- [HORS-IN-PLAY-NO-NEW-GAME-RESET-67](HORS-IN-PLAY-NO-NEW-GAME-RESET-67.md): dbg aw hors 0 started during play keeps the game before's script state: revealed map places, the explored map, the scripts' instances
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-ACTOR-HEALTH-ZERO-67](INSPECT-ACTOR-HEALTH-ZERO-67.md): The inspect line shows health 0.0 for every living actor: it printed the engine's own health field, which holds the player's health only
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- [INSPECT-PIN-LOAD-DOOR-51](INSPECT-PIN-LOAD-DOOR-51.md): The inspect pin at an exterior load door names the building shell around it, not the door: the drawn door looks absent
- [MAP-TELEPORT-28](MAP-TELEPORT-28.md): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67](MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67.md): A script that moves the player to another place runs only after the console is closed
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- [SWEEP-GNISIS-LOAD-STALL-57](SWEEP-GNISIS-LOAD-STALL-57.md): Settlement sweep: the teleport to Gnisis shows no game-clock progress for 20 s (hang or a load over 20 s)
- [SWEEP-SLOW-ARRIVALS-57](SWEEP-SLOW-ARRIVALS-57.md): Settlement sweep: 13 of 82 places run above 50 ms a frame just after arrival at 32 MB Fast
- [TELEPORT-XY-006](TELEPORT-XY-006.md): No dbg tp X Y; map teleport could land underwater
- TP-ARRIVAL-ABOVE-DOOR-57 (no report page): Settlement sweep: Bal Isra lands about 250 units above its door arrival (on top of the ruin?)
- TP-ARRIVAL-BELOW-DOOR-57 (no report page): Settlement sweep: Vivec, Temple and Uvirith s Grave land 160 to 290 units below their door arrivals
- [TP-MENU-LABEL-CUT-63](TP-MENU-LABEL-CUT-63.md): The dbg tp list box is narrower than the longest room names, so their (interior) mark can be cut off
- TP-PICKER-OPEN-FRAME-COST-57 (no report page): The dbg tp list box redraws the whole paused world every frame: 100 ms a frame open against 16 ms closed
- TP-PLACES-NO-DOOR-SEA-57 (no report page): Settlement list: Fields of Kummu arrives in the water (a place without a door used its cell middle)
- [USE-KEY-DEAD-IN-NOCLIP-68](USE-KEY-DEAD-IN-NOCLIP-68.md): With collision off (noclip), the use key does nothing on scripted objects such as levers and cranks; the original lets the player use them

Related bugs in other categories:

- [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)
- [IMAGE-LOADS-SLOWER-66](IMAGE-LOADS-SLOWER-66.md): Area loads on the v0.0.66-dev2 image take 1.3 to 2.2 times as long as on v0.0.66-dev1 with the same file work (Vivec 13.6 s against 29.9 s)
- [LOAD-ERROR-NOT-NAMED-67](LOAD-ERROR-NOT-NAMED-67.md): A place that cannot be reached or loaded is not named on screen: a dbg tp refusal is a console line only, and the failed-load box says only to look at the console

<!-- END GENERATED CATEGORY -->
