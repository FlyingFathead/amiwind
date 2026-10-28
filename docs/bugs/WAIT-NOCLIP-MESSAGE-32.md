# WAIT-NOCLIP-MESSAGE-32: Wait refusal names registration, dry ground and speech together instead of the reason that applied

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Wait dialogue (T) with noclip on, anywhere |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | low: Message wording. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

## Status: 8 October 2026

Open, low priority (message wording); cause found in source. Project decision: fix later, no code
change in v0.0.32. Reported by the maintainer in v0.0.32-dev3 play (8 October 2026); seen many times
before in earlier development builds (first version unknown).

## Symptom

With `noclip` on, pressing T (wait) shows "Wait after registration, on dry ground, when no one is
speaking." although registration is long done and nobody is speaking. The real reason is that the
player is not standing on the ground.

Refusing the wait itself follows the original game, which does not let the player wait or rest while
in the air (levitating, falling) or swimming. The defect is only the message: it lists every
condition at once instead of the one that applied. The original shows its own specific messages;
they are to be checked against OpenMW before any wording is copied.

## Where

`engine/aga/src/aw_wait.c`: `allowed()` and `wait_open()`.

## How it happened

`wait_open()` shows one combined message whenever `allowed()` returns 0. `allowed()` returns 0 when
the game is not a local single-player game, the story restricts waiting, character creation or a
book is open, or speech is playing, and also unless the player edict stands: health above 0,
movetype `MOVETYPE_WALK`, `FL_ONGROUND` set, waterlevel below 2, game not paused. Noclip changes the
movetype to `MOVETYPE_NOCLIP`, so that test fails and the combined registration, dry ground and
speech message is shown.

## Why it was not caught

No test covers the wait refusal reasons, and none covers waiting with noclip on; the message was
written for the opening, where registration is the usual reason.

## Reproduction

Any build with the wait dialogue: after release from the Census office, open the console, type
`noclip`, close the console, press T.

## Repair

Not yet. Let `allowed()` return the reason and show a message for that reason only (in the air or
flying, in water, during speech, before registration), with wording checked against the original
game in OpenMW. Waiting in noclip stays refused unless the maintainer decides otherwise.

## Verification

Pending.

## Prevention

Proposed: a native test of the wait refusal reasons (one state per reason, including noclip).

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
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

Related bugs in other categories:

- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)

<!-- END GENERATED CATEGORY -->
