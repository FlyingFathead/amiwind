# CHIM-REGION-DOORS-NO-PROMPT-42: Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | CHIM region frames: door entities and door links (Khuul, West Gash) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | medium: no way to see that a building has an entrance, even where its interior exists |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_17_v0.0.42-dev1_full-dev1-proof_5e043ad |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

## Symptom
Reported by the maintainer while playing v0.0.42-dev1: none of Khuul's doors show that there is an entrance, not
even "Interior unavailable"; the same in other CHIM region cells. Doors in Balmora, Seyda Neen and Vivec work.

## Where
The CHIM region frame maps (`tools/chim/frame_map.py` build_regions) and the engine's door tables
(`engine/aga/src/aw_scene.c` read_links_for: `doors-<map>.txt`, AWD3).

## How it happened
The engine shows a door's prompt only from a door table under the map's name. The town stages write one for
each town (`scene-doors-<town>.txt`, `tools/import_town.py` door_bank_text), and every converted room has its
own. A region frame map is made from the game data (worldspawn and player start only) and no step wrote a door
table for it: the door is drawn and solid, but the engine has no link for it.

## Why it was not caught
The CHIMport audit `door_links` counts the door models placed in the cell, not the door table the game reads; no
test or gate looked at a region frame's doors in the image.

## Reproduction
Any CHIM region cell with a load door, e.g. Khuul (-9,17), v0.0.42-dev1: aim at a shack door.

## Repair
- Every region frame map with load doors gets `doors-<map>.txt`: one AWD3 row per original load door (a DOOR
  record with a destination) placed in the frame's own cell, its box frame-local, its label the destination cell;
  the target is the converted room when there is one, else "-" (the engine shows "Interior unavailable").
- Measured on the v0.0.42-dev1 world: 167 of the 723 region frames hold 364 load doors (at most 19 in one frame;
  the engine keeps 256); Khuul has 10.

## Verification
Tests in `tests/test_chim_region_doors.py` (own cell only, ordinary doors left out, frame-local box, the 14 engine
fields, written only with doors, a frame without its scenery index refused). Pending: the prompt in game at
Khuul in the v0.0.42-dev2 build (clip).

## Prevention
A region frame map carries everything the game reads for its cell (statics, actors, doors, harvest); the door
table belongs to the same step as the frame map.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
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
- NPC-DREAMER-GREETING-DEFAULT-42 (no report page): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
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
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

Related bugs in other categories:

- [IMPORT-TOWN-NO-INTERIORS-32](IMPORT-TOWN-NO-INTERIORS-32.md): The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"

<!-- END GENERATED CATEGORY -->
