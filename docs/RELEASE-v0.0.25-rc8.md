# AmiWind v0.0.25-rc8

Torch crash correction; complete source update from published rc7.

The owner reported an immediate crash after raising fists with F and pressing V.
A host regression using the actual brush-render entry point reproduces a
segmentation fault in rc7: a converted non-colliding model's negative leaf root
was used as a node-array index. Collision-only positive roots also lack the
visible face references needed for correct lighting.

Dynamic lights now mark the brush model's own validated visible surface range,
using the existing local position/rotation transform. Nearby-model bounds and
face-plane distance limit the work; tiled sky/water surfaces are excluded.
The world BSP keeps its normal lighting traversal. The final dynamic-light bit
uses an unsigned shift. No new control or game-data conversion is introduced.
The owner's README cleanup from commit `690ecd4` is preserved.

[Validation](validation/rc8-source.json) distinguishes the crash reproduction,
regression checks and native engine/asset-free image build from emulator testing.
The repaired F-then-V sequence still requires a target retest, including toggling
off, lowering fists, nearby scenery, cave interiors and door transitions.
Do not promote v0.0.25 to final before that check.

Use [image recovery](IMAGE_RECOVERY.md) against the original completed-terrain rc3
run to rebuild only engine and image. The strict actor gate remains enabled.
Terrain, actor fitting, water rendering and QuakeC are unchanged from rc7.
No private game assets, HDF or ROM is included.
