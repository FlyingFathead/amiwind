# AmiWind v0.0.58-dev4 (in development)

Development snapshot, 1 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The fourth snapshot of v0.0.58, "Time To Talk". The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What the earlier snapshots brought is in the [dev3 notes](RELEASE-v0.0.58-dev3.md), the
[dev2 notes](RELEASE-v0.0.58-dev2.md) and the [dev1 notes](RELEASE-v0.0.58-dev1.md). This snapshot is for testing in
game; the new parts below have only partly been checked in game yet (see the last section).

## New since dev3

- **The aim box.** Aiming at something within reach shows a framed box. For an item it holds the name, the weight and
  the value, and the name is red when the item is owned. For a person it shows the name, and a door shows its name or,
  when it leads outside, the place it leads to. It works in rooms and outdoors: a builder stage lists every placed
  item, person and door of each room and each outdoor cell. In a room the box shows only items the room draws.
- **Placed items can be picked up.** E on an aimed item that the room draws as an object takes it into the
  inventory, and the taking is kept in the saved object state. The Census and Excise Office's small items are not in
  this build: as placed objects they made the office map hold more models than the engine allows, so they wait for a
  lighter way in.
- **The greeting is picked at talk time**, and the spoken greeting follows the one picked. The known topics follow the
  saved set.
- **Faction rank in dialogue.** Rank requirements come from the factions' rank tables, and the rank difference is read
  from the player's own rank.
- **Dialogue conditions and disposition.** Same sex, same race and "should attack" are read live; disease, a drawn
  weapon and the Charm effect count in the disposition.
- **Character creation.** The class page is a scrolled, clickable list with the class's specialization, favoured
  attributes and major and minor skills beside it. The birthsign page lists the signs with the sign's abilities,
  powers and spells by name. The review sheet shows name, level, race, class, sign, health, magicka and fatigue. The
  class questions of the install's `Morrowind.ini` run through a stage of their own, and the player can make a class
  of their own.
- **The creature sound test no longer stops.** The vanity camera never starts while the combat playground or an Arena
  fight runs, so the sounds mode of the playground keeps playing the full set of a creature.
- **Combat sounds on by default.** The swing, armour, miss and punch sounds play as OpenMW plays them; the player's own
  footsteps stay their own setting, off.
- **Seyda Neen.** The wedge-shaped gap in the shore wall is closed: flora cards push back in depth only on the card's
  bottom quarter, the trunk base.
- **Toolkit build monitor.** A build whose stages passed and whose only failed step is the performance check shows as
  "passed, perf guard failed". One overall progress bar shows the percentage and the expected finish, a machine view
  lists gates, tests and pregates with the cores they use, and the timeline has boxes for cores used and memory used.
- **Builds.** The build report gives the voice coverage (people voiced, creatures with sounds, named ones unmapped).

## Known in this build

- The back-room table of the Census and Excise Office is not drawn, so the dagger on it is not seen
  (CENSUS-BACK-TABLE-NOT-DRAWN-58, open in the [register](../../BUGS.md)).
- The aim box measures the reach to an item's origin, not to its nearer surface as the original does
  (FOCUS-REACH-ITEM-ORIGIN-58, open in the [register](../../BUGS.md)).
- A build's performance check can fail on loaded machines when other builds run beside it
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- The netch bull's reduced model loses a stretch of one leg
  (CREATURE-NETCH-BULL-LEG-REDUCED-58, open in the [register](../../BUGS.md)).
- Casting the spells you make, and using items you enchant, wait for player casting (a later version).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Picking up a placed item and keeping it taken across a save and a reload.
- The aim box outdoors, and for people and doors.
- The greeting picked at talk time, the known topics, the faction rank checks and the new dialogue conditions.
- The birthsign page, the class questions and the player's own class of character creation.
- The Seyda Neen shore wall after the depth change.
