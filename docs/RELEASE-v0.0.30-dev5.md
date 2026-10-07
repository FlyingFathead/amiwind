# AmiWind v0.0.30-dev5 - The Temple

Development build for testing the new lighting and the first Seyda Neen
loading improvement. Everything in [v0.0.30-dev4](RELEASE-v0.0.30-dev4.md) is
included. Two maps are rebuilt (Balmora Temple, Census and Excise Office);
every other map is unchanged from dev4.

## New: lighting

Each change has a console switch so it can be compared in place.

- **NPCs lit by their floor.** NPCs standing on converted floors take that
  floor's light instead of ambient only, so they no longer appear as dark
  silhouettes in interiors. Works in every map. `aw_actor_brush_light 0`
  turns it off.
- **Glowing materials.** Lantern glass, Dwemer lights, mushrooms and lava
  are lit by their own glow strength. Visible in rebuilt maps only: in this
  build the Balmora Temple's Dunmer lantern. `dbg emissive 0` turns it off.
- **Flames on placed fires and candles.** Fires, candles, lanterns and
  braziers show a flame. Rebuilt map in this build: the Census and Excise
  Office (fireplace and candles). The look is still being tuned.
  `aw_static_flames 0` turns them off.

Details: [lanterns and torch lighting](LANTERNS_AND_TORCH_LIGHTING.md).

## Faster Seyda Neen crossings

Converted NPC models are read once instead of twice while a region loads.
On the Seyda Neen test route the heavier crossings read about 15 % less and
load about 0.1 s faster in the emulator. `aw_alias_single_pass 0` restores
the old loader. See [Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md).

## Engine and build

- The engine builds without compiler warnings, and the build fails on any new
  one ([AGA build](AGA_BUILD.md)). The cleanup removed an unreachable, broken
  16-bit surface drawer, bounds all path formatting and moves a 15 KB sprite
  buffer off the stack.
- `build_aga.py image --canonical-land-source` passes the world-survey terrain
  to the Seyda Neen partition; regenerating Seyda Neen with public tools
  is still open ([BUILD-SEYDA-REGEN-30](BUG_JOURNAL.md)).
- New tool: [points-of-interest checklist](POI_CHECKLIST.md).

## Still open

The load freeze seen in 3 of about 55 automated Seyda Neen runs (all on the
night of 6-7 October, none since) is unexplained. Flames need visual tuning.
Glow and flames reach other maps as they are rebuilt. See the
[tracker](BUGS.md).
