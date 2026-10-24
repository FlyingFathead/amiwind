# Emulator presets

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

> **Placeholder.** This page is filled when the slow-accelerator FS-UAE preset
> is merged. Today the emulator setup is in the
> [FS-UAE guide](../../FS-UAE-PLAYTESTING.md) and the [WinUAE guide](../../WINUAE.md).

## Fast RAM

Play presets, playtest packages and the playtest launcher start with 32 MiB of Zorro III
Fast RAM, the safe minimum for the whole game (since 23 October 2026; 128 MiB from
21 October, 16 MiB before; [why 32 MB](../../REAL_HARDWARE.md#why-32-mb-of-fast-ram)).
More is used automatically. The launcher also offers 16 MiB (starts with a warning, loads
more often), 64 MiB, 128 MiB (like a 68060 accelerator card), 256 MiB,
512 MiB, 1 GiB, 1.5 GiB (the most FS-UAE 3.1.66 and WinUAE give) or a custom size,
checked against what the emulator can make. The measurement presets keep 16 MiB,
so their figures stay comparable with the earlier ones. Sizes, limits and the
keys written: [Fast RAM](../../FS-UAE-LAUNCHER.md#fast-ram).

Back to the [CHIM build guide](README.md).
