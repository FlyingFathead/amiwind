# EMISSIVE-UNSHIPPED-31: glowing lantern glass never reached the shipped maps

## Status: 7 October 2026

Open. Measured in the v0.0.31-dev2 maps; no repair yet.

## Symptom

Lanterns and lamps do not glow, although `dbg emissive` is on (owner: "that
lantern and the others in Balmora, they are NOT LIT").

## Where

The converter marks emissive materials per texture (`tools/prepare_scenery.py`
reads the original material's emissive colour; `tools/prepare_mesh_bsp.py`
names such textures `emitN_...`; `r_surf.c` lights them by the prefix). Only
maps converted after that marking was added carry it.

## How it happened

The marking was added and checked with the Temple rebuild, but the other maps
were never reconverted. Census of all 2,724 dev2 maps: one emissive texture in
total, in `bmtemple.bsp`. Balmora's street lamp mesh has 16 emissive
triangles in the original, but the shipped map has them as an ordinary
texture. Seyda Neen and the prison ship have none (the prison lantern mesh has
no emissive material in the original either).

## Why it was not caught

The feature was verified on the one rebuilt map; no check counts emissive
textures in the shipped maps against the original meshes.

## Reproduction

Any lantern outside the Balmora Temple, with `dbg emissive 1`.

## Repair

Not done: rebuild the maps with the current converter (part of the next full
map rebuild), then count emissive textures per map against the original.

## Verification

Pending.

## Prevention

A gate count of emissive materials per map against the original meshes.
