# ENGINE-STRICT-WARNINGS-36: The engine builds warning-free only under -Wall -Wno-unused; stricter flags show 482 warnings

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.36-dev3 at 2026-10-11 02:12 +0300: diagnostic engine build of c8bf614 with -Wextra -Wuninitialized -Wmaybe-uninitialized -Wmissing-field-initializers -Wshadow -Wunused: 482 distinct warnings
- Reported with v0.0.46 at 2026-10-20 23:29 +0300: outside review of v0.0.46 (registered 2026-10-20 20:29 UTC): gate still -Wall -Wno-unused; 451 warnings at -Wall -Wextra, 35 printf mismatches

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/Makefile WARN_FLAGS; engine/aga/src (printf-like functions, aw_ui.c, sv_move.c, ...) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3, v0.0.46 (last seen) |
| Severity | medium: uninitialised, shadowed and unused code can hide real faults that the gate cannot see |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | v0.0.36-dev3 |
| From commit | source 3b5e7a9, engine 3b5e7a9, CHIM world 3b5e7a9 |
| CHIM engine version | CHIM 0.1.0, engine 3b5e7a9, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Status: 20 October 2026](#status-20-october-2026)
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

## Status: 20 October 2026

PERSISTING since v0.0.36-dev3 (11 October 2026): an outside review of v0.0.46 raised it again on 20 October 2026,
and nothing had changed since the first report (still `-Wall -Wno-unused`). Repair ready on the branch
v0.0.47-strict-warnings, not yet on the development line: the real faults the stricter warnings show are fixed and
the gate's warning level is raised (below). What is still left: the warnings the new level does not ask for, all
classified as noise below; they are counted, not fixed.

### Measured on v0.0.46 (20 October 2026)

Distinct warnings over every engine variant the gate builds (`c` for the 68040 and the 68060, `upstream` at `-O1`
and `-O2`, `c` with its variables spelled out), split by file: AmiWind's own files (`aw_*.c`, `chim/*.c`, their
headers), inherited AmiQuake files AmiWind changed, and inherited files unchanged since upstream revision 9c62d90.

| Flags | Before: own / changed / unchanged = total | After |
| --- | --- | --- |
| `-Wall -Wno-unused` (the old gate) | 0 / 0 / 0 = 0 | 0 |
| the same, printf-like functions checked | 1 / 34 / 0 = 35 | 0 |
| `-Wall -Wextra -Wno-unused` | 227 / 193 / 31 = 451 | 157 / 190 / 31 = 378 |
| `-Wall -Wunused` | 5 / 15 / 1 = 21 | 0 / 15 / 1 = 16 |
| `-Wall -Wextra -Wno-unused -Wshadow -Wconversion -Wdouble-promotion -Wformat=2 -Wmissing-prototypes -Wundef -Wpointer-arith` | 1,375 / 2,168 / 525 = 4,068 | 1,231 / 2,164 / 525 = 3,920 |
| the new gate level (below) | 127 / 3 / 0 = 130 | 0 |

What is left after the repair is noise: `-Wmissing-field-initializers` (343: the `cvar_t` definitions name only
their first fields), `-Wconversion` / `-Wsign-conversion` / `-Wfloat-conversion` (2,566: integer and float
narrowing that Quake does on purpose), `-Wdouble-promotion` (488: float values widened for double constants and
calls; the 68040 FPU computes in extended precision either way, so this is a speed question, not a fault),
`-Wmissing-prototypes` in inherited files (429: Quake declares many functions only where they are used),
`-Wundef` (39: `#if id68k` and the engine profile switches, meant to be 0 when undefined), and in inherited files
signed/unsigned comparisons (35), shadowed names (19) and unused locals (16), each read and found harmless.

## Symptom

The engine gate builds with `-Wall -Wno-unused` and requires zero warnings. A diagnostic build of c8bf614 (the
v0.0.36-dev3 line) with `-Wall -Wextra -Wuninitialized -Wmaybe-uninitialized -Wmissing-field-initializers -Wshadow
-Wunused` at the same -O1 shows 482 distinct warnings. Among the files changed since v0.0.35: view.c 35,
chim/chim_world.c 18, sv_phys.c 5, chim/chim_far.c 5, aw_music.c 2, and one each in sv_main.c, chim/chim_models.c,
chim/chim_graft.c and chim/chim_chunks.c. None in aw_aread.c, where the dev3 crash was.

## Where

`engine/aga/Makefile` (`WARN_FLAGS = -Wall -Wno-unused`) and the engine sources.

## How it happened

The zero-warnings rule was enforced only for the flags the gate uses; stricter warnings were never looked at.

## Why it was not caught

The gate's flags hide unused, shadowed and possibly uninitialised variables, and missing field initialisers.

## Reproduction

