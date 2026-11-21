# ACTOR-AUDIT-APPENDED-TABLES-66: The actor record audit read a creature's animation table appended to the humanoid table as a plain one, so the skeletons, goblins, dremora and others counted as playing no animation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 17 November 2026, in v0.0.66 |
| Where | builder: the actor record audit's reader of animation tables (tools/anim_coverage.py table_groups, tools/actor_record_audit.py read_anim_build), used by the image step's actor spec check |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.66 (last seen) |
| Severity | medium: the build's actor spec check and the public audit counts over-reported missing animations (up to 561 records against about 160), hiding which actors really lack one; the game itself plays the full set |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.66 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (read from the release build's animation tables and the engine's table reader, no session) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.67-dev1 (ade41bda) | 2026-11-17 | gate 11030 passed on e75db7b8; tests/test_anim_coverage.py | the audit reads version 3 and 4 animation tables as the engine does and adds an appended table's base groups: about 160 records lack a kind on the v0.0.66 release build instead of up to 561 |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-17: reported in v0.0.66
- 2026-11-17: fixed in source: a gated commit, v0.0.67-dev1 (ade41bda); gate 11030 passed on e75db7b8; tests/test_anim_coverage.py: the audit reads version 3 and 4 animation tables as the engine does and adds an appended table's base groups: about 160 records lack a kind on the v0.0.66 release build instead of up to 561

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-ACTOR-MODEL-UNSUPPORTED-48](BUILD-ACTOR-MODEL-UNSUPPORTED-48.md): A Balmora build-speed measurement stopped on Unsupported actor model
- [BUILD-CACHE-NO-RETENTION-55](BUILD-CACHE-NO-RETENTION-55.md): The build cache keeps every entry forever: about 603 GB nothing recent uses
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47](BUILD-CHIM-CELLS-PRIVATE-LIST-47.md): The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells
- BUILD-CHIM-EARLY-CHECK-POOL-55 (no report page): The chim stage's early frame checks forked a worker pool of their own outside the stage's memory allowance
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-COMBAT-TEXT-SHADOW-61](BUILD-COMBAT-TEXT-SHADOW-61.md): The image step stops in its combat data part: a new local variable shadowed the stage's text helper
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-DIRECT-START-CELL-CHIM-64](BUILD-DIRECT-START-CELL-CHIM-64.md): A MiniWind direct start by cell stops the image step on a CHIM image
- [BUILD-DISK-NEED-UNKNOWN-52](BUILD-DISK-NEED-UNKNOWN-52.md): A public build can die halfway when the disk fills: the only space check runs once at the start, against a fixed 20 GiB, not what the release really takes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLAGS-MARK-SILENT-REFUSAL-66](BUILD-FLAGS-MARK-SILENT-REFUSAL-66.md): A build start is refused without a reason when the build options come from a file that begins with a byte-order mark
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- BUILD-GUARD-BLIND-NO-CGROUP-55 (no report page): Without a container memory limit the build's memory guard, its alarm and every pool's memory governor saw no memory at all
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
- [BUILD-LAYER-DATA-MWAD-SHADOWED-64](BUILD-LAYER-DATA-MWAD-SHADOWED-64.md): The Bloodmoon layer data stage stops with mwad is not a package in a MiniWind build
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-MERGED-MASTER-IN-CHECKOUT-66](BUILD-MERGED-MASTER-IN-CHECKOUT-66.md): The merged master of the selected game files is written into the source checkout's out folder also when --workspace names another folder; with a read-only checkout the build stops at its room grounding check before the first stage
- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- BUILD-MINIWIND-SEYDA-KELP-INDEX-54 (no report page): A Seyda Neen MiniWind can never pass: the chim-town-seyda stage stops because the kelp additions need the original scenery index, which a MiniWind plan does not build
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-NPC-GALLERY-SKIPPED-DEV-42](BUILD-NPC-GALLERY-SKIPPED-DEV-42.md): Development and playtest builds leave out the NPC gallery to save build time
- BUILD-NPC-RECIPES-COLLIDE-59 (no report page): Image step refuses the residents' recipe file written by several stages
- BUILD-NPC-RECIPES-PER-CELL-59 (no report page): Residents' recipe table held for the whole island instead of per cell and room
- BUILD-OOM-DEGRADE-NOT-DIE-54 (no report page): A worker killed for memory broke its stage's pool and failed the whole build
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
- [BUILD-PRESENTED-DATA-NO-WAIT-67](BUILD-PRESENTED-DATA-NO-WAIT-67.md): With the presented data folder on, the CHIM world stage did not wait for the stage that makes the folder it reads
- [BUILD-QCC-PATH-008](BUILD-QCC-PATH-008.md): Image assembly was given the QCC source directory as its compiler
- [BUILD-READINESS-MISSES-PLAN-WAIVERS-68](BUILD-READINESS-MISSES-PLAN-WAIVERS-68.md): The release readiness block does not list the Solstheim test route's options
- [BUILD-REGION-NO-LAND-PRESENTED-67](BUILD-REGION-NO-LAND-PRESENTED-67.md): The CHIM region land checks refused every cell without a LAND record, which Mournhold's presented districts are by design
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [BUILD-ROOM-SHELL-WRITER-UNPINNED-48](BUILD-ROOM-SHELL-WRITER-UNPINNED-48.md): The room shell form writes its conversion report without pinned encoding and line ends
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- BUILD-STAGE-KEY-NPC-MODULE-53 (no report page): The CHIM and town stages are keyed on the whole of src/mwad/npc.py, so a change to four NPCs in outfit() re-keys the CHIM world (22 of 43 stages, about 7 hours)
- [BUILD-TESTS-UNLISTED-48](BUILD-TESTS-UNLISTED-48.md): Seven test files of the v0.0.48 fix branches were not on the release list, so no gate ever ran them
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-TORCH-CREATURE-RESIDENT-42](BUILD-TORCH-CREATURE-RESIDENT-42.md): Image step stops in the torch guard on Vivec, an interior creature resident placed as an NPC entity
- [BUILD-VERSION-HEADER-RACE-61](BUILD-VERSION-HEADER-RACE-61.md): An engine build can stop on the warning that the generated CHIM version header is shorter than expected
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-FRAME-ALONE-FLAMES-48](CHIM-FRAME-ALONE-FLAMES-48.md): A town frame map read alone stops in its flames step: the frame-alone world holds its frames by index, the flames lookup walked them as a list
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [CHIM-LAVA-DUPLICATE-VERTEX-40](CHIM-LAVA-DUPLICATE-VERTEX-40.md): Float32 duplicate vertices falsely fail lava surface coverage
- [CHIM-OCEAN-ROUTING-UNNAMED-41](CHIM-OCEAN-ROUTING-UNNAMED-41.md): The world-terrain stage refused ocean routing cells without naming a cell or which rule failed
- [CHIM-ROOM-SHELL-ACTORS-EARLY-48](CHIM-ROOM-SHELL-ACTORS-EARLY-48.md): The scene stage actor check measured residents of shell rooms, which have no collision until the image: 110 refused
- [CHIM-SOL-TEST-MASTERS-NOT-IN-FOLDER-68](CHIM-SOL-TEST-MASTERS-NOT-IN-FOLDER-68.md): The Solstheim test frames stop at once: the stage reads the build's whole master list, which its own test data folder does not hold
- [CHIM-SOL-TEST-TWO-CHIMSOL-STORES-68](CHIM-SOL-TEST-TWO-CHIMSOL-STORES-68.md): A Solstheim test image stops in its image step: the test frames and the Solstheim build module both make the same store
- [CHIM-VISIBILITY-APRON-SCOPE-41](CHIM-VISIBILITY-APRON-SCOPE-41.md): Fixed stronghold visibility rejects regional aprons
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [CHIM-WINDOW-TOWER-SUPPORT-41](CHIM-WINDOW-TOWER-SUPPORT-41.md): Thatched tower omitted from decorative window facade support
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [ENGINE-FRAME-REFUSE-PROTOTYPE-48](ENGINE-FRAME-REFUSE-PROTOTYPE-48.md): The engine build stops on a missing prototype: AW_SceneFrameRefuse has no declaration
- [EXPANSION-ARCHIVE-READERS-66](EXPANSION-ARCHIVE-READERS-66.md): With the expansions selected, 24 builder stages that read the merged game data opened the base game archive alone, so a model or texture only an expansion archive holds was missing
- [EXPANSION-BASE-ONLY-TABLES-66](EXPANSION-BASE-ONLY-TABLES-66.md): With the expansions selected the build stopped at the focus table: activators and containers of Tribunal and Bloodmoon had no measured box, and their rooms had no rows
- [FRAME-HEAP-PEAK-MODELS-NUMBERING-67](FRAME-HEAP-PEAK-MODELS-NUMBERING-67.md): The frame memory report numbers its peak model lists differently in a build from scratch than in a build that reuses earlier work
- MINIWIND-EXTERIOR-DIRECT-START-CELL-57 (no report page): An exterior MiniWind direct start at cell 0,-7 (the Ascadian Isles creatures recipe) fails in the image step: no map of the build holds the point
- PREFLIGHT-GUARD-UNSTAMPED-NPCS-48 (no report page): The payload preflight guard count refused census.bsp: its three NPCs get their source identity later in the image step
- [RELEASE-FINAL-LINE-STALE-RC-48](RELEASE-FINAL-LINE-STALE-RC-48.md): The v0.0.48 final line was cut from an older rc1 head than the image: it lacked the two layout fixes the shipped image was built with
- [RELEASE-GUARD-NO-FROMSCRATCH-RULE-54](RELEASE-GUARD-NO-FROMSCRATCH-RULE-54.md): No release guard rule requires a from-scratch build: v0.0.52 and v0.0.53 shipped without one
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- [WIN-01](WIN-01.md): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [NPC-ATTACK-ANIMS-MISSING-65](NPC-ATTACK-ANIMS-MISSING-65.md): Most creatures play only six baked animation groups: no knockdown, spell cast, second or third attack

<!-- END GENERATED CATEGORY -->
