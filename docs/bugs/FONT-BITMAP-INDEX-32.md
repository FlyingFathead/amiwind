# FONT-BITMAP-INDEX-32: Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | bitmap font path (tools/prepare_ui.py, aw_ui.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Wrong characters on the Steam bitmap font path; little visible in shipped text. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
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

## Status: 8 October 2026

Open. Found by the font A/B (TrueType path from the GOG edition, bitmap path from the Steam edition). Affects Steam builds now; little visible in today's shipped text.

## Symptom

Bethesda's `.fnt` fonts store their glyphs in a DOS-style (code page 437-like) order, but the
converter copies the slots straight into the atlas and the engine looks glyphs up by the raw
Windows-1252 game byte. On the bitmap path 25 codes show the wrong letter (for example a
curly quote shows as ô or ö, dashes as û or ù, the ellipsis as à), other accented letters are
blank, and the curly apostrophes are blank but leave a wide gap.

## Where

`tools/prepare_ui.py` (`OriginalFont`, `pack_font`), `engine/aga/src/aw_ui.c` (`AW_UIText`).

## How it happened

The order inside the `.fnt` was never mapped; the conversion record also claims "CP1252
game strings" for the bitmap path.

## Why it was not caught

Only the GOG edition (TrueType path) was built, and today's shipped text has almost no
high characters.

## Reproduction

Build from the Steam edition and show text with curly quotes or accented letters.

## Repair

Not yet. One shared build-time mapping layer in `tools/prepare_ui.py`: atlas slot b always
means Windows-1252 byte b (the engine stays unchanged). Per byte, use the TrueType glyph only
if the font really has an outline for it (not a missing-glyph box, an empty zero-width glyph or
an ornament); otherwise the bitmap `.fnt` glyph through a verified per-font table from its
DOS-style (code page 437-like) order; otherwise a substitute as Morrowind and OpenMW use
(curly quotes to straight, dashes to a hyphen, the ellipsis to a full stop, accented capitals to
their base letter). Both editions then show the same characters. Decide the soft hyphen.

## Verification

Pending.

## Prevention

