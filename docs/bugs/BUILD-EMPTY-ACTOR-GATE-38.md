# BUILD-EMPTY-ACTOR-GATE-38: resident-free exterior rejected by contact gate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 12 October 2026, in v0.0.38-dev1 |
| Where | tools/check_actor_ground.py and tools/build_aga.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.38 |
| Severity | low: Stops empty exterior scene packaging before playtest |
| Family | Gates, CI and tests (`tests-ci`) |
| Playtest version | lava-sandbox-candidate |
| From commit | source 296a389, engine 296a389, CHIM world 296a389 |
| CHIM engine version | CHIM 0.2.0, engine 296a389, world format 0.7 |
| Build note | Image actor-contact gate rejected zero placements after empty resident packaging succeeded |
| Platform or emulator | not in game (Build stops before image preparation) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41 (16 October 2026)._

<!-- contents start -->
## Contents

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

## Symptom

The lava-pools image stops with No actor placements found, although its original exterior contains no NPC residents. Five leveled-creature spawn markers remain unconverted gameplay coverage.

## Where

Image actor-contact gate at source 296a389, after CHIM conversion and town packaging.

## How it happened

The contact gate treats every empty image as lost actor content. That is correct for ordinary scenes but does not represent an intentionally resident-free diagnostic exterior.

## Why it was not caught

Earlier MiniWind scenes had residents. The new exterior first reached this check after its empty resident packaging was repaired.

## Reproduction

Build the lava-pools preset at 296a389. The failed contact receipt has zero placements and one missing-actors error.

## Repair

For an exterior-only MiniWind with one matching CHIM town and no other scene BSPs, inspect original master placements against the configured frame. Any original NPC, direct creature or unresolved object prevents the empty-scene evidence. Leveled-creature markers are recorded individually as unconverted coverage, never supported actors. Only the sole empty-actor error becomes not-applicable, with master hash and scope recorded. Production actor acceptance stays false. All other contact errors and ordinary builds remain fail-closed. No engine mechanism changes.

## Verification

Regression covers the original actor census, normal/full scope refusal, empty audit output and invalid actor rejection. The prior candidate passed its source gate but correctly refused image creation upon finding five leveled-creature markers. Refined candidate image and native checks remain pending.

## Prevention

