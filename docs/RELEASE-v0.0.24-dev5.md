# v0.0.24-dev5 — Balmora stairs, surface ordering and playtest follow-up

30 September 2026. Delivered dev4 archives remain unchanged.

## Geometry and collision

Balmora's broken-looking stair edges and door arches, and the Census courtyard's
missing wall strips, have a native surface-ordering cause. Prepared polygons are
intact. The new span generator keeps world BSP ordering and splits mesh spans
where their depth order changes between edge events. Default `aw_surface_order 2`
selects it; `dbg render order 1` retains the legacy method for comparisons.
No additional framebuffer or per-frame allocation is introduced.

A separate collision problem closes narrow stairs: approximate convex unions
fill recesses, and expanding only their face/axial planes leaves solid wedges
beside oblique edges. The Balmora conversion now preserves authored open shells
and builds complete standing-box bevels offline for the inspected b02/b04/b13/
b15/b17, dsteps03, bridge05/06/07 and temple02 models. This is reusable per-model
conversion, not a collection of invisible ramps at reported coordinates.
Normal walking checks include ascending and descending the newly reported
549,-739; -297,-1180; 1182,-141; and -527,187 approaches.
See the investigation for exact endpoints and remaining acceptance scope.

The east-bank road tile at 455,-699 has a checked source-material repair.
Terrain quad materials are sampled inside the quad instead of its last height
corner. A guard's disappearing bonemold chest was over-reduced geometry; torso
reduction now retries when too much surface area or extent is lost, within the
existing native actor limit. The inspected guard increases from 511 to 586
triangles. This does not certify all armor combinations.

## Interface and debug controls

- `dbg hud type 2` is the default compact top version/location banner, using the
  small console glyphs. `dbg hud type 1` restores the older banner.
- `dbg aw hors 0` creates Hors, a male Nord / Barbarian / The Steed, with normal
  derived attributes and post-Census state, in Seyda Neen's square. It resets
  the current debug character/world state. `dbg tp balmora` supplies this preset
  only when no character exists; an existing character is preserved.
- Appearance starts on Race. Race/Sex/Face/Hair have gold mouse-clickable arrows;
  zero mouse motion no longer steals keyboard focus. Choose remains the default
  confirmation. Review retains its page count.
- Small gold TrueType glyphs use host-side outline oversampling before AWF
  quantization, restoring the inspected o/s strokes without runtime font work.
- Shift+V remains the accepted distance shortcut. No new bare number bindings.
- `dbg input trace on/off` logs raw Amiga keys and mouse events for the reported
  birthsign regression. Native normal key dispatch changes birthsign left/right;
  the owner's cursor-only trigger has not been reproduced or certified fixed.

## Doors and residency

The Census hall door near Ganciele uses the nearest point on its full bounds
for interaction, retaining facing and line-of-sight checks. Authored DOOR open/
close sound IDs resolve through SOUN records: 114 converted entrances share ten
11025 Hz mono samples, at source volume. `dbg door sounds off/on` changes the
persistent default-on option (`aw_door_sounds`). Transition doors play their
opening sound before loading and closing sound after arrival. The hall's
existing one-way opening action plays its open sound; this adds no new close
interaction. Door sounds can add up to one second before a scene transition.

Seyda Neen's town centre now stays in one regular core, with its northern core
edge at the reported bridge Y=474. Existing 96-unit hysteresis avoids repeated
loads on the edge; the actual switch occurs beyond that margin. Twenty-five
regular regions replace thirty. The special intro pier and ring courtyard
remain. Keep the accepted frozen frame and small top Loading... box, with the
black-screen option available. Loading remains synchronous, with the existing
exterior distance cap required by overlap.

## Preserved choices and open work

Balmora's accepted dev3 Silt Strider visual model/profile is unchanged. Keep
90-degree Quake FOV, bob, the 14.64 × 14.24 × 33.25 standing hull and the selected
race/sex eye heights. Whole-map high/low polygon-density analysis remains future
roadmap work. Balmora interiors and asynchronous streaming remain unfinished.

Start a new game or Demo Game: the geometry changes the content fingerprint and
old saves are rejected. These are focused native checks, not complete citywide
or natural-opening acceptance on every machine. Validation measurements are
recorded in `INVESTIGATION-v0.0.24-dev5.md` and the delivery handoff.

## Ship collision performance

A bounds index over the ship shell's 1,205 collision pieces reduces repeated
search work while preserving the existing floor and visible geometry. At the
matched lower-cabin view on the reference accelerated emulator, median frame
time improves from 76.62 to 35.40 ms (about 13 to 28 FPS), with server time falling
from 34.33 to 1.00 ms. This is a view/host-specific measurement, not a guarantee
for all hardware or the whole intro. See the investigation for method and limits.

## Final validation

291 host tests pass without skips. The native compiler warning set remains 82
with no additions or removals. Source checks cover 675 files. All 712 payload
files are read back from the HDF and hashed. The packaged-executable route
completes 1,378 frames and 17 captures, with nine stair ascent/descent checks,
Seyda bridge crossings in both loading modes, Hors/teleport and both HUD types.
No surface/edge overflows or native error occur. Peak sampled hunk use is
10,926,416 bytes within the 11 MiB reservation. The shipped HDF is unchanged by
the diagnostic run. These checks do not replace full owner playtesting.
