# INTERIOR-LIGHT-29: brightness controls and performance coverage

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
