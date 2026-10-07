# GUARD-TORCH-BRIGHT-31: Hlaalu guard torches over-bright at night

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev4; repaired in source for dev5, not yet
owner-checked.

## Symptom

In Balmora at night a Hlaalu guard's torch lights the street more than the
lamps and lanterns do ("super over the top bright").

## Where

`engine/aga/src/aw_guard_torch.c` (guard torch lights) and
`engine/aga/src/aw_torch.h` (`AW_TorchLightGain`).

## How it happened

Guard torches use the player's full torch light: the torch radius and the torch
surface gain. dev4 made the light-space night the default
([DLIGHT-WALLS-31](DLIGHT-WALLS-31.md)), which stops darkening dynamic light, so
the guard torches' full reach became visible across whole squares.

## Why it was not caught

The guard torch light was accepted under the old whole-frame night look and was
not walked again at night after the night look changed.

## Reproduction

v0.0.31-dev4, Balmora at night (21:38, Hlaalu guard on the square near global
-23973 -12638): the guard's torch pool covers most of the square.

## Repair

dev5: guard torches keep the player torch's brightness at the flame and light
half as far (`aw_guard_torch_radius` 0.5; `dbg guardtorch 0.1..2.0` sets it,
`on/off/auto` as before). The surface gain is 512 x strength / radius, so the
peak at the flame stays the same and only the reach shrinks.

## Verification

Native tests (guard torch fixture) and gate 075; same-pose captures dev4 versus
dev5 (guard radius 1.0 and 0.5), headlamp off. Owner check pending.

## Prevention

Night walks through each town with guards after any change to the night look.
