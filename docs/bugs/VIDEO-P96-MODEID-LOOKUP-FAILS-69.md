# VIDEO-P96-MODEID-LOOKUP-FAILS-69: On some Picasso96 setups, such as one on PiStorm, the game cannot find its screen mode at start

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 25 November 2026, in v0.0.68 |
| Where | start-up, screen mode choice on graphics cards (RTG) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.68 (last seen) |
| Severity | medium: on an affected setup the game does not start; the emulator's graphics card and other setups are not affected |
| Family | Boot and engine start-up (`boot-startup`) |
| Playtest version | unknown |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | a tester's report from real hardware; the build was not named |
| Platform or emulator | Amiga with an RTG graphics card through Picasso96 (seen on PiStorm) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.69-dev2 (7dfbbe60) | 2026-11-25 | gate 13202 of the planning item VIDEO-P96-MODEID-LOOKUP-FAILS-69 | With a graphics card the game checks the screen mode the card offers, searches the card's modes when it cannot be used, and opens the native AGA screen when none can; every step is logged. |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-25: reported in v0.0.68
- 2026-11-25: fixed in source: a gated commit, v0.0.69-dev2 (7dfbbe60); gate 13202 of the planning item VIDEO-P96-MODEID-LOOKUP-FAILS-69: With a graphics card the game checks the screen mode the card offers, searches the card's modes when it cannot be used, and opens the native AGA screen when none can; every step is logged.

<!-- END GENERATED TIMELINE -->

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
- [STARTUP-THEME-TIMING-23](STARTUP-THEME-TIMING-23.md): The startup logo faded too quickly and the theme started late
- VIDEO-NTSC-NO-PAL-MODE-58 (no report page): On an NTSC machine the game stops at start: it asks for a PAL screen mode by name

<!-- END GENERATED CATEGORY -->
