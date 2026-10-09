# NET-UDP-INIT-CRASH-32: UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | UDP network start-up (net_amigaudp.c) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Possible stop at boot when bsdsocket.library opens; never run. |
| Family | Boot and engine start-up (`boot-startup`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; runtime impact unverified. Found by the source study for a two-Amiga duel mode.

## Symptom

`engine/aga/src/net_amigaudp.c` uses the `gethostbyname` result without a NULL check (lines
78-80), and two later failures call `Sys_Error` (lines 90 and 135), which ends the game. This code
runs at boot in single-player whenever `bsdsocket.library` opens: a real Amiga TCP/IP stack, or an
emulator's bsdsocket emulation (an option some WinUAE and FS-UAE users enable). No playtest
configuration enables it, so the path has never run.

## Where

`engine/aga/src/net_amigaudp.c` (upstream AmiQuake code, unchanged by AmiWind).

## How it happened

Inherited from upstream; AmiWind never needed networking, so the start-up path was not exercised.

## Why it was not caught

Every test configuration runs without bsdsocket.library.

## Reproduction

To verify: boot with `bsdsocket_library = 1` in FS-UAE (or WinUAE's bsdsocket emulation) and with
no host name resolvable.

## Repair

Not yet: network start-up only when a network game is requested, and failures report and
continue in single-player instead of `Sys_Error`.

## Verification

Pending: an FS-UAE boot with bsdsocket emulation on.

## Prevention

A boot test with bsdsocket emulation in the emulator smoke set.

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
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher

<!-- END GENERATED CATEGORY -->