Build the engine with the flags above (`make -B fpu WARN_FLAGS="..."`) and count the `: warning:` lines. The full list
of the diagnostic build is kept with the private evidence of the dev3 crash investigation.

## Repair

20 October 2026, branch v0.0.47-strict-warnings, in two commits.

Faults fixed (the engine binary changes, only in the objects of these files):

- The printf-like engine functions (`Con_Printf`, `Con_DPrintf`, `Sys_Error`, `Sys_Printf`, `Host_Error`,
  `Host_EndGame`, `SV_ClientPrintf`, `SV_BroadcastPrintf`, `PR_RunError`, `va`, `AW_LogPrintf`, `COM_FormatPath`)
  had no format attribute, so no warning level checked their callers. With it, `-Wall` found 35 mismatches.
  Real: `FloorDivMod` printed a `double` with `%d` (the error text was wrong); `Con_NotifyBox` and the network
  reject reason passed text as the format (a `%` in it would be read as a conversion). The other 32 printed an
  `int` with `%ld` or the reverse, harmless on the Amiga (both 32 bits), corrected to the matching conversion.
- `SV_NewChaseDir` (inherited Quake code) compared float distances with the integer `abs()`, which cuts the
  fractions: now `fabs()`.
- The screen size (`vid.width`, `vid.height`) is unsigned, so a negative position compared with it became a huge
  number. `AW_UIFill` turned a rectangle wholly left of or above the screen into a fill of the whole row span or
  column; text that started left of the screen was dropped instead of clipped (`AW_SmallString`, the arena labels);
  the gallery's right-aligned text could hand `Draw_Character`, which does not clip, a position just left of the
  screen. AmiWind's own files now compare the screen size as `int`, and the gallery skips characters left of it.

Noise fixed in AmiWind's own files without a code change (their objects are byte-identical): names that shadowed a
global or an outer local were renamed; unused locals removed; two header helpers marked unused; functions called
from another file now have one shared prototype (`aw_links.h`, `aw_c2p.h`) that both the defining file and the
callers include, so a mismatched call is a compile error. One inherited fall-through is marked as intended.

The gate's warning level (`engine/aga/Makefile`): every file builds with `-Wall -Wextra -Wformat-security`, less
three checks that are noise in the inherited Quake code (unused code, partly initialised structs, signed/unsigned
comparisons); AmiWind's own files get those back (unused parameters excepted) plus `-Wshadow` and
`-Wmissing-prototypes`. The builder fails on any warning, so a new warning in either set stops the build.

## Verification

- Warning flags do not change the generated code: the fixed source built with the old flags (`-Wall -Wno-unused`)
  and with the new level gives the same SHA-256 in every engine variant the gate builds (the 68040 `c` engine
  `2d1fbf11...`, the 68060 engine, `upstream` at `-O1` and `-O2`).
