# DBG-ENTITY-INSPECT-39: Requested click-to-pin raw entity and reference inspection

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): First target compile rejects missing AW_CharacterActive declaration. Candidate includes aw_character.h; fresh exact-source compile retry pending. Existing17 focused checks are not target acceptance.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Corrected target compile passes; native HUD pins background Ord201385 through the foreground actor because whole-model bounds include other poses. Visible identity selection remains open.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Current rendered frame-bounds source candidate passes one real C UBSan regression incl. death-envelope false pick, stale client/cache controls. Corrected target/native/package acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Latest source explicitly labels server runtime/position separate from rendered client selection. One actual C UBSan check passes differing-frame assertion; corrected target/native acceptance pending.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Debug HUD and actor/scenery target identification |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | medium: Maintainer-visible mechanics or diagnostic requirement; original parity and candidate native verification remain pending. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer named RC1; the exact running binary was not independently read back for this report. The mutable RC2 source candidate has not been compiled or packaged. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-13: reported in v0.0.39-rc1
- 2026-10-13: seen again in v0.0.39-rc2: First target compile rejects missing AW_CharacterActive declaration.
- 2026-10-13: seen again in v0.0.39-rc2: Corrected target compile passes; native HUD pins background Ord201385 through the foreground actor because whole-model bounds include other poses.
- 2026-10-13: seen again in v0.0.39-rc2: Current rendered frame-bounds source candidate passes one real C UBSan regression incl.
- 2026-10-13: seen again in v0.0.39-rc2: Latest source explicitly labels server runtime/position separate from rendered client selection.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev2 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Timeline](#timeline)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Target compiler finding, 13 October 2026](#target-compiler-finding-13-october-2026)
- [Corrected compile and native selection limit, 13 October 2026](#corrected-compile-and-native-selection-limit-13-october-2026)
- [Current rendered frame-bounds source correction, 13 October 2026](#current-rendered-frame-bounds-source-correction-13-october-2026)
- [Explicit server metadata labels, 13 October 2026](#explicit-server-metadata-labels-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Requested during RC1 appearance investigation. Source candidate adds explicit dbg hud on/off click-to-pin entity/reference/model/position inspection; target compilation, candidate native checks and delivery remain pending. Ordinary overlay controls retain their previous combat behavior.

## Where

Debug HUD and actor/scenery target identification. Reported on 13 October 2026 during the RC1 inspection.

## How it happened

The normal target name alone cannot bind a visible foreground mesh to its original reference. The candidate reuses Quake traces, model/edict identity and existing HUD drawing. Bounds-selected objects must be labelled as bounds; world collision occludes selection. CHIM merged static geometry may have no individual source reference, which must be reported as unavailable.

## Why it was not caught

Earlier file, model-budget and scoped native checks did not exercise this exact
requirement. Source implementation and package/native acceptance are separate.

## Reproduction

Enable dbg hud on, click a target, and read the pinned raw entity ID, source NPC/object ID, reference, model and position. Turn it off and confirm attack works normally. Compare a foreground actor and an occluded background actor; test missing source IDs, merged static geometry, reloads and both camera views.

## Repair

Candidate inspection mode defaults off and is not saved. Only explicit dbg hud on enables click interception; clicks are consumed until it is disabled. Ctrl+H and dbg overlay remain overlay-only so ordinary coordinate display does not disable attacks. The ent one-shot command prints the current raw target. Pin copies identity strings and position rather than retaining live actor pointers; reset on every scene spawn, including the same map.

## Verification

Seventeen focused automated checks pass against an exact source snapshot, including an actual inspector C integration fixture for nearest actor identity, brush/world occlusion, client static selection and unavailable source fields, held-click consumption, off/release restoration, camera displacement, same-map reset, dead/menu/character gating and narrow-viewport bounds. General HUD, console and command-registry checks also pass. Target compilation, actual native inspection, package readback/delivery and maintainer acceptance remain pending. It supplies evidence for the Ordinator investigation; it does not itself repair actor appearance.

## Prevention

Exercise selection and attack interception independently of ordinary overlay toggles. Test on/off defaults, stable snapshots after actor removal, same-map reload clearing, world occlusion and honest unavailable reference fields.

## Target compiler finding, 13 October 2026

The first RC2 target compile at source858ad94 reports an implicit declaration of
AW_CharacterActive in aw_inspect.c. The focused host fixture did not make the
missing production header fail. The compiler-warning gate correctly refuses this
candidate; its earlier17 automated checks are not an Amiga compile pass.

The source correction includes the existing aw_character.h declaration header.
It changes no intended inspection or attack behavior. A fresh exact-source target
compile is required; no successful retry, native or packaged acceptance is claimed.
Keep the production compile warning gate strict and retain the failed receipt.

## Corrected compile and native selection limit, 13 October 2026

Corrected source4b968c2 passes the target compile gate. The separate native diagnostic uses the exact compiled engine, matching bootcheck and candidate debug catalogue in a fresh copy of RC1 assets. Standard dbg hud on and clicks print/pin raw identity; dbg hud off restores the ordinary mode. Both runs return to an observed AmigaDOS prompt, and post-exit engine, bootcheck and catalogue hashes match their staged inputs. This is a scoped hybrid diagnostic, not a complete RC2 package.

At the Hlaalu pose, the visible foreground unhelmeted elf is under the crosshair, but the bounds pick selects background Ordinator entity217, reference201385, model progs/a_305e68b87f69.mdl. This does not bind the foreground face to the selected actor. Source inspection and read-only payload measurements identify a concrete coarse-selection limit: model.c retains the quantization domain across every alias frame, and the inspector ray uses that domain. The Ordinator domain extends to localY-37.31 while its standing frame0 extends only to-2.44. With the recorded approximate camera ray and authored rotations, the broad domain is hit at8.18 units while all eight standing-frame boxes miss; Eloroth standing boxes are hit at14.47 units. Live Eloroth frame/yaw was not dumped, so those authored/facing rotation trials are diagnostics, not exact live-pose reconstruction. Current-frame bounds or finer geometry validation is needed before declaring visible target identification reliable.

The requested player pose115,97,-73 lies inside collision; disabling noclip was refused and movetype8 remained. The HUD reads heading32/pitch23 rather than the rounded requested31/24. This establishes neither ordinary collision nor exact original pose equivalence. The off-mode attack clip is retained; a post-release READY state alone does not prove a punch. Normal attack control and fully reliable selection remain separate acceptance gates.

## Current rendered frame-bounds source correction, 13 October 2026

The subsequent source candidate replaces the all-pose quantization-domain test
with the current rendered client-frame box, reusing R_AliasCheckBBox frame bounds
and R_AliasSetUpTransform pitch/scale conventions. Cache_Check permits resident
alias data only; absent cache entries are skipped without forced disk loading.
The client model and message time must match the current server actor before a
selection; its interpolated client origin/angles/frame drive the intersection.
Grouped MDL frames retain the renderer's group box, so selection remains bounds
based rather than exact triangle precision. Printed server runtime frame/position
can differ from the rendered pose during motion and must be read as runtime data.

One actual inspector C integration check passes with UBSAN against an immutable
source snapshot. It exercises the false death-envelope regression, actual client
frame/pose, stale-client refusal, resident-only cache access, alias pitch/scale,
and the earlier click/attack/scene-reset controls. This is source and focused
automated evidence. A fresh exact corrected-source target compile and native
Hlaalu foreground pick are pending; the earlier native false-pick receipt stays
historical and does not accept this correction. Noclip/pose, ordinary attack,
complete RC2 package and maintainer acceptance remain separate.

## Explicit server metadata labels, 13 October 2026

The latest source candidate labels server runtime frame and server local/global positions explicitly, while the intersection still uses the rendered client pose/frame. One actual C UBSan integration check passes a differing client-frame/server-frame assertion along with the prior selection/control cases, against an unchanged isolated source snapshot. This addresses metadata ambiguity in source only. Fresh corrected-selector target compilation, native foreground identification, complete RC2 package and maintainer acceptance remain pending; earlier source and native snapshots stay historical.

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
- [DBG-CAM-ORBIT-FAR-TARGET-68](DBG-CAM-ORBIT-FAR-TARGET-68.md): The debug orbit camera refuses a placed model farther than a few hundred units away although it fills the crosshair: it looks for its centre only in the collision near the player
- [DBG-COMBAT-CALM-LEAVES-HOSTILE-MARK-68](DBG-COMBAT-CALM-LEAVES-HOSTILE-MARK-68.md): `dbg combat calm` ends the fights but leaves the actors marked as hostile, so they still refuse to talk
- [DBG-CONTAINER-AIM-NO-SPOT-59](DBG-CONTAINER-AIM-NO-SPOT-59.md): aw_placed container aim finds no standing spot the room collision accepts in Arrille's Tradehouse
- [DBG-CONTAINER-AIM-OUT-OF-REACH-67](DBG-CONTAINER-AIM-OUT-OF-REACH-67.md): aw_placed container aim stands the player 40 units from the container, past the reach for a container on the floor, and aims above a small one
- [DBG-DBATTACK-ASLEEP-COUNT-67](DBG-DBATTACK-ASLEEP-COUNT-67.md): dbg dbattack reports no sleeping frame and a dead assassin when the attack wakes the player in the rest's first frame
- [DBG-DOOR-GO-AIM-CHIM-59](DBG-DOOR-GO-AIM-CHIM-59.md): aw_hinged_door go does not bring the door under the crosshair in a CHIM room
- [DBG-PLACED-LOOK-VIEW-NOT-TURNED-61](DBG-PLACED-LOOK-VIEW-NOT-TURNED-61.md): The test commands aw_placed look and aw_view set the view angles but the view does not turn
- [DBG-QUOTED-ID-REFUSED-62](DBG-QUOTED-ID-REFUSED-62.md): A debug command with a quoted record ID holding a space is refused as an unknown debug command (dbg npcs talk "agronian guy")
- [DBG-SPAWN-CELL-ZERO-67](DBG-SPAWN-CELL-ZERO-67.md): An actor placed by the debug spawn command is booked in cell 0,0 instead of the player's cell: the focus names it under the crosshair, but nothing is drawn there
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- [DBG-TP-BEINGS-66](DBG-TP-BEINGS-66.md): Requested: the dbg tp list chooses All, Exteriors, Interiors or Beings and reaches any person or creature by name
- [DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63](DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63.md): dbg tp into a room reached through a door list prints no arrival line
- [DBG-TP-DURING-LOAD-66](DBG-TP-DURING-LOAD-66.md): A dbg tp typed while a load is still running is lost: a town name does nothing, a place says no map holds the point, a room prints its name and stays
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
- [HORS-FROM-MENU-REGRESSED-68](HORS-FROM-MENU-REGRESSED-68.md): From the main menu, dbg aw hors 0 stops on a loading screen and returns to the main menu
- [HORS-IN-PLAY-NO-NEW-GAME-RESET-67](HORS-IN-PLAY-NO-NEW-GAME-RESET-67.md): dbg aw hors 0 started during play keeps the game before's script state: revealed map places, the explored map, the scripts' instances
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-ACTOR-HEALTH-ZERO-67](INSPECT-ACTOR-HEALTH-ZERO-67.md): The inspect line shows health 0.0 for every living actor: it printed the engine's own health field, which holds the player's health only
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- [INSPECT-PIN-LOAD-DOOR-51](INSPECT-PIN-LOAD-DOOR-51.md): The inspect pin at an exterior load door names the building shell around it, not the door: the drawn door looks absent
- [MAP-TELEPORT-28](MAP-TELEPORT-28.md): F10 map teleport intermittently fails
- [MENU-TITLE-AFTER-CONSOLE-START-68](MENU-TITLE-AFTER-CONSOLE-START-68.md): After a game is started from the main menu by a console command (dbg aw hors, a typed map), Escape in play opens the title main menu over the running game, and Escape does not close it
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

- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance

<!-- END GENERATED CATEGORY -->
