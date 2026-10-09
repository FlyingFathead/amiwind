# FPU support library (optional, your own copy)

AmiWind can put your own `68040.library` or `68060.library` on its boot disk
and open it at start-up. It is optional: without one the game builds and boots
as before, and the boot check shows a warning line. AmiWind never ships,
downloads or bundles this library; the builder only copies the file you point
it at, from your own Workbench or accelerator installation.

<!-- contents start -->
## Contents

- [Why](#why)
- [Where to find it on your installation](#where-to-find-it-on-your-installation)
- [Build option](#build-option)
- [Known versions](#known-versions)
- [What you see at boot](#what-you-see-at-boot)
- [How the loader installs the handlers](#how-the-loader-installs-the-handlers)
- [Tested](#tested)

<!-- contents end -->

## Why

The 68040 and 68060 have a smaller FPU than the 68881/68882. Some FPU
instructions are not in the hardware (for example `FSIN`, `FCOS`, `FETOX`,
`FMOVECR`, and on the 68040 `FINTRZ`), and the CPU also traps when an operand
is denormalized or unnormalized ("unimplemented data type"), whatever the
instruction. The 68060 additionally lacks a few integer instructions (64-bit
`MULU.L`/`DIVU.L`, `MOVEP`, `CAS2`). On a Workbench boot, `SetPatch` opens the
support library, whose trap handlers emulate all of this in software.

The AmiWind boot disk starts straight from Kickstart: no Workbench, no
`SetPatch`. Without a support library, a real 68040 or 68060 that meets one of
these cases stops the program. The engine avoids the known unimplemented
instructions (the builder checks every engine build with
`tools/check_fpu_unimplemented.py`), but denormal operands cannot be ruled out
in floating-point game code, so the library makes those rare cases safe.
Emulators normally execute these instructions themselves, so this matters on
real hardware, and in the emulator's strict mode (FS-UAE
`uae_fpu_no_unimplemented = true`, which works only with the JIT off). Status
and measurements: [ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md).

## Where to find it on your installation

- A Workbench 3.x installation on a 68040 machine (for example an A4000/040)
  has `68040.library` in its `Libs` drawer (`LIBS:68040.library`).
- 68060 accelerators come with a `68060.library` on their install disk; after
  installation it is in `LIBS:`. Some 68060 setups also have a small
  `68040.library` that opens the `68060.library`.
- Replacement CPU libraries (for example the MMULib package) provide both;
  those need `mmu.library`, which the builder copies too when it is in the
  same folder.
- For an emulator, look in the `Libs` drawer of the Workbench hard drive
  (directory or HDF) you installed yourself.

Copy the `Libs` drawer (or the whole Workbench folder) to where the builder can
read it, for example `~/amiga/workbench/Libs/`.

## Build option

```sh
./build.sh --data-files "/path/to/Morrowind" --amiga-libs ~/amiga/workbench
```

```bat
build.cmd --data-files "C:\GOG Games\Morrowind" --amiga-libs C:\amiga\workbench
```

`--amiga-libs DIR` accepts the folder itself or its parent: the builder looks
for `68040.library` and `68060.library` in `DIR` and in `DIR/LIBS`, ignoring
upper/lower case as AmigaOS does. When it finds one or both:

- they are copied to `LIBS/` on the boot partition (with `mmu.library` if it is
  beside them), and the small loader `AmiWindFPU` is copied to the root;
- `S:startup-sequence` runs `AmiWindFPU` before `AmiWindCheck`;
- each file is identified (see [Known versions](#known-versions)): its name,
  version, size, SHA-256 and verdict are recorded in `image/fpu-support.json`, in
  `fpu_support` of `image/build.json` and in the build summary
  (`FPU support library: 68040.library v37.30 (43,888 bytes) SHA-256 ...: known: ...`).

When the folder holds neither library, the build continues and reports
`FPU support library: none (no FPU support library)`. A folder that does not
exist is an error, so a typing mistake does not go unnoticed. The option also
works with `--dry-run`; that test image then contains your library, so keep it
to yourself like any image built from your files. Direct use:
`tools/build_aga.py image ... --amiga-libs DIR` and
`tools/build_dry_run.py ... --amiga-libs DIR`.

## Known versions

The builder reads each library it finds as an Amiga hunk executable: the resident
library structure (RomTag) gives its name and version, the revision comes from the
library's data table, its RomTag id string or its `$VER:` string. With the size and
SHA-256 this is compared with the known-inputs table
([`config/known-inputs.json`](../config/known-inputs.json),
[Known inputs](KNOWN_INPUTS.md)), at the start of the build and again when the image
is staged:

| Library | Version | Bytes | SHA-256 | Source |
| --- | --- | ---: | --- | --- |
| `68040.library` | 37.30 (Commodore, 18.1.93) | 43,888 | `b8c26d42369fb22719296a26b67e357640a82ee3dcf6fa8f42c953de41679fbf` | Amiga Forever 2016 (Cloanto), AmigaOS 3.1 system files |
| `68060.library` | 43.1 (MMULib, 22.10.2009) | 64,820 | `166472bc4dcc3580cf80f6dccb38f6f4f8ee39bb8f3113a3cc18343dcfb38fd9` | Amiga Forever 2016 (Cloanto), AmigaOS 3.1 system files |
| `mmu.library` | 43.11 (MMULib, 3.10.2009) | 56,720 | `6a4395da8057072db8c09e17d8fefcabc2c15888af56a04e7642f930e6bdc614` | Amiga Forever 2016 (Cloanto), AmigaOS 3.1 system files |

The `68060.library` and `mmu.library` of that set are from Thomas Richter's MMULib,
not from Commodore (AmigaOS 3.1 had no 68060.library). These are the builds the builder
was tested with; trap handling on a real 68040/68060 is not yet verified
([ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md)).

Each file gets one verdict, printed at the start of the build and in the summary:

```text
68040.library v37.30 (43,888 bytes) SHA-256 b8c26d42...: known: Amiga Forever 2016 (Cloanto), AmigaOS 3.1 system files (tested)
68060.library v46.2 (... bytes) SHA-256 ...: unknown build of 68060.library v46.2 (not tested; used)
mmu.library (... bytes) SHA-256 ...: invalid: not an Amiga library or version unreadable (not used): no hunk header
```

`--amiga-libs-policy warn` (default) uses unknown builds with a warning and never
copies an invalid file; `fail` stops the build on an invalid file; `require-known`
accepts only known builds. Other builds (other OS releases, accelerator vendors,
community builds) can be added to the table with their source label.

## What you see at boot

`AmiWindFPU` prints one line, for example:

```text
FPU support: 68040.library 37.30 open (68040) attn $804F>$807F
FPU support: 68060.library not opened (68060): absent/refused
```

`attn` is `SysBase->AttnFlags` before and after the open; a support library that
installs its emulation adds the 68881/68882 flags (`$0030`) according to the
NDK. "Absent/refused" means the file is not in `LIBS:` or the library declined
to start on this CPU.

The boot check (the five-second checklist; Space or Enter skips it) then shows
the CPU and the support library that is resident:

```text
CPU:                  68040                      [x] OK
FPU:                  internal 040/060 compatible [x] OK
FPU support:          68040.library 37.30 active [x] OK
```

or, without one, a warning that never stops the start-up:

```text
FPU support:          none - see docs (optional) [~] WARN
```

On a 68060 with Kickstart 3.1, the `FPU:` line fails until a `68060.library`
is loaded: that Kickstart does not know the 68060 and reports it as a 68040
without FPU in `AttnFlags`. The boot check still names
the 68060 (it reads the 68060-only PCR register) and shows the `FPU support:`
line, so the fix is visible: add your `68060.library` with `--amiga-libs`.
Measured in FS-UAE's 68060 emulation with Kickstart 3.1; a real
`68060.library` is expected to set the 68060 and FPU flags (not verified here).

The engine prints the same status to the console at start-up
(`FPU support: 68040.library v37.30 active (CPU 68040)` or
`FPU support: none (CPU 68040): rare FPU cases may crash on a real 68040/68060; see the docs, FPU support library`),
and `dbg fpu` prints it again ([console commands](AMIWIND_CONSOLE_COMMANDS.md)).

## How the loader installs the handlers

On a Workbench boot, `SetPatch` loads the CPU library at start-up and it stays
resident. These libraries install their support code when they are loaded, not
on each call: exec's ramlib loads the file from `LIBS:` on the
first `OpenLibrary()` and runs its initialisation, which installs the trap
handlers. The MMULib documentation describes the `fpsp.resource` (the FPU
emulation) as installed by the 68040/68060 libraries on start-up, and the NDK
(`exec/execbase.i`, `AFB_FPU40`) says that a 68040 FPU without the
`AFB_68881`/`AFB_68882` flags means "the 68040 math emulation code has not been
loaded", that is, the library sets those flags when it installs. Some 68040
accelerators shipped an `Init040` program that loads the `68040.library` from
the startup sequence in the same way.

`AmiWindFPU` (`engine/aga/boot/fpulib.asm`, 68000 code built by the SDK's vasm
with the engine) therefore:

1. reads `AttnFlags`; below a 68040 it does nothing;
2. picks `68060.library` on a 68060, otherwise `68040.library`. Kickstart 3.1
   does not know the 68060 and reports it as a 68040 until a `68060.library`
   sets `AFF_68060`, so the loader also reads the 68060-only Processor
   Configuration Register in supervisor mode; a 68040 takes an
   illegal-instruction exception there, which a temporary vector skips
   (`engine/aga/boot/fpu_support_inc.asm`);
3. calls `OpenLibrary(name, 0)` and keeps the library open, so it can never be
   expunged;
4. prints the result with `AttnFlags` before and after, so the emulation flags
   the library sets are visible.

It does not replace the rest of `SetPatch`. The boot check and the engine look
the library up by name in `SysBase->LibList` under `Forbid()`; they open
nothing.

## Tested

The repository tests use synthetic bytes only. Emulator tests use a library of
our own, `tests/fpu_test_library.asm`: a minimal valid Amiga library, assembled
under the name `68040.library` or `68060.library`, that does nothing but open
(version 1.0). It proves the loader, boot check and engine status paths, not
the trap handling of a real support library; that still needs a real library
on real hardware or in the emulator's strict mode.
