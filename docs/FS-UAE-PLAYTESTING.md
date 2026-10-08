# AmiWind playtesting with FS-UAE

## Automatically generated image configurations

Full-game assembly writes `AmiWind-v<VERSION>-WinUAE.uae` and
`AmiWind-v<VERSION>-FS-UAE.fs-uae` beside the HDFs. The verified image receipt
is the source of the drive list: load every required HDF simultaneously.
The boot disk comes first; additional world disks are not interchangeable
and do not require disk swapping.

Supply `--kickstart-file /path/to/owned.rom` to the build to fill both local
ROM paths, or select your licensed ROM in the emulator afterward. ROMs and
playable images are private build outputs, never public source assets.
Get your Kickstart ROM and Workbench legally, for example with Amiga Forever from Cloanto
([FAQ](FAQ.md#is-amiwind-official-do-i-need-the-game)).
Configurations use host-local absolute paths. After moving the image directory,
keep `build.json` and every listed HDF together and regenerate the configurations
on the destination host:

```sh
python tools/emulator_configs.py --image /path/to/AmiWind-v0.0.27.hdf --kickstart-file /path/to/owned.rom
```

The generator preserves a differing existing configuration instead of overwriting
custom settings; move that configuration to a backup name before regenerating.
The portable FS-UAE launcher updates moved paths with its existing backup workflow.
Both FS-UAE launchers now use every drive listed in `build.json`. A missing required
world disk stops configuration instead of silently launching an incomplete world.


This guide describes a known-working FS-UAE configuration for playtesting AmiWind on Linux.

Official homepage and downloads: [FS-UAE](https://fs-uae.net/).
FS-UAE also supports Windows and macOS; AmiWind's v0.0.16 emulator
validation used FS-UAE 3.1.66 on Linux.

For repeated runs of existing images, use the
[portable FS-UAE launcher](FS-UAE-LAUNCHER.md). It selects the latest numeric
version/development suffix, remembers the ROM and repairs local config paths.

## Current v0.0.27 preset

Prefer the matching generated configuration described above, which lists every
required HDF. For manual setup, save a local copy of
[AmiWind-v0.0.27-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.27-FS-UAE.fs-uae),
set your ROM and all required HDF paths, then launch it with FS-UAE.
To build the playable HDF from your Morrowind installation, use the
[Linux](LINUX_BUILD.md) or [Windows / WSL build guide](WINDOWS_BUILD.md).
The public source ZIP includes the preset, not game data, a playable HDF or
a Kickstart ROM. A public dry-run HDF, when produced for the current version, boots only to a
test notice. See [v0.0.27 release notes](RELEASE-v0.0.27.md) for current source
and build evidence. Actual FS-UAE multi-drive gameplay remains pending;
[v0.0.17 validation](VALIDATION-v0.0.17.md) records the earlier local baseline.

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
ROM paths, saves a version-matched `.fs-uae` file beside the HDF (for example,
`AmiWind-v0.0.21-dev7.fs-uae`), and runs FS-UAE with live
output. Close FS-UAE to return to the shell. `--check` and `--plan` check autorun
prerequisites but do not write a config or launch anything. `--dry-run` can also
autorun its asset-free notice HDF. Setup-only/inventory modes reject autorun.
If FS-UAE disappears or fails to start after the build, a warning is printed;
the completed HDF and successful build result are retained.

To launch an existing HDF without rebuilding, run from the repository root:

```sh
python3 tools/run_fs_uae.py --image /absolute/path/to/AmiWind-v0.0.21-dev7.hdf
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
/path/to/your/AmiWind-v0.0.21-dev7.hdf
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
uae_cpu_24bit_addressing = false

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
hard_drive_0 = /path/to/your/AmiWind-v0.0.21-dev7.hdf
hard_drive_0_type = hdf

# Keep movement keys available to AmiWind
joystick_port_1 = none

# Home/End and page keys as keys the game reads (the shipped presets do this)
keyboard_key_pageup = action_key_68
keyboard_key_pagedown = action_key_69
keyboard_key_home = action_key_6a
keyboard_key_end = action_key_6c

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

AmiWind performs a hardware check during startup. In dev7 the native checker
prints its exact AmiWind version and reports only facts the guest can observe.
FS-UAE-only settings such as JIT and fastest-possible CPU mode are printed and
validated by `AmiWind-FS-UAE-launcher.py`; the guest deliberately labels them as
host-side instead of pretending to detect them.

After a successful check, the report remains visible for a **five-second countdown**.
Press **Space** or **Enter** to continue immediately. The public dry-run HDF executes
the same checker first and then displays the normal asset-free test-build notice.
Do not depend on the boot console having scrollback.

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

## Benchmark profile

The playtest configuration above (JIT, `uae_cpu_speed = max`) runs the 68040 as fast as
the PC allows, so its frame rates and loading times say little about a real Amiga
([BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md)). For performance comparisons
between builds use this cycle-approximate profile instead; it is the relative
reference profile. **It is not real hardware**: FS-UAE 3.1.66 (WinUAE 3.3 core)
approximates 68040 instruction and memory timing, its hard disk is a virtual device
backed by the PC's file cache (load times are not real), and nothing here has been
checked against a real accelerated A1200 yet ([HARDWARE-BENCHMARK.md](HARDWARE-BENCHMARK.md)
asks owners for that number). Every performance report names its profile.

Replace the CPU speed lines of the playtest configuration with:

```ini
# Benchmark profile: interpreted 68040 (no JIT), cycle-approximate timing,
# CPU clock 7 x 3.546895 MHz = 24.8 MHz (a 68040 at 25 MHz)
jit_compiler = 0
uae_cpu_cycle_exact = true
uae_cpu_multiplier = 7
```

Everything else stays as in the playtest configuration (A1200, `68040-NOMMU` with its
FPU, 2 MB Chip RAM, 16 MB Zorro III RAM, Kickstart 3.1); warp mode stays off. Notes from
setting it up (FS-UAE 3.1.66, checked in the effective configuration FS-UAE writes):

- `uae_cpu_cycle_exact = true` also turns on memory cycle-exact mode for the 68020 and
  later; FS-UAE reports the CPU as "~cycle-exact fast".
- The clock comes from `uae_cpu_multiplier` (times 3.546895 MHz). `uae_cpu_frequency`
  is accepted but ignored in this mode: with `uae_cpu_frequency = 25000000` the CPU
  stays at the A1200 default multiplier 4 (14.2 MHz). Multiplier 11 gives 39 MHz.
- JIT and cycle-exact mode exclude each other.
- `uae_cpu_speed = real` without cycle-exact mode is not a substitute: its CPU loops are
  close to a 14 MHz cycle-exact run but Fast RAM copies run at 56 MB/s.

The asset-free `awbench cpu` loops ([HARDWARE-BENCHMARK.md](HARDWARE-BENCHMARK.md))
under each candidate profile (millions of loops per second; MB/s):

| Profile | integer multiply | integer add | FPU | Fast RAM copy | Chip RAM write |
| --- | ---: | ---: | ---: | ---: | ---: |
| Playtest (JIT, `max`) | 1,100.6 | 1,389.0 | 63.1 | 7,812.5 | 5,211.7 |
| No JIT, `max` | 28.9 | 23.7 | 2.22 | 529.7 | 122.8 |
| No JIT, `uae_cpu_speed = real` | 1.34 | 1.66 | 1.04 | 56.1 | 7.17 |
| Cycle-exact, multiplier 4 (14.2 MHz) | 2.34 | 2.00 | 1.12 | 14.6 | 4.42 |
| **Benchmark: cycle-exact, multiplier 7 (24.8 MHz)** | **4.17** | **3.58** | **2.00** | **26.1** | **6.69** |

The ten fixed cameras of [performance/RENDERER-COUNTERS.md](performance/RENDERER-COUNTERS.md)
(positions in [HARDWARE-BENCHMARK.md](HARDWARE-BENCHMARK.md#frame-time-in-the-game)),
measured 8 October 2026 with `dbg rcount` on the v0.0.32-dev engine overlaid on a copy
of the v0.0.31 image (noon, day/night cycle off, headlamp off; medians of the
per-second lines; the renderer counts were the same in every profile):

| Camera | Playtest frame ms | No JIT, `max`, strict FPU mode frame ms | **Benchmark frame ms** | Benchmark: brush models / scan (incl. draw) / span drawing / alias models ms | Benchmark brush model share of the view |
| --- | ---: | ---: | ---: | --- | ---: |
| Balmora 1 | 45.0 | 3,320 | **8,139** | 6,973 / 553 / 316 / 28 | 88 % |
| Balmora 2 | 24.3 | 1,742 | **4,384** | 3,187 / 502 / 303 / 28 | 76 % |
| Balmora 3 | 21.4 | 1,608 | **3,995** | 2,667 / 328 / 151 / 5 | 83 % |
| Balmora 4 | 28.3 | 1,604 | **4,292** | 3,195 / 444 / 307 / 49 | 78 % |
| Balmora 5 | 24.4 | 1,657 | **3,851** | 2,806 / 409 / 233 / 22 | 76 % |
| Seyda Neen 1 | 22.1 | 1,408 | **3,725** | 1,313 / 1,382 / 1,102 / 402 | 39 % |
| Seyda Neen 2 | 15.1 | 809 | **2,668** | 1,227 / 369 / 182 / 409 | 55 % |
| Seyda Neen 3 | 25.1 | 1,492 | **4,718** | 2,473 / 1,406 / 850 / 260 | 55 % |
| Seyda Neen 4 | 17.7 | 1,236 | **3,238** | 1,951 / 409 / 224 / 291 | 64 % |
| Seyda Neen 5 | 25.3 | 1,427 | **3,744** | 2,277 / 691 / 324 / 319 | 64 % |

Frame times are medians of the per-second lines (one frame per line at the benchmark
profile, 10-33 frames per camera); the no-JIT column ran at the same time as the
benchmark run on the same PC, so it is the least precise. At the benchmark profile a
view takes 2.7-8.1 seconds; in Balmora 76-88 % of it is the brush models' clipping
against the world BSP (see the counters page and RENDER-BMODEL-FRAGMENTS-32), in Seyda
Neen surface cache rebuilding (Seyda Neen 1 and 3) and alias models add up. Between
the playtest and the benchmark profile the frame time grows 148-188 times. Treat all of
these as relative numbers until a real 68040 measurement exists.

## Repository preset and validation note

A matching example is supplied under
[resources/emulators/AmiWind-v0.0.27-FS-UAE.fs-uae](../resources/emulators/AmiWind-v0.0.27-FS-UAE.fs-uae).
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


## Emulator development access

See [FS-UAE development access](FS-UAE-DEVELOPMENT.md) for guest memory and
register inspection, breakpoints, serial-terminal access, save-state/capture
limits and a proposed repeatable testing workflow. Stock interfaces and optional
patched backends are distinguished; unattended runtime validation is pending.

## Headless development container

See [FS-UAE in Docker](FS-UAE-DOCKER.md) for a persistent container,
private virtual display, screenshots, console debugger and backup steps.
