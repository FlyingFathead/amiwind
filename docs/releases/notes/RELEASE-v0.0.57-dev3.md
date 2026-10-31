# AmiWind v0.0.57-dev3 (in development)

Development snapshot, 30 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.57-dev2](RELEASE-v0.0.57-dev2.md).

v0.0.57, "Remembering The Emperor", is dedicated to the memory of Sir Patrick Stewart (1940-2026), the voice of
Emperor Uriel Septim VII.

The third snapshot of v0.0.57: people walk with their feet on the ground, more of the world answers when used, and the
settlement list lands on dry land everywhere. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it.

## New since v0.0.57-dev2

- **Walking that matches the ground.** Wandering, chasing and fleeing characters now play their walk and run cycles by
  the distance they cover, so their feet no longer slide, with the original's speed limits. The animation table is read
  from disk as it is needed: about 90 KB stays in memory around Seyda Neen instead of about 600 KB.
- **Using things in the world.** Using a scripted object (an activator, book, item or container whose script waits for
  it) within the game's reach now runs its script, as doors and characters already did.
- **Temple cures.** Shrine and temple cures of common and blight diseases now remove those diseases.
- **The settlement list** sends every place without a door to dry land next to it (one place used to land in water).

## Known in this build

- Some settlement arrivals are higher or lower than the door they belong to, and a few places are slow right after
  arriving; found by the settlement sweep and being worked on.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
