# INSPECT-OVER-VIEWPORT-42: Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | dbg hud inspect: hint bar and 10-line pin panel at the top of the view |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | medium: Debug tool hides the very thing being inspected; maintainer-visible in play. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.42-dev1 |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer's play session) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-rc1 (17 October 2026)._

## Symptom

With `dbg hud on` (click-to-pin inspection) the line "INSPECT: click pins / attack disabled / dbg hud off" is
drawn on a black bar across the top of the 3D view, and after a click the pinned snapshot adds nine more lines on
a black box below it. The panel covers a third of the view, including what is being inspected. The maintainer, on
17 October 2026 in v0.0.42-dev1 at Vivec's entrance (cell 1,-10): the text should be under the viewport, it is
blocking visibility.

## Where

`engine/aga/src/aw_inspect.c`, `draw()`: `Draw_Fill` + `AW_SmallString` from y = 36 down over the view.

## How it happened

The first version of the inspection HUD (DBG-ENTITY-INSPECT-39) drew its rows where there was room on screen,
over the view, with a black backing so they stay readable. Every other debug readout (the GLOBAL/LOCAL XYZ rows)
sits in the strip under the view.

## Why it was not caught

The native test checked only that the rows fit the screen (`y+7 < vid.height-22`), not that they stay out of
the view.

## Reproduction

`dbg hud on`, aim at anything and click.

## Repair

First repair (17 October 2026, v0.0.42-dev2): nothing is drawn over the view any more. The hint was one more
coordinate row directly above GLOBAL/LOCAL XYZ, and the pinned snapshot was packed into up to three lines above
the stat bars, in a strip under the view of 72 lines instead of 48.

The maintainer then specified the place (17 October 2026, after the first repair): "underneath the player stats
HUD". Second repair, for v0.0.42-rc1:

- the hint "INSPECT: click pin / right exit" and up to three lines of the pinned snapshot (rows joined with
  " | "; the full rows still go to the console, without notify lines at the top of the view) are the bottom four
  lines of the screen, below the health, magic and fatigue bars, in the same console font;
- while inspect is on, the stat bars, the weapon and magic boxes, the enemy bar, the guard word, the compass and
  the coordinate rows move up by those four lines (36 pixels), and the strip under the view grows from 48 to 84
  lines (`AW_INSPECT_SB_LINES`, `screen.c`), so nothing is drawn over the view, the bars or the boxes; the title
  line and the object-name line keep their places above the bars;
- the coordinate row above GLOBAL/LOCAL XYZ is free again for the cell readout;
- photo mode keeps its full-screen view (no lift); a right click still leaves inspect mode.

`aw_inspect.c` gives `aw_hud.c` the hint and the packed lines through two hooks; `aw_hud.c` draws them and tells
`aw_ui.c` the lift (`AW_InspectHudLift`, `aw_ui_hud_lift`).

## Verification

Native tests: `tests/aga_inspect_test.c` (hint length, packing, no notify lines) and `tests/aga_hud_test.c`
(every string of the strip is drawn inside the strip, never above `vid.height - sb_lines`; with inspect on, the
hint and the pin lines are the only text in the bottom 36 pixels, the coordinate rows and the title sit 36 pixels
higher, no lift without the grown strip or in photo mode). In game: pending the v0.0.42-rc1 image (same place,
headlamp off), then the maintainer's look.

## Prevention

The HUD test asserts that no debug text is drawn inside the view while a strip exists.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- DEBUG-GOD-LOCKED-DOORS-51 (no report page): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- DEBUG-POSE-AFTER-RELOAD-52 (no report page): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
