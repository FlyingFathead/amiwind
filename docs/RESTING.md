# Resting and waiting

_Last updated with AmiWind v0.0.61-dev3 (2026-11-06)._

Since v0.0.59 the T key and the game's beds work as in the original game. The rules are the original's, written
independently; the OpenMW engine (0.51) is the reference used to check them. Every number and every line on screen
comes from your own game files when the image is built (`levelup/rest.txt`, written by `tools/prepare_levelup.py`).
The rules themselves are in `engine/aga/src/aw_rest_rules.c`, the window in `engine/aga/src/aw_wait.c`.

## Rest or wait

The T window lets you pass 1 to 24 hours (arrow keys, Enter). It opens in one of two modes:

- **Rest** where you may sleep. Health, magicka and fatigue come back over the hours, a wilderness rest can be cut
  short, and a level-up that is due follows a rest. When health or magicka is below full, **Until Healed** (H)
  rests exactly as long as it takes to fill both.
- **Wait** where sleeping is not allowed. The window shows the game's line that resting here is illegal. Only the
  hours pass: fatigue comes back, health and magicka do not, and no level-up follows.

## Where you can sleep

Each cell of the game says whether sleeping without a bed is allowed. Towns are marked: the town cells of Seyda Neen,
Balmora, Pelagiad, the Vivec cantons and the other settlements give Wait, while the outskirts around them and the
wilderness give Rest. Most interiors with an owner (shops, houses, inns, temples, guild halls) give Wait; caves,
tombs, ruins and mines give Rest. The mark is read per cell, never per town name.

## Beds

Using a bed runs the bed's own script, which opens the window with that bed. A bed you may use always gives Rest,
even inside a cell where sleeping is otherwise not allowed:

- an unowned bed, or your own;
- a bed in a room you rented (the innkeeper's rent sets a game variable named on the bed for the rest of that day);
- a guild bed, when you are a member at the rank the bed asks for.

A bed that belongs to someone else does not open the window: the game's line says it is not your bed. (Using it is a
trespass in the original; the crime itself comes with the crime rules.) A bed also lets you rest where the ground is
uneven, but not in water or with enemies near.

## When the window will not open

- On water or in it, in the air (jumping, falling, levitating, flying): the game's line that you can only rest on
  solid ground. A bed lifts the air rule, not the water rule.
- With enemies near: the game's line that you cannot rest with enemies nearby. Both lines can show together.
- Before your character is registered at the Census Office: nothing opens.
- In a cell where sleeping is illegal, among them the Census and Excise Office itself (since v0.0.61-dev3): the
  game's line, and the window offers Wait only.

Not yet seen in game on a numbered build: Until Healed after damage and the interruption of a rest in the wilderness.

## What the hours do

Hour by hour the clock moves, and with it the sky and the weather, the magic items recharge and your spell effects
run out as they would over that time. After the hours, by the game's settings:

| | Rest | Wait |
| --- | --- | --- |
| Health per hour | a tenth of Endurance | nothing |
| Magicka per hour | fRestMagicMult (0.15) x Intelligence; nothing under stunted magicka (the Atronach) | nothing |
| Fatigue per hour | (fFatigueReturnBase + fFatigueReturnMult x (1 - load)) x fEndFatigueMult x Endurance x 3600, which in practice fills it within an hour | the same |

Load is what you carry over what you can carry (fEncumbranceStrMult x Strength). A fatigue raised above its maximum by
an effect is left as it is. Each stat stops at its maximum.

## The level-up after a rest

When a level-up is due (see [Levelling](CHARACTER_CREATION.md#levelling)), the level-up box opens after a rest that
ran its full length. A wait never opens it, and neither does a rest cut short: the level-up stays due for the next
full rest.

## Interrupted in the wilderness

A rest outdoors, in a region that has a list of creatures that disturb sleepers (the Bitter Coast, the Ascadian Isles,
the West Gash, the Ashlands, Red Mountain and others), can be cut short. When the rest starts, a die with as many
faces as hours is rolled; a roll under fSleepRandMod (0.25) x the hours means the rest stops after the hours minus
int(fSleepRestMod (0.3) x the hours), with the game's line that your rest has been interrupted. Rests of three hours
or less are never interrupted; an eight-hour rest is cut after six hours one time in four. Interiors and towns are
never interrupted this way.

## Rules followed and what is not in yet

The project follows OpenMW 0.51 where it settles a question the original leaves open: both refusals can show at once;
a level-up follows only a full rest; the interruption applies only outdoors.

Not in yet:

- the creature that interrupts a rest (one from the region's list, placed next to you) waits for creatures placed
  from a levelled list; the rest stops, nobody appears yet;
- the enemy check counts actors already fighting you; actors within the active area that would attack on sight but
  have not engaged yet are not counted until the aggression rule runs for every actor;
- NPCs do not yet walk on through the passed hours (they continue from where they stood);
- the trespass crime for a stranger's bed, werewolf form, and the game's scripted dreams and ambushes.

For testing, `dbg levelup rest [HOURS]` still passes the hours and opens a due level-up without the window, and
`dbg levelup bed REF` opens the window as the bed with that reference would (its ownership, Rest even in a town).
