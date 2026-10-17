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

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

Related bugs in other categories:

- [NPC-ORDINATOR-APPEARANCE-39](NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance

<!-- END GENERATED CATEGORY -->
