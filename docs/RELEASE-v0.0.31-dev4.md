# AmiWind v0.0.31-dev4 - Revisiting Seyda Neen

Development build: everything in [dev3](RELEASE-v0.0.31-dev3.md) with its
music start-up fixed, a quicker opening that fades in, and the AmiWind Toolkit
reorganised. Everything else is as in [v0.0.30](RELEASE-v0.0.30.md).

## Music

- dev3 played a random soundtrack piece under the startup logo. Start-up is now
  silent until the main menu starts the title music
  ([MUSIC-STARTUP-TRACK-31](bugs/MUSIC-STARTUP-TRACK-31.md)). Start-up also
  opens only one track instead of two, the likely source of the old start-up
  crackle.
- dev3 played a clip of the title music while the prison ship loaded. The
  opening now stops and empties the music until its own track starts
  ([MUSIC-OPENING-CLIP-31](bugs/MUSIC-OPENING-CLIP-31.md)).

## Opening

The wait between the intro video and the ship is shorter (the scene settles for
a quarter of a second instead of three quarters), and the ship fades in from
black over a second and a half, through the palette, so it costs nothing to
draw.

## Night light on by default

Outdoors at night the whole finished picture used to be darkened at the end,
torch light included, so torches barely lit town walls
([DLIGHT-WALLS-31](bugs/DLIGHT-WALLS-31.md)). The light-space night from dev3
is now the default: the night darkens the light itself, and torches and
glowing materials keep theirs. Measured at a Balmora wall: the headlamp lifts
it about 2.5 times more, with the night just as dark without it.
`dbg lightgallery` (Night: remap / light) or `dbg night light 0` switch back to
the old look for comparison.

## AmiWind Toolkit

World, Local and 3D Inspector are now three tabs, and the inspector has the
whole window. Grid on/off buttons on the map, a highlighted marker with its name
under the mouse, arrow keys or WASD to pan, and a "Please load a map" hint in
the empty inspector. See [AmiWind Toolkit](AMIWIND_TOOLKIT.md).

## Known in this build

- Street lamps do not light their surroundings yet
  ([BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md)); torches light the
  ground outdoors but not walls ([DLIGHT-WALLS-31](bugs/DLIGHT-WALLS-31.md)).
- Everything listed in the [dev3 notes](RELEASE-v0.0.31-dev3.md) and the
  [bug register](BUGS.md).
