# Planned day/night cycle and sky

Status: roadmap design for AmiWind; **not implemented in checkpoint-015**.
The goal is a crude but coherent impression of Morrowind's lighting. No global
illumination is proposed. The dim prison-ship opening is the first local-light
acceptance scene; see [Seyda Neen journal](journals/SEYDA_NEEN.md).

## One world clock, separate presentation

Maintain one game-time state for progression, waiting, saved state and eventual
NPC/quest conditions. Exterior ambient shading, fog, sky and sun/moon presentation
read that state. Interior lighting stays independently authored. Avoid a global
screen fade that also darkens the console or makes every interior follow noon.
Exact source transition hours, calendar behavior and time-dependent quest checks
must be audited from the user's installation and relevant OpenMW behavior before
we claim compatibility. A temple/time-of-day quest is a useful future regression
case; do not implement its condition by testing the rendered sky color.

## Planned debug interface

All commands below are proposals, not current console handlers. Keep names free
of underscores and list supported forms in `debug help` (or `dbg help`) when implemented.

| Proposed command | Behavior |
| --- | --- |
| `debug daycycle dawn` | Set the shared clock to the configured dawn test hour |
| `debug daycycle day` | Set it to the configured daylight test hour |
| `debug daycycle evening` | Set it to a late-day test hour before dusk |
| `debug daycycle dusk` | Set it to the configured sunset/twilight test hour |
| `debug daycycle night` | Set it to the configured night test hour |
| `debug daycycle hour 5.5` | Set an exact fractional hour in [0,24) |
| `debug daycycle freeze on` | Freeze clock progression for repeatable captures |
| `debug daycycle freeze off` | Resume normal progression |
| `debug daycycle status` | Report date/hour, freeze state, phase and presentation settings |

Reject invalid values without changing state. Presets map to documented,
configurable hours, not separate unrelated brightness flags. Preserve date on
an hour override. Specify forward/backward time-jump handling before quest or
schedule evaluation is attached; no accidental duplicate triggers or forced
quest advancement. Natural progression must handle midnight/date rollover.

## Cheap visual candidates to measure

1. Host-build a small set of indexed ambient/shading and fog lookup tables for
   key phases. Update lighting at a bounded rate; blend or quantize transitions
   according to measured CPU/RAM cost. Keep material palette and UI semantics
   coherent. Do not assume a palette change can independently shade pixels that
   share one palette entry across sky, world and interface.
2. Extract the installed game's sky resources locally, verify their source
   mapping, and downsample/quantize an exterior sky backdrop. First test a small
   star texture with yaw rotation/scrolling and a simple horizon gradient.
   No full-screen per-frame perspective texture warp is required for this trial.
   Use two presentation components: the whole sky background changes its base
   tone with time, while a local warm horizon region follows the low sun.
   Coordinate the base tone with fog and exterior ambient shading so the scene
   reads as dawn/sunset rather than a colored patch on a daytime sky.
   For dawn/dusk, precompute reddish-orange horizon ramps centered on the sun
   direction, fading toward the rest of the sky. Use the audited original solar
   timing/direction and the viewer yaw; do not keep the warm patch fixed on screen
   as the player turns. Quantize phase/azimuth and test seams/banding at the
   target palette. This is a painted lighting impression, not atmospheric scattering.
3. Test a tiny sun disc with a precomputed indexed gradient or dithered halo.
   Move it using a time-to-direction lookup, matching audited original day/night
   timing. Clip it behind terrain/buildings and below the horizon; avoid full-screen
   blending, real-time light scattering or global illumination. Profile its
   shaded pixel count and draw cost independently.
4. Test separate low-resolution moon layers and sparse clouds only after the
   base night sky has a measured budget. Preserve their source appearance where
   affordable; precise lunar/calendar behavior is a later audited requirement.
5. Draw sky only in the renderer's sky/background regions. Buildings and terrain
   must occlude it; interior ceilings must not leak sky. Match horizon fog to sky
   color through dawn/dusk and keep the culling boundary behind opaque fog.

These are implementation candidates, not performance guarantees. Compare sky
pixels/frame, CPU time, memory bandwidth, decoded RAM and disk bytes against a
flat-color baseline. Precompute phase/rotation tables on the host where useful.
Only the required sky working set should be resident; avoid one enormous frame
sequence whose disk size hides an unacceptable read/decode budget. No copied
commercial sky textures, renders or converted backdrops belong in public source.
The user supplies Morrowind; the converter generates private output locally.

## Acceptance route

- Capture the same exterior camera at dawn, day, evening, dusk and night with
  frozen time. Check stars/moon silhouettes, horizon seams, palette banding,
  readable doors/actors and UI. Include a camera turn and an occluding building.
- Compare dim ship interior with exterior and test transitions without palette
  flashes, black crush, missing surfaces or audio stalls.
- Profile matched routes on identical emulator/hardware settings and record
  lookup sizes, sky/fog/lighting time, peak memory and audio deadlines.
- Test midnight rollover, exact-hour overrides, invalid commands and persistence
  once clock state exists. Later test waiting/schedules/quest time windows against
  owned source behavior. Presentation approximation must not redefine game rules.

## Recovered sky fallback and guard-torch request

Day/night and sun remain unimplemented in checkpoint-016. Planned `dbg sky on/off`
(and true/false, 1/0) controls enhanced sky presentation only. Off restores the
existing starter background; the clock, schedules and quest conditions continue.
Retain this baseline for A/B tests and low-cost fallback. No new handler is claimed.

Night guards need audited torch equipment/ignition state and source light metadata.
Start with a bounded flame representation and a small measured light budget. Keep
light radius, affected surfaces, update rate and actor count explicit; profile
palette/indexed shading and audio deadlines. Do not allocate an unbounded dynamic
light per actor or infer a full night schedule from a remembered screenshot.
