# AmiWind v0.0.51: Let There Be More Inner Light

Released 25 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.50](RELEASE-v0.0.50.md);
development snapshots [v0.0.51-dev1](RELEASE-v0.0.51-dev1.md), [v0.0.51-dev2](RELEASE-v0.0.51-dev2.md) and
[v0.0.51-dev3](RELEASE-v0.0.51-dev3.md).

Akulakhan's Chamber, the last room of the main quest, loads on 32 MB and is lit as in the original. Every interior
of the game is baked again with the light the original gives it from above, which our rooms never had, so rooms that
live mostly on it are no longer dim. The music keeps playing through the CHIM world's loads, and the game's scripts
can enable, disable, lock and unlock objects and show message boxes (experimental, off by default).

## What changed since v0.0.50

- **Akulakhan's Chamber loads on 32 MB.** The engine takes spare Fast RAM as an extra cache for the CHIM world, but
  the first such bank needed 8 MiB beyond the margin left to the system; the v0.0.50 build left a 7 MiB budget on
  32 MB, so it took none, and the chamber's 10.1 MiB of models did not fit. The first bank now needs 4 MiB: 32 MB gets
  a 7 MiB bank, and on 32 MB Seyda Neen, Balmora and Vivec load with no "zone full" retry (567 with the v0.0.50
  engine on the same run) ([CHIM-AUTO-BANK-CLIFF-51](bugs/CHIM-AUTO-BANK-CLIFF-51.md),
  [CHIM-ROOM-HEART-CHAMBER-LOAD-50](bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)). A place the build marks for 32 MB is
  refused at its door when a start took no cache bank, instead of ending the game at its load. The engine smoke now
  fails any 32 MB run in which a CHIM chunk waited for room in the zone
  ([CHIM-ZONE-BUDGET-33](bugs/CHIM-ZONE-BUDGET-33.md)).
- **Interiors get their light from above.** Every interior cell of the game has a "sunlight" colour that the
  original lights the room with, as one directional light from a fixed direction; our rooms were baked without it,
  only with their ambient and lamps. 322 of the 1,335 interior cells have at least twice as much of it as ambient
  light, and Akulakhan's Chamber came out almost black. Every interior is baked again with it
  ([INTERIOR-SUNLIGHT-UNBAKED-51](bugs/INTERIOR-SUNLIGHT-UNBAKED-51.md)). The prison ship keeps the light it was
  judged with. The interior brightness default goes back to 1.0, the original light: the 1.2 default made up for the
  missing sunlight. Options > Video > Graphics and `dbg luma interior` still set 1.0 to 1.5, and a saved setting keeps
  its value ([interior lighting](INTERIOR_LIGHTING.md)).
- **The music through loads.** The CHIM world's reads (rooms, frames, models: up to megabytes in one read) now go in
  small slices with the music fed between them, as the other loads already did; on Balmora the longest pause in
  feeding the music fell from 205 ms to 46 ms. Every load prints one line, "Loading audio: ... longest gap ... late
  ...", naming the step of the load where the music waited longest; the intro movie, which pauses the music on
  purpose, is left out ([AUDIO-LOAD-29](bugs/AUDIO-LOAD-29.md)).
- **The game's scripts: object state and message boxes.** Scripts can enable and disable objects, lock and unlock
  them, and ask about both (`Enable`, `Disable`, `GetDisabled`, `Lock`, `Unlock`, `GetLocked`); a disabled object is
  hidden and not solid, and both are kept in saved games. A script that reads `OnActivate` takes over its door's use,
  and `Activate` hands it back, as in the original. `MessageBox` shows its text with its numbers formatted in; a box
  with buttons stops the world until the player chooses, and `GetButtonPressed` reads the choice once, as OpenMW does.
  EXPERIMENTAL, off by default (`dbg mwscript on`) ([the game's scripts](MWSCRIPT_BYTECODE.md)).
- **The Toolkit** shows v0.0.51 in the CHIM inclusion ledger, released with its readback and boot smoke
  (Toolkit 0.1.13).
- **Fewer console lines.** The fires of Seyda Neen no longer print "'aw_flame_light' is not a field" on every load.
- **Builds rebuild less.** An engine source edit no longer rebuilds the CHIM world
  ([BUILD-ENGINE-SOURCE-KEY-BROAD-36](bugs/BUILD-ENGINE-SOURCE-KEY-BROAD-36.md)), nor does a helper added to a shared
  module; stages that read nothing new are no longer rebuilt because of the file reads of their own cache keys; a
  change of what the cache keys count fails the tests until it raises the key form. The checks after the CHIM world
  is built use more of the machine (94 s instead of 116 s on the same world,
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md)).
- **The bug register.** Open bugs seen in three releases or more are listed with the reason each is not fixed yet; a
  "Waiting on" column; a new bug whose title nearly matches an open one is refused; the register files warn above
  75 % of the release text limit and fail above 95 % ([register rules](bugs/README.md)).

## Known in this build

- Everything in [v0.0.50's known items](RELEASE-v0.0.50.md#known-in-this-build) still applies, except Akulakhan's
  Chamber, which loads on 32 MB now.
- [CENSUS-OFFICE-BRIGHT-32](bugs/CENSUS-OFFICE-BRIGHT-32.md): the Census and Excise Office is brighter than the
  original; its own judged light, as the prison ship has, comes in v0.0.52.
- [INTERIOR-SUNLIGHT-COLOUR-51](bugs/INTERIOR-SUNLIGHT-COLOUR-51.md): the light from above is baked as brightness only, so Akulakhan's Chamber
  is lit grey where the original lights it red; v0.0.52.
- Doors into rooms read no lock from the game data yet; they wait for a way to open a lock
  ([DOOR-LOAD-LOCKS-MISSING-51](bugs/DOOR-LOAD-LOCKS-MISSING-51.md)).
- [BUILD-CUTOFF-WHOLE-ANCESTOR-51](bugs/BUILD-CUTOFF-WHOLE-ANCESTOR-51.md): a change to the room light reruns stages that do not read it; v0.0.52.
- Everything else is in the [bug register](BUGS.md).
