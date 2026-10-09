# BOOT-VOLUME-NOT-VALIDATED-33: At boot AmigaOS asks Volume AMIWIND is not validated (Retry/Cancel) while the game starts

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | Boot volume AMIWIND at game start (startup-sequence, engine start-up writes) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: A system requester stops the start; the player must choose Retry or Cancel, and Cancel may lose a write. |
| Family | Boot and engine start-up (`boot-startup`) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the build receipt does not record world commit |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 9 October 2026

Open. Cause measured and reproduced in FS-UAE; repaired in source on v0.0.33-dev (branch
v0.0.33-boot-validate, not merged, not shipped): the engine waits for the validation before
its first write, the optional debug log can no longer stop the game, and the diagnostic logs
stay in memory during play (owner decision, 9 October 2026), so play no longer writes to the
boot volume except for saves.

## Symptom

Right after the boot check printed "AmiWind v0.0.32 preflight OK.", "Starting now." and
"Loading AmiWind v0.0.32", AmigaOS opened a System Request: "Volume AMIWIND is not
validated" with the buttons Retry and Cancel. The game did not continue until one was chosen.

## Where

The boot volume AMIWIND (first partition of the game disk, FFS, 512-byte blocks, about
1.9 GB). `engine/aga/src/sys_amiga.c`: `main()` prints "Loading AmiWind" and then starts the
engine, whose first act is to create `DEBUG.TXT` on that volume (`Sys_Printf`, compiled in
because the engine is built without `NDEBUG`).

## How it happened

Measured in FS-UAE 3.1.66 (Docker, fresh copies of the private CHIM preview disks, the volume
state read from the root block's bitmap flag every 0.2 s):

- The game writes to AMIWIND from the first second: `DEBUG.TXT` and `music-events.csv` at
  start (11 s after power-on with the fast setting); during play the diagnostic logs
  (`walk-profile.csv`, `frame-stalls.csv`, `heap-audit.log`, `cell-load-profile.tsv`,
  `bsp-load-profile.txt`, `DEBUG.TXT`), `console-history.txt` on each console command, saves
  and autosaves; at Exit game `config.cfg`, `keymaps.cfg`, `frame-profile.txt` and
  `music-profile.txt`.
- After each write the file system marks the volume not validated for about one second
  (emulated time). Standing in Seyda Neen the volume was written every 6 to 10 s and was in
  that state 42 of 282 s (15 %); in the exit dialog every 2 to 3 s.
- If the emulator is closed, reset or killed in such a second, the flag stays "not validated"
  on disk and AmigaOS validates the whole volume at the next boot. Reproduced by stopping
  FS-UAE during a write: the flag read 0 afterwards.
- Next boot, fast setting (JIT, fastest CPU): the validation ends during the boot check's
  5-second countdown; no request appeared.
- Next boot, slow setting (cycle-exact 68040, CPU multiplier 14, JIT off): the request
  appeared about 15 s after power-on, identical to the owner's screenshot. The validation ended
  between 48 and 59 s after power-on (Retry at 26, 37 and 48 s brought the request back;
  Retry at 59 s let the game start). Retry after about 5 minutes also worked.
- Cancel stopped the game: "AmiWind v0.0.32 crashed! Crash details: Error opening DEBUG.TXT",
  because the debug log was opened through a helper that treats any failure as fatal.

So the request is AmigaOS waiting for its own disk check, triggered by an earlier session that
ended mid-write; the slow setting only makes the check outlast the boot check.

Side finding: FS-UAE keeps the last written block in a host buffer until the next disk access
or until it quits normally, so a hard kill of the emulator can also lose the write that marks
the volume validated again.

## Why it was not caught

Every automated boot test starts from a fresh copy of a clean disk image and uses the fastest
emulator setting, where the check is hidden by the boot countdown; no test ended a session
mid-write and then booted slowly.

## Reproduction

Boot the image, play, stop the emulator during a write (the volume is written every few
seconds in play), boot again with a cycle-exact 68040 at multiplier 14 and JIT off. Fast
setting: no request (the check is hidden).

## Repair

In source on v0.0.33-dev (branch v0.0.33-boot-validate):

- `main()` calls `AW_WaitBootVolumeValidated()` before `Sys_Init()`: it asks AmigaOS for the
  state of the program's volume (`Info()` on `PROGDIR:`) and, while it reports
  `ID_VALIDATING`, prints "The game volume is being validated: the last session / did not end
  cleanly. Waiting for AmigaOS to finish..." once and waits in 1-second steps (at most 900 s,
  then it starts anyway). Nothing is written while it waits.
- The previous immediate start stays selectable: the local shell variable
  `AmiWindValidateWait` set to `0` in `S:startup-sequence` (`Set AmiWindValidateWait 0`)
  skips the wait. Only the local variable is read, never `ENV:`, which the boot disk does not
  assign.
- `Sys_Printf` opens `DEBUG.TXT` with `fopen` once; if that fails (for example after Cancel)
  the game runs without the log instead of stopping, and it does not try again on every print.
- docs/FS-UAE-LAUNCHER.md tells players to quit with Exit game and wait for the shell prompt
  before closing the emulator, and what to do with the request on older builds (wait about a
  minute, Retry, never Cancel).

Diagnostic logs off the disk during play (owner decision, 9 October 2026):

