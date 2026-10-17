# HUD: weapon and magic boxes

Last updated with AmiWind v0.0.42-dev1.

<!-- contents start -->
## Contents

- [What the boxes show](#what-the-boxes-show)
- [How the boxes are made (builder)](#how-the-boxes-are-made-builder)
- [Inventory icons](#inventory-icons)
- [Window title bar](#window-title-bar)
- [Engine (aw_icons.c)](#engine-aw_iconsc)

<!-- contents end -->

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
