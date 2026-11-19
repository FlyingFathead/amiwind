# The light test and the item tester (dbg lighttest, dbg cycleitems)

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

Two debug commands of every build, one tool. `dbg lighttest` takes the player to a long, dark corridor with nothing in
it, where a carried light is the only light and nothing is drawn over the view but the names of what the hands hold.
`dbg cycleitems` puts every item the player can hold in the hands in turn there, walks with it and uses it, and checks
that it stays in the hand. Neither changes anything in play, and neither keeps anything in memory while it does not
run.

## The light test corridor

`maps/lighttest.bsp` is in every image, made by the builder (`tools/build_lighttest.py`) like the torch test room: six
walls of the game palette's grid, about 4,000 units long and 190 wide, no source-game texture, no light of its own (every
light sample is zero), and nothing in it but the player's start at its west end. The torch test room (`dbg torchtest`,
[TORCH.md](TORCH.md)) stays as it was.

| Command | What it does |
|---|---|
| `dbg lighttest` | Into the corridor; alone again inside it, it says what the hands hold. |
| `dbg lighttest 1` | The same, then the walk: 20 seconds forward, the head straight for 10 seconds, down at the hands (45 degrees) from 10 to 15 seconds, back up to the end. Inside the corridor it starts again from the west end. |
| `dbg lighttest center` | Back to the west end, facing along the corridor, the head straight. |
| `dbg lighttest stop` | Ends the walk. |
| `dbg lighttest exit` or Ctrl+X | Back to the game where it was left. |

In the corridor:

- the game's scripts are paused, so no message box, tutorial notice or scripted event comes up (`aw_lighttest_scripts 1`
  lets them run there; they run again as soon as the corridor is left);
- nothing is drawn over the world: no HUD, crosshair, notice, subtitle, counter or debug text. The one line at the top
  left names what the hands hold, the left hand first, with each item's game name and id (for example
  `Glass Lantern (light_de_lantern_02)  +  Chitin Dagger (chitin dagger)`); it changes as soon as another item is held.
  The console, the menu and a window the player opens still show;
- the numbers go to the console only: a `LIGHTTEST held:` line when the held items change, and a `LIGHTTEST walk` line
  at the start and the end of a walk (the units walked and the seconds).

The game is captured on the way in, as the torch test does, and given back as it was on the way out.

## What the item tester goes through

The list is the holdable item index of the image (`inventory/holdable.txt`), made by the builder from the game's own
records of Morrowind, Tribunal and Bloodmoon ([INVENTORY.md](INVENTORY.md#every-item-the-hands-can-hold-the-holdable-index)):
every weapon (right hand, or both hands for a two-handed weapon, a bow or a crossbow), every shield and every carried
light (left hand), every lockpick and probe (right hand). Only in-game items: nothing is made up for the test.

For each item, in this order, from the corridor's west end:

1. the hands empty (whatever was held is put away), the hands raised;
2. the item in the hand or hands, equipped as the inventory's Equip does (one is given first when the player has none);
3. the walk of `dbg lighttest 1`: 20 seconds forward, looking down at the hands from 10 to 15 seconds;
4. its action where it has one: a weapon's attack (the attack key); a shield blocks by itself, a light is carried, and
   a lockpick or probe waits for lockpicking;
5. the item put away again (the test grant taken back), then the next item.

The grip is measured in every frame from the item in the hand to the end of its action: the distance from the item's
attach point on its hand's bone to the nearest vertex of that hand as it is drawn (the engine's held-item readout); a
grip over 2 units is off the hand. An item the inventory does not equip yet (today the lockpicks and probes) is named
and skipped.

## Running the item tester

Start or load a game, then in the console:

| Command | What it does |
|---|---|
| `dbg cycleitems` or `dbg cycleitems start` | Every item from the first, in the light test corridor. |
| `dbg cycleitems start N` or `dbg cycleitems from N` | From the Nth item of the index. |
| `dbg cycleitems kind KIND` | Only the items of one kind: `light`, `shield`, `short blade`, `bow`, and so on (the index's kinds). |
| `dbg cycleitems here [N]` | The same where the player stands, outside the corridor. |
| `dbg cycleitems status` | Which item it is on, and how many had the grip off the hand so far. |
| `dbg cycleitems stop` | Ends it: every key it pressed is released, and the corridor is left. |

An item takes about 24 seconds of game time (the walk is 20 of them). Run it at the emulator's warp speed for the whole
list; without warp for timings, pictures and clips. While it runs, the line at the top left says the item's game name,
its id, its number of the whole and the step (for example `Iron Dagger (chargen dagger)  3/632  walk`); it is in every
still and clip taken then, photo mode included, and never in normal play.

## What it writes

One console line per item, for example

    CYCLEITEMS 3/632 chargen dagger (short blade, right, shortbladeonehand): grip in the hand, worst 1.10 units
    (hold 1.02, walk 1.10, action 0.98) over 1430 frames

and at the end `CYCLEITEMS RESULT PASS 632 of 632 items checked, 0 with the grip off the hand; worst grip ...` (or
`FAIL` with the count). The confirmed look book's held-item page reads these lines.

## Not yet

- the grip number: until the engine's held-item readout measures it, each item's line says "grip not measured" and
  the run checks that every item is held, walked with and used;
- the grip number in third person, and the lockpicks' and probes' own action (the original's `pickprobe`).

Tests: `tests/test_cycleitems.py`, `tests/aga_cycleitems_test.c`, `tests/test_holdable_items.py`,
`tests/test_lighttest_room.py`.