- `engine/aga/src/aw_log.c`: `DEBUG.TXT`, `walk-profile.csv`, `frame-stalls.csv`,
  `frame-profile.txt`, `heap-audit.log`, `cell-load-profile.tsv`, `cell-visible-profile.tsv`,
  `bsp-load-profile.txt`, `music-events.csv`, `music-profile.txt` and `console-history.txt`
  each have one fixed buffer (41 KiB in all, static, no growth); when a buffer is full the
  oldest whole lines drop. Stream logs keep their header line apart, so a written file always
  starts with it.
- They are written once at Exit game (`Sys_Quit`, after the settings), after a fatal error's
  crash report (`Sys_Error`, so the heap audit's fatal-exit phase survives), and on demand with
  `dbg savelogs` ("Saved 8 diagnostic log files to AMIWIND: (0 older lines dropped ...)").
  A second write adds only lines that are new; `heap-audit.log` and the cell profiles are
  appended as before.
- The previous method stays: `aw_logs_live 1` writes every log as it happens, exactly as
  before. `dbg logs live on/off` sets it and saves it in `config.cfg` (only once the player has
  set it; the default `0` is not written). Turning it on first writes what is buffered.
  Builder option `--live-logs` (benchmark and diagnostic images) puts `aw_logs_live 1` in the
  image's `default-game.cfg` and records `diagnostic-logs.json`. Benchmark readers
  (`tools/profile_aga.py`) read the same files either way; a benchmark run uses a live image or
  `dbg logs live on` so `walk-profile.csv` holds every sample.
- Saves, autosaves and the settings are written as before.

## Verification

FS-UAE, the gate engine of this change on the same disks, volume made dirty by stopping the
emulator during a write, slow setting: the notice appeared after "Loading AmiWind", no request,
the AmiWind logo at about 50 s and the main menu at about 55 s. With `Set AmiWindValidateWait 0`
in `S:startup-sequence` the old request appeared again (old behaviour kept), and Cancel then
let the game reach the main menu instead of stopping it. Full gate green.

Logs in memory, measured in FS-UAE on the slow setting (cycle-exact 68040, multiplier 14),
same disks, the gate 565 engine, root block read every 0.2 s:

| Engine | Play time measured | Write bursts during play | Volume "not validated" |
| --- | --- | --- | --- |
| previous (CHIM Preview 1 engine), slow setting | 410 s | 6 | 3.7 % of the time |
| previous, fast setting (first measurement) | 282 s | 32 | 15 % |
| logs in memory, slow setting, three sessions | 510 + 311 + 534 s | 0 | 0 % |

- Hard kill (SIGKILL of the emulator) after 534 s of play with the new engine: the volume read
  validated, so the next boot needs no validation. With the previous engine a kill or a closed
  window lands in a write about 4 % (slow setting) to 15 % (fast setting) of the time.
- `dbg savelogs`: one write burst and the message above. `dbg logs live on`: the buffered lines
  were written, then live writes again (one burst in 60 s on the slow setting, 8 % of that
  minute "not validated"); `dbg logs live off`: one last burst closing the live files, then
  quiet. Exit game: one burst writing the settings and the logs; the emulator closed in the exit
  dialog left the volume validated (the previous engine wrote every 2 to 3 s there).
- Not covered by these runs: autosaves. The measured sessions started with the demo start,
  which made no autosave in 9 minutes; a story autosave every 5 minutes is one write of about
  1 to 2 s (estimate from the save writes measured before, not measured here), so play keeps
  the volume quiet except for saves.
- Map changes (sn029 to sn034) wrote nothing.

## Prevention

`tests/test_boot_volume_validation.py`: source checks that the wait runs before `Sys_Init()`
and `Host_Init()`, reads `ID_VALIDATING` from `PROGDIR:`, uses only the local variable, writes
nothing, and that `Sys_Printf` has no fatal path; a native harness
(`tests/aga_validate_wait_test.c`) runs the real wait against scripted AmigaDOS answers (clean
volume, 3 s validation, the time limit, the opt-out, no lock, no memory, 63-column lines).

Logs: `tests/aga_log_test.c` (via `tests/test_diagnostic_logs.py`) checks the buffers are
fixed and bounded, keep the newest whole lines in order, write nothing to disk before a flush,
write header plus lines at the first flush and only new lines later, switch to and from live
mode without losing or repeating lines, and never stop on a file that cannot be created; the
benchmark reader `tools/profile_aga.py` is run on the files of a live and of a buffered run.
Source checks: no engine file opens a diagnostic log itself, the switch is bound before the
first write, the logs are flushed at Exit game and after the crash report, the switch defaults
to off and is saved only when the player sets it, and `--live-logs` reaches the image step only
when asked.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Boot and engine start-up (`boot-startup`). The boot check and engine start-up report problems clearly and never stop the game silently. See [families](README.md#families).

- [BOOT-68060-FPU-FAIL-32](BOOT-68060-FPU-FAIL-32.md): On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops
- [BOOT-CONSOLE-WIDTH-32](BOOT-CONSOLE-WIDTH-32.md): Boot check lines wrap on the 64-column boot console
- CFG-01 (no report page): Semicolons in default-config comments ran as console commands
- CONFIG-COMMENT-29 (no report page): Semicolons split default-config comments into commands
- CRASH-REPORT-02 (no report page): Fatal engine exit returned to AmigaDOS without a visible reason
- [ENGINE-ARGS-32](ENGINE-ARGS-32.md): The C start-up passes no arguments from the boot shell
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- END GENERATED CATEGORY -->
