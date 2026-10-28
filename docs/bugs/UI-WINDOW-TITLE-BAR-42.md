# UI-WINDOW-TITLE-BAR-42: Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | Inventory and other titled windows (aw_worldui.c, aw_ui.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | low: Cosmetic: the window is usable; the original framing is missing. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.41 release image |
| From commit | source 5ce02c8, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

## Symptom

In the original game every menu window has a title bar: a strip of the
original tiled frame texture with the window's name centred on a small dark
plaque. AmiWind's inventory window shows only a boxed "Inventory" heading.

## Where

The inventory window (engine/aga/src/aw_worldui.c, `inventory_draw`) and the
other titled windows drawn with the shared UI box.

## How it happened

The windows were built with the shared thick-border box and a text heading;
the original title-bar art was never imported.

## Why it was not caught

Window checks covered layout and text overlap, not the original framing.

## Reproduction

Press I and compare the top of the window with the original inventory window.

## Repair

The title bar is composed from the original art, imported at build time with
the HUD art (tools/prepare_icons.py): the head block of
`textures/menu_head_block_*.dds` (the tiled middle inside its 2-pixel edges) on
each side and the title between them on the window's black, the gap being the
title's width plus 24, as the original window skin lays it out
(files/data/mygui/openmw_windows.skin.xml MW_Caption and HB_ALL,
components/widgets/windowcaption.cpp WindowCaption::align, read for reference).
AmiWind's title band is 12 pixels, so the pieces are scaled 12/20 (1-pixel
edges, a 154-pixel tile). The title is centred on the plate by its painted
pixels. The inventory's title is, as in the original, the equipped weapon's
name or the hand-to-hand skill's name (GMST sSkillHandtohand) when unarmed
(windowmanagerimp.cpp setSelectedWeapon, hud.cpp unsetSelectedWeapon).
`aw_hud_icons 0` keeps the plain title. Branch v0.0.42-hud-title.

## Verification

Synthetic-picture builder test of the piece sizes, a native fixture of the
composition (edges, tile, plate width and position, one load) and a centring
test by painted pixels; in-game stills unarmed and with the sword and an A/B
with the original window are recorded with the evidence.

## Prevention

A unit test of the title centring and an A/B against the original window.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- EXTRAS-MENU-54 (no report page): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
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
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
