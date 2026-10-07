# BALMORA-LAMPS-DIM-31: Balmora's street lamps are far too dim at night

## Status: 7 October 2026

Open. Owner report from the v0.0.31-dev2 playtest. Causes measured in source
and in the shipped dev2 maps; no repair yet.

## Symptom

At night in Balmora a street lamp and the walls around it are almost black; the
lamp gives no visible pool of light. The owner confirms the same in Seyda Neen:
at night the only light in either town comes from the guards' torches. The
cause below is in the exterior converter, so it applies to every exterior. The lantern models themselves are dark too:
"that lantern and the others in Balmora, they are NOT LIT" (second view at
23:18, global -20907 -17118 532, a lantern hanging by a doorway). The owner also
notes "this very peculiar hue": the dark walls show scattered dark-red speckles
on near-black.

## Where

Balmora, game time 22:21, global XYZ -20970 -16963 521 (local -122 -1168 130),
looking up at a lamp (north-west, pitch -29).

## How it happened

Both owner views look at the same original lamp, `light_de_streetlight_01_223`
(radius 223 original units, colour 245 140 40) on a lamp post beside a Hlaalu
door, at original (-21076, -16773, 718). Three causes together:

1. Exterior lamps never become light. The Balmora builds
   (`tools/prepare_balmora.py`, `tools/rebuild_balmora_region.py`) call
   `append_meshes` without lighting data, so mesh faces get no lightmap at all
   (lightmap offset -1); the terrain map has no light entities, and the light
   compiler runs with only a minimum light. Measured in region bm019: 31,022
   faces, 2,129 with a lightmap (all terrain), lightdata 4,786 bytes. Every
   building, lamp and prop is drawn with the flat ambient (`r_ambient 128`).
   The other Balmora regions look the same.
2. The lamp glass is not emissive in the shipped maps: see
   [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md).
3. Night darkening is one palette remap of the finished frame
   (`aw_fog.c`, tables from `r_sky.c`): deep night scales every pixel by about
   (0.43, 0.52, 0.66), lit or not. Any lamp light, glow or torch would be
   crushed and turned blue with everything else. A wall texel near the lamp
   (mean about 69 63 42) is drawn as about (33, 30, 21) by day and (15, 16, 15)
   at night. The rust-coloured speckle comes from the same remap:
   [NIGHT-RUST-31](NIGHT-RUST-31.md).

## Why it was not caught

Night views of towns were never compared with the original game, and no check
reports exterior light references that produce no light.

## Reproduction

v0.0.31-dev2: `dbg tp -20970 -16963`, `dbg set time 2221`, look up at the lamp.

## Repair

Not started. AmiQuake machinery that fits (to be measured on the 68040 before
choosing):

- Lamp light baked on its own lightstyle, faces within reach only. The engine
  sets that style from the clock (off by day, on at night); the surface cache
  rebuilds affected surfaces only when the value changes (Quake's switchable
  lights). No per-frame cost; costs lightmap memory (estimate 116-295 KB per
  Balmora region before overlap; the heap budget must be checked).
- Night darkening moved into light space (ambient and the daylight style), the
  post-frame remap kept for tint only, so lamps, glows and torches survive.
- Dynamic point lights for the nearest lamps (the guard-torch pattern) need no
  rebuild but cost every frame; estimates say at most about 2 at once.
- Rebuild Balmora with the current converter so the glass is emissive.

## Verification

Reference: OpenMW at both owner poses (22:21 and 23:18, clear weather) shows the
lantern panes glowing cream-orange and a clear warm pool on the wall and door
arch below it, fading within about one storey; walls away from it are dim
blue-grey. Repair verification pending: the same poses in AmiWind side by side.

## Prevention

Pending the cause.
