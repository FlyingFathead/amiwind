# WinUAE setup

Official homepage and downloads: [WinUAE](https://www.winuae.net/).

## Public versioned preset

Load [AmiWind-v0.0.17-WinUAE.uae](../resources/emulators/AmiWind-v0.0.17-WinUAE.uae)
from WinUAE's Configurations panel. It sets the development machine below and
opens the GUI. It deliberately leaves the ROM path empty and mounts no disk.
In ROM, select your complete licensed A1200 Kickstart 3.1 ROM. In CD & Hard
drives, add your locally generated `AmiWind-v0.0.17.hdf` as an RDB hardfile
on the UAE controller, then save a private configured copy and Start.

To produce the playable HDF, follow the [Linux](LINUX_BUILD.md) or
[Windows / WSL build guide](WINDOWS_BUILD.md) with your own Morrowind files.
The public source ZIP contains the preset, not a playable HDF or Kickstart ROM.
The separate `AmiWind-v0.0.17-dry-run.hdf` boots only to a test notice.

The preset contains no personal Windows paths, device identifiers, ROMs or
game data. Its description and filename identify the development version.
It is configuration guidance for WinUAE 6.0.3 based on the prior owner config;
local execution tests use FS-UAE 3.1.66. Do not treat it as proof of a local
WinUAE run or stock A1200 speed. See [v0.0.16 validation](VALIDATION-v0.0.16.md)
for the tested machine and scope. Historical startup thresholds and owner
reports remain below for comparison.

The v0.0.23-dev2 preflight requires 14 MiB free Fast RAM before loading the
engine, including a contiguous 11 MiB heap plus 16 bytes for alignment. The
expanded town and interiors use this larger heap; the hardware preset remains
16 MiB Fast RAM.
The historical 10 MiB contiguous threshold falsely rejected a usable fragmented
pool; it is distinct from the current measured heap requirement. Type `amiwind` at the DOS prompt
to restart; run `AmiWindCheck` separately for diagnostics. The current private checkpoint
contains the tested KS3.1 ROM only, not every ROM listed in historical records.

## Mouse works, but WASD cannot move at initial spawn

Dev3's nominal player start overlaps converted collision. The owner escaped
with noclip; a fresh native test reproduced the same lock. Dev4 finds grounded
standing space with room to step in every direction. Use the new image, keeping
your working ROM. For the old image: F10, `noclip`, close the console, move clear
of the obstruction, then toggle `noclip` again. This is a workaround, not a key
binding fix. See [checkpoint-011](CHECKPOINT_011_VALIDATION.md).

The owner resolved the reported ROM/flicker startup issue with their correct
licensed ROM. Its effective checksum is not yet recorded. The packaged test ROM
has been byte-checked against the earlier package and has a valid checksum; no
ROM modification is part of dev4.

## “Error validating AMIWIND / Block 1146049281 out of range”

The earlier image builder wrote `DOS1` into a reserved legacy root-block field.
Its numeric value is exactly the reported block number. A dirty-bitmap copy of
the shipped dev2 image reproduced the requester; correcting this field allowed
the same native filesystem to revalidate. A clean ZIP extraction postpones that
failure but retains the defective metadata. Use the corrected dev3 image.

This does not establish what originally dirtied the owner's volume. See
[diagnosis and targeted copy repair](FILESYSTEM_REVALIDATION.md). Keep the
original archive; never attempt repair on the only copy. This repair does not
require changing the known-working ROM or increasing memory.

## Reference settings and historical v0.0.10 / checkpoint-008 record

Start with the A1200 Quickstart template, then customize it. The **4 MB Fast
RAM expanded** preset is too small for this build. A profile name containing
"040/FPU+JIT" does not change any hardware settings.

| Panel | Setting for the reference configuration |
| --- | --- |
| Chipset | AGA, A1200, PAL; both Cycle-exact boxes off |
| CPU and FPU | 68040; CPU internal FPU; MMU none; 24-bit addressing off |
| CPU speed | Fastest possible |
| JIT | On; 8 MB cache; FPU support on |
| RAM | 2 MB Chip; Z2 Fast none; **Z3 Fast 16 MB** |
| Other RAM | Slow, Processor slot and 32-bit Chip: none |
| ROM | Complete extracted A1200 KS3.1 or KS3.1.4 ROM; see hashes below |
| CD & Hard drives | New HDF, UAE controller, RDB autodetection; eject floppy images |
| Input | Mouse on port 0; no keyboard joystick mapping consuming movement keys |

The JIT cache is host-side translation storage. Increasing it does **not** add
Amiga Fast RAM. `chipmem_size=4` in a UAE text config means 2 MiB Chip; the unit
is 512 KiB. `z3mem_size=16` means 16 MiB Z3 RAM. Z3 RAM is the emulator reference
arrangement, not an expansion available inside a stock A1200.

Save the customized profile under a new name, restart the emulation from that
saved profile, and do not reapply a Quickstart preset afterward. Browse to the
ROM and HDF if paths in a supplied profile differ from your extraction folder.
Use a working copy of the HDF. Choose Escape > Exit, confirm, and wait at the DOS prompt
before closing the emulator.

The startup now prints `Loading AmiWind v0.0.10...`, checks CPU/FPU, OS version,
AGA and actual available memory, and stops with return code 20 if unsuitable.
It prints installed, free and largest contiguous Chip/Fast pools in KiB.
The conservative gate requires an approximately 2 MiB installed Chip pool,
512 KiB free Chip (256 KiB contiguous), 12 MiB free Fast and a 10 MiB contiguous
Fast block before loading the engine. These are startup budgets, not measured
minimum game requirements. Use the 2/16 MiB reference for this checkpoint.
The check does not certify FPU instruction emulation, disk speed or frame rate.

### ROM selection

The owner package supplies two complete, previously tested ROM files:

| File | Revision | SHA-256 |
| --- | --- | --- |
| `roms/kickstart-3.1-a1200.rom` | 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| `roms/kickstart-3.1.4-a1200.rom` | 46.143 | `f797db0b99856d9c8219ee1f11e16285fd7dbdc0cbca2e149befd3a3986eb007` |

Use the complete emulator ROM directly. Physical ROM-programming `-lo.bin`
and `-hi.bin` files require the correct reconstruction; a ZIP-member path alone
does not establish which effective ROM an emulator ultimately loaded. A reported
crash while selecting a split file is not proof that the ROM caused it.
No ROM bytes are included in public source. The AGA engine requires KS3.1+
under this checkpoint's guard; the KS1.3 A500 demo remains separate.

### Failure report from 27 September 2026

Two owner-supplied configs identify WinUAE 6.0.3. One had 4 MiB Z2 Fast and no Z3
RAM; the other had 16 MiB Z3 Fast. Both selected a split ROM member, real CPU
speed, JIT cache 16 MiB and 040/internal FPU. Do not describe both as low-memory
configs: the second already had the requested capacity.

The exact `80000027` requester was reproduced in FS-UAE by reducing v0.0.9 to
2 MiB Chip + 4 MiB Fast. The 16 MiB case, including its 0x40000000 Z3 mapping
and real CPU speed, rendered the town with the complete KS3.1.4 ROM in FS-UAE.
The owner subsequently reported that v0.0.9 loaded in WinUAE 6.0.3 after selecting
the complete bundled KS3.1 ROM with 16 MiB Z3 RAM. The submitted "Tester 2"
configuration still had `cpu_speed=real`; the owner reported severe audio
repetition/breakup and low speed. Set CPU and FPU > Fastest possible and restart.
The owner then selected Fastest possible and reported that it ran OK. This is
an owner-reported v0.0.9 result, not a local WinUAE run or a quantitative audio
certification. v0.0.10 remains locally tested with FS-UAE.

Paula DMA plays a looping buffer that the game loop must refill. A late frame
can replay stale samples even when the file is successfully streamed from disk.
The hardware gate does not solve that scheduling problem. Future lower-speed
work must measure worst frame time and audio deadlines separately, then improve
mixer servicing/queueing; simply making the HDF larger does not supply CPU time.

FS-UAE 3.1.66 is the locally tested emulator. WinUAE profiles are corrected
configuration guidance, not a claim of a local WinUAE validation run. Record
WinUAE's About/version, saved `.uae`, selected image version and preflight output
with any subsequent report. Full test details are in CHECKPOINT_008_VALIDATION.md.

## Preserved A500 v0.0.6 setup

This is setup guidance, not a claim of a WinUAE validation run. The release was
tested with FS-UAE 3.1.66 on Linux; exact effective settings and ROM identity are
in OPENING_VALIDATION.md. Record your WinUAE version from its About dialog when
reporting a result, and save the configuration used.

1. Extract the private ZIP fully. In WinUAE choose the A500 profile with
   Kickstart 1.3 and 512 KiB Chip + 512 KiB slow expansion RAM.
2. Select `roms/kickstart-1.3-a500.rom` from the demo folder in the ROM settings.
   If the Quickstart ROM list is empty, point System ROMs at that extracted
   directory and rescan. An outer ZIP containing more ZIPs is not a ROM file.
3. Confirm 68000, stock speed, compatible/cycle-exact operation, PAL and OCS.
   Disable JIT, Fast/Z3 RAM, RTG and immediate blits. Use the normal mouse on
   port 0, and avoid a joystick keyboard layout that consumes WASD.
4. Add `MorrowindDemo-v0.0.6.hdf` with the UAE virtual controller and RDB/full-drive
   autodetection. It contains three 32 MiB OFS partitions plus the RDB area;
   DH0 is bootable. Its geometry is recorded in `build.json` (3073 cylinders,
   one head, 64 sectors, 512-byte blocks). Do not force the older plain-partition
   geometry. Eject floppy images for this boot. Do not select A1200 IDE for this test.
5. Click inside to capture the mouse. Enter opens the filled terrain; WASD moves,
   mouse looks, left Shift runs, Tab switches filled/wireframe, 1/2/3 select fog
   distance and Escape restores AmigaDOS and prints frame counters. Opening-only mouse
   controls are left button for the next still and right button to exit.

F6/F7 select complete tracks. Music is streamed; geometry and the voice are
preloaded. The recorded emulator results do not establish physical-HDD speed.
Keep the ROM, images, converted assets and private ZIP private. The source tree
and its public docs contain only ROM metadata, not ROM bytes.

Configuration option reference: the emulator project's
[configuration implementation](https://github.com/tonioni/WinUAE/blob/master/cfgfile.cpp).

On exit, wait at least 10 seconds at the DOS prompt before shutting down the
emulator. The runtime writes `MWBOOT:MWPROFILE.BIN`; the filesystem may still
have buffered metadata after the program returns.
