# Interior and exterior brightness

## RC2 brightness measurement: 6 October 2026

Recorded after the RC2 source snapshot was sealed. This is follow-up
documentation for v0.0.29-rc2; the measured executable was not rebuilt for
these notes. This checkpoint supersedes earlier debug-only/default-1.0 plans.
RC2 enables controls by default: interior 1.2x including NPC static light,
exterior 1.0x, with six Options > Graphics steps from 1.0 to 1.5. Live
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
Options > Graphics offers six steps: 1.0, 1.1, 1.2, 1.3, 1.4 and 1.5.
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
