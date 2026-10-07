# NIGHT-RUST-31: night tint rounds dark colours to rust-red speckle

## Status: 7 October 2026

Open. Repair in source (engine `R_SkyNearest`), checked by a native test; not
yet packaged or seen in game.

## Symptom

At night, dark walls and ground show scattered dark rust-red speckles on
near-black, a hue the textures do not have ("this very peculiar hue", owner,
Balmora).

## Where

`engine/aga/src/r_sky.c`, `R_SkyNearest` and the day/night fog tables it fills;
applied to the finished frame by `aw_fog.c`.

## How it happened

The night remap scales each palette colour and then finds the nearest palette
entry through a 16 x 16 x 16 grid: each channel is rounded to steps of 17.
Near black, one channel can round up while the others round down. Palette 211
(23, 17, 13), a common dark wall and ground colour, becomes (9, 8, 8) at deep
night; red rounds up to 17, green and blue round down to 0, and the grid cell
(17, 0, 0) maps to palette 215 (23, 7, 3), dark rust. Measured on one Balmora
wall texture at night: 132 of 1,024 texels rust; on one terrain texture 292 of
1,024 (28.5 %). An exact nearest-colour search sends 211 to a dark grey.

## Why it was not caught

The grid lookup was chosen for speed; its error is invisible in bright colours
and only shows near black, and night frames were not checked texel by texel.

## Reproduction

Any exterior at deep night (`dbg set time 2300`), dark walls and ground.

## Repair

`R_SkyNearest` keeps the fast grid lookup, but a dark colour (all channels
below 64) whose grid answer is clearly more saturated than the colour itself
(spread more than 12 above the source's) is searched exactly over the palette.
On the shipped palette that is 6 of 256 colours at deep night, once per table
build, never per pixel; palette 211 and 214 then map to a near-black grey
(9, 9, 6) instead of rust (23, 7, 3). A full exact search of every table level
was rejected: about a million comparisons per table build on the 68040.

## Verification

Native test `--night-rust` (day/night test): a palette holding the measured
trap, rust nearest the grid point and a grey nearest the colour; the grey must
win and bright colours keep the grid answer. In-game check pending.

## Prevention

A check that the night tables never map a near-neutral colour to a colour of
noticeably different hue.
