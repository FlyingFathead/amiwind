# Resting and waiting

_Last updated with AmiWind v0.0.67 (19 November 2026)._

<!-- contents start -->
## Contents

- [Rest or wait](#rest-or-wait)
- [Where you can sleep](#where-you-can-sleep)
- [Beds](#beds)
- [When the window will not open](#when-the-window-will-not-open)
- [What the hours do](#what-the-hours-do)
- [The level-up after a rest](#the-level-up-after-a-rest)
- [Interrupted in the wilderness](#interrupted-in-the-wilderness)
- [Rules followed and what is not in yet](#rules-followed-and-what-is-not-in-yet)

<!-- contents end -->

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

Seen in game on the v0.0.67-dev3 image (19 November 2026, 32 MB of Fast RAM in the emulator, the Bitter Coast, level 40,
walking): the T window opened as Rest, a 12-hour rest that ran its full length opened the level-up box, and a cut rest
did not (see [below](#interrupted-in-the-wilderness)). Not yet seen in game on a numbered build: Until Healed after
damage.

## What the hours do

Since v0.0.67 (fixed in source, still to be seen in play) the hours pass over the following frames, as in the original: about sixty hours a second, at least one
each frame, with the window showing how many have passed. No key stops them. While the hours of a rest pass, the
game's scripts see the player asleep (GetPCSleep), so the scripts that wait for a sleeping player run: the Dark
Brotherhood attack of Tribunal, the vampire and werewolf scripts of Bloodmoon, the dream lines of the main quest. A
script that wakes the player (WakeUpPC) stops the hours there: the hours already passed count, no level-up follows,
and an interruption planned for that rest still comes. Before v0.0.67 all the hours passed at once when Enter was
pressed, and a script never saw the player asleep.

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

Measured on the v0.0.67-dev3 image (19 November 2026, 32 MB of Fast RAM in the emulator, Bitter Coast, cell -2,-8): of
14 twelve-hour rests, 2 were cut, each after 9 hours (12 minus int(0.3 x 12) = 9), against the rule's chance of one in
four. A cut rest opened no level-up box and no creature was placed beside the player (the nearest wild creature, a
mudcrab, was about 1,550 units away) and no line was shown beyond the game's own
([REST-CUT-NO-CREATURE-67](bugs/REST-CUT-NO-CREATURE-67.md)).

Since v0.0.67 (fixed in source after that image, still to be seen in play) the creature comes too: when the rest
stops, one creature of the region's list, picked at your level by the game's rule for levelled lists, appears 220 units
in front of you (the next direction when that way is blocked), facing you, as the game makes it: its stats, its
behaviour (a hostile one attacks) and its script. The builder puts the 13 regions' lists (Vvardenfell's nine and
Solstheim's four) into the actor table; every one of the 133 creatures they can give has a model in the build. The
interrupted line is also written to the console log. The creature stays while the area is loaded; leaving the area or
loading a save does not bring it back, where the original keeps it in its cell.

### The roll

On the v0.0.67 release image (19 November 2026, 32 MB of Fast RAM in the emulator, one Bitter Coast spot, a fresh
session) 7 of 8 twelve-hour rests were cut after 9 hours, and the ninth rest of that session carried a planned cut
too: 8 of 9, where one in four gives that about once in 9,000 sessions. The rule, the cut hour and the settings in the
image (fSleepRandMod 0.25, fSleepRestMod 0.3) were right. The roll came from the C library's random number generator
(`rand()`), which nothing seeded: every boot started the generator from the same state. The generator itself is a good
one (the toolchain's newlib: a 64-bit state, and a remainder by 12 of its output cuts one time in four over any long
run), so the eight draws of that session cannot be explained by the generator's bits, and the log held no count of
draws to replay them.

Since v0.0.67 (in source after that image, still to be seen in play):

- the game's random numbers start from the machine's clock once a boot (the console's `Random: boot seed N` line), so
  a new session no longer repeats the last one's rolls; the first fight's dice (the per-encounter seed) and the
  scripts' Random start from it too. `aw_seed N` still sets the generator for a test, and `dbg combat seed N` a
  fight's dice;
- every roll that decides a game outcome (this one, alchemy, casting, persuasion, the dialogue's random choice,
  voice and idle picks, spell magnitudes, the scripts' random(), monster moves) takes its number from the generator's
  top bits, one draw each, as before, so the same rule holds whatever C library a build links;
- each rest that a sleep list can cut writes its roll to the console log, cut or not: a cut rest's line `rest: Your
  rest has been interrupted. (after 9 of 12 h, sleep list ex_bittercoast_sleep)` is followed by `rest: roll 1 of
  0..11, a cut below 3`, and a rest that runs its hours writes `rest: not interrupted (12 of 12 h, sleep list
  ex_bittercoast_sleep; roll 7 of 0..11, a cut below 3)`, so the cut rate of a session is counted from its log;
- a game recording and its replay still draw the same numbers: the recorder sets the generator every frame from the
  recording's own seed, and the scripts' Random from it at a load inside the recording.

## Rules followed and what is not in yet

The project follows OpenMW 0.51 where it settles a question the original leaves open: both refusals can show at once;
a level-up follows only a full rest; the interruption applies only outdoors.

Not in yet:

- the creature that interrupts a rest is not kept when you leave its area or load a save (the original keeps it);
- seen in play on an image of this release: the creature of a cut rest (on the v0.0.67-dev3 image a cut rest placed
  none, [REST-CUT-NO-CREATURE-67](bugs/REST-CUT-NO-CREATURE-67.md), open until then) and the Dark Brotherhood's attack
  in sleep, which starts Tribunal (on the v0.0.67-dev3 image four 1-hour rests and six 12-hour rests at level 40 on the
  Bitter Coast brought no attack, the game's attack counter stayed 0 against the script's own chance of 90 in 100 a
  sleep, [GETPCSLEEP-NOT-CARRIED-OUT-67](bugs/GETPCSLEEP-NOT-CARRIED-OUT-67.md), open until then; `dbg dbattack` makes
  its roll sure for one rest to test the path);
- the enemy check counts actors already fighting you; actors within the active area that would attack on sight but
  have not engaged yet are not counted until the aggression rule runs for every actor;
- NPCs do not yet walk on through the passed hours (they continue from where they stood);
- the trespass crime for a stranger's bed and werewolf form.

For testing, `dbg levelup rest [HOURS]` still passes the hours and opens a due level-up without the window, and
`dbg levelup bed REF` opens the window as the bed with that reference would (its ownership, Rest even in a town).
