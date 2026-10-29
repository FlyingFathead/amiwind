# HUD-FPS-NEEDS-DBG-HUD-56: dbg fps shows nothing unless dbg hud is on

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 October 2026, in v0.0.56-dev1 |
| Where | Every platform: the HUD drawing (engine/aga/src/aw_hud.c, Sbar_Draw) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.56 |
| Severity | low: a debug readout; the game is unaffected, but frame rates on new machines could not be read |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | 2026_10_29_v0.0.56-dev1_full-dev1-arenapit_5406920 |
| From commit | source 5406920, engine 5406920, CHIM world 5406920 |
| CHIM engine version | CHIM 0.2.2, engine 5406920, world format 0.11 |
| Platform or emulator | Amiberry 8.5.0, JIT, 68040+FPU, Raspberry Pi 4 at 2.0 GHz (the v0.0.56-dev1 image on the boot stick) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.56-dev1 (29 October 2026)._

## Status: 29 October 2026

Fixed in the source for the next build. Found by the maintainer on the Raspberry Pi 4 boot stick (Amiberry): "it's
only showing the `dbg fps on` whenever you have already `dbg hud on`", and where it belongs: "under the fucking
viewport or at least on the bottom left corner of it" / "or top left corner, as long as it's not like that in the
middle of the screen".

## Symptom

`dbg fps on` draws nothing. With `dbg hud on` as well, the FPS box appears near the top left of the screen, over
the view, as part of the debug HUD.

## Where

Every platform and build since the FPS readout came in: the HUD drawing (`engine/aga/src/aw_hud.c`, `Sbar_Draw`).

## How it happened

The FPS box was drawn after the early return that skips the whole debug HUD when the debug overlays are off, so
its own switch only worked together with `dbg hud`. The page [DEBUG_OVERLAYS.md](../DEBUG_OVERLAYS.md) also named
a different place for it (the second top-right line).

## Why it was not caught

The HUD unit test turned the FPS on while the debug HUD was on, and checked only that it was not drawn with
both off.

## Reproduction

Always: `dbg hud off`, then `dbg fps on`.

## Repair

The maintainer, on where and when: "also be on during the vanity camera shoots" / "only appear on the top left or
bottom left corner of the entire available screen". The FPS counter is its own switch, drawn by the screen code
after everything else but the console (`AW_FpsDraw` in `aw_hud.c`, called from `screen.c`), so it shows without
`dbg hud` and in the vanity orbit, which skips the HUD; small, in the bottom-left corner of the whole screen, on
the HUD's black. Photo mode hides it unless Ctrl+H brings the HUD back. The Halloween benchmark draws the same
counter (`AW_FpsCorner`): its own copy filled its box with palette entry 0, which the maintainer saw as a white
box with no readable number on Amiberry. DEBUG_OVERLAYS.md says so.

## Verification

`tests/aga_hud_test.c` (run by `tests/test_aga_native_source.py`): the FPS draws from the screen code, not the
HUD, with the debug HUD off, in the screen's bottom-left corner on black, not over the console, not in photo mode
(unless Ctrl+H), and not when switched off; `tests/test_halloween.py`: the bench uses the same counter. In game:
the next build.

## Prevention

The test now checks the FPS switch alone, without the debug HUD.

## Related

[BENCH-NO-STANDARD-DEMO-48](BENCH-NO-STANDARD-DEMO-48.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- DBG-MWSCRIPT-SILENT-56 (no report page): dbg mwscript on prints nothing: the switch gives no answer, so it looks as if it did nothing
- EXTRAS-MENU-54 (no report page): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- HUD-INTERIOR-CLOCK-CUT-54 (no report page): The dbg hud line GLOBAL XYZ: unavailable (interior) is so long that the clock is cut off
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- PHOTO-CROSSHAIR-51 (no report page): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- RAM-WARNING-BOX-52 (no report page): Requested: under 32 MB of Fast RAM a WARNING message box for a few seconds before the AmiWind logo
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-ICONS-INVENTORY-42](UI-ICONS-INVENTORY-42.md): Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops
- [UI-INVENTORY-FONT-TABS-42](UI-INVENTORY-FONT-TABS-42.md): Inventory categories use the console font as plain text instead of the original Morrowind font on button tabs
- [UI-INVENTORY-HEADING-CENTRE-42](UI-INVENTORY-HEADING-CENTRE-42.md): The Inventory heading text is not vertically centred in its bar
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid
- [UI-INVENTORY-PREVIEW-GAP-41](UI-INVENTORY-PREVIEW-GAP-41.md): Inventory shows 'Character preview unavailable': a fixed 2 MiB memory guard refuses the 128 KB pose model in Seyda Neen
- [UI-INVENTORY-PREVIEW-STILL-42](UI-INVENTORY-PREVIEW-STILL-42.md): The inventory character is drawn live and turns instead of being a still picture
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- UI-MAP-PLAYER-ARROW-51 (no report page): Requested: the map shows the player as the original s arrow that turns with the player, not a crosshair
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- UI-PALETTE-NO-WHITE-48 (no report page): The game palette has no white: a White crosshair draws as the console ink cream (238,221,170)
- [UI-STATS-WINDOW-48](UI-STATS-WINDOW-48.md): No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
