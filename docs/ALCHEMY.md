# Alchemy

_Last updated with AmiWind v0.0.62-dev1 (2026-11-07)._

Since v0.0.62 alchemy works as in the original game: potions are drunk, ingredients are eaten, and a mortar and pestle
(or any other piece of apparatus) opens the alchemy window, where up to four ingredients make a potion. The rules are
the original's, written independently; the OpenMW engine (0.51) is the reference used to check them
(`apps/openmw/mwmechanics/alchemy.cpp`, `spellutil.cpp` and `spellcasting.cpp`). Every number and every line on screen
comes from your own game files when the image is built. The rules are in `engine/aga/src/aw_alchemy_rules.c`, the
window, the drink and the meal in `engine/aga/src/aw_alchemy.c`, the data in `tools/prepare_alchemy.py`.

## Using items from the inventory

Select a potion, an ingredient or a piece of apparatus in the inventory window and press E or Enter, or right-click
it and choose **Drink**, **Eat** or **Use**:

- **A potion** is used up and all of its effects land on you at once, whatever range the record names. They run
  through the same active effects as spells (`docs/MAGIC_EFFECTS.md` "Active effects"): a Restore effect works each
  second it lasts, a Fortify raises the stat until it ends.
- **An ingredient** is used up. Only its first effect can take hold, and only when a roll against your Alchemy skill,
  Intelligence, Luck and fatigue allows it; its strength and length grow with that skill. When it takes hold your
  Alchemy skill gets a use; when it does not, the game's own line says that the ingredient has no effect on you.
- **Apparatus** opens the alchemy window (the inventory window closes first).

## The alchemy window

- **Apparatus**: the best piece you carry of each kind (mortar and pestle, alembic, calcinator, retort), by quality.
  The mortar and pestle is needed to make anything.
- **Ingredients**: four slots. Up/Down choose an ingredient from the list on the right, Enter (or a click) puts it in
  the next free slot, 1 to 4 (or a click on a slot) take one out again. Each ingredient only once.
- **What your skill reveals**: under the list, the selected ingredient's effects; one more of its four effects shows
  for every 15 points of Alchemy (the game's `fWortChanceValue`), the rest show as "?".
- **Effects**: the potion the slots would make. Every effect that at least two of the ingredients share, in slot order,
  with its magnitude and duration; the first two show from 15 Alchemy, two more at 30, 45 and 60.
  A made potion shows the picture of the game's potion whose bottle it has.
- **Name**: the potion is named after its first effect.
- **Create** (C or the button): makes one potion. The ingredients are used up whether it works or not.

### How strong the potion is

As the original: the alchemy value is your Alchemy skill plus a tenth of Intelligence and a tenth of Luck, times the
mortar's quality, times the game's potion strength setting. Each effect's magnitude and duration come from that value
and the effect's base cost; a retort strengthens a helpful effect, an alembic weakens a harmful one, a calcinator adds
to both. An effect too weak to last is dropped. The potion's value follows the same alchemy value, its weight is the
average of the ingredients'. Create succeeds when a roll of 0 to 99 is not above your Alchemy skill plus a tenth of
Intelligence and a tenth of Luck; a success gives an Alchemy skill use, a failure says "Your potion failed."

A potion made before with the same name, effects, weight and value is made again as the same item (as the original
does); a new one gets one of the six bottles of the game's potions at random.

## Data and cost

- An ingredient's four effects, a potion's effects and an apparatus' quality are written into the item's own row of the
  item catalogue (`inventory/items.awi`, bytes 440 to 495 of a 512-byte row, in place of the weapon and armour numbers
  such a row does not use; flag 64). Reading the item reads them: no file of its own, no extra disk read when an item is
  used.
- `alchemy/settings.txt` (about 1 KB): the five game settings, the game's lines, the four sounds (Drink, Swallow,
  potion success, potion fail, in `sound/alchemy/`) and the bottle looks. Read when the window opens and freed when it
  closes; read once for a drink or a meal and freed.
- Resident memory: none while the window is closed, beyond about 60 bytes of counters. Every item record kept in
  memory is 54 bytes larger (the alchemy numbers; 582 bytes a record in the Amiga engine): up to about 14 KB more when
  the item records cache (256 records) is full. While the window is open: its state and the game's lines (about
  3 KB) and about 60 bytes per kind of ingredient carried (4,952 bytes in all with four kinds).
- Measured on FS-UAE at 32 MB Fast (68040 preset with JIT, v0.0.62-dev1 MiniWind of Seyda Neen, engine of gate 8222):
  the window opens in 52 to 64 ms (it reads the carried items' records as the inventory window does); Create takes 104
  to 269 ms (the roll, the made potion and the list read again); a drink or a meal 18 to 21 ms. Nothing runs while
  the window is closed; it draws only 2D text and fills, no models.
- A made potion is kept with the enchanted items you made (64 at most together) and saved with them; no new save
  block. A potion made again with the same name, effects, weight and value is the same item (the second of two
  identical potions in the measured session was).

## Test words

`aw_inventory use "ID"` drinks, eats or opens the window as the inventory's E does (the item must be carried).
With the window open: `aw_inventory alchemy add "ID"`, `aw_inventory alchemy remove N`, `aw_inventory alchemy create`,
`aw_inventory alchemy close`; `aw_inventory alchemy status` prints the apparatus, the slots, every effect (also those
the skill does not reveal), the counts of drinks, meals and potions made.

## Not yet

- Several potions at once (the original's count field); the potion's name cannot be typed yet.
- Ingredient and apparatus pictures in the window (the list is text).
- Non-player characters do not drink potions.
