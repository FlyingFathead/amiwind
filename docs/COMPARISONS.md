# Comparisons: other big PC games on the Amiga

Reference points for what AmiWind attempts: other PC role-playing and 3D games that run on Amiga hardware
today, what they need, and how fast they run. Figures are as published by their authors or sellers, with the
date they were read; AmiWind's own figures are linked to where they were measured.

## GemRB (Baldur's Gate, Icewind Dale, Planescape: Torment)

[GemRB](https://github.com/gemrb/gemrb) is a GPL re-implementation of the Infinity Engine. A commercial Amiga
package of it (AmigaOS 3 for fast 68k systems, AmigaOS 4, and WarpOS) was released in 2026 with installers for the
classic versions of Baldur's Gate 1 and 2, Icewind Dale 1 and Planescape: Torment, played from the player's own
discs or GOG copies ([seller's page](https://www.amiga-shop.net/Amiga-Software/Amiga-Spiele/GemRB-RPG-Paket-fuer-AmigaOS-3-4-WOS::1407.html),
read 16 October 2026).

Published frame rates of the 68k version, in average scenes:

| Machine | Screen | Frames per second |
| --- | --- | --- |
| PiStorm with a Compute Module 4 | 1024x768 | about 90 (frame limit off) |
| PiStorm with a Pi 3 | 1024x768 | 30 to 35 |
| Vampire V4 | 640x480 | about 20 |
| 68060 at 100 MHz | not stated | 7 to 10 |

Its stated minimum for AmigaOS 3 is a Vampire V4, with a PiStorm 3 or 4 recommended, and at least 300 MB of free
memory on the Workbench. The PowerPC versions reach 10 to 30 frames per second from an 800 MHz MicroAmigaOne to a
2 GHz AmigaOne X5000, and about 25 with WarpOS on an 800 MHz G3 or 450 MHz G4 card.

Two things make these numbers possible, and both differ from AmiWind's target:

- **A 2D engine.** The Infinity Engine draws pre-rendered backgrounds and sprites. There is no 3D world to
  transform, clip and texture every frame.
- **A graphics card screen (RTG).** The 1024x768 modes are chunky RTG screens. The frame never goes through the
  AGA chipset's planar conversion or the chip memory bus.

## What the original games asked of a PC

| Game (original release) | Processor | Memory | Graphics |
| --- | --- | --- | --- |
| Baldur's Gate II (2000), minimum | Pentium II 233 MHz | 32 MB | a DirectX 5 compatible card (2D) |
| Morrowind (2002), minimum | Pentium III, Celeron, Athlon or Duron at 500 MHz | 128 MB (256 MB on Windows 2000/XP) | a 32 MB Direct3D card with a DirectX 8.1 driver |
| Morrowind (2002), recommended | Pentium III or Athlon at 800 MHz or faster | 256 MB | GeForce 2 GTS, Radeon 7500 or faster |
| Morrowind on the original Xbox (2002) | Pentium III (Coppermine) at 733 MHz | 64 MB in total, shared by game, textures and screen | the console's NV2A 3D chip |

Morrowind's figures are Bethesda's own ([Bethesda Support: minimum system requirements for Morrowind](https://help.bethesda.net/#en/answer/17478),
read 16 October 2026). That page also asks for 1 GB of free disk space, an 8x CD/DVD drive and a DirectX 8.1 sound
card, and lists the supported 3D chipsets of the time, from the TNT2, Rage 128 and Matrox G400 up to the GeForce 4
and Radeon 8500.

The Xbox figures are the console's published hardware ([Xbox technical specifications](https://en.wikipedia.org/wiki/Xbox_technical_specifications),
read 16 October 2026). The Xbox version is the closest precedent for AmiWind's memory problem: the same island,
streamed through a fixed 64 MB that also held every texture and the screen, about a quarter of the PC's
recommended memory. It still had a dedicated 3D chip and a processor several times faster than any 68k.

Morrowind asked for about twice the processor of Baldur's Gate II, four to eight times the memory, and a 3D
accelerator, which Baldur's Gate II did not need at all. An Amiga has no 3D accelerator in that sense: AmiWind
does all of Morrowind's 3D drawing on the 68k processor.

## What this means for AmiWind

- **The fast-CPU route works.** On PiStorm-class hardware even a 2000-era PC role-playing game runs smoothly at
  high resolution. AmiWind's [FAQ](FAQ.md#why-not-use-pistorm32-rtg-and-minigl) describes what PiStorm, an RTG
  screen and MiniGL would each change for AmiWind.
- **A 68060 at 100 MHz is the shared reference point.** GemRB reaches 7 to 10 frames per second there for a 2D
  game. AmiWind draws a 3D world in software on the CPU and writes every frame through AGA. A tester's first
  real-hardware run of an earlier build on an A4000 with a 68060 at 100 MHz gave about 0.2 frames per second
  (14 October 2026; [CHIM-SLOWCPU-FRAMETIME-33](bugs/CHIM-SLOWCPU-FRAMETIME-33.md)).
- **Today the 3D work is the limit, not the screen.** At 0.2 frames per second a frame takes about 5 seconds,
  while even a cautious estimate of the AGA screen ceiling allows several frames per second at full screen. Most of
  AmiWind's frame is spent drawing its many separate scenery models (57 % of a slow Balmora frame in v0.0.33's
  measurements), which is why the [68060 work](68060.md) starts with the brush-model clipping.
- **On AGA the screen has its own ceiling.** Writing a full 256-colour frame through the chip memory bus costs
  time that no CPU upgrade removes; an RTG screen avoids it, as GemRB's high-resolution modes do. How much of
  AmiWind's frame that is gets measured separately from the 3D work (the Chip RAM write test of
  [awbench](HARDWARE-BENCHMARK.md) and a screen-copy-only test per screen size).
- **The same discipline applies.** GemRB's package ships executables tuned for specific machines and installs the
  game from the player's own discs. AmiWind builds from the player's own copy of Morrowind, and its
  [68060 work](68060.md) follows the same idea: one baseline that always works, and builds tuned for faster CPUs.
