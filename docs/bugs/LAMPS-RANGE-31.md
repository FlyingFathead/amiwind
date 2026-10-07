# LAMPS-RANGE-31: only the nearest lamps light up at night

## Status: 7 October 2026

Open (limit of the v0.0.31-dev4 night lamps). Owner report; cause known.

## Symptom

Walking through Balmora at night, distant lamps, including those in the next
sub-cell, stay dark and light up only as the player comes close ("can't see
shit", then "oh, there's light after all").

## Where

`engine/aga/src/aw_lamps.c`: night lamps are dynamic lights for the nearest
`aw_lamp_lights` (default 2) lamps within 512 local units of the player.

## How it happened

Dynamic lights cost time every frame, so only a few nearby lamps can be lit at
once; all other lamps have no light at all, because the exterior maps carry no
baked lamp light ([BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md)).

## Why it was not caught

The night lamps were first built as a stopgap and not walked across a whole
town at night before packaging.

## Reproduction

v0.0.31-dev4, Balmora at night: look along a street toward lamps more than a
few houses away.

## Repair

Not done. The lamp data is not lost between sub-cells: every lamp in the 3 x 3
cells around the player is read and known to be lit. Only the nearest lamps get
one of the few dynamic lights, so a step can hand a slot from the lamp ahead to
one behind ("like walking into motion detector lights", owner).

dev5 mitigation: lamps ahead of the view win the slots (a lamp behind counts
three times as far), a newly chosen lamp grows to full radius over 0.4 s instead
of popping on, the lamp radius is the torch radius (owner choice from 1.0/1.5/2.0 captures) (`dbg outdoorlantern`), and
lantern glass and windows glow at night at any distance (no per-frame cost).

Full repair (Quake's switchable lights): every lamp baked into the map
lightmaps on a night lightstyle (32 or above), switched on at dusk: all lamps
in view lit at any distance, no per-frame cost, one surface-cache rebuild at
dusk and dawn. Cost is lightmap memory, measured on the bm019 prototype at
about 0.96 MB of heap headroom; each map is to be checked by a lights gate.

## Verification

Pending.

## Prevention

Night walks across each town in the capture set.
