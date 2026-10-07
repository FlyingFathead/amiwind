# LAMPS-FLICKER-31: night lamps switch on and off while turning or walking

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev5 (Seyda Neen and Balmora at night); repaired
in source, not yet packaged.

## Symptom

At night, lamp light keeps going on and off: turning the head or taking a step
switches which nearby lamps light their surroundings, and a lamp that loses its
light goes dark at once.

## Where

`engine/aga/src/aw_lamps.c`, `AW_LampUpdate`.

## How it happened

Only `aw_lamp_lights` (2) lamps get a dynamic light, chosen again every frame.
dev5 made a lamp behind the view count three times as far, so turning round
moved the slots to other lamps; and only switching on faded, switching off was
instant. A dev5 change of ours (the LAMPS-RANGE-31 mitigation) caused it.

## Why it was not caught

The dev5 captures were still frames at fixed poses; nobody turned or walked
between lamps before packaging.

## Reproduction

v0.0.31-dev5, Seyda Neen or Balmora between two or three lamps at night: turn
on the spot.

## Repair

A lit lamp keeps its slot unless a rival is clearly nearer (its squared
distance counts at half). A lamp behind the view only loses near-ties (1.5x
instead of 3x). A dropped lamp shrinks away over 0.4 s on the spare lamp keys.
The full repair remains baking every lamp into the maps on a night light style
([LAMPS-RANGE-31](LAMPS-RANGE-31.md)).

## Verification

Native test: turning round keeps the lit lamps; a clearly nearer lamp takes a
slot and the dropped one fades, then goes. Owner walk pending.

## Prevention

Lighting changes get a short walking and turning clip, not only still frames.
