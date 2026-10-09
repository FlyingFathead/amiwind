# ENGINE-ARGS-32: The C start-up passes no arguments from the boot shell

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Amiga C start-up, boot shell arguments |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Programs get argc 1 from the boot shell; engine line unchecked. |
| Family | Boot and engine start-up (`boot-startup`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

Programs built with our toolchain get `argc` = 1 when started from the boot shell; `awbench`
now reads its arguments with ReadArgs. Whether the engine's own command line works is unchecked.

## Where

Amiga C start-up of the SDK; `engine/aga`.

## How it happened

Unknown.

## Why it was not caught

The engine is started without arguments today.

## Reproduction

Start `awbench cpu` from the boot shell with the plain C start-up.

## Repair

Not yet: check the engine command line; use ReadArgs where arguments matter.

## Verification

Pending.

## Prevention

A boot-shell argument test.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Boot and engine start-up (`boot-startup`). The boot check and engine start-up report problems clearly and never stop the game silently. See [families](README.md#families).

- [BOOT-68060-FPU-FAIL-32](BOOT-68060-FPU-FAIL-32.md): On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops
- [BOOT-CONSOLE-WIDTH-32](BOOT-CONSOLE-WIDTH-32.md): Boot check lines wrap on the 64-column boot console
- [BOOT-VOLUME-NOT-VALIDATED-33](BOOT-VOLUME-NOT-VALIDATED-33.md): At boot AmigaOS asks Volume AMIWIND is not validated (Retry/Cancel) while the game starts
- CFG-01 (no report page): Semicolons in default-config comments ran as console commands
- CONFIG-COMMENT-29 (no report page): Semicolons split default-config comments into commands
- CRASH-REPORT-02 (no report page): Fatal engine exit returned to AmigaDOS without a visible reason
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- END GENERATED CATEGORY -->
