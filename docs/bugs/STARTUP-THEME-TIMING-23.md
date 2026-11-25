# STARTUP-THEME-TIMING-23: The startup logo faded too quickly and the theme started late

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 29 September 2026, in v0.0.23-dev3 |
| Where | start-up: logo and title theme |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.23-dev4 |
| Severity | low: cosmetic timing |
| Family | Boot and engine start-up (`boot-startup`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-09-29: reported in v0.0.23-dev3
- 2026-09-29: dev3 regression retest / dev4: The maintainer confirms the port rock is fixed.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66 (16 November 2026)._

## Status: 16 November 2026

Fixed in v0.0.23-dev4. Fixed in v0.0.23-dev4: a two-second fade in, five-second hold and one-second fade out; the theme starts with the logo and continues into the menu (docs/history/feedback/FEEDBACK-v0.0.23-dev3.md). Recorded as an entry from the bug journal on 16 November 2026.

## Symptom

Startup theme and timing.

## Where

Start-up: logo and title theme.

## How it happened

As recorded in the bug journal: see the dated history in the timeline below.

## Why it was not caught

Not recorded.

## Reproduction

As in the symptom; reproduction: always.

## Repair

New fade timings; the theme starts with the logo.

## Verification

See the status and the timeline below.

## Prevention

Not recorded.

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
- HORS-AFTER-HALLOWEEN-CRASH-58 (no report page): dbg aw hors 0 after the Halloween benchmark crashes the game: NUM_FOR_EDICT: bad pointer
- [LAUNCHER-GL-CONTEXT-FALLBACK-36](LAUNCHER-GL-CONTEXT-FALLBACK-36.md): When FS-UAE cannot create an OpenGL context, the Linux launcher ends in a raw X error instead of explaining it and offering software rendering
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present
- VIDEO-NTSC-NO-PAL-MODE-58 (no report page): On an NTSC machine the game stops at start: it asks for a PAL screen mode by name
- [VIDEO-P96-MODEID-LOOKUP-FAILS-69](VIDEO-P96-MODEID-LOOKUP-FAILS-69.md): On some Picasso96 setups, such as one on PiStorm, the game cannot find its screen mode at start

<!-- END GENERATED CATEGORY -->
