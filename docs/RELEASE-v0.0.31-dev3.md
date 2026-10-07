# AmiWind v0.0.31-dev3 - Revisiting Seyda Neen

Development build: everything in [dev2](RELEASE-v0.0.31-dev2.md), plus music
that waits for loading, place names in the location label, a light gallery for
trying night lighting live, and new console commands. Everything else is as in
[v0.0.30](RELEASE-v0.0.30.md).

## Music waits for loading

The opening scene on the prison ship now holds until the ship is loaded and
settled before its music starts, and the startup logo no longer starts the
title music; the main menu starts it once it is shown. Both crackled on slower
disks ([AUDIO-03](bugs/AUDIO-03.md), [AUDIO-LOGO-31](bugs/AUDIO-LOGO-31.md)).

## Place names

The location label names the place you are in from the original game's own
cell names: "Vvardenfell / West Gash Region / Balmora". Looked up once per
cell, so it costs nothing per frame.

## Night lighting, to try

- `dbg lightgallery` lists lighting switches in a strip below the view:
  night mode, night tint, lamps, glow, headlamp, horizon veil and a time
  preview (the saved clock is untouched). Up/Down chooses, Left/Right changes,
  Esc closes.
- `dbg night light 1` moves night darkness into the lighting instead of
  darkening the finished picture, so glowing materials and torches keep their
  colour after dark; `dbg night tint 0..100` sets how strongly the night tints
  the scene. Off by default.
- `dbg horizon veil 0..15` hazes the lowest sky bands into the far fog colour,
  so gaps in distant silhouettes read as haze
  ([HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md)). Off by default.
- Dark near-grey colours no longer turn rust-red at night
  ([NIGHT-RUST-31](bugs/NIGHT-RUST-31.md)).

## Console

- `dbg time` shows the in-game date and time; `dbg time HHMM` (or a named
  time such as `dbg time sunset`) jumps there. `dbg settime` is the same.
- `dbg 24hrcycle [seconds]` (or `dbg daytimecycle`) steps through a whole day,
  one game hour at a time, each shown for the given seconds (default 1).
- `dbg luma` shows the current indoor and outdoor light multipliers and how to
  set them (`dbg luma indoor` / `dbg luma outdoor`).
- All commands: [console commands](AMIWIND_CONSOLE_COMMANDS.md).

## Known in this build

- Street lamps in towns do not light their surroundings yet and lantern glass
  does not glow outside the Temple
  ([BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md),
  [EMISSIVE-UNSHIPPED-31](bugs/EMISSIVE-UNSHIPPED-31.md)); the plan is in
  [light sources](LIGHT_SOURCES.md).
- Distant town silhouettes can break up against the sky
  ([HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md)); try the horizon veil.
- Everything listed in the [dev2 notes](RELEASE-v0.0.31-dev2.md), the
  [dev1 notes](RELEASE-v0.0.31-dev1.md), the [v0.0.30 notes](RELEASE-v0.0.30.md)
  and the [bug register](BUGS.md).
