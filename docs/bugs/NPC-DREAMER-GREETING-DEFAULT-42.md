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

<!-- contents start -->
## Contents

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

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- [DBG-MWSCRIPT-SILENT-56](DBG-MWSCRIPT-SILENT-56.md): dbg mwscript on prints nothing: the switch gives no answer, so it looks as if it did nothing
- EXTRAS-MENU-54 (no report page): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-FPS-NEEDS-DBG-HUD-56](HUD-FPS-NEEDS-DBG-HUD-56.md): dbg fps shows nothing unless dbg hud is on; with it, the box sits over the view near the top left
- HUD-INTERIOR-CLOCK-CUT-54 (no report page): The dbg hud line GLOBAL XYZ: unavailable (interior) is so long that the clock is cut off
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
- LEVEL-UP-MISSING-57 (no report page): Requested: levelling as in the original: skills rise with use, the level-up box with its text and sound, attributes raised, the new values used by every check
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- PHOTO-CROSSHAIR-51 (no report page): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- QUICKSAVE-NO-PROFILE-SILENT-57 (no report page): Quicksave says nothing when no character profile is chosen (a game started from the console with map), while quickload says why
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

Related bugs in other categories:

- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-GREETINGS-LIBRARY-MUTE-48](NPC-GREETINGS-LIBRARY-MUTE-48.md): NPCs placed by the actor library had no greeting, and every NPC said only part of its voice vocabulary
- [NPC-STORY-DISABLED-AT-START-42](NPC-STORY-DISABLED-AT-START-42.md): Story NPCs the original disables at the start (the twelve town Dreamers, the Dreamer Prophet) stand in the world from the first minute

<!-- END GENERATED CATEGORY -->
