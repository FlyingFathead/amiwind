# LIGHT-NEGATIVE-31: negative (darkening) lights bake as bright white light

## Status: 7 October 2026

Open. Cause read in source; no repair yet.

## Symptom

Corners that the original game darkens on purpose come out brighter instead.
Found at the Census and Excise Office fireplace in Seyda Neen.

## Where

`tools/interior_lighting.py`, `bake_surface`: every light's colour is added;
the light's flags are never read.

## How it happened

Morrowind lights carry flags (dynamic, can carry, negative, flicker, fire, off
by default, flicker slow, pulse, pulse slow). A light with the Negative flag
(0x4) removes light instead of adding it. The Census office places `dark_128`
(white, radius 128 original units, flag 0x4) beside the fireplace, at original
(-170, -474, 266). The bake adds it as full white light, so the corner the
original darkens is brightened instead.

## Why it was not caught

The bake was a first-pass approximation that was never checked light by light
against the original; flags were carried into the lighting data but unused.

## Reproduction

Census and Excise Office: look at the left side of the fireplace. In the data:
any interior light record with LHDT flags & 4.

## Repair

Not done yet: subtract negative lights in the bake (with the original
attenuation, see LIGHT-FALLOFF-31), clamped at zero; judge against OpenMW.

## Verification

Pending.

## Prevention

A gate check that every light flag the bake meets is either handled or listed
as deliberately ignored.
