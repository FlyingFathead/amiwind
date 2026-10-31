# AmiWind v0.0.57-dev5 (in development)

Development snapshot, 30 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.57-dev4](RELEASE-v0.0.57-dev4.md).

v0.0.57, "Remembering The Emperor", is dedicated to the memory of Sir Patrick Stewart (1940-2026), the voice of
Emperor Uriel Septim VII.

The fifth snapshot of v0.0.57: every character in town animates, creatures attack with their own moves, the sky
fades into the fog, characters can travel and follow by script, and the dialogue system's tables are in the image.
The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.57-dev4

- **Every character animates.** Characters whose models were read by the general model loader stood still; they now
  walk, run and fight like the rest (in Seyda Neen no character is left without animation).
- **Creature attacks**: a creature with its own animation table picks one of its own attacks each time, and
  swimmers use their swimming attacks.
- **The sky fades into the fog** as the draw distance shortens, so a short view no longer shows a hard band of open
  sky above the fog. It costs nothing per pixel: the fade is part of the sky tables.
- **More of the game's scripts run**: characters can be sent to travel to a point or to follow someone (AITravel,
  AIFollow), scripts can move and turn the player and objects (Position, Rotate) and ask whether the player stands on
  something (GetStandingPC). 957 of the game's 1,207 scripts now run whole.
- **Saves** keep which room each changed character is in and the characters' travel and follow orders.
- **Quicksave** says why it did nothing when no character profile is chosen.
- **dbg tp balmora** puts the player on the street outside a door, not on a roof edge.
- **Dialogue groundwork**: the image now carries the game's dialogue as a table on disk (only a 25 KB index stays in
  memory), and the engine picks the first matching answer the way the original does. The conversation window comes
  in a later snapshot.

## Known in this build

- A rare crash on arrival at Gnisis ([SPRITE-BAD-TYPE-THREADED-56](../../bugs/SPRITE-BAD-TYPE-THREADED-56.md)), being
  worked on.
- A few places are slow right after arriving.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
