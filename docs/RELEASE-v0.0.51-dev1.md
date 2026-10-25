# AmiWind v0.0.51-dev1 (in development)

Development snapshot, 24 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.50](RELEASE-v0.0.50.md).

v0.0.51 takes up the work moved from v0.0.50: the build fixes first, then the game's scripts and object state, the
actor sizes, Bloodmoon and the Morrowind-style UI ([roadmap](ROADMAP.md)). This snapshot is the first build of it.

## New since v0.0.50

- **Akulakhan's Chamber loads on 32 MB.** The engine takes spare Fast RAM as an extra cache for the CHIM world, but
  the first such bank needed 8 MiB beyond the margin left to the system; the v0.0.50 build left a 7 MiB budget on
  32 MB, so it took none, and the chamber's 10.1 MiB of models did not fit. The first bank now needs 4 MiB: 32 MB gets
  a 7 MiB bank, and on 32 MB Seyda Neen, Balmora and Vivec load with no "zone full" retry (567 with the v0.0.50
  engine on the same run) ([CHIM-AUTO-BANK-CLIFF-51](bugs/CHIM-AUTO-BANK-CLIFF-51.md),
  [CHIM-ROOM-HEART-CHAMBER-LOAD-50](bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)). A place the build marks for 32 MB is
  refused at its door when a start took no cache bank, instead of ending the game at its load.
- **The music through loads.** The CHIM world's reads (rooms, frames, models: up to megabytes in one read) now go
  in small slices with the music fed between them, as the other loads already did; on Balmora the longest pause in
  feeding the music fell from 205 ms to 46 ms. Every load prints one line, "Loading audio: ... longest gap ... late
  ...", so a load that starves the music shows in any emulator's log ([AUDIO-LOAD-29](BUGS.md)).
- **The game's scripts: object state.** Scripts can enable and disable objects, lock and unlock them, and ask about
  both (`Enable`, `Disable`, `GetDisabled`, `Lock`, `Unlock`, `GetLocked`); a disabled object is hidden and not solid,
  and both are kept in saved games. A script that reads `OnActivate` takes over its door's use, and `Activate` hands
  it back, as in the original. Doors that turn in place follow a script's lock. EXPERIMENTAL, off by default
  (`dbg mwscript on`) ([the game's scripts](MWSCRIPT_BYTECODE.md)).
- **Builds rebuild less.** An engine source edit no longer rebuilds the CHIM world (the stage keys named the whole
  engine folder: [BUILD-ENGINE-SOURCE-KEY-BROAD-36](bugs/BUILD-ENGINE-SOURCE-KEY-BROAD-36.md)), and a helper added to a
  shared module no longer does either. This snapshot rebuilds the CHIM world once, for the new keys.
- **The bug register.** Open bugs seen in three releases or more are listed with the reason each is not fixed yet
  (a missing system it waits for, the maintainer's deferral, or the release's work list); a "Waiting on" column; a
  new bug whose title nearly matches an open one is refused ([register rules](bugs/README.md)).

## Known in this build

- Everything in [v0.0.50's known items](RELEASE-v0.0.50.md#known-in-this-build) still applies, except the heart
  chamber, which loads on 32 MB now.
- Doors into rooms read no lock from the game data yet; they wait for a way to open a lock
  ([DOOR-LOAD-LOCKS-MISSING-51](BUGS.md)).
- Everything else is in the [bug register](BUGS.md).