Tests: the .fnt slot holding e-acute lands in atlas slot 0xE9; quotes are never blank.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- [ARRIVAL-LONG-FRAME-DEV6-59](ARRIVAL-LONG-FRAME-DEV6-59.md): Arriving in Seyda Neen, the first frame of play lasts about 13 to 15 seconds; v0.0.59-dev6 test sessions stopped on it as a stall
- [AW-20260928-09](AW-20260928-09.md): Papers unreadable
- [AW-20260928-13](AW-20260928-13.md): New Game confirmation defaults to Cancel
- [AW25-03](AW25-03.md): Map marker reported stale; HUD lacked global/local positions
- [BARTER-TRADE-WINDOW-MISSING-67](BARTER-TRADE-WINDOW-MISSING-67.md): Missing: the original trade window: an offer the player changes, a running total of both sides, the merchant gold limit and restocking, haggling
- [BLANK-PAPER-READ-60](BLANK-PAPER-READ-60.md): A blank sheet of paper offers Read although it has no text
- [BOOK-PICTURE-MARKER-SHOWN-67](BOOK-PICTURE-MARKER-SHOWN-67.md): A book shows a line with a literal picture marker where the original draws an image (seen in a book on the stars, page 3 of 15)
- BOOK-TEXT-MACROS-58 (no report page): A book read where it lies shows the text defines as written (Name: %PCName Race: %PCRace Class: %PCClass)
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHARGEN-ABILITY-DESCRIPTIONS-65](CHARGEN-ABILITY-DESCRIPTIONS-65.md): The birthsign and race menus do not show what an ability or a special power does
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- [CLASS-LIST-LAYOUT-62](CLASS-LIST-LAYOUT-62.md): The class choice window runs its lists together without separating lines
- [CONTAINER-OWNED-PROMPT-WORDING-67](CONTAINER-OWNED-PROMPT-WORDING-67.md): An owned container's aim hint reads "E: Steal" instead of "E: Open" in red, and the container window's "E: Steal" is not red
- CONTAINER-STRIP-REDRAW-COST-59 (no report page): The container strip redraws the whole screen every frame: about 17 fps while it is open
- [CONTAINER-STRIP-TAKE-STALL-59](CONTAINER-STRIP-TAKE-STALL-59.md): A take or put in the container strip can hold the game for seconds
- [CONTAINER-TAKE-NO-CONFIRM-62](CONTAINER-TAKE-NO-CONFIRM-62.md): Taking an item from a container shows only its name; nothing says it was taken
- [CRIME-RELEASE-LINE-CUT-62](CRIME-RELEASE-LINE-CUT-62.md): The release from jail shows only its first three lines: the skills that changed are cut off
- [DBG-HELP-PAGER-TITLE-SPLIT-67](DBG-HELP-PAGER-TITLE-SPLIT-67.md): The debug command list can end a page on a group's title, its separator line opening the next page
- [DBG-MWSCRIPT-SILENT-56](DBG-MWSCRIPT-SILENT-56.md): dbg mwscript on prints nothing: the switch gives no answer, so it looks as if it did nothing
- [DBG-TP-TYPED-PLACE-NOT-FOUND-67](DBG-TP-TYPED-PLACE-NOT-FOUND-67.md): dbg tp ghostgate says the place is not found and sends the player to Balmora; the list box reaches Ghostgate but also prints not found
- [DIALOGUE-ARROWS-MOVE-POINTER-60](DIALOGUE-ARROWS-MOVE-POINTER-60.md): In the dialogue window the Up and Down keys move the mouse pointer instead of the topic selection
- [DIALOGUE-BACKDROP-HUD-60](DIALOGUE-BACKDROP-HUD-60.md): The status bars stay visible behind the dialogue screen
- [DIALOGUE-CHOICE-LINE-UNMARKED-60](DIALOGUE-CHOICE-LINE-UNMARKED-60.md): An answer picked from a dialogue choice is printed like the NPC's text, not as the player's line
- [DIALOGUE-CLOSE-FRAME-FREEZE-59](DIALOGUE-CLOSE-FRAME-FREEZE-59.md): The talk window takes seconds to open
- [DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67](DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67.md): Incomplete: a topic whose answer is already in the journal is drawn greyed, but it has not been seen in a built game
- [DIALOGUE-GOODBYE-BLOCKED-HINT-67](DIALOGUE-GOODBYE-BLOCKED-HINT-67.md): While an answer waits for Continue, Goodbye does nothing and nothing shows why; requested: Goodbye and the topics greyed out, and a box "Continue the conversation first." when Goodbye is chosen
- [DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67](DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67.md): Incomplete: after a result script calls Goodbye only the Goodbye button is left in the window, not seen in a built game
- [DIALOGUE-ITEM-NOTICE-MISSING-61](DIALOGUE-ITEM-NOTICE-MISSING-61.md): An item a dialogue answer gives or takes shows no notice while talking
- DIALOGUE-LINK-MARK-AS-DEFINE-58 (no report page): Dialogue links lose their first two letters to a number, and the link itself, since the text defines table
- [DIALOGUE-LINKS-62](DIALOGUE-LINKS-62.md): The blue topic words in dialogue text cannot be clicked, a word is highlighted inside a longer word, and asking about a dead person gives "Who?"
- [DIALOGUE-MSGBOX-BEHIND-60](DIALOGUE-MSGBOX-BEHIND-60.md): Message boxes raised during a conversation open behind the dialogue window
- DIALOGUE-OPEN-STALL-58 (no report page): Opening a conversation hangs the game for many seconds
- [DIALOGUE-PADDING-UNEVEN-23](DIALOGUE-PADDING-UNEVEN-23.md): Two dialogue rows had uneven vertical spacing
- [EXTRAS-MENU-54](EXTRAS-MENU-54.md): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FOCUS-BOX-TWO-AT-ONCE-59](FOCUS-BOX-TWO-AT-ONCE-59.md): Two item boxes at once: the box of the item aimed at before stays while the next item's box is drawn below the view
- FOCUS-BOX-UNDRAWN-ITEMS-58 (no report page): The focus box showed for room items that the room does not draw, and the activate key then took nothing
- [FOCUS-NPC-OVERRIDES-ITEM-62](FOCUS-NPC-OVERRIDES-ITEM-62.md): Trying to take an item near a character talks to the character instead: the nearby character overrides the item under the crosshair
- [FOCUS-REACH-ITEM-ORIGIN-58](FOCUS-REACH-ITEM-ORIGIN-58.md): The focus box measures the reach to an item's origin, not to its nearer surface as the original does
- [FOCUS-ROWS-WINDOW-OVERFLOW-66](FOCUS-ROWS-WINDOW-OVERFLOW-66.md): In the busiest outdoor places some placed things have no focus row
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-FPS-NEEDS-DBG-HUD-56](HUD-FPS-NEEDS-DBG-HUD-56.md): dbg fps shows nothing unless dbg hud is on; with it, the box sits over the view near the top left
- HUD-INTERIOR-CLOCK-CUT-54 (no report page): The dbg hud line GLOBAL XYZ: unavailable (interior) is so long that the clock is cut off
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
- [HUD-TEXTS-OVERLAP-67](HUD-TEXTS-OVERLAP-67.md): Two texts are drawn on top of each other in the HUD: the name of the aimed character and the place name
- HUD-WEAPON-BOX-EMPTY-59 (no report page): HUD weapon box stays empty after equipping a weapon from the console
- [INFO-BOX-TEXT-CUT-62](INFO-BOX-TEXT-CUT-62.md): The name of an aimed door or object is drawn in a box over the view that cuts its text; before, the name was shown only below the view
- [INVENTORY-ARROWS-SCROLL-62](INVENTORY-ARROWS-SCROLL-62.md): The arrow keys do not move through any list window: dialogue topics, bartering, the inventory, containers and spells
- [INVENTORY-BURDEN-TEXT-UNREADABLE-61](INVENTORY-BURDEN-TEXT-UNREADABLE-61.md): The carried and maximum weight on the inventory burden bar cannot be read
- [INVENTORY-EQUIPPED-LABEL-67](INVENTORY-EQUIPPED-LABEL-67.md): An item the player already wears or holds still shows "E/Enter equip" in the inventory, and nothing marks it as equipped
- [INVENTORY-ITEM-INFO-67](INVENTORY-ITEM-INFO-67.md): Requested: an item information button in the inventory that opens a box with the item's properties, where the game data has them
- [INVENTORY-NO-ARMOR-RATING-61](INVENTORY-NO-ARMOR-RATING-61.md): The inventory window shows no armour rating under the character picture
- [INVENTORY-OPEN-WINDOW-NO-REFRESH-61](INVENTORY-OPEN-WINDOW-NO-REFRESH-61.md): An item given and worn through the console while the inventory window is open does not show in that window until it is opened again
- [INVENTORY-PREVIEW-STALE-61](INVENTORY-PREVIEW-STALE-61.md): The inventory character preview does not change when equipment is put on or taken off in the window
- [ITEM-ICONS-MISSING-62](ITEM-ICONS-MISSING-62.md): The container window shows clothing, armour, books, scrolls and potions as text without a picture, and the pictures it does show are small and sit in the corner of the slot, on a brown background
- [ITEM-VIEW-ENTER-UNEQUIPS-67](ITEM-VIEW-ENTER-UNEQUIPS-67.md): In the inventory's item information view, Enter unequips the item being viewed instead of only closing the view
- [JOURNAL-HYPERLINKS-QUEST-ENTRIES-67](JOURNAL-HYPERLINKS-QUEST-ENTRIES-67.md): Incomplete: the journal hyperlinks work on topic pages only: the quest entries (the dated pages) carry no link spans
- [JOURNAL-NOTICE-EMPTY-ENTRY-67](JOURNAL-NOTICE-EMPTY-ENTRY-67.md): Incomplete: the journal updated notice is shown for a new entry with empty text, where OpenMW skips it
- [JOURNAL-QUEST-ENTRIES-NOT-SEEN-67](JOURNAL-QUEST-ENTRIES-NOT-SEEN-67.md): Incomplete: the quests and their finished and restart marks in the journal book are not seen in a built game
- [JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67](JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67.md): Incomplete: the journal topic pages fill the %-values of an entry when the page is read, not when it was said
- [LEVEL-UP-MISSING-57](LEVEL-UP-MISSING-57.md): Requested: levelling as in the original: skills rise with use, the level-up box with its text and sound, attributes raised, the new values used by every check
- [LOOT-WINDOW-ITEM-PROPERTIES-60](LOOT-WINDOW-ITEM-PROPERTIES-60.md): Loot window does not show the selected item's type, weight and value
- [LOOT-WINDOW-LAYOUT-60](LOOT-WINDOW-LAYOUT-60.md): Loot window: key help cut off, item names clipped, buttons crammed against the frame
- [LORE-DATE-FORMAT-62](LORE-DATE-FORMAT-62.md): Game dates are printed as 18/08/427 instead of the original's form: day, month name, era and year
- [MADE-ITEM-NO-PICTURE-62](MADE-ITEM-NO-PICTURE-62.md): A made potion or a made enchanted item shows an empty picture in the inventory list
- [MAP-FOCUS-DRAG-29](MAP-FOCUS-DRAG-29.md): Map or journal keeps dragging after window focus returns
- [MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68](MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68.md): Inside a room the map opens on the World view instead of the room's plan in rooms built on the shared room store
- [MAP-MARKER-29](MAP-MARKER-29.md): Requested: click to place a user map marker
- [MAP-ORIGINAL-FEATURES-66](MAP-ORIGINAL-FEATURES-66.md): The map window lacks the original's map: the explored fog, the local map, the interior map and the place markers
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- [MAP-RIGHT-DRAG-29](MAP-RIGHT-DRAG-29.md): Advertised right-drag does not pan teleport map
- [MAP-SPOTS-28](MAP-SPOTS-28.md): In-game map screen has white/yellow spots
- [MAP-WORLD-TAB-BLANK-67](MAP-WORLD-TAB-BLANK-67.md): The World tab of the in-game map draws no land: only the player arrow and the place markers show on a blank background
- [MENU-PALETTE-RED-CAST-68](MENU-PALETTE-RED-CAST-68.md): The map screen, the inventory and the item icons have a red cast since the scene palette change for ice and snow
- [MSGBOX-NO-CURSOR-62](MSGBOX-NO-CURSOR-62.md): The death message box shows no mouse cursor
- [NAMED-ACTIVATOR-FOCUS-66](NAMED-ACTIVATOR-FOCUS-66.md): Named objects such as beds and shrines show no name when looked at
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- [OPENING-QUOTE-OVERLAY-23](OPENING-QUOTE-OVERLAY-23.md): The first prophecy quote of the intro showed unreadable burned-in lettering again
- [OPENING-SPEECH-LEADING-DOTS-65](OPENING-SPEECH-LEADING-DOTS-65.md): A speech line in the opening starts with a long row of dots before its text
- [OPENING-TUTORIAL-KEYS-65](OPENING-TUTORIAL-KEYS-65.md): The opening's tutorial boxes name the original game's controls (right click for the menus) instead of AmiWind's keys
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- [PHOTO-CROSSHAIR-51](PHOTO-CROSSHAIR-51.md): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PICKUP-NAME-ONLY-BOX-67](PICKUP-NAME-ONLY-BOX-67.md): Picking up an item shows only the item name in a box
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- QUICKSAVE-NO-PROFILE-SILENT-57 (no report page): Quicksave says nothing when no character profile is chosen (a game started from the console with map), while quickload says why
- [RACE-MENU-OK-HIGHLIGHT-65](RACE-MENU-OK-HIGHLIGHT-65.md): The OK box of the character windows shows no highlight when the keys reach it
- RAM-WARNING-BOX-52 (no report page): Requested: under 32 MB of Fast RAM a WARNING message box for a few seconds before the AmiWind logo
- [SIGNPOST-NAMES-MISSING-65](SIGNPOST-NAMES-MISSING-65.md): Signposts do not show what they read when the player looks at them
- [STATS-WINDOW-COLOURS-UNTIL-LOAD-67](STATS-WINDOW-COLOURS-UNTIL-LOAD-67.md): Stats window draws a raised attribute almost black and the birthsign icons brown until a saved game is loaded
- [SUBTITLE-BOX-HIDES-STATS-63](SUBTITLE-BOX-HIDES-STATS-63.md): The box of a spoken line rises over the whole lower part of the screen and hides the stat bar
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- [TOOLKIT-WORLD-FORMAT-STALE-64](TOOLKIT-WORLD-FORMAT-STALE-64.md): The 3D Map Inspector cannot open a current CHIM open world (format 0.11)
- [TRADEHOUSE-LONG-FRAME-59](TRADEHOUSE-LONG-FRAME-59.md): In Arrille's Tradehouse one frame can last about 10 seconds, with or without the container strip open
- [TUTORIAL-BOX-SHOWN-TWICE-65](TUTORIAL-BOX-SHOWN-TWICE-65.md): After the papers the same tutorial box is shown twice in a row
- [UI-ACCEPT-29](UI-ACCEPT-29.md): Character selection lacks a visible OK button
- [UI-CHARGEN-CLASS-FONT-67](UI-CHARGEN-CLASS-FONT-67.md): Requested: the Make your own class window uses the console font for the attribute and skill rows (as the race stats screen does), keeps the heading in the game font, and gives its hint row and Cancel and OK buttons the regular frame
- [UI-CONSOLE-FONT-SPECIAL-LETTERS-67](UI-CONSOLE-FONT-SPECIAL-LETTERS-67.md): Accented letters and curly quotes in game texts drawn in the console font show as other characters: an acute u as z, an acute e as i, a right single quote as a coloured digit
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-ICONS-INVENTORY-42](UI-ICONS-INVENTORY-42.md): Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops
- [UI-INVENTORY-FONT-TABS-42](UI-INVENTORY-FONT-TABS-42.md): Inventory categories use the console font as plain text instead of the original Morrowind font on button tabs
- [UI-INVENTORY-HEADING-CENTRE-42](UI-INVENTORY-HEADING-CENTRE-42.md): The Inventory heading text is not vertically centred in its bar
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid
- [UI-INVENTORY-PREVIEW-GAP-41](UI-INVENTORY-PREVIEW-GAP-41.md): Inventory shows 'Character preview unavailable': a fixed 2 MiB memory guard refuses the 128 KB pose model in Seyda Neen
- [UI-INVENTORY-PREVIEW-STILL-42](UI-INVENTORY-PREVIEW-STILL-42.md): The inventory character is drawn live and turns instead of being a still picture
- [UI-JOURNAL-HINT-EMPTY-BOX-67](UI-JOURNAL-HINT-EMPTY-BOX-67.md): An empty box flashes after the first journal hint has gone: the frame stays on screen for a moment without its text
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- [UI-MAP-PLAYER-ARROW-51](UI-MAP-PLAYER-ARROW-51.md): Requested: the map shows the player as the original s arrow that turns with the player, not a crosshair
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- [UI-NO-SHARED-LAYOUT-67](UI-NO-SHARED-LAYOUT-67.md): Menus place their boxes and buttons at fixed pixel positions of their own, so margins differ from screen to screen and buttons sit against the bottom edge of the box
- [UI-OK-BUTTON-THIN-FRAME-67](UI-OK-BUTTON-THIN-FRAME-67.md): The OK button in the menus has a thin outline instead of the regular button frame that View Stats has
- [UI-OPTIONS-WRAP-29](UI-OPTIONS-WRAP-29.md): Setup selection wraps despite a bounded scrollbar
- [UI-ORNAMENT-GLYPHS-23](UI-ORNAMENT-GLYPHS-23.md): The name-entry caret drew as a ball and the rotation hints as a skull and a tree (ornamental font glyphs)
- UI-PALETTE-NO-WHITE-48 (no report page): The game palette has no white: a White crosshair draws as the console ink cream (238,221,170)
- [UI-RACE-STATS-RETURN-SPACING-67](UI-RACE-STATS-RETURN-SPACING-67.md): Requested: the race stats screen gets a Return button under the attributes and space under the Attributes heading
- [UI-STATS-WINDOW-48](UI-STATS-WINDOW-48.md): No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows
- [UI-TEXT-BOX-CLEARANCE-64](UI-TEXT-BOX-CLEARANCE-64.md): Text boxes leave too little room above and below their text (the opening hint: the last line touches the bottom edge)
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
