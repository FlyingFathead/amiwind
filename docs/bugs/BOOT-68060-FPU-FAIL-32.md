# BOOT-68060-FPU-FAIL-32: On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Boot check FPU test (engine/aga/boot/bootcheck.asm) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | critical: Startup stops on a 68060 with Kickstart 3.1 and no 68060.library. |
| Family | Boot and engine start-up (`boot-startup`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the FPU support library work (FS-UAE, Kickstart 3.1, JIT off).

## Symptom

Kickstart 3.1 reports a 68060 without FPU flags (AttnFlags $000F) until a 68060.library is
loaded, so the boot check prints "required internal FPU absent [!] FAIL" and the startup
sequence stops, although the CPU has an FPU.

## Where

`engine/aga/boot/bootcheck.asm` (FPU test from AttnFlags).

## How it happened

The FPU test relies on flags that Kickstart 3.1 sets only for 68040s.

## Why it was not caught

Only 68040 profiles were tested.

## Reproduction

Boot the image in FS-UAE as a 68060 without a support library.

## Repair

Not yet: detect the FPU directly (probe an FPU register under a temporary trap vector, as the
loader already does for the 68060 PCR), and keep the support library as the WARN line.

## Verification

Pending.

## Prevention

A 68060 profile in the boot tests.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Boot and engine start-up (`boot-startup`). The boot check and engine start-up report problems clearly and never stop the game silently. See [families](README.md#families).

- [BOOT-CONSOLE-WIDTH-32](BOOT-CONSOLE-WIDTH-32.md): Boot check lines wrap on the 64-column boot console
- [BOOT-VOLUME-NOT-VALIDATED-33](BOOT-VOLUME-NOT-VALIDATED-33.md): At boot AmigaOS asks Volume AMIWIND is not validated (Retry/Cancel) while the game starts
- CFG-01 (no report page): Semicolons in default-config comments ran as console commands
- CONFIG-COMMENT-29 (no report page): Semicolons split default-config comments into commands
- CRASH-REPORT-02 (no report page): Fatal engine exit returned to AmigaDOS without a visible reason
- [ENGINE-ARGS-32](ENGINE-ARGS-32.md): The C start-up passes no arguments from the boot shell
- [ENGINE-STACK-UNCHECKED-35](ENGINE-STACK-UNCHECKED-35.md): The engine never checked the stack it was started with; the pak directory alone needs 128 KiB
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

Related bugs in other categories:

- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only

<!-- END GENERATED CATEGORY -->
