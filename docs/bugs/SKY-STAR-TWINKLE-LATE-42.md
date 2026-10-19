# SKY-STAR-TWINKLE-LATE-42: Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | r_sky.c R_NightPixel twinkle; midnight clearing window; night sky star roles |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | low: Minor visual: the stars do twinkle, but only a few of them and only once the midnight clearing has opened the sky; no gameplay effect |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | 2026_10_17_v0.0.42-dev1_full-dev1-proof_5e043ad |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

On 17 October 2026 the maintainer, playing v0.0.42-dev1 at night under Masser, asked whether the small star
twinkle of earlier versions was gone: the stars looked static. A few minutes later, further into the night, he
saw some twinkling again and judged it fine: a minor visual item, possibly the sky veil.

## Where

- `engine/aga/src/r_sky.c`, `R_NightPixel`: the twinkle. Only stars marked in the night sky's star roles whose
  palette colour is bright (all three channels above 160) and whose sky texel passes `(ix*17+iy*13)%5==0` cool
  slightly and pulse by up to four fade levels over sixteen world-clock steps of 30 s (`sky_night_step`).
- The midnight clearing (`aw_nightsky_mode 1`, the default): the night clouds fade out from 23:00 to 00:00, the
  sky stays clear until 03:00 and the clouds return by 04:00.

## How it happened

Nothing in the twinkle changed: `r_sky.c` is unchanged since v0.0.32, and the night sky has had its star roles
(AWN2) since v0.0.28. Measured on the shipped night sky files (an offline replay of the engine's test on each
build's night sky and palette):

| Build | Star texels | Bright (all channels > 160) | Twinkle texels on the whole sky |
| --- | ---: | ---: | ---: |
| v0.0.35, v0.0.36 | 163 | 22 | 4 |
| v0.0.41, v0.0.42-dev1 | 163 | 18 | 3 |

So the twinkle was always small: three or four stars of the whole sky dome, all between 10 and 25 degrees above
the horizon, where town walls, roofs and trees often stand in front of them. The palette of v0.0.41 cost one of
the four. Each of them still changes its shown colour over the sixteen steps at every brightness level.

What varies by the hour is the sky in front of them. The night strength is full from 21:00 (sky type 3), so the
brightness ramp is not the cause. Before 23:00 (and again from about 03:00) the night clouds and the dithered
cloud veil cover most of the sky, and the veil itself moves: in the by-hour clips (below) thousands of sky
pixels change every half second at 21:30, 23:00 and 03:00, and none at 00:00 or 01:00 with the sky clear. The
twinkle stars show only through gaps or once the midnight clearing has opened the sky, and the veil's own
movement at 23:00-00:00 and 03:00-04:00 can read as twinkling.

## Why it was not caught

The night checks (unit tests and the night gallery clips) hold the clock still, and a still clock never moves
the twinkle step; no test checked that a twinkle star changes over the steps.

## Reproduction

Always: at Balmora, any night before 23:00 with the default sky settings, look at the sky with the clock running;
the visible stars stay steady. After 00:00 look towards one of the three twinkle stars (for example yaw 258,
25 degrees up from the Balmora benchmark camera bm1) and it pulses slowly.

## Repair

No change to the look (decided for the project, 17 October 2026: "minor visual thing"). Added, as the maintainer
asked: `aw_star_twinkle` (saved, default 1; `dbg startwinkle on/off`): 1 keeps today's pulse, 0 keeps every star
at its own steady colour. The old behaviour is the default.

## Verification

- `tests/aga_daynight_test.c` (point star fixture): with `aw_star_twinkle 1` the zenith star changes its shown
  colour over the sixteen 30 s steps; with 0 it shows one steady bright colour at every step.
- By-hour clips (FS-UAE, JIT preset, a fresh play copy of the v0.0.42-dev1 proof image with the switch engine,
  Balmora camera bm1, still first-person camera, clock running, headlamp off, twinkle on and off at the same
  hour), pixels of the 3D view that change between 2 fps frames over 10 s:

  | Hour | View | Twinkle on | Twinkle off | What moves |
  | --- | --- | ---: | ---: | --- |
  | 21:30 | yaw 258, 25 degrees up | about 3,200 per 0.5 s | about 3,200 | the night clouds and their veil |
  | 23:00 | yaw 258, 25 degrees up | about 3,200 per 0.5 s | about 3,300 | the veil fading out |
  | 01:00 | yaw 258, 25 degrees up | 6 pixels (one star) | 0 | the one twinkle star in view, about 10 % brighter and dimmer |
  | 03:00 | yaw 258, 25 degrees up | about 1,200 per 0.5 s | about 1,300 | the clouds returning |

  Masser's edge, which moves with the clock, is left out of the counts. In the clear sky at 00:00 and 01:00 with
  the camera at yaw 113, 45 degrees up, no star twinkles: none of the three twinkle stars is in that view.

## Prevention

The twinkle test runs the clock through all sixteen steps, so a change that freezes or removes the pulse fails
the suite.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- [GUARD-TORCH-CHIM-FRAMES-44](GUARD-TORCH-CHIM-FRAMES-44.md): Outdoor guards carry no torch at night: the torch step never read the CHIM frame maps
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [LAMPS-FLICKER-31](LAMPS-FLICKER-31.md): Night lamps switch on and off while turning or walking
- [LAMPS-RANGE-31](LAMPS-RANGE-31.md): Only the nearest lamps light up at night
- [LIGHT-ENTITIES-UNWIRED-33](LIGHT-ENTITIES-UNWIRED-33.md): Morrowind lights are never turned into Quake light entities, so the light compiler bakes nothing
- LIGHT-EXTERIOR-JUMP-29 (no report page): Brightness discontinuity at the reported Seyda Neen shack
- [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md): Interior lights stop dead at their radius
- LIGHT-GRADIENT-29 (no report page): Unsigned light gradients overflow during surface interpolation
- [LIGHT-NEGATIVE-31](LIGHT-NEGATIVE-31.md): Negative (darkening) lights bake as bright white light
- [LIGHT-OFF-31](LIGHT-OFF-31.md): Lights flagged Off by default would bake as lit
- [LIGHT-STYLES-UNDEFINED-33](LIGHT-STYLES-UNDEFINED-33.md): The flicker and pulse lightstyles of the light design are never defined, and styles below 32 dim with daylight
- LIGHT-UV-DISTANCE-29 (no report page): Texture scale changes dynamic-light reach on surfaces
- [NIGHT-0400-DARK-31](NIGHT-0400-DARK-31.md): Exterior suddenly much darker around 04:00
- [NIGHT-RUST-31](NIGHT-RUST-31.md): Night tint rounds dark colours to rust-red speckle
- [NPC-LIGHT-COHERENCE-32](NPC-LIGHT-COHERENCE-32.md): Characters are lit by the floor below them, not by the light where they stand
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

Related bugs in other categories:

- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder

<!-- END GENERATED CATEGORY -->
