# Light sources: Morrowind lights mapped onto Quake's light machinery

Status: 7 October 2026. Census and mapping done; converters not yet wired.

AmiWind runs on AmiQuake, so light sources are handled the way Quake handles
them, not with a new engine feature:

- A light source is a map entity (`light`, and in id's game code
  `light_torch_small_walltorch`, `light_flame_large_yellow`, `light_globe`,
  `light_fluoro`). The light compiler bakes it into the lightmaps (AmiWind
  ships ericw-tools `light`: colour, falloff, styles, surface lights).
- Animated or switchable light uses lightstyles. `R_AnimateLight`
  (`engine/aga/src/r_light.c`) turns a style string into a brightness per
  frame; a surface is rebuilt in the surface cache only when one of its
  styles changes value (`d_surf.c`). Quake allows four styles per face.
- Moving light (the player's torch, guards' torches) uses dynamic lights
  (`cl_dlights`, 32 slots).

Every original light placement therefore becomes a light entity with a style.
Flames on fires, torches, candles and lanterns already come from each light
mesh's own particle emitters (`aw_flame`, drawn with the engine's particle
fire).

## The census

`tools/light_sources.py census Morrowind.esm` reads your own data file and
writes the numbers below (no game data in the report).

574 light types, 18,811 placements. Class comes from the original model and
ID first; the original Fire flag is also set on candles and lanterns, so it
only decides lights that name nothing else.

| Class | Placements | Interior | Exterior | Quake treatment |
| --- | ---: | ---: | ---: | --- |
| Lamp, lantern, streetlight | 6,942 | 6,397 | 545 | `light`; outdoors on the night-lamp style |
| Candle, chandelier | 3,805 | 3,799 | 6 | `light`, style from its flags |
| Fill light (no mesh) | 3,337 | 1,401 | 1,936 | `light`, style from its flags |
| Torch (wall, tiki) | 1,829 | 1,760 | 69 | `light` + flame |
| Fire (brazier, pit fire, flame light) | 1,263 | 1,189 | 74 | `light` + flame |
| Other (dwemer lamps, censers) | 657 | 657 | 0 | `light`, style from its flags |
| Glowing plant | 644 | 312 | 332 | `light` |
| Negative (darkens) | 334 | 322 | 12 | negative `light` |

Colour: 14,224 warm, 3,896 cool, 691 neutral placements.

## Per cell, not per world

What a map pays for is the lights of the cells it holds:

| Cells | Count | Median | 90 % | 99 % | Most |
| --- | ---: | ---: | ---: | ---: | ---: |
| Interior cells with lights | 1,077 | 12 | 28 | 54 | 95 |
| Exterior cells with lights | 697 | 3 | 8 | 19 | 35 |

A typical interior has about a dozen lights, the scale of an original Quake
map; a typical exterior cell has three. Balmora's busiest cell has 26 street
lamps, two of them animated.

## Styles

Original animation flags map to id's standard lightstyles; outdoor lamps use a
switchable style (Quake's switchable range starts at 32) that the clock turns
on at dusk and off at dawn.

| Original flag | Quake style | Placements |
| --- | --- | ---: |
| none | 0 normal | 2,028 |
| Flicker | 1 flicker | 240 |
| Flicker slow | 6 soft flicker | 12,557 |
| Pulse | 5 gentle pulse | 1 |
| Pulse slow | 11 slow pulse | 3,440 |
| (outdoor lamp) | 32 night lamps | 545 |

## Cost on the Amiga

- Steady baked light costs nothing per frame, whatever the count.
- An animated style rebuilds only the surfaces that use it, and only when its
  value changes. Lights are grouped by style, not one style per light, so a
  room animates a handful of values and a face never needs more than four.
- To measure before enabling animation widely: the surface-cache cost of the
  soft flicker style on the 68040 in the busiest interior (95 lights, all
  animated), against steady light, in one benchmark sweep.
- Lightmap memory per map against the heap budget.

## Plan

1. One shared mapping (`tools/light_sources.py`: class, style, colour class,
   entity text) used by the interior and the exterior converters.
2. Converters write the light entities into each map source, so the light
   compiler bakes the brush faces, and pass the same list to the mesh bake.
3. Engine: the night-lamp style driven by the clock; night darkening moved into
   light space so lamps, glows and torches keep their colour
   ([BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md)).
4. Rebuild the world cell by cell and check every cell against the census:
   each light placed, baked and styled, or listed with a reason.

Related: [LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md),
[LIGHT-NEGATIVE-31](bugs/LIGHT-NEGATIVE-31.md),
[EMISSIVE-UNSHIPPED-31](bugs/EMISSIVE-UNSHIPPED-31.md),
[NIGHT-RUST-31](bugs/NIGHT-RUST-31.md),
[LANTERNS_AND_TORCH_LIGHTING.md](LANTERNS_AND_TORCH_LIGHTING.md).
