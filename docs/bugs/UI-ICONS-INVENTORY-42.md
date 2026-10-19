# UI-ICONS-INVENTORY-42: Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | Inventory screen (aw_worldui.c inventory_icon, tools/prepare_inventory.py icon staging) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | low: Cosmetic: item identity still shown by name. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.41 release image |
| From commit | source 5ce02c8, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

## Symptom

The inventory list shows an item icon only for the handful of items the
build stages resources for (the starting clothes, the opening papers, gold,
the courtyard ring, a steel longsword and a steel shield). Every other owned
item shows an empty 16 x 16 box. The icons that do show are the 32 x 32
originals sampled unevenly down to 14 x 14 (some rows and columns dropped),
and enchanted or equipped items lack the original magic and equipped
backdrops.

## Where

The inventory screen: `inventory_icon` in engine/aga/src/aw_worldui.c and the
icon staging in tools/prepare_inventory.py (`gfx/inv/*.awi`, 32 x 32).

## How it happened

The inventory was built with interim resources for the items the opening
needs. The icon staging is limited to that selected set, and the list row
draws the 32 x 32 picture into a 14 x 14 area by nearest sampling.

## Why it was not caught

Inventory checks covered ownership, equip and drop transactions and the text
layout (UI-INVENTORY-LAYOUT-40), not the artwork against the original.

## Reproduction

Grant any item outside the opening set (`aw_inventory grant "iron dagger" 1`)
and open the inventory: its row has an empty icon box. Compare a staged
item's icon with the original inventory at the same item.

## Repair

On the HUD's icon table (HUD-STATS-29, docs/HUD.md "Inventory icons"): the
image step converts the inventory cell of every catalogue item that has an
icon (the original 42 x 42 item cell with its 32 x 32 icon, scaled to the
row's 16 x 16 slot), on the magic backdrop when enchanted, plus an equipped
variant on menu_icon_equip.dds (or menu_icon_magic_equip.dds) for equippable
items, as the original item widget does; potions now find their icon (the
record's TEXT field, not ITEX); all pictures are stored once in one pack (gfx/icons.awp). Each row draws
its picture without resampling; one slot per visible row, reloaded only on
change. `aw_hud_icons 0` keeps the old rows. Branch v0.0.42-hud-title.

## Verification

Builder tests with synthetic pictures (every item, the equipped and magic
backdrops, one picture for many rows, the process pool path, the pack
offsets and SHA-256), a native fixture of the row drawing and the pack
reading, the palette overlay's pack parser; in-game stills and a clip of
owned items outside the old staged set, one equipped. On a GOG Morrowind install:
3,414 rows, 1,150 pictures, pack 305,208 bytes, 1.3 s.

## Prevention

The icon import has a synthetic-picture test suite (tests/test_hud_icons.py);
the inventory change will add a row test that every owned item in a fixture
resolves through the table and draws unresampled.

## Every UI screen audited for icons, 17 October 2026

Audit of the in-game screens against the original (as OpenMW 0.51 lays it
out) for item, spell and effect icons:

| Screen | AmiWind now | Original |
| --- | --- | --- |
| HUD weapon box | Fixed in v0.0.42-dev1 (HUD-STATS-29) | Weapon icon or hand-to-hand icon, condition bar |
| HUD magic box | Fixed for magic items in v0.0.42-dev1 (HUD-STATS-29); no spells | Spell effect icon and cast chance, or item icon and charge |
| HUD sneak indicator | Absent (no sneaking) | Sneak icon while sneaking |
| HUD active effects | Absent (docs/HUD_ACTIVE_EFFECTS.md) | Small effect icons |
| HUD mini map, weapon/spell name line | Absent | Local map; the name for a few seconds after a change |
| Inventory list | This bug | Every item's icon, magic and equipped backdrops |
| Magic menu | Does not exist | Spell, power and magic item lists, active effects |
| Character / stats screen | Not implemented; character creation is text only | Class and birthsign pictures, icons in tooltips |
| Barter, containers | No screens | Item grid with icons |
| Dialogue, journal, book reader | Text and book art | No icons |
| World map | Player and towns drawn as small marks | Player marker texture; local map door markers |
| Main menu | Text buttons | Picture buttons |
| Tooltips | None | Item icon with its values |

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
- NPC-DREAMER-GREETING-DEFAULT-42 (no report page): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
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

<!-- END GENERATED CATEGORY -->
