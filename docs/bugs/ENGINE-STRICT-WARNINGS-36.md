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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-11: reported in v0.0.36-dev3
- 2026-10-11: ENGINE-MUSIC-NO-OFF-SWITCH-36 and ENGINE-STRICT-WARNINGS-36: ENGINE-MUSIC-NO-OFF-SWITCH-36: while isolating CHIM-DEV3-MAPLOAD-CRASH-36 the soundtrack could only be turned off by deleting music/playlist.txt; there is no cvar, option or ...
- 2026-10-11 02:12 +0300: seen again in v0.0.36-dev3: diagnostic engine build of c8bf614 with -Wextra -Wuninitialized -Wmaybe-uninitialized -Wmissing-field-initializers -Wshadow -Wunused: 482 distinct warnings
- 2026-10-20 23:29 +0300: seen again in v0.0.46: outside review of v0.0.46 (registered 2026-10-20 20:29 UTC): gate still -Wall -Wno-unused; 451 warnings at -Wall -Wextra, 35 printf mismatches

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Timeline](#timeline)
- [Status: 20 October 2026](#status-20-october-2026)
  - [Measured on v0.0.46 (20 October 2026)](#measured-on-v0046-20-october-2026)
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

- [ARRIVAL-CHECK-EMPTY-65](ARRIVAL-CHECK-EMPTY-65.md): The image's arrival check passes while it checks no door arrival
- [AW-RESULT-RECIPE-SAVED-36](AW-RESULT-RECIPE-SAVED-36.md): The master builder's result of a failed build from a requested recipe does not validate (recipe.saved left in)
- [AW-RUN-NAME-LONG-REASON-36](AW-RUN-NAME-LONG-REASON-36.md): aw gate refuses a long --reason after leasing the gate number: the run name, used as the request id, passes 128 characters
- [BUILD-ACTOR-SPEC-EXPANSIONS-66](BUILD-ACTOR-SPEC-EXPANSIONS-66.md): With the expansions selected, the image stage stopped on the actor spec check: its room counts were not like for like, and the places the build sets aside counted as missing
- [BUILD-CHECKLIST-JSON-CELLS-39](BUILD-CHECKLIST-JSON-CELLS-39.md): Exterior checklist rejects JSON cell coordinates before scenery conversion
- [BUILD-DEV1-EMULATOR-PRESETS-39](BUILD-DEV1-EMULATOR-PRESETS-39.md): Version bump omitted the matching dev1 emulator presets
- [BUILD-EMPTY-ACTOR-GATE-38](BUILD-EMPTY-ACTOR-GATE-38.md): Actor contact gate rejects a MiniWind exterior without residents
- [BUILD-EMPTY-RESIDENT-POOL-38](BUILD-EMPTY-RESIDENT-POOL-38.md): Town conversion starts a zero-worker pool when no residents are present
- [BUILD-EXECUTABLES-LIST-UNGATED-36](BUILD-EXECUTABLES-LIST-UNGATED-36.md): A file committed executable but missing from tools/release.py EXECUTABLES (tools/engine_smoke.py) broke the source ZIP only at kit time
- [BUILD-FACE-KEY-FORM-TEST-48](BUILD-FACE-KEY-FORM-TEST-48.md): The face key test tied the gallery face keys to the stage key form; stage keys in form 3 failed it (the faces rightly keep form 2)
- [BUILD-FAILURE-REPORT-66](BUILD-FAILURE-REPORT-66.md): Requested: a failed build writes one report file with everything needed to find its cause; the intro stage failure of a build of v0.0.64 and v0.0.65 outside the project came with its traceback, but without the build settings, the versions, which copy of the game data or the stage plan
- [BUILD-GATE-SHORT-SHA-67](BUILD-GATE-SHORT-SHA-67.md): A release build was refused as ungated right after its gate passed: the gate recorded the commit with nine digits and the build looked for eight
- [BUILD-LAVA-CORE-BOUNDS-38](BUILD-LAVA-CORE-BOUNDS-38.md): Lava sandbox bounds are not divisible by its core size
- [BUILD-LAVA-PRESET-FIXTURE-38](BUILD-LAVA-PRESET-FIXTURE-38.md): Lava sandbox addition omitted the preset inventory fixture
- [BUILD-SEYDA-CARRIER-VOICE-DIR-40](BUILD-SEYDA-CARRIER-VOICE-DIR-40.md): Fresh Seyda carrier cannot publish a resident voice without an inherited sound directory
- [BUILD-SHADOWED-WORLD-MAPS-38](BUILD-SHADOWED-WORLD-MAPS-38.md): Full image retains BSP maps shadowed by higher-priority world routes
- [BUILD-TOOLKIT-VERSION-40](BUILD-TOOLKIT-VERSION-40.md): Development source retains the prior Toolkit release label
- [BUILD-VERSION-EMULATOR-PRESETS-38](BUILD-VERSION-EMULATOR-PRESETS-38.md): Version bump omitted matching emulator presets
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](BUILD-WORLD-FINGERPRINT-RETIRED-38.md): Content fingerprint requires an explicitly retired exterior BSP
- [BUILD-WORLD-PACK-RETIRED-38](BUILD-WORLD-PACK-RETIRED-38.md): World disk packer requires explicitly omitted exterior BSP maps
- [CHECKS-NO-WILD-WALK-67](CHECKS-NO-WILD-WALK-67.md): The delivery checks never walk through the open world and never fail on engine error lines in the console, so the packet overflow reached the release
- [CHIM-SEYDA-RECEIPT-TEXT-40](CHIM-SEYDA-RECEIPT-TEXT-40.md): New Seyda metadata and carrier writers omit explicit UTF-8 and LF
- CI-01 (no report page): Windows short aliases mismatch resolved discovery paths in tests
- CI-ACTIONS-CACHE-NODE20-54 (no report page): The GitHub workflow pinned actions/cache v4.2.3, which runs on Node 20, a runtime GitHub retires
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-DRYRUN-CANCELLED-DEV3-67](CI-DRYRUN-CANCELLED-DEV3-67.md): The public CI's dry-run build of the v0.0.67-dev3 snapshot ran past its 20-minute limit and was cancelled; it took about two minutes before
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- [CI-JOBS-UNNAMED-53](CI-JOBS-UNNAMED-53.md): The six test jobs of the v0.0.53 CI split shipped with no names, and the maintainer was not told the new job list
- [CI-NEW-BUILDER-RULES-35](CI-NEW-BUILDER-RULES-35.md): Hosted CI failed on v0.0.35: the previous-release check refused the one-commit checkout and the run-name rule refused the Docker check's run name
- [CI-SHARD-TOOLS-SETUP-HANG-61](CI-SHARD-TOOLS-SETUP-HANG-61.md): A CI test shard hung in its tools setup step until the 30-minute job timeout cancelled it
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SOURCE-JOB-TIMEOUT-52](CI-SOURCE-JOB-TIMEOUT-52.md): The GitHub source check of v0.0.52 was cancelled at its 25-minute limit: the source-and-dry-run job outgrew it
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- CI-TAG-RUN-DUPLICATE-54 (no report page): The release tag push ran the whole CI test suite again on a commit main had already passed
- [CI-TEST-SHARD-ONE-SLOW-53](CI-TEST-SHARD-ONE-SLOW-53.md): The first test shard of the v0.0.53 GitHub run took six times as long as the others
- [CONTAINER-READ-ENOMEM-66](CONTAINER-READ-ENOMEM-66.md): In the development container, reads of the repository files sometimes fail with "Cannot allocate memory"; a retry works, so a check that hits it can report an unrelated failure
- [DELIVERY-LEAVES-LINE-UNCLEAN-66](DELIVERY-LEAVES-LINE-UNCLEAN-66.md): A snapshot delivery wrote the cell tracker page into the release line's working copy, so the line's next gate was not clean and could not be published
- [DELIVERY-RERUN-STOPS-ON-OWN-OUTPUT-66](DELIVERY-RERUN-STOPS-ON-OWN-OUTPUT-66.md): A second delivery of a snapshot stopped on what the first one left: its source package folder, then its Pi image, reported as a failed upload although the upload had gone through
- [DIALOGUE-OPENMW-AB-MISSING-67](DIALOGUE-OPENMW-AB-MISSING-67.md): Missing: the A/B of the dialogue against headless OpenMW 0.51 (the same speakers, topics and states give the same answers)
- [DOCS-PUBLIC-CHAT-QUOTES-56](DOCS-PUBLIC-CHAT-QUOTES-56.md): Public bug pages and code comments carried the maintainer's chat words and swearing
- [DOCS-PUBLIC-PRIVATE-CHANNEL-66](DOCS-PUBLIC-PRIVATE-CHANNEL-66.md): Public register text, code comments and test data named the private channel a report came through
- [DOCS-REGENERATE-ALL-MISSING-67](DOCS-REGENERATE-ALL-MISSING-67.md): A change that touches the bug register leaves several generated documents stale, and the checks find them one at a time: each full test run fails on the next stale page
- DOOR-ENTRANCE-AUDIT-51 (no report page): Requested: an entrance check in every build: each exterior entrance of the original must have a door that leads into its interior, found from the map, missing ones listed
- EMULATOR-SESSION-BESIDE-SMOKE-53 (no report page): A scripted FS-UAE evidence session ran beside a gate boot smoke (one emulator at a time)
- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies
- ENGINE-SMOKE-PREP-KILLED-52 (no report page): The engine smoke's play-copy step is killed on and off: copying the 4 GiB boot disk through the page cache fills its 2 GiB container
- ENGINE-WARNING-ROOM-PREGROW-54 (no report page): RoomPreGrow in chim_room.c compares signed with unsigned and broke the warning-free engine build
- [ENTITY-TRACKER-CELL-CHECK-LAYERS-66](ENTITY-TRACKER-CELL-CHECK-LAYERS-66.md): With the expansions selected, the entity tracker's per-cell loss check is skipped without a word
- [GATE-EMBERS-31](GATE-EMBERS-31.md): Ember commit broke native torch tests and a header format check
- [GATE-HOSTPARITY-TEMP-RACE-33](GATE-HOSTPARITY-TEMP-RACE-33.md): Two gates running at once share the host-parity step's log file, so one gate can report the other's error
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-NUMPY-PATH-SCRATCH-33](GATE-NUMPY-PATH-SCRATCH-33.md): The gate's NumPy and Pillow import folder lived in a temporary per-session folder, so gates broke once it was removed
- GATE-PRIVACY-NAMES-SWEARING-57 (no report page): The gate checked assistant names only in changed lines, never in file or folder names or the whole tree, and swearing in public text not at all
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SHARED-SOURCE-32](GATE-SHARED-SOURCE-32.md): The local gate always tested the main checkout, in one shared folder
- GATE-SMOKE-IMAGE-REMOVED-54 (no report page): Every gate failed its smoke part: the image it boots lived in an old build run that the automatic Docker cleanup retired
- [GATE-SMOKE-NO-REMOTE-CONTROL-60](GATE-SMOKE-NO-REMOTE-CONTROL-60.md): Gate boot smokes sometimes fail with no remote control after boot
- [GATE-SOURCE-RACE-33](GATE-SOURCE-RACE-33.md): The local gate copies the working tree after its clean check, so edits during the copy reach the tested source
- GATE-STAGES-DIRTY-WORKTREE-54 (no report page): A gate copies the worktree as it is when it starts, not the commit it was launched for
- [GATE-SUITE-WRITABLE-32](GATE-SUITE-WRITABLE-32.md): The test suite needs a writable source copy and an executable /tmp; the documented command does not say so
- [HARNESS-NEWGAME-BOX-STALL-54](HARNESS-NEWGAME-BOX-STALL-54.md): An FS-UAE session stalled at the Start a new game box before any map load: the probe sent its key on a fixed delay
- HORS-AFTER-HALLOWEEN-STAYS-ARENA-58 (no report page): dbg aw hors after the Halloween scene no longer crashes on the v0.0.58-dev5 image but leaves the player in the Arena Pit instead of Seyda Neen
- [JOURNEY-AIM-RETRY-YAW-66](JOURNEY-AIM-RETRY-YAW-66.md): The gameplay journey aimed at a door from an eye position that had changed: its thirteen retries ran round the wrong direction
- [JOURNEY-DOOR-USE-GOES-TO-ACTOR-66](JOURNEY-DOOR-USE-GOES-TO-ACTOR-66.md): The opening journey's use key at the census street door went to the body of the guard killed a step before, or to a message box still showing, and the step then waited for a load it had never asked for
- [JOURNEY-PART-B-SAVE-NOT-CARRIED-66](JOURNEY-PART-B-SAVE-NOT-CARRIED-66.md): The gameplay journey's second part never loaded the first part's save: the save was written where the session does not carry it
- [JOURNEY-STEP6-VICTIM-NEAREST-66](JOURNEY-STEP6-VICTIM-NEAREST-66.md): The opening journey's step 6 killed the nearest resident, which could be the guard by the census office's street door, whose body then took the use key instead of the door
- [JOURNEY-STEP7-FIGHT-UNREACHABLE-66](JOURNEY-STEP7-FIGHT-UNREACHABLE-66.md): The gameplay journey fight in step 7 took no health: the nearest resident was inside the census office, could not reach the player and fled
- [JOURNEY-STEP7-FIGHTER-NEAREST-66](JOURNEY-STEP7-FIGHTER-NEAREST-66.md): The opening journey's step 7 fights the nearest resident, which can be Fargoth, who fights unarmed, so the health may stay as it was
- [JOURNEY-WALK-DIALOGUE-DESYNC-66](JOURNEY-WALK-DIALOGUE-DESYNC-66.md): The gameplay journey lost its way in the census office: its key presses talked to the clerk and chose Persuasion instead of taking the papers, and every later step ran in that window
- KIT-CI-JOBS-SPLIT-53 (no report page): The release kit did not know the split CI workflow: its job check refused it and its publisher waited for the old job names
- LINUX-VALID-02 (no report page): Linux test fixtures failed to link (missing stubs)
- [MWAD-NAME-CLASH-66](MWAD-NAME-CLASH-66.md): tools/mwad.py has the name of the src/mwad package and hides it for any process with tools before src
- [MWAD-TEXT-WRITER-LF-35](MWAD-TEXT-WRITER-LF-35.md): Some JSON and text writers do not pin LF and UTF-8
- [NOTES-MOURNHOLD-WAY-STALE-67](NOTES-MOURNHOLD-WAY-STALE-67.md): The development notes of v0.0.67 said the way to Mournhold was not in the build, while the trip to Mournhold and back already worked
- [OPS-GATE-UNLISTED-TESTS-36](OPS-GATE-UNLISTED-TESTS-36.md): The gate runs only the tests listed in the public file list, and nothing checked that every test file is listed
- [PLAYTEST-SHIPPED-WITHOUT-SMOKE-36](PLAYTEST-SHIPPED-WITHOUT-SMOKE-36.md): The v0.0.36-dev3 private playtest package was published with an engine that dies on every map load: no ship step or gate booted it
- PREGATE-GLOBAL-SHADOW-58 (no report page): Pregate C check misses global shadowing; the engine build fails on it
- PREGATE-SYNTAX-SKIP-SILENT-57 (no report page): The pre-gate C syntax check skipped itself without failing on worktrees in the per-version folder layout
- [PUBLIC-GUARD-SPELLS-TOOL-NAMES-67](PUBLIC-GUARD-SPELLS-TOOL-NAMES-67.md): The public privacy check spells the private words it refuses, split in pieces, in its own code
- [REGISTER-WRITE-EINVAL-67](REGISTER-WRITE-EINVAL-67.md): The register tool stops now and then with "Invalid argument" while it writes docs/BUGS.md, after it has already saved the entry
- [REGRESSION-GUARD-MISSING-67](REGRESSION-GUARD-MISSING-67.md): Things the maintainer had confirmed working in play come back broken in later builds: no check kept them proven after their fix
- [RELEASE-CHECK-NOTES-LATE-66](RELEASE-CHECK-NOTES-LATE-66.md): The release check of the notes' core-use claims ran only when the snapshot package was made, after the build and its play tests, and read a sentence about allowed workers as a claim
- [RELEASE-CONNECT-STEP-SKIPPED-53](RELEASE-CONNECT-STEP-SKIPPED-53.md): After v0.0.52 and v0.0.53 were published the release's connect-it-fully step was skipped: the pinned previous release and the size baseline stayed at v0.0.51
- [RELEASE-GATE-COMPLETENESS-LOST-67](RELEASE-GATE-COMPLETENESS-LOST-67.md): The release check passes with rooms of a shipped expansion missing and without checking the expansions' doors
- [RELEASE-INCLUSION-CHECK-LATE-48](RELEASE-INCLUSION-CHECK-LATE-48.md): The release guard does not check the CHIM inclusion ledger: the v0.0.48 kit stopped in its source step after the guard and the full suite had passed
- [RELEASE-KIT-NO-REPAIR-MODE-35](RELEASE-KIT-NO-REPAIR-MODE-35.md): The release kit has no repair mode for a commit already pushed
- [RELEASE-KIT-PUSH-BEFORE-CI-45](RELEASE-KIT-PUSH-BEFORE-CI-45.md): The release kit pushes to main before CI has passed
- [RELEASE-KIT-RETRY-REUSES-CI-45](RELEASE-KIT-RETRY-REUSES-CI-45.md): A kit retry after a CI failure reads the same failed run again
- [RELEASE-LAVA-IMAGE-ALLOWLIST-38](RELEASE-LAVA-IMAGE-ALLOWLIST-38.md): Lava documentation images were listed without image-type approval
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [RELEASE-PATCH-TARGET-VERSION-39](RELEASE-PATCH-TARGET-VERSION-39.md): RC1 publication baseline lacks its target version
- [ROOM-TRACE-VISIT-GUARD-48](ROOM-TRACE-VISIT-GUARD-48.md): Long downward traces on the Hall of Processing's collision raise the trace visit guard (Cyclic or excessive collision tree)
- [ROUTE-PREFLIGHT-OWN-PROOFS-STOP-67](ROUTE-PREFLIGHT-OWN-PROOFS-STOP-67.md): The release route's final preflight stops on the proof sessions of its own release image
- [SESSION-CLIP-UNPLAYABLE-ON-STALL-67](SESSION-CLIP-UNPLAYABLE-ON-STALL-67.md): The screen recording of an emulator session that stalls cannot be opened: the recorder is cut off before it writes the index of the MP4 file, so the clip of the session that showed the stall is lost
- [SESSION-ENGINE-NOT-A-FILE-67](SESSION-ENGINE-NOT-A-FILE-67.md): An emulator session given an engine path that is not a file runs the image with no engine and waits 320 s for the remote control, instead of refusing at once
- [SESSION-PASS-DEAD-ENGINE-57](SESSION-PASS-DEAD-ENGINE-57.md): The scripted test session reported PASS while the engine had crashed
- [SESSION-STALL-CENSUS-QUICKSTART-58](SESSION-STALL-CENSUS-QUICKSTART-58.md): On the v0.0.58-dev6 image a session that quick-starts into the Census and Excise Office at 135 172 64 stalls before its first still: the runner reports game stalled with the game clock frozen at 23.23 s
- [SESSION-STALL-EMPTY-STATE-READ-67](SESSION-STALL-EMPTY-STATE-READ-67.md): A scripted test session ends as a game stall when one read of the game's state comes back empty, although the game runs on
- [SMOKE-DELIVERY-OLD-COPY-58](SMOKE-DELIVERY-OLD-COPY-58.md): The playtest delivery ran an old copy of the boot smoke: the v0.0.58 release smoke failed four times on a working image
- [SMOKE-END-CONSOLE-TOGGLE-OUTSIDE-PLAY-64](SMOKE-END-CONSOLE-TOGGLE-OUTSIDE-PLAY-64.md): A scripted session whose last step closes the console is judged as ended outside play while the game is in play
- [SMOKE-IDE-TRACE-LOG-63](SMOKE-IDE-TRACE-LOG-63.md): The gate smoke runs the emulator with its IDE trace log on, about 41 MB per two-minute run
- [SMOKE-INPLAY-UNSAMPLED-63](SMOKE-INPLAY-UNSAMPLED-63.md): The boot smoke never examines a stop where the game does not get into play after a load
- SMOKE-KEY-DURING-LOGO-52 (no report page): The engine smoke can type its console command while the logo is still up: the m of map is the logo s not-now key for the extra Fast RAM, so the start runs without the CHIM cache and the 32 MB zone check fails falsely
- SMOKE-M-KEY-SKIPS-CHIM-CACHE-57 (no report page): The gate's boot smoke sometimes fails with the CHIM zone full: an M typed while the startup memory notice shows turns the CHIM cache off for that start
- [SMOKE-MUSIC-REREAD-FLAKY-57](SMOKE-MUSIC-REREAD-FLAKY-57.md): The boot smoke's music check fails now and then: music is not read again after dbg music on (reads 35 -> 35), a rerun passes
- [SMOKE-PASSES-WITHOUT-MAP-36](SMOKE-PASSES-WITHOUT-MAP-36.md): The engine boot smoke passed while its first map ran under the title menu: a loaded server was taken for a played map
- [SMOKE-PROBE-ARRIVAL-LOAD-NOT-STARTED-64](SMOKE-PROBE-ARRIVAL-LOAD-NOT-STARTED-64.md): The session probe reports a MiniWind as never started while the preset's own arrival step is loading a room, and runs none of the session script
- SMOKE-SEYDA-AGAIN-NOT-IN-PLAY-58 (no report page): The boot smoke failed once with 'seyda again (before load 3 of 3) is not in play'; the rerun on the same commit passed
- [SMOKE-STALL-LABEL-INFERRED-60](SMOKE-STALL-LABEL-INFERRED-60.md): The boot smoke names a stop an emulator disk stall without checking the pending disk request
- [SMOKE-TALK-BOX-BLOCKS-REMOTE-57](SMOKE-TALK-BOX-BLOCKS-REMOTE-57.md): The boot smoke failed with a talk box (Yes?) open in Seyda Neen right after the load: the remote commands went unanswered and the music check read nothing
- [STALL-PROBE-NAME-BPTR-66](STALL-PROBE-NAME-BPTR-66.md): The stall examination showed no file name for a stuck open, lock or delete: it read the name at the raw BCPL pointer instead of the pointer times 4
- [STALL-PROBE-PROMPT-LOG-LINE-66](STALL-PROBE-PROMPT-LOG-LINE-66.md): The stall examination missed the debugger's prompt when an emulator log line followed it on the same line, never resumed the emulator, and the paused session read as a stop of the game
- [STALL-PROBE-RUNNING-GAME-66](STALL-PROBE-RUNNING-GAME-66.md): The stall examination read a running game as a missing task or as waiting on a file reply: it walked only the ready and waiting task lists and took the wait mask of a task that was not waiting
- [TEST-ACTOR-GROUND-SLICED-POOL-LOAD-67](TEST-ACTOR-GROUND-SLICED-POOL-LOAD-67.md): The actor ground fit identity test stopped once with a broken process pool while other test runs and gates loaded the machine; it passed when run again alone
- [TEST-ACTOR-LIBRARY-OFF-PLAN-48](TEST-ACTOR-LIBRARY-OFF-PLAN-48.md): test_actor_library StageTests.test_on_by_default_off_selectable fails on the interiors line: the actor-library stage stays in the plan with --chim-actor-table off
- [TEST-BUILD-STALL-STARTUP-TIMING-67](TEST-BUILD-STALL-STARTUP-TIMING-67.md): The build stall test of a startup watch (test_a_watch_started_before_the_run_name_writes_once_it_has_one) failed once in a gate on a busy machine: it allows the watch 0.2 s to write
- [TEST-CENSUS-CONTRACTS-40](TEST-CENSUS-CONTRACTS-40.md): Three quick-character expected failures lack reconciled contracts
- [TEST-CHIM-BIG-FRAME-TIMEOUT-33](TEST-CHIM-BIG-FRAME-TIMEOUT-33.md): The Balmora-sized CHIM world test times out on a loaded machine
- [TEST-CHIMPORT-POOL-COPY-REUSE-48](TEST-CHIMPORT-POOL-COPY-REUSE-48.md): test_chimport_pool test_copy_mode_reuses_by_verified_copy fails on the interiors branch head
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded machine (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- TEST-FACT-ROWS-WAITING-51 (no report page): The register's page test did not know the optional Waiting on and Deferred fact rows: the first bug page with a waiting reason failed the gate
- [TEST-GODMODE-UNLISTED-36](TEST-GODMODE-UNLISTED-36.md): The dbg godmode test was never run by the gate (missing from the public file list) and its escape check failed
- [TEST-HEAP-WATCHER-UNDER-LOAD-66](TEST-HEAP-WATCHER-UNDER-LOAD-66.md): The heap watcher native test failed in a full gate run and passed when run alone
- [TEST-MWAD-MODULE-SHADOW-48](TEST-MWAD-MODULE-SHADOW-48.md): test_room_late_passes fails to import when test_optimize_world_maps runs before it in the same process: tools/mwad.py hides the mwad package
- [TEST-NATIVE-STALE-IMPORT-33](TEST-NATIVE-STALE-IMPORT-33.md): Native engine tests run alone generate their version headers with the builder image's old tools copy
- [TEST-NATIVE-TMPDIR-32](TEST-NATIVE-TMPDIR-32.md): A native test overflows a 64-byte name buffer when the temp path is long
- [TEST-PARALLEL-ORDER-FLAKY-36](TEST-PARALLEL-ORDER-FLAKY-36.md): test_processes_keep_order_and_limit_nested_threads is timing-sensitive and fails now and then
- [TEST-PARALLEL-ORDER-LOAD-33](TEST-PARALLEL-ORDER-LOAD-33.md): The process-pool order test fails on a fully loaded machine (one worker process takes every item)
- [TEST-PARALLEL-SHARE-TIMING-36](TEST-PARALLEL-SHARE-TIMING-36.md): The fair-share scheduler test watched the freed budget for a fixed 4 s and failed on a loaded machine
- [TEST-POOL-LIVE-GROWTH-FLAKY-64](TEST-POOL-LIVE-GROWTH-FLAKY-64.md): The pool live growth test fails once in a full suite run while the machine is busy and passes when run alone
- [TEST-POOL-LONGEST-FIRST-LOAD-66](TEST-POOL-LONGEST-FIRST-LOAD-66.md): The pool test of longest-first ordering failed once in a gate run while two other gates shared the machine, and passes when run alone
- [TEST-POOL-QUEUE-REFILL-TIMING-64](TEST-POOL-QUEUE-REFILL-TIMING-64.md): The pool queue refill test (test_longest_first) failed once in a gate on a busy machine and passed on the rerun of the same commit
- [TEST-POOL-QUEUE-REFILL-TIMING-68](TEST-POOL-QUEUE-REFILL-TIMING-68.md): The pool queue test that checks the longest units start first fails now and then on a loaded machine
- [TEST-POOL-RESUME-SHELL-CONTAINER-58](TEST-POOL-RESUME-SHELL-CONTAINER-58.md): A stage-key test fails when run on its own in the shell container: a pool-mode resume reuses the scene-chain stage it should rerun
- [TEST-POOL-SCENE-RESUME-ENV-64](TEST-POOL-SCENE-RESUME-ENV-64.md): A stage-key test fails when run directly in the shell container but passes in the gate
- TEST-PORT-01 (no report page): Focused tests depended on repo root and Windows UTF-8 mode
- TEST-PORTABILITY-01 (no report page): Pre-release test fixtures assumed host features and links
- [TEST-PROFILE-OVERHEAD-SAMPLES-36](TEST-PROFILE-OVERHEAD-SAMPLES-36.md): The profiler overhead test sampled for a fixed 2 s and got too few samples on a loaded machine
- [TEST-PROFILE-SECTION-CPU-32](TEST-PROFILE-SECTION-CPU-32.md): The build profile section test fails on a loaded machine (CPU time read in clock ticks)
- [TEST-PROFILE-STAGE-WALL-32](TEST-PROFILE-STAGE-WALL-32.md): The build profile stage test needs an idle machine (wall time compared with CPU time)
- [TEST-PROFILE-TIMELINE-BOUND-33](TEST-PROFILE-TIMELINE-BOUND-33.md): A profiler test bounds the sampled CPU too tightly and fails on a loaded machine
- [TEST-PROFILE-TIMELINE-SUM-33](TEST-PROFILE-TIMELINE-SUM-33.md): The build profile test's sampled-timeline check fails on a loaded machine (timeline CPU above the stage's own CPU)
- [TEST-RC1-INTEGRATION-CONTRACTS-39](TEST-RC1-INTEGRATION-CONTRACTS-39.md): RC1 regression tests assume the old fingerprint location and a separate class cache unit
- [TEST-SAVED-EQUIPMENT-NATIVE-FLAKY-64](TEST-SAVED-EQUIPMENT-NATIVE-FLAKY-64.md): The saved equipment native test errors once in a full suite run while the machine is busy and passes when run alone
- [TEST-SKEL-NATIVE-FLAKY-UNDER-LOAD-60](TEST-SKEL-NATIVE-FLAKY-UNDER-LOAD-60.md): Native test test_skel_native (left_arm_takes_the_layer_frame) fails once under host load
- [TEST-SPAWN-SCAN-DOCSTRING-KEY-48](TEST-SPAWN-SCAN-DOCSTRING-KEY-48.md): The spawn contract scan read a docstring example in hand_metadata.py as a map key named key
- [TEST-TOWN-BOUNDS-40](TEST-TOWN-BOUNDS-40.md): Town expansion left recovery fixtures and coordinate audit stale
- [TEST-TRACKER-SLOW-48](TEST-TRACKER-SLOW-48.md): Bug register render, contents check and tracker tests take 5 to 6 minutes on one core
- [TEST-WORKER-SYSPATH-32](TEST-WORKER-SYSPATH-32.md): Pool workers started from tests import tools/mwad.py instead of the mwad package
- [TESTS-HEAD-REDUCER-BYTES-CI-45](TESTS-HEAD-REDUCER-BYTES-CI-45.md): A byte-exact head reducer test fails on some GitHub runners
- [TESTS-SUPERVISOR-START-CLOCK-46](TESTS-SUPERVISOR-START-CLOCK-46.md): A scheduler test sorted units by the clock each worker read, and failed when the host delayed a thread
- [TOOLKIT-TEST-POINTERLOCK-31](TOOLKIT-TEST-POINTERLOCK-31.md): Inspector test left pointer lock set, breaking later drag checks
- TOOLS-UNPINNED-WRITER-ATMOS-54 (no report page): tools/particle_emitters.py wrote JSON without pinned line endings
- TRACKER-BUGS-PAGE-SIZE-58 (no report page): docs/BUGS.md lists every bug with its whole status, archived ones too, so the archive rotation cannot keep it under its size limit: it reached 95.06 % of 1 MiB
- [VERSION-BUMP-TOOLKIT-HEADER-67](VERSION-BUMP-TOOLKIT-HEADER-67.md): A version opening leaves the Toolkit header, the previous-release pin and the size baseline at the old release, and the gate checks none of them

<!-- END GENERATED CATEGORY -->
