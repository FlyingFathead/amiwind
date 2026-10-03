# AmiWind v0.0.27-rc2 - Rocks and Mushrooms

## Scope

Use the existing Vvardenfell topomap as the foundation for 37,960 original
exterior rock placements and 816 giant mushrooms, covering 2,526 world regions.
Retain authored position, compound rotation, scale, original texture sources
and collision. Exclude small collectible mushrooms and expansion content.
Keep Seyda Neen and Balmora sub-cell divisions for frame cost.
Read [What are rocks?](WHAT_ARE_ROCKS.md) for the structural scenery policy.

The rc1 playtest confirmed visible rocks and giant mushrooms but revealed cap
gaps after independent material-wise simplification. Rc2 preserves shared-seam
material sections and source UVs on all five giant-mushroom models. Rock LOD
is unchanged. This is a conservative geometry correction; further reduction
must preserve joins. See GEO-01 in the [bug journal](BUG_JOURNAL.md).

Image assembly splits large payloads into additional HDFs automatically, with
each HDF below 4 GiB and each filesystem partition below 2 GiB. Both WinUAE and
FS-UAE configurations are generated with all drives mounted simultaneously.
The final output lists every disk and both configuration paths.
`dbg map tp` aliases `dbg tp map` for the world-map teleport picker.

## Local validation

- Corrected world overlay: 2,526 regions, 38,776 source references, 303.469 seconds
  using 24 workers. Retained terrain inputs remain unchanged.
- Maximum region: 3,924,496 bytes; maximum faces: 20,026; maximum clipnodes: 32,085.
  All existing storage, face and collision budget checks passed.
- All five mushroom models retain exact geometry and UVs on joined sections.
  The synthetic shared-rim regression and real console routing harness passed.
- Complete NPC gallery: 2,935 records, 3,551 models; strict packaged actor contact
  passed with zero unresolved cases.
- Filesystem readback, independent HDF hashes and generated configuration disk
  lists passed. Two HDF capacities: 4,026,564,608 and 1,073,774,592 bytes.

The owner accepted the corrected giant-mushroom caps in the rc2 WinUAE
playtest. Seyda Neen town/world terrain continuity remains a release blocker.
Rock texture acceptance and target performance remain pending.
Fresh Linux/Docker pipeline validation, hosted CI and publication are pending.
Native Windows remains experimental. WinUAE background-music snapping remains
open; a larger output-buffer comparison is an experiment, not a verified fix.

## Distribution

The public candidate contains GPL source and tooling. Users supply their own
Morrowind data and Kickstart ROM. Proprietary assets, converted content, playable
HDFs, ROMs and private host paths are excluded from the public package.

## Playtest screenshots

Owner-selected rc2 WinUAE views in the Ascadian Isles show joined cap rims,
textured undersides and giant mushrooms against the landscape.

![Closed mushroom cap](images/amiwind-v0.0.27-rc2-mushroom-cap.png)
![Ascadian Isles mushrooms](images/amiwind-v0.0.27-rc2-ascadian-mushrooms.png)
![Textured joined underside](images/amiwind-v0.0.27-rc2-mushroom-underside.png)

These are documentation screenshots, excluded from the code licence and never
used as distributable runtime assets.
