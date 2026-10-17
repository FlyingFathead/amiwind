# ENGINE-CRASH-EXIT-KEYBOARD-36: After AmiWind crashes, the AmigaDOS shell mangles typing: shift/caps latched, M and N never appear

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 6 times; something has to be done

- Reported with v0.0.25 at 2026-10-01 (time not recorded): earlier entry AW25-05 (v0.0.25): console typed only capitals and shifted digits; stuck Shift suspected, never reproduced natively
- Reported with v0.0.29-dev1 at 2026-10-05 12:07 +0300: earlier entry CONSOLE-CAPS-29 (v0.0.29-dev1, FS-UAE): Caps Lock appears stuck in the F10 console
- Reported with v0.0.36-dev5 at 2026-10-11 13:12 +0300: maintainer, dev5 playtest build, FS-UAE JIT: after the efrag crash the shell typed amiwind as AIWDID (capitals, M and N missing)
- Reported with v0.0.36-dev5 at 2026-10-11 13:35 +0300: maintainer, after the Balmora crash: AMIWIND arrives (M and N too) but all in capitals, no Shift or Caps Lock pressed
- Reported with v0.0.36-dev5 at 2026-10-11 13:36 +0300: maintainer, AmiWind restarted without a reboot: in the main menu the cursor keys move the mouse pointer (a latched Amiga qualifier)
- Reported with v0.0.36-dev5 at 2026-10-11 13:38 +0300: maintainer, same restarted run: console typed 1234567890 as !@#$%^&*() (a latched Shift inside the new run)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 1 October 2026, in v0.0.25 |
| Where | engine sys_amiga.c Sys_Error and Sys_Quit, the input.device handler AW_InputGuardInit |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.36-dev5 (last seen) |
| Severity | high: After a crash the shell is unusable until a reboot; the player cannot restart the game by typing |
| Family | Boot and engine start-up (`boot-startup`) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | Platform: FS-UAE, JIT, A1200 68040; dev5 playtest build 6c29a23 |
| Platform or emulator | FS-UAE, JIT, A1200 68040 (maintainer, dev5 playtest build); AmigaDOS shell after the crash and the next AmiWind run |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
- [Status: 11 October 2026](#status-11-october-2026)
- [Symptom](#symptom)
- [Evidence](#evidence)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 11 October 2026

Open and PERSISTING. The maintainer reports it since very early AmiWind versions; the exact first version is unknown.
The earliest tracker entries are AW25-05 (v0.0.25: the console typed only capitals and shifted digits)
and CONSOLE-CAPS-29 (v0.0.29-dev1: Caps Lock stuck in the F10 console). Both are listed as report lines above.
Repaired in source, not yet gated.

## Symptom

After the v0.0.36-dev5 playtest stopped with "AmiWind crashed!"
([CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md)), typing went wrong, both in the AmigaDOS shell
and in the next AmiWind run (no reboot):

| When (maintainer, 11 October 2026) | Where | What arrived |
| --- | --- | --- |
| 13:12 and 13:14 | AmigaDOS shell after the crash | "amiwind" came out as "AIWDID". A longer try came out as a long stretch of capitals ("AIWDIDAIDWIIAIDSADAIADSADASFDJKF"), then lowercase ("qeowietweitaid"). No m or n anywhere. |
| 13:35 | AmigaDOS shell after the Balmora crash | "AMIWIND": M and N arrive, but everything is in capitals with no Shift or Caps Lock pressed |
| 13:36 | AmiWind restarted from that shell, main menu | the cursor keys move the mouse pointer in steps instead of the menu highlight (Intuition's keyboard mouse control, which needs the Amiga key) |
| 13:38 | the same restarted run, console | "dbg aw hors 1234567890" came out as "dbg aw hors !@#$%^&*()" (Shift held inside the new run) |
| Total | 4 incidents | Shift, Caps Lock or Amiga qualifiers latched; M and N eaten in the first one |

## Evidence

The maintainer's photos (11 October 2026 13:12, 13:14, 13:35, 13:38) and reports, FS-UAE, dev5 playtest build 6c29a23,
JIT.

The engine installs an input.device handler, "AmiWind screen keys" (`sys_amiga.c`, `AW_InputGuardInit`). That handler
takes the Amiga qualifier off raw keys 0x36 (N) and 0x37 (M), so Intuition does not switch screens. M and N are
exactly the keys that went missing in the first incident.

The game's own key code took the event qualifiers as authoritative (`keys.c`, `Key_AmigaQualifiers`: "even after a
lost key-up event"). A Shift bit latched in the input stream therefore made the game type shifted characters even
though no Shift key went down in that run.

## Where

- `engine/aga/src/sys_amiga.c`: `AW_InputGuardInit`, `AW_InputGuardEvents`, `AW_InputGuardShutdown`, `Sys_Error`,
  `Sys_Quit`, `Sys_SendKeyEvents`.
- `engine/aga/src/vid_amiga.c`: `VID_Shutdown`, the only place that removed the handler.
- `engine/aga/src/keys.c`: `Key_AmigaQualifiers`.

## How it happened

Two parts:

1. **The exit route.** The handler left input.device's chain only in `VID_Shutdown`, at the end of `Host_Shutdown`.
   On the crash route, `Sys_Error` runs `Host_Shutdown`. If a shutdown step fails again, or `Host_Shutdown` is already
   running, it returns early ("recursive shutdown") and `VID_Shutdown` never runs. The program then exits with its
   handler still in the chain. Its code and data are freed memory, so every later key event passes through whatever
   is there. That is consistent with qualifiers latched until a reboot, M and N eaten in one run, and different
   behaviour the next time. The exact failing step in the maintainer's runs is not known.
2. **The game trusts latched qualifiers.** A new AmiWind run took the stale Shift, Caps Lock and Amiga bits as real,
   so the console typed symbols and Intuition moved the mouse pointer with the cursor keys.

## Why it was not caught

- The engine smoke ends by killing the emulator. Nothing types at the AmigaDOS shell after the game exits, after a
  normal quit or after a crash.
- The earlier reports (AW25-05, CONSOLE-CAPS-29) were treated as console-input problems. Their link to the exit route
  and to the input handler was not looked for, and no native reproduction was recorded.

## Reproduction

After an AmiWind crash in FS-UAE (JIT): type at the AmigaDOS prompt, then start AmiWind again from it and use the menu
and the console. Not yet repeated on demand.

## Repair

In source, not yet gated:

- `Sys_Error` and `Sys_Quit` remove the handler first, before any shutdown step that could fail.
- `AW_InputGuardInit` registers the removal with `atexit`, so any other `exit()` removes it too.
- The removal can run more than once safely.
- `Key_AmigaQualifiers` counts a Shift, Ctrl or Alt qualifier bit only while this run saw that key held (raw 0x60 to
  0x65, through `Key_AmigaQualifierKey`). It counts the Caps Lock bit only once this run saw the Caps Lock key. A
  focus change clears the held keys.
- The input handler removes the Amiga qualifier from every raw key while the game's window is active and no Amiga key
  is held, so a latched Amiga bit no longer turns the cursor keys into mouse control.

A handler that an older crashed build left behind stays in the chain until a reboot; the game now ignores what it
latches.

## Verification

- `tests/test_efrag_safety_source.py` checks that `Sys_Error` and `Sys_Quit` remove the handler before
  `Host_Shutdown`, and that the removal is registered with `atexit`.
- `tests/aga_crash_report_test.c` checks the order in the real `Sys_Error`: the handler leaves before the heap audit
  and `Host_Shutdown`.
- `tests/aga_console_history_test.c` and `tests/aga_modifier_state_test.c`:
  - a latched Shift bit without a Shift key types plain "aw 1234";
  - a real Shift key types "!" for 1;
  - its release ends the Shift even while the stale bit stays.

Planned in game:
- an engine smoke step that forces an error, types "echo amiwind >AWCTL:echo.txt" at the shell and compares the file
  on the host;
- the same after a normal quit.

## Prevention

- The shell-echo smoke step above, after both a normal quit and a forced error.
- The qualifier tests above.

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
- [ENGINE-STACK-UNCHECKED-35](ENGINE-STACK-UNCHECKED-35.md): The engine never checked the stack it was started with; the pak directory alone needs 128 KiB
- [LAUNCHER-GL-CONTEXT-FALLBACK-36](LAUNCHER-GL-CONTEXT-FALLBACK-36.md): When FS-UAE cannot create an OpenGL context, the Linux launcher ends in a raw X error instead of explaining it and offering software rendering
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

Related bugs in other categories:

- AW25-05 (no report page): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck

<!-- END GENERATED CATEGORY -->
