# UI-STATS-WINDOW-48: No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | Stats and Magic windows: engine/aga/src/aw_statswin.c on the inventory modal (aw_worldui.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | medium: the player cannot see the character's attributes, skills or level anywhere in the game |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 82c76d6, engine 82c76d6, CHIM world 82c76d6 |
| CHIM engine version | CHIM 0.2.1, engine 82c76d6, world format 0.12 |
| Platform or emulator | not in game (a missing window, reported in chat; the in-game check comes with the next build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

## Symptom

The game had no window that shows the character: no attributes, skills, level
or class, and the health, magicka and fatigue numbers only as HUD bars. The
maintainer, 23 October 2026 (desktop chat): "we don't have the attributes view
yet ... maybe P would be a good key for attributes, kind of like "properties"
... should have the original Morrowind UI and such", and "make sure all of these
are customizable in options/keyboard". The Magic window was asked for as a
placeholder on O: "it could of course be empty for the time being, a sort of
just a placeholder type menu", "it could start off with just starter spells and
could say in the Morrowind font at the center bottom (Not yet implemented)".

## Where

Gameplay windows. The inventory (I), journal (J) and map (M) existed; P and O
were unbound.

## How it happened

The window work so far covered the inventory, map and journal. The character
sheet existed in the engine (`aw_character`: attributes, modifiers, damage,
skills, current and maximum health, magicka and fatigue; race, class and
birthsign from `character/catalog.awc`) but nothing displayed it after
character creation.

## Why it was not caught

The original's Stats and Magic windows were not on the window checklist.

## Reproduction

Press P or O in game: nothing opened.

## Repair

`engine/aga/src/aw_statswin.c` draws both windows on the inventory's modal
(`AW_WorldUIOpenPanel` in `aw_worldui.c`): the same frame, original title bar,
fonts and colours, the same pause and input handling; Escape or the window's
own key closes it.

- **Stats (P, `aw_stats`)**: titled with the character's name, as in the
  original (OpenMW `mwgui/statswindow.cpp` setPlayerName). Left: health,
  magicka and fatigue bars with current/maximum, level, race, class, the eight
  attributes (base + modifiers - damage; a modified value in green) and the
  birthsign. Right: Major Skills and Minor Skills in the class's order (the
  class record's skill pairs), then Misc Skills in skill record order (OpenMW
  `configureSkills`), with a scrollbar. Read live every frame. Factions,
  reputation and bounty are left out: the engine has no faction state yet.
- **Magic (O, `aw_magicmenu`)**, a placeholder: the headings Powers, Spells and
  Magic Items; the race's and birthsign's spells by name, sorted under Powers
  or Spells by their SPEL type (abilities left out, as the original list does);
  "None" under an empty heading; "(Not yet implemented)" centred at the bottom
  in the window title font. The names come from `character/spells.aws`, which
  the image builder now writes from the player's own game data
  (`tools/prepare_character.py`); without it every heading shows None. The
  class-based starting spells the original picks at character creation are not
  listed yet.
- Both actions are in Options > Controls; `config/keymaps.cfg` binds P and O,
  and older saved key files get them where those keys are free
  (`AW_ControlsMigrate`). [Keymaps](../KEYMAPS.md),
  [windows](../INVENTORY.md#stats-and-magic-windows-23-october-2026).
- Resident cost: two command records, 64 bytes (tests/resident_registry_budget.json).

Checked by `tests/aga_statswin_test.c` (a fixture character drawn with the
real 3x5 glyphs: every content row, the grouping, the scroll, the keys and
rebinding, the live update, the Magic sections and footer), the Options >
Controls test and the key-file migration test. Open until in-game stills of
both windows are recorded.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
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
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
