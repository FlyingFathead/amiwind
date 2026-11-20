# Look book page INVENTORY-HINT-PER-KIND

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67._

The inventory's key line names the right action for every kind of item.

## What the maintainer confirmed

The key line under the inventory says equip (or unequip when worn) for weapons, armour, clothing and lights, use for potions and scrolls, read for books, eat for ingredients, and never offers equip on an item that cannot be equipped.

- 2026-11-18, on v0.0.67-dev2: the maintainer's report of the regression: the equip hint had been fixed before and is missing again on items that can be equipped (EQUIP-ACTION-REGRESSION-62)

## How it is checked

A scripted session step of the look book (`tests/lookbook/inventory_hint_per_kind.txt`), run with every other page in one emulator session on every development build before it is delivered. Its numbers are the check; its pictures are compared with their references where it has them.

- picture `inv-weapon`: the inventory on a weapon
- picture `inv-worn`: the inventory on a worn piece of clothing
- picture `inv-potion`: the inventory on a potion

- the key line read back from the open inventory per item kind (a readout the inventory's key-hint repair adds)

Status: drafted, not run yet.

## The code it lives in

- `engine/aga/src/aw_worldui.c`: `inventory_equippable`, `inventory_usable`, `inventory_readable` (the inventory window and its key line)
- `engine/aga/src/aw_inventory.c`: `AW_InventoryCanEquip` (what can be equipped)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [AMIWIND_CONSOLE_COMMANDS.md](../AMIWIND_CONSOLE_COMMANDS.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [EQUIP-ACTION-REGRESSION-62](../bugs/EQUIP-ACTION-REGRESSION-62.md)

Some weapons, armour and clothing show no Equip action in the inventory (the census office dagger reads "Actions unavailable for this item"). State: open; found in v0.0.61.

- 2026-11-18 Guarded by the look book page INVENTORY-HINT-PER-KIND (docs/lookbook/INVENTORY-HINT-PER-KIND.md): The inventory's key line names the right action for every kind of item; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 fixed in source: a gated commit, v0.0.67-dev3 (6af03ce3) (gate 11602 of the planning item INVENTORY-EQUIP-HINTS-67)
- 2026-11-18 seen again on v0.0.67-dev2: Seen again on the v0.0.67-dev2 image (the maintainer's picture, 2026-11-18): the inventory does not show the "E/Enter equip" hint on every item that can be equipped.
- 2026-11-18 12:46 +0200 Cause of the v0.0.67-dev2 sighting found in the inventory window (engine/aga/src/aw_worldui.c): an action's result line ("Equipment updated.", a drop refused) replaced the key hint under the list for every item until the next action, so after one Equip no other item showed "E/Enter equip". The catalogue still gives every weapon, armour piece, clothing piece, ring, amulet and carried light its Equip action; arrows and bolts, lockpicks and probes, which the original also equips, never had it (INVENTORY-EQUIP-KINDS-NOT-YET-67). Fix on branch v0.0.67-invui: one action per item kind (aw_inventory.c

### [INVENTORY-EQUIPPED-LABEL-67](../bugs/INVENTORY-EQUIPPED-LABEL-67.md)

An item the player already wears or holds still shows "E/Enter equip" in the inventory, and nothing marks it as equipped. State: open; found in v0.0.67-dev2.

- 2026-11-18 Guarded by the look book page INVENTORY-HINT-PER-KIND (docs/lookbook/INVENTORY-HINT-PER-KIND.md): The inventory's key line names the right action for every kind of item; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 fixed in source: a gated commit, v0.0.67-dev3 (6af03ce3) (gate 11602 of the planning item INVENTORY-EQUIP-HINTS-67)
- 2026-11-18 12:46 +0200 Cause found: the key hint's word came from the item's class alone (equippable: "equip"), never from whether it is worn, and the only mark of a worn item was a "* " before its name. Fix on branch v0.0.67-invui: the hint reads "E/Enter unequip" for a worn or held item, and its row ends in "Equipped" in a highlight colour.
