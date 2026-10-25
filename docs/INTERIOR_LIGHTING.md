# Interior and exterior brightness

_Last updated with AmiWind v0.0.51 (25 October 2026)._

## Interior sunlight and the 1.0 default: 25 October 2026 (v0.0.51)

Every interior cell has a "sunlight" colour, and the original lights the room with it as one directional light
from a fixed direction, as well as with its ambient and lamps. Our interiors were baked without it, which is why
many rooms were dimmer than the original, and why the interior brightness default was 1.2. From v0.0.51 the bake
includes the cell sunlight ([INTERIOR-SUNLIGHT-UNBAKED-51](bugs/INTERIOR-SUNLIGHT-UNBAKED-51.md)), and the interior default is back to 1.0, the
original light. The prison ship keeps the light it was judged with. The controls stay: Options > Video > Graphics
and `dbg luma interior` set 1.0 to 1.5 as before, and saved settings still override the default. At 1.0 the
multiplier does no work.

### What this taught us: every light input first, then any brightness knob

The light of a converted room looked "off" for weeks, and each time it was tuned: a 1.2 brightness default for all
interiors (RC2, [INTERIOR-LIGHT-29](bugs/INTERIOR-LIGHT-29.md)), per-room profiles, a darker census office. The
cause was an input the bake never read. A global multiplier on top of a missing input lifts every room by the same
amount, so rooms that live on the missing light stay too dark and the others get too bright.

The rule from here on, for any lighting that looks wrong against the original:

1. List every light input the game data holds for the place: the cell's ambient colour, its sunlight colour (a
   directional light in interiors), its fog, each placed light (colour, radius, flags) and glowing surfaces.
2. Check that the bake and the engine use each one, and in what form (brightness only, or colour too).
3. Compare with the original or OpenMW at the same place and pose, and record which inputs the comparison had.
4. Only then tune; a per-room profile records which inputs it was judged with (the prison ship's says it was judged
   without the sunlight).

What is still left out is in the bug register: the light colour is baked as brightness only, except warm lamps
([INTERIOR-SUNLIGHT-COLOUR-51](bugs/INTERIOR-SUNLIGHT-COLOUR-51.md)), and placed lights without a mesh give no light
on CHIM exteriors ([CHIM-MESHLESS-LIGHTS-33](bugs/CHIM-MESHLESS-LIGHTS-33.md)).

The bug register is what made the cause findable: INTERIOR-LIGHT-29 recorded why the 1.2 default was set, and
[CENSUS-OFFICE-BRIGHT-32](bugs/CENSUS-OFFICE-BRIGHT-32.md) recorded OpenMW's numbers for the census office, which
already include its sunlight, so the office's excess light had to come from the bake itself. Findings go into the
register the day they are made, with their numbers and how they were measured.

## RC2 brightness measurement: 6 October 2026

Recorded after the RC2 source snapshot was sealed. This is follow-up
documentation for v0.0.29-rc2; the measured executable was not rebuilt for
these notes. This checkpoint supersedes earlier debug-only/default-1.0 plans.
RC2 enables controls by default: interior 1.2x including NPC static light,
exterior 1.0x, with six Options > Video > Graphics steps from 1.0 to 1.5. Live
`dbg luma interior 1.3` works; both settings saved correctly after clean exit.

In the Census Office, three alternating `timerefresh` pairs gave median
128-frame rotation times of **1.175745 s at 1.0x** and **1.189845 s at 1.2x**:
**+1.199%**, or approximately **+0.110 ms per rendered frame**. The individual
samples overlap; this small experiment does not isolate the multiplier's
cost from measurement noise. Do not present these values as whole-game FPS,
physical-Amiga performance, zero overhead, or a controls-enabled/disabled A/B.

The renderer reuses its surface-light buffer and cached lighting calculations;
NPC static-light scaling remains separate from dynamic torch light. This adds
no new per-room lightmaps or full-screen pixel pass. Enabled state/checks still
exist at 1.0x. RAM overhead was not measured. The disabled build compiled, but
its native performance was not compared.

See [method and raw measurements](bugs/INTERIOR-LIGHT-29.md) and the
[machine-readable samples](benchmarks/interior-luma-rc2-20261006.json).
Broader gameplay frame-time, torch/night, other interiors and physical-Amiga
checks remain open. Brightness does not repair the separate Temple holes.

For v0.0.29-rc2, brightness controls are enabled by default. All gameplay
interiors use 1.2x static light by default, including NPC static lighting.
Exterior brightness is separate and defaults to the original 1.0x balance.
Options > Video > Graphics offers six steps: 1.0, 1.1, 1.2, 1.3, 1.4 and 1.5.
Settings are archived as `aw_interiorluma` and `aw_exteriorluma`.

Use `dbg luma interior 1.3` or `dbg luma exterior 1.1` for live adjustment.
Omit the value to query the setting. Console diagnostics accept 0 through 4;
the player sliders use only the six steps above. Existing interior aliases
remain supported. Values are relative to original static lighting, not compounded.
Dynamic torch lighting is added separately. Debug torchtest remains excluded.

Build with `--disallow-luma-controls` or its alias `--no-luma-controls` to omit
brightness settings, scaling and menu rows. A small explanatory handler remains:
"Can't adjust interior luma: built without luma controls."
The exterior command reports the corresponding message. Legacy enable flags
`--debug-luma` and `--interior-brightness` remain accepted.

Scaling reuses the existing surface-light buffer when cached lighting rebuilds,
plus NPC static-light samples. It adds no per-room lightmaps or screen-pixel pass.
Enabled controls still require state and checks even at 1.0. Native performance
measurement remains pending; no zero-cost claim is made.

Matched Temple and Census previews at 1.0, 1.1, 1.2 and 1.3 were captured from
one earlier candidate executable using live console commands in Docker FS-UAE.
Returning Temple to 1.0 reproduced its baseline image byte for byte. This is
brightness evidence, not acceptance of the separate Temple geometry defect.
