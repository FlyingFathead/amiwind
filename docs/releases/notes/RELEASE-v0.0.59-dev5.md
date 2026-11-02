# AmiWind v0.0.59-dev5 (in development)

Development snapshot, 2 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.58](RELEASE-v0.0.58.md).

The fifth snapshot of v0.0.59: everything of dev4 ([dev4 notes](RELEASE-v0.0.59-dev4.md)), and the player's body and
hands assembled from parts, a kit of every weapon type for testing, a weapon picture in the HUD for every weapon,
named sound events for the combat and creature sounds, a world change list that keeps more of what happens in the
world, and one shared conversion between map and game coordinates. The game needs 32 MB of Fast RAM, and the
emulator presets of this snapshot have it. This snapshot is for testing in game.

## New since dev4

- **The player's body from parts.** The third-person body is assembled from parts by equipment slot on the shared
  skeleton instead of being one baked model per race and sex, and the first-person arms are assembled from parts the
  same way. The parts share their vertices (bare arms went from 2,988 to 852 vertices); in a same-session measurement
  on the emulator at 32 MB Fast the arms from parts cost 0.34 to 0.38 ms per frame against 0.34 to 0.35 ms for the
  baked arms. The baked arms stay selectable (`dbg camera hands off`).
- **`dbg give weapons`.** A console command that gives one weapon of every type (short blade, long blade, blunt, axe,
  spear, bow with arrows, crossbow with bolts, thrown) and shields, and prints a table of each one's stats from the
  game's own records.
- **A weapon picture for every weapon.** The weapon box in the HUD shows a picture for every weapon.
- **Sound events.** 34 named sound events (weapon swings, hits, blocks, bow and crossbow, spells by school, falls and
  creature sounds among them) each play their mapped sound and can be triggered with `dbg sound`. The build report
  carries a coverage line that names every sound that is not mapped.
- **The world remembers more.** The world change list now also keeps open doors, locks, the stolen mark, the contents
  of containers and the faction ranks of NPCs across maps and saved games.
- **One conversion between map and game coordinates.** Script positions, lamps, weather, fog, the camera and the other
  engine parts that need a place in the game world find it on every map, the streamed towns included.

## Fixed since dev4

- The weapon box in the HUD stayed empty for every weapon outside the starting set: the builder made HUD pictures
  only for those (HUD-WEAPON-BOX-EMPTY-59).
- On the streamed towns the conversion to the game's coordinates found no place for most engine parts
  (CHIM-FRAME-SOURCE-CONVERSION-59).

## Known in this build

- The inventory preview draws the baked body of the race with its own outfit, not what the player wears
  (INVENTORY-PREVIEW-BAKED-BODY-59 in the [bug register](../../BUGS.md)).
- Journal stages, script values, topics learned and dispositions are not yet kept across saved games
  ([MWSCRIPT-STATE-NOT-SAVED-48](../../bugs/MWSCRIPT-STATE-NOT-SAVED-48.md)); this is in progress as the next part of
  the world change list.
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- The body and arms from parts on the Pi 4B and on a 68040.
- The creature sounds (roar, scream) in a scene with a creature, and the sound events on the WinUAE image.
- NPC faction ranks changed by a script (tested in the build; the open doors, locks, stolen marks and container
  contents were checked in game across a map change and a saved game on FS-UAE).
