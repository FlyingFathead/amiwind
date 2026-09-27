# AmiWind v0.0.10 / checkpoint-008 validation

27 September 2026. Public pipeline source 0.8.2; separate GPLv2 runtime.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Result and scope

Hardware and memory checks run before the C runtime/engine is loaded. Invalid
configurations return to the CLI with readable requirements and return code 20.
A direct engine launch also reports an unavailable 8 MiB Fast-memory hunk without
throwing the reproduced allocator exception. Normal launch, movement, music
controls and clean exit passed with complete A1200 KS3.1 and KS3.1.4 ROMs.

Only AmiWind, AmiWindCheck and S/startup-sequence differ from checkpoint-007.
Every world, texture and music payload was compared byte-for-byte with that
checkpoint, then every payload was read back independently from the new HDF.
All tests boot working copies; the release image is untouched.

## Identity

| Item | SHA-256 |
| --- | --- |
| HDF (134250496 bytes, 128 MiB FFS partition in RDB) | `36de896a055c1476114942ca003cf61149b3fbc0bd76f8078c8d20d5421ad27f` |
| AmiWind engine | `5e850257375270e2dfad17675ef5eabba2cca1c723c15d96c17d2984650190dd` |
| AmiWindCheck (1116-byte Hunk, 248-byte BSS) | `f46b9184687c33fb4765b7fd6895896c730c838c8530cafbdf15a56405e77580` |
| A1200 KS3.1 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| A1200 KS3.1.4 46.143 | `f797db0b99856d9c8219ee1f11e16285fd7dbdc0cbca2e149befd3a3986eb007` |
| A500 KS1.3 (rejection test only) | `ee05862d8102a08436ac4056da7d549db31625c7d47b24dfb7b3c9a5c113ca53` |
| FS-UAE binary | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |

## Reproduction and rejection matrix

FS-UAE 3.1.66 (Ubuntu 3.1.66-2build2), PAL, UAE virtual hardfile controller.
Unless overridden: A1200/AGA, 68040/internal FPU, 2 MiB Chip, 16 MiB Z3 Fast,
JIT cache 8192 KiB, maximum CPU speed, no Slow or Z2 Fast. Effective settings,
screenshots and executable/ROM metadata accompany the private checkpoint.

| Case | Observed result |
| --- | --- |
| Old v0.0.9, 4 MiB Z2 Fast, no Z3 | Reproduces Software Failure 80000027 |
| v0.0.10, same 4 MiB Fast | Memory quantities and requirements; engine not loaded |
| v0.0.10, 68020 + 68882 | CPU/FPU requirements; engine not loaded |
| v0.0.10, 68040 with no FPU | CPU/FPU requirements; engine not loaded |
| v0.0.10, ECS chipset | AGA requirement; engine not loaded |
| v0.0.10, 1 MiB Chip | Chip-memory requirement; engine not loaded |
| Checker from OFS ADF, A500/68000/KS1.3/512K Chip+512K Slow | KS3.1+ requirement; safe return to CLI |
| Direct v0.0.10 engine launch after guard rejects 4 MiB Fast | Checked heap-allocation message; clean return to CLI |
| v0.0.10, reference hardware, KS3.1 | Preflight passes; town, controls, music and exit pass |
| v0.0.10, reference hardware, KS3.1.4 | Preflight passes; town, controls, music and exit pass |

The KS1.3 test exercises only the checker. It does not make the AGA engine a
KS1.3 program. Detection calls SetChipRev(SETCHIPREV_BEST) before checking AGA;
without it a bare-ROM boot can expose uninitialized feature flags.

The guard conservatively requires approximately 2 MiB installed Chip (recognizes
OS-reserved bytes), 512 KiB free Chip and 256 KiB contiguous Chip, 12 MiB free
Fast and 10 MiB contiguous Fast before engine loading. These are budgets, not a
measured minimum. It does not test disk throughput, ROM checksums, all FPU
instructions, render speed or continuing audio deadlines.

## Functional run counters

Both runs exercised WASD, mouse look, jumping, fog presets, F6 next track,
F8 music-mode audition and Escape. ERROR.TXT was absent; return to DOS was
visually checked. The song history was 6,0,11; no adjacent repeat in either run.
These are short smoke tests, not whole-OST playback certification.

| Counter | KS3.1 | KS3.1.4 |
| --- | ---: | ---: |
| Frames | 4662 | 4022 |
| Elapsed game milliseconds | 64895 | 55957 |
| Worst frame microseconds | 44729 | 32954 |
| Hunk bytes used | 3766368 | 3766368 |
| Late audio updates | 1 | 1 |
| Missed audio frames | 1984 | 1556 |
| Music reads | 89 | 77 |
| Music read errors | 0 | 0 |
| Free Chip bytes at exit profiling | 1796432 | 1784072 |
| Free Fast bytes at exit profiling | 6113800 | 6103224 |

Other short rejection tests overlapped portions of these functional runs on the
host. They are not a matched performance comparison with checkpoint-007; retain
its baseline rather than claiming a speedup or a regression from these timings.
A late mixer update remains visible in the counters. Zero read errors is not a
claim of uninterrupted audio.

## Owner WinUAE result

The owner's saved configs identify WinUAE 6.0.3. One used only 4 MiB Fast; another
already used 16 MiB Z3. The subsequent Tester 2 config selected the complete
bundled KS3.1 ROM (CRC identity 1483A091), 040/internal FPU, 2 MiB Chip, 16 MiB
Z3 and JIT, but retained cpu_speed=real. The owner reported that v0.0.9 loaded
but ran slowly with severe repeating/broken audio. After selecting Fastest
possible, the owner reported that it ran OK. This is owner-reported v0.0.9
validation; v0.0.10 was tested locally with FS-UAE, not WinUAE.

The working profile is preserved with maximum CPU speed, a complete extracted
ROM path and the same 2/16 MiB memory configuration. JIT cache and Fast RAM are
different settings. See WINUAE.md for exact controls and path handling.

## Build and public packaging

Pinned AmiQuake commit 9c62d905151614af3e788ae3145a0d4ecc8a7bb8; upstream archive
SHA-256 43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c.
Fresh pinned patch build with AmigaPorts GCC 16.2-rc11 / compiler
16.2.0b20260825082934, -m68040 -m68881 -O1 and C span/C2P code. The new independent
checker uses vasm 2.0f, -m68000, -Fhunkexe and installed NDK definitions.
The 40 host tests pass. Native emulator cases above test the hardware branches.

Source ZIPs use an explicit allowlist, UTF-8/binary checks, member/CRC checks and
SHA-256 manifests. Public archives contain no ROMs, game assets, derived assets,
HDFs or executables. The private archive includes owner data and both complete
A1200 ROMs. Old checkpoints are retained without modification.
