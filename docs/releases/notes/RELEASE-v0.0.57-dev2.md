# AmiWind v0.0.57-dev2 (in development)

Development snapshot, 30 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.57-dev1](RELEASE-v0.0.57-dev1.md).

v0.0.57, "Remembering The Emperor", is dedicated to the memory of Sir Patrick Stewart (1940-2026), the voice of
Emperor Uriel Septim VII.

The second snapshot of v0.0.57: the people and creatures of Vvardenfell start to move, more of the game's own scripts
run, the Ashlander camps and central Ald'ruhn are lighter to draw, and a settlement list makes testing the whole island
quick. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.57-dev1

- **Creatures and people move.** Creatures and residents wander and idle by their own records, including the creatures
  that come from levelled lists (about 6,000 of the outdoor ones stood still before). Hostile creatures turn on the player
  within their fight distance, and flying creatures such as cliff racers fly instead of standing on the ground. The
  wander table is read from disk; only a small index stays in memory.
- **More of the game's scripts run**: crime level, reputation, faction rank and expulsion, faction reputation, race
  checks, scripted animations (PlayGroup, LoopGroup), new dialogue topics (AddTopic), and using an actor whose script
  waits for it (OnActivate). The player's standing and known topics are kept in saved games.
- **Guards carry torches at night**: the guards that carry one in the original light it in the dark hours and in ash
  and blight storms, with the original's light reach.
- **Lighter camps and Ald'ruhn**: the Ashlander yurts and camp props and the buildings of central Ald'ruhn have fewer
  faces, with a check that keeps the edges where their parts meet closed.
- **Smoother busy views**: the texture surface cache was a quarter of what busy views need, so they redrew their
  lit surfaces every frame; it now holds them (in the prison ship's hold and around Seyda Neen the surfaces redrawn per
  frame dropped from several hundred to none, and the drawing time from about 10 ms to 3 to 6 ms). It costs 1.5 MB of
  Fast RAM beside the game heap, and a machine short of it falls back to the old size.
- **A settlement list for `dbg tp`**: `dbg tp` with no place name opens a searchable list of the 82 named places of
  Vvardenfell in the console font, over the game, and takes you to the one you choose
  ([console commands](../../AMIWIND_CONSOLE_COMMANDS.md)). The list is read from disk only while it is open.
- **Toolkit**: the server keeps running through a passing shortage of network buffers on a busy machine.

## Known in this build

- Some settlement arrivals are too high or too low, and a few places are slow right after arriving; found by the new
  settlement sweep and being worked on.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