Keep missing-content failures distinct from source-proven absence; do not infer absence from a baked resident list alone.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Gates, CI and tests (`tests-ci`). A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. See [families](README.md#families).

- [AW-RESULT-RECIPE-SAVED-36](AW-RESULT-RECIPE-SAVED-36.md): The master builder's result of a failed build from a requested recipe does not validate (recipe.saved left in)
- [AW-RUN-NAME-LONG-REASON-36](AW-RUN-NAME-LONG-REASON-36.md): aw gate refuses a long --reason after leasing the gate number: the run name, used as the request id, passes 128 characters
- [BUILD-CHECKLIST-JSON-CELLS-39](BUILD-CHECKLIST-JSON-CELLS-39.md): Exterior checklist rejects JSON cell coordinates before scenery conversion
- [BUILD-DEV1-EMULATOR-PRESETS-39](BUILD-DEV1-EMULATOR-PRESETS-39.md): Version bump omitted the matching dev1 emulator presets
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
- CI-ACTIONS-CACHE-NODE20-54 (no report page): The GitHub workflow pinned actions/cache v4.2.3, which runs on Node 20, a runtime GitHub retires
- [CI-BOOTSTRAP-NUMPY-32](CI-BOOTSTRAP-NUMPY-32.md): The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist
- [CI-ERICW-SKIP-31](CI-ERICW-SKIP-31.md): Torch test room test never runs in hosted CI or the builder image
- [CI-HOSTDEPS-30](CI-HOSTDEPS-30.md): Host CI job fails: scenery export needs the NIF reader for non-NIF test data
- CI-JOBS-UNNAMED-53 (no report page): The six test jobs of the v0.0.53 CI split shipped with no names, and the maintainer was not told the new job list
- [CI-NEW-BUILDER-RULES-35](CI-NEW-BUILDER-RULES-35.md): Hosted CI failed on v0.0.35: the previous-release check refused the one-commit checkout and the run-name rule refused the Docker check's run name
- [CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md): Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned
- [CI-SOURCE-JOB-TIMEOUT-52](CI-SOURCE-JOB-TIMEOUT-52.md): The GitHub source check of v0.0.52 was cancelled at its 25-minute limit: the source-and-dry-run job outgrew it
- [CI-SUITE-TWICE-33](CI-SUITE-TWICE-33.md): Hosted CI runs the full test suite twice per revision
- CI-TAG-RUN-DUPLICATE-54 (no report page): The release tag push ran the whole CI test suite again on a commit main had already passed
- [CI-TEST-SHARD-ONE-SLOW-53](CI-TEST-SHARD-ONE-SLOW-53.md): The first test shard of the v0.0.53 GitHub run took six times as long as the others
- DOCS-PUBLIC-CHAT-QUOTES-56 (no report page): Public bug pages and code comments carried the maintainer's chat words and swearing
- DOOR-ENTRANCE-AUDIT-51 (no report page): Requested: an entrance check in every build: each exterior entrance of the original must have a door that leads into its interior, found from the map, missing ones listed
- EMULATOR-SESSION-BESIDE-SMOKE-53 (no report page): A scripted FS-UAE evidence session ran beside a gate boot smoke (one emulator at a time)
- [ENGINE-O2-STRNCPY-WARNINGS-36](ENGINE-O2-STRNCPY-WARNINGS-36.md): At -O2 the engine build printed four -Wstringop-truncation warnings for bounded strncpy copies
- ENGINE-SMOKE-PREP-KILLED-52 (no report page): The engine smoke's play-copy step is killed on and off: copying the 4 GiB boot disk through the page cache fills its 2 GiB container
- [ENGINE-STRICT-WARNINGS-36](ENGINE-STRICT-WARNINGS-36.md): The engine builds warning-free only under -Wall -Wno-unused; stricter flags show 482 warnings
- ENGINE-WARNING-ROOM-PREGROW-54 (no report page): RoomPreGrow in chim_room.c compares signed with unsigned and broke the warning-free engine build
- [GATE-EMBERS-31](GATE-EMBERS-31.md): Ember commit broke native torch tests and a header format check
- [GATE-HOSTPARITY-TEMP-RACE-33](GATE-HOSTPARITY-TEMP-RACE-33.md): Two gates running at once share the host-parity step's log file, so one gate can report the other's error
- [GATE-NODE-MISSING-31](GATE-NODE-MISSING-31.md): The local gate never runs the inspector JavaScript tests (no Node.js in the Docker images)
- [GATE-NUMPY-PATH-SCRATCH-33](GATE-NUMPY-PATH-SCRATCH-33.md): The gate's NumPy and Pillow import folder lived in a temporary per-session folder, so gates broke once it was removed
- GATE-PRIVACY-NAMES-SWEARING-57 (no report page): The gate checked assistant names only in changed lines, never in file or folder names or the whole tree, and swearing in public text not at all
- [GATE-PRIVACY-SCAN-33](GATE-PRIVACY-SCAN-33.md): The source preflight does not scan file contents for tool or model names and private path prefixes
- [GATE-SHARED-SOURCE-32](GATE-SHARED-SOURCE-32.md): The local gate always tested the main checkout, in one shared folder
- GATE-SMOKE-IMAGE-REMOVED-54 (no report page): Every gate failed its smoke part: the image it boots lived in an old build run that the automatic Docker cleanup retired
- [GATE-SOURCE-RACE-33](GATE-SOURCE-RACE-33.md): The local gate copies the working tree after its clean check, so edits during the copy reach the tested source
- GATE-STAGES-DIRTY-WORKTREE-54 (no report page): A gate copies the worktree as it is when it starts, not the commit it was launched for
- [GATE-SUITE-WRITABLE-32](GATE-SUITE-WRITABLE-32.md): The test suite needs a writable source copy and an executable /tmp; the documented command does not say so
- HARNESS-NEWGAME-BOX-STALL-54 (no report page): An FS-UAE session stalled at the Start a new game box before any map load: the probe sent its key on a fixed delay
- KIT-CI-JOBS-SPLIT-53 (no report page): The release kit did not know the split CI workflow: its job check refused it and its publisher waited for the old job names
- LINUX-VALID-02 (no report page): Linux test fixtures failed to link (missing stubs)
- [MWAD-TEXT-WRITER-LF-35](MWAD-TEXT-WRITER-LF-35.md): Some JSON and text writers do not pin LF and UTF-8
- [OPS-GATE-UNLISTED-TESTS-36](OPS-GATE-UNLISTED-TESTS-36.md): The gate runs only the tests listed in the public file list, and nothing checked that every test file is listed
- [PLAYTEST-SHIPPED-WITHOUT-SMOKE-36](PLAYTEST-SHIPPED-WITHOUT-SMOKE-36.md): The v0.0.36-dev3 private playtest package was published with an engine that dies on every map load: no ship step or gate booted it
- PREGATE-SYNTAX-SKIP-SILENT-57 (no report page): The pre-gate C syntax check skipped itself without failing on worktrees in the per-version folder layout
- RELEASE-CONNECT-STEP-SKIPPED-53 (no report page): After v0.0.52 and v0.0.53 were published the release's connect-it-fully step was skipped: the pinned previous release and the size baseline stayed at v0.0.51
- [RELEASE-INCLUSION-CHECK-LATE-48](RELEASE-INCLUSION-CHECK-LATE-48.md): The release guard does not check the CHIM inclusion ledger: the v0.0.48 kit stopped in its source step after the guard and the full suite had passed
- [RELEASE-KIT-NO-REPAIR-MODE-35](RELEASE-KIT-NO-REPAIR-MODE-35.md): The release kit has no repair mode for a commit already pushed
- [RELEASE-KIT-PUSH-BEFORE-CI-45](RELEASE-KIT-PUSH-BEFORE-CI-45.md): The release kit pushes to main before CI has passed
- [RELEASE-KIT-RETRY-REUSES-CI-45](RELEASE-KIT-RETRY-REUSES-CI-45.md): A kit retry after a CI failure reads the same failed run again
- [RELEASE-LAVA-IMAGE-ALLOWLIST-38](RELEASE-LAVA-IMAGE-ALLOWLIST-38.md): Lava documentation images were listed without image-type approval
- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text
- [RELEASE-PATCH-TARGET-VERSION-39](RELEASE-PATCH-TARGET-VERSION-39.md): RC1 publication baseline lacks its target version
- [ROOM-TRACE-VISIT-GUARD-48](ROOM-TRACE-VISIT-GUARD-48.md): Long downward traces on the Hall of Processing's collision raise the trace visit guard (Cyclic or excessive collision tree)
- SESSION-PASS-DEAD-ENGINE-57 (no report page): The scripted test session reported PASS while the engine had crashed
- SMOKE-KEY-DURING-LOGO-52 (no report page): The engine smoke can type its console command while the logo is still up: the m of map is the logo s not-now key for the extra Fast RAM, so the start runs without the CHIM cache and the 32 MB zone check fails falsely
- SMOKE-M-KEY-SKIPS-CHIM-CACHE-57 (no report page): The gate's boot smoke sometimes fails with the CHIM zone full: an M typed while the startup memory notice shows turns the CHIM cache off for that start
- [SMOKE-MUSIC-REREAD-FLAKY-57](SMOKE-MUSIC-REREAD-FLAKY-57.md): The boot smoke's music check fails now and then: music is not read again after dbg music on (reads 35 -> 35), a rerun passes
- [SMOKE-PASSES-WITHOUT-MAP-36](SMOKE-PASSES-WITHOUT-MAP-36.md): The engine boot smoke passed while its first map ran under the title menu: a loaded server was taken for a played map
- SMOKE-TALK-BOX-BLOCKS-REMOTE-57 (no report page): The boot smoke failed with a talk box (Yes?) open in Seyda Neen right after the load: the remote commands went unanswered and the music check read nothing
- TEST-ACTOR-LIBRARY-OFF-PLAN-48 (no report page): test_actor_library StageTests.test_on_by_default_off_selectable fails on the interiors line: the actor-library stage stays in the plan with --chim-actor-table off
- [TEST-CENSUS-CONTRACTS-40](TEST-CENSUS-CONTRACTS-40.md): Three quick-character expected failures lack reconciled contracts
- [TEST-CHIM-BIG-FRAME-TIMEOUT-33](TEST-CHIM-BIG-FRAME-TIMEOUT-33.md): The Balmora-sized CHIM world test times out on a busy host
- TEST-CHIMPORT-POOL-COPY-REUSE-48 (no report page): test_chimport_pool test_copy_mode_reuses_by_verified_copy fails on the interiors branch head
- [TEST-COST-ORDER-LOAD-33](TEST-COST-ORDER-LOAD-33.md): The scheduler cost-order test fails on a fully loaded host (start times compared within a fraction of a second)
- [TEST-ENV-LEAK-HULL-33](TEST-ENV-LEAK-HULL-33.md): A sequential run of the suite fails the CHIM unit fingerprint test: an earlier in-process test leaves AMIWIND_MODEL_HULL set
- TEST-FACT-ROWS-WAITING-51 (no report page): The register's page test did not know the optional Waiting on and Deferred fact rows: the first bug page with a waiting reason failed the gate
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
- TOOLS-UNPINNED-WRITER-ATMOS-54 (no report page): tools/particle_emitters.py wrote JSON without pinned line endings

<!-- END GENERATED CATEGORY -->
