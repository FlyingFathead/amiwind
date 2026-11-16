# Study: the THEA1200 as an AmiWind target

_Last updated with AmiWind v0.0.66-dev8 (15 November 2026)._

A short look at an announced machine, written before any unit exists to test. Nothing here is measured, and nothing
is claimed to work: AmiWind has not been run on a THEA1200.

## What it is, as announced

The THEA1200 is a full-size recreation of the Amiga 1200 by its makers, announced to launch on 4 December 2026. The
makers' pages (read 13 November 2026) describe emulation of the A1200 with its AGA chipset as well as the OCS and ECS
machines, an included Workbench installation, games loaded from a USB stick with WHDLoad support, HDMI and USB
connections, and newly developed RTG support so that software can use higher-resolution screen modes. Press coverage
also describes it as built on the Amiberry emulator, with a JIT switch, selectable CPU speeds and configurable Fast RAM;
the makers' pages read for this study do not state those details, so they are treated as unconfirmed here.

Sources: [the makers' product page](https://plaionreplai.com/en-gb/products/the-a1200) and
[the Retro Games product page](https://retrogames.biz/products/thea1200/).

## Why it is a plausible target

AmiWind already runs under Amiberry: the project's Raspberry Pi 4B reference machine runs the game in Amiberry as an
AGA Amiga with a 68040, its FPU, JIT and 32 MB of Fast RAM, and the speed work is measured there
([real hardware](REAL_HARDWARE.md#raspberry-pi-with-amiberry)). A machine built on the same emulator family, with AGA
and a JIT, has the right shape. Whether it offers everything the game needs is open.

## Open questions

1. **Starting the game.** AmiWind ships as hard-disk images with their own boot, and its first partition can also be
   started from Workbench ([storage](STORAGE.md#the-boot-volume-seen-from-workbench)). A reviewer's report says the
   machine loads hard-disk images from a USB stick ([roadmap](ROADMAP.md#test-on-amiberry-21-october-2026)); the makers'
   pages read for this study do not say so, and whether AmiWind's own boot image starts that way is to be tried. If only
   Workbench and WHDLoad launching work, AmiWind would need a Workbench-launchable package of the same files: a
   packaging task, not an engine change.
2. **The emulated machine.** AmiWind needs a 68040 or 68060 class CPU with its FPU, Kickstart 3.1 or newer and 32 MB of
   Fast RAM ([requirements](REAL_HARDWARE.md)). Whether the THEA1200's settings offer those CPU models, the FPU and
   that much Fast RAM is not known yet.
3. **The speed.** The processor inside has not been named by the makers. Until it is known or measured, nothing is
   said here about frame rates, and no synthetic figures are used as a stand-in: AmiWind's frame depends on its
   software renderer, the world streaming and the FPU path, not on integer speed alone.

## The plan, once a unit is available

1. **The current AGA build as it is**, with 32 MB of Fast RAM, the fastest CPU setting, the JIT and the FPU on: read the
   start-up check's report (chipset, Chip and Fast RAM, CPU and FPU) and play the opening. Results are recorded with
   the outcome labels of the [PiStorm study](PISTORM_RTG_STUDY.md#outcome-labels).
2. **The same benchmark scenes as on the Raspberry Pi 4B**, with the same settings (`aw bench halloween` and the frame
   counters), plus the time of a cell change, so the two machines compare like for like.
3. **RTG only if the screen matters.** If the measurements show that the copy to the AGA screen takes a real share of
   the frame, the RTG display backend concept in the [PiStorm study](PISTORM_RTG_STUDY.md#a-concept-for-the-rtg-backend)
   would serve the THEA1200's RTG mode too, once its programming interface is known.
