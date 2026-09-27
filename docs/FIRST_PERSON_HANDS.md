# First-person geometry and sprite experiment

The existing 3D converter and model are retained. **3D remains the default.**
Select `build.sh --hands 3d` or `build.sh --hands sprites` at build time. The
engine and image builders accept the same flag and reject mismatched modes.
There is no in-game mode switch. The optional private `experimental/` HDF is
for comparison, not a replacement with complete equipment coverage.

Both routes use the same locally sampled Nord-male unarmed model: 311 triangles,
28 poses (8 idle, 6 draw, 4 lower, 10 punch). The 3D MDL is 252,612 bytes. The
sprite baker rasterizes each pose on the host at 160x100 and packs opaque row
spans into a 22,426-byte AWS1 file. Runtime checks bounds once and draws indexed
pixels without blending or world-depth tests; no per-frame disk read.

The compile-time sprite path uses the existing animation frame state, avoiding
the hand-model cache load. The 3D source asset remains on disk. Some sampled
draw/lower/punch poses move fully offscreen; those empty baked frames are recorded
in the report and need animation/framing refinement. This prototype is not a
complete fix for the owner's disappearance report.

First-person drawing now occurs after world fog; 3D hand ambient has a minimum
brightness floor. This prevents the world fog pass from obscuring the overlay,
but it does not prove the original flicker cause or eliminate all model/texture
issues. Native screenshots still warrant owner comparison. Sprite lighting is
a fixed neutral bake and does not yet follow the dim interior.

## Coverage gate before adopting sprites generally

Bake every required motion for the selected race/body, equipment, weapon/spell
and handedness before relying on a sprite set. Race stays fixed during play,
but armor/clothing/weapon appearance can change. Use a complete appearance key
for caching and invalidate affected frames on equipment change. Missing coverage
keeps that target on the 3D build until an explicit fallback policy exists.

Keep A/B cameras, heading, pitch, viewport, draw distance and emulator settings
identical. `hands_ms` is separately profiled; aggregate routes include hidden
hands and console time, so they are not per-visible-frame speedup measurements.
This checkpoint tests both builds functionally, not physical-Amiga performance.
