# AmiWind v0.0.34 - CHIM: Tightening the Bolts

Running on CHIM Engine v0.1.0. The boot checklist says it the short way:
"AmiWind v0.0.34 / CHIM v0.1.0".

A fix release on top of [v0.0.33](RELEASE-v0.0.33.md): two things that playing v0.0.33
showed are repaired at the layer every town and map shares, and each comes with an
island-wide check that now runs in every build.

## Fixed in this release

**The silt strider's hull is closed** ([MESH-LOD-OPEN-SEAMS-33](bugs/MESH-LOD-OPEN-SEAMS-33.md),
[CHIM-STRIDER-RING-33](bugs/CHIM-STRIDER-RING-33.md)): mesh reduction pulled the strider's
shell plates apart, so the sky showed through the hull in Balmora and Seyda Neen. v0.0.33
knew it and held the repair back, because the full-detail repair did not fit Balmora's chunk
memory. The strider is now reduced with every seam and rim locked in place: no torn seam
anywhere on the model, and it is even a little smaller than before (3,219 faces instead of
3,266), so Balmora's busiest chunk ring has more room than in v0.0.33 (15,760 bytes instead
of 2,528). The legs are slightly thinner than the original's; the full-detail strider stays
selectable for when the memory is there.

**Bitter Coast mushrooms can all be picked** ([HARVEST-BITTERCOAST-29](bugs/HARVEST-BITTERCOAST-29.md)):
some mushrooms could not be picked while their neighbours could. The pick ray stopped on
invisible collision: a tree's simplified collision also fills the space under its roots, where
the mushrooms grow. A solid that contains a plant no longer hides it; a wall in front of a
plant still does. Checked over the whole island: 51 of the 934 placed plants could not be
picked from anywhere in v0.0.33, none now.

## New checks in every build

- **Seam audit:** every mesh the converters reduce is compared with its source, with the
  profile each converter actually uses (legacy towns, CHIM and the open world); a torn seam
  on a mesh that must stay closed, or a new torn mesh, stops the build.
- **Harvest pick audit:** the engine's pick rule is replayed for every placed plant on the
  final maps, from every direction a player can stand; a plant that cannot be picked stops
  the build before any disk is made.

## Known in this build

Everything open is in the [bug register](BUGS.md); the list in the
[v0.0.33 notes](RELEASE-v0.0.33.md#known-in-this-build) still applies, except the silt strider
entry. New:

- [HARVEST-PLANTS-IN-COLLISION-33](bugs/HARVEST-PLANTS-IN-COLLISION-33.md): the collision that
  covered those mushrooms is unchanged (it no longer blocks picking); it may still stop you under
  some tree roots
- [MESH-LOD-TORN-MESHES-33](bugs/MESH-LOD-TORN-MESHES-33.md): the seam audit's first island-wide
  run found 49 other reduced meshes (town flora, rocks, the arrival ship) with torn seams; they are
  recorded and the build fails if any of them gets worse

## Credits

As in [v0.0.33](RELEASE-v0.0.33.md#credits).