- The fixes change the 68040 `c` engine from `f2c246bc...` (the v0.0.46 dev head) to `2d1fbf11...`. Objects
  compared one by one: only the 27 files with the format, `fabs` and signed comparison changes above differ
  (in `chim_world.o` only a renamed static variable's symbol, which the stripped binary does not carry).
- `tests/test_engine_warnings.py`: the make command lines of every engine variant carry the two levels; every
  printf-like declaration carries the format attribute; the fixed faults stay fixed.
- The gate's engine step builds every variant at the new level with zero warnings.

## Prevention

The raised gate level keeps both sets at zero, and the format attribute makes every printf-like call checked. A new
printf-like function without the attribute fails `tests/test_engine_warnings.py`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- [AW-RESULT-RECIPE-SAVED-36](AW-RESULT-RECIPE-SAVED-36.md): The master builder's result of a failed build from a requested recipe does not validate (recipe.saved left in)
- [AW-RUN-NAME-LONG-REASON-36](AW-RUN-NAME-LONG-REASON-36.md): aw gate refuses a long --reason after leasing the gate number: the run name, used as the request id, passes 128 characters
- [BUILD-CHECKLIST-JSON-CELLS-39](BUILD-CHECKLIST-JSON-CELLS-39.md): Exterior checklist rejects JSON cell coordinates before scenery conversion
- [BUILD-DEV1-EMULATOR-PRESETS-39](BUILD-DEV1-EMULATOR-PRESETS-39.md): Version bump omitted the matching dev1 emulator presets
- [BUILD-EMPTY-ACTOR-GATE-38](BUILD-EMPTY-ACTOR-GATE-38.md): Actor contact gate rejects a MiniWind exterior without residents
- [BUILD-EMPTY-RESIDENT-POOL-38](BUILD-EMPTY-RESIDENT-POOL-38.md): Town conversion starts a zero-worker pool when no residents are present
- [BUILD-EXECUTABLES-LIST-UNGATED-36](BUILD-EXECUTABLES-LIST-UNGATED-36.md): A file committed executable but missing from tools/release.py EXECUTABLES (tools/engine_smoke.py) broke the source ZIP only at kit time
- [BUILD-FACE-KEY-FORM-TEST-48](BUILD-FACE-KEY-FORM-TEST-48.md): The face key test tied the gallery face keys to the stage key form; stage keys in form 3 failed it (the faces rightly keep form 2)
- [BUILD-LAVA-CORE-BOUNDS-38](BUILD-LAVA-CORE-BOUNDS-38.md): Lava sandbox bounds are not divisible by its core size
- [BUILD-LAVA-PRESET-FIXTURE-38](BUILD-LAVA-PRESET-FIXTURE-38.md): Lava sandbox addition omitted the preset inventory fixture
- [BUILD-SEYDA-CARRIER-VOICE-DIR-40](BUILD-SEYDA-CARRIER-VOICE-DIR-40.md): Fresh Seyda carrier cannot publish a resident voice without an inherited sound directory
- [BUILD-SHADOWED-WORLD-MAPS-38](BUILD-SHADOWED-WORLD-MAPS-38.md): Full image retains BSP maps shadowed by higher-priority world routes
- [BUILD-TOOLKIT-VERSION-40](BUILD-TOOLKIT-VERSION-40.md): Development source retains the prior Toolkit release label
- [BUILD-VERSION-EMULATOR-PRESETS-38](BUILD-VERSION-EMULATOR-PRESETS-38.md): Version bump omitted matching emulator presets
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](BUILD-WORLD-FINGERPRINT-RETIRED-38.md): Content fingerprint requires an explicitly retired exterior BSP
- [BUILD-WORLD-PACK-RETIRED-38](BUILD-WORLD-PACK-RETIRED-38.md): World disk packer requires explicitly omitted exterior BSP maps
- [CHIM-SEYDA-RECEIPT-TEXT-40](CHIM-SEYDA-RECEIPT-TEXT-40.md): New Seyda metadata and carrier writers omit explicit UTF-8 and LF
- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-NEW-BUILDER-RULES-35](CI-NEW-BUILDER-RULES-35.md): Hosted CI failed on v0.0.35: the previous-release check refused the one-commit checkout and the run-name rule refused the Docker check's run name
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies
- [GATE-EMBERS-31](GATE-EMBERS-31.md): Ember commit broke native torch tests and a header format check
- [GATE-HOSTPARITY-TEMP-RACE-33](GATE-HOSTPARITY-TEMP-RACE-33.md): Two gates running at once share the host-parity step's log file, so one gate can report the other's error
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-NUMPY-PATH-SCRATCH-33](GATE-NUMPY-PATH-SCRATCH-33.md): The gate's NumPy and Pillow import folder lived in a temporary per-session folder, so gates broke once it was removed
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SHARED-SOURCE-32](GATE-SHARED-SOURCE-32.md): The local gate always tested the main checkout, in one shared folder
- [GATE-SOURCE-RACE-33](GATE-SOURCE-RACE-33.md): The local gate copies the working tree after its clean check, so edits during the copy reach the tested source
- [GATE-SUITE-WRITABLE-32](GATE-SUITE-WRITABLE-32.md): The test suite needs a writable source copy and an executable /tmp; the documented command does not say so
- LINUX-VALID-02 (no report page): Linux test fixtures failed to link (missing stubs)
- [MWAD-TEXT-WRITER-LF-35](MWAD-TEXT-WRITER-LF-35.md): Some JSON and text writers do not pin LF and UTF-8
- [OPS-GATE-UNLISTED-TESTS-36](OPS-GATE-UNLISTED-TESTS-36.md): The gate runs only the tests listed in the public file list, and nothing checked that every test file is listed
- [PLAYTEST-SHIPPED-WITHOUT-SMOKE-36](PLAYTEST-SHIPPED-WITHOUT-SMOKE-36.md): The v0.0.36-dev3 private playtest package was published with an engine that dies on every map load: no ship step or gate booted it
- [RELEASE-INCLUSION-CHECK-LATE-48](RELEASE-INCLUSION-CHECK-LATE-48.md): The release guard does not check the CHIM inclusion ledger: the v0.0.48 kit stopped in its source step after the guard and the full suite had passed
- [RELEASE-KIT-NO-REPAIR-MODE-35](RELEASE-KIT-NO-REPAIR-MODE-35.md): The release kit has no repair mode for a commit already pushed
- [RELEASE-KIT-PUSH-BEFORE-CI-45](RELEASE-KIT-PUSH-BEFORE-CI-45.md): The release kit pushes to main before CI has passed
- [RELEASE-KIT-RETRY-REUSES-CI-45](RELEASE-KIT-RETRY-REUSES-CI-45.md): A kit retry after a CI failure reads the same failed run again
- [RELEASE-LAVA-IMAGE-ALLOWLIST-38](RELEASE-LAVA-IMAGE-ALLOWLIST-38.md): Lava documentation images were listed without image-type approval
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [RELEASE-PATCH-TARGET-VERSION-39](RELEASE-PATCH-TARGET-VERSION-39.md): RC1 publication baseline lacks its target version
- [ROOM-TRACE-VISIT-GUARD-48](ROOM-TRACE-VISIT-GUARD-48.md): Long downward traces on the Hall of Processing's collision raise the trace visit guard (Cyclic or excessive collision tree)
- [SMOKE-PASSES-WITHOUT-MAP-36](SMOKE-PASSES-WITHOUT-MAP-36.md): The engine boot smoke passed while its first map ran under the title menu: a loaded server was taken for a played map
- TEST-ACTOR-LIBRARY-OFF-PLAN-48 (no report page): test_actor_library StageTests.test_on_by_default_off_selectable fails on the interiors line: the actor-library stage stays in the plan with --chim-actor-table off
- [TEST-CENSUS-CONTRACTS-40](TEST-CENSUS-CONTRACTS-40.md): Three quick-character expected failures lack reconciled contracts
- [TEST-CHIM-BIG-FRAME-TIMEOUT-33](TEST-CHIM-BIG-FRAME-TIMEOUT-33.md): The Balmora-sized CHIM world test times out on a busy host
- TEST-CHIMPORT-POOL-COPY-REUSE-48 (no report page): test_chimport_pool test_copy_mode_reuses_by_verified_copy fails on the interiors branch head
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded host (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- [TEST-GODMODE-UNLISTED-36](TEST-GODMODE-UNLISTED-36.md): The dbg godmode test was never run by the gate (missing from the public file list) and its escape check failed
- TEST-MWAD-MODULE-SHADOW-48 (no report page): test_room_late_passes fails to import when test_optimize_world_maps runs before it in the same process: tools/mwad.py hides the mwad package
- [TEST-NATIVE-STALE-IMPORT-33](TEST-NATIVE-STALE-IMPORT-33.md): Native engine tests run alone generate their version headers with the builder image's old tools copy
- [TEST-NATIVE-TMPDIR-32](TEST-NATIVE-TMPDIR-32.md): A native test overflows a 64-byte name buffer when the temp path is long
- [TEST-PARALLEL-ORDER-FLAKY-36](TEST-PARALLEL-ORDER-FLAKY-36.md): test_processes_keep_order_and_limit_nested_threads is timing-sensitive and fails now and then
- [TEST-PARALLEL-ORDER-LOAD-33](TEST-PARALLEL-ORDER-LOAD-33.md): The process-pool order test fails on a fully loaded host (one worker process takes every item)
- [TEST-PARALLEL-SHARE-TIMING-36](TEST-PARALLEL-SHARE-TIMING-36.md): The fair-share scheduler test watched the freed budget for a fixed 4 s and failed on a busy host
- TEST-PORT-01 (no report page): Focused tests depended on repo root and Windows UTF-8 mode
- TEST-PORTABILITY-01 (no report page): Pre-release test fixtures assumed host features and links
- [TEST-PROFILE-OVERHEAD-SAMPLES-36](TEST-PROFILE-OVERHEAD-SAMPLES-36.md): The profiler overhead test sampled for a fixed 2 s and got too few samples on a busy host
- [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md): The build profile section test fails on a loaded host (CPU time read in clock ticks)
- [TEST-PROFILE-STAGE-WALL-32](TEST-PROFILE-STAGE-WALL-32.md): The build profile stage test needs an idle host (wall time compared with CPU time)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a busy host
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded host (timeline CPU above the stage's own CPU)
- [TEST-RC1-INTEGRATION-CONTRACTS-39](TEST-RC1-INTEGRATION-CONTRACTS-39.md): RC1 regression tests assume the old fingerprint location and a separate class cache unit
- [TEST-SPAWN-SCAN-DOCSTRING-KEY-48](TEST-SPAWN-SCAN-DOCSTRING-KEY-48.md): The spawn contract scan read a docstring example in hand_metadata.py as a map key named key
- [TEST-TOWN-BOUNDS-40](TEST-TOWN-BOUNDS-40.md): Town expansion left recovery fixtures and coordinate audit stale
- TEST-TRACKER-SLOW-48 (no report page): Bug register render, contents check and tracker tests take 5 to 6 minutes on one core
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TESTS-HEAD-REDUCER-BYTES-CI-45](TESTS-HEAD-REDUCER-BYTES-CI-45.md): A byte-exact head reducer test fails on some GitHub runners
- [TESTS-SUPERVISOR-START-CLOCK-46](TESTS-SUPERVISOR-START-CLOCK-46.md): A scheduler test sorted units by the clock each worker read, and failed when the host delayed a thread
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks

<!-- END GENERATED CATEGORY -->
