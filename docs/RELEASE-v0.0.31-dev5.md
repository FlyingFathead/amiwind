# AmiWind v0.0.31-dev5 - Lamps, Lanterns and Loading

Development build: everything in [dev4](RELEASE-v0.0.31-dev4.md), with lit
streets at night. Every map is identical to dev4.

## Lamps and lanterns at night

- Street lamps, lanterns, wall torches and fires give a torch's worth of light
  at night: pools of light with darker street between
  (`dbg outdoorlantern 0.25..3.0`, default 1.0; 2.0 lights whole streets).
  They burn whenever the sky is dimmed, as in the original game, where lamps
  never switch off.
- Only a few lamps can be lit at once (dynamic lights cost time every frame).
  Lamps ahead of you now win over lamps behind you, and a newly lit lamp grows
  to full light instead of popping on
  ([LAMPS-RANGE-31](bugs/LAMPS-RANGE-31.md)).
- Lantern glass and window glass glow at night, at any distance and at no
  per-frame cost (`id1/world/night-windows.txt`, written by
  `tools/night_windows.py`; `aw_night_window_lights 0` turns it off).
- Torch, lamp and window light is warm instead of grey: `dbg light hue R G B`
  (default 255 210 140) and a Hue row in `dbg lightgallery`. Blue lanterns keep
  plain light.
- `dbg lamps` shows the lamps the engine sees around you.

## Guard torches

Hlaalu guard torches outshone the lamps
([GUARD-TORCH-BRIGHT-31](bugs/GUARD-TORCH-BRIGHT-31.md)). They keep their
brightness at the flame and light half as far; `dbg guardtorch 0.1..2.0` sets
the reach (`on/off/auto` as before).

## Known in this build

- Lamps beyond the nearest two are not lit; the repair is baking every lamp
  into the maps on a night light style
  ([LAMPS-RANGE-31](bugs/LAMPS-RANGE-31.md)).
- A sudden darkening around 04:00 has been reported and is being measured
  ([NIGHT-0400-DARK-31](bugs/NIGHT-0400-DARK-31.md)).
- The lamp table in this build has no colour classes yet, so blue lanterns get
  warm light too.
- Seyda Neen's windows are wooden shutters without glass and its lanterns are
  not in its maps yet, so Seyda Neen barely glows at night.
- Everything listed in the [dev4 notes](RELEASE-v0.0.31-dev4.md) and the
  [bug register](BUGS.md).
