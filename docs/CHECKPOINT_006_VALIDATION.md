# v0.0.8 checkpoint-006 validation

Date: 27 September 2026. Public pipeline source: 0.8.0. This is the first
AGA textured-town HDF checkpoint. The previous A500 releases remain unchanged.

## Provenance

| Item | Value |
| --- | --- |
| Emulator | FS-UAE 3.1.66, Ubuntu package 3.1.66-2build2 |
| Emulator executable SHA-256 | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| ROM | Kickstart 3.1 A1200, revision 40.68, 524,288 bytes |
| ROM SHA-256 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| Released HDF SHA-256 | `8055c8bc26340166f93179246a0a1fe96fe90822739942e413f19dca134df7d7` |
| Runtime executable SHA-256 | `7e84aca6ef26619dd5369d37cc6fa069e8a2a26cb914422ccdef640569ecb0b5` |
| HDF size | 134,250,496 bytes; 128 MiB FFS partition inside RDB |
| Filesystem payload | 63,241,412 bytes, including 18 complete music files |
| Compiler | AmigaPorts GCC 16.2-rc11, 16.2.0b20260825082934 |
| BSP tools / QuakeC | ericw-tools 0.18.1 / id Software Quake-Tools qcc |

Effective emulator configuration was checked from `debug.uae`: AGA, PAL,
`cpu_model=68040`, `fpu_model=68040`, `cpu_speed=max`, `cachesize=8192`,
2 MiB Chip (`chipmem_size=4`), no 24-bit Fast RAM, 16 MiB Zorro III RAM.
Display: 320 x 200, viewsize 120, palette fog; default draw distance 700.
The image was mounted through the UAE virtual hardfile controller. These are
maximum-speed JIT functional-test settings, not a physical 040 timing model.
The Zorro III allocation does not describe a stock A1200 expansion.

## Build and integrity checks

- Built the pinned, patched runtime from a fresh upstream extraction using the
  public build command; no extracted C2P or span assembly was compiled.
- Also compiled the separately packaged corresponding source with the documented
  compiler/flags. Time/date build strings mean binary hashes change across builds.
- Validated all 18 MWA1 streams against their conversion manifest and decoded
  their length/padding structure. Total converted music: 56,262,944 bytes.
- Read every filesystem payload back from the finished RDB HDF and compared
  SHA-256 with the input file.
- Tested a copy of the release HDF; the pristine release image remains unchanged.
- All 37 host tests passed. Tests cover format bounds, source packaging, music identity, scene data,
  independent C2P pixel equivalence and benchmark mismatch/regression rejection.

## Sustained native run

The HDF booted to the native textured scene. The input sequence exercised forward
movement, strafe, mouse look, jump input, near/far/default fog settings, natural
song completion, next-track and battle/exploration audition, then Escape.
Screenshots and coordinate logs confirmed scene rendering and position/yaw
changes. Escape returned to the DOS prompt and wrote profiling files.
This is not exhaustive collision, underwater or gameplay testing.

| Metric | Observed |
| --- | ---: |
| Frames / measured elapsed | 17,401 / 241.981 s |
| Average fps | 71.91, at the ordinary 72 fps engine cap |
| Sampled p95 frame | 15.095 ms, from 1,740 every-tenth-frame samples |
| Worst frame, all-frame counter | 1,013.507 ms |
| World / entities / C2P / audio measured stages | 95,579 / 93 / 2,834 / 92 ms |
| Hunk use / heap reservation | 3,766,368 / 8,388,608 bytes |
| Free Chip / Fast at profile shutdown | 1,796,432 / 6,113,120 bytes |
| Music data read | 5,406,720 bytes in 330 blocks |
| Read failures | 0 |
| Late mixer updates / missed audio frames | 3 / 11,646 |

Recorded song IDs: `6,0,8,5,7,11,2`; no adjacent repeated ID. The initial song
contains 191.347 seconds of PCM and was allowed to finish before the audition
keys. A held audition key can advance more than once through normal key repeat.
Track history and exact test inputs are included in the private evidence folder.

The large worst frame and late audio updates remain **known issues**, despite
the high capped average. Their cause is not yet isolated: instrument track open,
filesystem reads and profiling-file writes before choosing a fix. The stage
counters do not account for every part of a frame or the limiter's waiting time.
No statement of glitch-free playback, physical Amiga speed or minimum hardware
is justified by this run.

## Scope and next work

The scene contains a converted patch of terrain, 128 static building/object
proxies and 13 foliage sprites. It is recognizable but visibly coarse. Convex
collision blocks some openings; scaled/tilted references are omitted. The world
is resident, not streamed by chunk. Music uses synchronous bounded reads.
No NPCs, interiors, activation, quest state, combat or dialogue are implemented.

The 020/no-FPU newlib and CLIB2 executables both stopped at a missing
mathieeedoubbas.library in the bare-ROM test; neither established stock A1200
performance. The released binary requires 040/FPU-class settings. WinUAE and
physical hardware have not been validated. See [optimization history](OPTIMIZATION_HISTORY.md)
for retained candidates and [AGA setup](AGA_BUILD.md) for controls/build steps.
