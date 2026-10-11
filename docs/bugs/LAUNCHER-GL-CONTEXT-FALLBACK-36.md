# LAUNCHER-GL-CONTEXT-FALLBACK-36: The Linux launcher ends in a raw X error when FS-UAE cannot create an OpenGL context

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 10 October 2026, in v0.0.35 |
| Where | tools/AmiWind-FS-UAE-launcher.py and the package's RUN-FS-UAE.sh (Linux) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.35 (last seen) |
| Severity | low: The game does not start until the player finds the cause; a known fallback exists (Mesa software OpenGL) |
| Family | Boot and engine start-up (`boot-startup`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3cbe85a |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Open. Workaround: start the launcher with Mesa's software OpenGL, `LIBGL_ALWAYS_SOFTWARE=1 ./RUN-FS-UAE.sh`.

## Symptom

The launcher's host preflight passes, FS-UAE starts, and then it stops with an X error from the GLX extension
(`X_GLXCreateContext`, `BadValue`) before any window opens. The launcher prints nothing that explains it.

## Where

The Linux start path: the package's `RUN-FS-UAE.sh` and `tools/AmiWind-FS-UAE-launcher.py`, which start FS-UAE and
pass its exit through unexplained.

## How it happened

FS-UAE needs an OpenGL context. When the host's GL stack cannot create one (a graphics driver updated without a
reboot, a remote or forwarded display, a missing GL library), FS-UAE exits with the raw X error. The launcher and the
emulator presets did not change between releases; the failure comes from the host.

## Why it was not caught

The launcher was tested on hosts with working OpenGL; no test covers an emulator that fails before opening a window.

## Reproduction

Sometimes: on a host whose GL driver cannot create a GLX context.

## Repair

Planned: the launcher recognises an emulator exit before the first frame with a GLX/OpenGL error, explains the likely
causes in plain words and offers to start again with software rendering.

## Verification

To do: a test with a stubbed emulator that fails this way; the launcher prints the explanation and the retry option.

## Prevention

The same test keeps the fallback in place.

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
- [ENGINE-CRASH-EXIT-KEYBOARD-36](ENGINE-CRASH-EXIT-KEYBOARD-36.md): After AmiWind crashes, the AmigaDOS shell mangles typing: shift/caps latched, M and N never appear
- [ENGINE-STACK-UNCHECKED-35](ENGINE-STACK-UNCHECKED-35.md): The engine never checked the stack it was started with; the pak directory alone needs 128 KiB
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- END GENERATED CATEGORY -->
