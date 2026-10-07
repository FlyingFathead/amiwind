# DLIGHT-WALLS-31: torches barely light town walls at night

## Status: 7 October 2026

Cause found and measured; repaired in source for v0.0.31-dev4 (light-space
night made the default), awaiting the owner's in-game check.

## Symptom

At night in Balmora the player's torch and the guards' torches seemed to light
the ground but not the buildings (owner). The same carried light lights walls
inside the prison ship.

## Where

`engine/aga/src/aw_fog.c` (`AW_FogDraw`, the whole-frame night remap through
`sky_fog`) and its tables in `engine/aga/src/r_sky.c`.

## How it happened

Not a light-marking problem: a native run of the real engine code on the
shipped Balmora map's faces shows placed walls get the full dynamic light
(264 of 266 faces at 32 to 64 units reach full light). Outdoors, after all
lighting, the night remap rewrote every geometry pixel through a table that
scales the palette by the night ambient (about 0.43, 0.52, 0.66 at deep night),
so it also halved the torch's own light; interiors skip that step. Walls
across a street are 100 to 200 units away against the torch's 192-unit reach,
so their remaining light was faint and easy to miss.

Measured in game (v0.0.31-dev3, Balmora, 22:21, one switch at a time): the
headlamp lifts the facade from 13.5 to 24.8 mean luma with the remap, and from
13.7 to 41.7 with light-space night (`aw_night_light 1`), the night being
equally dark without the headlamp.

## Why it was not caught

The native light tests run without the night remap; town walls at night were
not compared with and without a torch in game.

## Reproduction

Balmora at night, `dbg headlamp on` and off next to a facade, with
`dbg night light 0` and `1`.

## Repair

`aw_night_light` defaults to 1: the night's brightness goes into the light
(ambient and baked light), dynamic lights are added after it unscaled, and the
end-of-frame table keeps only the hue. The cvar is saved, so a configuration
that stored 0 keeps 0 until changed.

## Verification

In-game A/B above; owner check of dev4 pending.

## Prevention

A town headlamp pair at night in the regular capture set.
