# AmiWind playtesting with FS-UAE

This guide describes a known-working FS-UAE configuration for playtesting AmiWind on Linux.

The tested setup uses:

- Amiga 1200 machine profile
- AGA chipset
- 68040 CPU without MMU
- 68040 internal FPU
- JIT enabled
- Fastest possible CPU speed
- 2 MiB Chip RAM
- 16 MiB Zorro III Fast RAM
- Kickstart 3.1 for A1200
- AmiWind bootable HDF
- Emulated floppy-drive mechanical sounds disabled

## Requirements

You need:

1. FS-UAE
2. A legal Kickstart 3.1 A1200 ROM
3. An AmiWind playable HDF image

Example files:

```text
/path/to/your/kickstart-3.1-a1200.rom
/path/to/your/AmiWind-v0.0.12-dev1.hdf
```

The exact AmiWind HDF filename may differ between releases or development builds.

## Create the FS-UAE configuration

Create the FS-UAE configuration directory if it does not already exist:

```bash
mkdir -p ~/Documents/FS-UAE/Configurations
```

Create a configuration file:

```bash
nano ~/Documents/FS-UAE/Configurations/AmiWind.fs-uae
```

Use the following configuration:

```ini
[config]

# AmiWind accelerated playtesting machine
amiga_model = A1200

# 68040 with internal FPU, without MMU.
# FS-UAE JIT is not compatible with MMU emulation.
cpu = 68040-NOMMU
jit_compiler = 1
uae_cpu_speed = max

# Memory
chip_memory = 2048
zorro_iii_memory = 16384

# Disable emulated floppy-drive mechanical sounds
floppy_drive_volume = 0

# Kickstart 3.1 A1200 ROM
kickstart_file = /path/to/your/kickstart-3.1-a1200.rom

# AmiWind bootable HDF
hard_drive_0 = /path/to/your/AmiWind-v0.0.12-dev1.hdf

# Windowed mode
fullscreen = 0
```

Replace the two `/path/to/your/...` entries with the actual paths to the ROM and HDF on your system.

## Start AmiWind

Run FS-UAE with the configuration file:

```bash
fs-uae ~/Documents/FS-UAE/Configurations/AmiWind.fs-uae
```

The HDF should boot directly into the AmiWind playtesting environment.

## Expected memory check

AmiWind performs a hardware check during startup.

A working configuration should report approximately:

```text
Chip KiB installed 2048
Fast KiB installed 16384
```

The exact amount reported as free memory will be slightly lower because the operating system and startup environment consume some RAM.

If AmiWind reports:

```text
Fast KiB installed 0
```

check that the configuration contains:

```ini
cpu = 68040-NOMMU
zorro_iii_memory = 16384
```

Do not use plain:

```ini
cpu = 68040
```

with JIT enabled. In FS-UAE, that configuration enables MMU emulation, while MMU emulation and JIT are not compatible.

## Floppy-drive sounds

FS-UAE can emulate the mechanical sounds of an Amiga floppy drive, including the periodic click of an empty drive.

For AmiWind HDF playtesting, these sounds are disabled in the recommended configuration:

```ini
floppy_drive_volume = 0
```

This affects only the emulated mechanical drive noises. It does not disable Amiga audio output.

## Optional fullscreen mode

For fullscreen playtesting, change:

```ini
fullscreen = 0
```

to:

```ini
fullscreen = 1
```

## Notes

This is an accelerated AmiWind playtesting configuration. It is intended to provide a convenient Linux environment for running playable HDF builds.

It is not intended to represent the performance of a stock Amiga 1200 or Amiga 500. The configuration deliberately uses a 68040, JIT, Zorro III Fast RAM, and fastest-possible CPU speed.

For compatibility or minimum-spec testing, use a separate emulator configuration matching the intended target hardware.

## Repository preset and validation note

A matching example is supplied under
[resources/emulators/AmiWind-v0.0.15-dev1-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.15-dev1-FS-UAE.fs-uae).
It explicitly disables 24-bit addressing and keyboard joystick emulation,
selects the internal FPU and supplies placeholders for the owned ROM and HDF.
The guide above preserves the owner's working v0.0.12-dev1 recipe.

The earlier local FS-UAE 3.1.66 harness requested plain `68040` with JIT. Its
log warned about MMU/JIT incompatibility, then reported the resolved machine as
`CPU=68040, FPU=68040, MMU=0, JIT=CPU/FPU=8192`. Thus that build automatically
resolved the conflict; missing Fast RAM is not proven to result from the CPU
name alone. Use the explicit `68040-NOMMU` preset to avoid depending on that
fallback. If Fast RAM is missing, inspect the loaded configuration and memory
settings as well as the startup log.

Reference: [FS-UAE CPU options](https://fs-uae.net/docs/options/cpu/).

Current hotfix preset: [AmiWind-v0.0.15-dev2-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.15-dev2-FS-UAE.fs-uae). Same machine settings; structural ship repair and debug scene picker.
