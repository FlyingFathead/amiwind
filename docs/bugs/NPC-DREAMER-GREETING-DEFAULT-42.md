# NPC-DREAMER-GREETING-DEFAULT-42: Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | NPC greeting selection (dialogue lookup stage, aw_voice/aw_line on resident entities) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | medium: story characters say the wrong lines |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | 2026_10_17_v0.0.42-dev1_full-dev1-proof_5e043ad |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-17: reported in v0.0.42-dev1
- 2026-10-17: NPC-DREAMER-GREETING-DEFAULT-42: NPC-DREAMER-GREETING-DEFAULT-42: cause found: a talk said the NPC's Hello bark; the conversation greeting topics (Greeting 0-9) were never read, and the Hello topic has no Dreamer line.
- 2026-11-07: Register and work list synchronised: three entries fixed, the rest linked to open work: An audit of the register against the work list found entries that disagreed with it.

<!-- END GENERATED TIMELINE -->

<!-- contents start -->
## Contents

- [Timeline](#timeline)
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

## Symptom

Talking to a Dreamer in v0.0.42-dev1 (for example the one at Hla Oad) gives an ordinary greeting, "What is it,
sera?", with an ordinary voice. The maintainer, 17 October 2026: Dreamers greet with their own Sixth House lines.

## Where

The greeting fields the resident writers put on every placed NPC (`tools/import_town.py` for towns and CHIM
towns, `tools/prepare_area.py` for rooms and Seyda Neen) and the talk in `engine/aga/qc/world.qc` (`aw_greet`).

## How it happened

AmiWind had one line per NPC: `aw_voice` / `aw_line`, chosen by `greeting_fixture` (`src/mwad/npc.py`) from the
**Hello** voice topic, the bark an NPC says when the player comes near. A talk (E) said that same bark. The
original does something else when a conversation starts: it reads the **Greeting 0** to **Greeting 9** dialogue
topics. Those were never read, so every NPC opened a talk with its bark.

For a Dreamer the bark is generic: the Hello topic has no line for the Dreamers class (only one named
character has one), so the first matching Hello line is an ordinary Dark Elf line. The Sixth House words are
in Greeting 1, filtered on the class Dreamers (and for some Dreamers on their own ID or their cell): a first
meeting gives "We have you in our discerning eye, %PCName. We see you, waking and sleeping.", a later talk
"Beneath Red Mountain, Lord Dagoth has awakened. ... The Sixth House is risen, and Dagoth is its glory."

## Why it was not caught

The voiced-dialogue note listed the conversation greeting as separate, unimplemented work, but nothing in the
game said so: a talk looked like a working greeting.

## Reproduction

Any build up to v0.0.42-dev1: talk to a Dreamer (or anyone): the text is the NPC's Hello bark.

## Repair

`src/mwad/dialogue.py` picks the conversation greeting at build time by the rule of OpenMW 0.51
(`apps/openmw/mwdialogue/dialoguemanagerimp.cpp`, `DialogueManager::startDialogue`): the Greeting topics in the
store's order (sorted by ID, `apps/openmw/mwworld/store.cpp`), in each the first INFO in record order that
passes the filter (`apps/openmw/mwdialogue/filter.cpp`: speaker ID, race, class, faction and rank, sex; the
player's faction and cell; the conditions; the disposition). The conditions are evaluated for a new character
meeting the speaker for the first time: journals at 0, nobody dead, globals at their record values, script
locals at 0 (a local the speaker's script does not declare fails, as in OpenMW), no faction, level 1, no
bounty, not sneaking (so detected, OpenMW `awarenessCheck`), the starting clothes of the original player
record. What a build cannot know (the player's own race and sex, attributes, skills, `Random100`) is passed
over, and the residents report says which line was passed over (`talk_greetings`, `determined`).

Each NPC gets `aw_greeting` (first meeting) and, when it differs, `aw_greeting_again` (a later talk:
`TalkedToPc`). The speaker's text defines (`%Name`, `%Class`, `%Race`, `%Faction`, `%Rank`, `%Cell`) are filled
in at build time; the player's (`%PCName`, `%PCRace`, `%PCClass`) by the engine, as in books. A talk shows that
text in the dialogue box under the speaker's name (`PF_aw_converse`); like OpenMW's conversation start it
plays no sound. An NPC without a conversation greeting keeps the previous method: the Hello line and its
voice. The approach bark (the Hello topic) is unchanged.

Island-wide (the base master, every placed NPC reference, 2,897 placements of 2,620 NPCs): every placement has a
conversation greeting, so every talk now opens with it instead of the bark (none of them equals the old bark
text); 2,034 have a second line for later talks; 1,966 picks are fully determined, the rest passed over a line
that depends on the player character or on `Random100`. All 26 Dreamer records placed in the base master open
with a Sixth House line.

## Verification

`tests/test_conversation_greeting.py` (synthetic records): a class greeting beats a later generic one, first
meeting and later talk, a journal-gated line closed at the start, a script local, a player-dependent line passed
over and reported, the cell filter, sex and faction filters (no-faction marker), the starting clothing value,
the text defines, the record reader. In the game: pending a build with this commit.

## Prevention

The test above. The approach bark (the Hello topic, `greeting_fixture`) still differs from OpenMW's
first-match rule: that is the open [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md), left for its own change
(for a Dreamer OpenMW's first Hello match is an ordinary Dark Elf line too).

Related: [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md) (the town Dreamers should not stand
in the world before the main quest brings them).

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
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
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
- [MAP-MARKER-29](MAP-MARKER-29.md): Requested: click to place a user map marker
- [MAP-ORIGINAL-FEATURES-66](MAP-ORIGINAL-FEATURES-66.md): The map window lacks the original's map: the explored fog, the local map, the interior map and the place markers
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- [MAP-RIGHT-DRAG-29](MAP-RIGHT-DRAG-29.md): Advertised right-drag does not pan teleport map
- [MAP-SPOTS-28](MAP-SPOTS-28.md): In-game map screen has white/yellow spots
- [MAP-WORLD-TAB-BLANK-67](MAP-WORLD-TAB-BLANK-67.md): The World tab of the in-game map draws no land: only the player arrow and the place markers show on a blank background
- [MSGBOX-NO-CURSOR-62](MSGBOX-NO-CURSOR-62.md): The death message box shows no mouse cursor
- [NAMED-ACTIVATOR-FOCUS-66](NAMED-ACTIVATOR-FOCUS-66.md): Named objects such as beds and shrines show no name when looked at
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
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

Related bugs in other categories:

- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute

<!-- END GENERATED CATEGORY -->
