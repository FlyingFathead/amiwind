# AmiWind v0.0.31-dev6 - Lamps, Lanterns and Loading

Development build: everything in [dev5](RELEASE-v0.0.31-dev5.md), with steadier
night lamps, a fog distance slider and a fogged skyline. Every map is identical
to dev5.

## Night lamps

- Lamps no longer switch on and off while you turn or walk: a lit lamp keeps
  its light unless another lamp is clearly nearer, and a lamp that loses its
  light fades out instead of snapping off
  ([LAMPS-FLICKER-31](bugs/LAMPS-FLICKER-31.md)).
- `dbg lamps` also prints each part of the night test (exterior, daylight,
  guard night), to pin down lamps that stay dark
  ([NIGHT-0400-DARK-31](bugs/NIGHT-0400-DARK-31.md)).

## Fog distance

- Options > Fog distance opens a slider: drag it, use the arrows (Shift: steps
  of 1) or type a number; 100 to 1500 (`dbg fog distance` takes the same range).
  A short fog distance is the biggest frame-rate setting in towns.
- Skyline fill: sky that shows below distant scenery takes the fog colour, so
  a short fog distance leaves a fogged skyline instead of cut-outs
  (`aw_skyline_fill`, default on).
- Location fog: places can set their own day and night fog distance
  (`id1/world/fog-locations.txt`; Balmora 300 by day, 250 by night). Off by
  default; `dbg fog location 1` turns it on.

## Known in this build

- Town buildings, interior rooms and rocks do not block Quake's visibility
  data, so hidden buildings and NPCs are still drawn
  ([TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md),
  [Town visibility](performance/TOWN-VISIBILITY.md)). The repair (static
  building faces in the world model plus occluders) is being prototyped.
- Distant buildings beyond the fog distance are not drawn at all, so their
  skyline appears only as you come closer.
- Everything listed in the [dev5 notes](RELEASE-v0.0.31-dev5.md) and the
  [bug register](BUGS.md).
