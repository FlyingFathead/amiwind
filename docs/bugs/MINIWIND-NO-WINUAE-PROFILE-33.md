# MINIWIND-NO-WINUAE-PROFILE-33: MiniWind playtest packages ship only an FS-UAE profile

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Private playtest packaging of MiniWind builds (the package step after the builder's image) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The package boots in FS-UAE; WinUAE users must write their own configuration |
| Family | Boot and engine start-up (`boot-startup`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33-dev1 MiniWind #3 |
| From commit | source c4e14ab, engine c4e14ab, CHIM world c4e14ab |
| CHIM engine version | CHIM 0.1.0, engine c4e14ab, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. The package step is being changed to write the WinUAE profile and the launcher for every build
type (MiniWind, development, release candidate, final).

## Symptom

The owner unpacked a MiniWind playtest package to play it in WinUAE and found only an FS-UAE profile.
The v0.0.32 playtest packages had a launcher and a WinUAE configuration generated for the build.

## Where

The playtest package step that runs after the builder has written and read back the image. The
MiniWind variant of it was written for FS-UAE only.

## How it happened

The MiniWind package step was written from scratch for the first MiniWind build, with the headless
FS-UAE smoke test as its only user, instead of reusing the package step of full builds.

## Why it was not caught

The delivery check compares the unpacked folder with its manifest; nothing checks that every package
type carries the same set of emulator profiles.

## Reproduction

Unpack any MiniWind package up to MiniWind #3 and look for a `.uae` file: there is none.

## Repair

One package step for every build type writes the FS-UAE and WinUAE profiles from the builder's own
emulator templates (`tools/emulator_configs.py`) plus the launcher, and refuses to finish when one is
missing.

## Verification

Pending: the next package (v0.0.33-rc1) must contain both profiles and the launcher, listed in its
manifest.

## Prevention

The package step checks the profile set of every package it writes.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Boot and engine start-up (`boot-startup`). The boot check and engine start-up report problems clearly and never stop the game silently. See [families](README.md#families).

- [BOOT-68060-FPU-FAIL-32](BOOT-68060-FPU-FAIL-32.md): On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops
- [BOOT-CONSOLE-WIDTH-32](BOOT-CONSOLE-WIDTH-32.md): Boot check lines wrap on the 64-column boot console
- [BOOT-VOLUME-NOT-VALIDATED-33](BOOT-VOLUME-NOT-VALIDATED-33.md): At boot AmigaOS asks Volume AMIWIND is not validated (Retry/Cancel) while the game starts
- CFG-01 (no report page): Semicolons in default-config comments ran as console commands
- CONFIG-COMMENT-29 (no report page): Semicolons split default-config comments into commands
- CRASH-REPORT-02 (no report page): Fatal engine exit returned to AmigaDOS without a visible reason
- [ENGINE-ARGS-32](ENGINE-ARGS-32.md): The C start-up passes no arguments from the boot shell
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- END GENERATED CATEGORY -->
