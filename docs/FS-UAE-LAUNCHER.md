# Portable FS-UAE launcher

The public `tools/AmiWind-FS-UAE-launcher.py` and private playable-root copy
are executable on POSIX systems: `./AmiWind-FS-UAE-launcher.py`. The source
archive preserves mode 0755; Windows can continue using `python` or `py`.

`tools/AmiWind-FS-UAE-launcher.py` is a standalone Python 3.8+ helper for existing
local images. It requires no Python packages. Install FS-UAE separately and
provide your own playable HDF and suitable Kickstart ROM.

Copy the script beside your versioned HDFs and run:

```sh
python3 AmiWind-FS-UAE-launcher.py
```

It lists the images with versions and modification dates. Press Enter to run
the suggested latest image, enter a number to choose another, or `n` to cancel.
It searches `roms/` for a Kickstart ROM. If no usable ROM is found, it asks for
a file or directory and remembers the selected file for future runs.

For immediate subsequent launches with saved settings:

```sh
python3 AmiWind-FS-UAE-launcher.py --yes
```

From the repository, point the tool at your playable directory:

```sh
python3 tools/AmiWind-FS-UAE-launcher.py --directory /path/to/playables
```

Without `--directory`, it uses the script's own folder, even when invoked from
another working directory. Discovery checks files directly in that folder.
It does not download or unpack images, ROMs or FS-UAE.

## Choosing the latest image

Recognized filenames start with `AmiWind-vMAJOR.MINOR.PATCH` and end in `.hdf`.
Suffixes such as `-dev5`, `-dev10`, `-test-006`, `-beta2` and `-rc1` are supported.
Names and extension matching are case insensitive.

1. Compare major, minor and patch as numbers: `0.0.20` beats `0.0.9`.
2. Within one base version, final releases beat prereleases. Known stages sort
   `dev < test < alpha < beta < rc < final`; their numeric suffixes are numeric,
   so `-dev10` beats `-dev5` even if an older build was copied more recently.
3. Arbitrary development labels are accepted, ranked below numbered development
   builds of that base version. Modification time resolves equal version ranks;
   filenames provide a deterministic natural-order fallback for equal dates.

Dates are a hint, not proof of build age; copying files may change timestamps.
The interactive list always allows overriding the suggestion. `-play.hdf`,
`-backup.hdf` and `-dry-run.hdf` are excluded from automatic discovery. Select
one explicitly with `--hdf FILE` if needed. Selecting a different image for one
run does not pin future launches to it.

## Launcher settings

After a successful preflight, `AmiWind-launcher.json` is created beside the HDFs.
For example:

```json
{
  "format": 1,
  "kickstart_rom": "roms/kickstart-3.1-a1200.rom",
  "hdf": "latest",
  "fs_uae": "fs-uae",
  "confirm_launch": true
}
```

Keep `"hdf": "latest"` to discover the latest image on every launch. Set
`"confirm_launch": false` to launch that suggestion immediately, or leave it
true and use `--yes` for individual quick launches. To pin a particular image,
set `hdf` to its filename. `--hdf latest` overrides a pin for one run.

ROM paths within the playable directory are stored relatively; external ROM
paths are absolute. Relative paths are interpreted from the playable directory.
`--rom FILE_OR_DIRECTORY` updates the remembered ROM. `--fs-uae EXECUTABLE`
updates the remembered emulator command. Launcher settings contain local paths
and are excluded from public source; the distributed script has none built in.

The ROM's SHA-256 is checked on every run against the development Kickstart 3.1
A1200 reference:

`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`

A mismatch prints `[warn]`, the expected and actual hashes, and continues.
It does not claim to identify the unknown ROM's actual version. Directory search
prefers an exact checksum match regardless of filename, otherwise accepts one
plausibly sized ROM with the warning. Multiple unmatched files require explicit
selection; the launcher does not guess which machine's ROM to use. Supported
file sizes are 256 KiB, 512 KiB and 1 MiB.

## FS-UAE configuration

The launcher creates `AmiWind-vVERSION-FS-UAE.fs-uae` beside the selected HDF,
using a matching `resources/emulators/` template if present. Otherwise it uses
the embedded accelerated A1200/AGA, 68040/FPU/JIT, 2 MiB Chip and 16 MiB Z3 preset.
This is the accelerated development target. Stock A1200 performance is unproven.

On reruns it updates only the ROM/HDF paths, HDF type and the corrected
`uae_cpu_24bit_addressing = false` option, removing the rejected old
`uae_address_space_24` spelling. Other emulator settings and comments are kept.
An already matching config is not rewritten. Replaced configs are backed up
under `resources/emulators/backups/` with unique numbered names. If the playable
folder moves, paths in the emulator config are repaired on the next run.

```sh
python3 AmiWind-FS-UAE-launcher.py --configure-only
python3 AmiWind-FS-UAE-launcher.py --hdf AmiWind-v0.0.19.hdf
python3 AmiWind-FS-UAE-launcher.py --rom /path/to/owned.rom --yes
```

`--configure-only` creates/reuses configs without requiring or starting FS-UAE.
It and `--yes` never ask interactive questions; missing files cause a clear
error. Cancellation before configuration leaves files unchanged. Malformed
configs and config symlinks are rejected without overwriting them. FS-UAE is
started with literal arguments, without a shell, and its exit status is returned.

The launcher does not modify HDF or ROM bytes. FS-UAE can write to the selected
HDF during play; retain a clean backup. Before launching, dev6 prints a versioned
host preflight and enforces the managed AmiWind accelerated profile:

```text
AmiWind v0.0.21-dev7 host preflight
Amiga type:           A1200                   [x] OK
CPU:                  68040-NOMMU             [x] OK
FPU:                  68040 internal          [x] OK
CPU speed:            Fastest possible        [x] OK
JIT:                  ON                      [x] OK
24-bit addressing:    OFF                     [x] OK
Cycle-exact speed:    OFF (cpu_speed=max)     [x] OK
Kickstart:            3.1 A1200 40.68         [x] OK
```

The Kickstart label above is shown only when the ROM SHA-256 matches the known
development ROM. Existing configs with different managed machine values are
backed up and corrected; unrelated custom options such as window/fullscreen
choices are preserved. This utility does not diagnose or fix the open intermittent
ship-exit/menu freeze.

## Validation

The launcher regression suite uses synthetic files, including a fake emulator
process. It covers numeric/dev/date ordering, selection and cancellation, ROM
discovery/checksum warnings, remembered settings, moved folders, preservation
and backup of configs, failed replacement, literal paths and emulator exit status.

```sh
python3 -W error -m unittest discover -s tests -p test_fs_uae_launcher.py -v
```

The existing build-time `tools/run_fs_uae.py` and `--autorun-fs-uae` interface
remain available for the builder. This standalone helper is for repeated runs
of images already built or extracted.
