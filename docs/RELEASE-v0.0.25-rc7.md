# AmiWind v0.0.25-rc7

Complete public source update from rc6. Reuse the completed rc3 terrain run
through [image recovery](IMAGE_RECOVERY.md); this checkpoint rebuilds the engine
and final image contents without changing world-terrain geometry or water.

- Fit NPC idle-mesh contact to converted support, keeping original coordinates
  as metadata and identical overlap copies. Runtime placement preserves the
  certified initial point. The independent strict contact gate stays enabled.
- Use the game's original CELL/REGN records for region names beside the optional
  heading HUD and at the bottom right of the ordinary map. No inferred region
  names or manually drawn boundaries.
- Add `dbg tp map`: select a red crosshair, then confirm with TELEPORT.
- Draw the existing sky in uncovered outdoor background pixels instead of the
  pale solid clear colour. This targets the fog-off pale-background report;
  it does not certify that every terrain seam has been resolved.
- Add the F-then-V [placeholder torch](TORCH.md) and correct dynamic-light
  coordinates on translated/rotated brush models. Shift+V stays unchanged.
- Document [character progression states](CHARACTER_STATES.md), including the
  original Dreamer startup/quest enable behavior. General quest-driven actor
  presence is still missing and is not repaired by grounding.

See [validation evidence](validation/rc7-source.json) for the checks actually
run. Host regression tests, a native engine compile and an asset-free HDF are
separate from a complete game-image build and an emulator playtest. The private
contact fixture is checked with the unchanged strict audit; no waiver or new
airborne exception is used. Torch performance, map interaction and sky rendering
still require target playtesting. Compiler warnings are retained in build logs.

World profiling, persistent conversion caching, native Windows/MSYS2 setup,
GPU conversion and optional bundled QCC remain roadmaps. This release introduces
no terrain rebuild speedup, general incremental-build system or Windows support
claim. No converted game assets, private image or ROM is distributed.
