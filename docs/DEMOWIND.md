# DemoWind: the effects test kit

_Last updated with AmiWind v0.0.55 (29 October 2026)._

DemoWind is a test kit of cheap animated effects: no world and no game, only the effect, fullscreen on AGA, browsed
one after another, each with its cost on screen (milliseconds a frame and bytes). Effects that win go into the game.

## Running it

- In any image: `dbg demowind` (or `dbg demowind on`). The world is not drawn while it is on.
- The MiniWind preset `--miniwind-demowind` boots straight into it (`config/recipes/miniwind/demowind.json`).
- Keys: Right / N next effect, Left / P previous, Up / Down the distance step, Esc off.
- Console: `dbg demowind next`, `prev`, `effect 1-2`, `dist 0-7`, `status`, `off`.
- Every effect logs one `DEMOWIND COST` line per distance step after 32 frames: the average milliseconds a frame,
  the bytes, the bake time and the screen size. Run it at 32 MB Fast RAM, the game's requirement.

## Effects

1. **Plain sky**: Quake's own two-layer scrolling sky (a solid back layer and a holed cloud layer at another speed,
   composed into one 128x128 tile a frame, then one lookup a screen pixel), in the colours and cloud speed of the
   game's Clear weather.
2. **Red Mountain sky**: the same two layers with a dark blood-red back layer and fast, hard-edged blight and ash
   clouds. Up / Down steps the distance to the mountain (0 Seyda Neen .. 7 the crater): the palette shifts from the
   Clear weather to the Blight weather, the clouds speed up and cover more of the sky. The colours are the game's
   own weather data: the Red Mountain region's weather is Blight (100 %), and the Blight and Ash Storm weathers give
   the sky, fog and sun colours and the cloud speed (9 against Clear's 1.25).

Effect 2 is in the game from v0.0.55: the sky turns red by the distance to Red Mountain
([the Red Mountain sky](DAY_NIGHT_AND_SKY.md#region-weather-20-october-2026)).

The textures are drawn by the engine from seeded noise when DemoWind starts: our own, no picture from any game.
A distance step bakes the new palette into the two layer tiles once, so the frame work of both effects is the same;
the numbers on screen are measured, not estimated. DemoWind allocates 81,920 bytes on start and frees them on Esc.
