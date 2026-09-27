# Preserved ship rendering methods

`method_001` is the exterior ship from **v0.0.14-dev1 / checkpoint-015**, specifically
preserved at the owner's request because its distant appearance is the reference.
Its full source and private image ZIPs remain immutable.

`config/ship_methods/method_001.json` records the original assembly/LOD recipe and
source/archive hashes. This is archival metadata, not a runtime mode selector.
Restore the pinned converter files from the named public source ZIP to reproduce
that method; the public archive supplies no assets. Private image:
`AmiWind-v0.0.14-dev1-private-playable.zip`. Public source:
`AmiWind-v0.0.14-dev1-public-source.zip`.

Future `method_002` candidates must use a new output directory. Keep matching
broadside/bow/deck views, projection, palette, fog, XYZ/yaw/pitch and hardware.
Measure visible surfaces/edges, memory, frame stages and audio deadlines, and
retain rejected candidates. Structural corrections are not permission to overwrite
method_001 or change the exterior while repairing the separately loaded interior.

The interior's 8% blanket LOD is a separate failed visual trial. Its hull intrudes
into the furnished room; do not call it the preserved exterior baseline.

## Whole-exterior comparison baseline

The owner's 22:50 report additionally preserves the **checkpoint-016 exterior**
as the whole-scene method_001 for texture/poly-count A/B work. This is a broader
scope than the existing ship-only method_001 pinned to checkpoint-015. Keep the
checkpoint-016 public/private ZIPs immutable; camera (-44,259,75), yaw328/pitch-14
is the new slow-view reference. Do not overwrite either baseline with an
optimized candidate or conflate a new recipe with a validated speedup.
