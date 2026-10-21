# Workbench icon

_Last updated with AmiWind v0.0.46 (20 October 2026)._

AmiWind is a boot disk: the computer starts from the AmiWind hard disk image,
and `S:startup-sequence` runs the boot check, picks the engine for the CPU and
starts it with a 300,000-byte stack. Someone who boots their own Workbench with
the AmiWind disk attached sees the AmiWind volume as just another drive. The
builder puts an icon on that volume for them (`--workbench-icon`, `launch` by
default since v0.0.46).

## What the icon is

- A project icon named `AmiWind v<VERSION>` (for example `AmiWind v0.0.46`):
  Workbench shows the file name under the picture. The version comes from the
  build's `VERSION` file. With `.info` the name stays within the 30-character
  file name limit of the Amiga file system, also with a suffix such as
  `-dev10` or `-rc1`.
- The picture is the AmiWind logo in the 4 colours of a stock Workbench 3.1
  screen (grey, black, white, blue), 192 x 36 pixels, with a second picture
  for the selected icon. The sources are indexed PNG files in
  `resources/workbench/`; `tools/amiga_icon.py` writes them into a classic
  `.info` file (Workbench 1.x-3.1 format) and reads such files back field by
  field.
- The icon's default tool is `C:IconX`, which runs the small script the icon
  belongs to.
- The engine binary `AmiWind` has no icon. Workbench shows only files with
  icons, so it is not offered: started from Workbench it would skip the boot
  check and the CPU choice, and run with a small stack.

## Options

| `--workbench-icon` | What happens on a double-click |
| --- | --- |
| `off` | No icon is written. |
| `requester` | A requester (`C:RequestChoice` from Workbench 3.1) says that AmiWind starts by booting the computer from its disk, and how to pick it (boot drive, or the Early Startup menu: both mouse buttons at power-on). OK closes it; nothing else runs. |
| `launch` (default) | The script runs the boot steps from Workbench: the FPU support loader when the build installed one, the CPU selector or the boot check, `Stack 300000`, then the engine. The paths use the boot volume's name `AMIWIND:` instead of `SYS:`. |

Limits of `launch`: Workbench's own `SetPatch` has already run (it also opens
the system's 68040.library when there is one), and the CPU selector looks for
`SYS:AmiWind060`, which is on the AmiWind disk only when it is the boot disk,
so a 68060 started from Workbench gets the 68040 engine. Booting from the
AmiWind disk stays the way the game is meant to start.

## Checked in an emulator

20 October 2026, FS-UAE (A1200, 68040, 2 MiB Chip, 16 MiB Zorro III, JIT),
Kickstart 3.1, the maintainer's own Workbench 3.1 hard disk as the boot drive
and a copy of the v0.0.46 image as the second drive:

- The icon appears in the AMIWIND window in the stock colours with the label
  `AmiWind v0.0.46`; selected, it shows its second picture.
- `requester`: a double-click opens the requester; OK closes it and Workbench
  carries on.
- `launch`: a double-click starts the game (logo, main menu); Seyda Neen loads
  and plays for 10 seconds; Exit game returns to Workbench.

`launch` became the default after these checks (decided for the project,
20 October 2026); `requester` stays selectable. Not checked yet: a real Amiga,
and a 68060.

## Tests

`tests/test_workbench_icon.py`: the writer's header fields at their byte
offsets, bit planes, refusals (wrong magic, truncation, trailing bytes, colour
index out of range), the repository pictures, each option value, the script
contents, the name limit with the longest version suffixes, and that the
default build command adds nothing.
