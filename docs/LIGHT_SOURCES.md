# Light sources: Morrowind lights mapped onto Quake's light machinery

_Last updated with AmiWind v0.0.61-dev3 (2026-11-06)._

Status: the census and the mapping were done on 7 October 2026 and the converters were wired in v0.0.31, when the
original street lamps, lanterns, wall torches and fires began to light Balmora and Seyda Neen at night. The section
at the end covers the lights that can be taken and held (v0.0.61).

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
[LANTERNS_AND_TORCH_LIGHTING.md](history/superseded/LANTERNS_AND_TORCH_LIGHTING.md).

## Lights that can be taken and held (v0.0.61)

- **Taking a lit candle or lamp takes its flame and its light with it,** outdoors and indoors, and it stays gone after a
  save and a load. The builder writes each exterior cell's effect links (which flame and night lamp belong to which
  placement) into the cell's own area record at image assembly; in the dev1 data that is 25 cells, 524 rows, a median of
  112 bytes and at most 1,660 bytes. A build check covers the whole world and a test plants a miss on each path. In
  the five town frame maps (Vivec 49, Seyda Neen 4, and two more town maps with 4 each) the flame links of 61 flame
  rows of 53 carriable lights were looked up under the wrong map name, so a taken lantern left its flame floating; all
  288 flame rows are found now, and the build check also refuses a flame link that names no frame map of the image
  ([TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61](bugs/TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61.md)).
- **Held lights are drawn and lit as themselves.** A candle, a candlestick (three candles) and a lantern held in the
  hand show their own model and flames, in first person and on the third-person hand, and light by their own record:
  the candle reaches half as far as the torch, the candlesticks and lanterns as far as the torch, as in the original.
  The torch is unchanged ([INVENTORY.md](INVENTORY.md), "World models";
  [HELD-LIGHT-ALWAYS-TORCH-61](bugs/HELD-LIGHT-ALWAYS-TORCH-61.md)).
- **Limits in v0.0.61-dev3.** A light that is dropped or put down again gets no flame and gives no light where it lies
  ([DROPPED-LIGHT-NO-EFFECTS-61](bugs/DROPPED-LIGHT-NO-EFFECTS-61.md)). The baked light of a room stays when a light in
  it is taken (`TAKEN-LIGHT-BAKED-LIGHT-61`). Seyda Neen's carriable lanterns are
  missing from the open world ([SEYDA-LANTERNS-MISSING-31](bugs/SEYDA-LANTERNS-MISSING-31.md)). A lantern hangs below the
  hand, so in first person only its handle shows; the light's colour is one shade off the original; burn time is not
  counted; the light is not in the inventory picture. The Ebonheart lantern after a save and load, and the candle in
  Arrille's Tradehouse, are not yet seen taken on the dev3 image.
