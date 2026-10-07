# LIGHT-FALLOFF-31: interior lights stop dead at their radius

## Status: 7 October 2026

Open. No repair yet. Correction, same day: the first version of this page said
the opening lantern baked no light at all. That came from a faulty measuring
script, not from the map; see "Correction". What remains is the falloff
difference below.

## Symptom

In the opening scene the owner sees the hanging lantern above the start give
too little light around it.

## Where

`tools/interior_lighting.py`, `bake_surface`: the offline lightmap bake for
converted interiors.

## How it happened

The bake adds each light as `colour * (1 - d / radius)` and nothing beyond the
radius. Morrowind lights do not stop at their radius: the original attenuation
(OpenMW's defaults, `LightAttenuation_LinearMethod 1`, `LinearValue 3.0`, no
constant term) is `radius / (3 d)`, a third of full strength at the radius,
and OpenMW fades it out between the radius and twice the radius. Small lights
therefore light less, and less far, than in the original.

## Which lantern

OpenMW at the owner's pose shows that the hanging lantern in view is
`light_com_lantern_02_200_Boat` (radius 200 original units, 50 local units) at
local (20.7, -9.2, 22.6), on a rope. `light_com_lantern_02_64` sits on the deck
above the hold and cannot be seen from the start. In the original the whole
hold is very dark (mean frame luma 11 to 16 of 255); the start area is only
about 3 to 4 luma brighter when facing that lantern, whose beams are lit only
faintly.

## Correction

The first measurements read lightmaps of placed objects in their model-local
coordinates, without the placement (origin and yaw) the engine applies, so
distances to the lantern were wrong. Measured with the placement applied, the
shipped map is lit around the lantern: 821 of 822 faces within 30 local units
have light above the ambient; the hull within 50 units reads 64 to 208, a crate
next to the lantern up to 255. Recomputing the bake for every face from the
map's own data matches the stored lightmaps for 25,626 of 26,551 faces; the
rest are [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md).

## Why it was not caught

The bake was introduced as "an approximation, not TES3 lighting parity" and was
never compared light by light against the original.

## Reproduction

New Game; look at the hanging lantern above the start, and compare with OpenMW
at the same pose.

## Repair

Not done yet: bake with the original attenuation (already available as
`lighting['falloff'] = 'original'`), judged against OpenMW at the same cell,
position, heading and time.

## Verification

Pending.

## Prevention

Light-by-light comparison of baked light against the original attenuation;
measuring scripts apply the engine's placement of each object.
