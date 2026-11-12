# DIALOGUE-CLOSE-FRAME-FREEZE-59: Opening a conversation freezes the game for seconds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 3 November 2026, in v0.0.59-dev5 |
| Where | engine/aga/src/aw_dialwin.c (AW_DialWindowOpen), engine/aga/src/aw_dial.c (AW_DialConverse) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | fixed in v0.0.59-dev6 |
| Severity | high: The game stands still for about 14 s after Escape closes a conversation; it recovers on its own |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | 2026_11_03_v0.0.59-dev5_miniwind-seyda-uistate_daf9298 |
| From commit | source daf9298, engine daf9298, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine daf9298, world format unknown |
| Unknown because | MiniWind test image of the uistate branch; world and CHIM fields not recorded by the session |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.59-dev6 (3 November 2026)._

<!-- contents start -->
## Contents

- [Status: 3 November 2026](#status-3-november-2026)
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

## Status: 3 November 2026

Fixed in v0.0.59-dev6 for the conversation read (3.2 to 3.5 s before, 0.56 s after). Seen again in dev5 with the open at
about 6 s, from the script strings, which the dev6 string cache removes (see Verification).

## Symptom

Talking to an actor (Fargoth in Seyda Neen) held the game for several seconds before the window showed.

## Where

The conversation read of the talk window: list items, entries and condition rows of the dialogue data.

## How it happened

Measured per phase on the Seyda Neen MiniWind (FS-UAE, JIT, 32 MB Fast): the open took 3.2 to 3.5 s, of which 2.9 s was
reading the conversation (1384 small disk reads, one seek each). Every other phase was under 0.2 s.

## Why it was not caught

The talk window's open time was not measured per phase on the emulator before this report.

## Reproduction

In a Seyda Neen MiniWind, `dbg npcs talk fargoth` and read the phase line the console prints.

## Repair

The reads go through a small block cache (16 blocks of 4 KiB, made fresh at each open). The compiled scripts' short
strings are kept after the first read, so a second read of them is gone as well.

## Verification

The same open takes 0.56 s (conversation read 0.24 s, 137 disk reads); the greeting and the topic list are the same, and
play continues after Escape. The console prints the phases on every open; `dbg npcs talkcache off` reads without the
cache for comparison. A sighting in dev5 (open at about 6 s, the script string reads gone) is the report line on the
register entry.

## Prevention

The console prints the phases of every open, so a regression shows in any session.

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
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
