# HUD: weapon and magic boxes

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

<!-- contents start -->
## Contents

- [What the boxes show](#what-the-boxes-show)
- [How the boxes are made (builder)](#how-the-boxes-are-made-builder)
- [Inventory icons](#inventory-icons)
- [Window title bar](#window-title-bar)
- [Engine (aw_icons.c)](#engine-aw_iconsc)
- [Boxes on screen](#boxes-on-screen)
- [The shared layout (v0.0.67)](#the-shared-layout-v0067)
- [One target under the crosshair (v0.0.67)](#one-target-under-the-crosshair-v0067)

<!-- contents end -->

Last updated with AmiWind v0.0.42-dev1.

The lower-left HUD shows the three resource bars (health, magicka, fatigue)
and, beside them, the two original boxes: the **weapon box** and the **magic
box**. From v0.0.42-dev1 both boxes are drawn from the original game art,
converted at build time from your own Morrowind data (bug HUD-STATS-29).
Nothing in this repository contains a game texture, icon or a picture made
from one: the repository holds only the converter, the lookup-table logic and
tests with synthetic pictures.

## What the boxes show

| Box | Shows | Bar under the box |
| --- | --- | --- |
| Weapon | The equipped weapon's own inventory icon; the hand-to-hand icon when unarmed. An enchanted weapon sits on the original blue magic backdrop. | Weapon condition (empty for fists). |
| Magic | The selected magic item's icon on the magic backdrop; the empty box when nothing is selected. | The item's enchantment charge. |

The original also shows a selected **spell** (its first effect's icon, with the
cast chance in the bar). AmiWind has no spell list yet, so a spell cannot be
selected and the magic box shows only magic items.

The boxes appear in the same story stages as before (the weapon box after the
registration papers, the magic box after the courtyard ring; see
HUD-STATS-29).

### Selecting a magic item

The original selects magic items in the magic menu, which AmiWind does not
have yet. Until it exists, use the console:

| Command | Effect |
| --- | --- |
| `aw_magic` | Show the selected magic item and its charge. |
| `aw_magic select ID` | Select an owned Cast Once or Cast When Used item (as the original magic menu lists them), e.g. `aw_magic select ring_keley`. |
| `aw_magic none` | Clear the selection. |
| `aw_magic charge ID POINTS` | DIAGNOSTIC: set an item's current charge (for testing the bar). |
| `aw_magic stats` | The HUD icon counters and the boxes' measured cost per frame. |

The selection is cleared when the item leaves the inventory. Casting from an
item is not implemented yet, so charge is spent only by the diagnostic.

### Enchantment charge

* **Maximum charge**: the enchantment's authored charge, or, for an
  auto-calculated enchantment, the rounded total effect cost times the
  iMagicItemCharge setting of its type (Once, Strike, Use, Constant). The
  builder computes it from the ENCH, MGEF and GMST records and stores it in
  the item catalogue.
* **Current charge**: full until it is recorded below full; recorded per owned
  item in the save (save feature bit 4; older AmiWind versions refuse such a
  save rather than lose the charge).
* **Recharge**: Cast When Used and Cast When Strikes items regain
  fMagicItemRechargePerSecond (0.05 in Morrowind.esm) charge points per second
  of unpaused play, and the equivalent time when you wait (game hours divided
  by the time scale), never above the maximum.
* A partly spent item is not dropped (placed items do not carry charge yet);
  the drop is refused and the item kept.

## How the boxes are made (builder)

The image step's inventory conversion (tools/prepare_inventory.py) calls the
icon and HUD-art import (tools/prepare_icons.py). It writes:

* `gfx/icons.awl`: ONE lookup table for every UI picture: key, the original
  source path, the picture's place in the pack and its SHA-256. Keys:
  `item:<record id>` (the HUD icon of the record's icon field, 18 x 18),
  `inv:<record id>` and `inv:<record id>:equip` (the inventory cell, 16 x 16,
  and its equipped variant), `skill:26` (the hand-to-hand icon), `hud:box`,
  `hud:bar`, `hud:track:weapon`, `hud:track:magic`, `ui:head:*` (the window
  title bar), later `mgef:<index>` for spells.
* `gfx/icons.awp`: every picture once (identical pictures stored once), in one
  file rather than thousands (classic FFS directories), palette indices for
  the installed game palette. The engine still reads the first v0.0.42-dev1
  layout (one `gfx/icon/<sha>.awi` file per picture).
* `gfx/hud-settings.txt`: the recharge rate (fMagicItemRechargePerSecond) and
  the hand-to-hand name (sSkillHandtohand).
* the item catalogue (`inventory/items.awi`) bytes 496..511: enchantment type
  and maximum charge.

Only the referenced closure is converted: the HUD icons of the items the build
stages resources for, the inventory icon of every catalogue item the player
can own, and the fixed UI keys; the item pictures are converted in a process
pool with the build's `--jobs`. On a GOG Morrowind install: 3,414 rows, 1,150 distinct
pictures, a 305,208-byte pack and a 546,248-byte table, converted in about 1.3 s. The conversion prints one
line with the table rows, stored pictures, their bytes and any item held back
(a missing original is held with its reason, never replaced by other art).

### Original art used

| Picture | Original texture(s) | Size in AmiWind |
| --- | --- | --- |
| Box | `textures/menu_thin_border_*.dds` around a black interior | 20 x 20 (1-pixel border) |
| Bar frame | the same thin border pieces | 20 x 4 |
| Bar fill | `textures/menu_bar_gray.dds` tinted by Morrowind.ini `[FontColor] color_weapon_fill` / `color_magic_fill` | 18 x 2 |
| Item icon | the record's icon (`icons/...`, `.dds` first) | 18 x 18 |
| Hand-to-hand | `icons/k/stealth_handtohand.dds` | 18 x 18 |
| Magic backdrop | `textures/menu_icon_magic.dds` (behind enchanted items) | baked into the item icon |

### Where each rule comes from

AmiWind's code is its own implementation. The composition follows the
original HUD as OpenMW 0.51 describes it (read for reference, no code taken):

* `files/data/mygui/openmw_hud.layout` (WeapBox, SpellBox): a 36 x 36 box with
  a 36 x 6 bar under it, beside three 65 x 12 resource bars.
* `files/data/mygui/openmw_hud_box.skin.xml` (HUD_Box) and
  `openmw_box.skin.xml` (MW_Box): black interior inside the 2-pixel thin menu
  border.
* `files/data/mygui/openmw_hud_energybar.skin.xml` (MW_EnergyBar_Weapon,
  MW_EnergyBar_Magic, MW_BarTrack_*): thin border, black client, a 2-pixel
  grey track tinted by the fill colour.
* `files/data/mygui/openmw_resources.xml` (MW_ItemIconNoShadow) and
  `apps/openmw/mwgui/itemwidget.cpp` (ItemWidget::setItem): the 32 x 32 icon
  fills the box interior; the magic backdrop only for enchanted items.
* `apps/openmw/mwgui/hud.cpp` (setSelectedWeapon, unsetSelectedWeapon,
  setSelectedEnchantItem, unsetSelectedSpell) and `windowmanagerimp.cpp`:
  which icon and bar value each state shows.
* `apps/openmw/mwmechanics/spellutil.cpp` (getEnchantmentCharge,
  calcEffectCost), `recharge.cpp` (rechargeItem), `containerstore.cpp`
  (which items recharge), `mwworld/worldimp.cpp` (advanceTime: waiting),
  `mwgui/spellmodel.cpp` (which items can be selected).

AmiWind's three resource bars are 24 pixels tall where the original's span 42,
so every HUD size is the original's times 24/42 (rounded).

## Inventory icons

Each inventory row shows the item's own original icon as the original item
cell: the 42 x 42 cell with the 32 x 32 icon at 5,5 and the backdrop stretched
over it (files/data/mygui/openmw_resources.xml MW_ItemIcon,
apps/openmw/mwgui/itemwidget.cpp setItem), scaled to the row's 16 x 16 slot
(icon 12 x 12 at 2,2): the magic backdrop when enchanted, the equipped
backdrop (`menu_icon_equip.dds`, `menu_icon_magic_equip.dds`) when equipped.
Potions name their icon in the record's TEXT field, other items in ITEX. One picture slot per
visible row, loaded only when that row's item or state changes. `aw_hud_icons
0` keeps the old rows (the staged 32 x 32 icon in a small box).

## Window title bar

Titled windows (the inventory first) use the original title bar, imported in
the same step: `ui:head:block` (the head block strip: `menu_head_block_middle`
tiled inside its top and bottom edges), `ui:head:left` and `ui:head:right`
(the edge columns), scaled 12/20 to AmiWind's 12-pixel title band. The title
sits on the window's black between two head blocks, the gap being its width
plus 24 (scaled: 14), centred by its painted pixels. The inventory's title is
the equipped weapon's name, or the hand-to-hand skill's name (GMST
sSkillHandtohand, written to `gfx/hud-settings.txt`) when unarmed. Composition
from files/data/mygui/openmw_windows.skin.xml (MW_Caption, HB_ALL) and
components/widgets/windowcaption.cpp (WindowCaption::align).

## Engine (aw_icons.c)

* A slot holds one picture (at most 32 x 32) and reloads only when its key
  changes: switching weapons or the selection reads the table once; drawing
  the same state reads nothing.
* Cost check: console `aw_magic stats` prints table lookups, picture reads, misses,
  draws, the resident slot bytes and the measured time per frame of the boxes
  for each method in the same session.
* `aw_hud_icons 0` selects the interim marks of v0.0.40 (a fist or sword mark
  and a dash); an image without the converted table also falls back to them.

## Boxes on screen

Every message box, tutorial box and notice goes through one pipeline. Nothing is placed by hand: a missing feature
is added to the pipeline once.

- **Showing a box.** Call `AW_MsgBoxShow(text, buttons, count)` with plain text; `count` 0 makes a timed notice. The
  game's text defines (`%PCName`, `^ActionActivate` and the rest) are filled in by the same call.
- **Line breaks and empty rows.** `\n` ends a line; `\n\n` leaves an empty row. Long lines wrap inside the box's
  inner margins. The frame is sized from the lines, empty rows included (`AW_MsgBoxLayout`).
- **The key column.** A tab in a line splits it: the part before the tab stands at the left inner margin, the part
  after it right-aligned at the right inner margin. Lines without a tab are centred.
- **Keys come from the bindings.** A hint never names a fixed letter. Inside the engine use
  `AW_TextBoundKeyForCommand("aw_inventory")` (a letter in upper case, the mouse buttons in words, `NULL` when
  nothing is bound) or the game's `^Action` defines. The game's own tutorial boxes are matched by the hash of their
  text in `config/tutorial-texts.json` (rendered into the engine by `tools/tutorial_texts.py render`), where
  `{key:COMMAND}` is the key bound now and `(not bound)` shows when none is. The inventory window's own keys are
  bindable too (`aw_key_inv_use`, default `E ENTER`; `aw_key_inv_drop`, default `D`; since v0.0.67
  `aw_key_inv_info`, default `P`, the item information box). A test fails on any new
  player-facing text in the engine that names a fixed key letter; `tests/key-hint-allowlist.json` lists the ones
  left to convert.
- **Clearance.** Inside the frame's 4-pixel edge, the text keeps at least 4 clear pixel rows above its first line and
  below its last, and at least one clear row between lines. `tests/aga_ui_clearance_test.c` renders the box layouts
  at the game's font size and measures them; a box that gets too tall rises over the view instead of cutting its text.
- **The house layout of a tutorial box.** One plain sentence of what you got; an empty row; one line per action with
  its key in parentheses in the right column (`Open it\t(I)`); an empty row; the `Ok` button centred and sized to its
  label. Lines stay within about 36 characters for the 320-pixel box. Keys go in parentheses: the game font's square
  brackets are ornaments, not brackets.

## The shared layout (v0.0.67)

Every menu, message box and HUD text is placed by one layout helper, `engine/aga/src/aw_layout.c`, never by pixel
positions of its own. A screen gives its box; `AW_LayoutBox` returns where the title row, the content and the buttons
go, and `AW_LayoutBoxHeight` gives the height a box needs for its content. Every number is in one table,
`aw_layout_metrics`: the frame's 4-pixel edge, 4 clear pixels inside it, 22-pixel buttons sized to their labels
(12 pixels each side, 48 at least) and centred with 8 pixels between them, and the button row 6 clear rows above
the frame's inner bottom edge, never against it.

- **Buttons.** The regular thick frame is the default; the thin outline stays selectable with the saved setting
  `aw_ui_button_frame 0`. A focused or hovered button shows the menus' dark gold bar under its label.
- **Dense lists.** Rows closer together than the game font's letters (the own class window's rows) use the console
  font.
- **Pick-ups.** Taking an item says what happened, "Picked up Bottle." or "Picked up 3 Bottle.", as the plants'
  harvest line does. The original game shows no message, only the sound: the saved setting `aw_pickup_message 0`.
- **Hints over a window.** A short notice without buttons over an open window (the dialogue window's "Continue the
  conversation first.") is `AW_UIHintBox`: centred in the window, as wide as its text needs, its frame and padding
  from `AW_LayoutBox` and `AW_LayoutBoxHeight`, its lines centred by their ink.
- **Letters of the console font.** Both console fonts have the printable ASCII characters only, while the game's
  texts use the Windows-1252 code page. A letter past them (an accented name, a curly quote) is drawn as its nearest
  ASCII character, an acute u as u and a right single quote as a straight one, through one 128-entry table
  (`AW_ConsoleTextGlyph`, `engine/aga/src/aw_console_glyphs.c`).
- **The check.** While a test records, everything `aw_ui.c` draws is kept: each box, button and line of text (a line
  by its painted pixels). `AW_LayoutCheck` reports a text or button that touches or leaves its box, a button closer
  than the bottom margin to its box's bottom edge, and two texts on top of one another, the HUD included, unless a
  box drawn between them covers the first. `tests/aga_ui_layout_test.c` proves the check catches each fault and
  measures the message boxes; `tests/aga_spelllist_windows_test.c` measures the character windows. A screen moved
  onto the helper gets its measurement in a test.

## One target under the crosshair (v0.0.67)

Only one thing has the focus in a frame, and it alone gets the title, the action line under it and the use key: the
nearest thing along the view ray within the activation distance among a person or creature (where the ray enters
their box), an item, container or plant, a load door and a hinged door. An item or plant inside a person's box counts
as before them (a body lying on the floor, an arm's reach), and a door behind a person is never aimed at. A thing that
had the focus keeps it while the new nearest is less than 4 units nearer, and a person whose animation moves their box
off the ray stays aimed for a quarter of a second, so the focus does not flip between two things from frame to frame.
The rule is `AW_FocusChoose` in `engine/aga/src/aw_activate_rules.c`, tested by number in
`tests/aga_activate_rules_test.c`.
