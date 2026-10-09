# INTERIOR-LIGHT-29: brightness controls and performance coverage

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 4 October 2026, in v0.0.28 |
| Where | Converted interiors (local light sources) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.28, v0.0.29-rc2 (last seen) |
| Severity | medium: Interiors look bleak with no convincing local light sources; cause not yet audited. |
| Family | Lighting, lamps and night (`lighting-night`) |

<!-- END GENERATED FACTS -->

Status: controls and bounded native checks pass in v0.0.29-rc2; broader
performance acceptance remains open. This measurement does not close other
lighting or Temple geometry issues. Publication is tracked separately.

## Latest visual feedback: 6 October 2026

During the RC2 playtest, the player reports that luma is much more tolerable
with the current settings and describes the game as more tolerable in luminance. The exact factor was not supplied. This supports
a subjective visual improvement without identifying a new default or closing
static-NPC sampling, broader performance, RAM or physical-hardware coverage.
The defaults remain interior 1.2x and exterior 1.0x.

## Measurement identity and method

Measured on 2026-10-06, 18:56:18-18:56:30 UTC. Engine SHA-256:
`c3a3a6243e01b0e96ce9b0a30aa39224d39601dd1a08d12b2e26b9d0af620194`.
Source-tree measurement identifier:
`33f643c5cc0c5e0ae3dc92081e60f8b6e241cc03e68f5579fc202f505bb6e5cc`.

FS-UAE ran the AGA/68040 executable at 320x200, using the ordinary Census
arrival (logged spawn local XYZ 3 -33 65), fixed clock 10:21, torch off,
unchanged pose and emulator settings, warp off and actual audio active.
Three pairs alternated 1.0x then 1.2x in one enabled executable. Each
`timerefresh` renders a 128-frame full rotation including video update.
This is a renderer workload, not the normal gameplay frame loop. A background
backup remained active; builds/compression were held during the sample.

| Pair | 1.0x rotation (s) | 1.2x rotation (s) |
| --- | ---: | ---: |
| 1 | 1.175745 | 1.195214 |
| 2 | 1.153869 | 1.189845 |
| 3 | 1.189768 | 1.148743 |
| Median | 1.175745 | 1.189845 |

Median relative increase: 1.199%; difference divided by 128: 0.110 ms/render.
Overlapping values and only three pairs limit the inference. These figures
are not physical-Amiga FPS, a statistical guarantee, or a zero-cost result.
They compare scaling factors in the same enabled build, not feature enablement.
No allocation measurement was made. A first overlong console batch was
truncated and excluded; the complete six-sample batch above was retained.

Reproduction: enter Census, hold clock/camera/torch and host workload steady,
then alternate `dbg luma interior 1.0; timerefresh` and
`dbg luma interior 1.2; timerefresh` three times using short console lines.
Capture the complete log, restore 1.2 interior / 1.0 exterior and normal clock,
quit cleanly, and read back saved settings. Keep original input assets fixed.
The live menu also demonstrated 1.2 -> 1.3 -> 1.2. Configuration readback
confirmed `aw_interiorluma "1.200000"` and `aw_exteriorluma "1"`.

## Remaining acceptance

- Compare normal gameplay frame times, cache rebuilds and worst cases across
  representative interiors, NPCs, moving torches and exterior night scenes.
- Compare the enabled build with `--no-luma-controls` under matched conditions.
- Measure on intended Amiga hardware and account for state/binary/RAM overhead.
- Preserve separate static-world, static-NPC and dynamic-torch behavior; avoid
  a second torch multiplier or unnecessary cache invalidation each frame.

The default remains interior 1.2x and exterior 1.0x. Both opt-out spellings
`--disallow-luma-controls` and `--no-luma-controls` remain supported. Older
building-only and debug-only proposals in dated notes are historical.

[Brightness controls](../INTERIOR_LIGHTING.md) |
[Raw samples](../benchmarks/interior-luma-rc2-20261006.json)

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [LAMPS-FLICKER-31](LAMPS-FLICKER-31.md): Night lamps switch on and off while turning or walking
- [LAMPS-RANGE-31](LAMPS-RANGE-31.md): Only the nearest lamps light up at night
- [LIGHT-ENTITIES-UNWIRED-33](LIGHT-ENTITIES-UNWIRED-33.md): Morrowind lights are never turned into Quake light entities, so the light compiler bakes nothing
- LIGHT-EXTERIOR-JUMP-29 (no report page): Brightness discontinuity at the reported Seyda Neen shack
- [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md): Interior lights stop dead at their radius
- LIGHT-GRADIENT-29 (no report page): Unsigned light gradients overflow during surface interpolation
- [LIGHT-NEGATIVE-31](LIGHT-NEGATIVE-31.md): Negative (darkening) lights bake as bright white light
- [LIGHT-OFF-31](LIGHT-OFF-31.md): Lights flagged Off by default would bake as lit
- LIGHT-UV-DISTANCE-29 (no report page): Texture scale changes dynamic-light reach on surfaces
- [NIGHT-0400-DARK-31](NIGHT-0400-DARK-31.md): Exterior suddenly much darker around 04:00
- [NIGHT-RUST-31](NIGHT-RUST-31.md): Night tint rounds dark colours to rust-red speckle
- [NPC-LIGHT-COHERENCE-32](NPC-LIGHT-COHERENCE-32.md): Characters are lit by the floor below them, not by the light where they stand
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
