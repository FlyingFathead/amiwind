# AmiWind playtesting with FS-UAE

This guide describes a known-working FS-UAE configuration for playtesting AmiWind on Linux.

Official homepage and downloads: [FS-UAE](https://fs-uae.net/).
FS-UAE also supports Windows and macOS; AmiWind's v0.0.16 emulator
validation used FS-UAE 3.1.66 on Linux.

## Current v0.0.17 preset

Save a local copy of
[AmiWind-v0.0.17-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.17-FS-UAE.fs-uae),
replace its ROM and HDF placeholder paths, then launch it with FS-UAE.
To build the playable HDF from your Morrowind installation, use the
[Linux](LINUX_BUILD.md) or [Windows / WSL build guide](WINDOWS_BUILD.md).
The public source ZIP includes the preset, not game data, a playable HDF or
a Kickstart ROM. The separate `AmiWind-v0.0.17-dry-run.hdf` boots only to a
test notice. See [v0.0.17 validation](VALIDATION-v0.0.17.md) for test scope.

## Build and launch automatically

With FS-UAE installed and your owned ROM at
`~/.roms/kickstart-3.1-a1200.rom`:

```sh
./build.sh --autoinstall --autorun-fs-uae
```

Use `--kickstart-file /absolute/path/to/your.rom` for another ROM file, or
`--kickstart-file "$HOME/.roms"` to search that directory. Directory selection
checks immediate 512 KiB files against the reference SHA-256, regardless of
filename; it skips subdirectories and symlinks. Identical matching copies are
resolved in filename order. If the default filename is absent, `~/.roms/` is
checked this way automatically.
The requested autorun checks `fs-uae` on PATH and ROM readability before
dependency setup or game conversion. Missing FS-UAE exits with status 1. If no ROM is selected, an
interactive run asks for a file or directory; noninteractive runs exit with status 1 and
explain `--kickstart-file PATH`. The selected file path is filled into
`kickstart_file` in the local config. No username is hardcoded. Without autorun, building requires neither.
The ROM is never downloaded, copied into the image, or bundled with source.

SHA-256 `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`
is the owner's supplied Kickstart 3.1 A1200 reference. A match is reported as
"SHA-256 matches the owner-tested Kickstart 3.1 A1200 ROM." A different checksum on an explicitly selected file
warns that compatibility is unverified and continues with that file. A directory
without a match prompts for another location instead of guessing.
The checksum identifies matching bytes; it does not establish licensing or origin.

After a successful build, the launcher fills in this preset's absolute HDF and
ROM paths, saves `AmiWind-v0.0.17.fs-uae` beside the HDF, and runs FS-UAE with live
output. Close FS-UAE to return to the shell. `--check` and `--plan` check autorun
prerequisites but do not write a config or launch anything. `--dry-run` can also
autorun its asset-free notice HDF. Setup-only/inventory modes reject autorun.
If FS-UAE disappears or fails to start after the build, a warning is printed;
the completed HDF and successful build result are retained.

To launch an existing HDF without rebuilding, run from the repository root:

```sh
python3 tools/run_fs_uae.py --image /absolute/path/to/AmiWind-v0.0.17.hdf
```

This also accepts `--kickstart-file`. An identical generated config is reused; an
existing edited config is preserved and reported, so you can launch it manually.
Standalone launch returns nonzero if launching fails. Configs and personal paths
stay in the local output area, outside the public source package.

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
/path/to/your/AmiWind-v0.0.17.hdf
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
fpu = 68040
jit_compiler = 1
uae_cpu_speed = max
uae_address_space_24 = false

# Memory
chip_memory = 2048
slow_memory = 0
fast_memory = 0
zorro_iii_memory = 16384

# Disable emulated floppy-drive mechanical sounds
floppy_drive_volume = 0

# Kickstart 3.1 A1200 ROM
kickstart_file = /path/to/your/kickstart-3.1-a1200.rom

# AmiWind bootable HDF
hard_drive_0 = /path/to/your/AmiWind-v0.0.17.hdf
hard_drive_0_type = hdf

# Keep movement keys available to AmiWind
joystick_port_1 = none

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
[resources/emulators/AmiWind-v0.0.17-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.17-FS-UAE.fs-uae).
It explicitly disables 24-bit addressing and keyboard joystick emulation,
selects the internal FPU and supplies placeholders for the owned ROM and HDF.
The guide above carries forward the owner's working v0.0.12-dev1 recipe with
the current image name and the preset's explicit memory, CPU and input settings.

The earlier local FS-UAE 3.1.66 harness requested plain `68040` with JIT. Its
log warned about MMU/JIT incompatibility, then reported the resolved machine as
`CPU=68040, FPU=68040, MMU=0, JIT=CPU/FPU=8192`. Thus that build automatically
resolved the conflict; missing Fast RAM is not proven to result from the CPU
name alone. Use the explicit `68040-NOMMU` preset to avoid depending on that
fallback. If Fast RAM is missing, inspect the loaded configuration and memory
settings as well as the startup log.

Reference: [FS-UAE CPU options](https://fs-uae.net/docs/options/cpu/).

Historical hotfix preset: [AmiWind-v0.0.15-dev2-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.15-dev2-FS-UAE.fs-uae). Same machine settings; structural ship repair and debug scene picker.
