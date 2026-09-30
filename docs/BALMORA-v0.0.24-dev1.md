# Balmora exterior — v0.0.24-dev1

This checkpoint starts from the owner's `amiwind-2026-09-30_120052.zip` (v0.0.23).
The earlier failed-session ideas have been recovered as a development direction:
keep complete placements, bound residency with smaller cells, cross boundaries
in both directions, preserve mutable residents, and move expensive work offline.
This is the first synchronous implementation, not a claim of seamless streaming.

## Implemented

- Audit the nine source exterior cells around (-3, -2). Retain the full 1,532-reference
  catalogue and classify references that do not yet have runtime simulation.
- Convert all 1,488 selected model-bearing scenery references and their 226 source
  models. No per-cell nearest-object or entity-budget truncation is used.
- Build 64 cores, each 768 local units wide, with 1,024 units of overlapping
  terrain and whole-object bounds selection. Local scale is one quarter of source
  coordinates. The source rectangle spans 6,144 by 6,144 local units.
- Keep immutable scenery outside the 600-edict pool. Rendering and collision
  share the placement catalogue. Preserve rotated collision and world-hit identity.
- Use authored collision where available; otherwise use the existing approximate
  convex conversion. Visual simplification does not simplify collision sources.
- Convert all 18 humanoid placements / 15 appearances, original outfits and
  bounded generic greeting voices. Enlarged skin atlases support armour that
  resists the normal triangle target, within native alias vertex limits.
- Darvame's Balmora choice and Selvil's Seyda Neen return use original DODT travel
  coordinates. Other destinations retain the unavailable response. No fare is
  charged in this development checkpoint.
- Reload the owning BSP after crossing a core plus 96-unit hysteresis. Shared
  coordinates preserve player position, view direction and velocity. The current
  save mechanism carries actor reference IDs, position, angles, health and greeting
  counters across reloads, including exploration mode. The actor capacity is 128.
- Balmora keeps logical save scene ID 16 across every sub-cell. Existing IDs are
  unchanged. Content fingerprints include every sub-cell and the region directory.
- Display original exterior door destination names; their interiors are pending.
  The normal build pipeline now includes the Balmora conversion stage.

## Limits and follow-up

Boundary loading is synchronous and visibly pauses. There is no second resident
world, background prefetch, distant impostor tier, or height-based residency yet.
The coverage margin is designed for the default view and 540-unit fog distance;
Balmora caps larger draw-distance settings at 540 without changing the saved
setting for other scenes. Unusual debug FOVs and disabled fog are not certified.
The nine-cell source rectangle has a finite enclosing boundary.

Ten source markers are nonvisual. One placed creature and fifteen leveled-creature
references are catalogued but not simulated. Containers and activators have their
placed appearance/collision, not their eventual interaction logic. Lights have
placed geometry and the current basic ambient lighting, not a full lighting model.
NPCs currently idle and greet; combat, pursuit, wandering and service AI are not
implemented. Future AI state, navigation and cross-cell pursuit need a broader
actor-state schema. Current greeting playback can be interrupted by a reload.

The next steps are broader walking boundary traversal and stair/roof collision
inspection, then asynchronous geometry residency and distant representations.
Keep the full source catalogue as the coverage authority when changing budgets.

## Verification

- 276 host tests pass, including native C fixtures for 700 static placements,
  rotated collision, two-way ownership/hysteresis and both Strider menu routes.
- All 64 BSP payloads validate and contain 18 stable resident seeds. The largest
  sub-cell has 729 scenery placements; maxima are 188 inline models, 40,713
  clipnodes and 4,992,892 pre-resident BSP bytes. The coverage union loses no
  selected scenery references.
- Native 68040/FPU build: 85 warnings versus 87 in the same-toolchain v0.0.23
  baseline. No new warning diagnostic; two existing indentation diagnostics removed.
- FS-UAE, A1200, 68040/FPU, JIT, 2 MiB chip + 16 MiB Z3: arrival settled at
  (-209, -1486, 287), in walking mode. A scripted noclip crossing from bm019 to
  bm020 and back preserved the requested positions. Measured synchronous loads
  were 357 ms and 345 ms, with hunk use 9,322,752 and 9,287,952 bytes inside the
  unchanged 11 MiB heap. These are accelerated emulator results, not stock hardware
  timings or a walking-route certification.
- Nine shared-boundary standing-hull traces matched in both BSPs. The original
  travel point has a supporting platform at player-origin height 287.875.
- Native frames were captured and inspected. Full-city walking, every cell load,
  doorway/stair coverage, hardware performance and audible continuity remain
  unverified. Off-screen emulation used a null host audio sink. Resident model
  cache misses still need performance work in dense views.

Source-only archives exclude converted game data, ROMs and disk images.

## Rebuild and owner workflow

Use the usual `./build.sh --stage aga` workflow with owned source data and the
configured native toolchain. The `balmora` stage runs after `area`, before
`character`; its work and reports are outside the repository. Failed format or
model budgets stop the build. Resume requires the same source master, archive,
loose geometry/textures and conversion coordinate system.

The incremental archive is relative to the uploaded v0.0.23 source, not an older
recovery ZIP. Inspect its manifest before overlaying it. Run the tests and
`python3 tools/release.py --check`, review `git diff --check` and `git diff`, then
commit/push with the owner's normal GitHub workflow. Nothing has been pushed.
