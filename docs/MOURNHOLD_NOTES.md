# Mournhold: observations on how Tribunal's city works

_Last updated with AmiWind v0.0.67 (19 November 2026)._

<!-- contents start -->
## Contents

- [The five districts are interior cells that behave like exteriors](#the-five-districts-are-interior-cells-that-behave-like-exteriors)
- [The water: a flag, no height, a surface at 0](#the-water-a-flag-no-height-a-surface-at-0)
- [How high the streets lie](#how-high-the-streets-lie)
- [Where the build puts the districts](#where-the-build-puts-the-districts)
- [Containers, items and activators in a district](#containers-items-and-activators-in-a-district)
- [The gates](#the-gates)
- [Arrivals](#arrivals)
- [What the expansions change in the base game](#what-the-expansions-change-in-the-base-game)
- [Every space of Tribunal and Bloodmoon in the image](#every-space-of-tribunal-and-bloodmoon-in-the-image)
- [What follows from this for a port](#what-follows-from-this-for-a-port)

<!-- contents end -->

This page collects what was measured and read about Mournhold while its five outdoor districts were brought into the
build: how Tribunal's data describes them, where the water is, how high the streets lie, where the build puts them, how
the gates between them work, and the faults found on the way. The numbers are from the Game of the Year files and from
a test build of 18 November 2026. Heights are in the original game's units unless a line says otherwise. The plan for
the expansions as a whole is in [The expansions: Tribunal and Bloodmoon](EXPANSIONS.md).

## The five districts are interior cells that behave like exteriors

Tribunal adds no outdoor grid cells for Mournhold. The city's open-air places are five **interior** cells:

| District | Cell name in the data | Placements |
| --- | --- | --- |
| Godsreach | `Mournhold, Godsreach` | 282 |
| The Great Bazaar | `Mournhold, Great Bazaar` | 315 |
| Plaza Brindisi Dorom | `Mournhold, Plaza Brindisi Dorom` | 187 |
| The Royal Palace courtyard | `Mournhold, Royal Palace: Courtyard` | 126 |
| The Temple courtyard | `Mournhold, Temple Courtyard` | 302 |

Each of the five carries the cell flags `0x87`:

- `0x01`: the cell is an interior;
- `0x02`: the cell has water;
- `0x04`: sleeping there is illegal;
- `0x80`: the cell behaves like an exterior: it has the sky, the weather of its region and the sun.

The base game has no cell with the last flag. A district has no terrain: everything a player stands on is a placed
model (the streets, the plazas, the canal walls). It has coordinates of its own, as every interior has, and the
districts are joined to one another and to the city's rooms by load doors only.

## The water: a flag, no height, a surface at 0

The five districts carry the water flag and **no water height**: the cell records hold neither of the two fields
that give an interior its water level. An interior's water level then keeps its default, 0. OpenMW reads the data the
same way (`components/esm3/loadcell.cpp`: the level starts at 0 and only a height field changes it;
`apps/openmw/mwworld/cell.cpp`: an interior has water when its flag says so) and draws a water surface at height 0 in
each district. What the original engine does with a flagged interior that has no height was not verified by running
it.

A surface at 0 fits the districts as they are built. The streets lie above it, and each district builds something
below it for the water to fill:

| District | Below 0 | Lowest surface measured |
| --- | --- | --- |
| Godsreach | the canal bed | -321 |
| The Great Bazaar | a sunken part in the eastern half | -106 |
| Plaza Brindisi Dorom | a sunken part in the western half | -46 |
| The Temple courtyard | sunken parts, most of them in the north-west cell | -146 |
| The Royal Palace courtyard | nothing: the courtyard is high above | 3695 (its floor) |

So Mournhold's water lies in the canal and in the sunken parts the districts build for it. No street is under water.

## How high the streets lie

Measured on the converted districts' own collision: a grid of points 256 units apart in each cell, traced straight down from above, the first surface met taken as what a player could stand on there. The
traces start below the tallest roofs, so "highest" is not a building's height.

| District, cell | Lowest | Middle | Under 0 (points) |
| --- | --- | --- | --- |
| Godsreach, south cell | 80 | 195 | 0 |
| Godsreach, north cell | -321 | 192 | 51 |
| Great Bazaar, west cell | 25 | 297 | 0 |
| Great Bazaar, east cell | -106 | 297 | 55 |
| Plaza Brindisi Dorom, west cell | -46 | 169 | 7 |
| Plaza Brindisi Dorom, east cell | 62 | 189 | 0 |
| Temple courtyard, south-west cell | -146 | 169 | 2 |
| Temple courtyard, north-west cell | -146 | 161 | 91 |
| Temple courtyard, south-east cell | -146 | 160 | 2 |

The floor under each district's arrival point (where a teleport by the district's name sets the player down):

| District | Floor under the arrival |
| --- | --- |
| Godsreach | 80 |
| The Great Bazaar | 297 |
| Plaza Brindisi Dorom | 178 |
| The Temple courtyard | 415 |
| The Royal Palace courtyard | 3695 |

Two things stand out. The Royal Palace courtyard lies about 3,500 units above the other four: in the original it is a
separate cell, so nothing ties its height to theirs. And outside the placed models a district has nothing at all:
a point that misses the streets and walls meets no ground, at any depth. Between half and nine tenths of the grid
points of a cell are such points (the cells are squares, the districts are not).

In some cells part of the tall traces could not be followed through the collision data (between 9 and 190 of about
1,000 points a cell); those points are left out of the table.

## Where the build puts the districts

The outdoor converter reads squares of exterior grid cells, so the build presents each district as a block of
exterior cells of its own (see [the expansions page](EXPANSIONS.md#mournhold)). The blocks stand in a row far south
of Vvardenfell, outside the area the base game's map covers, and apart from one another:

| District | Block | Grid cells | Frame maps |
| --- | --- | --- | --- |
| Godsreach | 1 by 2 | (-12,-30), (-12,-29) | `mh0000`, `mh0001` |
| The Great Bazaar | 2 by 1 | (-8,-30), (-7,-30) | `mh0002`, `mh0003` |
| Plaza Brindisi Dorom | 2 by 1 | (-4,-30), (-3,-30) | `mh0004`, `mh0005` |
| The Royal Palace courtyard | 1 by 1 | (0,-30) | `mh0006` |
| The Temple courtyard | 2 by 2 | (4,-30), (4,-29), (5,-30), (5,-29) | `mh0007` to `mh0010` |

These positions are the build's own: the original gives a district no place on the grid. They are chosen so that no
block touches a cell of the game's own grid, and they never show: Mournhold is not on the Vvardenfell map, its
districts are not joined to Vvardenfell's frames, and the world map keeps the player's marker where the trip began.
In the game the districts' maps take the numbers after Vvardenfell's and Solstheim's (7936 to 8191), so no existing
map number moves.

**Heights are not shifted.** A district is moved sideways by one offset for its whole block; its heights are the
original's. In a frame map one unit is four of the original's, so the Great Bazaar's street at 297 is at 74 in its
frame, and the water surface at 0 is at 0 in both.

Within a district the cells are open to each other: walking across the border between the Plaza's two cells was
checked in the game and passes. A district's outer edges are closed.

## Containers, items and activators in a district

A district's placed things are read from the game data by the same tables as everywhere else: the table of what can be
aimed at (containers, items, doors, named activators, people), the list of placed items that are drawn, and each
area's levelled creatures. These tables are keyed by area: a room by its number, an outdoor cell by its grid position.
The game asks for a room's rows indoors and for the cells around the player outdoors.

In the game data a district is a room, and in the build it is outdoors. The tables at first kept the district's rows
under its room number at the original positions, so the game, standing outdoors in a district, asked for the block's
cells and found nothing: no crate could be opened and no item taken in any of the five districts (register entry
`DISTRICT-PLACED-THINGS-NO-ROW-67`). The rows were all there, under a key nothing asked for:

| District | Rows | Containers | Items | Doors | Named activators | People |
| --- | --- | --- | --- | --- | --- | --- |
| Godsreach | 73 | 46 | 2 | 15 | 0 | 10 |
| The Great Bazaar | 136 | 62 | 46 | 9 | 0 | 19 |
| Plaza Brindisi Dorom | 47 | 26 | 0 | 4 | 2 | 15 |
| The Royal Palace courtyard | 48 | 37 | 0 | 8 | 0 | 3 |
| The Temple courtyard | 15 | 0 | 1 | 4 | 0 | 10 |

**The fix in the build.** When the districts are built, the three tables read a district's cell as the cells of its
block: each placement is moved by the district's one offset, the same move the district's world gets, and goes to the
grid cell it then stands in. The 319 rows are the same rows, now under the 11 cells of the blocks; every other area's
rows are unchanged, and a build of the base game alone writes the tables it wrote before. A check in the build's first
minute holds each district's rows, by count and kind, against the district's own cell in the game files, and against
the table sizes of the game. Whether a crate opens and an item can be taken in the game is checked on the next test
build.

No district holds a light that can be picked up, so nothing of a district needs the link between a taken light and
its flame.

## The gates

The districts are joined by gates, which are load doors: using one moves the player to the other district's side.
With the districts built, the image links 69 doors and markers that name a district, and holds none back.

| Gate | From | To |
| --- | --- | --- |
| reference 4211014 | the Royal Palace courtyard, south side | Plaza Brindisi Dorom |
| reference 4218703 | Plaza Brindisi Dorom | the Royal Palace courtyard |
| reference 4211013 | the Royal Palace courtyard, north side | the Temple courtyard |
| reference 4212322 | the Temple courtyard | the Royal Palace courtyard |
| reference 4218705 | Plaza Brindisi Dorom | the Great Bazaar |
| reference 4219376 | Godsreach | Plaza Brindisi Dorom |
| reference 4211017 (a door) | the Royal Palace courtyard | the Royal Palace: Reception Area, a room |

**A gate on a cell border.** Godsreach is presented as two cells, and its gate to the Plaza stands on the border
between them. A door belongs to the frame map of the cell that holds its position, and the use key looks for doors in
the frame the player stands in. A player in Godsreach's other cell, a step from the gate, therefore cannot use it
(register entry `DISTRICT-GATE-ON-CELL-BORDER-67`). The original never has this case: there the district is one
cell. The gate from the Plaza sets the player 6 units inside Godsreach's northern cell, and the gate's box reaches 19
units into that cell, while its row was only in the southern cell's table.

**The fix (v0.0.67, the image's door tables).** A district door whose box comes within the use key's reach of an
inner border of its block is also written into the table of the cell beside it: the same door, the same way through,
its box in that cell's coordinates. In the v0.0.67-dev3 image's tables that is 8 of the districts' 40 doors:
Godsreach's two gates (to the Plaza and to the Temple courtyard), the Great Bazaar's two gates (to the Plaza and to
the Temple courtyard), the Plaza's gate to the Royal Palace courtyard and its way down to Bamz-Amschend, and the
Temple courtyard's door into the Temple and its gate to the Royal Palace courtyard. Doors elsewhere in the game are
not touched: the base game's frames have no such blocks.

## Arrivals

A teleport by a district's name, a door from a room and a script that moves the player all set the player down at a
point taken from the original's data, moved by the district's offset. Checked in the game on the test build, by the
player's height:

| Arrival | Result |
| --- | --- |
| Godsreach, Plaza Brindisi Dorom, the Temple courtyard, the Royal Palace courtyard | standing on the floor |
| The Great Bazaar | **under the street** on the dev2 test build; on the top of the gate's wall above the street on the dev3 image; on the street with the fix below |
| The Royal Palace: Reception Area and the other rooms checked | standing on the floor |

**The Great Bazaar fault** (register entry `MOURNHOLD-BAZAAR-UNDER-WATER-67`). The teleport left the player at
about -173: 470 units under the street, which is at 297 there, and 173 under the water surface. The picture is the
underwater one and the breath bar runs, so the district looks flooded. It is not: the street is dry, and the player is
under it, in the place where a district has nothing to stand on. The water is right; the arrival is wrong.

**The cause, by number.** The arrival point itself is right. The gate from the Plaza (reference 24401 of Tribunal.esm)
sets the player at -503 -2578 at height 378 in the Bazaar's own coordinates. Moved by the district's offset, that is
23 units west of the border between the Bazaar's two cells, so it lies in the western cell's frame at frame-local 1018
-660. The gate from the Temple courtyard (reference 25213) is the same case, 24 units west of the border. The fault is
where the player is set down around that point. It lies 13 units north of the district's own gate to the Plaza, and
the player's standing box there overlaps that gate's wall from the street up. Traced on the build's own collision of
the district, with every part of it loaded:

- A teleport with a height looks for the first surface at or below it. With the box blocked at the asked height, the
  search stepped down until the box was clear. The first clear place was under the street's slab, about 140 under the
  street's top at 297, so the player fell through the empty space under the district onto the water surface at 0.
  That was the dev2 arrival under the water, not a floor that loaded late.
- The dev3 change caught such a landing (more than 256 under the asked height) and asked the arrival search for a
  floor at the asked point. That search tries the point and eight places 64 units around it, from a little above the
  asked height downward, and takes the first floor it meets. Its first floor was the flat top of the same gate wall,
  64 units east and higher than the asked height (490 by the game's own position command). The street lies 64 units
  north (364, which is 67 over the street at 297, as a player stands).

**The fix (v0.0.67, the teleport's arrival).** A teleport whose first landing is far under the asked height now asks
the arrival search at the asked point at once, and for this case alone that search takes a floor beside the point
that is higher than the asked height only when it finds no other floor. The original game sets the player at the
marker and lets him come down onto the floor under it, which never puts him on a wall top beside it. The Great
Bazaar's teleport now lands on the street, 64 units north of the point. A teleport that lands at its asked floor is
never touched, so the settlement teleports keep their arrivals, and doors, rooms and teleports to a person keep the
search as it was. Applied to every arrival, the same preference would have moved 58 of the 6,210 room arrivals of
the dev3 image (people in yurts set under their floor among them): there a floor a few units above the marker beside
it is common and right. Checked by number on the dev3 image's collision: every door and teleport into the five
districts lands where it landed before, except the two names of the Great Bazaar teleport, which now land on the
street. The doors from the Plaza and the Temple courtyard already stood on the street.

Two smaller findings from the same check:

- After several district arrivals in a row the player stood a few units away from the arrival point (Godsreach about 190
  units, the others about 40); cause unknown (`DISTRICT-ARRIVAL-DRIFT-67`, open).
- The districts draw slowly on the test build, 8 to 16 frames a second at the arrival points: their conversion
  recipe reduces almost nothing yet (`DISTRICT-FRAME-RATE-LOW-67`, open), and the Plaza's two cells are over the
  memory budget of a 16 MB machine (`CHIM-MOURNHOLD-PLAZA-OVER-16MB-67`, open).

## What the expansions change in the base game

Both expansions are in a build by default, so the base game is built with them. Each expansion's records were
compared, one by one, with the record of the same id before it (14 November 2026, the Game of the Year files):

| | Tribunal | Bloodmoon |
| --- | ---: | ---: |
| New records | 1,842 | 2,725 |
| Base-game records changed | 85 | 57 |
| Base-game records saved again unchanged (no effect) | 301 | 302 |
| Records deleted | 0 | 0 |
| New cells | 96 rooms | 155 outdoor cells, 98 rooms |
| Base-game cells given new placements | 4 (4 placements) | 4 (6 placements, 3 of them in a test cell) |
| Base-game placements changed, moved or deleted | 0 | 0 |
| Base-game cell headers changed | 7 (water heights) | 5 |
| Base-game topics with lines added or changed | 613 | 30 |
| Lines added to base-game topics | 2,148 | 1,652 |
| Base-game lines changed | 751 | 5 |
| New topics | 217 dialogue, 59 journal | 183 dialogue, 67 journal |
| New scripts | 251 | 324 |
| Base-game scripts changed | 11 | 3 |
| Scripts started with the game | 3 | 1 |
| New global variables | 33 | 37 |

What that is, in the base game's own places:

- **People placed in base-game cells.** Tribunal places Apelles Matius outdoors in Ebonheart and Asciene Rane in
  Ebonheart's Grand Council Chambers (the two who lead to Mournhold); Bloodmoon places S'virr in Khuul (the boat to
  Fort Frostmoth) and Louis Beauchamp in Ald'ruhn (the airship quest). Neither expansion changes, moves or deletes
  a placement of the base game.
- **Base-game records changed.** Tribunal: 33 creatures (their AI settings; the summoned creatures also get a sound
  source), 13 land textures (index numbers only), 11 scripts, 6 people (clothes, armour, AI settings), 6 activators
  (names), 5 sounds, 4 cuirasses, 3 game settings (the loading messages), 2 lights, 1 weapon, 1 enchantment.
  Bloodmoon: 37 weapons, 5 land textures, 4 lights, 3 scripts, 2 containers, and one each of creature, door, game
  setting, ingredient, magic effect and sound. Neither expansion changes a levelled list of the base game.
  Tribunal's script changes are small fixes and hooks: Tribunal's contracts count as legal Morag Tong kills, one journal
  name is corrected, one rank is raised, two sign scripts lose a reset.
- **Scripts that start with the game.** Tribunal's three: one starts the Dark Brotherhood attacks on a sleeping
  player (which lead to Apelles Matius, then to Asciene Rane and Mournhold), one watches for the later attack on
  Mournhold, one keeps the city's states. Bloodmoon's one starts its own state script.
- **Dialogue.** Most of the lines added to base-game topics are spoken by the expansions' own people or in their
  own places; 606 of Tribunal's can be spoken by anyone who meets their conditions, and 20 by base-game people.

What a build does with it (the test build of 18 November 2026, both expansions selected):

- Of the 43 build stages that take the game data, 36 are keyed by all three game files and read them through the one
  merging reader, the dialogue table, the scripts, the people and the rooms among them. Mournhold's two module
  stages are keyed by the base file and Tribunal's. Five are keyed by the base file alone: the setup, the music, the
  media, the progress tracker and the Vvardenfell outdoor world. The last is by design: the expansions add no object
  to Vvardenfell's outdoors, and the three people they place there come from the people tables, which read all
  three files.
- All 253 scripts of Tribunal and all 324 of Bloodmoon are compiled, the four start scripts are in the start list,
  and every new journal has all its stages (59 and 67).
- The 59 people and creatures in the base game's own cells whose records come from an expansion (the new people,
  and base-game creatures whose record an expansion changes) are all placed with a model, the four named above
  among them. The lines of the trip to Mournhold and back are in the dialogue table with their
  speakers, and both ends of the trip are rooms in the image.
- The base-game topics hold the expansions' lines: of the lines a player can hear in the base game, 101 of
  Tribunal's and 58 of Bloodmoon's were found in the table by their text, 16 and 14 were not and are being looked
  at one by one.

Known gaps for a base game with the expansions on:

- The people of Mournhold's five districts are placed: all 57 are in the district frame maps of the release build, still
  to be seen in play (`DISTRICT-PEOPLE-NOT-PLACED-67`). The rooms' people are placed.
- Some people's scripts were not attached to them (27 in Mournhold and 47 on Solstheim); since v0.0.67 the script stage
  binds them, to be seen in play (`EXPANSION-SCRIPTS-NOT-ATTACHED-66`).
- S'virr stands in Khuul and his boat to Fort Frostmoth is in the travel table since v0.0.68, with the boat from Fort
  Frostmoth back to Khuul.
- Whether the Dark Brotherhood attack plays (a sleeping player woken, the attackers placed beside him) has not
  been checked in the game yet; the sleep test the script waits on is fixed in source and `dbg dbattack` tests the path.

## Every space of Tribunal and Bloodmoon in the image

Every cell of every master is built, whatever leads there (decided for the project on 19 November 2026): a room no door
leads to is still in the game. Measured on the release build of 19 November 2026 (door graph, the image's room and
frame lists, every load door followed both ways, every script and dialogue result read):

- Tribunal has 96 interior cells. 89 are rooms on CHIM rooms. The five districts are open terrain in 11 frame maps
  (`mh0000` to `mh0010`), with all 57 of their people and creatures in those maps. The last two, "Sotha Sil," and
  "Mournhold, Royal Palace", hold no scenery in the game data (the second holds one person) and are built as empty
  rooms from this version on: a shell with no scenery around their references, the start in its middle, the person
  placed.
- Tribunal's cells hold 253 load doors: 250 lead both ways in the image, 3 are one-way in the original itself, and 3
  are being looked at.
- What moves the player into Tribunal's spaces without a door, each target a room or a district frame in the image:
  PositionCell in SothaSilTeleport (Sotha Sil, Outer Flooded Halls), mazedbandEnd_Script (Sotha Sil, Dome of Sotha
  Sil; Mournhold Temple: High Chapel; Vivec, High Fane), MHTransportScript (Mournhold, Royal Palace: Reception Area),
  karrodMovement (Mournhold, Royal Palace Throne Room; Mournhold, The Winged Guar), Warlord_aScript (Mournhold, Royal
  Palace: Jail), SadriThief, Shunari_Plague, the match-maker scripts (the districts and Mournhold, Trader),
  LorkhanHeart (Akulakhan's Chamber) and VVTransportScript (Ebonheart, Grand Council Chambers).
- No door, script or dialogue result moves the player into "Sotha Sil," or "Mournhold, Royal Palace". The only
  mentions are tests: TribunalMain asks GetPCCell "Sotha Sil,", and two dialogue lines carry a Not Cell condition on
  "Mournhold, Royal Palace". Both match by prefix, as the original: GetPCCell "Sotha Sil," is true in every Sotha Sil
  room, and those lines are said nowhere whose cell name starts with "Mournhold, Royal Palace". Each of the two is
  reached by its row in the `dbg tp` picker, which lists every room the image holds; no door is added.
- Bloodmoon's 98 interior cells are in the room list; 95 of its 233 load doors lead to Solstheim's outdoors, which are
  not in the game yet (the next version's work). "Vor Lair, Chambers of Alta Vor" and "Vor Lair, Interior" are unused
  Bloodmoon cells with no reference at all; they are built as empty rooms too, reached by their picker rows.
- The tracker counts all of them: a room is in the game when it is built and reached by its way in (a door, a script
  or dialogue result that moves the player, or the picker row); a district built as open terrain is in the game.

## What follows from this for a port

- A district needs a water surface at 0 although its cell names no height, and nothing else about it is "underwater".
- A district has no ground under its models. An arrival, a fall or a push that leaves the models ends in nothing, so
  every way of setting the player down has to end on a floor, checked by its height.
- The districts' heights are unrelated to each other; only the doors join them.
- Presenting one original cell as several grid cells creates inner borders the original does not have. Everything
  that is looked up by cell (doors, containers, people) has to work across them.
