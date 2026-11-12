# WORLDMAP-LAVA-MISMATCH-36: The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | Map screen (M): lava pools on the world map vs the world |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: The map misleads: it shows lava where the player stands on grass |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev5_full-coast-arena-seyda-dev5_6c29a23 (playtest v0.0.36-dev5) |
| Platform or emulator | FS-UAE (dev5 playtest build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 11 October 2026](#status-11-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 11 October 2026

Fixed in v0.0.36. Reported by the maintainer on 11 October 2026 from the v0.0.36-dev5 playtest build on FS-UAE; the cause was the map, not the world.

## Symptom

In Molag Amar the in-game map (M) shows the player standing inside a lava band. The game itself shows grass there, and no lava. The maintainer was at GLOBAL 87439 3671 349, LOCAL -156 405 -296, cell 10,0, at 09:16 game time.

## Where

The map screen's lava layer (AWM2 `LAVA` section, `tools/prepare_world_ui.py`) compared with what the player sees. The world is right; the map was wrong.

## How it happened

A Morrowind lava pool is a flat tile (`in_lava_1024`, 1,024 units square, surface at a fixed height) laid into the land. Where the land rises above the surface the lava is buried and the player sees ground. The map layer drew every pool's whole outline and never looked at the land. At the reported pose the land is about 270 units high and the pool surface is 256, so the pool is buried there and the maintainer stood on grass inside a mapped tile. The land falls below 256 about 30 units south of that pose, which is where the visible lava begins.

The same mistake was everywhere, not only at that pose. Measured on the Game of the Year masters (the land read from the master's own LAND records, bilinear between the 128-unit vertices), the 349 pools cover 257.9 million square units, and only 119.3 million of them (46 %) lie on land below the pool surface. 27 pools are buried entirely, and the old layer painted the other 138.6 million square units (54 % of the footprints) over ground. The census was right (a pool is placed there); the world was right (the lava surface is under the ground there). The two candidates named when the bug was filed, a map that is too coarse and a world that lacks lava, were both wrong: the conversion keeps the pools and the lava surface stays hidden where the land covers it.

## Why it was not caught

The build checked that every outline lay inside its pool's footprint, and that is the wrong test: inside the tile does not mean on lava. Nothing compared the layer with the land, and the earlier checks used census-only fixtures without land.

## Reproduction

Always, at the pose above, or at any pool tile that the land partly or wholly covers (cells 6,21, 6,-5, 9,2 and 3,-1 have the most buried tiles): open the map and compare it with the view.

## Repair

The layer is now the visible lava. `tools/lava_map.py` reads the land heights of the master and covers each pool with rectangles on a 64-unit grid (finer for small pools and for ovals; 128 or 256 only if the rows would not fit the engine's 2,048-row limit). A grid square is lava when at least half of its sample points lie on land below the pool surface and its corners lie in the pool's footprint; vertically equal runs merge. A pool the land buries completely gets no row. The engine is unchanged: it already fills any outline of up to 16 points by scanline, and a rectangle is four points. `--world-map v1` still writes the map without lava, and the earlier whole-outline layer is kept in `lava_layer(pools)` without land (DON'T DELETE ANY METHOD).

The result on all 349 pools in 27 cells: 1,713 rectangles, 27 buried pools not drawn. The LAVA section grows from 19,688 to about 95,900 bytes (read with the map when it opens, freed when it closes).

| Quantity | Square units | Share of footprint area |
| --- | --- | --- |
| Footprints of the 349 pools | 257,887,600 | 100 % |
| Visible lava (land below the surface, 16-unit sampling) | 119,312,128 | 46.3 % |
| Painted on buried land, old layer | 138,575,472 | 53.7 % |
| Painted on buried land, now | 2,174,208 | 0.8 % |
| Visible lava left unpainted, now | 1,677,312 | 0.7 % |
| TOTALS: pools / buried / rectangles / largest land height above the surface under a painted sample | 349 / 27 / 1,713 / 82.9 units | |

The error is a boundary effect of the grid: at most one grid square wide along a contour, and the land is at most 83 units above the surface under any painted sample. On the whole-island view one map pixel is about 600 units, so this is below a pixel. At the reported pose the layer no longer paints the tile to the north and east: the painted edge is 9 units from the pose and the true contour 30 units, so the player marker sits at the lava's northern edge, not in the middle of a band (a finer grid would cost more rows than the engine accepts).

## Verification

`python3 tools/lava_map.py --data-files <Data Files>` prints the audit per cell and the TOTALS row above. In the build the world-UI step runs the same audit and stops with the cell and pool named when a pool paints more than 12 % of its footprint on buried land, leaves more than 20 % of it visible and unpainted, or paints a point where the land is more than 96 units above the surface (`tools/lava_map.py` `audit`, called by `check_lava_layer`). Unit tests: `tests/test_world_ui_assets.py` (visible lava follows a rising land, buried pool has no row, the audit fails on the whole-footprint layer, land read from LAND records).

## Prevention

The audit is part of every v2 map build, so a layer that disagrees with the land can no longer ship. Platform of the report: FS-UAE (the dev5 playtest build). In-game confirmation on the map screen follows with the next playtest build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- ARRIVAL-LONG-FRAME-DEV6-59 (no report page): Arriving in Seyda Neen, the first frame of play lasts about 13 to 15 seconds; v0.0.59-dev6 test sessions stopped on it as a stall
- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- BLANK-PAPER-READ-60 (no report page): A blank sheet of paper offers Read although it has no text
- BOOK-TEXT-MACROS-58 (no report page): A book read where it lies shows the text defines as written (Name: %PCName Race: %PCRace Class: %PCClass)
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- [CLASS-LIST-LAYOUT-62](CLASS-LIST-LAYOUT-62.md): The class choice window runs its lists together without separating lines
- CONTAINER-STRIP-REDRAW-COST-59 (no report page): The container strip redraws the whole screen every frame: about 17 fps while it is open
- [CONTAINER-STRIP-TAKE-STALL-59](CONTAINER-STRIP-TAKE-STALL-59.md): A take or put in the container strip can hold the game for seconds
- CONTAINER-TAKE-NO-CONFIRM-62 (no report page): Taking an item from a container shows only its name; nothing says it was taken
- CRIME-RELEASE-LINE-CUT-62 (no report page): The release from jail shows only its first three lines: the skills that changed are cut off
- [DBG-MWSCRIPT-SILENT-56](DBG-MWSCRIPT-SILENT-56.md): dbg mwscript on prints nothing: the switch gives no answer, so it looks as if it did nothing
- [DIALOGUE-ARROWS-MOVE-POINTER-60](DIALOGUE-ARROWS-MOVE-POINTER-60.md): In the dialogue window the Up and Down keys move the mouse pointer instead of the topic selection
- DIALOGUE-BACKDROP-HUD-60 (no report page): The status bars stay visible behind the dialogue screen
- DIALOGUE-CHOICE-LINE-UNMARKED-60 (no report page): An answer picked from a dialogue choice is printed like the NPC's text, not as the player's line
- [DIALOGUE-CLOSE-FRAME-FREEZE-59](DIALOGUE-CLOSE-FRAME-FREEZE-59.md): The talk window takes seconds to open
- [DIALOGUE-ITEM-NOTICE-MISSING-61](DIALOGUE-ITEM-NOTICE-MISSING-61.md): An item a dialogue answer gives or takes shows no notice while talking
- DIALOGUE-LINK-MARK-AS-DEFINE-58 (no report page): Dialogue links lose their first two letters to a number, and the link itself, since the text defines table
- [DIALOGUE-LINKS-62](DIALOGUE-LINKS-62.md): The blue topic words in dialogue text cannot be clicked, a word is highlighted inside a longer word, and asking about a dead person gives "Who?"
- DIALOGUE-MSGBOX-BEHIND-60 (no report page): Message boxes raised during a conversation open behind the dialogue window
- DIALOGUE-OPEN-STALL-58 (no report page): Opening a conversation hangs the game for many seconds
- EXTRAS-MENU-54 (no report page): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- FOCUS-BOX-TWO-AT-ONCE-59 (no report page): Two item boxes at once: the box of the item aimed at before stays while the next item's box is drawn below the view
- FOCUS-BOX-UNDRAWN-ITEMS-58 (no report page): The focus box showed for room items that the room does not draw, and the activate key then took nothing
- FOCUS-NPC-OVERRIDES-ITEM-62 (no report page): Trying to take an item near a character talks to the character instead: the nearby character overrides the item under the crosshair
- FOCUS-REACH-ITEM-ORIGIN-58 (no report page): The focus box measures the reach to an item's origin, not to its nearer surface as the original does
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-FPS-NEEDS-DBG-HUD-56](HUD-FPS-NEEDS-DBG-HUD-56.md): dbg fps shows nothing unless dbg hud is on; with it, the box sits over the view near the top left
- HUD-INTERIOR-CLOCK-CUT-54 (no report page): The dbg hud line GLOBAL XYZ: unavailable (interior) is so long that the clock is cut off
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
- HUD-WEAPON-BOX-EMPTY-59 (no report page): HUD weapon box stays empty after equipping a weapon from the console
- [INFO-BOX-TEXT-CUT-62](INFO-BOX-TEXT-CUT-62.md): The name of an aimed door or object is drawn in a box over the view that cuts its text; before, the name was shown only below the view
- [INVENTORY-ARROWS-SCROLL-62](INVENTORY-ARROWS-SCROLL-62.md): The arrow keys do not move through any list window: dialogue topics, bartering, the inventory, containers and spells
- INVENTORY-BURDEN-TEXT-UNREADABLE-61 (no report page): The carried and maximum weight on the inventory burden bar cannot be read
- INVENTORY-NO-ARMOR-RATING-61 (no report page): The inventory window shows no armour rating under the character picture
- INVENTORY-OPEN-WINDOW-NO-REFRESH-61 (no report page): An item given and worn through the console while the inventory window is open does not show in that window until it is opened again
- INVENTORY-PREVIEW-STALE-61 (no report page): The inventory character preview does not change when equipment is put on or taken off in the window
- ITEM-ICONS-MISSING-62 (no report page): The container window shows clothing, armour, books, scrolls and potions as text without a picture, and the pictures it does show are small and sit in the corner of the slot, on a brown background
- LEVEL-UP-MISSING-57 (no report page): Requested: levelling as in the original: skills rise with use, the level-up box with its text and sound, attributes raised, the new values used by every check
- LOOT-WINDOW-ITEM-PROPERTIES-60 (no report page): Loot window does not show the selected item's type, weight and value
- LOOT-WINDOW-LAYOUT-60 (no report page): Loot window: key help cut off, item names clipped, buttons crammed against the frame
- LORE-DATE-FORMAT-62 (no report page): Game dates are printed as 18/08/427 instead of the original's form: day, month name, era and year
- [MADE-ITEM-NO-PICTURE-62](MADE-ITEM-NO-PICTURE-62.md): A made potion or a made enchanted item shows an empty picture in the inventory list
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [MSGBOX-NO-CURSOR-62](MSGBOX-NO-CURSOR-62.md): The death message box shows no mouse cursor
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- OPENING-SPEECH-LEADING-DOTS-65 (no report page): A speech line in the opening starts with a long row of dots before its text
- [OPENING-TUTORIAL-KEYS-65](OPENING-TUTORIAL-KEYS-65.md): The opening's tutorial boxes name the original game's controls (right click for the menus) instead of AmiWind's keys
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- PHOTO-CROSSHAIR-51 (no report page): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- QUICKSAVE-NO-PROFILE-SILENT-57 (no report page): Quicksave says nothing when no character profile is chosen (a game started from the console with map), while quickload says why
- [RACE-MENU-OK-HIGHLIGHT-65](RACE-MENU-OK-HIGHLIGHT-65.md): The OK box of the character windows shows no highlight when the keys reach it
- RAM-WARNING-BOX-52 (no report page): Requested: under 32 MB of Fast RAM a WARNING message box for a few seconds before the AmiWind logo
- SUBTITLE-BOX-HIDES-STATS-63 (no report page): The box of a spoken line rises over the whole lower part of the screen and hides the stat bar
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- [TOOLKIT-WORLD-FORMAT-STALE-64](TOOLKIT-WORLD-FORMAT-STALE-64.md): The 3D Map Inspector cannot open a current CHIM open world (format 0.11)
- [TRADEHOUSE-LONG-FRAME-59](TRADEHOUSE-LONG-FRAME-59.md): In Arrille's Tradehouse one frame can last about 10 seconds, with or without the container strip open
- TUTORIAL-BOX-SHOWN-TWICE-65 (no report page): After the papers the same tutorial box is shown twice in a row
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
- [UI-TEXT-BOX-CLEARANCE-64](UI-TEXT-BOX-CLEARANCE-64.md): Text boxes leave too little room above and below their text (the opening hint: the last line touches the bottom edge)
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
